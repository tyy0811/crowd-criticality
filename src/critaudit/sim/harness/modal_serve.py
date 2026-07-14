"""Modal vLLM OpenAI-compatible endpoint for the LLM-harness reference cohort (Phase B, Task 9 Step 1).

$0 AUTHORING ARTIFACT — written and import-validated locally; NOT deployed. Steps 2-4 (deploy / smoke /
teardown) happen only AFTER a controller GPU-spend gate. Deploying this file is the FIRST time GPU is
touched in the whole sub-increment.

Serves `harness_spec.MODEL_ID` (Qwen2.5-7B-Instruct) at a concrete HF revision on a single A10, exposing
an OpenAI-compatible `/v1` endpoint that OASIS's CAMEL backend drives via the OPENAI_COMPATIBLE_MODEL
platform path (verified in the local rehearsal — see .superpowers/sdd/task9-rehearsal-report.md).

VERIFY-DON'T-RELAY corrections applied while authoring (modal client 1.4.0, verified 2026-07-14):
  * The current Modal docs example uses an `@app.server(...)` decorator — that decorator DOES NOT EXIST
    in the installed modal 1.4.0 (hasattr(App, "server") is False). The 1.4.0 canonical pattern is
    `@app.function(...)` + `@modal.web_server(port=...)` launching `vllm serve` via subprocess. That is
    what this file uses. (Re-check on a modal upgrade.)
  * GPU string: the current GPU reference page (modal.com/docs/reference/modal.gpu, 2026-07-14) lists the
    NVIDIA A10 as gpu="A10". The dispatch brief said "A10G" (the legacy AWS-variant alias). Modal does NOT
    validate the gpu string client-side (import-validation cannot catch a wrong one — it is checked
    server-side at deploy), so it is pinned below as a documented, one-line-swappable constant. If deploy
    rejects "A10", the fallback alias is "A10G".
  * Concurrency: Modal assigns ONE input per container by default (verified: docs/guide/concurrent-inputs).
    Without @modal.concurrent a single-container endpoint SERIALIZES requests, defeating vLLM's continuous
    batching and throttling OASIS's per-round fan-out (up to n_agents concurrent astep calls). The canonical
    vLLM pattern sets container concurrency; this file does so via @modal.concurrent (see GPU/cost note there).
"""
import os
import subprocess

import modal

MINUTES = 60  # seconds, for readable cap arithmetic below

# --- model identity ------------------------------------------------------------------------------
# Mirrors critaudit.sim.harness.harness_spec.MODEL_ID, read locally 2026-07-14 and kept here as a LITERAL
# (not imported) so bringing up the Modal container never requires importing the critaudit package
# remotely. Keep in sync by hand if harness_spec.MODEL_ID changes.
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
# Concrete commit resolved from HF `main` on 2026-07-14 (repo lastModified 2025-01-12). harness_spec.MODEL_REVISION
# is still the string "main" and gets PINNED to this exact commit at Task 10 Step 1 per the plan; we already
# serve the concrete commit here so the endpoint substrate is reproducible from first boot.
SERVED_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"

VLLM_PORT = 8000

# GPU: 1x NVIDIA A10 (24 GB VRAM) — owner decision. Qwen2.5-7B in bfloat16 is ~15.2 GB of weights, leaving
# ~6.8 GB for KV cache at --gpu-memory-utilization 0.92 and --max-model-len 8192 (tight but workable for
# modest concurrency). If the container OOMs at boot or under load, escalate to "A100-40GB" per design §7.
# "A10" is the current reference-page string; "A10G" is the legacy alias (see module docstring).
GPU = "A10"

app = modal.App("critaudit-harness-vllm")

# Image: pinned EXACTLY per the dispatch brief / current Modal vLLM example. No speculative decoding, no
# async-scheduling extras — one model, one GPU, minimal.
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
)

# Persistent caches so the ~15.2 GB of weights and vLLM's compiled artifacts survive container recycles
# (downloaded once into the volume, not on every cold boot). create_if_missing is lazy — the volumes are
# created at DEPLOY time by the controller, never at import.
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)


@app.function(
    image=vllm_image,
    gpu=GPU,                                   # 1x A10 (see GPU constant)
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    # Bearer token for the endpoint. The secret is NOT created by the authoring dispatch; the controller
    # creates it before deploy (command in the rehearsal report). Env var inside the container: VLLM_API_KEY.
    secrets=[modal.Secret.from_name("harness-vllm-token")],
    # CAP 1 - timeout: generous-but-FINITE backstop on the underlying function (owner directive: finite on
    #   everything). Actual chat requests are bounded far tighter by Modal's ~150 s HTTP-request cap and are
    #   short (~512-token completions); this 6 h ceiling only ever bites a forgotten/hung container, and idle
    #   ones are already reaped by scaledown_window below. Modal's max is 24 h; 6 h comfortably covers a full
    #   Phase-B cohort session while staying clear of the boundary. Raise toward 24 h if a session needs it.
    timeout=6 * 60 * MINUTES,
    # CAP 2 - scaledown_window: idle protection so a forgotten endpoint scales to zero after 5 min of no
    #   traffic (min_containers defaults to 0), instead of billing GPU-hours until manual teardown.
    scaledown_window=5 * MINUTES,
    # CAP 3 - startup_timeout (function-level): explicit finite container-startup cap so it is NOT inherited
    #   from `timeout` (Modal: an unset startup_timeout falls back to `timeout`). Matches the web_server boot
    #   budget below; first cold boot downloads ~15.2 GB into the volume.
    startup_timeout=15 * MINUTES,
    # CAP 4 - max_containers: hard 1 — no fan-out billing. Single GPU, single container for the whole cohort.
    max_containers=1,
)
# Container concurrency: let the ONE container accept many simultaneous requests so vLLM continuous-batches
# OASIS's per-round fan-out (up to n_agents=50 concurrent astep calls at the cohort operating point). Without
# this, Modal's default of one-input-per-container serializes requests and defeats batching. 64 covers a
# 50-agent round with headroom; max_containers=1 still caps billing to a single GPU.
@modal.concurrent(max_inputs=64)
# web_server: expose vLLM's own HTTP server (started by the subprocess below) as the Modal endpoint.
#   startup_timeout=15 min is the wait for vLLM to bind VLLM_PORT — sized for the ~15.2 GB cold-boot weight
#   download + CUDA/model init (default is 5 s, far too short).
@modal.web_server(port=VLLM_PORT, startup_timeout=15 * MINUTES)
def serve():
    """Launch the vLLM OpenAI-compatible server in-container. Runs only inside Modal at deploy/serve time;
    the body never executes during local import-validation (decorators evaluate; this function does not)."""
    cmd = [
        "vllm", "serve", MODEL_ID,
        "--revision", SERVED_REVISION,          # serve the concrete pinned commit, not floating `main`
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--served-model-name", MODEL_ID,        # clients request MODEL_ID (== harness_spec.MODEL_ID)
        # D0-critical tool-calling flags (the pipeline's identified fragility — vLLM's hermes parser is the
        # first thing re-verified in the Phase-B wiring smoke). Qwen2.5's chat template natively supports
        # Hermes-style tool use, so `hermes` is the documented parser choice.
        "--enable-auto-tool-choice",
        "--tool-call-parser", "hermes",
        "--dtype", "bfloat16",
        "--max-model-len", "8192",
        "--gpu-memory-utilization", "0.92",
        # Require Bearer auth. vLLM also auto-reads the VLLM_API_KEY env var, but pass it explicitly per the
        # serving-config spec. KeyError here would only fire at container runtime (secret missing), never at
        # local import (this body does not run then).
        "--api-key", os.environ["VLLM_API_KEY"],
        "--uvicorn-log-level", "info",
    ]
    subprocess.Popen(cmd)

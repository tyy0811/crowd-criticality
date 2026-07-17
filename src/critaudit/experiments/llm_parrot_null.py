"""Sub-inc-2 driver — matched parrot null (design 2026-07-17).

Part 1 (T5): theta calibration against the archived cohort's TRUE reply edges — the frozen
attribution-Youden procedure of llm_parrot_spec, structure-anchored and blind to every gate
quantity. Banked to results/s2_llm_parrot_null/.

FIREWALL (design §8, enforced by tests/test_llm_parrot_firewall.py): this module never imports the
τ-arm/powerlaw/scaling stack, never calls post_reply_tree on COHORT data, and never aggregates
attributed edges into any branching quantity on the cohort — cohort use is restricted to marginal
extraction + calibration against true edges. Cascade-def-#2 structure on the cohort is embargoed
to sub-inc 3.

$0 discipline: everything here reads the durable archive (~/crowd-crit-runs/s2_harness_subinc1/)
and runs local CPU. No GPU, no LLM, no network (the embedding revision is cached)."""
from __future__ import annotations
import json
import os

import numpy as np

from critaudit.cascades.similarity import attribution_rates_at_theta, calibrate_theta_pooled
from critaudit.sim.controls import llm_parrot_spec as lps
from critaudit.sim.harness.cohort_marginals import extract_marginals
from critaudit.sim.harness.oasis_adapter import export_harness_run

# The durable archive of the three registered cohort windows (sub-inc-1 writedown; raw artifacts
# never committed — repo convention). A location, not a spec constant.
DEFAULT_ARCHIVE = os.path.expanduser("~/crowd-crit-runs/s2_harness_subinc1")
_WINDOW_DIRS = {
    20260627: "windowA2_seed20260627",
    20260628: "windowB2_seed20260628",
    20260629: "windowC_seed20260629",
}
_TIMESTAMP_COL = "created_at"


def _window_db(archive_dir, seed):
    path = os.path.join(archive_dir, _WINDOW_DIRS[seed], "trace", "oasis.db")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"registered cohort DB missing: {path}")
    return path


def _round_of(run):
    """Round index per event (validated round-granular, same rule as extract_marginals)."""
    times = np.asarray(run.times, dtype=float)
    rounds = np.floor(times).astype(np.int64)
    if not np.all(times == rounds):
        raise ValueError("cohort stream is not round-granular (fail-closed)")
    return rounds


def load_cohort_windows(archive_dir=DEFAULT_ARCHIVE):
    """Export the three registered windows (WINDOW_ORDER) through the corrected authored-content
    exporter. Returns {seed: (run, marginals)} — the run feeds ONLY calibration (true edges) and
    marginal extraction; the generator sees marginals (+ pool embeddings) alone."""
    out = {}
    for seed in lps.WINDOW_ORDER:
        run = export_harness_run(_window_db(archive_dir, seed), timestamp_col=_TIMESTAMP_COL)
        out[seed] = (run, extract_marginals(run))
    return out


def run_theta_calibration(archive_dir=DEFAULT_ARCHIVE, out_path=None):
    """The frozen calibration (design §6): pooled attribution-Youden over the three registered
    windows' TRUE edges, candidates never crossing windows. Returns the banked record (dict);
    writes deterministic JSON to out_path when given (sorted keys, no wall-clock — byte-identical
    on re-run). Embeddings via the pinned realization; per-window embedding checksums recorded."""
    import hashlib
    from critaudit.sim.harness.embedding import embed_texts

    windows = load_cohort_windows(archive_dir)
    streams, per_window = [], {}
    for seed in lps.WINDOW_ORDER:
        run, marginals = windows[seed]
        E = embed_texts(marginals.authored_texts)
        rounds = _round_of(run)
        streams.append((run.parent_idx, rounds, E))
        per_window[str(seed)] = {
            "n_events": int(run.times.size),
            "n_true_edges": int((run.parent_idx >= 0).sum()),
            "n_true_roots": int((run.parent_idx < 0).sum()),
            "n_rounds": int(rounds.max()) + 1,
            "embedding_sha256": hashlib.sha256(E.tobytes()).hexdigest(),
            "_stream": (run.parent_idx, rounds, E),          # stripped before banking
        }

    res = calibrate_theta_pooled(streams)
    for seed_str, w in per_window.items():
        tpr, fpr = attribution_rates_at_theta(*w.pop("_stream"), res.theta)
        w["tpr_at_theta"] = tpr
        w["fpr_at_theta"] = fpr

    record = {
        "artifact": "theta_calibration",
        "design": lps.DESIGN_DOC,
        "design_sha256": lps.DESIGN_DOC_SHA256,
        "spec": {
            "embed_model_id": lps.EMBED_MODEL_ID,
            "embed_revision": lps.EMBED_REVISION,
            "cosine_decimals": lps.COSINE_DECIMALS,
            "theta_grid": [lps.THETA_GRID_START, lps.THETA_GRID_STOP, lps.THETA_GRID_STEP],
            "criterion": lps.THETA_CRITERION,
            "tie_rule": lps.THETA_TIE_RULE,
            "candidate_rule": lps.CANDIDATE_RULE,
            "window_order": list(lps.WINDOW_ORDER),
        },
        "theta": res.theta,
        "tpr": res.tpr,
        "fpr": res.fpr,
        "auc": res.auc,
        "same_round_ceiling": res.same_round_ceiling,
        "j_curve": [list(row) for row in res.j_curve],
        "per_window": per_window,
    }
    if out_path is not None:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(record, f, sort_keys=True, indent=1)
            f.write("\n")
    return record

"""Dormant recoverability runner for the causal reply probe (plan Task 7B).

The runner stays DORMANT through Tasks 1-7: `--dry-run` performs the hash preflight
(pre-draw OASIS setups through root creation only, canonical eligibility evidence,
frame/evidence/manifest hashing, teardown before any selection, treatment, action,
marker cascade, or outcome) and `--execute` — which requires the separate Task-8
owner authorization — runs ONLY the scripted full-platform control and the disjoint
marker control. Provider INFERENCE is uninvoked and fail-closed: every platform
session runs on the sentinel model wrapper, which raises on any model call, so no
provider network/inference path is exercised (the wrapper class is constructed but
never invoked). This module imports no provider client or driver-side inference
path — asserted by the runner import-surface test.

Gate clauses are frozen here, before any execution, and cannot change after
`--execute` begins: the evaluator is a pure function of the executed ledgers, the
hash-pinned power artifact, and the frozen manifest.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
import tempfile

import numpy as np

from critaudit.experiments.causal_probe_power import (
    MAX_MEAN_CI_FULL_WIDTH,
    MC_MAX_HALF_WIDTH,
    PLANT_R_GRID,
    RECOVERABILITY_SEEDS,
    TARGET_COVERAGE,
    TARGET_POWER,
    build_power_frame,
    build_power_schedule,
    write_canonical_json,
)
from critaudit.sim.controls.causal_probe_control import (
    CONTROL_SEED_STREAM,
    ScriptedControlRun,
    run_scripted_oasis_control,
)
from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_OPPORTUNITIES_PER_PARENT,
    MARKER_ROOT_COUNT,
    MARKER_ROUND_OFFSET,
    MARKER_ROUNDS,
    MARKER_SEED_STREAM,
    MARKER_SEEDS,
    MarkerGridCell,
    aggregate_marker_cell,
    locate_chi_peak,
    require_disjoint_manifests,
    require_disjoint_seed_sets,
    run_recursive_marker_control,
)
from critaudit.sim.harness import causal_probe_spec as spec
from critaudit.sim.harness.causal_probe import estimate_r_reply
from critaudit.sim.harness.causal_probe_records import (
    ProbeManifest,
    frame_eligibility_evidence_from_bytes,
    frame_eligibility_evidence_sha256,
    sampling_frame_from_bytes,
    sampling_frame_sha256,
    sampling_frame_to_bytes,
)
from critaudit.sim.harness.causal_probe_validation import (
    validate_frame_provenance,
    validate_sampling_frame,
)

__all__ = (
    "RECOVERABILITY_CELL_STREAM",
    "RecoverabilityManifest",
    "build_recoverability_manifest",
    "derive_cell_seed",
    "evaluate_recoverability_gate",
    "load_recoverability_manifest",
    "main",
    "run_dry_run",
    "run_execute",
    "write_recoverability_artifact",
)

# Registered independence derivation (review F4): the executed grid draws each
# (registered seed, cell) with an independent child seed. Reusing a raw seed
# across plants would NEST the potential schedules (shared uniforms across
# cells) and replay identical selection/treatment streams — a joint law the
# banked power simulator, which draws cells independently, does not describe.
RECOVERABILITY_CELL_STREAM = 941


def derive_cell_seed(seed: int, cell_index: int) -> int:
    return int(np.random.SeedSequence(
        int(seed), spawn_key=(RECOVERABILITY_CELL_STREAM, int(cell_index))
    ).generate_state(1)[0])


@dataclass(frozen=True)
class RecoverabilityManifest:
    schema_version: int
    power_artifact_path: str
    power_artifact_sha256: str
    frame_sha256s: tuple
    eligibility_evidence_sha256s: tuple
    plant_r_grid: tuple
    seeds: tuple
    marker_seeds: tuple
    branch_b_text: str


def _file_sha256(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _load_verified_power_artifact(path: str):
    digest = _file_sha256(path)
    if digest != spec.POWER_ARTIFACT_SHA256:
        raise ValueError(
            f"power artifact sha256 drift: {digest} != frozen "
            f"{spec.POWER_ARTIFACT_SHA256} (fail-closed)")
    with open(path) as handle:
        artifact = json.load(handle)
    constants = artifact["registered_constants"]
    expected = {
        "TARGET_COVERAGE": TARGET_COVERAGE,
        "MAX_MEAN_CI_FULL_WIDTH": MAX_MEAN_CI_FULL_WIDTH,
        "TARGET_POWER": TARGET_POWER,
        "MC_MAX_HALF_WIDTH": MC_MAX_HALF_WIDTH,
        "PLANT_R_GRID": list(PLANT_R_GRID),
        "RECOVERABILITY_SEEDS": list(RECOVERABILITY_SEEDS),
        "MARKER_SEEDS": list(MARKER_SEEDS),
    }
    for key, value in expected.items():
        if constants.get(key) != value:
            raise ValueError(
                f"power artifact registers a changed threshold {key} "
                f"(fail-closed)")
    if artifact.get("selected_support") != spec.SELECTED_SUPPORT:
        raise ValueError("power artifact selected support drifted from the spec")
    if artifact["selected_support"] is None:
        raise ValueError("Branch B is active: no selected support exists")
    return artifact


def build_recoverability_manifest(power_artifact_path: str, *,
                                  frame_sha256s, eligibility_evidence_sha256s):
    _load_verified_power_artifact(power_artifact_path)
    return RecoverabilityManifest(
        schema_version=spec.SCHEMA_VERSION,
        power_artifact_path=spec.POWER_ARTIFACT_PATH,
        power_artifact_sha256=spec.POWER_ARTIFACT_SHA256,
        frame_sha256s=tuple(frame_sha256s),
        eligibility_evidence_sha256s=tuple(eligibility_evidence_sha256s),
        plant_r_grid=PLANT_R_GRID,
        seeds=RECOVERABILITY_SEEDS,
        marker_seeds=MARKER_SEEDS,
        branch_b_text=spec.BRANCH_B_TEXT,
    )


def _resolve_power_artifact_path(manifest: RecoverabilityManifest) -> str:
    if os.path.isfile(manifest.power_artifact_path):
        return manifest.power_artifact_path
    # __file__ = <repo>/src/critaudit/experiments/causal_probe_recoverability.py
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(repo_root, manifest.power_artifact_path)


def _validate_manifest(manifest):
    if type(manifest) is not RecoverabilityManifest:
        raise ValueError("gate requires a RecoverabilityManifest")
    if manifest.schema_version != spec.SCHEMA_VERSION:
        raise ValueError("manifest schema version drifted (fail-closed)")
    if manifest.plant_r_grid != PLANT_R_GRID:
        raise ValueError("manifest plant grid drifted from PLANT_R_GRID")
    if manifest.seeds != RECOVERABILITY_SEEDS:
        raise ValueError("manifest seeds drifted from RECOVERABILITY_SEEDS")
    if manifest.marker_seeds != MARKER_SEEDS:
        raise ValueError(
            "manifest marker seeds have the wrong order or count (fail-closed)")
    if manifest.branch_b_text != spec.BRANCH_B_TEXT:
        raise ValueError("manifest Branch-B text is not the frozen text")
    if manifest.power_artifact_sha256 != spec.POWER_ARTIFACT_SHA256:
        raise ValueError("manifest power artifact sha256 drifted (fail-closed)")
    for field in ("frame_sha256s", "eligibility_evidence_sha256s"):
        values = getattr(manifest, field)
        if len(values) != 1 or not all(
            isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value)
            for value in values
        ):
            raise ValueError(
                f"manifest {field} must carry exactly one lowercase sha256 hex "
                f"digest (fail-closed)")
    require_disjoint_seed_sets(manifest.seeds, manifest.marker_seeds)


def _canonical_manifest_bytes(manifest) -> bytes:
    payload = asdict(manifest)
    for key in ("frame_sha256s", "eligibility_evidence_sha256s",
                "plant_r_grid", "seeds", "marker_seeds"):
        payload[key] = list(payload[key])
    return (json.dumps(payload, allow_nan=False, ensure_ascii=False,
                       separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def load_recoverability_manifest(path: str) -> RecoverabilityManifest:
    """Load and fail-closed-validate a banked dry-run manifest file."""
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        payload = json.loads(data)
    except ValueError as exc:
        raise ValueError(f"manifest file is not valid JSON: {exc}")
    try:
        manifest = RecoverabilityManifest(
            schema_version=payload["schema_version"],
            power_artifact_path=payload["power_artifact_path"],
            power_artifact_sha256=payload["power_artifact_sha256"],
            frame_sha256s=tuple(payload["frame_sha256s"]),
            eligibility_evidence_sha256s=tuple(
                payload["eligibility_evidence_sha256s"]),
            plant_r_grid=tuple(payload["plant_r_grid"]),
            seeds=tuple(payload["seeds"]),
            marker_seeds=tuple(payload["marker_seeds"]),
            branch_b_text=payload["branch_b_text"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"manifest file has a drifted schema: {exc}")
    if _canonical_manifest_bytes(manifest) != data:
        raise ValueError("manifest file bytes are not canonical (fail-closed)")
    _validate_manifest(manifest)
    return manifest


def _verify_run_manifest(run, frame, cell_index, position, seen_run_ids):
    """Per-run ProbeManifest verification (review F2): relabeled, reordered, or
    ledger-inconsistent run manifests fail closed."""
    probe_manifest = run.manifest
    if type(probe_manifest) is not ProbeManifest:
        raise ValueError("run manifest must be a ProbeManifest (fail-closed)")
    if probe_manifest.run_id in seen_run_ids:
        raise ValueError("run IDs must be unique across the grid (fail-closed)")
    seen_run_ids.add(probe_manifest.run_id)
    if probe_manifest.seed_stream_id != CONTROL_SEED_STREAM:
        raise ValueError(
            "run manifest is relabeled onto a foreign seed stream (fail-closed)")
    expected_seed = derive_cell_seed(RECOVERABILITY_SEEDS[position], cell_index)
    if probe_manifest.raw_seed != expected_seed:
        raise ValueError(
            f"run manifest raw seed {probe_manifest.raw_seed} does not equal "
            f"the registered derivation for seed position {position}, cell "
            f"{cell_index} (fail-closed)")
    if probe_manifest.frame_id != frame.frame_id:
        raise ValueError("run manifest frame ID drifted (fail-closed)")
    if probe_manifest.root_ids != tuple(
        parent.parent_item_id for parent in frame.parent_records
    ):
        raise ValueError("run manifest root registry drifted (fail-closed)")
    if probe_manifest.pair_ids != tuple(
        pair.pair_id for pair in frame.candidate_pairs
    ):
        raise ValueError("run manifest pair registry drifted (fail-closed)")
    if probe_manifest.assignment_ids != tuple(
        assignment.assignment_id for assignment in run.assignments
    ):
        raise ValueError(
            "run manifest assignments do not match the run's ledger (fail-closed)")
    children = {
        outcome.direct_child_item_id for outcome in run.outcomes
        if outcome.direct_child_item_id is not None
    }
    if not children <= set(probe_manifest.event_ids):
        raise ValueError(
            "run outcomes name children outside the manifest event registry "
            "(fail-closed)")


def _verify_cell_results(cell_results, manifest):
    """Re-verify EVERY structural claim from primary evidence (review F2): the
    complete per-run ledgers, byte-hash chains, deserialized-and-validated
    eligibility evidence, per-run manifests against the registered seed
    derivation, and estimate reproduction. A summary without evidence, or
    forged evidence, raises — it can never PASS."""
    results = tuple(cell_results)
    if len(results) != len(PLANT_R_GRID):
        raise ValueError("gate requires exactly one cell result per registered plant")
    frame_sha = manifest.frame_sha256s[0]
    evidence_sha = manifest.eligibility_evidence_sha256s[0]
    frame = None
    frame_bytes = None
    evidence_bytes = None
    seen_run_ids = set()
    reply_manifests = []
    means = []
    for cell_index, (cell, plant_r) in enumerate(zip(results, PLANT_R_GRID)):
        if cell.get("plant_r") != plant_r:
            raise ValueError("cell results are out of registered grid order")
        runs = tuple(cell.get("runs", ()))
        estimates = tuple(cell.get("estimates", ()))
        if len(runs) != len(RECOVERABILITY_SEEDS) or len(estimates) != len(runs):
            raise ValueError(
                "every cell needs one complete run and estimate per registered "
                "recoverability seed (fail-closed)")
        for position, run in enumerate(runs):
            if type(run) is not ScriptedControlRun:
                raise ValueError(
                    "cell results must carry complete ScriptedControlRun "
                    "evidence (fail-closed)")
            if hashlib.sha256(run.frame_bytes).hexdigest() != run.frame_sha256:
                raise ValueError("run frame bytes do not hash to their claimed "
                                 "sha256 (fail-closed)")
            if run.frame_sha256 != frame_sha:
                raise ValueError(
                    "run frame hash does not equal the banked manifest frame "
                    "hash (fail-closed)")
            if hashlib.sha256(run.eligibility_evidence_bytes).hexdigest() != (
                run.eligibility_evidence_sha256
            ):
                raise ValueError("run evidence bytes do not hash to their "
                                 "claimed sha256 (fail-closed)")
            if run.eligibility_evidence_sha256 != evidence_sha:
                raise ValueError(
                    "run evidence hash does not equal the banked manifest "
                    "evidence hash (fail-closed)")
            if frame is None:
                frame_bytes = run.frame_bytes
                frame = sampling_frame_from_bytes(frame_bytes)
                validate_sampling_frame(frame)
                if sampling_frame_sha256(frame) != frame_sha:
                    raise ValueError(
                        "reconstructed frame does not hash to the manifest "
                        "frame hash (fail-closed)")
                evidence_bytes = run.eligibility_evidence_bytes
                evidence = frame_eligibility_evidence_from_bytes(evidence_bytes)
                validate_frame_provenance(frame, evidence)
            else:
                if run.frame_bytes != frame_bytes:
                    raise ValueError("runs carry non-identical frame bytes "
                                     "(fail-closed)")
                if run.eligibility_evidence_bytes != evidence_bytes:
                    raise ValueError(
                        "runs carry non-identical evidence bytes (fail-closed)")
            _verify_run_manifest(run, frame, cell_index, position, seen_run_ids)
            reply_manifests.append(run.manifest)
            estimate = estimate_r_reply(
                frame, run.draws, run.assignments, run.outcomes)
            if estimate.estimate != estimates[position]:
                raise ValueError(
                    "reported estimate does not reproduce from the run's "
                    "complete ledgers (fail-closed)")
        mean = math.fsum(estimates) / len(estimates)
        if not math.isclose(mean, cell.get("mean_r_reply"), rel_tol=1e-9,
                            abs_tol=1e-12):
            raise ValueError("cell mean does not reproduce from its estimates")
        means.append(mean)
    return results, means, tuple(reply_manifests)


def _verify_marker_cells(marker_cells, chi_peak):
    cells = tuple(marker_cells)
    if len(cells) != len(PLANT_R_GRID):
        raise ValueError("gate requires exactly six aggregated marker cells")
    supports = set()
    marker_manifests = []
    for cell, plant_r in zip(cells, PLANT_R_GRID):
        if type(cell) is not MarkerGridCell:
            raise ValueError("marker cells must be MarkerGridCell records")
        rebuilt = aggregate_marker_cell(plant_r, cell.seed_results)
        if rebuilt != cell:
            raise ValueError(
                "marker cell does not reproduce from its own seed results "
                "(fail-closed)")
        for result in cell.seed_results:
            supports.add(result.manifest.support_per_root)
            marker_manifests.append(result.manifest)
    if len(supports) != 1:
        raise ValueError("marker cohort support is not equal across seeds/cells")
    if locate_chi_peak(cells) != chi_peak:
        raise ValueError(
            "chi peak does not reproduce from the marker cells (fail-closed)")
    return cells, tuple(marker_manifests)


def evaluate_recoverability_gate(cell_results, marker_cells, chi_peak, manifest):
    """Frozen PASS/FAIL clauses; scientific failures return FAIL, structural
    violations RAISE. Every structural claim is re-verified here from primary
    evidence — complete run ledgers, byte-hash chains against the banked
    manifest, marker re-aggregation, peak re-location, AND the full
    reply×marker manifest-disjointness firewall — so neither forged nor
    missing evidence (including cross-cohort identifier collisions) can reach a
    PASS (or launder a FAIL). The returned `structural_failures` is therefore 0
    by construction whenever the gate returns at all. No clause or threshold
    changes after execution begins."""
    _validate_manifest(manifest)
    results, means, reply_manifests = _verify_cell_results(cell_results, manifest)
    _marker_cells, marker_manifests = _verify_marker_cells(marker_cells, chi_peak)

    # independence firewall (review round 3, F2): the gate itself must reject
    # any cross-cohort identifier collision — the execution driver's check is
    # not part of the advertised pure gate. Every reply run manifest is checked
    # for disjointness against every marker manifest across all fields.
    for reply_manifest in reply_manifests:
        for marker_manifest in marker_manifests:
            require_disjoint_manifests(reply_manifest, marker_manifest)

    monotonicity_passed = all(a < b for a, b in zip(means, means[1:]))

    crossings = [
        index for index, (a, b) in enumerate(zip(means, means[1:]))
        if (a < 1.0 <= b) or (a >= 1.0 > b)
    ]
    crossing_resolved = len(crossings) == 1
    crossing_interval = (
        [PLANT_R_GRID[crossings[0]], PLANT_R_GRID[crossings[0] + 1]]
        if crossing_resolved else None)

    near_errors = {}
    near_passed = True
    for plant_r, mean in zip(PLANT_R_GRID, means):
        if plant_r in (0.97, 1.03):
            error = abs(mean - plant_r)
            near_errors[str(plant_r)] = error
            near_passed = near_passed and error <= spec.NEAR_CRITICAL_ABS_TOL

    artifact = _load_verified_power_artifact(
        _resolve_power_artifact_path(manifest))
    selected = artifact["selected_support"]
    candidate = next(
        c for c in artifact["candidates"]
        if c["parent_count"] == selected["parent_count"]
        and c["recipients_per_parent"] == selected["recipients_per_parent"])
    ci_coverage_passed = all(
        cell["coverage"] >= TARGET_COVERAGE for cell in candidate["cells"])
    ci_precision_passed = (
        candidate["power"] >= TARGET_POWER
        and all(cell["mean_full_ci_width"] <= MAX_MEAN_CI_FULL_WIDTH
                for cell in candidate["cells"])
        and all(cell["coverage_wilson_half_width"] <= MC_MAX_HALF_WIDTH
                for cell in candidate["cells"]))

    chi_resp_coincidence_passed = bool(
        crossing_interval is not None
        and chi_peak.neighbor_low <= crossing_interval[0]
        and crossing_interval[1] <= chi_peak.neighbor_high)

    # 0 by construction: every structural claim was re-verified above and any
    # problem raised instead of returning (see the docstring).
    structural_failures = 0

    passed = bool(
        monotonicity_passed and crossing_resolved and near_passed
        and ci_coverage_passed and ci_precision_passed
        and chi_resp_coincidence_passed and structural_failures == 0)
    return {
        "monotonicity_passed": monotonicity_passed,
        "crossing_resolved": crossing_resolved,
        "crossing_interval": crossing_interval,
        "near_critical_abs_error": near_errors,
        "near_critical_passed": near_passed,
        "ci_precision_passed": ci_precision_passed,
        "ci_coverage_passed": ci_coverage_passed,
        "chi_resp_coincidence_passed": chi_resp_coincidence_passed,
        "structural_failures": structural_failures,
        "mean_r_reply": means,
        "chi_peak": asdict(chi_peak),
        "passed": passed,
        "status": (spec.STATUS_RECOVERABILITY_PASSED if passed
                   else spec.STATUS_RECOVERABILITY_FAILED),
    }


def write_recoverability_artifact(path: str, artifact) -> None:
    write_canonical_json(path, artifact)


# --- pre-draw OASIS setups (dry run) ----------------------------------------------------------


async def _predraw_reply_setup(frame, database_path):
    """Mirror of the scripted-control bridge THROUGH ROOT CREATION ONLY: sign-ups,
    parents/fillers/background posts, one clock step, canonical eligibility
    evidence — then teardown before any controller, selection, treatment, action,
    or outcome. If this mirror ever drifts from the bridge, --execute fails closed
    on the evidence hash comparison."""
    from oasis import ActionType, AgentGraph, SocialAgent, make
    from critaudit.sim.harness.causal_channel import LowLatencyChannel
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType

    from critaudit.sim.harness import harness_spec as hs
    from critaudit.sim.harness.causal_probe_validation import (
        validate_frame_provenance,
    )
    from critaudit.sim.harness.oasis_adapter import (
        NEWS_AGENT_NAME,
        _make_news_sentinel_model,
        _new_user_info,
        load_frame_eligibility_evidence,
        read_trace_rows,
    )

    parent_count = len(frame.parent_records)
    recipients = sorted({pair.agent_id for pair in frame.candidate_pairs})
    # Registered convention: the exclusion registry's last two entries are the
    # filler/organic author and the dedicated news user.
    filler_author, news_user = frame.excluded_recipient_agent_ids[-2:]

    sentinel = _make_news_sentinel_model(
        model_id="dryrun-sentinel", endpoint_url="http://sentinel.invalid/v1",
        token="dryrun", max_tokens=64, temperature=0.0, timeout=5,
        context_budget=1024)

    platform = Platform(
        db_path=database_path,
        channel=LowLatencyChannel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=3,
        max_rec_post_len=5,
        following_post_count=hs.FOLLOWING_POST_COUNT,
    )
    graph = AgentGraph()
    available = [ActionType(name) for name in
                 ("create_post", "create_comment", "repost", "quote_post",
                  "do_nothing")]
    agent_names = {}
    for i in range(parent_count):
        agent_names[i] = f"control_author_{i}"
    for agent_id in recipients:
        agent_names[agent_id] = f"control_recipient_{agent_id}"
    agent_names[filler_author] = "control_organic"
    agent_names[news_user] = NEWS_AGENT_NAME
    for agent_id in sorted(agent_names):
        graph.add_agent(SocialAgent(
            agent_id=agent_id,
            user_info=_new_user_info(name=agent_names[agent_id],
                                     bio="control fixture",
                                     user_profile="control fixture"),
            model=sentinel, available_actions=available))

    env = make(agent_graph=graph, platform=platform, database_path=database_path)
    await env.reset()
    try:
        creations = []
        for i, parent in enumerate(frame.parent_records):
            creations.append((parent.author_agent_id, f"control parent {i + 1}"))
        for i in range(parent_count):
            creations.append((filler_author, f"control filler {i + 1}"))
        creations.append((filler_author, "control background one"))
        creations.append((filler_author, "control background two"))
        for expected_id, (agent_id, content) in enumerate(creations, start=1):
            result = await graph.get_agent(agent_id).env.action.create_post(content)
            if not (result.get("success") is True
                    and result.get("post_id") == expected_id):
                raise RuntimeError(
                    f"dry-run creation drifted: expected post {expected_id}, "
                    f"got {result!r}")
        await env.step({})
        evidence = load_frame_eligibility_evidence(
            frame, database_path, read_trace_rows(database_path))
        validate_frame_provenance(frame, evidence)
    finally:
        await env.close()
    return frame_eligibility_evidence_sha256(evidence)


async def _predraw_marker_setup(database_path, root_count):
    """Marker pre-draw setup through root creation only: burn the disjoint-round
    offset, plant the roots, verify their ids, tear down before any cascade."""
    from oasis import ActionType, AgentGraph, SocialAgent, make
    from critaudit.sim.harness.causal_channel import LowLatencyChannel
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType

    from critaudit.sim.harness import harness_spec as hs
    from critaudit.sim.harness.oasis_adapter import (
        _make_news_sentinel_model,
        _new_user_info,
    )

    sentinel = _make_news_sentinel_model(
        model_id="dryrun-sentinel", endpoint_url="http://sentinel.invalid/v1",
        token="dryrun", max_tokens=64, temperature=0.0, timeout=5,
        context_budget=1024)
    platform = Platform(
        db_path=database_path,
        channel=LowLatencyChannel(),
        recsys_type=RecsysType(hs.RECSYS_TYPE),
        refresh_rec_post_count=3,
        max_rec_post_len=5,
        following_post_count=hs.FOLLOWING_POST_COUNT,
    )
    graph = AgentGraph()
    available = [ActionType(name) for name in
                 ("create_post", "create_comment", "repost", "quote_post",
                  "do_nothing")]
    names = {0: "marker_root_author"}
    for slot in range(MARKER_OPPORTUNITIES_PER_PARENT):
        names[1 + slot] = f"marker_recipient_{slot}"
    for agent_id in sorted(names):
        graph.add_agent(SocialAgent(
            agent_id=agent_id,
            user_info=_new_user_info(name=names[agent_id], bio="marker fixture",
                                     user_profile="marker fixture"),
            model=sentinel, available_actions=available))
    env = make(agent_graph=graph, platform=platform, database_path=database_path)
    await env.reset()
    try:
        for _ in range(MARKER_ROUND_OFFSET):
            await env.step({})
        for k in range(root_count):
            result = await graph.get_agent(0).env.action.create_post(
                f"marker root {k + 1}")
            if not (result.get("success") is True
                    and result.get("post_id") == k + 1):
                raise RuntimeError(f"marker dry-run root drifted: {result!r}")
    finally:
        await env.close()


def run_dry_run(power_artifact_path: str, work_dir: str, *, support=None):
    """Hash preflight with NO draw, action, cascade, or outcome, and no result
    artifact. Prints the canonical manifest JSON and returns it."""
    import asyncio

    os.makedirs(work_dir, exist_ok=True)
    _load_verified_power_artifact(power_artifact_path)
    if support is None:
        support = spec.SELECTED_SUPPORT
    frame = build_power_frame(
        support["parent_count"], support["recipients_per_parent"])
    frame_sha = sampling_frame_sha256(frame)

    reply_db = os.path.join(work_dir, "reply_predraw.db")
    evidence_sha = asyncio.run(_predraw_reply_setup(frame, reply_db))

    marker_db = os.path.join(work_dir, "marker_predraw.db")
    asyncio.run(_predraw_marker_setup(marker_db, MARKER_ROOT_COUNT))

    manifest = build_recoverability_manifest(
        power_artifact_path,
        frame_sha256s=(frame_sha,),
        eligibility_evidence_sha256s=(evidence_sha,),
    )
    manifest_bytes = _canonical_manifest_bytes(manifest)
    manifest_path = os.path.join(work_dir, "dryrun_manifest.json")
    with open(manifest_path, "wb") as handle:
        handle.write(manifest_bytes)
    manifest_json = asdict(manifest)
    for key in ("frame_sha256s", "eligibility_evidence_sha256s",
                "plant_r_grid", "seeds", "marker_seeds"):
        manifest_json[key] = list(manifest_json[key])
    report = {
        "execute": False,
        # precise claim (review): provider INFERENCE is uninvoked and
        # fail-closed — the sentinel wrapper is constructed but raises on any
        # model call; no network inference path is exercised.
        "provider_inference_invoked": False,
        "provider_inference_fail_closed": True,
        "support": dict(support),
        "manifest": manifest_json,
        "manifest_path": manifest_path,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    print(json.dumps(report, allow_nan=False, ensure_ascii=False,
                     separators=(",", ":"), sort_keys=True))
    return report


# --- the guarded execute path (dormant until Task-8 owner authorization) -----------------------


def run_execute(power_artifact_path: str, output_path: str, manifest_path: str,
                work_dir=None):
    """The registered $0 scripted recoverability grid. DORMANT: running this
    requires the separate Task-8 owner authorization. Uses only the scripted
    full-platform control and the disjoint marker control; the sentinel model
    raises on any LLM invocation.

    Banked-hash enforcement (review F1): the caller must supply the banked
    dry-run manifest; the frozen frame hash is checked against it up front, a
    dedicated pre-draw verification session must recreate the banked
    eligibility-evidence hash BEFORE any draw anywhere, and every live session
    additionally enforces the same evidence hash pre-draw inside the bridge."""
    import asyncio

    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix="causal_probe_recoverability_")
    os.makedirs(work_dir, exist_ok=True)
    manifest = load_recoverability_manifest(manifest_path)
    _load_verified_power_artifact(power_artifact_path)
    support = spec.SELECTED_SUPPORT
    frame = build_power_frame(
        support["parent_count"], support["recipients_per_parent"])
    frame_sha = sampling_frame_sha256(frame)
    if frame_sha != manifest.frame_sha256s[0]:
        raise ValueError(
            "frozen frame does not recreate the banked manifest frame hash "
            "(fail-closed)")
    banked_evidence_sha = manifest.eligibility_evidence_sha256s[0]

    # pre-draw verification session: recreate the banked evidence hash BEFORE
    # any draw in any session, then tear down.
    verification_db = os.path.join(work_dir, "predraw_verification.db")
    verification_sha = asyncio.run(_predraw_reply_setup(frame, verification_db))
    if verification_sha != banked_evidence_sha:
        raise ValueError(
            "pre-draw setup does not recreate the banked eligibility-evidence "
            "hash — failing closed before the first draw")

    reply_cells = []
    cell_results = []
    reply_manifests = []
    for cell_index, plant_r in enumerate(PLANT_R_GRID):
        estimates = []
        runs = []
        run_records = []
        for seed in RECOVERABILITY_SEEDS:
            # registered independence derivation (review F4): schedules and
            # selection/treatment streams are independent ACROSS CELLS, matching
            # the banked power simulator's joint law — a raw registered seed is
            # never reused across plants.
            derived_seed = derive_cell_seed(seed, cell_index)
            truth = build_power_schedule(frame, plant_r, derived_seed)
            database_path = os.path.join(
                work_dir, f"reply_{plant_r}_{seed}.db")
            run = run_scripted_oasis_control(
                frame, truth,
                run_id=f"run:recoverability:{plant_r}:{seed}",
                seed_stream_id=CONTROL_SEED_STREAM,
                seed=derived_seed,
                database_path=database_path,
                expected_evidence_sha256=banked_evidence_sha,
            )
            if run.frame_sha256 != frame_sha:
                raise ValueError(
                    "executed frame hash is not byte-identical to the banked "
                    "frame (fail-closed)")
            estimate = estimate_r_reply(
                frame, run.draws, run.assignments, run.outcomes)
            estimates.append(estimate.estimate)
            reply_manifests.append(run.manifest)
            runs.append(run)
            # generator truth for the future finding lock (review F5): R_plant,
            # the hidden R_gen_frame, and the fixed potential-response schedule
            # (by canonical hash) ride in the ARTIFACT only — the gate never
            # consumes them.
            schedule_bytes = (json.dumps(
                [[row.pair_id, row.potential_response]
                 for row in truth.potential_responses],
                allow_nan=False, ensure_ascii=False, separators=(",", ":"))
                + "\n").encode("utf-8")
            run_records.append({
                "manifest": asdict(run.manifest),
                "frame_sha256": run.frame_sha256,
                "eligibility_evidence_sha256": run.eligibility_evidence_sha256,
                "draws": [asdict(d) for d in run.draws],
                "assignments": [asdict(a) for a in run.assignments],
                "outcomes": [asdict(o) for o in run.outcomes],
                "estimate": asdict(estimate),
                "registered_seed": int(seed),
                "derived_seed": int(derived_seed),
                "schedule_seed": int(derived_seed),
                "r_plant": truth.r_plant,
                "r_gen_frame": truth.r_gen_frame,
                "potential_responses_sha256": hashlib.sha256(
                    schedule_bytes).hexdigest(),
            })
        cell_results.append({
            "plant_r": plant_r,
            "mean_r_reply": math.fsum(estimates) / len(estimates),
            "estimates": tuple(estimates),
            "runs": tuple(runs),
        })
        reply_cells.append({
            "plant_r": plant_r,
            "r_gen_frames": [record["r_gen_frame"] for record in run_records],
            "runs": run_records,
        })

    marker_cells = []
    for plant_r in PLANT_R_GRID:
        seed_results = tuple(
            run_recursive_marker_control(
                root_count=MARKER_ROOT_COUNT,
                opportunities_per_parent=MARKER_OPPORTUNITIES_PER_PARENT,
                plant_r=plant_r,
                rounds=MARKER_ROUNDS,
                run_id=f"run:marker:{plant_r}:{seed}",
                frame_id=f"frame:marker:{plant_r}",
                seed_stream_id=MARKER_SEED_STREAM,
                seed=seed,
                database_path=os.path.join(
                    work_dir, f"marker_{plant_r}_{seed}.db"),
            )
            for seed in MARKER_SEEDS
        )
        for result in seed_results:
            for reply_manifest in reply_manifests:
                require_disjoint_manifests(reply_manifest, result.manifest)
        marker_cells.append(aggregate_marker_cell(plant_r, seed_results))
    chi_peak = locate_chi_peak(tuple(marker_cells))

    gate = evaluate_recoverability_gate(
        tuple(cell_results), tuple(marker_cells), chi_peak, manifest)

    manifest_json = asdict(manifest)
    for key in ("frame_sha256s", "eligibility_evidence_sha256s",
                "plant_r_grid", "seeds", "marker_seeds"):
        manifest_json[key] = list(manifest_json[key])
    artifact = {
        "schema_version": spec.SCHEMA_VERSION,
        "manifest": manifest_json,
        "manifest_sha256": hashlib.sha256(
            _canonical_manifest_bytes(manifest)).hexdigest(),
        "reply_cells": reply_cells,
        "cell_results": [
            {
                "plant_r": cell["plant_r"],
                "mean_r_reply": cell["mean_r_reply"],
                "estimates": list(cell["estimates"]),
            }
            for cell in cell_results
        ],
        "marker_cells": [asdict(cell) for cell in marker_cells],
        "chi_peak": asdict(chi_peak),
        "gate": gate,
    }
    write_recoverability_artifact(output_path, artifact)
    return artifact


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Guarded causal-probe recoverability runner (dormant)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="hash preflight; no draw, no result artifact")
    mode.add_argument("--execute", action="store_true",
                      help="REQUIRES Task-8 owner authorization")
    parser.add_argument("--power-artifact", required=True)
    parser.add_argument("--output", default=None,
                        help="result artifact path (execute only)")
    parser.add_argument("--manifest", default=None,
                        help="banked dry-run manifest path (execute only)")
    parser.add_argument("--work-dir", default=None)
    arguments = parser.parse_args(argv)

    if arguments.dry_run:
        work_dir = arguments.work_dir or tempfile.mkdtemp(
            prefix="causal_probe_dryrun_")
        run_dry_run(arguments.power_artifact, work_dir)
        return 0
    if not arguments.output:
        parser.error("--execute requires --output")
    if not arguments.manifest:
        parser.error("--execute requires --manifest (the banked dry-run manifest)")
    run_execute(arguments.power_artifact, arguments.output, arguments.manifest,
                work_dir=arguments.work_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Sub-inc-2 driver — matched parrot null (design 2026-07-17, contract repair v2).

Part 1 calibrates definition #2's finite (window, theta) rule against true cascade membership.
Only a Gate-D-passing banked rule may flow into the registered matched-null band.

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

from critaudit.cascades.calibrate import adjusted_rand
from critaudit.cascades.extract import roots_from_parents
from critaudit.cascades.similarity import (
    attribute_similarity_parents, calibrate_similarity_rule_pooled)
from critaudit.sim.controls import llm_parrot_spec as lps
from critaudit.sim.harness.cohort_marginals import extract_marginals, round_indices
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
    """Round index per event — the SHARED round_indices rule (one validation home with
    extract_marginals; the two copies had already diverged once, review 2026-07-17)."""
    return round_indices(run.times)


def load_cohort_windows(archive_dir=DEFAULT_ARCHIVE):
    """Export the three registered windows (WINDOW_ORDER) through the corrected authored-content
    exporter. Returns {seed: (run, marginals)} — the run feeds ONLY calibration (true edges) and
    marginal extraction; the generator sees marginals (+ pool embeddings) alone."""
    out = {}
    for seed in lps.WINDOW_ORDER:
        run = export_harness_run(_window_db(archive_dir, seed), timestamp_col=_TIMESTAMP_COL)
        out[seed] = (run, extract_marginals(run))
    return out


def run_similarity_calibration(archive_dir=DEFAULT_ARCHIVE, out_path=None):
    """Calibrate finite window and theta by equal-window mean cascade-membership ARI."""
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
        }

    res = calibrate_similarity_rule_pooled(streams)
    for seed, stream in zip(lps.WINDOW_ORDER, streams):
        parent_true, rounds, E = stream
        _, recovered_root = attribute_similarity_parents(
            rounds, E, res.theta, window=res.window)
        true_root = roots_from_parents(parent_true)
        per_window[str(seed)]["ari_at_rule"] = float(
            adjusted_rand(recovered_root, true_root))

    record = {
        "artifact": "similarity_calibration",
        "construction_version": lps.CALIBRATION_CONSTRUCTION_VERSION,
        "design": lps.DESIGN_DOC,
        "design_sha256": lps.DESIGN_DOC_SHA256,
        "amendment": lps.CALIBRATION_AMENDMENT,
        "spec": {
            "embed_model_id": lps.EMBED_MODEL_ID,
            "embed_revision": lps.EMBED_REVISION,
            "cosine_decimals": lps.COSINE_DECIMALS,
            "theta_grid": [lps.THETA_GRID_START, lps.THETA_GRID_STOP, lps.THETA_GRID_STEP],
            "criterion": lps.THETA_CRITERION,
            "tie_rule": lps.THETA_TIE_RULE,
            "candidate_rule": lps.CANDIDATE_RULE,
            "window_grid": list(lps.WINDOW_GRID),
            "recovery_threshold": lps.RECOVERY_THRESHOLD,
            "window_order": list(lps.WINDOW_ORDER),
        },
        "status": res.status,
        "window": res.window,
        "theta": res.theta,
        "mean_ari": res.mean_ari,
        "per_stream_ari": list(res.per_stream_ari),
        "recovery_surface": [
            [window, theta, mean_ari, list(per_stream)]
            for window, theta, mean_ari, per_stream in res.recovery_surface
        ],
        "per_window": per_window,
    }
    if out_path is not None:
        _dump_banked_json(record, out_path)
    return record


# Compatibility spelling for callers of the original sub-inc-2 driver. The returned artifact is
# construction-v2 finite-window membership calibration, not the superseded theta-only procedure.
run_theta_calibration = run_similarity_calibration


def _dump_banked_json(record, out_path):
    """Deterministic banked-artifact serialization: sorted keys, no wall-clock anywhere —
    byte-identical on re-run (the @slow reproduction anchor). allow_nan=False fails loudly if a
    NaN diagnostic ever reaches a banked artifact (RFC-8259-invalid `NaN` tokens must never enter
    the committed record silently)."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(record, f, sort_keys=True, indent=1, allow_nan=False)
        f.write("\n")


# Part 2 (T7): a registered band is permitted only from a status-passed construction-v2 banked
# rule. The legacy 64-seed file remains descriptive and byte-preserved because v2 failed Gate D.
#
# SINGLE SOURCE of the banked-artifact locations (the reproduction tests and the firewall's
# schema guard import these — four independent spellings was a drift channel, review 2026-07-17).
# The repo-root walk assumes the src-layout EDITABLE install that is this project's registered
# substrate (~/oasis_venv); under a non-editable install the results/ tree is not packaged at all
# and banked_similarity_rule() fails loudly with the path in the message.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
BANKED_DIR = os.path.join(_REPO_ROOT, "results", "s2_llm_parrot_null")
BANKED_CALIBRATION_JSON = os.path.join(BANKED_DIR, "2026-07-17_theta_calibration.json")
BANKED_THETA_JSON = BANKED_CALIBRATION_JSON  # compatibility alias; schema validation is v2
BANKED_BAND_JSON = os.path.join(BANKED_DIR, "2026-07-17_nstruct_band.json")


def banked_similarity_rule(path=BANKED_CALIBRATION_JSON):
    """Return a certified ``(window, theta)`` pair or reject the banked artifact fail-closed."""
    with open(path) as f:
        rec = json.load(f)
    expected_spec = {
        "criterion": lps.THETA_CRITERION,
        "tie_rule": lps.THETA_TIE_RULE,
        "candidate_rule": lps.CANDIDATE_RULE,
        "theta_grid": [lps.THETA_GRID_START, lps.THETA_GRID_STOP, lps.THETA_GRID_STEP],
        "window_grid": list(lps.WINDOW_GRID),
        "recovery_threshold": lps.RECOVERY_THRESHOLD,
        "window_order": list(lps.WINDOW_ORDER),
    }
    if rec.get("artifact") != "similarity_calibration":
        raise ValueError("banked calibration artifact identity mismatch")
    if rec.get("construction_version") != lps.CALIBRATION_CONSTRUCTION_VERSION:
        raise ValueError("banked calibration construction version mismatch")
    if (rec.get("design") != lps.DESIGN_DOC
            or rec.get("design_sha256") != lps.DESIGN_DOC_SHA256
            or rec.get("amendment") != lps.CALIBRATION_AMENDMENT):
        raise ValueError("banked calibration design identity mismatch")
    got_spec = rec.get("spec")
    if not isinstance(got_spec, dict) or any(
            got_spec.get(key) != value for key, value in expected_spec.items()):
        raise ValueError("banked calibration spec mismatch")
    try:
        rows = rec["recovery_surface"]
        expected_theta = tuple(float(v) for v in np.round(np.arange(
            lps.THETA_GRID_START,
            lps.THETA_GRID_STOP + lps.THETA_GRID_STEP / 2,
            lps.THETA_GRID_STEP), 6))
        expected_pairs = {(window, theta) for window in lps.WINDOW_GRID
                          for theta in expected_theta}
        parsed = {}
        for row in rows:
            if not isinstance(row, list) or len(row) != 4:
                raise ValueError("malformed row")
            row_window, row_theta, row_mean, per_stream = row
            pair = (int(row_window), float(row_theta))
            if pair in parsed or pair not in expected_pairs:
                raise ValueError("duplicate or unregistered grid pair")
            per_stream = tuple(float(v) for v in per_stream)
            if (len(per_stream) != len(lps.WINDOW_ORDER)
                    or not np.isfinite(per_stream).all()
                    or not all(-1.0 <= v <= 1.0 for v in per_stream)):
                raise ValueError("bad per-stream ARI")
            row_mean = float(row_mean)
            if not np.isfinite(row_mean) or not np.isclose(
                    row_mean, np.mean(per_stream), rtol=0.0, atol=1e-12):
                raise ValueError("surface mean does not match per-stream ARIs")
            parsed[pair] = (row_mean, per_stream)
        if set(parsed) != expected_pairs:
            raise ValueError("surface does not cover the registered grid")
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"banked calibration recovery surface malformed: {e}") from e

    best_pair, (best_mean, best_per_stream) = max(
        parsed.items(), key=lambda item: (item[1][0], -item[0][0], item[0][1]))
    derived_status = "passed" if best_mean >= lps.RECOVERY_THRESHOLD else "failed"
    try:
        window = int(rec["window"])
        theta = float(rec["theta"])
        mean_ari = float(rec["mean_ari"])
        per_stream_ari = tuple(float(v) for v in rec["per_stream_ari"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError("banked calibration selected rule malformed") from e
    if ((window, theta) != best_pair
            or not np.isclose(mean_ari, best_mean, rtol=0.0, atol=1e-12)
            or per_stream_ari != best_per_stream
            or rec.get("status") != derived_status):
        raise ValueError("banked calibration selected rule/status does not match its surface")
    if derived_status != "passed":
        raise RuntimeError(
            f"banked calibration status {derived_status}; definition #2 is blocked")

    if window not in lps.WINDOW_GRID:
        raise ValueError(f"banked window {window!r} outside the registered grid")
    if not np.isfinite(theta) or not (0.0 < theta <= 1.0):
        raise ValueError(f"banked theta {theta} outside (0,1] — malformed artifact")
    if not np.isfinite(mean_ari) or mean_ari < lps.RECOVERY_THRESHOLD:
        raise ValueError("banked passed calibration does not clear the recovery threshold")
    return int(window), theta


def banked_theta(path=BANKED_CALIBRATION_JSON):
    """Compatibility accessor; status and the complete v2 contract are still enforced."""
    return banked_similarity_rule(path)[1]


def run_matched_null_band(archive_dir=DEFAULT_ARCHIVE, *, theta=None, window=None, out_path=None,
                          n_seeds=None, base_seed=None, windows=None):
    """The matched null's own n_struct distribution (design §7): n_seeds null streams, seeds
    base_seed+i, window assignment round-robin i mod len(window_order) (WINDOW_ORDER for the
    registered cohort). Per seed: generate -> fail-closed gate (ONE failure aborts the band — no
    silently partial band) -> n_struct via post_reply_tree. Banked: all values, per-window
    breakdown, the max edge (SWEEP_BAND_EDGE) and the SWEEP_BAND_QUANTILE quantile (recorded
    softer reference edge, design §9c).

    n_struct ONLY — this driver computes no exponent, imports no fitting stack; the result dict
    and banked JSON carry no embargoed field (enforced structurally by the T8 firewall tests).

    `windows` (mapping label -> (CohortMarginals, pool_embeddings)) makes the core loop
    archive-independent for the fast synthetic tier; when None the three registered windows are
    loaded and their authored pools embedded once each."""
    from critaudit.sim.controls.llm_parrot import (
        check_matched_null_control, generate_matched_null)

    if n_seeds is None:
        n_seeds = lps.SWEEP_BAND_SEEDS
    if base_seed is None:
        base_seed = lps.NULL_BASE_SEED
    if n_seeds <= 0:
        raise ValueError(f"run_matched_null_band: n_seeds must be > 0 (got {n_seeds}) — an empty "
                         f"band would bank an edge computed from no data (fail-closed)")
    if windows is None:
        if theta is not None or window is not None:
            raise ValueError(
                "registered archive mode rejects ad-hoc window/theta overrides; use the banked rule")
        window, theta = banked_similarity_rule()
        from critaudit.sim.harness.embedding import embed_texts
        windows = {seed: (marg, embed_texts(marg.authored_texts))
                   for seed, (run, marg) in load_cohort_windows(archive_dir).items()}
        window_order = lps.WINDOW_ORDER
        windows_source = "archive"
    else:
        if theta is None or window is None:
            raise ValueError("injected mode requires explicit window and theta")
        # Injected mode (the fast synthetic tier): window order = the mapping's insertion order —
        # deterministic for a given construction, and stamped as non-archive provenance so a
        # synthetic band can never be mistaken for the registered artifact.
        window_order = tuple(windows)
        windows_source = "injected"

    values, seeds_rows = [], []
    per_window = {str(w): [] for w in window_order}
    for i in range(n_seeds):
        seed = base_seed + i
        w = window_order[i % len(window_order)]
        marg, E_pool = windows[w]
        run = generate_matched_null(seed, marg, E_pool, theta, window=window)
        diag = check_matched_null_control(run, marg, E_pool)   # fail-closed: aborts the band
        ns = diag["n_struct"]
        values.append(ns)
        per_window[str(w)].append(ns)
        seeds_rows.append({"seed": int(seed), "window": str(w), **diag})

    arr = np.asarray(values, dtype=float)
    record = {
        "artifact": "nstruct_band",
        "construction_version": lps.CALIBRATION_CONSTRUCTION_VERSION,
        "design": lps.DESIGN_DOC,
        "design_sha256": lps.DESIGN_DOC_SHA256,
        "spec": {
            "theta": float(theta),
            "similarity_window": int(window),
            "resampling_rule": lps.RESAMPLING_RULE,
            "base_seed": int(base_seed),
            "n_seeds": int(n_seeds),
            "window_assignment": lps.WINDOW_ASSIGNMENT,
            "window_order": [str(w) for w in window_order],
            "windows_source": windows_source,
            "band_quantile": lps.SWEEP_BAND_QUANTILE,
            "band_edge": lps.SWEEP_BAND_EDGE,
        },
        "n_struct_values": [float(v) for v in arr],
        "per_window": per_window,
        "edge_max": float(arr.max()),
        "quantile_value": float(np.quantile(arr, lps.SWEEP_BAND_QUANTILE)),
        "seeds": seeds_rows,
    }
    if out_path is not None:
        _dump_banked_json(record, out_path)
    return record

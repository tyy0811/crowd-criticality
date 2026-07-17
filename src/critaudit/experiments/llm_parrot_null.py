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
        _dump_banked_json(record, out_path)
    return record


def _dump_banked_json(record, out_path):
    """Deterministic banked-artifact serialization: sorted keys, no wall-clock anywhere —
    byte-identical on re-run (the @slow reproduction anchor)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(record, f, sort_keys=True, indent=1)
        f.write("\n")


# Part 2 (T7): the 64-seed n_struct band — n_struct ONLY (design §7/§8). The frozen chain:
# theta defaults to the BANKED T5 calibration output, never an ad-hoc value.
_BANKED_THETA_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "results", "s2_llm_parrot_null", "2026-07-17_theta_calibration.json")


def banked_theta(path=_BANKED_THETA_JSON):
    """The calibrated theta from the committed T5 artifact (fail-closed if absent/malformed)."""
    with open(path) as f:
        rec = json.load(f)
    theta = float(rec["theta"])
    if not (0.0 < theta < 1.0):
        raise ValueError(f"banked theta {theta} outside (0,1) — malformed artifact")
    return theta


def run_matched_null_band(archive_dir=DEFAULT_ARCHIVE, *, theta=None, out_path=None,
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
    if theta is None:
        theta = banked_theta()
    if windows is None:
        from critaudit.sim.harness.embedding import embed_texts
        windows = {seed: (marg, embed_texts(marg.authored_texts))
                   for seed, (run, marg) in load_cohort_windows(archive_dir).items()}
        window_order = lps.WINDOW_ORDER
    else:
        window_order = tuple(windows)

    values, seeds_rows = [], []
    per_window = {str(w): [] for w in window_order}
    for i in range(n_seeds):
        seed = base_seed + i
        w = window_order[i % len(window_order)]
        marg, E_pool = windows[w]
        run = generate_matched_null(seed, marg, E_pool, theta)
        diag = check_matched_null_control(run, marg, E_pool)   # fail-closed: aborts the band
        ns = diag["n_struct"]
        values.append(ns)
        per_window[str(w)].append(ns)
        seeds_rows.append({"seed": int(seed), "window": str(w), **diag})

    arr = np.asarray(values, dtype=float)
    record = {
        "artifact": "nstruct_band",
        "design": lps.DESIGN_DOC,
        "design_sha256": lps.DESIGN_DOC_SHA256,
        "spec": {
            "theta": float(theta),
            "base_seed": int(base_seed),
            "n_seeds": int(n_seeds),
            "window_assignment": lps.WINDOW_ASSIGNMENT,
            "window_order": [str(w) for w in window_order],
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

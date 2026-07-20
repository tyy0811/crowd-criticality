"""Fast synthetic tests for the n_struct band driver (sub-inc-2 T7): structure, determinism, and
the fail-closed abort path — no archive, no torch. The @slow real-archive band reproduction lives
here too (archive-gated)."""
import json
import hashlib
import os
import re

import numpy as np
import pytest

from critaudit.experiments.llm_parrot_null import banked_similarity_rule, run_matched_null_band
from critaudit.sim.controls import llm_parrot_spec as lps
from critaudit.sim.harness.cohort_marginals import CohortMarginals


def _toy_window(seed, n=30, dim=8, rounds=(10, 10, 10)):
    rng = np.random.default_rng(seed)
    E = np.ones(dim) + 0.3 * rng.normal(size=(n, dim))   # anisotropic (real-embedding geometry)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    texts = tuple(f"w{seed}-msg-{i:02d}-" + "x" * (i % 7) for i in range(n))
    return CohortMarginals(per_round_counts=rounds, authored_texts=texts), E


@pytest.fixture()
def toy_windows():
    return {f"win{k}": _toy_window(k) for k in range(3)}


def test_band_shape_keys_and_roundrobin(toy_windows):
    rec = run_matched_null_band(theta=0.5, window=2, n_seeds=6, base_seed=100,
                                windows=toy_windows)
    assert rec["artifact"] == "nstruct_band"
    assert len(rec["n_struct_values"]) == 6
    assert all(0.0 <= v < 1.0 for v in rec["n_struct_values"])
    assert [len(rec["per_window"][w]) for w in ("win0", "win1", "win2")] == [2, 2, 2]
    assert rec["edge_max"] == max(rec["n_struct_values"])
    assert rec["quantile_value"] <= rec["edge_max"]
    assert [row["seed"] for row in rec["seeds"]] == [100 + i for i in range(6)]


def test_band_deterministic(toy_windows):
    r1 = run_matched_null_band(theta=0.5, window=2, n_seeds=6, base_seed=100,
                               windows=toy_windows)
    r2 = run_matched_null_band(theta=0.5, window=2, n_seeds=6, base_seed=100,
                               windows=toy_windows)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_band_aborts_on_first_gate_failure(toy_windows):
    # Fail-closed abort (design §11 — no silently partial band): doctor one window so its pool
    # embeddings misalign with its marginals; the generator raises on the FIRST seed assigned to
    # that window and the band never returns.
    marg, E = toy_windows["win1"]
    toy_windows["win1"] = (marg, E[:-1])
    with pytest.raises(ValueError, match="misaligned"):
        run_matched_null_band(theta=0.5, window=2, n_seeds=6, base_seed=100,
                              windows=toy_windows)


def test_band_record_carries_no_embargoed_keys(toy_windows):
    rec = run_matched_null_band(theta=0.5, window=2, n_seeds=3, base_seed=7,
                                windows=toy_windows)
    blob = json.dumps(rec)
    assert not re.search(r'"[^"]*(tau|p_boot|alpha|gate_|n_emit)[^"]*"\s*:', blob)


def _calibration_record(status="passed"):
    target = 0.95 if status == "passed" else 0.2
    surface = []
    for window in lps.WINDOW_GRID:
        for theta in np.round(np.arange(
                lps.THETA_GRID_START,
                lps.THETA_GRID_STOP + lps.THETA_GRID_STEP / 2,
                lps.THETA_GRID_STEP), 6):
            ari = target if (window, float(theta)) == (2, 0.5) else 0.1
            surface.append([window, float(theta), ari, [ari, ari, ari]])
    return {
        "artifact": "similarity_calibration",
        "construction_version": lps.CALIBRATION_CONSTRUCTION_VERSION,
        "design": lps.DESIGN_DOC,
        "design_sha256": lps.DESIGN_DOC_SHA256,
        "amendment": lps.CALIBRATION_AMENDMENT,
        "status": status,
        "window": 2,
        "theta": 0.5,
        "mean_ari": target,
        "per_stream_ari": [target, target, target],
        "recovery_surface": surface,
        "spec": {
            "criterion": lps.THETA_CRITERION,
            "tie_rule": lps.THETA_TIE_RULE,
            "candidate_rule": lps.CANDIDATE_RULE,
            "theta_grid": [lps.THETA_GRID_START, lps.THETA_GRID_STOP, lps.THETA_GRID_STEP],
            "window_grid": list(lps.WINDOW_GRID),
            "recovery_threshold": lps.RECOVERY_THRESHOLD,
            "window_order": list(lps.WINDOW_ORDER),
        },
    }


def test_banked_similarity_rule_rejects_failed_calibration(tmp_path):
    path = tmp_path / "failed.json"
    path.write_text(json.dumps(_calibration_record("failed")))
    with pytest.raises(RuntimeError, match="status failed"):
        banked_similarity_rule(str(path))


def test_banked_similarity_rule_validates_and_returns_passed_pair(tmp_path):
    path = tmp_path / "passed.json"
    path.write_text(json.dumps(_calibration_record()))
    assert banked_similarity_rule(str(path)) == (2, 0.5)


def test_banked_similarity_rule_rejects_design_or_surface_tampering(tmp_path):
    record = _calibration_record()
    record["design_sha256"] = "0" * 64
    path = tmp_path / "tampered-design.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="design identity"):
        banked_similarity_rule(str(path))

    record = _calibration_record()
    record["recovery_surface"][0][2] = 0.99
    path = tmp_path / "tampered-surface.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="selected rule|surface"):
        banked_similarity_rule(str(path))


def test_registered_archive_mode_rejects_ad_hoc_rule_override():
    with pytest.raises(ValueError, match="registered archive"):
        run_matched_null_band(theta=0.5, window=2, n_seeds=1)


# Single-source location of the superseded descriptive band.
from critaudit.experiments.llm_parrot_null import (   # noqa: E402
    BANKED_BAND_JSON as _BANKED, DEFAULT_ARCHIVE as _ARCHIVE)


def test_failed_registered_calibration_blocks_band_and_preserves_legacy_bytes():
    """No construction-v2 band may be produced; the old descriptive band is not re-banked."""
    with pytest.raises(RuntimeError, match="status failed"):
        run_matched_null_band(_ARCHIVE)
    digest = hashlib.sha256(open(_BANKED, "rb").read()).hexdigest()
    assert digest == "b559523b33f3a0c66bbd9b2dd7210d096092a3e6a9e95caf2d2040af10296ced"

"""Planted-surface power checks for the recoverability-gate evaluator (sub-inc-3 T4): every
verdict branch is forced by a constructed surface — PASS-shaped, displaced-peak, flat
(demoted-χ-shaped ratio ≈ 1), non-monotone, endpoint-peak, and fabricated surfaces. The 'DID NOT
RAISE'/forced-verdict discipline: a gate whose failure branches were never tripped proves
nothing."""
import numpy as np
import pytest

from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.controls.probe_gate import evaluate_recoverability

_GRID = np.array(pspec.EPS_GRID)
_NE, _NS = _GRID.size, pspec.N_SEEDS


def _surface(chi_mean, n_gen_mean, *, noise=1e-4, seed=0, n_resp_offset=0.0):
    """Deterministic planted surface: per-seed values = mean + tiny seed-indexed jitter (keeps
    argmaxes aligned across seeds unless a test displaces them)."""
    rng = np.random.default_rng(seed)
    jitter = noise * rng.standard_normal((_NE, _NS))
    chi = np.asarray(chi_mean)[:, None] + jitter
    n_gen = np.asarray(n_gen_mean)[:, None] + noise * rng.standard_normal((_NE, _NS))
    s_mean = 1.0 / np.clip(1.0 - n_gen, 1e-3, None)          # consistent S̄ for monotonicity
    n_resp = n_gen + n_resp_offset                            # plant a controllable transform gap
    used = np.full((_NE, _NS), pspec.M_ELIGIBLE, dtype=int)
    return {"eps_grid": _GRID.tolist(), "chi_resp": chi.tolist(), "s_mean": s_mean.tolist(),
            "n_gen": n_gen.tolist(), "n_resp": n_resp.tolist(), "used_markers": used.tolist()}


def _passing_means():
    """chi peaked at the interior grid point nearest the planted n_gen=1 crossing; n_gen rises
    monotonically through 1 inside the dense window."""
    n_gen_mean = np.linspace(0.3, 1.6, _NE)                   # crosses 1 ~ index 9
    cross_idx = int(np.flatnonzero((n_gen_mean[:-1] < 1) & (n_gen_mean[1:] >= 1))[0])
    chi_mean = np.exp(-0.5 * ((np.arange(_NE) - cross_idx) / 1.2) ** 2) * 10.0 + 0.5
    return chi_mean, n_gen_mean, cross_idx


def test_pass_shaped_surface_passes():
    chi_mean, n_gen_mean, cross_idx = _passing_means()
    v = evaluate_recoverability(_surface(chi_mean, n_gen_mean))
    assert v["status"] == "PASS" and v["reasons"] == []
    assert abs(v["locator"]["eps_hat_index"] - cross_idx) <= 1
    assert v["transform"]["pass"] is True                     # n_resp planted == n_gen
    assert v["resolution"]["pass"] is True


def test_displaced_peak_fails():
    chi_mean, n_gen_mean, cross_idx = _passing_means()
    displaced = np.roll(chi_mean, 4)                          # peak 4 grid steps from crossing
    v = evaluate_recoverability(_surface(displaced, n_gen_mean))
    assert v["status"] == "FAIL"
    assert "crossing_outside_neighbor_interval" in v["reasons"]


def test_flat_surface_fails_on_prominence():
    # The demoted belief-variance χ shape: peak/off-peak ratio ~0.98 — must fail the 2.0 floor.
    _, n_gen_mean, _ = _passing_means()
    flat = np.full(_NE, 1.0)
    flat[_NE // 2] = 1.02
    v = evaluate_recoverability(_surface(flat, n_gen_mean))
    assert v["status"] == "FAIL"
    assert "prominence_below_floor" in v["reasons"]


def test_endpoint_argmax_fails():
    _, n_gen_mean, _ = _passing_means()
    rising = np.linspace(1.0, 20.0, _NE)                      # argmax at the last grid point
    v = evaluate_recoverability(_surface(rising, n_gen_mean))
    assert v["status"] == "FAIL"
    assert "endpoint_argmax" in v["reasons"]


def test_no_crossing_fails():
    chi_mean, _, _ = _passing_means()
    always_sub = np.linspace(0.2, 0.8, _NE)                   # never crosses 1
    v = evaluate_recoverability(_surface(chi_mean, always_sub))
    assert v["status"] == "FAIL"
    assert "crossing_not_bracketed_exactly_once" in v["reasons"]


def test_seed_inconsistency_fails():
    chi_mean, n_gen_mean, cross_idx = _passing_means()
    s = _surface(chi_mean, n_gen_mean)
    chi = np.asarray(s["chi_resp"])
    for col in range(5):                                      # 5 of 12 seeds peak far away
        chi[:, col] = np.roll(chi_mean, 6) + 1e-4 * col
    s["chi_resp"] = chi.tolist()
    v = evaluate_recoverability(s)
    assert v["status"] == "FAIL"
    assert "seed_consistency_below_floor" in v["reasons"]


def test_transform_subverdict_fails_on_planted_gap_without_gating():
    # A planted n_resp gap beyond tolerance fails (b) — but the GATE (locator) still passes:
    # sub-verdicts never gate (design §4).
    chi_mean, n_gen_mean, _ = _passing_means()
    v = evaluate_recoverability(_surface(chi_mean, n_gen_mean, n_resp_offset=0.2))
    assert v["status"] == "PASS"
    assert v["transform"]["pass"] is False
    assert any(r.startswith("accuracy_exceeded") for r in v["transform"]["reasons"])


def test_fabricated_surfaces_raise():
    chi_mean, n_gen_mean, _ = _passing_means()
    s = _surface(chi_mean, n_gen_mean)
    thin = {**s, "used_markers": (np.asarray(s["used_markers"]) - 1).tolist()}
    with pytest.raises(ValueError, match="marker support"):
        evaluate_recoverability(thin)
    nan = {**s, "chi_resp": np.where(np.isfinite(s["chi_resp"]), s["chi_resp"], 0).tolist()}
    nan["chi_resp"][3][4] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        evaluate_recoverability(nan)
    missing = {k: v for k, v in s.items() if k != "n_resp"}
    with pytest.raises(ValueError, match="missing"):
        evaluate_recoverability(missing)
    short = {**s, "chi_resp": s["chi_resp"][:-1]}
    with pytest.raises(ValueError, match="shape"):
        evaluate_recoverability(short)

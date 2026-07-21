"""Recoverability-gate evaluator (sub-inc-3 design §4) — a PURE function over a banked-surface
dict (never over live sim objects), Gate-D shape: fail-closed validation, status first-class,
machine-readable reasons, anti-fabrication guards. A FAILED verdict is diagnostic-only; Option B
(probe_spec.OPTION_B_TEXT) activates mechanically on locator FAIL."""
from __future__ import annotations

import numpy as np

from critaudit.sim.controls import probe_spec as pspec

_SURFACE_KEYS = ("eps_grid", "chi_resp", "s_mean", "n_gen", "n_resp", "used_markers")


def _as_matrix(surface, key, n_eps):
    m = np.asarray(surface[key], dtype=float)
    if m.shape != (n_eps, pspec.N_SEEDS):
        raise ValueError(f"surface[{key!r}] shape {m.shape} != ({n_eps}, {pspec.N_SEEDS}) — "
                         f"incomplete or fabricated surface (fail-closed)")
    if not np.all(np.isfinite(m)):
        raise ValueError(f"surface[{key!r}] carries non-finite values (fail-closed)")
    return m


def evaluate_recoverability(surface, *, spec=pspec):
    """surface: the banked per-(eps, seed) matrices. Returns the verdict dict with first-class
    status. RAISES (never returns) on structural problems: missing keys, wrong shapes, NaN,
    unequal marker support — the fabricated-surface guards (Gate-D used_seeds precedent).
    Gate status: PASS = locator (a); transform (b) and resolution (b2) are sub-verdicts recorded
    alongside and never gate."""
    for k in _SURFACE_KEYS:
        if k not in surface:
            raise ValueError(f"surface missing {k!r} (fail-closed)")
    grid = np.asarray(surface["eps_grid"], dtype=float)
    n_eps = grid.size
    if n_eps < 3 or np.any(np.diff(grid) <= 0):
        raise ValueError("eps_grid must be sorted, unique, length >= 3")
    chi = _as_matrix(surface, "chi_resp", n_eps)
    s_mean = _as_matrix(surface, "s_mean", n_eps)
    n_gen = _as_matrix(surface, "n_gen", n_eps)
    n_resp = _as_matrix(surface, "n_resp", n_eps)
    used = np.asarray(surface["used_markers"], dtype=np.int64)
    if used.shape != (n_eps, spec.N_SEEDS) or not np.all(used == spec.USED_MARKERS_MIN):
        raise ValueError(
            "unequal or thin marker support — every cell must carry exactly "
            f"{spec.USED_MARKERS_MIN} markers (fail-closed; no unequal support/df)")

    train = list(spec.TRAIN_SEED_INDICES)
    test = list(spec.TEST_SEED_INDICES)
    reasons = []

    # ---- (a) LOCATOR ---------------------------------------------------------------------
    chi_mean = chi.mean(axis=1)
    n_gen_mean = n_gen.mean(axis=1)

    # eps_c_gen: seed-mean n_gen crosses 1 exactly once (negative -> non-negative), no other
    # sign change anywhere on the grid.
    sign = n_gen_mean >= 1.0
    transitions = np.flatnonzero(sign[1:] != sign[:-1])
    eps_c_gen = None
    if transitions.size != 1 or not (not sign[0] and sign[-1]):
        reasons.append("crossing_not_bracketed_exactly_once")
    else:
        g = int(transitions[0])
        f0, f1 = n_gen_mean[g] - 1.0, n_gen_mean[g + 1] - 1.0
        eps_c_gen = float(grid[g] - f0 * (grid[g + 1] - grid[g]) / (f1 - f0))

    i_hat = int(np.argmax(chi_mean))
    interior = 0 < i_hat < n_eps - 1
    if not interior:
        reasons.append("endpoint_argmax")

    crossing_in_interval = False
    if interior and eps_c_gen is not None:
        crossing_in_interval = bool(grid[i_hat - 1] <= eps_c_gen <= grid[i_hat + 1])
        if not crossing_in_interval:
            reasons.append("crossing_outside_neighbor_interval")

    endpoint_max = float(max(chi_mean[0], chi_mean[-1]))
    prominence_ratio = float(chi_mean[i_hat] / endpoint_max) if endpoint_max > 0 else float("inf")
    if prominence_ratio < spec.PEAK_RATIO_MIN:
        reasons.append("prominence_below_floor")

    per_seed_argmax = np.argmax(chi, axis=0)
    consistent = np.abs(per_seed_argmax - i_hat) <= 1          # neighbor-interval sense
    seed_consistency = float(np.mean(consistent))
    if seed_consistency < spec.SEED_CONSISTENCY_MIN:
        reasons.append("seed_consistency_below_floor")

    locator_pass = not reasons

    # ---- (b) TRANSFORM (sub-verdict; never gates) -----------------------------------------
    tr_reasons = []
    n_gen_train = n_gen[:, train].mean(axis=1)
    sub = np.flatnonzero(n_gen_train < 1.0)
    if sub.size < 2:
        tr_reasons.append("fewer_than_two_subcritical_points")
    else:
        for a, b in zip(sub[:-1], sub[1:]):
            for name, m in (("s_mean", s_mean), ("n_gen", n_gen)):
                mu_a = m[a, train].mean()
                mu_b = m[b, train].mean()
                se = float(np.sqrt(m[a, train].std(ddof=1) ** 2 / len(train)
                                   + m[b, train].std(ddof=1) ** 2 / len(train)))
                if (mu_b - mu_a) <= -spec.MONOTONE_SE_MULT * se:
                    tr_reasons.append(f"non_monotone_{name}_at_{grid[a]:g}_{grid[b]:g}")
    lo, hi = spec.N_RESP_ACCURACY_RANGE
    acc_pts = np.flatnonzero((n_gen_train >= lo) & (n_gen_train <= hi))
    accuracy = {}
    if acc_pts.size == 0:
        tr_reasons.append("no_accuracy_range_points")
    for g in acc_pts:
        err = float(abs(n_resp[g, test].mean() - n_gen[g, test].mean()))
        accuracy[f"{grid[g]:g}"] = err
        if err > spec.N_RESP_TOL:
            tr_reasons.append(f"accuracy_exceeded_at_{grid[g]:g}")
    transform_pass = not tr_reasons

    # ---- (b2) RESOLUTION FLOOR (separate sub-verdict) --------------------------------------
    b2_reasons = []
    blo, bhi = spec.N_RESP_BAND
    band_pts = np.flatnonzero((n_gen_train >= blo) & (n_gen_train < bhi))
    band_2sd = {}
    if band_pts.size == 0:
        b2_reasons.append("no_band_points")
    for g in band_pts:
        v = float(2.0 * n_resp[g, test].std(ddof=1))
        band_2sd[f"{grid[g]:g}"] = v
        if v > spec.N_RESP_TOL:
            b2_reasons.append(f"resolution_exceeded_at_{grid[g]:g}")
    resolution_pass = not b2_reasons

    return {
        "status": "PASS" if locator_pass else "FAIL",
        "reasons": reasons,
        "locator": {
            "pass": locator_pass,
            "eps_hat": float(grid[i_hat]),
            "eps_hat_index": i_hat,
            "eps_c_gen": eps_c_gen,
            "interior": interior,
            "crossing_in_neighbor_interval": crossing_in_interval,
            "prominence_ratio": prominence_ratio,
            "seed_consistency": seed_consistency,
            "dist_from_eps_crit": float(abs(grid[i_hat] - 0.134)),   # recorded-not-gated
        },
        "transform": {"pass": transform_pass, "reasons": tr_reasons, "accuracy_err": accuracy},
        "resolution": {"pass": resolution_pass, "reasons": b2_reasons, "band_2sd": band_2sd},
    }

"""Per-market near-criticality gate: profile-likelihood over the branching ratio n, maxed over a power-law
shape grid, read under grid-extension toward the heavy-tail boundary. identified = the profile peak STAYS at
an interior near-critical n as the eps grid opens; migrated = it runs to the supercritical boundary. The
s-cached profile_ll is bit-equal to mu_t.fit_mu_only (was |Δ|=0; golden-guarded at <1e-3) and is the speed
the gate rides on. FROZEN PARAMETERS below are the gate's spec. The measured specificity — genuine
near-critical under a rate ramp false-migrates 15-27% per-market at 18-35k (N-matched), and out to 100k stays
in a ~7-17% band with no firm sub-10% N-trend (the 100k CI straddles 10%) -> per-market near-criticality not
resolvable at achievable Polymarket event counts — is the locked acceptance characterization (tests/test_gate_specificity.py
+ results/s0.4_feasibility/2026-06-23_per_market_criticality_DELIVERABLE.md).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from critaudit.hawkes.binned import PowerLawKernel
from critaudit.hawkes.mu_t import segment_edges_by_count

# ---- FROZEN gate parameters (the spec of the gate) ----
K_FLEX = 12
N_GRID = [0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20]
EPS_FULL = [0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.1]
C_GRID = [0.5, 1.0, 2.0]
EPS_MINS = [0.4, 0.2, 0.1, 0.05, 0.02]
MIGRATE_TOL = 0.15                       # identified iff |peak(0.02)-peak(0.4)| < TOL AND peak(0.02) < 1


def self_excitation(times, a, betas):
    """Per-event self-excitation s_i = Σ_k a_k Σ_{j<i} exp(-β_k (t_i - t_j)), stable O(N) recursion.
    Depends ONLY on (times, kernel) -> cache across n and across all μ-fit L-BFGS evals."""
    t = times
    A = np.zeros((t.size, betas.size))
    for i in range(1, t.size):
        A[i] = np.exp(-betas * (t[i] - t[i - 1])) * (A[i - 1] + 1.0)
    return A @ a


def comp_coef(times, horizon, a, betas):
    """Self-compensator per unit n: Σ_k (a_k/β_k) Σ_i (1 - exp(-(horizon - t_i) β_k))."""
    return float(np.sum((a / betas) * (1.0 - np.exp(-np.outer(horizon - times, betas))).sum(0)))


def profile_ll(times, horizon, s, cc, n, K):
    """max over piecewise-LINEAR μ(t) knots of the loglik, with n and shape (via cached s, cc) FIXED.
    Convex in μ -> single start. Bit-equal to mu_t.fit_mu_only(...,n,K)['ll']."""
    t = times
    knots = segment_edges_by_count(t, K, horizon)[0]
    L = np.diff(knots)
    seg = np.clip(np.searchsorted(knots, t, side="right") - 1, 0, K - 1)
    w = (t - knots[seg]) / L[seg]
    loc = np.empty(K + 1)
    for j in range(K + 1):
        lo, hi = knots[max(j - 1, 0)], knots[min(j + 1, K)]
        loc[j] = np.sum((t >= lo) & (t < hi)) / max(hi - lo, 1e-9) * 0.5
    m0 = np.maximum(loc, 1e-6)

    def fg(m):
        if np.any(m <= 0):
            return np.inf, np.zeros_like(m)
        lam = (1.0 - w) * m[seg] + w * m[seg + 1] + n * s
        if np.any(lam <= 0):
            return np.inf, np.zeros_like(m)
        comp_mu = np.sum(0.5 * (m[:-1] + m[1:]) * L)
        f = -(np.sum(np.log(lam)) - comp_mu - n * cc)
        invlam = 1.0 / lam
        g = np.zeros(K + 1)
        np.add.at(g, np.arange(K), 0.5 * L)
        np.add.at(g, np.arange(1, K + 1), 0.5 * L)
        np.add.at(g, seg, -(1.0 - w) * invlam)
        np.add.at(g, seg + 1, -w * invlam)
        return f, g

    r = minimize(fg, m0, method="L-BFGS-B", jac=True, bounds=[(1e-9, None)] * (K + 1))
    return -float(r.fun)


def ll_grid(times, horizon, K, n_grid=N_GRID, eps_full=EPS_FULL, c_grid=C_GRID):
    """ll[(n,eps,c)] over the full grid, caching s + cc once per (eps,c)."""
    ll = {}
    for eps in eps_full:
        for c in c_grid:
            a, betas = PowerLawKernel(eps=eps, c=c).soe()
            s = self_excitation(times, a, betas)
            cc = comp_coef(times, horizon, a, betas)
            for n in n_grid:
                ll[(n, eps, c)] = profile_ll(times, horizon, s, cc, n, K)
    return ll


def peak_at(ll, eps_min, n_cap, n_grid=N_GRID, eps_full=EPS_FULL, c_grid=C_GRID):
    """peak-n over shapes with eps >= eps_min, optionally constrained to n < n_cap."""
    epss = [e for e in eps_full if e >= eps_min]
    ns = [n for n in n_grid if n_cap is None or n < n_cap]
    prof = [(n, max(ll[(n, e, c)] for e in epss for c in c_grid)) for n in ns]
    return max(prof, key=lambda x: x[1])[0]


@dataclass
class GateVerdict:
    identified: bool          # interior near-critical max holds (True) vs migrated/degenerate (False)
    peak: float               # peak-n at the fully-opened grid (eps_min=0.02)
    peak_constrained: float   # peak-n under the n<1 cap (finite-window artifact vs genuine supercritical)
    peak04: float             # peak-n at the unopened grid (eps_min=0.4)
    migrated: float           # peak - peak04
    trajectory: list          # peak-n vs eps_min cutoff (the grid-extension trace)
    trajectory_constrained: list


def certify_near_critical(times, horizon, *, eps_mins=EPS_MINS, K=K_FLEX) -> GateVerdict:
    """The frozen per-market gate. identified iff the profile peak stays interior (|migrated| < MIGRATE_TOL)
    and subcritical (< 1) as the eps grid opens to the heavy-tail boundary."""
    ll = ll_grid(times, horizon, K)
    traj = [peak_at(ll, em, None) for em in eps_mins]
    traj_sub = [peak_at(ll, em, 1.0) for em in eps_mins]
    migrated = traj[-1] - traj[0]
    identified = bool(abs(migrated) < MIGRATE_TOL and traj[-1] < 1.0)
    return GateVerdict(identified=identified, peak=traj[-1], peak_constrained=traj_sub[-1],
                       peak04=traj[0], migrated=migrated, trajectory=traj, trajectory_constrained=traj_sub)

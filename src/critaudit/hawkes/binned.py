"""Within-bin-marginalizing Hawkes MLE for block-time-quantized (binned) event data.

When events are observed only as counts per time bin (e.g. on-chain trades stamped at ~2 s block
time), the within-bin order is lost — and a naive continuous-time MLE on the tied timestamps, or a
binned-Poisson likelihood, is biased HIGH in the branching ratio `n`. This estimator MARGINALIZES the
unknown within-bin order via Monte Carlo EM (Metropolis on within-bin positions + a continuous MLE
M-step), recovering `n`. Validated in S0.4 / Stage-1 (DECISIONS.md 2026-06-16): tracks the full-data
MLE across the power-law / near-critical envelope; the granularity gate cleared on this estimator.

Kernel-agnostic by design: a kernel supplies its unit-mass sum-of-exponentials (SOE) shape, so the
exponential and power-law (long-memory) kernels plug in through one interface. Kept modular because
real-data certification is the single thing most likely to force a change to the within-bin model.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import gamma as _gamma


# --- Kernels: .soe() -> (a, betas) for the unit-mass shape g(t)=sum_k a_k e^{-beta_k t}, normalised so
#     sum_k a_k/beta_k == 1. The branching ratio n (kernel scale) is fit separately by the estimator. ---

@dataclass(frozen=True)
class ExpKernel:
    """Exponential kernel g(t) = beta e^{-beta t} — a single SOE component, unit mass."""
    beta: float

    def soe(self):
        b = np.array([float(self.beta)])
        return b.copy(), b.copy()


@dataclass(frozen=True)
class PowerLawKernel:
    """Long-memory kernel phi(t) proportional to 1/(t+c)^(1+eps); unit-mass SOE by Bernstein quadrature.
    Small eps = heavier long-memory tail; small c = more sub-grid (within-bin) mass."""
    eps: float
    c: float
    M: int = 60

    def soe(self):
        edges = np.geomspace(1e-4, 1e4, self.M + 1)
        betas = np.sqrt(edges[:-1] * edges[1:])
        ds = edges[1:] - edges[:-1]
        rho = (self.eps * self.c**self.eps / _gamma(1.0 + self.eps)) * betas**self.eps * np.exp(-betas * self.c)
        a = rho * ds
        deficit = 1.0 - float((a / betas).sum())   # exact unit mass: absorb the small-s quadrature deficit
        if abs(deficit) > 1e-12:
            beta_tail = 1e-5
            a = np.append(a, deficit * beta_tail)
            betas = np.append(betas, beta_tail)
        return a, betas


def _nll(params, times, horizon, a, betas):
    """SOE Hawkes neg-log-lik of (mu, n) with fixed unit-mass kernel shape (a, betas). O(N*M)."""
    mu, n = params
    if mu <= 0 or n <= 0:
        return np.inf
    t = np.asarray(times, float)
    A = np.zeros((t.size, betas.size))
    for i in range(1, t.size):
        A[i] = np.exp(-betas * (t[i] - t[i - 1])) * (A[i - 1] + 1.0)
    lam = mu + n * (A @ a)
    if np.any(lam <= 0):
        return np.inf
    comp = mu * horizon + n * np.sum((a / betas) * (1.0 - np.exp(-np.outer(horizon - t, betas))).sum(0))
    return -(np.sum(np.log(lam)) - comp)


def _mle(times, horizon, a, betas, mu0):
    best = None
    for n0 in (0.3, 0.6, 0.9):
        r = minimize(_nll, [mu0, n0], args=(times, horizon, a, betas),
                     method="L-BFGS-B", bounds=[(1e-9, None), (1e-9, None)])
        best = r if best is None or r.fun < best.fun else best
    return float(best.x[0]), float(best.x[1])


def _ess(x):
    """Effective sample size of a 1-D trace (initial-positive-sequence autocorrelations)."""
    x = np.asarray(x, float) - np.mean(x)
    if x.size < 4 or x.var() == 0:
        return float(x.size)
    ac = np.correlate(x, x, "full")[x.size - 1:] / (x.var() * x.size)
    s = 1.0
    for k in range(1, x.size):
        if ac[k] <= 0:
            break
        s += 2 * ac[k]
    return float(x.size / s)


@dataclass
class BinnedFit:
    n: float                 # branching-ratio estimate
    mu: float                # baseline-rate estimate
    acceptance: float        # mean E-step Metropolis acceptance (mixing diagnostic)
    ess: float               # effective sample size of the post-burn n-trajectory
    trajectory: list         # per-EM-iteration n estimates


def fit_binned(counts, grid, horizon, kernel, rng, *, em_iters=20, sweeps=4, n0=0.5, burn=8) -> BinnedFit:
    """Estimate (mu, n) from binned event counts by marginalising the lost within-bin order (MCEM).

    counts  : events per bin (length ceil(horizon/grid)).
    kernel  : object with .soe() -> (a, betas); the kernel SHAPE is known, the branching ratio n is recovered.
    Returns a BinnedFit with n, mu, and the acceptance/ESS mixing diagnostics (load-bearing near n->1).
    """
    a, betas = kernel.soe()
    counts = np.asarray(counts, float)
    pieces = [rng.uniform(k * grid, (k + 1) * grid, int(ck)) for k, ck in enumerate(counts)]
    times = np.sort(np.concatenate(pieces)) if any(p.size for p in pieces) else np.empty(0)
    mu, n = counts.sum() / horizon * 0.5, float(n0)
    traj, accs = [], []
    for _ in range(em_iters):
        cur = _nll([mu, n], times, horizon, a, betas)
        acc, N = 0, times.size
        for _ in range(sweeps):
            for _ in range(N):
                i = int(rng.integers(N))
                k = int(times[i] // grid)
                prop = times.copy()
                prop[i] = rng.uniform(k * grid, (k + 1) * grid)
                prop.sort()
                pn = _nll([mu, n], prop, horizon, a, betas)
                if pn < cur or rng.random() < np.exp(min(0.0, cur - pn)):
                    times, cur, acc = prop, pn, acc + 1
        mu, n = _mle(times, horizon, a, betas, mu)
        traj.append(n)
        accs.append(acc / (sweeps * N) if N else 0.0)
    post = traj[burn:] if len(traj) > burn else traj[-1:]
    return BinnedFit(n=float(np.mean(post)), mu=float(mu),
                     acceptance=float(np.mean(accs)), ess=_ess(post), trajectory=traj)


def _counts(times, grid, horizon):
    nb = int(np.ceil(horizon / grid))
    return np.histogram(times, bins=np.arange(nb + 1) * grid)[0].astype(float)


@dataclass
class GranularityCert:
    n_full: float            # branching ratio from full-resolution timing (the reference)
    n_binned: float          # from grid-quantized counts, via within-bin marginalization
    diff: float              # n_binned - n_full
    fit: BinnedFit


def fit_full(times, horizon, kernel):
    """Continuous full-resolution Hawkes MLE -> (mu, n) with the kernel SHAPE fixed. The reference
    the granularity cert compares against AND the fit the GoF judges -- exposed (not discarded) so
    both callers see the identical deterministic result. Tolerates Δt=0 ties: the SOE + Lomax
    c-offset never reach phi(0)=inf (verified 2026-06-18)."""
    a, betas = kernel.soe()
    t = np.sort(np.asarray(times, dtype=float))
    return _mle(t, horizon, a, betas, t.size / horizon * 0.5)


def certify_granularity(times, grid, horizon, kernel, rng, **mcem_kw) -> GranularityCert:
    """Real-data granularity certification: does grid-quantization preserve n̂ on THESE dynamics?

    Fit n on the full (sub-grid) timing -> n_full (reference); fit n on the grid-binned counts via the
    within-bin-marginalizing estimator -> n_binned. On real source-B trades (sub-2 s match timestamps)
    with grid=2 s, this IS the real-data granularity certification — the remaining S0.4 risk: a small
    |diff| certifies that 2 s block-time (source A) loses no n̂ information for this market's dynamics.
    """
    t = np.sort(np.asarray(times, dtype=float))
    n_full = fit_full(t, horizon, kernel)[1]
    fit = fit_binned(_counts(t, grid, horizon), grid, horizon, kernel, rng, **mcem_kw)
    return GranularityCert(n_full=n_full, n_binned=fit.n, diff=fit.n - n_full, fit=fit)

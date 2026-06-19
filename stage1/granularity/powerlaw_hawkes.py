"""Power-law / long-memory Hawkes — generator + exact compensator (Stage-1 power-law granularity test).

Per DECISIONS 2026-06-16 (qualified G1): the decisive regime is the project's actual one — scale-free
(Hardiman-Bouchaud long-memory, IMPLEMENTATION_PLAN §82) and near-critical — NOT the exponential proxy.

Kernel: phi(t) = n * g(t),  g(t) = eps * c**eps / (t + c)**(1 + eps)   (Lomax/Pareto-II offspring delay,
tail exponent `eps`, lower cutoff `c`). Branching ratio n = ∫phi. BOTH knobs are dialed (review note 1):
  - small `eps`  -> heavier long-memory tail (the empirically-relevant shape);
  - small `c`    -> more sub-grid (within-bin) mass -> the regime that STRAINS marginalization.
Fraction of offspring within the grid Δ: F(Δ) = 1 - (c/(c+Δ))**eps.

Exact compensator (∫phi) per parent: n * (1 - (c/(c+t))**eps). Used for (a) Ogata residual validation
of the GENERATOR on its own output, and (b) the reference the sum-of-exponentials approx is checked
against sub-grid before it enters MCEM. O(N^2) — validation only, never the MCEM inner loop.
"""
from __future__ import annotations

import numpy as np


def simulate_powerlaw(n, horizon, mu, eps, c, rng, max_events=500_000):
    """Cluster/immigrant-offspring power-law Hawkes; offspring delays ~ Lomax(eps, c)."""
    n_imm = int(rng.poisson(mu * horizon))
    times = list(rng.uniform(0.0, horizon, size=n_imm))
    queue = list(times)
    while queue:
        parent = queue.pop()
        k = int(rng.poisson(n))
        if k:
            u = rng.uniform(0.0, 1.0, size=k)
            delays = c * ((1.0 - u) ** (-1.0 / eps) - 1.0)  # Lomax(eps, c) inverse-CDF
            for d in delays:
                ct = parent + float(d)
                if ct < horizon:
                    times.append(ct)
                    queue.append(ct)
        if len(times) > max_events:
            raise RuntimeError("event explosion — check n < 1")
    return np.sort(np.asarray(times, dtype=float))


def intensity_powerlaw(times, mu, n, eps, c):
    """lambda(t_i) = mu + sum_{j<i} phi(t_i - t_j). O(N^2) — exact reference."""
    t = np.asarray(times, dtype=float)
    lam = np.full(t.size, float(mu))
    for i in range(1, t.size):
        s = t[i] - t[:i]
        lam[i] += np.sum(n * eps * c**eps / (s + c) ** (1.0 + eps))
    return lam


def rescaled_times_powerlaw(times, mu, n, eps, c):
    """Cumulative compensator Lambda(t_i) = mu*t_i + sum_{j<i} n*(1 - (c/(c+t_i-t_j))**eps). O(N^2).
    Time-rescaling theorem: diff(Lambda) ~ iid Exp(1) iff the data match this exact power-law model."""
    t = np.asarray(times, dtype=float)
    Lam = np.empty(t.size)
    for i in range(t.size):
        past = t[:i]
        Lam[i] = mu * t[i] + np.sum(n * (1.0 - (c / (c + t[i] - past)) ** eps))
    return Lam


# --- Sum-of-exponentials (SOE) approximation: makes the power-law likelihood O(N*M) instead of
#     O(N^2). Validated against the EXACT kernel AND its consumed functionals (total mass, integrated
#     kernel sub-grid, bin-integrated intensity) before it enters MCEM — review addition 2. ---

def fit_soe(n, eps, c, M=60, s_lo=1e-4, s_hi=1e4):
    """phi(t) ~ sum_j a_j exp(-beta_j t) via QUADRATURE of the power-law's exact Bernstein/exponential
    representation:  phi(t) = int_0^inf rho(s) e^{-s t} ds,  rho(s) = n*eps*c^eps/Gamma(1+eps)*s^eps*e^{-s c}.
    Midpoint rule on a log-s grid -> a_j = rho(s_j)*ds_j, beta_j = s_j. Well-conditioned (no fitting),
    a_j >= 0 by construction, total mass sum a/beta = n in the continuum (quadrature error only)."""
    from scipy.special import gamma as _gamma
    edges = np.geomspace(s_lo, s_hi, M + 1)
    betas = np.sqrt(edges[:-1] * edges[1:])                 # log-midpoints
    ds = edges[1:] - edges[:-1]
    rho = (n * eps * c**eps / _gamma(1.0 + eps)) * betas**eps * np.exp(-betas * c)
    a = rho * ds
    # The log-grid quadrature undercounts the heavy far-tail (small-s) mass; absorb the deficit into
    # ONE slow component so the branching ratio sum a/beta = n is EXACT, without perturbing the
    # sub-grid integral (1-exp(-beta t) ~ 0 there). Keeps the consumed functionals faithful.
    deficit = n - float((a / betas).sum())
    if deficit > 1e-12:
        beta_tail = s_lo * 0.1
        a = np.append(a, deficit * beta_tail)
        betas = np.append(betas, beta_tail)
    return a, betas


def soe_kernel(t, a, betas):
    t = np.atleast_1d(np.asarray(t, float))
    return (a[None, :] * np.exp(-np.outer(t, betas))).sum(1)


def soe_integrated(t, a, betas):
    """SOE compensator int_0^t phi_soe = sum_j (a_j/beta_j)(1 - exp(-beta_j t)) — the consumed functional."""
    t = np.atleast_1d(np.asarray(t, float))
    return ((a / betas)[None, :] * (1.0 - np.exp(-np.outer(t, betas)))).sum(1)


def exact_integrated(t, n, eps, c):
    return n * (1.0 - (c / (c + np.asarray(t, float))) ** eps)


# --- Likelihoods: SOE (O(N*M), the MCEM engine) + exact (O(N^2), the anchor reference). Both fit
#     (mu, n) with the kernel SHAPE (eps, c) known — the favorable case that isolates n-recovery. ---

def _soe_recursion_A(times, betas):
    """A_k(i) = sum_{j<i} exp(-beta_k (t_i - t_j)); O(N*M) recursion. Returns (N, M)."""
    t = np.asarray(times, float)
    A = np.zeros((t.size, betas.size))
    for i in range(1, t.size):
        A[i] = np.exp(-betas * (t[i] - t[i - 1])) * (A[i - 1] + 1.0)
    return A


def soe_nll(params, times, horizon, a_hat, betas):
    """Neg-log-lik of (mu, n), fixed unit-mass SOE shape (a_hat, betas). lambda = mu + n*(A.a_hat)."""
    mu, n = params
    if mu <= 0 or n <= 0:
        return np.inf
    t = np.asarray(times, float)
    lam = mu + n * (_soe_recursion_A(t, betas) @ a_hat)
    if np.any(lam <= 0):
        return np.inf
    comp = mu * horizon + n * np.sum((a_hat / betas) * (1.0 - np.exp(-np.outer(horizon - t, betas))).sum(0))
    return -(np.sum(np.log(lam)) - comp)


def soe_mle(times, horizon, eps, c, M=60):
    """Recover (mu, n) via the SOE likelihood; kernel SHAPE (eps, c) known. O(N*M)/eval."""
    from scipy.optimize import minimize
    a_hat, betas = fit_soe(1.0, eps, c, M=M)            # unit-mass shape
    mu0 = times.size / horizon * 0.5
    best = None
    for n0 in (0.3, 0.6, 0.9):
        r = minimize(soe_nll, [mu0, n0], args=(times, horizon, a_hat, betas),
                     method="L-BFGS-B", bounds=[(1e-9, None), (1e-9, None)])
        best = r if best is None or r.fun < best.fun else best
    return float(best.x[0]), float(best.x[1])


def exact_nll(params, times, horizon, eps, c):
    """Exact O(N^2) neg-log-lik of (mu, n) — the reference the SOE engine is anchored against."""
    mu, n = params
    if mu <= 0 or n <= 0:
        return np.inf
    lam = intensity_powerlaw(times, mu, n, eps, c)
    if np.any(lam <= 0):
        return np.inf
    t = np.asarray(times, float)
    comp = mu * horizon + np.sum(n * (1.0 - (c / (c + horizon - t)) ** eps))
    return -(np.sum(np.log(lam)) - comp)


def exact_mle(times, horizon, eps, c):
    from scipy.optimize import minimize
    mu0 = times.size / horizon * 0.5
    best = None
    for n0 in (0.3, 0.6, 0.9):
        r = minimize(exact_nll, [mu0, n0], args=(times, horizon, eps, c),
                     method="L-BFGS-B", bounds=[(1e-9, None), (1e-9, None)])
        best = r if best is None or r.fun < best.fun else best
    return float(best.x[0]), float(best.x[1])


if __name__ == "__main__":
    from scipy import stats

    n, mu, eps, c, H = 0.6, 0.4, 0.4, 0.5, 4000.0
    print(f"power-law Hawkes generator self-validation (n={n}, mu={mu}, eps={eps}, c={c}, H={H})")
    print(f"sub-grid offspring fraction F(2s) = {1 - (c/(c+2.0))**eps:.3f}  (high within-bin mass target)")
    t = simulate_powerlaw(n, H, mu, eps, c, np.random.default_rng(0))
    print(f"\n[branching ratio] N={t.size}  rate={t.size/H:.4f}  expected mu/(1-n)={mu/(1-n):.4f}")
    Lam = rescaled_times_powerlaw(t, mu, n, eps, c)
    resid = np.diff(Lam)
    ks = stats.kstest(resid, "expon")
    print(f"[Ogata residuals, exact compensator] mean={resid.mean():.3f} (expect 1.000)  "
          f"var={resid.var():.3f} (expect 1.000)  KS-vs-Exp(1) p={ks.pvalue:.3f}")
    print("PASS if rate ~ mu/(1-n) AND KS p>0.05 -> generator produces a correct power-law Hawkes "
          "and can serve as the validated test bed for the SOE likelihood (review note 3).")

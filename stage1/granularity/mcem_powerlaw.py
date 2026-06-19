"""Power-law within-bin MCEM + recovery/discrimination test — the verdict-deciding step.

Reuses the validated within-bin augmentation (within_bin_mle.py) but swaps the exponential
likelihood for the certified SOE power-law likelihood. E-step is INSTRUMENTED (acceptance rate +
n-trajectory ESS) per review note: near n=1 a stuck sampler can look converged and be wrong.

Recovery criterion (review): MCEM (on 2 s-quantized counts) must track the FULL-DATA SOE-MLE on the
true un-quantized times — NOT the planted value, which is unrecoverable near critical even with
perfect data. Discrimination is judged at the resolution the full timing itself achieves.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from powerlaw_hawkes import simulate_powerlaw, fit_soe, soe_nll, soe_mle


def _counts(times, grid, horizon):
    nb = int(np.ceil(horizon / grid))
    return np.histogram(times, bins=np.arange(nb + 1) * grid)[0].astype(float)


def _init_positions(counts, grid, rng):
    times = [rng.uniform(k * grid, (k + 1) * grid) for k, ck in enumerate(counts) for _ in range(int(ck))]
    return np.sort(np.asarray(times, float))


def _estep(times, grid, mu, n, horizon, a_hat, betas, rng, sweeps):
    cur = soe_nll([mu, n], times, horizon, a_hat, betas)
    N, acc = times.size, 0
    for _ in range(sweeps):
        for _ in range(N):
            i = int(rng.integers(N))
            k = int(times[i] // grid)
            prop = times.copy()
            prop[i] = rng.uniform(k * grid, (k + 1) * grid)
            prop.sort()
            pn = soe_nll([mu, n], prop, horizon, a_hat, betas)
            if pn < cur or rng.random() < np.exp(min(0.0, cur - pn)):
                times, cur, acc = prop, pn, acc + 1
    return times, acc / (sweeps * N)


def _mstep(times, horizon, a_hat, betas, mu0):
    best = None
    for n0 in (0.3, 0.6, 0.9):
        r = minimize(soe_nll, [mu0, n0], args=(times, horizon, a_hat, betas),
                     method="L-BFGS-B", bounds=[(1e-9, None), (1e-9, None)])
        best = r if best is None or r.fun < best.fun else best
    return float(best.x[0]), float(best.x[1])


def _ess(x):
    """Effective sample size of a 1-D trace via initial-positive-sequence autocorrelations."""
    x = np.asarray(x, float)
    x = x - x.mean()
    if x.size < 4 or x.var() == 0:
        return float(x.size)
    ac = np.correlate(x, x, "full")[x.size - 1:] / (x.var() * x.size)
    s = 1.0
    for k in range(1, x.size):
        if ac[k] <= 0:
            break
        s += 2 * ac[k]
    return float(x.size / s)


def mcem_pl(counts, grid, horizon, eps, c, rng, M=14, em_iters=18, sweeps=3, n0=0.5, burn=8):
    a_hat, betas = fit_soe(1.0, eps, c, M=M)
    times = _init_positions(counts, grid, rng)
    mu, n = counts.sum() / horizon * 0.5, n0
    traj, accs = [], []
    for _ in range(em_iters):
        times, acc = _estep(times, grid, mu, n, horizon, a_hat, betas, rng, sweeps)
        mu, n = _mstep(times, horizon, a_hat, betas, mu)
        traj.append(n)
        accs.append(acc)
    return {"n_hat": float(np.mean(traj[burn:])), "traj": traj,
            "acc": float(np.mean(accs)), "ess": _ess(traj[burn:])}


def recovery_point(n_true, eps, c, mu, horizon, grid, seeds, M=14):
    """One envelope point: full-data SOE-MLE reference vs MCEM on 2 s-quantized counts."""
    out = []
    for s in seeds:
        t = simulate_powerlaw(n_true, horizon, mu, eps, c, np.random.default_rng(s))
        ref = soe_mle(t, horizon, eps, c, M=M)[1]
        r = mcem_pl(_counts(t, grid, horizon), grid, horizon, eps, c, np.random.default_rng(1000 + s), M=M)
        out.append((t.size, ref, r["n_hat"], r["acc"], r["ess"]))
    return out

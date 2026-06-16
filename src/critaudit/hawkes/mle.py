from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize, brentq
from scipy.stats import chi2

_BETA_STARTS = (0.5, 1.0, 2.0, 5.0)


@dataclass
class HawkesFit:
    n: float
    mu: float
    beta: float
    loglik: float
    ci: tuple = (float("nan"), float("nan"))  # 95% profile CI on n (Task 8)


def _recursion_R(times, beta):
    R = np.zeros(times.size)
    for i in range(1, times.size):
        R[i] = np.exp(-beta * (times[i] - times[i - 1])) * (1.0 + R[i - 1])
    return R


def _nll(params, times, horizon):
    mu, n, beta = params
    if mu <= 0 or n <= 0 or beta <= 0:
        return np.inf
    R = _recursion_R(times, beta)
    lam = mu + n * beta * R
    if np.any(lam <= 0):
        return np.inf
    compensator = mu * horizon + n * np.sum(1.0 - np.exp(-beta * (horizon - times)))
    return -(np.sum(np.log(lam)) - compensator)


def _fit_full(times, horizon):
    best = None
    mu0 = times.size / horizon * 0.5
    for b0 in _BETA_STARTS:
        r = minimize(_nll, [mu0, 0.5, b0], args=(times, horizon),
                     method="L-BFGS-B", bounds=[(1e-9, None)] * 3)
        if best is None or r.fun < best.fun:
            best = r
    return best


def _profile_nll(n_fixed, times, horizon):
    best = np.inf
    mu0 = times.size / horizon * 0.5
    for b0 in _BETA_STARTS:
        r = minimize(lambda p: _nll([p[0], n_fixed, p[1]], times, horizon),
                     [mu0, b0], method="L-BFGS-B", bounds=[(1e-9, None)] * 2)
        best = min(best, r.fun)
    return best


def _profile_ci(times, horizon, n_hat, nll_min, level):
    thr = chi2.ppf(level, 1)
    g = lambda nf: 2.0 * (_profile_nll(nf, times, horizon) - nll_min) - thr
    lo_b = max(1e-6, n_hat - 0.01)
    while lo_b > 1e-6 and g(lo_b) < 0:
        lo_b = max(1e-6, lo_b - 0.1)
    lo = brentq(g, lo_b, n_hat) if g(lo_b) > 0 else lo_b
    hi_b = n_hat + 0.01            # free to exceed 1 (stationarity-unconstrained)
    while g(hi_b) < 0 and hi_b < n_hat + 5.0:
        hi_b += 0.1
    hi = brentq(g, n_hat, hi_b) if g(hi_b) > 0 else hi_b
    return (float(lo), float(hi))


def fit(events, level=0.95):
    times = np.asarray(events.times, dtype=float)
    horizon = float(events.horizon)
    if times.size < 10:
        raise ValueError("need >= 10 events to fit")
    res = _fit_full(times, horizon)
    mu, n, beta = res.x
    ci = _profile_ci(times, horizon, n, res.fun, level)
    return HawkesFit(n=float(n), mu=float(mu), beta=float(beta),
                     loglik=float(-res.fun), ci=ci)

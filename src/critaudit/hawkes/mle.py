from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize

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


def fit(events, level=0.95):
    times = np.asarray(events.times, dtype=float)
    horizon = float(events.horizon)
    if times.size < 10:
        raise ValueError("need >= 10 events to fit")
    res = _fit_full(times, horizon)
    mu, n, beta = res.x
    return HawkesFit(n=float(n), mu=float(mu), beta=float(beta), loglik=float(-res.fun))

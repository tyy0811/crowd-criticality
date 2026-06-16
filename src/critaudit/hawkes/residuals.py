from __future__ import annotations
import numpy as np
from scipy.stats import kstest


def rescaled_residuals(events, fit):
    """Ogata time-rescaling: Lambda(t_i) = mu*t_i + n*(#prior - R_i). Under a
    correct model the increments dLambda are i.i.d. Exp(1). Returns (dtau, KS, p)."""
    times = np.asarray(events.times, dtype=float)
    mu, n, beta = fit.mu, fit.n, fit.beta
    R = np.zeros(times.size)
    for i in range(1, times.size):
        R[i] = np.exp(-beta * (times[i] - times[i - 1])) * (1.0 + R[i - 1])
    prior_counts = np.arange(times.size)  # events strictly before index i
    Lambda = mu * times + n * (prior_counts - R)
    dtau = np.diff(Lambda)
    ks_stat, ks_p = kstest(dtau, "expon")  # unit-rate exponential
    return dtau, float(ks_stat), float(ks_p)

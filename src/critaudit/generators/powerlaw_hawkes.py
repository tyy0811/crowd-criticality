"""Power-law / long-memory Hawkes generator — phi(t) proportional to 1/(t+c)^(1+eps), branching ratio n.

Companion to the exponential `hawkes_sim`: the long-memory kernel of the Hardiman-Bouchaud market
lineage (small eps = heavier tail; small c = more sub-grid mass). Cluster / immigrant-offspring
simulation with Lomax(eps, c) offspring delays. `rescaled_times` gives the exact-compensator
time-rescaling residuals for Ogata goodness-of-fit.
"""
from __future__ import annotations

import numpy as np


def simulate(n, horizon, mu, eps, c, rng, max_events=500_000):
    """Cluster/immigrant-offspring power-law Hawkes; offspring delays ~ Lomax(eps, c). Sorted times.

    Note: realized rate runs below the stationary mu/(1-n) at finite horizon for heavy tails (eps<=1)
    because offspring beyond the horizon are truncated — a horizon edge effect, not a normalization
    error (it shrinks as horizon grows; the kernel integral is exactly n)."""
    if rng is None:
        raise ValueError("pass an explicit numpy Generator as rng")
    n_imm = int(rng.poisson(mu * horizon))
    times = list(rng.uniform(0.0, horizon, size=n_imm))
    queue = list(times)
    while queue:
        parent = queue.pop()
        k = int(rng.poisson(n))
        if k:
            u = rng.uniform(0.0, 1.0, size=k)
            for d in c * ((1.0 - u) ** (-1.0 / eps) - 1.0):   # Lomax(eps, c) inverse-CDF
                ct = parent + float(d)
                if ct < horizon:
                    times.append(ct)
                    queue.append(ct)
        if len(times) > max_events:
            raise RuntimeError("event explosion — check n < 1")
    return np.sort(np.asarray(times, dtype=float))


def rescaled_times(times, mu, n, eps, c):
    """Cumulative compensator Lambda(t_i) = mu*t_i + sum_{j<i} n*(1 - (c/(c+t_i-t_j))^eps). O(N^2).
    Time-rescaling theorem: diff(Lambda) ~ iid Exp(1) iff the data match this exact power-law model."""
    t = np.asarray(times, dtype=float)
    Lam = np.empty(t.size)
    for i in range(t.size):
        past = t[:i]
        Lam[i] = mu * t[i] + np.sum(n * (1.0 - (c / (c + t[i] - past)) ** eps))
    return Lam

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


def simulate_ramp(n, horizon, mu0, eps, c, ramp, rng, max_events=500_000):
    """Power-law Hawkes with a LINEAR-ramp immigration rate mu(t) = mu0*(1 + ramp*t/horizon) (end/start
    swing = 1+ramp). Offspring delays ~ Lomax(eps, c), as in `simulate`. The non-stationarity a smooth
    mu(t) fit must absorb; `ramp=0` reduces to the stationary `simulate` immigration. Sorted times."""
    mu_max = mu0 * (1.0 + max(ramp, 0.0))
    cand = rng.uniform(0.0, horizon, rng.poisson(mu_max * horizon))
    imm = cand[rng.uniform(0.0, 1.0, cand.size) < (mu0 * (1.0 + ramp * cand / horizon)) / mu_max]
    times, queue = list(imm), list(imm)
    while queue:
        p = queue.pop()
        k = int(rng.poisson(n))
        if k:
            for ct in p + c * ((1.0 - rng.uniform(0.0, 1.0, k)) ** (-1.0 / eps) - 1.0):
                if ct < horizon:
                    times.append(ct); queue.append(ct)
        if len(times) > max_events:
            raise RuntimeError("event explosion — check n < 1")   # raise, matching `simulate` (not a silent truncate)
    return np.sort(np.asarray(times, float))


def simulate_labeled(n, horizon, mu, eps, c, rng, max_events=500_000):
    """Label-emitting twin of `simulate`: IDENTICAL rng stream + sorted times, PLUS each event's root
    (immigrant) id and parent index, both in sorted-space (immigrants have parent_idx = -1). The
    bookkeeping adds no rng draws, so for a given seed simulate_labeled(...)[0] is np.array_equal to
    simulate(...). Used to build Gate-D cascade ground truth (the mechanical parent->offspring tree)."""
    if rng is None:
        raise ValueError("pass an explicit numpy Generator as rng")
    n_imm = int(rng.poisson(mu * horizon))
    times = list(rng.uniform(0.0, horizon, size=n_imm))
    root = list(range(n_imm))           # immigrant i is its own root (generation-order index)
    parent = [-1] * n_imm               # immigrants have no parent
    queue = list(range(n_imm))          # INDICES, LIFO — same processing order as simulate's value-queue
    while queue:
        pidx = queue.pop()
        k = int(rng.poisson(n))
        if k:
            u = rng.uniform(0.0, 1.0, size=k)
            for d in c * ((1.0 - u) ** (-1.0 / eps) - 1.0):
                ct = times[pidx] + float(d)
                if ct < horizon:
                    cidx = len(times)
                    times.append(ct)
                    root.append(root[pidx])
                    parent.append(pidx)
                    queue.append(cidx)
        if len(times) > max_events:
            raise RuntimeError("event explosion — check n < 1")
    t = np.asarray(times, dtype=float)
    order = np.argsort(t, kind="stable")               # generation-order -> time-sorted
    inv = np.empty(t.size, dtype=np.int64)
    inv[order] = np.arange(t.size)                     # old gen-index -> new sorted-index
    pg = np.asarray(parent, dtype=np.int64)[order]
    parent_sorted = np.where(pg < 0, -1, inv[np.where(pg < 0, 0, pg)])
    root_sorted = inv[np.asarray(root, dtype=np.int64)[order]]
    return t[order], root_sorted, parent_sorted

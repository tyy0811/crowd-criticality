from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from critaudit.powerlaw.csn import _fit   # the powerlaw.Fit wrapper from Task 6
from critaudit.types import AvalancheSet


@dataclass
class DeltaResult:
    samples: np.ndarray
    ci: tuple
    halfwidth: float


def _clean(av):
    if av.censored is not None:
        keep = ~np.asarray(av.censored)
        return np.asarray(av.sizes)[keep], np.asarray(av.durations)[keep]
    return np.asarray(av.sizes), np.asarray(av.durations)


def _curv_slope(sizes, durations, min_count=50):
    """1/snz via the curvature-corrected bulk fit log<S|T> = a + g*logT + b/T -> g.
    (A reasonable, NOT load-bearing estimator: Gate A.2 is a coarse corroborative check.)"""
    T, M = [], []
    for t in np.unique(durations):
        m = durations == t
        if m.sum() >= min_count:
            T.append(t); M.append(sizes[m].mean())
    if len(T) < 4:
        return np.nan
    T = np.array(T, float); M = np.array(M)
    X = np.column_stack([np.ones_like(T), np.log(T), 1.0 / T])
    return float(np.linalg.lstsq(X, np.log(M), rcond=None)[0][1])


def exponents(av, min_count=50, xmin_size=None, xmin_dur=None):
    sizes, durations = _clean(av)
    tau = float(_fit(sizes, xmin=xmin_size).power_law.alpha)
    alpha = float(_fit(durations, xmin=xmin_dur).power_law.alpha)
    return tau, alpha, _curv_slope(sizes, durations, min_count)


def delta(av, min_count=50):
    tau, alpha, inv = exponents(av, min_count)
    return (alpha - 1.0) / (tau - 1.0) - inv


def joint_bootstrap(av, B, rng, min_count=50):
    """Resample avalanches; re-estimate all exponents per replicate (re-running CSN
    so x_min is re-selected each replicate) -> Delta's bootstrap CI for reporting."""
    sizes, durations = _clean(av)
    N = sizes.size
    samples = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, N, size=N)
        sub = AvalancheSet(sizes=sizes[idx], durations=durations[idx])
        tau, alpha, inv = exponents(sub, min_count)
        samples[b] = (alpha - 1.0) / (tau - 1.0) - inv
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return DeltaResult(samples=samples, ci=(float(lo), float(hi)), halfwidth=float((hi - lo) / 2))

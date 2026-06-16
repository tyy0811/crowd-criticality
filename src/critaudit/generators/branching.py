from __future__ import annotations
import warnings
import numpy as np
from critaudit.types import AvalancheSet

_SANITY_DONE = set()


def galton_watson(offspring_mean, n_avalanches, rng, size_cap=10**10):
    """Poisson-offspring Galton–Watson avalanches. m=1 critical (tau=3/2, alpha=2,
    1/snz=2); m<1 subcritical (CSN-killer). Per-avalanche cost is O(duration).

    `size_cap` is ONLY a runaway-termination safety bound (the critical m=1 size law
    has divergent mean). The critical generator has NO intrinsic size cutoff — it is a
    clean s^-3/2 — so the cap must sit FAR above the natural maximum s_max ~ N^2, or it
    truncates the upper tail and the CSN truncated-power-law LRT correctly rejects the
    (now-truncated) sizes, failing Gate A.1. The default 10**10 clears s_max for
    n_avalanches up to ~1e5; censoring is then ~0. (size_cap=10**6 was a verified bug:
    it depleted the tail at only ~0.1% censored and made the critical cell un-passable.
    See DECISIONS.md 2026-06-16.)"""
    sizes = np.empty(n_avalanches, dtype=np.int64)
    durations = np.empty(n_avalanches, dtype=np.int64)
    censored = np.zeros(n_avalanches, dtype=bool)
    for i in range(n_avalanches):
        size = 0
        gen = 0
        current = 1
        while current > 0:
            gen += 1
            size += current
            if size > size_cap:
                censored[i] = True
                break
            current = int(rng.poisson(offspring_mean * current))
        sizes[i] = size
        durations[i] = gen
    frac = float(censored.mean())
    if frac > 0.0005:
        warnings.warn(
            f"galton_watson: censored fraction {frac:.3%} (size_cap={size_cap}) — "
            f"the cap is depleting the upper tail, which biases the CSN power-law / "
            f"scaling fits (truncated-PL LRT will reject). Raise size_cap well above "
            f"s_max ~ N^2 for m={offspring_mean}."
        )
    av = AvalancheSet(sizes=sizes, durations=durations, censored=censored)
    _sanity(offspring_mean, av)
    return av


def _sanity(m, av):
    if m in _SANITY_DONE:
        return
    _SANITY_DONE.add(m)
    s = av.sizes
    print(f"=== galton_watson sanity (m={m}) ===")
    print(f"  n={s.size} size[min/mean/max]={s.min()}/{s.mean():.2f}/{s.max()} "
          f"dur_max={av.durations.max()} censored={av.censored.mean():.4f}")

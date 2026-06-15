from __future__ import annotations
import warnings
import numpy as np
from critaudit.types import AvalancheSet

_SANITY_DONE = set()


def galton_watson(offspring_mean, n_avalanches, rng, size_cap=10**6):
    """Poisson-offspring Galton–Watson avalanches. m=1 critical (tau=3/2, alpha=2,
    1/snz=2); m<1 subcritical (CSN-killer). Per-avalanche cost is O(duration)."""
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
    if frac > 0.01:
        warnings.warn(
            f"galton_watson: censored fraction {frac:.2%} > 1% "
            f"(size_cap={size_cap} too low for m={offspring_mean})"
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

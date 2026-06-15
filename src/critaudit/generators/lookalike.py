from __future__ import annotations
import numpy as np
from critaudit.types import AvalancheSet


def scaling_break(critical, delta, rng):
    """Permute the (S, T) pairing of a critical AvalancheSet. delta>=1 = full
    shuffle: marginals preserved, mean-size-vs-duration scaling destroyed."""
    if critical.censored is not None:
        keep = ~critical.censored
        sizes = np.asarray(critical.sizes)[keep].copy()
        durations = np.asarray(critical.durations)[keep].copy()
    else:
        sizes = np.asarray(critical.sizes).copy()
        durations = np.asarray(critical.durations).copy()
    n = sizes.size
    if delta >= 1.0:
        durations = durations[rng.permutation(n)]
    elif delta > 0.0:
        k = int(delta * n)
        idx = rng.choice(n, size=k, replace=False)
        durations[idx] = durations[rng.permutation(idx)]
    return AvalancheSet(sizes=sizes, durations=durations)  # clean: censored=None

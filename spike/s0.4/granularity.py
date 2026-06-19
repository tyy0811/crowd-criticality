"""Granularity primitives shared by the synthetic sweep and the real-data reconstruction.

`quantize_to_grid` models Polygon block-time assignment: every event in a ~2 s block
takes the block's start timestamp, so a burst of sub-block trades collapses to ties.
`tie_fraction` is the granularity *signal* — ties concentrate in exactly the bursts that
carry the Hawkes self-excitation, so it is the right lens (not the mean inter-event gap).
"""
from __future__ import annotations

import numpy as np


def quantize_to_grid(times: np.ndarray, grid: float) -> np.ndarray:
    """Floor `times` to a grid of spacing `grid`. Order-preserving; introduces ties for
    events sharing a grid cell. Returns a float array of the same length (non-decreasing)."""
    t = np.asarray(times, dtype=float)
    return np.floor(t / grid) * grid


def tie_fraction(times: np.ndarray) -> float:
    """Fraction of consecutive events with an identical timestamp (same-block ties)."""
    t = np.asarray(times, dtype=float)
    if t.size < 2:
        return 0.0
    return float(np.mean(np.diff(t) == 0.0))

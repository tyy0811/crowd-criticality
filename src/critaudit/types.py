from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class EventStream:
    times: np.ndarray
    horizon: float
    marks: np.ndarray | None = None  # RESERVED for Phase 2; always None in Phase 1

    def __post_init__(self):
        t = np.asarray(self.times, dtype=float)
        object.__setattr__(self, "times", t)
        if t.ndim != 1:
            raise ValueError("times must be 1-D")
        if t.size and np.any(np.diff(t) <= 0):
            raise ValueError("times must be strictly increasing")
        if t.size and (t[0] < 0 or t[-1] > self.horizon):
            raise ValueError("times must lie within [0, horizon]")


@dataclass(frozen=True)
class AvalancheSet:
    sizes: np.ndarray
    durations: np.ndarray
    censored: np.ndarray | None = None

    def __post_init__(self):
        s = np.asarray(self.sizes)
        d = np.asarray(self.durations)
        object.__setattr__(self, "sizes", s)
        object.__setattr__(self, "durations", d)
        if s.shape != d.shape:
            raise ValueError("sizes and durations must share shape")
        if s.size and (np.any(s < 1) or np.any(d < 1)):
            raise ValueError("sizes and durations must be >= 1")
        if self.censored is not None:
            c = np.asarray(self.censored, dtype=bool)
            object.__setattr__(self, "censored", c)
            if c.shape != s.shape:
                raise ValueError("censored mask must match sizes shape")

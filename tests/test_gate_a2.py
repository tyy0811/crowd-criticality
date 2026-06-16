import numpy as np
from critaudit.scaling.crackling import DeltaResult
from critaudit.scaling.gate_a2 import corroborate


def _dr(samples):
    s = np.asarray(samples, dtype=float)
    lo, hi = np.percentile(s, [2.5, 97.5])
    return DeltaResult(samples=s, ci=(float(lo), float(hi)),
                       halfwidth=float((hi - lo) / 2))


def test_small_delta_not_grossly_violated():
    # centred near 0 with a modest spread (half-width) -> corroborated
    dr = _dr([-0.08, -0.02, 0.0, 0.03, 0.07])
    assert corroborate(dr) == "not-grossly-violated"


def test_large_delta_grossly_violated():
    # centred near 2 (the full-shuffle look-alike) with a tight spread -> rejected
    dr = _dr([1.9, 1.95, 2.0, 2.05, 2.1])
    assert corroborate(dr) == "grossly-violated"


def test_explicit_resolution_overrides_halfwidth():
    # when resolution is given, it is used instead of the bootstrap half-width
    dr = _dr([0.3, 0.35, 0.4, 0.45, 0.5])  # mean ~0.4
    assert corroborate(dr, resolution=0.5) == "not-grossly-violated"  # 0.4 <= 2*0.5
    assert corroborate(dr, resolution=0.05) == "grossly-violated"     # 0.4 > 2*0.05

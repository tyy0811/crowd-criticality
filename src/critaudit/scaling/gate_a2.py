from __future__ import annotations


def corroborate(delta_result, resolution=None, k=2.0):
    """Coarse corroboration (NOT a fine pass/fail; no reference-null, no ceiling).
    resolution = the Gate-A.2 resolution Delta_min; if None, use the bootstrap half-width
    as a per-realization proxy. 'not-grossly-violated' if |mean Delta| <= k*resolution,
    else 'grossly-violated'."""
    res = delta_result.halfwidth if resolution is None else resolution
    return "not-grossly-violated" if abs(float(delta_result.samples.mean())) <= k * res else "grossly-violated"

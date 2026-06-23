import numpy as np

from critaudit.generators.powerlaw_hawkes import simulate_ramp


def _rate_profile(t, horizon, k=6):
    c, _ = np.histogram(t, bins=np.linspace(0, horizon, k + 1))
    return c / (horizon / k)


def test_simulate_ramp_actually_ramps():
    # The property the whole increment rides on: the event rate RISES across the horizon (the
    # non-stationarity the smooth μ(t) must absorb). Stationary `simulate` does NOT do this.
    t = simulate_ramp(0.60, 40000.0, 0.02, 0.35, 1.7, 9.0, np.random.default_rng(0))
    r = _rate_profile(t, 40000.0)
    assert r[-1] > 3.0 * r[0]                      # last sixth ≫ first sixth -> a real ramp
    assert t.size > 1000 and np.all(np.diff(t) >= 0)


def test_simulate_ramp_zero_is_stationary():
    # ramp=0 -> homogeneous immigration -> roughly flat rate (only heavy-tail offspring buildup).
    t = simulate_ramp(0.60, 40000.0, 0.05, 0.35, 1.7, 0.0, np.random.default_rng(1))
    r = _rate_profile(t, 40000.0)
    assert r[-1] < 2.0 * r[0]                      # NOT ramping

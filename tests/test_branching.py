import numpy as np
from critaudit.generators.branching import galton_watson
from critaudit.types import AvalancheSet


def test_returns_valid_avalancheset():
    av = galton_watson(1.0, 500, np.random.default_rng(0))
    assert isinstance(av, AvalancheSet)
    assert av.sizes.min() >= 1 and av.durations.min() >= 1
    assert av.censored.shape == av.sizes.shape


def test_reproducible():
    a = galton_watson(0.7, 300, np.random.default_rng(1)).sizes
    b = galton_watson(0.7, 300, np.random.default_rng(1)).sizes
    assert np.array_equal(a, b)


def test_subcritical_smaller_than_critical():
    crit = galton_watson(1.0, 4000, np.random.default_rng(2)).sizes.mean()
    sub = galton_watson(0.7, 4000, np.random.default_rng(3)).sizes.mean()
    assert sub < crit


def test_low_cap_flags_censored():
    av = galton_watson(1.0, 2000, np.random.default_rng(4), size_cap=50)
    assert av.censored.any()

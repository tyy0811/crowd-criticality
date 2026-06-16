import numpy as np
import pytest
from critaudit.generators.exact import pure_power_law


def test_returns_valid_sizes():
    s = pure_power_law(5000, np.random.default_rng(0))
    assert s.shape == (5000,)
    assert s.dtype == np.int64
    assert s.min() >= 1


def test_reproducible():
    a = pure_power_law(2000, np.random.default_rng(1))
    b = pure_power_law(2000, np.random.default_rng(1))
    assert np.array_equal(a, b)


def test_heavier_tail_for_smaller_exponent():
    # a shallower exponent (1.5) has a heavier tail than a steep one (3.0)
    rng = np.random.default_rng(2)
    shallow = pure_power_law(20000, rng, exponent=1.5)
    steep = pure_power_law(20000, rng, exponent=3.0)
    assert shallow.max() > steep.max()


def test_rejects_exponent_le_1():
    with pytest.raises(ValueError):
        pure_power_law(100, np.random.default_rng(0), exponent=1.0)

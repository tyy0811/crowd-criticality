import numpy as np
import pytest
from critaudit.generators.branching import galton_watson
from critaudit.types import AvalancheSet
from critaudit.scaling.crackling import exponents, delta, _clean


def test_critical_exponents_coarse():
    crit = galton_watson(1.0, 40000, np.random.default_rng(0))
    tau, alpha, inv = exponents(crit)
    assert 1.4 < tau < 1.6, f"tau={tau:.4f} outside [1.4, 1.6]"
    assert 1.8 < alpha < 2.2, f"alpha={alpha:.4f} outside [1.8, 2.2]"
    d = delta(crit)
    assert abs(d) < 0.3, f"delta={d:.4f} not < 0.3"


def test_clean_excludes_censored():
    rng = np.random.default_rng(42)
    n = 20
    sizes = rng.integers(1, 100, size=n)
    durations = rng.integers(1, 20, size=n)
    censored = np.zeros(n, dtype=bool)
    censored[::3] = True  # every 3rd entry censored
    av = AvalancheSet(sizes=sizes, durations=durations, censored=censored)
    clean_s, clean_d = _clean(av)
    expected_mask = ~censored
    assert len(clean_s) == expected_mask.sum(), (
        f"clean sizes length {len(clean_s)} != {expected_mask.sum()}"
    )
    assert len(clean_d) == expected_mask.sum(), (
        f"clean durations length {len(clean_d)} != {expected_mask.sum()}"
    )
    np.testing.assert_array_equal(clean_s, sizes[expected_mask])
    np.testing.assert_array_equal(clean_d, durations[expected_mask])

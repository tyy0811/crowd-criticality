import numpy as np
from granularity import quantize_to_grid, tie_fraction


def test_quantize_floors_to_grid():
    times = np.array([0.0, 1.9, 2.1, 3.999, 4.0])
    q = quantize_to_grid(times, 2.0)
    assert np.allclose(q, [0.0, 0.0, 2.0, 2.0, 4.0])


def test_quantize_preserves_order():
    times = np.array([0.1, 0.5, 2.3, 2.7, 5.0])
    q = quantize_to_grid(times, 2.0)
    assert np.all(np.diff(q) >= 0)


def test_tie_fraction_counts_consecutive_equal():
    # diffs [0, 2, 0, 2] -> 2 of 4 are ties
    times = np.array([0.0, 0.0, 2.0, 2.0, 4.0])
    assert tie_fraction(times) == 0.5


def test_tie_fraction_empty_and_singleton():
    assert tie_fraction(np.array([])) == 0.0
    assert tie_fraction(np.array([1.0])) == 0.0

import numpy as np
import pytest
from critaudit.types import AvalancheSet
from critaudit.sim.controls.anchors import n_struct


def test_n_struct_immigrant_only_is_zero():
    av = AvalancheSet(sizes=np.ones(5, np.int64), durations=np.ones(5, np.int64))
    assert n_struct(av) == 0.0


def test_n_struct_known_trees():
    # 3 trees, 6 events -> 1 - 3/6 = 0.5
    av = AvalancheSet(sizes=np.array([3, 1, 2], np.int64), durations=np.array([2, 1, 2], np.int64))
    assert n_struct(av) == pytest.approx(0.5)


def test_n_struct_empty_raises():
    av = AvalancheSet(sizes=np.array([], np.int64), durations=np.array([], np.int64))
    with pytest.raises(ValueError):
        n_struct(av)

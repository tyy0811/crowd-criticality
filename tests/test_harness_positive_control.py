# tests/test_harness_positive_control.py
import numpy as np
from critaudit.sim.harness.types import HarnessRun
from critaudit.sim.harness.positive_control import check_positive_control

def _coupled_run():
    # one tree of 4 (root + 3 read->emit replies) -> not all size-1, not one giant, read_emit>0
    times = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    parent_idx = np.array([-1, 0, 1, -1, 3, 0], dtype=np.int64)
    root_id = np.array([0, 0, 0, 3, 3, 0], dtype=np.int64)
    read_emit = np.array([False, True, True, False, True, True])
    content = ["aaaa", "bbbbbbbb", "cc", "dddddddddd", "e", "ffffff"]
    return HarnessRun(times, root_id, parent_idx, read_emit, content)

def _degenerate_all_size1():
    n = 6
    times = np.arange(n, dtype=float)
    parent_idx = np.full(n, -1, dtype=np.int64)
    root_id = np.arange(n, dtype=np.int64)
    read_emit = np.zeros(n, dtype=bool)
    content = ["x"] * n
    return HarnessRun(times, root_id, parent_idx, read_emit, content)

def test_positive_control_passes_on_coupled():
    diag = check_positive_control(_coupled_run())
    assert diag["read_emit_ratio"] > 0.0

def test_positive_control_raises_on_degenerate():
    try:
        check_positive_control(_degenerate_all_size1())
        assert False, "expected AssertionError on a degenerate (all size-1, no read->emit) crowd"
    except AssertionError:
        pass

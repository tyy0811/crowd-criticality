# tests/test_harness_positive_control.py
import numpy as np
import pytest
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

def _giant_only():
    # ONE tree swallowing ALL events (a degenerate single-component crowd) -> trips ONLY the giant check.
    # Hand-computed: sizes=[6], n_events=6 -> frac_size1 = 0/1 = 0.0 (clears <=0.95, single multi-event
    # tree has no size-1 trees); read_emit ratio = 4/6 ~= 0.667 (clears >0.01); length_spread =
    # std([4,8,2,10,1,6]) ~= 3.18 (clears >1.0); giant_frac = 6/6 = 1.0 > 0.90 is the SOLE failing check.
    times = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    parent_idx = np.array([-1, 0, 1, 0, 3, 0], dtype=np.int64)
    root_id = np.array([0, 0, 0, 0, 0, 0], dtype=np.int64)
    read_emit = np.array([False, True, True, False, True, True])
    content = ["aaaa", "bbbbbbbb", "cc", "dddddddddd", "e", "ffffff"]
    return HarnessRun(times, root_id, parent_idx, read_emit, content)

def _empty_run():
    # A degraded/timeout reference trace with ZERO events (empty arrays, empty content list).
    return HarnessRun(np.array([]), np.array([], dtype=np.int64),
                      np.array([], dtype=np.int64), np.array([], dtype=bool), [])

def test_positive_control_passes_on_coupled():
    diag = check_positive_control(_coupled_run())
    assert diag["read_emit_ratio"] > 0.0

def test_positive_control_raises_on_degenerate():
    try:
        check_positive_control(_degenerate_all_size1())
        assert False, "expected AssertionError on a degenerate (all size-1, no read->emit) crowd"
    except AssertionError:
        pass

def test_positive_control_raises_on_giant_only():
    # Regression guard on the giant_frac failure path — the ONE threshold no other fixture trips
    # (and simultaneously the tightest coupled-fixture margin). The fixture isolates giant_frac: only
    # that check fails (see _giant_only hand-computation), so a silent-always-pass drift in
    # harness_spec.MAX_GIANT_FRAC (e.g. a bound mis-set > 1.0) would surface HERE and nowhere else.
    # pytest.raises (not try/except + `assert False`) is deliberate: the latter idiom would SWALLOW the
    # very AssertionError under test, giving a false green when the gate stops enforcing (teeth check).
    with pytest.raises(AssertionError):
        check_positive_control(_giant_only())

def test_positive_control_raises_labelled_on_empty():
    # An empty/degraded reference must fail the gate LOUDLY with a LABELLED AssertionError — the guard
    # exists precisely so this is NOT an incidental ZeroDivisionError from the frac_size1 division (0/0).
    # Live scenario: this sub-increment already produced a timeout-degraded OASIS trace (design §8/§9).
    with pytest.raises(AssertionError):
        check_positive_control(_empty_run())

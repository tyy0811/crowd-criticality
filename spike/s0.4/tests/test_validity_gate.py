import pytest
from validity_gate import classify


def _good(**over):
    kw = dict(resolvable_timescale=8.0, t_threshold=2.0,
              reconciliation_ratio=1.0, expected_ratio=1.0, tolerance=0.05)
    kw.update(over)
    return classify(**kw)


def test_feasible_when_granularity_and_reconciliation_pass():
    v = _good()
    assert v.status == "feasible"
    assert v.granularity_ok and v.reconciliation_ok


def test_inadequate_when_timescale_below_threshold():
    v = _good(resolvable_timescale=1.0)  # < t_threshold 2.0
    assert v.status == "inadequate"
    assert v.granularity_ok is False


def test_inadequate_when_reconciliation_off_pinned_ratio():
    v = _good(reconciliation_ratio=1.4)  # |1.4 - 1.0| > 0.05
    assert v.status == "inadequate"
    assert v.reconciliation_ok is False


def test_blocked_requires_access_cost_or_effort_category():
    v = classify(resolvable_timescale=8.0, t_threshold=2.0, reconciliation_ratio=1.0,
                 expected_ratio=1.0, tolerance=0.05,
                 blocker="free Dune credits exhausted; paid tier needed at project scale",
                 blocker_category="cost")
    assert v.status == "blocked"
    assert "cost" in v.detail


def test_infeasible_is_not_an_available_verdict():
    with pytest.raises(ValueError):
        classify(resolvable_timescale=8.0, t_threshold=2.0, reconciliation_ratio=1.0,
                 expected_ratio=1.0, tolerance=0.05,
                 blocker="reconstruction impossible", blocker_category="infeasible")

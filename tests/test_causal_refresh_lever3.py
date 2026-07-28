"""Lever 3 differential equivalence: the optimized (index-backed) CausalRefreshController vs a
test-only naive-scan reference that overrides ONLY the three parent-set helpers with full-frame
comprehensions. All other logic (_build_feed, the guards, refresh, draw/serve/ledger) is the shared
production code, so this compares the optimized set-computation against an independent full scan,
never against itself. Covers treatment, holdout, no-selection, same-round leak, future leak, and
unregistered-round exposure over a multi-agent, multi-round frame. Fresh controller pairs are used
after any expected error."""

from __future__ import annotations

import pytest

from critaudit.sim.harness.causal_probe_records import (
    CandidatePair,
    ParentEligibility,
    SamplingFrame,
)
from critaudit.sim.harness.causal_refresh import CausalRefreshController


class NaiveCausalRefreshController(CausalRefreshController):
    """Naive-scan reference: overrides ONLY the three parent-set helpers with
    full-frame comprehensions; everything else is shared production logic."""

    def _agent_pairs(self, agent_id):
        return tuple(
            pair for pair in self._frame.candidate_pairs
            if pair.agent_id == agent_id)

    def _same_round_parents(self, agent_id, round_id):
        return frozenset(
            pair.parent_item_id for pair in self._frame.candidate_pairs
            if pair.agent_id == agent_id and pair.round_id == round_id)

    def _future_undrawn_parents(self, agent_id, round_id):
        return {
            pair.parent_item_id for pair in self._frame.candidate_pairs
            if pair.agent_id == agent_id and pair.round_id > round_id
            and pair.stratum_id not in self._drawn_strata}


class _Stream:
    def __init__(self, *values):
        self._values = list(values)

    def random(self):
        return self._values.pop(0)


def _rich_frame() -> SamplingFrame:
    """Multi-agent, multi-round: agent 20 has strata in rounds 3 AND 5 (so
    round-3 refreshes have a real future-round undrawn parent, post:3); agents
    21 (round 4) and 22 (round 5) give cross-agent coverage."""
    return SamplingFrame(
        frame_id="frame:lever3",
        parent_records=(
            ParentEligibility("post:1", author_agent_id=10, created_round=0),
            ParentEligibility("post:2", author_agent_id=11, created_round=0),
            ParentEligibility("post:3", author_agent_id=12, created_round=0),
            ParentEligibility("post:4", author_agent_id=13, created_round=0),
        ),
        excluded_recipient_agent_ids=(10, 11, 12, 13, 99),
        candidate_pairs=(
            CandidatePair("a1", "post:1", 20, 3, "agent:20:round:3", 0.4, 0.5, 3, 0, True),
            CandidatePair("a2", "post:2", 20, 3, "agent:20:round:3", 0.4, 0.5, 3, 0, True),
            CandidatePair("b1", "post:3", 20, 5, "agent:20:round:5", 0.5, 0.5, 5, 0, True),
            CandidatePair("c1", "post:2", 21, 4, "agent:21:round:4", 0.4, 0.5, 4, 0, True),
            CandidatePair("c2", "post:4", 21, 4, "agent:21:round:4", 0.4, 0.5, 4, 0, True),
            CandidatePair("d1", "post:4", 22, 5, "agent:22:round:5", 0.5, 0.5, 5, 0, True),
        ),
    )


_PARENT_POSTS = {f"post:{i}": {"post_id": i, "user_id": 9 + i} for i in (1, 2, 3, 4)}
_FILLER_POSTS = {f"post:{i}": {"post_id": 100 + i, "user_id": 50} for i in (1, 2, 3, 4)}


def _post(post_id):
    return {"post_id": post_id}


def _controllers(selection, treatment):
    """A production/naive pair on identical frames and identical RNG streams."""
    prod = CausalRefreshController(
        _rich_frame(), _Stream(*selection), _Stream(*treatment),
        parent_posts=_PARENT_POSTS, filler_posts=_FILLER_POSTS)
    naive = NaiveCausalRefreshController(
        _rich_frame(), _Stream(*selection), _Stream(*treatment),
        parent_posts=_PARENT_POSTS, filler_posts=_FILLER_POSTS)
    return prod, naive


def _step(ctrl, agent_id, round_id, background):
    """Return ('ok', feed_ids) or ('err', ExcType, message)."""
    try:
        feed = ctrl.refresh(agent_id, round_id, background)
    except Exception as exc:  # noqa: BLE001 - comparing exact type+message across impls
        return ("err", type(exc).__name__, str(exc))
    return ("ok", tuple(p["post_id"] for p in feed))


def _state(ctrl):
    return (ctrl.draws, ctrl.assignments, ctrl.services)


def _assert_step_equivalent(prod, naive, agent_id, round_id, background):
    rp = _step(prod, agent_id, round_id, background)
    rn = _step(naive, agent_id, round_id, background)
    assert rp == rn, f"step diverged: prod={rp} naive={rn}"
    assert _state(prod) == _state(naive), "post-step ledger state diverged"
    return rp


# --- lockstep sequence (treatment, holdout, no-selection, multi-round) --------------------------


def test_differential_lockstep_treatment_holdout_noselection_multiround():
    # round 3 agent 20 -> selected pair a1, treated (treatment 0.10 < 0.5)
    # round 4 agent 21 -> selected pair c1, holdout (treatment 0.90 >= 0.5)
    # round 5 agent 20 -> no selection (0.95 > 0.5+... residual), then agent 22 selected treated
    selection = [0.10, 0.10, 0.95, 0.10]
    treatment = [0.10, 0.90, 0.10]
    prod, naive = _controllers(selection, treatment)
    bg = (_post(500), _post(501))

    r1 = _assert_step_equivalent(prod, naive, 20, 3, bg)   # treatment
    assert r1[0] == "ok"
    r2 = _assert_step_equivalent(prod, naive, 21, 4, bg)   # holdout
    assert r2[0] == "ok"
    r3 = _assert_step_equivalent(prod, naive, 20, 5, bg)   # no-selection
    assert r3[0] == "ok"
    r4 = _assert_step_equivalent(prod, naive, 22, 5, bg)   # treatment
    assert r4[0] == "ok"
    # both controllers logged identical complete ledgers
    assert prod.draws == naive.draws
    assert prod.assignments == naive.assignments
    assert prod.services == naive.services


# --- expected-error scenarios (fresh controller pairs each) --------------------------------------


def test_differential_same_round_leak():
    # no-selection at round 3 (agent 20) with a same-round parent (post:2 -> id 2) in the background
    prod, naive = _controllers([0.95], [])
    bg = (_post(2), _post(500))
    r = _assert_step_equivalent(prod, naive, 20, 3, bg)
    assert r[0] == "err" and "same-round" in r[2]


def test_differential_future_leak():
    # no-selection at round 3 (agent 20) with the FUTURE-round parent (post:3 -> id 3, agent 20's
    # round-5 stratum, undrawn) in the background
    prod, naive = _controllers([0.95], [])
    bg = (_post(3), _post(500))
    r = _assert_step_equivalent(prod, naive, 20, 3, bg)
    assert r[0] == "err" and "future-round" in r[2]


def test_differential_selected_future_leak_in_build_feed():
    # selected+treated at round 3 (agent 20) but the future-round parent post:3 rides in the
    # background -> _build_feed's future-round guard raises
    prod, naive = _controllers([0.10], [0.10])
    bg = (_post(3), _post(500))
    r = _assert_step_equivalent(prod, naive, 20, 3, bg)
    assert r[0] == "err" and "future-round" in r[2]


def test_differential_unregistered_round_exposure():
    # assert_no_pending_exposure: agent 20 at an UNREGISTERED round (7) served a pending parent
    prod, naive = _controllers([], [])
    bg = (_post(1), _post(500))   # post:1 is agent 20's undrawn round-3 parent
    rp = None
    for ctrl in (prod, naive):
        try:
            ctrl.assert_no_pending_exposure(20, 7, bg)
            res = ("ok",)
        except Exception as exc:  # noqa: BLE001
            res = ("err", type(exc).__name__, str(exc))
        rp = res if rp is None else rp
        assert res == rp
    assert rp[0] == "err" and "registered parent" in rp[2]


def test_differential_selected_co_stratum_parent_stripped():
    # selected+treated at round 3; the co-stratum parent post:2 is stripped from the served feed
    # identically by both controllers
    prod, naive = _controllers([0.10], [0.10])
    bg = (_post(2), _post(500), _post(501))
    r = _assert_step_equivalent(prod, naive, 20, 3, bg)
    assert r[0] == "ok"
    assert 2 not in r[1] and r[1][0] == 1   # co-stratum post:2 stripped, parent post:1 served


# --- power check: the differential harness actually catches divergence ---------------------------


def test_differential_harness_has_power():
    """A deliberately-wrong helper override must be caught by the lockstep comparison."""
    class _BrokenController(CausalRefreshController):
        def _same_round_parents(self, agent_id, round_id):
            return frozenset()   # wrong: never strips co-stratum parents

    prod = CausalRefreshController(
        _rich_frame(), _Stream(0.10), _Stream(0.10),
        parent_posts=_PARENT_POSTS, filler_posts=_FILLER_POSTS)
    broken = _BrokenController(
        _rich_frame(), _Stream(0.10), _Stream(0.10),
        parent_posts=_PARENT_POSTS, filler_posts=_FILLER_POSTS)
    bg = (_post(2), _post(500), _post(501))
    with pytest.raises(AssertionError):
        _assert_step_equivalent(prod, broken, 20, 3, bg)

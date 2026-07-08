import numpy as np
from critaudit.sim.harness.types import EventRecord, RefreshRecord
from critaudit.sim.harness.assemble import compute_read_emit


def test_read_emit_pairing_cases():
    events = [
        EventRecord("p0", 0.0, 0, None, "root"),       # root -> not an emit
        EventRecord("c1", 1.0, 1, "p0", "reply"),      # agent1 read p0 -> success
        EventRecord("p3", 1.5, 0, None, "root2"),      # root -> not an emit
        EventRecord("c2", 2.0, 2, "c1", "reply"),      # agent2's served set lacks c1 -> not success
    ]
    refreshes = [
        RefreshRecord(1, 0.5, frozenset({"p0"})),      # agent1 saw p0 before t=1
        RefreshRecord(2, 1.5, frozenset({"p99"})),     # agent2 never saw c1
    ]
    out = compute_read_emit(events, refreshes)
    assert out.tolist() == [False, True, False, False]


def test_most_recent_prior_refresh_wins():
    events = [
        EventRecord("p0", 0.0, 0, None, "root"),
        EventRecord("c1", 1.0, 1, "p0", "reply"),
    ]
    refreshes = [
        RefreshRecord(1, 0.2, frozenset({"p0"})),      # older: saw p0
        RefreshRecord(1, 0.5, frozenset()),            # most-recent prior: empty -> not success
    ]
    out = compute_read_emit(events, refreshes)
    assert out.tolist() == [False, False]


def test_emit_before_any_refresh_is_not_success():
    events = [
        EventRecord("p0", 0.0, 0, None, "root"),
        EventRecord("c1", 0.1, 1, "p0", "reply"),      # agent1 has no refresh before t=0.1
    ]
    refreshes = [RefreshRecord(1, 5.0, frozenset({"p0"}))]
    out = compute_read_emit(events, refreshes)
    assert out.tolist() == [False, False]


# --- round-granular clock: created_at primary, trace-rowid (seq) tiebreaker within a round ---
# OASIS's sandbox clock advances created_at once per round; within a round the flow is
# refresh -> LLM -> emit, so a refresh and its consequent same-round emit SHARE created_at and
# are ordered only by trace insertion-order (rowid). Bare created_at '<' reconstructs 0 same-round
# pairs (the 2026-06-30 amendment); the pairing keys on (created_at, seq) instead.

def test_same_round_refresh_precedes_emit_via_seq():
    # refresh (seq=3) and its emit (seq=4) share created_at=1; the refresh is prior by rowid -> success
    events = [
        EventRecord("post:0", 0.0, 0, None, "root", seq=1),
        EventRecord("post:1", 1.0, 1, "post:0", "quote", seq=4),
    ]
    refreshes = [RefreshRecord(1, 1.0, frozenset({"post:0"}), seq=3)]
    out = compute_read_emit(events, refreshes)
    assert out.tolist() == [False, True]


def test_same_round_refresh_after_emit_is_not_success():
    # same created_at=1 but the refresh's rowid (seq=5) is AFTER the emit's (seq=3) -> NOT prior.
    # (This is the case a non-strict created_at '<=' would wrongly accept.)
    events = [
        EventRecord("post:0", 0.0, 0, None, "root", seq=1),
        EventRecord("post:1", 1.0, 1, "post:0", "quote", seq=3),
    ]
    refreshes = [RefreshRecord(1, 1.0, frozenset({"post:0"}), seq=5)]
    out = compute_read_emit(events, refreshes)
    assert out.tolist() == [False, False]


def test_seq_never_overrides_created_at_across_rounds():
    # a LATER-round refresh (created_at=2) with a tiny rowid (seq=1) must NOT count as prior to an
    # earlier-round emit (created_at=1): created_at is primary, seq only breaks within-round ties.
    events = [
        EventRecord("post:0", 0.0, 0, None, "root", seq=1),
        EventRecord("post:1", 1.0, 1, "post:0", "quote", seq=2),
    ]
    refreshes = [RefreshRecord(1, 2.0, frozenset({"post:0"}), seq=1)]
    out = compute_read_emit(events, refreshes)
    assert out.tolist() == [False, False]

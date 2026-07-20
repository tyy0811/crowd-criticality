from __future__ import annotations
import numpy as np
from critaudit.sim.harness.types import HarnessRun


def _time_sorted(events):
    """Stable sort by time — preserves causal insertion order on equal timestamps."""
    return sorted(events, key=lambda e: e.time)


def build_parent_root(events):
    """events: list[EventRecord]. Returns (times, root_id, parent_idx) in time-sorted, sorted-index
    space satisfying post_reply_tree's invariants. FAIL-CLOSED: unknown parent, duplicate item_id, or
    a parent that does not precede its child in time all raise (a malformed tree must not silently
    produce wrong sizes)."""
    ev = _time_sorted(events)
    n = len(ev)
    times = np.array([e.time for e in ev], dtype=float)
    id_to_idx = {}
    for i, e in enumerate(ev):
        if e.item_id in id_to_idx:
            raise ValueError(f"duplicate item_id {e.item_id!r}")
        id_to_idx[e.item_id] = i
    parent_idx = np.full(n, -1, dtype=np.int64)
    for i, e in enumerate(ev):
        if e.parent_item_id is not None:
            if e.parent_item_id not in id_to_idx:
                raise ValueError(f"event {e.item_id!r} references unknown parent {e.parent_item_id!r}")
            p = id_to_idx[e.parent_item_id]
            if not p < i:
                raise ValueError(f"parent {e.parent_item_id!r} does not precede child {e.item_id!r}")
            parent_idx[i] = p
    from critaudit.cascades.extract import roots_from_parents   # single home of root propagation
    return times, roots_from_parents(parent_idx), parent_idx


def compute_read_emit(events, refreshes):
    """Per-event read->emit success, aligned to the time-sorted events. True iff the event has a parent
    AND that parent's item_id is in the served set of the event-agent's MOST-RECENT PRIOR REFRESH,
    where 'prior' is by (time, seq) lexicographically: `time` (= created_at) is primary and `seq`
    (= trace rowid) breaks ties ONLY within the same `time`, never across rounds (the ratified
    2026-06-30 pairing rule — OASIS's clock is round-granular, so a refresh and its same-round emit
    share created_at and are ordered only by rowid). Realized fraction only (<= n_struct < 1) — NOT
    the crosses-1 n_emit."""
    by_agent = {}
    for r in refreshes:
        by_agent.setdefault(r.agent_id, []).append(r)
    for a in by_agent:
        by_agent[a].sort(key=lambda r: (r.time, r.seq))   # created_at primary, rowid tiebreaker
    ev = _time_sorted(events)
    out = np.zeros(len(ev), dtype=bool)
    for i, e in enumerate(ev):
        if e.parent_item_id is None:
            continue
        served = None
        for r in by_agent.get(e.agent_id, []):
            if (r.time, r.seq) < (e.time, e.seq):   # most-recent PRIOR by (created_at, rowid)
                served = r.served_item_ids
            else:
                break
        if served is not None and e.parent_item_id in served:
            out[i] = True
    return out


def assemble_harness_run(events, refreshes):
    """Compose the normalized HarnessRun. build_parent_root and compute_read_emit each re-apply the
    same stable time-sort, so their outputs align; content is taken in that same order."""
    ev = _time_sorted(events)
    times, root_id, parent_idx = build_parent_root(events)
    read_emit_success = compute_read_emit(events, refreshes)
    return HarnessRun(times=times, root_id=root_id, parent_idx=parent_idx,
                      read_emit_success=read_emit_success, content=[e.content for e in ev])

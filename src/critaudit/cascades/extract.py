"""Cascade extractors -> AvalancheSet. #1 post-reply tree (from parent links); #3 belief-update sequence
(canonical Beggs-Plenz avalanche binning, from timing only). Frozen knobs/policy come from spec.py.
Parent always precedes child in time (offspring delay d>0), so after time-sorting parent_idx[i] < i."""
from __future__ import annotations
import numpy as np
from critaudit.types import AvalancheSet
from critaudit.cascades import spec


def post_reply_tree(times, root_id, parent_idx) -> AvalancheSet:
    """#1: cascade = reply tree (events sharing a root). size = tree event-count; duration = generation
    depth (root depth 1), matching galton_watson's gen convention -> a critical stream gives tau~1.5,
    alpha~2. Deterministic from parent links; no fuzzy knob.

    Inputs are validated (FAIL-CLOSED): the forward depth pass needs parent_idx[i] < i, and the
    size-by-root_id grouping needs root_id consistent with the parent tree — otherwise a bad
    external/real-data tree would silently yield wrong sizes/durations (it does not crash)."""
    parent_idx = np.asarray(parent_idx, dtype=np.int64)
    root_id = np.asarray(root_id)
    n = parent_idx.size
    if root_id.size != n:
        raise ValueError("root_id and parent_idx must have the same length")
    idx = np.arange(n)
    has_parent = parent_idx >= 0
    if not (parent_idx[has_parent] < idx[has_parent]).all():
        raise ValueError("parent_idx[i] must reference an earlier index i (time-sort the stream first)")
    if not (root_id[~has_parent] == idx[~has_parent]).all():
        raise ValueError("immigrants (parent_idx < 0) must be their own root_id")
    if has_parent.any() and not (root_id[has_parent] == root_id[parent_idx[has_parent]]).all():
        raise ValueError("each event's root_id must equal its parent's root_id (inconsistent tree labels)")
    depth = np.ones(n, dtype=np.int64)
    for i in range(n):                          # forward pass valid: parent_idx[i] < i (asserted above)
        p = parent_idx[i]
        if p >= 0:
            depth[i] = depth[p] + 1
    _, inverse = np.unique(root_id, return_inverse=True)
    sizes = np.bincount(inverse).astype(np.int64)
    durations = np.zeros(sizes.size, dtype=np.int64)
    np.maximum.at(durations, inverse, depth)
    return AvalancheSet(sizes=sizes, durations=durations)


def bin_width(times, k):
    """Δt = k * median inter-event gap — rate-normalized, so a frozen k transports across streams of
    different rates. k is the dimensionless quiescence knob frozen in spec.TAU_Q_K. FAIL-CLOSED: needs
    >= 2 events to define a gap (an all-tied stream yields width 0, rejected downstream by
    _avalanche_labels rather than silently binning garbage)."""
    t = np.sort(np.asarray(times, dtype=float))
    gaps = np.diff(t)
    if gaps.size == 0:
        raise ValueError("bin_width needs >= 2 events to define a rate-normalized width")
    return float(k * np.median(gaps))


def _avalanche_labels(sorted_times, dt):
    """Per-event avalanche id under the frozen MERGE_POLICY at width dt: an empty bin (quiescence > dt)
    breaks the run. `sorted_times` MUST be ascending. Returns int64 ids 0..M-1 aligned to sorted_times
    ([] for empty input).

    The policy is READ from spec.MERGE_POLICY (load-bearing, not decorative): an unimplemented policy
    RAISES rather than silently doing the default, so the frozen constant cannot drift out of sync with
    the executed binning. dt must be finite and > 0 (FAIL-CLOSED: 0 from tied timestamps, NaN from
    < 2 events)."""
    policy = spec.MERGE_POLICY
    if not policy.single_membership:
        raise NotImplementedError("MERGE_POLICY.single_membership=False is not implemented")
    if policy.bin_edge != "left-closed":
        raise NotImplementedError(f"MERGE_POLICY.bin_edge={policy.bin_edge!r} not implemented (only 'left-closed')")
    t = np.asarray(sorted_times, dtype=float)
    if t.size == 0:
        return np.empty(0, dtype=np.int64)                   # empty -> no avalanches (defined)
    if not (np.isfinite(dt) and dt > 0):
        raise ValueError(f"dt must be finite and > 0 (got {dt!r}) — 0 from tied timestamps or NaN from < 2 events")
    b = np.floor((t - t[0]) / dt).astype(np.int64)           # left-closed bin index per event
    occupied = np.unique(b)
    new_run = np.concatenate([[0], (np.diff(occupied) > 1).astype(np.int64)])  # gap>1 bin => new avalanche
    run_id = np.cumsum(new_run)
    bin_to_run = {int(bb): int(r) for bb, r in zip(occupied, run_id)}
    return np.array([bin_to_run[int(bb)] for bb in b], dtype=np.int64)


def belief_update_sequence(times, is_belief_update, dt) -> AvalancheSet:
    """#3: among belief-update events, canonical avalanche binning at width dt. size = events in run;
    duration = #bins spanned (integer -> feeds the discrete CSN). MergePolicy: left-closed bins,
    single-membership (read from spec via _avalanche_labels)."""
    sel = np.asarray(is_belief_update, dtype=bool)
    t = np.sort(np.asarray(times, dtype=float)[sel])
    if t.size == 0:
        return AvalancheSet(sizes=np.array([], np.int64), durations=np.array([], np.int64))
    lab = _avalanche_labels(t, dt)
    b = np.floor((t - t[0]) / dt).astype(np.int64)
    M = int(lab.max()) + 1
    sizes = np.bincount(lab, minlength=M).astype(np.int64)
    durations = np.zeros(M, dtype=np.int64)
    for a in range(M):
        bb = b[lab == a]
        durations[a] = int(bb.max() - bb.min() + 1)
    return AvalancheSet(sizes=sizes, durations=durations)

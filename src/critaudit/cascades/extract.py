"""Cascade extractors -> AvalancheSet. #1 post-reply tree (from parent links); #3 belief-update sequence
(canonical Beggs-Plenz avalanche binning, from timing only). Frozen knobs/policy come from spec.py.
Parent always precedes child in time (offspring delay d>0), so after time-sorting parent_idx[i] < i."""
from __future__ import annotations
import numpy as np
from critaudit.types import AvalancheSet


def post_reply_tree(times, root_id, parent_idx) -> AvalancheSet:
    """#1: cascade = reply tree (events sharing a root). size = tree event-count; duration = generation
    depth (root depth 1), matching galton_watson's gen convention -> a critical stream gives tau~1.5,
    alpha~2. Deterministic from parent links; no fuzzy knob."""
    parent_idx = np.asarray(parent_idx, dtype=np.int64)
    n = parent_idx.size
    depth = np.ones(n, dtype=np.int64)
    for i in range(n):                          # forward pass valid: parent_idx[i] < i
        p = parent_idx[i]
        if p >= 0:
            depth[i] = depth[p] + 1
    _, inverse = np.unique(np.asarray(root_id), return_inverse=True)
    sizes = np.bincount(inverse).astype(np.int64)
    durations = np.zeros(sizes.size, dtype=np.int64)
    np.maximum.at(durations, inverse, depth)
    return AvalancheSet(sizes=sizes, durations=durations)


def bin_width(times, k):
    """Δt = k * median inter-event gap — rate-normalized, so a frozen k transports across streams of
    different rates. k is the dimensionless quiescence knob frozen in spec.TAU_Q_K."""
    t = np.sort(np.asarray(times, dtype=float))
    gaps = np.diff(t)
    return float(k * np.median(gaps)) if gaps.size else float("nan")


def _avalanche_labels(sorted_times, dt):
    """Per-event avalanche id under left-closed binning at width dt: an empty bin (quiescence > dt)
    breaks the run. `sorted_times` MUST be ascending. Returns int64 ids 0..M-1 aligned to sorted_times."""
    t = np.asarray(sorted_times, dtype=float)
    b = np.floor((t - t[0]) / dt).astype(np.int64)           # bin index per event
    occupied = np.unique(b)
    new_run = np.concatenate([[0], (np.diff(occupied) > 1).astype(np.int64)])  # gap>1 bin => new avalanche
    run_id = np.cumsum(new_run)
    bin_to_run = {int(bb): int(r) for bb, r in zip(occupied, run_id)}
    return np.array([bin_to_run[int(bb)] for bb in b], dtype=np.int64)


def belief_update_sequence(times, is_belief_update, dt) -> AvalancheSet:
    """#3: among belief-update events, canonical avalanche binning at width dt. size = events in run;
    duration = #bins spanned (integer -> feeds the discrete CSN). MergePolicy: left-closed bins,
    single-membership."""
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

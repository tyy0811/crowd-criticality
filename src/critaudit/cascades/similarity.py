"""Cascade definition #2: finite-window embedding-similarity infection.

The registered contract is membership recovery, not exact-parent recovery.  An event may inherit
one active cascade through the most-similar event in a strictly earlier round no more than
``window`` rounds old.  The calibrated rule is the (window, theta) pair maximizing equal-stream
mean ARI against true cascade membership; a rule is consumable only when it clears Gate D.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from critaudit.cascades import spec as cascade_spec
from critaudit.cascades.calibrate import adjusted_rand
from critaudit.cascades.extract import roots_from_parents
from critaudit.sim.controls import llm_parrot_spec as lps


def theta_grid(spec=lps):
    """The inclusive registered theta grid, represented as exact six-decimal values."""
    n = int(round((spec.THETA_GRID_STOP - spec.THETA_GRID_START) / spec.THETA_GRID_STEP)) + 1
    return np.round(spec.THETA_GRID_START + spec.THETA_GRID_STEP * np.arange(n), 6)


def rounded_cosines(E_query, E_cand, *, decimals=lps.COSINE_DECIMALS):
    """Rounded cosine matrix over pre-normalized embedding rows."""
    E_query = np.asarray(E_query, dtype=np.float64)
    E_cand = np.asarray(E_cand, dtype=np.float64)
    if E_query.ndim != 2 or E_cand.ndim != 2 or E_query.shape[1] != E_cand.shape[1]:
        raise ValueError(f"bad embedding shapes {E_query.shape} vs {E_cand.shape}")
    return np.round(E_query @ E_cand.T, decimals)


def _validate_policy():
    policy = cascade_spec.MERGE_POLICY
    if not policy.single_membership or policy.merge_within_definition:
        raise NotImplementedError(
            "definition #2 implements only single-membership, no-merge cascades")


def _validate_window(window):
    if isinstance(window, bool) or int(window) != window or int(window) < 1:
        raise ValueError(f"window must be a positive integer number of rounds (got {window!r})")
    return int(window)


def _per_round_blocks(round_of, E, window, *, decimals):
    """Return rounded-cosine blocks for the one registered finite-window candidate rule."""
    round_of = np.asarray(round_of)
    E = np.asarray(E)
    window = _validate_window(window)
    if round_of.ndim != 1:
        raise ValueError("round_of must be one-dimensional")
    n = round_of.size
    if E.ndim != 2 or E.shape[0] != n:
        raise ValueError(f"round_of ({n}) and embeddings ({E.shape}) misaligned")
    if n and np.any(np.diff(round_of) < 0):
        raise ValueError("round_of must be non-decreasing (stream order)")

    blocks = []
    for r in np.unique(round_of):
        members = np.flatnonzero(round_of == r)
        lo = int(np.searchsorted(round_of, r - window, side="left"))
        hi = int(np.searchsorted(round_of, r, side="left"))
        C = (rounded_cosines(E[members], E[lo:hi], decimals=decimals)
             if hi > lo else None)
        blocks.append((members, lo, C))
    return blocks


def _best_window_candidate(round_of, E, window, *, decimals):
    """Best eligible candidate and rounded score per event; ties use lowest stream index."""
    n = np.asarray(round_of).size
    best_idx = np.full(n, -1, dtype=np.int64)
    best_cos = np.full(n, np.nan)
    for members, lo, C in _per_round_blocks(round_of, E, window, decimals=decimals):
        if C is None:
            continue
        local = np.argmax(C, axis=1)
        best_idx[members] = lo + local
        best_cos[members] = C[np.arange(members.size), local]
    return best_idx, best_cos


def _parents_from_best(best_idx, best_cos, theta, *, decimals):
    theta = float(theta)
    if not np.isfinite(theta) or not (0.0 < theta <= 1.0):
        raise ValueError(f"theta must be finite and in (0,1] (got {theta!r})")
    theta = round(theta, decimals)
    parent_idx = np.full(best_idx.size, -1, dtype=np.int64)
    hit = np.isfinite(best_cos) & (best_cos >= theta)
    parent_idx[hit] = best_idx[hit]
    return parent_idx


def attribute_similarity_parents(round_of, E, theta, *, window, spec=lps):
    """Apply registered definition #2 and return ``(parent_idx, root_id)`` in stream order."""
    _validate_policy()
    best_idx, best_cos = _best_window_candidate(
        round_of, E, window, decimals=spec.COSINE_DECIMALS)
    parent_idx = _parents_from_best(
        best_idx, best_cos, theta, decimals=spec.COSINE_DECIMALS)
    return parent_idx, roots_from_parents(parent_idx)


@dataclass(frozen=True)
class CalibrationResult:
    """Measured output of the registered joint membership-recovery calibration."""

    window: int
    theta: float
    mean_ari: float
    per_stream_ari: tuple
    status: str
    # (window, theta, equal-stream mean ARI, tuple(per-stream ARI)) for every grid pair.
    recovery_surface: tuple


def _validated_true_stream(parent_idx_true, round_of, E):
    parent_idx_true = np.asarray(parent_idx_true)
    round_of = np.asarray(round_of)
    E = np.asarray(E)
    if parent_idx_true.ndim != 1 or parent_idx_true.size == 0:
        raise ValueError("calibrate_similarity_rule: empty stream (fail-closed)")
    n = parent_idx_true.size
    if round_of.ndim != 1 or round_of.size != n or E.ndim != 2 or E.shape[0] != n:
        raise ValueError("parent_idx_true, round_of, and embeddings misaligned")
    if np.any(np.diff(round_of) < 0):
        raise ValueError("round_of must be non-decreasing (stream order)")
    if not np.issubdtype(parent_idx_true.dtype, np.integer):
        raise ValueError("parent_idx_true must have integer dtype")
    idx = np.arange(n)
    has_parent = parent_idx_true >= 0
    if not has_parent.any():
        raise ValueError("calibrate_similarity_rule: stream has no true edges (fail-closed)")
    if np.any(parent_idx_true < -1) or np.any(parent_idx_true[has_parent] >= idx[has_parent]):
        raise ValueError("parent_idx_true must contain -1 or an earlier event index")
    return parent_idx_true.astype(np.int64, copy=False), round_of, E, roots_from_parents(parent_idx_true)


def calibrate_similarity_rule_pooled(streams, *, spec=lps):
    """Jointly calibrate finite window and theta against equal-stream mean membership ARI."""
    _validate_policy()
    if not streams:
        raise ValueError("calibrate_similarity_rule_pooled: no streams (fail-closed)")
    prepared = [_validated_true_stream(*stream) for stream in streams]
    grid = theta_grid(spec)
    surface = []

    for window in spec.WINDOW_GRID:
        candidates = [
            (*_best_window_candidate(round_of, E, window,
                                     decimals=spec.COSINE_DECIMALS), true_root)
            for _, round_of, E, true_root in prepared
        ]
        for theta in grid:
            aris = []
            for best_idx, best_cos, true_root in candidates:
                parent_idx = _parents_from_best(
                    best_idx, best_cos, theta, decimals=spec.COSINE_DECIMALS)
                aris.append(float(adjusted_rand(roots_from_parents(parent_idx), true_root)))
            per_stream = tuple(aris)
            surface.append((int(window), float(theta), float(np.mean(aris)), per_stream))

    # Primary: largest mean ARI. Exact ties: smallest window, then largest theta.
    best = max(surface, key=lambda row: (row[2], -row[0], row[1]))
    status = "passed" if best[2] >= spec.RECOVERY_THRESHOLD else "failed"
    return CalibrationResult(window=best[0], theta=best[1], mean_ari=best[2],
                             per_stream_ari=best[3], status=status,
                             recovery_surface=tuple(surface))


def calibrate_similarity_rule(parent_idx_true, round_of, E, *, spec=lps):
    """Single-stream convenience wrapper around the registered pooled procedure."""
    return calibrate_similarity_rule_pooled([(parent_idx_true, round_of, E)], spec=spec)

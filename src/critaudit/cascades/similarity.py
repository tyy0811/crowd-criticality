"""Cascade definition #2 machinery — similarity-attributed parents (sub-inc-2 design 2026-07-17 §6).

Pure numpy over PRECOMPUTED embedding matrices; this module never imports torch, never reads a
cohort DB, and (structurally, enforced by tests/test_llm_parrot_firewall.py) never touches the
τ-arm/powerlaw/scaling stack. The frozen surface it realizes is llm_parrot_spec: the attribution
rule (argmax rounded cosine over strictly-earlier-round candidates, iff >= theta; ties -> lowest
index; else root) and the calibration PROCEDURE (attribution-Youden over the frozen grid;
theta = the procedure's measured output, never a constant).

Quantities named apart (the anchors.py discipline): the attributed parents here are cascade
DEFINITION #2 — an ATTRIBUTION rule, not observed reply links; on the LLM cohort this module is
used ONLY to calibrate theta against the TRUE links (def-#2 structure on the cohort itself is
embargoed to sub-inc 3)."""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from critaudit.sim.controls import llm_parrot_spec as lps


def theta_grid(spec=lps):
    """The frozen inclusive calibration grid (start/stop/step from the spec), rounded to 6 dp so
    grid values are exact decimals, not accumulated float steps."""
    n = int(round((spec.THETA_GRID_STOP - spec.THETA_GRID_START) / spec.THETA_GRID_STEP)) + 1
    return np.round(spec.THETA_GRID_START + spec.THETA_GRID_STEP * np.arange(n), 6)


def rounded_cosines(E_query, E_cand, *, decimals=lps.COSINE_DECIMALS):
    """(n_q, n_c) cosine matrix of L2-normalized rows, rounded to `decimals` BEFORE any use —
    the fp-jitter fence: a sub-1e-6 wobble can never flip an attribution or a threshold test."""
    E_query = np.asarray(E_query, dtype=np.float64)
    E_cand = np.asarray(E_cand, dtype=np.float64)
    if E_query.ndim != 2 or E_cand.ndim != 2 or E_query.shape[1] != E_cand.shape[1]:
        raise ValueError(f"bad embedding shapes {E_query.shape} vs {E_cand.shape}")
    return np.round(E_query @ E_cand.T, decimals)


def _best_earlier_round_candidate(round_of, E, *, decimals):
    """Per event i: (best_idx[i], best_cos[i]) over all events of STRICTLY EARLIER rounds
    (the frozen CANDIDATE_RULE), argmax of the ROUNDED cosine, ties -> lowest index (np.argmax's
    first-max on the rounded values). Events with no earlier-round candidate get (-1, nan).
    Theta-independent — the threshold is applied by the caller, so calibration sweeps the grid
    without recomputing."""
    round_of = np.asarray(round_of)
    E = np.asarray(E)
    n = round_of.size
    if E.shape[0] != n:
        raise ValueError(f"round_of ({n}) and embeddings ({E.shape[0]}) misaligned")
    if n and np.any(np.diff(round_of) < 0):
        raise ValueError("round_of must be non-decreasing (stream order)")
    best_idx = np.full(n, -1, dtype=np.int64)
    best_cos = np.full(n, np.nan)
    for r in np.unique(round_of):
        members = np.flatnonzero(round_of == r)
        n_cand = int(np.searchsorted(round_of, r))   # strictly-earlier rounds = prefix (sorted)
        if n_cand == 0:
            continue
        C = rounded_cosines(E[members], E[:n_cand], decimals=decimals)
        best_idx[members] = np.argmax(C, axis=1)     # first max = lowest index (frozen tie rule)
        best_cos[members] = C[np.arange(members.size), best_idx[members]]
    return best_idx, best_cos


def attribute_similarity_parents(round_of, E, theta, *, spec=lps):
    """The frozen attribution rule -> (parent_idx, root_id) in stream order, satisfying
    post_reply_tree's invariants by construction (an earlier-round parent is an earlier index).
    parent(i) = argmax rounded-cosine over strictly-earlier-round events iff that rounded cosine
    >= theta (rounded theta comparison on rounded cosines); ties -> lowest index; else root."""
    best_idx, best_cos = _best_earlier_round_candidate(round_of, E, decimals=spec.COSINE_DECIMALS)
    theta = round(float(theta), spec.COSINE_DECIMALS)
    n = best_idx.size
    parent_idx = np.full(n, -1, dtype=np.int64)
    hit = ~np.isnan(best_cos) & (best_cos >= theta)
    parent_idx[hit] = best_idx[hit]
    root_id = np.arange(n, dtype=np.int64)
    for i in range(n):                                # forward pass valid: parent_idx[i] < i
        p = parent_idx[i]
        if p >= 0:
            root_id[i] = root_id[p]
    return parent_idx, root_id


@dataclass(frozen=True)
class CalibrationResult:
    """Banked output of the frozen calibration procedure (design §6). theta is the MEASURED
    argmax-J grid point; everything else is the recorded diagnostic surface."""
    theta: float
    tpr: float                  # at theta: attributed parent == true parent, over ALL true-edged children
    fpr: float                  # at theta: true roots receiving any attributed parent
    auc: float                  # pairwise rounded-cosine AUC, true-parent vs non-parent-candidate pairs
    j_curve: tuple              # ((theta, tpr, fpr, j), ...) over the full frozen grid
    same_round_ceiling: float   # fraction of true-edged children whose true parent is same-round
                                # (unreachable under CANDIDATE_RULE; caps TPR honestly; cannot
                                # move the argmax — an unreachable child is wrong at every theta)


def _stream_scores(parent_idx_true, round_of, E, *, spec):
    """Per-stream theta-independent score vectors for the pooled calibration. Returns
    (child_hit, child_cos, root_cos, unreachable, pos, neg): the argmax-candidate correctness and
    rounded-cosine per true-edged child, the best rounded-cosine per true root (-inf when no
    candidate exists), the per-child same-round-unreachable flags, and the AUC pair scores
    (true-parent vs non-parent-candidate). FAIL-CLOSED on empty/misaligned inputs."""
    parent_idx_true = np.asarray(parent_idx_true, dtype=np.int64)
    round_of = np.asarray(round_of)
    n = parent_idx_true.size
    if n == 0:
        raise ValueError("calibrate_theta: empty stream (fail-closed)")
    if round_of.size != n:
        raise ValueError("parent_idx_true and round_of misaligned")
    children = np.flatnonzero(parent_idx_true >= 0)
    roots = np.flatnonzero(parent_idx_true < 0)

    best_idx, best_cos = _best_earlier_round_candidate(round_of, E, decimals=spec.COSINE_DECIMALS)

    child_hit = best_idx[children] == parent_idx_true[children]        # same-round parent -> False
    child_cos = np.where(np.isnan(best_cos[children]), -np.inf, best_cos[children])
    root_cos = (np.where(np.isnan(best_cos[roots]), -np.inf, best_cos[roots])
                if roots.size else np.array([]))
    unreachable = (round_of[parent_idx_true[children]] >= round_of[children]
                   if children.size else np.array([], dtype=bool))

    # AUC pair scores (recorded diagnostic): deterministic, candidates never cross streams.
    pos, neg = [], []
    for i in range(n):
        n_cand = int(np.searchsorted(round_of, round_of[i]))
        if n_cand == 0:
            continue
        c = rounded_cosines(E[i:i + 1], E[:n_cand], decimals=spec.COSINE_DECIMALS)[0]
        p = parent_idx_true[i]
        if p >= 0 and p < n_cand:
            pos.append(c[p])
            neg.extend(np.delete(c, p))
        else:
            neg.extend(c)
    return child_hit, child_cos, root_cos, unreachable, pos, neg


def calibrate_theta_pooled(streams, *, spec=lps):
    """The frozen attribution-Youden procedure (design §6) over one or more streams whose
    candidate sets never cross stream boundaries (the three registered cohort windows). Pooled
    denominators: TPR over ALL true-edged children of every stream, FPR over ALL true roots.
    theta* = argmax J = TPR - FPR over theta_grid(); ties -> LARGEST theta (frozen: fewest
    manufactured edges). Positives/negatives DETERMINISTIC — no sampling anywhere. FAIL-CLOSED on
    an empty stream list or an empty pooled true-edge pool."""
    if not streams:
        raise ValueError("calibrate_theta_pooled: no streams (fail-closed)")
    hits, ccos, rcos, unre, pos, neg = [], [], [], [], [], []
    for parent_idx_true, round_of, E in streams:
        h, c, r, u, p, ng = _stream_scores(parent_idx_true, round_of, E, spec=spec)
        hits.append(h); ccos.append(c); rcos.append(r); unre.append(u)
        pos.extend(p); neg.extend(ng)
    child_hit = np.concatenate(hits) if hits else np.array([], dtype=bool)
    child_cos = np.concatenate(ccos)
    root_cos = np.concatenate(rcos)
    unreachable = np.concatenate(unre)
    if child_hit.size == 0:
        raise ValueError("calibrate_theta_pooled: no true edges to calibrate against (fail-closed)")
    same_round_ceiling = float(np.mean(unreachable))

    grid = theta_grid(spec)
    tpr_curve = np.array([np.mean(child_hit & (child_cos >= t)) for t in grid])
    fpr_curve = (np.array([np.mean(root_cos >= t) for t in grid])
                 if root_cos.size else np.zeros(grid.size))
    j_curve = tpr_curve - fpr_curve
    i_star = int(np.flatnonzero(j_curve == j_curve.max())[-1])         # ties -> LARGEST theta
    theta_star = float(grid[i_star])

    if pos and neg:
        scores = np.concatenate([np.asarray(pos), np.asarray(neg)])
        ranks = _midranks(scores)
        auc = float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                    / (len(pos) * len(neg)))
    else:
        auc = float("nan")

    return CalibrationResult(
        theta=theta_star, tpr=float(tpr_curve[i_star]), fpr=float(fpr_curve[i_star]), auc=auc,
        j_curve=tuple((float(t), float(a), float(b), float(j))
                      for t, a, b, j in zip(grid, tpr_curve, fpr_curve, j_curve)),
        same_round_ceiling=same_round_ceiling)


def calibrate_theta(parent_idx_true, round_of, E, *, spec=lps):
    """Single-stream convenience wrapper over the pooled procedure (identical by construction)."""
    res = calibrate_theta_pooled([(parent_idx_true, round_of, E)], spec=spec)
    return res


def attribution_rates_at_theta(parent_idx_true, round_of, E, theta, *, spec=lps):
    """(tpr, fpr) of the frozen attribution rule on ONE stream at a FIXED theta — the per-window
    diagnostic recorded alongside the pooled theta*."""
    child_hit, child_cos, root_cos, _, _, _ = _stream_scores(
        parent_idx_true, round_of, E, spec=spec)
    theta = round(float(theta), spec.COSINE_DECIMALS)
    if child_hit.size == 0:
        raise ValueError("attribution_rates_at_theta: no true edges in stream (fail-closed)")
    tpr = float(np.mean(child_hit & (child_cos >= theta)))
    fpr = float(np.mean(root_cos >= theta)) if root_cos.size else 0.0
    return tpr, fpr


def _midranks(x):
    """1-based midranks (average ranks on ties) — the Mann-Whitney AUC convention."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size, dtype=float)
    sx = x[order]
    i = 0
    while i < x.size:
        j = i
        while j + 1 < x.size and sx[j + 1] == sx[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks

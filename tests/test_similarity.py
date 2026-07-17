"""Fast synthetic-embedding tests for cascades.similarity (sub-inc-2 T4) — no torch, no model:
hand-built unit vectors exercise the frozen attribution rule and the calibration procedure on
planted ground truth. The @slow model-determinism tier lives in test_embedding_pin.py."""
import numpy as np
import pytest

from critaudit.cascades.extract import post_reply_tree
from critaudit.cascades.similarity import (
    CalibrationResult, attribute_similarity_parents, calibrate_theta, rounded_cosines, theta_grid)


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def test_theta_grid_frozen_shape():
    g = theta_grid()
    assert g[0] == 0.01 and g[-1] == 0.99
    assert g.size == 197                              # inclusive 0.01..0.99 step 0.005
    assert np.all((g > 0) & (g < 1))
    assert np.allclose(np.diff(g), 0.005)


def test_rounded_cosines_rounds_before_use():
    a = _unit([1.0, 1e-9])
    b = _unit([1.0, -1e-9])
    C = rounded_cosines(a[None, :], b[None, :])
    assert C[0, 0] == 1.0                             # sub-1e-6 jitter fenced off by rounding


def test_attribution_planted_parents_and_tree_feed():
    # rounds:   0    0    1        1      2
    # event 2 ~= event 0 (planted parent); event 3 orthogonal; event 4 ~= event 2's direction.
    E = np.stack([
        _unit([1, 0, 0]),
        _unit([0, 1, 0]),
        _unit([1, 0.05, 0]),                          # cos to e0 ~ 0.999
        _unit([0, 0, 1]),                             # far from everything earlier
        _unit([1, 0.08, 0]),                          # closest earlier = event 2 (round 1)
    ])
    round_of = np.array([0, 0, 1, 1, 2])
    parent_idx, root_id = attribute_similarity_parents(round_of, E, 0.8)
    assert parent_idx.tolist() == [-1, -1, 0, -1, 2]
    assert root_id.tolist() == [0, 1, 0, 3, 0]
    # Feeds the extractor without error (invariants hold by construction).
    av = post_reply_tree(round_of.astype(float), root_id, parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 1, 3]


def test_attribution_threshold_and_no_candidates():
    E = np.stack([_unit([1, 0]), _unit([0.9, 0.1])])
    round_of = np.array([0, 1])
    # theta above the pair cosine -> everything is a root; round-0 events always roots.
    parent_idx, root_id = attribute_similarity_parents(round_of, E, 0.9999)
    assert parent_idx.tolist() == [-1, -1] and root_id.tolist() == [0, 1]


def test_attribution_tie_breaks_to_lowest_index():
    E = np.stack([_unit([1, 0]), _unit([1, 0]), _unit([1, 0.01])])   # events 0,1 identical
    round_of = np.array([0, 0, 1])
    parent_idx, _ = attribute_similarity_parents(round_of, E, 0.5)
    assert parent_idx[2] == 0                          # rounded tie -> first (lowest) index


def test_attribution_deterministic():
    rng = np.random.default_rng(20260717)
    E = rng.normal(size=(40, 8))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    round_of = np.sort(rng.integers(0, 5, size=40))
    a1 = attribute_similarity_parents(round_of, E, 0.3)
    a2 = attribute_similarity_parents(round_of, E, 0.3)
    assert np.array_equal(a1[0], a2[0]) and np.array_equal(a1[1], a2[1])


def _planted_calibration_problem():
    """Roots in round 0 mutually ~orthogonal; each round-1 child IDENTICAL to its true parent
    (rounded cos 1.0); cross-pairs far below. J(theta)=1 on the whole grid above the cross-pair
    level, so ties->largest must select the LARGEST grid point (0.99)."""
    e0, e1, e2 = _unit([1, 0, 0]), _unit([0, 1, 0]), _unit([0, 0, 1])
    E = np.stack([e0, e1, e2, e0, e1])
    round_of = np.array([0, 0, 0, 1, 1])
    parent_idx_true = np.array([-1, -1, -1, 0, 1])
    return parent_idx_true, round_of, E


def test_calibrate_theta_planted_recovery_and_tie_rule():
    parent_idx_true, round_of, E = _planted_calibration_problem()
    res = calibrate_theta(parent_idx_true, round_of, E)
    assert isinstance(res, CalibrationResult)
    assert res.theta == 0.99                           # ties -> LARGEST theta (frozen)
    assert res.tpr == 1.0 and res.fpr == 0.0
    assert res.auc == 1.0                              # perfect separation, planted
    assert res.same_round_ceiling == 0.0
    assert len(res.j_curve) == theta_grid().size


def test_calibrate_theta_same_round_ceiling_caps_tpr():
    # One child's true parent is SAME-round -> unreachable under strictly_earlier_round: it is
    # wrong at every theta, capping TPR at 1/2 and recording the ceiling honestly.
    e0, e1, e2 = _unit([1, 0, 0]), _unit([0, 1, 0]), _unit([0, 0, 1])
    E = np.stack([e0, e1, e0, e2])
    round_of = np.array([0, 0, 1, 1])
    parent_idx_true = np.array([-1, -1, 0, 2])         # event 3's parent is same-round event 2
    res = calibrate_theta(parent_idx_true, round_of, E)
    assert res.same_round_ceiling == 0.5
    assert res.tpr <= 0.5


def test_calibrate_theta_fail_closed():
    _, round_of, E = _planted_calibration_problem()
    with pytest.raises(ValueError, match="no true edges"):
        calibrate_theta(np.full(5, -1), round_of, E)
    with pytest.raises(ValueError, match="empty"):
        calibrate_theta(np.array([]), np.array([]), np.empty((0, 3)))
    with pytest.raises(ValueError, match="misaligned"):
        calibrate_theta(np.array([-1, 0]), np.array([0]), E[:2])


def test_attribution_rejects_unsorted_rounds():
    E = np.eye(3)
    with pytest.raises(ValueError, match="non-decreasing"):
        attribute_similarity_parents(np.array([1, 0, 2]), E, 0.5)

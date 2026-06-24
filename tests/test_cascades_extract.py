import numpy as np
from critaudit.cascades import spec


def test_frozen_spec_surface():
    # The pre-registered constants are fenced + legible; a change here is unmistakably a spec change.
    assert spec.RECOVERY_THRESHOLD == 0.90
    assert spec.MERGE_POLICY.single_membership is True
    assert spec.MERGE_POLICY.merge_within_definition is False
    assert spec.MERGE_POLICY.bin_edge == "left-closed"
    assert len(spec.TAU_Q_GRID) >= 6 and spec.TAU_Q_GRID[0] < spec.TAU_Q_GRID[-1]
    # TAU_Q_K is None until Task 5's result-blind recovery freezes it.
    assert spec.TAU_Q_K is None or (0.0 < spec.TAU_Q_K)


from critaudit.cascades.ground_truth import labeled_stream
from critaudit.generators.powerlaw_hawkes import simulate_labeled


def test_ground_truth_is_a_pure_relay():
    # ground_truth packages; it does NOT recompute membership. Same seed -> root_id IDENTICAL to the
    # generator's (any divergence means ground_truth added cascade logic -> the recovery test goes circular).
    rng_a = np.random.default_rng(11)
    rng_b = np.random.default_rng(11)
    t_g, root_g, par_g = simulate_labeled(0.8, 4000.0, 0.05, 0.35, 1.7, rng_a)
    t, ibu, root, par = labeled_stream(0.8, 4000.0, 0.05, 0.35, 1.7, rng_b)
    assert np.array_equal(t, t_g) and np.array_equal(root, root_g) and np.array_equal(par, par_g)
    assert ibu.dtype == bool and ibu.all() and ibu.size == t.size


from critaudit.cascades.extract import (post_reply_tree, belief_update_sequence, bin_width,
                                         _avalanche_labels)
from critaudit.types import AvalancheSet


def test_post_reply_tree_recovers_known_trees():
    # Two planted trees: root 0 with children 1,2 (3 events, depth 2); root 3 alone (1 event, depth 1).
    times = np.array([0.0, 1.0, 2.0, 3.0])
    root_id = np.array([0, 0, 0, 3])
    parent_idx = np.array([-1, 0, 1, -1])         # 0<-1<-2 chain (depth 3) ; 3 immigrant
    av = post_reply_tree(times, root_id, parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 3]
    assert sorted(av.durations.tolist()) == [1, 3]   # chain depth 3 ; singleton depth 1


def test_belief_update_binning_segments_and_durations():
    # events at t = 0,1,2 (one burst), then a long gap, then 100,101 (second burst). dt=3 -> 2 avalanches.
    times = np.array([0.0, 1.0, 2.0, 100.0, 101.0])
    ibu = np.ones(5, bool)
    av = belief_update_sequence(times, ibu, dt=3.0)
    assert sorted(av.sizes.tolist()) == [2, 3]
    assert (av.durations >= 1).all()


def test_merge_policy_planted_two_clusters_straddling_dt():
    # INDEPENDENT correct answer (planted): two 2-event clusters whose internal span is ~1.0, separated
    # by gap G. With dt=2.0: G=1.0 (< dt) -> MERGE into one (truth: too close to resolve); G=10.0 (>> dt)
    # -> SEPARATE. The planted truth, not the policy, defines correct.
    near = np.array([0.0, 1.0, 2.0, 3.0])                      # gaps all 1.0 -> one run at dt=2
    lab_near = _avalanche_labels(near, dt=2.0)
    assert len(set(lab_near.tolist())) == 1                    # merged (correct: unresolvable at dt=2)
    far = np.array([0.0, 1.0, 11.0, 12.0])                     # gap 10 between clusters
    lab_far = _avalanche_labels(far, dt=2.0)
    assert len(set(lab_far.tolist())) == 2                     # separated (correct)


def test_post_reply_tree_recovers_critical_exponent_via_existing_modules():
    # END-TO-END bridge: a near-critical (n=0.99) labeled stream -> trees -> AvalancheSet -> existing CSN
    # gives a size exponent in the critical-branching neighbourhood (tau ~ 1.5). n=0.99 (vs a slacker 0.97)
    # widens the power-law regime so CSN robustly finds xmin~1 and tau~1.58 — verified 10/10 seeds in this
    # band, std 0.03 (at 0.97, ~1/10 seeds hit a high-xmin CSN outlier ~2.3); band kept loose for finite-N.
    from critaudit.cascades.ground_truth import labeled_stream
    from critaudit.powerlaw.csn import _fit
    t, ibu, root, par = labeled_stream(0.99, 30000.0, 0.05, 0.35, 1.7, np.random.default_rng(5))
    av = post_reply_tree(t, root, par)
    tau = float(_fit(av.sizes).power_law.alpha)
    assert 1.2 < tau < 2.2                                     # critical-branching neighbourhood


def test_belief_update_bridge_is_calibration_blocked_but_plumbing_sound():
    # Task 6 #3 bridge, ADAPTED to the MEASURED state. #3 was to bridge to scaling.exponents through the
    # FROZEN TAU_Q_K; that freeze is BLOCKED on the heavy-tail market regime (a #3-recoverability finding —
    # see test_cascades_calibrate + DECISIONS.md 2026-06-24), so TAU_Q_K is None. We assert the measured
    # state (no frozen knob) AND that the extractor PLUMBING is intact: given an explicit (unfrozen) dt,
    # #3 -> AvalancheSet -> scaling.exponents runs and returns finite exponents. What is blocked is the
    # CALIBRATION, not the code path.
    from critaudit.cascades.ground_truth import labeled_stream
    from critaudit.cascades.extract import belief_update_sequence, bin_width
    from critaudit.cascades import spec
    from critaudit.scaling.crackling import exponents
    assert spec.TAU_Q_K is None                       # calibration-blocked: no frozen knob to bridge through
    t, ibu, root, par = labeled_stream(0.85, 60000.0, 0.002, 0.35, 1.7, np.random.default_rng(9))
    dt = bin_width(t, 1.0)                             # provisional unfrozen dt (one median gap) — PLUMBING ONLY, not a calibrated knob
    av = belief_update_sequence(t, ibu, dt)
    tau, alpha, inv = exponents(av)
    assert np.isfinite(tau) and np.isfinite(alpha)    # the #3 -> scaling bridge is wired; only the knob is unfrozen
    assert av.sizes.min() >= 1 and av.durations.min() >= 1

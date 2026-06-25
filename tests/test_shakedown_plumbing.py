import numpy as np
import pytest

from critaudit.sim.controls import spec
from critaudit.sim.controls.deffuant import simulate_labeled, AbmRun
from critaudit.hawkes.gate import certify_near_critical
from critaudit.experiments.shakedown import run_pipeline, ShakedownResult


def _tiny_run():
    # @fast plumbing fixture: a NEAR-CRITICAL run (eps=EPS_CRIT) is depth-diverse — a power-law spread of
    # tree sizes populates the >=4 depth-bins x >=50 avalanches the coarse 1/snz curvature estimator needs
    # (a deep-supercritical run's giant cascades all reach one depth -> inv_snz nan-BY-DESIGN, not a bug).
    # Small enough to run fast; the discrimination plants (spec.EPS_*) are exercised in the @slow Task 7.
    return simulate_labeled(eps=spec.EPS_CRIT, horizon=300.0, mu_news=3.0, N=120, k_reach=spec.K_REACH,
                            mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS, c=spec.KERNEL_C,
                            rng=np.random.default_rng(1))


@pytest.fixture(scope="module")
def tiny_run():
    return _tiny_run()


@pytest.fixture(scope="module")
def res(tiny_run):
    # small n_boot: the CSN goodness-of-fit bootstrap is a reporting statistic (res.pl is never read as
    # science here); the wiring is what this @fast test locks. Task 7 / production use the default 200.
    return run_pipeline(tiny_run, n_match=1200, csn_rng=np.random.default_rng(0), n_boot=10)


def test_pipeline_runs_end_to_end_finite(tiny_run, res):
    assert isinstance(res, ShakedownResult)
    # every arm returns finite/well-formed output (incl. the CSN power-law exponent and the coarse 1/snz)
    for v in (res.gate.peak, res.gate.peak04, res.gate.migrated, res.tau, res.alpha,
              res.inv_snz, res.n_tree, res.chi, res.pl.exponent):
        assert np.isfinite(v)
    assert isinstance(res.gate.identified, bool)
    assert res.av.sizes.sum() == tiny_run.times.size      # scaling arm consumed the full stream
    assert res.n_events == min(1200, tiny_run.times.size)  # gate read N-matched


def test_pipeline_golden_stable_per_seed(tiny_run, res):
    # plumbing golden: the wiring (not the science) is deterministic for a fixed seed AND run_pipeline
    # routes the gate faithfully — its N-matched gate.peak equals a direct certify_near_critical call on
    # the same first-n_match window. (Generator determinism itself is locked in test_deffuant.py.)
    t = tiny_run.times[:1200]
    assert res.gate.peak == certify_near_critical(t, float(t[-1])).peak


def test_run_pipeline_rejects_empty_stream():
    # a mis-sized plant (mu_news*horizon too small → zero immigrants) yields an empty AbmRun; run_pipeline
    # must fail CLOSED with a clear message (mirroring anchors.n_tree), not an opaque IndexError on t[-1].
    empty = np.empty(0, dtype=np.int64)
    run = AbmRun(times=np.empty(0), root_id=empty, parent_idx=empty,
                 belief_traj=np.empty(0), successes=0)
    with pytest.raises(ValueError):
        run_pipeline(run, n_match=1200)

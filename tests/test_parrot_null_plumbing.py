import numpy as np
import pytest
from critaudit.types import AvalancheSet
from critaudit.sim.controls.deffuant import AbmRun
from critaudit.experiments.parrot_null import (read_tau_arm, ArmRead, run_parrot_null, _read_columns,
                                               ColumnRead, ParrotNullResult)
from critaudit.sim.controls import parrot_spec as ps

# small substrate keeps the fast path fast; overrides are SPEED-ONLY (plumbing checks well-formedness,
# determinism and invariants — NOT the frozen separation criterion, which lives in the @slow cohort).
SMALL = dict(N=80, horizon=160.0, mu_news=0.5, n_match=500, n_boot=20,
             window_sizes=(160 / 20.0, 160 / 5.0))


def test_read_tau_arm_degenerate_is_no_power_law():
    # collapsed null: every avalanche size 1 -> no power law admissible, no powerlaw.Fit call
    av = AvalancheSet(sizes=np.ones(500, np.int64), durations=np.ones(500, np.int64))
    arm = read_tau_arm(av, rng=np.random.default_rng(0), n_boot=20)
    assert isinstance(arm, ArmRead)
    assert arm.passes is False
    assert np.isnan(arm.tau) and np.isnan(arm.p_boot)
    assert np.isnan(arm.alpha) and np.isnan(arm.inv_snz) and np.isnan(arm.delta)


def test_read_tau_arm_constant_size_ge2_is_no_power_law():
    # constant sizes >= 2 bypass a `sizes.max() < 2` guard but admit no power law (and would crash
    # powerlaw.Fit on constant data) -> the `unique(sizes) < 2` guard catches them
    av = AvalancheSet(sizes=np.full(400, 3, np.int64), durations=np.full(400, 2, np.int64))
    arm = read_tau_arm(av, rng=np.random.default_rng(0), n_boot=20)
    assert arm.passes is False and np.isnan(arm.tau)


# n_boot is a SPEED knob here: these plumbing tests assert only well-formedness (finite τ / bool verdict /
# nan-where-undefined), which is independent of the CSN bootstrap depth — so a token n_boot keeps the fast
# lane fast (the full 200-replicate bootstrap is the @slow cohort's job). The heavy tail is also CAPPED
# (raw zipf max ~3e5 makes the discrete xmin sweep slow); capping exercises the same code path far cheaper.
_FIT_NBOOT = 3
_SIZES = np.minimum(np.random.default_rng(0).zipf(2.0, size=800).astype(np.int64), 300)


def test_read_tau_arm_constant_durations_keeps_tau_drops_crackling():
    # varied sizes but CONSTANT durations: the size power law still stands, but the duration fit inside
    # exponents() would crash -> the crackling trio (alpha/inv_snz/delta) is nan WITHOUT crashing
    av = AvalancheSet(sizes=_SIZES, durations=np.ones_like(_SIZES))
    arm = read_tau_arm(av, rng=np.random.default_rng(1), n_boot=_FIT_NBOOT)
    assert isinstance(arm.passes, bool) and np.isfinite(arm.tau)
    assert np.isnan(arm.alpha) and np.isnan(arm.inv_snz) and np.isnan(arm.delta)


def test_read_tau_arm_nondegenerate_returns_finite_arm():
    # varied sizes AND durations -> the full crackling arm is computed
    durations = np.maximum(1, np.ceil(np.log2(_SIZES + 1)).astype(np.int64))  # depth ~ log(size)
    av = AvalancheSet(sizes=_SIZES, durations=durations)
    arm = read_tau_arm(av, rng=np.random.default_rng(1), n_boot=_FIT_NBOOT)
    assert isinstance(arm.passes, bool)
    assert np.isfinite(arm.tau) and np.isfinite(arm.alpha)   # durations vary -> crackling trio computed


def test_read_columns_empty_stream_raises():
    # a zero-event run is fail-closed (mirrors shakedown.run_pipeline) rather than an opaque t[-1] IndexError
    empty = np.empty(0, np.int64)
    run0 = AbmRun(times=np.empty(0, float), root_id=empty, parent_idx=empty,
                  belief_traj=np.empty(0, float), successes=0)
    with pytest.raises(ValueError):
        _read_columns(run0, n_match=500, rng=np.random.default_rng(0), n_boot=5,
                      horizon=160.0, window_sizes=(8.0, 32.0))


def _finite_columnread(c):
    assert isinstance(c, ColumnRead)
    assert isinstance(c.tau_passes, bool) and isinstance(c.gate_identified, bool)
    for v in (c.n_struct, c.burstiness, c.n_emit, c.gate_peak, c.gate_migrated):
        assert np.isfinite(v)
    for v in (c.tau, c.p_boot, c.alpha, c.inv_snz, c.crackling_delta):
        assert isinstance(v, float)   # col-1 arm values: finite on the coupled side, nan on the degenerate null
    assert c.fano.shape == (2,)


@pytest.fixture(scope="module")
def small_res():
    # shared once: the two rig tests below read byte-identical (seed=3, SMALL) output
    return run_parrot_null(seed=3, **SMALL)


def test_rig_runs_finite_and_wellformed(small_res):
    assert isinstance(small_res, ParrotNullResult)
    _finite_columnread(small_res.coupled)
    _finite_columnread(small_res.parrot)


def test_rig_positive_control_gates_hold_on_parrot(small_res):
    assert small_res.tripwire_ok is True          # parrot.successes == 0 (upstream-enforced)
    assert small_res.struct_ok is True            # n_struct(parrot) == 0.0 (rig fail-closes otherwise)
    assert small_res.parrot.n_struct == 0.0
    assert small_res.parrot.n_emit == 0.0
    assert small_res.parrot.tau_passes is False   # collapsed null -> no power law (null-confirmation)
    assert np.isnan(small_res.parrot.crackling_delta)   # degenerate null -> crackling undefined


def test_rig_is_deterministic_under_seed(small_res):
    # reuse the module fixture (seed=3) as run A; only run B fresh — one rig instead of two
    again = run_parrot_null(seed=3, **SMALL)
    assert (small_res.parrot.n_struct, small_res.parrot.n_emit) == (again.parrot.n_struct, again.parrot.n_emit)
    assert small_res.coupled.n_emit == again.coupled.n_emit
    assert np.array_equal(small_res.coupled.fano, again.coupled.fano)

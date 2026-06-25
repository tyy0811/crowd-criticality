import numpy as np
import pytest
from critaudit.types import AvalancheSet
from critaudit.experiments.parrot_null import (read_tau_arm, run_parrot_null,
                                               ColumnRead, ParrotNullResult)
from critaudit.sim.controls import parrot_spec as ps

# small substrate keeps the fast path fast; overrides are SPEED-ONLY (plumbing checks well-formedness,
# determinism and invariants — NOT the frozen separation criterion, which lives in the @slow cohort).
SMALL = dict(N=80, horizon=160.0, mu_news=0.5, n_match=500, n_boot=20,
             window_sizes=(160 / 20.0, 160 / 5.0))


def test_read_tau_arm_degenerate_is_no_power_law():
    # collapsed null: every avalanche size 1 -> no power law admissible, no powerlaw.Fit call
    av = AvalancheSet(sizes=np.ones(500, np.int64), durations=np.ones(500, np.int64))
    passes, tau, p_boot = read_tau_arm(av, rng=np.random.default_rng(0), n_boot=20)
    assert passes is False
    assert np.isnan(tau) and np.isnan(p_boot)


def test_read_tau_arm_nondegenerate_returns_finite_tau():
    # a varied size distribution -> the fit runs and returns a finite tau and a bool verdict.
    # durations must VARY too: read_tau_arm -> exponents() also fits durations, and a constant
    # durations array crashes powerlaw's xmin search ("no data points in range"). Real avalanche
    # sets always have generation-depth durations that grow with size (a size>1 tree has depth>=2);
    # only the size-1 collapsed case has constant durations, and that path is the degenerate guard.
    rng = np.random.default_rng(0)
    sizes = (rng.zipf(2.0, size=3000)).astype(np.int64)   # heavy-tailed integer sizes, max >> 1
    durations = np.maximum(1, np.ceil(np.log2(sizes + 1)).astype(np.int64))  # depth ~ log(size)
    av = AvalancheSet(sizes=sizes, durations=durations)
    passes, tau, p_boot = read_tau_arm(av, rng=np.random.default_rng(1), n_boot=20)
    assert isinstance(passes, bool)
    assert np.isfinite(tau)


def _finite_columnread(c):
    assert isinstance(c, ColumnRead)
    assert isinstance(c.tau_passes, bool) and isinstance(c.gate_identified, bool)
    for v in (c.n_struct, c.burstiness, c.n_emit, c.gate_peak, c.gate_migrated):
        assert np.isfinite(v)
    assert c.fano.shape == (2,)


def test_rig_runs_finite_and_wellformed():
    res = run_parrot_null(seed=3, **SMALL)
    assert isinstance(res, ParrotNullResult)
    _finite_columnread(res.coupled)
    _finite_columnread(res.parrot)


def test_rig_positive_control_gates_hold_on_parrot():
    res = run_parrot_null(seed=3, **SMALL)
    assert res.tripwire_ok is True          # parrot.successes == 0
    assert res.struct_ok is True            # n_struct(parrot) == 0.0
    assert res.parrot.n_struct == 0.0
    assert res.parrot.n_emit == 0.0
    assert res.parrot.tau_passes is False   # collapsed null -> no power law (null-confirmation)


def test_rig_is_deterministic_under_seed():
    a = run_parrot_null(seed=5, **SMALL)
    b = run_parrot_null(seed=5, **SMALL)
    assert (a.parrot.n_struct, a.parrot.n_emit) == (b.parrot.n_struct, b.parrot.n_emit)
    assert a.coupled.n_emit == b.coupled.n_emit
    assert np.array_equal(a.coupled.fano, b.coupled.fano)

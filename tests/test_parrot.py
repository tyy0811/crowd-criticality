import numpy as np

from critaudit.sim.controls import parrot_spec as ps
from critaudit.sim.controls import spec as cs
from critaudit.sim.controls.parrot import simulate_parrot


def _parrot(seed, **over):
    kw = dict(horizon=200.0, mu_news=0.5, N=80, k_reach=4, mu_step=0.5,
              kernel_eps=0.35, c=1.7, rng=np.random.default_rng(seed))
    kw.update(over)
    return simulate_parrot(**kw)


def test_parrot_spec_frozen_surface():
    # the collapse IS the zero confidence bound — definitional, not a tunable
    assert ps.BELIEF_FREE_EPS == 0.0
    # reference plant is CRIT, wired to the increment-3 frozen constants (not redefined)
    assert ps.REFERENCE_EPS == cs.EPS_CRIT
    assert ps.REFERENCE_MU_NEWS == cs.MU_NEWS_CRIT
    # shared substrate is held identical to the coupled control
    assert (ps.N_AGENTS, ps.K_REACH, ps.MU_STEP) == (cs.N_AGENTS, cs.K_REACH, cs.MU_STEP)
    assert (ps.KERNEL_EPS, ps.KERNEL_C, ps.HORIZON) == (cs.KERNEL_EPS, cs.KERNEL_C, cs.HORIZON)
    # frozen null-confirmation readings are present and Poisson/theory-anchored
    assert ps.TAU_NULL_PASSES is False
    assert ps.N_EMIT_NULL == 0.0
    assert 0.0 < ps.BURST_NULL_HI < 0.5          # Poisson B≈0 + finite-sample tol
    assert ps.FANO_NULL_LO < 1.0 < ps.FANO_NULL_HI  # Poisson F≈1 band
    assert ps.N_EMIT_REF_MIN > 0.0               # coupled CRIT n_emit crosses toward 1
    assert ps.N_EMIT_REF_MIN == cs.N_TREE_SUB    # the floor IS incr-3's subcritical bound (theory-anchored)
    assert len(ps.FANO_WINDOW_SIZES) >= 2         # scale-resolved
    # the reference plant is named (documents the contrast plant identity)
    assert ps.REFERENCE_PLANT == "CRIT"
    # sweep-side interface band: frozen-but-not-consumed in the prototype, LOCKED here so its construction
    # parameters cannot drift / be widened after seeing where a decoupled run lands (the anti-p-hacking
    # freeze the §8 comment promises is otherwise unenforced — documentation is not verification)
    assert ps.SWEEP_BAND_SEEDS == 64
    assert ps.SWEEP_BAND_QUANTILE == 0.95
    assert ps.SWEEP_BAND_EDGE == "max"


def test_parrot_collapses_to_immigrant_only():
    run = _parrot(1)
    assert run.times.size > 0                         # the news driver still fires
    assert run.successes == 0                         # no |Δx|<eps success ever fires (collapse)
    assert np.all(run.parent_idx == -1)               # every event is an immigrant (no offspring edge)
    assert np.array_equal(run.root_id, np.arange(run.times.size))  # each event its own root
    assert np.all(np.diff(run.times) > 0)             # sorted, strictly increasing


def test_parrot_is_deterministic_under_seed():
    a = _parrot(7)
    b = _parrot(7)
    assert np.array_equal(a.times, b.times)
    assert np.array_equal(a.parent_idx, b.parent_idx)
    assert a.successes == b.successes == 0

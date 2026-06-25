from critaudit.sim.controls import parrot_spec as ps
from critaudit.sim.controls import spec as cs


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
    assert len(ps.FANO_WINDOW_SIZES) >= 2         # scale-resolved

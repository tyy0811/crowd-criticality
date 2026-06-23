import numpy as np

from critaudit.hawkes.gate import (self_excitation, comp_coef, profile_ll, certify_near_critical,
                                    GateVerdict, K_FLEX, N_GRID, EPS_FULL, C_GRID, EPS_MINS, MIGRATE_TOL)
from critaudit.hawkes.mu_t import fit_mu_only
from critaudit.hawkes.binned import PowerLawKernel
from critaudit.generators import powerlaw_hawkes
from critaudit.generators.hawkes_sim import simulate as exp_simulate


def test_cached_profile_ll_matches_fit_mu_only_bit_close():
    # THE load-bearing invariant: the s-cached profile == the tested estimator (was |Δ|=0). Golden.
    t = powerlaw_hawkes.simulate(0.85, 3000.0, 0.4, 0.35, 1.7, np.random.default_rng(0))
    T = float(t[-1])
    worst = 0.0
    for eps, c, n in [(0.4, 2.0, 0.75), (0.2, 1.0, 0.90), (0.7, 0.5, 0.45), (0.1, 2.0, 1.05)]:
        a, betas = PowerLawKernel(eps=eps, c=c).soe()
        s = self_excitation(t, a, betas); cc = comp_coef(t, T, a, betas)
        fast = profile_ll(t, T, s, cc, n, K_FLEX)
        ref = fit_mu_only(t, T, PowerLawKernel(eps=eps, c=c), n, K_FLEX)["ll"]
        worst = max(worst, abs(fast - ref))
    assert worst < 1e-3


def test_gate_identifies_clean_stationary_powerlaw():
    # A clean STATIONARY power-law stream (no ramp) is IDENTIFIED at an interior subcritical peak. NOTE:
    # the flexible μ(K=12) baseline UNDER-estimates n on stationary data (planted 0.85 -> recovered ~0.6;
    # the documented over-flexibility, mu_t.py docstring), so this does NOT verify near-critical recovery
    # (the gate is a migration detector, not an n estimator) — it verifies stationary data stays interior
    # and does not migrate. The lower bound guards against the peak collapsing to the grid floor.
    t = powerlaw_hawkes.simulate(0.85, 4000.0, 0.5, 0.35, 1.7, np.random.default_rng(3))
    v = certify_near_critical(t, float(t[-1]))
    assert isinstance(v, GateVerdict)
    assert v.identified and 0.45 <= v.peak < 1.0


def test_gate_does_not_false_flag_clean_crosskernel_stationary_data():
    # SPECIFICITY: migration is driven by NON-STATIONARITY, not kernel misspecification. A clean STATIONARY
    # stream — even from the WRONG (exp) kernel — is fit at a stable interior n (measured: peak 0.6), NOT
    # false-flagged as degenerate. The gate's MIGRATION positive control is on RAMPED data, in
    # tests/test_gate_specificity.py (seed 5 -> peak 1.05); stationary wrong-kernel data must NOT migrate.
    # (peak_constrained<=peak is exercised where it BINDS — on a migrated case — in test_gate_specificity.)
    es = exp_simulate(0.6, 4000.0, mu=0.5, beta=1.0, rng=np.random.default_rng(4))
    v = certify_near_critical(es.times, float(es.times[-1]))
    assert v.identified and v.peak < 1.0


def test_frozen_gate_parameters():
    # FREEZE the spec constants the decision rule and every recorded golden depend on. A retune (e.g.
    # MIGRATE_TOL 0.15->0.25, or a grid change) is then a deliberate, reviewable diff — not a silent one.
    # (The rule's APPLICATION — identified iff |migrated|<MIGRATE_TOL and peak<1 — is exercised by the real
    # certify_near_critical calls in the other gate tests and in test_gate_specificity.)
    assert MIGRATE_TOL == 0.15 and K_FLEX == 12
    assert N_GRID == [0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20]
    assert EPS_FULL == [0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.1]
    assert C_GRID == [0.5, 1.0, 2.0] and EPS_MINS == [0.4, 0.2, 0.1, 0.05, 0.02]

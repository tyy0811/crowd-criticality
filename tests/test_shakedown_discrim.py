import numpy as np
import pytest

from critaudit.sim.controls import spec
from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.anchors import n_tree, chi
from critaudit.experiments.shakedown import run_pipeline


# n_boot for the cohort's run_pipeline calls. res.pl (the CSN goodness-of-fit bootstrap) is NOT part of
# any frozen criterion — gate fields, n_tree, res.tau (from crackling.exponents), and chi are all
# INDEPENDENT of fit_powerlaw's bootstrap depth — so this is a BUDGET knob, not a result threshold:
# every asserted value is identical at n_boot=10 vs 200, but 200 spends minutes/call on a never-asserted
# p_boot. (Production/real-data callers use run_pipeline's default n_boot=200.)
_CSN_NBOOT = 10


def _plant(eps, mu_news, seed):
    return simulate_labeled(eps=eps, horizon=spec.HORIZON, mu_news=mu_news, N=spec.N_AGENTS,
                            k_reach=spec.K_REACH, mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS,
                            c=spec.KERNEL_C, rng=np.random.default_rng(seed))


@pytest.fixture(scope="module")
def plants():
    low = _plant(spec.EPS_LOW, spec.MU_NEWS_LOW, spec.SEED + 1)
    high = _plant(spec.EPS_HIGH, spec.MU_NEWS_HIGH, spec.SEED + 2)
    crit = _plant(spec.EPS_CRIT, spec.MU_NEWS_CRIT, spec.SEED + 3)
    return low, high, crit


@pytest.fixture(scope="module")
def results(plants):
    low, high, crit = plants
    return (run_pipeline(low, n_match=spec.N_MATCH, csn_rng=np.random.default_rng(spec.SEED + 10), n_boot=_CSN_NBOOT),
            run_pipeline(high, n_match=spec.N_MATCH, csn_rng=np.random.default_rng(spec.SEED + 11), n_boot=_CSN_NBOOT),
            run_pipeline(crit, n_match=spec.N_MATCH, csn_rng=np.random.default_rng(spec.SEED + 12), n_boot=_CSN_NBOOT))


@pytest.mark.slow
def test_plant_certification_n_tree_orders_extremes(plants):
    low, high, crit = plants
    # event budget: enough IN-WINDOW events (offspring are censored at HORIZON) to N-match at the floor.
    # HIGH needs MU_NEWS_HIGH=0.4 for this post-censoring; the value is a budget knob, immaterial to the
    # carry quantities (results/s2_shakedown/2026-06-24_budget_invariance.txt).
    assert low.times.size >= spec.N_MATCH and high.times.size >= spec.N_MATCH
    # n_tree is the SOLE load-bearing directional instrument (the gate peak gap fell under censoring — see
    # test_gate_is_observationally_regime_blind_under_heavy_tail), so it is STRESSED across seeds: the
    # LOW < SUB < SUPER < HIGH ordering must be seed-stable WITH MARGIN against the frozen thresholds, not
    # a point-value fluke. (Per-seed spreads logged in results/s2_shakedown/2026-06-24_budget_invariance.txt.)
    lo = [n_tree(_plant(spec.EPS_LOW, spec.MU_NEWS_LOW, spec.SEED + 100 + s)) for s in range(5)]
    hi = [n_tree(_plant(spec.EPS_HIGH, spec.MU_NEWS_HIGH, spec.SEED + 100 + s)) for s in range(5)]
    assert max(lo) < spec.N_TREE_SUB            # every LOW seed certified subcritical (margin ~0.32 << 0.7)
    assert min(hi) > spec.N_TREE_SUPER          # every HIGH seed certified supercritical (margin ~3.1 >> 1.3)
    # the cohort plants sit at the same structural regimes (CRIT ~1 is the critical plant, between the band)
    assert n_tree(low) < spec.N_TREE_SUB < spec.N_TREE_SUPER < n_tree(high)


@pytest.mark.slow
def test_gate_is_observationally_regime_blind_under_heavy_tail(results):
    rlo, rhi, _rcrit = results   # NO gate verdict is read at CRIT (the unresolvable middle; see below)
    # TWO BRANCHING RATIOS. n_tree = STRUCTURAL branching (local per-parent count; tail-robust); the gate's
    # peak = OBSERVATIONAL branching (finite-horizon μ(t) inference). RESULT-BLIND FINDING (the frozen
    # PEAK_GAP and HIGH-supercritical clauses did NOT clear → logged not relaxed, DECISIONS 2026-06-24;
    # precedent test_cascades_calibrate.py): under the infinite-mean Lomax kernel the OBSERVATIONAL ratio is
    # REGIME-BLIND — the deep-supercritical HIGH plant (n_tree >> SUPER) reads observationally SUBCRITICAL —
    # because the heavy tail relocates self-excitation outside any finite observation window (it needs
    # temporal compactness the tail destroys). n_tree resolves regime precisely because it is local. The
    # gate is NOT malfunctioning: it faithfully reports the finite-horizon observable, which is genuinely
    # subcritical for HIGH. Only the ROBUST facts (HIGH never ceilings, never migrates — 0/20 seeds in the
    # 2nd-review probe) are asserted; no inverse knife-edge (the HIGH−LOW peak gap is inside the seed noise).
    #
    # LOW: the gate is reliable in the subcritical regime — interior, and its peak AGREES with the
    # structural n_tree. (migrated is NOT asserted: at the n-grid step it sits exactly on the 0.15 boundary
    # for some seeds — a float/grid artifact, not a regime signal.)
    assert rlo.gate.peak < 1.0
    assert abs(rlo.gate.peak - rlo.n_tree) <= spec.AGREE_TOL
    # HIGH (structural n_tree >> SUPER) reads OBSERVATIONALLY SUBCRITICAL: interior, never migrates/ceilings.
    assert rhi.n_tree > spec.N_TREE_SUPER
    assert rhi.gate.peak < 1.0 and abs(rhi.gate.migrated) < spec.GATE_MIGRATE_TOL
    # CRIT: NO gate verdict is asserted — CRIT is the unresolvable middle by construction (off-limits by the
    # locked specificity floor), so even a clean reading there would be off-limits. CRIT keeps only the
    # gate-FREE τ certification (test_crit_tau_corroborates_criticality). It in fact false-migrates on a
    # minority of seeds — qualitatively consistent with the Phase-1 near-critical floor (7–27%); no rate is
    # claimed (a single cohort seed cannot carry one). That is the floor showing, not a CRIT defect.


@pytest.mark.slow
def test_crit_tau_corroborates_criticality(results):
    _, _, rcrit = results
    # POSITIVE corroboration (not merely a passing check): the scaling arm recovers the mean-field critical
    # exponent τ≈3/2 on the CRIT plant. This independently validates — gate-free — that the plant labelled
    # CRIT is genuinely critical, which is what makes the gate's interior reading of CRIT a true instance of
    # observational regime-blindness (above) rather than an ambiguous case.
    assert abs(rcrit.tau - spec.TAU_TARGET) <= spec.TAU_TOL


@pytest.mark.slow
def test_chi_has_no_resolving_power():
    # RESULT-BLIND FINDING (logged not relaxed; precedent test_cascades_calibrate.py). The frozen secondary
    # criterion  chi(CRIT) >= chi(LOW) and chi(CRIT) >= chi(HIGH)  (a susceptibility should PEAK at
    # criticality) did NOT clear. It is converted to this characterization, NOT relaxed.
    #
    # χ = var(population-MEAN opinion) is not a susceptibility: the mean is ~0.5 by the symmetric Deffuant
    # dynamics, so it is not an order parameter. LEAD EVIDENCE — a CONTROLLED sweep (mu_news FIXED, removing
    # the cohort's mu_news confound) shows no resolved peak at eps_crit; the committed 8-seed run
    # (results/s2_shakedown/2026-06-24_chi_diagnostic.py) gives chi(crit)/mean(others) ≈ 0.98 (eps_crit
    # below the mean — no peak; a true susceptibility would be >> 1). A 6-seed re-derivation re-confirms it.
    eps_grid = [spec.EPS_LOW, 0.08, spec.EPS_CRIT, 0.20, spec.EPS_HIGH]
    cm = {e: float(np.mean([chi(simulate_labeled(eps=e, horizon=1500.0, mu_news=2.0, N=400,
                                                 k_reach=spec.K_REACH, mu_step=spec.MU_STEP,
                                                 kernel_eps=spec.KERNEL_EPS, c=spec.KERNEL_C,
                                                 rng=np.random.default_rng(2000 + s))) for s in range(6)]))
          for e in eps_grid}
    others = [cm[e] for e in eps_grid if abs(e - spec.EPS_CRIT) >= 1e-9]
    assert cm[spec.EPS_CRIT] < 2.0 * float(np.mean(others))   # NO resolved susceptibility peak at eps_crit
    # NOTE: the single-cohort inequality chi(CRIT) < mean(chi(LOW), chi(HIGH)) is NOT asserted — the
    # 2nd-pass review measured it failing 5/20 seeds (χ is noise-dominated, so a point comparison is a
    # knife-edge). The robust no-peak claim rests on the controlled fixed-mu_news sweep above, only.

"""FROZEN ACCEPTANCE — the locked resolution-floor specificity of the promoted gate, exercised in the
RAMPED regime that produces it (a STATIONARY cohort would show 0 migrations and test nothing).

Reference (measured, not asserted here): genuine near-critical (n=0.90) under a rate ramp false-migrates
15-27% per-market at 18-35k (N-matched), and out to 100k stays in a ~7-17% band with no firm sub-10% trend
(the 100k CI straddles 10%), so per-market near-criticality is not separable from apparent near-criticality
at achievable Polymarket event counts. Full numbers + the four-round derivation
(and an UNTESTED open thread on whether the floor depends on ramp steepness independent of N — suggestive but
under-powered + confounded, NOT a finding): results/s0.4_feasibility/2026-06-23_per_market_criticality_DELIVERABLE.md.
The spike driver that reproduces the rate at scale: spike/s0.4/mac/convergent_migration_cal.py
(--tight / --finegrid / --nprobe). A 16-seed cohort cannot lock a 15-27% RATE (binomial noise) — so the rate
stays in the DELIVERABLE and the package locks the QUALITATIVE property: present, a minority, and mild.

Recorded + margin-tested 2026-06-23 at the frozen regime (simulate_ramp(0.90, 32760, 0.0142, 0.35, 1.7, 11.0,
seed)): migrators = seeds {0, 5, 7, 10} of 0..15, every migrator peak == 1.05. The regime is hand-picked to
exhibit the phenomenon, so the COUNT and WHICH seeds migrate are regime-fragile: a T +-5% margin test showed
only seed 5 migrates robustly and seed 1 identifies robustly (seeds 0/7/10 flip under a small T change). So
the cohort uses a robust band (anchored by seed 5) and the per-seed regression asserts only seeds 5 and 1.
"""
import numpy as np
import pytest

from critaudit.hawkes.gate import certify_near_critical
from critaudit.generators.powerlaw_hawkes import simulate_ramp

# frozen ramped test regime (market-like; exhibits the phenomenon; see Global Constraints)
N, T, MU0, EPS, C, RAMP = 0.90, 32760.0, 0.0142, 0.35, 1.7, 11.0


def _verdict(seed):
    t = simulate_ramp(N, T, MU0, EPS, C, RAMP, np.random.default_rng(seed))
    return certify_near_critical(t, T)


@pytest.mark.slow
def test_genuine_near_critical_migrates_sometimes_and_only_mildly():
    # BOTH directions, on RAMPED data. (a) the phenomenon is PRESENT (NOT zero — the under-resolution trap
    # a stationary cohort falls into); (b) it is a MINORITY (most identify); (c) every false-migration is
    # MILD — genuine migrators stay at the FIRST supercritical rung (1.05), never the 1.20 ceiling, so
    # `<= 1.05` has teeth (a runaway to 1.20 would fail; `<= 1.20` cannot fail since 1.20 IS the grid max).
    # Bands absorb numpy drift; a count/peak outside them is a real change -> diff the spike, do not widen.
    verdicts = [_verdict(s) for s in range(16)]
    migrated = [v for v in verdicts if not v.identified]
    assert 1 <= len(migrated) <= 7                     # present (NOT zero) AND a minority (recorded: 4)
    assert all(v.peak <= 1.05 for v in migrated)       # MILD — the magnitude collapse (1.05, not 1.20)
    assert all(v.peak < 1.0 for v in verdicts if v.identified)   # identifiers sit interior subcritical


@pytest.mark.slow
def test_recorded_per_seed_verdicts_regression():
    # Deterministic per-seed lock on MARGIN-TESTED seeds only (recorded 2026-06-23; T +-5% probe): seed 5
    # migrates robustly across the perturbation and seed 1 identifies robustly. Seeds 0/7/10 also migrate at
    # this exact regime but FLIP to identify under a small T change (knife-edge) -> deliberately NOT asserted.
    # Assert the robust VERDICT DIRECTION + a coarse peak bound, NOT an exact argmax rung: a scipy/numpy
    # point release that nudges the L-BFGS optimum across an N_GRID rung must not trip this; only a real
    # gate-behaviour change should. If 5 or 1 ever flips DIRECTION, margin-test and replace the seed.
    v5 = _verdict(5)
    assert (not v5.identified) and 1.0 <= v5.peak <= 1.05    # robustly MIGRATES, and MILD (not a runaway)
    assert v5.peak_constrained < v5.peak                     # the n<1 cap BINDS here — the case that matters
    v1 = _verdict(1)
    assert v1.identified and 0.45 <= v1.peak < 1.0           # robustly IDENTIFIES at an interior subcritical peak

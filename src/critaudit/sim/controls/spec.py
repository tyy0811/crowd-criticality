"""FROZEN SPEC SURFACE for the classical-ABM shakedown — the pre-registered, result-blind constants.
A change to anything here is a change to the frozen spec, NOT a code tweak (the anti-drift contract at
file level). The generator (deffuant.py) and the discrimination cohort (test_shakedown_discrim.py)
CONSUME these; the separation thresholds are frozen HERE, before any discrimination is measured.

⚠ Two distinct epsilons: `eps` (the Deffuant confidence bound, the SWEPT order parameter — EPS_LOW/CRIT/HIGH)
vs `KERNEL_EPS` (the Lomax offspring-delay shape, FROZEN to the gate's power-law-Hawkes calibration regime).
"""
from __future__ import annotations

# --- population / dynamics ---
N_AGENTS = 800
K_REACH = 4          # mean-field influence attempts per firing
MU_STEP = 0.5        # Deffuant convergence rate (midpoint at 0.5)

# --- offspring TIMING kernel: FROZEN to the gate's calibration substrate (test_gate.py uses 0.35/1.7) ---
KERNEL_EPS = 0.35    # Lomax delay shape (NOT the order parameter)
KERNEL_C = 1.7

# --- the order parameter (Deffuant confidence bound): three FROZEN plants ---
# initial-distribution branching m0 = K_REACH * (2*eps - eps^2) for Uniform[0,1] opinions
EPS_LOW = 0.04       # m0 ≈ 0.31  (deep subcritical)
EPS_CRIT = 0.134     # K_REACH*(2e - e^2) = 1  (mean-field critical point)
EPS_HIGH = 0.30      # m0 ≈ 2.0   (deep supercritical)

# --- event budget per plant (Gate-D-style: enough events to read; then N-matched by truncation) ---
# These are BUDGET knobs (event count is not the measured outcome): if a plant yields < N_MATCH raw
# events, raise that plant's HORIZON/MU_NEWS until it does (documented), NOT a result knob.
HORIZON = 4000.0
MU_NEWS_LOW = 6.0      # ~24k immigrants; trees ~size 1.3 → ~30k IN-WINDOW events
MU_NEWS_CRIT = 0.5     # ~2k critical trees → power-law avalanche statistics for the τ check
MU_NEWS_HIGH = 0.4     # BUDGET knob (see DECISIONS 2026-06-24, results/s2_shakedown/..._budget_invariance):
                       # offspring are censored at HORIZON (finite observation window), so the original
                       # 0.015 yields only ~12k IN-WINDOW events (< N_MATCH); 0.4 → ~3e5. n_tree (~3.1–3.5)
                       # is mu_news-INVARIANT, and the gate's observational-subcritical VERDICT (peak<1,
                       # no migration) holds at every mu_news (exact peak wobbles in 0.45–0.75, all < 1), so
                       # this value cannot outcome-tune the finding (only χ moves with it — and χ's no-peak
                       # is sourced from the controlled sweep, not the cohort).
N_MATCH = 16000        # gof-power floor; the gate reads the first N_MATCH events (apples-to-apples)

# --- result-blind separation criterion (FROZEN before measuring; see DECISIONS 2026-06-24) ---
N_TREE_SUB = 0.7       # LOW certified subcritical iff n_tree < N_TREE_SUB
N_TREE_SUPER = 1.3     # HIGH certified supercritical iff n_tree > N_TREE_SUPER
PEAK_GAP = 0.40        # gate discrimination: peak(HIGH) - peak(LOW) >= PEAK_GAP
GATE_MIGRATE_TOL = 0.15  # gate's own MIGRATE_TOL: migrated(LOW) < TOL <= migrated(HIGH)
AGREE_TOL = 0.20       # |gate peak(LOW) - n_tree(LOW)| <= AGREE_TOL (one coarse grid step of slack)
TAU_TARGET = 1.5       # mean-field critical avalanche-size exponent
TAU_TOL = 0.30         # CRIT scaling anchor: csn exponent in [TAU_TARGET ± TAU_TOL]

SEED = 20260624        # base seed for the discrimination cohort

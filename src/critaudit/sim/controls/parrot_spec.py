"""FROZEN, result-blind surface for the parrot-null prototype. A change to a constant here is a spec
change, not a code tweak. All thresholds are frozen BEFORE the first run, from theory (Poisson F≈1,
B≈0) or cited from increment-3 (n_gen(CRIT)≈1.3) — never back-filled from observed parrot values.

Three distinct 'n_tree'-ish quantities live in this rig (see anchors.py docstring):
  n_gen   = anchors.n_tree (successes/events, belief-coupled) -> 0 in the parrot = the tripwire
  n_struct= 1 - #roots/#events (post_reply_tree on true links) -> 0 in the parrot = structural gate
  n_emit  = the read->emit analog; == n_gen computationally in Deffuant, splits at the sweep = column 5
"""
from __future__ import annotations
from critaudit.sim.controls import spec as cs

# --- reference plant: CRIT, where the coupled crowd's critical signature is sharpest ---
REFERENCE_PLANT = "CRIT"
REFERENCE_EPS = cs.EPS_CRIT            # 0.134
REFERENCE_MU_NEWS = cs.MU_NEWS_CRIT    # 0.5

# --- shared temporal substrate: held identical to the coupled control; NOT matched on branching ---
N_AGENTS = cs.N_AGENTS
K_REACH = cs.K_REACH
MU_STEP = cs.MU_STEP
KERNEL_EPS = cs.KERNEL_EPS
KERNEL_C = cs.KERNEL_C
HORIZON = cs.HORIZON
N_MATCH = cs.N_MATCH

# --- the collapse: belief coupling removed == zero confidence bound (no |Δx|<eps success ever fires) ---
BELIEF_FREE_EPS = 0.0

# --- scale-resolved temporal-clustering windows (multi-scale Fano), frozen ---
FANO_WINDOW_SIZES = (HORIZON / 200.0, HORIZON / 50.0, HORIZON / 10.0)

# --- positive control (is the null real): tripwire successes==0 ; structural n_struct==0 (asserted in code) ---
# --- frozen null-confirmation column readings (theory-anchored) ---
TAU_NULL_PASSES = False        # collapsed null is all size-1 avalanches -> no power law admissible
N_EMIT_NULL = 0.0              # no read->emit successes
BURST_NULL_HI = 0.20           # Poisson immigrants: B≈0 in expectation; finite-sample tol (theory, not obs)
FANO_NULL_LO = 0.60            # Poisson: F≈1 at all scales; frozen finite-sample band lower edge
FANO_NULL_HI = 1.60            # ... upper edge

# --- coupled-reference contrast (separation = the trivial-but-confirming instrument-discovery readout) ---
# The coupled τ-arm separation rides the THEORY-ANCHORED τ-band (mean-field 3/2), the criterion incr-3
# actually anchored (test_shakedown_discrim::test_crit_tau_corroborates_criticality). The CSN strict
# .passes / p_boot is RECORDED-NOT-ASSERTED — incr-3 disclaims it as a budget knob, and the full-shape
# Clauset bootstrap rejects the known-critical coupled CRIT (finite-size cutoff != PURE power law) despite
# a near-perfect exponent. See the 2026-06-25 DECISIONS entry (freeze-correction + scoped GoF finding).
# N_EMIT_REF_MIN: THEORY-anchored. EPS_CRIT is DEFINED by m0 = K_REACH·(2eps−eps²) = 1 (spec.py:23, the
# mean-field critical point), so the generative branching at the coupled CRIT crosses toward 1; 0.70 is a
# conservative floor — the SAME value as the incr-3 subcritical bound N_TREE_SUB (spec.py:42) — asserting
# only "coupled CRIT n_emit is NOT subcritical". incr-3's measured n_tree(CRIT) ≈ 1.3 is CORROBORATION
# (its DECISIONS prose), NOT a test-locked anchor: incr-3 locks only the LOW/HIGH extremes + CRIT τ, not a
# CRIT n_tree bound (test_shakedown_discrim.py / test_anchors.py). So the threshold rests on theory, not pedigree.
N_EMIT_REF_MIN = 0.70          # = N_TREE_SUB; coupled CRIT n_emit crosses toward 1 (m0=1 by construction)
TAU_TARGET = cs.TAU_TARGET     # 1.5
TAU_TOL = cs.TAU_TOL           # 0.30

# --- CSN bootstrap budget (NOT a result knob; no frozen criterion asserts p_boot depth) ---
N_BOOT = 200

# --- SWEEP-SIDE INTERFACE (named; NOT consumed by any prototype test) ---
# When the null is content-marginal-structured (sweep), n_struct is positive-width and the live tail-band
# gate replaces the degenerate prototype `assert n_struct==0`. Construction params frozen HERE, in the same
# motion, so the band cannot be widened after seeing where the decoupled run lands:
SWEEP_BAND_SEEDS = 64
SWEEP_BAND_QUANTILE = 0.95
SWEEP_BAND_EDGE = "max"        # upper edge = max over seeds

SEED = 20260625                # base seed for the confirmation cohort

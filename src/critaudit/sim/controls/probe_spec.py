"""FROZEN result-blind surface for the probe-recoverability study (sub-increment 3).

Design: docs/superpowers/specs/2026-07-20-probe-recoverability-subinc3-design.md (untracked per
repo convention; content pinned by DESIGN_DOC_SHA256; DECISIONS 2026-07-20 freeze entry is the
committed record). A change to any constant here is a SPEC CHANGE, not a tweak.

PRIMARY CLAIM (owner-ratified 2026-07-20): probe recoverability as an intervention-response /
SUSCEPTIBILITY instrument (chi_resp). n_resp = 1 - 1/S_bar is ONLY a candidate calibration
transform — mean realized tree size = 1/(1 - n_struct) algebraically, and realized trees
undercount n_gen by exactly the collision + censor mass, so the Galton-Watson identity fails at
the finite-size/censoring boundary; activation requires the MEASURED mapping to clear the
transform criterion under the identical operator. chi_resp and n_resp derive from ONE seeded
statistic and can never satisfy PRE_REGISTRATION line 189's two-independent-diagnostics
requirement ("neither defines the other") — the second diagnostic is OPEN. H1b's n placement
stays BLOCKED in all branches. The sub-inc-2 §9a/§9b criteria are retired-as-blocked
(RETIRED_CRITERIA below, string-only); no def-#2-dependent tau or n_emit work runs anywhere in
this increment.
"""

# --- the untracked design note, pinned ---------------------------------------------------------
DESIGN_DOC = "docs/superpowers/specs/2026-07-20-probe-recoverability-subinc3-design.md"
DESIGN_DOC_SHA256 = "d0a35334d73b7424f5fce01d5f78abc861cd5e30b6caf592f588eea4c9508c40"

# --- retirement record (STRING-ONLY — importing llm_parrot_spec would pull the probe modules
#     into the sub-inc-2 firewall scan set; design §6, risk R8) --------------------------------
RETIRED_CRITERIA = (
    "llm_parrot_spec.NULL_TAU_FRAC_MAX (sub-inc-2 §9a sharp-tau): RETIRED-AS-BLOCKED, owner "
    "2026-07-20 — composed on def-#2, whose v2 calibration FAILED (ARI 0.2497 vs 0.90).",
    "llm_parrot_spec.N_EMIT_DEFINITION (sub-inc-2 §9b crosses-1 n_emit): RETIRED-AS-BLOCKED, "
    "owner 2026-07-20 — same composition, same block.",
)

# --- the primary grid (frozen input-side; design §3) -------------------------------------------
# Dense over ~[0.09, 0.155]: belief clustering lifts realized branching above the
# initial-distribution m0 (shakedown: n_tree 3.0-3.4 at HIGH vs m0 ~ 2.0), so the realized
# n_gen = 1 crossing is expected AT OR BELOW EPS_CRIT = 0.134. Includes all three plants.
EPS_GRID = (0.04, 0.06, 0.08, 0.09, 0.10, 0.11, 0.12, 0.125, 0.13, 0.134,
            0.138, 0.145, 0.155, 0.17, 0.20, 0.25, 0.30)

# DRIVE IS FIXED ACROSS THE ENTIRE PRIMARY GRID (owner correction 2026-07-20): chi moves with
# mu_news on the measured record (DECISIONS 2026-06-24 chi entry) while only n_gen is
# drive-invariant — a piecewise drive table would confound the gated chi_resp surface (its
# switch points would sit inside the dense window). 0.4 = the banked shakedown working value at
# HIGH; at HORIZON=4000 it yields ~1,600 immigrants/run (~1,000 post-burn eligible), so power
# never motivates a table. The piecewise table survives ONLY as the sensitivity panel below.
MU_NEWS_PROBE = 0.4

# Sensitivity panel (recorded-not-asserted; NEVER enters any gate): one dense-window eps at two
# alternative drives, characterizing chi_resp's drive sensitivity.
SENSITIVITY_EPS = 0.12
SENSITIVITY_MU_NEWS = (0.5, 2.0)

# Seeds: 12 per grid point, frozen train/test INDEX split (8/4). Namespaced streams:
# default_rng(SeedSequence(SEED_PROBE, spawn_key=(eps_index, seed_index))).
SEED_PROBE = 20260720
N_SEEDS = 12
TRAIN_SEED_INDICES = (0, 1, 2, 3, 4, 5, 6, 7)
TEST_SEED_INDICES = (8, 9, 10, 11)

# --- marker eligibility + equal support (design §2/§3) -----------------------------------------
# Eligible marker r: T_BURN <= news_time_r < HORIZON - T_TAIL_GUARD. Burn-in excludes the
# un-clustered transient; the tail guard limits (never eliminates — disclosed) censoring
# truncation of late trees. Both cuts are part of the frozen operator definition.
T_BURN = 1000.0
T_TAIL_GUARD = 500.0
# EQUAL SUPPORT: exactly the FIRST M_ELIGIBLE eligible markers by news_time order per (eps,
# seed) cell (deterministic — no selection channel). A run with fewer eligible markers FAILS
# the study loudly (fail-closed; no cell may contribute unequal marker support/df). Expected
# eligible at MU_NEWS_PROBE*2500 ~ 1000 (Poisson), so 512 is ~15 sigma below the mean —
# thin-run failure is a real anomaly, never noise. Power at (M_ELIGIBLE x N_SEEDS) is certified
# by the GW positive control BEFORE any measurement; a certification fail raises budgets
# pre-measurement (a recorded spec change), never post hoc.
M_ELIGIBLE = 512

# Exposure normalization on THIS substrate: none — mean-field, every firing makes exactly
# K_REACH attempts, so per-injection exposure is constant. (The OASIS pilot, where exposure
# varies, normalizes per exposure; §OASIS below.)
EXPOSURE_NORMALIZATION = "none_mean_field_k_reach_constant"

# THE SUSCEPTIBILITY STATISTIC (pre-freeze construction correction, measured on the
# independent-capped-GW
# positive control BEFORE anything was frozen or run on the ABM — the sanctioned ground-truth
# calibration phase; plan deviation disclosed in the DECISIONS freeze entry):
#   chi_resp(s, eps) = CV^2(S) = Var(S; ddof=1) / mean(S)^2 over the M_ELIGIBLE markers.
# Rationale (two-sided pinch): subcritically CV^2 ~ sigma^2/(1-m) diverges toward the crossing;
# in the capped-supercritical branch CV^2 ~ (1-theta)/theta diverges toward the crossing from
# above — the peak is pinched AT m=1 from BOTH sides. The plan's original Var(S) peaks at
# theta*(1-theta)*cap^2, GENERICALLY displaced supercritical — MEASURED on the GW control at the
# frozen budgets: Var(S) argmax at m=1.244 (+0.24), Fano Var/mean at m=1.076 (+0.08), CV^2 at
# m=0.972 with the crossing inside the argmax's neighbor interval, seed consistency 11/12,
# prominence 26.5x. Var(S) and Fano are retained as recorded-not-gated diagnostic columns.
CHI_RESP_STATISTIC = "cv2_seeded_response"

# --- gate criteria (design §4; Gate-D shape) ---------------------------------------------------
# (a) LOCATOR (the gate): eps_c_gen = linear-interpolated crossing of seed-mean n_gen(eps)
# through 1 (FAIL unless bracketed exactly once). PASS iff the chi_resp argmax is interior, the
# crossing lies in the argmax's neighbor interval, prominence clears PEAK_RATIO_MIN, and
# per-seed argmax consistency clears SEED_CONSISTENCY_MIN.
PEAK_RATIO_MIN = 2.0            # anchored: the demoted belief-variance chi measured a FLAT
                                # peak/off-peak ratio ~0.98; a (1-n)^-3-class divergence
                                # predicts >= an order of magnitude. 2.0 kills the known-flat
                                # failure mode with margin on both sides.
SEED_CONSISTENCY_MIN = 0.75     # >= 9 of 12 per-seed argmaxes within one grid step of the
                                # pooled argmax (neighbor-interval sense).
# (b) TRANSFORM (n_resp activation sub-verdict): noise-aware monotonicity (each adjacent
# subcritical seed-mean increment of S_bar and of n_gen satisfies delta > -2*SE(delta)) +
# held-out accuracy at every grid point with train-mean n_gen in N_RESP_ACCURACY_RANGE.
N_RESP_TOL = 0.05               # = the pre-registration's own half-band / H1c margin (cited,
                                # not invented).
N_RESP_ACCURACY_RANGE = (0.5, 0.9)
# (b2) resolution floor (separate sub-verdict; (b) may pass with (b2) failed — the transform
# then activates with band-resolving power certified ABSENT): 2*SD_test(n_resp) <= 0.05 at
# every grid point with train-mean n_gen in the near-critical band.
N_RESP_BAND = (0.9, 1.0)
MONOTONE_SE_MULT = 2.0
# Fabricated-surface guards (Gate-D used_seeds precedent): the evaluator RAISES unless every
# grid point carries exactly N_SEEDS seeds and every cell exactly M_ELIGIBLE markers.
USED_SEEDS_MIN = N_SEEDS
USED_MARKERS_MIN = M_ELIGIBLE

# OPERATOR-IDENTITY CLAUSE: any (b) activation binds ONLY to the exact operator fingerprint —
# spec.N_AGENTS/K_REACH/MU_STEP/KERNEL_EPS/KERNEL_C/HORIZON, the censor-at-horizon rule, the
# eligibility rule above, and MU_NEWS_PROBE. No transfer to OASIS (variable exposure, recsys,
# finite memory horizon) without a separate calibration. H1b remains BLOCKED in all branches.

# --- Option B: the frozen fail-branch (activates MECHANICALLY on locator FAIL) -----------------
# Only the [reasons] slot is filled from the verdict; everything else is immutable.
OPTION_B_TEXT = (
    "FAIL-BRANCH (Option B — activates automatically on recoverability-gate failure; frozen "
    "before any run): The regime question remains UNRESOLVED at this substrate. The chi_resp "
    "intervention-response instrument did not certify recoverability on the ground-truth "
    "operator (banked verdict: [reasons], results/s3_probe/). H1b is therefore "
    "inconclusive-by-instrument: no calibrated n placement exists, and this is recorded as a "
    "pre-registration §10 deviation ('inconclusive-by-instrument'), not as a negative regime "
    "finding. No threshold is relaxed, no grid point is added post hoc, no alternative "
    "estimator is substituted, and the OASIS accessibility pilot does not run. The n_resp "
    "candidate transform remains unactivated; the independent second diagnostic required by "
    "PRE_REGISTRATION line 189 remains open; the sub-inc-2 §9a/§9b criteria remain "
    "retired-as-blocked.")

# --- OASIS accessibility pilot (frozen now; runs ONLY behind the gate; design §5) --------------
# AUTHORIZATION RULE — FLAGGED FOR OWNER RATIFICATION (DECISIONS freeze entry): recommended =
# pilot runs on locator-(a)-PASS alone (it tests channel ACCESSIBILITY, not n placement);
# disclosed alternative = require the full PASS incl. (b).
PILOT_INJECTION_ROUNDS = (2, 4, 6, 8, 10)   # early + multiple: the measured windowB2 fact (one
                                            # round-15 injection -> 0 exposures, consistent
                                            # with expected ~0.25) vs banked per-post exposure
                                            # median 2 / mean 7.8.
PILOT_MARKER_POOL_INDICES = (0, 1, 2, 3, 4)  # NEWS_POOL[0..4] in round order — deterministic,
                                             # distinct, no new content surface.
# Accessibility gate: >= PILOT_MIN_EXPOSED_MARKERS of the 5 markers exposed >= 1 AND total
# marker exposures >= PILOT_MIN_TOTAL_EXPOSURES AND fail-closed export. exposures(m) = number
# of RefreshRecords whose served set contains marker m; response = true-link tree size rooted
# at m; per-exposure normalization (tree_size - 1)/exposures; exposures = 0 ->
# undefined-inaccessible (NEVER 0). NO regime claim in any branch; the finite-memory-horizon
# and exposure-volume caveats are restated in the banked record.
PILOT_MIN_EXPOSED_MARKERS = 4
PILOT_MIN_TOTAL_EXPOSURES = 10

"""FROZEN result-blind surface for the MATCHED parrot null (sub-increment 2).

Design: docs/superpowers/specs/2026-07-17-llm-parrot-null-subinc2-design.md (untracked working
artifact per repo convention; its content is pinned by DESIGN_DOC_SHA256 below and in the
2026-07-17 DECISIONS freeze entry). A change to any constant here is a SPEC CHANGE, not a tweak.

Every value below is frozen from theory / input-side reasoning BEFORE any sub-inc-2 cohort
measurement runs (the T5 calibration, the T6 generation, the T7 band). What is frozen for the
calibration is the PROCEDURE — theta itself is that procedure's measured output, banked in
results/s2_llm_parrot_null/, never a constant here.

The prototype's do-not-match list (parrot_spec / design 2026-06-25 §4) BINDS UNCHANGED: the
branching ratio, the avalanche-size distribution, and the per-agent emission rate are never
matched. Matched = the aggregate per-round emission profile + the authored-length marginal + the
embedding marginal, nothing else.

DEFINED-NOT-EVALUATED (design §9; enforced structurally by tests/test_llm_parrot_firewall.py):
NULL_TAU_FRAC_MAX and N_EMIT_DEFINITION are sub-inc-3 execution criteria authored now so they are
frozen before any null tau or cohort cascade-def-#2 quantity exists. NOTHING in this package
evaluates them.
"""
from critaudit.sim.harness import harness_spec as _hs

# --- the untracked design doc, pinned (tamper-evident committed record) ------------------------
DESIGN_DOC = "docs/superpowers/specs/2026-07-17-llm-parrot-null-subinc2-design.md"
DESIGN_DOC_SHA256 = "5805d7027aed9825c577414f696e0946d733a34da428b210bd0809ee96a5e2be"

# --- embedding pin (design §4) -----------------------------------------------------------------
# Resolved from the HF API at spec authoring (2026-07-17) and verified already present in the
# local HF cache — hermetic, zero-network at run time. CPU ONLY (never MPS: the silent
# nondeterminism trap on Darwin); float32; L2-normalized; fixed batch size in stream order
# (batch composition changes fp sums); single torch thread.
EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBED_DIM = 384
EMBED_DEVICE = "cpu"
EMBED_BATCH_SIZE = 32
EMBED_NORMALIZE = True
EMBED_MAX_SEQ_LENGTH = 256          # model default, RECORDED (truncation horizon for long texts)
EMBED_TORCH_THREADS = 1

# All cosines are rounded to this many decimals BEFORE any theta comparison (the fp-jitter fence:
# a sub-1e-6 wobble can never flip an attribution).
COSINE_DECIMALS = 6

# --- theta calibration (design §6): frozen PROCEDURE, measured output --------------------------
# Grid: inclusive, start/stop/step. theta* = argmax J(theta) = TPR - FPR over the grid;
# ties -> LARGEST theta (conservative: fewest manufactured edges).
#   TPR(theta) = fraction of ALL true-edged children whose attributed parent (argmax rounded
#                cosine over CANDIDATE_RULE candidates, iff >= theta) equals their true parent —
#                denominators include same-round-parent children the candidate rule cannot reach
#                (recorded as same_round_ceiling; identical for cohort and null, cannot move the
#                argmax: an unreachable child is wrong at every theta).
#   FPR(theta) = fraction of TRUE ROOTS receiving any attributed parent.
THETA_GRID_START = 0.01
THETA_GRID_STOP = 0.99
THETA_GRID_STEP = 0.005
THETA_CRITERION = "attribution_youden"
THETA_TIE_RULE = "largest"
# Candidates for event i = all events of STRICTLY EARLIER rounds (parent_idx[i] < i structural;
# no same-time edges; round = the OASIS round-granular created_at tick).
CANDIDATE_RULE = "strictly_earlier_round"

# --- matching-quality gate (design §7): sample-size formulas, never tuned ----------------------
# (i) per-round aggregate counts: an exact copy of the assigned cohort window's -> tolerance ZERO.
MATCH_COUNTS_RULE = "exact_copy"
# (ii) authored-length marginal: two-sample KS statistic D <= COEFF * sqrt((n+m)/(n*m)) — DKW
#      scale, ~3x sampling noise (~0.16 at n≈m≈700). A construction-bug detector (wrong field
#      embedded, wrong window matched), not a statistical-surprise test.
MATCH_LEN_KS_COEFF = 3.0
# (iii) embedding marginal: cosine(mean null embedding, mean cohort embedding) >= this floor — a
#       with-replacement resample of the SAME pool concentrates at 1 with O(1/sqrt(m)) deviation.
MATCH_EMBED_MEAN_COS_MIN = 0.98

# --- null construction (design §7) -------------------------------------------------------------
NULL_BASE_SEED = 20260717
# Namespaced SeedSequence spawn-key stream indices (harness_spec RNG_STREAM_* precedent).
NULL_STREAM_CONTENT = 0
# Window assignment for null seed i (i = 0..SWEEP_BAND_SEEDS-1): round-robin i mod 3 over the
# registered cohort windows ordered by cohort seed ASCENDING (= harness_spec.COHORT_SEEDS order:
# 20260627 A', 20260628 B', 20260629 C) -> 22/21/21. Disclosed alternative (3x64 per-window
# bands) recorded in the design; per-window sub-bands are recorded either way.
WINDOW_ASSIGNMENT = "round_robin"
WINDOW_ORDER = _hs.COHORT_SEEDS
# Gate clause (iii) diagnostics (recorded, NOT asserted): fano_profile horizon = n_rounds (the
# round-granular clock), window sizes in ROUND units — all >= 1 round so the profile is
# meaningful on a round-granular stream.
NULL_FANO_WINDOW_SIZES = (1.0, 4.0, 10.0)

# --- the n_struct band (design §7): ACTIVATES the prototype's dormant frozen constants ---------
# Imported, never duplicated — parrot_spec is the single source; a divergence is a drift bug the
# frozen-surface test trips on.
from critaudit.sim.controls.parrot_spec import (   # noqa: E402  (re-export, single-source)
    SWEEP_BAND_SEEDS, SWEEP_BAND_QUANTILE, SWEEP_BAND_EDGE)
# Band reading (design §9c, flagged for owner ratification): SWEEP_BAND_EDGE="max" is the GATE
# edge (worst case over the seeds); the SWEEP_BAND_QUANTILE (0.95) value is RECORDED as the softer
# reference edge.

# =============================================================================================
# DEFINED — NOT EVALUATED (design §9a/§9b; sub-inc 3 executes these; nothing here computes them)
# =============================================================================================

# §9a — the sharp "matched structure manufactures tau" criterion. Over the SWEEP_BAND_SEEDS
# frozen null seeds, sub-inc 3 runs the tau-arm on each null stream's forest; the null
# MANUFACTURES tau iff the fraction of seeds with a FINITE tau inside the frozen band
# |tau - TAU_TARGET| <= TAU_TOL (parrot_spec, 1.5 +/- 0.30) exceeds this maximum. tau_passes /
# p_boot are RECORDED-NOT-ASSERTED — deliberately NOT a `tau_passes AND band` conjunction: the
# banked prototype finding is that the Clauset GoF bootstrap rejects even known-critical CRIT
# (finite-size cutoff), so conditioning on tau_passes would bias the sharp test toward false
# comfort. Band-based on BOTH sides (cohort read and null read) is the repo's precedent.
NULL_TAU_FRAC_MAX = 0.05

# §9b — the crosses-1 multi-influence n_emit (the pivot's hard horn, banked open since sub-inc-1
# design §12). Frozen definition text; composes two already-frozen rules with NO new knob.
N_EMIT_DEFINITION = (
    "For each cohort event e that has a most-recent-prior REFRESH under the frozen sub-inc-1 "
    "pairing rule (harness_spec: served set of the agent's most-recent prior refresh by "
    "(created_at, trace-rowid)): influence in-degree d(e) = number of DISTINCT served items s in "
    "that refresh with rounded-cosine(authored(e), authored(s)) >= theta* (COSINE_DECIMALS "
    "rounding; theta* = the banked T5 calibration output). n_emit = sum_e d(e) / n_events. "
    "Multi-attribution over the read-verified served set is what frees n_emit from the "
    "one-parent-per-event cap that pins n_struct < 1 — it can cross 1. Computed NOWHERE until "
    "sub-inc 3.")

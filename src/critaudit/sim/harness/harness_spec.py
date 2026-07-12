"""FROZEN, result-blind surface for the LLM-harness sub-increment 1. A change to a constant here is a
spec change, not a tweak. Thresholds are frozen from theory / input-side ranges BEFORE the reference
run — never back-filled from observed values. See docs/superpowers/specs/2026-06-27-llm-harness-subinc1-design.md.

READ->EMIT PAIRING RULE (frozen): an emit is a read->emit success iff its parent post is in the served
set of that agent's most-recent-prior REFRESH, where "prior" is by created_at (primary) with trace-rowid
breaking ties ONLY within the same created_at, never across rounds (OASIS's sandbox clock is round-granular;
ratified amendment 2026-06-30 — provenance: results/s2_harness/2026-06-29_task1_recon_pass_conditions.md +
DECISIONS.md 2026-06-30). read_emit_ratio = successes/events is the REALIZED fraction (<= n_struct < 1) —
it resolves read->emit ACCESSIBILITY only, NOT the crosses-1 generative n_emit (deferred; design §2/§12)."""
from __future__ import annotations

# --- positive-control thresholds (theory / Poisson-baseline; not back-filled) ---
READ_EMIT_FLOOR = 0.01     # read_emit_ratio must exceed this -> coupling present (some reads drive emits)
MAX_FRAC_SIZE1 = 0.95      # not ALL trees size-1 (a fully decoupled crowd is ~all size-1)
MAX_GIANT_FRAC = 0.90      # no single tree may swallow ~all events (degenerate one-component crowd)
LENGTH_SPREAD_FLOOR = 1.0  # message-length std (chars) > this -> content non-degenerate

# --- model (pinned for reproducibility; gate-model = sweep-model). Default starting rung. ---
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"   # 7-8B instruct, fits a single ~$1-2/hr Modal GPU (escalate per design §7)
MODEL_REVISION = "main"                   # PIN to a concrete commit hash at Task 9 before the cohort run

# --- cohort seeds for the @slow positive-control run ---
COHORT_SEEDS = (20260627, 20260628, 20260629)

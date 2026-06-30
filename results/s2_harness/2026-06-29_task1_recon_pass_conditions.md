# Task-1 recon — result-blind pass conditions (FROZEN before run)

**Date:** 2026-06-29
**Branch:** `stage2-llm-harness-subinc1` (off `main @ 567b54d`)
**Status:** drafted for owner ratification; FROZEN before any OASIS install / recon run / measurement.
**Plan:** `docs/superpowers/plans/2026-06-27-llm-harness-subinc1.md` Task 1 (the hard gate).
**Design:** `docs/superpowers/specs/2026-06-27-llm-harness-subinc1-design.md` §6.

Task 1 confirms — from the OASIS **schema + action-logging source**, corroborated by one clean
end-to-end smoke pair — the two facts the "adopt OASIS" decision rests on. Both pass conditions are
stated **structurally** (schema/code), so NO produced cascade number can retrofit them. A frozen
condition that does not clear is a **finding, logged not relaxed** (build-vs-adopt reopens).

## Evidence hierarchy (applies to both conditions)

1. **PRIMARY** — the OASIS schema + action-logging source: does the persistence/structure EXIST.
2. **CONFIRMATORY** — the smoke trace (3 agents, 2 rounds, local Ollama model): does it reconstruct end-to-end.
3. The smoke run NEVER overrides the schema read. A schema that persists the fact + a smoke run that
   happens not to trigger it = the fact is **accessible** (PASS on the schema); the smoke is an
   incomplete confirmation, not a fail.

## Diagnostic ordering (resolves the ambiguous null)

Before reading any trace content, confirm the run actually produced agent actions:

- **D0 (tool-call emission):** at least one agent emitted a VALID, PARSED tool call (CAMEL `FunctionTool` /
  OASIS action).
  - If D0 fails → the run is inconclusive at the **MODEL/SERVING** layer (model didn't emit a well-formed
    action, or Ollama's tool-call parser didn't match the model's chat-template format), NOT an
    OASIS-persistence fail. Fix the model/serving (escalate model rung, fix parser) and re-run. An empty
    trace with D0 failed is NOT a gate fail.
  - Only once D0 passes does an empty / REFRESH-less trace read as informative about persistence.

## Pass condition A — REFRESH-persistence (read→emit accessibility)

PASS iff, established from schema/source AND confirmed by ≥1 clean smoke pair:

- **A1.** The trace persists each REFRESH (read) action with: the acting agent id, an orderable timestamp,
  and the **IDENTITIES of the served items** (post ids) — i.e. the served set is recoverable offline
  (not merely "a refresh happened").
- **A2.** A **join key** exists: served item ids from a REFRESH row match to the item ids of that SAME
  agent's subsequent emits, ordered by **`created_at` (primary), trace insertion-order (rowid) as the
  within-same-`created_at` tiebreaker** — *refined 2026-06-30, see amendment below* (OASIS's sandbox clock
  is round-granular, so a refresh and its consequent same-round emit share `created_at`; the original
  "strictly before the emit timestamp" could not express within-round ordering).
- **A3.** ≥1 clean read→emit pair reconstructs in the smoke trace: an emit whose parent item was in that
  agent's most-recent-prior REFRESH served set.

**FAIL branch (logged not relaxed):** if the schema does not persist served-item identities, OR there is
no orderable timestamp, OR served sets cannot join to emits → read→emit **ACCESSIBILITY** (the
loggable-and-reconstructable half of the pivot) is unresolved → STOP, record the observed schema, mark
"adopt OASIS regains the n_emit-accessibility instrumentation tax (measured)", surface to owner that
build-vs-adopt reopens (design §6). Do not work around it.

## Pass condition B — topology-fidelity (structural-instrument integrity)

Protects `n_tree` and the avalanche size/duration tails — the structural instrument the §4f gate now
leans on after the μ(t) temporal gate came back regime-blind. Resolved in the SAME recon, from the
schema, NOT from produced cascades.

- **B1.** Read whether OASIS records a comment's TRUE parent — does a comment carry a reference to the
  specific item it replies to (which may be another comment), or only to the root post?
- **B2. FROZEN adapter rule:** preserve the TRUE parent whenever OASIS records it (comment→comment or
  comment→post); map `parent_item_id` to the actual parent item. Fall back to `post:<post_id>` ONLY when
  the parent genuinely IS the post (OASIS does not model nested replies, or this comment replies to the post).
- **B3.** Any residual flattening is acceptable ONLY if OASIS structurally does not record the finer
  parent — determined from the schema, not from "comment-on-comment looks rare in the output" (that
  selects the measurement model on the quantity under test).

**DECISIONS entry (either outcome):** record what OASIS exposes for comment parentage and the resulting
parent-assignment rule.

## Model / serving (Task-1 recon)

- **Backend:** Ollama (local, $0, OpenAI-compatible at `http://localhost:11434/v1`; CAMEL
  `ModelPlatformType.OLLAMA`).
- **Model:** a ≥4B model TRAINED for tool calling (OASIS agents act via tool calls, not free text). Target
  Qwen3-family **4B (primary) / 8B (margin)**. EXACT Ollama tag verified against the registry at pull
  time (verify-don't-relay) — do not relay a tag. Avoid sub-4B general models and tool-calling
  "specialist" SKUs (xLAM-2, Hammer), which underperform plain Qwen outside their own harness.
- This is the **RECON** model (drives the smoke to populate the trace). It is distinct from the eventual
  gate/sweep model (`harness_spec.MODEL_ID`, Task 6/9). The tool-call-reliability requirement applies to both.

---
*Frozen before the run per the plan's result-blind rule and the pre-flight discipline (documentation is
not verification). Ratify or edit before Task-1 execution begins.*

---

## AMENDMENT (2026-06-30, ratified) — pairing rule: `created_at` primary, rowid within-round tiebreaker

**Provenance (predates the pass; justified by schema, not by result).** The schema read found OASIS's
TWITTER sandbox clock is **round-granular**: `env.step` advances `created_at` once per round, and within a
round `to_text_prompt()` → `refresh()` (logs the served set) → builds the LLM prompt → the emit, so a
refresh and its consequent same-round emit **share `created_at`**. The original A2 wording ("REFRESH
timestamp *strictly before* the emit timestamp") assumed sub-round timestamp resolution OASIS does not
provide → it reconstructed **0** pairs on the first trace, despite the pairs causally existing.

**Refined rule (the correct operationalization of A2/A3's intent).** Most-recent-prior REFRESH by
**`created_at` (primary); trace insertion-order (rowid) breaks ties ONLY within the same `created_at`,
never across rounds.** Within a round the refresh genuinely precedes its emit (causally guaranteed by the
`to_text_prompt`→`refresh`→LLM→emit flow), and the trace rowid is the true causal order; across rounds
`created_at` remains the real ordering (rowid must not override it — async writes/retries can diverge from
causal order across rounds).

**Why this is a refinement, not a relaxation (the direction is the tell).** It replaces a timestamp that
*cannot express* the ordering with one that can; it does not widen a tolerance to rescue a borderline
pair. It moves to a *stricter, causally-certain* operationalization (same-round refresh-before-emit is
structural), and the pairs are causally certain once keyed correctly. Source-established-before-result.

**Confirmed on a clean instrument.** Re-validated on the pristine (`qwen3:4b-instruct`, non-thinking,
zero-timeout) trace: **A3 = 3 same-round read→emit pairs, cross-round false-pairs = 0** (the across-round
guard holds), **B = 4 repost/quote→original_post links**, D0 PASS. The first run was timeout-degraded
(lost emits) and the timeout-bumped re-run still dropped one (qwen3-thinking is unbounded on CPU); the
committed fixture is the clean re-run on the non-thinking instruct variant. See DECISIONS 2026-06-30.

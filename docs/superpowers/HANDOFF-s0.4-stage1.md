# HANDOFF — S0.4 resolved → Stage-1 estimator promoted (2026-06)

**Branch:** `s0.4-data-feasibility-spike` (grew well past the spike — now also holds Stage-1 work).
**Status:** the question that gated the project is **answered**; the estimator that answers it is **in
production behind fast tests**; the certification path is **built and waiting on source-B data**.

This handoff is transient — remove it once the next phase is underway (as `HANDOFF-post-s0.1.md` was).

---

## TL;DR — what landed

**S0.4 granularity is RESOLVED (qualified G1 cleared).** 2 s on-chain block-time quantization is **not** a
barrier to recovering the Hawkes branching ratio `n̂` in the project's regime (power-law, near-critical).
The original `T_threshold = inf` was **estimator inadequacy** (continuous-MLE on tied block timestamps),
not data inadequacy. The fix — a **within-bin-marginalizing MCEM** estimator — tracks the full-data MLE to
≤0.013 across the whole envelope incl the near-critical × sharp-within-bin hard corner. **Source A is
viable on the granularity axis; source B stays the forward hedge.**

**Authoritative record:** `DECISIONS.md` — read the two 2026-06-16 entries "qualified-G1" (the decision)
and "qualified-G1 RESOLVED" (the verdict). Numbers/tables live in the writedowns (below); `DECISIONS.md`
is result-blind by house rule.

---

## The one thing to internalize: the barrier MOVED, it didn't vanish

Clearing granularity **relocated** the binding constraint at n→1 (the regime the project's interesting
markets occupy) onto the **event-count floor** — enough events to estimate `n` at all. That floor is now
the **operative** limit (it was the gate granularity stood in front of), and it couples to real-data
certification (do real near-critical markets supply enough events?). The granularity finding stands
independent of it because granularity is *relative* (binned vs full timing) and the floor hits both
equally, so it cancels. **S0.2 (the event-count floor) is no longer a queued deferral — it is the next
real risk.**

---

## Repo state

**Committed (the arc, newest first):**
- `cff8b48` cert harness (`certify_granularity`) + power-law generator (`critaudit.generators.powerlaw_hawkes`)
- `59f1dbc` **promote** within-bin MCEM → `critaudit.hawkes.binned` (modular, kernel-agnostic) + `tests/test_binned.py`
- `b82cbbc` writedowns → tables
- `96046ad` power-law recovery **verdict** + DECISIONS resolution
- `48709fc` power-law generator + SOE kernel certified
- `ed93cdd` source-B order-preservation verified live + recorder URL/UA fix
- `ac8381a` within-bin MCEM de-risk (exponential, init-robust)
- `55096b8` qualified-G1 DECISIONS entry

**Held / uncommitted — intentional, keep held:**
- `results/s0.4_feasibility/2026-06-16_quantization_sweep.txt` — the `inf` sweep; **not** a verdict (retired).
- `results/s0.4_feasibility/2026-06-16_granularity_crossreview_brief.md` — staged cross-review brief.
- `spike/s0.4/quantization_sweep.py`, the `spike/s0.4/tests/test_granularity.py` modification — held Task 2.

**NEVER commit:** `verification/adv_*.py` (4 files) — untracked by standing rule.

**Production estimator (the deliverable):** `critaudit.hawkes.binned`
- `ExpKernel`, `PowerLawKernel` — each `.soe() -> (a, betas)` unit-mass; the estimator is kernel-agnostic.
- `fit_binned(counts, grid, horizon, kernel, rng) -> BinnedFit(n, mu, acceptance, ess, trajectory)`.
- `certify_granularity(times, grid, horizon, kernel, rng) -> GranularityCert(n_full, n_binned, diff, fit)`
  — full-timing n̂ vs binned-MCEM n̂. **On real source-B trades (sub-2 s match timestamps, grid=2 s) this IS
  the real-data granularity certification.**
- `tests/test_binned.py` — 5 fast CI-safe tests (~24 s). Slow at-scale validation stays in `stage1/granularity/`.

**Prototypes + writedowns (numbers/tables):** `stage1/granularity/`
- `2026-06-16_recovery_verdict.md` (the verdict + tables), `_powerlaw_components.md`, `_derisk_recovery.md`
- `within_bin_mle.py`, `powerlaw_hawkes.py`, `mcem_powerlaw.py`, `recovery_envelope.py`, `recovery_edge.py`,
  `validate_soe*.py` — the throwaway-but-kept validation chain.
- `results/s0.4_feasibility/2026-06-16_source_b_verification.md` — B preserves within-bin order (Q1–Q4 table).

**Firewall note:** the *spike* firewall (no `src/critaudit` edits) is **lifted** — we crossed into Stage-1,
and the qualified-G1 resolution explicitly sanctioned promoting into `critaudit`. `pyproject` unchanged
(no new deps; `websockets` is offsite-only, never added).

---

## What's next (priority-ordered)

1. **Deploy source-B forward capture — USER ACTION, highest priority.** `spike/s0.4/ws_recorder.py` is
   deploy-ready (URL `ws-subscriptions-clob` + browser UA both fixed). Gated only on a one-time **ToS read**
   (the authoritative text couldn't be fetched headless; the documented-public-endpoint anchor is confirmed).
   It is the only clock that can't restart, and it now also supplies the **event-sufficiency** answer and the
   **real-data certification** data. `python spike/s0.4/ws_recorder.py --max-days 30` after `pip install websockets`.
2. **B-capture reader** — the one thin connector from B-JSONL (`{"recv_ts", "msg":{last_trade_price, timestamp(ms), asset_id}}`)
   → event times → `certify_granularity`. Deliberately not built yet (don't guess premature data-layer structure;
   schema is confirmed in the B-verification writedown). Add when B data lands.
3. **Real-data certification** — run `certify_granularity` on captured B data per market: small `|diff|` certifies
   2 s block-time loses no n̂ there. This is the remaining S0.4 risk.
4. **S0.2 — near-critical event-count floor** (synthetic estimator-stability sims). Now the operative limit.
5. **Held A-side tasks 5/6/8** (Dune query, `/prices-history` probe, RUN/memo) — tidy when **activating** A-side
   for historical certification, not for their own sake (on-chain permanence makes holding free).
6. **Branch integration** — this branch now spans spike + Stage-1 + production. Decide merge-to-`main` (it has
   real `critaudit` features) vs continue here. `git user: tyy0811`; main is the usual PR base.

---

## Working context for the new session
- The methodology that made the verdict trustworthy is in `MEMORY.md` → `anchor-each-component-before-reliance.md`
  (+ `measure-before-amending`, `result-blind-rule-selection`): validate each pipeline stage on its own output
  before reliance; track the best-achievable reference not the ideal; hard-corner-first; capability-block ≠
  decision-hold. The user enforces these hard — match that rigor.
- `~/.claude/CLAUDE.md` pre-flight checklist applies to any expensive compute (the MCEM near-critical sweeps
  are O(N²·M) and slow — bound N, hard-corner-first).
- The user drives cross-review (Claude/ChatGPT/human) on load-bearing calls; surface forks, don't barrel.

### Paste into the new session
> Read `docs/superpowers/HANDOFF-s0.4-stage1.md` and the two 2026-06-16 "qualified-G1" entries in
> `DECISIONS.md` (the spike branch `s0.4-data-feasibility-spike` is already checked out). S0.4 granularity is
> resolved — A viable, the within-bin estimator is promoted to `critaudit.hawkes.binned`. I want to
> [pick: "add the B-capture reader and wire up the real-data certification path" OR "start S0.2, the
> near-critical event-count floor" OR "decide branch integration / merge to main"]. Hold the standing
> disciplines (anchor-each-component, result-blind DECISIONS, never commit `verification/adv_*.py`).

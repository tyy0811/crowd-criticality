# Sub-increment 1 (LLM harness) — Task-10 reference-cohort writedown

**Date:** 2026-07-14 · **Branch:** `stage2-llm-harness-phaseB` · **Cohort closeout:** `9d95aa0` · **Plan:** Task 10 Steps 4–5
(The plan text names this file `2026-06-27_subinc1_writedown.md` — the plan-authoring date; it is dated here
by the actual run date per repo convention. Cosmetic deviation, recorded.)

## Pre-flight (written BEFORE the GPU launch, per the owner's global pre-flight checklist)

The checklist is written for GPU *training* runs; the checks below are its analogues for a paid inference
cohort. Checks 1–4 pass on recorded evidence; check 5 runs FIRST inside the GPU window and its observed
numbers are appended below before the cohort proceeds. Fail rule: the positive control is fail-closed —
a failing seed STOPS the cohort (finding, logged not relaxed); teardown is unconditional on every path.

**1. Data inspection (actual values, not documented ones) — PASS.**
Task-9 endpoint smoke (real vLLM traffic, A10): 6 events, all four emit types parsed
(create_post 3 / create_comment 1 / repost 1 / quote_post 1); export well-formed: events=6, parents=3,
read_emit_successes=3, ratio=0.5000, zero raises. Construction-half $0 integration test (installed
camel-oasis 0.2.5, no LLM): DB follow rows == M(6)=3 exactly (crowd-only, no self-loops), news posts land
per the drawn schedule (author user_id = n_agents), zero crowd LLM traffic.

**2. Round-trip analogue (normalize/denormalize → export invariants) — PASS.**
`export_harness_run` output satisfies every `post_reply_tree` invariant by construction (fail-closed both
sides); the committed real-trace fixture regression (7 events / 4 parents / 3 successes / ratio 3/7) is
green in the current suite (116 passed / 34 deselected).

**3. Metric sanity (known cases) — PASS.**
`check_positive_control` on known inputs: coupled fixture clears all four thresholds with recorded margins
(frac_size1 0.000 ≤ 0.95; giant_frac 0.667 ≤ 0.90; read_emit_ratio 0.667 > 0.01; length_spread 3.184 > 1.0);
degenerate all-size-1 trips (3 of 4); giant-only fixture trips exactly MAX_GIANT_FRAC (failure path
power-checked: transient MAX_GIANT_FRAC=2.0 → DID NOT RAISE); empty run raises the labelled guard.

**4. Reference reproduction — PASS.**
The banked Task-1 fixture values reproduce through the current adapter (regression test green);
D0-under-vLLM PASSED on this exact serving config (hermes parser, structured tool call) in Task 9.

**5. Tiny smoke through the NEW driver (the one untested seam) — RUN FIRST IN-WINDOW; results appended below.**
Config: `run_oasis_minimal`, 6 agents / 3 rounds / density 0.10 / news 0.05 / social_influence 3,
seed 424242 (deliberately NOT a cohort seed), live endpoint. Verifies: completes; follow rows == M(6)=3;
token_counts nonzero and plausible; emits parse; export well-formed. This is a plumbing check on a toy
config — no positive control applied, no quantity interpreted.

## Registered effective substrate (pre-run record)

- **Model:** `Qwen/Qwen2.5-7B-Instruct` @ revision `a09a35458c702b33eeacc393d103063234e8bc28`
  (harness_spec.MODEL_REVISION == modal_serve.SERVED_REVISION, drift-tripwired).
- **Serving:** Modal A10 ×1, vllm==0.21.0, `--enable-auto-tool-choice --tool-call-parser hermes
  --dtype bfloat16 --max-model-len 8192 --gpu-memory-utilization 0.92 --api-key <secret>`,
  `--served-model-name` = MODEL_ID; caps: timeout 6h / scaledown 5min / startup 15min / max_containers 1 /
  @modal.concurrent(64). App `critaudit-harness-vllm`; weights cached in Modal volumes.
- **Client:** CAMEL `OPENAI_COMPATIBLE_MODEL`, timeout 600 s, `max_tokens = COHORT_MAX_TOKENS = 4096`
  (frozen instrument constant; 512 measured to truncate prompts), `temperature = 0.7` (Task-1 fixture-config
  precedent, DECISIONS 2026-06-30).
- **Platform:** `recsys_type = RECSYS_TYPE = "random"` (frozen; reddit kills follow feed + clock; "twitter"
  variant carries a verified rec-matrix indexing defect; twhin-bert adds an embedding substrate);
  `refresh_rec_post_count = OPERATING_POINT["social_influence"] = 3` (the coupling knob);
  `max_rec_post_len = 5` (must exceed the knob — OASIS default 2 would silently cap it; largest shipped value);
  **`following_post_count = 3` — OASIS library default, NOT spec-registered (review hygiene note): registered
  HERE pre-run as part of the effective substrate; explicit spec registration deferred to the sweep increment.**
  camel-oasis 0.2.5 (venv-pinned).
- **Crowd/graph/news (frozen rules, discharged 2026-07-14):** 50 LLM agents + 1 model-free manual news user
  (id 50, zero followers, fail-closed sentinel model — any inference call raises); follow edges exact-count
  directed G(n,M), M = round(0.10·50·49) = 245, awaited `SocialAction.follow` post-reset/pre-round-1
  (DB `follow` table = the realized graph); news Bernoulli(0.05)/round ≤1, content from the frozen 12-string
  pool; streams: graph/schedule/content = SeedSequence(seed).spawn 0/1/2. Minimal action space per design §3.
- **Cohort:** `COHORT_SEEDS = (20260627, 20260628, 20260629)`, `OPERATING_POINT` = {n_agents 50, n_rounds 20,
  network_density 0.10, news_rate 0.05, social_influence 3}; per-seed: export → `check_positive_control`
  (fail-closed) → diagnostics + token counts.
- **Known substrate nondeterminism (recorded, input-side):** server-side recsys sampling uses unseeded stdlib
  RNG (OASIS internals); LLM at temperature 0.7. Construction inputs (graph/schedule/content) are
  seed-deterministic. Seed 20260627 draws 0 news injections over 20 rounds (P≈0.36 — plausible Bernoulli
  outcome, NOT reseeded; that seed's positive control rests on spontaneous crowd posting alone and fails
  closed if the crowd is quiet).

## Check-5 (mini-smoke) observed results

**PASS (2026-07-14 15:32 UTC, in-window, before the cohort).** seed 424242, 6 agents / 3 rounds, live A10
endpoint. Completed in 178.5 s. **DB follow rows = 3 == M(6) exactly.** token_counts = {prompt 21408,
completion 508, total 21916, n_calls 18} — nonzero and plausible (n_calls = 6×3 exactly; ~1.19k prompt /
~28 completion tokens per call). LLM emits parse: {create_comment: 5, create_post: 3} (plus do_nothing 10,
follow 3 = the construction edges, refresh 6, sign_up 7 = 6 crowd + news user). `export_harness_run`
well-formed, zero raises: events=8, parents=5, read_emit_successes=5, ratio=0.6250, content_len=8.
Verdicts: follow==3 TRUE | tokens nonzero TRUE | emits parse TRUE | export OK TRUE → **cohort may proceed.**

## Cohort results (per seed)

**PARTIAL: 1 of 3 seeds completed; window stopped at the cap (details + instrument finding below and in
`.superpowers/sdd/task10-cohort-report.md`). Nothing retried, no knob changed, no reseeding.**

- **seed 20260627 — COMPLETED; positive control PASS** (recomputed locally from the trace DB after
  teardown; the in-window check also passed implicitly — the driver only proceeds past a seed on PASS).
  n_events = 132 · frac_size1 = 0.2174 (≤0.95) · giant_frac = 0.1364 (≤0.90) · read_emit_ratio = 0.7955
  (>0.01) · length_spread = 31.171 (>1.0). token_counts = {prompt 326529, completion 6938, total 333467,
  n_calls 167}. Wall-clock 3407.3 s (56.8 min). Construction verified: follow rows = 245 = M(50) exact;
  news posts = 0 (the pre-registered plausible Bernoulli outcome for this seed — recorded, not reseeded).
  Emit mix: create_comment 94 / create_post 23 / quote_post 13 / repost 2 (+ do_nothing 32).
- **seed 20260628 — NOT COMPLETED (run stopped ~3.3 min in, before meaningful output; partial DB is a
  discard artifact).** Stopped by the window-cap rule, not by any failure of the seed.
- **seed 20260629 — NOT RUN** (window cap).

**@slow-test assertions on the captured results (test itself NOT re-run against the endpoint):**
`len(results) == 3` → **FALSE (1/3, partial window)**; `read_emit_ratio > 0.0` → TRUE for the one
completed seed. The @slow cohort test CANNOT pass on this window's output.

**INSTRUMENT FINDING (root-caused from the full log, verbatim evidence; found AFTER teardown, nothing
tuned):** seed-1's crowd emitted only in rounds 0–4 (18/48/49/14/3 events), then ZERO for rounds 5–19:
1021 caught-and-logged per-turn errors, all `Error code: 400 — "This model's maximum context length is
8192 tokens. However, you requested 4096 output tokens and your prompt is …"`. Mechanism: CAMEL sets the
agent context budget = `max_tokens` (= frozen COHORT_MAX_TOKENS = 4096), so truncated prompts approach
4096 as agent memory grows, and once `prompt + 4096 > 8192` (server `--max-model-len`) EVERY later call
for that agent 400s — OASIS catches per-turn and continues silently. Net: the frozen n_rounds = 20
realized ~5 effective LLM rounds; late rounds were retry grind (round 18→20 cadence ~4 min each), which
also explains n_calls = 167 (successful completions only) and the 56.8-min seed wall-clock. The positive
control measures coupling/accessibility (which the 5 effective rounds cleared decisively), not horizon
realization — the PASS stands as recorded, but the substrate under-delivered the registered horizon.
Resolution touches frozen/registered surfaces (COHORT_MAX_TOKENS and/or the serving config) → owner
decision required before any re-run; measure-before-amending applies.

## GPU cost

Window 2 (this run): start 15:19:37Z (deploy) → stop 16:39:06Z = **79 min 29 s = 4769 s** wall, under the
100-min cap. Upper-bound estimate 4769 × $0.000306 ≈ **$1.46** (readiness ~2.6 min on cached weights;
traffic was near-continuous, so billed GPU-container time ≈ the window). In-window segments: check-5
178.5 s; seed-1 3407.3 s; seed-2 aborted ~3.3 min. **Modal dashboard is the authoritative spend figure.**

**Safety-rail note (first live firing):** the window-cap rule + unconditional-teardown discipline fired
exactly as designed on seed 2 — the driver was stopped at a seed boundary once a ~57-min seed provably
could not fit the remaining 29 min, the partial DB was declared a discard artifact, teardown was verified
(`stopped`, 0 tasks), and all diagnosis happened after the meter closed. Recorded with satisfaction.

## Amendment — context-wall correction, owner-ratified 2026-07-14 (repaired instrument)

**Ratification (owner, 2026-07-14):** decoupling RIGHT; seed-1's PASS = a pass of the WRONG experiment
(5 effective rounds of a registered 20) → **recorded, not banked**; all three seeds re-run on the repaired
instrument; seed-1 preserved above as the finding that exposed the wall. Corrections applied before the
freeze: the completion cap anchored on the observed TAIL (not mean-multiples), the overhead term MEASURED
(the 1,021 rejection bodies are censored at the validation threshold — all `value=4097` — so the
measurement is constructive), two guards landed pre-GPU, and the finite-memory-horizon property declared.

**Measured anchors (amendment commit `cb4fc61`; measurements offline/$0, independently reproduced to the
digit in review):**
- `COHORT_MAX_TOKENS: 4096 → 512` — all 164 seed-1 completions reconstructed in hermes form and tokenized
  at the pinned revision: mean 41.3 / p99 56.1 / **max 59** → 512 clears the observed max by **8.7×**.
- `COHORT_CONTEXT_BUDGET = 5632` (new; decoupled memory window via a driver-side `token_limit` override) —
  constructive overhead measurement: client counter = OpenAITokenCounter(GPT_4O_MINI)/o200k regardless of
  the Qwen model string; **overhead_max = 1731** (worst shape: OASIS-like rounds with 19 tool-call turns —
  the client counter under-counts tool-call turns by ~51 tokens each; decomposition 696 tool-schema +
  51/turn + 1/msg + 2.37% content). Derivation: 6144+1731+512+256 = 8643 > 8192 **FAIL** →
  5632+1731+512+256 = 8131 ≤ 8192 **PASS** (256 = declared safety slack, the one non-measured term).
  `OVERHEAD_MAX_MEASURED = 1731` registered as a frozen constant; consumed guard enforces the full
  overhead-inclusive inequality.
- The original 4096 was authored under the then-unknown coupling constraint (CAMEL hardwires
  `token_limit` to `max_tokens`, base_model.py:530-542) — correction-by-provenance, same shape as the
  pairing-rule amendment; no gate quantity anywhere in the anchor reasoning.

**Guards (both landed + tested pre-GPU):** (1) loud-400 — server rejections are counted at the driver's
model layer and re-raised; `run_oasis_minimal` fails at the FIRST rejection (per-round check + final
assert) instead of completing a plausible-looking degraded artifact; test drives the real async path.
(2) decoupling tripwire — a unit test pins `token_limit == COHORT_CONTEXT_BUDGET ≠ max_tokens ==
COHORT_MAX_TOKENS`, so a future camel upgrade that re-couples the knobs fails loudly (covers the smoke
gap at the mechanism level: 2-3-round smokes structurally cannot reach the wall).

**FINITE-MEMORY-HORIZON (declared substrate property, same status as the exposure-volume caveat):** with
a 5632-token memory budget, late-round agents truncate their oldest messages — the crowd has a finite
memory horizon by construction. Memory truncation can plausibly shape cascade statistics (agents
forgetting early posts changes what they can reply to); declared now as an assumption surface of the
operating point so it cannot surface later as an unrecorded confound.

**Raw-artifact location (durable, uncommitted):** registered trace DBs, result/usage JSONs, runner
logs/scripts, the window-2 broken-instrument evidence, and the two anchor-measurement scripts are
archived under `~/crowd-crit-runs/s2_harness_subinc1/` (the session scratchpad is volatile tmp; trace
DBs are run artifacts, never committed — repo convention).

## Cohort results — repaired instrument (per seed)

**Window A (2026-07-14, seed 20260627): SEED NOT COMPLETED — runner killed EXTERNALLY at ~round 18/20
by the session harness's background-task lifetime (~64 min), NOT by the endpoint, the guard, or the
control. Instrument-repair evidence from the run is decisive; the registered seed measurement remains
pending (re-run in a fresh window with a detached runner).**

- **Repaired-instrument validation (the window's primary check) — CONFIRMED on 18 rounds:**
  emit-by-round = {0:16, 1:49, 2:49, 3:50, 4:49, 5:50, 6:48, 7:46, 8:42, 9:37, 10:28, 11:31, 12:31,
  13:29, 14:28, 15:31, 16:31, 17:1(kill mid-round)} — **every round active, 646 emits** (broken
  instrument: dead after round 4, 132 emits). **Rejections = 0 through round 17, guard-enforced**
  (the loud-400 guard checks after every round and raised nothing; the failure was an external
  SIGKILL). Context budget LIVE in the log: `Context truncation performed: … after=5631, limit=5632`.
- Construction: follow rows = 245 = M(50) exact; news posts = 0 (same registered Bernoulli outcome).
  Emit mix (through the kill): comment 291 / quote 279 / post 76 / repost 0 (+do_nothing 66).
- **Post-hoc control on the TRUNCATED artifact (labelled — NOT the registered measurement):** PASS —
  frac_size1 0.5263 ≤ 0.95 · giant_frac 0.2430 ≤ 0.90 · read_emit_ratio 0.5046 > 0.01 ·
  length_spread 35.619 > 1.0 · n_events 646.
- **Live anchor stats (max/p99 completion vs 512; max prompt vs 5632+1731): NOT CAPTURED — the
  per-call usage_log lived in the killed process's memory.** To capture next window regardless of
  kill timing, the runner should flush usage_log to disk incrementally. Zero rejections through 17
  rounds already bounds the sum anchor live (no `prompt + 512 > 8192` ever occurred).
- Wall: rounds 1-17 in ~57 min (round cadence ~40 s early → ~5-6 min late as prompts fill the budget;
  a full 20-round seed projects ~70-80 min — window B/C cap sizing should assume the top of that).
- **Orchestration fix for windows B/C (recorded):** launch the seed runner DETACHED (`nohup`/`setsid`,
  writing log+JSON to disk) so it survives harness background-task reaping; the session only polls files.

- **Seed 20260627 (window A′, REGISTERED) — 2026-07-14/15, detached runner (pid 5234), status
  `SEED_COMPLETE_CONTROL_PASS`, instrument `repaired@140dce9`:**
  - Positive control: **PASS** — frac_size1 0.4765625 · giant_frac 0.14705882352941177 ·
    read_emit_ratio 0.43983957219251335 · length_spread 38.232342169432776.
  - n_events = 748 (20/20 rounds with activity).
  - emit-by-round = {0:14, 1:50, 2:49, 3:49, 4:48, 5:47, 6:47, 7:43, 8:41, 9:38, 10:38, 11:32,
    12:38, 13:30, 14:26, 15:37, 16:33, 17:30, 18:28, 19:30}.
  - Rejections = 0 (n_calls 1000, loud-400 guard raised nothing).
  - Live anchor validation: completion max 212 / p99 176 vs cap 512; prompt max 6947 / p99 6914
    vs anchor 7363 (= 5632+1731). All under.
  - Tokens: prompt 5,938,344 / completion 58,824 / total 5,997,168 / n_calls 1000.
  - Wall-clock: 6308.2 s (105.1 min), runner 20:59:04Z → 22:44:36Z.
  - Construction: follow rows 245 = M(50) exact; news posts 0; trace actions: comment 322 /
    quote 289 / post 128 / repost 9 / follow 245 / refresh 615 / do_nothing 71 / sign_up 51.
  - DB: scratchpad `cohortA2/seed_20260627/oasis.db`; final JSON `windowA2_result.json`.
  - **Window A′ cost:** 20:45:22Z (deploy) → ~22:45:00Z (stop verified; `modal app list` →
    stopped, Tasks 0) = ~7178 s ≈ **$2.20 upper bound** at $0.000306/s (A10). Dashboard authoritative.

## GPU cost — repaired-instrument windows

- **Window A:** 19:21:18Z (deploy) → 20:30:40Z (stop verified; `modal app list` → stopped, Tasks 0) =
  **69 min 22 s = 4162 s** ≈ **$1.27 upper bound** at $0.000306/s (readiness 2.7 min on cached weights;
  teardown within ~1 min of the kill notification). Dashboard authoritative.
  Cumulative Phase-B upper bound ≈ $3.21 (windows 1+2+A).

**Seed 20260628 (window B′, REGISTERED) — SEED_COMPLETE_CONTROL_PASS (2026-07-15).**
Positive control PASS: frac_size1 0.4752 (≤0.95) · giant_frac 0.1369 (≤0.90) · read_emit_ratio 0.5000
(>0.01) · length_spread 44.61 (>1.0). n_events = 672; all 20/20 rounds active (emit-by-round: 14, 49, 46,
48, 48, 48, 47, 43, 37, 35, 31, 29, 28, 23, 24, 24, 25, 24, 27, 21). Rejections = 0 (1000 calls,
loud-400 guard silent). Live anchors: completion max 277 / p99 175 vs cap 512 (margin 1.85× — the live
tail has grown across seeds: 200 → 277; cap still clears with real margin, recorded for the sweep's
re-anchor trigger) · prompt max 6953 / p99 6896 vs anchor 7363. Tokens {prompt 5,941,652, completion
60,069, total 6,001,721, n_calls 1000}. News posts (user 50): 1. Runner wall 87 min (natural exit);
window ≈ 91 min ≈ $1.67 (A10, dashboard authoritative). NOTE (ops, not science): this seed is the RE-RUN
after the overnight scratchpad wipe destroyed window B's artifacts pre-read — recorded in the ledger;
first-run outputs were never seen, so no selection channel exists. Raw artifacts:
~/crowd-crit-runs/s2_harness_subinc1/windowB2_seed20260628/.

**Seed 20260629 (window C, REGISTERED) — SEED_COMPLETE_CONTROL_PASS (2026-07-15).**
Positive control PASS: frac_size1 0.5167 (≤0.95) · giant_frac 0.2141 (≤0.90) · read_emit_ratio 0.5196
(>0.01) · length_spread 42.43 (>1.0). n_events = 766; all 20/20 rounds active (emit-by-round: 17, 50, 50,
49, 48, 47, 47, 45, 44, 41, 37, 42, 37, 37, 27, 30, 33, 31, 25, 29). Rejections = 0 (1000 calls). Live
anchors: completion max 245 / p99 185 vs cap 512 · prompt max 6916 / p99 6912 vs anchor 7363. Tokens
{prompt 5,916,892, completion 57,251, total 5,974,143, n_calls 1000}. News posts (user 50): 0. Runner
wall 96 min (natural exit); window ≈ 102 min ≈ $1.87 (A10, dashboard authoritative). Raw artifacts:
~/crowd-crit-runs/s2_harness_subinc1/windowC_seed20260629/.

## Cohort summary (repaired instrument) — 3/3 REGISTERED PASSES

All three frozen seeds clear the fail-closed positive control at the frozen operating point with margin
on every threshold: read_emit_ratio 0.4398 / 0.5000 / 0.5196 (floor 0.01) · frac_size1 0.4766 / 0.4752 /
0.5167 (max 0.95) · giant_frac 0.1471 / 0.1369 / 0.2141 (max 0.90) · length_spread 38.23 / 44.61 / 42.43
(floor 1.0). n_events 748 / 672 / 766; every seed 20/20 effective rounds; **0 server rejections across
all 3,000 registered calls** (loud-400 guard silent — the context-wall amendment held live in all three
windows). @slow-test assertions verified on the registered set: len == 3 TRUE; every ratio > 0 TRUE.
News draws per frozen schedule: 0 / 1 / 0. Completion-tail watch across seeds: live max 212 / 277 /
245 vs cap 512 (worst margin 1.85×) — the amendment's re-anchor trigger (re-run Measurement 1; never an
ad-hoc lift) fires if a future run approaches the cap. **Scope: this validates read→emit ACCESSIBILITY +
genuine coupling of the reference crowd ONLY — no regime claim, no crosses-1 n_emit claim (deferred,
design §2/§12), and all cascade-statistic interpretation downstream inherits the declared
FINITE-MEMORY-HORIZON property.**

## GPU cost — repaired-instrument windows (upper-bound estimates; Modal dashboard authoritative)

Window A (killed run): $1.27 · Window A′ (seed 1 registered): $2.20 · Window B (lost to scratchpad
wipe pre-read): ≈$2 bounded by scaledown, dashboard authoritative · Window B′ (seed 2 registered):
$1.67 · Window C (seed 3 registered): $1.87. Phase-B GPU total incl. Task 9 + the broken-instrument
window: ≈ **$11 upper bound of the $60 budget**. Cohort token total (registered runs): 17,973,032
across exactly 3,000 calls.

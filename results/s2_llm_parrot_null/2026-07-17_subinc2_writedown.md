# Sub-increment 2 (matched parrot null) — writedown

**Date:** 2026-07-17 · **Branch:** `stage2-llm-parrot-null` (off `origin/main` @ `aa32f76`) ·
**Design:** `docs/superpowers/specs/2026-07-17-llm-parrot-null-subinc2-design.md` (untracked per repo
convention; SHA-256 `5805d702…e5e2be` pinned in `llm_parrot_spec.DESIGN_DOC_SHA256`, hash-guarded).
**$0 increment:** everything below ran local CPU against the durable archive
(`~/crowd-crit-runs/s2_harness_subinc1/`); no GPU, no LLM call, no network (embedding revision cached).

> **Post-review amendment:** Sections 2–7 preserve the original construction-v1 record. Section 8
> is authoritative for definition #2: v1 is superseded, construction v2 is calibration-blocked,
> and the v1 `n_struct` band is descriptive legacy evidence only.

**Freeze-before-measurement spine (git-visible):** T3 freeze `f4bfac4` (+ T1 spec, hash-pinned) strictly
precedes the T5 calibration `ab3ac59` and the T7 band `10fbfc2`. The θ-calibration PROCEDURE and every
constant were frozen before the first cohort measurement ran; θ itself is the procedure's measured
output, banked not frozen. No frozen rule was changed after seeing any result.

## 1. Authored-content correction (T2, `90eff2d`) — prerequisite, registered

Owner-flagged; verified against all 3 archived DBs + the committed fixture; corrected registered
spreads **39.0131 / 40.7699 / 38.8229** reproduced to the digit by two independent implementations;
every registered PASS unchanged; all other diagnostics bit-identical. Full record: the 2026-07-17
amendment in `results/s2_harness/2026-07-14_subinc1_writedown.md` + DECISIONS. All sub-inc-2 marginals
below are computed on AUTHORED text.

## 2. Registered instruments (frozen surface, `llm_parrot_spec.py`)

- **Embedding:** `sentence-transformers/all-MiniLM-L6-v2` @ `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`,
  CPU/float32/L2/batch-32 stream-order/1 torch thread; cosines rounded to 6 dp before every θ
  comparison. NEWS_POOL determinism anchor `08c6859d…` (@slow). Per-window authored-pool embedding
  checksums (banked): A′ `8211c441…` · B′ `d7b1d7be…` · C `c1e797be…`.
- **Calibration procedure:** attribution-Youden, grid 0.01…0.99 step 0.005 (197 pts), ties→largest,
  strictly-earlier-round candidates; pooled denominators over the three registered windows
  (candidates never cross windows).
- **Null construction:** `NULL_BASE_SEED = 20260717`, 64 seeds, round-robin windows (22/21/21,
  cohort-seed ascending); per-round counts copied exactly; content = with-replacement resample of the
  window's authored pool; embeddings looked up by pool index; `read_emit_success ≡ all-False`; no agent
  identity. Do-not-match list untouched (branching / avalanche sizes / per-agent rates never matched).
- **`FOLLOWING_POST_COUNT = 3`** registered (sub-inc-1 deferred obligation discharged) and passed
  explicitly to `Platform`.

## 3. θ calibration (T5, banked `2026-07-17_theta_calibration.json`) — **INSTRUMENT FINDING**

Pools: 1,837 true-edged children / 349 true roots over 2,186 events (A′ 620/128 · B′ 571/101 ·
C 646/120). `same_round_ceiling = 0.0` — every true edge is cross-round (consistent with OASIS
round-r-readable-from-r+1).

**The frozen criterion never goes positive.** J = TPR − FPR < 0 at every grid point, monotone toward
the edge: J(0.50) = −0.779 · J(0.70) = −0.698 · J(0.90) = −0.388 · J(0.95) = −0.289 ·
**J(0.99) = −0.183 (unique max → θ\* = 0.99; the tie rule never fired).** At θ\*: pooled TPR = 0.0201,
FPR = 0.2034; per-window TPR 0.032/0.010/0.017, FPR 0.172/0.168/0.267. Pairwise AUC = 0.693.

**Diagnosis (probe-verified before acceptance; bug ruled out):** the true-parent signal EXISTS —
cos(child, true parent) median 0.570 vs 0.364 random-earlier, direction right, AUC 0.69 — but the
crowd is so topically homogeneous that the true parent is beaten by a median ~21 % of candidates:
argmax recovery collapses to 2 %. Simultaneously, enough near-duplicate content exists (0.72 % of
pairs ≥ 0.99) that even the strictest threshold manufactures parents on 1-in-5 true roots.

**Reading (logged not relaxed; frozen procedure untouched):** embedding-similarity argmax attribution
CANNOT recover true reply structure in this crowd. θ\* = 0.99 is carried into T6/T7 per the frozen
chain. Two implications flagged for owner review: (a) cascade-def-#2 at θ\* attributes only
near-duplicates — the §9b `n_emit` (frozen composition, unevaluated) will inherit this; (b) the
artifact channel the sharp test exists to quantify is REAL and measured — content statistics alone
attribute plausible parents at material rates.

## 4. The 64-seed n_struct band (T7, banked `2026-07-17_nstruct_band.json`) — **BANKED RESULT**

All 64 seeds generated and gated fail-closed — **0 gate failures** (decoupling tripwire 0 everywhere;
counts exact-copy; KS ∈ [0.012, 0.063] vs bound 0.155; mean-embed-cos ≥ 0.99701).

**Band: the matched null manufactures `n_struct` ∈ [0.5160, 0.5997] (median 0.555) from content
statistics alone — zero belief coupling.** Edge (frozen reading, `SWEEP_BAND_EDGE="max"`):
**0.5997**; q95 (recorded softer reference): 0.5888. Per-window medians/maxima: A′ 0.539/0.567 ·
B′ 0.579/0.600 · C 0.552/0.574.

Reference points (named-apart, no comparison criterion asserted here): collapse parrot `n_struct = 0`
exactly (immigrant-only); cohort TRUE-link `n_struct` ≈ 0.829/0.850/0.843. Mechanism note (disclosed,
by construction): a with-replacement parrot REPEATS texts — exact self-duplicates plus near-duplicate
crowd content attribute under θ\* = 0.99; that is the matched-marginal artifact channel itself, not a
defect. Recorded-not-asserted structure diagnostics: burstiness 0.708–0.725; Fano medians 2.3/4.1/7.9
at scales 1/4/10 rounds (super-Poisson by construction — the copied ramp).

## 5. SCOPE (the §9 embargo held)

**`n_struct` only.** No τ-arm ran on any matched-null output; no cascade-def-#2 quantity (structure,
τ, `n_emit`) was computed on the LLM cohort; the §9a sharp-test criterion (`NULL_TAU_FRAC_MAX = 0.05`,
band-not-passes) and the §9b `n_emit` definition are frozen, unevaluated, and structurally firewalled
(`tests/test_llm_parrot_firewall.py`: AST scan power-checked against a known violator, banked-JSON
schema guard, `CohortMarginals` two-field whitelist). Both execute in sub-inc 3 against the criteria
frozen at `f4bfac4`. No regime claim, no criticality claim, no artifact-gate verdict is made here.

## 6. Verification & reproducibility

Fast suite **166 passed** (`-m "not slow"`, torch-free). $0 slow subset **6 passed**: corrected-exporter
archive regression (spreads to 2 dp, PASS unchanged), embedding-pin determinism ×3, calibration
byte-reproduction, band byte-reproduction — both banked JSONs regenerate **byte-identically** from the
archive through the pinned realization (environment drift fails loudly; re-bank consciously).
Runtimes: calibration ~51 s; band ~36 s (local CPU, post-review single-pass refactor).

**Whole-branch review pass (2026-07-17, 8-angle multi-agent + fixes applied same-day).** Verified
findings fixed, none touching a frozen rule or a banked value: the isolation gate's bare `assert`s
converted to explicit `raise AssertionError` (the `positive_control.py` idiom — bare asserts are
stripped under `python -O`, silently disabling a fail-closed gate); gate round-granularity validated
before count binning (truncation could fold a corrupted clock back into an "exact" match);
`_authored_content` tightened (repost `quote_content` NULL-contract; traceless-row `quote_content`
fail-open corner closed) with power checks; per-stream no-true-edges guard restored in the pooled
calibration (a degraded all-roots window must fail loudly, not contribute silent FPR mass);
`test_embedding_pin` no longer imports torch at collection (a broken-torch interpreter aborted the
whole suite); childless-root-through-SQL export coverage restored; firewall scan set now
self-discovers modules importing the sub-inc-2 surface (the hand-maintained list was a completeness
hole); banked-JSON writer refuses NaN; banked-path constants single-sourced from the driver; shared
`roots_from_parents`/`round_indices` helpers (root/round semantics single-homed across cohort and
null paths); `_midranks` → `scipy.stats.rankdata`; calibration AUC computed from the same per-round
cosine blocks as attribution (one candidate-rule home, ~2× faster). **Refactor byte-safety proven:
the post-refactor calibration regenerates the committed T5 artifact byte-identically.** The band
JSON was re-banked once for one additive provenance field (`windows_source: "archive"` — a synthetic
band can no longer masquerade as the registered artifact); all 64 `n_struct` values, the max edge,
and the q95 are unchanged to the last digit. Deferred to the owner (design consideration, frozen
surfaces untouched): carrying the OASIS action as a first-class event-type field (reposts are
currently `''`-content events; under def-#2 all `''` texts embed identically, so resampled `''`
events chain deterministically — one disclosed component of the manufactured-duplicate mechanism);
the non-editable-install path residual (registered substrate is the editable checkout).

## 7. Flagged for owner ratification (design §9 + the T5 finding)

1. **Band-edge reading** — max (0.5997) = gate edge, q95 (0.5888) recorded (recommended, implemented).
2. **Window assignment** — round-robin 22/21/21 (implemented; 3×64 alternative disclosed in design).
3. **§9b `n_emit` definition** — pairing rule ∘ calibrated θ\*, no new knob (most needs sign-off,
   especially given the θ finding).
4. **The θ finding itself** (§3): whether sub-inc 3 proceeds with def-#2 at θ\* = 0.99 as frozen, or
   the owner treats J < 0-everywhere as a calibration-does-not-discriminate block on the def-#2 arm
   (a measure-before-amending call that belongs to the owner, not this increment).

## 8. Post-review definition-#2 contract repair and owner ratification

**Contract repaired.** Construction v1 optimized exact-parent Youden over all prior rounds. That did
not implement `PRE_REGISTRATION.md` §5.2, which requires recovery of known **cascade membership** from
a recent active-cascade event within finite window `w`. Construction v2 jointly searches every
attainable registered round window `w = 1…19` and `θ = 0.01…1.00` by 0.005. For each pair it computes
ARI between recovered single-membership/no-merge labels and true `root_id` separately per registered
seed, then selects maximum equal-seed mean ARI; ties choose smaller `w`, then larger `θ`. Certification
requires the existing Gate-D floor, mean ARI ≥ 0.90. The complete surface and status are banked in
`2026-07-17_theta_calibration.json` as `similarity_calibration`, construction version 2.

**Measured status: FAILED, not a least-bad usable rule.** The best diagnostic pair is `w = 7`,
`θ = 0.745`, mean ARI **0.2496735**; per-seed ARIs are **0.1877983 / 0.3566462 / 0.2045759**. Every
registered consumer verifies the artifact/design/spec identity, recomputes its selected pair and
status from the complete surface, and refuses a non-passing record. Consequently definition #2 and
the downstream `n_emit` composition are **calibration-blocked**; the diagnostic pair is not banked as
a usable knob.

**Isolation gate hardened.** The gate now requires exact `(n,)` alignment for times, `root_id`,
`parent_idx`, and boolean `read_emit_success`, plus `len(content) = n`; rejects non-boolean cancellation
payloads, nonfinite/non-round times, malformed parent/root structure, malformed counts, nonfinite or
non-unit pool embeddings, and inconsistent embeddings for duplicate text. Exact-text, nonidentical,
and empty-endpoint attributed-edge counts are recorded for future bands.

**Resampling interpretation ratified; construction unchanged.** Uniform-with-replacement sampling is
the empirical-bootstrap **literal-parrot null**. It preserves empirical text atoms in expectation and
intentionally includes bootstrap-amplified exact repetitions; it is not a fixed-multiset permutation
null. Review decomposition of the legacy band found 24,953/25,970 attributed edges (96.1%) joined
byte-identical text, contributing 24,953/46,654 = 0.53485 to mean `n_struct`; nonidentical edges
contributed about 0.0218. A disclosed permutation sensitivity had median `n_struct = 0.3636` versus
about 0.555 for the registered bootstrap, confirming that replacement amplification is material and
part of this null's scope.

**Banking disposition.** The registered attribution construction changed, so the calibration artifact
was re-banked. Calibration failed, so **no construction-v2 `n_struct` band was generated or banked**.
The construction-v1 band remains byte-for-byte unchanged (SHA-256
`b559523b33f3a0c66bbd9b2dd7210d096092a3e6a9e95caf2d2040af10296ced`) and is explicitly
non-consumable legacy evidence. This resolves owner-ratification item 4 without relaxing Gate D.

# Pre-Registration — Crowd-Criticality (Stage 0)

**Title:** Branching-ratio criticality as the signature of skillful crowd forecasting: a pre-registered study on Polymarket and a matched LLM-agent crowd
**Author:** Jane Yeung
**Version:** v0.3 (incorporates Claude/ChatGPT cross-review round 2: mechanism statement and Murphy-decomposition secondary analysis, control-crowd artifact gate in §4f, H1c as TOST equivalence, uncertainty-aware Gate A.2, de-circularized critical-point identification, exploratory self-organization observable)
**Date drafted:** _[fill]_  **Date frozen:** _[fill — must precede any Stage-1 data interpretation]_
**Registration target:** OSF
**Status:** DRAFT — not yet frozen. Once frozen, deviations go only in §10, never by silent edit.

> Purpose: lock the hypotheses, data source, event definition, estimators, fitting protocol, and decision thresholds *before* seeing results. Pre-registration is the primary defence against the most common failure in self-organized-criticality claims — choosing, post hoc, the cascade definition, kernel, or fitting window that produces the "right" exponent.

---

## 0. Selection-rule principle (result-blind)

Every `[fill]` value below is governed by a **frozen selection rule that does not inspect the quantity of interest.** A selection rule MAY inspect: synthetic ground-truth data, held-out *non-outcome* data, event counts, and compute/runtime budgets. A selection rule MAY NOT inspect: the real-market branching ratio `n`, any avalanche exponent on real or simulated data, or any Brier-vs-`n` result. This is the deep form of pre-registration: the labels are not what we protect — the operational choices are.

---

## 1. Study information

**Research questions.**
1. What is the branching ratio `n` of real prediction-market (Polymarket) event dynamics under a non-stationary-baseline-corrected Hawkes model?
2. Does an LLM-agent social-simulation crowd (MiroFish/OASIS) exhibit a *tunable* critical point, evidenced by Hawkes `n`, avalanche exponents, and the crackling-noise scaling relation?
3. Is crowd forecasting skill (Brier/log-loss against resolved outcomes) optimized near criticality?

**Framing precision.** The claims below concern a *tuned* critical point, located by an order-parameter sweep, not self-organized criticality in the strict Bak sense; no hypothesis asserts that the crowd reaches `n = 1` without tuning. A self-organization observable is logged as exploratory in §6 and carries no confirmatory weight.

**Proposed mechanism (stated before any data are seen).** Forecasting skill decomposes (Murphy) into reliability and resolution, and the two place opposing demands on crowd dynamics. Resolution requires that dispersed private information propagate and integrate: in a subcritical crowd (`n` well below 1) belief-update cascades die before information held by few agents reaches the aggregate, so forecasts under-react and hug the prior. Reliability requires that noise not be amplified into consensus: in a supercritical crowd (`n` above 1) cascades self-sustain, herding decouples consensus from evidence, and forecasts overshoot. Near criticality the correlation length is maximal while cascades remain marginally finite, so the crowd integrates dispersed information without runaway amplification; the hypothesis is that the reliability-resolution trade-off is optimized near `n = 1`. The internal signature of this mechanism is pre-registered as a secondary analysis in §5.4 and §6.

**Hypotheses (decomposed — H1 is no longer bundled).**
- **H1a** — *interior optimum exists.* In the simulation sweep, Brier/log-loss as a function of `n` has an interior minimum that is **statistically distinguishable from both sweep endpoints** (pre-specified test in §6). A flat curve with a noisy dip does not satisfy H1a.
- **H1b** — *optimum is near-critical.* The interior minimum lies in the frozen near-critical band `n ∈ [0.9, 1.0)` (see §2).
- **H1c** (revised): *sim optimum matches the market, tested as equivalence, not as absence of difference.* Two one-sided tests (TOST) on `n_min`(sim) minus `n`(market, baseline-corrected) against equivalence margin `±delta` (selection rule in §6). A non-significant difference test alone is never reported as consistency. H1c can hold or fail independently of H2.
- **H2** — *the market is near-critical.* Baseline-corrected Polymarket `n ∈ [0.9, 1.0)`.
- **H3** (revised — coarse corroboration, not a fine test): *the scaling relation is not grossly violated.* The discrepancy `Δ = (α−1)/(τ−1) − 1/σνz` is small relative to the **measured resolution `Δ_min(N)`** at the candidate critical point (§6). Gate A.2's resolution is intrinsically coarse (Stage-0 measurement), so H3 **corroborates** the `n`-based criticality claim by confirming the scaling relation does not contradict it; it does not adjudicate near-critical gradations. The branching ratio `n` (§5.1) and Gate A.1 carry the criticality claim.

**Outcomes treated as first-class results (pre-committed to publication).**
- H1a fails (no distinguishable interior optimum) or H1b fails (optimum outside the band) → headline hypothesis falsified; negative result.
- H1c fails while H1a/H1b hold → "the LLM crowd is critically optimal but does not reproduce the real market's regime" — interesting and reportable.
- H1a/H1b hold but the Murphy internal signature (§6) fails → the Brier minimum is reported without the mechanistic interpretation; the mechanism is reported as unsupported.
- The Stage-2 artifact gate fails (exponents survive the parrot null, §4f) → no emergence claim; Stage 2 is reframed as a characterization of pipeline- and model-imposed statistics.
- H2 fails → reframe Stage 1 as "`n` varies with market regime and predicts Brier."
- H3 fails → power law without criticality; downshift to a dynamical-class characterization.

---

## 2. Regime definitions (branching ratio)

Bands are frozen before fitting. `n ≥ 0.7` is **not** treated as near-critical.

| Regime | Definition |
|---|---|
| Clearly subcritical | `n < 0.7` |
| Endogenous / reflexive | `0.7 ≤ n < 0.9` |
| Near-critical | `0.9 ≤ n < 1.0` |
| Unstable / supercritical | `n ≥ 1.0` (handled carefully; fitted Hawkes may be non-stationary) |

**Estimation hazard (acknowledged).** As `n → 1` from below, the Hawkes likelihood flattens and the MLE variance inflates — precisely the near-critical band of interest is where estimation is least precise. All near-band estimates are therefore subject to the wide-CI no-interpret rule (§6, Gate A.4).

---

## 3. Design

- **Observational arm (Stage 1):** point-process analysis of historical Polymarket event streams. No intervention.
- **Simulation arm (Stages 2–3):** controlled order-parameter sweep over a generative LLM-agent crowd; forecasting evaluation against resolved real-world outcomes on a fixed shared question set.
- **Control arm (Stage 2, artifact gate):** a classical opinion-dynamics ABM and a parrot null run through the identical estimation pipeline (§4f).

---

## 4. Data

### 4a. Data-source decision and validity gate (Stage 1) — decided in the Stage-0 feasibility spike

The convenient public API is **not** sufficient for tick-level point-process analysis of resolved markets: the CLOB `/prices-history` endpoint returns *aggregated price bars* `(t, p)`, and sub-12-hour granularity is unavailable for resolved/closed markets (documented limitation). The data source is therefore one of:

| Source | What it yields | Cost / limit |
|---|---|---|
| **A. On-chain Polygon reconstruction** | Settled trade fills with timestamps (à la Yang & Tsang 2026) | Substantial engineering; settlement (not quote) lifecycle; block-time granularity |
| **B. Live WebSocket capture** | Clean tick-level trades, self-recorded going forward | Must wait for resolution; pick short-horizon markets |
| **C. Paid third-party feed** | Minute price bars + L2 snapshots, **Aug 2025 onward only** | Bars not trades (price-move process); misses the 2024 election; cost |

The chosen source is `[fill: A / B / C, decided in Stage 0]`. It partly forces the event definition (§4b).

**Validity gate (must pass before any Hawkes interpretation):**
- [ ] Event timestamps resolve finer than `[fill]` for every market analyzed.
- [ ] Per-market event count ≥ sufficiency floor (§4c).
- [ ] The reconstructed stream reconciles against an independent reference (e.g., settled notional vs. known market totals) within tolerance `[fill]`.
- [ ] Wash-trade filter applied (§4d).
- **If the gate fails:** the Stage-1 deliverable becomes a **data-validity / microstructure-reconstruction technical report** (this is now the *expected* pre-PhD artifact, not a fallback). Hawkes analysis moves to early PhD.

### 4b. Event definition for the point process — frozen

The Hawkes process counts `[fill, governed by source]`:
- **Trade-arrival events** (source A or B): each settled/recorded fill is one event. This is the primary intended object.
- **Price-move events** (source C): each price bar whose move exceeds threshold `[fill]` is one event. A coarser, distinct object — branching ratio of price moves ≠ branching ratio of trade arrivals.

Whichever is chosen is fixed; the two are not mixed, and the manuscript states which object `n` describes.

### 4c. Polymarket market selection — result-blind

- **Selection rule:** the top **`N = [fill]`** markets by *number of trades* over `[fill date range]`. `N` is set by the event-count sufficiency floor and compute budget — **not** by inspecting any `n`.
- **Event-count floor:** `[fill]`, set from estimator-stability simulations on synthetic data (the count at which the chosen estimator resolves `n` to within the §6 precision target). Markets below the floor are excluded from per-market analysis and may enter only via pooling.
- **Pooling rule (Gate C broader pass):** structurally similar markets (e.g. binary sports moneylines) are also pooled into a combined stream; per-market and pooled results are both reported.

### 4d. Wash-trade filtering — fully specified, runs before any fit

Wash trades are self-exciting by construction and would inflate `n`.
- **Graph nodes:** wallet addresses transacting in the market.
- **Edges:** directed offsetting fills / transfers between the same pair within window `W = [fill]`.
- **Circular-flow criterion:** `[fill]` (e.g. net position change below `ε` despite gross volume above threshold).
- **Clustering algorithm:** `[fill]` (e.g. connected-component / community detection on the offsetting-flow graph).
- **Removal threshold:** `[fill]`.
- **Both streams analyzed:** `n` is fit on filtered **and** unfiltered streams and the delta reported — the contamination magnitude is itself informative, and the filter is not assumed perfect.
- **Sensitivity:** results reported across `[fill]` threshold values.
- All thresholds are result-blind (calibrated on flagged-cluster structure, not on `n`).

### 4e. Simulation (MiroFish on OASIS)
- **Agent count:** `[fill]`  **Network topology:** `[fill]`  **LLM backend (+version):** `[fill]`
- **Control axes (sweep):** (i) network density; (ii) social-influence / peer-update strength; (iii) news-injection rate.
- **Sweep grid:** `[fill ranges + step counts]`, with grid size set by runtime/compute budget (result-blind).
- **Event stream:** time-stamped agent message and belief-update events, exported for point-process and cascade analysis.

### 4f. Control crowds (Stage-2 artifact gate): pre-registered readings

LLMs are trained on human text that is saturated with scale-free structure, so an LLM-agent crowd may exhibit power laws and an apparently tunable critical point as an artifact of the model's own output statistics rather than of emergent social dynamics. Two controls run through the *identical* estimation pipeline (same cascade definitions, same estimators, same gates):

- **Classical control (runs before the LLM sweep).** A bounded-confidence (Deffuant or Hegselmann-Krause) or Bayesian social-learning ABM on the same network topologies. Axis translation: network density and news-injection rate identical; social-influence strength maps to the confidence bound (bounded confidence) or the social-likelihood weight (Bayesian). Also serves as an end-to-end pipeline shakedown at near-zero token cost.
- **Parrot null.** Each LLM agent is replaced by a generator matched to the marginal output statistics of a reference mid-sweep LLM run (message rate, message-length distribution, embedding marginal distribution; matching procedure `[fill]`), with belief-state coupling removed (agents never read neighbours' states).

**Pre-registered readings (frozen):**
1. Tunable criticality in **both** the LLM crowd and the classical control → the social-dynamics mechanism is supported (strongest configuration).
2. Criticality **only** in the LLM crowd → the emergence claim is withheld until disambiguated: the parrot null and the scaling relation (Gate A.2) must both reject the artifact reading.
3. Exponents **survive the parrot null** → they are imposed by the pipeline or the model's output statistics; the artifact gate fails and no collective-criticality claim is made for the LLM crowd.

---

## 5. Variables

### 5.1 Branching ratio `n` (primary)

**Kernel-selection rule (the primary procedure).** Market self-excitation kernels are empirically long-memory power laws, so an exponential kernel risks misspecifying `n`. Therefore:
1. Fit both an **exponential** kernel and a **power-law (or sum-of-exponentials) long-memory** kernel, each with a non-stationary baseline.
2. **Select** the kernel by random-time-change residual diagnostics (Ogata residuals → KS test on transformed inter-event times) on a **held-out segment**. The selected kernel's MLE `n` is the **primary estimate**.
3. Report the **non-selected** kernel's `n` and the **Hardiman–Bouchaud mean-variance** `n` as robustness checks; a semimartingale-baseline `n` if feasible.
4. Report the **constant-baseline** `n` always, to expose any stationarity artifact.

**Identifiability confound (acknowledged and addressed).** A long-memory kernel and a non-stationary baseline both generate excess long-lag clustering and are hard to separate — this *is* the Filimonov–Sornette debate about whether market criticality is real or a baseline artifact. The baseline is estimated on held-out structure; the kernel-vs-baseline sensitivity is reported, and the near-critical claim is rejected if `n ≈ 1` only under the constant baseline (Gate A.3).

**Estimators:** MLE (primary); Hardiman–Bouchaud mean-variance approximator (robustness); EM piecewise-constant / logspline / semimartingale baselines as specified above. Estimator divergence is a finding, never averaged away.

### 5.2 Cascade definitions (exactly three; knobs frozen by synthetic calibration)

No post-hoc additions or swaps. Each definition's knobs are set to **best recover known cascade structure on synthetic ground-truth data** (result-blind), never by inspecting real-data exponents.
1. **Post-reply tree** — connected reply/repost tree rooted at an originating event.
2. **Embedding-similarity infection** — an event joins a cascade if its content embedding (model `[fill: fixed model+version]`) exceeds similarity threshold `[fill]` to a recent active-cascade event within window `[fill]`.
3. **Belief-update sequence** — a temporally contiguous run of belief-update events separated by quiescence longer than `[fill]`.

Frozen for all three: whether cascades may **merge** `[fill]`, and whether one event may belong to **multiple** cascades `[fill]`. The three definitions must agree on exponents within bootstrap error; all three are reported.

### 5.3 Exponents
Avalanche-size exponent `τ`; duration exponent `α`; `1/σνz` measured **independently** from mean-size-vs-duration scaling. Mean-field critical-branching reference: `τ = 3/2`, `α = 2`.

### 5.4 Forecasting skill (Brier / log-loss) — fully specified
- **Market forecast price:** `[fill: e.g. last trade price at the evaluation timestamp]`.
- **Sampling:** at **fixed lead-time horizons before resolution**, set `H = [fill, e.g. {7d, 3d, 1d, 6h}]` — not calendar-uniform.
- **Exclude the final pre-resolution window** of length `[fill]` (prices pin to 0/1 and manufacture fake skill).
- **Clipping:** `p ∈ [0.01, 0.99]` for log-loss.
- **Weighting:** equal-by-question (primary); market-weighted and time-weighted as robustness.
- **Exclusions:** ambiguous, cancelled, or UMA-disputed markets removed.
- **Sim–market matching:** the simulation and the market are scored at **identical lead times on the same fixed shared question set** (within-question design; see §6).
- **Murphy decomposition (pre-registered secondary analysis):** Brier decomposed into reliability, resolution, and uncertainty via the binned decomposition with `K = [fill]` probability bins; `K` is set by a result-blind stability rule on synthetic forecast data / held-out non-outcome data, and is identical across all sweep points and the market benchmark.

---

## 6. Analysis plan

**Power-law fitting (CSN, Gate A.1).** For every distribution: MLE exponent with KS-selected `x_min`; goodness-of-fit p-value via parametric bootstrap; likelihood-ratio tests vs lognormal, exponential, truncated power-law.
- **Pass:** bootstrap p-value ≥ `[fill, e.g. 0.10]` **and** LRT not favouring lognormal. Failing either ⇒ no power-law claim.

**Scaling-relation check (Gate A.2 — coarse corroboration).** Compute `Δ = (α−1)/(τ−1) − 1/σνz` (with `1/σνz` the curvature-corrected `⟨S|T⟩` slope and `τ, α` from CSN), and the **resolution** `Δ_min(N) = 2√2·SD_seed(Δ)`, calibrated on synthetic critical generators at matched event counts.

> **A.2 is a coarse corroborative check, not a fine quantitative gate — by Stage-0 measurement.** A genuinely critical generator gives `Δ → 0` with N (no bias floor — an earlier single-seed "floor" was withdrawn), but the resolution is **coarse (`Δ_min ~0.24` at 1e5 avalanches, ~0.12 at 4e5) and intrinsic** to finite-N marginal-exponent estimation: `(α−1)/(τ−1)` amplifies the `τ, α` CSN noise, and neither a different `1/σνz` estimator nor a joint `(τ,α)` fit closes the order-of-magnitude gap to fine resolution. Asserting a precision the instrument cannot deliver would itself be un-earned assertion; the coarse reading is the honest one.

Reading: `|Δ| ≤ k·Δ_min` (`k = [fill, e.g. 2]`) → **not grossly violated** — corroborates the `n`-based criticality claim. `|Δ|` far exceeding `k·Δ_min` → **grossly violated** — the scaling relation contradicts criticality. The headline criticality evidence is the branching ratio `n` (§5.1) and Gate A.1; A.2 confirms the scaling relation does not contradict it and does **not** adjudicate near-critical gradations. Both `Δ` and `Δ_min(N)` are reported. (This replaces the earlier "consistent ≙ CI contains 0 within an informativeness ceiling" gate, retired by the Stage-0 discrimination probe; see the implementation plan and `DECISIONS.md`.)

**Baseline-correction interpretation (Gate A.3).** If `n` is near 1 only under the constant baseline and falls substantially under the non-stationary baseline, the near-critical reading is rejected as a stationarity artifact. Report kernel/baseline identifiability sensitivity here.

**Critical-point identification (sim): two observables, neither defines the other.** The candidate critical point is located by two diagnostics computed on distinct data facets: (i) consensus susceptibility `χ`, from fluctuations of the aggregate belief (or from the response to a standardized micro-injection probe, spec `[fill]`), and (ii) the Hawkes `n` fitted to the event stream. The candidate critical point requires the `χ` peak and the `n = 1` crossing to coincide within sweep resolution; the coincidence is reported as a consistency check, never assumed. `n` must additionally pass **smoothly through 1** as the control parameters vary (evidence criticality is *tuned*, not hard-coded by the prompt/update rule).

**Brier-vs-`n` (H1 test) — hierarchical, on a fixed question set.**
- Evaluate every sweep point on the **same fixed set of resolved questions** (difficulty held constant by design).
- Fit a **mixed-effects model** with question-level random effects to Brier/log-loss vs `n`, removing residual question-difficulty confounding.
- Fit candidate curve shapes: **unimodal/peaked**, monotone-increasing, monotone-decreasing, flat. Compare by `[fill: AIC/BIC or cross-validated log-loss]` with margin `[fill]`.
- **H1a:** the peaked model's interior optimum is statistically distinguishable from both endpoints (`[fill: e.g. likelihood-ratio / bootstrap test, threshold]`).
- **H1b:** `n_min ∈ [0.9, 1.0)`.
- **H1c (TOST equivalence):** two one-sided tests on `n_min`(sim) − `n`(market) against margin `±delta`, with `delta = [fill]` and test level `[fill: α]`. **Selection rule (result-blind, executed in Stage 0):** `delta` is the smallest margin the estimator-stability simulations show is resolvable at the achievable event counts, capped at 0.05 (half the near-critical band width). If the smallest resolvable margin exceeds the cap, H1c is declared inconclusive in advance and reported as such. A non-significant difference test is never reported as consistency.

**Murphy internal-signature test (secondary, pre-registered).** Along the sweep, the resolution component must improve with `n` over the subcritical range (monotone trend test `[fill: e.g. isotonic-regression bootstrap or Page's trend test, threshold]`) while the reliability component degrades beyond the critical region. Readings: signature present alongside an H1a/H1b pass → the mechanistic interpretation is supported; H1a/H1b pass without the signature → the Brier minimum is reported with the mechanistic interpretation withheld. The signature carries no confirmatory weight for H1a/H1b themselves.

**Wide-CI no-interpret rule (Gate A.4).** If the 95% bootstrap CI half-width on `n` at the candidate optimum exceeds `[fill, e.g. 0.05]` (i.e. cannot resolve position within the near-critical band), declare the test **inconclusive** rather than confirming or falsifying. The threshold is set from §4c estimator-stability simulations.

**Exploratory (non-confirmatory) observables.** During long fixed-knob runs, the locally estimated `n(t)` is tracked for drift toward 1 (a self-organization signature in the strict SOC sense). Exploratory only: no headline claim attaches to it, no decision rule consumes it, and it is reported descriptively if at all.

---

## 7. Pre-specified decision rules (frozen go/no-go)

| Stage | Rule | If pass | If fail |
|---|---|---|---|
| 0 | (a) scaling-relation check distinguishes a critical generator from a *grossly* non-critical power-law generator (coarse A.2; fine near-critical discrimination is not claimed); (b) feasibility spike resolves source A/B/C and sets validity-gate + floor + precision thresholds + the H1c equivalence margin `delta` + the Gate-A.2 resolution `Δ_min(N)` calibration | Proceed to Stage 1 | Fix toolkit / resolve data source; do not proceed |
| 1 | Data-validity gate (§4a) passes | Run Hawkes | **Ship the reconstruction/validity report** (expected outcome); Hawkes → early PhD |
| 1 | Baseline-corrected `n` band | `[0.9,1.0)` → near-critical market stands (H2) | `[0.7,0.9)` → reframe as strong endogeneity; `<0.7` → abandon near-critical framing |
| 2 | Scaling relation not grossly violated (coarse Gate A.2; corroborative, `Δ_min` reported) at the critical point **and** `n` crosses 1 smoothly over the sweep **and** the §4f artifact gate resolves in reading 1, or in reading 2 with the parrot null and Gate A.2 both rejecting the artifact | Proceed to Stage 3 | Downshift to "dynamical class of LLM crowds" methods paper; if reading 3 (parrot null survives), reframe as a pipeline/model-statistics characterization |
| 3 | H1a (distinguishable interior min) **and** H1b (`n_min ∈ [0.9,1.0)`) **and** peaked model beats alternatives by the pre-set margin | Confirm headline (report H1c equivalence and the Murphy signature separately) | If CIs too wide (Gate A.4) → inconclusive; if clean fail → **negative result** |

---

## 8. What would falsify the headline hypothesis

A Brier-vs-`n` curve with no interior optimum distinguishable from the endpoints (H1a fails), or whose optimum lies outside `[0.9, 1.0)` (H1b fails). Both outcomes are pre-committed to publication. H1c failing alone (sim optimal but market elsewhere) does not falsify the criticality-optimizes-forecasting claim; it qualifies its transfer to real markets. Separately, exponents surviving the parrot null (§4f) do not falsify H1 but block any confirmation: criticality measured in the LLM crowd would not be interpretable as collective dynamics, so no headline claim is made regardless of the Brier curve.

---

## 9. Researcher-degrees-of-freedom controls

- Exactly three cascade definitions, fixed in §5.2; knobs set by result-blind synthetic calibration; the three must agree within bootstrap error and all are reported.
- One primary kernel-selection rule; both kernels, both baselines, and filtered **and** unfiltered streams always reported.
- No post-hoc market re-selection, window re-cropping, kernel cherry-picking, or estimator selection by `n`.
- Brier sampling, weighting, and exclusions frozen before any outcome is inspected.
- The H1c equivalence margin `delta`, the Gate-A.2 resolution `Δ_min(N)` calibration and gross-violation factor `k`, and the Murphy bin count `K` are frozen by Stage-0, result-blind selection rules before any real-data fit.
- Control-crowd readings (§4f) are pre-registered; no post-hoc reinterpretation of which crowd "counts."
- Every change is logged in §10 with rationale and date.

---

## 10. Deviations from pre-registration (append-only)

| Date | What changed | Why | Effect on conclusions |
|---|---|---|---|
| _[fill as they occur]_ | | | |

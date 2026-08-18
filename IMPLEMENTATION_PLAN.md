# Crowd-Criticality — Implementation Plan

**Project:** Branching-ratio criticality as the signature of skillful crowd forecasting, tested on Polymarket and a matched LLM-agent crowd (MiroFish/OASIS).
**Owner:** Jane Yeung
**Repo (proposed):** `crowd-criticality` · extractable toolkit package: `critaudit`
**Version:** v0.4 (2026-07-22 living-plan reconciliation; preserves the original v0.3 roadmap while recording measured stage status and prospective authorization boundaries)
**Companion file:** `PRE_REGISTRATION.md` v0.3 (historical draft; never globally frozen or registered)

> **Agent orientation.** The protocol lives in two files by design: this plan (living, editable) and `PRE_REGISTRATION.md` (the historical v0.3 global draft). Load both files for any task on this repo. The intended global freeze never occurred: the freeze date and OSF registration were never completed. Do not treat the draft as retroactive coverage for Stage 1 or Stage 2 results. Locally prospective specifications and committed freeze-before-measure spines retain only their documented local scope.

## 2026-07-22 reconciliation checkpoint (current authority)

This checkpoint reconciles the roadmap with the repository after Stage 2 sub-increment 3. It changes status and authorization, not a scientific threshold, hypothesis, or banked artifact. The original v0.3 stages remain below as historical intent; this section controls current execution where they conflict.

### Governance status

The global v0.3 `PRE_REGISTRATION.md` remains **DRAFT**: its freeze fields and selection-rule placeholders were not completed, no freeze tag exists, and no OSF registration is recorded. Stage 1 and Stage 2 results are therefore instrument-development or exploratory evidence relative to the global H1–H3 claims. Several later increments did freeze criteria prospectively and result-blind in local specs and code; those records remain evidence for their narrowly stated instrument claims, but they do not retroactively create a global preregistration.

Status terms in this checkpoint are **Complete**, **Partial**, **Blocked**, and **Not started**. “Blocked” identifies a measured or structural impediment; it does not mean a failed hypothesis.

| Stage | State | Reconciled reading |
|---|---|---|
| Stage 0 | Partial | Core Hawkes, power-law, scaling, generator, and synthetic-validation work exists. The complete planned production surface, all global selection thresholds, source decision in the global draft, v0.1 tag, and global freeze are not complete. |
| Stage 1 | Fallback complete | The validity gate selected the planned reconstruction/data-validity report. Fixed-shape GoF certified 0/9 assessable markets and the independent identifiability gate did not support a trustworthy per-market `n`; H2 and the H1c market anchor are not banked. |
| Stage 2 | Partial and pre-sweep blocked | OASIS harness/export, a three-seed reference cohort, controls, local cascade work, the classical `chi_resp` locator, and injection accessibility are complete. No calibrated OASIS regime-placement instrument or independent second diagnostic exists, so the registered sweep and regime claims are unauthorized. |
| Stage 3 | Not started and closed | H1a/H1b/H1c and Murphy analyses require a valid sweep and trustworthy placement instrument. Those prerequisites are absent. |
| Stage 4 | Foundation only | Reusable code exists, but release packaging, a repository license artifact, release version/tag, and the productization gate are incomplete. |

### Measured closures carried forward

- Stage 1's final artifact is [`results/s0.4_feasibility/2026-06-27_stage1_data_validity_report.md`](results/s0.4_feasibility/2026-06-27_stage1_data_validity_report.md). It is a retrospective repository archive: the June 25–27 supporting files were not committed in their stated sequence, so their local chronology is not git-visible proof of freeze-before-measure ordering. No scientific number was changed during archive.
- Cascade definition #1 (true reply links) is available. Definition #3 is calibration-blocked under the heavy-tail timing operator. Definition #2 construction v2 is calibration-blocked at mean membership ARI about 0.25 versus the unchanged 0.90 floor.
- The fitted observational Hawkes gate is regime-blind on the classical heavy-tail operator. Generator bookkeeping resolves the plant but is unavailable in the OASIS sweep.
- The matched parrot null demonstrates a material content-statistics artifact channel; its v1 band remains descriptive and non-consumable after definition #2 failed calibration.
- `chi_resp = CV²(S)` is a certified critical-point locator only on the measured classical operator fingerprint. The candidate `n_resp` transform failed and is not activated. The OASIS pilot established channel accessibility (5/5 markers, 66 exposures), not locator transfer or regime placement.
- H1b remains blocked in every current branch. The independent second diagnostic named in line 189 and any OASIS-side `chi_resp` calibration remain open.

### Authorization boundary and next decision

**The original three-way Stage 2 sweep is not authorized. Stage 3 remains closed. No paid or GPU-backed measurement is authorized by this reconciliation.**

The next increment is a $0, specification-first comparison:

1. **Branch A — bounded OASIS-side susceptibility calibration design.** Specify a non-circular ground-truth bridge or falsification route for `chi_resp`, an actually independent second diagnostic, censoring/exposure treatment, a recoverability/transfer gate, and a hard cost ceiling. If those elements cannot be specified without borrowing the desired result, Branch A fails at design review and no run follows.
2. **Branch B — methods/knob-space fallback.** Record that no recoverable OASIS regime instrument is currently available; retain the classical locator and OASIS accessibility findings at their earned scope; limit future OASIS analyses to observable knob-space or null-confirmation questions without `n` placement or H1b claims.

The design comparison does not presume Branch A will work. Any measurement authorization is a later owner decision after the design exposes whether a valid bridge and independent diagnostic exist.

**Ratification outcome (2026-07-22).** Branch A is conditionally design-valid as a **micro-randomized exposure-response instrument** at the OASIS refresh boundary: `R_reply` estimates one-generation causal explicit-response reproduction from randomized served/holdout impressions and native parent links, while `chi_resp` is measured on a disjoint marker cohort. This authorizes implementation planning and later code/fixture development under the ratified design; it does not equate `R_reply` with Hawkes `n`, activate H1b, or authorize a scientific run. **Branch B remains the mechanical fail branch** if the refresh-isolation, scripted recoverability, independence, estimand, measurement-authorization, or budget gate fails. Design record: [`results/s3_probe/2026-07-22_oasis_causal_probe_design_review.md`](results/s3_probe/2026-07-22_oasis_causal_probe_design_review.md).

**Sampling-frame amendment (owner-ratified 2026-07-22).** The estimator must consume an immutable `SamplingFrame`, fixed and serialized before the first causal draw, containing the complete fixed parent registry and every eligible candidate pair. Selection strata are exactly agent-rounds; exactly one immutable `StratumDraw`, including an explicit no-selection result, is required for every stratum. The fixed parent denominator and candidate-pair count come from the complete frame, never realized assignments. A dynamic or adaptive OASIS frame is not authorized by this amendment. The full-frame Horvitz–Thompson point estimate remains `R_reply`; its observed diagonal variance output is named `estimated_diagonal_variance_bound`, an unbiased estimator of a conservative variance-bound quantity rather than a guaranteed per-realization bound. Its derived interval stays `design_only`; Task 7 must bank a deterministic worst-case binary-response variance bound and demonstrate exact-selector coverage and width before activation. Strict fail-closed record, probability, identity, feed, and native-child provenance checks apply. The Branch-B and no-Hawkes-`n` boundaries remain unchanged, and the **Task 8 owner stop remains binding**: no scientific or provider-backed run is authorized by this amendment.

### Development authority

**Owner amendment (2026-07-22): Repository development is not gated by external employment or milestone records.** Code, tests, specifications, and local synthetic/fixture work may continue under the measurement-integrity protocol. Scientific OASIS measurements, paid/GPU work, the registered sweep, and Stage 3 still require their own prospective instrument gates and explicit owner authorization; removing an administrative prerequisite does not relax a scientific gate.

---

> **Historical-status note.** Sections 0–7 below preserve the original v0.3 roadmap and scientific intent. Within those sections, words such as “frozen” and “pre-registered” describe the state the roadmap required, not evidence that the unfinished global draft attained that state. The reconciliation checkpoint above governs current status and authorization.

## 0. Thesis and contract (read this first)

**Thesis.** The contribution is a *dynamical-class* claim, not a forecasting-accuracy claim. The primary object is the **branching ratio `n`** (and the avalanche exponents that accompany criticality). Brier/log-loss is *external validation only* — the LLM-forecasting-vs-Polymarket-Brier space is saturated, and leading with it gets the project scooped.

**Headline hypothesis** (now decomposed — see `PRE_REGISTRATION.md` §1 for H1a/H1b/H1c, H2, H3):
> *Crowd forecasting skill is maximized when the simulated crowd sits near criticality* — Brier/log-loss has an interior optimum, that optimum lies in the frozen near-critical band `n ∈ [0.9, 1.0)`, and the sim's optimal `n` is statistically consistent with the real market's. This is the social-dynamics analog of the critical-brain hypothesis (Shew & Plenz).

**Framing precision.** The claim concerns a *tuned* critical point, located by an order-parameter sweep, not self-organized criticality in the strict Bak sense: there is no claim that the crowd drives itself to `n = 1` without tuning. A cheap self-organization observable (drift of locally estimated `n` during fixed-knob runs) is logged as exploratory in `PRE_REGISTRATION.md` §6 and stays out of headline scope.

**Proposed mechanism (intended to be frozen before any Stage-1 interpretation; the global freeze did not occur).** Forecasting skill decomposes (Murphy) into reliability and resolution, and the two place opposing demands on crowd dynamics. Resolution requires that dispersed private information propagate and integrate: in a subcritical crowd (`n` well below 1) belief-update cascades die before information held by few agents reaches the aggregate, so forecasts under-react and hug the prior. Reliability requires that noise not be amplified into consensus: in a supercritical crowd (`n` above 1) cascades self-sustain, herding decouples consensus from evidence, and forecasts overshoot. Near criticality the correlation length is maximal while cascades remain marginally finite, so the crowd integrates dispersed information without runaway amplification; the hypothesis is that the reliability-resolution trade-off is optimized near `n = 1`. **Intended internal signature (`PRE_REGISTRATION.md` §5.4 and §6):** along the sweep, the Murphy resolution component should improve roughly monotonically with `n` while the reliability component degrades beyond the critical region. A Brier minimum without this signature weakens the mechanistic reading even if H1a and H1b pass.

### The anti-drift contract (load-bearing)
Four gates. No artifact ships, and no stage advances, unless all hold.

- **Gate A — criticality is earned, not asserted.** Any "critical/near-critical" claim must clear: (A.1) CSN goodness-of-fit + LRT favouring power law over lognormal/exponential; (A.2) the crackling-noise scaling relation consistent within jointly bootstrapped uncertainty across *independently measured* exponents, subject to an informativeness ceiling (an over-wide interval yields "inconclusive", never a pass; see `PRE_REGISTRATION.md` §6); (A.3) robustness to the non-stationary-baseline correction (a power law that appears critical only under a constant baseline is rejected); (A.4) the wide-CI no-interpret rule — near `n = 1` the estimator is least precise, so an under-resolved estimate yields "inconclusive," not a claim.
- **Gate B — branching ratio is the headline.** Every abstract, caption, and README foregrounds `n` and the dynamical class. Brier appears only as validation. If a draft headline becomes "we forecast Polymarket," it has drifted — rewrite.
- **Gate C — every scope-narrowing gets a second, broader pass.** Narrowing (e.g. "top-50 markets," "filtered stream") must run alongside a complementary broader pass (pooling; unfiltered stream) with the divergence reported.
- **Gate D — result-blind selection.** Every undecided parameter is fixed by a selection rule that inspects only synthetic data, held-out *non-outcome* data, event counts, or compute budget — never the `n`, the exponents, or the Brier curve. (Full statement in `PRE_REGISTRATION.md` §0.)

### Out of scope (explicit)
Beating the market on Brier · live trading / a trading product · any medical-AI tie-in (deferred to PhD year 2–3 under FZJ conflict-of-interest constraints; the fintech reflexivity angle in Stage 4 is the only commercial wedge) · a SaaS company (the commercial path is a services wedge).

---

## 1. Repository layout

```
crowd-criticality/
├── README.md
├── DECISIONS.md                 # append-only design-decision log (verify→fix→verify entries)
├── PRE_REGISTRATION.md          # frozen before Stage-1 interpretation
├── pyproject.toml
├── Makefile
├── .github/workflows/ci.yaml
├── src/critaudit/               # extractable, reusable toolkit (open-source core)
│   ├── hawkes/
│   │   ├── mle.py               #   MLE Hawkes (exponential + power-law / long-memory kernels)
│   │   ├── kernel_select.py     #   Ogata residual (random-time-change) kernel-selection rule
│   │   ├── meanvar.py           #   Hardiman–Bouchaud mean-variance approximator
│   │   └── baseline.py          #   EM piecewise-constant + logspline non-stationary baseline
│   ├── powerlaw/                #   CSN: MLE exponent, KS x_min, bootstrap p, LRT vs alternatives
│   ├── scaling/                 #   crackling-noise relation (τ, α, 1/σνz) + exponent collapse
│   ├── cascades/                #   3 pre-registered definitions; knobs set by synthetic calibration
│   ├── data/
│   │   ├── reconstruct/         #   on-chain Polygon fill reconstruction (source A)
│   │   ├── ws_capture/          #   live CLOB WebSocket trade recorder (source B)
│   │   └── washfilter.py        #   offsetting-flow graph clustering; filtered + unfiltered
│   └── sim/                     #   MiroFish/OASIS wrapper, sweep driver, event-stream export
│       └── controls/            #   classical-ABM control + parrot-null generators (Stage-2 artifact gate)
├── synthetic/                   # ground-truth generators (known-n Hawkes, critical branching)
├── experiments/
│   ├── stage1_polymarket/
│   ├── stage2_sim_sweep/
│   └── stage3_brier_criticality/
├── results/
└── tests/                       # deterministic; mocked LLM provider; CI-safe, no API keys
```

`critaudit` detaches as a standalone open-source package (Apache-2.0, like `physics-lint`). The same estimators are reusable later for scale-free analysis of neural/imaging time series — a quiet bridge to the PhD, not a dependency on it.

---

## 2. Measurement-integrity protocol (runs *before* any interpretation)

Mirrors the standing sequence: *verify the measurement is trustworthy before interpreting the finding.*

1. **Synthetic ground truth first.** Validate the whole pipeline on generators with *known* `n`, `τ`, `α`: a critical branching process and Hawkes at `n ∈ {0.3, 0.6, 0.9, 0.99}`. Recover planted values within CI; confirm the scaling-relation check *passes* on a critical generator and *rejects* a non-critical power-law look-alike. The estimator-stability sweep here also fixes the event-count floor, the Gate-A.4 CI threshold, the H1c equivalence margin `delta`, and the Gate-A.2 informativeness ceiling (the latter via joint avalanche bootstraps on synthetic critical generators).
2. **Data-validity gate (Stage 1, before any Hawkes interpretation).** The public CLOB `/prices-history` endpoint returns *aggregated bars*, and sub-12-hour granularity is unavailable for resolved markets — so it cannot feed a tick-level fit. Resolve the data source (A on-chain reconstruction / B live WebSocket capture / C paid Aug-2025+ bars) in the Stage-0 spike, then pass the validity gate: timestamp granularity, event-count floor, reconciliation against an independent reference, wash-filter applied. **If the gate fails, the Stage-1 deliverable is the data-validity/reconstruction report** (expected outcome), not a forced Hawkes paper.
3. **Event definition is fixed before fitting.** Trade-arrival events (source A/B) vs price-move events (source C) are *different* branching ratios; the manuscript states which object `n` describes. Frozen in `PRE_REGISTRATION.md` §4b.
4. **Kernel-selection rule, both baselines.** Market kernels are empirically long-memory, so the kernel is *selected* by Ogata residual diagnostics on held-out data (not defaulted to exponential); the selected kernel's MLE `n` is primary, the other kernel and the mean-variance approximator are robustness. Constant- and non-stationary-baseline `n` are both reported. Acknowledge the long-memory-kernel ↔ non-stationary-baseline identifiability confound (the Filimonov–Sornette problem) and estimate the baseline on held-out structure.
5. **Estimator triangulation.** ≥2 independent estimators; divergence is a finding, never averaged away.
6. **Wash trades: filtered and unfiltered.** Fit on both streams, report the `n` delta — the contamination magnitude is informative and the filter is not assumed perfect.

---

## 3. Staged execution

Each stage: objective, tasks, deliverable, tests, **go/no-go**, **fallback reframe**.

### Stage 0 — Pre-registration + synthetic validators + data-feasibility spike
- **Objective:** lock the protocol; prove the instrument on synthetic ground truth; **resolve the data source before filling the pre-reg**, since the source forces the event definition, market selection, and granularity.
- **Tasks:**
  - [ ] Implement `critaudit.hawkes` (incl. `kernel_select`), `.powerlaw`, `.scaling`; validate against synthetic generators (recover known `n`, `τ`, `α`; scaling check passes critical / rejects look-alike).
  - [ ] Estimator-stability simulations → set the event-count floor, the Gate-A.4 CI threshold, the H1c TOST equivalence margin `delta`, and the Gate-A.2 informativeness ceiling.
  - [ ] **Data-feasibility spike:** prototype source A (on-chain fill reconstruction for one high-volume resolved market) *and* stand up source B (WebSocket recorder on a basket of short-horizon open markets); decide A/B/C and set validity-gate thresholds.
  - [ ] Complete and freeze `PRE_REGISTRATION.md` with every `[fill]` either filled or bound to a Gate-D selection rule. CI green; tests API-key-free.
- **Deliverable:** frozen pre-registration + validated toolkit + a data-source decision (tag `v0.1`).
- **Go/no-go:** scaling-relation check distinguishes critical from look-alike; the spike yields a viable source with a defined validity gate. If no source is viable for resolved markets, Stage 1 becomes the reconstruction report by default.

### Stage 1 — Polymarket Hawkes **/ data-reconstruction report**
- **Objective:** estimate `n` on real prediction-market data with proper baseline correction. First novelty (no prior Hawkes/SOC work on prediction markets). **Sequenced data-first**, because the data may not exist at the needed granularity.
- **Tasks:**
  - [ ] **Weeks 3–4 — data feasibility & reconstruction validation:** build the chosen source; reconcile the event stream against an independent reference; pass (or fail) the validity gate.
  - [ ] **Weeks 5–8 — Hawkes, only if the gate passed:** wash-filter (filtered + unfiltered); kernel-selection rule; `n` (MLE primary + mean-variance robustness), constant vs non-stationary baseline, report divergence; Gate-C pooled broader pass.
- **Deliverable (whichever the gate yields):**
  - Gate **passes** → standalone manuscript, the prediction-market analog of Hardiman–Bercot–Bouchaud (2013); target *Quantitative Finance* / *EPJ B*.
  - Gate **fails** → **"Reconstructing prediction-market microstructure: a data-validity study"** — a useful public artifact in its own right, and the expected pre-PhD output if reconstruction is hard.
- **Go/no-go (`n` band):** `[0.9,1.0)` → near-critical market stands (H2); `[0.7,0.9)` → reframe as "strong endogenous reflexivity"; `<0.7` → abandon the near-critical-market framing (the Stage-3 link survives via "`n` predicts Brier").
- **Fallback reframe:** the reconstruction report (above) and/or "`n` varies with market regime and predicts Brier."

### Stage 2 — MiroFish/OASIS simulation + control sweep
- **Objective:** measure the *same* observables in an LLM-agent crowd and locate its critical point. Genuinely unclaimed: no LLM-agent-sim paper estimates a Hawkes `n`, tests the scaling relation, or runs an order-parameter sweep (the 2026 precedents fit only a size exponent and frame heavy tails as a *pathology to suppress* — the opposite of this hypothesis).
- **Tasks:**
  - [ ] Build MiroFish on OASIS; export the message / belief-update event stream.
  - [ ] Implement the three **pre-registered, synthetic-calibrated** cascade definitions (knobs frozen by recovery on synthetic data, not by real exponents).
  - [ ] **Artifact gate, part 1 (classical control, runs first):** run the identical estimation pipeline on a classical bounded-confidence (Deffuant / Hegselmann-Krause) or Bayesian social-learning ABM on the same network topologies, with sweep axes translated where meaningful (density and news-injection rate identical; influence strength maps to the confidence bound or social-likelihood weight). Doubles as an end-to-end pipeline shakedown at near-zero token cost before any LLM sweep.
  - [ ] **Artifact gate, part 2 (parrot null):** replace each LLM agent with a generator matched to the marginal output statistics of a reference mid-sweep run (message rate, length distribution, embedding distribution) with belief-state coupling removed. Exponents that survive this null are imposed by the pipeline or the model's output statistics and are not evidence of collective criticality. Readings pre-registered in `PRE_REGISTRATION.md` §4f.
  - [ ] Run the 3-way sweep (network density × social-influence strength × news-injection rate); measure `n`, `τ`, `α`, and the scaling relation at each point.
- **Deliverable:** sweep dataset + criticality characterization of the simulated crowd and its controls.
- **Go/no-go:** scaling relation consistent (revised Gate A.2) at the candidate critical point, **and** `n` crosses 1 *smoothly* across the sweep (criticality tuned, not prompt-hard-coded), **and** the artifact gate resolves: criticality in the classical control supports a social-dynamics mechanism; LLM-only criticality must be disambiguated via the parrot null before any emergence claim; exponents surviving the parrot null fail the gate.
- **Fallback reframe:** "What dynamical class do LLM-agent crowds occupy?" — a methods contribution to the (acknowledged-central) generative-simulation *validation* problem.

### Stage 3 — Brier-vs-criticality (the headline test)
- **Objective:** test the decomposed hypothesis directly, with question difficulty controlled.
- **Tasks:**
  - [ ] Score every sweep point on the **same fixed set of resolved questions** at **matched lead times** (within-question design); Brier sampling/weighting/exclusions per `PRE_REGISTRATION.md` §5.4.
  - [ ] Fit a **mixed-effects model** (question-level random effects) of Brier vs `n`; compare peaked vs monotone vs flat curve shapes by the pre-set criterion.
  - [ ] Evaluate H1a (distinguishable interior min), H1b (`n_min ∈ [0.9,1.0)`), H1c (TOST equivalence between sim `n_min` and the baseline-corrected market `n`, margin `delta` per `PRE_REGISTRATION.md` §6; a non-significant difference test alone is never reported as consistency).
  - [ ] **Murphy decomposition** (reliability / resolution / uncertainty) at every sweep point; test the pre-registered internal signature (resolution improving with `n`, reliability degrading beyond the critical region).
- **Deliverable:** main manuscript — "criticality is the signature of skillful crowd forecasting."
- **Go/no-go:** H1a ∧ H1b ∧ peaked model wins by margin; report H1c (equivalence) and the Murphy signature separately.
- **Fallback reframe:** Gate-A.4 inconclusive (CIs too wide) → report as inconclusive with the precision bound; clean fail → **negative-result paper** (sharp hypothesis → valuable null). *Note:* a negative here kills the Stage-4 commercial wedge, not the science.

### Stage 4 — `critaudit` open-source + EU AI Act consulting wedge (parallel, from Stage 2)
- **Objective:** convert the instrument into an inbound channel for the existing DACH-fintech conformity practice. **Services, not product.**
- **Tasks:** release `critaudit` (Apache-2.0) as a herding/reflexivity *audit* toolkit; position as a fixed-scope systemic-risk / reflexivity audit under the EU AI Act systemic-risk framing for fintech (Art. 55 lineage), delivered through the existing practice; track inbound.
- **Go/no-go (productization):** ≥3 paying conformity engagements at €25–50k each, *driven by inbound interest in `critaudit`*, before considering anything beyond a consulting wedge.
- **Reality:** incumbents (Aaru, CulturePulse, Simile, Listen Labs, Keplar, Outset) sell behavioural *outcome prediction* and neither expose nor are asked for dynamical-class diagnostics. The pain point is *latent* — good for the paper, weak for a standalone product.

---

## 4. Timeline (reality-checked; data-feasibility now the binding constraint)

The full Stage 0–3 arc is ~5 months. The pre-PhD window almost certainly yields **Stage 0 plus a data-feasibility outcome** — the Hawkes paper ships only if reconstruction is easy; otherwise the reconstruction/validity report is the pre-PhD artifact and the Hawkes paper slides into early PhD. Stages 2–4 continue as a separately managed research thread.

| Window | Stages | Output | Cadence |
|---|---|---|---|
| **Pre-PhD wk 1–2** | Stage 0 | Frozen pre-reg + validated `critaudit` + **data-source decision** | Full-time-ish |
| **Pre-PhD wk 3–4** | Stage 1a | Data feasibility & reconstruction validation (validity gate) | Full-time-ish |
| **Pre-PhD wk 5-8** | Stage 1b | **Primary pre-PhD deliverable: the reconstruction/validity report.** Hawkes paper only as a conditional bonus, iff the validity gate passed with weeks to spare | Full-time-ish |
| **PhD mo 1–3** | Stage 2 | Sim + sweep dataset | Part-time research |
| **PhD mo 3–5** | Stage 3 | Main paper (or negative-result / inconclusive paper) | Part-time research |
| **PhD mo 2 →** | Stage 4 | `critaudit` release + consulting inbound | Parallel, low effort |

**Development sequencing (owner-amended 2026-07-22):** repository work is governed by the scientific and budget gates in this plan, not by external employment or milestone records. Do **not** budget a six-week Hawkes paper against data that is not reliably accessible: the reconstruction report remains the honest hedge and the Stage-1 deliverable.

---

## 5. Risk register

| # | Risk | Severity | Trigger / tell | Mitigation |
|---|---|---|---|---|
| 1 | **Resolved-market data inaccessible at required granularity** | **Critical** | `/prices-history` empty <12h for resolved markets; on-chain reconstruction harder than scoped | Stage-0 feasibility spike; source A/B/C decision; reconstruction report as the deliverable if the gate fails |
| 2 | Non-stationary-baseline bias inflates `n → 1` | **Critical** | `n ≈ 1` only under constant baseline; collapses under EM | EM piecewise-constant + logspline baseline; report constant *and* corrected; identifiability sensitivity |
| 3 | Kernel misspecification biases `n` | High | Exponential-kernel `n` diverges from long-memory-kernel `n` | Ogata-residual kernel-selection rule; report both kernels; never default to exponential |
| 4 | Near-critical estimation instability | High | Wide/non-converging CIs as `n → 1` | Gate-A.4 wide-CI no-interpret rule; precision target from synthetic stability sims |
| 5 | Wash-trade contamination inflates `n` | High | Implausible self-excitation in flagged markets | Offsetting-flow graph filter; fit filtered + unfiltered; report delta |
| 6 | Cascade-definition researcher DOF | High | Exponent shifts with definition choice | 3 definitions frozen via synthetic calibration; agree within bootstrap error; no post-hoc swaps |
| 7 | Question-difficulty confounds Brier-vs-`n` | High | Curve shape tracks question mix, not `n` | Fixed shared question set; mixed-effects model with question random effects |
| 8 | Criticality is a prompt artifact, not emergent | High | `n` pinned at 1 across the whole sweep | Sweep must show `n` crossing 1 *continuously* as knobs vary |
| 9 | Power-law over-claiming (Gate A.1) | High | Nice log-log plot, untested | CSN bootstrap p + LRT, then the scaling-relation orthogonal check |
| 10 | Scooped on the prediction-market `n` | Medium | New arXiv preprint on Hawkes-in-prediction-markets | Pre-written pivot memo in `DECISIONS.md`: if scooped, the preprint becomes the Stage-1 anchor citation, weight shifts to the sim arm and the Brier-vs-`n` test, and the reconstruction report plus `critaudit` retain full value; arXiv watched weekly as the trigger |
| 11 | Time overrun past pre-PhD window | Medium | Stage 1 not shippable by week 8 | Reconstruction report is the shippable hedge; Stages 2–4 pre-planned PhD-side |
| 12 | Drift into the saturated Brier framing | Medium | Draft headline becomes "we forecast Polymarket" | Gate-B review on every abstract/README revision |
| 13 | **Apparent criticality is an LLM statistical artifact** (scale-free structure imposed by the model's training distribution, not emergent social dynamics) | High | Exponents survive the parrot null; criticality appears in the LLM crowd but not the classical control | Stage-2 artifact gate: classical-ABM control plus parrot null with pre-registered readings (`PRE_REGISTRATION.md` §4f) |

---

## 6. Definition of done

**Per stage:** deliverable produced; all four anti-drift gates pass; relevant measurement-integrity checks pass; a `DECISIONS.md` entry records each non-obvious choice and any honest negative finding; CI green.

**Project (success path):** frozen pre-registration; a Stage-1 artifact (Hawkes paper *or* reconstruction/validity report); a main paper reporting Brier-vs-`n` with its Murphy decomposition (positive, negative, or inconclusive-with-bound); a released `critaudit` toolkit.

**Project (honest-null path):** the same artifacts, the main paper reporting that criticality does *not* optimize crowd forecasting — framed as the falsification of a sharp hypothesis, with the Stage-2 dynamical-class characterization as the durable contribution.

---

## 7. Process norms

- **Cross-review per spec.** Each manuscript and module spec goes through Claude/ChatGPT cross-review (≥5 rounds) before it's stable. *(This plan and pre-reg are at round 2.)*
- **verify → fix → verify** for every document and code edit; nothing is "done" until re-verified.
- **Result-blind selection (Gate D).** Undecided parameters are fixed by rules that never inspect `n`, the exponents, or the Brier curve.
- **`DECISIONS.md` is append-only** and captures the *why*, especially for negative results and estimator choices.
- **External review and self-gate are complementary**, never substitutes; both run.

---

## 8. Key references / independent anchors

*Markets & reflexivity*
- Hardiman, Bercot & Bouchaud (2013), "Critical reflexivity in financial markets," *EPJ B* 86:442.
- Filimonov & Sornette (2012), *Phys. Rev. E* 85:056108; Filimonov & Sornette (2015).
- Wehrli, Wheatley & Sornette — scale/time/asset dependence of Hawkes estimates (SSRN 3597938).
- Potiron et al. (2025), branching-ratio estimation with Itô-semimartingale baselines.
- Hardiman & Bouchaud (2014), mean-variance branching-ratio approximator (arXiv:1403.5227).
- Bacry, Dayri & Muzy / Bacry & Muzy — long-memory (power-law) self-excitation kernels in markets.
- Lallouache & Challet (2016), "The limits of statistical significance of Hawkes processes fitted to financial data," *Quant. Finance* 16(1).
- Ogata (1988), residual analysis / random time change for point processes (kernel goodness-of-fit).

*Prediction-market microstructure & data*
- Yang & Tsang (2026), "The Anatomy of a Blockchain Prediction Market: Polymarket in the 2024 U.S. Presidential Election" (arXiv:2603.03136).
- Sirolly, Ma, Kanoria & Sethi (2025), network-based wash-trading detection on Polymarket.
- Polymarket API docs: CLOB `/prices-history` (aggregated bars; sub-12h unavailable for resolved markets), Data API (trades/activity), Gamma (discovery), CLOB WebSocket (live trade feed).

*LLM-agent simulation & cascades*
- OASIS (2024), "Open Agent Social Interaction Simulations with One Million Agents" (arXiv:2411.11581).
- Molt Dynamics (2026) (arXiv:2603.03555); "Hidden Power Laws of Collective Cognition" (2026) (arXiv:2604.02674).

*Control crowds (opinion dynamics)*
- Deffuant, Neau, Amblard & Weisbuch (2000), "Mixing beliefs among interacting agents," *Adv. Complex Syst.* 3.
- Hegselmann & Krause (2002), "Opinion dynamics and bounded confidence: models, analysis, and simulation," *JASSS* 5(3).

*Power-law statistics & criticality*
- Clauset, Shalizi & Newman (2009), "Power-law distributions in empirical data," *SIAM Review* 51(4).
- Sethna, Dahmen & Myers (2001), "Crackling noise," *Nature* 410.
- Friedman et al. (2012), scaling relation for neural avalanches, *PRL* 108:208102.

*Critical-brain analog*
- Beggs & Plenz (2003), neuronal avalanches, *J. Neurosci.* 23.
- Shew et al. (2009), *J. Neurosci.* 29:15595 (dynamic range); Shew & Plenz (2013), *Neuroscientist* 19:88–100 (functional benefits of criticality).
- Beggs & Timme (2012), "Being critical of criticality in the brain" (skeptical counterweight).

*Mechanism & forecast evaluation*
- Murphy (1973), "A new vector partition of the probability score," *J. Appl. Meteorol.* 12 (Brier decomposition: reliability, resolution, uncertainty).
- Kinouchi & Copelli (2006), "Optimal dynamic range of excitable networks at criticality," *Nat. Phys.* 2:348.
- Lakens (2017), "Equivalence tests: a practical primer," *Soc. Psychol. Personal. Sci.* 8(4) (TOST procedure).

*Cascade theory foundation*
- Watts (2002), "A simple model of global cascades on random networks," *PNAS* 99.

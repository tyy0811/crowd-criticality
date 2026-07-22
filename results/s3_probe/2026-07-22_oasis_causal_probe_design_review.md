# OASIS-side criticality instrument — $0 design comparison and ratification

**Date:** 2026-07-22

**Status:** design ratified conditionally; repository development may proceed; scientific measurement not authorized

**Cost:** $0; repository/source review only

**Development authority:** owner-amended 2026-07-22; development is governed by scientific and budget gates, not external employment or milestone records

## 1. Decision

Branch A is **design-valid for a future freeze increment** in one narrow form: a micro-randomized exposure-response instrument at OASIS's `Platform.refresh` boundary. It estimates a one-generation **causal explicit-response reproduction number**, named `R_reply`, from randomized served impressions and true reply links. A disjoint standardized-marker cohort supplies `chi_resp`. Branch B remains the automatic fail branch.

This ratification authorizes documentation, implementation planning, and later code/fixture work under an approved execution plan. It does **not** itself authorize a scripted calibration measurement, an LLM call, a GPU job, a sweep, re-banking, or Stage 3. Each scientific run still requires its frozen instrument gate and an explicit owner call.

The naming boundary is load-bearing: `R_reply` is not silently renamed Hawkes `n`. It is an intervention-defined reproduction estimand on the explicit reply channel. H1b remains blocked unless a future global protocol prospectively adopts this estimand or separately earns an equivalence argument to the headline branching ratio. No such equivalence is asserted here.

## 2. Why this is the surviving Branch A

Every measured closure so far attempted to reconstruct influence from emitted structure or to transfer a response transform across operators:

- the fitted observational gate is regime-blind on the heavy-tail classical operator;
- cascade definition #3 is calibration-blocked;
- cascade definition #2 membership recovery is about 0.25 ARI against a 0.90 floor;
- `n_resp = 1 - 1/S_bar` fails because collision and censoring bias grows toward the critical region;
- a scripted or classical `chi_resp` calibration cannot simply transfer to an LLM response policy with a different operator fingerprint.

The surviving design changes the identification strategy. It randomizes the exposure that could cause a direct child and reads the child from native OASIS parent links. It does not infer the parent from text, embeddings, timing, or a fitted Hawkes decomposition. It estimates one generation directly, avoiding the completion-tail transform that broke `n_resp`.

## 3. Approaches compared

### A — micro-randomized exposure-response reproduction instrument (ratified)

Intercept the refresh result before it enters an agent's prompt. For one eligible parent-agent pair, randomly assign either a verified served impression or a shadow holdout. Measure a direct true-link reply in that agent's immediately following action. Known randomization probabilities identify the expected number of causally induced direct children per eligible parent.

Advantages: designed intervention; native true links; can cross 1 because it estimates reproduction potential rather than edges divided by a completed finite forest; one-round outcome avoids completion-tail censoring; distinct from multi-generation `chi_resp`.

Risks: only the explicit-response channel is measured; the refresh hook must preserve background-feed load; interference and prior exposure must be structurally excluded; the estimand is not automatically the project's Hawkes `n`.

### A2 — scripted OASIS twin followed by direct transfer (rejected as sufficient)

Run scripted agents with known response probability through the OASIS platform, validate `chi_resp`, then apply the same locator to LLM agents.

This is useful only as a positive control for code and exposure mechanics. It cannot establish LLM-side transfer because the response policy is part of the operator fingerprint. Treating the scripted peak as an LLM calibration would repeat the transfer error already excluded by sub-increment 3.

### B — methods/knob-space fallback (frozen fail branch)

Bank that no recoverable OASIS regime instrument is available; retain the classical locator and OASIS accessibility findings; restrict future analysis to observable knob-space and null confirmation without `n` placement or H1b.

Branch B activates mechanically if any required gate in section 8 fails. It is not reconsidered after seeing a scientifically inconvenient LLM result.

## 4. Causal estimand

For a native crowd post `p` created in round `r-1`, let `C(p)` be the prospectively defined set of crowd agents for whom `p` is eligible for an experimental slot in round `r`. Eligibility is computed before any round-`r` outcome and excludes the author, the news user, agents previously exposed to `p`, and agents without a complete same-action observation.

For each selected pair `(i, p)`, `Z_ip` is randomized with known probability:

- `Z_ip = 1`: `p` is inserted into the experimental refresh slot and its presence in the trace is verified;
- `Z_ip = 0`: `p` is removed from the background and experimental slots, a result-blind filler preserves feed length, and trace absence is verified.

`Y_ip = 1` iff agent `i` authors a comment, quote, or repost whose native parent is `p` in the LLM action immediately following that refresh; otherwise `Y_ip = 0`. Parent identity comes from the OASIS database link, never similarity. The candidate-selection and treatment probabilities are recorded, so a Horvitz-Thompson total estimates the potential direct children of each parent. Averaging across eligible parents yields `R_reply`.

The exact estimator, inclusion probabilities, variance estimator, and confidence interval must be frozen in the executable spec before any run. The design requirement is that the estimator targets the total one-generation reply potential over `C(p)`, not the observed edge/node ratio. Therefore `R_reply` can in principle lie below or above 1 despite a finite forest.

## 5. Identification construction

The installed OASIS 0.2.5 path is feasible in principle:

1. Every LLM action calls `to_text_prompt`, which calls `refresh`, before generation.
2. `Platform.refresh` constructs the served posts and writes them to the trace table.
3. The harness already exports those served IDs fail-closed and joins them to subsequent emits in causal row order.
4. Posts authored in round `r` become readable from round `r+1`; round-`r+1` emissions are not readable to peers until the next round. That boundary permits a same-action outcome without within-round contagion from other experimental recipients.

The future implementation must subclass or wrap `Platform.refresh`; it must not patch the post-hoc export. The intervention assignment is made before prompt construction and recorded in a new immutable trace row. Treatment and holdout feeds have equal length. The experimental parent is removed from the natural background in both arms before treatment insertion, preventing accidental double exposure.

At most one experimental parent is assigned to an agent-round. A parent is eligible only in its first readable round, which makes prior exposure structurally impossible. Any trace mismatch, duplicate exposure, background leakage, late outcome, missing assignment probability, or multiple experimental parents fails the cell closed.

## 6. Independent second diagnostic

`chi_resp` remains `CV2(S)`, the squared coefficient of variation of multi-generation seeded true-link tree size. It is measured on a **disjoint marker cohort**: different roots, rounds, assignment stream, and run/seed allocation from `R_reply`.

The two diagnostics use different data facets:

- `R_reply`: randomized one-generation native-parent response potential;
- `chi_resp`: multi-generation fluctuation of standardized exogenous-root response.

They may share the platform and true-link schema, but no event, marker, or randomization assignment is consumed by both estimates. Equal served-impression support across sweep cells is required for `chi_resp`; an exposure-volume change may not manufacture its peak. The support target is selected by a result-blind power calculation and frozen before any LLM call.

A candidate critical point requires a smooth `R_reply = 1` crossing and a `chi_resp` peak in the same neighboring knob interval. Neither observable defines, tunes, or corrects the other.

## 7. Ground-truth bridge

The first future executable gate is a $0 scripted-agent positive control on the exact OASIS platform, refresh wrapper, network, round clock, trace schema, candidate selector, and estimator.

The scripted policy recursively replies to a treated eligible parent with registered Bernoulli probabilities chosen to plant reproduction values on both sides of 1. Generator bookkeeping provides `R_gen`; it is never used by the estimator. The grid must include deep-subcritical, band-interior, near-crossing, and supercritical cells. Train cells may determine no result threshold; held-out cells decide recovery.

The frozen recoverability requirements are:

- strict monotone ordering across the planted grid;
- one resolved crossing through 1;
- held-out absolute error at or below 0.05 in the near-critical neighborhood;
- confidence-interval coverage and width criteria fixed by a pre-run binomial power calculation;
- the `chi_resp` peak contains the planted crossing within sweep resolution;
- forced malformed traces and exposure leakage fail closed.

Passing this control validates implementation and the design-based estimator. It does not transfer a scripted `chi_resp` curve to LLM agents. LLM-side identification comes from fresh exposure randomization; the positive control transfers only the measurement mechanics and estimator algebra.

## 8. Mechanical gates and Branch B triggers

Branch A stops and Branch B activates for scientific use if any of these occurs:

1. **Hook gate:** served and shadow-held-out assignments cannot be enforced and verified before prompt construction without changing non-experimental behavior.
2. **Isolation gate:** prior exposure, unequal feed length, more than one experimental parent per agent-round, or within-round interference cannot be excluded.
3. **Recoverability gate:** the scripted OASIS control misses monotonicity, crossing, error, precision, or `chi_resp` coincidence criteria.
4. **Independence gate:** `R_reply` and `chi_resp` cannot be computed from disjoint assignments and equal-support marker data.
5. **Estimand gate:** the future protocol cannot state prospectively whether `R_reply` replaces, complements, or is theoretically linked to Hawkes `n`. In that case it remains a methods observable and cannot carry H1b.
6. **Measurement-authorization gate:** the executable spec, power calculation, and fail branch are not frozen before a scientific run, or the owner has not authorized that run.
7. **Budget gate:** a future pilot cannot be bounded prospectively within its owner-approved ceiling. No partial paid run is interpreted.

No tolerance is relaxed, cell added, marker swapped, or estimator corrected after a failed gate.

## 9. Future cost and sequencing boundary

This review spent $0 and authorizes $0.

After an executable spec and implementation plan are separately approved, sequencing is:

1. freeze the executable estimator, assignment scheme, power calculation, gates, and Branch B text;
2. implement and test the refresh intervention entirely against fixtures;
3. run the scripted OASIS recoverability grid at $0;
4. stop on any failure;
5. only after a full ground-truth pass, request a separate owner decision for a small OASIS LLM pilot with a hard ceiling proposed at $4 upper bound;
6. keep the original three-way sweep and Stage 3 closed until the new instrument and a prospective global protocol both earn them.

## 10. Ratification boundary

**Ratified:** Branch A's micro-randomized `R_reply` plus disjoint `chi_resp` architecture is coherent enough to become the next future freeze design. It is the only surviving route that is intervention-based, native-link, one-generation, and capable of crossing 1 without an observational reconstruction.

**Not ratified:** equivalence to Hawkes `n`; H1b activation; LLM-side recoverability; any threshold not explicitly fixed above; any scientific run; any spend.

**Standing fail branch:** Branch B remains frozen and activates mechanically when a scientific gate fails.

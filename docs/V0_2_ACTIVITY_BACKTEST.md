# v0.2 Polymarket Activity-Burst Screening Boundary

**Status:** Prospective boundary drafted 2026-08-28 and tracked 2026-09-03, before any provider-backed measurement in this workstream.

## Research question and target

This is a **retrospective screening study** of the incremental predictive value of cutoff-safe social data for a next-24-hour, market-relative Polymarket activity burst.

At a 00:00 UTC cutoff, the candidate label is:

```text
N_next24 >= 20 AND N_next24 >= 2 * median(N_previous_7_days)
```

This mixes cold-start jumps with relative surges. M1 includes the seven-day median, so the mechanical relationship between that feature and the label must be disclosed.

## Frozen comparison arms

- **M0:** training prevalence.
- **M1:** market-history features.
- **M2:** M1 plus deterministic social counts.
- **M3Q:** M2 plus fixed Gemini scores from the market question only.
- **M3P:** M2 plus otherwise-identical Gemini scores from the question and cutoff-safe posts.

A social-semantic interpretation requires **M3P must beat M3Q**. A full-social interpretation also requires M3P to beat M1. M3Q performance represents a market-semantic prior; it is not by itself evidence of training-set recall.

## Data and freeze gates

- The historical Polymarket Data API audit is one-directional: each valid transaction observed by the old recorder must appear in the API response. The converse is untestable because the old recorder did not bank its subscribed roster.
- Exact calendar boundaries are chosen by a frozen rule only after historical Bluesky coverage and minimum-detectable-effect (MDE) gates are measured. Burst outcomes and model performance cannot choose the window.
- Historical metadata and posts must be demonstrably available by their cutoff. Current engagement counters are prohibited.
- Features, cohort, split, prompts, models, and predictions are hashed before locked labels are opened. The retrospective screen runs once from canonical paths; failures do not permit a new output path or tuned rerun.

Raw provider data, caches, ledgers, and labels remain outside the repository under `/Users/zenith/v0_2_activity/`. Only aggregate reports, hashes, and protocol records may be committed. Added v0.2 storage is capped at 1 GB.

## Privacy and budget

The total ceiling is **USD 20**. Historical Gemini calls have a hard **USD 5** ceiling; the remaining USD 15 is reserved and is not authorization for a MiroFish-style agent simulation.

A **paid Gemini tier is required before any post text is submitted**. Public post text must not be sent on Gemini's free tier. Before a paid request, strip author handles, DIDs, record URIs, display names, profile fields, URLs, and mentions. Missing billing confirmation, failed redaction, or a missing cost reservation fails closed.

These ceilings define a possible later experiment. This Task 1 commit authorizes documentation and firewall tests only—no network request, provider spend, service action, or locked-label access.

## Scientific and operational boundaries

This work makes **no criticality claim**, earns **no H1b credit**, and earns **no OASIS regime-placement credit**. Branch B remains activated, the original Stage 2 sweep remains unauthorized, and **Stage 3 remains closed**.

The existing launchd service `com.crowdcriticality.brecorder` **must not be stopped, modified, or replaced** by this workstream. Its continued operation and 1.0 GB capture require a separate owner decision before any parallel recorder is authorized.

Historical social search is survivor-biased and the dates have elapsed. No retrospective result is confirmatory: **forward shadow replication is the adjudicating test**.

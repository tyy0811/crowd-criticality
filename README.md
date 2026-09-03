# crowd-criticality

**Is crowd forecasting skill maximized when the crowd sits near criticality?**

The primary object of this project is the **branching ratio `n`** of a forecasting crowd's event dynamics — the order parameter of a dynamical-class claim, the social-dynamics analog of the critical-brain hypothesis. We estimate `n` (and the avalanche exponents that accompany criticality) for a real prediction market (Polymarket) and for a matched LLM-agent crowd, locate the simulated crowd's critical point by an order-parameter sweep, and test whether forecasting skill is optimized there.

> Forecasting accuracy (Brier / log-loss) is **external validation only**, never the headline. The contribution is the dynamical class, not beating the market. (Anti-drift Gate B.)

## Status

### Current checkpoint (2026-08-28)

The repository retains the post-merge state after **Stage 2's causal-probe instrument, Branch-B activation, and the registered parrot-null v2 R3 measurement** (PR #13, squashed into `main` at `989f8b9`). A separate v0.2 activity-screening boundary is now current for that workstream only; it does not reopen the closed criticality program.

- **Stage 1:** the validity gate selected its fallback deliverable, [`Reconstructing Polymarket microstructure`](results/s0.4_feasibility/2026-06-27_stage1_data_validity_report.md). The fixed-shape fit certified 0/9 assessable markets and the independent identifiability analysis found no trustworthy per-market `n`; H2 and the H1c market anchor are therefore not banked.
- **Stage 2:** the OASIS harness/reference cohort, controls, local cascade calibrations, classical `chi_resp` locator, and injection-channel accessibility pilot are complete at their stated scope. See the [harness writedown](results/s2_harness/2026-07-14_subinc1_writedown.md), [parrot-null writedown](results/s2_llm_parrot_null/2026-07-17_subinc2_writedown.md), and [probe writedown](results/s3_probe/2026-07-20_subinc3_writedown.md).
- **Branch B activated ([DECISIONS.md](DECISIONS.md), 2026-07-30):** the marker χ-coincidence diagnostic found no recoverable OASIS regime-placement instrument. Future OASIS analysis is restricted to observable knob-space and null confirmation, without `n` placement or H1b.
- **Parrot-null v2 closed as R3 ([PRE_REGISTRATION.md §11](PRE_REGISTRATION.md), [DECISIONS.md](DECISIONS.md) 2026-08-17/18):** the registered 45-run measurement fail-stopped on run 1/45 (a schedule–substrate incompatibility). No R1 or R2 is creditable; the measurement is closed.
- **v0.2 activity screen:** the [prospective boundary](docs/V0_2_ACTIVITY_BACKTEST.md) defines a result-blind test of whether cutoff-safe social data adds next-24-hour activity-burst signal. Only its documentation/firewall Task 1 is authorized now; it earns no criticality, H1b, or OASIS placement credit.
- **Still absent:** the registered three-way sweep and every Stage 3 hypothesis test. Accessibility is not transfer calibration and carries no regime claim.
- **Protocol status (read both):** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) is the living v0.4 roadmap. [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md) remains the historical v0.3 **draft**; it was never globally frozen or registered and cannot be applied retroactively. Later local prospective freezes (including §11 above) retain only their documented local scope.
- **Design-decision log:** [`DECISIONS.md`](DECISIONS.md) (append-only).

The plan's [2026-08-28 activity-workstream checkpoint](IMPLEMENTATION_PLAN.md#2026-08-28-activity-workstream-checkpoint-current-authority) is the current authority, together with the [v0.2 boundary](docs/V0_2_ACTIVITY_BACKTEST.md). Later data measurements, provider calls, service changes, and locked-label access require their stated gates and fresh owner authorization. The Stage 2 sweep and Stage 3 remain closed.

## `critaudit`

The estimators detach as a standalone, Apache-2.0 toolkit (`critaudit`): MLE Hawkes branching-ratio estimation, CSN power-law fitting, the crackling-noise scaling relation, and the synthetic ground-truth generators that validate them. The same instruments are reusable for scale-free analysis of other time series.

## Principle

Verify the measurement is trustworthy before interpreting the finding. The instrument is proven on synthetic data with *known* `n`, `τ`, `α` — recovering planted values and distinguishing genuine criticality from power-law look-alikes — before it touches real or simulated crowds.

# crowd-criticality

**Is crowd forecasting skill maximized when the crowd sits near criticality?**

The primary object of this project is the **branching ratio `n`** of a forecasting crowd's event dynamics — the order parameter of a dynamical-class claim, the social-dynamics analog of the critical-brain hypothesis. We estimate `n` (and the avalanche exponents that accompany criticality) for a real prediction market (Polymarket) and for a matched LLM-agent crowd, locate the simulated crowd's critical point by an order-parameter sweep, and test whether forecasting skill is optimized there.

> Forecasting accuracy (Brier / log-loss) is **external validation only**, never the headline. The contribution is the dynamical class, not beating the market. (Anti-drift Gate B.)

## Status

Stage 0 — building and validating the instrument before interpreting any data.

- **Protocol (read both):** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) (living) and [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md) (frozen before any Stage-1 interpretation; do not edit frozen content except via its §10).
- **Current slice:** S0.1 — the `critaudit` instrument core + synthetic validators. Design specs under [`docs/superpowers/specs/`](docs/superpowers/specs/).
- **Design-decision log:** [`DECISIONS.md`](DECISIONS.md) (append-only).

## `critaudit`

The estimators detach as a standalone, Apache-2.0 toolkit (`critaudit`): MLE Hawkes branching-ratio estimation, CSN power-law fitting, the crackling-noise scaling relation, and the synthetic ground-truth generators that validate them. The same instruments are reusable for scale-free analysis of other time series.

## Principle

Verify the measurement is trustworthy before interpreting the finding. The instrument is proven on synthetic data with *known* `n`, `τ`, `α` — recovering planted values and distinguishing genuine criticality from power-law look-alikes — before it touches real or simulated crowds.

# S0.4 Granularity Feasibility — Gate-A.1 Cross-Review Brief

**Status:** PROVISIONAL cross-review input. **Not committed**, not a spike deliverable — a
self-contained brief staged for cross-model review. Throwaway until cross-review rules.
**Audience:** a reviewer with **no access to the working session** — written to stand alone.
**Date:** 2026-06-16 · **Branch:** `s0.4-data-feasibility-spike`

> **Bottom line (read first).** This is a **scope tradeoff, not a measurement.** The only
> granularity result that exists is **exponential-kernel, moderate-n** — and it does **not**
> transfer to the project's **power-law, near-critical (n→1)** regime, where recovering the
> branching ratio n̂ from 2 s data is **untested**. The decision: **pay now** to build that test
> (it is new code, before the offsite kit), or **proceed on the exponential result and accept the
> late-discovery risk** that Stage-1 finds the real regime unrecoverable at 2 s. And the measured
> granularity bias is **directionally upward, toward criticality** — so that risk is not mere
> imprecision but **false-positive criticality**, a threat to the project's central claim (§6).
> *(Any "≈8 s threshold" below is an exponential-kernel number — it is **not** the project's bar.)*

---

## 0. The decision you are being asked to make

**The exponential-kernel result does not transfer to the project's regime — that gap is the
decision.** A synthetic sweep established whether the Hawkes **branching ratio n̂** survives
quantization to **2 s** (Polygon block time) **for an exponential kernel at moderate n (≈0.6)**.
The project's real regime is **neither**: **power-law / long-memory** (Hardiman–Bouchaud
microstructure lineage) and **near-critical (n→1)** — both moving *toward* the failure mode (§4).

**Scoping question (project-wide — Stage-1 inherits whatever estimator is blessed here):**

> Should the source-A feasibility verdict **require power-law / near-critical validation** of
> the corrected (binned) estimator **before** it is issued — or should it **proceed on the
> exponential, moderate-n result plus the real market's measured kernel**, and treat power-law
> recovery as **Stage-1 certification**?

**The axis to weigh — *upfront cost* vs *late-discovery risk*:**
- **Pay upfront (gate the verdict):** build a power-law generator + power-law binned likelihood
  (real new code, §5) and test n̂ recovery at 2 s near criticality **before** issuing the verdict
  or building the offsite kit (Tasks 5–8).
- **Proceed and certify late:** issue a regime-scoped verdict on the exponential result + the
  market's *measured* kernel now, accepting the risk that **Stage-1 discovers** the near-critical
  power-law regime does **not** recover at 2 s — after more has been built assuming it does.

This is a scope decision, not a measurement (the gap is new code, §5). Cross-review should make
the call; §7 lists the concrete options against this axis.

---

## 1. Background (self-contained)

- **Goal of the spike:** a definite *accessibility* verdict on **source A** = reconstructing a
  resolved Polymarket market's trade-arrival point process from on-chain CTF-Exchange
  `OrderFilled` fills (via a Dune indexer), then fitting a Hawkes model to get **n̂**, the
  self-excitation / branching ratio that operationalizes "crowd criticality" (n→1 = critical).
- **Why 2 s matters:** on-chain events carry **block-time** timestamps (~2 s on Polygon). Many
  trades share a block → identical timestamps (**ties**). The question is whether n̂ survives
  that quantization.
- **The instrument:** an exponential-kernel Hawkes simulator + an exponential-kernel MLE
  (point estimate of n via `x=[mu,n,beta]`). Both already exist and are unit-validated; the
  sweep reuses them. **No power-law-kernel generator or likelihood exists in the codebase**
  (verified: the only "power-law" code is a discrete *avalanche-size* Zipf draw, a different
  object; the MLE recursion `R[i]=exp(-β·Δt)(1+R[i-1])` is exponential-specific).
- **Verdict axis = accessibility, not possibility.** Reconstruction's technical possibility is
  settled (Yang & Tsang 2026 reconstructed the 2024 election fills). "Technically infeasible"
  is **not** an available verdict; an access/cost/effort blocker is the only "blocked" outcome.

---

## 2. What was measured (exponential kernel, n≈0.6) — and the false alarm it cleared

**First result (continuous MLE on quantized times): `T_threshold = inf`.** No kernel timescale
in [0.25, 16] s drove the absolute bias |n̂−n| below 0.05. Taken at face value this would force
**every** market to "inadequate" on granularity — a near-infeasibility claim.

**It was a false alarm caused by the wrong estimator.** Three competing explanations were
tested and **refuted** (each labeled by the run and column it cites, so the numbers are
traceable and not silently mixed across runs):

1. **Swept range too short** — refuted (the §3 binned re-run, 5 seeds, **continuous-quant
   |n̂−n|** column): that bias **stays between 0.09 and 0.14 across the whole 32× timescale range
   (0.5→16 s) and never crosses 0.05** — it flattens at the slow end (0.100→0.093 over ts
   8→16 s), asymptoting *above* the bar, not toward it. **Clincher:** the *binned* estimator's
   bias **does** fall to ~0 at ts=16 s (§3), so the information **is** present at large timescale
   and the continuous MLE's residual is **estimator degeneracy, not insufficient range**.
2. **Sample size** — refuted (horizon diagnostic, **continuous-quant |n̂−n|**): at ts=16 s,
   raising horizon 2 000→8 000 (≈4× the events) moves the bias only 0.091→0.088. **Systematic,
   not variance.**
3. **Rate / tie density** — refuted (rate diagnostic, timescale fixed at 4 s, **continuous-quant
   |n̂−n|**): **lowering** the event rate makes it **worse** — **0.10→0.38** as rate 1.5→0.05
   ev/s — the opposite of a tie-crowding story.

The clean (unquantized) fit recovers n to <0.02 everywhere → **the instrument is sound; the
breakage is specifically the quantized handling.**

**Root cause:** feeding **exact ties** to a **continuous-time** MLE is degenerate. The
identifying signal for n vs the background rate is the **short-lag clustering** — the excess
intensity right after each event — which lives in the **sub-2 s structure** quantization
destroys and which a continuous likelihood then mis-reads.

---

## 3. The correction and the partition (the substantive finding)

Re-estimating with a **discretized / binned-Poisson likelihood** — the *actual candidate
estimator for 2 s data*: bin into 2 s counts `c_k`; `c_k ~ Poisson(Λ_k)`,
`Λ_k = μΔ + n(1−e^{−βΔ})·S_k`, causal cross-bin recursion `S_{k+1}=e^{−βΔ}S_k + c_k e^{−βΔ/2}`;
**within-bin self-excitation is dropped on purpose** (within-bin order is the lost information).

Absolute bias |n̂−n|, 5 seeds/point, n=0.6, μ=0.6, horizon=2000 s, grid=2 s:

| kernel timescale | continuous-clean (best case) | continuous-quant (**broken**) | **binned-quant (corrected)** | binned **excess over clean** |
|---:|---:|---:|---:|---:|
| 0.5 s | 0.016 | 0.140 | **38.8** (diverges) | — |
| 1.0 s | 0.026 | 0.125 | **0.99** (supercritical) | +0.96 |
| 2.0 s | 0.029 | 0.113 | **0.33** | +0.30 |
| 4.0 s | 0.015 | 0.113 | **0.114** | +0.099 |
| 8.0 s | 0.044 | 0.100 | **0.051** | **+0.007** |
| 16.0 s | 0.060 | 0.093 | **0.057** | **−0.003** |

**Direction of the binned bias (signed — mean n̂ vs true 0.60):** **0.62** (16 s), **0.64** (8 s),
**0.71** (4 s), **0.93** (2 s), **1.59** (1 s), **39.4** (0.5 s). The adopted estimator
**over-estimates n at every timescale**, monotonically worse as it goes sub-grid; in the
dangerous 2–4 s band the signed bias *equals* the absolute bias (all five seeds over-estimate).
**The bias is directionally upward, toward criticality** — stakes in §6.

**The real-vs-artifact fork resolves to *both*, partitioned by timescale, mechanism-consistent
(all numbers exponential-kernel, n≈0.6):**

- **Resolvable (timescale ≳ 8 s ≈ 4× grid): the `inf` was estimator inadequacy.** The binned
  estimator's *excess over the clean-data fit* collapses to **+0.007 at 8 s and ≈0 at 16 s** —
  i.e. the binned estimator on 2 s data is as accurate as the continuous MLE on **un**quantized
  data. Quantization is **nearly free** there *for this kernel class*. Most self-excitation is
  cross-bin (recoverable from counts); the continuous MLE only failed on the ties.
- **Unresolvable (timescale ≲ 2 s ≈ grid): information is genuinely gone.** The binned
  estimator **also** fails — catastrophically (n̂=38.8 at 0.5 s) — because the self-excitation
  is within-bin and no estimator recovers within-bin order from counts. **Not** estimator-fixable.

This **vindicates the spike's "resolvable vs unresolvable" framing and restores a finite
threshold ≈ 8 s — for the exponential kernel only** (see §4 before using this number).

**Adopted correction (carry into the project):** the **continuous-MLE-on-ties is refuted** for
quantized data; the **binned likelihood replaces it**. This is real and should propagate.

---

## 4. The central open item: the project's regime is neither exponential nor moderate-n

**`T_threshold ≈ 8 s` is an exponential-kernel, moderate-n number. Do not promote it to the
general feasibility bar.** The target regime moves toward the failure mode on **both** axes:

- **Power-law / long-memory kernel** (Hardiman–Bouchaud find market Hawkes kernels are
  power-law, not exponential): a power-law kernel is **scale-free** → it carries **non-negligible
  sub-2 s mass by construction**, and there is **no single characteristic timescale** to compare
  against 8 s. The entire "real timescale vs 8 s" verdict has **no clean analog** here.
- **Near-critical (n→1):** the process clusters harder (more ties) and the MLE is intrinsically
  **higher-variance** — exactly where a granularity penalty bites worst.

So "binned estimator recovers n̂ above ~8 s" is established **for the proxy, not the target**.
Whether the binned estimator recovers n̂ for a **power-law, near-critical** kernel at 2 s is
**untested**.

---

## 5. Why this is a scope decision, not a probe

Closing §4 requires **new code on both sides**, neither of which exists:

1. A **power-law / long-memory Hawkes generator** (was Phase-2; not built — the existing
   simulator is exponential-only).
2. A **power-law binned likelihood** (the existing MLE's O(N) recursion is exponential-specific;
   a long-memory kernel needs a different, costlier estimator — e.g. sum-of-exponentials
   approximation or direct quadrature).

**Why the build can't be shortcut.** The obvious shortcut — estimate a candidate power-law
kernel's **sub-2 s mass fraction** and read the bias off the exponential sweep, skipping the
build — is **closed by this spike's own rate result.** Holding the kernel fixed (so its
short-lag mass fraction is constant) and varying only the event rate, the continuous-quant bias
moved **0.10 → 0.38** (rate diagnostic, |n̂−n|; §2 ref 3). So the sub-2 s mass fraction **alone
does not determine the bias**; the **cross-bin signal density** (set by the rate *and* the full
kernel shape) does too. A scale-free power-law kernel changes **both** at once and across all
lags. Predicting its bias therefore requires the **temporal simulation**, not a mass-fraction
calculation.

This is Stage-1-grade work, not a throwaway diagnostic — hence the §0 decision.

---

## 6. Provisional status, contingencies, and non-claims

- **The bias is directionally UPWARD — a validity threat, not a precision problem.** The adopted
  binned estimator **over-estimates** n at every timescale (signed mean n̂: 0.62→39 as ts
  16→0.5 s; true 0.60; §3). Mechanism: with within-bin timing gone, the lost within-bin
  clustering is **mis-attributed to the cross-bin n term and inflates it**. Because the project's
  headline object is **criticality (n→1)**, an upward granularity bias is a **false-positive-
  criticality** risk: a genuinely subcritical market on under-resolved data can read as
  near-critical or supercritical (binned n̂=0.93 at ts=2 s for true 0.60). It is worst **exactly
  in the target regime** — near n=1 the margin to the critical line is already small, so even a
  modest upward bias crosses it. So under **G2** the late-discovery risk is not "n̂ is imprecise,"
  it is "**part of the criticality signal may be a resolution artifact**" — a threat to the
  central claim, not merely its precision.
- **The 2–4 s band is the dangerous zone.** It yields **plausible-but-biased** n̂ — not an obvious
  blow-up — **and the bias there is confirmed upward and all-seeds** (binned signed bias **+0.11
  at 4 s, +0.33 at 2 s**, signed = absolute). Any timescale-based verdict therefore **needs an
  upward margin**, not a bare threshold crossing.
- **The binned estimator is doubly provisional and project-wide in scope.** Adopted as the
  correct *form* (ties handled natively), but **(a)** recovering the *planted* n on the *exact*
  synthetic model is **necessary, not sufficient** — real on-chain within-bin dynamics may
  differ (**real-data certification** owed); **(b)** **power-law / near-critical validation**
  owed (§4). Stage-1 inherits whatever is blessed here.
- **A-vs-B is now contingent on the power-law outcome.** Source A's 2 s limit is a block-time
  artifact; source B (live WebSocket capture) timestamps at **message arrival (sub-2 s)**.
  *If* the near-critical power-law regime recovers at 2 s → **A is fine for slow markets, B
  stays a hedge.** *If not* → **B's fine timestamps become load-bearing for n̂**, flipping B
  from hedge to architecture. To verify cheaply: read the live feed's timestamp resolution
  while standing up the recorder.
- **Jitter is a cautionary artifact, not evidence.** Sub-grid uniform jitter "recovers" n̂ even
  at 0.5 s (bias 0.014) where information is provably gone — it imposes a wrong random order the
  continuous MLE mistakes for signal. It corroborates the binned result only in the resolvable
  regime; trust the binned likelihood.
- **Not claimed:** that 2 s is hopeless for n̂ (it is not, for slow exponential kernels); that
  the project is feasible (unproven pending §4/§6); any committed change — **nothing is
  committed, the `inf` sweep writedown is held, and the offsite kit (Tasks 5–8) is not built.**

---

## 7. Concrete options, against the §0 axis

**The spine is G1 vs G2 — the *upfront-cost* vs *late-discovery-risk* poles of the §0 axis.**
G3 is the fork that opens only if A is judged structurally inadequate.

- **(G1) Pay upfront — gate the verdict on power-law validation.** Build the power-law generator
  + power-law binned likelihood (§5) first; issue the source-A verdict only after testing n̂
  recovery for a **near-critical power-law** kernel at 2 s. **Cost:** Stage-1-grade code, paid
  before Tasks 5–8. **Buys:** no late surprise; the verdict covers the real regime.
- **(G2) Accept the risk — issue a regime-scoped verdict now.** Verdict = "source A reconstructs;
  n̂ recoverable **iff the measured kernel sits in the resolvable regime with margin**," carrying
  the binned estimator as an adopted-but-uncertified correction and power-law recovery as an
  explicit **Stage-1 certification** gate. **Cost:** the risk Stage-1 finds the near-critical
  power-law regime unrecoverable at 2 s (and biased **upward**, §6), after more is built on it.
  **Buys:** keeps the spike a spike; defers the hardest unknown to where it can be certified on
  real data.
- **(G3) Re-route to B (conditional fork).** If the timestamp-resolution check (and the
  power-law risk) make A's 2 s structurally inadequate for the near-critical regime, treat
  **B (sub-2 s live capture) as the primary n̂ source** and A as coverage for what survives
  quantization — an architecture change for cross-review.

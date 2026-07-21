# Sub-increment 3 (probe recoverability) — writedown

**Date:** 2026-07-20 · **Branch:** `stage2-probe-recoverability` (off `stage2-llm-parrot-null` @
`fcc5bf6`) · **Design:** `docs/superpowers/specs/2026-07-20-probe-recoverability-subinc3-design.md`
(untracked; SHA-256 `d0a35334…508c40` pinned in `probe_spec.DESIGN_DOC_SHA256`, hash-guarded).
**$0 study:** local CPU only; wall 144 s (mp.Pool). Freeze commit `40cd757` strictly precedes this
measurement (git-visible spine); GW positive control PASSED at the frozen budgets before the freeze.

## 1. Headline

**χ_resp is CERTIFIED as a critical-point locator on ground truth (locator PASS, all margins), and
`n_resp` is NOT ACTIVATED (transform FAIL, all margins) — the collision+censor gap is now a
measured quantity, growing toward criticality exactly as the owner's correction predicted.** H1b's
n placement remains BLOCKED (now with a measured reason stacked on the structural one). Option B
did NOT activate (the gate passed); the OASIS accessibility pilot is authorized by the frozen chain
**pending the owner's ratification of the pilot authorization rule** (§6).

## 2. Pre-freeze construction correction (disclosed plan deviation; the control doing its job)

The plan's `χ_resp = Var(S)` FAILED the frozen locator on the independent-capped-GW control
(Binomial offspring, independent trees, no collisions/horizon censoring, terminal cap at
N_AGENTS — wording corrected 2026-07-21 per review: "exact GW" overstated the construction; the
cap is integral to it) before anything was
frozen: in a capped system Var(S) peaks at θ(1−θ)·cap², systematically supercritical — measured
displacement +0.24 in m (12/12 seeds); Fano +0.08. Adopted: **`χ_resp = CV²(S) = Var(S)/S̄²`**,
pinched at the crossing from both sides (subcritical σ²/(1−m); capped-supercritical (1−θ)/θ) —
control-measured: argmax m = 0.972, crossing in the neighbor interval, 11/12 seeds, prominence
26.5×. Var(S)/Fano retained as recorded-not-gated diagnostic columns in the banked artifact.

## 3. The banked measurement (`2026-07-20_probe_recoverability.json`; byte-reproducible)

Frozen design executed exactly: 17-eps grid × 12 seeds, fixed `MU_NEWS_PROBE = 0.4` (the owner's
drive-confound correction — one drive across the whole primary surface), `M_ELIGIBLE = 512` equal
support (measured eligible per run: min 903, median 1001 — the thin-run guard never approached
firing), horizon 4000, tagged-native markers, per-tree retention.

**LOCATOR — PASS (the gate):**
- χ_resp peak at **eps_hat = 0.12** (interior); measured n_gen = 1 crossing **eps_c_gen = 0.1104**
  — inside the peak's neighbor interval [0.11, 0.125].
- Prominence **4.80×** (floor 2.0) · seed consistency **12/12 = 1.0** (floor 0.75).
- The crossing sits well below EPS_CRIT = 0.134 (realized n_gen at 0.134 is **1.308**) — the
  clustering shift the dense window was frozen to catch; distance recorded-not-gated (0.014).

**TRANSFORM — FAIL (n_resp NOT activated), with margins:**
- Held-out |n_resp − n_gen| at the accuracy-range points: **0.0632 / 0.0780 / 0.1032** (eps
  0.08/0.09/0.10) vs tolerance 0.05 — every point strictly above.
- The mean collision+censor gap Δ = n_gen − n_resp grows monotonically toward and past the
  crossing: **0.063 → 0.078 → 0.104 → 0.164 → 0.265** (eps 0.08 → 0.12). The realized-response
  undercount is not a constant offset a calibration could absorb blind — it is regime-dependent,
  largest exactly where H1b's band lives.
- **(b2) resolution floor — FAIL:** 2·SD_test(n_resp) = 0.1167 at the one band point (floor 0.05).
- Instrument-not-defect separation: the independent-capped-GW control cleared the same transform
  at TOL/2, so
  this failure is a property of the ABM's collision/censoring/finite-population operator — the
  precise content of the owner's n_resp correction, now measured.

**Diagnostics (recorded-not-asserted):** lag1 marker autocorrelation median 0.000 / max 0.128 (the
seed-level-only inference rule was conservative and validated); sensitivity panel at eps 0.12:
χ_resp = 3.61 / 3.58 / 3.27 at mu_news 0.4 / 0.5 / 2.0 (mild drive sensitivity — the fixed-drive
design made this a non-issue by construction rather than by hope); Var(S)/Fano columns banked.

## 4. Scope

χ_resp certification binds to the **exact operator fingerprint** (N=800, K_REACH=4, MU_STEP=0.5,
Lomax 0.35/1.7, horizon 4000, censor-at-horizon, the eligibility rule, MU_NEWS_PROBE=0.4). **No
OASIS transfer without separate calibration.** χ_resp and n_resp share one seeded statistic —
neither this PASS nor anything downstream discharges line 189's independent-second-diagnostic
requirement (OPEN). **H1b blocked in all branches**; §9a/§9b remain retired-as-blocked; def-#2
remains calibration-FAILED. No regime claim, no criticality claim is made here.

## 5. Locks & reproducibility

`tests/test_probe_recoverability_finding.py` (@slow) — anti-relaxation in BOTH directions: the
locator PASS locked with its margins AND the transform FAIL locked with its margins (a silent
tolerance-lift that "activates" n_resp breaks the test), plus full byte-reproduction of the banked
artifact from the frozen design (verified green, 129 s). Fast suite 209 passed. Ops note (recorded):
the first grid launch was wedged by the macOS spawn/stdin-heredoc interaction (workers respawning,
zero science executed, no artifact written); relaunched from a real script file with a
`__main__` guard — the lesson lives in the runner's docstring.

## 6. Pending owner decisions

1. **Pilot authorization rule** (flagged at the freeze): recommended — the OASIS accessibility
   pilot (~$2, frozen construction) runs on locator-PASS alone, which the gate now satisfies;
   alternative — require the full PASS incl. the transform (which failed), i.e. no pilot.
2. Branch merge sequencing (this branch stacks on unmerged `stage2-llm-parrot-null`).

## 7. Explicitly OPEN

Independent second diagnostic (line 189); H1b n placement; OASIS-side χ_resp/n_resp calibration
(the pilot tests channel accessibility only); §9a/§9b retired; def-#2 calibration-FAILED.

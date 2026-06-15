# HANDOFF — S0.1 `critaudit` instrument-core build (resume in a fresh session)

**Date:** 2026-06-16 · **Branch:** `s0.1-instrument-core` (commit work HERE, not `main`) · **Status:** Tasks 0–3 done, 13 tests green; resume at **Task 4**.

> **First action for the new session:** read this file, then `git -C /Users/zenith/Desktop/crowd-criticality checkout s0.1-instrument-core` (you should already be on it), confirm `pytest -m "not slow" -q` is green, then continue the subagent-driven build from Task 4. Invoke `superpowers:subagent-driven-development` and follow its loop.

---

## 1. What this is

Building the `critaudit` Python toolkit (S0.1 = "prove the instrument on synthetic ground truth"). It estimates branching-ratio criticality (Hawkes `n`, CSN power-laws, the crackling-noise scaling relation) and validates the estimators on known-ground-truth generators. Greenfield package, `src/` layout, strict TDD.

- **Plan (task source):** `docs/superpowers/plans/2026-06-15-s0.1-critaudit-instrument-core.md` (17 tasks, 0–16).
- **Spec (design of record):** `docs/superpowers/specs/2026-06-15-s0.1-critaudit-instrument-core-design.md`.
- **Decision history (the methods saga):** `DECISIONS.md`, the `2026-06-15` entries (read the last ~5 for the Gate-A.2 demotion).
- **Phase-2 robustness layer is firewalled** (sibling spec, `…phase2-robustness-design.md`) — do NOT build any `kernel_select`/`meanvar`/`baseline` module in this build.

## 2. ⚠️ CRITICAL — the Gate-A.2 demotion (read before Tasks 10–13)

A long methods investigation **refuted** the plan's original scaling-relation design and **demoted Gate A.2 to a coarse corroborative check.** **The plan's Tasks 10, 11, 12, and the A.2 cell of Task 13 are STALE** — they describe a duration-`x_min` floor / reference-differenced-null / sign-test design that was **withdrawn**. **Do NOT build them as the plan text says.** Use the corrected specs in §6 below (provide them to the implementer subagents directly — you hand each subagent its task text anyway, so you needn't edit the plan, though updating the plan file first is cleaner).

**Why (one paragraph):** Gate A.2's discrimination at achievable sample sizes is intrinsically **coarse** (resolution `Δ_min ≈ 0.12–0.49`, set by the CSN marginal-exponent `τ,α` noise that `(α−1)/(τ−1)` amplifies — *not* the `1/σνz` estimator; a joint `(τ,α)` fit can't close the gap). A genuinely critical generator gives `Δ → 0` with N (no bias floor — an earlier "floor" was single-seed noise, withdrawn). So A.2 corroborates the `n`-based criticality claim coarsely ("scaling relation not grossly violated") and is **not** a fine quantitative gate. The headline criticality evidence is the branching ratio `n` + Gate A.1 (CSN). Full detail: `DECISIONS.md` 2026-06-15 + `results/s0.1_snz_triangulation/*.txt` + `verification/s0.1_*.py`. The pre-reg draft was already reworded to match (H3, §6, §7, §9) — **that's a methods follow-up, not a build task.**

**Concrete consequences for the build:**
- `1/σνz` estimator = **`curv`** (curvature-corrected `⟨S|T⟩` slope), a *reasonable, not load-bearing* estimator. No shape-collapse, no duration-`x_min` floor.
- `AvalancheSet` has **NO `profiles` field** (shape-collapse was dropped). It's `sizes, durations, censored` — already built in Task 1, leave it.
- `gate_a2` exposes **`corroborate(...)`**, not `classify(...)`. No reference-null, no informativeness ceiling, no consistent/inconsistent/inconclusive trichotomy.

## 3. Done so far (each its own commit, clean resume points)

| Task | Module | Commit | Tests |
|---|---|---|---|
| 0 | scaffold (`pyproject.toml`, `Makefile`, CI, smoke) | `b455774` | 1 |
| 1 | `src/critaudit/types.py` (`EventStream`, `AvalancheSet`) | `f22ce61` | 5 |
| 2 | `src/critaudit/generators/branching.py` (Galton–Watson) | `98cdd19` | 4 |
| 3 | `src/critaudit/generators/hawkes_sim.py` (thinning + `choose_backend`; `_simulate_cluster` is a `NotImplementedError` stub) | `a4aa0cb` | 3 |

`pytest -m "not slow" -q` → **13 passed** on `s0.1-instrument-core`.

## 4. The build loop (how to run it)

Use `superpowers:subagent-driven-development`. Per task:
1. **Dispatch an implementer subagent** (model **`sonnet`**) with the FULL task text + scene-setting context pasted in (never make them read the plan file). Tell them: work from `/Users/zenith/Desktop/crowd-criticality`, branch `s0.1-instrument-core`, commit there, strict TDD, don't touch `main`/`docs`/`verification`.
2. Read its report (DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT).
3. **Review proportionately:** for the substantive numerical tasks (7–8 MLE, 9 residuals, 10–11 scaling, 13 harness) do the full two-stage review (spec-compliance reviewer, then code-quality reviewer, each a subagent); for mechanical tasks a controller self-check (read the commit, confirm spec + green tests) is fine.
4. Next task. Continuous — don't pause to ask "should I continue".
5. After Task 16: dispatch a final whole-implementation code reviewer, then `superpowers:finishing-a-development-branch`.

**Conventions (already established in Tasks 0–3):** strict TDD (failing test → confirm fail → implement → confirm pass → commit); one commit per task; explicit seeded `numpy.random.Generator` (never the global); heavy tests marked `@pytest.mark.slow`; CI / `make test` run `-m "not slow"`; per-generator `=== <name> sanity ===` prints (once per process).

## 5. Environment gotchas (real — will bite the subagents)

- **`make install` FAILS locally:** this machine's `make` resolves `python` → `/usr/local/bin/python` = **Python 2.7**. The package is already installed **editable under python3.11**; tell subagents to use `python3 -m pip …` / `pytest` directly, **not** `make install`. (CI is fine — it uses `setup-python`.) Tests run via `pytest -m "not slow" -q`.
- **`tick` is NOT installable** (no wheel for this platform/Python; numpy-2 incompatible) — that is WHY the Hawkes MLE is built by hand (Tasks 7–8). Do not try to use `tick`.
- **`powerlaw` 2.0.0 IS installed** — wrap it for CSN (Task 6). Its KS `x_min` search is **slow on large arrays** (100k+ pts, seconds per fit); keep test sample sizes modest, mark anything heavy `@pytest.mark.slow`.
- **Background scripts block-buffer stdout** (output appears only at completion); use `python3 -u` if you need live progress.
- **4 untracked `verification/adv_*.py`** are adversarial-reviewer scratch (unvetted) — ignore them; the build never touches `verification/`. Don't commit them.
- **This `HANDOFF` file** should be deleted before the branch is merged (it's transient).

## 6. Remaining tasks 4–16 (with the demotion rewrites inline)

Tasks **4–9, 14–16** are fine to build **as the plan text says** (paste the plan's task text to the implementer). Tasks **10–13** use the corrected text below.

- **Task 4** — `hawkes_sim.py` cluster backend (immigrant-cluster / Hawkes–Oakes) replacing the stub + the `n=0.6` thinning↔cluster agreement cross-check. *(plan as-is)*
- **Task 5** — `generators/lookalike.py` `scaling_break(critical, delta, rng)` (full shuffle of the `(S,T)` pairing). *(plan as-is — still needed: the full-shuffle look-alike is the gross-violation case the coarse harness rejects.)*
- **Task 6** — `powerlaw/csn.py`: wrap `powerlaw` + Clauset bootstrap-p; `PowerLawFit`, `fit_powerlaw`, `_fit`; Gate A.1 `.passes`. *(plan as-is)*
- **Task 7** — `hawkes/mle.py`: Ogata-recursion NLL + point MLE (`HawkesFit`, stationarity-unconstrained `n`). *(plan as-is — full two-stage review)*
- **Task 8** — `hawkes/mle.py`: profile-likelihood CI via `brentq` (asymmetric, upper limit free to exceed 1). *(plan as-is — full review)*
- **Task 9** — `hawkes/residuals.py`: time-rescaling (Ogata) residuals + KS. *(plan as-is)*

### Task 10 (REWORDED) — `scaling/crackling.py`: exponents + `curv` + `delta`
Files: `src/critaudit/scaling/__init__.py` (empty), `src/critaudit/scaling/crackling.py`; Test `tests/test_crackling.py`.
```python
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from critaudit.powerlaw.csn import _fit   # the powerlaw.Fit wrapper from Task 6

@dataclass
class DeltaResult:
    samples: np.ndarray
    ci: tuple
    halfwidth: float

def _clean(av):
    if av.censored is not None:
        keep = ~np.asarray(av.censored)
        return np.asarray(av.sizes)[keep], np.asarray(av.durations)[keep]
    return np.asarray(av.sizes), np.asarray(av.durations)

def _curv_slope(sizes, durations, min_count=50):
    """1/snz via the curvature-corrected bulk fit log<S|T> = a + g*logT + b/T -> g.
    (A reasonable, NOT load-bearing estimator: Gate A.2 is a coarse corroborative check.)"""
    T, M = [], []
    for t in np.unique(durations):
        m = durations == t
        if m.sum() >= min_count:
            T.append(t); M.append(sizes[m].mean())
    if len(T) < 4:
        return np.nan
    T = np.array(T, float); M = np.array(M)
    X = np.column_stack([np.ones_like(T), np.log(T), 1.0 / T])
    return float(np.linalg.lstsq(X, np.log(M), rcond=None)[0][1])

def exponents(av, min_count=50, xmin_size=None, xmin_dur=None):
    sizes, durations = _clean(av)
    tau = float(_fit(sizes, xmin=xmin_size).power_law.alpha)
    alpha = float(_fit(durations, xmin=xmin_dur).power_law.alpha)
    return tau, alpha, _curv_slope(sizes, durations, min_count)

def delta(av, min_count=50):
    tau, alpha, inv = exponents(av, min_count)
    return (alpha - 1.0) / (tau - 1.0) - inv
```
Tests (TDD): on critical GW (`galton_watson(1.0, 40000, rng)`) assert `1.4<tau<1.6`, `1.8<alpha<2.2`, and `abs(delta(av)) < 0.3` (COARSE — this is a coarse check, do not assert a tight bound); assert `_clean` excludes censored. Commit `feat(scaling): crackling exponents (curv 1/snz) + delta`.

### Task 11 (REWORDED) — `scaling/crackling.py`: `joint_bootstrap`
Add to `crackling.py` (uses `AvalancheSet` from `critaudit.types`):
```python
from critaudit.types import AvalancheSet

def joint_bootstrap(av, B, rng, min_count=50):
    """Resample avalanches; re-estimate all exponents per replicate (re-running CSN
    so x_min is re-selected each replicate) -> Delta's bootstrap CI for reporting."""
    sizes, durations = _clean(av)
    N = sizes.size
    samples = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, N, size=N)
        sub = AvalancheSet(sizes=sizes[idx], durations=durations[idx])
        tau, alpha, inv = exponents(sub, min_count)
        samples[b] = (alpha - 1.0) / (tau - 1.0) - inv
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return DeltaResult(samples=samples, ci=(float(lo), float(hi)), halfwidth=float((hi - lo) / 2))
```
Tests: returns a `DeltaResult` with `samples.size == B`, `halfwidth > 0`; on critical GW the CI brackets a small `|Δ|`. (Mark slow if B×N is large.) Commit `feat(scaling): joint avalanche bootstrap for Delta CI`.

### Task 12 (REWORDED) — `scaling/gate_a2.py`: `corroborate`
File `src/critaudit/scaling/gate_a2.py`; Test `tests/test_gate_a2.py`.
```python
from __future__ import annotations

def corroborate(delta_result, resolution=None, k=2.0):
    """Coarse corroboration (NOT a fine pass/fail; no reference-null, no ceiling).
    resolution = the Gate-A.2 resolution Delta_min; if None, use the bootstrap half-width
    as a per-realization proxy. 'not-grossly-violated' if |mean Delta| <= k*resolution,
    else 'grossly-violated'."""
    res = delta_result.halfwidth if resolution is None else resolution
    return "not-grossly-violated" if abs(float(delta_result.samples.mean())) <= k * res else "grossly-violated"
```
Tests: a `DeltaResult` centred near 0 with modest half-width → `"not-grossly-violated"`; one centred at ~2 (the full-shuffle look-alike) → `"grossly-violated"`. Commit `feat(scaling): Gate-A.2 coarse corroboration`.

### Task 13 (REWORDED A.2 cell) — `validation/gate0a.py` harness
Build the Gate-0(a) harness, but the **A.2 cells are coarse-corroborative**, not the old sign-test:
- **Critical generator:** `corroborate(joint_bootstrap(crit, …))` → assert **`"not-grossly-violated"`**.
- **Scaling-breaker (full shuffle, Task 5):** `corroborate(...)` → assert **`"grossly-violated"`**.
- The harness also reports `Δ` and the resolution it used. **No reference-null, no ceiling.**
- **Keep unchanged from the plan:** the **Gate A.1 cells** (G2 critical CSN passes; CSN-killer `m=0.7` CSN-rejects via LRT-vs-truncated), the **thinning↔cluster backend cross-check** at `n=0.6`, and the **writedown** artifact to `results/s0.1_gate0a/`.
- Avalanche counts: a coarse check is fine at moderate counts; use ~2e4–5e4 so CSN is stable. The full certification test is `@pytest.mark.slow`; a small-`k` plumbing test is the fast one (assert structure + the robust `"grossly-violated"` cell, not the critical cell at tiny `k`).

- **Task 14** — `experiments/recovery_grid.py`: multiprocessing `n`-recovery coverage grid. *(plan as-is)*
- **Task 15** — `experiments/recovery_grid.py`: parametric bootstrap CI + profile↔bootstrap audit at `n=0.99`. *(plan as-is)*
- **Task 16** — full-suite green + final integration; `make gate0a` certification; `make grid`. *(plan as-is; then final review + finishing-a-development-branch.)*

## 7. Definition of done

Fast suite green (`pytest -m "not slow"`); `make gate0a` (run as `python3 -m critaudit.validation.gate0a`) exits 0 with the coarse 2×2 holding (critical not-grossly-violated; scaling-breaker grossly-violated; CSN-killer A.1-rejected; backend cross-check agrees; writedown emitted); recovery grid coverage ≥0.90 for `n∈{0.3,0.6,0.9}` at `N≥1e4`; no Phase-2 module exists; `DECISIONS.md` current. Then `superpowers:finishing-a-development-branch`, deleting this HANDOFF file.

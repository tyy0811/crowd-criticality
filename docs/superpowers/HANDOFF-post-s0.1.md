# HANDOFF — S0.1 complete; what's next (read in a fresh session)

**Date:** 2026-06-16 · **Branch:** `main` (S0.1 merged + pushed) · **Repo:** https://github.com/tyy0811/crowd-criticality

> **S0.1 `critaudit` instrument-core is DONE.** Gate-0(a) certification PASSES, fast suite green (37), merged to `main`, pushed. This handoff is for the **next phase**, not for resuming S0.1. There is no half-finished work to pick up — the next session chooses among the options in §4/§5.

---

## 1. Where things stand

- **S0.1 instrument-core complete** (`src/critaudit/`): types, generators (Galton–Watson, Hawkes thinning+cluster, scaling-breaker, exact-power-law control), CSN power-law + Clauset bootstrap (Gate A.1), Hawkes MLE + profile CI + residuals, crackling exponents + `corroborate` (coarse Gate A.2), the Gate-0(a) 2×2 harness, the recovery-coverage grid.
- **DoD met / honestly accounted:** fast suite **37 passed**; `python3 -m critaudit.validation.gate0a` **PASSES** (writedown in `results/s0.1_gate0a/`); recovery-coverage **trip-wire clean** (n=0.3→0.933, 0.6→0.967, 0.9→1.000; `results/s0.1_recovery/`); Phase-2 firewall intact; `DECISIONS.md` current.
- **Authoritative records:** `DECISIONS.md` (read the **2026-06-16** entries — they carry the three build-time methodology findings); the design spec has ⚠️ correction banners (§5, §6, §149) pointing to DECISIONS; memory `[[measure-before-amending]]`, `[[result-blind-rule-selection]]`.

## 2. The three S0.1 build-time findings (already resolved; context for §4)

1. **GW `size_cap` 1e6→1e10.** The 1e6 cap depleted the critical generator's tail, so Clauset's (valid) truncated-PL LRT correctly rejected it → critical couldn't pass A.1. Generator bug; **CSN criterion + pre-reg unchanged**.
2. **Borel vs strict Clauset → exact-power-law A.1 control (Option 3).** Critical-GW sizes are Borel-Tanner (only *asymptotically* `s^-3/2`), so strict GoF rejects them at large N. The Borel was never a valid strict-power-law positive control; A.1 is now gated on an exact Zipf control (`generators.exact.pure_power_law`, exponent 2.5 for tractability), critical anchors the A.2 axis with informational A.1. **No criterion change.**
3. **Flaky `test_csn`:** `powerlaw.generate_random` uses the unseeded global RNG → seeded it.

## 3. ⚠️ Methodology debt that must be paid BEFORE the pre-reg freezes

These are queued in `DECISIONS.md` 2026-06-16, NOT patched into the build. The next methods round must address them:

- **Real-data Gate-A.1 criterion.** Strong evidence the *strict* Clauset GoF is the wrong bar for **real** data: if the exactly-critical Borel fails it at achievable N (non-universal bulk curvature), real critical markets/sims (bulk structure + noise) will fail it too → strict-GoF A.1 would reject genuinely-critical systems. This is the same shape as the A.2 demotion. **Decide it at cross-review with the Borel evidence before the pre-reg locks** — an LRT-based A.1 (power_law beats non-nested alternatives) is the likely replacement, but it's a registered-criterion change, so don't do it unilaterally.

## 4. Deferred S0.2 infra (compute, not methodology)

- **Full ≥0.90 coverage certification.** The local trip-wire (R=30) corroborates calibration but is underpowered to certify (Clopper-Pearson: 30/30 → ~0.88 lower bound). The full R≥50 grid is intractable on this 8-core machine (~150s/profile-CI-fit; mp.Pool oversubscribes — general load, NOT a tunable BLAS pool; `threadpoolctl(1)` didn't help). **Run it via Modal CPU fan-out** (one realization per container).
- **Profile warm-start** (per-fit cost lever): warm-start the profile's nuisance `(μ,β)` optimization from the previous grid point instead of cold-starting each — cuts the fundamental cost, compounds across thousands of fits.

## 5. The actual next build: Phase-2 robustness (now UNBLOCKED)

The Phase-2 spec (`docs/superpowers/specs/2026-06-15-s0.1-phase2-robustness-design.md`) is a **firewalled STUB**: "DO NOT START until Gate-0(a) passes … When Gate-0(a) passes, this stub gets its own brainstorming round → full spec → plan." **Gate-0(a) now passes**, so that firewall is liftable. Phase 2 is what's needed to fit **real** data honestly (a Stage-1 prerequisite). The next session, if doing Phase-2, should: invoke `superpowers:brainstorming` on the stub → write the full spec → write the plan → build (subagent-driven, like S0.1). Do this on a **new feature branch**, not `main`.

> Recommended ordering: settle the §3 real-data-A.1 question (methods, with cross-review) **before or alongside** the Phase-2 spec, since Phase-2 is about real data and the A.1 bar is part of that contract.

## 6. Environment gotchas (carry over — these bit repeatedly)

- **`make install` FAILS** (this machine's `make` resolves `python`→Python 2.7). Use `python3 -m pip` / `pytest` directly. Package is editable-installed under python3.11.
- **`powerlaw` discrete fits:** ~0.8s on a clean light tail, but **~8s** on the heavy critical tail (full size range) — that's why `test_csn` (~4 min), `test_mle` (~5 min), and the gate0a certification are slow. CI marker split keeps `-m "not slow"` runnable; heavy realistic-N tests are `@pytest.mark.slow`.
- **Multiprocessing oversubscribes** on this 8-core box (numpy = scipy-OpenBLAS; env caps and `threadpoolctl` didn't drop the load). The recovery-coverage grid is **not** locally certifiable → Modal (§4). For local ad-hoc mp runs, guard scripts with `if __name__ == "__main__":` (spawn re-imports and will fork-bomb otherwise — it happened this session, load hit 170).
- **4 untracked `verification/adv_*.py`** are adversarial-reviewer scratch — ignore, never commit.
- **This HANDOFF** is transient — delete it once the next phase is underway.

## 7. How to start the next session

Paste:

> Read `docs/superpowers/HANDOFF-post-s0.1.md` in `/Users/zenith/Desktop/crowd-criticality`. S0.1 is done and merged. I want to start the next phase — [either: "settle the deferred real-data Gate-A.1 question (§3)" OR "begin the Phase-2 robustness brainstorming (§5)" OR "set up Modal for the full coverage cert (§4)"]. Work on a new branch.

Everything needed is in this file + `DECISIONS.md` (2026-06-16 entries).

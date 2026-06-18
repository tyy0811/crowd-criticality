# HANDOFF — S0.4 resolved → estimator promoted → source-B deploy PAUSED on disk (2026-06-18)

**Branch:** `s0.4-data-feasibility-spike` (grew past the spike — holds Stage-1 + production work too).
**Status:** the project-gating question is **answered**; the estimator is **in production behind fast
tests**; source-B forward capture was **deployed and working, then deliberately stopped** because the
Mac's disk is nearly full — the **live open thread is the restart decision** (below).

Transient doc — remove when the next phase is underway.

---

## TL;DR — what landed

**S0.4 granularity is RESOLVED (qualified G1 cleared).** 2 s on-chain block-time quantization is **not** a
barrier to recovering the Hawkes branching ratio `n̂` in the project regime (power-law, near-critical). The
`T_threshold = inf` was **estimator inadequacy** (continuous-MLE on tied block timestamps), fixed by a
**within-bin-marginalizing MCEM** that tracks the full-data MLE to ≤0.013 across the whole envelope incl
the near-critical × sharp-within-bin hard corner. **Source A viable on the granularity axis; B is the
forward hedge.** Authoritative record: `DECISIONS.md`, the two 2026-06-16 "qualified-G1" entries.

**The barrier MOVED, didn't vanish:** clearing granularity relocates the n→1 constraint onto the
**event-count floor** (S0.2) — now the *operative* limit for the regime that matters, coupled to real-data
certification. That's why B's forward capture matters (supplies event-sufficiency + cert data).

---

## ⚠️ LIVE OPEN THREAD — source-B restart decision (resume here)

B was deployed (launchd service, capturing trades-only) and verified healthy, **then stopped by request**
because the disk is the constraint:

- **Disk:** `233Gi total, 204Gi used, ~2.9Gi free, 99% capacity` (measured 2026-06-18). Dangerous for macOS
  independent of the capture. *(macOS "purgeable" space isn't in `df` — user should check  → Storage for
  real headroom.)*
- **Capture rate (measured live):** ~1.4 trades/s × ~440 B = **~54 MB/day ≈ 1.6 GB/month** plain;
  **~250 MB/month gzipped**.
- **Current state:** launchd agent **unloaded** (stopped), `~/b_capture.jsonl` **deleted** (clean slate).
  Deploy infra **preserved** for a one-command restart.

**The decision to make with the user (paused here):** where the capture lands —
1. **gzip to internal** (~250 MB/month) — needs a small recorder change to append to `b_capture.jsonl.gz`;
2. **external drive** — point the plist `--out` at `/Volumes/<drive>/…`, costs internal disk nothing;
3. **free internal space first**, then capture (plain or gzipped).

Do NOT restart a multi-week capture onto the 99%-full internal disk as-is.

### Source-B deploy mechanics (all in place, just stopped)
- **launchd agent:** `~/Library/LaunchAgents/com.crowdcriticality.brecorder.plist` — `RunAtLoad`+`KeepAlive`
  (auto-restart), wraps `/usr/bin/caffeinate -i` (idle-sleep guard) → anaconda python → the recorder →
  `--out ~/b_capture.jsonl --max-days 30 --refresh-hours 6`. Restart: `launchctl load -w <plist>`; stop:
  `launchctl unload <plist>`.
- **Recorder copy:** `~/brecorder/ws_recorder.py` (a COPY of the committed `spike/s0.4/ws_recorder.py` —
  launchd can't read `~/Desktop` due to macOS TCC, so it runs from non-protected `~/`). If the repo recorder
  changes, re-copy + reload.
- **Recorder behavior:** writes **only `last_trade_price`** events (per-trade, with ms server match
  timestamp + `asset_id` for per-market grouping) — skips book/price_change to cut disk ~25×; re-selects the
  basket every 6 h.
- **Hard-won lessons (don't relearn):** a bare `python` is **system Python 2** here — always
  `/Users/zenith/anaconda3/bin/python`; `nohup &` is killed by closing the Terminal (→ launchd); launchd
  can't read `~/Desktop` (→ `~/brecorder`); **laptop lid-close still sleeps it** (`caffeinate -i` blocks
  idle sleep only — for 24/7 keep lid open on power, clamshell+display, or an always-on machine).
- **Verify a running capture:** `pgrep -fl ws_recorder.py`; `tail -2 ~/brec.log`; and
  `/Users/zenith/anaconda3/bin/python` reading `~/b_capture.jsonl` for trade count + `mod-1000ms` timestamp
  spread (wide ⇒ sub-2 s match timing being captured).
- **ToS gate:** the user's one-time read of polymarket.com/tos for sustained public-data research collection
  (documented-public-endpoint anchor confirmed; browser-UA is ordinary plumbing).

---

## Repo state (committed, newest first)
- `700171b` recorder: last_trade_price-only + periodic basket-refresh (multi-week-safe)
- `79ae47f` (prior handoff — this supersedes it)
- `cff8b48` granularity certification harness + power-law generator
- `59f1dbc` **promote** within-bin MCEM → `critaudit.hawkes.binned` (modular) + `tests/test_binned.py`
- `b82cbbc` writedowns → tables · `96046ad` power-law **verdict** + DECISIONS resolution
- `48709fc` power-law generator + SOE certified · `ed93cdd` source-B order-preservation verified + URL/UA fix
- `ac8381a` within-bin MCEM de-risk · `55096b8` qualified-G1 DECISIONS entry

**Held / uncommitted (intentional, keep held):** `results/s0.4_feasibility/2026-06-16_quantization_sweep.txt`
(the retired `inf` sweep), `..._granularity_crossreview_brief.md`, `spike/s0.4/quantization_sweep.py`, the
`spike/s0.4/tests/test_granularity.py` mod. **NEVER commit** `verification/adv_*.py` (4, untracked).
`spike/s0.4/run_recorder.sh` is an untracked nohup-supervisor — superseded by launchd, ignore it.

**Production (the deliverable):** `critaudit.hawkes.binned`
- `ExpKernel`/`PowerLawKernel` (`.soe()` unit-mass; estimator is kernel-agnostic),
  `fit_binned(counts, grid, horizon, kernel, rng) -> BinnedFit(n, mu, acceptance, ess, trajectory)`,
  `certify_granularity(times, grid, horizon, kernel, rng) -> GranularityCert(n_full, n_binned, diff, fit)`
  — full-timing vs binned n̂; **on real B trades this IS the real-data granularity certification.**
- `critaudit.generators.powerlaw_hawkes` (`simulate`, `rescaled_times`). `tests/test_binned.py` (5 fast tests, ~24 s).
- Prototypes + numbers/tables: `stage1/granularity/` (`*_recovery_verdict.md`, `*_powerlaw_components.md`,
  `*_derisk_recovery.md`, plus the `within_bin_mle.py` / `powerlaw_hawkes.py` / `mcem_powerlaw.py` chain).
  `results/s0.4_feasibility/2026-06-16_source_b_verification.md` (B preserves within-bin order).
- **Firewall lifted** (Stage-1): `src/critaudit` edits sanctioned; `pyproject` unchanged (no new deps;
  `websockets` is offsite-only).

---

## Next steps (priority-ordered)
1. **Resolve the source-B restart (the live thread above)** — pick gzip / external / free-space *with the
   user*, wire it up, relaunch the launchd agent, verify. Time-sensitive (the only clock that can't restart),
   but **not** onto the 99%-full disk.
2. **Real-data certification** — once B has a few days of `~/b_capture.jsonl`, point `certify_granularity` at
   it per market (build the thin B-JSONL → event-times reader first; schema in the B-verification writedown).
   Small `|diff|` certifies 2 s loses no n̂ for that market. The remaining S0.4 risk.
3. **S0.2 — near-critical event-count floor** (synthetic estimator-stability). Now the operative limit.
4. **Held A-side tasks 5/6/8** — tidy only when activating A-side for historical certification.
5. **Branch integration** — this branch spans spike + Stage-1 + production; decide merge-to-`main`. git user: tyy0811.

## Working context
- Disciplines that made the verdict trustworthy: `MEMORY.md` → `anchor-each-component-before-reliance`
  (+ `measure-before-amending`, `result-blind-rule-selection`). Match the rigor; surface forks for
  cross-review; result-blind DECISIONS; verify-before-trust (it caught the Python-2 recorder bug twice).

### Paste into the new session
> Read `docs/superpowers/HANDOFF-s0.4-stage1.md` (branch `s0.4-data-feasibility-spike` is checked out).
> S0.4 granularity is resolved, the within-bin estimator is in `critaudit.hawkes.binned`, and source-B
> capture is deployed-but-stopped on a near-full disk. I want to **[resume the B restart decision — I've
> {freed space / plugged in an external drive at /Volumes/… / want gzip}]**  OR  **[start S0.2]**  OR
> **[build the B-JSONL reader + real-data certification]**. Hold the standing disciplines (anchor-each-
> component, result-blind DECISIONS, never commit `verification/adv_*.py`, always use the anaconda python3).

#!/usr/bin/env python3
"""CONVERGENT MEASUREMENT (cross-review round 1 -> 2): the FALSE-MIGRATION RATE of genuine near-critical
under the 3-step trust gate, at each over-floor market's OWN realized (N, swing) regime. The one run that
decides whether the per-market split (1 genuine / 2 mis-modelled) is earned, or whether near-criticality
is simply NOT RESOLVABLE at 18-22k (a real Filimonov-Sornette result either way).

Folds cross-review findings 1-6 into one principled, result-blind run:
  #1 floor non-monotone at 18k (2/4, under-powered): replace the generic-plant coarse floor map with a
     per-market false-migration rate at the market's EXACT realized N, >=8 seeds.
  #2 grid-extension never run on genuine synthetics: the gate HERE includes grid-extension, applied to the
     genuine-near-critical synthetics -- the missing composition that "rescues the noise" assumed.
  #3 ...3503 own-fit supercritical/unsimulable: BRACKETED by the pre-specified subcritical plant (n=0.90)
     at its (N, swing) -- its regime is calibrated even though its own fit cannot be planted.
  #4 "migrates to eps=0.02" is really a supercritical mode surfacing at eps=0.2: report the gate BOTH
     unconstrained (n<=1.2) and n<1-constrained, to separate a finite-window artifact from true supercrit.
  #5 calibration only at n_true=0.5 (+0.1 biased): plant at the NEAR-CRITICAL end (n=0.90), where the
     markets and the mu(t)<->long-memory-kernel confound live.
  #6 ramp units + N mismatch: simulate_ramp's realized swing is (1+ramp); pass ramp = swing_measured - 1,
     tune mu0 to the market's realized N, and REPORT realized N and swing per synthetic.

RESULT-BLIND ORDERING (finding 8 / measure-before-amending applied to the gate's OWN knobs): the gate's
decision rule (eps-extension range, n-grid, MIGRATE_TOL, peak<1) is FROZEN here in code; PHASE A measures
the per-regime false-migration baseline on known-truth synthetics and writes it out; only THEN does PHASE B
run the SAME frozen gate on the real markets. Nothing in the rule is tuned after the real peaks are seen.

PERFORMANCE: fit_mu_only recomputes the O(N) self-excitation recursion on EVERY likelihood eval. Here the
per-event self-excitation s (= A@a) and the self-compensator coef are cached per (eps,c) -- they depend
only on the kernel shape, not on n or mu -- and reused across the n-grid and all L-BFGS evals. `--verify`
asserts the cached profile-ll matches the tested fit_mu_only bit-close before any result is trusted.

USAGE:
  python convergent_migration_cal.py --verify     # golden: cached profile == fit_mu_only
  python convergent_migration_cal.py --smoke       # 1 regime x 1 seed, reduced grid: plumbing + timing
  python convergent_migration_cal.py               # full: Phase A (freeze) then Phase B (verdict)
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from scipy.optimize import minimize

from b_reader import read_markets
from critaudit.hawkes.binned import PowerLawKernel
from mu_t_hawkes import segment_edges_by_count

OUT = "/Users/zenith/b_capture/ws_capture.jsonl"
RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"

# ---- FROZEN gate knobs (locked BEFORE the real verdict; identical to the published grid-extension gate) -
FLOOR, SLEEP_GAP_S, K_FLEX = 16000, 60.0, 12
N_GRID = [0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20]
EPS_FULL = [0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.1]
C_GRID = [0.5, 1.0, 2.0]
EPS_MINS = [0.4, 0.2, 0.1, 0.05, 0.02]
MIGRATE_TOL = 0.15                       # identified iff |peak(0.02) - peak(0.4)| < TOL AND peak(0.02) < 1
# ---- calibration plant (near-critical end, off the test grid -> no home-field) ------------------------
N_PLANT, EPS_PLANT, C_PLANT = 0.90, 0.35, 1.7
SEEDS = 8                                # 4 seeds is what left the 18k floor cell ambiguous


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ============================ self-excitation cache + mu(t)-profile likelihood =========================
def self_excitation(times, a, betas):
    """Per-event self-excitation s_i = sum_k a_k * sum_{j<i} exp(-beta_k (t_i - t_j)), stable O(N)
    recursion. Depends ONLY on (times, kernel) -> cache across n and across all mu-fit L-BFGS evals."""
    t = times
    A = np.zeros((t.size, betas.size))
    for i in range(1, t.size):
        A[i] = np.exp(-betas * (t[i] - t[i - 1])) * (A[i - 1] + 1.0)
    return A @ a


def comp_coef(times, horizon, a, betas):
    """Self-compensator per unit n: sum_k (a_k/beta_k) * sum_i (1 - exp(-(horizon - t_i) beta_k))."""
    return float(np.sum((a / betas) * (1.0 - np.exp(-np.outer(horizon - times, betas))).sum(0)))


def profile_ll(times, horizon, s, cc, n, K):
    """max over piecewise-LINEAR mu(t) knots of the loglik, with n and shape (via cached s, cc) FIXED.
    Convex in mu -> single start. Bit-equivalent to mu_t_hawkes.fit_mu_only(...,n,K)['ll'] (--verify)."""
    t = times
    knots = segment_edges_by_count(t, K, horizon)[0]
    L = np.diff(knots)
    seg = np.clip(np.searchsorted(knots, t, side="right") - 1, 0, K - 1)
    w = (t - knots[seg]) / L[seg]
    loc = np.empty(K + 1)
    for j in range(K + 1):
        lo, hi = knots[max(j - 1, 0)], knots[min(j + 1, K)]
        loc[j] = np.sum((t >= lo) & (t < hi)) / max(hi - lo, 1e-9) * 0.5
    m0 = np.maximum(loc, 1e-6)

    def fg(m):
        if np.any(m <= 0):
            return np.inf, np.zeros_like(m)
        lam = (1.0 - w) * m[seg] + w * m[seg + 1] + n * s
        if np.any(lam <= 0):
            return np.inf, np.zeros_like(m)
        comp_mu = np.sum(0.5 * (m[:-1] + m[1:]) * L)
        f = -(np.sum(np.log(lam)) - comp_mu - n * cc)
        invlam = 1.0 / lam
        g = np.zeros(K + 1)
        np.add.at(g, np.arange(K), 0.5 * L)
        np.add.at(g, np.arange(1, K + 1), 0.5 * L)
        np.add.at(g, seg, -(1.0 - w) * invlam)
        np.add.at(g, seg + 1, -w * invlam)
        return f, g

    r = minimize(fg, m0, method="L-BFGS-B", jac=True, bounds=[(1e-9, None)] * (K + 1))
    return -float(r.fun)


def ll_grid(times, horizon, K, n_grid=N_GRID, eps_full=EPS_FULL, c_grid=C_GRID):
    """ll[(n,eps,c)] over the full grid, caching s + cc once per (eps,c)."""
    ll = {}
    for eps in eps_full:
        for c in c_grid:
            a, betas = PowerLawKernel(eps=eps, c=c).soe()
            s = self_excitation(times, a, betas)
            cc = comp_coef(times, horizon, a, betas)
            for n in n_grid:
                ll[(n, eps, c)] = profile_ll(times, horizon, s, cc, n, K)
    return ll


def peak_at(ll, eps_min, n_cap, n_grid=N_GRID, eps_full=EPS_FULL, c_grid=C_GRID):
    """peak-n over shapes with eps>=eps_min, optionally constrained to n<n_cap."""
    epss = [e for e in eps_full if e >= eps_min]
    ns = [n for n in n_grid if n_cap is None or n < n_cap]
    prof = [(n, max(ll[(n, e, c)] for e in epss for c in c_grid)) for n in ns]
    return max(prof, key=lambda x: x[1])[0]


def run_gate(times, horizon, K=K_FLEX):
    """The FROZEN 3-step gate on one event stream. Returns the peak-n trajectory under grid extension,
    both unconstrained (n<=1.2) and n<1-constrained, plus the identified verdict."""
    ll = ll_grid(times, horizon, K)
    traj = [peak_at(ll, em, None) for em in EPS_MINS]            # unconstrained
    traj_sub = [peak_at(ll, em, 1.0) for em in EPS_MINS]         # n<1-constrained (#4)
    migrated = traj[-1] - traj[0]
    identified = bool(abs(migrated) < MIGRATE_TOL and traj[-1] < 1.0)
    return dict(traj=traj, traj_sub=traj_sub, migrated=migrated,
                identified=identified, peak04=traj[0], peak002=traj[-1])


# ============================ ramp generator (corrected units, #6) =====================================
def simulate_ramp(mu0, ramp, n, T, eps, c, rng):
    """Lomax-kernel Hawkes with a LINEAR-ramp immigration mu(t)=mu0*(1 + ramp*t/T). REALIZED rate swing
    = mu(T)/mu(0) = 1 + ramp (so to hit a measured swing S, pass ramp = S - 1; see #6)."""
    mu_max = mu0 * (1.0 + max(ramp, 0.0))
    cand = rng.uniform(0, T, rng.poisson(mu_max * T))
    imm = cand[rng.uniform(0, 1, cand.size) < (mu0 * (1.0 + ramp * cand / T)) / mu_max]
    times, queue = list(imm), list(imm)
    while queue:
        p = queue.pop()
        kk = rng.poisson(n)
        if kk:
            for ct in p + c * ((1.0 - rng.uniform(0, 1, kk)) ** (-1.0 / eps) - 1.0):
                if ct < T:
                    times.append(ct); queue.append(ct)
    return np.sort(np.asarray(times, float))


def rate_swing(times, horizon, k_rate=8):
    """Measured rate swing = max/min over k_rate equal-time windows (matches nonstationarity_check.py)."""
    counts, _ = np.histogram(times, bins=np.linspace(0, horizon, k_rate + 1))
    rates = counts[counts > 0] / (horizon / k_rate)
    return float(rates.max() / rates.min()) if rates.size else float("nan")


def quarter_ratio(times, horizon):
    """Robust non-stationarity index: mean event rate in the LAST quarter / FIRST quarter of time. Smoother
    + monotone in the immigration ramp than max/min -> the calibration target (max/min is reported too)."""
    q = horizon / 4.0
    first = int(np.sum(times < q))
    last = int(np.sum(times >= horizon - q))
    return float(last / max(first, 1))


def mu0_for_N(N_target, ramp, n, T):
    """mu0 such that E[total events] = mu0*T*(1+ramp/2)/(1-n) = N_target (mean-of-ramp x branching;
    infinite-horizon approx -> heavy-tail truncation undershoots it, so calibrate() corrects empirically)."""
    return N_target * (1.0 - n) / (T * (1.0 + ramp / 2.0))


def calibrate(N_target, qr_target, n, T, eps, c, cal_seeds=3, iters=6):
    """Find (mu0, ramp) whose REALIZED (N, quarter-ratio) match the market's, averaged over cal_seeds.
    Branching + heavy-tail truncation dilute the immigration ramp and drop offspring past T, so immigration
    params != realized (naive ramp=swing-1 under-shot 7.7x->3.4x in smoke). This is finding 6 done
    properly: put the GENUINE synthetic at the market's actual regime, not an easier one."""
    ramp = max(qr_target - 1.0, 0.2)
    mu0 = mu0_for_N(N_target, ramp, n, T)
    for _ in range(iters):
        Ns, qrs = [], []
        for sd in range(cal_seeds):
            t = simulate_ramp(mu0, ramp, n, T, eps, c, np.random.default_rng(9000 + sd))
            Ns.append(t.size); qrs.append(quarter_ratio(t, T))
        N_real, qr_real = float(np.mean(Ns)), float(np.mean(qrs))
        ramp = float(np.clip(ramp * (qr_target / max(qr_real, 1.01)) ** 0.6, 0.05, 500.0))
        mu0 *= N_target / max(N_real, 1.0)
    Ns, qrs, sws = [], [], []
    for sd in range(cal_seeds):
        t = simulate_ramp(mu0, ramp, n, T, eps, c, np.random.default_rng(9000 + sd))
        Ns.append(t.size); qrs.append(quarter_ratio(t, T)); sws.append(rate_swing(t, T))
    return mu0, ramp, float(np.mean(Ns)), float(np.mean(qrs)), float(np.mean(sws))


# ============================ market regimes (realized, read from the capture) =========================
def over_floor_markets():
    mk = read_markets(OUT, sleep_gap_s=SLEEP_GAP_S)
    over = sorted((m for m in mk if m.n_events >= FLOOR), key=lambda m: m.n_events)
    regimes = []
    for m in over:
        regimes.append(dict(tag=m.asset_id[-10:], N=m.n_events, T=m.horizon,
                            swing=rate_swing(m.times, m.horizon),
                            qr=quarter_ratio(m.times, m.horizon), times=m.times))
    return regimes


# ============================ verify / smoke / phases ==================================================
def verify():
    """Golden: the cached profile_ll must equal the tested mu_t_hawkes.fit_mu_only on the SAME inputs."""
    from mu_t_hawkes import fit_mu_only
    t = simulate_ramp(0.02, 9.0, 0.85, 30000.0, 0.35, 1.7, np.random.default_rng(0))
    T = float(t[-1])
    log(f"verify: N={t.size}, comparing cached profile_ll vs fit_mu_only")
    worst = 0.0
    for eps, c, n in [(0.4, 2.0, 0.75), (0.2, 1.0, 0.90), (0.7, 0.5, 0.45), (0.1, 2.0, 1.05)]:
        a, betas = PowerLawKernel(eps=eps, c=c).soe()
        s = self_excitation(t, a, betas); cc = comp_coef(t, T, a, betas)
        fast = profile_ll(t, T, s, cc, n, K_FLEX)
        ref = fit_mu_only(t, T, PowerLawKernel(eps=eps, c=c), n, K_FLEX)["ll"]
        d = abs(fast - ref); worst = max(worst, d)
        log(f"  eps={eps} c={c} n={n}: cached={fast:.4f} ref={ref:.4f} |Δ|={d:.2e}")
    assert worst < 1e-3, f"cached profile_ll diverges from fit_mu_only by {worst} -> DO NOT trust results"
    log(f"verify PASS (worst |Δ|={worst:.2e})")


def smoke():
    reg = over_floor_markets()[0]
    log(f"smoke: regime {reg['tag']} N={reg['N']} T={reg['T']/3600:.1f}h swing={reg['swing']:.1f}x "
        f"qr={reg['qr']:.1f}")
    mu0, ramp, Nr, qrr, swr = calibrate(reg["N"], reg["qr"], N_PLANT, reg["T"], EPS_PLANT, C_PLANT)
    log(f"smoke: calibrated mu0={mu0:.4f} ramp={ramp:.1f} -> realized N={Nr:.0f} qr={qrr:.1f} swing={swr:.1f}x "
        f"(targets N={reg['N']} qr={reg['qr']:.1f} swing={reg['swing']:.1f}x)")
    t0 = time.time()
    t = simulate_ramp(mu0, ramp, N_PLANT, reg["T"], EPS_PLANT, C_PLANT, np.random.default_rng(700))
    g = run_gate(t, reg["T"])
    log(f"smoke: one gate on synth N={t.size} swing={rate_swing(t, reg['T']):.1f}x "
        f"traj={[round(x,2) for x in g['traj']]} identified={g['identified']} ({time.time()-t0:.0f}s)")


def phase_a(regimes):
    """FREEZE: false-migration rate of genuine near-critical (n=0.90) at each market's realized regime."""
    lines = [f"# PHASE A (FROZEN) — false-migration rate of genuine near-critical under the gate "
             f"— {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"plant n={N_PLANT} (near-critical), off-grid shape eps={EPS_PLANT}/c={C_PLANT}; ramp=swing-1 "
             f"(#6); mu0 tuned to realized N; {SEEDS} seeds; gate frozen: identified iff "
             f"|peak(eps0.02)-peak(eps0.4)|<{MIGRATE_TOL} AND peak<1.", "",
             "p_migrate = fraction of GENUINE near-critical seeds the gate WRONGLY flags (migrated).", ""]
    summary = {}
    for reg in regimes:
        mu0, ramp, Nr, qrr, swr = calibrate(reg["N"], reg["qr"], N_PLANT, reg["T"], EPS_PLANT, C_PLANT)
        log(f"[A {reg['tag']}] target N={reg['N']} qr={reg['qr']:.1f} swing={reg['swing']:.1f}x -> "
            f"calibrated realized N={Nr:.0f} qr={qrr:.1f} swing={swr:.1f}x (mu0={mu0:.4f} ramp={ramp:.1f})")
        lines += [f"## regime {reg['tag']}  (market N={reg['N']}, swing={reg['swing']:.1f}x, qr={reg['qr']:.1f}; "
                  f"calibrated synth realized N≈{Nr:.0f}, swing≈{swr:.1f}x, qr≈{qrr:.1f}; plant n={N_PLANT})",
                  f"{'seed':>4} {'synthN':>7} {'synSwing':>8} {'peak@0.4':>9} {'peak@0.02':>10} "
                  f"{'peak<1@.02':>10} {'verdict':>10}"]
        migr = 0
        for sd in range(SEEDS):
            t = simulate_ramp(mu0, ramp, N_PLANT, reg["T"], EPS_PLANT, C_PLANT, np.random.default_rng(700 + sd))
            g = run_gate(t, reg["T"])
            migr += (not g["identified"])
            lines.append(f"{sd:>4} {t.size:>7} {rate_swing(t, reg['T']):>7.1f}x {g['peak04']:>9.2f} "
                         f"{g['peak002']:>10.2f} {g['traj_sub'][-1]:>10.2f} "
                         f"{'OK' if g['identified'] else 'MIGRATED':>10}")
            log(f"   seed {sd}: N={t.size} traj={[round(x,2) for x in g['traj']]} "
                f"sub={[round(x,2) for x in g['traj_sub']]} {'OK' if g['identified'] else 'MIGRATED'}")
        p = migr / SEEDS
        summary[reg["tag"]] = p
        lines += [f"- **p_migrate(genuine near-critical @ N={reg['N']}, swing={reg['swing']:.1f}x) "
                  f"= {migr}/{SEEDS} = {p:.2f}**", ""]
    lines += ["## FROZEN baseline (read BEFORE Phase B)",
              "A single real market's migration is interpretable only against p_migrate here:",
              "  p_migrate LOW  (<= ~1/8) -> a real market that migrates is genuinely degenerate/mis-modelled.",
              "  p_migrate HIGH (~half)   -> a single real migration is uninformative -> near-criticality",
              "                              NOT RESOLVABLE at that N (resolution-floor reading).", ""]
    for tag, p in summary.items():
        lines.append(f"  {tag}: p_migrate={p:.2f}")
    outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_phaseA_false_migration.md"
    outp.write_text("\n".join(lines))
    log(f"PHASE A frozen baseline -> {outp}")
    print("\n".join(lines))
    return summary


def phase_b(regimes, baseline):
    """VERDICT: the SAME frozen gate on the real markets, read against the Phase-A baseline."""
    lines = [f"# PHASE B (VERDICT) — real over-floor markets through the frozen gate "
             f"— {time.strftime('%Y-%m-%d %H:%M:%S')}",
             "Read each real market's migration against its regime's Phase-A p_migrate (the frozen baseline).", "",
             f"{'market':>11} {'N':>7} {'swing':>6} {'peak@0.4':>9} {'peak@0.02':>10} {'peak<1@.02':>10} "
             f"{'verdict':>10} {'p_mig(genuine)':>15}"]
    for reg in regimes:
        g = run_gate(reg["times"], reg["T"])
        p = baseline.get(reg["tag"], float("nan"))
        log(f"[B {reg['tag']}] traj={[round(x,2) for x in g['traj']]} sub={[round(x,2) for x in g['traj_sub']]} "
            f"{'OK' if g['identified'] else 'MIGRATED'}  (genuine p_migrate={p:.2f})")
        lines.append(f"{reg['tag']:>11} {reg['N']:>7} {reg['swing']:>5.1f}x {g['peak04']:>9.2f} "
                     f"{g['peak002']:>10.2f} {g['traj_sub'][-1]:>10.2f} "
                     f"{'OK' if g['identified'] else 'MIGRATED':>10} {p:>14.2f}")
    lines += ["",
              "Interpretation rule (frozen): a real MIGRATED verdict is meaningful only where the genuine",
              "p_migrate is low; where genuine p_migrate ~ 0.5 the real migration is single-realization noise",
              "and the honest verdict is 'near-criticality not resolvable at this N'. peak<1@.02 separates a",
              "finite-window artifact (interior subcritical max under the n<1 cap) from a genuine supercritical",
              "mode (cap binds at the n-grid top)."]
    outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_phaseB_real_verdict.md"
    outp.write_text("\n".join(lines))
    log(f"PHASE B verdict -> {outp}")
    print("\n".join(lines))


# ============================ TIGHTENED re-run (round-2 response) ======================================
# Closes the two existing-tooling axes round 2 flagged: (power) seeds sized to the false-positive bound we
# need; (regime) N matched DOWN to the real value (removing the favorable +N bias) + swing targeted +
# realized N/swing/qr VERIFIED and reported; plant n=0.75 (markets' own fit) AND 0.90 (conservative). What
# it CANNOT close: the bursty-baseline axis (the gate's smooth mu(K=12) cannot represent a bursty baseline),
# so a clean result earns the split ONLY against SMOOTH confounds — the output says exactly that.
from scipy.stats import beta as _beta

SEEDS_TIGHT = 40                 # 0/40 -> 7.2% one-sided 95% upper bound; 1/40 -> 10.9% (robust to a fluke)
PLANT_LEVELS = [0.75, 0.90]      # 0.75 = markets' own constrained fit (primary); 0.90 = conservative


def binom_upper95(k, n):
    """One-sided 95% Clopper-Pearson upper bound on a rate from k migrations in n seeds. k=0 -> 1-0.05^(1/n)."""
    return 1.0 if k == n else float(_beta.ppf(0.95, k + 1, n - k))


def calibrate_tight(N_target, swing_target, n, T, eps, c, cal_seeds=5, iters=10):
    """Target (realized N, realized max/min swing) with two knobs (mu0->N, ramp->swing); N matched DOWN to
    the real value (removes round 2's favorable +N bias), swing targeted, both verified + reported. A linear
    ramp CANNOT also match the quarter-ratio if the market is bursty -> qr is reported and its residual IS
    the bursty signature (caveat 2). Averages over cal_seeds to tame the noisy max/min target."""
    ramp = max(swing_target - 1.0, 0.2)
    mu0 = mu0_for_N(N_target, ramp, n, T)
    for _ in range(iters):
        Ns, sws = [], []
        for sd in range(cal_seeds):
            t = simulate_ramp(mu0, ramp, n, T, eps, c, np.random.default_rng(9000 + sd))
            Ns.append(t.size); sws.append(rate_swing(t, T))
        N_real, sw_real = float(np.mean(Ns)), float(np.mean(sws))
        ramp = float(np.clip(ramp * ((swing_target - 1.0) / max(sw_real - 1.0, 0.2)) ** 0.5, 0.05, 800.0))
        mu0 *= N_target / max(N_real, 1.0)
    Ns, sws, qrs = [], [], []
    for sd in range(cal_seeds):
        t = simulate_ramp(mu0, ramp, n, T, eps, c, np.random.default_rng(9000 + sd))
        Ns.append(t.size); sws.append(rate_swing(t, T)); qrs.append(quarter_ratio(t, T))
    return mu0, ramp, float(np.mean(Ns)), float(np.mean(sws)), float(np.mean(qrs))


def phase_a_tight(regimes):
    lines = [f"# TIGHTENED Phase A — confidence-bounded false-migration of genuine near-critical "
             f"— {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"Round-2 response: N matched DOWN to real (favorable +N bias removed) + swing targeted + "
             f"realized N/swing/qr VERIFIED; {SEEDS_TIGHT} seeds (0/{SEEDS_TIGHT} -> "
             f"{binom_upper95(0, SEEDS_TIGHT)*100:.1f}% 95% upper bound); plant n in {PLANT_LEVELS} "
             f"(0.75 = markets' own fit, 0.90 = conservative).",
             "",
             "**CONDITIONALITY (load-bearing):** this earns/breaks the split ONLY against SMOOTH confounds. "
             "The bursty-baseline axis is NOT reached here (smooth mu(K=12) cannot represent it) and caveat 2 "
             "is direct evidence the markets ARE bursty (qr-high/swing-low) — so a clean result here is "
             "'earned against smooth confounds, bursty axis still the determining open test', NOT settled.", ""]
    for n_plant in PLANT_LEVELS:
        lines.append(f"## plant n={n_plant}")
        for reg in regimes:
            mu0, ramp, Nc, swc, qrc = calibrate_tight(reg["N"], reg["swing"], n_plant, reg["T"],
                                                       EPS_PLANT, C_PLANT)
            nmatch = "OK" if abs(Nc - reg["N"]) / reg["N"] < 0.06 else "**N-MISMATCH**"
            log(f"[tight n={n_plant} {reg['tag']}] target N={reg['N']} swing={reg['swing']:.1f}x -> "
                f"calibrated realized N={Nc:.0f} swing={swc:.1f}x qr={qrc:.1f} [{nmatch}] (mu0={mu0:.4f} ramp={ramp:.1f})")
            migr = 0; Ns = []; sws = []
            for sd in range(SEEDS_TIGHT):
                t = simulate_ramp(mu0, ramp, n_plant, reg["T"], EPS_PLANT, C_PLANT, np.random.default_rng(700 + sd))
                g = run_gate(t, reg["T"])
                migr += (not g["identified"]); Ns.append(t.size); sws.append(rate_swing(t, reg["T"]))
                if (sd + 1) % 10 == 0:
                    log(f"   n={n_plant} {reg['tag']}: {sd+1}/{SEEDS_TIGHT} done, migrated so far={migr}")
            ub = binom_upper95(migr, SEEDS_TIGHT)
            lines += [f"### regime {reg['tag']}  (market N={reg['N']}, swing={reg['swing']:.1f}x)",
                      f"- calibration verify: realized N≈{np.mean(Ns):.0f} (target {reg['N']}, {nmatch}), "
                      f"realized swing≈{np.mean(sws):.1f}x (target {reg['swing']:.1f}x), cal qr≈{qrc:.1f} "
                      f"(market qr={reg['qr']:.1f} — residual = bursty signature)",
                      f"- **p_migrate = {migr}/{SEEDS_TIGHT} = {migr/SEEDS_TIGHT:.3f}; 95% upper bound = "
                      f"{ub*100:.1f}%**", ""]
    lines += ["## Read (against the round-1 danger zone ~50% and an 'earned' threshold of <10%)",
              "A 95% upper bound well under 10% at plant n=0.75 (markets' own fit), with N matched down,",
              "earns 'genuine near-critical rarely migrates at the markets' regime' — AGAINST SMOOTH",
              "CONFOUNDS ONLY. The real markets (Phase B below) migrating decisively then licenses 'not-clean",
              "under the smooth model'. The bursty axis remains the determining open test of the central claim."]
    outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_phaseA_tight.md"
    outp.write_text("\n".join(lines))
    log(f"TIGHTENED Phase A -> {outp}")
    print("\n".join(lines))


# ============================ MAGNITUDE probe (round-2 option B, measured) =============================
# Does the MAGNITUDE of migration discriminate where the binary did not? Genuine-false-migrations may
# cluster low (1.05-1.20) while the real markets pin a high ceiling. PRE-REGISTERED, result-blind (finding
# 8): the rule below is fixed in code BEFORE any real-market peak is computed. Anti-circularity (check 2):
# plant the conservative n=0.90 anchor, NOT the suspect markets' own 0.75 fit. Grid extended past 1.20
# (check 3) so neither genuine nor real piles at a wall. Seeds bumped to firm the specificity CI (check 1).
SEEDS_MAG = 80
N_GRID_EXT = [0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20, 1.40, 1.60, 1.80, 2.00]  # extended past 1.20
MAG_PLANT = 0.90                  # robust anti-circular anchor (not the suspect 0.75)
RESTORED_PCT = 90                 # real peak > this pctile of genuine-false peaks => discrimination RESTORED
# RULE (frozen here, before results): pool genuine(n=0.90)-false-migration peaks across regimes -> G.
#   restored  : real migration peak > 90th pctile of G
#   graded    : median(G) < real peak <= 90th pctile of G
#   absent    : real peak <= median(G)
# n* (the discriminating cut) = 90th pctile of G, reported. Ceiling check: if most of G sits at 2.00 the
# grid is still a wall -> extend further before reading (flagged, not silently passed).


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z / d) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, c - h), min(1.0, c + h))


def pct_rank(value, arr):
    arr = np.asarray(arr, float)
    return float((np.sum(arr < value) + 0.5 * np.sum(arr == value)) / arr.size * 100) if arr.size else float("nan")


def migration_peak_ext(times, horizon, K=K_FLEX):
    """Gate on the EXTENDED n-grid (to 2.0). Returns (identified, peak@eps0.02, peak@eps0.4)."""
    ll = ll_grid(times, horizon, K, n_grid=N_GRID_EXT)
    peak04 = peak_at(ll, 0.4, None, n_grid=N_GRID_EXT)
    peak002 = peak_at(ll, 0.02, None, n_grid=N_GRID_EXT)
    identified = bool(abs(peak002 - peak04) < MIGRATE_TOL and peak002 < 1.0)
    return identified, peak002, peak04


def phase_magnitude(regimes):
    rule = [f"# MAGNITUDE probe — does migration EXTENT discriminate? — {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "**PRE-REGISTERED RULE (frozen before any real-market peak; result-blind, finding 8):**",
            f"- plant genuine n={MAG_PLANT} (conservative anti-circular anchor, NOT the suspect 0.75 fit), "
            f"N matched down, {SEEDS_MAG} seeds; n-grid extended to {N_GRID_EXT[-1]} (no 1.20 wall).",
            f"- pool genuine-FALSE-migration peaks across regimes -> G; n* = {RESTORED_PCT}th pctile of G.",
            "- per real market: RESTORED if real peak > n*; GRADED if median(G) < peak <= n*; ABSENT if <= median.",
            "- N=1 real obs/market -> at most 'real peak sits in the tail of G', a graded per-market statement.",
            "- CEILING CHECK: if most of G sits at 2.00 the grid still walls -> extend further (flagged).", ""]
    log("MAGNITUDE probe: genuine n=0.90, extended grid, " + str(SEEDS_MAG) + " seeds (calibration first)")
    G = []                                          # pooled genuine-false-migration peaks
    spec_lines = ["## Specificity (firmed CI) + genuine-false peaks, plant n=0.90", ""]
    for reg in regimes:
        mu0, ramp, Nc, swc, qrc = calibrate_tight(reg["N"], reg["swing"], MAG_PLANT, reg["T"], EPS_PLANT, C_PLANT)
        nmatch = "OK" if abs(Nc - reg["N"]) / reg["N"] < 0.06 else "**N-MISMATCH**"
        log(f"[mag {reg['tag']}] calibrated realized N={Nc:.0f} swing={swc:.1f}x [{nmatch}]")
        migr = 0; reg_false = []
        for sd in range(SEEDS_MAG):
            t = simulate_ramp(mu0, ramp, MAG_PLANT, reg["T"], EPS_PLANT, C_PLANT, np.random.default_rng(700 + sd))
            ident, pk, _ = migration_peak_ext(t, reg["T"])
            if not ident:
                migr += 1; reg_false.append(pk); G.append(pk)
            if (sd + 1) % 20 == 0:
                log(f"   {reg['tag']}: {sd+1}/{SEEDS_MAG} done, migrated={migr}")
        lo, hi = wilson_ci(migr, SEEDS_MAG)
        spec_lines += [f"### {reg['tag']} (market N={reg['N']}, swing={reg['swing']:.1f}x; cal {nmatch})",
                       f"- false-migration {migr}/{SEEDS_MAG} = {migr/SEEDS_MAG:.3f}; Wilson95 CI "
                       f"[{lo:.3f}, {hi:.3f}]; specificity [{1-hi:.3f}, {1-lo:.3f}]",
                       f"- genuine-false peaks: {sorted(round(p,2) for p in reg_false)}", ""]
    # genuine-false peak distribution G (calibration object) — computed BEFORE real peaks
    G = np.array(G, float)
    ceil_frac = float(np.mean(G >= 2.0)) if G.size else float("nan")
    nstar = float(np.percentile(G, RESTORED_PCT)) if G.size else float("nan")
    gmed = float(np.median(G)) if G.size else float("nan")
    dist_lines = ["## Genuine-false-migration peak distribution G (pooled, n=0.90)",
                  f"- N migrating seeds pooled = {G.size}; median={gmed:.2f}; "
                  f"n*({RESTORED_PCT}th pctile)={nstar:.2f}; fraction at ceiling 2.00 = {ceil_frac:.2f}",
                  f"- CEILING CHECK: {'WALL — most genuine-false at 2.00, extend grid further before trusting' if ceil_frac > 0.5 else 'OK — genuine-false NOT piled at ceiling'}",
                  f"- peaks: {sorted(round(p,2) for p in G.tolist())}", ""]
    # NOW the real markets (extended grid), rule applied
    real_lines = ["## Real markets on the extended grid — pre-registered rule applied", "",
                  f"{'market':>11} {'real peak@.02':>13} {'pctile in G':>12} {'verdict':>10}"]
    for reg in regimes:
        _, pk_real, _ = migration_peak_ext(reg["times"], reg["T"])
        pr = pct_rank(pk_real, G)
        verdict = ("RESTORED" if pk_real > nstar else "graded" if pk_real > gmed else "absent")
        log(f"[mag REAL {reg['tag']}] peak={pk_real:.2f} pctile={pr:.0f}% -> {verdict}")
        real_lines.append(f"{reg['tag']:>11} {pk_real:>13.2f} {pr:>11.0f}% {verdict:>10}")
    real_lines += ["",
                   "Read: 'RESTORED' = the real market's migration is more extreme than 90% of genuine-false",
                   "migrations, so magnitude separates it where the binary did not (graded, N=1 real obs).",
                   "If real peaks AND G both pile at the 2.00 ceiling, magnitude cannot separate — extend further."]
    out = "\n".join(rule + spec_lines + dist_lines + real_lines)
    outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_magnitude_probe.md"
    outp.write_text(out)
    log(f"MAGNITUDE probe -> {outp}")
    print(out)


# ============================ FINER-GRID / continuous-peak check (round-3 prerequisite) ================
# Round-2 symmetry: "discrimination restored" rests on a 0.15 n-grid where 1.0-1.3 holds only {1.05, 1.20}.
# "All 23 genuine at EXACTLY 1.05" is the tell of grid-spacing > underlying spread (a continuous quantity
# with seed noise would show 1.02/1.06/1.09). Resolve the n-axis through 1.0-1.3 to distinguish: genuine
# TIGHT sub-1.10 (separation real, maybe stronger) vs genuine SPREADS toward 1.15-1.20 (separation is a
# quantization artifact -> resolution-floor). Also: is the real peak a STEEP max at ~1.20 or a FLAT ridge
# 1.05-1.20 (collapses from the real side)? And is the migration endpoint stable to the eps-grid step?
# Per-market N-matched. Rule frozen BELOW, before results (finding 8).
N_GRID_FINE = [0.60, 0.75, 0.90, 0.95, 1.00, 1.025, 1.05, 1.075, 1.10, 1.125, 1.15, 1.175, 1.20,
               1.25, 1.30, 1.45, 1.70, 2.00]
EPS_FINE = [0.02, 0.035, 0.05, 0.07, 0.1, 0.15, 0.2, 0.4, 0.7, 1.1]   # finer near the action (eps-stability)
SEEDS_FINE = 40
SEP_GENUINE_CAP = 1.125    # separation needs genuine fine migration-peaks' 95th pctile <= this
SEP_REAL_SHARP = 10.0      # separation needs real ll(argmax)-ll(1.05) >= this (non-flat) AND argmax >= 1.175


def profile_curve(times, horizon, n_grid, eps_full, c_grid=C_GRID, K=K_FLEX, eps_min=0.02):
    """The continuous-ish profile: (n, max-over-shape ll) at eps>=eps_min, over a (fine) n-grid."""
    ll = ll_grid(times, horizon, K, n_grid=n_grid, eps_full=eps_full, c_grid=c_grid)
    epss = [e for e in eps_full if e >= eps_min]
    return [(n, max(ll[(n, e, c)] for e in epss for c in c_grid)) for n in n_grid]


def _argmax_n(curve):
    return max(curve, key=lambda x: x[1])[0]


def phase_finegrid(regimes):
    lines = [f"# FINER-GRID / continuous-peak check — is the 1.05-vs-1.20 separation real or quantization? "
             f"— {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
             "**PRE-REGISTERED RULE (frozen before results, finding 8):** separation HOLDS iff "
             f"(a) genuine fine migration-peaks' 95th pctile <= {SEP_GENUINE_CAP} (genuine stays clearly "
             f"below the real 1.20) AND (b) each migrating real market has profile argmax >= 1.175 and "
             f"ll(argmax)-ll(1.05) >= {SEP_REAL_SHARP} (a steep max, not a flat 1.05-1.20 ridge). "
             "Else COLLAPSES -> resolution-floor + the binary population claim.",
             f"n-grid fine through 1.0-1.3 (step 0.025); plant genuine n=0.90, {SEEDS_FINE} seeds, "
             "per-market N-matched; eps-stability checked on the real markets.", ""]
    # ---- genuine fine-grid migration spread (per regime, N-matched) ----
    Gfine = []
    lines.append("## Genuine (n=0.90) fine-grid migration peaks — TIGHT cluster or SPREAD?")
    for reg in regimes:
        mu0, ramp, Nc, swc, qrc = calibrate_tight(reg["N"], reg["swing"], MAG_PLANT, reg["T"], EPS_PLANT, C_PLANT)
        log(f"[fine {reg['tag']}] cal N={Nc:.0f} swing={swc:.1f}x; {SEEDS_FINE} seeds on fine grid")
        peaks = []
        for sd in range(SEEDS_FINE):
            t = simulate_ramp(mu0, ramp, MAG_PLANT, reg["T"], EPS_PLANT, C_PLANT, np.random.default_rng(700 + sd))
            pk = _argmax_n(profile_curve(t, reg["T"], N_GRID_FINE, EPS_FULL))
            if pk > 1.0:
                peaks.append(pk); Gfine.append(pk)
            if (sd + 1) % 20 == 0:
                log(f"   {reg['tag']}: {sd+1}/{SEEDS_FINE} done, migrated={len(peaks)}")
        lines.append(f"- {reg['tag']} (N={reg['N']}): {len(peaks)} migrated, fine peaks "
                     f"{sorted(round(p,3) for p in peaks)}")
    Gfine = np.array(Gfine, float)
    g95 = float(np.percentile(Gfine, 95)) if Gfine.size else float("nan")
    gmax = float(Gfine.max()) if Gfine.size else float("nan")
    spread = "TIGHT (sub-1.10)" if Gfine.size and gmax <= 1.10 else ("SPREADS toward real" if Gfine.size else "n/a")
    lines += [f"- pooled genuine fine peaks N={Gfine.size}; median={np.median(Gfine) if Gfine.size else float('nan'):.3f}; "
              f"95th pctile={g95:.3f}; max={gmax:.3f} -> {spread}", ""]
    # ---- real markets: continuous profile curve + sharpness + eps-stability ----
    lines.append("## Real markets — continuous profile (steep max at 1.20 or flat ridge?) + eps-stability")
    real_ok = {}
    for reg in regimes:
        curve = profile_curve(reg["times"], reg["T"], N_GRID_FINE, EPS_FULL)
        d = dict(curve)
        argmax = _argmax_n(curve)
        ll_max = max(v for _, v in curve)
        sharp = d[argmax] - d[1.05]
        argmax_finee = _argmax_n(profile_curve(reg["times"], reg["T"], N_GRID_FINE, EPS_FINE))
        rel = [(n, round(d[n] - ll_max, 1)) for n in N_GRID_FINE if 0.90 <= n <= 1.45]
        migrating = argmax > 1.0
        sharp_ok = argmax >= 1.175 and sharp >= SEP_REAL_SHARP
        real_ok[reg["tag"]] = (not migrating) or sharp_ok
        log(f"[fine REAL {reg['tag']}] argmax={argmax:.3f} (eps-fine {argmax_finee:.3f}) "
            f"ll(argmax)-ll(1.05)={sharp:.1f}")
        lines += [f"### {reg['tag']}  argmax_n={argmax:.3f} (eps-fine grid: {argmax_finee:.3f} "
                  f"-> endpoint {'STABLE' if abs(argmax-argmax_finee) < 0.05 else 'MOVES'})",
                  f"- ll(argmax)-ll(1.05) = {sharp:.1f} units -> "
                  f"{'STEEP (1.20 clearly favored)' if sharp >= SEP_REAL_SHARP else 'FLAT ridge (1.05~1.20 barely separated)'}",
                  f"- profile Δll vs max (n: Δll): {rel}", ""]
    # ---- pre-registered verdict ----
    genuine_ok = bool(Gfine.size and g95 <= SEP_GENUINE_CAP)
    migrating_reals = [t for t, ok in real_ok.items() if not ok]   # markets that migrate but aren't sharp
    holds = genuine_ok and all(real_ok.values())
    lines += ["## PRE-REGISTERED VERDICT",
              f"- genuine 95th pctile {g95:.3f} <= {SEP_GENUINE_CAP}? **{genuine_ok}**",
              f"- every migrating real market a steep max (argmax>=1.175, sharp>={SEP_REAL_SHARP})? "
              f"**{all(real_ok.values())}**" + (f" (failing: {migrating_reals})" if migrating_reals else ""),
              f"- => SEPARATION **{'HOLDS — magnitude discrimination is real, not quantization' if holds else 'COLLAPSES — back to resolution-floor + the binary population claim'}**",
              "",
              "Bankable regardless (grid-independent): the BINARY population claim — P(this migrate/not "
              "pattern | all 3 smooth-genuine) ~ 2% (depends on WHICH migrate, not how far). Non-stationarity "
              "inflation untouched. Even if separation holds, the per-market verdict is 'not SMOOTH-genuine', "
              "NOT 'degenerate' — bursty-genuine gives the same signature; that is the bursty chapter."]
    outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_finegrid_check.md"
    outp.write_text("\n".join(lines))
    log(f"FINER-GRID check -> {outp}")
    print("\n".join(lines))


# ============================ N-PROBE: is the resolution floor N-dependent or intrinsic? ===============
# The fine grid relocated the markets to 1.125 (mild, inside the genuine range) -> they may be genuine
# near-critical the instrument cannot resolve at 18-35k. Does MORE N break the floor? Plant genuine n=0.90
# at higher N; does false-migration drop below 10%? The capture is accruing toward 60-100k, so this says
# whether volume resolves the per-market question for free. Threshold frozen BELOW, result-blind (finding 8).
N_TARGETS_PROBE = [35000, 60000, 100000]    # 35k = anchor (should reproduce the measured ~10-20%)
T_PROBE, SWING_PROBE = 12 * 3600.0, 10.0    # representative regime (markets span 9-20h, 7.7-11.7x); N via density
SEEDS_NPROBE = 30                           # 0/30 -> 9.5% upper bound (clears the 10% threshold); 100k gates ~112s each
FLOOR_BREAK_THRESH = 0.10                    # floor N-DEPENDENT iff false-migration < this at N=100k


def phase_nprobe(_regimes=None):
    lines = [f"# N-PROBE — is the per-market resolution floor N-dependent or intrinsic? "
             f"— {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
             f"**PRE-REGISTERED (frozen): floor is N-DEPENDENT/volume-fixable iff genuine false-migration "
             f"< {FLOOR_BREAK_THRESH:.0%} at N=100k; INTRINSIC iff >= {FLOOR_BREAK_THRESH:.0%} at 100k.** "
             f"plant genuine n=0.90, off-grid shape eps={EPS_PLANT}/c={C_PLANT}, T={T_PROBE/3600:.0f}h, "
             f"swing~{SWING_PROBE:.0f}x (fixed regime; N raised by density), {SEEDS_NPROBE} seeds, "
             "operational gate (run_gate).", "",
             f"{'N_target':>9} {'realizedN':>10} {'realSwing':>10} {'false-mig':>12} {'Wilson95':>18}"]
    results = []
    for Nt in N_TARGETS_PROBE:
        mu0, ramp, Nc, swc, qrc = calibrate_tight(Nt, SWING_PROBE, MAG_PLANT, T_PROBE, EPS_PLANT, C_PLANT)
        log(f"[nprobe N={Nt}] cal realized N={Nc:.0f} swing={swc:.1f}x (mu0={mu0:.5f} ramp={ramp:.1f})")
        migr = 0; Ns = []
        for sd in range(SEEDS_NPROBE):
            t = simulate_ramp(mu0, ramp, MAG_PLANT, T_PROBE, EPS_PLANT, C_PLANT, np.random.default_rng(700 + sd))
            g = run_gate(t, T_PROBE)
            migr += (not g["identified"]); Ns.append(t.size)
            if (sd + 1) % 10 == 0:
                log(f"   N={Nt}: {sd+1}/{SEEDS_NPROBE} done, migrated={migr}")
        lo, hi = wilson_ci(migr, SEEDS_NPROBE)
        results.append((Nt, float(np.mean(Ns)), migr / SEEDS_NPROBE, lo, hi))
        lines.append(f"{Nt:>9} {np.mean(Ns):>10.0f} {swc:>9.1f}x {migr}/{SEEDS_NPROBE}={migr/SEEDS_NPROBE:>5.2f} "
                     f"  [{lo:.3f}, {hi:.3f}]")
    fm100 = next(r[2] for r in results if r[0] == 100000)
    verdict = ("N-DEPENDENT — volume fixes the floor; high-N markets become certifiable"
               if fm100 < FLOOR_BREAK_THRESH else
               "INTRINSIC — floor persists at 100k; the smooth-μ instrument cannot resolve per-market here")
    lines += ["", f"## VERDICT: false-migration at 100k = {fm100:.2f} -> **{verdict}**",
              "N-dependent -> path forward is VOLUME (let the capture accrue), not a new model.",
              "Intrinsic -> the bursty chapter becomes the determinant (own matched-recovery calibration; "
              "the tightened+magnitude+finegrid result is the baseline it must beat).",
              "", "Caveat: N raised by DENSITY at fixed T (cleanest N-axis isolation); the 'longer-T, fixed "
              "density' interpretation (how the capture actually accrues) is a follow-up if the boundary is near."]
    outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_nprobe.md"
    outp.write_text("\n".join(lines))
    log(f"N-PROBE -> {outp}")
    print("\n".join(lines))


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify()
    elif "--smoke" in sys.argv:
        verify(); smoke()
    elif "--magnitude" in sys.argv:
        verify()
        phase_magnitude(over_floor_markets())
    elif "--finegrid" in sys.argv:
        verify()
        phase_finegrid(over_floor_markets())
    elif "--nprobe" in sys.argv:
        verify()
        phase_nprobe()
    elif "--tight" in sys.argv:
        verify()                                   # never run a result on an unverified estimator
        regimes = over_floor_markets()
        log(f"TIGHTENED re-run: {len(regimes)} regimes x {len(PLANT_LEVELS)} plant levels x {SEEDS_TIGHT} seeds")
        phase_a_tight(regimes)
        phase_b(regimes, {r["tag"]: float("nan") for r in regimes})   # real markets, unchanged gate
    else:
        verify()                                   # never run a result on an unverified estimator
        regimes = over_floor_markets()
        log(f"{len(regimes)} over-floor regimes: "
            + ", ".join(f"{r['tag']}(N={r['N']},swing={r['swing']:.1f}x)" for r in regimes))
        baseline = phase_a(regimes)                # FREEZE first (written out)...
        phase_b(regimes, baseline)                 # ...then the real verdict against it

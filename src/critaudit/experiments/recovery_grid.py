from __future__ import annotations
import multiprocessing as mp
import numpy as np
from critaudit.generators.hawkes_sim import simulate
from critaudit.hawkes.mle import fit, _fit_full   # point MLE without CI

GRID_N = (0.3, 0.6, 0.9, 0.99)
GRID_EVENTS = (1000, 10000)          # acceptance grid; 1e5 only at low n (sanity)


def _one(args):
    n, n_events, mu, beta, seed = args
    rng = np.random.default_rng(seed)
    horizon = n_events / (mu / (1.0 - n))      # target ~ n_events
    es = simulate(n, horizon, mu=mu, beta=beta, backend="auto", rng=rng)
    if es.times.size < 10:
        return None
    f = fit(es)
    lo, hi = f.ci
    return (f.n, lo, hi, es.times.size)


def coverage_cell(n, n_events, R, base_seed, mu=0.6, beta=1.0):
    seeds = np.random.SeedSequence(base_seed).spawn(R)
    args = [(n, n_events, mu, beta, s) for s in seeds]
    with mp.Pool() as pool:
        res = [r for r in pool.map(_one, args) if r is not None]
    covers = [lo <= n <= hi for (_, lo, hi, _) in res]
    return {"n": n, "n_events": n_events, "R": len(res),
            "coverage": float(np.mean(covers)) if covers else float("nan"),
            "median_nhat": float(np.median([r[0] for r in res])) if res else float("nan")}


def main(R=100, base_seed=20260615):
    print("=== recovery coverage grid (gate: coverage>=0.90 for n in {.3,.6,.9}, N>=1e4) ===")
    for n in GRID_N:
        for ne in GRID_EVENTS:
            print(coverage_cell(n, ne, R, base_seed))
        if n in (0.3, 0.6):              # monotonicity sanity only at low n
            print(coverage_cell(n, 100000, R, base_seed))


def bootstrap_ci(events, fit_result, B, rng, level=0.95):
    """Parametric bootstrap CI on n: simulate B datasets from the fitted (n,mu,beta)
    on the same horizon, refit each (point estimate), take the percentile interval.
    This is the truth-free CI carried to Stage-1 real data."""
    n0, mu0, beta0, horizon = fit_result.n, fit_result.mu, fit_result.beta, events.horizon
    nhats = []
    for _ in range(B):
        sim = simulate(n0, horizon, mu=mu0, beta=beta0, backend="auto", rng=rng)
        if sim.times.size >= 10:
            nhats.append(float(_fit_full(np.asarray(sim.times), horizon).x[1]))
    a = (1 - level) / 2 * 100
    lo, hi = np.percentile(nhats, [a, 100 - a])
    return (float(lo), float(hi))


def profile_bootstrap_audit(n_events, R, base_seed, n=0.99, B=100, mu=0.6, beta=1.0):
    """Method-transfer audit at the boundary: for R datasets at n, compare the
    profile CI (from fit) to the parametric bootstrap CI on the same dataset."""
    seeds = np.random.SeedSequence(base_seed).spawn(R)
    lo_diff, hi_diff, overlap = [], [], []
    for s in seeds:
        rng = np.random.default_rng(s)
        horizon = n_events / (mu / (1.0 - n))
        es = simulate(n, horizon, mu=mu, beta=beta, backend="auto", rng=rng)
        if es.times.size < 10:
            continue
        f = fit(es)                               # profile CI in f.ci
        bci = bootstrap_ci(es, f, B, rng)
        lo_diff.append(abs(f.ci[0] - bci[0]))
        hi_diff.append(abs(f.ci[1] - bci[1]))
        overlap.append(max(0.0, min(f.ci[1], bci[1]) - max(f.ci[0], bci[0])))
    return {"n": n, "R": len(overlap),
            "mean_lo_diff": float(np.mean(lo_diff)) if lo_diff else float("nan"),
            "mean_hi_diff": float(np.mean(hi_diff)) if hi_diff else float("nan"),
            "mean_overlap": float(np.mean(overlap)) if overlap else float("nan")}


if __name__ == "__main__":
    main()

from __future__ import annotations
import multiprocessing as mp
import numpy as np
from critaudit.generators.hawkes_sim import simulate
from critaudit.hawkes.mle import fit

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


if __name__ == "__main__":
    main()

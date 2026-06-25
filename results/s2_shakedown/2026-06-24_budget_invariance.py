"""Budget-knob invariance + n_tree load-bearing stress (increment-3, DECISIONS 2026-06-24).

PART 1 — MU_NEWS_HIGH is a BUDGET knob, not a result knob. Offspring are censored at HORIZON (finite
observation window), so the original MU_NEWS_HIGH=0.015 yields < N_MATCH in-window events; it was raised
to 0.4. This shows structural n_tree is INVARIANT to mu_news across 0.015 / 0.1 / 0.4, and the gate's
observational-subcritical VERDICT (peak < 1, no migration) is invariant too — the exact gate peak wobbles
(it is NOT a fixed number), but always stays subcritical. Only the event budget and χ move with mu_news,
so 0.4 cannot have outcome-tuned the gate finding.

PART 2 — n_tree is now the SOLE load-bearing directional instrument (the gate peak gap fell), so it gets
the stress that killed the peak gap: its per-seed spread for all three plants, to confirm the LOW<SUB,
HIGH>SUPER ordering is seed-stable with margin (not a point-value artifact).
Run: `/Users/zenith/anaconda3/bin/python results/s2_shakedown/2026-06-24_budget_invariance.py`
"""
import numpy as np
from critaudit.sim.controls import spec
from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.anchors import n_tree
from critaudit.experiments.shakedown import run_pipeline


def plant(eps, mu_news, seed):
    return simulate_labeled(eps=eps, horizon=spec.HORIZON, mu_news=mu_news, N=spec.N_AGENTS,
                            k_reach=spec.K_REACH, mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS,
                            c=spec.KERNEL_C, rng=np.random.default_rng(seed))


def main():
    print(f"frozen: N_MATCH={spec.N_MATCH} N_TREE_SUB={spec.N_TREE_SUB} N_TREE_SUPER={spec.N_TREE_SUPER}")
    print("=" * 78)
    print("PART 1 — HIGH carry-quantities vs mu_news (n_tree + observational gate peak):")
    print(f"{'mu_news':>8} | {'n_events':>9} {'>=N_MATCH':>9} | {'n_tree':>7} | {'gate peak':>9} {'migrated':>9}")
    for mun in (0.015, 0.1, 0.4):
        r = plant(spec.EPS_HIGH, mun, spec.SEED + 2)
        m = min(spec.N_MATCH, r.times.size)
        res = run_pipeline(r, n_match=m, csn_rng=np.random.default_rng(0), n_boot=5)
        print(f"{mun:>8} | {r.times.size:>9d} {str(r.times.size >= spec.N_MATCH):>9} | "
              f"{n_tree(r):>7.3f} | {res.gate.peak:>9.3f} {res.gate.migrated:>9.3f}")

    print("=" * 78)
    print("PART 2 — n_tree per-seed spread (5 seeds/plant; ordering must be seed-stable with margin):")
    for name, eps, mun in [("LOW", spec.EPS_LOW, spec.MU_NEWS_LOW),
                           ("CRIT", spec.EPS_CRIT, spec.MU_NEWS_CRIT),
                           ("HIGH", spec.EPS_HIGH, spec.MU_NEWS_HIGH)]:
        nts = [n_tree(plant(eps, mun, spec.SEED + 100 + s)) for s in range(5)]
        print(f"  {name:>4}: n_tree min={min(nts):.3f} max={max(nts):.3f}  (per-seed {[round(v,3) for v in nts]})")


if __name__ == "__main__":
    main()

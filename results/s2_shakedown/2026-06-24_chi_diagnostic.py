"""Controlled diagnostic for the increment-3 χ non-clearance (DECISIONS 2026-06-24).

WHY THIS EXISTS. The frozen secondary criterion `chi(CRIT) >= chi(LOW) and chi(CRIT) >= chi(HIGH)`
(a susceptibility should PEAK at criticality) did NOT clear. Before converting that failed criterion
to a characterization (test_shakedown_discrim.py::test_chi_does_not_resolve_the_critical_hump), the
diagnosis was confirmed by CONTROLLED measurement — this script — so the conversion rests on a
re-runnable observation, not a description ("documentation is not verification").

WHAT IT SHOWS. χ = var(population-MEAN opinion) is flat-to-noisy in eps and does NOT peak at eps_crit:
the population mean is ~0.5 by the symmetric Deffuant dynamics, so it is not an order parameter and its
temporal variance is not a susceptibility. Holding mu_news FIXED (removing the cohort's mu_news
confound, where the three plants have wildly different belief-sample counts) and sweeping eps across
criticality over several seeds, χ shows no resolved hump at eps_crit, while n_tree (the PRIMARY anchor)
is cleanly monotonic and crosses 1. Run: `/Users/zenith/anaconda3/bin/python results/s2_shakedown/2026-06-24_chi_diagnostic.py`
"""
import numpy as np
from critaudit.sim.controls import spec
from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.anchors import n_tree, chi

# CONTROLLED sweep: mu_news + horizon + N held FIXED, eps swept across criticality, several seeds.
N, HORIZON, MU_NEWS, SEEDS = 400, 1500.0, 2.0, range(8)
EPS_GRID = [0.04, 0.08, spec.EPS_CRIT, 0.20, 0.30]


def _run(eps, seed):
    return simulate_labeled(eps=eps, horizon=HORIZON, mu_news=MU_NEWS, N=N, k_reach=spec.K_REACH,
                            mu_step=spec.MU_STEP, kernel_eps=spec.KERNEL_EPS, c=spec.KERNEL_C,
                            rng=np.random.default_rng(1000 + seed))


def main():
    print(f"CONTROLLED chi-vs-eps sweep (mu_news={MU_NEWS} FIXED, N={N}, horizon={HORIZON}, "
          f"{len(list(SEEDS))} seeds; CENSORED generator)")
    print(f"{'eps':>7} | {'chi mean':>11} {'chi std':>11} | {'n_tree mean':>11}")
    print("-" * 56)
    chi_means = {}
    for eps in EPS_GRID:
        cs = [chi(_run(eps, s)) for s in SEEDS]
        nts = [n_tree(_run(eps, s)) for s in SEEDS]
        chi_means[eps] = float(np.mean(cs))
        mark = "  <-- eps_crit" if abs(eps - spec.EPS_CRIT) < 1e-9 else ""
        print(f"{eps:>7.3f} | {np.mean(cs):>11.2e} {np.std(cs):>11.2e} | {np.mean(nts):>11.3f}{mark}")
    crit = chi_means[spec.EPS_CRIT]
    others = [v for e, v in chi_means.items() if abs(e - spec.EPS_CRIT) >= 1e-9]
    print("-" * 56)
    print(f"chi(eps_crit) mean = {crit:.2e};  max chi over the grid at eps = "
          f"{max(chi_means, key=chi_means.get):.3f}  (a true susceptibility would peak AT eps_crit)")
    print(f"chi(eps_crit) / mean(chi at other eps) = {crit / np.mean(others):.2f}  "
          f"(>> 1 for a resolved peak; ~1 here -> no peak)")


if __name__ == "__main__":
    main()

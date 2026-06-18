"""Step 1 anchor: match the SOE likelihood engine against the EXACT O(N^2) likelihood on CLEAN
(un-quantized) power-law data, seed-by-seed, across n INCLUDING near-critical — where the
quadrature's tail handling is most strained (review note). If soe_mle tracks exact_mle at every n,
the engine is validated and its MLE-on-true-times is a legitimate recovery-test reference.

Both fit (mu, n) with the kernel SHAPE (eps, c) known. Near-critical rows use a short window (to keep
exact O(N^2) feasible); any shared bias there is the information limit, not an SOE artifact — the
anchor question is AGREEMENT, not hitting the planted value.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from powerlaw_hawkes import simulate_powerlaw, soe_mle, exact_mle

EPS, C, MU, N_TARGET = 0.4, 0.5, 0.4, 2500
print(f"SOE-MLE vs EXACT-MLE on clean power-law data (eps={EPS}, c={C}); shape known, recover n.")
print(f"{'n':>5} {'H':>7} {'N':>6} {'exact n̂':>9} {'SOE n̂':>8} {'|diff|':>7}")
worst = 0.0
for n in (0.6, 0.8, 0.9, 0.95, 0.97, 0.99):
    H = N_TARGET * (1 - n) / MU            # ~constant N; near-critical window is short (info limit)
    for seed in (1, 2):
        t = simulate_powerlaw(n, H, MU, EPS, C, np.random.default_rng(seed))
        ne = exact_mle(t, H, EPS, C)[1]
        ns = soe_mle(t, H, EPS, C)[1]
        worst = max(worst, abs(ne - ns))
        tag = "" if seed == 1 else "  (seed2)"
        print(f"{n:>5.2f} {H:>7.0f} {t.size:>6d} {ne:>9.3f} {ns:>8.3f} {abs(ne-ns):>7.3f}{tag}")
print(f"\nworst |SOE - exact| across all rows = {worst:.3f}")
print("PASS if SOE n̂ tracks exact n̂ at every n incl near-critical -> the SOE engine matches the exact "
      "likelihood and its MLE-on-true-times is a valid recovery reference for the MCEM test.")

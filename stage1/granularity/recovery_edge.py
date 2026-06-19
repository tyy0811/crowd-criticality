"""Complete the near-critical edge (n -> 1) at the sharp within-bin corner, per review 'extend to
0.99'. Criterion stays track-the-reference: near criticality the full-data MLE is itself noisy, so a
pass = MCEM matches that (noisy) reference, i.e. MCEM adds no bias beyond the information limit."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcem_powerlaw import recovery_point

EPS, C, GRID = 0.4, 0.2, 2.0          # sharp within-bin (F(2s)=0.62)
# (n, mu, H) — mu tuned to bound N~800 while H is long enough for a usable near-critical reference
CONFIGS = [(0.95, 0.033, 1200.0), (0.97, 0.020, 1200.0), (0.99, 0.0067, 1500.0)]
print("%5s %6s %5s %7s %8s %7s %5s %5s" % ("n", "H", "N", "ref", "MCEM", "|diff|", "acc", "ess"))
for n, mu, H in CONFIGS:
    for N, ref, nhat, acc, ess in recovery_point(n, EPS, C, mu, H, GRID, seeds=[1, 2], M=60):
        print("%5.2f %6.0f %5d %7.3f %8.3f %7.3f %5.2f %5.1f" % (n, H, N, ref, nhat, abs(ref - nhat), acc, ess))
print("\nREAD: MCEM tracks ref across n->0.99 -> envelope holds to the near-critical edge, A viable for the "
      "project regime. A growing gap somewhere -> that n is the trustworthy ceiling; B carries beyond it.")

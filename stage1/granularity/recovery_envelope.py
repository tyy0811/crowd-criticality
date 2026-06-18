"""Hard-corner-first power-law recovery/discrimination sweep — the power-law granularity verdict.
Lead with near-critical x sharp-within-bin; if MCEM tracks the full-data SOE-MLE there, the envelope
is the whole space. Criterion = track the full-data reference (NOT the planted value, unrecoverable
near critical even with perfect data)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcem_powerlaw import recovery_point

EPS, GRID = 0.4, 2.0
CONFIGS = [
    ("HARD near-critical n=0.9 x sharp c=0.2 F(2s)=0.62", 0.9, 0.2, 0.1, 1000.0),
    ("EASY anchor n=0.6 x mild c=2.0 F(2s)=0.24", 0.6, 2.0, 0.4, 800.0),
]
print("%-50s %5s %7s %8s %7s %5s %5s" % ("config", "N", "ref", "MCEM", "|diff|", "acc", "ess"))
for label, n, c, mu, H in CONFIGS:
    for N, ref, nhat, acc, ess in recovery_point(n, EPS, c, mu, H, GRID, seeds=[1, 2], M=60):
        print("%-50s %5d %7.3f %8.3f %7.3f %5.2f %5.1f" % (label, N, ref, nhat, abs(ref - nhat), acc, ess))
print("\nREAD: MCEM tracks ref at the HARD corner -> within-bin marginalization recovers n across the "
      "envelope -> source A viable for near-critical power-law. Gap -> A's trustworthy region is bounded.")

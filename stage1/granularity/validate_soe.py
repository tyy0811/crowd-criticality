"""Validate the SOE approximation to the tolerance of the functionals MCEM consumes (review note),
BEFORE it enters the recovery test — so a later recovery failure is attributable to the science,
not the approximation. Checks: (1) total mass (branching ratio) sum a/beta == n; (2) the integrated
kernel (compensator) relative error, sub-grid especially; (3) the bin-integrated intensity over 2 s
windows at sub-grid lags; (4) pointwise kernel (secondary).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from powerlaw_hawkes import fit_soe, soe_kernel, soe_integrated, exact_integrated

GRID = 2.0


def relerr(x, y):
    return float(np.max(np.abs(x - y) / np.maximum(np.abs(y), 1e-12)))


for eps, c in [(0.4, 0.5), (0.3, 0.25), (0.6, 1.0)]:   # realistic power-law exponents + cutoffs (note 1)
    n = 0.6
    a, betas = fit_soe(n, eps, c)
    mass = float((a / betas).sum())
    tg = np.geomspace(1e-3, 1e3, 400)
    phi_ex = n * eps * c**eps / (tg + c) ** (1.0 + eps)
    G_ex, G_soe = exact_integrated(tg, n, eps, c), soe_integrated(tg, a, betas)
    sub = tg < GRID
    print(f"\n=== eps={eps}, c={c}  (F(2s)={1-(c/(c+2))**eps:.2f}, M={a.size} active={int((a>0).sum())}) ===")
    print(f"  (1) total mass sum a/beta = {mass:.4f}  vs n={n}  -> branching-ratio rel err {abs(mass-n)/n:.4f}")
    print(f"  (2) INTEGRATED (consumed) rel err: all={relerr(G_soe, G_ex):.4f}  sub-grid(t<2s)={relerr(G_soe[sub], G_ex[sub]):.4f}")
    for lag in (0.0, 0.5, 1.0, 2.0):
        be = float(exact_integrated(lag + GRID, n, eps, c) - exact_integrated(lag, n, eps, c))
        bs = float(soe_integrated(np.array([lag + GRID]), a, betas)[0] - soe_integrated(np.array([lag]), a, betas)[0])
        print(f"  (3) bin-integrated phi over [{lag:.1f},{lag+GRID:.1f}]: exact={be:.4f} soe={bs:.4f} relerr={abs(bs-be)/max(be,1e-12):.4f}")
    print(f"  (4) pointwise kernel rel err: all={relerr(soe_kernel(tg, a, betas), phi_ex):.4f}  sub-grid={relerr(soe_kernel(tg[sub], a, betas), phi_ex[sub]):.4f}")
print("\nPASS if branching-ratio rel err and INTEGRATED sub-grid rel err are small (<~1-2%): the SOE "
      "carries the consumed functionals faithfully and may enter MCEM. Else refit (more M / fit the integral).")

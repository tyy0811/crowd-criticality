#!/usr/bin/env python3
"""The MEMORY axis of the identifiability floor — the one that may explain the real-market split. The
(N,ramp) floor map at eps=0.4 was flat & low (<10k), so volume/ramp don't gate it there. But the
degenerate real markets PREFER heavier tails (peak migrates to eps→0.2); a heavier tail should floor
HIGHER. Map floor(eps_plant): plant a near-critical n=0.85 at several kernel memories (eps), sweep N,
find where recovery switches on.

  floor RISES steeply as eps_plant shrinks, reaching >22k near eps~0.1–0.2  -> RESTORES the floor story
    as a memory-dependent surface: markets 1,2 (heavy tail) below their floor at 18–22k, market 3
    (eps=0.4) above its low floor at 35k. The split is a (memory) floor after all.
  floor STAYS low (<~15k) even at heavy tails  -> the real markets are genuinely MIS-MODELLED off the
    clean Lomax+smooth-ramp surface (a deeper finding): their degeneracy is model inadequacy, not a floor.

Recovery criterion: profile peak over a wide shape grid (incl. eps down to 0.02 = the runaway boundary)
stays at the planted n=0.85 (IDENTIFIED) vs runs to 1.05/1.20 (degenerate).
"""
import pathlib
import sys
import time

SPIKE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE))
import numpy as np
from critaudit.hawkes.binned import PowerLawKernel
from mu_t_hawkes import fit_mu_only

RESULTS = SPIKE.parent.parent / "results" / "s0.4_feasibility"
K_FLEX = 12
C_T, N_PLANT, RAMP, T = 2.0, 0.85, 10.0, 50000.0
EPS_PLANTS = [0.1, 0.2, 0.3, 0.4]                       # kernel memory: heavy -> light tail
N_TARGETS = [12000, 20000, 30000, 45000]
N_GRID = [0.60, 0.85, 1.05, 1.20]
EPS_TEST = [0.02, 0.05, 0.1, 0.2, 0.4]                 # test shapes incl. the heavy-tail runaway boundary


def simulate_ramp(mu0, ramp, n, T, eps, c, rng):
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


def peak_n(t):
    prof = [(n, max(fit_mu_only(t, T, PowerLawKernel(eps=e, c=C_T), n, K_FLEX)["ll"] for e in EPS_TEST))
            for n in N_GRID]
    return max(prof, key=lambda x: x[1])[0]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


log(f"floor(eps) map: plant n={N_PLANT}, c={C_T}, ramp={RAMP}; eps_plant={EPS_PLANTS}; N={N_TARGETS}")
cells = {}
for eps_t in EPS_PLANTS:
    for Nt in N_TARGETS:
        mu0 = Nt * (1.0 - N_PLANT) / (T * (1.0 + RAMP / 2.0))
        t = simulate_ramp(mu0, RAMP, N_PLANT, T, eps_t, C_T, np.random.default_rng(41))
        pk = peak_n(t)
        cells[(eps_t, Nt)] = (t.size, pk)
        log(f"eps_plant={eps_t} N_target={Nt:>6} -> N={t.size:>6}  peak-n={pk:.2f}  "
            f"{'IDENTIFIED' if pk <= N_PLANT + 1e-9 else 'degenerate'}")

lines = [f"# Identifiability floor vs kernel MEMORY (planted n={N_PLANT}, ramp={RAMP}x) — {time.strftime('%Y-%m-%d %H:%M:%S')}",
         f"Cell = peak-n; IDENTIFIED iff stays at planted {N_PLANT}; degenerate iff runs to 1.05/1.20.", "",
         f"{'N_target':>9} | " + " | ".join(f"eps {e:g}" for e in EPS_PLANTS)]
for Nt in N_TARGETS:
    row = []
    for e in EPS_PLANTS:
        n_act, pk = cells[(e, Nt)]
        row.append(f"{pk:.2f}{'✓' if pk <= N_PLANT + 1e-9 else '×'}(N={n_act})")
    lines.append(f"{Nt:>9} | " + " | ".join(row))
lines += ["", "## floor(eps): smallest N that IDENTIFIES"]
for e in EPS_PLANTS:
    ids = [Nt for Nt in N_TARGETS if cells[(e, Nt)][1] <= N_PLANT + 1e-9]
    lines.append(f"- eps={e:g} (tail {'heavy' if e <= 0.2 else 'lighter'}): floor ≈ "
                 f"{min(ids) if ids else '> %d' % N_TARGETS[-1]} events")
lines += ["", "Read: if floor RISES into 22–45k as eps shrinks to 0.1–0.2, the real split is a "
          "MEMORY-dependent floor (markets 1,2 heavy-tail below floor; market 3 eps=0.4 above). If floor "
          "stays <~15k even at eps=0.1, the real degenerate markets are MIS-MODELLED, not floored."]
outp = RESULTS / f"{time.strftime('%Y-%m-%d')}_floor_eps_map.md"
outp.write_text("\n".join(lines))
log(f"-> {outp}")
print("\n" + "\n".join(lines))

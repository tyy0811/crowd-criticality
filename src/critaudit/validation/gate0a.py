from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import os
import numpy as np
from critaudit.generators.branching import galton_watson
from critaudit.generators.exact import pure_power_law
from critaudit.generators.lookalike import scaling_break
from critaudit.generators.hawkes_sim import simulate
from critaudit.powerlaw.csn import fit_powerlaw
from critaudit.scaling.crackling import joint_bootstrap, exponents
from critaudit.scaling.gate_a2 import corroborate


@dataclass
class CellResult:
    name: str
    role: str            # "A1" (A.1 gated) | "A2" (A.2 gated; A.1 informational only)
    a1_passes: bool      # A1 cells: gated Clauset verdict. A2 cells: informational LRT verdict.
    a2_label: str | None
    tau: float           # size power-law exponent
    alpha: float         # duration exponent (A.2 cells; nan for A1 cells)
    inv_snz: float       # curv 1/snz (A.2 cells; nan for A1 cells)
    delta_mean: float
    resolution: float
    boot_nan: int = 0    # # of NaN bootstrap-Delta replicates (>0 => A.2 verdict unreliable)


@dataclass
class Gate0aReport:
    cells: dict
    backend_check: dict
    passed: bool
    writedown_path: str


def _a1_cell(name, sizes, rng, n_boot):
    """A.1-GATED cell: full Clauset CSN (bootstrap GoF p + LRT). `.passes` is the gate."""
    f = fit_powerlaw(np.asarray(sizes), rng=rng, n_boot=n_boot)
    return CellResult(name, role="A1", a1_passes=f.passes, a2_label=None,
                      tau=f.exponent, alpha=float("nan"), inv_snz=float("nan"),
                      delta_mean=float("nan"), resolution=float("nan"), boot_nan=0)


def _a2_cell(name, av, rng, B):
    """A.2-GATED cell: corroborate the crackling scaling relation. A.1 is reported
    INFORMATIONALLY only (LRT arm, compute_p=False): the critical generator's sizes are
    Borel-Tanner — only asymptotically a power law — so the strict-GoF p_boot is marginal
    at large N and is deliberately NOT gated here (the strict-power-law A.1 pass is
    certified by the `pure_powerlaw` positive control). See DECISIONS.md 2026-06-16."""
    sizes = av.sizes if av.censored is None else av.sizes[~av.censored]
    tau, alpha, inv = exponents(av)
    dr = joint_bootstrap(av, B, rng)
    bnan = int(np.isnan(dr.samples).sum())
    label = corroborate(dr)
    a1_info = fit_powerlaw(sizes, rng=rng, n_boot=0, compute_p=False).passes  # LRT-only
    return CellResult(name, role="A2", a1_passes=a1_info, a2_label=label,
                      tau=tau, alpha=alpha, inv_snz=inv,
                      delta_mean=float(dr.samples.mean()), resolution=float(dr.halfwidth),
                      boot_nan=bnan)


def _backend_crosscheck(rng, n=0.6, horizon=5000.0, reps=8, tol_sd=3.0):
    th = np.array([simulate(n, horizon, backend="thinning", rng=rng).times.size
                   for _ in range(reps)])
    cl = np.array([simulate(n, horizon, backend="cluster", rng=rng).times.size
                   for _ in range(reps)])
    se = np.sqrt(th.var(ddof=1) / reps + cl.var(ddof=1) / reps)
    return {"thinning_mean": float(th.mean()), "cluster_mean": float(cl.mean()),
            "se": float(se), "agree": bool(abs(th.mean() - cl.mean()) <= tol_sd * se)}


def run_gate0a(rng, n_avalanches=20000, B=40, n_boot=40,
               out_dir="results/s0.1_gate0a"):
    """Gate-0(a) 2x2: an A.1 axis (does CSN tell a power law from a cutoff look-alike?)
    and an A.2 axis (does the coarse scaling-relation check tell a critical generator
    from a pairing-shuffled look-alike?).

    A.1 axis is gated on STRICT-power-law controls: `pure_powerlaw` (exact Zipf s^-3/2)
    must pass; `csn_killer` (subcritical GW, real cutoff) must reject. The critical GW is
    NOT an A.1 control (its Borel sizes are only asymptotically a power law); it anchors
    the A.2 axis, with its A.1 reported informationally."""
    pure = pure_power_law(n_avalanches, rng)            # exact Zipf s^-2.5 (not s^-1.5: see exact.py) -> A.1 positive control
    killer = galton_watson(0.7, n_avalanches, rng)      # subcritical cutoff -> A.1 negative control
    crit = galton_watson(1.0, n_avalanches, rng)        # critical -> A.2 (scaling relation holds)
    breaker = scaling_break(crit, delta=1.0, rng=rng)   # pairing shuffled -> A.2 negative control

    killer_sizes = killer.sizes if killer.censored is None else killer.sizes[~killer.censored]
    cells = {
        "pure_powerlaw": _a1_cell("pure_powerlaw", pure, rng, n_boot),
        "csn_killer": _a1_cell("csn_killer", killer_sizes, rng, n_boot),
        "critical": _a2_cell("critical", crit, rng, B),
        "scaling_breaker": _a2_cell("scaling_breaker", breaker, rng, B),
    }

    backend = _backend_crosscheck(rng)
    passed = (cells["pure_powerlaw"].a1_passes                            # A.1 positive control passes
              and not cells["csn_killer"].a1_passes                       # A.1 negative control rejected
              and cells["critical"].a2_label == "not-grossly-violated"    # A.2 positive
              and cells["scaling_breaker"].a2_label == "grossly-violated" # A.2 negative
              and backend["agree"])
    path = _writedown(cells, backend, passed, n_avalanches, out_dir)
    return Gate0aReport(cells=cells, backend_check=backend, passed=passed,
                        writedown_path=path)


def _writedown(cells, backend, passed, n_avalanches, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{date.today().isoformat()}_writedown.txt")
    with open(path, "w") as fh:
        fh.write(f"=== Gate-0(a) writedown ({date.today().isoformat()}) ===\n")
        fh.write(f"n_avalanches={n_avalanches}\n")
        for c in cells.values():
            if c.role == "A1":
                fh.write(f"[{c.name}] role=A1-GATE A1_passes={c.a1_passes} "
                         f"tau={c.tau:.3f}\n")
            else:
                fh.write(f"[{c.name}] role=A2-GATE A2={c.a2_label} "
                         f"(A1_LRT={c.a1_passes}, informational) "
                         f"tau={c.tau:.3f} alpha={c.alpha:.3f} 1/snz={c.inv_snz:.3f} "
                         f"delta={c.delta_mean:.3f} resolution={c.resolution:.3f} "
                         f"boot_nan={c.boot_nan}\n")
        fh.write(f"[backend n=0.6] {backend}\n")
        fh.write(f"PASSED={passed}\n")
    return path


if __name__ == "__main__":   # `make gate0a`: the executable certification
    import sys
    report = run_gate0a(np.random.default_rng(20260615))
    print(f"Gate-0(a) PASSED={report.passed} -> {report.writedown_path}")
    sys.exit(0 if report.passed else 1)

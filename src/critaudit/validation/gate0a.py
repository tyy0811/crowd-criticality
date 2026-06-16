from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import os
import numpy as np
from critaudit.generators.branching import galton_watson
from critaudit.generators.lookalike import scaling_break
from critaudit.generators.hawkes_sim import simulate
from critaudit.powerlaw.csn import fit_powerlaw
from critaudit.scaling.crackling import joint_bootstrap, exponents
from critaudit.scaling.gate_a2 import corroborate


@dataclass
class CellResult:
    name: str
    a1_passes: bool
    a2_label: str | None
    tau: float
    alpha: float
    inv_snz: float
    delta_mean: float
    resolution: float


@dataclass
class Gate0aReport:
    cells: dict
    backend_check: dict
    passed: bool
    writedown_path: str


def _a1(sizes, rng, n_boot):
    f = fit_powerlaw(sizes, rng=rng, n_boot=n_boot)
    return f.passes, f


def _backend_crosscheck(rng, n=0.6, horizon=5000.0, reps=8, tol_sd=3.0):
    th = np.array([simulate(n, horizon, backend="thinning", rng=rng).times.size
                   for _ in range(reps)])
    cl = np.array([simulate(n, horizon, backend="cluster", rng=rng).times.size
                   for _ in range(reps)])
    se = np.sqrt(th.var(ddof=1) / reps + cl.var(ddof=1) / reps)
    return {"thinning_mean": float(th.mean()), "cluster_mean": float(cl.mean()),
            "se": float(se), "agree": bool(abs(th.mean() - cl.mean()) <= tol_sd * se)}


def run_gate0a(rng, n_avalanches=20000, B=50, n_boot=50,
               out_dir="results/s0.1_gate0a"):
    crit = galton_watson(1.0, n_avalanches, rng)
    killer = galton_watson(0.7, n_avalanches, rng)
    breaker = scaling_break(crit, delta=1.0, rng=rng)

    cells = {}
    for name, av in (("critical", crit), ("csn_killer", killer),
                     ("scaling_breaker", breaker)):
        sizes = av.sizes if av.censored is None else av.sizes[~av.censored]
        a1_pass, _ = _a1(sizes, rng, n_boot)
        tau, alpha, inv = exponents(av)
        if name == "csn_killer":          # A.1-tier look-alike: no A.2 reading
            label, dmean, res = None, float("nan"), float("nan")
        else:
            dr = joint_bootstrap(av, B, rng)
            label = corroborate(dr)        # coarse: not-grossly-violated / grossly-violated
            dmean, res = float(dr.samples.mean()), float(dr.halfwidth)
        cells[name] = CellResult(name, a1_pass, label, tau, alpha, inv, dmean, res)

    backend = _backend_crosscheck(rng)
    passed = (cells["critical"].a1_passes
              and cells["critical"].a2_label == "not-grossly-violated"
              and not cells["csn_killer"].a1_passes
              and cells["scaling_breaker"].a1_passes
              and cells["scaling_breaker"].a2_label == "grossly-violated"
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
            fh.write(f"[{c.name}] A1_passes={c.a1_passes} A2={c.a2_label} "
                     f"tau={c.tau:.3f} alpha={c.alpha:.3f} 1/snz={c.inv_snz:.3f} "
                     f"delta={c.delta_mean:.3f} resolution={c.resolution:.3f}\n")
        fh.write(f"[backend n=0.6] {backend}\n")
        fh.write(f"PASSED={passed}\n")
    return path


if __name__ == "__main__":   # `make gate0a`: the executable certification
    import sys
    report = run_gate0a(np.random.default_rng(20260615))
    print(f"Gate-0(a) PASSED={report.passed} -> {report.writedown_path}")
    sys.exit(0 if report.passed else 1)

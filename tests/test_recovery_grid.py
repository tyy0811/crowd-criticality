import numpy as np, pytest
from critaudit.experiments.recovery_grid import coverage_cell


def test_coverage_cell_structure_fast():
    out = coverage_cell(0.5, 1200, R=4, base_seed=0)
    assert 0.0 <= out["coverage"] <= 1.0
    assert out["R"] <= 4 and out["n"] == 0.5


@pytest.mark.slow
def test_coverage_at_n06_is_high():
    out = coverage_cell(0.6, 10000, R=50, base_seed=1)
    assert out["coverage"] >= 0.85   # ~95% nominal; gate at 0.90 in the full grid


from critaudit.generators.hawkes_sim import simulate
from critaudit.hawkes.mle import fit
from critaudit.experiments.recovery_grid import bootstrap_ci, profile_bootstrap_audit


def test_bootstrap_ci_brackets_point_estimate():
    es = simulate(0.5, 4000.0, mu=0.6, beta=1.0, backend="thinning",
                  rng=np.random.default_rng(0))
    f = fit(es)
    lo, hi = bootstrap_ci(es, f, B=20, rng=np.random.default_rng(1))
    assert lo < f.n < hi


@pytest.mark.slow
def test_profile_bootstrap_audit_runs_at_boundary():
    out = profile_bootstrap_audit(3000, R=4, base_seed=2, B=60)
    assert out["R"] >= 1 and np.isfinite(out["mean_overlap"])

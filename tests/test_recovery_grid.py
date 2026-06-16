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

"""Reduced-budget end-to-end smoke of the probe-grid driver (sub-inc-3 T6, @slow $0): schema
complete, deterministic, and a non-frozen design can never masquerade as the registered artifact
(frozen_design=False + verdict NOT_EVALUATED)."""
import json

import pytest

from critaudit.experiments.probe_recoverability import run_probe_grid


@pytest.mark.slow
def test_reduced_budget_smoke_schema_and_determinism(tmp_path):
    kw = dict(_eps_grid=(0.10, 0.134, 0.20), _n_seeds=2, _horizon=250.0, _m_eligible=8,
              _with_sensitivity=False, n_workers=2)
    r1 = run_probe_grid(out_path=str(tmp_path / "a.json"), **kw)
    r2 = run_probe_grid(out_path=str(tmp_path / "b.json"), **kw)
    assert open(tmp_path / "a.json", "rb").read() == open(tmp_path / "b.json", "rb").read()
    assert r1["artifact"] == "probe_recoverability"
    assert r1["frozen_design"] is False                       # cannot masquerade as registered
    assert r1["verdict"] == {"status": "NOT_EVALUATED_NON_FROZEN_DESIGN"}
    for key in ("chi_resp", "s_mean", "n_gen", "n_resp", "used_markers"):
        m = r1["surface"][key]
        assert len(m) == 3 and all(len(row) == 2 for row in m)
        assert all(v is not None for row in m for v in row)
    assert all(all(v == 8 for v in row) for row in r1["surface"]["used_markers"])
    blob = json.dumps(r1)
    import re
    assert not re.search(r'"[^"]*(tau|p_boot|alpha|gate_|n_emit)[^"]*"\s*:', blob)

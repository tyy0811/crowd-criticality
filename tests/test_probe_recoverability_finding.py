"""Characterization lock for the banked sub-inc-3 probe-recoverability finding (@slow, $0) —
the Gate-D precedent shape, anti-relaxation in BOTH directions:

  - the LOCATOR PASS is locked WITH ITS MARGINS (prominence 4.8x vs floor 2.0; seed consistency
    12/12 vs floor 9/12; the crossing inside the peak's neighbor interval) — a regression that
    degrades the instrument breaks this;
  - the TRANSFORM FAIL is locked WITH ITS MARGINS (held-out errors strictly ABOVE the 0.05
    tolerance) — a silent tolerance-lift or estimator swap that makes n_resp 'pass' breaks this
    ('just raise the bar' is forbidden in either direction; n_resp stays UNACTIVATED).

Byte-reproduction: the banked artifact regenerates byte-identically from the frozen design
(environment drift fails loudly; re-bank consciously)."""
import filecmp
import json

import pytest

from critaudit.experiments.probe_recoverability import BANKED_GRID_JSON, run_probe_grid
from critaudit.sim.controls import probe_spec as pspec


@pytest.mark.slow
def test_banked_probe_finding_locked(tmp_path):
    with open(BANKED_GRID_JSON) as f:
        rec = json.load(f)
    assert rec["frozen_design"] is True
    v = rec["verdict"]

    # LOCATOR PASS with margins (the chi_resp instrument certification).
    assert v["status"] == "PASS" and v["reasons"] == []
    loc = v["locator"]
    assert loc["eps_hat"] == 0.12 and loc["interior"] is True
    assert loc["crossing_in_neighbor_interval"] is True
    assert 0.10 < loc["eps_c_gen"] < 0.12          # the measured clustering-shifted crossing
    assert loc["prominence_ratio"] >= 2.0 * pspec.PEAK_RATIO_MIN       # 4.8 vs floor 2.0
    assert loc["seed_consistency"] == 1.0

    # TRANSFORM FAIL with margins: every accuracy-range error strictly ABOVE tolerance —
    # n_resp is UNACTIVATED and the collision+censor gap is the measured reason.
    tr = v["transform"]
    assert tr["pass"] is False
    assert set(tr["accuracy_err"]) == {"0.08", "0.09", "0.1"}
    for err in tr["accuracy_err"].values():
        assert err > pspec.N_RESP_TOL              # 0.063 / 0.078 / 0.103 vs 0.05
    assert max(tr["accuracy_err"].values()) > 0.10  # the gap GROWS toward criticality
    # (b2) resolution floor also failed at the band point — recorded.
    assert v["resolution"]["pass"] is False

    # Anti-relaxation guard on the frozen constants themselves.
    assert pspec.N_RESP_TOL == 0.05 and pspec.PEAK_RATIO_MIN == 2.0

    # Byte-reproduction from the frozen design (144 s; the strongest regression anchor).
    out = str(tmp_path / "regen.json")
    run_probe_grid(out_path=out)
    assert filecmp.cmp(out, BANKED_GRID_JSON, shallow=False)

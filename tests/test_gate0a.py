import os
import numpy as np, pytest
from critaudit.validation.gate0a import run_gate0a


@pytest.mark.slow
def test_gate0a_plumbing_fast(tmp_path):
    # Small-N PLUMBING test: assert the harness wires end-to-end and emits a well-formed
    # report + writedown. The science verdicts (pure_powerlaw passes A.1, csn_killer
    # rejects A.1, critical not-grossly-violated, breaker grossly-violated) need realistic
    # N and are asserted only in the slow certification: at n_avalanches=2000 the curv
    # 1/snz fit runs on ~4 duration bins, so the A.2 bootstrap half-width is huge and no
    # coarse verdict is N-robust here. We therefore check structure, not verdicts.
    rep = run_gate0a(np.random.default_rng(0), n_avalanches=2000, B=20,
                     n_boot=20, out_dir=str(tmp_path))
    assert set(rep.cells) == {"pure_powerlaw", "csn_killer", "critical", "scaling_breaker"}
    # A.1 cells (the gated A.1 axis) carry no A.2 reading
    assert rep.cells["pure_powerlaw"].role == "A1" and rep.cells["pure_powerlaw"].a2_label is None
    assert rep.cells["csn_killer"].role == "A1" and rep.cells["csn_killer"].a2_label is None
    # A.2 cells produce a valid coarse verdict (value not asserted at this N)
    for name in ("critical", "scaling_breaker"):
        assert rep.cells[name].role == "A2"
        assert rep.cells[name].a2_label in {"not-grossly-violated", "grossly-violated"}
    assert {"thinning_mean", "cluster_mean", "se", "agree"} <= set(rep.backend_check)
    assert isinstance(rep.passed, bool)
    assert os.path.exists(rep.writedown_path)


@pytest.mark.slow
def test_gate0a_full_certification(tmp_path):
    rep = run_gate0a(np.random.default_rng(20260615), out_dir=str(tmp_path))
    # A.1 axis: exact power law passes, real-cutoff look-alike rejects
    assert rep.cells["pure_powerlaw"].a1_passes is True
    assert rep.cells["csn_killer"].a1_passes is False
    # A.2 axis: critical corroborates the scaling relation, shuffle grossly violates it
    assert rep.cells["critical"].a2_label == "not-grossly-violated"
    assert rep.cells["scaling_breaker"].a2_label == "grossly-violated"
    assert rep.backend_check["agree"] is True
    assert rep.passed is True

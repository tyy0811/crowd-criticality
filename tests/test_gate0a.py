import os
import numpy as np, pytest
from critaudit.validation.gate0a import run_gate0a


def test_gate0a_plumbing_fast(tmp_path):
    # Small-N PLUMBING test: assert the harness wires end-to-end and emits a
    # well-formed report + writedown. The 2x2 SCIENCE verdicts (critical
    # not-grossly-violated, csn_killer A.1 reject, scaling_breaker grossly-violated)
    # require realistic N and are asserted only in the slow certification: at
    # n_avalanches=2000 the curvature-corrected 1/snz fit runs on ~4 duration bins,
    # so the bootstrap half-width (the corroborate resolution proxy) is huge and no
    # coarse verdict is N-robust here. We therefore check structure, not verdicts.
    rep = run_gate0a(np.random.default_rng(0), n_avalanches=2000, B=20,
                     n_boot=20, out_dir=str(tmp_path))
    assert set(rep.cells) == {"critical", "csn_killer", "scaling_breaker"}
    # csn_killer is an A.1-tier look-alike -> it carries no A.2 reading (structural)
    assert rep.cells["csn_killer"].a2_label is None
    # the two A.2 cells produce a valid coarse verdict (the value is not asserted)
    for name in ("critical", "scaling_breaker"):
        assert rep.cells[name].a2_label in {"not-grossly-violated", "grossly-violated"}
    # the backend cross-check ran and produced its agreement structure
    assert {"thinning_mean", "cluster_mean", "se", "agree"} <= set(rep.backend_check)
    assert isinstance(rep.passed, bool)
    assert os.path.exists(rep.writedown_path)


@pytest.mark.slow
def test_gate0a_full_certification(tmp_path):
    rep = run_gate0a(np.random.default_rng(1), out_dir=str(tmp_path))
    assert rep.cells["critical"].a1_passes is True
    assert rep.cells["critical"].a2_label == "not-grossly-violated"
    assert rep.cells["csn_killer"].a1_passes is False
    assert rep.cells["scaling_breaker"].a1_passes is True
    assert rep.cells["scaling_breaker"].a2_label == "grossly-violated"
    assert rep.backend_check["agree"] is True
    assert rep.passed is True

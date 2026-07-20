"""Cohort marginal extraction plus byte-reproduction of definition-#2 calibration v2."""
import json
import os

import numpy as np
import pytest

from critaudit.sim.harness.cohort_marginals import (
    COHORT_MARGINALS_FIELDS, CohortMarginals, extract_marginals)
from critaudit.sim.harness.types import HarnessRun


def _run(times, content=None):
    times = np.asarray(times, dtype=float)
    n = times.size
    return HarnessRun(times=times, root_id=np.arange(n, dtype=np.int64),
                      parent_idx=np.full(n, -1, dtype=np.int64),
                      read_emit_success=np.zeros(n, dtype=bool),
                      content=content if content is not None else [f"t{i}" for i in range(n)])


def test_extract_marginals_counts_and_pool():
    m = extract_marginals(_run([0, 0, 1, 3, 3, 3], content=list("abcdef")))
    assert isinstance(m, CohortMarginals)
    assert m.per_round_counts == (2, 1, 0, 3)          # zero-count round 2 kept in the profile
    assert m.authored_texts == ("a", "b", "c", "d", "e", "f")


def test_extract_marginals_whitelist_is_pinned():
    # The structural firewall (design §8): exactly two fields, nothing for a tree statistic to
    # ride in on. A field addition is a spec change and must fail here first.
    assert COHORT_MARGINALS_FIELDS == ("per_round_counts", "authored_texts")


def test_extract_marginals_fail_closed():
    with pytest.raises(ValueError, match="empty"):
        extract_marginals(_run([]))
    with pytest.raises(ValueError, match="round-granular"):
        extract_marginals(_run([0.0, 1.5]))
    with pytest.raises(ValueError, match="misaligned"):
        extract_marginals(_run([0, 1], content=["only-one"]))


# Single-source locations (review 2026-07-17): the driver owns them; a re-bank updates driver +
# tests in one edit.
from critaudit.experiments.llm_parrot_null import (   # noqa: E402
    BANKED_CALIBRATION_JSON as _BANKED, DEFAULT_ARCHIVE as _ARCHIVE)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.isdir(_ARCHIVE),
                    reason="registered cohort archive not present on this machine")
def test_similarity_calibration_reproduces_banked_json(tmp_path):
    """The finite-window membership calibration is reproducible and explicitly failed."""
    pytest.importorskip("sentence_transformers", reason="optional [embed] extra not installed")
    from critaudit.experiments.llm_parrot_null import run_similarity_calibration

    out = str(tmp_path / "similarity.json")
    rec = run_similarity_calibration(_ARCHIVE, out_path=out)
    assert rec["artifact"] == "similarity_calibration"
    assert rec["construction_version"] == 2
    assert rec["status"] == "failed"
    assert rec["mean_ari"] < rec["spec"]["recovery_threshold"]
    assert rec["window"] in rec["spec"]["window_grid"]
    assert 0.0 < rec["theta"] <= 1.0
    assert set(rec["per_window"]) == {"20260627", "20260628", "20260629"}
    # Schema firewall (design §8): no embargoed key anywhere in the banked artifact.
    import re
    blob = json.dumps(rec)
    assert not re.search(r'"[^"]*(tau|p_boot|alpha|gate_|n_emit)[^"]*"\s*:', blob)
    # The failed finding is still a deterministic banked calibration artifact.
    assert open(out, "rb").read() == open(_BANKED, "rb").read()

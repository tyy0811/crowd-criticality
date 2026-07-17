"""Fast synthetic tests for the n_struct band driver (sub-inc-2 T7): structure, determinism, and
the fail-closed abort path — no archive, no torch. The @slow real-archive band reproduction lives
here too (archive-gated)."""
import json
import os
import re

import numpy as np
import pytest

from critaudit.experiments.llm_parrot_null import run_matched_null_band
from critaudit.sim.harness.cohort_marginals import CohortMarginals


def _toy_window(seed, n=30, dim=8, rounds=(10, 10, 10)):
    rng = np.random.default_rng(seed)
    E = np.ones(dim) + 0.3 * rng.normal(size=(n, dim))   # anisotropic (real-embedding geometry)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    texts = tuple(f"w{seed}-msg-{i:02d}-" + "x" * (i % 7) for i in range(n))
    return CohortMarginals(per_round_counts=rounds, authored_texts=texts), E


@pytest.fixture()
def toy_windows():
    return {f"win{k}": _toy_window(k) for k in range(3)}


def test_band_shape_keys_and_roundrobin(toy_windows):
    rec = run_matched_null_band(theta=0.5, n_seeds=6, base_seed=100, windows=toy_windows)
    assert rec["artifact"] == "nstruct_band"
    assert len(rec["n_struct_values"]) == 6
    assert all(0.0 <= v < 1.0 for v in rec["n_struct_values"])
    assert [len(rec["per_window"][w]) for w in ("win0", "win1", "win2")] == [2, 2, 2]
    assert rec["edge_max"] == max(rec["n_struct_values"])
    assert rec["quantile_value"] <= rec["edge_max"]
    assert [row["seed"] for row in rec["seeds"]] == [100 + i for i in range(6)]


def test_band_deterministic(toy_windows):
    r1 = run_matched_null_band(theta=0.5, n_seeds=6, base_seed=100, windows=toy_windows)
    r2 = run_matched_null_band(theta=0.5, n_seeds=6, base_seed=100, windows=toy_windows)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_band_aborts_on_first_gate_failure(toy_windows):
    # Fail-closed abort (design §11 — no silently partial band): doctor one window so its pool
    # embeddings misalign with its marginals; the generator raises on the FIRST seed assigned to
    # that window and the band never returns.
    marg, E = toy_windows["win1"]
    toy_windows["win1"] = (marg, E[:-1])
    with pytest.raises(ValueError, match="misaligned"):
        run_matched_null_band(theta=0.5, n_seeds=6, base_seed=100, windows=toy_windows)


def test_band_record_carries_no_embargoed_keys(toy_windows):
    rec = run_matched_null_band(theta=0.5, n_seeds=3, base_seed=7, windows=toy_windows)
    blob = json.dumps(rec)
    assert not re.search(r'"[^"]*(tau|p_boot|alpha|gate_|n_emit)[^"]*"\s*:', blob)


_ARCHIVE = os.path.expanduser("~/crowd-crit-runs/s2_harness_subinc1")
_BANKED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "s2_llm_parrot_null", "2026-07-17_nstruct_band.json")


@pytest.mark.slow
@pytest.mark.skipif(not os.path.isdir(_ARCHIVE),
                    reason="registered cohort archive not present on this machine")
def test_real_band_reproduces_banked_json(tmp_path):
    """The banked 64-seed band is byte-reproducible from the archive at the BANKED theta through
    the pinned realization. Environment drift fails loudly — re-bank consciously."""
    pytest.importorskip("sentence_transformers", reason="optional [embed] extra not installed")
    out = str(tmp_path / "band.json")
    rec = run_matched_null_band(_ARCHIVE, out_path=out)
    assert len(rec["n_struct_values"]) == 64
    assert open(out, "rb").read() == open(_BANKED, "rb").read()
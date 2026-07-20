"""Frozen-surface guards for llm_parrot_spec (sub-inc-2 T3) — the anti-p-hacking freeze, in the
test_parrot_spec_frozen_surface tradition: existence + range + cross-file drift tripwires. No value
back-fill ever; a mismatch here is a spec change that must be made loudly, not absorbed."""
import hashlib
import os
import re

import pytest

from critaudit.sim.controls import llm_parrot_spec as lps
from critaudit.sim.controls import parrot_spec as ps
from critaudit.sim.harness import harness_spec as hs

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_embedding_pin_frozen():
    assert lps.EMBED_MODEL_ID == "sentence-transformers/all-MiniLM-L6-v2"
    assert re.fullmatch(r"[0-9a-f]{40}", lps.EMBED_REVISION)      # a concrete commit, not a branch
    assert lps.EMBED_DIM == 384
    assert lps.EMBED_DEVICE == "cpu"                              # never MPS (design §4)
    assert lps.EMBED_BATCH_SIZE >= 1
    assert lps.EMBED_NORMALIZE is True
    assert lps.EMBED_TORCH_THREADS == 1
    assert lps.COSINE_DECIMALS == 6


def test_theta_calibration_procedure_frozen():
    assert 0.0 < lps.THETA_GRID_START < lps.THETA_GRID_STOP <= 1.0
    assert 0.0 < lps.THETA_GRID_STEP < (lps.THETA_GRID_STOP - lps.THETA_GRID_START)
    assert lps.THETA_CRITERION == "cascade_membership_ari"
    assert lps.THETA_TIE_RULE == "smallest_window_then_largest_theta"
    assert lps.CANDIDATE_RULE == "strictly_earlier_round_within_window"
    assert lps.WINDOW_GRID == tuple(range(1, 20))
    assert lps.RECOVERY_THRESHOLD == 0.90
    assert lps.CALIBRATION_CONSTRUCTION_VERSION == 2
    assert "definition-#2 contract repair" in lps.CALIBRATION_AMENDMENT
    assert lps.RESAMPLING_RULE == "uniform_with_replacement_empirical_bootstrap"


def test_matching_gate_formulas_frozen_sample_size_only():
    # Formulas from sampling theory — the constants are scale factors, not fitted numbers.
    assert lps.MATCH_COUNTS_RULE == "exact_copy"
    assert lps.MATCH_LEN_KS_COEFF > 0.0
    assert 0.0 < lps.MATCH_EMBED_MEAN_COS_MIN < 1.0


def test_null_construction_frozen():
    assert lps.NULL_BASE_SEED == 20260717
    assert lps.NULL_STREAM_CONTENT == 0
    assert lps.WINDOW_ASSIGNMENT == "round_robin"
    # WINDOW_ORDER is the registered cohort, ascending — cross-file drift tripwire.
    assert lps.WINDOW_ORDER == hs.COHORT_SEEDS == (20260627, 20260628, 20260629)
    assert all(w >= 1.0 for w in lps.NULL_FANO_WINDOW_SIZES)      # >= 1 round: meaningful profile
    assert tuple(sorted(lps.NULL_FANO_WINDOW_SIZES)) == lps.NULL_FANO_WINDOW_SIZES


def test_band_constants_single_sourced_from_parrot_spec():
    # ACTIVATION of the dormant prototype constants — imported, never duplicated. Identity (is)
    # would be trivially true for interned ints; equality against parrot_spec AND the registered
    # values guards both the import wiring and the upstream values.
    assert lps.SWEEP_BAND_SEEDS == ps.SWEEP_BAND_SEEDS == 64
    assert lps.SWEEP_BAND_QUANTILE == ps.SWEEP_BAND_QUANTILE == 0.95
    assert lps.SWEEP_BAND_EDGE == ps.SWEEP_BAND_EDGE == "max"


def test_defined_not_evaluated_constants_present():
    # §9a/§9b exist as FROZEN criteria; the firewall test asserts nothing evaluates them here.
    assert 0.0 < lps.NULL_TAU_FRAC_MAX < 0.5
    assert isinstance(lps.N_EMIT_DEFINITION, str)
    for phrase in ("most-recent-prior REFRESH", "DISTINCT served items", "theta*",
                   "cross 1", "sub-inc 3"):
        assert phrase in lps.N_EMIT_DEFINITION


def test_following_post_count_registered_and_bound():
    # Registration (design §5): frozen at the sub-inc-1 effective value, and the driver passes it
    # EXPLICITLY to Platform so the constant binds, not the installed library default (textual
    # check in the test_task10_spec_freezes_present_and_sane tradition).
    assert hs.FOLLOWING_POST_COUNT == 3
    adapter_src = open(os.path.join(
        _REPO_ROOT, "src", "critaudit", "sim", "harness", "oasis_adapter.py")).read()
    assert "following_post_count=hs.FOLLOWING_POST_COUNT" in adapter_src


_DESIGN_DOC = os.path.join(_REPO_ROOT, *lps.DESIGN_DOC.split("/"))


@pytest.mark.skipif(not os.path.isfile(_DESIGN_DOC),
                    reason="design doc is an untracked working artifact; absent on fresh clones")
def test_design_doc_hash_pinned():
    """The design doc is untracked per repo convention (docs/superpowers/specs/ is gitignored);
    its content is pinned here so the committed record is tamper-evident. A ratified spec change
    updates BOTH the doc and this hash — loudly."""
    digest = hashlib.sha256(open(_DESIGN_DOC, "rb").read()).hexdigest()
    assert digest == lps.DESIGN_DOC_SHA256

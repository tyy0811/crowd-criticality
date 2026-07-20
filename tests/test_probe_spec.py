"""Frozen-surface guards for probe_spec (sub-inc-3 T2) — existence + range + cross-file
tripwires, in the test_parrot_spec_frozen_surface tradition. No value back-fill ever."""
import ast
import hashlib
import os
import re

import pytest

from critaudit.sim.controls import probe_spec as pspec
from critaudit.sim.controls import spec as cs

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_grid_frozen_sorted_and_contains_plants():
    g = pspec.EPS_GRID
    assert list(g) == sorted(set(g))                     # sorted, unique
    assert len(g) == 17
    for plant in (cs.EPS_LOW, cs.EPS_CRIT, cs.EPS_HIGH):
        assert plant in g                                # all three plants on the grid
    assert 0.0 < g[0] and g[-1] < 1.0


def test_fixed_drive_and_sensitivity_panel_disjoint():
    # The owner's confound correction: ONE drive across the primary grid; the panel never
    # coincides with the primary drive (it would measure nothing).
    assert pspec.MU_NEWS_PROBE == 0.4
    assert pspec.MU_NEWS_PROBE not in pspec.SENSITIVITY_MU_NEWS
    assert pspec.SENSITIVITY_EPS in pspec.EPS_GRID


def test_seed_design_frozen():
    assert pspec.SEED_PROBE == 20260720
    assert pspec.N_SEEDS == 12
    assert set(pspec.TRAIN_SEED_INDICES) | set(pspec.TEST_SEED_INDICES) == set(range(12))
    assert not set(pspec.TRAIN_SEED_INDICES) & set(pspec.TEST_SEED_INDICES)


def test_eligibility_and_equal_support_sane():
    assert 0.0 < pspec.T_BURN < cs.HORIZON - pspec.T_TAIL_GUARD
    assert pspec.T_TAIL_GUARD > 0.0
    # M_ELIGIBLE must sit far below the expected eligible count so a thin-run failure is a
    # real anomaly: expected = MU_NEWS_PROBE * (HORIZON - T_BURN - T_TAIL_GUARD).
    expected = pspec.MU_NEWS_PROBE * (cs.HORIZON - pspec.T_BURN - pspec.T_TAIL_GUARD)
    assert pspec.M_ELIGIBLE <= expected - 5 * expected ** 0.5
    assert pspec.USED_SEEDS_MIN == pspec.N_SEEDS         # exact-support design, not a floor
    assert pspec.USED_MARKERS_MIN == pspec.M_ELIGIBLE


def test_gate_constants_frozen():
    assert pspec.PEAK_RATIO_MIN == 2.0
    assert pspec.SEED_CONSISTENCY_MIN == 0.75
    assert pspec.N_RESP_TOL == 0.05
    assert pspec.N_RESP_ACCURACY_RANGE == (0.5, 0.9)
    assert pspec.N_RESP_BAND == (0.9, 1.0)
    assert pspec.MONOTONE_SE_MULT == 2.0
    assert pspec.EXPOSURE_NORMALIZATION == "none_mean_field_k_reach_constant"


def test_option_b_text_frozen_phrases():
    for phrase in ("UNRESOLVED at this substrate", "inconclusive-by-instrument",
                   "§10 deviation", "[reasons]", "does not run",
                   "retired-as-blocked"):
        assert phrase in pspec.OPTION_B_TEXT


def test_retirement_recorded_string_only():
    assert len(pspec.RETIRED_CRITERIA) == 2
    assert any("NULL_TAU_FRAC_MAX" in s and "RETIRED-AS-BLOCKED" in s
               for s in pspec.RETIRED_CRITERIA)
    assert any("N_EMIT_DEFINITION" in s for s in pspec.RETIRED_CRITERIA)


def test_pilot_construction_frozen():
    assert pspec.PILOT_INJECTION_ROUNDS == (2, 4, 6, 8, 10)
    assert pspec.PILOT_MARKER_POOL_INDICES == (0, 1, 2, 3, 4)
    assert 1 <= pspec.PILOT_MIN_EXPOSED_MARKERS <= len(pspec.PILOT_INJECTION_ROUNDS)
    assert pspec.PILOT_MIN_TOTAL_EXPOSURES >= pspec.PILOT_MIN_EXPOSED_MARKERS


def test_probe_spec_imports_no_subinc2_surface():
    # R8 firewall direction 1: probe_spec must not import llm_parrot_spec/cohort_marginals
    # (string-only retirement), or it would join the sub-inc-2 self-discovering scan set.
    src = open(os.path.join(_REPO, "src", "critaudit", "sim", "controls", "probe_spec.py")).read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        refs = []
        if isinstance(node, ast.Import):
            refs = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            refs = [node.module or ""] + [a.name for a in node.names]
        assert not any(("llm_parrot" in r) or ("cohort_marginals" in r) for r in refs if r)


_DESIGN = os.path.join(_REPO, *pspec.DESIGN_DOC.split("/"))


@pytest.mark.skipif(not os.path.isfile(_DESIGN),
                    reason="design note is an untracked working artifact; absent on fresh clones")
def test_design_doc_hash_pinned():
    digest = hashlib.sha256(open(_DESIGN, "rb").read()).hexdigest()
    assert digest == pspec.DESIGN_DOC_SHA256

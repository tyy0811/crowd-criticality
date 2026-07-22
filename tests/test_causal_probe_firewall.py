"""Causal-probe structural firewalls (plan Task 6).

Three layers: (1) AST import firewalls — no causal module may import similarity,
powerlaw, Hawkes fitters, the parrot calibration surface, or reference `n_resp`,
and the estimator's import surface is pinned to the frozen record/validator
modules; (2) manifest/seed disjointness guards power-checked field by field;
(3) strict fail-closed validator checks that must hold under BOTH normal Python
and `python -O` (no scientific guard may live in a strippable `assert`)."""

from __future__ import annotations

import ast
from dataclasses import replace
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_ROUND_OFFSET,
    MARKER_SEED_STREAM,
    MARKER_SEEDS,
    MarkerManifest,
    require_disjoint_manifests,
    require_disjoint_seed_sets,
)
from critaudit.sim.harness.causal_probe import estimate_r_reply
from critaudit.sim.harness.causal_probe_records import (
    Assignment,
    CandidatePair,
    Outcome,
    ParentEligibility,
    ProbeManifest,
    SamplingFrame,
    StratumDraw,
)
from critaudit.sim.harness.causal_probe_validation import (
    validate_assignments,
    validate_outcomes,
    validate_sampling_frame,
)
from critaudit.sim.harness.causal_refresh import CausalRefreshController

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- layer 1: AST import firewalls -------------------------------------------------------------

_CAUSAL_MODULES = [
    "src/critaudit/sim/harness/causal_probe_spec.py",
    "src/critaudit/sim/harness/causal_probe_records.py",
    "src/critaudit/sim/harness/causal_probe_validation.py",
    "src/critaudit/sim/harness/causal_probe.py",
    "src/critaudit/sim/harness/causal_refresh.py",
    "src/critaudit/sim/controls/causal_probe_control.py",
    "src/critaudit/sim/controls/causal_probe_marker_control.py",
]
_OPTIONAL_CAUSAL_MODULES = [
    "src/critaudit/experiments/causal_probe_power.py",
    "src/critaudit/experiments/causal_probe_recoverability.py",
]

_FORBIDDEN_MODULE_PREFIXES = (
    "critaudit.powerlaw",
    "critaudit.hawkes",
    "critaudit.scaling",
    "critaudit.cascades.similarity",
)
_FORBIDDEN_MODULE_TOKENS = ("similarity", "parrot")
_FORBIDDEN_NAMES = {"n_resp", "fit_powerlaw", "attribute_similarity_parents"}


def _names_and_imports(path):
    with open(os.path.join(_REPO, path)) as handle:
        tree = ast.parse(handle.read(), filename=path)
    imports, names = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return imports, names


def _causal_scan_targets():
    return _CAUSAL_MODULES + [
        path for path in _OPTIONAL_CAUSAL_MODULES
        if os.path.isfile(os.path.join(_REPO, path))
    ]


def test_causal_modules_clean_of_fitting_and_calibration_stack():
    for path in _causal_scan_targets():
        imports, names = _names_and_imports(path)
        for module in imports:
            assert not any(
                module == prefix or module.startswith(prefix + ".")
                for prefix in _FORBIDDEN_MODULE_PREFIXES
            ), f"{path} imports embargoed module {module!r}"
            assert not any(token in module for token in _FORBIDDEN_MODULE_TOKENS), \
                f"{path} imports embargoed surface {module!r}"
        hit = names & _FORBIDDEN_NAMES
        assert not hit, f"{path} references embargoed symbol(s) {sorted(hit)}"


def test_estimator_import_surface_is_pinned():
    """The estimator consumes ONLY the frozen records, validators, spec, and math."""
    path = os.path.join(_REPO, "src/critaudit/sim/harness/causal_probe.py")
    with open(path) as handle:
        tree = ast.parse(handle.read(), filename=path)
    allowed_from = {
        "__future__",
        "causal_probe_records",
        "causal_probe_spec",
        "causal_probe_validation",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert {alias.name for alias in node.names} <= {"math"}, \
                f"estimator imports beyond math: {ast.dump(node)}"
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[-1]
            assert module in allowed_from, \
                f"estimator imports from unexpected module {node.module!r}"


def test_import_scanner_has_power_on_known_violators():
    imports, _ = _names_and_imports("src/critaudit/sim/controls/llm_parrot.py")
    assert any("similarity" in module for module in imports)
    _, names = _names_and_imports("src/critaudit/sim/controls/probe_gate.py")
    assert "n_resp" in names


# --- shared record fixtures --------------------------------------------------------------------


def _frame():
    return SamplingFrame(
        frame_id="frame:firewall",
        parent_records=(
            ParentEligibility("post:1", author_agent_id=10, created_round=2),
            ParentEligibility("post:2", author_agent_id=11, created_round=3),
        ),
        excluded_recipient_agent_ids=(10, 11, 99),
        candidate_pairs=(
            CandidatePair(
                pair_id="pair:1", parent_item_id="post:1", agent_id=20, round_id=3,
                stratum_id="agent:20:round:3", selection_probability=0.4,
                treatment_probability=0.5, parent_first_readable_round=3,
                prior_exposure_count=0, complete_same_action_opportunity=True),
            CandidatePair(
                pair_id="pair:2", parent_item_id="post:2", agent_id=21, round_id=4,
                stratum_id="agent:21:round:4", selection_probability=0.5,
                treatment_probability=0.5, parent_first_readable_round=4,
                prior_exposure_count=0, complete_same_action_opportunity=True),
        ),
    )


def _draws(select_second=False):
    return (
        StratumDraw("frame:firewall", "agent:20:round:3", "pair:1"),
        StratumDraw(
            "frame:firewall", "agent:21:round:4", "pair:2" if select_second else None),
    )


def _assignment(pair_id="pair:1", filler="post:9", treated=True):
    return Assignment(
        assignment_id=f"assignment:{pair_id}", frame_id="frame:firewall",
        pair_id=pair_id, filler_item_id=filler, treated=treated)


def _outcome(assignment_id="assignment:pair:1", child="comment:1", author=20, round_id=3):
    return Outcome(
        assignment_id=assignment_id, parent_served=True,
        parent_seen_in_background=False, feed_length_before=3, feed_length_after=3,
        direct_child_item_id=child,
        direct_child_parent_id="post:1" if child else None,
        child_author_agent_id=author if child else None,
        child_round=round_id if child else None)


# --- layer 2: disjointness guards --------------------------------------------------------------


def _reply_manifest(**overrides):
    values = dict(
        run_id="run:reply:1",
        frame_id="frame:reply:1",
        seed_stream_id="control:scripted",
        raw_seed=7,
        root_ids=("post:1", "post:2"),
        round_ids=(0, 1),
        event_ids=("post:1", "post:2", "comment:1"),
        pair_ids=("pair:1:1", "pair:1:2"),
        assignment_ids=("assignment:pair:1:1",),
    )
    values.update(overrides)
    return ProbeManifest(**values)


def _marker_manifest(**overrides):
    values = dict(
        run_id="run:marker:1",
        frame_id="frame:marker:1",
        seed_stream_id=MARKER_SEED_STREAM,
        raw_seed=MARKER_SEEDS[0],
        plant_r=0.97,
        response_probability=0.2425,
        root_count=2,
        opportunities_per_parent=4,
        rounds=3,
        root_ids=("marker:post:1", "marker:post:2"),
        round_ids=(MARKER_ROUND_OFFSET, MARKER_ROUND_OFFSET + 1, MARKER_ROUND_OFFSET + 2),
        event_ids=("marker:post:1", "marker:post:2", "marker:post:3"),
        pair_ids=("marker-pair:post:1:0",),
        assignment_ids=("marker-assignment:post:3",),
        support_per_root=(4, 4),
    )
    values.update(overrides)
    return MarkerManifest(**values)


def test_disjoint_manifests_pass_on_the_clean_fixture():
    require_disjoint_manifests(_reply_manifest(), _marker_manifest())


@pytest.mark.parametrize(
    ("field", "overlap"),
    [
        ("run_id", "run:reply:1"),
        ("frame_id", "frame:reply:1"),
        ("seed_stream_id", "control:scripted"),
        ("raw_seed", 7),
        ("root_ids", ("marker:post:1", "post:1")),
        ("round_ids", (0, MARKER_ROUND_OFFSET)),
        ("event_ids", ("marker:post:1", "comment:1")),
        ("pair_ids", ("marker-pair:post:1:0", "pair:1:1")),
        ("assignment_ids", ("assignment:pair:1:1",)),
    ],
)
def test_disjoint_manifests_power_check_every_field(field, overlap):
    tainted = _marker_manifest(**{field: overlap})
    with pytest.raises(ValueError, match=field):
        require_disjoint_manifests(_reply_manifest(), tainted)


def test_require_disjoint_seed_sets():
    require_disjoint_seed_sets((1, 2), (3, 4), (5,))
    require_disjoint_seed_sets()
    with pytest.raises(ValueError, match="overlap"):
        require_disjoint_seed_sets((1, 2), (2, 3))
    with pytest.raises(ValueError, match="overlap"):
        require_disjoint_seed_sets((1, 2), (3, 4), (4, 5))


# --- known violators ---------------------------------------------------------------------------


def test_dropped_no_selection_draw_fails_closed():
    with pytest.raises(ValueError, match="stratum"):
        estimate_r_reply(
            _frame(), (_draws()[0],), (_assignment(),), (_outcome(),))


def _controller(frame):
    class _Stream:
        def random(self):
            return 0.99

    return CausalRefreshController(
        frame, _Stream(), _Stream(),
        parent_posts={"post:1": {"post_id": 1, "user_id": 10},
                      "post:2": {"post_id": 2, "user_id": 11}},
        filler_posts={"post:1": {"post_id": 8, "user_id": 12},
                      "post:2": {"post_id": 9, "user_id": 12}})


def test_dynamically_added_pair_fails_closed():
    frame = _frame()
    controller = _controller(frame)
    smuggled = replace(frame.candidate_pairs[0], pair_id="pair:smuggled",
                       stratum_id="agent:20:round:9", round_id=9,
                       parent_first_readable_round=9)
    object.__setattr__(frame, "candidate_pairs", frame.candidate_pairs + (smuggled,))
    with pytest.raises(ValueError, match="frame content changed"):
        controller.refresh(20, 3, ({"post_id": 5},))


def test_changed_frame_hash_fails_closed():
    frame = _frame()
    controller = _controller(frame)
    object.__setattr__(frame, "frame_id", "frame:tampered")
    with pytest.raises(ValueError, match="frame content changed"):
        controller.refresh(20, 3, ({"post_id": 5},))


def test_denominator_is_never_reconstructed_from_observed_assignments():
    estimate = estimate_r_reply(_frame(), _draws(), (_assignment(),), (_outcome(),))
    assert estimate.parent_count == 2          # complete frame registry
    assert estimate.candidate_pair_count == 2  # complete candidate ledger
    assert estimate.treated_count == 1         # only one realized assignment


def test_duplicate_native_child_fails_closed():
    draws = _draws(select_second=True)
    assignments = (_assignment(), _assignment("pair:2", filler="post:8"))
    outcomes = (
        _outcome(),
        Outcome(
            assignment_id="assignment:pair:2", parent_served=True,
            parent_seen_in_background=False, feed_length_before=3,
            feed_length_after=3, direct_child_item_id="comment:1",
            direct_child_parent_id="post:2", child_author_agent_id=21,
            child_round=4),
    )
    with pytest.raises(ValueError, match="unique"):
        validate_outcomes(_frame(), draws, assignments, outcomes)


# --- layer 3: strict fail-closed under normal Python AND python -O -----------------------------


def _strict_cases():
    frame = _frame()
    draws = _draws()
    assignments = (_assignment(),)
    outcomes = (_outcome(),)
    return (
        ("exposure_leakage", lambda: validate_outcomes(
            frame, draws, assignments,
            (replace(outcomes[0], parent_seen_in_background=True),))),
        ("fake_duck_typed_record", lambda: validate_assignments(
            frame, draws,
            (SimpleNamespace(
                assignment_id="assignment:pair:1", frame_id="frame:firewall",
                pair_id="pair:1", filler_item_id="post:9", treated=True),))),
        ("bool_as_int_field", lambda: validate_sampling_frame(
            replace(frame, candidate_pairs=(
                replace(frame.candidate_pairs[0], agent_id=True),)
                + frame.candidate_pairs[1:]))),
        ("invalid_probability", lambda: validate_sampling_frame(
            replace(frame, candidate_pairs=(
                replace(frame.candidate_pairs[0], selection_probability=1.5),)
                + frame.candidate_pairs[1:]))),
        ("treatment_probability_not_half", lambda: validate_sampling_frame(
            replace(frame, candidate_pairs=(
                replace(frame.candidate_pairs[0], treatment_probability=0.6),)
                + frame.candidate_pairs[1:]))),
        ("parent_equals_filler", lambda: validate_assignments(
            frame, draws, (replace(assignments[0], filler_item_id="post:1"),))),
        ("child_author_mismatch", lambda: validate_outcomes(
            frame, draws, assignments,
            (replace(outcomes[0], child_author_agent_id=21),))),
        ("incomplete_relationships", lambda: validate_outcomes(
            frame, draws, assignments, ())),
    )


def run_strict_violators():
    """Every violator must raise, with NO reliance on strippable assert statements.
    Returns the number of cases checked; raises SystemExit naming any violator
    that slipped through."""
    checked = 0
    for name, case in _strict_cases():
        try:
            case()
        except (ValueError, TypeError):
            checked += 1
            continue
        raise SystemExit(f"strict violator {name!r} passed validation (fail-open)")
    return checked


def test_strict_violators_raise_under_normal_python():
    assert run_strict_violators() == 8


def test_strict_violators_raise_under_python_O():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        (os.path.join(_REPO, "src"), os.path.join(_REPO, "tests")))
    completed = subprocess.run(
        [sys.executable, "-O", "-c",
         "import test_causal_probe_firewall as firewall; "
         "raise SystemExit(0 if firewall.run_strict_violators() == 8 else 1)"],
        env=env, capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr

from __future__ import annotations

import dataclasses
import math

import pytest

from critaudit.sim.controls.causal_probe_control import (
    CONTROL_SEED_STREAM,
    ControlTruth,
    PotentialResponse,
    ScriptedControlRun,
    ScriptedReply,
    build_scripted_control_frame,
    control_probe_rngs,
    run_scripted_oasis_control,
    scripted_action_for_assignment,
)
from critaudit.sim.harness.causal_probe_records import (
    Assignment,
    ProbeManifest,
    sampling_frame_sha256,
    sampling_frame_to_bytes,
)
from critaudit.sim.harness.causal_probe_validation import validate_sampling_frame


def _build(parent_count=2, recipients_per_parent=2, plant_r=1.0, seed=7):
    return build_scripted_control_frame(
        parent_count=parent_count,
        recipients_per_parent=recipients_per_parent,
        plant_r=plant_r,
        seed=seed,
    )


# --- pure frame builder and planted truth -----------------------------------------------------


def test_scripted_control_frame_is_valid_and_deterministic():
    frame_a, truth_a = _build()
    frame_b, truth_b = _build()
    validate_sampling_frame(frame_a)
    assert frame_a == frame_b
    assert truth_a == truth_b
    assert type(truth_a) is ControlTruth
    assert truth_a.frame_id == frame_a.frame_id
    assert len(frame_a.parent_records) == 2
    assert len(frame_a.candidate_pairs) == 4
    # one pair per stratum, certain selection, frozen treatment probability
    strata = [pair.stratum_id for pair in frame_a.candidate_pairs]
    assert len(set(strata)) == len(strata)
    assert all(pair.selection_probability == 1.0 for pair in frame_a.candidate_pairs)
    assert all(pair.treatment_probability == 0.5 for pair in frame_a.candidate_pairs)
    assert all(pair.round_id == 1 for pair in frame_a.candidate_pairs)
    assert all(
        parent.created_round == 0 for parent in frame_a.parent_records
    )


def test_layout_excludes_authors_filler_author_and_news_user():
    frame, _ = _build(parent_count=2, recipients_per_parent=2)
    # authors 0..1, recipients 2..5, filler author 6, news user 7
    assert frame.excluded_recipient_agent_ids == (0, 1, 6, 7)
    assert {pair.agent_id for pair in frame.candidate_pairs} == {2, 3, 4, 5}
    assert [parent.parent_item_id for parent in frame.parent_records] == [
        "post:1",
        "post:2",
    ]


def test_potential_responses_are_fixed_per_pair_with_registered_q():
    frame, truth = _build(plant_r=1.0)
    assert len(truth.potential_responses) == len(frame.candidate_pairs)
    assert [row.pair_id for row in truth.potential_responses] == [
        pair.pair_id for pair in frame.candidate_pairs
    ]
    assert all(row.response_probability == 0.5 for row in truth.potential_responses)
    assert all(type(row.potential_response) is bool for row in truth.potential_responses)


def test_r_plant_and_r_gen_frame_definitions_hold():
    frame, truth = _build(parent_count=3, recipients_per_parent=4, plant_r=2.0, seed=11)
    # R_plant = mean over parents of the summed registered q
    assert truth.r_plant == pytest.approx(2.0)
    # hidden R_gen_frame = mean over parents of the summed fixed potential responses
    y_by_parent = {}
    pair_parent = {pair.pair_id: pair.parent_item_id for pair in frame.candidate_pairs}
    for row in truth.potential_responses:
        parent = pair_parent[row.pair_id]
        y_by_parent[parent] = y_by_parent.get(parent, 0) + int(row.potential_response)
    expected = math.fsum(y_by_parent.get(p.parent_item_id, 0) for p in frame.parent_records)
    expected /= len(frame.parent_records)
    assert truth.r_gen_frame == pytest.approx(expected)


def test_degenerate_probabilities_pin_potential_responses():
    _, all_on = _build(parent_count=2, recipients_per_parent=2, plant_r=2.0, seed=3)
    assert all(row.potential_response is True for row in all_on.potential_responses)
    assert all_on.r_gen_frame == pytest.approx(2.0)
    _, all_off = _build(parent_count=2, recipients_per_parent=2, plant_r=0.0, seed=3)
    assert all(row.potential_response is False for row in all_off.potential_responses)
    assert all_off.r_gen_frame == 0.0


def test_out_of_range_response_probability_fails_closed():
    with pytest.raises(ValueError, match="response_probability"):
        _build(recipients_per_parent=2, plant_r=2.5)
    with pytest.raises(ValueError, match="response_probability"):
        _build(plant_r=-0.1)


def test_seeds_vary_only_the_response_stream():
    frame_a, truth_a = _build(parent_count=8, recipients_per_parent=4, plant_r=2.0, seed=1)
    frame_b, truth_b = _build(parent_count=8, recipients_per_parent=4, plant_r=2.0, seed=2)
    assert frame_a.candidate_pairs == frame_b.candidate_pairs
    assert frame_a.parent_records == frame_b.parent_records
    assert frame_a.frame_id != frame_b.frame_id
    assert [row.potential_response for row in truth_a.potential_responses] != [
        row.potential_response for row in truth_b.potential_responses
    ]


def test_records_are_immutable():
    _, truth = _build()
    with pytest.raises(dataclasses.FrozenInstanceError):
        truth.r_plant = 9.9
    with pytest.raises(dataclasses.FrozenInstanceError):
        truth.potential_responses[0].potential_response = True


# --- scripted response policy -----------------------------------------------------------------


def _assignment(pair_id, treated):
    return Assignment(
        assignment_id=f"assignment:{pair_id}",
        frame_id="frame:scripted-control:7",
        pair_id=pair_id,
        filler_item_id="post:3",
        treated=treated,
    )


def test_policy_replies_only_when_treated_and_potentially_responsive():
    frame, truth = _build()
    responsive = [row for row in truth.potential_responses if row.potential_response]
    unresponsive = [row for row in truth.potential_responses if not row.potential_response]
    if responsive:
        action = scripted_action_for_assignment(
            _assignment(responsive[0].pair_id, treated=True), truth
        )
        assert type(action) is ScriptedReply
        assert action.pair_id == responsive[0].pair_id
        # a holdout never replies, even with a live potential response
        assert scripted_action_for_assignment(
            _assignment(responsive[0].pair_id, treated=False), truth
        ) is None
    if unresponsive:
        assert scripted_action_for_assignment(
            _assignment(unresponsive[0].pair_id, treated=True), truth
        ) is None


def test_policy_rejects_unknown_pairs():
    _, truth = _build()
    with pytest.raises(ValueError, match="pair"):
        scripted_action_for_assignment(_assignment("pair:9:9", treated=True), truth)


def test_control_rng_namespace_is_frozen():
    selection_a, treatment_a = control_probe_rngs(CONTROL_SEED_STREAM, 5)
    selection_b, treatment_b = control_probe_rngs(CONTROL_SEED_STREAM, 5)
    seq_a = [selection_a.random() for _ in range(3)]
    assert seq_a == [selection_b.random() for _ in range(3)]
    assert [treatment_a.random() for _ in range(3)] == [
        treatment_b.random() for _ in range(3)
    ]
    with pytest.raises(ValueError, match="seed stream"):
        control_probe_rngs("control:relabelled", 5)


# --- installed-OASIS non-LLM bridge -----------------------------------------------------------


def test_scripted_oasis_control_bridge(tmp_path):
    pytest.importorskip("oasis")

    frame, truth = _build(parent_count=2, recipients_per_parent=2, plant_r=1.0, seed=7)
    pre_bytes = sampling_frame_to_bytes(frame)
    pre_sha = sampling_frame_sha256(frame)

    run = run_scripted_oasis_control(
        frame,
        truth,
        run_id="run:control:1",
        seed_stream_id=CONTROL_SEED_STREAM,
        seed=7,
        database_path=str(tmp_path / "control_a.db"),
    )
    assert type(run) is ScriptedControlRun

    # frame and evidence are hash-verified before the first draw
    assert run.frame_bytes == pre_bytes
    assert run.frame_sha256 == pre_sha
    assert run.eligibility_evidence_bytes
    assert run.eligibility_evidence_sha256

    manifest = run.manifest
    assert type(manifest) is ProbeManifest
    assert manifest.run_id == "run:control:1"
    assert manifest.frame_id == frame.frame_id
    assert manifest.seed_stream_id == CONTROL_SEED_STREAM
    assert manifest.raw_seed == 7
    assert manifest.root_ids == ("post:1", "post:2")
    assert manifest.round_ids == (0, 1)
    assert manifest.pair_ids == tuple(p.pair_id for p in frame.candidate_pairs)
    assert manifest.assignment_ids == tuple(
        a.assignment_id for a in run.assignments
    )

    # every stratum draws; certain selection realizes one assignment per stratum
    assert len(run.draws) == 4
    assert all(draw.selected_pair_id is not None for draw in run.draws)
    assert len(run.assignments) == 4
    assert len(run.outcomes) == 4

    # native links realize exactly the treated live potential responses
    truth_by_pair = {row.pair_id: row for row in truth.potential_responses}
    outcomes_by_assignment = {o.assignment_id: o for o in run.outcomes}
    expected_children = 0
    for assignment in run.assignments:
        outcome = outcomes_by_assignment[assignment.assignment_id]
        should_reply = (
            assignment.treated
            and truth_by_pair[assignment.pair_id].potential_response
        )
        expected_children += int(should_reply)
        if should_reply:
            assert outcome.direct_child_item_id is not None
            assert outcome.direct_child_parent_id is not None
            assert outcome.child_round == 1
        else:
            assert outcome.direct_child_item_id is None

    # emitted children never enter the fixed R_reply frame
    parent_ids = {p.parent_item_id for p in frame.parent_records}
    child_ids = {
        o.direct_child_item_id for o in run.outcomes if o.direct_child_item_id
    }
    assert child_ids.isdisjoint(parent_ids)
    assert child_ids <= set(manifest.event_ids)

    # the estimator result matches the exported ledger
    from critaudit.sim.harness.causal_probe import estimate_r_reply

    estimate = estimate_r_reply(frame, run.draws, run.assignments, run.outcomes)
    assert estimate.status == "design_only"
    assert estimate.response_count == expected_children
    assert estimate.parent_count == 2

    # byte-determinism: an identical seed reproduces the complete ledger
    rerun = run_scripted_oasis_control(
        frame,
        truth,
        run_id="run:control:1",
        seed_stream_id=CONTROL_SEED_STREAM,
        seed=7,
        database_path=str(tmp_path / "control_b.db"),
    )
    assert rerun == run

    # relabeled seed streams are rejected
    with pytest.raises(ValueError, match="seed stream"):
        run_scripted_oasis_control(
            frame,
            truth,
            run_id="run:control:2",
            seed_stream_id="control:relabelled",
            seed=7,
            database_path=str(tmp_path / "control_c.db"),
        )

    # banked-evidence enforcement (review F1): the correct hash passes; a wrong
    # hash fails closed BEFORE the first draw (no refresh trace row is written)
    import sqlite3

    replay = run_scripted_oasis_control(
        frame, truth, run_id="run:control:1",
        seed_stream_id=CONTROL_SEED_STREAM, seed=7,
        database_path=str(tmp_path / "control_d.db"),
        expected_evidence_sha256=run.eligibility_evidence_sha256,
    )
    assert replay.eligibility_evidence_sha256 == run.eligibility_evidence_sha256
    with pytest.raises(ValueError, match="BEFORE the first draw"):
        run_scripted_oasis_control(
            frame, truth, run_id="run:control:3",
            seed_stream_id=CONTROL_SEED_STREAM, seed=7,
            database_path=str(tmp_path / "control_e.db"),
            expected_evidence_sha256="0" * 64,
        )
    con = sqlite3.connect(str(tmp_path / "control_e.db"))
    assert con.execute(
        "SELECT COUNT(*) FROM trace WHERE action = 'refresh'").fetchone()[0] == 0
    con.close()

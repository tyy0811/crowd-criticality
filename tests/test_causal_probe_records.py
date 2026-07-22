from dataclasses import FrozenInstanceError, fields

import pytest

from critaudit.sim.harness import causal_probe_records as records


def _frame() -> records.SamplingFrame:
    return records.SamplingFrame(
        frame_id="frame:1",
        parent_records=(
            records.ParentEligibility(
                parent_item_id="post:1",
                author_agent_id=7,
                created_round=2,
            ),
        ),
        excluded_recipient_agent_ids=(7, 99),
        candidate_pairs=(
            records.CandidatePair(
                pair_id="pair:1",
                parent_item_id="post:1",
                agent_id=8,
                round_id=3,
                stratum_id="round:3",
                selection_probability=0.25,
                treatment_probability=0.5,
                parent_first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )


def _evidence() -> records.FrameEligibilityEvidence:
    return records.FrameEligibilityEvidence(
        frame_id="frame:1",
        news_user_agent_id=99,
        pair_evidence=(
            records.PairEligibilityEvidence(
                pair_id="pair:1",
                parent_author_agent_id=7,
                parent_created_round=2,
                first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )


def test_exact_public_surface_is_frozen():
    assert type(records.__all__) is tuple
    assert records.__all__ == (
        "ParentEligibility",
        "CandidatePair",
        "SamplingFrame",
        "PairEligibilityEvidence",
        "FrameEligibilityEvidence",
        "StratumDraw",
        "Assignment",
        "Outcome",
        "ProbeManifest",
        "RReplyEstimate",
        "sampling_frame_to_bytes",
        "sampling_frame_sha256",
        "frame_eligibility_evidence_to_bytes",
        "frame_eligibility_evidence_sha256",
    )


@pytest.mark.parametrize(
    ("record_type", "expected_fields"),
    [
        (
            records.ParentEligibility,
            ("parent_item_id", "author_agent_id", "created_round"),
        ),
        (
            records.CandidatePair,
            (
                "pair_id",
                "parent_item_id",
                "agent_id",
                "round_id",
                "stratum_id",
                "selection_probability",
                "treatment_probability",
                "parent_first_readable_round",
                "prior_exposure_count",
                "complete_same_action_opportunity",
            ),
        ),
        (
            records.SamplingFrame,
            (
                "frame_id",
                "parent_records",
                "excluded_recipient_agent_ids",
                "candidate_pairs",
            ),
        ),
        (
            records.PairEligibilityEvidence,
            (
                "pair_id",
                "parent_author_agent_id",
                "parent_created_round",
                "first_readable_round",
                "prior_exposure_count",
                "complete_same_action_opportunity",
            ),
        ),
        (
            records.FrameEligibilityEvidence,
            ("frame_id", "news_user_agent_id", "pair_evidence"),
        ),
        (
            records.StratumDraw,
            ("frame_id", "stratum_id", "selected_pair_id"),
        ),
        (
            records.Assignment,
            ("assignment_id", "frame_id", "pair_id", "filler_item_id", "treated"),
        ),
        (
            records.Outcome,
            (
                "assignment_id",
                "parent_served",
                "parent_seen_in_background",
                "feed_length_before",
                "feed_length_after",
                "direct_child_item_id",
                "direct_child_parent_id",
                "child_author_agent_id",
                "child_round",
            ),
        ),
        (
            records.ProbeManifest,
            (
                "run_id",
                "frame_id",
                "seed_stream_id",
                "raw_seed",
                "root_ids",
                "round_ids",
                "event_ids",
                "pair_ids",
                "assignment_ids",
            ),
        ),
        (
            records.RReplyEstimate,
            (
                "frame_id",
                "estimate",
                "estimated_diagonal_variance_bound",
                "standard_error_conservative",
                "ci95_low",
                "ci95_high",
                "deterministic_worst_case_variance_bound",
                "parent_count",
                "candidate_pair_count",
                "stratum_count",
                "draw_count",
                "selected_count",
                "no_selection_count",
                "treated_count",
                "control_count",
                "response_count",
                "status",
            ),
        ),
    ],
)
def test_record_field_order_and_immutability_are_frozen(record_type, expected_fields):
    assert tuple(field.name for field in fields(record_type)) == expected_fields
    assert record_type.__dataclass_params__.frozen is True


def test_record_instances_reject_mutation():
    frame = _frame()

    with pytest.raises(FrozenInstanceError):
        frame.frame_id = "frame:changed"


def test_sampling_frame_canonical_bytes_and_digest_are_pinned():
    expected = (
        b'{"candidate_pairs":[{"agent_id":8,'
        b'"complete_same_action_opportunity":true,"pair_id":"pair:1",'
        b'"parent_first_readable_round":3,"parent_item_id":"post:1",'
        b'"prior_exposure_count":0,"round_id":3,"selection_probability":0.25,'
        b'"stratum_id":"round:3","treatment_probability":0.5}],'
        b'"excluded_recipient_agent_ids":[7,99],"frame_id":"frame:1",'
        b'"parent_records":[{"author_agent_id":7,"created_round":2,'
        b'"parent_item_id":"post:1"}]}\n'
    )

    assert records.sampling_frame_to_bytes(_frame()) == expected
    assert (
        records.sampling_frame_sha256(_frame())
        == "20d43e6e5854fb541288b63e5b4f0f48dfb5f3b7cc9cacc333ec1d07d8a4873c"
    )


def test_frame_evidence_canonical_bytes_and_digest_are_pinned():
    expected = (
        b'{"frame_id":"frame:1","news_user_agent_id":99,'
        b'"pair_evidence":[{"complete_same_action_opportunity":true,'
        b'"first_readable_round":3,"pair_id":"pair:1",'
        b'"parent_author_agent_id":7,"parent_created_round":2,'
        b'"prior_exposure_count":0}]}\n'
    )

    assert records.frame_eligibility_evidence_to_bytes(_evidence()) == expected
    assert (
        records.frame_eligibility_evidence_sha256(_evidence())
        == "8fb414840acdd9ac66df31aee083060388014d7a3f32755b47e8e48f3778f07d"
    )


@pytest.mark.parametrize(
    "function",
    [records.sampling_frame_to_bytes, records.sampling_frame_sha256],
)
def test_sampling_frame_serializers_require_exact_record_type(function):
    with pytest.raises(TypeError, match="SamplingFrame"):
        function(_evidence())

    class SamplingFrameSubclass(records.SamplingFrame):
        pass

    with pytest.raises(TypeError, match="SamplingFrame"):
        function(
            SamplingFrameSubclass(
                **_frame().__dict__,
            )
        )


@pytest.mark.parametrize(
    "function",
    [
        records.frame_eligibility_evidence_to_bytes,
        records.frame_eligibility_evidence_sha256,
    ],
)
def test_frame_evidence_serializers_require_exact_record_type(function):
    with pytest.raises(TypeError, match="FrameEligibilityEvidence"):
        function(_frame())


def test_sampling_frame_serialization_rejects_nonfinite_numbers():
    frame = _frame()
    invalid_pair = records.CandidatePair(
        **{**frame.candidate_pairs[0].__dict__, "selection_probability": float("nan")}
    )
    invalid_frame = records.SamplingFrame(
        **{**frame.__dict__, "candidate_pairs": (invalid_pair,)}
    )

    with pytest.raises(ValueError, match="Out of range float values"):
        records.sampling_frame_to_bytes(invalid_frame)


def test_canonical_json_is_encoded_as_utf8_not_ascii_escapes():
    frame = records.SamplingFrame(
        **{**_frame().__dict__, "frame_id": "främe:1"}
    )

    assert b'"frame_id":"fr\xc3\xa4me:1"' in records.sampling_frame_to_bytes(frame)

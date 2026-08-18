from dataclasses import replace
import math

import pytest

from critaudit.sim.harness.causal_probe_records import (
    Assignment,
    CandidatePair,
    FrameEligibilityEvidence,
    Outcome,
    PairEligibilityEvidence,
    ParentEligibility,
    SamplingFrame,
    StratumDraw,
)
from critaudit.sim.harness.causal_probe_validation import (
    validate_assignments,
    validate_frame_provenance,
    validate_outcomes,
    validate_sampling_frame,
    validate_stratum_draws,
)


def _frame() -> SamplingFrame:
    return SamplingFrame(
        frame_id="frame:1",
        parent_records=(
            ParentEligibility(
                parent_item_id="parent:1",
                author_agent_id=10,
                created_round=1,
            ),
            ParentEligibility(
                parent_item_id="parent:2",
                author_agent_id=11,
                created_round=2,
            ),
        ),
        excluded_recipient_agent_ids=(10, 11, 99),
        candidate_pairs=(
            CandidatePair(
                pair_id="pair:1",
                parent_item_id="parent:1",
                agent_id=20,
                round_id=3,
                stratum_id="agent:20:round:3",
                selection_probability=0.4,
                treatment_probability=0.5,
                parent_first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            CandidatePair(
                pair_id="pair:2",
                parent_item_id="parent:2",
                agent_id=20,
                round_id=3,
                stratum_id="agent:20:round:3",
                selection_probability=0.4,
                treatment_probability=0.5,
                parent_first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            CandidatePair(
                pair_id="pair:3",
                parent_item_id="parent:1",
                agent_id=21,
                round_id=4,
                stratum_id="agent:21:round:4",
                selection_probability=0.5,
                treatment_probability=0.5,
                parent_first_readable_round=4,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )


def _evidence() -> FrameEligibilityEvidence:
    return FrameEligibilityEvidence(
        frame_id="frame:1",
        news_user_agent_id=99,
        pair_evidence=(
            PairEligibilityEvidence(
                pair_id="pair:1",
                parent_author_agent_id=10,
                parent_created_round=1,
                first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            PairEligibilityEvidence(
                pair_id="pair:2",
                parent_author_agent_id=11,
                parent_created_round=2,
                first_readable_round=3,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
            PairEligibilityEvidence(
                pair_id="pair:3",
                parent_author_agent_id=10,
                parent_created_round=1,
                first_readable_round=4,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )


def _draws() -> tuple[StratumDraw, ...]:
    return (
        StratumDraw(
            frame_id="frame:1",
            stratum_id="agent:20:round:3",
            selected_pair_id="pair:1",
        ),
        StratumDraw(
            frame_id="frame:1",
            stratum_id="agent:21:round:4",
            selected_pair_id=None,
        ),
    )


def _assignments(*, treated: bool = True) -> tuple[Assignment, ...]:
    return (
        Assignment(
            assignment_id="assignment:1",
            frame_id="frame:1",
            pair_id="pair:1",
            filler_item_id="filler:1",
            treated=treated,
        ),
    )


def _outcomes(*, treated: bool = True) -> tuple[Outcome, ...]:
    if treated:
        return (
            Outcome(
                assignment_id="assignment:1",
                parent_served=True,
                parent_seen_in_background=False,
                feed_length_before=25,
                feed_length_after=25,
                direct_child_item_id="child:1",
                direct_child_parent_id="parent:1",
                child_author_agent_id=20,
                child_round=3,
            ),
        )
    return (
        Outcome(
            assignment_id="assignment:1",
            parent_served=False,
            parent_seen_in_background=False,
            feed_length_before=25,
            feed_length_after=25,
            direct_child_item_id=None,
            direct_child_parent_id=None,
            child_author_agent_id=None,
            child_round=None,
        ),
    )


def _replace_parent(
    frame: SamplingFrame,
    index: int,
    **changes: object,
) -> SamplingFrame:
    parents = list(frame.parent_records)
    parents[index] = replace(parents[index], **changes)
    return replace(frame, parent_records=tuple(parents))


def _replace_pair(frame: SamplingFrame, index: int, **changes: object) -> SamplingFrame:
    pairs = list(frame.candidate_pairs)
    pairs[index] = replace(pairs[index], **changes)
    return replace(frame, candidate_pairs=tuple(pairs))


def _replace_evidence(
    evidence: FrameEligibilityEvidence,
    index: int,
    **changes: object,
) -> FrameEligibilityEvidence:
    rows = list(evidence.pair_evidence)
    rows[index] = replace(rows[index], **changes)
    return replace(evidence, pair_evidence=tuple(rows))


def test_valid_complete_sampling_frame_passes() -> None:
    validate_sampling_frame(_frame())


@pytest.mark.parametrize("bad_frame", [None, {}, object()])
def test_sampling_frame_requires_exact_record(bad_frame: object) -> None:
    with pytest.raises(TypeError):
        validate_sampling_frame(bad_frame)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field",
    ["parent_records", "excluded_recipient_agent_ids", "candidate_pairs"],
)
def test_sampling_frame_requires_exact_tuples(field: str) -> None:
    frame = _frame()
    bad_frame = replace(frame, **{field: list(getattr(frame, field))})

    with pytest.raises(TypeError):
        validate_sampling_frame(bad_frame)


def test_sampling_frame_requires_exact_nested_record_types() -> None:
    frame = _frame()

    with pytest.raises(TypeError):
        validate_sampling_frame(
            replace(
                frame,
                parent_records=(object(),) + frame.parent_records[1:],
            )
        )
    with pytest.raises(TypeError):
        validate_sampling_frame(
            replace(
                frame,
                candidate_pairs=(object(),) + frame.candidate_pairs[1:],
            )
        )


@pytest.mark.parametrize(
    "bad_frame",
    [
        replace(_frame(), frame_id=""),
        _replace_parent(_frame(), 0, parent_item_id=""),
        _replace_pair(_frame(), 0, pair_id=""),
        _replace_pair(_frame(), 0, parent_item_id=""),
        _replace_pair(_frame(), 0, stratum_id=""),
    ],
)
def test_sampling_frame_rejects_empty_or_non_string_identifiers(
    bad_frame: SamplingFrame,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_sampling_frame(bad_frame)


@pytest.mark.parametrize(
    "bad_frame",
    [
        _replace_parent(_frame(), 0, author_agent_id=True),
        _replace_parent(_frame(), 0, created_round=True),
        _replace_pair(_frame(), 0, agent_id=True),
        _replace_pair(_frame(), 0, round_id=True),
        _replace_pair(_frame(), 0, parent_first_readable_round=True),
        _replace_pair(_frame(), 0, prior_exposure_count=True),
        replace(_frame(), excluded_recipient_agent_ids=(10, True, 99)),
    ],
)
def test_sampling_frame_rejects_bool_for_integer_fields(
    bad_frame: SamplingFrame,
) -> None:
    with pytest.raises(TypeError):
        validate_sampling_frame(bad_frame)


@pytest.mark.parametrize(
    "bad_frame",
    [
        _replace_parent(_frame(), 0, author_agent_id=-1),
        _replace_parent(_frame(), 0, created_round=-1),
        _replace_pair(_frame(), 0, agent_id=-1),
        _replace_pair(_frame(), 0, round_id=-1),
        _replace_pair(_frame(), 0, parent_first_readable_round=-1),
        _replace_pair(_frame(), 0, prior_exposure_count=-1),
        replace(_frame(), excluded_recipient_agent_ids=(10, -1, 99)),
    ],
)
def test_sampling_frame_rejects_negative_integer_fields(
    bad_frame: SamplingFrame,
) -> None:
    with pytest.raises(ValueError):
        validate_sampling_frame(bad_frame)


def test_sampling_frame_requires_exact_opportunity_boolean() -> None:
    with pytest.raises(TypeError):
        validate_sampling_frame(
            _replace_pair(_frame(), 0, complete_same_action_opportunity=1)
        )


@pytest.mark.parametrize(
    "value",
    [0.0, -0.1, 1.1, math.inf, -math.inf, math.nan, 10**1000, True],
)
def test_sampling_frame_rejects_invalid_selection_probability(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_sampling_frame(_replace_pair(_frame(), 0, selection_probability=value))


@pytest.mark.parametrize(
    "value",
    [0.4, 0.6, 0.0, 1.0, math.inf, math.nan, 10**1000, True],
)
def test_sampling_frame_requires_fair_treatment_probability(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_sampling_frame(_replace_pair(_frame(), 0, treatment_probability=value))


def test_sampling_frame_requires_two_unique_parents() -> None:
    frame = _frame()

    with pytest.raises(ValueError):
        validate_sampling_frame(replace(frame, parent_records=frame.parent_records[:1]))
    with pytest.raises(ValueError):
        validate_sampling_frame(
            _replace_parent(
                frame,
                1,
                parent_item_id=frame.parent_records[0].parent_item_id,
            )
        )


def test_sampling_frame_requires_each_parent_to_have_a_registered_pair() -> None:
    frame = _frame()

    with pytest.raises(ValueError):
        validate_sampling_frame(
            replace(
                frame,
                candidate_pairs=(
                    frame.candidate_pairs[0],
                    frame.candidate_pairs[2],
                ),
            )
        )
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(frame, 0, parent_item_id="unknown"))


def test_sampling_frame_requires_unique_pair_ids() -> None:
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(_frame(), 1, pair_id="pair:1"))


def test_sampling_frame_excludes_parent_authors_and_frozen_recipients() -> None:
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(_frame(), 0, agent_id=10))
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(_frame(), 0, agent_id=99))


@pytest.mark.parametrize(
    "changes",
    [
        {"prior_exposure_count": 1},
        {"parent_first_readable_round": 2},
        {"complete_same_action_opportunity": False},
    ],
)
def test_sampling_frame_commits_prospective_eligibility(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(_frame(), 0, **changes))


def test_sampling_frame_derives_consistent_strata_from_pairs() -> None:
    frame = _frame()

    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(frame, 1, agent_id=22))
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(frame, 2, stratum_id="agent:20:round:3"))
    with pytest.raises(ValueError):
        validate_sampling_frame(
            _replace_pair(
                frame,
                2,
                stratum_id="agent:20:round:3:duplicate",
                agent_id=20,
                round_id=3,
                parent_first_readable_round=3,
            )
        )


def test_sampling_frame_uses_stable_sum_for_stratum_selection_mass() -> None:
    frame = _frame()

    validate_sampling_frame(
        _replace_pair(
            _replace_pair(frame, 0, selection_probability=0.1),
            1,
            selection_probability=0.2,
        )
    )
    with pytest.raises(ValueError):
        validate_sampling_frame(_replace_pair(frame, 1, selection_probability=0.7))


def test_valid_frame_provenance_passes() -> None:
    validate_frame_provenance(_frame(), _evidence())


def test_frame_provenance_requires_exact_record_and_tuple() -> None:
    evidence = _evidence()

    with pytest.raises(TypeError):
        validate_frame_provenance(_frame(), object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        validate_frame_provenance(
            _frame(), replace(evidence, pair_evidence=list(evidence.pair_evidence))
        )
    with pytest.raises(TypeError):
        validate_frame_provenance(
            _frame(),
            replace(
                evidence,
                pair_evidence=(object(),) + evidence.pair_evidence[1:],
            ),
        )


@pytest.mark.parametrize(
    "bad_evidence",
    [
        replace(_evidence(), frame_id="other"),
        replace(_evidence(), news_user_agent_id=True),
        replace(_evidence(), news_user_agent_id=-1),
        replace(_evidence(), news_user_agent_id=98),
        replace(_evidence(), pair_evidence=_evidence().pair_evidence[:-1]),
        replace(
            _evidence(),
            pair_evidence=_evidence().pair_evidence
            + (replace(_evidence().pair_evidence[0]),),
        ),
        _replace_evidence(_evidence(), 0, pair_id="unknown"),
        _replace_evidence(_evidence(), 0, parent_author_agent_id=12),
        _replace_evidence(_evidence(), 0, parent_created_round=2),
        _replace_evidence(_evidence(), 0, first_readable_round=2),
        _replace_evidence(_evidence(), 0, prior_exposure_count=1),
        _replace_evidence(_evidence(), 0, complete_same_action_opportunity=False),
    ],
)
def test_frame_provenance_rejects_incomplete_or_mismatched_evidence(
    bad_evidence: FrameEligibilityEvidence,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_frame_provenance(_frame(), bad_evidence)


def test_frame_provenance_validates_evidence_scalar_types() -> None:
    with pytest.raises(TypeError):
        validate_frame_provenance(
            _frame(), _replace_evidence(_evidence(), 0, parent_author_agent_id=True)
        )
    with pytest.raises(TypeError):
        validate_frame_provenance(
            _frame(),
            _replace_evidence(
                _evidence(),
                0,
                complete_same_action_opportunity=1,
            ),
        )


def test_valid_complete_stratum_draw_ledger_passes() -> None:
    validate_stratum_draws(_frame(), _draws())


def test_stratum_draws_require_exact_tuple_and_records() -> None:
    with pytest.raises(TypeError):
        validate_stratum_draws(_frame(), list(_draws()))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        validate_stratum_draws(_frame(), (object(),))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_draws",
    [
        _draws()[:-1],
        _draws() + (_draws()[0],),
        (replace(_draws()[0], frame_id="other"), _draws()[1]),
        (replace(_draws()[0], stratum_id=""), _draws()[1]),
        (replace(_draws()[0], stratum_id="unknown"), _draws()[1]),
        (replace(_draws()[0], selected_pair_id=""), _draws()[1]),
        (replace(_draws()[0], selected_pair_id="pair:3"), _draws()[1]),
        (_draws()[0], replace(_draws()[1], selected_pair_id="unknown")),
    ],
)
def test_stratum_draws_reject_incomplete_or_mismatched_ledger(
    bad_draws: tuple[StratumDraw, ...],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_stratum_draws(_frame(), bad_draws)


def test_valid_assignment_ledger_passes_for_selection_and_none() -> None:
    validate_assignments(_frame(), _draws(), _assignments())


def test_assignment_ledger_requires_exact_tuple_and_records() -> None:
    with pytest.raises(TypeError):
        validate_assignments(
            _frame(),
            _draws(),
            list(_assignments()),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        validate_assignments(_frame(), _draws(), (object(),))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_assignments",
    [
        (),
        _assignments() + _assignments(),
        (replace(_assignments()[0], assignment_id=""),),
        (replace(_assignments()[0], frame_id="other"),),
        (replace(_assignments()[0], pair_id="pair:2"),),
        (replace(_assignments()[0], filler_item_id=""),),
        (replace(_assignments()[0], filler_item_id="parent:1"),),
        (replace(_assignments()[0], treated=1),),
    ],
)
def test_assignment_ledger_rejects_missing_duplicate_or_invalid_rows(
    bad_assignments: tuple[Assignment, ...],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_assignments(_frame(), _draws(), bad_assignments)


def test_no_selection_draw_has_no_assignment() -> None:
    all_none = tuple(replace(draw, selected_pair_id=None) for draw in _draws())

    validate_assignments(_frame(), all_none, ())
    with pytest.raises(ValueError):
        validate_assignments(_frame(), all_none, _assignments())


def test_valid_treated_and_holdout_outcome_ledgers_pass() -> None:
    validate_outcomes(_frame(), _draws(), _assignments(), _outcomes())
    validate_outcomes(
        _frame(),
        _draws(),
        _assignments(treated=False),
        _outcomes(treated=False),
    )


def test_outcome_ledger_requires_exact_tuple_and_records() -> None:
    with pytest.raises(TypeError):
        validate_outcomes(
            _frame(),
            _draws(),
            _assignments(),
            list(_outcomes()),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        validate_outcomes(
            _frame(),
            _draws(),
            _assignments(),
            (object(),),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "bad_outcomes",
    [
        (),
        _outcomes() + _outcomes(),
        (replace(_outcomes()[0], assignment_id=""),),
        (replace(_outcomes()[0], assignment_id="unknown"),),
        (replace(_outcomes()[0], parent_served=1),),
        (replace(_outcomes()[0], parent_seen_in_background=0),),
        (replace(_outcomes()[0], feed_length_before=True),),
        (replace(_outcomes()[0], feed_length_before=-1),),
        (replace(_outcomes()[0], feed_length_after=24),),
    ],
)
def test_outcome_ledger_rejects_missing_duplicate_or_invalid_rows(
    bad_outcomes: tuple[Outcome, ...],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_outcomes(_frame(), _draws(), _assignments(), bad_outcomes)


@pytest.mark.parametrize(
    "changes",
    [
        {"direct_child_parent_id": None},
        {"child_author_agent_id": None},
        {"child_round": None},
        {"direct_child_item_id": None},
        {"direct_child_item_id": ""},
        {"direct_child_parent_id": "parent:2"},
        {"child_author_agent_id": 21},
        {"child_author_agent_id": True},
        {"child_round": 4},
        {"child_round": True},
    ],
)
def test_outcome_ledger_requires_complete_matching_child_provenance(
    changes: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_outcomes(
            _frame(),
            _draws(),
            _assignments(),
            (replace(_outcomes()[0], **changes),),
        )


def test_outcome_child_item_ids_are_globally_unique() -> None:
    frame = _frame()
    draws = (
        replace(_draws()[0], selected_pair_id="pair:1"),
        replace(_draws()[1], selected_pair_id="pair:3"),
    )
    assignments = (
        _assignments()[0],
        Assignment("assignment:2", "frame:1", "pair:3", "filler:2", True),
    )
    outcomes = (
        _outcomes()[0],
        Outcome(
            "assignment:2",
            True,
            False,
            25,
            25,
            "child:1",
            "parent:1",
            21,
            4,
        ),
    )

    with pytest.raises(ValueError):
        validate_outcomes(frame, draws, assignments, outcomes)


@pytest.mark.parametrize(
    "changes",
    [
        {"parent_served": False},
        {"parent_seen_in_background": True},
    ],
)
def test_treatment_requires_verified_service_without_background_duplicate(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        validate_outcomes(
            _frame(),
            _draws(),
            _assignments(),
            (replace(_outcomes()[0], **changes),),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"parent_served": True},
        {"parent_seen_in_background": True},
        {
            "direct_child_item_id": "child:1",
            "direct_child_parent_id": "parent:1",
            "child_author_agent_id": 20,
            "child_round": 3,
        },
    ],
)
def test_holdout_requires_no_service_leakage_or_child(
    changes: dict[str, object],
) -> None:
    assignments = _assignments(treated=False)
    outcome = replace(_outcomes(treated=False)[0], **changes)

    with pytest.raises(ValueError):
        validate_outcomes(_frame(), _draws(), assignments, (outcome,))

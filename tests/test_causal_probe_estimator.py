from dataclasses import FrozenInstanceError
import math

import pytest

from critaudit.sim.harness import causal_probe_spec as spec
from critaudit.sim.harness.causal_probe import (
    Assignment,
    Outcome,
    estimate_r_reply,
    validate_assignments,
    validate_outcomes,
)


def _assignment(
    assignment_id: str = "a1",
    *,
    round_id: int = 4,
    agent_id: int = 7,
    parent_item_id: str = "post:11",
    selection_probability: float = 0.25,
    treatment_probability: float = 0.5,
    treated: bool = True,
    parent_first_readable_round: int | None = None,
) -> Assignment:
    return Assignment(
        assignment_id=assignment_id,
        round_id=round_id,
        agent_id=agent_id,
        parent_item_id=parent_item_id,
        filler_item_id="post:12",
        selection_probability=selection_probability,
        treatment_probability=treatment_probability,
        treated=treated,
        parent_first_readable_round=(
            round_id
            if parent_first_readable_round is None
            else parent_first_readable_round
        ),
    )


def _outcome(
    assignment: Assignment,
    *,
    parent_served: bool | None = None,
    parent_seen_in_background: bool = False,
    feed_length_before: int = 4,
    feed_length_after: int = 4,
    response: bool = False,
    direct_child_item_id: str | None = None,
    direct_child_parent_id: str | None = None,
    child_round: int | None = None,
) -> Outcome:
    if parent_served is None:
        parent_served = assignment.treated
    if response:
        direct_child_item_id = f"comment:{assignment.assignment_id}"
        direct_child_parent_id = assignment.parent_item_id
        child_round = assignment.round_id + spec.OUTCOME_LAG_ROUNDS
    return Outcome(
        assignment_id=assignment.assignment_id,
        parent_served=parent_served,
        parent_seen_in_background=parent_seen_in_background,
        feed_length_before=feed_length_before,
        feed_length_after=feed_length_after,
        direct_child_item_id=direct_child_item_id,
        direct_child_parent_id=direct_child_parent_id,
        child_round=child_round,
    )


def _two_parent_zero_response_fixture() -> tuple[list[Assignment], list[Outcome]]:
    assignments = [
        _assignment("a1", agent_id=1, parent_item_id="post:1"),
        _assignment(
            "a2", agent_id=2, parent_item_id="post:2", treated=False
        ),
    ]
    return assignments, [_outcome(assignment) for assignment in assignments]


def test_plan_example_records_are_immutable():
    assignment = Assignment(
        assignment_id="round:agent:parent",
        round_id=4,
        agent_id=7,
        parent_item_id="post:11",
        filler_item_id="post:12",
        selection_probability=0.25,
        treatment_probability=0.5,
        treated=True,
        parent_first_readable_round=4,
    )
    outcome = Outcome(
        assignment_id="round:agent:parent",
        parent_served=True,
        parent_seen_in_background=False,
        feed_length_before=4,
        feed_length_after=4,
        direct_child_item_id="comment:21",
        direct_child_parent_id="post:11",
        child_round=4,
    )

    validate_assignments([assignment])
    validate_outcomes([assignment], [outcome])
    with pytest.raises(FrozenInstanceError):
        assignment.treated = False
    with pytest.raises(FrozenInstanceError):
        outcome.parent_served = False


def test_hand_computed_two_parent_ht_estimate_can_exceed_one():
    assignments = [
        _assignment(
            "a1",
            agent_id=1,
            parent_item_id="post:1",
            selection_probability=0.25,
            treatment_probability=0.5,
        ),
        _assignment(
            "a2", agent_id=2, parent_item_id="post:1", treated=False
        ),
        _assignment(
            "a3",
            agent_id=3,
            parent_item_id="post:2",
            selection_probability=0.5,
            treatment_probability=0.5,
        ),
        _assignment("a4", agent_id=4, parent_item_id="post:2"),
    ]
    outcomes = [
        _outcome(assignments[0], response=True),
        _outcome(assignments[1]),
        _outcome(assignments[2], response=True),
        _outcome(assignments[3]),
    ]

    result = estimate_r_reply(assignments, outcomes)

    expected_se = math.sqrt(17.0)
    assert result.estimate == pytest.approx(6.0)
    assert result.standard_error == pytest.approx(expected_se)
    assert result.ci95_low == pytest.approx(6.0 - 1.96 * expected_se)
    assert result.ci95_high == pytest.approx(6.0 + 1.96 * expected_se)
    assert result.parent_count == 2
    assert result.candidate_pair_count == 4
    assert result.treated_count == 3
    assert result.control_count == 1
    assert result.response_count == 2
    assert result.status == spec.STATUS_DESIGN_ONLY


def test_zero_response_has_zero_standard_error_and_point_ci():
    assignments, outcomes = _two_parent_zero_response_fixture()

    result = estimate_r_reply(assignments, outcomes)

    assert result.estimate == 0.0
    assert result.standard_error == 0.0
    assert result.ci95_low == 0.0
    assert result.ci95_high == 0.0
    assert result.response_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("selection_probability", None),
        ("selection_probability", 0.0),
        ("selection_probability", -0.1),
        ("selection_probability", 1.01),
        ("selection_probability", math.inf),
        ("selection_probability", math.nan),
        ("treatment_probability", None),
        ("treatment_probability", 0.0),
        ("treatment_probability", -0.1),
        ("treatment_probability", 1.01),
        ("treatment_probability", -math.inf),
        ("treatment_probability", math.nan),
    ],
)
def test_invalid_inclusion_probability_fails_closed(field, value):
    overrides = {field: value}
    assignment = _assignment(**overrides)

    with pytest.raises(ValueError, match=field):
        validate_assignments([assignment])


def test_duplicate_assignment_ids_fail_closed():
    assignments = [_assignment("duplicate"), _assignment("duplicate", agent_id=8)]

    with pytest.raises(ValueError, match="duplicate assignment_id"):
        validate_assignments(assignments)


def test_duplicate_outcome_ids_fail_closed():
    assignments, outcomes = _two_parent_zero_response_fixture()
    outcomes.append(_outcome(assignments[0]))

    with pytest.raises(ValueError, match="duplicate outcome assignment_id"):
        validate_outcomes(assignments, outcomes)


def test_missing_outcome_id_fails_closed():
    assignments, outcomes = _two_parent_zero_response_fixture()

    with pytest.raises(ValueError, match="exactly one outcome"):
        validate_outcomes(assignments, outcomes[:-1])


def test_unknown_outcome_id_fails_closed():
    assignments, outcomes = _two_parent_zero_response_fixture()
    outcomes.append(
        Outcome(
            assignment_id="unknown",
            parent_served=False,
            parent_seen_in_background=False,
            feed_length_before=4,
            feed_length_after=4,
            direct_child_item_id=None,
            direct_child_parent_id=None,
            child_round=None,
        )
    )

    with pytest.raises(ValueError, match="unknown assignment_id"):
        validate_outcomes(assignments, outcomes)


def test_more_than_one_experimental_parent_per_agent_round_fails_closed():
    assignments = [
        _assignment("a1", agent_id=7, parent_item_id="post:1"),
        _assignment("a2", agent_id=7, parent_item_id="post:2"),
    ]

    with pytest.raises(ValueError, match="agent-round"):
        validate_assignments(assignments)


def test_treatment_without_verified_service_fails_closed():
    assignment = _assignment()

    with pytest.raises(ValueError, match="treated parent must be served"):
        validate_outcomes([assignment], [_outcome(assignment, parent_served=False)])


def test_treated_background_duplication_fails_closed():
    assignment = _assignment()

    with pytest.raises(ValueError, match="background duplication"):
        validate_outcomes(
            [assignment],
            [_outcome(assignment, parent_seen_in_background=True)],
        )


@pytest.mark.parametrize(
    ("parent_served", "parent_seen_in_background"),
    [(True, False), (False, True)],
)
def test_holdout_parent_leakage_fails_closed(
    parent_served, parent_seen_in_background
):
    assignment = _assignment(treated=False)

    with pytest.raises(ValueError, match="holdout parent leakage"):
        validate_outcomes(
            [assignment],
            [
                _outcome(
                    assignment,
                    parent_served=parent_served,
                    parent_seen_in_background=parent_seen_in_background,
                )
            ],
        )


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [(-1, -1, "nonnegative"), (4, 3, "feed length changed")],
)
def test_invalid_feed_lengths_fail_closed(before, after, message):
    assignment = _assignment()

    with pytest.raises(ValueError, match=message):
        validate_outcomes(
            [assignment],
            [
                _outcome(
                    assignment,
                    feed_length_before=before,
                    feed_length_after=after,
                )
            ],
        )


def test_mismatched_native_child_parent_fails_closed():
    assignment = _assignment()
    outcome = _outcome(assignment, response=True)
    outcome = Outcome(
        **{
            **outcome.__dict__,
            "direct_child_parent_id": "post:different",
        }
    )

    with pytest.raises(ValueError, match="native child parent"):
        validate_outcomes([assignment], [outcome])


@pytest.mark.parametrize(
    ("child_item", "child_parent", "child_round"),
    [
        ("comment:1", None, None),
        (None, "post:11", None),
        (None, None, 4),
        ("comment:1", "post:11", None),
    ],
)
def test_partial_child_fields_fail_closed(child_item, child_parent, child_round):
    assignment = _assignment()

    with pytest.raises(ValueError, match="child fields"):
        validate_outcomes(
            [assignment],
            [
                _outcome(
                    assignment,
                    direct_child_item_id=child_item,
                    direct_child_parent_id=child_parent,
                    child_round=child_round,
                )
            ],
        )


def test_control_arm_direct_child_fails_closed():
    assignment = _assignment(treated=False)

    with pytest.raises(ValueError, match="control arm direct child"):
        validate_outcomes([assignment], [_outcome(assignment, response=True)])


def test_prior_or_inconsistent_first_readable_round_fails_closed():
    assignment = _assignment(parent_first_readable_round=3)

    with pytest.raises(ValueError, match="first-readable round"):
        validate_assignments([assignment])


def test_late_outcome_fails_closed():
    assignment = _assignment()
    outcome = _outcome(assignment, response=True)
    outcome = Outcome(**{**outcome.__dict__, "child_round": 5})

    with pytest.raises(ValueError, match="outcome round"):
        validate_outcomes([assignment], [outcome])


@pytest.mark.parametrize("assignments", [[], [_assignment(parent_item_id="")]])
def test_empty_or_missing_eligible_parent_fails_closed(assignments):
    with pytest.raises(ValueError, match="eligible parent"):
        validate_assignments(assignments)


def test_estimator_requires_two_unique_eligible_parents():
    assignment = _assignment()

    with pytest.raises(ValueError, match="at least two unique eligible parents"):
        estimate_r_reply([assignment], [_outcome(assignment)])

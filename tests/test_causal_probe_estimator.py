from dataclasses import replace
import math

import pytest

from critaudit.sim.harness.causal_probe import (
    deterministic_worst_case_variance_bound,
    estimate_r_reply,
)
from critaudit.sim.harness.causal_probe_records import (
    Assignment,
    CandidatePair,
    Outcome,
    ParentEligibility,
    RReplyEstimate,
    SamplingFrame,
    StratumDraw,
)
from critaudit.sim.harness.causal_probe_spec import STATUS_DESIGN_ONLY


def _frame() -> SamplingFrame:
    return SamplingFrame(
        frame_id="frame:estimator",
        parent_records=(
            ParentEligibility("parent:1", author_agent_id=10, created_round=1),
            ParentEligibility("parent:2", author_agent_id=11, created_round=2),
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


def _draws() -> tuple[StratumDraw, ...]:
    return (
        StratumDraw(
            frame_id="frame:estimator",
            stratum_id="agent:20:round:3",
            selected_pair_id="pair:1",
        ),
        StratumDraw(
            frame_id="frame:estimator",
            stratum_id="agent:21:round:4",
            selected_pair_id=None,
        ),
    )


def _assignments(*, treated: bool = True) -> tuple[Assignment, ...]:
    return (
        Assignment(
            assignment_id="assignment:1",
            frame_id="frame:estimator",
            pair_id="pair:1",
            filler_item_id="filler:1",
            treated=treated,
        ),
    )


def _outcomes(*, response: bool = True) -> tuple[Outcome, ...]:
    return (
        Outcome(
            assignment_id="assignment:1",
            parent_served=True,
            parent_seen_in_background=False,
            feed_length_before=25,
            feed_length_after=25,
            direct_child_item_id="child:1" if response else None,
            direct_child_parent_id="parent:1" if response else None,
            child_author_agent_id=20 if response else None,
            child_round=3 if response else None,
        ),
    )


def test_complete_frame_estimate_can_exceed_one_with_explicit_no_selection() -> None:
    result = estimate_r_reply(_frame(), _draws(), _assignments(), _outcomes())

    expected_observed_variance = 5.0
    expected_worst_case_variance = 2.75
    expected_se = math.sqrt(expected_observed_variance)
    assert type(result) is RReplyEstimate
    assert result.frame_id == "frame:estimator"
    assert result.estimate == pytest.approx(2.5)
    assert result.estimated_diagonal_variance_bound == pytest.approx(
        expected_observed_variance
    )
    assert result.standard_error_conservative == pytest.approx(expected_se)
    assert result.ci95_low == pytest.approx(2.5 - 1.96 * expected_se)
    assert result.ci95_high == pytest.approx(2.5 + 1.96 * expected_se)
    assert result.deterministic_worst_case_variance_bound == pytest.approx(
        expected_worst_case_variance
    )
    assert result.parent_count == 2
    assert result.candidate_pair_count == 3
    assert result.stratum_count == 2
    assert result.draw_count == 2
    assert result.selected_count == 1
    assert result.no_selection_count == 1
    assert result.treated_count == 1
    assert result.control_count == 0
    assert result.response_count == 1
    assert result.status == STATUS_DESIGN_ONLY


def test_zero_response_has_point_ci_but_positive_frame_bound() -> None:
    result = estimate_r_reply(
        _frame(),
        _draws(),
        _assignments(),
        _outcomes(response=False),
    )

    assert result.estimate == 0.0
    assert result.estimated_diagonal_variance_bound == 0.0
    assert result.standard_error_conservative == 0.0
    assert result.ci95_low == 0.0
    assert result.ci95_high == 0.0
    assert result.deterministic_worst_case_variance_bound == pytest.approx(2.75)
    assert result.response_count == 0


def test_holdout_counts_in_complete_ledgers_without_contributing() -> None:
    assignments = _assignments(treated=False)
    outcomes = (
        replace(
            _outcomes(response=False)[0],
            parent_served=False,
        ),
    )

    result = estimate_r_reply(_frame(), _draws(), assignments, outcomes)

    assert result.estimate == 0.0
    assert result.selected_count == 1
    assert result.treated_count == 0
    assert result.control_count == 1
    assert result.response_count == 0


def test_deterministic_worst_case_bound_uses_every_candidate_pair() -> None:
    assert deterministic_worst_case_variance_bound(_frame()) == pytest.approx(2.75)

    frame_with_extra_pair = replace(
        _frame(),
        candidate_pairs=_frame().candidate_pairs
        + (
            CandidatePair(
                pair_id="pair:4",
                parent_item_id="parent:2",
                agent_id=22,
                round_id=5,
                stratum_id="agent:22:round:5",
                selection_probability=0.5,
                treatment_probability=0.5,
                parent_first_readable_round=5,
                prior_exposure_count=0,
                complete_same_action_opportunity=True,
            ),
        ),
    )
    assert deterministic_worst_case_variance_bound(
        frame_with_extra_pair
    ) == pytest.approx(3.5)


def test_deterministic_worst_case_bound_validates_the_frame() -> None:
    with pytest.raises(ValueError):
        deterministic_worst_case_variance_bound(
            replace(_frame(), parent_records=_frame().parent_records[:1])
        )


@pytest.mark.parametrize(
    ("frame", "draws", "assignments", "outcomes"),
    [
        (
            replace(_frame(), parent_records=_frame().parent_records[:1]),
            _draws(),
            _assignments(),
            _outcomes(),
        ),
        (_frame(), _draws()[:1], _assignments(), _outcomes()),
        (_frame(), _draws(), (), _outcomes()),
        (_frame(), _draws(), _assignments(), ()),
    ],
)
def test_estimator_calls_every_complete_ledger_validator(
    frame: SamplingFrame,
    draws: tuple[StratumDraw, ...],
    assignments: tuple[Assignment, ...],
    outcomes: tuple[Outcome, ...],
) -> None:
    with pytest.raises(ValueError):
        estimate_r_reply(frame, draws, assignments, outcomes)

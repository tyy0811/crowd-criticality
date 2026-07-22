"""Pure records and design-based estimator for the causal reply probe."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Iterable

from critaudit.sim.harness import causal_probe_spec as spec

__all__ = (
    "Assignment",
    "Outcome",
    "RReplyEstimate",
    "validate_assignments",
    "validate_outcomes",
    "estimate_r_reply",
)


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    round_id: int
    agent_id: int
    parent_item_id: str
    filler_item_id: str
    selection_probability: float
    treatment_probability: float
    treated: bool
    parent_first_readable_round: int


@dataclass(frozen=True)
class Outcome:
    assignment_id: str
    parent_served: bool
    parent_seen_in_background: bool
    feed_length_before: int
    feed_length_after: int
    direct_child_item_id: str | None
    direct_child_parent_id: str | None
    child_round: int | None


@dataclass(frozen=True)
class RReplyEstimate:
    estimate: float
    standard_error: float
    ci95_low: float
    ci95_high: float
    parent_count: int
    candidate_pair_count: int
    treated_count: int
    control_count: int
    response_count: int
    status: str


def _validated_probability(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or not 0.0 < float(value) <= 1.0
    ):
        raise ValueError(f"{field} must be real, finite, and in (0, 1]")
    return float(value)


def validate_assignments(assignments: Iterable[Assignment]) -> None:
    """Fail closed on assignments outside the frozen experimental contract."""
    assignment_records = tuple(assignments)
    if not assignment_records:
        raise ValueError("missing eligible parent: assignments must be non-empty")

    assignment_ids: set[str] = set()
    agent_rounds: set[tuple[int, int]] = set()
    eligible_parents: set[str] = set()

    for assignment in assignment_records:
        if assignment.assignment_id in assignment_ids:
            raise ValueError(
                f"duplicate assignment_id: {assignment.assignment_id!r}"
            )
        assignment_ids.add(assignment.assignment_id)

        if not isinstance(assignment.parent_item_id, str) or not assignment.parent_item_id:
            raise ValueError("missing eligible parent: parent_item_id must be non-empty")
        eligible_parents.add(assignment.parent_item_id)

        _validated_probability(
            assignment.selection_probability, "selection_probability"
        )
        _validated_probability(
            assignment.treatment_probability, "treatment_probability"
        )

        if assignment.parent_first_readable_round != assignment.round_id:
            raise ValueError(
                "parent first-readable round must equal assignment round_id"
            )

        agent_round = (assignment.agent_id, assignment.round_id)
        if agent_round in agent_rounds:
            raise ValueError(
                "more than one experimental parent for an agent-round"
            )
        agent_rounds.add(agent_round)

    if not eligible_parents:
        raise ValueError("missing eligible parent")


def validate_outcomes(
    assignments: Iterable[Assignment], outcomes: Iterable[Outcome]
) -> None:
    """Require one isolated, same-action outcome for every assignment."""
    assignment_records = tuple(assignments)
    outcome_records = tuple(outcomes)
    validate_assignments(assignment_records)

    assignments_by_id = {
        assignment.assignment_id: assignment for assignment in assignment_records
    }
    outcomes_by_id: dict[str, Outcome] = {}

    for outcome in outcome_records:
        if outcome.assignment_id in outcomes_by_id:
            raise ValueError(
                f"duplicate outcome assignment_id: {outcome.assignment_id!r}"
            )
        if outcome.assignment_id not in assignments_by_id:
            raise ValueError(
                f"outcome has unknown assignment_id: {outcome.assignment_id!r}"
            )
        outcomes_by_id[outcome.assignment_id] = outcome

    if set(outcomes_by_id) != set(assignments_by_id):
        raise ValueError("every assignment must have exactly one outcome")

    for assignment in assignment_records:
        outcome = outcomes_by_id[assignment.assignment_id]

        if outcome.feed_length_before < 0 or outcome.feed_length_after < 0:
            raise ValueError("feed lengths must be nonnegative")
        if outcome.feed_length_before != outcome.feed_length_after:
            raise ValueError("feed length changed across assignment")

        child_fields_present = (
            outcome.direct_child_item_id is not None,
            outcome.direct_child_parent_id is not None,
            outcome.child_round is not None,
        )
        if any(child_fields_present) and not all(child_fields_present):
            raise ValueError("direct child fields must be all populated or all absent")
        has_response = all(child_fields_present)

        if assignment.treated:
            if not outcome.parent_served:
                raise ValueError("treated parent must be served")
            if outcome.parent_seen_in_background:
                raise ValueError("treated parent has background duplication")
        else:
            if outcome.parent_served or outcome.parent_seen_in_background:
                raise ValueError("holdout parent leakage")
            if has_response:
                raise ValueError("control arm direct child is forbidden")

        if has_response:
            if outcome.direct_child_parent_id != assignment.parent_item_id:
                raise ValueError("native child parent does not match assigned parent")
            expected_round = assignment.round_id + spec.OUTCOME_LAG_ROUNDS
            if outcome.child_round != expected_round:
                raise ValueError(
                    f"outcome round must equal assignment round plus "
                    f"OUTCOME_LAG_ROUNDS ({expected_round})"
                )


def estimate_r_reply(
    assignments: Iterable[Assignment], outcomes: Iterable[Outcome]
) -> RReplyEstimate:
    """Estimate mean per-parent direct reply potential by Horvitz-Thompson totals."""
    assignment_records = tuple(assignments)
    outcome_records = tuple(outcomes)
    validate_outcomes(assignment_records, outcome_records)

    eligible_parents = {assignment.parent_item_id for assignment in assignment_records}
    parent_count = len(eligible_parents)
    if parent_count < 2:
        raise ValueError("estimate requires at least two unique eligible parents")

    outcomes_by_id = {
        outcome.assignment_id: outcome for outcome in outcome_records
    }
    ht_total = 0.0
    variance_total = 0.0
    response_count = 0

    for assignment in assignment_records:
        outcome = outcomes_by_id[assignment.assignment_id]
        has_response = outcome.direct_child_item_id is not None
        if not assignment.treated or not has_response:
            continue
        inclusion_probability = (
            float(assignment.selection_probability)
            * float(assignment.treatment_probability)
        )
        ht_total += 1.0 / inclusion_probability
        variance_total += (
            (1.0 - inclusion_probability)
            / (inclusion_probability * inclusion_probability)
        )
        response_count += 1

    estimate = ht_total / parent_count
    standard_error = math.sqrt(variance_total / (parent_count * parent_count))
    ci_half_width = 1.96 * standard_error
    treated_count = sum(assignment.treated for assignment in assignment_records)

    return RReplyEstimate(
        estimate=estimate,
        standard_error=standard_error,
        ci95_low=estimate - ci_half_width,
        ci95_high=estimate + ci_half_width,
        parent_count=parent_count,
        candidate_pair_count=len(assignment_records),
        treated_count=treated_count,
        control_count=len(assignment_records) - treated_count,
        response_count=response_count,
        status=spec.STATUS_DESIGN_ONLY,
    )

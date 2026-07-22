"""Strict validators for the frozen causal-probe sampling ledgers."""

from __future__ import annotations

from collections import defaultdict
import math

from .causal_probe_records import (
    Assignment,
    CandidatePair,
    FrameEligibilityEvidence,
    Outcome,
    PairEligibilityEvidence,
    ParentEligibility,
    SamplingFrame,
    StratumDraw,
)
from .causal_probe_spec import OUTCOME_LAG_ROUNDS, TREATMENT_PROBABILITY

__all__ = (
    "validate_sampling_frame",
    "validate_frame_provenance",
    "validate_stratum_draws",
    "validate_assignments",
    "validate_outcomes",
)


def _require_exact_record(value: object, expected: type, name: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{name} must be exactly {expected.__name__}")


def _require_tuple(value: object, name: str) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be exactly tuple")


def _require_id(value: object, name: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be exactly str")
    if not value:
        raise ValueError(f"{name} must be non-empty")


def _require_nonnegative_int(value: object, name: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be exactly int")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _require_bool(value: object, name: str) -> None:
    if type(value) is not bool:
        raise TypeError(f"{name} must be exactly bool")


def _require_probability(value: object, name: str) -> None:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(value) or not 0 < value <= 1:
        raise ValueError(f"{name} must be finite and in (0, 1]")


def _frame_maps(
    frame: SamplingFrame,
) -> tuple[
    dict[str, ParentEligibility],
    dict[str, CandidatePair],
    dict[str, tuple[CandidatePair, ...]],
]:
    parents = {parent.parent_item_id: parent for parent in frame.parent_records}
    pairs = {pair.pair_id: pair for pair in frame.candidate_pairs}
    by_stratum_lists: dict[str, list[CandidatePair]] = defaultdict(list)
    for pair in frame.candidate_pairs:
        by_stratum_lists[pair.stratum_id].append(pair)
    by_stratum = {
        stratum_id: tuple(stratum_pairs)
        for stratum_id, stratum_pairs in by_stratum_lists.items()
    }
    return parents, pairs, by_stratum


def validate_sampling_frame(frame: SamplingFrame) -> None:
    """Reject any sampling frame that is not complete and immutable in shape."""

    _require_exact_record(frame, SamplingFrame, "frame")
    _require_id(frame.frame_id, "frame.frame_id")
    _require_tuple(frame.parent_records, "frame.parent_records")
    _require_tuple(
        frame.excluded_recipient_agent_ids,
        "frame.excluded_recipient_agent_ids",
    )
    _require_tuple(frame.candidate_pairs, "frame.candidate_pairs")

    parent_ids: list[str] = []
    for index, parent in enumerate(frame.parent_records):
        _require_exact_record(
            parent,
            ParentEligibility,
            f"frame.parent_records[{index}]",
        )
        _require_id(parent.parent_item_id, f"parent_records[{index}].parent_item_id")
        _require_nonnegative_int(
            parent.author_agent_id,
            f"parent_records[{index}].author_agent_id",
        )
        _require_nonnegative_int(
            parent.created_round,
            f"parent_records[{index}].created_round",
        )
        parent_ids.append(parent.parent_item_id)

    if len(set(parent_ids)) < 2:
        raise ValueError("frame must contain at least two unique parents")
    if len(set(parent_ids)) != len(parent_ids):
        raise ValueError("parent item IDs must be unique")

    excluded_recipients: set[int] = set()
    for index, agent_id in enumerate(frame.excluded_recipient_agent_ids):
        _require_nonnegative_int(
            agent_id,
            f"excluded_recipient_agent_ids[{index}]",
        )
        excluded_recipients.add(agent_id)

    parents = {parent.parent_item_id: parent for parent in frame.parent_records}
    pair_ids: set[str] = set()
    paired_parent_ids: set[str] = set()
    stratum_agent_round: dict[str, tuple[int, int]] = {}
    agent_round_stratum: dict[tuple[int, int], str] = {}
    stratum_selection_mass: dict[str, list[float]] = defaultdict(list)

    for index, pair in enumerate(frame.candidate_pairs):
        _require_exact_record(
            pair,
            CandidatePair,
            f"frame.candidate_pairs[{index}]",
        )
        prefix = f"candidate_pairs[{index}]"
        _require_id(pair.pair_id, f"{prefix}.pair_id")
        _require_id(pair.parent_item_id, f"{prefix}.parent_item_id")
        _require_nonnegative_int(pair.agent_id, f"{prefix}.agent_id")
        _require_nonnegative_int(pair.round_id, f"{prefix}.round_id")
        _require_id(pair.stratum_id, f"{prefix}.stratum_id")
        _require_probability(
            pair.selection_probability,
            f"{prefix}.selection_probability",
        )
        _require_probability(
            pair.treatment_probability,
            f"{prefix}.treatment_probability",
        )
        if pair.treatment_probability != TREATMENT_PROBABILITY:
            raise ValueError(
                f"{prefix}.treatment_probability must equal "
                f"{TREATMENT_PROBABILITY}"
            )
        _require_nonnegative_int(
            pair.parent_first_readable_round,
            f"{prefix}.parent_first_readable_round",
        )
        _require_nonnegative_int(
            pair.prior_exposure_count,
            f"{prefix}.prior_exposure_count",
        )
        _require_bool(
            pair.complete_same_action_opportunity,
            f"{prefix}.complete_same_action_opportunity",
        )

        if pair.pair_id in pair_ids:
            raise ValueError("pair IDs must be unique")
        pair_ids.add(pair.pair_id)
        if pair.parent_item_id not in parents:
            raise ValueError(f"pair {pair.pair_id!r} has an unregistered parent")
        paired_parent_ids.add(pair.parent_item_id)

        parent = parents[pair.parent_item_id]
        if pair.agent_id == parent.author_agent_id:
            raise ValueError("pair recipient must differ from the parent author")
        if pair.agent_id in excluded_recipients:
            raise ValueError("pair recipient is in the frozen exclusion registry")
        if pair.prior_exposure_count != 0:
            raise ValueError("candidate pairs must have zero prior exposure")
        if pair.parent_first_readable_round != pair.round_id:
            raise ValueError(
                "candidate parent must first be readable in its pair round"
            )
        if pair.complete_same_action_opportunity is not True:
            raise ValueError("candidate pair opportunity must be complete")

        agent_round = (pair.agent_id, pair.round_id)
        existing_agent_round = stratum_agent_round.setdefault(
            pair.stratum_id,
            agent_round,
        )
        if existing_agent_round != agent_round:
            raise ValueError("all pairs in a stratum must share one agent-round")
        existing_stratum = agent_round_stratum.setdefault(agent_round, pair.stratum_id)
        if existing_stratum != pair.stratum_id:
            raise ValueError("each agent-round must map to exactly one stratum")
        stratum_selection_mass[pair.stratum_id].append(pair.selection_probability)

    missing_parent_ids = set(parent_ids) - paired_parent_ids
    if missing_parent_ids:
        raise ValueError(
            "every registered parent must have at least one candidate pair"
        )
    for probabilities in stratum_selection_mass.values():
        if math.fsum(probabilities) > 1:
            raise ValueError("selection probability mass exceeds one in a stratum")


def validate_frame_provenance(
    frame: SamplingFrame,
    evidence: FrameEligibilityEvidence,
) -> None:
    """Cross-check the complete frame against frozen pre-draw eligibility evidence."""

    validate_sampling_frame(frame)
    _require_exact_record(evidence, FrameEligibilityEvidence, "evidence")
    _require_id(evidence.frame_id, "evidence.frame_id")
    if evidence.frame_id != frame.frame_id:
        raise ValueError("evidence frame ID does not match sampling frame")
    _require_nonnegative_int(
        evidence.news_user_agent_id,
        "evidence.news_user_agent_id",
    )
    if evidence.news_user_agent_id not in frame.excluded_recipient_agent_ids:
        raise ValueError("dedicated news user must be in the exclusion registry")
    _require_tuple(evidence.pair_evidence, "evidence.pair_evidence")

    parents, pairs, _ = _frame_maps(frame)
    evidence_by_pair: dict[str, PairEligibilityEvidence] = {}
    for index, row in enumerate(evidence.pair_evidence):
        _require_exact_record(
            row,
            PairEligibilityEvidence,
            f"evidence.pair_evidence[{index}]",
        )
        prefix = f"pair_evidence[{index}]"
        _require_id(row.pair_id, f"{prefix}.pair_id")
        _require_nonnegative_int(
            row.parent_author_agent_id,
            f"{prefix}.parent_author_agent_id",
        )
        _require_nonnegative_int(
            row.parent_created_round,
            f"{prefix}.parent_created_round",
        )
        _require_nonnegative_int(
            row.first_readable_round,
            f"{prefix}.first_readable_round",
        )
        _require_nonnegative_int(
            row.prior_exposure_count,
            f"{prefix}.prior_exposure_count",
        )
        _require_bool(
            row.complete_same_action_opportunity,
            f"{prefix}.complete_same_action_opportunity",
        )
        if row.pair_id in evidence_by_pair:
            raise ValueError("eligibility evidence must be unique by pair")
        if row.pair_id not in pairs:
            raise ValueError("eligibility evidence names an unknown pair")
        evidence_by_pair[row.pair_id] = row

    if set(evidence_by_pair) != set(pairs):
        raise ValueError("eligibility evidence must contain exactly one row per pair")

    for pair_id, pair in pairs.items():
        row = evidence_by_pair[pair_id]
        parent = parents[pair.parent_item_id]
        if row.parent_author_agent_id != parent.author_agent_id:
            raise ValueError("evidence parent author does not match the registry")
        if row.parent_created_round != parent.created_round:
            raise ValueError(
                "evidence parent creation round does not match the registry"
            )
        if row.first_readable_round != pair.parent_first_readable_round:
            raise ValueError("evidence first-readable round does not match the pair")
        if row.prior_exposure_count != 0:
            raise ValueError("evidence must confirm zero prior exposure")
        if row.complete_same_action_opportunity is not True:
            raise ValueError("evidence must confirm a complete same-action opportunity")


def validate_stratum_draws(
    frame: SamplingFrame,
    draws: tuple[StratumDraw, ...],
) -> None:
    """Require one explicit selection or no-selection draw for every stratum."""

    validate_sampling_frame(frame)
    _require_tuple(draws, "draws")
    _, pairs, by_stratum = _frame_maps(frame)
    draw_by_stratum: dict[str, StratumDraw] = {}

    for index, draw in enumerate(draws):
        _require_exact_record(draw, StratumDraw, f"draws[{index}]")
        prefix = f"draws[{index}]"
        _require_id(draw.frame_id, f"{prefix}.frame_id")
        _require_id(draw.stratum_id, f"{prefix}.stratum_id")
        if draw.frame_id != frame.frame_id:
            raise ValueError("draw frame ID does not match sampling frame")
        if draw.stratum_id in draw_by_stratum:
            raise ValueError("draws must be unique by stratum")
        if draw.stratum_id not in by_stratum:
            raise ValueError("draw names an unknown stratum")
        if draw.selected_pair_id is not None:
            _require_id(draw.selected_pair_id, f"{prefix}.selected_pair_id")
            selected_pair = pairs.get(draw.selected_pair_id)
            if selected_pair is None:
                raise ValueError("draw selects an unknown pair")
            if selected_pair.stratum_id != draw.stratum_id:
                raise ValueError("selected pair does not belong to the draw stratum")
        draw_by_stratum[draw.stratum_id] = draw

    if set(draw_by_stratum) != set(by_stratum):
        raise ValueError("draw ledger must contain every derived stratum")


def validate_assignments(
    frame: SamplingFrame,
    draws: tuple[StratumDraw, ...],
    assignments: tuple[Assignment, ...],
) -> None:
    """Require exactly one valid assignment for every selected pair."""

    validate_stratum_draws(frame, draws)
    _require_tuple(assignments, "assignments")
    parents, pairs, _ = _frame_maps(frame)
    selected_pair_ids = {
        draw.selected_pair_id
        for draw in draws
        if draw.selected_pair_id is not None
    }
    assignment_ids: set[str] = set()
    assigned_pair_ids: list[str] = []

    for index, assignment in enumerate(assignments):
        _require_exact_record(assignment, Assignment, f"assignments[{index}]")
        prefix = f"assignments[{index}]"
        _require_id(assignment.assignment_id, f"{prefix}.assignment_id")
        _require_id(assignment.frame_id, f"{prefix}.frame_id")
        _require_id(assignment.pair_id, f"{prefix}.pair_id")
        _require_id(assignment.filler_item_id, f"{prefix}.filler_item_id")
        _require_bool(assignment.treated, f"{prefix}.treated")
        if assignment.assignment_id in assignment_ids:
            raise ValueError("assignment IDs must be unique")
        assignment_ids.add(assignment.assignment_id)
        if assignment.frame_id != frame.frame_id:
            raise ValueError("assignment frame ID does not match sampling frame")
        if assignment.pair_id not in pairs:
            raise ValueError("assignment names an unknown pair")
        parent_id = pairs[assignment.pair_id].parent_item_id
        if assignment.filler_item_id == parents[parent_id].parent_item_id:
            raise ValueError("filler item must differ from the selected parent")
        assigned_pair_ids.append(assignment.pair_id)

    if len(assigned_pair_ids) != len(set(assigned_pair_ids)):
        raise ValueError("selected pairs must have exactly one assignment")
    if set(assigned_pair_ids) != selected_pair_ids:
        raise ValueError("assignments must match selected pairs exactly")


def validate_outcomes(
    frame: SamplingFrame,
    draws: tuple[StratumDraw, ...],
    assignments: tuple[Assignment, ...],
    outcomes: tuple[Outcome, ...],
) -> None:
    """Require a fail-closed outcome for every selected-pair assignment."""

    validate_assignments(frame, draws, assignments)
    _require_tuple(outcomes, "outcomes")
    _, pairs, _ = _frame_maps(frame)
    assignments_by_id = {
        assignment.assignment_id: assignment for assignment in assignments
    }
    outcome_ids: set[str] = set()
    child_item_ids: set[str] = set()

    for index, outcome in enumerate(outcomes):
        _require_exact_record(outcome, Outcome, f"outcomes[{index}]")
        prefix = f"outcomes[{index}]"
        _require_id(outcome.assignment_id, f"{prefix}.assignment_id")
        _require_bool(outcome.parent_served, f"{prefix}.parent_served")
        _require_bool(
            outcome.parent_seen_in_background,
            f"{prefix}.parent_seen_in_background",
        )
        _require_nonnegative_int(
            outcome.feed_length_before,
            f"{prefix}.feed_length_before",
        )
        _require_nonnegative_int(
            outcome.feed_length_after,
            f"{prefix}.feed_length_after",
        )
        if outcome.feed_length_before != outcome.feed_length_after:
            raise ValueError("feed lengths must be equal before and after assignment")
        if outcome.assignment_id in outcome_ids:
            raise ValueError("outcomes must be unique by assignment ID")
        if outcome.assignment_id not in assignments_by_id:
            raise ValueError("outcome names an unknown assignment")
        outcome_ids.add(outcome.assignment_id)

        child_fields = (
            outcome.direct_child_item_id,
            outcome.direct_child_parent_id,
            outcome.child_author_agent_id,
            outcome.child_round,
        )
        child_present = [value is not None for value in child_fields]
        if any(child_present) and not all(child_present):
            raise ValueError(
                "child provenance fields must be all present or all absent"
            )

        assignment = assignments_by_id[outcome.assignment_id]
        pair = pairs[assignment.pair_id]
        has_child = all(child_present)
        if has_child:
            _require_id(outcome.direct_child_item_id, f"{prefix}.direct_child_item_id")
            _require_id(
                outcome.direct_child_parent_id,
                f"{prefix}.direct_child_parent_id",
            )
            _require_nonnegative_int(
                outcome.child_author_agent_id,
                f"{prefix}.child_author_agent_id",
            )
            _require_nonnegative_int(outcome.child_round, f"{prefix}.child_round")
            if outcome.direct_child_parent_id != pair.parent_item_id:
                raise ValueError("child parent does not match selected pair")
            if outcome.child_author_agent_id != pair.agent_id:
                raise ValueError("child author does not match selected recipient")
            if outcome.child_round != pair.round_id + OUTCOME_LAG_ROUNDS:
                raise ValueError("child round does not match the frozen outcome lag")
            if outcome.direct_child_item_id in child_item_ids:
                raise ValueError("direct child item IDs must be globally unique")
            child_item_ids.add(outcome.direct_child_item_id)

        if assignment.treated:
            if outcome.parent_served is not True:
                raise ValueError("treated assignment must verify parent service")
            if outcome.parent_seen_in_background is not False:
                raise ValueError("treated parent must not be duplicated in background")
        else:
            if outcome.parent_served is not False:
                raise ValueError("holdout assignment must not serve the parent")
            if outcome.parent_seen_in_background is not False:
                raise ValueError("holdout assignment must not leak the parent")
            if has_child:
                raise ValueError("holdout assignment must not produce a direct child")

    if outcome_ids != set(assignments_by_id):
        raise ValueError("outcomes must match assignments exactly")

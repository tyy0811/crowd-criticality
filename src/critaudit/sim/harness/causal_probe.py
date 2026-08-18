"""Pure design-based estimator for the frozen causal reply probe."""

from __future__ import annotations

import math

from .causal_probe_records import (
    Assignment,
    CandidatePair,
    Outcome,
    RReplyEstimate,
    SamplingFrame,
    StratumDraw,
)
from .causal_probe_spec import STATUS_DESIGN_ONLY
from .causal_probe_validation import (
    validate_assignments,
    validate_outcomes,
    validate_sampling_frame,
    validate_stratum_draws,
)

__all__ = (
    "deterministic_worst_case_variance_bound",
    "estimate_r_reply",
)


def _inclusion_probability(pair: CandidatePair) -> float:
    probability = pair.selection_probability * pair.treatment_probability
    if not math.isfinite(probability) or probability <= 0.0:
        raise ValueError(
            f"pair {pair.pair_id!r} has an invalid combined inclusion probability"
        )
    return probability


def deterministic_worst_case_variance_bound(frame: SamplingFrame) -> float:
    """Return the frozen all-pair design bound used for power calculation."""

    validate_sampling_frame(frame)
    parent_count = len(frame.parent_records)
    pair_terms = []
    for pair in frame.candidate_pairs:
        inclusion_probability = _inclusion_probability(pair)
        pair_terms.append((1.0 - inclusion_probability) / inclusion_probability)
    return math.fsum(pair_terms) / (parent_count * parent_count)


def estimate_r_reply(
    frame: SamplingFrame,
    draws: tuple[StratumDraw, ...],
    assignments: tuple[Assignment, ...],
    outcomes: tuple[Outcome, ...],
) -> RReplyEstimate:
    """Estimate full-frame mean direct-reply reproduction by HT totals.

    Frame provenance is deliberately outside this pure estimator. Integrated
    callers must validate and persist the frozen eligibility evidence before
    drawing assignments.
    """

    validate_sampling_frame(frame)
    validate_stratum_draws(frame, draws)
    validate_assignments(frame, draws, assignments)
    validate_outcomes(frame, draws, assignments, outcomes)

    pairs_by_id = {pair.pair_id: pair for pair in frame.candidate_pairs}
    outcomes_by_assignment_id = {
        outcome.assignment_id: outcome for outcome in outcomes
    }
    parent_count = len(frame.parent_records)
    ht_terms = []
    diagonal_terms = []
    response_count = 0

    for assignment in assignments:
        outcome = outcomes_by_assignment_id[assignment.assignment_id]
        has_response = outcome.direct_child_item_id is not None
        if not assignment.treated or not has_response:
            continue
        pair = pairs_by_id[assignment.pair_id]
        inclusion_probability = _inclusion_probability(pair)
        ht_terms.append(1.0 / inclusion_probability)
        diagonal_terms.append(
            (1.0 - inclusion_probability)
            / (inclusion_probability * inclusion_probability)
        )
        response_count += 1

    estimate = math.fsum(ht_terms) / parent_count
    estimated_diagonal_variance_bound = math.fsum(diagonal_terms) / (
        parent_count * parent_count
    )
    standard_error_conservative = math.sqrt(
        estimated_diagonal_variance_bound
    )
    ci_half_width = 1.96 * standard_error_conservative
    selected_count = sum(draw.selected_pair_id is not None for draw in draws)
    treated_count = sum(assignment.treated for assignment in assignments)

    return RReplyEstimate(
        frame_id=frame.frame_id,
        estimate=estimate,
        estimated_diagonal_variance_bound=estimated_diagonal_variance_bound,
        standard_error_conservative=standard_error_conservative,
        ci95_low=estimate - ci_half_width,
        ci95_high=estimate + ci_half_width,
        deterministic_worst_case_variance_bound=(
            deterministic_worst_case_variance_bound(frame)
        ),
        parent_count=parent_count,
        candidate_pair_count=len(frame.candidate_pairs),
        stratum_count=len({pair.stratum_id for pair in frame.candidate_pairs}),
        draw_count=len(draws),
        selected_count=selected_count,
        no_selection_count=len(draws) - selected_count,
        treated_count=treated_count,
        control_count=len(assignments) - treated_count,
        response_count=response_count,
        status=STATUS_DESIGN_ONLY,
    )

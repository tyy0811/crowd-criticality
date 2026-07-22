"""Frozen executable vocabulary for the OASIS causal-probe design."""

from critaudit.sim.harness import causal_probe_spec as spec


def test_registered_causal_probe_concepts_are_frozen():
    assert spec.SCHEMA_VERSION == 1
    assert spec.TREATMENT_PROBABILITY == 0.5
    assert spec.MAX_EXPERIMENTAL_PARENTS_PER_AGENT_ROUND == 1
    assert spec.OUTCOME_LAG_ROUNDS == 0
    assert spec.NEAR_CRITICAL_ABS_TOL == 0.05
    assert spec.STATUS_DESIGN_ONLY == "design_only"
    assert spec.STATUS_RECOVERABILITY_PASSED == "recoverability_passed"
    assert spec.STATUS_RECOVERABILITY_FAILED == "recoverability_failed"
    assert spec.ESTIMAND_NAME == "R_reply"


def test_branch_b_text_is_frozen_verbatim():
    assert spec.BRANCH_B_TEXT == (
        "Bank that no recoverable OASIS regime instrument is available; retain the "
        "classical locator and OASIS accessibility findings; restrict future analysis "
        "to observable knob-space and null confirmation without `n` placement or H1b."
    )


def test_r_reply_has_no_hawkes_n_symbol_alias():
    aliases = {
        name
        for name in spec.__all__
        if getattr(spec, name) == "R_reply"
    }
    assert aliases == {"ESTIMAND_NAME"}


def test_exact_public_surface_is_frozen():
    assert type(spec.__all__) is tuple
    assert spec.__all__ == (
        "SCHEMA_VERSION",
        "TREATMENT_PROBABILITY",
        "MAX_EXPERIMENTAL_PARENTS_PER_AGENT_ROUND",
        "OUTCOME_LAG_ROUNDS",
        "NEAR_CRITICAL_ABS_TOL",
        "STATUS_DESIGN_ONLY",
        "STATUS_RECOVERABILITY_PASSED",
        "STATUS_RECOVERABILITY_FAILED",
        "ESTIMAND_NAME",
        "REQUIRED_ASSIGNMENT_FIELDS",
        "REQUIRED_GATE_FIELDS",
        "BRANCH_B_TEXT",
    )


def test_required_assignment_fields_are_an_exact_immutable_tuple():
    assert type(spec.REQUIRED_ASSIGNMENT_FIELDS) is tuple
    assert spec.REQUIRED_ASSIGNMENT_FIELDS == (
        "assignment_id",
        "round_id",
        "agent_id",
        "parent_item_id",
        "filler_item_id",
        "selection_probability",
        "treatment_probability",
        "treated",
        "parent_first_readable_round",
    )


def test_required_gate_fields_are_an_exact_immutable_tuple():
    assert type(spec.REQUIRED_GATE_FIELDS) is tuple
    assert spec.REQUIRED_GATE_FIELDS == (
        "monotonicity_passed",
        "crossing_resolved",
        "near_critical_abs_error",
        "ci_precision_passed",
        "ci_coverage_passed",
        "chi_resp_coincidence_passed",
        "structural_failures",
    )

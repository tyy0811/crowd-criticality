"""Frozen executable vocabulary for the OASIS causal-probe design."""

SCHEMA_VERSION = 1

TREATMENT_PROBABILITY = 0.5
MAX_EXPERIMENTAL_PARENTS_PER_AGENT_ROUND = 1
OUTCOME_LAG_ROUNDS = 0
NEAR_CRITICAL_ABS_TOL = 0.05

STATUS_DESIGN_ONLY = "design_only"
STATUS_RECOVERABILITY_PASSED = "recoverability_passed"
STATUS_RECOVERABILITY_FAILED = "recoverability_failed"

ESTIMAND_NAME = "R_reply"

REQUIRED_ASSIGNMENT_FIELDS = (
    "assignment_id",
    "round",
    "agent_id",
    "native_parent_post_id",
    "filler_post_id",
    "selection_probability",
    "treatment_probability",
    "treatment_arm",
    "first_readable_round",
)

REQUIRED_GATE_FIELDS = (
    "monotonicity_passed",
    "crossing_resolved",
    "near_critical_abs_error",
    "ci_precision_passed",
    "ci_coverage_passed",
    "chi_resp_coincidence_passed",
    "structural_failures",
)

BRANCH_B_TEXT = (
    "Bank that no recoverable OASIS regime instrument is available; retain the "
    "classical locator and OASIS accessibility findings; restrict future analysis "
    "to observable knob-space and null confirmation without `n` placement or H1b."
)

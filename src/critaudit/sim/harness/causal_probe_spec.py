"""Frozen executable vocabulary for the OASIS causal-probe design."""

__all__ = (
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
    "SELECTED_SUPPORT",
    "POWER_ARTIFACT_PATH",
    "POWER_ARTIFACT_SHA256",
)

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
    "frame_id",
    "pair_id",
    "filler_item_id",
    "treated",
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

# Task-7A power freeze (2026-07-22; re-banked 2026-07-23 under the ALIGNED joint
# randomization law after owner review — power is now the probability that the
# gate's own statistic passes under the law the executed grid realizes): the
# smallest sufficient support selected by the banked exact-selector power
# calculation, and the SHA-256 of that artifact. The selection criteria were
# frozen result-blind BEFORE each banking and were not changed after reading.
SELECTED_SUPPORT = {"parent_count": 8192, "recipients_per_parent": 4}
POWER_ARTIFACT_PATH = "results/s4_causal_probe/2026-07-22_power_calculation.json"
POWER_ARTIFACT_SHA256 = (
    "b4091ab19cbffc90b6e508b9495fc147ad5a23e24b001148aa245054f63db660"
)

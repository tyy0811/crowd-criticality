"""FROZEN SPEC SURFACE for critaudit.cascades — the pre-registered, result-blind design constants.
A change to anything here is a change to the frozen spec, NOT a code tweak (the anti-drift contract at
file level). Extraction code in extract.py CONSUMES these; the calibration in calibrate.py FREEZES
TAU_Q_K by the rule below.

#3 (belief-update sequence) τ_q calibration — frozen BEFORE the sweep (Task 2), value AFTER (Task 5):
  metric         = ARI(recovered #3 per-event membership, generator root_id)   # clustering recovery
  pass threshold = RECOVERY_THRESHOLD
  selection rule = argmax of mean ARI over TAU_Q_GRID (k = bin width / median inter-event gap)
  TAU_Q_K        = the k the rule selects on the frozen synthetic (None until frozen in Task 5)
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class MergePolicy:
    single_membership: bool      # each event in exactly one cascade within a definition
    merge_within_definition: bool
    bin_edge: str                # #3 binning tie-break


MERGE_POLICY = MergePolicy(single_membership=True, merge_within_definition=False, bin_edge="left-closed")

RECOVERY_THRESHOLD = 0.90
TAU_Q_GRID = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0)   # k = bin width in median-inter-event-gap units
TAU_Q_K = None    # UNFROZEN BY DESIGN — NOT an unfilled placeholder. #3 timing-only recovery is
                  # calibration-blocked on the heavy-tail market regime (eps=0.35): no k clears
                  # RECOVERY_THRESHOLD because trees are temporally scale-free (a #3-recoverability
                  # finding). See DECISIONS.md 2026-06-24 + tests/test_cascades_calibrate.py. Do NOT
                  # freeze a value here without re-opening that finding (and never by lowering the threshold).

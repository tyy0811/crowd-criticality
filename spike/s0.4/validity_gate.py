"""The S0.4 validity gate: measured numbers -> a verdict on source-A accessibility.

Verdict axis = accessibility, not technical possibility (Yang & Tsang 2026 settled
possibility). "infeasible" is NOT an available verdict; an access-route artifact is a
wrong-tool signal, never a finding. A blocker must be a named access/cost/effort item.
"""
from __future__ import annotations

from dataclasses import dataclass

ALLOWED_BLOCKER_CATEGORIES = ("access", "cost", "effort")


@dataclass
class Verdict:
    status: str                  # "feasible" | "inadequate" | "blocked"
    granularity_ok: bool | None
    reconciliation_ok: bool | None
    detail: str


def classify(*, resolvable_timescale, t_threshold, reconciliation_ratio,
             expected_ratio, tolerance, blocker=None, blocker_category=None) -> Verdict:
    if blocker is not None:
        if blocker_category not in ALLOWED_BLOCKER_CATEGORIES:
            raise ValueError(
                f"a blocker must be one of {ALLOWED_BLOCKER_CATEGORIES}; got "
                f"{blocker_category!r}. 'technically infeasible' is NOT an available verdict "
                "(Yang & Tsang 2026 settled possibility). Re-route the access/wrong-tool "
                "artifact (indexer first); do not record it as a finding.")
        return Verdict("blocked", None, None, f"blocked ({blocker_category}): {blocker}")

    granularity_ok = resolvable_timescale >= t_threshold
    reconciliation_ok = abs(reconciliation_ratio - expected_ratio) <= tolerance
    if granularity_ok and reconciliation_ok:
        return Verdict("feasible", True, True,
                       f"resolvable timescale {resolvable_timescale} s >= T_threshold "
                       f"{t_threshold} s; reconciliation {reconciliation_ratio:.3f} within "
                       f"{tolerance} of expected {expected_ratio}")
    reasons = []
    if not granularity_ok:
        reasons.append(f"resolvable timescale {resolvable_timescale} s < T_threshold "
                       f"{t_threshold} s (2 s data too coarse for this market's dynamics)")
    if not reconciliation_ok:
        reasons.append(f"reconciliation {reconciliation_ratio:.3f} off expected "
                       f"{expected_ratio} by > {tolerance}")
    return Verdict("inadequate", granularity_ok, reconciliation_ok, "; ".join(reasons))

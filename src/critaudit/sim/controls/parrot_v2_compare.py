"""Task 6 (Branch-B parrot-null v2 implementation plan, 2026-07-31): the PURE comparison / guards /
verdict module. No I/O, no OASIS imports, no `check_positive_control`, no
`write_recoverability_artifact` — every function here is a total function of the replay payloads
(Task 5's output shape) it is handed.

Three width-keyed payloads (`triple = {width: payload}`) are compared four ways:

1. `manipulation_guard` — is the refresh ledger ITSELF trustworthy across widths? It pairs ledger
   entries by the immutable `schedule_index` (never by position or count, which a dropped/added
   entry would silently re-key) and requires the SAME `(schedule_index, agent_id, round)` skeleton
   at every index, plus outcome consistency (no `served`<->`empty` flip at an aligned index). An
   outcome flip shifts every later trace `seq` (the tolerated-empty refresh writes no trace row —
   Task 5 sec 3), which would forge an emission divergence unrelated to the recommender, so a flip
   is a guard failure — NEVER counted as realized contrast, no matter how many served-set
   differences also happened to be present. Only once the guard is clean does a served-vs-served
   set difference at an aligned index count as `realized_contrast` (the null's exposure manipulation
   actually fired).
2. `schedule_verdict` — is the manipulation-null's core claim true for THIS schedule: emission bytes
   AND the four `GATED_OBSERVABLES` (spec rev-5 sec4) identical across all three widths?
   `read_emit_ratio` is descriptive (an exposure diagnostic, not a crowd-behaviour observable) and is
   never part of equality.
3. `violator_verdict` — is the harness's own detection power confirmed, PAIRWISE, on this schedule:
   for every width pair where the ledger shows a REALIZED served-set difference, do the emission
   records actually differ? A pair with contrast but byte-identical records is a blind spot — the
   harness would not have caught a real manipulation on that pair — and is reported by name.
4. `overall_verdict` — folds many schedules' verdicts into one of three frozen readings (R1/R2/R3)
   under a precedence that is FROZEN, not tunable: any run failure, any guard failure, any guard
   that never saw a realized contrast, or any violator blind spot forces R3 even when some schedule
   ALSO shows an emission mismatch — a broken guard or an unconfirmed detector cannot be allowed to
   manufacture an R2 (manipulation-detected) reading out of evidence nothing actually validated.
"""
from __future__ import annotations

import itertools

from critaudit.sim.controls import parrot_v2_spec
from critaudit.sim.controls.parrot_v2_records import decode_emission_record
from critaudit.sim.harness.observables import GATED_OBSERVABLES

__all__ = ["manipulation_guard", "schedule_verdict", "violator_verdict", "overall_verdict"]

_EVENT_FIELDS = ("item_id", "time", "agent_id", "parent_item_id", "content", "seq")


def _guard_failure(failure: str) -> dict:
    return {"ok": False, "failure": failure, "realized_contrast": False,
            "paired_served_differences": 0}


def _ledger_by_index(triple: dict, widths: list) -> dict:
    """`{schedule_index: {width: ledger_entry}}` — the ONE place ledger entries are keyed by their
    immutable `schedule_index` rather than by position, so a dropped/reordered entry cannot silently
    re-pair against the wrong index."""
    by_index: dict = {}
    for w in widths:
        for entry in triple[w]["refresh_ledger"]:
            by_index.setdefault(entry["schedule_index"], {})[w] = entry
    return by_index


def manipulation_guard(triple: dict) -> dict:
    """Is the refresh ledger trustworthy across widths? See module docstring point 1."""
    widths = sorted(triple)

    if set(triple) != set(parrot_v2_spec.WIDTHS):
        return _guard_failure("width_mismatch")

    for w in widths:
        if triple[w]["width"] != w:
            return _guard_failure(f"width_mismatch:{w}")

    by_index = _ledger_by_index(triple, widths)

    for idx, per_width in by_index.items():
        if set(per_width) != set(widths):
            return _guard_failure(f"missing_entry:index={idx}")

    for idx in sorted(by_index):
        entries = [by_index[idx][w] for w in widths]
        if len({(e["agent_id"], e["round"]) for e in entries}) != 1:
            return _guard_failure(f"misaligned_skeleton:index={idx}")
        if len({e["outcome"] for e in entries}) != 1:
            return _guard_failure(f"outcome_flip:index={idx}")

    paired_served_differences = 0
    for a, b in itertools.combinations(widths, 2):
        for idx in by_index:
            ea, eb = by_index[idx][a], by_index[idx][b]
            if ea["outcome"] == "served" and eb["outcome"] == "served":
                if set(ea["served_item_ids"]) != set(eb["served_item_ids"]):
                    paired_served_differences += 1

    return {"ok": True, "failure": None,
            "realized_contrast": paired_served_differences > 0,
            "paired_served_differences": paired_served_differences}


def _first_emission_divergence(events_a: tuple, events_b: tuple, wa: int, wb: int) -> dict:
    if len(events_a) != len(events_b):
        return {"kind": "emission", "field": "length", "widths": (wa, wb),
                "values": (len(events_a), len(events_b))}
    for i, (ea, eb) in enumerate(zip(events_a, events_b)):
        if ea != eb:
            for field in _EVENT_FIELDS:
                va, vb = getattr(ea, field), getattr(eb, field)
                if va != vb:
                    return {"kind": "emission", "field": field, "index": i,
                            "widths": (wa, wb), "values": (va, vb)}
    raise AssertionError("_first_emission_divergence called on equal tuples")


def schedule_verdict(triple: dict) -> dict:
    """Is the manipulation-null's core claim true for this schedule? See module docstring point 2."""
    widths = sorted(triple)
    guard = manipulation_guard(triple)
    decoded = {w: decode_emission_record(triple[w]["emission_record_b64"]) for w in widths}

    ref = widths[0]
    invariant = True
    first_divergence = None

    for w in widths[1:]:
        if decoded[w] != decoded[ref]:
            invariant = False
            first_divergence = _first_emission_divergence(decoded[ref], decoded[w], ref, w)
            break

    if invariant:
        for key in GATED_OBSERVABLES:
            ref_val = triple[ref]["observables"][key]
            for w in widths[1:]:
                val = triple[w]["observables"][key]
                if val != ref_val:
                    invariant = False
                    first_divergence = {"kind": "observable", "field": key,
                                         "widths": (ref, w), "values": (ref_val, val)}
                    break
            if not invariant:
                break

    return {"invariant": invariant, "first_divergence": first_divergence, "guard": guard}


def violator_verdict(triple: dict) -> dict:
    """Is the harness's own detection power confirmed, pairwise? See module docstring point 3."""
    guard = manipulation_guard(triple)
    if not guard["ok"]:
        return {"ok": False, "reason": "guard"}

    widths = sorted(triple)
    by_index = _ledger_by_index(triple, widths)
    decoded = {w: decode_emission_record(triple[w]["emission_record_b64"]) for w in widths}

    for a, b in itertools.combinations(widths, 2):
        contrast = any(
            by_index[idx][a]["outcome"] == "served" and by_index[idx][b]["outcome"] == "served"
            and set(by_index[idx][a]["served_item_ids"]) != set(by_index[idx][b]["served_item_ids"])
            for idx in by_index
        )
        if contrast and decoded[a] == decoded[b]:
            return {"ok": False, "reason": f"blind_pair:({a},{b})"}

    return {"ok": True, "reason": None}


_NO_CONTRAST_DETAIL = "no realized exposure contrast; invalid for this schedule"


def overall_verdict(schedule_verdicts, violator_verdicts, run_failures=()) -> dict:
    """Fold many schedules' verdicts into one of three frozen readings. See module docstring
    point 4 — the precedence order below is FROZEN, not a design choice open to retuning."""
    if run_failures:
        return {"reading": "R3", "detail": f"run failures (verbatim): {tuple(run_failures)}"}

    bad_guards = [sv["guard"] for sv in schedule_verdicts if not sv["guard"]["ok"]]
    if bad_guards:
        return {"reading": "R3",
                "detail": f"manipulation guard failed: {bad_guards[0]['failure']}"}

    no_contrast = [sv["guard"] for sv in schedule_verdicts
                   if sv["guard"]["ok"] and not sv["guard"]["realized_contrast"]]
    if no_contrast:
        return {"reading": "R3", "detail": _NO_CONTRAST_DETAIL}

    bad_violators = [vv for vv in violator_verdicts if not vv["ok"]]
    if bad_violators:
        return {"reading": "R3",
                "detail": f"violator detection blind spot: {bad_violators[0]['reason']}"}

    if any(not sv["invariant"] for sv in schedule_verdicts):
        return {"reading": "R2",
                "detail": "emission/observable invariance broken under a clean, "
                          "contrast-confirmed guard"}

    return {"reading": "R1",
            "detail": "invariance held: guards contrastive, violator confirmed, no breaks"}

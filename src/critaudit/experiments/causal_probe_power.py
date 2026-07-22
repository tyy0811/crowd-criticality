"""Exact-selector prospective power surface for the causal reply probe (Task 7A).

All constants below are RESULT-BLIND freezes made before the artifact is generated;
none inspects project output. The simulation law is the exact frozen categorical
selector: every stratum holds exactly ``PAIRS_PER_SELECTION_STRATUM = 2`` candidate
pairs at ``PAIR_SELECTION_PROBABILITY = 0.40`` each (residual no-selection 0.20),
treatment exactly 0.5 only on selection.

Sufficient-statistic derivation (documented so the Monte Carlo is auditable): with
the uniform inclusion probability ``pi = 0.40 * 0.5 = 0.2`` and a FIXED binary
potential-response schedule, the Horvitz-Thompson estimate, its observed diagonal
variance bound, and the Wald interval are exact functions of the count ``K`` of
included live pairs. Selection is exclusive within a stratum, so a stratum with
exactly one live pair contributes Bernoulli(0.2) to ``K`` and a stratum with two
live pairs contributes Bernoulli(0.4) (never two). Hence
``K = Binomial(M1, 0.2) + Binomial(M2, 0.4)`` exactly, where ``M1``/``M2`` count
single-live/double-live strata of the fixed schedule. The test suite power-checks
this law against an independent per-stratum replay of the selector.

The observed diagonal bound is conservative: its expectation exceeds the true
sampling variance by ``2 * M2 / P^2 >= 0``, so measured coverage of the nominal
95% interval is expected at or above target — measured here, never assumed.
"""

from __future__ import annotations

import argparse
import json
import math
from statistics import NormalDist

import numpy as np

from critaudit.sim.controls.causal_probe_control import ControlTruth, PotentialResponse
from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_OPPORTUNITIES_PER_PARENT,
    MARKER_ROOT_COUNT,
    MARKER_ROUNDS,
    MARKER_SEEDS,
    PLANT_R_GRID,
)
from critaudit.sim.harness.causal_probe import deterministic_worst_case_variance_bound
from critaudit.sim.harness.causal_probe_records import (
    CandidatePair,
    ParentEligibility,
    SamplingFrame,
)
from critaudit.sim.harness.causal_probe_spec import (
    BRANCH_B_TEXT,
    NEAR_CRITICAL_ABS_TOL,
    SCHEMA_VERSION,
    TREATMENT_PROBABILITY,
)
from critaudit.sim.harness.causal_probe_validation import validate_sampling_frame

__all__ = (
    "TARGET_COVERAGE",
    "MAX_MEAN_CI_FULL_WIDTH",
    "TARGET_POWER",
    "MC_REPLICATES",
    "MC_WILSON_CONFIDENCE",
    "MC_MAX_HALF_WIDTH",
    "POWER_RNG_SEED",
    "PARENT_SUPPORT_CANDIDATES",
    "RECIPIENTS_PER_PARENT_CANDIDATES",
    "PLANT_R_GRID",
    "HELD_OUT_FRAMES_PER_CELL",
    "PAIRS_PER_SELECTION_STRATUM",
    "PAIR_SELECTION_PROBABILITY",
    "NEAR_CROSSING_PLANTS",
    "RECOVERABILITY_SEEDS",
    "POWER_SCHEDULE_SEEDS",
    "MARKER_SEEDS",
    "build_power_frame",
    "build_power_schedule",
    "build_power_artifact",
    "candidate_order",
    "select_smallest_sufficient_support",
    "simulate_fixed_schedule",
    "simulate_power_grid",
    "write_canonical_json",
    "write_power_artifact",
)

TARGET_COVERAGE = 0.95
MAX_MEAN_CI_FULL_WIDTH = 0.10  # 2 * NEAR_CRITICAL_ABS_TOL
TARGET_POWER = 0.80
MC_REPLICATES = 200_000
MC_WILSON_CONFIDENCE = 0.99
MC_MAX_HALF_WIDTH = 0.003
POWER_RNG_SEED = 20260722
PARENT_SUPPORT_CANDIDATES = (64, 128, 256, 512, 1024, 2048, 4096, 8192)
RECIPIENTS_PER_PARENT_CANDIDATES = (4, 8, 16)
HELD_OUT_FRAMES_PER_CELL = 12
PAIRS_PER_SELECTION_STRATUM = 2
PAIR_SELECTION_PROBABILITY = 0.40  # residual no-selection probability 0.20
NEAR_CROSSING_PLANTS = (PLANT_R_GRID[2], PLANT_R_GRID[3])
RECOVERABILITY_SEEDS = (
    2026072201, 2026072202, 2026072203, 2026072204,
    2026072205, 2026072206, 2026072207, 2026072208,
    2026072209, 2026072210, 2026072211, 2026072212,
)
POWER_SCHEDULE_SEEDS = (
    2026072101, 2026072102, 2026072103, 2026072104,
    2026072105, 2026072106, 2026072107, 2026072108,
    2026072109, 2026072110, 2026072111, 2026072112,
)

# Namespaced SeedSequence streams
POWER_STREAM_SCHEDULE = 931
POWER_STREAM_REPLICATES = 932

_WALD_Z = 1.96

_FRAME_CACHE: dict = {}


def candidate_order():
    """Frozen candidate selection order: ascending total pair count, then parent
    count, then recipients per parent."""
    candidates = [
        (parents, recipients)
        for parents in PARENT_SUPPORT_CANDIDATES
        for recipients in RECIPIENTS_PER_PARENT_CANDIDATES
    ]
    return sorted(candidates, key=lambda c: (c[0] * c[1], c[0], c[1]))


def build_power_frame(parent_count: int, recipients_per_parent: int) -> SamplingFrame:
    """Deterministic closed-form layout: parent i = post:i+1 by author agent i in
    round 0; every stratum holds one pair each of two DISTINCT parents (2t, 2t+1)
    at the frozen selection probability; one unique recipient agent per stratum."""
    key = (int(parent_count), int(recipients_per_parent))
    if key in _FRAME_CACHE:
        return _FRAME_CACHE[key]
    parent_count, recipients_per_parent = key
    if parent_count < 2 or parent_count % 2:
        raise ValueError("power frames need an even parent count >= 2")
    strata_per_slot = parent_count // 2
    parents = tuple(
        ParentEligibility(f"post:{i + 1}", author_agent_id=i, created_round=0)
        for i in range(parent_count)
    )
    pairs = []
    for slot in range(recipients_per_parent):
        for t in range(strata_per_slot):
            agent_id = parent_count + slot * strata_per_slot + t
            stratum_id = f"agent:{agent_id}:round:1"
            for member in (2 * t, 2 * t + 1):
                pairs.append(CandidatePair(
                    pair_id=f"pair:{member + 1}:{slot + 1}",
                    parent_item_id=f"post:{member + 1}",
                    agent_id=agent_id,
                    round_id=1,
                    stratum_id=stratum_id,
                    selection_probability=PAIR_SELECTION_PROBABILITY,
                    treatment_probability=TREATMENT_PROBABILITY,
                    parent_first_readable_round=1,
                    prior_exposure_count=0,
                    complete_same_action_opportunity=True,
                ))
    # The exclusion registry's LAST TWO entries are the filler author and the
    # dedicated news user — the registered convention the scripted-control bridge
    # derives its agent layout from — allocated contiguously after the recipients
    # so the frame is directly runnable through run_scripted_oasis_control.
    filler_author = parent_count + recipients_per_parent * strata_per_slot
    frame = SamplingFrame(
        frame_id=f"frame:power:{parent_count}x{recipients_per_parent}",
        parent_records=parents,
        excluded_recipient_agent_ids=(
            tuple(range(parent_count)) + (filler_author, filler_author + 1)),
        candidate_pairs=tuple(pairs),
    )
    validate_sampling_frame(frame)
    _FRAME_CACHE[key] = frame
    return frame


def build_power_schedule(frame: SamplingFrame, plant_r: float, schedule_seed: int) -> ControlTruth:
    """Draw ONE fixed binary potential-response schedule for the frame before any
    replicate; the schedule is never resampled inside the replicate loop."""
    parent_count = len(frame.parent_records)
    recipients_per_parent = len(frame.candidate_pairs) // parent_count
    response_probability = float(plant_r) / recipients_per_parent
    if not 0.0 <= response_probability <= 1.0 or not math.isfinite(response_probability):
        raise ValueError(
            f"response_probability = plant_r / recipients_per_parent must lie in "
            f"[0, 1], got {response_probability}")
    rng = np.random.default_rng(
        np.random.SeedSequence(int(schedule_seed), spawn_key=(POWER_STREAM_SCHEDULE,)))
    live = rng.random(len(frame.candidate_pairs)) < response_probability
    potential = tuple(
        PotentialResponse(
            pair_id=pair.pair_id,
            response_probability=response_probability,
            potential_response=bool(flag),
        )
        for pair, flag in zip(frame.candidate_pairs, live)
    )
    live_per_parent: dict = {}
    for pair, flag in zip(frame.candidate_pairs, live):
        live_per_parent[pair.parent_item_id] = (
            live_per_parent.get(pair.parent_item_id, 0) + int(flag))
    r_gen_frame = math.fsum(
        live_per_parent.get(parent.parent_item_id, 0)
        for parent in frame.parent_records) / parent_count
    return ControlTruth(
        frame_id=frame.frame_id,
        r_plant=response_probability * recipients_per_parent,
        r_gen_frame=r_gen_frame,
        potential_responses=potential,
    )


def _wilson_interval(successes: float, trials: int, confidence: float):
    z = NormalDist().inv_cdf(1.0 - (1.0 - confidence) / 2.0)
    if trials <= 0:
        raise ValueError("Wilson interval needs a positive trial count")
    p = successes / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    half = (
        z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
        / denominator)
    return center - half, center + half, half


def simulate_fixed_schedule(frame: SamplingFrame, truth: ControlTruth,
                            replicates: int, seed: int):
    """Exact law of the frozen categorical selector over one fixed schedule, via
    the sufficient statistic K = Binomial(M1, pi) + Binomial(M2, 2*pi)."""
    if truth.frame_id != frame.frame_id:
        raise ValueError("schedule truth does not belong to the supplied frame")
    parent_count = len(frame.parent_records)
    live_by_pair = {
        row.pair_id: row.potential_response for row in truth.potential_responses}
    if set(live_by_pair) != {pair.pair_id for pair in frame.candidate_pairs}:
        raise ValueError("schedule truth does not cover exactly the frame pairs")

    inclusion = None
    live_per_stratum: dict = {}
    for pair in frame.candidate_pairs:
        pair_inclusion = pair.selection_probability * pair.treatment_probability
        if inclusion is None:
            inclusion = pair_inclusion
        elif pair_inclusion != inclusion:
            raise ValueError(
                "the sufficient-statistic sampler requires the uniform frozen "
                "inclusion probability")
        counts = live_per_stratum.setdefault(pair.stratum_id, [0, 0])
        counts[0] += 1
        counts[1] += int(live_by_pair[pair.pair_id])
    for stratum_id, (n_pairs, _) in live_per_stratum.items():
        if n_pairs != PAIRS_PER_SELECTION_STRATUM:
            raise ValueError(
                f"stratum {stratum_id!r} does not hold exactly "
                f"{PAIRS_PER_SELECTION_STRATUM} pairs")

    single_live = sum(1 for _, live in live_per_stratum.values() if live == 1)
    double_live = sum(1 for _, live in live_per_stratum.values() if live == 2)

    replicates = int(replicates)
    rng = np.random.default_rng(
        np.random.SeedSequence(int(seed), spawn_key=(POWER_STREAM_REPLICATES,)))
    included = (
        rng.binomial(single_live, inclusion, replicates)
        + rng.binomial(double_live, 2.0 * inclusion, replicates))

    weight = 1.0 / inclusion / parent_count
    estimates = included * weight
    diagonal = included * ((1.0 - inclusion) / (inclusion * inclusion)) / (
        parent_count * parent_count)
    half_widths = _WALD_Z * np.sqrt(diagonal)
    covered = np.abs(estimates - truth.r_gen_frame) <= half_widths
    coverage = float(covered.mean())
    wilson_low, wilson_high, wilson_half = _wilson_interval(
        float(covered.sum()), replicates, MC_WILSON_CONFIDENCE)
    return {
        "parent_count": parent_count,
        "recipients_per_parent": len(frame.candidate_pairs) // parent_count,
        "plant_r": truth.r_plant,
        "r_plant": truth.r_plant,
        "r_gen_frame": truth.r_gen_frame,
        "replicates": replicates,
        "live_single_strata": int(single_live),
        "live_double_strata": int(double_live),
        "coverage": coverage,
        "coverage_wilson_low": wilson_low,
        "coverage_wilson_high": wilson_high,
        "coverage_wilson_half_width": wilson_half,
        "mean_full_ci_width": float((2.0 * half_widths).mean()),
        "zero_response_frequency": float((included == 0).mean()),
        "mean_estimate": float(estimates.mean()),
        "mc_estimate_sd": float(estimates.std()),
        "bias": float(estimates.mean()) - truth.r_gen_frame,
        "deterministic_worst_case_variance_bound": (
            deterministic_worst_case_variance_bound(frame)),
    }


def simulate_power_grid(parent_count: int, recipients_per_parent: int,
                        plant_r_grid, potential_schedule_seeds,
                        replicates: int, seed: int):
    """Fixed-schedule simulations for every registered plant and predeclared
    schedule seed, plus held-out cohort ordering/crossing/error evaluation."""
    plant_r_grid = tuple(plant_r_grid)
    schedule_seeds = tuple(potential_schedule_seeds)
    structural_failures = 0
    failure_notes = []
    frame = build_power_frame(parent_count, recipients_per_parent)

    cells = []
    for cell_index, plant_r in enumerate(plant_r_grid):
        per_schedule = []
        for seed_index, schedule_seed in enumerate(schedule_seeds):
            try:
                truth = build_power_schedule(frame, plant_r, schedule_seed)
                replicate_seed = int(np.random.SeedSequence(
                    int(seed), spawn_key=(cell_index, seed_index)
                ).generate_state(1)[0])
                result = simulate_fixed_schedule(
                    frame, truth, replicates, replicate_seed)
                result["schedule_seed"] = int(schedule_seed)
                per_schedule.append(result)
            except (ValueError, TypeError) as exc:
                structural_failures += 1
                failure_notes.append(
                    f"cell {plant_r} seed {schedule_seed}: {exc}")
        n_ok = len(per_schedule)
        pooled_trials = sum(r["replicates"] for r in per_schedule)
        pooled_successes = math.fsum(
            r["coverage"] * r["replicates"] for r in per_schedule)
        if n_ok and pooled_trials:
            _, _, pooled_half = _wilson_interval(
                pooled_successes, pooled_trials, MC_WILSON_CONFIDENCE)
            cells.append({
                "plant_r": plant_r,
                "per_schedule": per_schedule,
                "coverage": pooled_successes / pooled_trials,
                "coverage_wilson_half_width": pooled_half,
                "mean_full_ci_width": math.fsum(
                    r["mean_full_ci_width"] for r in per_schedule) / n_ok,
                "zero_response_frequency": math.fsum(
                    r["zero_response_frequency"] for r in per_schedule) / n_ok,
                "mean_bias": math.fsum(r["bias"] for r in per_schedule) / n_ok,
            })
        else:
            cells.append({"plant_r": plant_r, "per_schedule": per_schedule})

    cohorts = []
    passing = 0
    for schedule_seed in schedule_seeds:
        means = []
        complete = True
        for cell in cells:
            row = next(
                (r for r in cell.get("per_schedule", [])
                 if r["schedule_seed"] == int(schedule_seed)), None)
            if row is None:
                complete = False
                break
            means.append(row["mean_estimate"])
        if not complete:
            structural_failures += 1
            failure_notes.append(f"incomplete cohort for seed {schedule_seed}")
            continue
        strictly_increasing = all(a < b for a, b in zip(means, means[1:]))
        crossings = [
            index for index, (a, b) in enumerate(zip(means, means[1:]))
            if (a < 1.0 <= b) or (a >= 1.0 > b)
        ]
        crossing_interval = (
            [plant_r_grid[crossings[0]], plant_r_grid[crossings[0] + 1]]
            if len(crossings) == 1 else None)
        near_errors = {}
        near_ok = True
        for plant_r, mean in zip(plant_r_grid, means):
            if plant_r in NEAR_CROSSING_PLANTS:
                error = abs(mean - plant_r)
                near_errors[str(plant_r)] = error
                near_ok = near_ok and error <= NEAR_CRITICAL_ABS_TOL
        passed = strictly_increasing and len(crossings) == 1 and near_ok
        passing += int(passed)
        cohorts.append({
            "schedule_seed": int(schedule_seed),
            "mean_estimates": means,
            "strictly_increasing": strictly_increasing,
            "crossing_count": len(crossings),
            "crossing_interval": crossing_interval,
            "near_crossing_errors": near_errors,
            "near_crossing_errors_ok": near_ok,
            "passed": passed,
        })

    return {
        "parent_count": int(parent_count),
        "recipients_per_parent": int(recipients_per_parent),
        "total_pairs": int(parent_count) * int(recipients_per_parent),
        "cells": cells,
        "cohorts": cohorts,
        "power": passing / len(schedule_seeds) if schedule_seeds else 0.0,
        "structural_failures": structural_failures,
        "failure_notes": failure_notes,
    }


def _candidate_passes(result):
    if result["structural_failures"] != 0:
        return False
    if result["power"] < TARGET_POWER:
        return False
    for cell in result["cells"]:
        if "coverage" not in cell:
            return False
        if cell["coverage"] < TARGET_COVERAGE:
            return False
        if cell["mean_full_ci_width"] > MAX_MEAN_CI_FULL_WIDTH:
            return False
        if cell["coverage_wilson_half_width"] > MC_MAX_HALF_WIDTH:
            return False
    return True


def select_smallest_sufficient_support(results):
    """First passing candidate in the frozen order; None activates Branch B."""
    results = tuple(results)
    keys = [
        (r["parent_count"] * r["recipients_per_parent"],
         r["parent_count"], r["recipients_per_parent"])
        for r in results
    ]
    if keys != sorted(keys):
        raise ValueError("candidate results are out of the frozen selection order")
    for result in results:
        if _candidate_passes(result):
            return {
                "parent_count": result["parent_count"],
                "recipients_per_parent": result["recipients_per_parent"],
            }
    return None


def build_power_artifact():
    """The complete deterministic power surface over every registered candidate."""
    results = tuple(
        simulate_power_grid(parents, recipients, PLANT_R_GRID,
                            POWER_SCHEDULE_SEEDS, MC_REPLICATES, POWER_RNG_SEED)
        for parents, recipients in candidate_order()
    )
    selected = select_smallest_sufficient_support(results)
    return {
        "schema_version": SCHEMA_VERSION,
        "registered_constants": {
            "TARGET_COVERAGE": TARGET_COVERAGE,
            "MAX_MEAN_CI_FULL_WIDTH": MAX_MEAN_CI_FULL_WIDTH,
            "TARGET_POWER": TARGET_POWER,
            "MC_REPLICATES": MC_REPLICATES,
            "MC_WILSON_CONFIDENCE": MC_WILSON_CONFIDENCE,
            "MC_MAX_HALF_WIDTH": MC_MAX_HALF_WIDTH,
            "POWER_RNG_SEED": POWER_RNG_SEED,
            "PARENT_SUPPORT_CANDIDATES": list(PARENT_SUPPORT_CANDIDATES),
            "RECIPIENTS_PER_PARENT_CANDIDATES": list(
                RECIPIENTS_PER_PARENT_CANDIDATES),
            "PLANT_R_GRID": list(PLANT_R_GRID),
            "HELD_OUT_FRAMES_PER_CELL": HELD_OUT_FRAMES_PER_CELL,
            "PAIRS_PER_SELECTION_STRATUM": PAIRS_PER_SELECTION_STRATUM,
            "PAIR_SELECTION_PROBABILITY": PAIR_SELECTION_PROBABILITY,
            "NEAR_CROSSING_PLANTS": list(NEAR_CROSSING_PLANTS),
            "NEAR_CRITICAL_ABS_TOL": NEAR_CRITICAL_ABS_TOL,
            "POWER_SCHEDULE_SEEDS": list(POWER_SCHEDULE_SEEDS),
            "RECOVERABILITY_SEEDS": list(RECOVERABILITY_SEEDS),
            "MARKER_SEEDS": list(MARKER_SEEDS),
            "MARKER_ROOT_COUNT": MARKER_ROOT_COUNT,
            "MARKER_OPPORTUNITIES_PER_PARENT": MARKER_OPPORTUNITIES_PER_PARENT,
            "MARKER_ROUNDS": MARKER_ROUNDS,
        },
        "candidate_order": [list(candidate) for candidate in candidate_order()],
        "candidates": list(results),
        "selected_support": selected,
        "branch_b_activation": None if selected is not None else BRANCH_B_TEXT,
    }


def write_canonical_json(path: str, payload) -> None:
    with open(path, "w") as handle:
        json.dump(payload, handle, allow_nan=False, ensure_ascii=False,
                  separators=(",", ":"), sort_keys=True)
        handle.write("\n")


def write_power_artifact(path: str) -> None:
    write_canonical_json(path, build_power_artifact())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Frozen $0 exact-selector power calculation (design only)")
    parser.add_argument("--write", required=True,
                        help="output path for the canonical power artifact")
    arguments = parser.parse_args(argv)
    write_power_artifact(arguments.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

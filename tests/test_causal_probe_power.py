from __future__ import annotations

import json
import math

import numpy as np
import pytest

from critaudit.experiments.causal_probe_power import (
    HELD_OUT_FRAMES_PER_CELL,
    MAX_MEAN_CI_FULL_WIDTH,
    MC_MAX_HALF_WIDTH,
    MC_REPLICATES,
    MC_WILSON_CONFIDENCE,
    NEAR_CROSSING_PLANTS,
    PAIR_SELECTION_PROBABILITY,
    PAIRS_PER_SELECTION_STRATUM,
    PARENT_SUPPORT_CANDIDATES,
    POWER_RNG_SEED,
    POWER_SCHEDULE_SEEDS,
    RECIPIENTS_PER_PARENT_CANDIDATES,
    RECOVERABILITY_SEEDS,
    TARGET_COVERAGE,
    TARGET_POWER,
    build_power_frame,
    build_power_schedule,
    candidate_order,
    select_smallest_sufficient_support,
    simulate_fixed_schedule,
    simulate_power_grid,
    write_canonical_json,
)
from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_OPPORTUNITIES_PER_PARENT,
    MARKER_ROOT_COUNT,
    MARKER_ROUNDS,
    MARKER_SEEDS,
    PLANT_R_GRID,
)
from critaudit.sim.harness.causal_probe import deterministic_worst_case_variance_bound
from critaudit.sim.harness.causal_probe_validation import validate_sampling_frame


# --- frozen result-blind constants -------------------------------------------------------------


def test_power_constants_are_frozen():
    assert TARGET_COVERAGE == 0.95
    assert MAX_MEAN_CI_FULL_WIDTH == 0.10
    assert TARGET_POWER == 0.80
    assert MC_REPLICATES == 200_000
    assert MC_WILSON_CONFIDENCE == 0.99
    assert MC_MAX_HALF_WIDTH == 0.003
    assert POWER_RNG_SEED == 20260722
    assert PARENT_SUPPORT_CANDIDATES == (64, 128, 256, 512, 1024, 2048, 4096, 8192)
    assert RECIPIENTS_PER_PARENT_CANDIDATES == (4, 8, 16)
    assert PLANT_R_GRID == (0.60, 0.92, 0.97, 1.03, 1.08, 1.30)
    assert HELD_OUT_FRAMES_PER_CELL == 12
    assert PAIRS_PER_SELECTION_STRATUM == 2
    assert PAIR_SELECTION_PROBABILITY == 0.40
    assert NEAR_CROSSING_PLANTS == (0.97, 1.03)
    assert RECOVERABILITY_SEEDS == tuple(2026072201 + k for k in range(12))
    assert POWER_SCHEDULE_SEEDS == tuple(2026072101 + k for k in range(12))
    assert MARKER_SEEDS == tuple(2026072401 + k for k in range(12))
    assert MARKER_ROOT_COUNT == 512
    assert MARKER_OPPORTUNITIES_PER_PARENT == 4
    assert MARKER_ROUNDS == 8


def test_candidate_order_ascends_pairs_then_parents_then_recipients():
    order = candidate_order()
    assert len(order) == len(PARENT_SUPPORT_CANDIDATES) * len(
        RECIPIENTS_PER_PARENT_CANDIDATES)
    keys = [(p * r, p, r) for p, r in order]
    assert keys == sorted(keys)
    assert order[0] == (64, 4)
    # tie at 512 pairs: the smaller parent count precedes
    assert order.index((64, 8)) < order.index((128, 4))
    assert order[-1] == (8192, 16)


# --- frame layout and fixed potential schedules ------------------------------------------------


def test_power_frame_layout_is_valid_and_uniform():
    frame = build_power_frame(64, 4)
    validate_sampling_frame(frame)
    assert len(frame.parent_records) == 64
    assert len(frame.candidate_pairs) == 256
    strata = {}
    for pair in frame.candidate_pairs:
        assert pair.selection_probability == PAIR_SELECTION_PROBABILITY
        assert pair.treatment_probability == 0.5
        strata.setdefault(pair.stratum_id, []).append(pair.parent_item_id)
    assert all(len(parents) == PAIRS_PER_SELECTION_STRATUM for parents in strata.values())
    assert all(len(set(parents)) == 2 for parents in strata.values())


def test_power_schedule_is_fixed_and_deterministic():
    frame = build_power_frame(64, 4)
    truth_a = build_power_schedule(frame, 1.03, POWER_SCHEDULE_SEEDS[0])
    truth_b = build_power_schedule(frame, 1.03, POWER_SCHEDULE_SEEDS[0])
    truth_c = build_power_schedule(frame, 1.03, POWER_SCHEDULE_SEEDS[1])
    assert truth_a == truth_b
    assert truth_a != truth_c
    assert truth_a.r_plant == pytest.approx(1.03)
    assert all(
        row.response_probability == pytest.approx(1.03 / 4)
        for row in truth_a.potential_responses
    )


def test_out_of_range_schedule_fails_closed():
    frame = build_power_frame(64, 4)
    with pytest.raises(ValueError, match="response_probability"):
        build_power_schedule(frame, 4.5, POWER_SCHEDULE_SEEDS[0])


# --- exact-selector simulation -----------------------------------------------------------------


def test_simulate_fixed_schedule_is_deterministic_and_complete():
    frame = build_power_frame(64, 4)
    truth = build_power_schedule(frame, 1.03, POWER_SCHEDULE_SEEDS[0])
    result_a = simulate_fixed_schedule(frame, truth, 20_000, 11)
    result_b = simulate_fixed_schedule(frame, truth, 20_000, 11)
    assert result_a == result_b
    for key in (
        "coverage", "coverage_wilson_low", "coverage_wilson_high",
        "coverage_wilson_half_width", "mean_full_ci_width",
        "zero_response_frequency", "mean_estimate", "bias", "r_gen_frame",
        "r_plant", "replicates", "deterministic_worst_case_variance_bound",
    ):
        assert key in result_a
    assert 0.0 <= result_a["coverage"] <= 1.0
    assert result_a["replicates"] == 20_000
    assert result_a["deterministic_worst_case_variance_bound"] == pytest.approx(
        deterministic_worst_case_variance_bound(frame))
    # the estimator is unbiased for the schedule's hidden R_gen_frame
    assert abs(result_a["bias"]) < 0.05


def test_schedule_is_held_fixed_across_replicates():
    """Resampling potential responses inside replicates is forbidden: the MC mean must
    match THIS schedule's hidden R_gen_frame, not the ensemble R_plant."""
    frame = build_power_frame(64, 4)
    # find a seed whose realized R_gen_frame is visibly far from R_plant
    for seed in POWER_SCHEDULE_SEEDS:
        truth = build_power_schedule(frame, 0.60, seed)
        if abs(truth.r_gen_frame - truth.r_plant) > 0.05:
            break
    else:
        pytest.skip("no held-out schedule with a visible R_gen/R_plant gap")
    result = simulate_fixed_schedule(frame, truth, 50_000, 13)
    assert abs(result["mean_estimate"] - truth.r_gen_frame) < 0.02
    assert abs(result["mean_estimate"] - truth.r_plant) > 0.03


def test_simulate_matches_bruteforce_exact_selector():
    """Independent per-stratum replay of the frozen categorical selector: the
    module's sufficient-statistic sampler must reproduce the same law."""
    frame = build_power_frame(8, 4)
    truth = build_power_schedule(frame, 1.03, POWER_SCHEDULE_SEEDS[2])
    result = simulate_fixed_schedule(frame, truth, 200_000, 17)

    live = {row.pair_id for row in truth.potential_responses if row.potential_response}
    strata = {}
    for pair in frame.candidate_pairs:
        strata.setdefault(pair.stratum_id, []).append(pair)
    parent_count = len(frame.parent_records)
    rng = np.random.default_rng(1234)
    replicates = 200_000
    estimates = np.zeros(replicates)
    for stratum_pairs in strata.values():
        u = rng.random(replicates)
        t = rng.random(replicates)
        for index, pair in enumerate(stratum_pairs):
            if pair.pair_id not in live:
                continue
            low = index * PAIR_SELECTION_PROBABILITY
            high = low + PAIR_SELECTION_PROBABILITY
            included = (u >= low) & (u < high) & (t < pair.treatment_probability)
            estimates += included / (
                pair.selection_probability * pair.treatment_probability)
    estimates /= parent_count
    assert result["mean_estimate"] == pytest.approx(estimates.mean(), abs=0.02)
    assert result["zero_response_frequency"] == pytest.approx(
        float((estimates == 0).mean()), abs=0.01)
    module_sd = result["mc_estimate_sd"]
    assert module_sd == pytest.approx(float(estimates.std()), rel=0.05)


# --- grid, aligned-law power, and support selection --------------------------------------------


def test_simulate_power_grid_structure():
    grid = simulate_power_grid(64, 4, PLANT_R_GRID, POWER_SCHEDULE_SEEDS[:3],
                               5_000, POWER_RNG_SEED)
    assert grid["parent_count"] == 64
    assert grid["recipients_per_parent"] == 4
    assert grid["total_pairs"] == 256
    assert len(grid["cells"]) == 6
    for cell, plant_r in zip(grid["cells"], PLANT_R_GRID):
        assert cell["plant_r"] == plant_r
        assert len(cell["per_schedule"]) == 3
    # the fixed-schedule cohort diagnostics remain DESCRIPTIVE records
    assert len(grid["fixed_schedule_cohorts"]) == 3
    for cohort in grid["fixed_schedule_cohorts"]:
        assert set(cohort) >= {
            "schedule_seed", "mean_estimates", "strictly_increasing",
            "crossing_count", "crossing_interval", "near_crossing_errors_ok",
            "passed",
        }
    # power itself is banked under the ALIGNED joint law
    assert 0.0 <= grid["power"] <= 1.0
    assert grid["power"] == grid["grid_power"]
    assert grid["grid_power_replicates"] == 5_000
    assert grid["grid_power_wilson_half_width"] > 0.0
    assert grid["structural_failures"] == 0


def test_grid_power_uses_the_aligned_joint_law():
    """Power must be the probability that the GATE'S OWN statistic — the per-cell
    mean of 12 SINGLE-realization estimates on freshly drawn schedules — passes
    the scientific clauses. Cross-check the module's sufficient-statistic grid
    sampler against an independent brute-force replay of the joint law."""
    from critaudit.experiments.causal_probe_power import simulate_grid_power

    parent_count, recipients = 64, 4
    result = simulate_grid_power(parent_count, recipients, PLANT_R_GRID,
                                 12, 50_000, 20260722)
    assert set(result) >= {"grid_power", "grid_power_wilson_half_width",
                          "grid_power_replicates", "clause_pass_rates"}

    rng = np.random.default_rng(99)
    strata = parent_count * recipients // 2
    replicates = 50_000
    passes = 0
    for _ in range(replicates):
        means = []
        for plant_r in PLANT_R_GRID:
            q = plant_r / recipients
            live = rng.multinomial(
                strata, ((1 - q) ** 2, 2 * q * (1 - q), q * q), size=12)
            included = rng.binomial(live[:, 1], 0.2) + rng.binomial(
                live[:, 2], 0.4)
            means.append(float((included * 5.0 / parent_count).mean()))
        increasing = all(a < b for a, b in zip(means, means[1:]))
        crossings = sum(
            1 for a, b in zip(means, means[1:])
            if (a < 1.0 <= b) or (a >= 1.0 > b))
        near_ok = all(
            abs(mean - plant_r) <= 0.05
            for mean, plant_r in zip(means, PLANT_R_GRID)
            if plant_r in NEAR_CROSSING_PLANTS)
        passes += int(increasing and crossings == 1 and near_ok)
    brute = passes / replicates
    assert result["grid_power"] == pytest.approx(brute, abs=0.02)


def _fake_result(parent_count, recipients, *, coverage=0.99, width=0.05,
                 power=1.0, half_width=0.001, failures=0):
    return {
        "parent_count": parent_count,
        "recipients_per_parent": recipients,
        "total_pairs": parent_count * recipients,
        "cells": [
            {
                "plant_r": plant_r,
                "coverage": coverage,
                "mean_full_ci_width": width,
                "coverage_wilson_half_width": half_width,
            }
            for plant_r in PLANT_R_GRID
        ],
        "power": power,
        "grid_power": power,
        "grid_power_wilson_half_width": 0.001,
        "structural_failures": failures,
    }


def test_select_smallest_sufficient_support_picks_first_passing():
    results = (
        _fake_result(64, 4, width=0.5),
        _fake_result(64, 8, coverage=0.90),
        _fake_result(128, 4, power=0.5),
        _fake_result(128, 8),
        _fake_result(256, 4),
    )
    assert select_smallest_sufficient_support(results) == {
        "parent_count": 128,
        "recipients_per_parent": 8,
    }


def test_select_smallest_sufficient_support_branch_b_on_no_pass():
    results = (
        _fake_result(64, 4, width=0.5),
        _fake_result(64, 8, failures=1),
    )
    assert select_smallest_sufficient_support(results) is None


def test_select_smallest_sufficient_support_rejects_disorder():
    with pytest.raises(ValueError, match="order"):
        select_smallest_sufficient_support(
            (_fake_result(128, 4), _fake_result(64, 4)))


# --- canonical writer --------------------------------------------------------------------------


def test_write_canonical_json_is_deterministic(tmp_path):
    payload = {"b": [1.5, 2.25], "a": {"nested": True}}
    path_a = str(tmp_path / "a.json")
    path_b = str(tmp_path / "b.json")
    write_canonical_json(path_a, payload)
    write_canonical_json(path_b, payload)
    with open(path_a, "rb") as handle_a, open(path_b, "rb") as handle_b:
        bytes_a, bytes_b = handle_a.read(), handle_b.read()
    assert bytes_a == bytes_b
    assert json.loads(bytes_a) == payload
    with pytest.raises(ValueError):
        write_canonical_json(str(tmp_path / "c.json"), {"x": math.nan})

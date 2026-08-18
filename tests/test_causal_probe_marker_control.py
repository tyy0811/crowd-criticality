from __future__ import annotations

import dataclasses
import math

import pytest

from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_OPPORTUNITIES_PER_PARENT,
    MARKER_ROOT_COUNT,
    MARKER_ROUND_OFFSET,
    MARKER_ROUNDS,
    MARKER_SEEDS,
    MARKER_SEED_STREAM,
    PLANT_R_GRID,
    ChiPeak,
    MarkerControlResult,
    MarkerGridCell,
    MarkerManifest,
    aggregate_marker_cell,
    compute_chi_resp,
    locate_chi_peak,
    run_recursive_marker_control,
)


# --- frozen registry --------------------------------------------------------------------------


def test_marker_registry_is_frozen():
    assert MARKER_SEEDS == tuple(2026072401 + k for k in range(12))
    assert len(set(MARKER_SEEDS)) == 12
    assert PLANT_R_GRID == (0.60, 0.92, 0.97, 1.03, 1.08, 1.30)
    assert MARKER_ROOT_COUNT == 512
    assert MARKER_OPPORTUNITIES_PER_PARENT == 4
    assert MARKER_ROUNDS == 8
    assert MARKER_SEED_STREAM == "control:marker"
    assert MARKER_ROUND_OFFSET == 2


# --- chi_resp ----------------------------------------------------------------------------------


def test_compute_chi_resp_known_values():
    assert compute_chi_resp((1, 1, 1, 1)) == 0.0
    # mean 2, population variance 1 -> CV^2 = 0.25
    assert compute_chi_resp((1, 3)) == pytest.approx(0.25)


def test_compute_chi_resp_fails_closed():
    with pytest.raises(ValueError):
        compute_chi_resp(())
    with pytest.raises(ValueError):
        compute_chi_resp((0, 0))


# --- synthetic manifests for the pure aggregation ---------------------------------------------


def _sizes(big_value, big_count=8, root_count=MARKER_ROOT_COUNT):
    return (1,) * (root_count - big_count) + (int(big_value),) * big_count


def _manifest(seed_position, plant_r, **overrides):
    values = dict(
        run_id=f"run:marker:{seed_position}",
        frame_id="frame:marker:cell",
        seed_stream_id=MARKER_SEED_STREAM,
        raw_seed=MARKER_SEEDS[seed_position],
        plant_r=plant_r,
        response_probability=plant_r / MARKER_OPPORTUNITIES_PER_PARENT,
        root_count=MARKER_ROOT_COUNT,
        opportunities_per_parent=MARKER_OPPORTUNITIES_PER_PARENT,
        rounds=MARKER_ROUNDS,
        root_ids=tuple(f"marker:post:{i + 1}" for i in range(MARKER_ROOT_COUNT)),
        round_ids=tuple(range(MARKER_ROUND_OFFSET, MARKER_ROUND_OFFSET + MARKER_ROUNDS)),
        event_ids=tuple(f"marker:post:{i + 1}" for i in range(MARKER_ROOT_COUNT)),
        pair_ids=(f"marker-pair:post:1:{seed_position}",),
        assignment_ids=(),
        support_per_root=(MARKER_OPPORTUNITIES_PER_PARENT,) * MARKER_ROOT_COUNT,
    )
    values.update(overrides)
    return MarkerManifest(**values)


def _cell_results(plant_r, big_value=4):
    return tuple(
        MarkerControlResult(
            manifest=_manifest(k, plant_r),
            tree_sizes=_sizes(big_value),
            chi_resp=compute_chi_resp(_sizes(big_value)),
        )
        for k in range(12)
    )


def test_aggregate_marker_cell_pools_with_equal_root_weight():
    plant_r = PLANT_R_GRID[2]
    # seeds carry DIFFERENT dispersions so pooling and averaging disagree
    results = tuple(
        MarkerControlResult(
            manifest=_manifest(k, plant_r),
            tree_sizes=_sizes(2 + (k % 3) * 4),
            chi_resp=compute_chi_resp(_sizes(2 + (k % 3) * 4)),
        )
        for k in range(12)
    )
    cell = aggregate_marker_cell(plant_r, results)
    assert type(cell) is MarkerGridCell
    pooled = ()
    for result in results:
        pooled += result.tree_sizes
    assert cell.pooled_tree_sizes == pooled
    assert len(cell.pooled_tree_sizes) == 12 * MARKER_ROOT_COUNT
    assert cell.aggregated_chi_resp == pytest.approx(compute_chi_resp(pooled))
    seed_mean = math.fsum(result.chi_resp for result in results) / 12
    assert cell.aggregated_chi_resp != pytest.approx(seed_mean)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda results: results[:11],
        lambda results: (results[1], results[0]) + results[2:],
        lambda results: (
            dataclasses.replace(
                results[0],
                manifest=dataclasses.replace(
                    results[0].manifest, seed_stream_id="control:relabelled"
                ),
            ),
        )
        + results[1:],
        lambda results: (
            dataclasses.replace(
                results[0],
                manifest=dataclasses.replace(results[0].manifest, plant_r=0.92),
            ),
        )
        + results[1:],
        lambda results: (
            dataclasses.replace(
                results[0],
                manifest=dataclasses.replace(results[0].manifest, root_count=511),
            ),
        )
        + results[1:],
        lambda results: (
            dataclasses.replace(
                results[0],
                manifest=dataclasses.replace(
                    results[0].manifest, response_probability=0.5
                ),
            ),
        )
        + results[1:],
        lambda results: (
            dataclasses.replace(
                results[0],
                manifest=dataclasses.replace(
                    results[0].manifest,
                    support_per_root=(3,) * MARKER_ROOT_COUNT,
                ),
            ),
        )
        + results[1:],
        lambda results: (
            dataclasses.replace(results[0], tree_sizes=results[0].tree_sizes[:-1]),
        )
        + results[1:],
    ],
)
def test_aggregate_marker_cell_rejects_invalid_cohorts(mutate):
    plant_r = PLANT_R_GRID[2]
    with pytest.raises(ValueError):
        aggregate_marker_cell(plant_r, mutate(_cell_results(plant_r)))


# --- peak location -----------------------------------------------------------------------------


def _grid_cells(big_values=(2, 3, 9, 4, 3, 2)):
    return tuple(
        aggregate_marker_cell(plant_r, _cell_results(plant_r, big_value=big))
        for plant_r, big in zip(PLANT_R_GRID, big_values)
    )


def test_locate_chi_peak_interior_unique_max():
    peak = locate_chi_peak(_grid_cells())
    assert type(peak) is ChiPeak
    assert peak.argmax_plant_r == PLANT_R_GRID[2]
    assert peak.neighbor_low == PLANT_R_GRID[1]
    assert peak.neighbor_high == PLANT_R_GRID[3]
    assert peak.prominence > 0
    assert peak.seed_count == 12
    assert peak.seed_argmax_consistency_count == 12


@pytest.mark.parametrize(
    "big_values",
    [
        (9, 3, 2, 2, 2, 2),   # boundary maximum
        (2, 2, 2, 2, 3, 9),   # boundary maximum (high side)
        (2, 9, 9, 3, 2, 2),   # non-unique maximum
    ],
)
def test_locate_chi_peak_rejects_degenerate_surfaces(big_values):
    with pytest.raises(ValueError):
        locate_chi_peak(_grid_cells(big_values))


def test_locate_chi_peak_requires_registered_grid_order():
    cells = _grid_cells()
    with pytest.raises(ValueError):
        locate_chi_peak(cells[:5])
    with pytest.raises(ValueError):
        locate_chi_peak((cells[1], cells[0]) + cells[2:])


def test_locate_chi_peak_requires_seed_consistency():
    plant_r_peak = PLANT_R_GRID[2]
    cells = list(_grid_cells())
    # rebuild the neighbor cell so ONE seed position out-peaks the aggregated argmax
    inconsistent = tuple(
        MarkerControlResult(
            manifest=_manifest(k, PLANT_R_GRID[3]),
            tree_sizes=_sizes(20 if k == 0 else 4),
            chi_resp=compute_chi_resp(_sizes(20 if k == 0 else 4)),
        )
        for k in range(12)
    )
    cells[3] = aggregate_marker_cell(PLANT_R_GRID[3], inconsistent)
    # keep the aggregated argmax at index 2 by boosting it
    boosted = tuple(
        MarkerControlResult(
            manifest=_manifest(k, plant_r_peak),
            tree_sizes=_sizes(12),
            chi_resp=compute_chi_resp(_sizes(12)),
        )
        for k in range(12)
    )
    cells[2] = aggregate_marker_cell(plant_r_peak, boosted)
    assert cells[2].aggregated_chi_resp > cells[3].aggregated_chi_resp
    with pytest.raises(ValueError, match="seed"):
        locate_chi_peak(tuple(cells))


# --- installed-OASIS recursive bridge ---------------------------------------------------------


def test_recursive_marker_control_bridge(tmp_path):
    pytest.importorskip("oasis")

    result = run_recursive_marker_control(
        root_count=3,
        opportunities_per_parent=2,
        plant_r=2.0,   # q = 1: every opportunity fires -> exact deterministic trees
        rounds=3,
        run_id="run:marker:bridge",
        frame_id="frame:marker:bridge",
        seed_stream_id=MARKER_SEED_STREAM,
        seed=MARKER_SEEDS[0],
        database_path=str(tmp_path / "marker_a.db"),
    )
    assert type(result) is MarkerControlResult
    manifest = result.manifest
    assert manifest.run_id == "run:marker:bridge"
    assert manifest.seed_stream_id == MARKER_SEED_STREAM
    assert manifest.raw_seed == MARKER_SEEDS[0]
    assert manifest.plant_r == 2.0
    assert manifest.response_probability == 1.0
    assert manifest.root_count == 3
    assert manifest.opportunities_per_parent == 2
    assert manifest.rounds == 3
    assert manifest.root_ids == ("marker:post:1", "marker:post:2", "marker:post:3")
    assert manifest.round_ids == (2, 3, 4)
    assert manifest.support_per_root == (2, 2, 2)

    # q=1 with 2 opportunities over 2 reply rounds: every tree is exactly 1 + 2 + 4 = 7,
    # and children born in the final round get no opportunity (the frozen horizon)
    assert result.tree_sizes == (7, 7, 7)
    assert result.chi_resp == 0.0
    assert len(manifest.event_ids) == 21
    assert len(manifest.assignment_ids) == 18   # realized replies
    assert all(event.startswith("marker:") for event in manifest.event_ids)
    assert all(pair.startswith("marker-pair:") for pair in manifest.pair_ids)

    # determinism: an identical seed reproduces the complete result
    rerun = run_recursive_marker_control(
        root_count=3,
        opportunities_per_parent=2,
        plant_r=2.0,
        rounds=3,
        run_id="run:marker:bridge",
        frame_id="frame:marker:bridge",
        seed_stream_id=MARKER_SEED_STREAM,
        seed=MARKER_SEEDS[0],
        database_path=str(tmp_path / "marker_b.db"),
    )
    assert rerun == result

    # zero plant: every tree stays a singleton
    silent = run_recursive_marker_control(
        root_count=3,
        opportunities_per_parent=2,
        plant_r=0.0,
        rounds=3,
        run_id="run:marker:silent",
        frame_id="frame:marker:silent",
        seed_stream_id=MARKER_SEED_STREAM,
        seed=MARKER_SEEDS[1],
        database_path=str(tmp_path / "marker_c.db"),
    )
    assert silent.tree_sizes == (1, 1, 1)
    assert silent.chi_resp == 0.0
    assert silent.manifest.assignment_ids == ()


def test_recursive_marker_control_fail_closed(tmp_path):
    pytest.importorskip("oasis")
    with pytest.raises(ValueError, match="seed stream"):
        run_recursive_marker_control(
            root_count=3, opportunities_per_parent=2, plant_r=1.0, rounds=3,
            run_id="r", frame_id="f", seed_stream_id="control:scripted",
            seed=1, database_path=str(tmp_path / "marker_d.db"))
    with pytest.raises(ValueError, match="response_probability"):
        run_recursive_marker_control(
            root_count=3, opportunities_per_parent=2, plant_r=2.5, rounds=3,
            run_id="r", frame_id="f", seed_stream_id=MARKER_SEED_STREAM,
            seed=1, database_path=str(tmp_path / "marker_e.db"))


def test_marker_and_reply_manifests_are_disjoint(tmp_path):
    pytest.importorskip("oasis")
    from critaudit.sim.controls.causal_probe_control import (
        CONTROL_SEED_STREAM,
        build_scripted_control_frame,
        run_scripted_oasis_control,
    )

    marker = run_recursive_marker_control(
        root_count=3, opportunities_per_parent=2, plant_r=1.0, rounds=3,
        run_id="run:marker:disjoint", frame_id="frame:marker:disjoint",
        seed_stream_id=MARKER_SEED_STREAM, seed=MARKER_SEEDS[2],
        database_path=str(tmp_path / "marker_f.db"))

    frame, truth = build_scripted_control_frame(
        parent_count=2, recipients_per_parent=2, plant_r=1.0, seed=7)
    reply = run_scripted_oasis_control(
        frame, truth, run_id="run:control:disjoint",
        seed_stream_id=CONTROL_SEED_STREAM, seed=7,
        database_path=str(tmp_path / "reply.db"))

    marker_manifest = marker.manifest
    reply_manifest = reply.manifest
    assert marker_manifest.run_id != reply_manifest.run_id
    assert marker_manifest.frame_id != reply_manifest.frame_id
    assert marker_manifest.seed_stream_id != reply_manifest.seed_stream_id
    assert marker_manifest.raw_seed != reply_manifest.raw_seed
    assert set(marker_manifest.root_ids).isdisjoint(reply_manifest.root_ids)
    assert set(marker_manifest.round_ids).isdisjoint(reply_manifest.round_ids)
    assert set(marker_manifest.event_ids).isdisjoint(reply_manifest.event_ids)
    assert set(marker_manifest.pair_ids).isdisjoint(reply_manifest.pair_ids)
    assert set(marker_manifest.assignment_ids).isdisjoint(
        reply_manifest.assignment_ids)

    # marker descendants never enter the fixed R_reply frame
    frame_parents = {parent.parent_item_id for parent in frame.parent_records}
    assert set(marker_manifest.event_ids).isdisjoint(frame_parents)

    # equal registered support within and across seeds
    assert len(set(marker_manifest.support_per_root)) == 1

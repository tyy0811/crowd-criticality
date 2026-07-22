from __future__ import annotations

import dataclasses
import io
import json
import os
from contextlib import redirect_stdout

import pytest

from critaudit.experiments.causal_probe_power import (
    MC_MAX_HALF_WIDTH,
    PLANT_R_GRID,
    POWER_SCHEDULE_SEEDS,
    RECOVERABILITY_SEEDS,
)
from critaudit.experiments.causal_probe_recoverability import (
    RecoverabilityManifest,
    build_recoverability_manifest,
    evaluate_recoverability_gate,
    main,
    run_dry_run,
    write_recoverability_artifact,
)
from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_OPPORTUNITIES_PER_PARENT,
    MARKER_ROOT_COUNT,
    MARKER_SEED_STREAM,
    MARKER_SEEDS,
    MarkerControlResult,
    MarkerGridCell,
    MarkerManifest,
    aggregate_marker_cell,
    compute_chi_resp,
    locate_chi_peak,
)
from critaudit.sim.harness import causal_probe_spec as spec

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_POWER_ARTIFACT = os.path.join(_REPO, spec.POWER_ARTIFACT_PATH)


# --- manifest ----------------------------------------------------------------------------------


def _manifest(**overrides):
    values = dict(
        schema_version=spec.SCHEMA_VERSION,
        power_artifact_path=spec.POWER_ARTIFACT_PATH,
        power_artifact_sha256=spec.POWER_ARTIFACT_SHA256,
        frame_sha256s=("a" * 64,),
        eligibility_evidence_sha256s=("b" * 64,),
        plant_r_grid=PLANT_R_GRID,
        seeds=RECOVERABILITY_SEEDS,
        marker_seeds=MARKER_SEEDS,
        branch_b_text=spec.BRANCH_B_TEXT,
    )
    values.update(overrides)
    return RecoverabilityManifest(**values)


def test_manifest_record_is_frozen_and_immutable():
    manifest = _manifest()
    assert manifest.plant_r_grid == PLANT_R_GRID
    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.seeds = ()


def test_build_manifest_verifies_the_banked_power_artifact(tmp_path):
    manifest = build_recoverability_manifest(
        _POWER_ARTIFACT,
        frame_sha256s=("a" * 64,),
        eligibility_evidence_sha256s=("b" * 64,),
    )
    assert manifest.power_artifact_sha256 == spec.POWER_ARTIFACT_SHA256
    assert manifest.seeds == RECOVERABILITY_SEEDS
    assert manifest.marker_seeds == MARKER_SEEDS
    # hash drift fails closed
    tampered = tmp_path / "tampered.json"
    with open(_POWER_ARTIFACT) as source:
        artifact = json.load(source)
    artifact["registered_constants"]["TARGET_COVERAGE"] = 0.5
    with open(tampered, "w") as handle:
        json.dump(artifact, handle)
    with pytest.raises(ValueError, match="sha256|hash"):
        build_recoverability_manifest(
            str(tampered), frame_sha256s=("a" * 64,),
            eligibility_evidence_sha256s=("b" * 64,))


# --- synthetic gate inputs ---------------------------------------------------------------------


def _sizes(big_value, big_count=8, root_count=MARKER_ROOT_COUNT):
    return (1,) * (root_count - big_count) + (int(big_value),) * big_count


def _marker_result(position, plant_r, big_value):
    manifest = MarkerManifest(
        run_id=f"run:marker:{plant_r}:{position}",
        frame_id="frame:marker:grid",
        seed_stream_id=MARKER_SEED_STREAM,
        raw_seed=MARKER_SEEDS[position],
        plant_r=plant_r,
        response_probability=plant_r / MARKER_OPPORTUNITIES_PER_PARENT,
        root_count=MARKER_ROOT_COUNT,
        opportunities_per_parent=MARKER_OPPORTUNITIES_PER_PARENT,
        rounds=8,
        root_ids=tuple(f"marker:post:{i + 1}" for i in range(MARKER_ROOT_COUNT)),
        round_ids=(2, 3, 4, 5, 6, 7, 8, 9),
        event_ids=tuple(f"marker:post:{i + 1}" for i in range(MARKER_ROOT_COUNT)),
        pair_ids=(f"marker-pair:post:1:{position}",),
        assignment_ids=(),
        support_per_root=(MARKER_OPPORTUNITIES_PER_PARENT,) * MARKER_ROOT_COUNT,
    )
    return MarkerControlResult(
        manifest=manifest,
        tree_sizes=_sizes(big_value),
        chi_resp=compute_chi_resp(_sizes(big_value)),
    )


def _marker_grid(big_values=(2, 3, 5, 9, 3, 2)):
    return tuple(
        aggregate_marker_cell(
            plant_r,
            tuple(_marker_result(k, plant_r, big) for k in range(12)),
        )
        for plant_r, big in zip(PLANT_R_GRID, big_values)
    )


def _cell_results(means=(0.61, 0.90, 0.96, 1.04, 1.09, 1.28)):
    return tuple(
        {
            "plant_r": plant_r,
            "mean_r_reply": mean,
            "estimates": tuple(mean for _ in RECOVERABILITY_SEEDS),
            "structural_failures": 0,
        }
        for plant_r, mean in zip(PLANT_R_GRID, means)
    )


def test_gate_passes_on_a_clean_configuration():
    marker_cells = _marker_grid()          # aggregated peak at plant 1.03
    peak = locate_chi_peak(marker_cells)   # neighbors [0.97, 1.08]
    gate = evaluate_recoverability_gate(
        _cell_results(), marker_cells, peak, _manifest())
    for field in spec.REQUIRED_GATE_FIELDS:
        assert field in gate
    assert gate["monotonicity_passed"] is True
    assert gate["crossing_resolved"] is True
    assert gate["crossing_interval"] == [0.97, 1.03]
    assert gate["near_critical_abs_error"]["0.97"] == pytest.approx(0.01)
    assert gate["near_critical_abs_error"]["1.03"] == pytest.approx(0.01)
    assert gate["ci_coverage_passed"] is True
    assert gate["ci_precision_passed"] is True
    assert gate["chi_resp_coincidence_passed"] is True
    assert gate["structural_failures"] == 0
    assert gate["passed"] is True
    assert gate["status"] == spec.STATUS_RECOVERABILITY_PASSED


def test_gate_fails_scientifically_without_raising():
    marker_cells = _marker_grid()
    peak = locate_chi_peak(marker_cells)
    # non-monotone means
    gate = evaluate_recoverability_gate(
        _cell_results((0.61, 0.95, 0.90, 1.04, 1.09, 1.28)),
        marker_cells, peak, _manifest())
    assert gate["monotonicity_passed"] is False
    assert gate["passed"] is False
    assert gate["status"] == spec.STATUS_RECOVERABILITY_FAILED
    # crossing unresolved (never crosses one)
    gate = evaluate_recoverability_gate(
        _cell_results((0.2, 0.3, 0.4, 0.5, 0.6, 0.7)),
        marker_cells, peak, _manifest())
    assert gate["crossing_resolved"] is False
    assert gate["passed"] is False
    # near-crossing error beyond tolerance
    gate = evaluate_recoverability_gate(
        _cell_results((0.61, 0.90, 0.905, 1.10, 1.15, 1.28)),
        marker_cells, peak, _manifest())
    assert gate["near_critical_passed"] is False
    assert gate["passed"] is False


def test_gate_chi_coincidence_requires_containment():
    # peak at 0.92: neighbor interval [0.60, 0.97] cannot contain crossing [0.97, 1.03]
    marker_cells = _marker_grid((2, 9, 5, 3, 2.5, 2))
    peak = locate_chi_peak(marker_cells)
    gate = evaluate_recoverability_gate(
        _cell_results(), marker_cells, peak, _manifest())
    assert gate["chi_resp_coincidence_passed"] is False
    assert gate["passed"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"plant_r_grid": (0.5, 0.9, 1.0, 1.1, 1.2, 1.3)},
        {"seeds": POWER_SCHEDULE_SEEDS},
        {"marker_seeds": MARKER_SEEDS[::-1]},
        {"marker_seeds": MARKER_SEEDS[:11]},
        {"branch_b_text": "relaxed"},
        {"power_artifact_sha256": "c" * 64},
    ],
)
def test_gate_rejects_structural_manifest_violations(overrides):
    marker_cells = _marker_grid()
    peak = locate_chi_peak(marker_cells)
    with pytest.raises(ValueError):
        evaluate_recoverability_gate(
            _cell_results(), marker_cells, peak, _manifest(**overrides))


def test_gate_rejects_incomplete_cell_results():
    marker_cells = _marker_grid()
    peak = locate_chi_peak(marker_cells)
    with pytest.raises(ValueError):
        evaluate_recoverability_gate(
            _cell_results()[:5], marker_cells, peak, _manifest())
    short = _cell_results()
    short = (dict(short[0], estimates=short[0]["estimates"][:3]),) + short[1:]
    with pytest.raises(ValueError):
        evaluate_recoverability_gate(short, marker_cells, peak, _manifest())


# --- canonical writer --------------------------------------------------------------------------


def test_write_recoverability_artifact_is_canonical(tmp_path):
    payload = {"gate": {"passed": False}, "manifest": {"seeds": list(RECOVERABILITY_SEEDS)}}
    path_a = str(tmp_path / "a.json")
    path_b = str(tmp_path / "b.json")
    write_recoverability_artifact(path_a, payload)
    write_recoverability_artifact(path_b, payload)
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        assert fa.read() == fb.read()


# --- CLI guard and the no-execution dry run ----------------------------------------------------


def test_cli_requires_exactly_one_mode(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        main(["--power-artifact", _POWER_ARTIFACT])
    assert excinfo.value.code not in (0, None)
    with pytest.raises(SystemExit) as excinfo:
        main(["--dry-run", "--execute", "--power-artifact", _POWER_ARTIFACT,
              "--output", str(tmp_path / "out.json")])
    assert excinfo.value.code not in (0, None)


def test_dry_run_builds_hashes_without_any_draw(tmp_path):
    pytest.importorskip("oasis")
    work_dir = str(tmp_path / "dry")
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        report = run_dry_run(
            _POWER_ARTIFACT, work_dir,
            support={"parent_count": 2, "recipients_per_parent": 2})
    # the platform layer prints its own noise; the canonical manifest is the
    # final stdout line
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    printed = json.loads(lines[-1])
    assert printed["execute"] is False
    assert printed["provider_paths_reachable"] is False
    assert printed == report

    manifest = report["manifest"]
    assert len(manifest["frame_sha256s"]) == 1
    assert len(manifest["eligibility_evidence_sha256s"]) == 1
    assert manifest["seeds"] == list(RECOVERABILITY_SEEDS)
    assert manifest["marker_seeds"] == list(MARKER_SEEDS)

    # no draw happened: the pre-draw database carries roots but no refresh trace
    import sqlite3
    db_files = [name for name in os.listdir(work_dir) if name.endswith(".db")]
    assert db_files
    for name in db_files:
        con = sqlite3.connect(os.path.join(work_dir, name))
        refreshes = con.execute(
            "SELECT COUNT(*) FROM trace WHERE action = 'refresh'").fetchone()[0]
        comments = con.execute("SELECT COUNT(*) FROM comment").fetchone()[0]
        con.close()
        assert refreshes == 0
        assert comments == 0

    # no recoverability result artifact was created
    result_files = [name for name in os.listdir(work_dir) if "recoverability" in name]
    assert result_files == []


def test_runner_module_has_no_provider_or_llm_import_surface():
    import ast
    path = os.path.join(
        _REPO, "src/critaudit/experiments/causal_probe_recoverability.py")
    with open(path) as handle:
        tree = ast.parse(handle.read(), filename=path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    for forbidden in ("openai", "modal", "_make_counting_model",
                      "run_oasis_minimal", "OpenAICompatibleModel"):
        assert forbidden not in names, f"runner reaches provider path {forbidden!r}"

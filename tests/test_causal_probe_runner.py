from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import os
from contextlib import redirect_stdout

import pytest

from critaudit.experiments.causal_probe_power import (
    PLANT_R_GRID,
    POWER_SCHEDULE_SEEDS,
    RECOVERABILITY_SEEDS,
    build_power_frame,
)
from critaudit.experiments.causal_probe_recoverability import (
    RecoverabilityManifest,
    build_recoverability_manifest,
    evaluate_recoverability_gate,
    load_recoverability_manifest,
    main,
    run_dry_run,
    write_recoverability_artifact,
)
from critaudit.sim.controls.causal_probe_control import (
    CONTROL_SEED_STREAM,
    ScriptedControlRun,
)
from critaudit.sim.controls.causal_probe_marker_control import (
    MARKER_OPPORTUNITIES_PER_PARENT,
    MARKER_ROOT_COUNT,
    MARKER_SEED_STREAM,
    MARKER_SEEDS,
    MarkerControlResult,
    MarkerManifest,
    aggregate_marker_cell,
    compute_chi_resp,
    locate_chi_peak,
)
from critaudit.sim.harness import causal_probe_spec as spec
from critaudit.sim.harness.causal_probe import estimate_r_reply
from critaudit.sim.harness.causal_probe_records import (
    Assignment,
    Outcome,
    ProbeManifest,
    StratumDraw,
    sampling_frame_sha256,
    sampling_frame_to_bytes,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_POWER_ARTIFACT = os.path.join(_REPO, spec.POWER_ARTIFACT_PATH)

# --- fabricated PRIMARY evidence for the pure gate tests ---------------------------------------
# A small but real power-layout frame; every gate input below carries complete
# ledgers the gate must re-verify, never bare summaries.

_FRAME = build_power_frame(100, 4)
_FRAME_BYTES = sampling_frame_to_bytes(_FRAME)
_FRAME_SHA = sampling_frame_sha256(_FRAME)
_EVIDENCE_BYTES = b'{"fixture": "predraw eligibility evidence"}\n'
_EVIDENCE_SHA = hashlib.sha256(_EVIDENCE_BYTES).hexdigest()


def _manifest(**overrides):
    values = dict(
        schema_version=spec.SCHEMA_VERSION,
        power_artifact_path=spec.POWER_ARTIFACT_PATH,
        power_artifact_sha256=spec.POWER_ARTIFACT_SHA256,
        frame_sha256s=(_FRAME_SHA,),
        eligibility_evidence_sha256s=(_EVIDENCE_SHA,),
        plant_r_grid=PLANT_R_GRID,
        seeds=RECOVERABILITY_SEEDS,
        marker_seeds=MARKER_SEEDS,
        branch_b_text=spec.BRANCH_B_TEXT,
    )
    values.update(overrides)
    return RecoverabilityManifest(**values)


def _fabricated_run(plant_r, position, n_responders):
    """A complete, validator-clean ScriptedControlRun: the first `n_responders`
    strata select their first pair (treated, with a native child in the frozen
    outcome round); every other stratum logs an explicit no-selection draw."""
    draws = []
    assignments = []
    outcomes = []
    strata_seen = set()
    responders = 0
    for pair in _FRAME.candidate_pairs:
        if pair.stratum_id in strata_seen:
            continue
        strata_seen.add(pair.stratum_id)
        if responders < n_responders:
            draws.append(StratumDraw(_FRAME.frame_id, pair.stratum_id, pair.pair_id))
            assignment_id = f"assignment:{pair.pair_id}"
            assignments.append(Assignment(
                assignment_id=assignment_id, frame_id=_FRAME.frame_id,
                pair_id=pair.pair_id, filler_item_id=f"filler:{pair.pair_id}",
                treated=True))
            outcomes.append(Outcome(
                assignment_id=assignment_id, parent_served=True,
                parent_seen_in_background=False, feed_length_before=3,
                feed_length_after=3,
                direct_child_item_id=f"comment:{responders + 1}",
                direct_child_parent_id=pair.parent_item_id,
                child_author_agent_id=pair.agent_id,
                child_round=pair.round_id))
            responders += 1
        else:
            draws.append(StratumDraw(_FRAME.frame_id, pair.stratum_id, None))
    manifest = ProbeManifest(
        run_id=f"run:recoverability:{plant_r}:{RECOVERABILITY_SEEDS[position]}",
        frame_id=_FRAME.frame_id,
        seed_stream_id=CONTROL_SEED_STREAM,
        raw_seed=RECOVERABILITY_SEEDS[position],
        root_ids=tuple(p.parent_item_id for p in _FRAME.parent_records),
        round_ids=(0, 1),
        event_ids=tuple(o.direct_child_item_id for o in outcomes),
        pair_ids=tuple(p.pair_id for p in _FRAME.candidate_pairs),
        assignment_ids=tuple(a.assignment_id for a in assignments),
    )
    return ScriptedControlRun(
        manifest=manifest,
        frame_bytes=_FRAME_BYTES,
        frame_sha256=_FRAME_SHA,
        eligibility_evidence_bytes=_EVIDENCE_BYTES,
        eligibility_evidence_sha256=_EVIDENCE_SHA,
        draws=tuple(draws),
        assignments=tuple(assignments),
        outcomes=tuple(outcomes),
    )


def _cell_results(responder_counts=(12, 18, 19, 21, 22, 26)):
    cells = []
    for plant_r, count in zip(PLANT_R_GRID, responder_counts):
        runs = tuple(
            _fabricated_run(plant_r, position, count) for position in range(12))
        estimates = tuple(
            estimate_r_reply(_FRAME, run.draws, run.assignments, run.outcomes).estimate
            for run in runs)
        cells.append({
            "plant_r": plant_r,
            "mean_r_reply": sum(estimates) / len(estimates),
            "estimates": estimates,
            "runs": runs,
        })
    return tuple(cells)


# --- manifest ----------------------------------------------------------------------------------


def test_manifest_record_is_frozen_and_immutable():
    manifest = _manifest()
    assert manifest.plant_r_grid == PLANT_R_GRID
    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.seeds = ()


def test_build_manifest_verifies_the_banked_power_artifact(tmp_path):
    manifest = build_recoverability_manifest(
        _POWER_ARTIFACT,
        frame_sha256s=(_FRAME_SHA,),
        eligibility_evidence_sha256s=(_EVIDENCE_SHA,),
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
            str(tampered), frame_sha256s=(_FRAME_SHA,),
            eligibility_evidence_sha256s=(_EVIDENCE_SHA,))


# --- synthetic marker inputs -------------------------------------------------------------------


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


# --- the self-verifying gate -------------------------------------------------------------------


def test_gate_passes_on_verified_primary_evidence():
    marker_cells = _marker_grid()          # aggregated peak at plant 1.03
    peak = locate_chi_peak(marker_cells)   # neighbors [0.97, 1.08]
    gate = evaluate_recoverability_gate(
        _cell_results(), marker_cells, peak, _manifest())
    for field in spec.REQUIRED_GATE_FIELDS:
        assert field in gate
    assert gate["monotonicity_passed"] is True
    assert gate["crossing_resolved"] is True
    assert gate["crossing_interval"] == [0.97, 1.03]
    assert gate["near_critical_abs_error"]["0.97"] == pytest.approx(0.02)
    assert gate["near_critical_abs_error"]["1.03"] == pytest.approx(0.02)
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
        _cell_results((12, 19, 18, 21, 22, 26)), marker_cells, peak, _manifest())
    assert gate["monotonicity_passed"] is False
    assert gate["passed"] is False
    assert gate["status"] == spec.STATUS_RECOVERABILITY_FAILED
    # crossing unresolved (never crosses one)
    gate = evaluate_recoverability_gate(
        _cell_results((2, 3, 4, 5, 6, 7)), marker_cells, peak, _manifest())
    assert gate["crossing_resolved"] is False
    assert gate["passed"] is False
    # near-crossing error beyond tolerance
    gate = evaluate_recoverability_gate(
        _cell_results((12, 18, 21, 26, 27, 28)), marker_cells, peak, _manifest())
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
        {"frame_sha256s": (_FRAME_SHA, _FRAME_SHA)},
        {"eligibility_evidence_sha256s": ("NOT-HEX" * 8,)},
    ],
)
def test_gate_rejects_structural_manifest_violations(overrides):
    marker_cells = _marker_grid()
    peak = locate_chi_peak(marker_cells)
    with pytest.raises(ValueError):
        evaluate_recoverability_gate(
            _cell_results(), marker_cells, peak, _manifest(**overrides))


def _tamper_first_run(cells, **replacements):
    first = cells[0]
    runs = (dataclasses.replace(first["runs"][0], **replacements),) + first["runs"][1:]
    return (dict(first, runs=runs),) + cells[1:]


@pytest.mark.parametrize(
    "forge",
    [
        # reported estimate not reproducible from the ledgers
        lambda cells: (dict(
            cells[0],
            estimates=(cells[0]["estimates"][0] + 0.05,) + cells[0]["estimates"][1:],
            mean_r_reply=cells[0]["mean_r_reply"] + 0.05 / 12,
        ),) + cells[1:],
        # frame hash not the banked one
        lambda cells: _tamper_first_run(cells, frame_sha256="f" * 64),
        # evidence bytes do not hash to the claim
        lambda cells: _tamper_first_run(cells, eligibility_evidence_bytes=b"forged"),
        # missing run
        lambda cells: (dict(
            cells[0], runs=cells[0]["runs"][:11],
            estimates=cells[0]["estimates"][:11],
        ),) + cells[1:],
        # incomplete draw ledger inside a run
        lambda cells: _tamper_first_run(
            cells, draws=cells[0]["runs"][0].draws[:-1]),
        # summaries instead of primary evidence
        lambda cells: (dict(cells[0], runs=({"forged": True},) * 12),) + cells[1:],
    ],
)
def test_gate_rejects_forged_or_missing_run_evidence(forge):
    marker_cells = _marker_grid()
    peak = locate_chi_peak(marker_cells)
    with pytest.raises(ValueError):
        evaluate_recoverability_gate(
            forge(_cell_results()), marker_cells, peak, _manifest())


def test_gate_rejects_forged_marker_cells_and_peak():
    marker_cells = _marker_grid()
    peak = locate_chi_peak(marker_cells)
    forged_cells = (dataclasses.replace(
        marker_cells[0], aggregated_chi_resp=999.0),) + marker_cells[1:]
    with pytest.raises(ValueError, match="reproduce"):
        evaluate_recoverability_gate(
            _cell_results(), forged_cells, peak, _manifest())
    forged_peak = dataclasses.replace(peak, prominence=peak.prominence + 1.0)
    with pytest.raises(ValueError, match="peak"):
        evaluate_recoverability_gate(
            _cell_results(), marker_cells, forged_peak, _manifest())


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


def test_cli_requires_exactly_one_mode_and_execute_inputs(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        main(["--power-artifact", _POWER_ARTIFACT])
    assert excinfo.value.code not in (0, None)
    with pytest.raises(SystemExit) as excinfo:
        main(["--dry-run", "--execute", "--power-artifact", _POWER_ARTIFACT,
              "--output", str(tmp_path / "out.json")])
    assert excinfo.value.code not in (0, None)
    # --execute without the banked manifest is refused
    with pytest.raises(SystemExit) as excinfo:
        main(["--execute", "--power-artifact", _POWER_ARTIFACT,
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

    # the banked manifest file is written, canonical, hash-stable, and loadable
    manifest_path = report["manifest_path"]
    assert os.path.dirname(manifest_path) == work_dir
    with open(manifest_path, "rb") as handle:
        manifest_bytes = handle.read()
    assert hashlib.sha256(manifest_bytes).hexdigest() == report["manifest_sha256"]
    loaded = load_recoverability_manifest(manifest_path)
    assert loaded.frame_sha256s == tuple(manifest["frame_sha256s"])
    assert loaded.eligibility_evidence_sha256s == tuple(
        manifest["eligibility_evidence_sha256s"])

    # no draw happened: the pre-draw databases carry roots but no refresh trace
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


def test_load_recoverability_manifest_fails_closed(tmp_path):
    path = str(tmp_path / "manifest.json")
    with open(path, "w") as handle:
        handle.write("not json")
    with pytest.raises(ValueError, match="JSON"):
        load_recoverability_manifest(path)
    # non-canonical bytes of a valid manifest are rejected
    from critaudit.experiments.causal_probe_recoverability import (
        _canonical_manifest_bytes,
    )
    with open(path, "wb") as handle:
        handle.write(b" " + _canonical_manifest_bytes(_manifest()))
    with pytest.raises(ValueError, match="canonical"):
        load_recoverability_manifest(path)


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

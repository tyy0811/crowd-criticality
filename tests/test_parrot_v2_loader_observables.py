import numpy as np
import pytest

FIXTURE = "tests/fixtures/oasis_trace_recon.sqlite"


def test_loader_matches_exporter_parity():
    from critaudit.sim.harness.oasis_adapter import (
        export_harness_run, load_harness_records)
    from critaudit.sim.harness.assemble import assemble_harness_run
    events, refreshes, _ = load_harness_records(FIXTURE, timestamp_col="created_at")
    via_loader = assemble_harness_run(events, refreshes)
    direct = export_harness_run(FIXTURE, timestamp_col="created_at")
    assert np.array_equal(via_loader.times, direct.times)
    assert np.array_equal(via_loader.root_id, direct.root_id)
    assert np.array_equal(via_loader.parent_idx, direct.parent_idx)
    assert np.array_equal(via_loader.read_emit_success, direct.read_emit_success)
    assert via_loader.content == direct.content


def test_loader_returns_full_records_with_seq_and_action_map():
    from critaudit.sim.harness.oasis_adapter import load_harness_records
    events, refreshes, action_by_item = load_harness_records(
        FIXTURE, timestamp_col="created_at")
    assert events and refreshes
    assert all(hasattr(e, "seq") for e in events)
    assert any(e.seq > 0 for e in events)              # strict seq-join populated
    assert all(hasattr(r, "served_item_ids") for r in refreshes)
    traced = [e for e in events if e.seq > 0]
    assert all(action_by_item.get(e.item_id) for e in traced)


def test_compute_observables_pure_and_complete():
    from critaudit.sim.harness.oasis_adapter import export_harness_run
    from critaudit.sim.harness.observables import compute_observables
    run = export_harness_run(FIXTURE, timestamp_col="created_at")
    obs = compute_observables(run)
    assert set(obs) == {"n_events", "frac_size1", "giant_frac",
                        "length_spread", "read_emit_ratio"}
    assert obs["n_events"] == run.times.size
    assert 0.0 <= obs["frac_size1"] <= 1.0 and 0.0 <= obs["giant_frac"] <= 1.0
    assert obs["read_emit_ratio"] == pytest.approx(
        float(np.count_nonzero(run.read_emit_success)) / run.times.size)


def test_compute_observables_never_gates():
    from critaudit.sim.harness.observables import compute_observables
    from critaudit.sim.harness.types import HarnessRun
    run = HarnessRun(times=np.array([0.0]), root_id=np.array([0]),
                     parent_idx=np.array([-1]),
                     read_emit_success=np.array([False]), content=["x"])
    obs = compute_observables(run)
    assert obs["n_events"] == 1 and obs["frac_size1"] == 1.0
    with pytest.raises(ValueError):
        compute_observables(HarnessRun(times=np.array([]), root_id=np.array([]),
                                       parent_idx=np.array([]),
                                       read_emit_success=np.array([]), content=[]))

import json, os, pytest
import critaudit.experiments.parrot_v2_invariance as orch
from critaudit.sim.controls.parrot_v2_profile import CohortActionProfile
from critaudit.sim.harness import harness_spec as hs


def _profiles():
    def prof(w):
        return CohortActionProfile(
            window_seed=w,
            per_round_type_counts=((1, 0, 0, 0), (1, 0, 0, 0)),
            per_round_refresh_counts=(0, 1),
            news_events=(), authored_corpus=("alpha",))
    return {w: prof(w) for w in hs.COHORT_SEEDS}


def _fake_runner():
    """Writes through the REAL codec so digest verification is exercised."""
    import base64
    from critaudit.experiments.parrot_v2_replay import write_replay_output
    from critaudit.sim.controls.parrot_v2_records import emission_record_bytes
    from critaudit.sim.controls.parrot_v2_schedule import envelope_from_bytes
    from critaudit.sim.harness.types import EventRecord
    ev = [EventRecord(item_id="post:1", time=0.0, agent_id=0,
                      parent_item_id=None, content="alpha", seq=1)]
    def fake(envelope_path, *, width, database_path, out_path, violator, timeout):
        env = envelope_from_bytes(open(envelope_path, "rb").read())
        with open(database_path, "wb") as fh:
            fh.write(b"db")                       # artifact retained + hashed
        write_replay_output({
            "schema": 1, "schedule_seed": env.schedule_seed,
            "assigned_window": env.assigned_window,
            "profile_sha256": env.profile_sha256,
            "platform_seed": env.platform_seed,
            "schedule_sha256": env.schedule_sha256,
            "graph_sha256": "ab" * 32,               # constant across the triple
            "width": width, "n_rounds": 2, "violator": violator,
            "emission_record_b64":
                base64.b64encode(emission_record_bytes(ev)).decode(),
            "observables": {"n_events": 1, "frac_size1": 1.0, "giant_frac": 1.0,
                             "length_spread": 0.0, "read_emit_ratio": 0.0},
            "refresh_ledger": [], "violator_item_ids": [], "timings": {}}, out_path)
    return fake


def test_deadline_zero_fails(tmp_path):
    with pytest.raises(orch.InvarianceFailure, match="deadline"):
        orch._run_invariance_core(str(tmp_path), str(tmp_path / "r.json"),
                                  profiles=_profiles(), schedule_seeds=(818201,),
                                  widths=(1, 3, 5), violator_seeds=(),
                                  ceiling_seconds=0, replay_runner=_fake_runner())


def test_profile_key_validation(tmp_path):
    bad = {20260627: _profiles()[20260627]}       # missing two windows
    with pytest.raises(orch.InvarianceFailure, match="profile"):
        orch._run_invariance_core(str(tmp_path), str(tmp_path / "r.json"),
                                  profiles=bad, schedule_seeds=(818201,),
                                  widths=(1, 3, 5), violator_seeds=(),
                                  ceiling_seconds=3600, replay_runner=_fake_runner())


def test_child_failure_frozen_path_three_properties(tmp_path):
    """(a) dispatch stops immediately; (b) partial manifest + R3 report with the
    VERBATIM failure are persisted; (c) InvarianceFailure raised."""
    calls = []
    def failing(*a, **kw):
        calls.append(kw["width"])
        raise orch.InvarianceFailure("child failed (injected)")
    report_path = str(tmp_path / "r.json")
    with pytest.raises(orch.InvarianceFailure, match="injected"):          # (c)
        orch._run_invariance_core(str(tmp_path), report_path,
                                  profiles=_profiles(), schedule_seeds=(818201,),
                                  widths=(1, 3, 5), violator_seeds=(),
                                  ceiling_seconds=3600, replay_runner=failing)
    assert len(calls) == 1                                                 # (a)
    rep = json.load(open(report_path))                                     # (b)
    assert rep["reading"] == "R3"
    assert "child failed (injected)" in json.dumps(rep)
    run_dirs = [d for d in os.listdir(tmp_path) if d.startswith("run-")]
    assert len(run_dirs) == 1
    assert os.path.exists(os.path.join(str(tmp_path), run_dirs[0], "manifest.json"))


def test_graph_sha_divergence_is_run_failure(tmp_path):
    """A planted graph_sha mismatch inside a width triple takes the frozen
    failure path: persisted R3 report naming the divergence, then raise."""
    real = _fake_runner()
    def diverging(envelope_path, *, width, database_path, out_path, violator, timeout):
        real(envelope_path, width=width, database_path=database_path,
             out_path=out_path, violator=violator, timeout=timeout)
        if width == 5:                          # tamper: rewrite with a different graph sha
            from critaudit.experiments.parrot_v2_replay import (
                read_replay_output, write_replay_output)
            payload = read_replay_output(out_path)
            payload["graph_sha256"] = "cd" * 32
            write_replay_output(payload, out_path)
    report_path = str(tmp_path / "r.json")
    with pytest.raises(orch.InvarianceFailure, match="graph"):
        orch._run_invariance_core(str(tmp_path), report_path,
                                  profiles=_profiles(), schedule_seeds=(818201,),
                                  widths=(1, 3, 5), violator_seeds=(),
                                  ceiling_seconds=3600, replay_runner=diverging)
    rep = json.load(open(report_path))
    assert rep["reading"] == "R3" and "graph" in json.dumps(rep)


def test_report_manifest_unique_dir_and_retention(tmp_path):
    report_path = str(tmp_path / "report.json")
    result = orch._run_invariance_core(
        str(tmp_path), report_path, profiles=_profiles(),
        schedule_seeds=(818201,), widths=(1, 3, 5), violator_seeds=(),
        ceiling_seconds=3600, replay_runner=_fake_runner())
    rep = json.load(open(report_path))
    # empty ledgers -> no realized contrast -> R3, with the frozen wording
    assert rep["reading"] == "R3" and result["reading"] == "R3"
    assert "no realized exposure contrast" in json.dumps(rep)
    # invocation-unique run dir, retained artifacts, non-circular hashes
    run_dir = result["run_dir"]
    assert os.path.isdir(run_dir) and run_dir.startswith(str(tmp_path))
    manifest = json.load(open(os.path.join(run_dir, "manifest.json")))
    assert manifest                                  # every artifact hashed
    for rel in manifest:
        assert os.path.exists(os.path.join(run_dir, rel))     # RETAINED
    import hashlib
    expected = hashlib.sha256(
        open(os.path.join(run_dir, "manifest.json"), "rb").read()).hexdigest()
    assert rep["manifest_sha256"] == expected
    assert "manifest.json" not in manifest and "report.json" not in manifest
    # a second invocation gets a DIFFERENT empty dir
    r2 = orch._run_invariance_core(
        str(tmp_path), str(tmp_path / "r2.json"), profiles=_profiles(),
        schedule_seeds=(818201,), widths=(1, 3, 5), violator_seeds=(),
        ceiling_seconds=3600, replay_runner=_fake_runner())
    assert r2["run_dir"] != run_dir


def test_production_entry_signature_is_frozen():
    import inspect
    params = inspect.signature(orch.run_invariance).parameters
    assert list(params) == ["work_dir", "report_path", "archive_dir"]


def test_never_imports_forbidden_surfaces():
    import inspect
    src = inspect.getsource(orch)
    assert "write_recoverability_artifact" not in src
    assert "check_positive_control" not in src

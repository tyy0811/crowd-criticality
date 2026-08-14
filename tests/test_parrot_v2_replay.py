# tests/test_parrot_v2_replay.py
import asyncio, pytest
from critaudit.sim.controls.parrot_v2_profile import CohortActionProfile
from critaudit.sim.controls.parrot_v2_schedule import build_schedule_envelope
from critaudit.sim.controls.parrot_v2_records import (
    canonical_served_encoding, decode_emission_record, served_hash)
from critaudit.sim.harness.observables import GATED_OBSERVABLES

pytestmark = pytest.mark.slow


def _profile():
    return CohortActionProfile(
        window_seed=20260627,
        per_round_type_counts=((2, 0, 0, 0), (0, 1, 1, 1)),   # news-ADJUSTED
        per_round_refresh_counts=(1, 2),
        news_events=((1, "NEWS ITEM"),),
        authored_corpus=("alpha", "beta", "gamma"))


def _envelope():
    return build_schedule_envelope(_profile(), 818201)


def test_replay_identity_ledger_and_counts(tmp_path):
    from critaudit.experiments.parrot_v2_replay import replay_envelope
    env = _envelope()
    out = asyncio.run(replay_envelope(env, width=3,
                                      database_path=str(tmp_path / "w3.db")))
    assert out["width"] == 3 and out["n_rounds"] == 2
    # identity echo
    assert out["schedule_seed"] == 818201
    assert out["assigned_window"] == 20260627
    assert out["schedule_sha256"] == env.schedule_sha256
    assert out["platform_seed"] == env.platform_seed
    assert len(out["graph_sha256"]) == 64             # paired-graph provenance
    # emissions: r0 = 2 create_post; r1 = 1 comment + 1 repost + 1 quote + 1 news = 6
    assert out["observables"]["n_events"] == 6
    # ledger: one entry per SCHEDULED refresh, keyed by schedule index, empty incl.
    assert len(out["refresh_ledger"]) == 3
    for entry in out["refresh_ledger"]:
        assert set(entry) == {"schedule_index", "agent_id", "round", "outcome",
                              "served_item_ids", "trace_seq"}
        assert entry["outcome"] in ("served", "empty")
        if entry["outcome"] == "empty":
            assert entry["served_item_ids"] == [] and entry["trace_seq"] is None


def test_emission_invariance_toy_gated_only(tmp_path):
    """Rig mini-invariance at toy scale: emission bytes + the FOUR gated
    observables. read_emit_ratio is descriptive and MAY differ across widths."""
    from critaudit.experiments.parrot_v2_replay import replay_envelope
    import random
    env = _envelope()
    outs = {}
    for w in (1, 5):
        random.seed(env.platform_seed)            # same platform seed across widths
        outs[w] = asyncio.run(replay_envelope(
            env, width=w, database_path=str(tmp_path / f"w{w}.db")))
    assert outs[1]["emission_record_b64"] == outs[5]["emission_record_b64"]
    for key in GATED_OBSERVABLES:
        assert outs[1]["observables"][key] == outs[5]["observables"][key]


def test_violator_hashes_every_scheduled_refresh(tmp_path):
    """Additions are identified ONLY via the recorded violator_item_ids —
    cross-database id set difference is invalid (violator posts shift ids)."""
    from critaudit.experiments.parrot_v2_replay import replay_envelope
    import random
    env = _envelope()
    random.seed(env.platform_seed)
    base = asyncio.run(replay_envelope(env, width=3,
                                       database_path=str(tmp_path / "b.db")))
    assert base["violator_item_ids"] == []
    random.seed(env.platform_seed)
    vio = asyncio.run(replay_envelope(env, width=3, violator=True,
                                      database_path=str(tmp_path / "v.db")))
    n_scheduled = len(vio["refresh_ledger"])          # EVERY scheduled refresh
    assert n_scheduled == 3
    assert vio["observables"]["n_events"] == base["observables"]["n_events"] + n_scheduled
    assert len(vio["violator_item_ids"]) == n_scheduled
    by_id = {e.item_id: e for e in decode_emission_record(vio["emission_record_b64"])}
    got_hashes = sorted(by_id[i].content for i in vio["violator_item_ids"])
    expected_hashes = sorted(
        served_hash(entry["served_item_ids"]) for entry in vio["refresh_ledger"])
    assert got_hashes == expected_hashes              # hash MULTISET from the ledger
    assert all(len(h) == 64 and set(h) <= set("0123456789abcdef")
               for h in got_hashes)
    empties = [l for l in vio["refresh_ledger"] if l["outcome"] == "empty"]
    if empties:
        assert served_hash([]) in got_hashes
    assert canonical_served_encoding([]) == b"[]"


def test_subprocess_roundtrip(tmp_path):
    from critaudit.sim.controls.parrot_v2_schedule import envelope_to_bytes
    from critaudit.experiments.parrot_v2_replay import (
        read_replay_output, run_replay_subprocess)
    env = _envelope()
    ep = tmp_path / "env.bin"; ep.write_bytes(envelope_to_bytes(env))
    out = tmp_path / "out.json"
    run_replay_subprocess(str(ep), width=3, database_path=str(tmp_path / "s.db"),
                          out_path=str(out), violator=False, timeout=600)
    payload = read_replay_output(str(out))
    assert payload["width"] == 3 and payload["platform_seed"] == env.platform_seed
    with open(out, "ab") as fh:
        fh.write(b" ")
    with pytest.raises(ValueError, match="digest"):
        read_replay_output(str(out))

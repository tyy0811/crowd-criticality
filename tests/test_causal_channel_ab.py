"""Lever-1 acceptance gate 2: concurrency-matched one-session A/B. A full scripted-control
session at real sign-up contention (~300 agents) run under BOTH the stock OASIS Channel and
LowLatencyChannel must produce byte-identical recorded quantities — hashes, ProbeManifest,
ledgers, R_reply estimate, AND canonical trace/post/comment/user/rec DB rows. This measures that
event-driven wake-order (the only thing lever 1 changes) reaches no recorded quantity or DB row.
"""
from __future__ import annotations

import sqlite3

import pytest

from critaudit.sim.controls.causal_probe_control import (
    CONTROL_SEED_STREAM,
    build_scripted_control_frame,
    run_scripted_oasis_control,
)
from critaudit.sim.harness.causal_probe import estimate_r_reply


def _canonical_db(path):
    """Canonical dump of EVERY table in the database — enumerated from sqlite_master
    (not a hard-coded list), including `sqlite_sequence` (the AUTOINCREMENT counter
    state), so channel-induced insertion-order differences cannot hide in any table."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = sorted(
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall())
    out = {"__tables__": tables}
    for table in tables:
        rows = con.execute(f'SELECT * FROM "{table}"').fetchall()
        out[table] = sorted(repr(row) for row in rows)   # content, order-independent
    con.close()
    return out


def test_channel_transport_equivalence_ab(tmp_path, monkeypatch):
    pytest.importorskip("oasis")
    from oasis.social_platform.channel import Channel

    # ~303 agents: 100 authors + 200 recipients + filler + news -> real concurrent sign-up load
    frame, truth = build_scripted_control_frame(
        parent_count=100, recipients_per_parent=2, plant_r=1.0, seed=7)

    def _run(db_name):
        return run_scripted_oasis_control(
            frame, truth, run_id="run:ab",
            seed_stream_id=CONTROL_SEED_STREAM, seed=7,
            database_path=str(tmp_path / db_name))

    # arm A: LowLatencyChannel (the wired production default)
    low = _run("low.db")

    # arm B: stock Channel — patch the lazy import target in the channel module so the
    # bridge's `from ...causal_channel import LowLatencyChannel` resolves to the stock class
    monkeypatch.setattr(
        "critaudit.sim.harness.causal_channel.LowLatencyChannel", Channel)
    stock = _run("stock.db")

    # recorded quantities identical
    assert low.frame_sha256 == stock.frame_sha256
    assert low.frame_bytes == stock.frame_bytes
    assert low.eligibility_evidence_sha256 == stock.eligibility_evidence_sha256
    assert low.eligibility_evidence_bytes == stock.eligibility_evidence_bytes
    assert low.manifest == stock.manifest
    assert low.draws == stock.draws
    assert low.assignments == stock.assignments
    assert low.outcomes == stock.outcomes

    # estimate identical
    est_low = estimate_r_reply(frame, low.draws, low.assignments, low.outcomes)
    est_stock = estimate_r_reply(frame, stock.draws, stock.assignments, stock.outcomes)
    assert est_low == est_stock

    # canonical DB rows identical across EVERY table (enumerated from sqlite_master,
    # incl. sqlite_sequence), not a hard-coded subset
    low_db = _canonical_db(str(tmp_path / "low.db"))
    stock_db = _canonical_db(str(tmp_path / "stock.db"))
    # prove the comparison actually covers the full schema + the autoincrement state
    assert low_db["__tables__"] == stock_db["__tables__"]
    assert "sqlite_sequence" in low_db["__tables__"]
    assert len(low_db["__tables__"]) > 6           # more than the old hard-coded list
    assert low_db == stock_db

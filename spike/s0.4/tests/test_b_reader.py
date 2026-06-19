import json

import numpy as np
import pytest

from b_reader import read_markets, MarketEvents


def _rec(asset, ts_ms, price="0.5", event_type="last_trade_price", recv=0.0):
    return json.dumps({"recv_ts": recv,
                       "msg": {"event_type": event_type, "asset_id": asset,
                               "timestamp": str(ts_ms), "price": price}})


def _write(tmp_path, lines, newline="\n"):
    p = tmp_path / "cap.jsonl"
    p.write_text(newline.join(lines) + newline, encoding="utf-8")
    return str(p)


def test_zero_bases_and_converts_ms_to_seconds(tmp_path):
    t0 = 1_700_000_000_000  # large Unix-ms origin -- the real-data path, not simulate()'s t=0
    path = _write(tmp_path, [_rec("A", t0), _rec("A", t0 + 500), _rec("A", t0 + 1500)])
    (m,) = read_markets(path)
    assert isinstance(m, MarketEvents) and m.asset_id == "A"
    np.testing.assert_allclose(m.times, [0.0, 0.5, 1.5])
    assert m.horizon == 1.5
    assert abs(m.t0_unix_s - t0 / 1000.0) < 1e-6
    assert m.n_events == 3


def test_groups_by_asset_and_sorts(tmp_path):
    t0 = 1_700_000_000_000
    path = _write(tmp_path, [_rec("A", t0 + 1000), _rec("B", t0), _rec("A", t0)])
    markets = {m.asset_id: m for m in read_markets(path)}
    assert set(markets) == {"A", "B"}
    np.testing.assert_allclose(markets["A"].times, [0.0, 1.0])   # sorted within market


def test_keeps_ties_under_fill_and_collapses_under_match(tmp_path):
    t0 = 1_700_000_000_000
    # 3 fills share one ms (a multi-fill match) + 1 later trade
    path = _write(tmp_path, [_rec("A", t0, price="0.5"), _rec("A", t0, price="0.5"),
                             _rec("A", t0, price="0.5"), _rec("A", t0 + 2000)])
    (m_fill,) = read_markets(path, event_unit="fill")
    assert m_fill.n_events == 4
    assert m_fill.max_ms_multiplicity == 3
    assert m_fill.n_tied_events == 3
    (m_match,) = read_markets(path, event_unit="match")
    assert m_match.n_events == 2                       # same-(asset, ms) collapsed to one
    assert m_match.max_ms_multiplicity == 3            # diagnostics stay fill-level


def test_skips_malformed_and_non_trade_lines(tmp_path):
    t0 = 1_700_000_000_000
    lines = [_rec("A", t0), "{not valid json",
             _rec("A", t0 + 100, event_type="book"), _rec("A", t0 + 200)]
    path = _write(tmp_path, lines)
    (m,) = read_markets(path)
    assert m.n_events == 2                              # the trade lines only


def test_handles_crlf_and_empty(tmp_path):
    t0 = 1_700_000_000_000
    path = _write(tmp_path, [_rec("A", t0), _rec("A", t0 + 100)], newline="\r\n")
    (m,) = read_markets(path)
    assert m.n_events == 2
    empty = tmp_path / "empty.jsonl"; empty.write_text("", encoding="utf-8")
    assert read_markets(str(empty)) == []


def test_dup_price_consecutive_count(tmp_path):
    t0 = 1_700_000_000_000
    path = _write(tmp_path, [_rec("A", t0, price="0.5"), _rec("A", t0 + 1, price="0.5"),
                             _rec("A", t0 + 2, price="0.6")])
    (m,) = read_markets(path)
    assert m.n_dup_price_consecutive == 1              # the 2nd 0.5 repeats the 1st


def test_skips_overflow_timestamp_and_unhashable_asset(tmp_path):
    # #7: JSON-valid but pathological records must be SKIPPED, not crash the reader. int(float("1e999"))
    # raises OverflowError; an unhashable/non-string asset_id breaks the per-asset dict.
    t0 = 1_700_000_000_000
    lines = [
        _rec("A", t0),
        json.dumps({"recv_ts": 0.0, "msg": {"event_type": "last_trade_price", "asset_id": "A",
                                            "timestamp": "1e999", "price": "0.5"}}),       # float inf -> OverflowError
        json.dumps({"recv_ts": 0.0, "msg": {"event_type": "last_trade_price", "asset_id": ["bad"],
                                            "timestamp": str(t0 + 100), "price": "0.5"}}),  # unhashable asset
        _rec("A", t0 + 200),
    ]
    path = _write(tmp_path, lines)
    (m,) = read_markets(path)                           # must not raise
    assert m.asset_id == "A" and m.n_events == 2        # only the two clean A trades

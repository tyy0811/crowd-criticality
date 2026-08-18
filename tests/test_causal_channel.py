"""Lever-1 unit stress test: LowLatencyChannel Future-only lifecycle under adversarial
orderings — correct delivery, no lost/duplicated wakeups, empty `_futures` after every case."""
from __future__ import annotations

import asyncio

import pytest

from critaudit.sim.harness.causal_channel import LowLatencyChannel


def _run(coro):
    return asyncio.run(coro)


async def _platform_reply(ch, message_id, agent_id, result):
    await ch.send_to((message_id, agent_id, result))


def test_read_before_send():
    async def scenario():
        ch = LowLatencyChannel()
        mid = await ch.write_to_receive_queue((1, "act", "create_post"))
        read_task = asyncio.ensure_future(ch.read_from_send_queue(mid))
        await asyncio.sleep(0)                       # let the read start and await
        assert not read_task.done()
        await ch.send_to((mid, 1, {"ok": True}))
        result = await read_task
        assert result == (mid, 1, {"ok": True})
        assert ch._futures == {}
    _run(scenario())


def test_send_before_read():
    async def scenario():
        ch = LowLatencyChannel()
        mid = await ch.write_to_receive_queue((1, "act", "create_post"))
        await ch.send_to((mid, 1, {"ok": True}))      # response arrives first
        result = await ch.read_from_send_queue(mid)    # read returns it immediately
        assert result == (mid, 1, {"ok": True})
        assert ch._futures == {}
    _run(scenario())


def test_concurrent_distinct_ids():
    async def scenario():
        ch = LowLatencyChannel()
        mids = [await ch.write_to_receive_queue((i, "a", "create_post")) for i in range(200)]
        reads = [asyncio.ensure_future(ch.read_from_send_queue(m)) for m in mids]
        await asyncio.sleep(0)
        # resolve in a shuffled-ish order (reverse) to exercise independence
        for i, m in reversed(list(enumerate(mids))):
            await ch.send_to((m, i, {"n": i}))
        results = await asyncio.gather(*reads)
        assert results == [(m, i, {"n": i}) for i, m in enumerate(mids)]
        assert ch._futures == {}
    _run(scenario())


def test_duplicate_send_is_first_wins():
    async def scenario():
        ch = LowLatencyChannel()
        mid = await ch.write_to_receive_queue((1, "a", "create_post"))
        read_task = asyncio.ensure_future(ch.read_from_send_queue(mid))
        await asyncio.sleep(0)
        await ch.send_to((mid, 1, {"first": True}))    # first wins
        await ch.send_to((mid, 1, {"second": True}))   # duplicate: discarded, no raise
        result = await read_task
        assert result == (mid, 1, {"first": True})
        assert ch._futures == {}
    _run(scenario())


def test_cancellation_then_late_send_is_discarded_and_clean():
    async def scenario():
        ch = LowLatencyChannel()
        mid = await ch.write_to_receive_queue((1, "a", "create_post"))
        read_task = asyncio.ensure_future(ch.read_from_send_queue(mid))
        await asyncio.sleep(0)
        read_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await read_task
        assert ch._futures == {}                       # cancellation cleaned up
        # a LATE response for the cancelled id must be discarded, not leak
        await ch.send_to((mid, 1, {"late": True}))
        assert ch._futures == {}
    _run(scenario())


def test_exit_sentinel_registers_no_future():
    async def scenario():
        ch = LowLatencyChannel()
        mid = await ch.write_to_receive_queue((None, None, "exit"))
        assert mid not in ch._futures
        assert ch._futures == {}
        # receive side still delivers the sentinel to the platform loop
        got = await ch.receive_from()
        assert got == (mid, (None, None, "exit"))
    _run(scenario())


def test_interleaved_load_no_leak():
    """Many requests with interleaved reads/sends/one cancellation: all delivered
    correctly and `_futures` fully drained."""
    async def scenario():
        ch = LowLatencyChannel()
        mids = [await ch.write_to_receive_queue((i, "a", "create_post")) for i in range(50)]
        reads = {m: asyncio.ensure_future(ch.read_from_send_queue(m)) for m in mids}
        await asyncio.sleep(0)
        reads[mids[10]].cancel()                       # cancel one mid-flight
        with pytest.raises(asyncio.CancelledError):
            await reads[mids[10]]
        for i, m in enumerate(mids):
            await ch.send_to((m, i, {"n": i}))         # includes a late send for the cancelled id
        done = await asyncio.gather(*(reads[m] for m in mids if m != mids[10]))
        assert done == [(m, i, {"n": i}) for i, m in enumerate(mids) if m != mids[10]]
        assert ch._futures == {}
    _run(scenario())

"""Event-driven, low-latency drop-in for the OASIS ``Channel`` (lever 1, runtime-only).

The stock OASIS channel polls ``read_from_send_queue`` on a fixed 0.1 s sleep, which
is ~100 ms of the measured ~100.7 ms per platform action. This channel delivers each
response via a per-request ``asyncio.Future`` resolved the instant the platform calls
``send_to`` — so an awaited action returns as soon as its response exists.

It implements ONLY the four methods the OASIS core uses (``receive_from``, ``send_to``,
``write_to_receive_queue``, ``read_from_send_queue``), so it is a standalone class — no
subclassing, no ``oasis`` import. Delivery is **Future-only** (there is no ``send_dict``),
which removes the class of bug where a late ``send_to`` after a Future was popped would
leave an unconsumed second delivery structure. It changes only WHEN an action's response
is delivered, never WHAT is delivered, so it is transport-only: recorded quantities are
functions of logical time and seeded RNG, not wall clock or wake order.
"""

from __future__ import annotations

import asyncio
import uuid

__all__ = ("LowLatencyChannel",)


def _is_exit_sentinel(action_info: object) -> bool:
    """The EXIT sentinel is enqueued by ``env.close`` as ``(None, None, EXIT)``; every
    real action carries a concrete ``agent_id`` in slot 0. The platform never responds
    to EXIT and ``env.close`` never reads it, so registering a Future for it would
    dangle. Detected structurally to avoid importing the ``oasis`` ActionType."""
    return isinstance(action_info, tuple) and len(action_info) >= 1 and action_info[0] is None


class LowLatencyChannel:
    """Future-only event-driven channel. Drop-in for ``oasis...Channel``."""

    def __init__(self) -> None:
        self.receive_queue: asyncio.Queue = asyncio.Queue()
        self._futures: dict[str, asyncio.Future] = {}

    async def receive_from(self):
        return await self.receive_queue.get()

    async def write_to_receive_queue(self, action_info) -> str:
        message_id = str(uuid.uuid4())
        # Register the Future BEFORE the request can reach the platform (and thus
        # send_to): this closes the send-before-read window. Skip the EXIT sentinel.
        if not _is_exit_sentinel(action_info):
            self._futures[message_id] = asyncio.get_running_loop().create_future()
        await self.receive_queue.put((message_id, action_info))
        return message_id

    async def send_to(self, message) -> None:
        message_id = message[0]
        fut = self._futures.get(message_id)
        # Missing Future  -> late response (read cancelled/completed) or a duplicate
        #                    whose Future was already popped: discard, nothing leaks.
        # Future already done -> duplicate response: deterministic first-wins, discard.
        if fut is None or fut.done():
            return
        fut.set_result(message)

    async def read_from_send_queue(self, message_id: str):
        fut = self._futures.get(message_id)
        if fut is None:
            # Defensive read-before-send (should not occur on the confirmed
            # write->read agent path, which registers the Future in write).
            fut = asyncio.get_running_loop().create_future()
            self._futures[message_id] = fut
        try:
            return await fut
        finally:
            # Cleanup on BOTH success and cancellation. After this the id is gone,
            # so any later send_to for it hits the missing-Future discard branch.
            self._futures.pop(message_id, None)

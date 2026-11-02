from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import asdict
from threading import Lock
from typing import Any, AsyncIterator

from b2t.models import ProgressSnapshot


_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


class SSEManager:
    """Bridge between the ThreadPoolExecutor-based task worker and FastAPI's
    async event loop so that progress updates can be streamed via SSE."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = defaultdict(list)
        self._lock = Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # -- public API (called from async endpoints) -----------------------

    def bind_loop(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Bind the running asyncio event loop.  Must be called once at
        application startup (from inside an async context)."""
        self._loop = loop or asyncio.get_running_loop()

    def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any] | None]:
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        with self._lock:
            self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        with self._lock:
            queues = self._subscribers.get(task_id, [])
            try:
                queues.remove(queue)
            except ValueError:
                pass
            if not queues:
                self._subscribers.pop(task_id, None)

    async def event_stream(
        self,
        task_ids: list[str],
        *,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Yield SSE-formatted strings for one or more task ids.

        *history* is a list of already-serialised events that should be
        replayed to a newly-connecting client so it can catch up.
        """
        queues: dict[str, asyncio.Queue[dict[str, Any] | None]] = {}
        for tid in task_ids:
            queues[tid] = self.subscribe(tid)

        try:
            # Replay historical events first.
            if history:
                for event in history:
                    yield _format_sse("progress", event)

            # Stream live events until every watched task reaches a terminal
            # state.
            finished = {tid: False for tid in task_ids}
            while not all(finished.values()):
                # Wait for the next event from *any* subscribed queue.
                done_queues = {tid: q for tid, q in queues.items() if not finished[tid]}
                if not done_queues:
                    break

                # Use asyncio.wait on all queue-get tasks.
                tasks = {asyncio.ensure_future(q.get()): tid for tid, q in done_queues.items()}
                done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

                for completed_task in done:
                    tid = tasks[completed_task]
                    try:
                        payload = completed_task.result()
                    except Exception:
                        continue

                    if payload is None:
                        # Sentinel — queue closed.
                        finished[tid] = True
                        continue

                    yield _format_sse("progress", payload)

                    if payload.get("status") in _TERMINAL_STATUSES:
                        finished[tid] = True
        finally:
            for tid, q in queues.items():
                self.unsubscribe(tid, q)

    # -- public API (called from worker threads) -----------------------

    def publish(self, snapshot: ProgressSnapshot) -> None:
        """Push a progress snapshot to all SSE subscribers.

        Safe to call from any thread — it schedules the queue put on the
        bound asyncio event loop.
        """
        payload = asdict(snapshot)
        with self._lock:
            queues = list(self._subscribers.get(snapshot.task_id, []))

        loop = self._loop
        if loop is None or loop.is_closed():
            # No running loop yet — silently drop.
            return

        for queue in queues:
            asyncio.run_coroutine_threadsafe(queue.put(payload), loop)

    def notify_terminal(self, task_id: str) -> None:
        """Send a sentinel ``None`` to all subscribers so their generators
        can exit cleanly."""
        with self._lock:
            queues = list(self._subscribers.get(task_id, []))

        loop = self._loop
        if loop is None or loop.is_closed():
            return

        for queue in queues:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)


# -- helpers ---------------------------------------------------------------


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

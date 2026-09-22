"""Async relay orchestration: capture, infer, enqueue, and drain without unbounded work."""

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Protocol, Any

from .queue import BoundedEventQueue
from .schema import EventEnvelope


class Sink(Protocol):
    async def __call__(self, event: EventEnvelope) -> None: ...


class Relay:
    def __init__(self, queue: BoundedEventQueue[EventEnvelope], sink: Sink):
        self.queue = queue
        self.sink = sink
        self._worker: Optional[asyncio.Task[None]] = None
        self._stopping = False

    async def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._stopping = False
            self._worker = asyncio.create_task(self._drain())

    async def stop(self) -> None:
        self._stopping = True
        await self.queue.join()
        if self._worker:
            await self._worker
            self._worker = None

    async def ingest(self, event: EventEnvelope):
        return self.queue.offer(event.normalized())

    async def _drain(self) -> None:
        while not self._stopping or self.queue.qsize():
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            try:
                await self.sink(event)
            finally:
                self.queue.task_done()

    async def capture_and_infer(self, capture: Any, inference: Any, device_id: str, frames: int) -> None:
        """Run a finite deterministic capture loop; overload is reported by ingest's result."""
        for index in range(frames):
            frame = await capture.capture(index)
            result = await inference.infer(frame)
            await self.ingest(EventEnvelope(device_id=device_id, event_type="vision.observation",
                captured_at=datetime.now(timezone.utc), payload=result,
                confidence=1.0 if result.get("label") == "person" else 0.0))

"""Bounded queue with observable, explicit overload behavior."""

import asyncio
from enum import Enum
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class DropPolicy(str, Enum):
    DROP_NEWEST = "drop_newest"
    DROP_OLDEST = "drop_oldest"


class EnqueueResult(Generic[T]):
    def __init__(self, accepted: bool, dropped: Optional[T] = None, reason: str = "accepted"):
        self.accepted = accepted
        self.dropped = dropped
        self.reason = reason


class BoundedEventQueue(Generic[T]):
    """Non-blocking producer queue; producers never wait indefinitely under load."""

    def __init__(self, maxsize: int = 256, policy: DropPolicy = DropPolicy.DROP_NEWEST):
        if maxsize < 1:
            raise ValueError("maxsize must be positive")
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)
        self.policy = policy
        self.accepted_count = 0
        self.dropped_count = 0

    def offer(self, item: T) -> EnqueueResult[T]:
        try:
            self._queue.put_nowait(item)
            self.accepted_count += 1
            return EnqueueResult(True)
        except asyncio.QueueFull:
            if self.policy == DropPolicy.DROP_OLDEST:
                dropped = self._queue.get_nowait()
                self._queue.task_done()
                self._queue.put_nowait(item)
                self.accepted_count += 1
                self.dropped_count += 1
                return EnqueueResult(True, dropped, "dropped_oldest")
            self.dropped_count += 1
            return EnqueueResult(False, item, "dropped_newest")

    async def get(self) -> T:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()

    async def join(self) -> None:
        await self._queue.join()

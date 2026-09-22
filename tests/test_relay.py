from datetime import datetime, timezone

import httpx
import pytest

from edge_vision_relay.api import create_app
from edge_vision_relay.fake import FakeCapture, FakeInference
from edge_vision_relay.queue import BoundedEventQueue, DropPolicy
from edge_vision_relay.relay import Relay
from edge_vision_relay.schema import EventEnvelope


def event(**overrides):
    values = {
        "device_id": "cam-01",
        "event_type": "vision.observation",
        "captured_at": datetime(2026, 1, 1, 12, 0),
        "payload": {"label": "person"},
    }
    values.update(overrides)
    return EventEnvelope(**values)


def test_event_normalized_to_utc():
    normalized = event().normalized()

    assert normalized.captured_at.tzinfo == timezone.utc
    assert normalized.captured_at.hour == 12


def test_queue_drop_newest_is_explicit():
    queue = BoundedEventQueue[int](maxsize=1)
    queue.offer(1)

    result = queue.offer(2)

    assert not result.accepted
    assert result.dropped == 2
    assert result.reason == "dropped_newest"
    assert queue.dropped_count == 1


@pytest.mark.asyncio
async def test_queue_drop_oldest_keeps_newest_item():
    queue = BoundedEventQueue[int](maxsize=1, policy=DropPolicy.DROP_OLDEST)
    queue.offer(1)

    result = queue.offer(2)

    assert result.accepted
    assert result.dropped == 1
    assert await queue.get() == 2
    queue.task_done()


@pytest.mark.asyncio
async def test_relay_drains_events_and_capture_pipeline():
    received = []

    async def sink(observation):
        received.append(observation)

    relay = Relay(BoundedEventQueue[EventEnvelope](4), sink)
    await relay.start()
    await relay.capture_and_infer(FakeCapture(), FakeInference(), "cam-01", frames=3)
    await relay.stop()

    assert [item.payload["label"] for item in received] == ["person", "empty", "person"]
    assert all(item.device_id == "cam-01" for item in received)


@pytest.mark.asyncio
async def test_api_accepts_events_and_reports_health():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/events", json={
            "device_id": "cam-01",
            "event_type": "vision.observation",
            "payload": {"label": "empty"},
        })
        health = await client.get("/healthz")

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    assert health.json() == {"status": "ok", "schema_version": "1.0", "queue_depth": 1}

"""HTTP surface for health checks and versioned event ingestion."""

from fastapi import FastAPI, HTTPException, status

from .queue import BoundedEventQueue
from .relay import Relay
from .schema import EventEnvelope, SCHEMA_VERSION


def create_app(relay: Relay = None) -> FastAPI:
    queue = relay.queue if relay else BoundedEventQueue[EventEnvelope](256)
    app = FastAPI(title="Edge Vision Relay", version="0.1.0")
    app.state.relay = relay
    app.state.queue = queue

    @app.get("/healthz")
    async def health():
        return {"status": "ok", "schema_version": SCHEMA_VERSION, "queue_depth": queue.qsize()}

    @app.post("/v1/events", status_code=status.HTTP_202_ACCEPTED)
    async def ingest(event: EventEnvelope):
        result = await relay.ingest(event) if relay else queue.offer(event.normalized())
        if not result.accepted:
            raise HTTPException(status_code=429, detail={"reason": result.reason, "dropped": 1})
        return {"accepted": True, "event_id": str(event.event_id), "drop_reason": result.reason if result.dropped else None}

    return app

# Edge Vision Relay

A small, dependency-light FastAPI service for moving edge computer-vision observations into an asynchronous, bounded queue. It makes overload behavior explicit instead of allowing producers to block indefinitely or letting memory grow without a limit.

## Quickstart

```bash
cd edge-vision-relay
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
uvicorn edge_vision_relay.__main__:app --app-dir src --reload
```

The service listens on `http://127.0.0.1:8000` by default when started with Uvicorn.

## API

Check service and queue state:

```bash
curl http://127.0.0.1:8000/healthz
```

Submit an observation:

```bash
curl -X POST http://127.0.0.1:8000/v1/events \
  -H 'content-type: application/json' \
  -d '{"device_id":"cam-01","event_type":"vision.observation","payload":{"label":"person"},"confidence":0.98}'
```

`202 Accepted` means the event entered the queue. The default queue holds 256 events and uses `drop_newest` when full, returning `429 Too Many Requests` with an explicit drop reason. `drop_oldest` is available when constructing `BoundedEventQueue` for an embedded deployment.

## Architecture

- `schema.py` defines the stable `EventEnvelope` contract and UTC normalization.
- `queue.py` provides non-blocking bounded enqueue behavior and counters.
- `relay.py` drains events asynchronously to an injected sink and includes a finite capture/inference seam for device adapters.
- `api.py` exposes health and versioned ingestion endpoints.
- `fake.py` provides deterministic capture and inference fixtures for demos and tests.

The default module-level app queues events but does not persist or forward them. Production wiring should construct a `Relay` with a durable or observable sink, configure deployment-specific limits, and add authentication and transport encryption at the edge boundary.

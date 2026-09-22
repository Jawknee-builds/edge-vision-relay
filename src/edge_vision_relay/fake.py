"""Deterministic capture and inference implementations for tests and demos."""

from typing import Dict, Any


class FakeCapture:
    def __init__(self, frames: int = 3):
        self.frames = frames

    async def capture(self, index: int) -> Dict[str, Any]:
        return {"frame_index": index, "pixels": "fixture"}


class FakeInference:
    async def infer(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        index = int(frame["frame_index"])
        return {"label": "person" if index % 2 == 0 else "empty", "frame_index": index}

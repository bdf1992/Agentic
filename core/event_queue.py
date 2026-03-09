"""
Event queue — receives hook events, classifies them, dispatches to agents.

Events are dicts with:
    type:      str   — what happened (file_changed, commit, test_failed, timer, command)
    repo:      str   — which repo (system3, RiftEngine, FieldForge, InvertedSand, Agentic)
    payload:   dict  — type-specific data
    timestamp: float — when it happened
"""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Callable

QUEUE_DIR = Path(__file__).parent.parent / "data" / "events"


@dataclass
class Event:
    type: str
    repo: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.type}_{self.repo}_{int(self.timestamp * 1000)}"


class EventQueue:
    """Thread-safe in-memory event queue with optional persistence."""

    def __init__(self, persist: bool = True):
        self._queue: deque[Event] = deque()
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()
        self._persist = persist
        if persist:
            QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    def emit(self, event_type: str, repo: str = "unknown", **payload) -> Event:
        """Push an event onto the queue."""
        ev = Event(type=event_type, repo=repo, payload=payload)
        with self._lock:
            self._queue.append(ev)
        if self._persist:
            self._write(ev)
        self._dispatch(ev)
        return ev

    def register(self, event_type: str, handler: Callable):
        """Register a handler for an event type. Use '*' for all events."""
        self._handlers.setdefault(event_type, []).append(handler)

    def drain(self, limit: int = 100) -> list[Event]:
        """Pull up to `limit` events off the queue."""
        with self._lock:
            batch = []
            for _ in range(min(limit, len(self._queue))):
                batch.append(self._queue.popleft())
            return batch

    def pending(self) -> int:
        return len(self._queue)

    def _dispatch(self, ev: Event):
        for handler in self._handlers.get(ev.type, []) + self._handlers.get("*", []):
            try:
                handler(ev)
            except Exception as e:
                print(f"[EventQueue] handler error for {ev.type}: {e}")

    def _write(self, ev: Event):
        path = QUEUE_DIR / f"{ev.id}.json"
        path.write_text(json.dumps(asdict(ev), indent=2))


# Module-level convenience
_default_queue = EventQueue(persist=True)


def emit(event_type: str, repo: str = "unknown", **payload) -> Event:
    """Emit an event to the default queue."""
    return _default_queue.emit(event_type, repo=repo, **payload)


def register(event_type: str, handler: Callable):
    """Register a handler on the default queue."""
    _default_queue.register(event_type, handler)


def queue() -> EventQueue:
    """Get the default queue instance."""
    return _default_queue

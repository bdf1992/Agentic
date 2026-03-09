"""
Event Dispatcher — the autonomic nervous system.

Connects the event queue to agent spawning. When an event arrives:
1. Check trigger rules to determine which agent type should handle it
2. Spawn matching agents via the config-based spawner
3. Collect findings into state for dashboard review

The dispatcher is what makes the platform autonomous.
Without it, events pile up and nothing happens.

Usage:
    from core.dispatcher import Dispatcher
    d = Dispatcher()
    d.start()           # begins listening on the event queue
    d.stop()            # graceful shutdown
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

from core.event_queue import Event, register, queue
from core.state import state
from agents.configs import AGENTS, get_agent_config


# ---------------------------------------------------------------------------
# Trigger rules: event type → agent type(s) to spawn
# ---------------------------------------------------------------------------

TRIGGER_RULES: dict[str, list[str]] = {
    # Code changes → validate
    "commit":        ["guardian"],
    "push":          ["guardian"],

    # Test failures → investigate
    "test_failed":   ["guardian"],

    # File changes in workspace → synthesis looks for patterns
    "file_changed":  ["synthesis"],

    # Scheduled / timer events → orchestrator decides
    "timer":         ["orchestrator"],
    "schedule":      ["orchestrator"],

    # Manual command events
    "command":       [],  # handled by payload["agent_type"] if present

    # Health alerts → infrastructure
    "health_alert":  ["infra"],

    # Build completion → judge + synthesis
    "build_complete": ["synthesis"],
}


class Dispatcher:
    """Routes events to matching agents via config-based spawning."""

    def __init__(self, poll_interval: float = 2.0):
        self._poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._recent_spawns: dict[str, float] = {}  # agent_type → last spawn time
        self._cooldown = 120.0  # seconds between spawns of same type

        agent_names = [cfg["name"] for cfg in AGENTS.values()]
        print(f"[dispatcher] Available agent types: {', '.join(agent_names)}")

    def start(self):
        """Start the dispatcher in a background thread."""
        if self._running:
            return

        self._running = True
        register("*", self._on_event)

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("[dispatcher] Started")

    def stop(self):
        """Stop the dispatcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[dispatcher] Stopped")

    def _on_event(self, event: Event):
        """Called when an event is emitted. Spawns matching agents."""
        # Determine which agent types to spawn
        agent_types = self._match(event)

        for agent_type in agent_types:
            if not self._can_spawn(agent_type):
                print(f"[dispatcher] {agent_type} on cooldown, skipping")
                continue

            try:
                # Lazy import to avoid circular dependency
                from agents.spawner import spawn_headless
                print(f"[dispatcher] {event.type} → spawning {agent_type}")
                spawn_headless(agent_type)
                with self._lock:
                    self._recent_spawns[agent_type] = time.time()
            except Exception as e:
                print(f"[dispatcher] Error spawning {agent_type}: {e}")

    def _match(self, event: Event) -> list[str]:
        """Determine which agent types should handle this event."""
        # Check for explicit agent_type in command events
        if event.type == "command" and "agent_type" in event.payload:
            requested = event.payload["agent_type"]
            if requested in AGENTS:
                return [requested]
            return []

        # Look up trigger rules
        return TRIGGER_RULES.get(event.type, [])

    def _can_spawn(self, agent_type: str) -> bool:
        """Check cooldown — don't spam the same agent type."""
        with self._lock:
            last = self._recent_spawns.get(agent_type, 0)
            return (time.time() - last) >= self._cooldown

    def _poll_loop(self):
        """Poll for spool files (events that arrived while server was down)."""
        spool_dir = Path(__file__).parent.parent / "data" / "spool"

        while self._running:
            if spool_dir.exists():
                for spool_file in sorted(spool_dir.glob("*.json")):
                    try:
                        data = json.loads(spool_file.read_text())
                        event = Event(
                            type=data.get("type", "unknown"),
                            repo=data.get("repo", "unknown"),
                            payload=data.get("payload", {}),
                        )
                        self._on_event(event)
                        spool_file.unlink()
                        print(f"[dispatcher] Consumed spool event: {event.type}")
                    except Exception as e:
                        print(f"[dispatcher] Bad spool file {spool_file}: {e}")

            time.sleep(self._poll_interval)

    def status(self) -> dict:
        """Current dispatcher state."""
        with self._lock:
            active_cooldowns = {
                k: round(self._cooldown - (time.time() - v))
                for k, v in self._recent_spawns.items()
                if (time.time() - v) < self._cooldown
            }
        return {
            "running": self._running,
            "agent_types": list(AGENTS.keys()),
            "trigger_rules": {k: v for k, v in TRIGGER_RULES.items() if v},
            "cooldowns": active_cooldowns,
        }

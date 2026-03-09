"""
Event Dispatcher — the autonomic nervous system.

Connects the event queue to the agent roster. When an event arrives:
1. Check all registered agent types for trigger matches
2. Spawn matching agents (in background threads)
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

import threading
import time
import importlib
from pathlib import Path
from typing import Optional

from core.event_queue import Event, register, queue
from core.state import state
from agents.base import Agent


# All agent classes, discovered from agents/ directory
def _discover_agents() -> list[type[Agent]]:
    """Find all Agent subclasses in agents/."""
    agents_dir = Path(__file__).parent.parent / "agents"
    agent_classes = []

    for py_file in agents_dir.glob("*_agent.py"):
        module_name = f"agents.{py_file.stem}"
        try:
            mod = importlib.import_module(module_name)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, Agent)
                        and attr is not Agent
                        and hasattr(attr, 'triggers')):
                    agent_classes.append(attr)
        except Exception as e:
            print(f"[dispatcher] Failed to load {module_name}: {e}")

    return agent_classes


class Dispatcher:
    """Routes events to matching agents."""

    def __init__(self, poll_interval: float = 2.0):
        self._agent_classes = _discover_agents()
        self._poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._workers: list[threading.Thread] = []

        # Log what we found
        names = [cls.name for cls in self._agent_classes]
        print(f"[dispatcher] Discovered {len(self._agent_classes)} agent types: {', '.join(names)}")

    def start(self):
        """Start the dispatcher in a background thread."""
        if self._running:
            return

        self._running = True

        # Register for all events on the queue
        register("*", self._on_event)

        # Also start a polling thread for batched/spool events
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("[dispatcher] Started")

    def stop(self):
        """Stop the dispatcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        # Wait for workers to finish
        for w in self._workers:
            w.join(timeout=10)
        print("[dispatcher] Stopped")

    def _on_event(self, event: Event):
        """Called immediately when an event is emitted. Spawns matching agents."""
        for agent_cls in self._agent_classes:
            try:
                agent = agent_cls()
                if agent.matches(event):
                    print(f"[dispatcher] {event.type} → spawning {agent.name}")
                    t = threading.Thread(
                        target=self._run_agent,
                        args=(agent, event),
                        daemon=True,
                    )
                    t.start()
                    self._workers.append(t)
            except Exception as e:
                print(f"[dispatcher] Error checking {agent_cls}: {e}")

        # Clean up finished workers
        self._workers = [w for w in self._workers if w.is_alive()]

    def _run_agent(self, agent: Agent, event: Event):
        """Execute an agent in a background thread."""
        try:
            finding = agent.execute(event)
            severity_icon = {
                "info": ".",
                "warning": "!",
                "action_required": "!!!",
            }.get(finding.severity, "?")

            print(f"[dispatcher] {agent.name} finished [{severity_icon}]: {finding.summary[:100]}")
        except Exception as e:
            print(f"[dispatcher] {agent.name} crashed: {e}")

    def _poll_loop(self):
        """Poll for spool files (events that arrived while server was down)."""
        spool_dir = Path(__file__).parent.parent / "data" / "spool"

        while self._running:
            # Check for spooled events
            if spool_dir.exists():
                import json
                for spool_file in spool_dir.glob("*.json"):
                    try:
                        data = json.loads(spool_file.read_text())
                        event = Event(
                            type=data.get("type", "unknown"),
                            repo=data.get("repo", "unknown"),
                            payload=data.get("payload", {}),
                        )
                        self._on_event(event)
                        spool_file.unlink()  # consumed
                        print(f"[dispatcher] Consumed spool event: {event.type}")
                    except Exception as e:
                        print(f"[dispatcher] Bad spool file {spool_file}: {e}")

            time.sleep(self._poll_interval)

    def status(self) -> dict:
        """Current dispatcher state."""
        return {
            "running": self._running,
            "agent_types": [cls.name for cls in self._agent_classes],
            "active_workers": len([w for w in self._workers if w.is_alive()]),
        }

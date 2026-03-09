"""
Manager state — tracks running agents, their results, and pending human reviews.

The state is the platform's working memory. It answers:
- What agents are alive right now?
- What finished since I last looked?
- What needs my decision?
"""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

STATE_DIR = Path(__file__).parent.parent / "data" / "state"


class AgentStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class AgentRecord:
    agent_id: str
    agent_type: str
    trigger_event: str
    status: AgentStatus = AgentStatus.RUNNING
    started: float = field(default_factory=time.time)
    finished: Optional[float] = None
    finding: Optional[str] = None
    severity: str = "info"  # info, warning, action_required
    human_decision: Optional[str] = None


class PlatformState:
    """Thread-safe platform state manager."""

    def __init__(self):
        self._agents: dict[str, AgentRecord] = {}
        self._lock = threading.Lock()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def spawn(self, agent_id: str, agent_type: str, trigger_event: str) -> AgentRecord:
        """Record a new agent spawn."""
        rec = AgentRecord(
            agent_id=agent_id,
            agent_type=agent_type,
            trigger_event=trigger_event,
        )
        with self._lock:
            self._agents[agent_id] = rec
        self._persist(rec)
        return rec

    def complete(self, agent_id: str, finding: str, severity: str = "info"):
        """Mark an agent as completed with its finding."""
        with self._lock:
            rec = self._agents[agent_id]
            rec.status = AgentStatus.COMPLETED
            rec.finished = time.time()
            rec.finding = finding
            rec.severity = severity
            if severity == "action_required":
                rec.status = AgentStatus.AWAITING_APPROVAL
        self._persist(rec)

    def fail(self, agent_id: str, error: str):
        """Mark an agent as failed."""
        with self._lock:
            rec = self._agents[agent_id]
            rec.status = AgentStatus.FAILED
            rec.finished = time.time()
            rec.finding = f"FAILED: {error}"
            rec.severity = "warning"
        self._persist(rec)

    def decide(self, agent_id: str, decision: str):
        """Record a human decision on a pending finding."""
        with self._lock:
            rec = self._agents[agent_id]
            rec.human_decision = decision
            rec.status = AgentStatus.APPROVED if decision == "approve" else AgentStatus.REJECTED
        self._persist(rec)

    def active(self) -> list[AgentRecord]:
        """All currently running agents."""
        with self._lock:
            return [r for r in self._agents.values() if r.status == AgentStatus.RUNNING]

    def pending_review(self) -> list[AgentRecord]:
        """All findings awaiting human decision."""
        with self._lock:
            return [r for r in self._agents.values() if r.status == AgentStatus.AWAITING_APPROVAL]

    def recent(self, limit: int = 20) -> list[AgentRecord]:
        """Most recent agent records."""
        with self._lock:
            records = sorted(self._agents.values(), key=lambda r: r.started, reverse=True)
            return records[:limit]

    def digest(self) -> dict:
        """Summary for the dashboard."""
        with self._lock:
            records = list(self._agents.values())
        return {
            "active": len([r for r in records if r.status == AgentStatus.RUNNING]),
            "pending_review": len([r for r in records if r.status == AgentStatus.AWAITING_APPROVAL]),
            "completed_today": len([
                r for r in records
                if r.status in (AgentStatus.COMPLETED, AgentStatus.APPROVED)
                and r.finished and r.finished > time.time() - 86400
            ]),
            "failed_today": len([
                r for r in records
                if r.status == AgentStatus.FAILED
                and r.finished and r.finished > time.time() - 86400
            ]),
        }

    def _persist(self, rec: AgentRecord):
        path = STATE_DIR / f"{rec.agent_id}.json"
        path.write_text(json.dumps(asdict(rec), indent=2, default=str))


# Module-level singleton
_state = PlatformState()


def state() -> PlatformState:
    return _state


def require_approval(description: str):
    """Decorator that gates a function behind human approval."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            agent_id = f"gate_{fn.__name__}_{int(time.time())}"
            _state.spawn(agent_id, "human_gate", description)
            _state.complete(agent_id, f"Approval needed: {description}", severity="action_required")
            # In real operation, this would block until human decides via dashboard.
            # For now, we record the gate and return the agent_id for async resolution.
            return agent_id
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator

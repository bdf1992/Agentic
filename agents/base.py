"""
Base agent — defines the contract every agent type must follow.

An agent:
1. Has a name and a set of event types it responds to
2. Receives an event (or manual trigger)
3. Does work (runs code, spawns Claude Code CLI, queries vector store)
4. Returns a Finding (result + severity + optional data)
5. Dies. Agents are ephemeral. State lives in PlatformState.

Agents can spawn Claude Code as a subprocess for tasks that need
LLM reasoning, file reading, code search, etc.
"""

from __future__ import annotations

import subprocess
import json
import time
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.state import state, AgentStatus
from core.event_queue import Event


@dataclass
class Finding:
    """What an agent produces."""
    summary: str
    severity: str = "info"  # info | warning | action_required
    data: dict = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


class Agent(ABC):
    """Base class for all platform agents."""

    name: str = "unnamed"
    triggers: list[str] = []  # event types this agent responds to

    def __init__(self):
        self._state = state()
        self._agent_id = f"{self.name}_{int(time.time() * 1000)}"

    @abstractmethod
    def run(self, event: Optional[Event] = None) -> Finding:
        """Execute the agent's task. Must return a Finding."""
        ...

    def execute(self, event: Optional[Event] = None) -> Finding:
        """Full lifecycle: register, run, report."""
        trigger = event.id if event else "manual"
        self._state.spawn(self._agent_id, self.name, trigger)

        try:
            finding = self.run(event)
            self._state.complete(self._agent_id, finding.summary, finding.severity)
            return finding
        except Exception as e:
            self._state.fail(self._agent_id, str(e))
            return Finding(summary=f"FAILED: {e}", severity="warning")

    def matches(self, event: Event) -> bool:
        """Does this agent want to handle this event?"""
        for trigger in self.triggers:
            if ":" in trigger:
                # Pattern like "file_changed:system3/primitives.py"
                t_type, t_pattern = trigger.split(":", 1)
                if event.type == t_type and t_pattern in json.dumps(event.payload):
                    return True
            elif event.type == trigger:
                return True
        return False

    # -----------------------------------------------------------------------
    # Tools available to all agents
    # -----------------------------------------------------------------------

    def claude(self, prompt: str, cwd: Optional[str] = None,
               allowed_tools: Optional[list[str]] = None) -> str:
        """
        Spawn a Claude Code CLI subprocess.

        This is how agents get LLM reasoning, code search, file reading, etc.
        The agent stays in control — Claude Code is the tool, not the boss.
        """
        cmd = ["claude", "--print", "--prompt", prompt]
        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(ROOT),
            timeout=300,
            shell=True,
        )
        return result.stdout.strip()

    def run_command(self, cmd: str, cwd: Optional[str] = None,
                    timeout: int = 120) -> tuple[str, int]:
        """Run a shell command and return (output, returncode)."""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(ROOT),
            timeout=timeout,
            shell=True,
        )
        output = result.stdout + result.stderr
        return output.strip(), result.returncode

    def finding(self, summary: str, severity: str = "info", **data) -> Finding:
        """Convenience: create a Finding."""
        return Finding(summary=summary, severity=severity, data=data)

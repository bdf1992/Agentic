"""
Synthesis Agent — cross-repo awareness and pattern surfacing.

This agent looks *across* repos and sessions for:
- Convergent patterns (two repos solving the same problem differently)
- Structural echoes (a shape in system3 math appearing in RiftEngine code)
- Stale connections (a reference in one repo to something that changed in another)
- Opportunity signals (resolved conjecture whose implications haven't propagated)

The synthesis agent is the platform's pattern-matching layer.
It doesn't act — it surfaces.
"""

from __future__ import annotations

from typing import Optional

from agents.base import Agent, Finding
from core.event_queue import Event
from core.vector_store import VectorStore


class SynthesisAgent(Agent):
    name = "synthesis"
    triggers = ["conjecture_resolved", "experiment_completed", "timer_daily"]

    def __init__(self):
        super().__init__()
        self.store = VectorStore("synthesis")

    def run(self, event: Optional[Event] = None) -> Finding:
        """
        Look for cross-cutting patterns.

        Strategy depends on trigger:
        - conjecture_resolved: check what else this affects
        - experiment_completed: compare with prior experiments
        - timer_daily: broad sweep for stale connections
        """
        if event and event.type == "conjecture_resolved":
            return self._propagation_check(event)
        elif event and event.type == "experiment_completed":
            return self._experiment_echo(event)
        else:
            return self._daily_sweep()

    def _propagation_check(self, event: Event) -> Finding:
        """A conjecture was resolved — what else should change?"""
        conjecture = event.payload.get("conjecture", "unknown")
        status = event.payload.get("status", "unknown")

        # Use Claude Code to search for references to this conjecture
        prompt = f"""Search across system3 for references to conjecture {conjecture}.
Check: KERNEL.md, MEMORY.md, any files in conjectures/, docs/, research/.
List every file that mentions it and whether it needs updating given
the conjecture is now {status}. Be concise — just file paths and what needs changing."""

        output = self.claude(
            prompt,
            cwd="C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3",
            allowed_tools=["Grep", "Read"],
        )

        needs_action = "needs updating" in output.lower() or "should change" in output.lower()
        return self.finding(
            f"Propagation check for {conjecture}: {'updates needed' if needs_action else 'clean'}",
            severity="action_required" if needs_action else "info",
            data={"analysis": output},
        )

    def _experiment_echo(self, event: Event) -> Finding:
        """An experiment completed — does it rhyme with anything?"""
        run_id = event.payload.get("run_id", "unknown")
        summary = event.payload.get("summary", "")

        # Search vector store for similar past findings
        # (requires embeddings — stub for now)
        return self.finding(
            f"Experiment {run_id} completed. Echo analysis pending embeddings.",
            data={"summary": summary},
        )

    def _daily_sweep(self) -> Finding:
        """Broad sweep for stale connections across repos."""
        prompt = """Quickly check:
1. Are there any conjectures in conjectures/ that reference resolved conjectures without updates?
2. Are there any imports of primitives.py constants that don't match current values?
3. Are there files in research/ older than 2 weeks that reference active conjectures?

Be very concise. Just list issues found, or say 'clean' if none."""

        output = self.claude(
            prompt,
            cwd="C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3",
            allowed_tools=["Grep", "Read", "Glob"],
        )

        has_issues = "clean" not in output.lower()
        return self.finding(
            f"Daily sweep: {'issues found' if has_issues else 'clean'}",
            severity="warning" if has_issues else "info",
            data={"analysis": output},
        )

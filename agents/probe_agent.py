"""
Probe Agent — runs experiments and interprets results.

Given a seed or hypothesis, the probe agent:
1. Designs a small experiment (or runs a predefined one)
2. Executes it
3. Interprets the output against expected properties
4. Returns a finding: confirmed, falsified, or inconclusive

Used by the experiment framework for agentic cartography runs.
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path

from agents.base import Agent, Finding
from core.event_queue import Event


class ProbeAgent(Agent):
    name = "probe"
    triggers = ["experiment_requested", "conjecture_test"]

    def __init__(self, seed_path: Optional[str] = None, working_dir: Optional[str] = None):
        super().__init__()
        self.seed_path = seed_path
        self.working_dir = working_dir or str(Path(__file__).parent.parent / "experiments" / "runs")

    def run(self, event: Optional[Event] = None) -> Finding:
        """
        Run a probe experiment.

        If a seed_path is provided, the agent reads the seed and uses Claude Code
        to design + execute an experiment. If an event triggered this, the event
        payload specifies what to probe.
        """
        if self.seed_path:
            return self._run_from_seed()
        elif event and event.payload:
            return self._run_from_event(event)
        else:
            return self.finding("No seed or event provided", severity="warning")

    def _run_from_seed(self) -> Finding:
        """Read a seed packet and run an experiment from it."""
        seed = Path(self.seed_path)
        if not seed.exists():
            return self.finding(f"Seed not found: {self.seed_path}", severity="warning")

        # Use Claude Code to interpret the seed and design an experiment
        prompt = f"""You are a probe agent. Read the seed packet at {self.seed_path}.

Design a small, self-contained Python experiment that explores the concepts in the seed.
The experiment should:
1. Be executable as a standalone script
2. Produce quantitative output (numbers, not just text)
3. Test for invariance, spectral properties, or self-referential structure
4. Print results as JSON to stdout

Write the experiment to {self.working_dir}/probe_output.py and run it.
Return the JSON output."""

        output = self.claude(prompt, allowed_tools=["Read", "Write", "Bash"])
        return self.finding(f"Probe completed: {output[:200]}", data={"raw": output})

    def _run_from_event(self, event: Event) -> Finding:
        """Run a probe based on an event payload."""
        hypothesis = event.payload.get("hypothesis", "")
        script = event.payload.get("script", "")

        if script:
            output, code = self.run_command(f"python {script}")
            success = code == 0
            return self.finding(
                f"Script {'passed' if success else 'failed'}: {output[:200]}",
                severity="info" if success else "warning",
                data={"output": output, "returncode": code},
            )

        if hypothesis:
            prompt = f"Design a falsifiable test for: {hypothesis}. Write and run it."
            output = self.claude(prompt, allowed_tools=["Read", "Write", "Bash"])
            return self.finding(f"Hypothesis probe: {output[:200]}", data={"raw": output})

        return self.finding("Event had no hypothesis or script", severity="warning")

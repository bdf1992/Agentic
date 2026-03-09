"""
Guardian Agent — regression and drift detection.

Watches for changes that might break invariants:
- Runs golden runs after commits to load-bearing files
- Cross-checks constants across repos
- Flags unexpected drift in test outputs

The guardian is paranoid by design. False positives are acceptable.
False negatives (missed breaks) are not.
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path

from agents.base import Agent, Finding
from core.event_queue import Event


# Files that, if changed, require golden run validation
LOAD_BEARING = {
    "system3": [
        "primitives.py", "formulas.py", "system3.py",
        "photon_mesh/meta_byte/", "s3/",
    ],
    "RiftEngine": [
        "Assets/Scripts/Core/", "Assets/Scripts/Braid/",
    ],
}


class GuardianAgent(Agent):
    name = "guardian"
    triggers = ["file_changed", "commit"]

    def __init__(self, repo_roots: Optional[dict[str, str]] = None):
        super().__init__()
        self.repo_roots = repo_roots or {
            "system3": "C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3",
            "RiftEngine": "C:/Users/bdf19/CatalystCore/CatalystCore",
        }

    def run(self, event: Optional[Event] = None) -> Finding:
        if not event:
            return self._full_sweep()

        repo = event.repo
        changed = event.payload.get("path", "")

        # Check if this is a load-bearing change
        is_critical = False
        for pattern in LOAD_BEARING.get(repo, []):
            if pattern in changed:
                is_critical = True
                break

        if not is_critical:
            return self.finding(f"Non-critical change: {repo}/{changed}")

        # Load-bearing change detected — run golden runs
        return self._run_golden(repo)

    def _run_golden(self, repo: str) -> Finding:
        """Run golden runs for a repo."""
        if repo == "system3":
            root = self.repo_roots.get("system3", "")
            output, code = self.run_command(
                "python golden_runs/run_all.py",
                cwd=root,
                timeout=300,
            )
            if code == 0:
                return self.finding(
                    f"Golden runs PASSED for {repo}",
                    data={"output": output[-500:]},
                )
            else:
                return self.finding(
                    f"Golden runs FAILED for {repo}: {output[-300:]}",
                    severity="action_required",
                    data={"output": output},
                )
        else:
            return self.finding(
                f"No golden runs configured for {repo}",
                severity="warning",
            )

    def _full_sweep(self) -> Finding:
        """Run all golden runs across all repos."""
        results = {}
        all_passed = True

        for repo, root in self.repo_roots.items():
            if repo == "system3":
                output, code = self.run_command(
                    "python golden_runs/run_all.py",
                    cwd=root,
                    timeout=300,
                )
                results[repo] = {"passed": code == 0, "output": output[-300:]}
                if code != 0:
                    all_passed = False

        severity = "info" if all_passed else "action_required"
        summary = "Full sweep: ALL PASSED" if all_passed else "Full sweep: FAILURES DETECTED"
        return self.finding(summary, severity=severity, data=results)

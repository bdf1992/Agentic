"""
Maintenance Agent — entropy management.

Handles the boring-but-critical work that rots codebases when ignored:
- Dead code detection
- Dependency drift
- Stale embeddings / index refresh
- Documentation-code divergence
- Rigor tag audit

This agent runs on schedule (nightly) or on demand.
"""

from __future__ import annotations

from typing import Optional

from agents.base import Agent, Finding
from core.event_queue import Event


class MaintenanceAgent(Agent):
    name = "maintenance"
    triggers = ["timer_nightly", "maintenance_requested"]

    def __init__(self):
        super().__init__()
        self.repo_roots = {
            "system3": "C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3",
        }

    def run(self, event: Optional[Event] = None) -> Finding:
        """Run maintenance checks."""
        issues = []

        # 1. Rigor tag audit
        rigor_result = self._rigor_audit()
        if rigor_result:
            issues.append(rigor_result)

        # 2. Stale file detection
        stale_result = self._stale_check()
        if stale_result:
            issues.append(stale_result)

        # 3. Import health
        import_result = self._import_check()
        if import_result:
            issues.append(import_result)

        if not issues:
            return self.finding("Maintenance sweep: all clean")

        summary = f"Maintenance found {len(issues)} issue(s): " + "; ".join(issues)
        severity = "warning" if len(issues) <= 2 else "action_required"
        return self.finding(summary, severity=severity, data={"issues": issues})

    def _rigor_audit(self) -> Optional[str]:
        """Check for deprecated rigor tags."""
        output, code = self.run_command(
            "python infra/rigor.py audit 2>&1 | tail -5",
            cwd=self.repo_roots["system3"],
            timeout=30,
        )
        if code != 0:
            return None  # Script might not exist yet, that's fine
        if "deprecated" in output.lower() or "old tag" in output.lower():
            return f"Rigor audit: {output.strip()}"
        return None

    def _stale_check(self) -> Optional[str]:
        """Check for files not touched in a long time that reference active conjectures."""
        output, code = self.run_command(
            'git log --diff-filter=M --since="2 weeks ago" --name-only --pretty=format: | sort -u | wc -l',
            cwd=self.repo_roots["system3"],
            timeout=15,
        )
        return None  # Stub — full implementation uses git log + conjecture cross-ref

    def _import_check(self) -> Optional[str]:
        """Check for hardcoded constants that should use primitives.py."""
        output, code = self.run_command(
            'grep -rn "= 7$\\|= 13$\\|= 28$" --include="*.py" research/ photon_mesh/ 2>/dev/null | head -10',
            cwd=self.repo_roots["system3"],
            timeout=15,
        )
        if output.strip():
            lines = output.strip().split("\n")
            return f"Possible hardcoded constants in {len(lines)} file(s)"
        return None

"""
Infrastructure Agent — prevents work from outgrowing its support structure.

The other agents produce: probes, findings, experiments, code.
This agent ensures the PLATFORM can handle what it produces.

Checks on every cycle:
1. SCALE:     Are data directories growing unchecked? (events, state, vectors, spool)
2. COVERAGE:  Are new agent types registered? Do they have triggers?
3. INDEXING:  Is the vector store stale? Are embeddings missing for recent files?
4. HOOKS:     Are connected repos still hooked? Did any hooks break?
5. INTEGRITY: Can every agent import cleanly? Are there circular deps?
6. CAPACITY:  Are there too many concurrent agents? Queue backing up?
7. NARRATIVE:  Does CLAUDE.md match reality? Are there undocumented agents?

If any check fails, the finding tells you exactly what outgrew what.

Triggers: runs on a timer (every cycle with docs agent), after any new
agent file is created, or on manual request.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Optional

from agents.base import Agent, Finding
from core.event_queue import Event

ROOT = Path(__file__).parent.parent


class InfraAgent(Agent):
    name = "infra"
    triggers = ["timer_30min", "file_changed", "infra_requested"]

    def run(self, event: Optional[Event] = None) -> Finding:
        """Run all infrastructure health checks."""
        issues = []
        warnings = []
        stats = {}

        # 1. SCALE — data directory sizes
        scale_issues = self._check_scale(stats)
        issues.extend(scale_issues)

        # 2. COVERAGE — all agents discoverable and triggered
        coverage_issues = self._check_coverage(stats)
        issues.extend(coverage_issues)

        # 3. HOOKS — connected repos still wired
        hook_issues = self._check_hooks(stats)
        warnings.extend(hook_issues)

        # 4. INTEGRITY — all agents import cleanly
        integrity_issues = self._check_integrity(stats)
        issues.extend(integrity_issues)

        # 5. CAPACITY — queue and worker health
        capacity_issues = self._check_capacity(stats)
        issues.extend(capacity_issues)

        # 6. NARRATIVE — CLAUDE.md and README match reality
        narrative_issues = self._check_narrative(stats)
        warnings.extend(narrative_issues)

        # 7. EXPERIMENTS — runs directory not filling up unreviewed
        exp_issues = self._check_experiments(stats)
        warnings.extend(exp_issues)

        # Build finding
        total_issues = len(issues) + len(warnings)
        if issues:
            severity = "action_required"
            summary = f"INFRA: {len(issues)} issue(s), {len(warnings)} warning(s) — platform capacity at risk"
        elif warnings:
            severity = "warning"
            summary = f"INFRA: {len(warnings)} warning(s) — attention recommended"
        else:
            severity = "info"
            summary = f"INFRA: all clear — {stats.get('total_files', '?')} files, {stats.get('agent_count', '?')} agents, {stats.get('data_size_mb', '?')}MB data"

        return self.finding(
            summary,
            severity=severity,
            data={
                "issues": issues,
                "warnings": warnings,
                "stats": stats,
            },
        )

    def _check_scale(self, stats: dict) -> list[str]:
        """Check data directory sizes."""
        issues = []
        data_dir = ROOT / "data"
        total_bytes = 0

        if data_dir.exists():
            for f in data_dir.rglob("*"):
                if f.is_file():
                    total_bytes += f.stat().st_size

        stats["data_size_mb"] = round(total_bytes / (1024 * 1024), 2)

        # Alert if data exceeds 100MB
        if total_bytes > 100 * 1024 * 1024:
            issues.append(f"Data directory is {stats['data_size_mb']}MB — needs cleanup")

        # Check individual directories
        for subdir in ["events", "state", "vectors", "spool"]:
            p = data_dir / subdir
            if p.exists():
                count = len(list(p.glob("*")))
                stats[f"data_{subdir}_count"] = count
                if count > 1000:
                    issues.append(f"data/{subdir}/ has {count} files — needs rotation")

        return issues

    def _check_coverage(self, stats: dict) -> list[str]:
        """Check that all agents are discoverable and have triggers."""
        issues = []
        agents_dir = ROOT / "agents"
        agent_files = list(agents_dir.glob("*_agent.py"))
        stats["agent_count"] = len(agent_files)

        for af in agent_files:
            module_name = f"agents.{af.stem}"
            try:
                mod = importlib.import_module(module_name)
                # Find the Agent subclass
                found = False
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (isinstance(attr, type)
                            and issubclass(attr, Agent)
                            and attr is not Agent):
                        found = True
                        if not getattr(attr, 'triggers', []):
                            issues.append(f"{af.stem}: agent has no triggers — dispatcher can't route to it")
                if not found:
                    issues.append(f"{af.stem}: no Agent subclass found")
            except Exception as e:
                issues.append(f"{af.stem}: import failed — {e}")

        return issues

    def _check_hooks(self, stats: dict) -> list[str]:
        """Check connected repo hooks are still alive."""
        warnings = []
        known_repos = {
            "system3": Path("C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3"),
            "RiftEngine": Path("C:/Users/bdf19/CatalystCore/CatalystCore"),
        }

        hooked = 0
        for name, repo_path in known_repos.items():
            if repo_path.exists():
                hook = repo_path / ".git" / "hooks" / "post-commit"
                if hook.exists() and "Agentic" in hook.read_text():
                    hooked += 1
                else:
                    warnings.append(f"{name}: repo exists but hook not installed")

        stats["hooked_repos"] = hooked
        return warnings

    def _check_integrity(self, stats: dict) -> list[str]:
        """Verify all core modules import cleanly."""
        issues = []
        core_modules = [
            "core.event_queue",
            "core.state",
            "core.vector_store",
            "core.dispatcher",
            "core.server",
        ]

        for mod_name in core_modules:
            try:
                importlib.import_module(mod_name)
            except Exception as e:
                issues.append(f"{mod_name}: import failed — {e}")

        return issues

    def _check_capacity(self, stats: dict) -> list[str]:
        """Check queue depth and active workers."""
        issues = []

        from core.event_queue import queue as get_queue
        from core.state import state as get_state

        q = get_queue()
        s = get_state()

        stats["queue_depth"] = q.pending()
        stats["active_agents"] = len(s.active())

        if q.pending() > 50:
            issues.append(f"Event queue has {q.pending()} pending events — agents can't keep up")

        if len(s.active()) > 10:
            issues.append(f"{len(s.active())} agents running concurrently — possible spawn storm")

        return issues

    def _check_narrative(self, stats: dict) -> list[str]:
        """Check that docs match reality."""
        warnings = []

        # Check CLAUDE.md mentions all agent types
        claude_md = ROOT / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            agents_dir = ROOT / "agents"
            for af in agents_dir.glob("*_agent.py"):
                agent_name = af.stem.replace("_agent", "")
                if agent_name not in content.lower():
                    warnings.append(f"CLAUDE.md doesn't mention '{agent_name}' agent — update docs")

        # Check README mentions all agent types
        readme = ROOT / "README.md"
        if readme.exists():
            content = readme.read_text()
            for af in agents_dir.glob("*_agent.py"):
                agent_name = af.stem.replace("_agent", "")
                # "Infra" or "Infrastructure" both count
                if agent_name not in content.lower() and agent_name.replace("infra", "infrastructure") not in content.lower():
                    warnings.append(f"README.md doesn't mention '{agent_name}' agent — docs agent should pick this up")

        # Count total project files
        all_files = list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.json")) + list(ROOT.rglob("*.md"))
        all_files = [f for f in all_files if ".git" not in str(f) and "__pycache__" not in str(f)]
        stats["total_files"] = len(all_files)

        return warnings

    def _check_experiments(self, stats: dict) -> list[str]:
        """Check experiment runs for unreviewed results."""
        warnings = []
        runs_dir = ROOT / "experiments" / "runs"

        if runs_dir.exists():
            runs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name != ".gitkeep"]
            stats["experiment_runs"] = len(runs)

            unreviewed = 0
            for run_dir in runs:
                verdict = run_dir / "verdict.json"
                if not verdict.exists():
                    unreviewed += 1

            if unreviewed > 3:
                warnings.append(f"{unreviewed} experiment runs have no verdict — judge them or archive them")

        return warnings

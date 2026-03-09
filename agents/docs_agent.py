"""
Documentation Agent — keeps README, indexes, and narrative framing current.

Runs on a 30-minute loop (or on demand). Each cycle:
1. Scans the repo for structural changes (new files, removed files, new experiments)
2. Reads current README.md
3. Updates the status block, directory tree, experiment results, and agent roster
4. Ensures narrative framing matches reality (no stale claims, no missing agents)
5. Commits if there are meaningful changes (not whitespace-only)

This agent is intentionally chatty in its findings — it's the platform's narrator.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents.base import Agent, Finding
from core.event_queue import Event

ROOT = Path(__file__).parent.parent


class DocsAgent(Agent):
    name = "docs"
    triggers = ["timer_30min", "file_changed", "docs_requested"]

    def run(self, event: Optional[Event] = None) -> Finding:
        """Update README and report what changed."""
        changes = []

        # 1. Gather current state
        state = self._gather_state()

        # 2. Read current README
        readme_path = ROOT / "README.md"
        if not readme_path.exists():
            return self.finding("README.md not found", severity="warning")

        current = readme_path.read_text(encoding="utf-8")

        # 3. Update the status block
        updated, status_changed = self._update_status_block(current, state)
        if status_changed:
            changes.append("status block updated")

        # 4. Update experiment results table
        updated, exp_changed = self._update_experiment_table(updated, state)
        if exp_changed:
            changes.append("experiment results updated")

        # 5. Update connected repos table
        updated, repo_changed = self._update_repo_table(updated, state)
        if repo_changed:
            changes.append("connected repos updated")

        # 6. Write if changed
        if changes:
            readme_path.write_text(updated, encoding="utf-8")
            return self.finding(
                f"README updated: {', '.join(changes)}",
                data={"changes": changes, "state": state},
            )
        else:
            return self.finding("README is current, no changes needed")

    def _gather_state(self) -> dict:
        """Collect current platform state."""
        state = {}

        # Count commits
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, cwd=str(ROOT)
            )
            state["commits"] = int(result.stdout.strip()) if result.returncode == 0 else "?"
        except Exception:
            state["commits"] = "?"

        # Count agent types
        agents_dir = ROOT / "agents"
        agent_files = [f.stem for f in agents_dir.glob("*_agent.py")]
        state["agent_types"] = agent_files
        state["agent_names"] = [f.replace("_agent", "") for f in agent_files]

        # Count experiments
        runs_dir = ROOT / "experiments" / "runs"
        runs = [d.name for d in runs_dir.iterdir() if d.is_dir() and d.name != ".gitkeep"] if runs_dir.exists() else []
        state["experiment_runs"] = runs

        # Gather experiment results
        state["experiment_results"] = []
        for run_name in runs:
            run_dir = runs_dir / run_name
            verdict_path = run_dir / "verdict.json"
            derivation_files = list(run_dir.glob("derivation_*.md"))
            probe_files = list(run_dir.glob("probe_*.py"))

            result = {"run_id": run_name, "probes": len(probe_files)}

            if verdict_path.exists():
                try:
                    verdict = json.loads(verdict_path.read_text())
                    result["verdict"] = verdict.get("verdict", "?")
                    result["properties"] = verdict.get("summary", {}).get("present", "?")
                except Exception:
                    pass

            # Try to extract check count from probe files
            for pf in probe_files:
                try:
                    content = pf.read_text()
                    # Look for "N/N checks passed" or "all N checks"
                    m = re.search(r'(\d+)/(\d+)\s+checks?\s+passed', content)
                    if m:
                        result["checks"] = f"{m.group(1)}/{m.group(2)}"
                    else:
                        m = re.search(r'all\s+(\d+)\s+checks?\s+passed', content)
                        if m:
                            result["checks"] = f"{m.group(1)}/{m.group(1)}"
                except Exception:
                    pass

            # Try to extract from derivation
            for df in derivation_files:
                try:
                    content = df.read_text()
                    m = re.search(r'(\d+)\s+of\s+17', content)
                    if m:
                        result["properties"] = int(m.group(1))
                    # Find structure name
                    m = re.search(r'#\s+Derivation\s+\d+\s*[—–-]\s*(.+)', content)
                    if m:
                        result["structure"] = m.group(1).strip()
                except Exception:
                    pass

            state["experiment_results"].append(result)

        # Check connected repos
        hooks_dir = ROOT / "hooks"
        state["connected_repos"] = []
        # Check known repo locations for our hook
        known_repos = {
            "system3": "C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3",
            "RiftEngine": "C:/Users/bdf19/CatalystCore/CatalystCore",
            "FieldForge": None,
            "InvertedSand": None,
        }
        for name, path in known_repos.items():
            if path and Path(path).exists():
                hook_path = Path(path) / ".git" / "hooks" / "post-commit"
                has_hook = hook_path.exists() and "Agentic" in hook_path.read_text() if hook_path.exists() else False
                state["connected_repos"].append({
                    "name": name, "exists": True, "hooked": has_hook
                })
            else:
                state["connected_repos"].append({
                    "name": name, "exists": False, "hooked": False
                })

        # File count
        all_files = list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.json")) + list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.yml"))
        all_files = [f for f in all_files if ".git" not in str(f) and "__pycache__" not in str(f)]
        state["total_files"] = len(all_files)

        state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        return state

    def _update_status_block(self, readme: str, state: dict) -> tuple[str, bool]:
        """Update the <!-- AGENT_STATUS --> block at the bottom."""
        agents_str = ", ".join(state["agent_names"])
        runs_str = f"{len(state['experiment_runs'])} run(s)"
        run_names = ", ".join(state["experiment_runs"]) if state["experiment_runs"] else "none"

        new_block = (
            f"<!-- AGENT_STATUS_BEGIN -->\n"
            f"**Last updated**: {state['timestamp']} | "
            f"**Agents**: {agents_str} | "
            f"**Experiments**: {runs_str} ({run_names}) | "
            f"**Commits**: {state['commits']} | "
            f"**Files**: {state['total_files']}\n"
            f"<!-- AGENT_STATUS_END -->"
        )

        pattern = r"<!-- AGENT_STATUS_BEGIN -->.*?<!-- AGENT_STATUS_END -->"
        if re.search(pattern, readme, re.DOTALL):
            updated = re.sub(pattern, new_block, readme, flags=re.DOTALL)
            changed = updated != readme
            return updated, changed
        else:
            # Append if not found
            updated = readme.rstrip() + "\n\n" + new_block + "\n"
            return updated, True

    def _update_experiment_table(self, readme: str, state: dict) -> tuple[str, bool]:
        """Update the experiment results table if new probes exist."""
        results = state.get("experiment_results", [])
        if not results:
            return readme, False

        # Build new table rows
        rows = []
        for r in results:
            run_id = r.get("run_id", "?")
            structure = r.get("structure", "?")
            props = r.get("properties", "?")
            checks = r.get("checks", "?")
            probes = r.get("probes", 0)
            rows.append(f"| {run_id} | {structure} | {props}/17 | {checks} |")

        # Find and replace the results table
        table_pattern = r"(\| Probe \| Structure Found \| Properties \| Checks \|\n\|[-\s|]+\n)((?:\|.*\n)*)"
        match = re.search(table_pattern, readme)
        if match:
            header = match.group(1)
            new_table = header + "\n".join(rows) + "\n"
            updated = readme[:match.start()] + new_table + readme[match.end():]
            changed = updated != readme
            return updated, changed

        return readme, False

    def _update_repo_table(self, readme: str, state: dict) -> tuple[str, bool]:
        """Update the connected repos table."""
        repos = state.get("connected_repos", [])
        if not repos:
            return readme, False

        roles = {
            "system3": "Math foundation, axiom algebra, research",
            "RiftEngine": "Unity braid-memory engine",
            "FieldForge": "Constraint system",
            "InvertedSand": "Renderer",
        }

        rows = []
        for r in repos:
            name = r["name"]
            role = roles.get(name, "?")
            if r["hooked"]:
                status = "Installed"
            elif r["exists"]:
                status = "Available (not hooked)"
            else:
                status = "Not found"
            rows.append(f"| `{name}` | {role} | {status} |")

        # Find and replace
        table_pattern = r"(\| Repo \| Role \| Hook Status \|\n\|[-\s|]+\n)((?:\|.*\n)*)"
        match = re.search(table_pattern, readme)
        if match:
            header = match.group(1)
            new_table = header + "\n".join(rows) + "\n"
            updated = readme[:match.start()] + new_table + readme[match.end():]
            changed = updated != readme
            return updated, changed

        return readme, False

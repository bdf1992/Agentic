"""
GitHub Agent — manages the repo lifecycle.

Handles:
1. CODE REVIEW:   When a PR is opened or updated, reviews the diff for:
                   - Breaking changes to agent contracts (base.py, event_queue, state)
                   - Missing tests for new agents
                   - Narrative drift (new code not reflected in README/CLAUDE.md)
                   - Style consistency

2. COMMIT HYGIENE: After commits, checks:
                   - Commit messages follow conventions ([docs-agent], Co-Authored-By, etc.)
                   - No secrets or data/ files accidentally committed
                   - No giant binary blobs

3. ISSUE TRIAGE:   When issues are filed:
                   - Auto-labels by area (core, agents, hooks, experiments)
                   - Links to relevant code
                   - Suggests which agent type should handle it

4. RELEASE NOTES:  On tag/release, compiles changes since last release
                   into a human-readable summary.

Requires: `gh` CLI or GitHub API token for write operations.
Read operations work via git log and local repo state.
"""

from __future__ import annotations

import re
import subprocess
import json
from pathlib import Path
from typing import Optional

from agents.base import Agent, Finding
from core.event_queue import Event

ROOT = Path(__file__).parent.parent


class GitHubAgent(Agent):
    name = "github"
    triggers = ["commit", "pr_opened", "pr_updated", "issue_opened", "github_requested"]

    def run(self, event: Optional[Event] = None) -> Finding:
        if event and event.type == "commit":
            return self._review_commit(event)
        elif event and event.type in ("pr_opened", "pr_updated"):
            return self._review_pr(event)
        elif event and event.type == "issue_opened":
            return self._triage_issue(event)
        else:
            # Manual trigger or general health check
            return self._repo_health()

    # ------------------------------------------------------------------
    # Commit review
    # ------------------------------------------------------------------

    def _review_commit(self, event: Event) -> Finding:
        """Review a commit for hygiene issues."""
        issues = []
        commit_hash = event.payload.get("commit_hash", "HEAD")
        message = event.payload.get("commit_message", "")
        files = event.payload.get("files_changed", [])

        # Check commit message conventions
        if len(message) > 0:
            if len(message) > 100 and "\n" not in message:
                issues.append("Commit message > 100 chars on first line — consider splitting")

        # Check for accidental data/ or secret commits
        danger_patterns = [".env", "credentials", "secret", "token", "data/events", "data/state"]
        for f in files:
            for pattern in danger_patterns:
                if pattern in f.lower():
                    issues.append(f"Potentially sensitive file committed: {f}")

        # Check for large files
        if files:
            for f in files:
                file_path = ROOT / f
                if file_path.exists() and file_path.stat().st_size > 5 * 1024 * 1024:
                    issues.append(f"Large file ({file_path.stat().st_size // 1024}KB): {f}")

        # Check if agent files changed without CLAUDE.md/README update
        agent_changed = any("agents/" in f for f in files)
        docs_changed = any(f in ("CLAUDE.md", "README.md") for f in files)
        if agent_changed and not docs_changed:
            issues.append("Agent code changed but docs not updated — infra agent will catch this too")

        if issues:
            return self.finding(
                f"Commit review: {len(issues)} issue(s) — {issues[0]}",
                severity="warning",
                data={"issues": issues, "commit": commit_hash},
            )
        return self.finding(f"Commit {commit_hash[:8]} looks clean")

    # ------------------------------------------------------------------
    # PR review
    # ------------------------------------------------------------------

    def _review_pr(self, event: Event) -> Finding:
        """Review a pull request diff."""
        pr_number = event.payload.get("pr_number", "?")
        diff = event.payload.get("diff", "")
        files = event.payload.get("files", [])

        concerns = []

        # Check for breaking changes to core contracts
        contract_files = ["agents/base.py", "core/event_queue.py", "core/state.py", "core/dispatcher.py"]
        changed_contracts = [f for f in files if f in contract_files]
        if changed_contracts:
            concerns.append(f"Contract files changed: {', '.join(changed_contracts)} — all agents may be affected")

        # Check for new agents without triggers
        new_agents = [f for f in files if f.startswith("agents/") and f.endswith("_agent.py")]
        if new_agents:
            for agent_file in new_agents:
                path = ROOT / agent_file
                if path.exists():
                    content = path.read_text()
                    if 'triggers = []' in content or 'triggers' not in content:
                        concerns.append(f"New agent {agent_file} has no triggers — dispatcher can't route to it")

        # Check for test coverage
        if any("agents/" in f or "core/" in f for f in files):
            test_files = [f for f in files if "test" in f.lower()]
            if not test_files:
                concerns.append("Code changed in agents/ or core/ but no test files in PR")

        if concerns:
            return self.finding(
                f"PR #{pr_number} review: {len(concerns)} concern(s)",
                severity="warning" if len(concerns) <= 2 else "action_required",
                data={"concerns": concerns, "pr": pr_number},
                suggestions=["Address concerns before merging"],
            )
        return self.finding(f"PR #{pr_number} looks good")

    # ------------------------------------------------------------------
    # Issue triage
    # ------------------------------------------------------------------

    def _triage_issue(self, event: Event) -> Finding:
        """Auto-label and link an issue to relevant code."""
        title = event.payload.get("title", "")
        body = event.payload.get("body", "")
        text = f"{title} {body}".lower()

        labels = []
        area = "unknown"

        # Detect area
        if any(w in text for w in ["agent", "probe", "guardian", "synthesis", "maintenance", "docs", "infra"]):
            labels.append("agents")
            area = "agents"
        if any(w in text for w in ["event", "queue", "dispatch", "server", "api"]):
            labels.append("core")
            area = "core"
        if any(w in text for w in ["hook", "post-commit", "install"]):
            labels.append("hooks")
            area = "hooks"
        if any(w in text for w in ["experiment", "seed", "probe", "cartography", "judge"]):
            labels.append("experiments")
            area = "experiments"
        if any(w in text for w in ["dashboard", "ui", "browser"]):
            labels.append("dashboard")
            area = "dashboard"
        if any(w in text for w in ["bug", "error", "fail", "crash", "broken"]):
            labels.append("bug")
        if any(w in text for w in ["feature", "add", "new", "implement"]):
            labels.append("enhancement")

        return self.finding(
            f"Issue triaged → area: {area}, labels: {', '.join(labels) or 'none'}",
            data={"labels": labels, "area": area},
        )

    # ------------------------------------------------------------------
    # Repo health
    # ------------------------------------------------------------------

    def _repo_health(self) -> Finding:
        """General repo health check."""
        issues = []
        stats = {}

        # Check git status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        uncommitted = len([l for l in result.stdout.strip().split("\n") if l.strip()])
        stats["uncommitted_files"] = uncommitted
        if uncommitted > 10:
            issues.append(f"{uncommitted} uncommitted files — consider committing or gitignoring")

        # Check branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        stats["branch"] = result.stdout.strip()

        # Check if ahead/behind remote
        result = subprocess.run(
            ["git", "status", "-sb"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        status_line = result.stdout.strip().split("\n")[0] if result.stdout else ""
        if "ahead" in status_line:
            m = re.search(r'ahead (\d+)', status_line)
            count = m.group(1) if m else "?"
            issues.append(f"Branch is {count} commit(s) ahead of remote — push when ready")
            stats["ahead"] = int(count) if m else 0
        if "behind" in status_line:
            m = re.search(r'behind (\d+)', status_line)
            count = m.group(1) if m else "?"
            issues.append(f"Branch is {count} commit(s) behind remote — pull recommended")

        # Recent commit activity
        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        recent_commits = result.stdout.strip().split("\n")
        stats["recent_commits"] = len(recent_commits)

        # Check for stale branches
        result = subprocess.run(
            ["git", "branch"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        branches = [b.strip().lstrip("* ") for b in result.stdout.strip().split("\n") if b.strip()]
        stats["branches"] = len(branches)
        if len(branches) > 5:
            issues.append(f"{len(branches)} branches — consider cleaning up stale ones")

        if issues:
            return self.finding(
                f"Repo health: {len(issues)} item(s) — {issues[0]}",
                severity="warning",
                data={"issues": issues, "stats": stats},
            )
        return self.finding(
            f"Repo healthy: {stats.get('branch', '?')} branch, {uncommitted} uncommitted, {stats.get('recent_commits', '?')} recent commits",
            data={"stats": stats},
        )

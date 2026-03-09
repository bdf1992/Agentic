"""
Post-commit hook — emits events to the Agentic platform.

Install this in any connected repo's .git/hooks/post-commit.
It detects what changed and POSTs an event to the platform server.

Can also be called directly:
    python post_commit.py --repo system3 --server http://localhost:8750
"""

from __future__ import annotations

import subprocess
import json
import sys
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


DEFAULT_SERVER = "http://localhost:8750"


def get_changed_files() -> list[str]:
    """Get files changed in the most recent commit."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def get_commit_info() -> dict:
    """Get info about the most recent commit."""
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%H|%s|%an"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {}
    parts = result.stdout.strip().split("|", 2)
    if len(parts) == 3:
        return {"hash": parts[0], "message": parts[1], "author": parts[2]}
    return {}


def detect_repo_name() -> str:
    """Infer the repo name from the git remote or directory name."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        url = result.stdout.strip()
        return url.split("/")[-1].replace(".git", "")

    # Fallback to directory name
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).name
    return "unknown"


def emit_event(repo: str, server: str = DEFAULT_SERVER):
    """Emit a commit event to the platform."""
    changed = get_changed_files()
    commit = get_commit_info()

    for path in changed:
        event = {
            "type": "file_changed",
            "repo": repo,
            "payload": {
                "path": path,
                "commit_hash": commit.get("hash", ""),
                "commit_message": commit.get("message", ""),
                "author": commit.get("author", ""),
            },
        }

        if HAS_REQUESTS:
            try:
                requests.post(f"{server}/events", json=event, timeout=5)
            except Exception:
                # Hook must never block the commit
                _fallback_write(event)
        else:
            _fallback_write(event)

    # Also emit a single commit-level event
    commit_event = {
        "type": "commit",
        "repo": repo,
        "payload": {
            **commit,
            "files_changed": changed,
            "file_count": len(changed),
        },
    }
    if HAS_REQUESTS:
        try:
            requests.post(f"{server}/events", json=commit_event, timeout=5)
        except Exception:
            _fallback_write(commit_event)
    else:
        _fallback_write(commit_event)


def _fallback_write(event: dict):
    """If the server is unreachable, write event to a spool directory."""
    spool = Path(__file__).parent.parent / "data" / "spool"
    spool.mkdir(parents=True, exist_ok=True)
    import time
    path = spool / f"{event['type']}_{int(time.time() * 1000)}.json"
    path.write_text(json.dumps(event, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Emit post-commit events")
    parser.add_argument("--repo", default=None, help="Repo name (auto-detected if omitted)")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Platform server URL")
    args = parser.parse_args()

    repo = args.repo or detect_repo_name()
    emit_event(repo, args.server)
    print(f"[agentic] Events emitted for {repo}")

"""
Documentation agent loop — runs the docs agent on a 30-minute interval.

Usage:
    python agents/run_docs_loop.py                # 30-min default
    python agents/run_docs_loop.py --interval 10  # every 10 minutes
    python agents/run_docs_loop.py --once          # single run, no loop

Each cycle:
1. Runs the DocsAgent to update README.md
2. If changes were made, auto-commits with a [docs-agent] prefix
3. Optionally pushes to remote

The agent commits autonomously (README updates only) but does NOT push
unless --push is specified. Human reviews the commit log and pushes when ready.
"""

from __future__ import annotations

import sys
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.docs_agent import DocsAgent


def run_cycle(auto_commit: bool = True, auto_push: bool = False) -> str:
    """Run one docs agent cycle. Returns the finding summary."""
    agent = DocsAgent()
    finding = agent.execute()

    print(f"[docs-agent] {finding.summary}")

    if "updated" in finding.summary and auto_commit:
        # Check if README actually changed in git
        result = subprocess.run(
            ["git", "diff", "--name-only", "README.md"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        if result.stdout.strip():
            subprocess.run(
                ["git", "add", "README.md"],
                cwd=str(ROOT)
            )
            subprocess.run(
                ["git", "commit", "-m", f"[docs-agent] {finding.summary}"],
                capture_output=True, text=True, cwd=str(ROOT)
            )
            print("[docs-agent] Committed README update")

            if auto_push:
                subprocess.run(
                    ["git", "push"],
                    capture_output=True, text=True, cwd=str(ROOT)
                )
                print("[docs-agent] Pushed to remote")

    return finding.summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Documentation agent loop")
    parser.add_argument("--interval", type=int, default=30, help="Minutes between cycles (default: 30)")
    parser.add_argument("--once", action="store_true", help="Run once, no loop")
    parser.add_argument("--push", action="store_true", help="Auto-push after commit")
    parser.add_argument("--no-commit", action="store_true", help="Don't auto-commit changes")
    args = parser.parse_args()

    auto_commit = not args.no_commit

    if args.once:
        run_cycle(auto_commit=auto_commit, auto_push=args.push)
        return

    print(f"[docs-agent] Starting loop — every {args.interval} minutes")
    print(f"[docs-agent] Auto-commit: {auto_commit} | Auto-push: {args.push}")
    print(f"[docs-agent] Press Ctrl+C to stop")

    while True:
        try:
            run_cycle(auto_commit=auto_commit, auto_push=args.push)
            print(f"[docs-agent] Next cycle in {args.interval} minutes...")
            time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            print("\n[docs-agent] Stopped")
            break


if __name__ == "__main__":
    main()

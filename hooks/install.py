"""
Hook installer — installs Agentic hooks into connected repos.

Usage:
    python hooks/install.py /path/to/repo
    python hooks/install.py /path/to/repo --server http://localhost:8750
"""

from __future__ import annotations

import sys
import stat
from pathlib import Path

HOOK_TEMPLATE = '''#!/bin/sh
# Agentic Platform post-commit hook
# Emits events to the platform server on every commit.
python "{hook_script}" --repo "{repo_name}" --server "{server}" &
'''


def install(repo_path: str, server: str = "http://localhost:8750"):
    """Install the post-commit hook into a repo."""
    repo = Path(repo_path).resolve()
    hooks_dir = repo / ".git" / "hooks"

    if not hooks_dir.exists():
        print(f"ERROR: {hooks_dir} does not exist. Is this a git repo?")
        sys.exit(1)

    hook_script = Path(__file__).parent / "post_commit.py"
    repo_name = repo.name

    hook_path = hooks_dir / "post-commit"

    # Don't overwrite — append if hook already exists
    if hook_path.exists():
        existing = hook_path.read_text()
        if "Agentic Platform" in existing:
            print(f"Hook already installed in {repo_name}")
            return
        # Append to existing hook
        with open(hook_path, "a") as f:
            f.write(f'\n# Agentic Platform addition\npython "{hook_script}" --repo "{repo_name}" --server "{server}" &\n')
        print(f"Appended Agentic hook to existing post-commit in {repo_name}")
    else:
        hook_path.write_text(HOOK_TEMPLATE.format(
            hook_script=str(hook_script).replace("\\", "/"),
            repo_name=repo_name,
            server=server,
        ))
        # Make executable
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
        print(f"Installed post-commit hook in {repo_name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Install Agentic hooks")
    parser.add_argument("repo", help="Path to the git repo")
    parser.add_argument("--server", default="http://localhost:8750")
    args = parser.parse_args()
    install(args.repo, args.server)

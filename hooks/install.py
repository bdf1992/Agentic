"""
Hook installer — installs Agentic hooks into connected repos.

Usage:
    python hooks/install.py                          # Install in all connected repos
    python hooks/install.py /path/to/repo            # Install in specific repo
    python hooks/install.py --list                   # Show hook status across repos
    python hooks/install.py --uninstall /path/to/repo  # Remove hook from repo
"""

from __future__ import annotations

import sys
import stat
from pathlib import Path

ROOT = Path(__file__).parent.parent

# All connected repos — keep in sync with core/server.py
CONNECTED_REPOS = {
    "system3": Path("C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3"),
    "CatalystCore": Path("C:/Users/bdf19/CatalystCore/CatalystCore"),
    "Agentic": ROOT,
}

HOOK_TEMPLATE = '''#!/bin/sh
# Agentic Platform post-commit hook
# Emits events to the platform server on every commit.
python "{hook_script}" --repo "{repo_name}" --server "{server}" &
'''


def install(repo_path: str, server: str = "http://localhost:8750") -> bool:
    """Install the post-commit hook into a repo. Returns True on success."""
    repo = Path(repo_path).resolve()
    hooks_dir = repo / ".git" / "hooks"

    if not hooks_dir.exists():
        print(f"  SKIP: {repo.name} — not a git repo ({hooks_dir} missing)")
        return False

    hook_script = Path(__file__).parent / "post_commit.py"
    repo_name = repo.name

    hook_path = hooks_dir / "post-commit"

    # Don't overwrite — append if hook already exists
    if hook_path.exists():
        existing = hook_path.read_text()
        if "Agentic Platform" in existing:
            print(f"  OK:   {repo_name} — hook already installed")
            return True
        # Append to existing hook
        with open(hook_path, "a") as f:
            f.write(
                f'\n# Agentic Platform addition\n'
                f'python "{hook_script}" --repo "{repo_name}" --server "{server}" &\n'
            )
        print(f"  ADD:  {repo_name} — appended to existing post-commit hook")
    else:
        hook_path.write_text(HOOK_TEMPLATE.format(
            hook_script=str(hook_script).replace("\\", "/"),
            repo_name=repo_name,
            server=server,
        ))
        # Make executable
        try:
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
        except OSError:
            pass  # Windows doesn't need this
        print(f"  NEW:  {repo_name} — installed post-commit hook")

    return True


def uninstall(repo_path: str) -> bool:
    """Remove the Agentic hook from a repo."""
    repo = Path(repo_path).resolve()
    hook_path = repo / ".git" / "hooks" / "post-commit"

    if not hook_path.exists():
        print(f"  SKIP: {repo.name} — no post-commit hook")
        return False

    text = hook_path.read_text()
    if "Agentic Platform" not in text:
        print(f"  SKIP: {repo.name} — hook exists but not ours")
        return False

    # If the entire hook is ours, remove the file
    lines = text.strip().splitlines()
    non_agentic = [l for l in lines if "Agentic" not in l and "agentic" not in l.lower()
                   and l.strip() != "#!/bin/sh" and l.strip()]
    if not non_agentic:
        hook_path.unlink()
        print(f"  DEL:  {repo.name} — removed post-commit hook")
    else:
        # Other hooks exist, just remove our lines
        new_lines = []
        skip_next = False
        for line in lines:
            if "Agentic Platform" in line:
                skip_next = True
                continue
            if skip_next and ("post_commit.py" in line or "agentic" in line.lower()):
                skip_next = False
                continue
            skip_next = False
            new_lines.append(line)
        hook_path.write_text("\n".join(new_lines) + "\n")
        print(f"  TRIM: {repo.name} — removed Agentic lines from post-commit hook")

    return True


def show_status():
    """Show hook installation status across all connected repos."""
    print("Hook status across connected repos:")
    print()
    for name, path in CONNECTED_REPOS.items():
        if not path.exists():
            print(f"  {name:20s}  NOT FOUND  ({path})")
            continue
        hook_path = path / ".git" / "hooks" / "post-commit"
        if not hook_path.exists():
            print(f"  {name:20s}  NO HOOK")
        elif "Agentic" in hook_path.read_text():
            print(f"  {name:20s}  INSTALLED")
        else:
            print(f"  {name:20s}  OTHER HOOK (not ours)")


def install_all(server: str = "http://localhost:8750"):
    """Install hooks in all connected repos."""
    print(f"Installing Agentic hooks (server: {server})")
    print()
    installed = 0
    for name, path in CONNECTED_REPOS.items():
        if not path.exists():
            print(f"  SKIP: {name} — path does not exist: {path}")
            continue
        if install(str(path), server):
            installed += 1
    print(f"\nInstalled: {installed}/{len(CONNECTED_REPOS)} repos")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Install Agentic hooks")
    parser.add_argument("repo", nargs="?", default=None, help="Path to a specific repo (omit for all)")
    parser.add_argument("--server", default="http://localhost:8750")
    parser.add_argument("--list", action="store_true", help="Show hook status")
    parser.add_argument("--uninstall", action="store_true", help="Remove hooks")
    parser.add_argument("--all", action="store_true", help="Install in all connected repos")
    args = parser.parse_args()

    if args.list:
        show_status()
    elif args.uninstall:
        if args.repo:
            uninstall(args.repo)
        else:
            print("Uninstalling from all connected repos:")
            for name, path in CONNECTED_REPOS.items():
                if path.exists():
                    uninstall(str(path))
    elif args.repo:
        install(args.repo, args.server)
    else:
        install_all(args.server)

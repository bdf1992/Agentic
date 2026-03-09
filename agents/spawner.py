"""
Agent Spawner — launches Claude Code instances as agents.

Each agent = a `claude` CLI process with:
- A system prompt defining its role
- Allowed tools controlling what it can do
- A working directory
- Optional MCP tools for platform operations

Two modes:
- Headless (-p): runs, returns result, exits. For autonomous/scheduled tasks.
- Interactive: opens a terminal you can jump into. For steering/debugging.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
import os
from pathlib import Path
from typing import Optional

from agents.configs import AGENTS, get_agent_config
from core.state import state
from core.vector_store import VectorStore, Document
from core.metadata import extract_metadata

ROOT = Path(__file__).parent.parent

# Vector store for indexing agent outputs
_output_store = VectorStore("agent_outputs")


class AgentProcess:
    """Tracks a running Claude Code agent instance."""

    def __init__(self, agent_id: str, agent_type: str, process: subprocess.Popen,
                 mode: str = "headless"):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.process = process
        self.mode = mode
        self.started = time.time()
        self.finished: float | None = None
        self.output: str = ""
        self.returncode: int | None = None


# Track running processes
_active: dict[str, AgentProcess] = {}
_lock = threading.Lock()


def spawn_headless(agent_type: str, task: str = "",
                   extra_prompt: str = "", output_format: str = "text") -> str:
    """
    Launch a Claude Code instance in headless mode (-p).
    Returns the agent_id. Output is collected asynchronously.
    """
    config = get_agent_config(agent_type)
    if not config:
        raise ValueError(f"Unknown agent type: {agent_type}")

    agent_id = f"{agent_type}_{int(time.time())}"

    # Build the prompt - combine startup message with task
    startup = config.get("startup_message", "")
    if task:
        prompt = task
    else:
        prompt = startup or "Run your standard workflow and report findings."

    if extra_prompt:
        prompt = f"{extra_prompt}\n\n{prompt}"

    # Build CLI command - prompt will be piped via stdin
    cmd = ["claude", "-p", "--model", "opus"]

    # System prompt
    cmd.extend(["--system-prompt", config["system_prompt"]])

    # Allowed tools
    if config.get("allowed_tools"):
        cmd.extend(["--allowedTools", ",".join(config["allowed_tools"])])

    # Permission mode
    if config.get("permission_mode"):
        cmd.extend(["--permission-mode", config["permission_mode"]])

    # Additional directories
    if config.get("add_dirs"):
        for d in config["add_dirs"]:
            if Path(d).exists():
                cmd.extend(["--add-dir", d])

    # MCP config
    mcp_path = ROOT / ".mcp.json"
    if mcp_path.exists():
        cmd.extend(["--mcp-config", str(mcp_path)])

    # Output format
    if output_format != "text":
        cmd.extend(["--output-format", output_format])

    # Register in state
    s = state()
    s.spawn(agent_id, agent_type, "headless")

    # Launch in background thread
    def _run():
        try:
            # Pipe prompt via stdin — positional args with newlines
            # break Windows argument parsing
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=config.get("cwd", str(ROOT)),
                timeout=600,  # 10 min max
            )
            with _lock:
                if agent_id in _active:
                    proc = _active[agent_id]
                    proc.output = result.stdout.strip()
                    proc.returncode = result.returncode
                    proc.finished = time.time()

            # Save finding to state
            output = result.stdout.strip()
            if result.returncode == 0 and output:
                # Truncate for state storage, keep full in process
                summary = output[:500] if len(output) > 500 else output
                s.complete(agent_id, summary, "info")
            else:
                error = result.stderr.strip() or "Process failed"
                s.fail(agent_id, error[:500])

            # Save full output to file
            output_dir = ROOT / "data" / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{agent_id}.txt"
            full_output = (
                f"Agent: {agent_type}\n"
                f"Started: {time.ctime(proc.started)}\n"
                f"Finished: {time.ctime(proc.finished)}\n"
                f"Return code: {result.returncode}\n"
                f"{'='*60}\n"
                f"{result.stdout}\n"
                f"{'='*60}\n"
                f"STDERR:\n{result.stderr}\n"
            )
            output_file.write_text(full_output)

            # Auto-index into vector store with rich metadata
            try:
                duration = proc.finished - proc.started if proc.finished else 0
                meta = extract_metadata(
                    full_output, agent_type=agent_type,
                    return_code=result.returncode, duration=duration,
                )
                doc = Document(
                    id=agent_id,
                    text=full_output[:5000],
                    metadata={
                        **meta.to_dict(),
                        "timestamp": proc.finished,
                    },
                )
                _output_store.add(doc)
            except Exception:
                pass  # indexing failure should never block agent completion

        except subprocess.TimeoutExpired:
            s.fail(agent_id, "Timed out after 10 minutes")
        except Exception as e:
            s.fail(agent_id, str(e))
        finally:
            with _lock:
                _active.pop(agent_id, None)

    proc = AgentProcess(agent_id, agent_type, None, "headless")
    with _lock:
        _active[agent_id] = proc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return agent_id


def spawn_interactive(agent_type: str, task: str = "") -> dict:
    """
    Open a new terminal window with Claude Code configured as this agent.
    Uses a PowerShell launcher script to pass the system prompt from a file,
    avoiding Windows shell escaping issues with multi-line text.
    """
    config = get_agent_config(agent_type)
    if not config:
        raise ValueError(f"Unknown agent type: {agent_type}")

    cwd = config.get("cwd", str(ROOT))

    # Combine system prompt + startup message into one system prompt.
    # Passing a positional arg to `claude` triggers headless (-p) mode,
    # so the startup instructions must live in the system prompt instead.
    startup = config.get("startup_message", "")
    if task:
        startup = task
    full_prompt = config["system_prompt"]
    if startup:
        full_prompt += (
            "\n\n=== STARTUP INSTRUCTIONS ===\n"
            "When the user sends their first message (even just 'go' or 'start'), "
            "execute these instructions immediately:\n\n"
            f"{startup}"
        )

    # Write combined prompt to file (avoids shell escaping nightmares)
    prompt_dir = ROOT / "data" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = prompt_dir / f"{agent_type}.txt"
    prompt_file.write_text(full_prompt, encoding="utf-8")

    # Build a PowerShell launcher script that reads the prompt file
    # and passes its content to claude --system-prompt
    launcher_dir = ROOT / "data" / "launchers"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    launcher_file = launcher_dir / f"{agent_type}.ps1"

    # Build claude args (everything except --system-prompt)
    claude_args = ["--model", "opus"]
    if config.get("allowed_tools"):
        claude_args.extend(["--allowedTools", ",".join(config["allowed_tools"])])
    if config.get("permission_mode"):
        claude_args.extend(["--permission-mode", config["permission_mode"]])
    if config.get("add_dirs"):
        for d in config["add_dirs"]:
            if Path(d).exists():
                claude_args.extend(["--add-dir", d])

    mcp_path = ROOT / ".mcp.json"
    if mcp_path.exists():
        claude_args.extend(["--mcp-config", str(mcp_path)])

    args_str = " ".join(f'"{a}"' if " " in a and not a.startswith('"') else a
                        for a in claude_args)

    # PowerShell script: read prompt file, invoke claude with content (no positional arg)
    ps_script = f"""$prompt = Get-Content -Path '{prompt_file}' -Raw -Encoding UTF8
claude --system-prompt $prompt {args_str}
"""
    launcher_file.write_text(ps_script, encoding="utf-8")

    # Open in Windows Terminal running the PowerShell launcher
    try:
        wt_cmd = [
            "wt", "-d", cwd,
            "--title", f"Agentic: {config['name']}",
            "powershell", "-ExecutionPolicy", "Bypass",
            "-File", str(launcher_file),
        ]
        subprocess.Popen(wt_cmd, shell=True)
        method = "wt"
    except Exception:
        try:
            # Fallback: cmd.exe launching powershell
            subprocess.Popen(
                f'start "{config["name"]} Agent" powershell -ExecutionPolicy Bypass'
                f' -File "{launcher_file}"',
                shell=True,
                cwd=cwd,
            )
            method = "cmd"
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return {
        "status": "opened",
        "method": method,
        "agent_type": agent_type,
        "cwd": cwd,
    }


def get_active() -> list[dict]:
    """List currently running agent processes."""
    with _lock:
        return [
            {
                "agent_id": p.agent_id,
                "agent_type": p.agent_type,
                "mode": p.mode,
                "started": p.started,
                "elapsed": time.time() - p.started,
            }
            for p in _active.values()
        ]


def get_output(agent_id: str) -> str | None:
    """Get the output of a completed agent run."""
    output_file = ROOT / "data" / "outputs" / f"{agent_id}.txt"
    if output_file.exists():
        return output_file.read_text()
    return None


def list_outputs(limit: int = 20) -> list[dict]:
    """List recent agent output files."""
    output_dir = ROOT / "data" / "outputs"
    if not output_dir.exists():
        return []

    files = sorted(output_dir.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    results = []
    for f in files[:limit]:
        # Parse agent type from filename
        parts = f.stem.rsplit("_", 1)
        agent_type = parts[0] if len(parts) > 1 else "unknown"
        results.append({
            "agent_id": f.stem,
            "agent_type": agent_type,
            "timestamp": f.stat().st_mtime,
            "size": f.stat().st_size,
        })
    return results

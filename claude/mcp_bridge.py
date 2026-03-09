"""
MCP Bridge — platform tools for Claude Code agent instances.

Every Claude Code instance spawned by the platform gets these MCP tools.
They let the agent interact with the platform (report findings, check status,
read other agents' outputs, etc.)

Configure in .mcp.json:
{
    "mcpServers": {
        "agentic": {
            "command": "python",
            "args": ["claude/mcp_bridge.py"]
        }
    }
}
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

SERVER = "http://localhost:8750"


def handle_tool_call(tool_name: str, arguments: dict) -> str:
    """Route MCP tool calls."""

    # --- Platform status tools (talk to server if running) ---

    if tool_name == "agentic_status":
        if HAS_REQUESTS:
            try:
                r = requests.get(f"{SERVER}/status", timeout=5)
                return json.dumps(r.json(), indent=2)
            except Exception:
                pass
        # Fallback: read state directly
        from core.state import state
        s = state()
        return json.dumps(s.digest(), indent=2)

    elif tool_name == "agentic_digest":
        if HAS_REQUESTS:
            try:
                r = requests.get(f"{SERVER}/digest", timeout=5)
                return r.json().get("digest", "No digest")
            except Exception:
                pass
        from core.state import state
        s = state()
        d = s.digest()
        recent = s.recent(10)
        lines = [f"Active: {d['active']} | Pending: {d['pending_review']} | Completed: {d['completed_today']}"]
        for r in recent:
            status = r.status.value if hasattr(r.status, 'value') else str(r.status)
            lines.append(f"  {r.agent_type}: {status} — {r.finding or 'running...'}")
        return "\n".join(lines)

    elif tool_name == "agentic_report":
        # Agent reports a finding back to the platform
        summary = arguments.get("summary", "No summary")
        severity = arguments.get("severity", "info")
        agent_type = arguments.get("agent_type", "unknown")
        agent_id = f"{agent_type}_{int(time.time())}"

        from core.state import state
        s = state()
        s.spawn(agent_id, agent_type, "mcp_report")
        s.complete(agent_id, summary, severity)

        # Also save to outputs
        output_dir = ROOT / "data" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{agent_id}.txt").write_text(
            f"Agent: {agent_type}\nSeverity: {severity}\nTime: {time.ctime()}\n"
            f"{'='*60}\n{summary}\n"
        )
        return json.dumps({"status": "reported", "agent_id": agent_id})

    elif tool_name == "agentic_read_output":
        # Read another agent's output
        target_id = arguments.get("agent_id", "")
        output_file = ROOT / "data" / "outputs" / f"{target_id}.txt"
        if output_file.exists():
            return output_file.read_text()
        return f"No output found for agent {target_id}"

    elif tool_name == "agentic_list_outputs":
        # List recent agent outputs
        output_dir = ROOT / "data" / "outputs"
        if not output_dir.exists():
            return "No outputs yet"
        files = sorted(output_dir.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
        results = []
        for f in files[:20]:
            results.append(f"{f.stem} ({f.stat().st_size} bytes, {time.ctime(f.stat().st_mtime)})")
        return "\n".join(results) or "No outputs yet"

    elif tool_name == "agentic_spawn":
        # Spawn another agent
        if HAS_REQUESTS:
            try:
                r = requests.post(f"{SERVER}/spawn", json=arguments, timeout=10)
                return json.dumps(r.json(), indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": "Server not running"})

    elif tool_name == "agentic_decide":
        agent_id = arguments.get("agent_id", "")
        if HAS_REQUESTS:
            try:
                r = requests.post(f"{SERVER}/decide/{agent_id}", json=arguments, timeout=5)
                return json.dumps(r.json(), indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": "Server not running"})

    elif tool_name == "agentic_judge":
        # Run the experiment judge against a directory
        run_dir = arguments.get("run_dir", "workspace")
        skip_llm = arguments.get("skip_llm", False)

        run_path = Path(run_dir)
        if not run_path.is_absolute():
            run_path = ROOT / run_dir

        if not run_path.exists():
            return json.dumps({"error": f"Directory not found: {run_dir}"})

        try:
            from experiments.judge import judge_run
            verdict = judge_run(str(run_path), skip_llm=skip_llm)
            return json.dumps(verdict, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Judge failed: {e}"})

    elif tool_name == "agentic_health":
        # Quick health check — repos, imports, workspace
        if HAS_REQUESTS:
            try:
                r = requests.get(f"{SERVER}/health", timeout=30)
                return json.dumps(r.json(), indent=2)
            except Exception:
                pass
        # Fallback: basic local checks
        checks = {}
        repos = {"Agentic": ROOT}
        for name, path in repos.items():
            checks[name] = {"exists": path.exists(), "path": str(path)}
        # Workspace file check
        workspace = ROOT / "workspace"
        if workspace.exists():
            py_files = list(workspace.glob("*.py"))
            checks["workspace_py_files"] = len(py_files)
        return json.dumps(checks, indent=2)

    elif tool_name == "agentic_search":
        # Filtered search across agent outputs
        query = arguments.get("query", "")
        agent_type_filter = arguments.get("agent_type", "")
        role_filter = arguments.get("role", "")
        concept_filter = arguments.get("concept", "")
        observation_filter = arguments.get("observation", "")
        prop_filter = arguments.get("property", "")

        if HAS_REQUESTS:
            try:
                params = {"q": query}
                if agent_type_filter:
                    params["agent_type"] = agent_type_filter
                if role_filter:
                    params["role"] = role_filter
                if concept_filter:
                    params["concept"] = concept_filter
                if observation_filter:
                    params["observation"] = observation_filter
                if prop_filter:
                    params["prop"] = prop_filter
                r = requests.get(f"{SERVER}/search-outputs", params=params, timeout=10)
                return json.dumps(r.json(), indent=2)
            except Exception:
                pass

        # Fallback: direct file search (text only, no metadata filtering)
        if not query:
            return json.dumps({"error": "No query provided (server offline, metadata filters unavailable)"})
        output_dir = ROOT / "data" / "outputs"
        if not output_dir.exists():
            return json.dumps({"results": [], "query": query})
        results = []
        for f in sorted(output_dir.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True)[:30]:
            try:
                text = f.read_text(errors="replace")
                if query.lower() in text.lower():
                    idx = text.lower().index(query.lower())
                    start = max(0, idx - 100)
                    end = min(len(text), idx + len(query) + 100)
                    results.append({"agent_id": f.stem, "context": text[start:end]})
            except Exception:
                continue
        return json.dumps({"results": results[:10], "query": query}, indent=2)

    elif tool_name == "agentic_knowledge":
        # What does the platform know? Tag summary across all indexed outputs.
        if HAS_REQUESTS:
            try:
                r = requests.get(f"{SERVER}/knowledge", timeout=10)
                return json.dumps(r.json(), indent=2)
            except Exception:
                pass
        return json.dumps({"error": "Server not running — knowledge summary requires indexed outputs"})

    elif tool_name == "agentic_export":
        # Build an export package from internal knowledge
        framing = arguments.get("framing", "")
        if not framing:
            return json.dumps({"error": "framing is required — describe the topic/theme for the export"})

        if HAS_REQUESTS:
            try:
                payload = {"framing": framing}
                if arguments.get("name"):
                    payload["name"] = arguments["name"]
                if "include_code" in arguments:
                    payload["include_code"] = arguments["include_code"]
                if "include_docs" in arguments:
                    payload["include_docs"] = arguments["include_docs"]
                if "include_outputs" in arguments:
                    payload["include_outputs"] = arguments["include_outputs"]
                if arguments.get("extra_paths"):
                    payload["extra_paths"] = arguments["extra_paths"]
                r = requests.post(f"{SERVER}/export", json=payload, timeout=30)
                return json.dumps(r.json(), indent=2)
            except Exception:
                pass

        # Fallback: run export directly
        try:
            from core.export import export_package
            result = export_package(
                framing=framing,
                name=arguments.get("name", ""),
                include_code=arguments.get("include_code", True),
                include_docs=arguments.get("include_docs", True),
                include_outputs=arguments.get("include_outputs", True),
                extra_paths=arguments.get("extra_paths"),
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Export failed: {e}"})

    elif tool_name == "agentic_list_exports":
        # List existing export packages
        if HAS_REQUESTS:
            try:
                r = requests.get(f"{SERVER}/exports", timeout=10)
                return json.dumps(r.json(), indent=2)
            except Exception:
                pass
        try:
            from core.export import list_exports
            return json.dumps({"exports": list_exports()}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# MCP tool definitions
TOOLS = [
    {
        "name": "agentic_status",
        "description": "Get platform status: active agents, pending reviews, queue depth, recent activity",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_digest",
        "description": "Get a human-readable digest of recent platform activity",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_report",
        "description": "Report a finding back to the platform. Use this to save your results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "What you found (concise)"},
                "severity": {"type": "string", "enum": ["info", "warning", "action_required"],
                             "description": "How important is this"},
                "agent_type": {"type": "string", "description": "Your agent type (guardian, infra, etc.)"},
            },
            "required": ["summary", "severity"],
        },
    },
    {
        "name": "agentic_read_output",
        "description": "Read the full output of a previous agent run",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to read output from"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "agentic_list_outputs",
        "description": "List recent agent run outputs (most recent first)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_spawn",
        "description": "Spawn another agent. Types: guardian, docs, infra, github, maintenance, probe, synthesis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {"type": "string", "description": "Agent type to spawn"},
                "trigger": {"type": "string", "description": "What triggered this"},
                "config": {"type": "object", "description": "Agent-specific config"},
            },
            "required": ["agent_type"],
        },
    },
    {
        "name": "agentic_decide",
        "description": "Approve or reject a pending agent finding",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to decide on"},
                "decision": {"type": "string", "enum": ["approve", "reject", "redirect"]},
            },
            "required": ["agent_id", "decision"],
        },
    },
    {
        "name": "agentic_judge",
        "description": "Run the experiment judge against a directory. Returns verdict (STRONG_PASS/PASS/PARTIAL/INSUFFICIENT/FAIL) with scores for 17 properties.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_dir": {"type": "string", "description": "Directory to judge (default: workspace). Relative to project root."},
                "skip_llm": {"type": "boolean", "description": "Skip LLM scoring, only run mechanical checks (faster)"},
            },
        },
    },
    {
        "name": "agentic_health",
        "description": "Run a deep health check: connected repos, imports, workspace code execution, disk usage, vector store stats.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_search",
        "description": "Search agent outputs by text and/or metadata. Filter by agent_type, role (builder/operator), concept (eigenvalue/topology/etc), observation (O0-O8), or property (spectral/invariant/etc).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text search term"},
                "agent_type": {"type": "string", "description": "Filter by agent type (probe, guardian, synthesis, etc.)"},
                "role": {"type": "string", "description": "Filter by role: builder, operator, coordinator, evaluator"},
                "concept": {"type": "string", "description": "Filter by concept: eigenvalue, group_theory, topology, algebra, quaternion, entropy, proof, etc."},
                "observation": {"type": "string", "description": "Filter by observation: O0, O1, O2, ..., O8"},
                "property": {"type": "string", "description": "Filter by property: invariant, spectral, ouroboros, time_like, etc."},
            },
        },
    },
    {
        "name": "agentic_knowledge",
        "description": "What does the platform know? Returns tag counts across all indexed agent outputs — which concepts, observations, properties, and agent types are represented.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_export",
        "description": "Build a portable export package from internal knowledge. Given a framing query (topic/theme), gathers relevant code, docs, agent outputs, and RAG context into a flat directory with a synthesis document. The result is a self-contained package any LLM or human can review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "framing": {"type": "string", "description": "Topic/theme/question driving the export (e.g. 'spectral gap derivation', 'all topology work', 'quaternion algebra and conservation')"},
                "name": {"type": "string", "description": "Optional package name (auto-generated if empty)"},
                "include_code": {"type": "boolean", "description": "Include matching .py files (default true)"},
                "include_docs": {"type": "boolean", "description": "Include matching .md files (default true)"},
                "include_outputs": {"type": "boolean", "description": "Include matching agent outputs (default true)"},
                "extra_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional file paths to force-include in the export",
                },
            },
            "required": ["framing"],
        },
    },
    {
        "name": "agentic_list_exports",
        "description": "List all existing export packages with their framing, file counts, and paths.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def main():
    """Stdio-based MCP server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            method = msg.get("method", "")
            msg_id = msg.get("id")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "agentic", "version": "0.2.0"},
                    },
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"tools": TOOLS},
                }
            elif method == "tools/call":
                tool_name = msg["params"]["name"]
                arguments = msg["params"].get("arguments", {})
                result = handle_tool_call(tool_name, arguments)
                response = {
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": [{"type": "text", "text": result}]},
                }
            elif method == "notifications/initialized":
                continue
            else:
                response = {
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"},
                }

            print(json.dumps(response), flush=True)

        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    main()

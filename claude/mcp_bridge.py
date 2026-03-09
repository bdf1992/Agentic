"""
MCP Bridge — connects Claude Code tools to the Agentic platform API.

This runs as an MCP server that Claude Code can use natively.
It exposes platform operations as MCP tools:
- agentic_status: get platform status
- agentic_spawn: spawn an agent
- agentic_digest: get the human-readable digest
- agentic_decide: approve/reject a pending finding

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
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

SERVER = "http://localhost:8750"


def handle_tool_call(tool_name: str, arguments: dict) -> str:
    """Route MCP tool calls to the platform API."""
    if not HAS_REQUESTS:
        return json.dumps({"error": "requests library not installed"})

    try:
        if tool_name == "agentic_status":
            r = requests.get(f"{SERVER}/status", timeout=5)
            return json.dumps(r.json(), indent=2)

        elif tool_name == "agentic_digest":
            r = requests.get(f"{SERVER}/digest", timeout=5)
            return r.json().get("digest", "No digest available")

        elif tool_name == "agentic_spawn":
            r = requests.post(f"{SERVER}/spawn", json=arguments, timeout=10)
            return json.dumps(r.json(), indent=2)

        elif tool_name == "agentic_decide":
            agent_id = arguments.get("agent_id", "")
            r = requests.post(f"{SERVER}/decide/{agent_id}", json=arguments, timeout=5)
            return json.dumps(r.json(), indent=2)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    except requests.ConnectionError:
        return json.dumps({"error": "Platform server not running. Start with: python core/server.py"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# MCP protocol scaffolding (stdio-based)
TOOLS = [
    {
        "name": "agentic_status",
        "description": "Get current platform status: active agents, pending reviews, queue depth",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_digest",
        "description": "Get a human-readable digest of recent platform activity",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agentic_spawn",
        "description": "Spawn an agent. Types: probe, guardian, synthesis, maintenance",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {"type": "string", "description": "Agent type to spawn"},
                "trigger": {"type": "string", "description": "What triggered this spawn"},
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
]


def main():
    """Stdio-based MCP server. Reads JSON-RPC from stdin, writes to stdout."""
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
                        "serverInfo": {"name": "agentic", "version": "0.1.0"},
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
                continue  # No response needed for notifications
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

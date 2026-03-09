"""
Agentic Platform Server — the heartbeat.

FastAPI service that:
- Receives events from hooks
- Exposes status/digest endpoints
- Serves the dashboard
- Manages agent lifecycle

Usage:
    python core/server.py              # Start the platform
    python core/server.py --status     # Quick status check
"""

from __future__ import annotations

import sys
import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Path setup
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.event_queue import emit, queue
from core.state import state

app = FastAPI(title="Agentic Platform", version="0.1.0")

# ---------------------------------------------------------------------------
# Event ingestion
# ---------------------------------------------------------------------------

@app.post("/events")
async def receive_event(request: Request):
    """Receive an event from a hook or external source."""
    body = await request.json()
    ev = emit(
        event_type=body.get("type", "unknown"),
        repo=body.get("repo", "unknown"),
        **body.get("payload", {}),
    )
    return {"status": "queued", "event_id": ev.id}


# ---------------------------------------------------------------------------
# Status & digest
# ---------------------------------------------------------------------------

@app.get("/status")
async def platform_status():
    """Current platform state."""
    s = state()
    return {
        "digest": s.digest(),
        "active_agents": [
            {"id": r.agent_id, "type": r.agent_type, "trigger": r.trigger_event}
            for r in s.active()
        ],
        "pending_review": [
            {"id": r.agent_id, "finding": r.finding, "severity": r.severity}
            for r in s.pending_review()
        ],
        "event_queue_depth": queue().pending(),
    }


@app.get("/digest")
async def digest():
    """Human-readable digest of recent activity."""
    s = state()
    recent = s.recent(20)
    pending = s.pending_review()
    d = s.digest()

    lines = [
        f"## Platform Digest",
        f"",
        f"**Active**: {d['active']} | **Pending review**: {d['pending_review']} | "
        f"**Completed today**: {d['completed_today']} | **Failed**: {d['failed_today']}",
        f"",
    ]

    if pending:
        lines.append("### Needs Your Decision")
        for r in pending:
            lines.append(f"- [{r.severity.upper()}] {r.finding} (agent: {r.agent_id})")
        lines.append("")

    if recent:
        lines.append("### Recent Activity")
        for r in recent[:10]:
            status = r.status.value if hasattr(r.status, 'value') else r.status
            lines.append(f"- `{r.agent_type}` — {status}: {r.finding or 'running...'}")

    return {"digest": "\n".join(lines)}


# ---------------------------------------------------------------------------
# Agent control
# ---------------------------------------------------------------------------

@app.post("/spawn")
async def spawn_agent(request: Request):
    """Manually spawn an agent."""
    body = await request.json()
    agent_type = body.get("agent_type", "probe")
    trigger = body.get("trigger", "manual")
    config = body.get("config", {})

    # For now, record the spawn. Real spawning comes in agents/ layer.
    s = state()
    import time
    agent_id = f"{agent_type}_{int(time.time())}"
    rec = s.spawn(agent_id, agent_type, trigger)

    return {"status": "spawned", "agent_id": agent_id}


@app.post("/decide/{agent_id}")
async def decide(agent_id: str, request: Request):
    """Record a human decision on a pending finding."""
    body = await request.json()
    decision = body.get("decision", "approve")  # approve | reject | redirect
    s = state()
    s.decide(agent_id, decision)
    return {"status": "decided", "agent_id": agent_id, "decision": decision}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """The command center — single surface for human review."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Mono', 'Fira Code', monospace;
            background: #0a0a0a; color: #e0e0e0;
            padding: 2rem;
        }
        h1 { color: #7af; margin-bottom: 1rem; }
        h2 { color: #adf; margin: 1.5rem 0 0.5rem; font-size: 1rem; }
        .card {
            background: #151515; border: 1px solid #333;
            border-radius: 6px; padding: 1rem; margin: 0.5rem 0;
        }
        .stat { display: inline-block; margin-right: 2rem; }
        .stat .n { font-size: 2rem; color: #7af; }
        .stat .label { font-size: 0.8rem; color: #888; }
        .severity-warning { border-left: 3px solid #fa0; }
        .severity-action_required { border-left: 3px solid #f44; }
        .severity-info { border-left: 3px solid #4a4; }
        .tier-gold { border-left: 3px solid #ffd700; }
        .tier-silver { border-left: 3px solid #c0c0c0; }
        .tier-bronze { border-left: 3px solid #cd7f32; }
        .tier-label { font-weight: bold; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .tier-label.gold { color: #ffd700; }
        .tier-label.silver { color: #c0c0c0; }
        .tier-label.bronze { color: #cd7f32; }
        .finding { margin: 0.5rem 0; }
        .btn {
            background: #333; border: 1px solid #555; color: #ddd;
            padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer;
            margin-right: 0.5rem;
        }
        .btn:hover { background: #444; }
        .btn.approve { border-color: #4a4; }
        .btn.reject { border-color: #f44; }
        #digest { white-space: pre-wrap; line-height: 1.6; }
    </style>
</head>
<body>
    <h1>Agentic Platform</h1>
    <div id="stats" class="card"></div>
    <h2>Pending Review</h2>
    <div id="pending"></div>
    <h2>Recent Activity</h2>
    <div id="recent"></div>

    <script>
        async function refresh() {
            const res = await fetch('/status');
            const data = await res.json();
            const d = data.digest;

            document.getElementById('stats').innerHTML = `
                <span class="stat"><span class="n">${d.active}</span><br><span class="label">Active</span></span>
                <span class="stat"><span class="n">${d.pending_review}</span><br><span class="label">Pending</span></span>
                <span class="stat"><span class="n">${d.completed_today}</span><br><span class="label">Completed</span></span>
                <span class="stat"><span class="n">${d.failed_today}</span><br><span class="label">Failed</span></span>
            `;

            const pendingEl = document.getElementById('pending');
            if (data.pending_review.length === 0) {
                pendingEl.innerHTML = '<div class="card">Nothing pending.</div>';
            } else {
                pendingEl.innerHTML = data.pending_review.map(r => {
                    // Detect tier from finding text
                    let tierClass = 'severity-' + r.severity;
                    let tierLabel = '';
                    if (r.finding && r.finding.includes('GOLD')) {
                        tierClass = 'tier-gold';
                        tierLabel = '<span class="tier-label gold">GOLD</span> ';
                    } else if (r.finding && r.finding.includes('SILVER')) {
                        tierClass = 'tier-silver';
                        tierLabel = '<span class="tier-label silver">SILVER</span> ';
                    } else if (r.finding && r.finding.includes('BRONZE')) {
                        tierClass = 'tier-bronze';
                        tierLabel = '<span class="tier-label bronze">BRONZE</span> ';
                    }
                    return `
                    <div class="card ${tierClass}">
                        <div class="finding">${tierLabel}${r.finding}</div>
                        <button class="btn approve" onclick="decide('${r.id}','approve')">Approve</button>
                        <button class="btn reject" onclick="decide('${r.id}','reject')">Reject</button>
                    </div>`;
                }).join('');
            }

            const recentEl = document.getElementById('recent');
            recentEl.innerHTML = data.active_agents.map(r => `
                <div class="card severity-info">
                    <strong>${r.type}</strong> — running (trigger: ${r.trigger})
                </div>
            `).join('') || '<div class="card">No recent activity.</div>';
        }

        async function decide(agentId, decision) {
            await fetch(`/decide/${agentId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({decision})
            });
            refresh();
        }

        refresh();
        setInterval(refresh, 5000);
    </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if "--status" in sys.argv:
        s = state()
        d = s.digest()
        print(f"Active: {d['active']} | Pending: {d['pending_review']} | "
              f"Completed today: {d['completed_today']} | Failed: {d['failed_today']}")
        return

    print("Starting Agentic Platform on http://localhost:8750")
    uvicorn.run(app, host="0.0.0.0", port=8750, log_level="info")


if __name__ == "__main__":
    main()

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
from core.dispatcher import Dispatcher

# Global dispatcher instance
_dispatcher: Dispatcher | None = None

app = FastAPI(title="Agentic Platform", version="0.1.0")


@app.on_event("startup")
async def startup():
    """Start the dispatcher when the server boots."""
    global _dispatcher
    _dispatcher = Dispatcher()
    _dispatcher.start()


@app.on_event("shutdown")
async def shutdown():
    """Stop the dispatcher on server shutdown."""
    global _dispatcher
    if _dispatcher:
        _dispatcher.stop()


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
        "dispatcher": _dispatcher.status() if _dispatcher else {"running": False},
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


@app.get("/recent")
async def recent_activity():
    """Recent agent activity for the dashboard timeline."""
    s = state()
    records = s.recent(30)
    return [
        {
            "id": r.agent_id,
            "type": r.agent_type,
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "finding": r.finding or "running...",
            "severity": r.severity,
            "started": r.started,
            "finished": r.finished,
            "decision": r.human_decision,
        }
        for r in records
    ]


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
    <title>Agentic</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;
            background: #0a0a0a; color: #e0e0e0;
            max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem;
        }

        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        header h1 { font-size: 1.5rem; font-weight: 600; color: #fff; }
        .pulse { width: 10px; height: 10px; border-radius: 50%; background: #4a4; display: inline-block; animation: pulse 2s infinite; margin-right: 0.5rem; }
        .pulse.idle { background: #555; animation: none; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .header-status { font-size: 0.85rem; color: #888; display: flex; align-items: center; }

        /* Stats row */
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 1.25rem; text-align: center; }
        .stat-card .number { font-size: 2rem; font-weight: 700; line-height: 1; }
        .stat-card .label { font-size: 0.75rem; color: #666; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .stat-card.active .number { color: #7af; }
        .stat-card.pending .number { color: #fa0; }
        .stat-card.completed .number { color: #4a4; }
        .stat-card.failed .number { color: #f44; }

        /* Sections */
        section { margin-bottom: 2rem; }
        section h2 { font-size: 0.85rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.75rem; }

        /* Cards */
        .card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
        .card.needs-action { border-left: 3px solid #f44; }
        .card.warning { border-left: 3px solid #fa0; }
        .card.info { border-left: 3px solid #4a4; }
        .card.running { border-left: 3px solid #7af; }
        .card.gold { border-left: 3px solid #ffd700; }
        .card.silver { border-left: 3px solid #c0c0c0; }
        .card.bronze { border-left: 3px solid #cd7f32; }
        .card .row { display: flex; justify-content: space-between; align-items: center; }
        .card .agent-type { font-weight: 600; font-size: 0.85rem; text-transform: capitalize; }
        .card .status-badge { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 10px; font-weight: 600; }
        .badge-running { background: rgba(119,170,255,0.15); color: #7af; }
        .badge-completed { background: rgba(68,170,68,0.15); color: #4a4; }
        .badge-failed { background: rgba(255,68,68,0.15); color: #f44; }
        .badge-awaiting { background: rgba(255,170,0,0.15); color: #fa0; }
        .card .finding-text { font-size: 0.85rem; color: #aaa; margin-top: 0.5rem; line-height: 1.4; }
        .card .meta { font-size: 0.7rem; color: #555; margin-top: 0.4rem; }

        /* Buttons */
        .btn-group { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
        .btn { background: #1a1a1a; border: 1px solid #333; color: #ddd; padding: 0.4rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; transition: all 0.15s; }
        .btn:hover { background: #252525; border-color: #555; }
        .btn.approve { border-color: #4a4; color: #4a4; }
        .btn.approve:hover { background: rgba(68,170,68,0.1); }
        .btn.reject { border-color: #f44; color: #f44; }
        .btn.reject:hover { background: rgba(255,68,68,0.1); }

        /* Quick actions */
        .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 2rem; }
        .action-btn { background: #151515; border: 1px solid #333; color: #aaa; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
        .action-btn:hover { background: #1a1a1a; color: #ddd; border-color: #555; }

        /* Dispatcher info */
        .dispatcher-bar { background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 6px; padding: 0.6rem 1rem; font-size: 0.75rem; color: #555; display: flex; gap: 1.5rem; margin-bottom: 2rem; }
        .dispatcher-bar span { color: #777; }

        /* Empty state */
        .empty { color: #444; font-size: 0.85rem; padding: 1rem; text-align: center; }

        /* Timeline dots */
        .timeline-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-right: 0.5rem; flex-shrink: 0; margin-top: 0.35rem; }
        .dot-running { background: #7af; }
        .dot-completed { background: #4a4; }
        .dot-failed { background: #f44; }
        .dot-awaiting { background: #fa0; }
    </style>
</head>
<body>
    <header>
        <h1>Agentic</h1>
        <div class="header-status" id="headerStatus">
            <span class="pulse" id="pulseIndicator"></span>
            <span id="statusText">connecting...</span>
        </div>
    </header>

    <div class="dispatcher-bar" id="dispatcherBar"></div>

    <div class="stats" id="stats"></div>

    <div class="actions">
        <button class="action-btn" onclick="runAgent('guardian')">Run Guardian</button>
        <button class="action-btn" onclick="runAgent('docs')">Update Docs</button>
        <button class="action-btn" onclick="runAgent('infra')">Check Infra</button>
        <button class="action-btn" onclick="runAgent('github')">Repo Health</button>
        <button class="action-btn" onclick="runAgent('maintenance')">Maintenance</button>
    </div>

    <section id="pendingSection" style="display:none">
        <h2>Needs Your Decision</h2>
        <div id="pending"></div>
    </section>

    <section>
        <h2>Activity</h2>
        <div id="timeline"></div>
    </section>

    <script>
        function ago(ts) {
            if (!ts) return '';
            const diff = Math.floor(Date.now()/1000 - ts);
            if (diff < 60) return diff + 's ago';
            if (diff < 3600) return Math.floor(diff/60) + 'm ago';
            if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
            return Math.floor(diff/86400) + 'd ago';
        }

        function badgeClass(status) {
            if (status === 'running') return 'badge-running';
            if (status === 'completed' || status === 'approved') return 'badge-completed';
            if (status === 'failed') return 'badge-failed';
            if (status === 'awaiting_approval') return 'badge-awaiting';
            return '';
        }

        function dotClass(status) {
            if (status === 'running') return 'dot-running';
            if (status === 'completed' || status === 'approved') return 'dot-completed';
            if (status === 'failed') return 'dot-failed';
            if (status === 'awaiting_approval') return 'dot-awaiting';
            return 'dot-completed';
        }

        function cardClass(r) {
            if (r.finding && r.finding.includes('GOLD')) return 'gold';
            if (r.finding && r.finding.includes('SILVER')) return 'silver';
            if (r.finding && r.finding.includes('BRONZE')) return 'bronze';
            if (r.status === 'running') return 'running';
            if (r.status === 'awaiting_approval') return 'needs-action';
            if (r.status === 'failed') return 'warning';
            return 'info';
        }

        function statusLabel(status) {
            return status.replace('_', ' ').replace('awaiting approval', 'needs review');
        }

        async function refresh() {
            try {
                const [statusRes, recentRes] = await Promise.all([
                    fetch('/status'), fetch('/recent')
                ]);
                const data = await statusRes.json();
                const recent = await recentRes.json();
                const d = data.digest;
                const disp = data.dispatcher || {};

                // Header
                const isAlive = disp.running !== false;
                document.getElementById('pulseIndicator').className = isAlive ? 'pulse' : 'pulse idle';
                document.getElementById('statusText').textContent = isAlive
                    ? `${disp.agent_types?.length || 0} agent types listening`
                    : 'dispatcher offline';

                // Dispatcher bar
                document.getElementById('dispatcherBar').innerHTML =
                    `<span>Dispatcher: ${isAlive ? 'active' : 'stopped'}</span>` +
                    `<span>Queue: ${data.event_queue_depth} events</span>` +
                    `<span>Workers: ${disp.active_workers || 0} running</span>` +
                    `<span>Types: ${(disp.agent_types || []).join(', ')}</span>`;

                // Stats
                document.getElementById('stats').innerHTML = `
                    <div class="stat-card active"><div class="number">${d.active}</div><div class="label">Active</div></div>
                    <div class="stat-card pending"><div class="number">${d.pending_review}</div><div class="label">Pending</div></div>
                    <div class="stat-card completed"><div class="number">${d.completed_today}</div><div class="label">Completed Today</div></div>
                    <div class="stat-card failed"><div class="number">${d.failed_today}</div><div class="label">Failed Today</div></div>
                `;

                // Pending review
                const pendingSection = document.getElementById('pendingSection');
                const pendingEl = document.getElementById('pending');
                const pendingItems = recent.filter(r => r.status === 'awaiting_approval');
                if (pendingItems.length > 0) {
                    pendingSection.style.display = 'block';
                    pendingEl.innerHTML = pendingItems.map(r => `
                        <div class="card needs-action">
                            <div class="row">
                                <span class="agent-type">${r.type}</span>
                                <span class="status-badge badge-awaiting">needs review</span>
                            </div>
                            <div class="finding-text">${r.finding}</div>
                            <div class="btn-group">
                                <button class="btn approve" onclick="decide('${r.id}','approve')">Approve</button>
                                <button class="btn reject" onclick="decide('${r.id}','reject')">Reject</button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    pendingSection.style.display = 'none';
                }

                // Timeline
                const timelineEl = document.getElementById('timeline');
                if (recent.length === 0) {
                    timelineEl.innerHTML = '<div class="empty">No activity yet. Use the buttons above to run an agent.</div>';
                } else {
                    timelineEl.innerHTML = recent.map(r => `
                        <div class="card ${cardClass(r)}">
                            <div class="row">
                                <div style="display:flex; align-items:flex-start;">
                                    <span class="timeline-dot ${dotClass(r.status)}"></span>
                                    <div>
                                        <span class="agent-type">${r.type}</span>
                                        <div class="finding-text">${r.finding}</div>
                                        <div class="meta">${ago(r.started)}${r.finished ? ' · took ' + Math.round(r.finished - r.started) + 's' : ''}</div>
                                    </div>
                                </div>
                                <span class="status-badge ${badgeClass(r.status)}">${statusLabel(r.status)}</span>
                            </div>
                        </div>
                    `).join('');
                }
            } catch(e) {
                document.getElementById('statusText').textContent = 'disconnected';
                document.getElementById('pulseIndicator').className = 'pulse idle';
            }
        }

        async function decide(agentId, decision) {
            await fetch(`/decide/${agentId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({decision})
            });
            refresh();
        }

        async function runAgent(type) {
            await fetch('/spawn', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({agent_type: type, trigger: 'dashboard'})
            });
            refresh();
        }

        refresh();
        setInterval(refresh, 3000);
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

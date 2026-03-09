"""
Agentic Platform Server — Claude Code session launcher and manager.

Dashboard = a customizer for launching Claude Code instances as agents.
Each agent is a real Claude Code session with a system prompt, tools, and permissions.

Usage:
    python core/server.py              # Start the platform
    python core/server.py --status     # Quick status check
"""

from __future__ import annotations

import asyncio
import importlib
import shutil
import subprocess
import sys
import json
import time
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# Path setup
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.event_queue import emit, queue
from core.state import state
from core.vector_store import VectorStore, Document
from core.metadata import extract_metadata
from agents.configs import AGENTS, get_agent_config, list_agent_types
from agents.spawner import spawn_headless, spawn_interactive, get_active, get_output, list_outputs
from core.dispatcher import Dispatcher
from core.export import export_package, list_exports
from core.embeddings import embed_text, embed_query

app = FastAPI(title="Agentic Platform", version="0.3.0")

# Connected repositories — the repos this platform monitors
CONNECTED_REPOS = {
    "Agentic": ROOT,
}

# Shared vector store for agent output indexing
_output_store = VectorStore("agent_outputs")


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
        "active_processes": get_active(),
        "active_agents": [
            {"id": r.agent_id, "type": r.agent_type, "trigger": r.trigger_event}
            for r in s.active()
        ],
        "pending_review": [
            {"id": r.agent_id, "finding": r.finding, "severity": r.severity}
            for r in s.pending_review()
        ],
        "agent_types": list_agent_types(),
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
# Agent control — launches real Claude Code instances
# ---------------------------------------------------------------------------

@app.get("/agents")
async def list_agents():
    """List all available agent types with their configs."""
    return {
        name: {
            "name": cfg["name"],
            "description": cfg["description"],
            "allowed_tools": cfg.get("allowed_tools", []),
            "cwd": cfg.get("cwd", ""),
            "permission_mode": cfg.get("permission_mode", "default"),
        }
        for name, cfg in AGENTS.items()
    }


@app.post("/spawn")
async def spawn_agent(request: Request):
    """
    Launch a Claude Code instance as an agent.

    Body:
        agent_type: str — which agent config to use
        task: str — what to do (optional, uses default workflow)
        mode: str — "headless" (default) or "interactive"
    """
    body = await request.json()
    agent_type = body.get("agent_type", "guardian")
    task = body.get("task", "")
    mode = body.get("mode", "headless")

    if agent_type not in AGENTS:
        return JSONResponse(
            {"error": f"Unknown agent type: {agent_type}. Available: {list_agent_types()}"},
            status_code=400,
        )

    if mode == "interactive":
        # Opens a terminal window directly
        info = spawn_interactive(agent_type, task)
        return info
    else:
        # Launch headless Claude Code instance
        agent_id = spawn_headless(agent_type, task)
        return {
            "status": "spawned",
            "mode": "headless",
            "agent_id": agent_id,
            "agent_type": agent_type,
        }


@app.get("/output/{agent_id}")
async def agent_output(agent_id: str):
    """Get the full output of an agent run."""
    output = get_output(agent_id)
    if output:
        return {"agent_id": agent_id, "output": output}
    return JSONResponse({"error": f"No output for {agent_id}"}, status_code=404)


@app.get("/outputs")
async def recent_outputs():
    """List recent agent output files."""
    return list_outputs()


@app.post("/decide/{agent_id}")
async def decide(agent_id: str, request: Request):
    """Record a human decision on a pending finding."""
    body = await request.json()
    decision = body.get("decision", "approve")
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
# Judge — run experiment evaluation from the API
# ---------------------------------------------------------------------------

@app.post("/judge")
async def judge_experiment(request: Request):
    """
    Run the judge against a directory.
    Body: {run_dir: str, skip_llm: bool}
    """
    body = await request.json()
    run_dir = body.get("run_dir", "workspace")
    skip_llm = body.get("skip_llm", False)

    # Resolve relative to ROOT
    run_path = Path(run_dir)
    if not run_path.is_absolute():
        run_path = ROOT / run_dir

    if not run_path.exists():
        return JSONResponse({"error": f"Directory not found: {run_dir}"}, status_code=404)

    # Run judge in background thread to avoid blocking
    import threading as _threading
    result_holder = {"verdict": None, "error": None}

    def _run_judge():
        try:
            from experiments.judge import judge_run
            result_holder["verdict"] = judge_run(str(run_path), skip_llm=skip_llm)
        except Exception as e:
            result_holder["error"] = str(e)

    thread = _threading.Thread(target=_run_judge)
    thread.start()
    thread.join(timeout=360)  # 6 min max

    if result_holder["error"]:
        return JSONResponse({"error": result_holder["error"]}, status_code=500)
    if result_holder["verdict"] is None:
        return JSONResponse({"error": "Judge timed out"}, status_code=504)

    # Store verdict in state for dashboard visibility
    verdict = result_holder["verdict"]
    s = state()
    agent_id = f"judge_{int(time.time())}"
    s.spawn(agent_id, "judge", f"judging {run_dir}")
    verdict_str = verdict.get("verdict", "UNKNOWN")
    severity = "action_required" if verdict_str.startswith("FAIL") else "info"
    summary_parts = [f"Verdict: {verdict_str}"]
    if "summary" in verdict:
        sm = verdict["summary"]
        summary_parts.append(f"Present: {sm['present']}/{sm['total']} | Partial: {sm['partial']}")
    s.complete(agent_id, " | ".join(summary_parts), severity)

    return verdict


@app.get("/verdicts")
async def list_verdicts():
    """List all verdict.json files from experiment runs and workspace."""
    verdicts = []
    for verdict_file in ROOT.rglob("verdict.json"):
        if "__pycache__" in str(verdict_file):
            continue
        try:
            data = json.loads(verdict_file.read_text())
            verdicts.append({
                "path": str(verdict_file.relative_to(ROOT)),
                "run_id": data.get("run_id", verdict_file.parent.name),
                "verdict": data.get("verdict", "UNKNOWN"),
                "timestamp": data.get("timestamp", ""),
                "summary": data.get("summary", {}),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return sorted(verdicts, key=lambda v: v["timestamp"], reverse=True)


# ---------------------------------------------------------------------------
# Health — cross-repo validation
# ---------------------------------------------------------------------------

@app.get("/health")
async def platform_health():
    """Deep health check: repos, imports, disk, hooks."""
    checks = {}

    # 1. Connected repos — do they exist and are they git repos?
    repo_health = {}
    for name, path in CONNECTED_REPOS.items():
        info = {"path": str(path), "exists": path.exists()}
        if path.exists():
            git_dir = path / ".git"
            info["is_git_repo"] = git_dir.exists()
            # Check for uncommitted changes
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True, text=True, cwd=str(path), timeout=10
                )
                changed = [l for l in result.stdout.strip().split("\n") if l.strip()]
                info["uncommitted_changes"] = len(changed)
                info["clean"] = len(changed) == 0
            except Exception:
                info["uncommitted_changes"] = -1
                info["clean"] = None
            # Check if hooks are installed
            hook_path = git_dir / "hooks" / "post-commit"
            info["hook_installed"] = hook_path.exists() and "Agentic" in (
                hook_path.read_text() if hook_path.exists() else ""
            )
        repo_health[name] = info
    checks["repos"] = repo_health

    # 2. Core imports
    import_checks = {}
    for module_name in ["core.server", "core.state", "core.event_queue", "core.vector_store",
                         "core.dispatcher", "core.export",
                         "agents.configs", "agents.spawner",
                         "experiments.judge"]:
        try:
            importlib.import_module(module_name)
            import_checks[module_name] = "ok"
        except Exception as e:
            import_checks[module_name] = f"FAIL: {e}"
    checks["imports"] = import_checks

    # 3. Disk usage
    data_dir = ROOT / "data"
    if data_dir.exists():
        total_size = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
        checks["disk"] = {
            "data_dir_mb": round(total_size / (1024 * 1024), 2),
            "output_files": len(list((data_dir / "outputs").glob("*.txt"))) if (data_dir / "outputs").exists() else 0,
            "state_files": len(list((data_dir / "state").glob("*.json"))) if (data_dir / "state").exists() else 0,
            "spool_files": len(list((data_dir / "spool").glob("*.json"))) if (data_dir / "spool").exists() else 0,
        }
    else:
        checks["disk"] = {"data_dir_mb": 0, "output_files": 0, "state_files": 0, "spool_files": 0}

    # 4. Vector store
    checks["vector_store"] = {
        "documents": _output_store.count(),
        "ids": _output_store.all_ids()[:10],
    }

    # 5. Workspace health — do all .py files run?
    workspace = ROOT / "workspace"
    if workspace.exists():
        py_files = list(workspace.glob("*.py"))
        workspace_health = {"py_files": len(py_files), "results": {}}
        for pf in py_files:
            try:
                result = subprocess.run(
                    [sys.executable, str(pf)],
                    capture_output=True, text=True, cwd=str(workspace), timeout=15
                )
                workspace_health["results"][pf.name] = "ok" if result.returncode == 0 else f"exit {result.returncode}"
            except subprocess.TimeoutExpired:
                workspace_health["results"][pf.name] = "timeout"
            except Exception as e:
                workspace_health["results"][pf.name] = str(e)
        checks["workspace"] = workspace_health
    else:
        checks["workspace"] = {"py_files": 0, "results": {}}

    # Overall status
    all_imports_ok = all(v == "ok" for v in import_checks.values())
    all_repos_exist = all(r["exists"] for r in repo_health.values())
    workspace_results = checks.get("workspace", {}).get("results", {})
    all_code_runs = len(workspace_results) == 0 or all(v == "ok" for v in workspace_results.values())
    checks["overall"] = "healthy" if (all_imports_ok and all_repos_exist) else "degraded"
    if not all_code_runs:
        checks["overall"] = "degraded"

    return checks


@app.get("/repos")
async def list_repos():
    """List connected repositories with basic info."""
    repos = {}
    for name, path in CONNECTED_REPOS.items():
        info = {"path": str(path), "exists": path.exists()}
        if path.exists():
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--pretty=format:%H|%s|%ar"],
                    capture_output=True, text=True, cwd=str(path), timeout=10
                )
                if result.returncode == 0:
                    parts = result.stdout.split("|", 2)
                    if len(parts) == 3:
                        info["last_commit"] = {"hash": parts[0][:8], "message": parts[1], "when": parts[2]}
            except Exception:
                pass
        repos[name] = info
    return repos


# ---------------------------------------------------------------------------
# Vector store — search agent outputs
# ---------------------------------------------------------------------------

@app.post("/index-outputs")
async def index_outputs():
    """Index all agent outputs into the vector store with rich metadata."""
    output_dir = ROOT / "data" / "outputs"
    if not output_dir.exists():
        return {"indexed": 0}

    count = 0
    for f in output_dir.glob("*.txt"):
        doc_id = f.stem
        if _output_store.get(doc_id):
            continue  # already indexed
        text = f.read_text(errors="replace")
        # Extract agent_type from filename (format: {type}_{timestamp})
        parts = doc_id.rsplit("_", 1)
        agent_type = parts[0] if len(parts) > 1 else "unknown"
        meta = extract_metadata(text, agent_type=agent_type)
        embedding = embed_text(text[:5000])
        doc = Document(id=doc_id, text=text[:5000], embedding=embedding, metadata={
            **meta.to_dict(),
            "filename": f.name,
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime,
        })
        _output_store.add(doc)
        count += 1

    return {"indexed": count, "total": _output_store.count()}


@app.get("/search-outputs")
async def search_outputs(q: str = "", agent_type: str = "", role: str = "",
                         concept: str = "", observation: str = "", prop: str = ""):
    """Search agent outputs by text and/or metadata filters.

    Query params:
      q: text search
      agent_type: filter by agent type (probe, guardian, etc.)
      role: filter by role (builder, operator, coordinator)
      concept: filter by concept (eigenvalue, group_theory, topology, etc.)
      observation: filter by observation (O0-O8)
      prop: filter by property name (spectral, invariant, etc.)
    """
    # If any filter is provided, use filtered search
    has_filters = any([agent_type, role, concept, observation, prop])

    if not q and not has_filters:
        return {"results": [], "query": ""}

    # Use filtered search
    docs = _output_store.filter(
        agent_type=agent_type, role=role, concept=concept,
        observation=observation, prop=prop, text_query=q, limit=20,
    )
    results = []
    for doc in docs:
        context = ""
        if q:
            idx = doc.text.lower().find(q.lower())
            if idx >= 0:
                start = max(0, idx - 100)
                end = min(len(doc.text), idx + len(q) + 100)
                context = doc.text[start:end]
        else:
            context = doc.text[:300]
        results.append({
            "agent_id": doc.id,
            "context": context,
            "metadata": doc.metadata,
        })
    return {"results": results, "query": q, "filters": {
        "agent_type": agent_type, "role": role, "concept": concept,
        "observation": observation, "prop": prop,
    }, "total_matches": len(results)}


@app.get("/semantic-search")
async def semantic_search(q: str = "", top_k: int = 10):
    """Semantic search using TF-IDF embeddings and cosine similarity.

    Unlike /search-outputs (text matching), this finds conceptually similar
    outputs even if they use different words.
    """
    if not q:
        return {"results": [], "query": ""}
    query_vec = embed_query(q)
    matches = _output_store.search(query_vec, top_k=top_k)
    results = []
    for doc, score in matches:
        results.append({
            "agent_id": doc.id,
            "score": round(score, 4),
            "context": doc.text[:300],
            "metadata": doc.metadata,
        })
    return {"results": results, "query": q, "mode": "semantic"}


@app.get("/knowledge")
async def knowledge_summary():
    """What the platform knows — aggregate tag counts across all indexed outputs."""
    return {
        "documents": _output_store.count(),
        "tags": _output_store.tag_summary(),
    }


# ---------------------------------------------------------------------------
# Export — build portable review packages
# ---------------------------------------------------------------------------

@app.post("/export")
async def create_export(request: Request):
    """Build an export package driven by a framing query.

    POST body: {
        "framing": "spectral gap derivation",
        "name": "optional_package_name",
        "include_code": true,
        "include_docs": true,
        "include_outputs": true,
        "max_files": 30,
        "extra_paths": ["workspace/algebra/spectral_gap_proof.py"]
    }
    """
    body = await request.json()
    framing = body.get("framing", "")
    if not framing:
        return JSONResponse({"error": "framing is required"}, status_code=400)

    result = export_package(
        framing=framing,
        name=body.get("name", ""),
        include_code=body.get("include_code", True),
        include_docs=body.get("include_docs", True),
        include_outputs=body.get("include_outputs", True),
        max_files=body.get("max_files", 30),
        extra_paths=body.get("extra_paths"),
    )
    return result


@app.get("/exports")
async def get_exports():
    """List existing export packages."""
    return {"exports": list_exports()}


# ---------------------------------------------------------------------------
# Scheduler — run agents on intervals
# ---------------------------------------------------------------------------

_schedules: dict[str, dict] = {}  # agent_type -> {interval_sec, last_run, enabled}
_scheduler_task = None
_infra_task = None
_dispatcher = Dispatcher()

# Track last infrastructure run times
_infra_timers = {
    "health_check": 0.0,
    "index_outputs": 0.0,
    "mechanical_judge": 0.0,
    "spool_drain": 0.0,
}

# Builder agents whose completion should trigger a mechanical judge
_BUILDER_TYPES = {"probe", "guardian", "synthesis"}


async def _scheduler_loop():
    """Background loop that checks schedules and spawns agents."""
    while True:
        await asyncio.sleep(30)  # check every 30 seconds
        now = time.time()
        for agent_type, sched in list(_schedules.items()):
            if not sched["enabled"]:
                continue
            if now - sched["last_run"] >= sched["interval_sec"]:
                # Don't spawn if one is already running
                active = get_active()
                running_types = {p["agent_type"] for p in active}
                if agent_type not in running_types:
                    spawn_headless(agent_type)
                    sched["last_run"] = now


async def _infra_loop():
    """Background infrastructure automation — runs without human intervention."""
    # Wait for server to fully start
    await asyncio.sleep(5)

    # --- Startup tasks (run once) ---
    print("[infra] Running startup tasks...")

    # 1. Index any existing outputs not yet in vector store
    _run_index_outputs()
    print(f"[infra] Indexed outputs: {_output_store.count()} documents in vector store")

    # 2. Drain spool (events that arrived while server was down)
    _drain_spool()

    # --- Recurring loop ---
    while True:
        await asyncio.sleep(60)  # check every minute
        now = time.time()

        # Auto-index new outputs every 2 minutes
        if now - _infra_timers["index_outputs"] >= 120:
            _run_index_outputs()
            _infra_timers["index_outputs"] = now

        # Drain spool every 5 minutes
        if now - _infra_timers["spool_drain"] >= 300:
            _drain_spool()
            _infra_timers["spool_drain"] = now

        # Auto mechanical judge every 30 minutes (only if workspace exists)
        if now - _infra_timers["mechanical_judge"] >= 1800:
            workspace = ROOT / "workspace"
            if workspace.exists() and list(workspace.glob("*.py")):
                _run_mechanical_judge(workspace)
            _infra_timers["mechanical_judge"] = now

        # Check if a builder agent recently completed → trigger mechanical judge
        s = state()
        recent = s.recent(5)
        for rec in recent:
            if (rec.agent_type in _BUILDER_TYPES
                    and rec.status.value in ("completed",)
                    and rec.finished
                    and now - rec.finished < 120):  # completed in last 2 min
                workspace = ROOT / "workspace"
                if workspace.exists():
                    print(f"[infra] Builder {rec.agent_type} completed — running mechanical judge")
                    _run_mechanical_judge(workspace)
                    _infra_timers["mechanical_judge"] = now
                break  # only judge once per cycle


def _run_index_outputs():
    """Index all unindexed agent outputs into vector store with rich metadata."""
    output_dir = ROOT / "data" / "outputs"
    if not output_dir.exists():
        return
    for f in output_dir.glob("*.txt"):
        doc_id = f.stem
        if _output_store.get(doc_id):
            continue
        try:
            text = f.read_text(errors="replace")
            parts = doc_id.rsplit("_", 1)
            agent_type = parts[0] if len(parts) > 1 else "unknown"
            meta = extract_metadata(text, agent_type=agent_type)
            doc = Document(id=doc_id, text=text[:5000], metadata={
                **meta.to_dict(),
                "filename": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
            _output_store.add(doc)
        except Exception:
            pass


def _drain_spool():
    """Process events that were spooled while server was down."""
    import json as _json
    spool_dir = ROOT / "data" / "spool"
    if not spool_dir.exists():
        return
    spool_files = list(spool_dir.glob("*.json"))
    if not spool_files:
        return
    print(f"[infra] Draining {len(spool_files)} spooled events")
    for sf in spool_files:
        try:
            data = _json.loads(sf.read_text())
            emit(data.get("type", "unknown"), data.get("repo", "unknown"), data.get("payload", {}))
            sf.unlink()
        except Exception as e:
            print(f"[infra] Bad spool file {sf.name}: {e}")


def _run_mechanical_judge(workspace: Path):
    """Run mechanical-only judge and save verdict (no LLM, instant)."""
    try:
        from experiments.judge import phase1_mechanical
        result = phase1_mechanical(workspace)
        # Save a lightweight verdict
        verdict = {
            "run_id": "workspace",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mechanical": {
                "py_files": result.py_files,
                "all_code_runs": result.all_code_runs,
                "has_eigenvalues": result.has_eigenvalues,
                "has_numerical_output": result.has_numerical_output,
                "smuggled_constants": len(result.smuggled),
                "artifact_count": result.artifact_count,
            },
            "verdict": "FAIL_CODE" if not result.all_code_runs else "MECHANICAL_ONLY",
        }
        verdict_path = workspace / "verdict.json"
        verdict_path.write_text(json.dumps(verdict, indent=2))

        if not result.all_code_runs:
            # Report broken code to state
            s = state()
            agent_id = f"autojudge_{int(time.time())}"
            s.spawn(agent_id, "judge", "auto-mechanical")
            failed = [f for f, r in result.py_results.items() if not r["runs"]]
            s.complete(agent_id, f"FAIL_CODE: {', '.join(failed)}", "warning")
            print(f"[infra] Mechanical judge: FAIL_CODE — {failed}")
        else:
            print(f"[infra] Mechanical judge: OK ({len(result.py_files)} files pass)")
    except Exception as e:
        print(f"[infra] Mechanical judge error: {e}")


@app.on_event("startup")
async def start_scheduler():
    global _scheduler_task, _infra_task
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    _infra_task = asyncio.create_task(_infra_loop())
    _dispatcher.start()
    print("[infra] Scheduler, dispatcher, and infrastructure automation started")


@app.post("/schedule")
async def set_schedule(request: Request):
    """
    Set a recurring schedule for an agent.
    Body: {agent_type, interval_min, enabled: true/false}
    """
    body = await request.json()
    agent_type = body.get("agent_type")
    interval_min = body.get("interval_min", 10)
    enabled = body.get("enabled", True)

    if agent_type not in AGENTS:
        return JSONResponse(
            {"error": f"Unknown agent type: {agent_type}"},
            status_code=400,
        )

    _schedules[agent_type] = {
        "interval_sec": interval_min * 60,
        "last_run": time.time() if enabled else 0,
        "enabled": enabled,
    }
    return {
        "status": "scheduled" if enabled else "disabled",
        "agent_type": agent_type,
        "interval_min": interval_min,
    }


@app.delete("/schedule/{agent_type}")
async def remove_schedule(agent_type: str):
    """Remove a recurring schedule."""
    _schedules.pop(agent_type, None)
    return {"status": "removed", "agent_type": agent_type}


@app.get("/dispatcher")
async def dispatcher_status():
    """Current dispatcher state — trigger rules, cooldowns, running status."""
    return _dispatcher.status()


@app.get("/schedules")
async def list_schedules():
    """List all active schedules."""
    return {
        agent_type: {
            "interval_min": sched["interval_sec"] / 60,
            "last_run": sched["last_run"],
            "enabled": sched["enabled"],
            "next_run_in": max(0, sched["interval_sec"] - (time.time() - sched["last_run"])),
        }
        for agent_type, sched in _schedules.items()
    }


# ---------------------------------------------------------------------------
# Dashboard — Claude Code session launcher & manager
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """The command center — launch, monitor, and interact with Claude Code agents."""
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
            max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem;
        }

        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        header h1 { font-size: 1.5rem; font-weight: 600; color: #fff; }
        .header-sub { font-size: 0.75rem; color: #555; margin-top: 0.15rem; }
        .pulse { width: 10px; height: 10px; border-radius: 50%; background: #4a4; display: inline-block; animation: pulse 2s infinite; margin-right: 0.5rem; }
        .pulse.idle { background: #555; animation: none; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .header-status { font-size: 0.85rem; color: #888; display: flex; align-items: center; }

        /* Stats row */
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
        .stat-card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 1rem; text-align: center; }
        .stat-card .number { font-size: 1.75rem; font-weight: 700; line-height: 1; }
        .stat-card .label { font-size: 0.7rem; color: #666; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .stat-card.active .number { color: #7af; }
        .stat-card.pending .number { color: #fa0; }
        .stat-card.completed .number { color: #4a4; }
        .stat-card.failed .number { color: #f44; }

        /* Agent tiles */
        section { margin-bottom: 2rem; }
        section h2 { font-size: 0.85rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.75rem; }
        .agent-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 0.75rem; margin-bottom: 2rem; }
        .agent-tile {
            background: #111; border: 1px solid #222; border-radius: 8px; padding: 1rem;
            transition: border-color 0.15s;
        }
        .agent-tile:hover { border-color: #444; }
        .agent-tile .tile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .agent-tile .tile-name { font-weight: 600; font-size: 0.9rem; color: #fff; }
        .agent-tile .tile-desc { font-size: 0.8rem; color: #777; line-height: 1.4; margin-bottom: 0.75rem; }
        .agent-tile .tile-tools { font-size: 0.7rem; color: #555; margin-bottom: 0.75rem; }
        .agent-tile .tile-tools code { background: #1a1a1a; padding: 0.1rem 0.35rem; border-radius: 3px; color: #888; }
        .tile-actions { display: flex; gap: 0.5rem; }

        /* Buttons */
        .btn { background: #1a1a1a; border: 1px solid #333; color: #ddd; padding: 0.4rem 0.85rem; border-radius: 6px; cursor: pointer; font-size: 0.78rem; transition: all 0.15s; }
        .btn:hover { background: #252525; border-color: #555; }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn.primary { border-color: #7af; color: #7af; }
        .btn.primary:hover { background: rgba(119,170,255,0.1); }
        .btn.open { border-color: #4a4; color: #4a4; }
        .btn.open:hover { background: rgba(68,170,68,0.1); }
        .btn.approve { border-color: #4a4; color: #4a4; }
        .btn.approve:hover { background: rgba(68,170,68,0.1); }
        .btn.reject { border-color: #f44; color: #f44; }
        .btn.reject:hover { background: rgba(255,68,68,0.1); }

        /* Cards */
        .card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
        .card.needs-action { border-left: 3px solid #f44; }
        .card.warning { border-left: 3px solid #fa0; }
        .card.info { border-left: 3px solid #4a4; }
        .card.running { border-left: 3px solid #7af; }
        .card .row { display: flex; justify-content: space-between; align-items: center; }
        .card .agent-type { font-weight: 600; font-size: 0.85rem; text-transform: capitalize; }
        .card .status-badge { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 10px; font-weight: 600; }
        .badge-running { background: rgba(119,170,255,0.15); color: #7af; }
        .badge-completed { background: rgba(68,170,68,0.15); color: #4a4; }
        .badge-failed { background: rgba(255,68,68,0.15); color: #f44; }
        .badge-awaiting { background: rgba(255,170,0,0.15); color: #fa0; }
        .card .finding-text { font-size: 0.8rem; color: #aaa; margin-top: 0.5rem; line-height: 1.4; white-space: pre-wrap; word-break: break-word; }
        .card .meta { font-size: 0.7rem; color: #555; margin-top: 0.4rem; }
        .btn-group { display: flex; gap: 0.5rem; margin-top: 0.5rem; }

        /* Custom task input */
        .task-input { display: none; margin-top: 0.5rem; }
        .task-input.visible { display: flex; gap: 0.5rem; }
        .task-input input {
            flex: 1; background: #0d0d0d; border: 1px solid #333; color: #ddd;
            padding: 0.4rem 0.6rem; border-radius: 6px; font-size: 0.8rem; outline: none;
        }
        .task-input input:focus { border-color: #7af; }

        /* Output viewer */
        .output-modal {
            display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85); z-index: 100; padding: 2rem;
        }
        .output-modal.visible { display: flex; flex-direction: column; }
        .output-content {
            flex: 1; background: #111; border: 1px solid #333; border-radius: 8px;
            padding: 1.5rem; overflow: auto; font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 0.8rem; line-height: 1.6; color: #ccc; white-space: pre-wrap;
            max-width: 900px; margin: 0 auto; width: 100%;
        }
        .output-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; max-width: 900px; margin: 0 auto 1rem; width: 100%; }
        .output-header h3 { color: #fff; font-size: 1rem; }

        /* Timeline dots */
        .timeline-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-right: 0.5rem; flex-shrink: 0; margin-top: 0.35rem; }
        .dot-running { background: #7af; }
        .dot-completed { background: #4a4; }
        .dot-failed { background: #f44; }
        .dot-awaiting { background: #fa0; }

        .empty { color: #444; font-size: 0.85rem; padding: 1rem; text-align: center; }

        /* Spinner */
        .spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid #333; border-top-color: #7af; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 0.4rem; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Agentic</h1>
            <div class="header-sub">72-hour build sprint — derive everything from observations</div>
        </div>
        <div class="header-status" id="headerStatus">
            <span class="pulse" id="pulseIndicator"></span>
            <span id="statusText">connecting...</span>
        </div>
    </header>

    <div class="stats" id="stats"></div>

    <section>
        <h2>Launch Agent</h2>
        <div class="agent-grid" id="agentGrid"></div>
    </section>

    <section id="pendingSection" style="display:none">
        <h2>Needs Your Decision</h2>
        <div id="pending"></div>
    </section>

    <section id="verdictsSection" style="display:none">
        <h2>Experiment Verdicts</h2>
        <div id="verdicts"></div>
        <div style="margin-top:0.75rem">
            <button class="btn primary" onclick="runJudge('workspace')">Judge Workspace</button>
            <button class="btn" onclick="runJudge('workspace', true)">Quick Judge (skip LLM)</button>
        </div>
    </section>

    <section id="healthSection">
        <h2>Platform Health</h2>
        <div id="healthPanel" class="empty">Loading...</div>
    </section>

    <section id="knowledgeSection">
        <h2>Knowledge & Search</h2>
        <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem;">
            <input type="text" id="searchInput" placeholder="Search outputs... (text, concept, observation)"
                   style="flex:1;background:#0d0d0d;border:1px solid #333;color:#ddd;padding:0.4rem 0.6rem;border-radius:6px;font-size:0.8rem;outline:none;"
                   onkeydown="if(event.key==='Enter')searchOutputs()">
            <button class="btn primary" onclick="searchOutputs()">Search</button>
        </div>
        <div id="searchResults"></div>
        <div id="knowledgePanel" class="empty">Loading knowledge...</div>
    </section>

    <section id="exportSection">
        <h2>Export Packages</h2>
        <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem;">
            <input type="text" id="exportFraming" placeholder="Framing query... (e.g. 'spectral gap derivation', 'topology work')"
                   style="flex:1;background:#0d0d0d;border:1px solid #333;color:#ddd;padding:0.4rem 0.6rem;border-radius:6px;font-size:0.8rem;outline:none;"
                   onkeydown="if(event.key==='Enter')createExport()">
            <button class="btn primary" onclick="createExport()" id="exportBtn">Export</button>
        </div>
        <div id="exportList"></div>
    </section>

    <section id="dispatcherSection">
        <h2>Event Dispatcher</h2>
        <div id="dispatcherPanel" class="empty">Loading...</div>
    </section>

    <section>
        <h2>Activity</h2>
        <div id="timeline"></div>
    </section>

    <!-- Output viewer modal -->
    <div class="output-modal" id="outputModal">
        <div class="output-header">
            <h3 id="outputTitle">Agent Output</h3>
            <button class="btn" onclick="closeOutput()">Close</button>
        </div>
        <div class="output-content" id="outputContent"></div>
    </div>

    <script>
        let agentConfigs = {};

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
            if (r.status === 'running') return 'running';
            if (r.status === 'awaiting_approval') return 'needs-action';
            if (r.status === 'failed') return 'warning';
            return 'info';
        }

        function statusLabel(status) {
            return status.replace(/_/g, ' ').replace('awaiting approval', 'needs review');
        }

        async function loadAgentTypes() {
            try {
                const res = await fetch('/agents');
                agentConfigs = await res.json();
                renderAgentGrid();
            } catch(e) {
                console.error('Failed to load agent types:', e);
            }
        }

        function renderAgentGrid() {
            const grid = document.getElementById('agentGrid');
            grid.innerHTML = Object.entries(agentConfigs).map(([key, cfg]) => `
                <div class="agent-tile" id="tile-${key}">
                    <div class="tile-header">
                        <span class="tile-name">${cfg.name}</span>
                    </div>
                    <div class="tile-desc">${cfg.description}</div>
                    <div class="tile-tools">
                        Tools: ${cfg.allowed_tools.map(t => '<code>' + t + '</code>').join(' ')}
                        &middot; ${cfg.permission_mode}
                    </div>
                    <div class="tile-actions">
                        <button class="btn primary" onclick="launchHeadless('${key}')" id="btn-run-${key}">
                            Run Headless
                        </button>
                        <button class="btn open" onclick="launchInteractive('${key}')">
                            Open Terminal
                        </button>
                        <button class="btn" onclick="toggleTaskInput('${key}')">
                            Custom Task
                        </button>
                    </div>
                    <div class="task-input" id="task-${key}">
                        <input type="text" placeholder="Describe the task..." id="task-input-${key}"
                               onkeydown="if(event.key==='Enter')launchWithTask('${key}')">
                        <button class="btn primary" onclick="launchWithTask('${key}')">Go</button>
                    </div>
                </div>
            `).join('');
        }

        function toggleTaskInput(type) {
            const el = document.getElementById('task-' + type);
            el.classList.toggle('visible');
            if (el.classList.contains('visible')) {
                document.getElementById('task-input-' + type).focus();
            }
        }

        async function launchHeadless(type) {
            const btn = document.getElementById('btn-run-' + type);
            btn.innerHTML = '<span class="spinner"></span>Launching...';
            btn.disabled = true;

            await fetch('/spawn', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ agent_type: type, mode: 'headless' })
            });

            setTimeout(() => {
                btn.innerHTML = 'Run Headless';
                btn.disabled = false;
                refresh();
            }, 2000);
        }

        async function launchInteractive(type) {
            const btn = event.target;
            btn.innerHTML = '<span class="spinner"></span>Opening...';
            btn.disabled = true;

            const res = await fetch('/spawn', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ agent_type: type, mode: 'interactive' })
            });
            const data = await res.json();

            setTimeout(() => {
                btn.innerHTML = 'Open Terminal';
                btn.disabled = false;
            }, 2000);
        }

        async function launchWithTask(type) {
            const input = document.getElementById('task-input-' + type);
            const task = input.value.trim();
            if (!task) return;

            const btn = document.getElementById('btn-run-' + type);
            btn.innerHTML = '<span class="spinner"></span>Launching...';
            btn.disabled = true;

            await fetch('/spawn', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ agent_type: type, mode: 'headless', task: task })
            });

            input.value = '';
            document.getElementById('task-' + type).classList.remove('visible');

            setTimeout(() => {
                btn.innerHTML = 'Run Headless';
                btn.disabled = false;
                refresh();
            }, 2000);
        }

        async function viewOutput(agentId) {
            try {
                const res = await fetch('/output/' + agentId);
                const data = await res.json();
                document.getElementById('outputTitle').textContent = agentId;
                document.getElementById('outputContent').textContent = data.output || 'No output available';
                document.getElementById('outputModal').classList.add('visible');
            } catch(e) {
                console.error('Failed to load output:', e);
            }
        }

        function closeOutput() {
            document.getElementById('outputModal').classList.remove('visible');
        }

        // Close modal on Escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeOutput();
        });

        async function decide(agentId, decision) {
            await fetch('/decide/' + agentId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({decision})
            });
            refresh();
        }

        async function refresh() {
            try {
                const [statusRes, recentRes] = await Promise.all([
                    fetch('/status'), fetch('/recent')
                ]);
                const data = await statusRes.json();
                const recent = await recentRes.json();
                const d = data.digest;

                // Header
                const activeCount = (data.active_processes || []).length;
                document.getElementById('pulseIndicator').className = activeCount > 0 ? 'pulse' : 'pulse idle';
                document.getElementById('statusText').textContent = activeCount > 0
                    ? activeCount + ' agent(s) running'
                    : 'idle';

                // Stats
                document.getElementById('stats').innerHTML = `
                    <div class="stat-card active"><div class="number">${d.active}</div><div class="label">Active</div></div>
                    <div class="stat-card pending"><div class="number">${d.pending_review}</div><div class="label">Pending</div></div>
                    <div class="stat-card completed"><div class="number">${d.completed_today}</div><div class="label">Completed</div></div>
                    <div class="stat-card failed"><div class="number">${d.failed_today}</div><div class="label">Failed</div></div>
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
                                <button class="btn" onclick="viewOutput('${r.id}')">View Output</button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    pendingSection.style.display = 'none';
                }

                // Timeline
                const timelineEl = document.getElementById('timeline');
                if (recent.length === 0) {
                    timelineEl.innerHTML = '<div class="empty">No activity yet. Launch an agent above to get started.</div>';
                } else {
                    timelineEl.innerHTML = recent.map(r => `
                        <div class="card ${cardClass(r)}">
                            <div class="row">
                                <div style="display:flex; align-items:flex-start;">
                                    <span class="timeline-dot ${dotClass(r.status)}"></span>
                                    <div>
                                        <span class="agent-type">${r.type}</span>
                                        <div class="finding-text">${escapeHtml(r.finding)}</div>
                                        <div class="meta">${ago(r.started)}${r.finished ? ' &middot; took ' + Math.round(r.finished - r.started) + 's' : ''}</div>
                                    </div>
                                </div>
                                <div style="display:flex; gap:0.5rem; align-items:center;">
                                    ${r.status === 'completed' || r.status === 'failed' ? '<button class="btn" onclick="viewOutput(\\''+r.id+'\\')">View</button>' : ''}
                                    <span class="status-badge ${badgeClass(r.status)}">${statusLabel(r.status)}</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                }
            } catch(e) {
                document.getElementById('statusText').textContent = 'disconnected';
                document.getElementById('pulseIndicator').className = 'pulse idle';
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;');
        }

        // --- Verdicts ---
        async function loadVerdicts() {
            try {
                const res = await fetch('/verdicts');
                const verdicts = await res.json();
                const section = document.getElementById('verdictsSection');
                const el = document.getElementById('verdicts');
                if (verdicts.length === 0) { section.style.display = 'none'; return; }
                section.style.display = 'block';
                el.innerHTML = verdicts.map(v => {
                    const color = v.verdict === 'STRONG_PASS' ? '#4a4' : v.verdict === 'PASS' ? '#7af' : v.verdict === 'PARTIAL' ? '#fa0' : '#f44';
                    const sm = v.summary || {};
                    return `<div class="card" style="border-left:3px solid ${color}">
                        <div class="row"><span class="agent-type">${escapeHtml(v.run_id)}</span>
                        <span class="status-badge" style="background:${color}22;color:${color}">${v.verdict}</span></div>
                        ${sm.present !== undefined ? '<div class="meta" style="margin-top:0.4rem">Present: '+sm.present+'/'+sm.total+' | Partial: '+sm.partial+' | Absent: '+sm.absent+'</div>' : ''}
                        <div class="meta">${v.timestamp}</div></div>`;
                }).join('');
            } catch(e) {}
        }

        async function runJudge(dir, skipLlm) {
            const btn = event.target;
            btn.innerHTML = '<span class="spinner"></span>Judging...';
            btn.disabled = true;
            try {
                const res = await fetch('/judge', { method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({run_dir: dir, skip_llm: !!skipLlm}) });
                const data = await res.json();
                if (data.verdict) alert('Verdict: ' + data.verdict);
                else if (data.error) alert('Error: ' + data.error);
                loadVerdicts(); refresh();
            } catch(e) { alert('Judge failed: ' + e); }
            btn.innerHTML = skipLlm ? 'Quick Judge (skip LLM)' : 'Judge Workspace';
            btn.disabled = false;
        }

        // --- Health ---
        async function loadHealth() {
            try {
                const res = await fetch('/health');
                const h = await res.json();
                const el = document.getElementById('healthPanel');
                const overall = h.overall === 'healthy'
                    ? '<span style="color:#4a4;font-weight:600">HEALTHY</span>'
                    : '<span style="color:#fa0;font-weight:600">DEGRADED</span>';
                let html = '<div class="card"><div class="row"><span class="agent-type">Overall</span>'+overall+'</div></div>';
                if (h.repos) {
                    html += '<div style="margin-top:0.5rem;font-size:0.8rem;color:#888">Connected Repos</div>';
                    for (const [name, info] of Object.entries(h.repos)) {
                        const color = info.exists ? (info.hook_installed ? '#4a4' : '#fa0') : '#f44';
                        const icon = info.exists ? (info.hook_installed ? '&#9679;' : '&#9675;') : '&#10007;';
                        html += '<div class="card" style="padding:0.6rem 1rem"><span style="color:'+color+';margin-right:0.5rem">'+icon+'</span><strong>'+name+'</strong>';
                        html += info.exists ? (info.clean ? ' &middot; clean' : ' &middot; '+info.uncommitted_changes+' changes') : ' &middot; NOT FOUND';
                        html += info.hook_installed ? ' &middot; hooked' : (info.exists ? ' &middot; <em>no hook</em>' : '');
                        html += '</div>';
                    }
                }
                if (h.workspace && h.workspace.py_files > 0) {
                    html += '<div style="margin-top:0.5rem;font-size:0.8rem;color:#888">Workspace ('+h.workspace.py_files+' files)</div>';
                    for (const [file, result] of Object.entries(h.workspace.results)) {
                        const ok = result === 'ok';
                        html += '<div style="font-size:0.8rem;padding:0.2rem 0;color:'+(ok?'#4a4':'#f44')+'">'+(ok?'&#10003;':'&#10007;')+' '+file+(ok?'':' — '+result)+'</div>';
                    }
                }
                if (h.disk) html += '<div style="margin-top:0.5rem;font-size:0.75rem;color:#555">Data: '+h.disk.data_dir_mb+'MB &middot; '+h.disk.output_files+' outputs &middot; '+h.disk.state_files+' state files</div>';
                el.innerHTML = html;
            } catch(e) { document.getElementById('healthPanel').innerHTML = '<div class="empty">Health check failed</div>'; }
        }

        // --- Knowledge & Search ---
        async function loadKnowledge() {
            try {
                const res = await fetch('/knowledge');
                const k = await res.json();
                const el = document.getElementById('knowledgePanel');
                if (k.documents === 0) { el.innerHTML = '<div class="empty">No indexed outputs yet. Run agents to populate.</div>'; return; }
                let html = '<div class="card"><div class="row"><span class="agent-type">Indexed Documents</span><span style="color:#7af;font-weight:600">'+k.documents+'</span></div></div>';
                const tags = k.tags || {};
                for (const [category, items] of Object.entries(tags)) {
                    if (!items || Object.keys(items).length === 0) continue;
                    html += '<div style="margin-top:0.5rem;font-size:0.75rem;color:#888;text-transform:uppercase">'+category+'</div>';
                    const sorted = Object.entries(items).sort((a,b) => b[1]-a[1]).slice(0,12);
                    html += '<div style="display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.25rem">';
                    for (const [tag, count] of sorted) {
                        html += '<span style="background:#1a1a1a;border:1px solid #333;padding:0.15rem 0.5rem;border-radius:10px;font-size:0.7rem;color:#aaa">'+escapeHtml(tag)+' <span style="color:#666">'+count+'</span></span>';
                    }
                    html += '</div>';
                }
                el.innerHTML = html;
            } catch(e) { document.getElementById('knowledgePanel').innerHTML = '<div class="empty">Knowledge unavailable</div>'; }
        }

        async function searchOutputs() {
            const q = document.getElementById('searchInput').value.trim();
            if (!q) return;
            const el = document.getElementById('searchResults');
            el.innerHTML = '<div class="empty"><span class="spinner"></span>Searching...</div>';
            try {
                const res = await fetch('/search-outputs?q=' + encodeURIComponent(q));
                const results = await res.json();
                if (!results.length) { el.innerHTML = '<div class="empty">No results for "'+escapeHtml(q)+'"</div>'; return; }
                el.innerHTML = results.map(r => {
                    const tags = (r.tags || []).slice(0,5).map(t => '<span style="background:#1a1a1a;border:1px solid #333;padding:0.1rem 0.4rem;border-radius:8px;font-size:0.65rem;color:#888">'+escapeHtml(t)+'</span>').join(' ');
                    const preview = escapeHtml((r.text || '').slice(0,200));
                    return '<div class="card info" style="cursor:pointer" onclick="viewOutput(\\''+escapeHtml(r.id || '')+'\\')"><div class="row"><span class="agent-type">'+(r.agent_type||'unknown')+'</span>'+tags+'</div><div class="finding-text" style="font-size:0.75rem;max-height:3rem;overflow:hidden">'+preview+'</div></div>';
                }).join('');
            } catch(e) { el.innerHTML = '<div class="empty">Search failed</div>'; }
        }

        // --- Exports ---
        async function createExport() {
            const framing = document.getElementById('exportFraming').value.trim();
            if (!framing) return;
            const btn = document.getElementById('exportBtn');
            btn.innerHTML = '<span class="spinner"></span>Building...';
            btn.disabled = true;
            try {
                const res = await fetch('/export', { method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({framing}) });
                const data = await res.json();
                if (data.status === 'ok') {
                    document.getElementById('exportFraming').value = '';
                    loadExports();
                } else { alert('Export failed: ' + (data.error || 'unknown')); }
            } catch(e) { alert('Export error: ' + e); }
            btn.innerHTML = 'Export'; btn.disabled = false;
        }

        async function loadExports() {
            try {
                const res = await fetch('/exports');
                const data = await res.json();
                const el = document.getElementById('exportList');
                const exports = data.exports || [];
                if (exports.length === 0) { el.innerHTML = '<div class="empty">No exports yet. Enter a framing query above to build one.</div>'; return; }
                el.innerHTML = exports.map(e => `
                    <div class="card info">
                        <div class="row">
                            <span class="agent-type">${escapeHtml(e.name || '')}</span>
                            <span style="font-size:0.7rem;color:#666">${e.file_count || 0} files</span>
                        </div>
                        <div class="finding-text" style="font-size:0.75rem">${escapeHtml(e.framing || '')}</div>
                        <div class="meta">${escapeHtml(e.created || '')}</div>
                    </div>
                `).join('');
            } catch(e) { document.getElementById('exportList').innerHTML = '<div class="empty">Exports unavailable</div>'; }
        }

        // --- Dispatcher ---
        async function loadDispatcher() {
            try {
                const res = await fetch('/dispatcher');
                const d = await res.json();
                const el = document.getElementById('dispatcherPanel');
                let html = '<div class="card"><div class="row"><span class="agent-type">Status</span><span style="color:'+(d.running?'#4a4':'#f44')+';font-weight:600">'+(d.running?'RUNNING':'STOPPED')+'</span></div></div>';
                const rules = d.trigger_rules || {};
                if (Object.keys(rules).length > 0) {
                    html += '<div style="margin-top:0.5rem;font-size:0.75rem;color:#888;text-transform:uppercase">Trigger Rules</div>';
                    for (const [event, agents] of Object.entries(rules)) {
                        html += '<div style="font-size:0.8rem;padding:0.15rem 0"><span style="color:#7af">'+event+'</span> &rarr; '+agents.join(', ')+'</div>';
                    }
                }
                const cooldowns = d.cooldowns || {};
                if (Object.keys(cooldowns).length > 0) {
                    html += '<div style="margin-top:0.5rem;font-size:0.75rem;color:#888;text-transform:uppercase">Active Cooldowns</div>';
                    for (const [agent, secs] of Object.entries(cooldowns)) {
                        html += '<div style="font-size:0.8rem;padding:0.15rem 0"><span style="color:#fa0">'+agent+'</span> — '+secs+'s remaining</div>';
                    }
                }
                el.innerHTML = html;
            } catch(e) { document.getElementById('dispatcherPanel').innerHTML = '<div class="empty">Dispatcher unavailable</div>'; }
        }

        // Initialize
        loadAgentTypes();
        refresh();
        loadVerdicts();
        loadHealth();
        loadKnowledge();
        loadExports();
        loadDispatcher();
        setInterval(refresh, 3000);
        setInterval(loadHealth, 30000);
        setInterval(loadKnowledge, 30000);
        setInterval(loadDispatcher, 10000);
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

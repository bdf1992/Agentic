# CLAUDE.md — Agentic Platform

This platform spawns and manages Claude Code CLI sessions, each configured for a specific role.
Every agent is a real Claude Code instance running on the user's Claude Max subscription — not an API call, not a toy. Each gets a system prompt, allowed tools, working directory, and permission mode.

## What This Actually Is

A **FastAPI dashboard** (port 8750) that:
- Launches Claude Code sessions (headless or interactive terminal)
- Configures each with role-specific system prompts and tool access
- Tracks active/completed runs and stores outputs
- Schedules recurring agent runs via server-side scheduler

**Implemented infrastructure:**
- Experiment judge (2-phase: mechanical + LLM adversarial scoring, 17 properties)
- Vector store with rich metadata (auto-tags: agent_type, role, observations O0-O8, 17 properties, concepts, files touched)
- Metadata extractor (auto-extracts structured tags from agent output text on every run)
- Filtered search API (search by agent_type, role, concept, observation, property, text)
- Semantic search with TF-IDF embeddings (256-dim: 64 domain concepts + 64 obs/properties + 128 trigram hashes)
- Knowledge summary endpoint (`/knowledge` — aggregate tag counts, what the platform knows)
- Event dispatcher (event → agent routing with trigger rules and cooldown system)
- Export tool (build portable review packages from workspace + RAG by framing query)
- CI/CD workflows (on-push validation, nightly maintenance, judge workflow, morning digest)
- Hook installer (batch install/uninstall across connected repos)
- Health checks (cross-repo validation, import checking, workspace code execution)
- Infrastructure automation (auto-index, spool drain, mechanical judge — all on server startup)
- 14 MCP tools for agent self-service (status, judge, search, semantic search, knowledge, spawn, export, etc.)

**Not implemented** (don't pretend these exist):
- Agent-to-agent direct communication channel

## Agent-Human Precedence

### The Human is the Architect

The human defines intent, meaning, direction, and approval gates.
Agents propose, they do not decree. When ambiguous, surface both options.

### Precedence Order

```
Human intent  >  CLAUDE.md rules  >  Agent judgment  >  Automation defaults
```

### What Agents May Do Without Asking

- Run tests, linters, validation suites
- Read files, search code, explore repos
- Generate reports and status summaries
- Create new files in their designated workspace
- Write code, build features, run experiments

### What Agents Must Ask Before Doing

- Pushing to any remote repository
- Deleting files or branches
- Creating or closing GitHub issues/PRs
- Modifying CLAUDE.md or agent configs
- Any irreversible action

**Key shift**: agents are not just watchers. They BUILD. A guardian doesn't just report a regression — it investigates root cause and proposes a fix. A probe agent doesn't just read a seed — it writes code, runs experiments, iterates. The orchestrator doesn't just schedule health checks — it assesses what the project NEEDS and launches agents to do that work.

## Architecture

```
Dashboard (http://localhost:8750)
├── Agent grid — launch any agent headless or interactive
├── Activity timeline — see what ran, what's running
├── Output viewer — read completed agent results
├── Verdict panel — experiment judge results with scores
├── Health panel — repo status, workspace validation, disk usage
├── Knowledge & Search — search outputs, browse indexed tags
├── Export panel — build portable review packages by framing query
├── Dispatcher panel — trigger rules, cooldowns, event routing status
├── Scheduler — recurring agent runs (server-side asyncio)
└── Status API — JSON endpoints for orchestrator decisions

Spawner (agents/spawner.py)
├── Interactive: opens Windows Terminal with configured claude session
├── Headless: runs claude -p in background, captures output
└── Auto-indexes output into vector store on completion

Infrastructure Automation (runs on server startup, no manual intervention)
├── Auto-index: indexes agent outputs into vector store every 2 min
├── Spool drain: processes offline events every 5 min
├── Mechanical judge: validates workspace code every 30 min
├── Post-builder judge: auto-judges workspace when probe/guardian/synthesis completes
└── Startup: indexes all existing outputs + drains spool on boot

Export Tool (core/export.py)
├── RAG-driven: searches vector store + workspace files by keyword relevance
├── Flat output: copies code, docs, agent outputs into data/exports/<name>/
├── Synthesis doc: auto-generates SYNTHESIS.md + MANIFEST.json
└── Available as API (POST /export), MCP tool (agentic_export), and direct import

Configs (agents/configs.py)
└── 8 agent types, each with system_prompt, startup_message, tools, cwd, permissions
```

### How Agents Launch

**Interactive** (opens a terminal window):
1. System prompt + startup message written to temp file
2. PowerShell launcher reads file, passes to `claude --system-prompt`
3. Windows Terminal opens with configured working directory
4. Human types "go" and agent executes startup instructions

**Headless** (background, captured output):
1. Combined prompt passed to `claude -p --model opus`
2. Runs in background thread
3. Output stored in `data/outputs/{agent_id}.txt`
4. Dashboard shows results when complete

### Connected Repository

| Repo | Path | Role |
|------|------|------|
| Agentic | This directory | Platform itself |

## Agent Types

### Builders (these CREATE things)

| Agent | What It Does |
|-------|-------------|
| **Probe** | Runs experiments — writes code, tests hypotheses, produces artifacts |
| **Synthesis** | Finds cross-repo patterns, writes synthesis documents, proposes connections |
| **Docs** | Updates documentation to match code reality — edits files directly |

### Operators (these MAINTAIN things)

| Agent | What It Does |
|-------|-------------|
| **Guardian** | Runs golden tests, classifies failures, investigates root causes |
| **Maintenance** | Finds dead code, broken imports, hardcoded constants — reports what to clean |
| **Infrastructure** | Checks platform health — disk, imports, hooks, capacity |
| **GitHub** | Reviews commits, flags danger patterns, tracks repo health |

### Coordinator

| Agent | What It Does |
|-------|-------------|
| **Orchestrator** | Assesses project state, decides which agents to launch, reviews results |

## Orchestrator Decision Logic

The orchestrator runs every 10 minutes. Its job is NOT just health monitoring. It should:

1. **Assess what the project needs RIGHT NOW** — new code? tests? cleanup? experiments?
2. **Check what recently completed** — read outputs, learn from findings
3. **Launch the agent that moves the project forward most** — not just the safest one
4. **Prioritize building over monitoring** — if nothing is broken, build something

### Decision Framework

```
IF recent commits changed structural code → Guardian (verify nothing broke)
IF Guardian passed and no active builders → Probe or Synthesis (advance the project)
IF experiments completed → Synthesis (find patterns across results)
IF docs drifted from code → Docs (fix the drift)
IF nothing specific needed → Probe (explore, discover, create)
FALLBACK: Infrastructure or Maintenance (health check)
```

The bias is toward CREATION, not surveillance. Monitoring is what you do when everything else is done.

## Commands

```bash
# Start the platform
python -m core.server
# → Dashboard at http://localhost:8750

# API endpoints — Core
GET  /status              — platform health + active agents
GET  /agents              — list all agent types
POST /spawn               — launch an agent {"agent_type": "guardian", "mode": "headless"}
GET  /outputs             — list completed runs
GET  /output/{agent_id}   — read a specific output
POST /schedule            — set recurring schedule {"agent_type": "orchestrator", "interval_min": 10}
GET  /schedules           — list active schedules
DELETE /schedule/{type}   — remove a schedule

# API endpoints — Infrastructure
GET  /health              — deep health check (repos, imports, workspace, disk)
GET  /repos               — connected repos with last commit info
POST /judge               — run experiment judge {"run_dir": "workspace", "skip_llm": false}
GET  /verdicts            — list all verdict.json files with scores
POST /index-outputs       — index agent outputs into vector store
GET  /search-outputs?q=   — text search across agent outputs
GET  /semantic-search?q=  — cosine similarity search using TF-IDF embeddings
GET  /knowledge           — aggregate tag counts (concepts, observations, properties)
GET  /dispatcher          — event dispatcher status, trigger rules, cooldowns
POST /export              — build export package {"framing": "spectral gap derivation"}
GET  /exports             — list existing export packages

# Hook management
python hooks/install.py              # install hooks in all connected repos
python hooks/install.py --list       # show hook status
python hooks/install.py --uninstall  # remove hooks from all repos

# Experiment judge
python experiments/judge.py workspace/              # full judge (mechanical + LLM)
python experiments/judge.py workspace/ --skip-llm   # mechanical only (fast)
```

## MCP Tools (available to all agents)

| Tool | What It Does |
|------|-------------|
| `agentic_status` | Query platform status |
| `agentic_digest` | Human-readable activity summary |
| `agentic_report` | Report findings back to platform |
| `agentic_read_output` | Read another agent's output |
| `agentic_list_outputs` | List recent agent runs |
| `agentic_spawn` | Spawn another agent |
| `agentic_decide` | Approve/reject a pending finding |
| `agentic_judge` | Run experiment judge against a directory |
| `agentic_health` | Deep health check (repos, imports, workspace) |
| `agentic_search` | Search outputs by text + metadata (agent_type, role, concept, observation, property) |
| `agentic_semantic_search` | Cosine similarity search using TF-IDF embeddings — finds related content even with different wording |
| `agentic_knowledge` | Tag summary — what concepts, observations, properties the platform has indexed |
| `agentic_export` | Build a portable export package from internal knowledge, driven by a framing query |
| `agentic_list_exports` | List all existing export packages |

## Directory Structure

```
Agentic/
├── core/
│   ├── server.py        — FastAPI server, dashboard, scheduler, judge/health/search endpoints
│   ├── state.py         — thread-safe agent record tracking, persistence
│   ├── vector_store.py  — numpy-backed vector store, filtered search by tags, auto-indexing
│   ├── metadata.py      — auto-extracts tags from agent outputs (observations, properties, concepts, files)
│   ├── embeddings.py    — TF-IDF embeddings (256-dim) for semantic search, no external APIs
│   ├── event_queue.py   — event emission, queuing, persistence
│   ├── dispatcher.py    — event → agent routing (trigger rules, cooldowns, spool consumption)
│   └── export.py        — build portable review packages (search, gather, synthesize)
├── agents/
│   ├── configs.py       — 8 agent type definitions (prompts, tools, settings)
│   └── spawner.py       — spawn_interactive() and spawn_headless(), auto-indexes outputs
├── claude/
│   └── mcp_bridge.py    — 13 MCP tools for agent self-service (stdio server)
├── data/
│   ├── outputs/         — headless agent output files
│   ├── state/           — agent records (JSON)
│   ├── vectors/         — vector store persistence
│   ├── exports/         — portable review packages
│   ├── prompts/         — generated system prompt files
│   ├── launchers/       — generated PowerShell launcher scripts
│   ├── events/          — event log
│   └── spool/           — offline event queue
├── experiments/
│   ├── judge.py         — 2-phase evaluation (mechanical + LLM, 17 properties)
│   ├── seeds/           — experiment seed packets
│   └── runs/            — experiment results (isolated per run, with verdict.json)
├── hooks/
│   ├── post_commit.py   — event emission hook for connected repos
│   └── install.py       — batch install/uninstall/status across repos
├── .github/workflows/
│   ├── on_push.yml      — validate imports, run workspace code, mechanical judge
│   ├── nightly.yml      — maintenance sweep, syntax check, judge
│   ├── digest.yml       — morning digest with workspace + verdict status
│   └── judge.yml        — manual trigger: full experiment judge
└── workspace/           — the build workspace (agents create here)
```

# Agentic

> Agents derive a complete mathematical system from 9 seed observations alone — no constants given, no structures assumed.

## What This Is

A platform that spawns and manages **Claude Code CLI sessions** as specialized agents.
Each agent is a real Claude Code instance (Opus, via Claude Max subscription) with a
system prompt, tool access, and working directory.

The mission: **given only 9 seed observations about distinction, build a working
mathematical system that satisfies 18 required properties.** No constants are given —
everything must be derived. No code is provided — everything must be written.

**Result: ALL 18 PROPERTIES SATISFIED.** 44 Python modules, 110+ mathematical artifacts,
spectral gap 2/3 verified across all systems.

## Quick Start

```bash
pip install fastapi uvicorn requests numpy

# Start the platform
python -m core.server
# → Dashboard at http://localhost:8750

# Schedule the orchestrator (every 10 min)
curl -X POST http://localhost:8750/schedule \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "orchestrator", "interval_min": 10}'
```

## Agent Roles

### Builders
| Agent | Job |
|-------|-----|
| **Probe** | Primary builder — derives algebra from seed observations, writes code |
| **Synthesis** | Finds connections across derivations, unifies structures |
| **Docs** | Documents the emerging system: derivation chain, property scorecard |

### Operators
| Agent | Job |
|-------|-----|
| **Guardian** | Validates work against 18 properties, fixes bugs and gaps |
| **Infra** | Keeps workspace buildable — imports, test harness, shared utilities |
| **Maintenance** | Cleans duplicates, resolves inconsistencies across files |
| **GitHub** | Commits progress, tracks property count over time |

### Coordinator
| Agent | Job |
|-------|-----|
| **Orchestrator** | Decides which agent to run next. Bias: BUILD > VALIDATE > CONNECT > CLEAN |

## The Rules

Agents get:
- **9 seed observations** (`experiments/seeds/cartography_v1.json`)
- **18 required properties** (listed in `CLAUDE.md`)
- Standard mathematics (group theory, topology, spectral theory)

Agents cannot use:
- Constants (3, 7, 8, 13, 28) unless derived
- Named structures (PPT, Berggren, MetaByte, Hamming)
- Code or architecture from system3
- The function f(n) = 2n + 1 or n₀ = 2

## The Judge

```bash
# Full evaluation (mechanical + LLM adversarial scoring)
python experiments/judge.py workspace/

# Quick check (mechanical only, no LLM)
python experiments/judge.py workspace/ --skip-llm

# Via API
curl -X POST http://localhost:8750/judge \
  -H "Content-Type: application/json" \
  -d '{"run_dir": "workspace"}'
```

Phase 1 (mechanical): Does code run? Smuggled constants? Eigenvalues present?
Phase 2 (LLM): Adversarial property scoring — prosecutor, not cheerleader.

## Infrastructure

Beyond spawning agents, the platform ships with:

- **Vector store** — numpy-backed, auto-indexes every agent output; rich metadata tags (agent type, role, 9 observations, 18 properties, concepts, files touched)
- **Semantic search** — TF-IDF embeddings (256-dim: domain concepts + trigram hashes), cosine similarity, no external APIs
- **Metadata extractor** — auto-extracts structured tags from agent output text on every run
- **Event dispatcher** — event → agent routing with trigger rules and cooldown system; offline spool for events that arrive when platform is down
- **Export tool** — RAG-driven: build portable review packages from workspace + agent outputs by framing query
- **Agent-to-agent messaging** — send/read messages between agent types with priority and read tracking
- **16 MCP tools** — agents can query platform status, search outputs, spawn other agents, send messages, run the judge, and more — without leaving their session
- **Infrastructure automation** — on startup: index all existing outputs, drain spool; recurring: auto-index every 2 min, spool drain every 5 min, mechanical judge every 30 min
- **CI/CD workflows** — on-push validation, nightly maintenance, morning digest, manual judge trigger

## Directory Structure

```
Agentic/
├── core/
│   ├── server.py        — FastAPI server, dashboard, all API endpoints
│   ├── state.py         — thread-safe agent record tracking
│   ├── vector_store.py  — filtered search by tags, auto-indexing
│   ├── metadata.py      — auto-extracts tags from agent outputs
│   ├── embeddings.py    — TF-IDF semantic search, no external APIs
│   ├── event_queue.py   — event emission, queuing, persistence
│   ├── dispatcher.py    — event → agent routing (trigger rules, cooldowns)
│   └── export.py        — build portable review packages
├── agents/
│   ├── configs.py        — 8 agent configs (prompts, tools, permissions)
│   └── spawner.py        — spawn_interactive() and spawn_headless()
├── claude/
│   └── mcp_bridge.py    — 16 MCP tools for agent self-service (stdio server)
├── experiments/
│   ├── seeds/            — seed observations (the starting material)
│   ├── runs/             — completed experiment derivations
│   └── judge.py          — 2-phase evaluation (mechanical + LLM)
├── hooks/
│   ├── post_commit.py    — event emission hook for connected repos
│   └── install.py        — batch install/uninstall/status
├── .github/workflows/    — CI/CD (on_push, nightly, digest, judge)
├── workspace/            — WHERE AGENTS BUILD (their codebase)
└── data/
    ├── outputs/          — headless agent output files
    ├── state/            — agent records (JSON)
    ├── vectors/          — vector store persistence
    ├── exports/          — portable review packages
    ├── messages/         — agent-to-agent messages
    ├── events/           — event log
    ├── spool/            — offline event queue
    ├── prompts/          — generated system prompt files
    └── launchers/        — generated PowerShell launcher scripts
```

## API

### Core
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Dashboard |
| GET | `/status` | Platform health + active agents |
| GET | `/agents` | List agent types |
| POST | `/spawn` | Launch agent `{agent_type, mode, task}` |
| GET | `/outputs` | List completed runs |
| GET | `/output/{id}` | Read specific output |
| POST | `/schedule` | Set recurring schedule `{agent_type, interval_min}` |
| GET | `/schedules` | List active schedules |
| DELETE | `/schedule/{type}` | Remove a schedule |

### Infrastructure
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/judge` | Run judge `{run_dir, skip_llm}` |
| GET | `/verdicts` | List all verdict.json files with scores |
| GET | `/health` | Deep health check (repos, imports, disk, workspace) |
| GET | `/repos` | Connected repos with last commit info |
| POST | `/index-outputs` | Index agent outputs into vector store |
| GET | `/search-outputs?q=` | Text search across agent outputs |
| GET | `/semantic-search?q=` | Cosine similarity search (TF-IDF) |
| GET | `/knowledge` | Aggregate tag counts — what the platform knows |
| GET | `/dispatcher` | Event dispatcher status, trigger rules, cooldowns |
| POST | `/export` | Build export package `{framing}` |
| GET | `/exports` | List existing export packages |
| POST | `/message` | Send agent-to-agent message |
| GET | `/messages` | Read messages (filter by recipient, unread) |
| POST | `/message/{id}/read` | Mark message as read |

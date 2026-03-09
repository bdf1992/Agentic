# Agentic

> 72-hour build sprint: agents derive a mathematical system from observations alone.

## What This Is

A platform that spawns and manages **Claude Code CLI sessions** as specialized agents.
Each agent is a real Claude Code instance (Opus, via Claude Max subscription) with a
system prompt, tool access, and working directory.

The mission: **given only 9 seed observations about distinction, build a working
mathematical system that satisfies 17 required properties.** No constants are given —
everything must be derived. No code is provided — everything must be written.

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
| **Guardian** | Validates work against 17 properties, fixes bugs and gaps |
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
- **17 required properties** (listed in `CLAUDE.md`)
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

## Directory Structure

```
Agentic/
├── core/server.py       — FastAPI server, dashboard, scheduler
├── agents/
│   ├── configs.py        — 8 agent configs (prompts, tools, permissions)
│   └── spawner.py        — spawn_interactive() and spawn_headless()
├── experiments/
│   ├── seeds/            — seed observations (the starting material)
│   ├── runs/             — completed experiment derivations
│   └── judge.py          — 2-phase evaluation (mechanical + LLM)
├── workspace/            — WHERE AGENTS BUILD (their codebase)
└── data/
    ├── outputs/          — headless agent output files
    ├── prompts/          — generated system prompt files
    └── launchers/        — generated PowerShell launcher scripts
```

## API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Dashboard |
| GET | `/status` | Platform health + active agents |
| GET | `/agents` | List agent types |
| POST | `/spawn` | Launch agent `{agent_type, mode, task}` |
| GET | `/outputs` | List completed runs |
| GET | `/output/{id}` | Read specific output |
| POST | `/judge` | Run judge `{run_dir, skip_llm}` |
| GET | `/verdicts` | List all verdict.json files |
| GET | `/health` | Deep health check (repos, imports, disk, workspace) |
| POST | `/schedule` | Set recurring schedule `{agent_type, interval_min}` |
| GET | `/schedules` | List active schedules |

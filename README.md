# Agentic

> A nervous system for research and development — not a tool, an operator.

Agentic is a persistent, event-driven platform that manages, guards, and orchestrates work across the Rift Realms project ecosystem. It bridges Claude Code (the hands) with a standalone Python service (the heartbeat), creating a dual OS where agents autonomously maintain, test, and explore while a human architect steers.

---

## Architecture

```
Claude Code (micro-backend)          Agentic Service (heartbeat)
├── Skills, memory, slash commands   ├── FastAPI server (port 8750)
├── Git hooks → emit file events     ├── Vector store (persistent memory)
├── Agent browser → interact w/ UI   ├── Event queue (hook consumer)
├── CLI → spawn/manage agents        ├── Agent loop (spawn, monitor, digest)
│                                    └── State manager (tracks everything)
└────────── API + file bridge ───────┘
```

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn requests numpy

# Start the platform
python core/server.py
# → Dashboard at http://localhost:8750

# Check status (no server needed)
python core/server.py --status

# Install hooks in a connected repo
python hooks/install.py /path/to/your/repo
```

## Agent Types

| Agent | Role | Triggers |
|-------|------|----------|
| **Guardian** | Runs tests after changes, reports failures by severity tier | `file_changed`, `commit` |
| **Probe** | Runs experiments, interprets results against hypotheses | `experiment_requested` |
| **Synthesis** | Finds patterns across repos, flags stale connections | `experiment_completed`, `timer_daily` |
| **Maintenance** | Cleans up — dead code, dependency drift, stale indexes | `timer_nightly`, `maintenance_requested` |
| **Documentation** | Keeps README, indexes, and narrative framing current | `timer_30min`, `file_changed` |

## Test Tiering

Not all tests are equal. The guardian classifies failures by what actually broke:

| Tier | What it means | Dashboard severity |
|------|--------------|-------------------|
| **Gold** | Something structural broke — a roundtrip fails, a simulation diverges, a multi-step process doesn't converge | `action_required` |
| **Silver** | A derived computation changed — a formula that should produce a known value doesn't | `warning` |
| **Bronze** | A constant doesn't equal itself — catches typos, not real breaks | `info` |

New or unclassified tests default to Gold. Better to over-alert than miss a real break.

## The Experiment: Agentic Cartography

The platform's first experiment asks: **can an agentic loop, given only observations about distinction (not our specific map), derive a self-consistent algebraic structure?**

### Seed Observations (no constants, no named structures)
- Defining one thing creates three: the thing, its complement, and the distinction itself
- Binary distinction creates four states: neither, A, B, both
- The boundary between things is itself a thing
- A circle has two sides but one boundary
- Counting requires memory
- Symmetry is cheaper than asymmetry
- A knot that looks trivial locally can be non-trivial globally
- Any self-referential system must contain a fixed point

### 17 Required Properties
Any structure the loop discovers must be:

1. **Invariant** — forced by the math, not chosen by the designer
2. **Spectral** — built on eigenvalues, not coordinates
3. **Semantically mappable** — concepts attach to the algebra naturally
4. **Self-encoding** — can represent data about itself, on itself
5. **Time-like** — has a clock, irreversibility, sequence
6. **Space-like** — has neighbors, adjacency, locality
7. **Physics-like** — has conservation laws and symmetry breaking
8. **Logic-gated** — makes discrete decisions
9. **Self-recursive** — its own operator applies to its own output
10. **Living** — thermodynamic, not static
11. **Bridges discrete and continuous** — lattice embeds in continuum
12. **LLM-compatible** — can consume and produce embeddings
13. **Maps onto known structures** — discovers, doesn't invent
14. **Dimensionless ratios first** — pure numbers before units
15. **Geometrically grounded** — dimensionless quantities anchored on unit sphere
16. **Shape memory** — deformations remember their origin
17. **Topological-spectral** — connectivity meets eigenvalues

### Results So Far

| Probe | Structure Found | Properties | Checks |
|-------|----------------|------------|--------|
| cartography_001 | Distinction Algebra | 12/17 | ? |

Probe 001 started from "defining one thing creates three" and "the boundary is a thing." From those two observations alone, it derived a 9-state algebra with three logic gates (identity, flip, reset), a spectral gap of 1/3, and an irreversible drift toward the boundary — everything decays into the distinction itself. 12 of 17 properties confirmed, 19/19 quantitative checks passed. See [derivation_001.md](experiments/runs/cartography_001/derivation_001.md) for the full reasoning chain.

## Agent-Human Precedence

```
Human intent  >  CLAUDE.md rules  >  Agent judgment  >  Automation defaults
```

- **Human = Architect**: defines intent, assigns meaning, approves gates
- **Agents = Operators**: propose findings, escalate ambiguity, stop when stuck
- Agents may autonomously run tests, index files, and generate reports
- Agents must ask before modifying code, closing issues, pushing, or deleting anything

See [CLAUDE.md](CLAUDE.md) for the full precedence hierarchy.

## Connected Repositories

| Repo | Role | Hook Status |
|------|------|-------------|
| `system3` | Math foundation and research | Installed |
| `RiftEngine` | Unity game engine | Available (not hooked) |
| `FieldForge` | Constraint system | Not found |
| `InvertedSand` | Renderer | Not found |

## Directory Structure

```
agentic/
├── core/           # FastAPI server, event queue, state, vector store
├── agents/         # Agent definitions (base, probe, guardian, synthesis, maintenance, docs)
├── hooks/          # Git hook emitters + installer for connected repos
├── claude/         # Claude Code integration (MCP tools, skills, memory)
├── experiments/    # Experiment seeds, isolated runs, and scoring
│   ├── seeds/      # Starting observations (no answers, just questions)
│   └── runs/       # Each run's discoveries, isolated from each other
├── .github/        # CI/CD (on_push, nightly, digest)
└── data/           # Runtime state (gitignored)
```

## CI/CD

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `on_push` | Every push/PR | Run platform tests, verify imports |
| `nightly` | 6am UTC daily | Maintenance agent sweep |
| `digest` | Noon UTC daily | Morning digest generation |

---

*This README is maintained by the documentation agent, which runs every 30 minutes to keep it current with the state of the platform.*

<!-- AGENT_STATUS_BEGIN -->
**Last updated**: 2026-03-08 22:27 | **Agents**: docs, guardian, maintenance, probe, synthesis | **Experiments**: 1 run(s) (cartography_001) | **Commits**: 3 | **Files**: 29
<!-- AGENT_STATUS_END -->

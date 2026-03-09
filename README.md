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
| **Guardian** | Regression + drift detection with Gold/Silver/Bronze tiering | `file_changed`, `commit` |
| **Probe** | Runs experiments, interprets results against hypotheses | `experiment_requested`, `conjecture_test` |
| **Synthesis** | Cross-repo pattern surfacing, stale connection detection | `conjecture_resolved`, `experiment_completed`, `timer_daily` |
| **Maintenance** | Entropy management — dead code, dependency drift, rigor audits | `timer_nightly`, `maintenance_requested` |
| **Documentation** | Keeps README, indexes, and narrative framing current | `timer_30min`, `file_changed` |

## Golden Run Tiering

Not all tests are created equal. The guardian agent classifies failures by severity:

| Tier | What it catches | Severity | Example |
|------|----------------|----------|---------|
| **Gold** | Structural breaks — roundtrips fail, convergence breaks, dynamics die | `action_required` | Melt/freeze roundtrip, 20-turn stability, servo quantization |
| **Silver** | Algebraic consistency — derived identities, confluences | `warning` | M=13 from 4 forms, Hamming syndrome decode, Galperin |
| **Bronze** | Tautologies — arithmetic that catches typos | `info` | V==3, D==2, FANO==7 |

Unknown tests default to Gold. The guardian is paranoid by design.

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
A discovered structure must be: invariant, spectral, semantically mappable, ouroboros, time-like, space-like, physics-like, logic-gated, self-recursive, living state, discrete-continuous bridge, LLM-integrable, maps onto known forced structures, dimensionless-ratios-first, unit-sphere grounded, shape-memory, and topological-spectral.

### Results So Far

| Probe | Structure Found | Properties | Checks |
|-------|----------------|------------|--------|
| cartography_001 | Distinction Algebra | 12/17 | ? |

Probe 001 derived a 3-element monoid ({+1, -1, 0}, multiplication) from O1+O3 alone, extended it through the Boolean lattice (O2) and symmetry quotient (O6) to a 9-state algebra with spectral gap 1/3, two fixed points, three logic gates (IDENTITY/NOT/RESET), and a thermodynamic arrow toward the boundary absorber.

## Agent-Human Precedence

```
Human intent  >  CLAUDE.md rules  >  Agent judgment  >  Automation defaults
```

- **Human = Architect**: defines intent, assigns meaning, approves gates
- **Agents = Operators**: propose findings, escalate ambiguity, die gracefully
- Agents may autonomously run tests, index files, generate digests
- Agents must ask before modifying code, closing issues, pushing, or deleting anything

See [CLAUDE.md](CLAUDE.md) for the full precedence hierarchy.

## Connected Repositories

| Repo | Role | Hook Status |
|------|------|-------------|
| `system3` | Math foundation, axiom algebra, research | Installed |
| `RiftEngine` | Unity braid-memory engine | Available (not hooked) |
| `FieldForge` | Constraint system | Not found |
| `InvertedSand` | Renderer | Not found |

## Directory Structure

```
agentic/
├── core/           # FastAPI server, event queue, state, vector store
├── agents/         # Agent definitions (base, probe, guardian, synthesis, maintenance, docs)
├── hooks/          # Git hook emitters + installer for connected repos
├── claude/         # Claude Code integration (MCP bridge, skills, memory)
├── experiments/    # Seed packets, isolated runs, 17-property judge
│   ├── seeds/      # Observation-only seed packets
│   └── runs/       # Each run's discoveries, isolated
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

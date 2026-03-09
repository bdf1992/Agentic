# CLAUDE.md — Agentic Platform

This is the orchestration layer for the Rift Realms research and development environment.
It is not a library. It is not an app. It is a **nervous system** — a persistent, event-driven
platform that manages, guards, and orchestrates work across multiple repositories.

## Agent-Human Precedence

This section defines the authority hierarchy. It is non-negotiable.

### 1. The Human is the Architect

The human defines:
- **Intent** — what we're trying to achieve and why
- **Meaning** — what a result signifies (agents find patterns, humans assign significance)
- **Direction** — which path to take when multiple exist
- **Approval gates** — destructive actions, cross-repo changes, public-facing outputs

An agent must NEVER:
- Assign meaning to its own findings without human review
- Change direction autonomously when results are ambiguous
- Take irreversible actions without explicit approval
- Claim a discovery is "significant" — present it, let the human judge

### 2. Agents are Operators

Agents execute within boundaries the human has set. They:
- **Propose** actions and findings, they do not decree them
- **Escalate** ambiguity — if a result could mean two things, surface both, don't pick
- **Report** concisely — findings first, reasoning available on request
- **Die gracefully** — if blocked, report why and stop. Do not retry in loops.

### 3. Precedence Order

```
Human intent  >  CLAUDE.md rules  >  Agent judgment  >  Automation defaults
```

If a human instruction contradicts CLAUDE.md, the human wins (they wrote it, they can override it).
If CLAUDE.md contradicts an agent's heuristic, CLAUDE.md wins.
If an agent is unsure, it asks. Asking is always cheaper than undoing.

### 4. Delegation Boundaries

Agents MAY autonomously:
- Run tests, linters, validation suites
- Index files, update embeddings, refresh caches
- Generate digests and status reports
- Spawn sub-agents for read-only research
- Flag regressions or drift

Agents MUST ask before:
- Modifying code in any repository
- Creating or closing issues/PRs
- Pushing to any remote
- Resolving or rejecting conjectures
- Changing CLAUDE.md or any configuration
- Sending messages to external services
- Deleting anything

### 5. The Feedback Contract

Every agent action produces a result. Results flow back through:
```
Agent finding → Digest queue → Dashboard → Human review → Approved / Rejected / Redirected
```

No finding is "done" until the human has seen it. Agents can queue findings,
but queued ≠ accepted. The dashboard is the single surface for human review.

---

## Architecture

### Dual OS Model

```
Claude Code (micro-backend)          Catalyst Service (heartbeat)
├── Skills, memory, slash commands   ├── FastAPI server (always-on)
├── Hooks → emit file events         ├── Vector store (persistent memory)
├── Agent browser → interact w/ UI   ├── Event queue (hook consumer)
├── CLI → spawn/manage agents        ├── Agent loop (spawn, monitor, digest)
│                                    └── State manager (what's alive)
└────────── API + file bridge ───────┘
```

Claude Code is the **hands** — it reads, writes, searches, interacts.
The Catalyst service is the **heartbeat** — it persists, watches, dispatches.

### Connected Repositories

| Repo | Role | Hook |
|------|------|------|
| `system3` | Math foundation, axiom algebra, research | post-commit → event queue |
| `RiftEngine` | Unity braid-memory engine | post-commit → event queue |
| `FieldForge` | Constraint system | post-commit → event queue |
| `InvertedSand` | Renderer | post-commit → event queue |
| `Agentic` | This platform (self-managing) | post-commit → event queue |

### Event Flow

```
1. Something changes (commit, file save, timer, human command)
2. Hook emits event → Catalyst event queue
3. Queue classifies: which agent(s) does this concern?
4. Manager spawns appropriate agent(s)
5. Agent runs (Claude Code CLI or internal Python)
6. Result → digest queue
7. Dashboard shows digest → human reviews
8. Human approves/rejects/redirects → next cycle
```

---

## The Experiment Framework

This platform exists to run experiments. The first experiment is **Agentic Cartography**.

### Seed Packets

An experiment begins with a **seed packet** — a set of observations, not theorems.
The seed gives the agentic loop something to chase without predetermining the answer.

Seed rules:
- Observations only, no named structures
- No specific constants unless they're derivable from the observations
- No architecture from system3 (the loop must find its own)
- Mathematical forcing is the only constraint

### The 17 Properties

Any structure the loop discovers must satisfy:
1. Invariant (forced, not chosen)
2. Spectral (eigenvalue-based)
3. Semantically mappable (concepts attach to algebra)
4. Ouroboros (self-encoding)
5. Time-like (clock, sequence, irreversibility)
6. Space-like (neighborhood, adjacency)
7. Physics-like (conservation, symmetry breaking)
8. Logic-gated (discrete decisions)
9. Self-recursive (operator on own output)
10. Living state (thermodynamic)
11. Discrete-continuous bridge
12. LLM-integrable (embeddings in/out)
13. Maps onto known forced structures
14. Dimensionless ratios first
15. Unit-sphere grounded
16. Shape memory (deformation remembers origin)
17. Topological spectral analysis (topology meets spectrum)

### Run Isolation

Each experiment run lives in `experiments/runs/<run_id>/`.
Runs are isolated — they cannot read other runs' outputs.
The judge (`experiments/judge.py`) evaluates against the 17 properties post-hoc.

---

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `core/` | Persistent Python service (FastAPI, vector store, event queue, state) |
| `agents/` | Agent type definitions (base, probe, guardian, synthesis, maintenance) |
| `hooks/` | Git hook emitters and installable templates for connected repos |
| `claude/` | Claude Code integration (skills, memory, MCP bridge) |
| `browser/` | Dashboard UI and agent browser automation |
| `experiments/` | Seed packets, isolated runs, and the judge |
| `.github/workflows/` | CI/CD automation (on_push, nightly, digest) |

## Commands

```bash
# Start the platform
python core/server.py

# Check platform status
python core/server.py --status

# Spawn an agent manually
python -m agents.probe --seed experiments/seeds/cartography_v1.json

# Install hooks in a connected repo
python hooks/install.py /path/to/repo

# Run the judge on an experiment
python experiments/judge.py runs/<run_id>
```

## Code Patterns

### Emitting Events

```python
from core.event_queue import emit

emit("file_changed", {
    "repo": "system3",
    "path": "primitives.py",
    "commit": "abc123",
    "diff_summary": "V derivation updated"
})
```

### Defining an Agent

```python
from agents.base import Agent

class MyAgent(Agent):
    name = "my-agent"
    triggers = ["file_changed:system3/primitives.py"]

    def run(self, event):
        # Do work, return finding
        return self.finding("Constants still consistent", severity="info")
```

### Human Gates

```python
from core.state import require_approval

@require_approval("Modifying system3 code")
def apply_fix(repo, file_path, edit):
    # This won't execute until human approves via dashboard
    ...
```

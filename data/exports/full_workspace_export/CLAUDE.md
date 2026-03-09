# Workspace — Agent Build Zone

This directory is where agents build their mathematical system from scratch.

## The Mission

Derive a self-consistent algebraic structure from 9 seed observations about distinction.
The structure must satisfy at least 12 of the 17 required properties.

## Rules

**You get:**
- Seed observations: `../experiments/seeds/cartography_v1.json`
- Standard mathematics (group theory, topology, spectral theory, category theory)
- The concept that "some structures are forced, not chosen"
- Published theorems and known results

**You cannot use:**
- Specific constants (3, 7, 8, 13, 28) unless you DERIVE them from observations
- Named structures from system3 (PPT, Berggren, Clifford, Hamming, MetaByte)
- The function f(n) = 2n + 1 or the seed n₀ = 2
- Any code from the system3 repository

## File Placement (MANDATORY)

**Read `INDEX.md` before creating ANY file.** The workspace is organized into subdirectories:

| Directory       | Contents                                |
|-----------------|-----------------------------------------|
| `algebra/`      | Core algebraic implementations (.py)    |
| `derivations/`  | Mathematical proof documents (.md)      |
| `synthesis/`    | Cross-cutting pattern documents (.md)   |
| `demos/`        | Runnable demonstrations (.py)           |
| `bridges/`      | Cross-domain connectors (.py)           |
| `validation/`   | Test suites and guardian reports         |

**Rules:**
- NEVER create files at workspace root — use the correct subdirectory
- Update `INDEX.md` when you add, rename, or delete files
- Check what exists before building — don't duplicate work
- Import shared constants from a central module (don't hardcode)
- Use `sys.path.insert(0, ...)` for cross-directory imports
- Check other agents' outputs: `curl http://localhost:8750/outputs`

## The 17 Properties

1. **Invariant** — forced, not chosen (uniqueness proof required)
2. **Spectral** — eigenvalue-based, not coordinate-based
3. **Semantically mappable** — concepts attach to algebra naturally
4. **Self-encoding (ouroboros)** — can represent data about itself
5. **Time-like** — has clock, sequences, irreversibility
6. **Space-like** — has neighborhood, adjacency, locality
7. **Physics-like** — conservation laws AND symmetry breaking
8. **Logic-gated** — discrete decisions, Boolean structure
9. **Self-recursive** — operator applies to its own output
10. **Living state** — thermodynamic, not static
11. **Discrete-continuous bridge** — lattice embeds in continuum
12. **LLM-integrable** — can consume and produce embeddings
13. **Maps known structures** — isomorphism to named mathematical objects
14. **Dimensionless ratios** — pure numbers before units
15. **Unit-sphere grounded** — geometric anchoring on unit sphere
16. **Shape memory** — deformation remembers origin
17. **Topological-spectral** — connectivity meets eigenvalues

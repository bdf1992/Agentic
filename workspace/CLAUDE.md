# Workspace — Algebraic Rendering Engine

## The Mission

Build a **complete rendering system** — geometry, color, sound, texture — whose every parameter is derived from the algebra of distinction. No magic numbers. No artist knobs. The algebra IS the control surface.

The 18 properties below are not a checklist to verify. They are the **engineering spec** for what the renderer must do. Each property is a capability the system must have, implemented through algebraic controls that trace back to the forced structures (Z₃, Z₂, spectral gap 2/3).

## What Already Exists (the math layer)

The algebraic foundations are proven and implemented in `algebra/`:

| Structure | What it is | Rendering role |
|-----------|-----------|----------------|
| **Z₃** (position) | {thing, complement, boundary} — forced by O1 | Geometry: vertex placement, surface tiling, mesh topology |
| **Z₂** (color) | {+, -} — fluid between topology and algebra | Color: hue polarity, orientation-as-pigment |
| **2/3** (spectral gap) | |Z₂|/|Z₃| — invariant under all surface transitions | Master coupling constant: locks all channels together |
| **(2/3)^d** (volumetric) | Per-dimension survival rate | Texture: grain density, fractal scaling, LOD |
| **U(1)** (circle group) | Z₃ embeds as roots of unity | Hue wheel, phase, continuous rotation |
| **Q₈** (quaternions) | Recovered on all surfaces via color | 3D rotation, orientation, spin |
| **Surface maps** | Embedding + projection roundtrips | Shape-universal rendering on any topology |

## What Needs To Be Built (the rendering layer)

The algebra produces numbers. The renderer turns those numbers into pixels, samples, vertices, and texels. The gap between `algebra/` and a running renderer is the work.

**Concrete deliverables:**
- Real-time mesh generation from Z₃ lattices on arbitrary surfaces
- Continuous color field driven by Z₂ × U(1) (not a lookup table — the algebra computes it)
- Audio synthesis from eigenvalue frequencies (the distinction chord)
- Procedural texture from (2/3)^d fractal noise with Z₃ frequency scaling
- Deformation system where pushing geometry shifts color/sound/texture coherently
- All channels locked: change one algebraic parameter, everything responds

## Rules

**You get:**
- Seed observations: `../experiments/seeds/cartography_v1.json`
- Standard mathematics (group theory, topology, spectral theory, category theory)
- The concept that "some structures are forced, not chosen"
- Published theorems and known results
- Any rendering framework (WebGL, three.js, SDL, wgpu, etc.)

**You cannot use:**
- Specific constants (3, 7, 8, 13, 28) unless you DERIVE them from observations
- Named structures from system3 (PPT, Berggren, Clifford, Hamming, MetaByte)
- The function f(n) = 2n + 1 or the seed n₀ = 2
- Any code from the system3 repository
- Arbitrary tuning parameters — every number must trace to the algebra

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

## The 18 Properties (Rendering Spec)

These are capabilities the rendering system must exhibit:

1. **Invariant** — all parameters derived, not chosen; uniqueness proof required
2. **Spectral** — eigenvalue-driven, not coordinate-hardcoded
3. **Semantically mappable** — every algebraic element has a visible/audible meaning
4. **Self-encoding (ouroboros)** — the system can render data about itself
5. **Time-like** — has clock, sequences, irreversible transitions (animation)
6. **Space-like** — has neighborhood, adjacency, locality (spatial coherence)
7. **Physics-like** — conservation laws in the simulation; symmetry breaking as visual events
8. **Logic-gated** — discrete decisions, Boolean structure (branching behavior)
9. **Self-recursive** — operator applies to its own output (fractal zoom, feedback)
10. **Living state** — thermodynamic, not static (the scene evolves)
11. **Discrete-continuous bridge** — Z₃ lattice renders as smooth geometry via U(1)
12. **LLM-integrable** — can consume/produce embedding vectors (data I/O)
13. **Maps known structures** — isomorphic to named mathematical objects (verifiable)
14. **Dimensionless ratios** — pure numbers (2/3, 1/3) before any unit system
15. **Unit-sphere grounded** — geometric anchoring on S¹, S², S³
16. **Shape memory** — deformation remembers origin, elastic recovery at rate 2/3
17. **Topological-spectral** — connectivity (surface topology) meets eigenvalues (spectral gap)
18. **Cohesive sensory manifold** — unified color + sound + geometry + texture, all channels locked by spectral gap 2/3, all derived from Z₃ position / Z₂ color / eigenvalue frequencies / (2/3)^d grain

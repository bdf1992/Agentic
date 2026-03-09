# Workspace Spatial Index

> **Read this BEFORE creating any file.** Place files in the correct directory.
> Update this index when you add or remove files.

## Directory Map

```
workspace/
├── algebra/          ← Core algebraic implementations (.py)
│   ├── trinity_algebra.py         Z₃ from single distinction (O1)
│   ├── quaternion_algebra.py      Q₈ from binary distinction (O2)
│   ├── topology_algebra.py        U(1), winding numbers, SU(2)→SO(3) (O4, O7)
│   ├── conservation_algebra.py    Conservation laws CL1-CL3 (O3, O6)
│   ├── fixedpoint_algebra.py      Fixed points, self-reference (O8)
│   ├── memory_algebra.py          Heisenberg-Weyl from counting (O5)
│   ├── symmetry_algebra.py        Information economics of symmetry (O6)
│   ├── surface_algebra.py         Surface-level algebraic structures
│   ├── shape_memory.py            Deformation memory (Property 16)
│   └── spectral_gap_proof.py      Spectral gap verification
│
├── derivations/      ← Mathematical proof documents (.md)
│   ├── derivation_01_trinity.md       Why distinction forces Z₃
│   ├── derivation_02_quaternion.md    Why binary forces quaternions
│   ├── derivation_03_topology.md      Circle topology forces U(1)
│   ├── derivation_04_conservation.md  Conservation from distinction
│   ├── derivation_05_fixedpoint.md    Fixed points from O8
│   ├── derivation_06_memory.md        Counting requires memory (O5)
│   └── derivation_07_symmetry.md      Symmetry is cheaper (O6)
│
├── synthesis/        ← Cross-cutting pattern documents (.md)
│   ├── synthesis_confluences.md           Pattern connections
│   └── synthesis_grand_unification.md     Unified derivation chain
│
├── demos/            ← Runnable demonstrations and validators (.py)
│   ├── forced_structures.py       Original complete derivation
│   └── unified_demonstration.py   Full 17/17 property demo
│
├── bridges/          ← Cross-domain connectors (.py)
│   ├── llm_bridge.py              LLM embedding integration
│   └── unified_confluences.py     Confluence mapping
│
├── validation/       ← Test suites and health reports
│   ├── verify_all_properties.py   17-property verification
│   └── GUARDIAN_REPORT.md         Latest guardian findings
│
├── CLAUDE.md         ← Agent build rules (DO NOT MOVE)
├── README.md         ← System overview (DO NOT MOVE)
├── INDEX.md          ← THIS FILE — spatial map
├── WORK_NARRATIVE.md ← Progress narrative
└── verdict.json      ← Latest judge verdict
```

## Placement Rules

| You're creating...                  | Put it in...      | Name pattern                     |
|-------------------------------------|-------------------|----------------------------------|
| New algebraic structure             | `algebra/`        | `{name}_algebra.py`             |
| Mathematical derivation/proof       | `derivations/`    | `derivation_{NN}_{topic}.md`    |
| Cross-cutting synthesis doc         | `synthesis/`      | `synthesis_{topic}.md`          |
| Runnable demo or combined validator | `demos/`          | `{descriptive_name}.py`         |
| LLM/external integration code      | `bridges/`        | `{system}_bridge.py`            |
| Test suite or guardian report       | `validation/`     | `verify_{what}.py` or `*.md`    |
| New category entirely              | Create subdir + update this index |                  |

## Rules for Agents

1. **Read INDEX.md before creating files** — check if what you need already exists.
2. **Never dump files at workspace root** — use the correct subdirectory.
3. **Update INDEX.md** when you add, rename, or delete files.
4. **Sequential numbering** for derivations: check the latest `derivation_NN_*` and increment.
5. **Import paths**: use `sys.path.insert(0, ...)` when importing across directories (see `demos/forced_structures.py` for example).
6. **One concept per file** — don't stuff unrelated structures into existing files.

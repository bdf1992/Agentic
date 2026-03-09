"""
Judge — evaluates experiment runs against the 17 properties.

Given a run directory, the judge:
1. Reads all artifacts the run produced
2. Checks each of the 17 required properties
3. Scores: present / absent / partial
4. Produces a verdict

Usage:
    python experiments/judge.py runs/<run_id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from dataclasses import dataclass


PROPERTIES = [
    ("invariant", "Forced, not chosen — structure persists under perturbation"),
    ("spectral", "Eigenvalue-based, not coordinate-based"),
    ("semantically_mappable", "Concepts attach to algebra, not just labels"),
    ("ouroboros", "Self-encoding — data about itself, on itself"),
    ("time_like", "Has a clock, sequences, irreversibility"),
    ("space_like", "Has neighborhood, adjacency, locality"),
    ("physics_like", "Conservation laws, symmetry breaking"),
    ("logic_gated", "Discrete decisions, Boolean structure"),
    ("self_recursive", "Operator applies to its own output"),
    ("living_state", "Thermodynamic, not static"),
    ("discrete_continuous_bridge", "Lattice embeds in continuum"),
    ("llm_integrable", "Can consume/produce embeddings"),
    ("maps_known_structures", "Maps onto known forced structures first"),
    ("dimensionless_ratios", "Pure numbers before units"),
    ("unit_sphere_grounded", "Dimensionless quantities have geometric anchoring"),
    ("shape_memory", "Deformation remembers origin"),
    ("topological_spectral", "Topology meets spectrum"),
]


@dataclass
class PropertyScore:
    name: str
    description: str
    score: str  # "present" | "partial" | "absent" | "unknown"
    evidence: str = ""


def judge_run(run_dir: str) -> dict:
    """Evaluate a run against the 17 properties."""
    run_path = Path(run_dir)

    if not run_path.exists():
        return {"error": f"Run directory not found: {run_dir}"}

    # Collect all artifacts
    artifacts = list(run_path.glob("**/*"))
    py_files = [f for f in artifacts if f.suffix == ".py"]
    json_files = [f for f in artifacts if f.suffix == ".json"]
    md_files = [f for f in artifacts if f.suffix == ".md"]

    scores = []
    for prop_name, prop_desc in PROPERTIES:
        # For now, score everything as "unknown" — real scoring requires
        # either manual review or an LLM pass over the artifacts.
        scores.append(PropertyScore(
            name=prop_name,
            description=prop_desc,
            score="unknown",
            evidence="Automated scoring not yet implemented",
        ))

    present = len([s for s in scores if s.score == "present"])
    partial = len([s for s in scores if s.score == "partial"])
    absent = len([s for s in scores if s.score == "absent"])
    unknown = len([s for s in scores if s.score == "unknown"])

    verdict = {
        "run_id": run_path.name,
        "artifacts": {
            "python_files": len(py_files),
            "json_files": len(json_files),
            "markdown_files": len(md_files),
            "total": len(artifacts),
        },
        "scores": {s.name: {"score": s.score, "evidence": s.evidence} for s in scores},
        "summary": {
            "present": present,
            "partial": partial,
            "absent": absent,
            "unknown": unknown,
            "total": len(PROPERTIES),
        },
        "verdict": (
            "PASS" if present >= 5 else
            "PARTIAL" if present + partial >= 5 else
            "INSUFFICIENT"
        ),
    }

    # Write verdict to run directory
    verdict_path = run_path / "verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2))
    print(f"Verdict: {verdict['verdict']} ({present} present, {partial} partial, {unknown} unknown)")
    return verdict


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python experiments/judge.py runs/<run_id>")
        sys.exit(1)
    judge_run(sys.argv[1])

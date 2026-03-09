"""
Judge — evaluates experiment runs against the 17 properties.

Two-phase evaluation:
  Phase 1: Mechanical pre-checks (code runs? smuggled constants? numerical output?)
  Phase 2: LLM adversarial scoring (claude -p with prosecutor prompt)

Usage:
    python experiments/judge.py <run_dir>
    python experiments/judge.py workspace/           # judge the workspace itself
    python experiments/judge.py experiments/runs/cartography_001
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


PROPERTIES = [
    ("invariant", "Forced, not chosen — the structure is the ONLY one satisfying its constraints. "
     "Evidence: uniqueness proof or exhaustive enumeration."),
    ("spectral", "Eigenvalue-based, not coordinate-based. "
     "Evidence: explicit eigenvalue computation, spectral gap, or characteristic polynomial."),
    ("semantically_mappable", "Concepts attach to algebra naturally, not just labels. "
     "Evidence: a mapping table where algebraic operations have semantic meaning."),
    ("ouroboros", "Self-encoding — can represent data about itself, on itself. "
     "Evidence: the structure's own elements encode its multiplication table or transition rules."),
    ("time_like", "Has a clock, sequences, irreversibility. "
     "Evidence: a monotone quantity (entropy, decay rate) or irreversible transition."),
    ("space_like", "Has neighborhood, adjacency, locality. "
     "Evidence: adjacency graph, distance metric, or neighborhood structure."),
    ("physics_like", "Conservation laws and symmetry breaking. "
     "Evidence: a conserved quantity AND a symmetry that breaks under some operation."),
    ("logic_gated", "Discrete decisions, Boolean structure. "
     "Evidence: gates (AND/OR/NOT equivalents) or binary branching in the algebra."),
    ("self_recursive", "Operator applies to its own output. "
     "Evidence: T^n converges or cycles, fixed-point iteration."),
    ("living_state", "Thermodynamic, not static — has energy, entropy, equilibrium. "
     "Evidence: free energy function, entropy computation, or non-trivial steady state."),
    ("discrete_continuous_bridge", "Lattice embeds in continuum. "
     "Evidence: a discrete structure with a continuous limit or rate-matrix embedding."),
    ("llm_integrable", "Can consume and produce embeddings. "
     "Evidence: explicit embedding/projection code, not just 'could be embedded'."),
    ("maps_known_structures", "Maps onto known forced mathematical structures. "
     "Evidence: explicit isomorphism to a named structure (group, ring, code, etc.)."),
    ("dimensionless_ratios", "Pure numbers before units. "
     "Evidence: key quantities are dimensionless ratios derived from structure."),
    ("unit_sphere_grounded", "Dimensionless quantities have geometric anchoring on a unit sphere. "
     "Evidence: normalization to L^1 or L^2 unit sphere, or geometric interpretation."),
    ("shape_memory", "Deformation remembers origin — deformed structure retains info about undeformed. "
     "Evidence: a deformation map with recoverable original state."),
    ("topological_spectral", "Topology meets spectrum — connectivity affects eigenvalues. "
     "Evidence: graph Laplacian, Betti numbers, or spectral-topological relationship."),
]

# Constants that must be DERIVED, not assumed
SMUGGLED_CONSTANTS = {
    "3": "triad/V",
    "7": "Fano/Mersenne",
    "8": "Bott/2^3",
    "13": "projective container M",
    "28": "perfect number/D-chain",
}


@dataclass
class MechanicalResult:
    """Results from Phase 1 mechanical checks."""
    py_files: list[str] = field(default_factory=list)
    py_results: dict[str, dict] = field(default_factory=dict)  # file -> {runs, output, error}
    smuggled: list[dict] = field(default_factory=list)  # {file, line, constant, context}
    has_eigenvalues: bool = False
    has_numerical_output: bool = False
    artifact_count: int = 0
    all_code_runs: bool = True


def phase1_mechanical(run_path: Path) -> MechanicalResult:
    """Phase 1: Mechanical pre-checks — no LLM needed."""
    result = MechanicalResult()
    run_path = run_path.resolve()

    # Collect artifacts
    all_files = [f for f in run_path.rglob("*") if f.is_file()]
    result.artifact_count = len(all_files)
    py_files = [f for f in all_files if f.suffix == ".py"
                and "judge" not in f.name
                and "__pycache__" not in str(f)]
    md_files = [f for f in all_files if f.suffix == ".md"]
    result.py_files = [str(f.relative_to(run_path)) for f in py_files]

    # --- Check 1: Does the code run? ---
    for pf in py_files:
        try:
            proc = subprocess.run(
                [sys.executable, str(pf)],
                capture_output=True, text=True,
                cwd=str(run_path), timeout=30,
            )
            runs = proc.returncode == 0
            result.py_results[str(pf.relative_to(run_path))] = {
                "runs": runs,
                "stdout": proc.stdout[:500] if proc.stdout else "",
                "stderr": proc.stderr[:500] if proc.stderr else "",
            }
            if not runs:
                result.all_code_runs = False
            if proc.stdout:
                result.has_numerical_output = True
        except subprocess.TimeoutExpired:
            result.py_results[str(pf.relative_to(run_path))] = {
                "runs": False, "stdout": "", "stderr": "TIMEOUT (30s)",
            }
            result.all_code_runs = False
        except Exception as e:
            result.py_results[str(pf.relative_to(run_path))] = {
                "runs": False, "stdout": "", "stderr": str(e),
            }
            result.all_code_runs = False

    # --- Check 2: Smuggled constants ---
    # Look for bare numeric literals that match system3 constants
    # but ONLY flag them if they appear without derivation context
    derivation_words = {"derive", "derived", "forced", "follows", "therefore", "implies",
                        "compute", "calculate", "eigenvalue", "solution",
                        "yields", "gives", "equals", "produces", "observation",
                        "from o", "from o1", "from o2", "from o3",
                        "creates three", "four states", "boundary",
                        "absorb", "involution", "spectral gap", "quotient"}

    for f in list(py_files) + list(md_files):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            text_lower = text.lower()
        except Exception:
            continue

        # First pass: check if each constant has ANY derivation in the file
        # If the file derives a constant ANYWHERE, uses of that constant
        # throughout the file are legitimate
        file_derived = set()
        for const_str, const_name in SMUGGLED_CONSTANTS.items():
            # Check if the constant is derived somewhere in this file
            if const_str == "3":
                # "3" is derived if file mentions "three" in derivation context
                if any(w in text_lower for w in
                       ["creates three", "three:", "thing, complement",
                        "thing, its complement", "3 elements", "triad",
                        "from o1", "o1:", "observation"]):
                    file_derived.add(const_str)
            elif const_str == "7":
                if any(w in text_lower for w in
                       ["mersenne", "2^3 - 1", "2**3 - 1", "fano"]):
                    file_derived.add(const_str)
            elif const_str == "8":
                if any(w in text_lower for w in
                       ["2^3", "2**3", "bott", "clifford"]):
                    file_derived.add(const_str)
            elif const_str == "13":
                if any(w in text_lower for w in
                       ["9 + 4", "projective", "v^2 + d^2"]):
                    file_derived.add(const_str)
            elif const_str == "28":
                if any(w in text_lower for w in
                       ["perfect number", "7 * 4", "triangular"]):
                    file_derived.add(const_str)
            # Generic derivation check
            for dw in derivation_words:
                if dw in text_lower and const_str in text:
                    file_derived.add(const_str)
                    break

        # Second pass: only flag constants that have NO derivation in the file
        for i, line in enumerate(lines, 1):
            for const_str, const_name in SMUGGLED_CONSTANTS.items():
                if const_str in file_derived:
                    continue  # This constant is derived in this file
                # Match the constant as a standalone number
                pattern = rf'(?<![.\d]){re.escape(const_str)}(?![.\d])'
                if re.search(pattern, line):
                    # Skip comments that are clearly explanatory
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue
                    result.smuggled.append({
                        "file": str(f.relative_to(run_path)),
                        "line": i,
                        "constant": const_str,
                        "name": const_name,
                        "context": stripped[:100],
                    })

    # --- Check 3: Eigenvalue / spectral content ---
    spectral_words = {"eigenvalue", "eigenval", "eigenvector", "spectral",
                      "eig(", "eigh(", "eigvals", "characteristic polynomial",
                      "spectrum"}
    for f in list(py_files) + list(md_files):
        try:
            text = f.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
        if any(w in text for w in spectral_words):
            result.has_eigenvalues = True
            break

    return result


def phase2_llm_score(run_path: Path, mechanical: MechanicalResult) -> dict:
    """Phase 2: LLM adversarial scoring via claude -p."""

    # Collect all text content for the LLM to read
    content_parts = []
    for f in sorted(run_path.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix in (".py", ".md", ".txt", ".json"):
            if "__pycache__" in str(f) or "verdict" in f.name:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if len(text) > 5000:
                    text = text[:5000] + "\n... [TRUNCATED]"
                content_parts.append(f"=== {f.relative_to(run_path)} ===\n{text}")
            except Exception:
                continue

    if not content_parts:
        return {"error": "No readable artifacts found"}

    all_content = "\n\n".join(content_parts)

    # Build the mechanical summary
    mech_summary = (
        f"MECHANICAL PRE-CHECK RESULTS:\n"
        f"- Python files found: {len(mechanical.py_files)}\n"
        f"- All code runs: {mechanical.all_code_runs}\n"
        f"- Has eigenvalue computations: {mechanical.has_eigenvalues}\n"
        f"- Has numerical output: {mechanical.has_numerical_output}\n"
        f"- Potentially smuggled constants: {len(mechanical.smuggled)}\n"
    )
    if mechanical.smuggled:
        mech_summary += "  Flagged constants:\n"
        for s in mechanical.smuggled[:20]:
            mech_summary += f"    {s['file']}:{s['line']} — {s['constant']} ({s['name']}): {s['context']}\n"
    if not mechanical.all_code_runs:
        mech_summary += "  Failed files:\n"
        for fname, res in mechanical.py_results.items():
            if not res["runs"]:
                mech_summary += f"    {fname}: {res['stderr'][:100]}\n"

    # Build the property list for the prompt
    prop_list = "\n".join(
        f"  {i+1}. {name}: {desc}"
        for i, (name, desc) in enumerate(PROPERTIES)
    )

    # The adversarial scoring prompt
    system_prompt = (
        "You are a strict mathematical auditor. Your job is to evaluate whether a set of "
        "mathematical derivations and code ACTUALLY satisfies a list of required properties.\n\n"
        "YOUR BIAS IS TOWARD DENIAL. You are a prosecutor, not a cheerleader.\n\n"
        "Rules for scoring:\n"
        "- PRESENT: You can point to specific equations, code, or proofs that demonstrate the property. "
        "The evidence must be CONCRETE — a line number, an equation, a computed value.\n"
        "- PARTIAL: There's relevant work but it's incomplete — a claim without proof, "
        "code that doesn't run, or a derivation with gaps.\n"
        "- ABSENT: No evidence, or the claim is wrong, or the evidence is circular.\n\n"
        "Additional rules:\n"
        "- If a constant (3, 7, 8, 13, 28) appears without derivation, that's a VIOLATION. "
        "Flag it and downgrade any property that depends on it.\n"
        "- 'Could be extended to...' is NOT evidence. Only what IS demonstrated counts.\n"
        "- Self-assessment by the run's author does NOT count as evidence. YOU judge.\n"
        "- If code doesn't run, any property that requires running code is ABSENT.\n"
        "- If a property is claimed but the evidence is just 'this algebra has property X', "
        "that's PARTIAL at best — show the math or show the code.\n"
    )

    prompt = (
        f"Evaluate this mathematical derivation/codebase against 17 required properties.\n\n"
        f"{mech_summary}\n\n"
        f"PROPERTIES TO EVALUATE:\n{prop_list}\n\n"
        f"ARTIFACTS:\n{all_content}\n\n"
        f"Respond with ONLY a JSON object (no markdown fences, no commentary before/after). "
        f"The JSON must have this exact structure:\n"
        f'{{\n'
        f'  "scores": {{\n'
        f'    "invariant": {{"score": "present|partial|absent", "evidence": "specific citation", "weakness": "what would make it stronger"}},\n'
        f'    "spectral": {{"score": "...", "evidence": "...", "weakness": "..."}},\n'
        f'    ... (all 17 properties)\n'
        f'  }},\n'
        f'  "smuggled_constants": ["list any constants used without derivation"],\n'
        f'  "strongest_property": "name of best-evidenced property",\n'
        f'  "weakest_claim": "name of most over-claimed property",\n'
        f'  "overall_assessment": "1-2 sentence honest summary"\n'
        f'}}\n'
    )

    # Call claude -p
    try:
        proc = subprocess.run(
            ["claude", "-p", "--model", "opus", "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True,
            timeout=300,  # 5 min max for judging
        )
        if proc.returncode != 0:
            return {"error": f"Claude exited with code {proc.returncode}: {proc.stderr[:500]}"}

        # Parse the JSON from the response
        raw = proc.stdout.strip()

        # Try to extract JSON from the response (might be wrapped in markdown)
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                return {"error": "Failed to parse LLM JSON output", "raw": raw[:2000]}
        else:
            return {"error": "No JSON found in LLM output", "raw": raw[:2000]}

    except subprocess.TimeoutExpired:
        return {"error": "LLM scoring timed out (5 min)"}
    except FileNotFoundError:
        return {"error": "claude CLI not found — is it installed and on PATH?"}
    except Exception as e:
        return {"error": f"LLM scoring failed: {e}"}


def judge_run(run_dir: str, skip_llm: bool = False) -> dict:
    """Full evaluation: mechanical + LLM scoring."""
    run_path = Path(run_dir).resolve()

    if not run_path.exists():
        print(f"ERROR: Directory not found: {run_dir}")
        return {"error": f"Run directory not found: {run_dir}"}

    print(f"Judging: {run_path.name}")
    print(f"{'='*60}")

    # Phase 1: Mechanical
    print("\nPhase 1: Mechanical pre-checks...")
    mechanical = phase1_mechanical(run_path)

    print(f"  Files: {len(mechanical.py_files)} Python, {mechanical.artifact_count} total")
    print(f"  Code runs: {'ALL PASS' if mechanical.all_code_runs else 'FAILURES DETECTED'}")
    print(f"  Eigenvalues: {'found' if mechanical.has_eigenvalues else 'not found'}")
    print(f"  Smuggled constants: {len(mechanical.smuggled)} flagged")

    if not mechanical.all_code_runs:
        print("\n  FAILED FILES:")
        for fname, res in mechanical.py_results.items():
            if not res["runs"]:
                print(f"    {fname}: {res['stderr'][:80]}")

    if mechanical.smuggled:
        print("\n  SMUGGLED CONSTANTS:")
        for s in mechanical.smuggled[:10]:
            print(f"    {s['file']}:{s['line']} — {s['constant']} ({s['name']})")

    # Phase 2: LLM scoring
    if skip_llm:
        print("\nPhase 2: SKIPPED (--skip-llm)")
        llm_scores = {"skipped": True}
    else:
        print("\nPhase 2: LLM adversarial scoring (this takes 1-3 minutes)...")
        llm_scores = phase2_llm_score(run_path, mechanical)

        if "error" in llm_scores:
            print(f"  ERROR: {llm_scores['error']}")
        elif "scores" in llm_scores:
            present = sum(1 for s in llm_scores["scores"].values()
                         if isinstance(s, dict) and s.get("score") == "present")
            partial = sum(1 for s in llm_scores["scores"].values()
                         if isinstance(s, dict) and s.get("score") == "partial")
            absent = sum(1 for s in llm_scores["scores"].values()
                        if isinstance(s, dict) and s.get("score") == "absent")
            print(f"  Present: {present} | Partial: {partial} | Absent: {absent}")
            if llm_scores.get("strongest_property"):
                print(f"  Strongest: {llm_scores['strongest_property']}")
            if llm_scores.get("weakest_claim"):
                print(f"  Weakest:   {llm_scores['weakest_claim']}")
            if llm_scores.get("overall_assessment"):
                print(f"  Assessment: {llm_scores['overall_assessment']}")

    # Build verdict
    verdict = {
        "run_id": run_path.name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mechanical": {
            "py_files": mechanical.py_files,
            "py_results": {k: {"runs": v["runs"]} for k, v in mechanical.py_results.items()},
            "all_code_runs": mechanical.all_code_runs,
            "has_eigenvalues": mechanical.has_eigenvalues,
            "has_numerical_output": mechanical.has_numerical_output,
            "smuggled_constants": mechanical.smuggled,
            "artifact_count": mechanical.artifact_count,
        },
        "llm_scores": llm_scores,
    }

    # Compute final verdict
    if "scores" in llm_scores:
        scores = llm_scores["scores"]
        present = sum(1 for s in scores.values()
                     if isinstance(s, dict) and s.get("score") == "present")
        partial = sum(1 for s in scores.values()
                     if isinstance(s, dict) and s.get("score") == "partial")
        verdict["summary"] = {
            "present": present,
            "partial": partial,
            "absent": 17 - present - partial,
            "total": 17,
        }
        if not mechanical.all_code_runs:
            verdict["verdict"] = "FAIL_CODE"
        elif len(mechanical.smuggled) > 5:
            verdict["verdict"] = "FAIL_SMUGGLED"
        elif present >= 12:
            verdict["verdict"] = "STRONG_PASS"
        elif present >= 5:
            verdict["verdict"] = "PASS"
        elif present + partial >= 5:
            verdict["verdict"] = "PARTIAL"
        else:
            verdict["verdict"] = "INSUFFICIENT"
    else:
        verdict["verdict"] = "MECHANICAL_ONLY" if skip_llm else "LLM_FAILED"

    # Save verdict
    verdict_path = run_path / "verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2))
    print(f"\n{'='*60}")
    print(f"VERDICT: {verdict['verdict']}")
    print(f"Saved to: {verdict_path}")

    return verdict


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python experiments/judge.py <run_dir> [--skip-llm]")
        print("Examples:")
        print("  python experiments/judge.py workspace/")
        print("  python experiments/judge.py experiments/runs/cartography_001")
        print("  python experiments/judge.py workspace/ --skip-llm")
        sys.exit(1)

    skip = "--skip-llm" in sys.argv
    run_dir = sys.argv[1]
    judge_run(run_dir, skip_llm=skip)

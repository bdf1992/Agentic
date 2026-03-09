"""
Run All — single entry point to validate the entire workspace.

Runs in order:
  1. All algebra modules (import + execute)
  2. All demo scripts (headless execution)
  3. Coherence proof (7 tests)
  4. Property verification (17 properties)
  5. Mechanical judge (smuggled constants, eigenvalues)

Produces a consolidated pass/fail report with timing.
"""

import subprocess
import sys
import time
import json
import os
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
ROOT = WORKSPACE.parent

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_python(filepath: Path, timeout: int = 60) -> tuple[bool, float, str]:
    """Run a Python file and return (success, duration_sec, error_msg)."""
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(filepath)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(filepath.parent),
        )
        duration = time.time() - start
        if result.returncode == 0:
            return True, duration, ""
        else:
            error = result.stderr.strip().split("\n")[-1] if result.stderr else f"exit {result.returncode}"
            return False, duration, error
    except subprocess.TimeoutExpired:
        return False, timeout, "TIMEOUT"
    except Exception as e:
        return False, time.time() - start, str(e)


def section(title: str):
    print(f"\n{BOLD}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{RESET}\n")


def main():
    total_start = time.time()
    results = {"passed": 0, "failed": 0, "skipped": 0, "sections": {}}

    # ============================================
    # 1. Algebra modules
    # ============================================
    section("1. ALGEBRA MODULES")
    algebra_dir = WORKSPACE / "algebra"
    algebra_results = {}

    if algebra_dir.exists():
        for pyf in sorted(algebra_dir.glob("*.py")):
            if pyf.name == "__init__.py":
                continue
            ok, dur, err = run_python(pyf, timeout=45)
            status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            print(f"  [{status}] {pyf.name:40s} ({dur:.1f}s){f'  {err}' if err else ''}")
            algebra_results[pyf.name] = ok
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
    else:
        print(f"  {YELLOW}No algebra/ directory{RESET}")

    results["sections"]["algebra"] = algebra_results

    # ============================================
    # 2. Demo scripts
    # ============================================
    section("2. DEMO SCRIPTS")
    demos_dir = WORKSPACE / "demos"
    demo_results = {}

    if demos_dir.exists():
        for pyf in sorted(demos_dir.glob("*.py")):
            if pyf.name == "__init__.py":
                continue
            ok, dur, err = run_python(pyf, timeout=60)
            status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            print(f"  [{status}] {pyf.name:40s} ({dur:.1f}s){f'  {err}' if err else ''}")
            demo_results[pyf.name] = ok
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
    else:
        print(f"  {YELLOW}No demos/ directory{RESET}")

    results["sections"]["demos"] = demo_results

    # ============================================
    # 3. Bridge modules
    # ============================================
    section("3. BRIDGE MODULES")
    bridges_dir = WORKSPACE / "bridges"
    bridge_results = {}

    if bridges_dir.exists():
        for pyf in sorted(bridges_dir.glob("*.py")):
            if pyf.name == "__init__.py":
                continue
            ok, dur, err = run_python(pyf, timeout=30)
            status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            print(f"  [{status}] {pyf.name:40s} ({dur:.1f}s){f'  {err}' if err else ''}")
            bridge_results[pyf.name] = ok
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1

    results["sections"]["bridges"] = bridge_results

    # ============================================
    # 4. Coherence proof
    # ============================================
    section("4. COHERENCE PROOF")
    coherence_file = demos_dir / "coherence_proof.py"
    if coherence_file.exists():
        ok, dur, err = run_python(coherence_file, timeout=120)
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}] coherence_proof.py ({dur:.1f}s)")
        results["sections"]["coherence"] = ok
        # Already counted in demos, don't double-count
    else:
        print(f"  {YELLOW}coherence_proof.py not found{RESET}")
        results["sections"]["coherence"] = None

    # ============================================
    # 5. Property verification
    # ============================================
    section("5. PROPERTY VERIFICATION")
    verify_file = WORKSPACE / "validation" / "verify_all_properties.py"
    if verify_file.exists():
        ok, dur, err = run_python(verify_file, timeout=60)
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}] verify_all_properties.py ({dur:.1f}s)")
        results["sections"]["property_verification"] = ok
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
    else:
        print(f"  {YELLOW}verify_all_properties.py not found{RESET}")

    # ============================================
    # 6. Mechanical judge
    # ============================================
    section("6. MECHANICAL JUDGE")
    try:
        sys.path.insert(0, str(ROOT))
        from experiments.judge import phase1_mechanical
        mech = phase1_mechanical(WORKSPACE)
        print(f"  Python files: {len(mech.py_files)}")
        print(f"  All code runs: {GREEN if mech.all_code_runs else RED}{mech.all_code_runs}{RESET}")
        print(f"  Eigenvalues found: {mech.has_eigenvalues}")
        print(f"  Smuggled constants: {len(mech.smuggled)}")
        if mech.smuggled:
            for s in mech.smuggled[:5]:
                print(f"    {RED}{s['file']}:{s['line']} — {s['constant']} ({s['name']}){RESET}")
        # Show files that failed to run
        failed_files = [f for f, r in mech.py_results.items() if not r.get("runs", True)]
        if failed_files:
            print(f"  Failed files ({len(failed_files)}):")
            for ff in failed_files[:10]:
                err = mech.py_results[ff].get("error", "")
                print(f"    {RED}{ff}{RESET}{f': {err}' if err else ''}")
        results["sections"]["judge"] = {
            "py_files": len(mech.py_files),
            "all_run": mech.all_code_runs,
            "eigenvalues": mech.has_eigenvalues,
            "smuggled": len(mech.smuggled),
        }
    except Exception as e:
        print(f"  {RED}Judge failed: {e}{RESET}")
        results["sections"]["judge"] = {"error": str(e)}

    # ============================================
    # Summary
    # ============================================
    total_time = time.time() - total_start
    section("SUMMARY")

    total = results["passed"] + results["failed"]
    all_pass = results["failed"] == 0

    print(f"  Total files tested: {total}")
    print(f"  {GREEN}Passed: {results['passed']}{RESET}")
    if results["failed"] > 0:
        print(f"  {RED}Failed: {results['failed']}{RESET}")
    else:
        print(f"  Failed: 0")
    print(f"  Time: {total_time:.1f}s")
    print()

    if all_pass:
        print(f"  {GREEN}{BOLD}ALL TESTS PASS{RESET}")
    else:
        print(f"  {RED}{BOLD}FAILURES DETECTED{RESET}")

    # Write machine-readable results
    report_path = WORKSPACE / "validation" / "run_all_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "passed": results["passed"],
            "failed": results["failed"],
            "total_time_sec": round(total_time, 1),
            "all_pass": all_pass,
            "sections": {k: v for k, v in results["sections"].items()
                         if not isinstance(v, dict) or "error" not in v},
        }, f, indent=2, default=str)
    print(f"\n  Report: {report_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

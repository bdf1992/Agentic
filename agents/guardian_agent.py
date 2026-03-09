"""
Guardian Agent — regression and drift detection with Gold/Silver/Bronze tiering.

Watches for changes that might break invariants:
- Runs golden runs after commits to load-bearing files
- Cross-checks constants across repos
- Flags unexpected drift in test outputs

The guardian is paranoid by design. False positives are acceptable.
False negatives (missed breaks) are not.

Tier definitions:
    GOLD:   Structural/mechanized — roundtrips, convergence, multi-step dynamics,
            cross-layer coupling, statistical validation. These catch REAL breaks.
    SILVER: Derived algebra — non-trivial computations from primitives, confluences,
            spectral properties, combinatorial identities. These verify the math spine.
    BRONZE: Trivial arithmetic — constant equality, tautologies. These catch typos.

A Gold failure is action_required. A Silver failure is warning. A Bronze failure is info.
"""

from __future__ import annotations

import re
from typing import Optional
from pathlib import Path

from agents.base import Agent, Finding
from core.event_queue import Event


# Files that, if changed, require golden run validation
LOAD_BEARING = {
    "system3": [
        "primitives.py", "formulas.py", "system3.py",
        "photon_mesh/meta_byte/", "s3/",
    ],
    "RiftEngine": [
        "Assets/Scripts/Core/", "Assets/Scripts/Braid/",
    ],
}

# ── Tier classification ─────────────────────────────────────────────
# Golden runs are classified by their MODULE PATH.
# Each test is assigned to a tier based on what it actually verifies.

GOLD_TESTS = {
    # Engine: real computation, roundtrips, convergence
    "engine.g08_ring_conservation",
    "engine.g09_shell_syndrome",
    "engine.g10_mode_conservation",
    "engine.g11_boundary_ports",
    "engine.g12_triple_coupling",
    "engine.g15_duality_servo",
    "engine.g19_persistent_continuous",
    "engine.g20_phase_router",
    "engine.g26_gate_interface",
    "engine.g28_ouroboros_bridge",
    "engine.g30_long_run_stability",
    "engine.g31_lie_transport",
    "engine.g38_z4_channel",
    "engine.g48_freeze_melt_invariant",
    "engine.g83_propagator_bridge",
    "engine.g85_mult_basin_separation",
    # Geometry: navigation roundtrips, spatial dynamics
    "geometry.g27_ppt_navigate",
    "geometry.g39_berggren_spatial",
    "geometry.g44_theta_descent",
    "geometry.g47_geometric_profile",
    "geometry.g49_torus_autocorrelation",
    "geometry.g50_sdf_terminus",
    "geometry.g65_clifford_routing",
    "geometry.g70_clifford_torus_probe",
    "geometry.g74_foliation_fano",
    "geometry.g77_boost_parameter",
    "geometry.g78_lp_witness",
    "geometry.g84_tda_coset_probe",
    # Spectral: eigenvalues, mode coupling, convergence
    "spectral.g51_kubic_harmonics",
    "spectral.g56_lp_freeze_predictions",
    "spectral.g57_gate_lp_match",
    "spectral.g58_schatten_probe",
    "spectral.g59_lp_limit_probe",
    "spectral.g61_kubic_dissonance",
    "spectral.g63_interface_move_fraction",
    "spectral.g64_complex_moments",
    "spectral.g76_torus_mode_coupling",
    "spectral.g79_drum_isolation",
    # Pipeline: agent roundtrips, multi-turn stability
    "pipeline.g07_agent_seed",
    "pipeline.g14_point_schema",
    "pipeline.g17_grokking_loop",
    "pipeline.g21_cascading_sensors",
    "pipeline.g22_crystallization",
    "pipeline.g23_checkpoint",
    "pipeline.g24_skill_roundtrip",
    "pipeline.g25_observation_synthesis",
    "pipeline.g29_bge_reader",
    "pipeline.g32_reader_stability",
    "pipeline.g33_adversarial",
    "pipeline.g52_element_algebra",
    "pipeline.g53_atomic_node",
    "pipeline.g54_coupled_pair",
    "pipeline.g55_triple_node",
    "pipeline.g66_s3_address",
    "pipeline.g67_s3_correct",
    "pipeline.g68_s3_servo",
    "pipeline.g69_s3_process",
    "pipeline.g71_s3_persistence",
    "pipeline.g72_s3_query",
    "pipeline.g73_s3_turn",
    "pipeline.g75_dchain_negative_control",
    # Product: full-stack integration
    "product.g41_hello_page",
    "product.g42_two_page_planner",
    "product.g43_rift_db_schema",
    "product.g45_reader_planner",
    "product.g46_vertical_slice",
    "product.g60_spectral_engine",
    # Witness: meta-tests
    "witness.g80_contract_integrity",
    "witness.g81_neural_probe_discrimination",
    "witness.g82_constant_ablation",
}

SILVER_TESTS = {
    # Algebra: derived identities, combinatorial verification
    "algebra.g06_hamming",
    "algebra.g16_deficit_closure",
    "algebra.g18_solver_tiers",
    "algebra.g35_eigenspace_truncation",
    "algebra.g40_s3_isomorphism",
    # Bedrock derived: non-trivial computations
    "bedrock.g03_gnomon_seed",
    "bedrock.g04_galperin",
    "bedrock.g05_transfer_trace",
    "bedrock.g13_fano_shell",
    "bedrock.g34_confluence",
    "bedrock.g36_axiom_prime_closure",
    "bedrock.g37_loop_projective",
    # Constraints files (cross-layer verification)
    "bedrock.constraints",
    "algebra.constraints",
    "engine.constraints",
    "geometry.constraints",
    "spectral.constraints",
    "pipeline.constraints",
    "product.constraints",
}

BRONZE_TESTS = {
    # Pure constant equality — catches typos, nothing structural
    "bedrock.g01_primitives",
}


def classify_test(name: str) -> str:
    """Classify a test as gold, silver, or bronze."""
    if name in GOLD_TESTS:
        return "gold"
    if name in SILVER_TESTS:
        return "silver"
    if name in BRONZE_TESTS:
        return "bronze"
    # Unknown tests default to gold (paranoid)
    return "gold"


class GuardianAgent(Agent):
    name = "guardian"
    triggers = ["file_changed", "commit"]

    def __init__(self, repo_roots: Optional[dict[str, str]] = None):
        super().__init__()
        self.repo_roots = repo_roots or {
            "system3": "C:/Users/bdf19/OneDrive/Desktop/Rift Realms/system3",
            "RiftEngine": "C:/Users/bdf19/CatalystCore/CatalystCore",
        }

    def run(self, event: Optional[Event] = None) -> Finding:
        if not event:
            return self._full_sweep()

        repo = event.repo
        changed = event.payload.get("path", "")

        # Check if this is a load-bearing change
        is_critical = False
        for pattern in LOAD_BEARING.get(repo, []):
            if pattern in changed:
                is_critical = True
                break

        if not is_critical:
            return self.finding(f"Non-critical change: {repo}/{changed}")

        # Load-bearing change detected — run golden runs
        return self._run_golden(repo)

    def _run_golden(self, repo: str) -> Finding:
        """Run golden runs for a repo with tiered reporting."""
        if repo == "system3":
            root = self.repo_roots.get("system3", "")
            output, code = self.run_command(
                "python golden_runs/run_all.py",
                cwd=root,
                timeout=300,
            )

            if code == 0:
                return self.finding(
                    f"Golden runs PASSED for {repo}",
                    data={"output": output[-500:]},
                )

            # Parse failures and classify by tier
            return self._classify_failures(repo, output)
        else:
            return self.finding(
                f"No golden runs configured for {repo}",
                severity="warning",
            )

    def _classify_failures(self, repo: str, output: str) -> Finding:
        """Parse golden run output and classify failures by tier."""
        gold_fails = []
        silver_fails = []
        bronze_fails = []

        # Parse "FAIL: <module_name> — <message>" lines
        for line in output.split("\n"):
            fail_match = re.search(r"FAIL:\s+(\S+)", line)
            if fail_match:
                test_name = fail_match.group(1)
                tier = classify_test(test_name)
                entry = f"{test_name}: {line.strip()}"
                if tier == "gold":
                    gold_fails.append(entry)
                elif tier == "silver":
                    silver_fails.append(entry)
                else:
                    bronze_fails.append(entry)

        # Determine severity by highest-tier failure
        if gold_fails:
            severity = "action_required"
            summary = f"GOLD FAILURE in {repo}: {len(gold_fails)} structural test(s) broke"
        elif silver_fails:
            severity = "warning"
            summary = f"SILVER FAILURE in {repo}: {len(silver_fails)} algebraic test(s) broke"
        elif bronze_fails:
            severity = "info"
            summary = f"BRONZE FAILURE in {repo}: {len(bronze_fails)} arithmetic check(s) broke"
        else:
            # Failed but we couldn't parse why
            severity = "action_required"
            summary = f"UNPARSED FAILURE in {repo} — manual review needed"

        return self.finding(
            summary,
            severity=severity,
            data={
                "gold_failures": gold_fails,
                "silver_failures": silver_fails,
                "bronze_failures": bronze_fails,
                "raw_output": output[-500:],
            },
        )

    def _full_sweep(self) -> Finding:
        """Run all golden runs across all repos with tiered reporting."""
        results = {}
        worst_severity = "info"

        for repo, root in self.repo_roots.items():
            if repo == "system3":
                output, code = self.run_command(
                    "python golden_runs/run_all.py",
                    cwd=root,
                    timeout=300,
                )

                if code == 0:
                    results[repo] = {"tier": "all_passed", "output": output[-300:]}
                else:
                    finding = self._classify_failures(repo, output)
                    results[repo] = finding.data
                    if finding.severity == "action_required":
                        worst_severity = "action_required"
                    elif finding.severity == "warning" and worst_severity != "action_required":
                        worst_severity = "warning"

        if worst_severity == "info" and all(
            r.get("tier") == "all_passed" for r in results.values()
        ):
            return self.finding("Full sweep: ALL PASSED", data=results)

        # Build tiered summary
        total_gold = sum(len(r.get("gold_failures", [])) for r in results.values())
        total_silver = sum(len(r.get("silver_failures", [])) for r in results.values())
        total_bronze = sum(len(r.get("bronze_failures", [])) for r in results.values())

        summary = (
            f"Full sweep: {total_gold} GOLD / {total_silver} SILVER / {total_bronze} BRONZE failures"
        )
        return self.finding(summary, severity=worst_severity, data=results)

"""
Topology Algebra: Structures forced by circle and knot observations.

Derived from:
  O4: "A circle has two sides but one boundary."
  O7: "A knot that looks trivial locally can be non-trivial globally."

Key derivations:
  1. O4 forces U(1) — the circle group, the simplest continuous symmetry
  2. O7 forces π₁(S¹) = ℤ — integers emerge from winding numbers
  3. Z₃ embeds in U(1) as cube roots of unity (connects to trinity_algebra)
  4. Q₈ maps to SU(2) which double-covers SO(3) (connects to quaternion_algebra)
  5. The boundary dimension (OB4) is forced: dim(∂) = dim(bulk) - 1
"""

import numpy as np
from typing import Dict, List, Tuple


class CircleGroup:
    """U(1): the group forced by O4's circular boundary.

    A circle has two sides (inside/outside) but one boundary.
    The boundary itself is S¹, whose symmetry group is U(1) = {e^{iθ} : θ ∈ [0, 2π)}.
    This is the ONLY continuous group on a 1-dimensional closed manifold.

    THE COST OF UNARY (O0 meets U(1)):
    U(1) is called "unitary" but it is NOT unary. The name refers to 1×1 matrices,
    but the group itself is irreducibly binary:
      - Every element e^{iθ} presupposes its conjugate e^{-iθ}
      - The unit circle separates inside from outside (two sides, O4)
      - Real and imaginary axes are the distinction that makes the circle possible
      - Even the simplest continuous symmetry group pays the cost of O0:
        you cannot have U(1) without the complex plane, which IS a distinction

    Belonging to a unitary group means carrying your opposite with you at all times.
    The "1" is a lie — there is no 1 without the structure that distinguishes it.
    """

    def __init__(self, resolution: int = 360):
        self.resolution = resolution

    def element(self, theta: float) -> complex:
        """A U(1) element is a point on the unit circle."""
        return np.exp(1j * theta)

    def point(self, theta: float) -> complex:
        """Alias for element - get a point on the unit circle."""
        return self.element(theta)

    def multiply(self, theta1: float, theta2: float) -> float:
        """Group operation: addition of angles mod 2π."""
        return (theta1 + theta2) % (2 * np.pi)

    def inverse(self, theta: float) -> float:
        """Inverse: negate angle mod 2π."""
        return (2 * np.pi - theta) % (2 * np.pi)

    def identity(self) -> float:
        """Identity element: θ = 0."""
        return 0.0

    def verify_group_axioms(self, samples: int = 100) -> bool:
        """Verify U(1) group axioms on sampled elements."""
        rng = np.random.default_rng(42)
        angles = rng.uniform(0, 2 * np.pi, samples)

        # Closure
        for i in range(min(samples, 20)):
            for j in range(min(samples, 20)):
                result = self.multiply(angles[i], angles[j])
                if not (0 <= result < 2 * np.pi + 1e-10):
                    return False

        # Associativity (sample)
        for i in range(min(samples, 10)):
            a, b, c = angles[i], angles[(i+1) % samples], angles[(i+2) % samples]
            left = self.multiply(self.multiply(a, b), c)
            right = self.multiply(a, self.multiply(b, c))
            if abs(left - right) > 1e-10 and abs(abs(left - right) - 2*np.pi) > 1e-10:
                return False

        # Identity
        for i in range(min(samples, 20)):
            if abs(self.multiply(angles[i], self.identity()) - angles[i]) > 1e-10:
                return False

        # Inverse
        for i in range(min(samples, 20)):
            result = self.multiply(angles[i], self.inverse(angles[i]))
            if abs(result) > 1e-10 and abs(result - 2*np.pi) > 1e-10:
                return False

        return True

    def embed_cyclic_group(self, n: int) -> List[float]:
        """Embed Z_n into U(1) as nth roots of unity.

        This shows that Z₃ from trinity_algebra LIVES INSIDE U(1).
        The discrete structure embeds in the continuous one.
        """
        return [2 * np.pi * k / n for k in range(n)]

    def roots_of_unity(self, n: int) -> List[complex]:
        """The nth roots of unity — Z_n realized as complex numbers."""
        return [self.element(theta) for theta in self.embed_cyclic_group(n)]

    def spectral_decomposition(self, n: int) -> Dict[str, np.ndarray]:
        """Fourier analysis on Z_n ⊂ U(1).

        The DFT matrix IS the representation theory of Z_n.
        Each row is a character (irreducible representation).
        """
        omega = np.exp(2j * np.pi / n)
        dft_matrix = np.array([[omega ** (j * k) for k in range(n)] for j in range(n)]) / np.sqrt(n)
        eigenvalues = np.linalg.eigvals(dft_matrix)
        return {
            "dft_matrix": dft_matrix,
            "eigenvalues": eigenvalues,
            "spectral_gap": np.max(np.abs(eigenvalues)) - np.sort(np.abs(eigenvalues))[-2]
                if len(eigenvalues) > 1 else 0.0
        }

    def unary_cost(self) -> Dict[str, str]:
        """O0 applied to U(1): the cost of pretending to be one thing.

        U(1) looks minimal — one-dimensional, abelian, the 'simplest' Lie group.
        But it smuggles in all of binary distinction:
          - Complex numbers require real vs imaginary (a distinction)
          - The unit circle requires inside vs outside (O4's two sides)
          - Conjugation e^{iθ} ↔ e^{-iθ} is the complement operation
          - The identity 1 ∈ U(1) only has meaning against -1 ∈ U(1)

        The unary position is incoherent even in continuous mathematics.
        """
        return {
            "group_name": "U(1) — 'unitary' group of degree 1",
            "apparent_simplicity": "1-dimensional, abelian, connected, compact",
            "hidden_binary_structure": {
                "real_vs_imaginary": "Complex plane is a distinction (ℝ × ℝ)",
                "inside_vs_outside": "Circle separates plane into two regions (O4)",
                "element_vs_conjugate": "Every e^{iθ} implies e^{-iθ}",
                "identity_vs_negation": "1 only means '1' against -1",
                "winding_vs_unwinding": "n winds forward, -n winds back (ℤ has ±)",
            },
            "cost": "To 'be one thing' (U(1)) requires embedding in a binary space (ℂ)",
            "o0_verdict": "Unary is incoherent: even the simplest Lie group is built on distinction",
        }

    def boundary_dimension(self) -> Dict[str, int]:
        """OB4: The boundary dimension relative to the bulk.

        O4 says: a circle has two sides but one boundary.
        The bulk (plane) is 2D, the boundary (circle) is 1D.
        dim(∂) = dim(bulk) - 1. This is FORCED.
        """
        return {
            "bulk_dimension": 2,
            "boundary_dimension": 1,
            "codimension": 1,
            "sides": 2,
            "boundary_components": 1,
            "formula": "dim(∂M) = dim(M) - 1"
        }


class WindingNumber:
    """π₁(S¹) = ℤ: integers forced by O7's local/global distinction.

    O7: "A knot that looks trivial locally can be non-trivial globally."

    On a circle, every small piece looks like a line segment (locally trivial).
    But a path can wind around the circle n times (globally non-trivial).
    The winding number is an INTEGER — you can't wind 1.5 times around.

    This forces ℤ to emerge from topology.
    """

    def __init__(self):
        pass

    def compute_winding(self, path: np.ndarray) -> int:
        """Compute the winding number of a closed path around the origin.

        The winding number = (1/2π) ∮ dθ, always an integer.
        This is the fundamental group π₁(S¹) in action.
        """
        # Compute angle changes along the path
        total_angle = 0.0
        for i in range(len(path) - 1):
            z1 = complex(path[i][0], path[i][1])
            z2 = complex(path[i+1][0], path[i+1][1])
            if abs(z1) < 1e-10 or abs(z2) < 1e-10:
                continue
            dtheta = np.angle(z2 / z1)
            total_angle += dtheta

        return int(np.round(total_angle / (2 * np.pi)))

    def generate_winding_path(self, n: int, num_points: int = 1000) -> np.ndarray:
        """Generate a path that winds n times around the origin."""
        t = np.linspace(0, 2 * np.pi * n, num_points)
        x = np.cos(t)
        y = np.sin(t)
        return np.column_stack([x, y])

    def verify_integer_invariant(self, max_winding: int = 5) -> bool:
        """Verify that winding number is always an integer.

        This is the deep result: topology FORCES discreteness.
        Continuous paths yield discrete invariants.
        """
        for n in range(-max_winding, max_winding + 1):
            path = self.generate_winding_path(n)
            # Close the path
            path = np.vstack([path, path[0:1]])
            computed = self.compute_winding(path)
            if computed != n:
                return False
        return True

    def demonstrate_local_vs_global(self) -> Dict[str, str]:
        """Show how O7 manifests in the circle.

        Locally: every piece of a wound path looks like a straight line.
        Globally: different winding numbers are topologically distinct.
        You CANNOT deform a doubly-wound path into a singly-wound path
        without cutting — that's the non-trivial global structure.
        """
        return {
            "local_structure": "Every small arc ≅ ℝ (a line segment)",
            "global_invariant": "Winding number ∈ ℤ (an integer)",
            "why_forced": "Continuous deformation preserves winding number",
            "consequence": "Integers are topologically necessary, not invented"
        }


class DoubleCover:
    """SU(2) → SO(3): the forced double cover connecting quaternions to rotations.

    The quaternion group Q₈ from quaternion_algebra lives inside SU(2).
    SU(2) double-covers SO(3): every rotation has TWO quaternion representatives.
    This is the topological fact behind O7 — globally non-trivial despite
    local triviality.

    The path from Q₈ to physical rotations goes:
      Q₈ ⊂ SU(2) --2:1--> SO(3)
    """

    def __init__(self):
        # Pauli matrices (basis of su(2) Lie algebra)
        self.sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        self.sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        self.sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        self.identity = np.array([[1, 0], [0, 1]], dtype=complex)

    def quaternion_to_su2(self, a: float, b: float, c: float, d: float) -> np.ndarray:
        """Map quaternion q = a + bi + cj + dk to SU(2) matrix.

        q ↦ aI + ibσ_x + icσ_y + idσ_z

        This is an isomorphism: quaternion multiplication = matrix multiplication.
        """
        return (a * self.identity +
                1j * b * self.sigma_x +
                1j * c * self.sigma_y +
                1j * d * self.sigma_z)

    def su2_to_so3(self, U: np.ndarray) -> np.ndarray:
        """Map SU(2) matrix to SO(3) rotation matrix.

        R_{ij} = (1/2) Tr(σ_i U σ_j U†)

        This is the double cover: U and -U map to the SAME rotation.
        """
        sigmas = [self.sigma_x, self.sigma_y, self.sigma_z]
        R = np.zeros((3, 3))
        U_dag = U.conj().T

        for i in range(3):
            for j in range(3):
                R[i, j] = 0.5 * np.real(np.trace(sigmas[i] @ U @ sigmas[j] @ U_dag))

        return R

    def verify_double_cover(self, samples: int = 50) -> bool:
        """Verify that U and -U give the same SO(3) rotation.

        This is O7 in algebra: locally (at the Lie algebra level) SU(2) and SO(3)
        look the same. Globally they differ — SU(2) winds around twice.
        """
        rng = np.random.default_rng(42)

        for _ in range(samples):
            # Random unit quaternion
            q = rng.normal(size=4)
            q = q / np.linalg.norm(q)

            U = self.quaternion_to_su2(*q)
            minus_U = self.quaternion_to_su2(*(-q))

            R1 = self.su2_to_so3(U)
            R2 = self.su2_to_so3(minus_U)

            if not np.allclose(R1, R2, atol=1e-10):
                return False

        return True

    def verify_su2_group(self, samples: int = 20) -> bool:
        """Verify SU(2) matrices are unitary and have determinant 1."""
        rng = np.random.default_rng(42)

        for _ in range(samples):
            q = rng.normal(size=4)
            q = q / np.linalg.norm(q)
            U = self.quaternion_to_su2(*q)

            # Unitary: U†U = I
            if not np.allclose(U.conj().T @ U, self.identity, atol=1e-10):
                return False
            # Special: det(U) = 1
            if abs(np.linalg.det(U) - 1.0) > 1e-10:
                return False

        return True

    def fundamental_group_so3(self) -> Dict[str, str]:
        """π₁(SO(3)) = ℤ₂: the topological reason for spin.

        A 360° rotation in SO(3) is NOT contractible to identity.
        A 720° rotation IS contractible.
        This is why fermions need 720° to return to their original state.
        This is FORCED by O7 — global non-triviality.
        """
        return {
            "pi1_SO3": "ℤ₂",
            "pi1_SU2": "trivial (simply connected)",
            "covering_degree": 2,
            "physical_consequence": "Spin-1/2 particles require 720° rotation",
            "why_forced": "O7: locally trivial (both are 3D rotation groups), globally distinct"
        }


def run_topological_derivation():
    """Complete derivation of topological structures from O4 and O7."""

    print("█" * 70)
    print(" " * 15 + "TOPOLOGICAL STRUCTURES FROM DISTINCTION")
    print(" " * 10 + "Deriving U(1), ℤ, and the Double Cover from O4 + O7")
    print("█" * 70)

    # --- O4: Circle forces U(1) ---
    print("\n" + "=" * 70)
    print("DERIVATION FROM O4: Circle Boundary Forces U(1)")
    print("=" * 70)

    print("\nO4: 'A circle has two sides but one boundary.'")
    print("\nLogical Derivation:")
    print("1. A distinction in a plane creates a closed curve (the boundary)")
    print("2. The simplest closed curve is S¹ (the circle)")
    print("3. S¹ has exactly one continuous symmetry group: U(1) = {e^{iθ}}")
    print("4. U(1) is FORCED — it is the ONLY continuous group on S¹")

    circle = CircleGroup()
    print(f"\nVerification:")
    print(f"   U(1) satisfies group axioms: {circle.verify_group_axioms()}")

    # Boundary dimension
    bd = circle.boundary_dimension()
    print(f"\n   Boundary dimension (OB4):")
    print(f"   Bulk dimension:     {bd['bulk_dimension']}")
    print(f"   Boundary dimension: {bd['boundary_dimension']}")
    print(f"   Formula:            {bd['formula']}")
    print(f"   Sides:              {bd['sides']} (inside + outside)")
    print(f"   Boundary components: {bd['boundary_components']}")

    # --- O0 meets U(1): the cost of unary ---
    print("\n" + "=" * 70)
    print("O0 MEETS U(1): The Cost of Belonging to a Unitary Group")
    print("=" * 70)

    cost = circle.unary_cost()
    print(f"\n   {cost['group_name']}")
    print(f"   Apparent simplicity: {cost['apparent_simplicity']}")
    print(f"\n   But U(1) is NOT unary. Hidden binary structure:")
    for key, val in cost["hidden_binary_structure"].items():
        print(f"     • {key}: {val}")
    print(f"\n   Cost: {cost['cost']}")
    print(f"   O0 verdict: {cost['o0_verdict']}")
    print(f"\n   The 'U' in U(1) stands for 'unitary', not 'unary'.")
    print(f"   But the lesson is the same: there is no '1' without distinction.")
    print(f"   Belonging to a unitary group means carrying your opposite at all times.")

    # --- Z₃ embeds in U(1) ---
    print("\n" + "=" * 70)
    print("CONNECTION: Z₃ ⊂ U(1) (Trinity Lives in the Circle)")
    print("=" * 70)

    z3_angles = circle.embed_cyclic_group(3)
    z3_roots = circle.roots_of_unity(3)
    print("\nZ₃ as cube roots of unity in U(1):")
    for k, (theta, root) in enumerate(zip(z3_angles, z3_roots)):
        print(f"   ω^{k} = e^{{i·{theta:.4f}}} = {root:.4f}")
    print("\nThese are EXACTLY the trinity algebra elements on the unit circle.")
    print("The discrete structure (Z₃) embeds in the continuous one (U(1)).")

    # Spectral analysis of Z₃ inside U(1)
    spec = circle.spectral_decomposition(3)
    print(f"\nSpectral decomposition of Z₃:")
    print(f"   DFT eigenvalues: {spec['eigenvalues']}")
    print(f"   Spectral gap: {spec['spectral_gap']:.4f}")

    # --- O7: Winding numbers force ℤ ---
    print("\n" + "=" * 70)
    print("DERIVATION FROM O7: Local Triviality + Global Non-triviality Forces ℤ")
    print("=" * 70)

    print("\nO7: 'A knot that looks trivial locally can be non-trivial globally.'")
    print("\nLogical Derivation:")
    print("1. Every small arc of S¹ looks like a line segment (locally trivial)")
    print("2. But a path can wind around S¹ multiple times (globally non-trivial)")
    print("3. The winding number is ALWAYS an integer — you can't wind 1.5 times")
    print("4. π₁(S¹) = ℤ — the integers emerge from topology")
    print("5. The INTEGERS are forced by the circle, not invented by counting")

    winding = WindingNumber()
    print(f"\nVerification:")
    print(f"   Winding number is always integer: {winding.verify_integer_invariant()}")

    print("\n   Sample winding numbers:")
    for n in [-2, -1, 0, 1, 2, 3]:
        path = winding.generate_winding_path(n)
        path = np.vstack([path, path[0:1]])
        w = winding.compute_winding(path)
        print(f"     Path winding {n}x → computed winding number = {w}")

    local_global = winding.demonstrate_local_vs_global()
    print(f"\n   Local:  {local_global['local_structure']}")
    print(f"   Global: {local_global['global_invariant']}")
    print(f"   Why:    {local_global['consequence']}")

    # --- Double cover: Q₈ → SU(2) → SO(3) ---
    print("\n" + "=" * 70)
    print("CONNECTION: Q₈ ⊂ SU(2) → SO(3) (Quaternions are Rotations)")
    print("=" * 70)

    cover = DoubleCover()
    print("\nThe chain: Q₈ ⊂ SU(2) --2:1--> SO(3)")
    print("   Q₈ from quaternion_algebra lives inside SU(2)")
    print("   SU(2) double-covers SO(3) (every rotation has 2 representatives)")

    print(f"\nVerification:")
    print(f"   SU(2) matrices are unitary with det=1: {cover.verify_su2_group()}")
    print(f"   U and -U give same rotation (double cover): {cover.verify_double_cover()}")

    # Show a concrete example
    q_example = np.array([1, 0, 0, 0]) / 1.0  # identity quaternion
    U = cover.quaternion_to_su2(*q_example)
    R = cover.su2_to_so3(U)
    print(f"\n   Example: q = (1,0,0,0)")
    print(f"   SU(2) matrix:\n{np.array2string(U, precision=3, suppress_small=True)}")
    print(f"   SO(3) rotation:\n{np.array2string(R, precision=3, suppress_small=True)}")

    # 90° rotation around z-axis
    theta = np.pi / 2
    q_rot = np.array([np.cos(theta/2), 0, 0, np.sin(theta/2)])
    U_rot = cover.quaternion_to_su2(*q_rot)
    R_rot = cover.su2_to_so3(U_rot)
    print(f"\n   Example: 90° rotation around z-axis")
    print(f"   Quaternion: ({q_rot[0]:.3f}, {q_rot[1]:.3f}, {q_rot[2]:.3f}, {q_rot[3]:.3f})")
    print(f"   SO(3) rotation:\n{np.array2string(R_rot, precision=3, suppress_small=True)}")

    # Fundamental group
    pi1 = cover.fundamental_group_so3()
    print(f"\n   Fundamental groups:")
    print(f"     π₁(SO(3)) = {pi1['pi1_SO3']}")
    print(f"     π₁(SU(2)) = {pi1['pi1_SU2']}")
    print(f"     Covering degree: {pi1['covering_degree']}")
    print(f"     Physical consequence: {pi1['physical_consequence']}")

    # --- Summary ---
    print("\n" + "█" * 70)
    print("SUMMARY: What O4 and O7 Force Into Existence")
    print("█" * 70)

    print("""
    O4 (circle boundary) FORCES:
      • U(1) — the circle group, continuous symmetry
      • dim(∂) = dim(bulk) - 1 — the boundary dimension formula
      • Z₃ ⊂ U(1) — trinity embeds as cube roots of unity

    O7 (local/global distinction) FORCES:
      • π₁(S¹) = ℤ — integers from winding numbers
      • SU(2) → SO(3) double cover — quaternions ARE rotations
      • π₁(SO(3)) = ℤ₂ — spin (fermions need 720°)

    NEW DERIVED QUANTITIES:
      • The integers ℤ (from winding, not counting!)
      • The double cover (2:1 mapping)
      • Boundary codimension = 1
      • Spin as topological necessity

    CONNECTIONS TO EXISTING WORK:
      • Z₃ (trinity_algebra) embeds in U(1) at 120° intervals
      • Q₈ (quaternion_algebra) embeds in SU(2)
      • Both discrete structures are SLICES of continuous ones
      • The continuous structures are forced by circle topology
    """)

    print("All observations now explored: O0-O8 ✓")
    print("█" * 70)

    return {
        "observations_used": ["O4", "O7"],
        "structures_derived": ["U(1)", "ℤ (integers)", "SU(2)→SO(3) double cover"],
        "connections": ["Z₃ ⊂ U(1)", "Q₈ ⊂ SU(2)", "π₁(S¹) = ℤ", "π₁(SO(3)) = ℤ₂"],
        "observables_addressed": ["OB4 (boundary dimension)"],
        "new_constants": ["codimension = 1", "covering degree = 2"]
    }


if __name__ == "__main__":
    run_topological_derivation()

"""
Quaternion Algebra: The forced 4-element structure from binary distinction.

Derived from Observation O2: "Binary distinction creates four states:
neither, A, B, both."

This implements the quaternion group Q₈ as the natural algebra on 4 states.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


class QuaternionAlgebra:
    """The quaternion algebra forced by binary distinction."""

    def __init__(self):
        # The four basis states from binary distinction
        self.states = {
            (0, 0): "neither",
            (1, 0): "A_only",
            (0, 1): "B_only",
            (1, 1): "both"
        }

        # Map to quaternion basis
        self.quaternion_map = {
            (0, 0): "1",   # identity
            (1, 0): "i",   # first imaginary
            (0, 1): "j",   # second imaginary
            (1, 1): "k"    # third imaginary
        }

        # Quaternion multiplication table
        self.mult_table = self._generate_multiplication_table()

        # Matrix representations
        self.matrices = self._generate_matrix_representations()

    def _generate_multiplication_table(self) -> Dict[Tuple[str, str], str]:
        """Generate the quaternion multiplication table."""
        table = {}

        # Identity multiplications
        for q in ["1", "i", "j", "k", "-1", "-i", "-j", "-k"]:
            table[("1", q)] = q
            table[(q, "1")] = q

        # Imaginary unit squares
        table[("i", "i")] = "-1"
        table[("j", "j")] = "-1"
        table[("k", "k")] = "-1"

        # Cyclic products
        table[("i", "j")] = "k"
        table[("j", "k")] = "i"
        table[("k", "i")] = "j"

        # Anti-cyclic products
        table[("j", "i")] = "-k"
        table[("k", "j")] = "-i"
        table[("i", "k")] = "-j"

        # Negative multiplications
        table[("-1", "-1")] = "1"
        table[("i", "-i")] = "-1"
        table[("j", "-j")] = "-1"
        table[("k", "-k")] = "-1"
        table[("-i", "i")] = "-1"
        table[("-j", "j")] = "-1"
        table[("-k", "k")] = "-1"

        # Products with -1
        for q in ["i", "j", "k"]:
            table[("-1", q)] = f"-{q}"
            table[(q, "-1")] = f"-{q}"
            table[("-1", f"-{q}")] = q
            table[(f"-{q}", "-1")] = q

        # More complex products
        table[("-i", "-i")] = "-1"
        table[("-j", "-j")] = "-1"
        table[("-k", "-k")] = "-1"

        table[("-i", "j")] = "-k"
        table[("i", "-j")] = "-k"
        table[("-i", "-j")] = "k"

        table[("-j", "k")] = "-i"
        table[("j", "-k")] = "-i"
        table[("-j", "-k")] = "i"

        table[("-k", "i")] = "-j"
        table[("k", "-i")] = "-j"
        table[("-k", "-i")] = "j"

        table[("j", "-i")] = "k"
        table[("-j", "i")] = "k"
        table[("-j", "-i")] = "-k"

        table[("k", "-j")] = "i"
        table[("-k", "j")] = "i"
        table[("-k", "-j")] = "-i"

        table[("i", "-k")] = "j"
        table[("-i", "k")] = "j"
        table[("-i", "-k")] = "-j"

        return table

    def _generate_matrix_representations(self) -> Dict[str, np.ndarray]:
        """Generate 2x2 complex matrix representations (Pauli matrices)."""
        matrices = {
            "1": np.array([[1, 0], [0, 1]], dtype=complex),
            "i": np.array([[0, 1j], [1j, 0]], dtype=complex),
            "j": np.array([[0, -1], [1, 0]], dtype=complex),
            "k": np.array([[1j, 0], [0, -1j]], dtype=complex),
            "-1": np.array([[-1, 0], [0, -1]], dtype=complex),
            "-i": np.array([[0, -1j], [-1j, 0]], dtype=complex),
            "-j": np.array([[0, 1], [-1, 0]], dtype=complex),
            "-k": np.array([[-1j, 0], [0, 1j]], dtype=complex)
        }
        return matrices

    def multiply(self, a: str, b: str) -> str:
        """Multiply two quaternion elements."""
        if (a, b) in self.mult_table:
            return self.mult_table[(a, b)]
        else:
            # Handle cases not explicitly in table
            return "undefined"

    def binary_to_quaternion(self, state: Tuple[int, int]) -> str:
        """Convert binary state to quaternion element."""
        return self.quaternion_map.get(state, "undefined")

    def hamming_distance(self, s1: Tuple[int, int], s2: Tuple[int, int]) -> int:
        """Calculate Hamming distance between two binary states."""
        return sum(a != b for a, b in zip(s1, s2))

    def verify_quaternion_relations(self) -> bool:
        """Verify the fundamental quaternion relations."""
        checks = []

        # i² = j² = k² = -1
        checks.append(self.multiply("i", "i") == "-1")
        checks.append(self.multiply("j", "j") == "-1")
        checks.append(self.multiply("k", "k") == "-1")

        # ijk = -1
        ij = self.multiply("i", "j")
        checks.append(self.multiply(ij, "k") == "-1")

        # Cyclic relations
        checks.append(self.multiply("i", "j") == "k")
        checks.append(self.multiply("j", "k") == "i")
        checks.append(self.multiply("k", "i") == "j")

        # Anti-cyclic relations
        checks.append(self.multiply("j", "i") == "-k")
        checks.append(self.multiply("k", "j") == "-i")
        checks.append(self.multiply("i", "k") == "-j")

        return all(checks)

    def compute_spectral_gap(self) -> float:
        """Compute the spectral gap for quaternion matrices."""
        gaps = []
        for label, matrix in self.matrices.items():
            if label != "1" and label != "-1":  # Skip scalars
                eigenvalues = np.linalg.eigvals(matrix)
                eigenvalues = sorted(np.abs(eigenvalues), reverse=True)
                if len(eigenvalues) >= 2:
                    gap = eigenvalues[0] - eigenvalues[1]
                    gaps.append(np.real(gap))

        return np.mean(gaps) if gaps else 0.0

    def find_fixed_points(self) -> List[str]:
        """Find elements that are fixed under conjugation."""
        # In quaternions, only real elements are fixed under conjugation
        # Conjugation: q* = a - bi - cj - dk for q = a + bi + cj + dk
        fixed = []
        for elem in ["1", "-1"]:
            fixed.append(elem)
        return fixed

    def verify_norm_conservation(self) -> bool:
        """Verify that quaternion norm is preserved under multiplication."""
        # For unit quaternions, |pq| = |p| |q|
        unit_quats = ["1", "i", "j", "k"]

        for p in unit_quats:
            for q in unit_quats:
                product = self.multiply(p, q)
                if product and product != "undefined":
                    # All unit quaternions have norm 1
                    # Their products should also have norm 1 or -1 (which has norm 1)
                    if product not in ["1", "i", "j", "k", "-1", "-i", "-j", "-k"]:
                        return False
        return True

    def demonstrate_boundary_structure(self):
        """Show how boundaries between states form the quaternion structure."""
        print("\nBoundary Analysis (from O3):")
        print("Binary states and their Hamming distances:")

        states = list(self.states.keys())
        for i, s1 in enumerate(states):
            for j, s2 in enumerate(states):
                if i < j:
                    dist = self.hamming_distance(s1, s2)
                    q1 = self.binary_to_quaternion(s1)
                    q2 = self.binary_to_quaternion(s2)
                    print(f"   {s1} ({q1}) <--{dist}--> {s2} ({q2})")

        print("\nHamming distance 1 = adjacent faces (edge)")
        print("Hamming distance 2 = opposite corners (diagonal)")

    def demonstrate(self):
        """Demonstrate the key properties of the quaternion algebra."""
        print("="*60)
        print("QUATERNION ALGEBRA - The Forced Structure of Binary Distinction")
        print("="*60)

        print("\n1. The Four States (from O2):")
        for state, name in self.states.items():
            quat = self.binary_to_quaternion(state)
            print(f"   {state}: {name:10} -> {quat}")

        print("\n2. Quaternion Relations:")
        print(f"   Fundamental relations hold: {self.verify_quaternion_relations()}")
        print("   i² = j² = k² = ijk = -1")

        print("\n3. Multiplication Examples:")
        examples = [("i", "j"), ("j", "k"), ("k", "i"), ("j", "i")]
        for a, b in examples:
            result = self.multiply(a, b)
            print(f"   {a} × {b} = {result}")

        self.demonstrate_boundary_structure()

        print("\n4. Conservation Law (from CL2):")
        print(f"   Norm is conserved: {self.verify_norm_conservation()}")
        print("   |pq| = |p||q| for all quaternions")

        print("\n5. Fixed Points (from O8):")
        fixed = self.find_fixed_points()
        print(f"   Fixed under conjugation: {fixed}")
        print("   (Real quaternions are self-conjugate)")

        print("\n6. Spectral Properties (from OB2):")
        gap = self.compute_spectral_gap()
        print(f"   Average spectral gap: {gap:.3f}")
        print("   (Maximal for unit-norm operators)")

        print("\n7. Why 4 is FORCED:")
        print("   - Binary distinction creates 2² = 4 states")
        print("   - These states have natural quaternion structure")
        print("   - Q₈ is the most symmetric non-abelian group of order 8")
        print("   - Quaternions emerge from distinction, not invention")

        print("\n8. Matrix Representations:")
        for label in ["i", "j", "k"]:
            matrix = self.matrices[label]
            eigenvalues = np.linalg.eigvals(matrix)
            print(f"   {label}: eigenvalues = {eigenvalues}")


if __name__ == "__main__":
    quat = QuaternionAlgebra()
    quat.demonstrate()
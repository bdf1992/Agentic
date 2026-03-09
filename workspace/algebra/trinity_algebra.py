"""
Trinity Algebra: The forced 3-element structure from distinction.

Derived from Observation O1: "Defining one thing creates three:
the thing, its complement, and the distinction itself."

This implements Z₃ as the minimal algebraic structure of distinction.
"""

import numpy as np
from typing import Dict, List, Tuple


class TrinityAlgebra:
    """The 3-element algebra forced by making a single distinction."""

    def __init__(self):
        # The three elements: thing (0), complement (1), distinction (2)
        self.elements = [0, 1, 2]

        # Labels for clarity
        self.labels = {
            0: "thing",
            1: "complement",
            2: "distinction"
        }

        # The distinction operator: rotate through the three states
        self.distinction_map = {
            0: 1,  # thing -> complement
            1: 2,  # complement -> distinction
            2: 0   # distinction -> thing (cycles back)
        }

        # Addition table (group operation)
        self.add_table = self._generate_add_table()

        # Multiplication table (ring structure)
        self.mult_table = self._generate_mult_table()

    def _generate_add_table(self) -> Dict[Tuple[int, int], int]:
        """Generate the addition table for Z₃."""
        table = {}
        for a in self.elements:
            for b in self.elements:
                table[(a, b)] = (a + b) % 3
        return table

    def _generate_mult_table(self) -> Dict[Tuple[int, int], int]:
        """Generate the multiplication table for Z₃."""
        table = {}
        for a in self.elements:
            for b in self.elements:
                table[(a, b)] = (a * b) % 3
        return table

    def distinguish(self, element: int) -> int:
        """Apply the distinction operator."""
        return self.distinction_map[element]

    def generate_states(self):
        """Generate all states in Z₃."""
        return self.elements.copy()

    def distinction_operator(self, state: int) -> int:
        """Apply the distinction operator to a state."""
        return self.distinction_map[state]

    def power_of_distinction(self, n: int) -> Dict[int, int]:
        """Show what happens when we apply distinction n times."""
        result = {}
        for elem in self.elements:
            current = elem
            for _ in range(n):
                current = self.distinguish(current)
            result[elem] = current
        return result

    def verify_group_axioms(self) -> bool:
        """Verify that this forms a group under addition."""
        # Check closure
        for a in self.elements:
            for b in self.elements:
                if self.add_table[(a, b)] not in self.elements:
                    return False

        # Check associativity
        for a in self.elements:
            for b in self.elements:
                for c in self.elements:
                    left = self.add_table[(self.add_table[(a, b)], c)]
                    right = self.add_table[(a, self.add_table[(b, c)])]
                    if left != right:
                        return False

        # Check identity (0)
        for a in self.elements:
            if self.add_table[(0, a)] != a or self.add_table[(a, 0)] != a:
                return False

        # Check inverses
        for a in self.elements:
            has_inverse = False
            for b in self.elements:
                if self.add_table[(a, b)] == 0:
                    has_inverse = True
                    break
            if not has_inverse:
                return False

        return True

    def get_matrix_representation(self) -> Dict[int, np.ndarray]:
        """Get the matrix representation of the trinity algebra."""
        # Represent as 3x3 permutation matrices
        matrices = {
            0: np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),  # identity
            1: np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]]),  # rotation
            2: np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]])   # rotation²
        }
        return matrices

    def spectral_analysis(self) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """Compute eigenvalues and eigenvectors for each element."""
        matrices = self.get_matrix_representation()
        spectra = {}

        for elem, matrix in matrices.items():
            eigenvalues, eigenvectors = np.linalg.eig(matrix)
            spectra[elem] = (eigenvalues, eigenvectors)

        return spectra

    def verify_conservation_law(self) -> bool:
        """Verify that Z₃ charge is conserved under addition."""
        # Total "charge" modulo 3 should be conserved
        for a in self.elements:
            for b in self.elements:
                sum_before = (a + b) % 3
                sum_after = self.add_table[(a, b)]
                if sum_before != sum_after:
                    return False
        return True

    def find_fixed_points(self) -> List[int]:
        """Find fixed points under the distinction operator."""
        fixed_points = []
        for elem in self.elements:
            if self.distinguish(elem) == elem:
                fixed_points.append(elem)
        return fixed_points

    def demonstrate(self):
        """Demonstrate the key properties of the trinity algebra."""
        print("="*60)
        print("TRINITY ALGEBRA - The Forced Structure of Distinction")
        print("="*60)

        print("\n1. The Three Elements (from O1):")
        for elem in self.elements:
            print(f"   {elem}: {self.labels[elem]}")

        print("\n2. The Distinction Operator:")
        for elem in self.elements:
            result = self.distinguish(elem)
            print(f"   ∂({self.labels[elem]}) = {self.labels[result]}")

        print("\n3. Powers of Distinction:")
        for n in [1, 2, 3]:
            print(f"   ∂^{n} = {self.power_of_distinction(n)}")
        print("   Notice: ∂³ = identity (returns everything to itself)")

        print("\n4. Group Structure Verification:")
        print(f"   Forms a valid group: {self.verify_group_axioms()}")

        print("\n5. Conservation Law:")
        print(f"   Z₃ charge is conserved: {self.verify_conservation_law()}")

        print("\n6. Fixed Points (from O8):")
        fixed = self.find_fixed_points()
        if fixed:
            print(f"   Fixed points under ∂: {fixed}")
        else:
            print("   No fixed points (distinction cycles through all states)")

        print("\n7. Spectral Properties:")
        spectra = self.spectral_analysis()
        for elem in self.elements:
            eigenvalues = spectra[elem][0]
            print(f"   Element {elem} eigenvalues: {eigenvalues}")

        print("\n8. Why 3 is FORCED:")
        print("   - Making ONE distinction creates THREE things")
        print("   - The distinction operator has order 3")
        print("   - This is the minimal non-trivial cyclic group")
        print("   - The number 3 emerges from logic, not choice")


if __name__ == "__main__":
    trinity = TrinityAlgebra()
    trinity.demonstrate()
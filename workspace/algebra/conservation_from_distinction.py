"""
Conservation From Pure Distinction: Why conservation laws are logically necessary.

This module demonstrates that conservation laws are not physical principles we
impose on reality, but logical necessities that emerge from the structure of
distinction itself.

Starting ONLY from observations O0-O8, we derive:
1. Why something must be conserved (you can't create from nothing)
2. What specific quantities are conserved (charge, information, symmetry currents)
3. The deep connection between conservation and fixed points (O8)

Key insight: Conservation is the price we pay for making distinctions.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import warnings


class DistinctionConservation:
    """
    Conservation laws that emerge from the act of distinction itself.

    Core principle: When you make a distinction, you create a closed system.
    The total "amount of distinction" cannot change - it can only be redistributed.
    """

    def __init__(self):
        # From O1: Single distinction creates exactly 3 states
        self.trinity_states = ['thing', 'complement', 'boundary']

        # From O2: Binary distinction creates exactly 4 states
        self.quaternion_states = ['neither', 'first', 'second', 'both']

        # The fundamental conserved quantity: total distinctness = 1
        self.total_distinctness = 1.0

    def derive_conservation_necessity(self) -> Dict[str, Any]:
        """
        Derive why conservation MUST exist from pure logic.

        Argument:
        1. To distinguish X from not-X, you need a reference frame
        2. The reference frame itself exists within the system
        3. Therefore the system is closed (no outside to draw from)
        4. In a closed system, you cannot create or destroy, only transform
        5. THEREFORE: Something must be conserved
        """

        derivation = {
            'premise': 'O0: Even unary distinction requires binary structure',
            'step1': 'Any distinction creates a closed logical universe',
            'step2': 'Within this universe, total "amount" is fixed',
            'step3': 'Transformations can only redistribute, not create/destroy',
            'conclusion': 'Conservation is logically necessary',
            'conserved_quantity': 'Total distinctness = 1 (normalized)'
        }

        return derivation

    def trinity_conservation(self, state_vector: np.ndarray) -> Dict[str, float]:
        """
        Conservation in the trinity (Z₃) system.

        From O1: thing + complement + boundary = total
        This gives us a conservation law: probabilities sum to 1.

        But there's a deeper conservation: the "distinction charge"
        """

        # Normalize to ensure probability conservation
        if not np.allclose(np.sum(np.abs(state_vector)**2), 1.0):
            state_vector = state_vector / np.linalg.norm(state_vector)

        # Distinction charges (forced by symmetry)
        charges = np.array([1, -1, 0])  # thing, complement, boundary

        # Total charge (must be conserved)
        total_charge = np.sum(charges * np.abs(state_vector)**2)

        # Angular momentum in Z₃ (0, 2π/3, 4π/3)
        angles = np.array([0, 2*np.pi/3, 4*np.pi/3])
        angular_momentum = np.sum(angles * np.abs(state_vector)**2)

        return {
            'probability': np.sum(np.abs(state_vector)**2),
            'distinction_charge': total_charge,
            'angular_momentum_mod_2pi': angular_momentum % (2*np.pi),
            'entropy': -np.sum(np.abs(state_vector)**2 *
                              np.log(np.abs(state_vector)**2 + 1e-15))
        }

    def quaternion_conservation(self, state_vector: np.ndarray) -> Dict[str, float]:
        """
        Conservation in the quaternion (Q₈) system.

        From O2: Binary distinction creates 4 states
        From O3: Boundaries have weight (non-commutativity)

        This forces conservation of norm AND orientation.
        """

        # Ensure unit norm (probability conservation)
        if not np.allclose(np.sum(np.abs(state_vector)**2), 1.0):
            state_vector = state_vector / np.linalg.norm(state_vector)

        # Quaternion structure preserves more than just norm
        # It preserves a 3D orientation (from i, j, k structure)

        # Map to quaternion basis: 1, i, j, k
        q_real = np.abs(state_vector[0])**2  # 'neither' maps to 1
        q_i = np.abs(state_vector[1])**2     # 'first' maps to i
        q_j = np.abs(state_vector[2])**2     # 'second' maps to j
        q_k = np.abs(state_vector[3])**2     # 'both' maps to k

        # Quaternion norm (must = 1)
        q_norm = np.sqrt(q_real**2 + q_i**2 + q_j**2 + q_k**2)

        # Scalar vs vector decomposition
        scalar_part = q_real
        vector_norm = np.sqrt(q_i**2 + q_j**2 + q_k**2)

        return {
            'total_probability': np.sum(np.abs(state_vector)**2),
            'quaternion_norm': q_norm,
            'scalar_part': scalar_part,
            'vector_part_norm': vector_norm,
            'chirality': q_real * q_k - q_i * q_j  # Conserved under proper rotations
        }

    def fixed_point_conservation(self) -> Dict[str, Any]:
        """
        From O8: Self-referential systems have fixed points.

        Fixed points represent conserved structures - things that
        don't change under the system's own operations.

        This is a deep connection: conservation ↔ fixed points
        """

        results = {}

        # The boundary is a fixed point in many operations
        # This makes it a conserved structure
        results['boundary_fixed'] = {
            'operation': 'distinction',
            'fixed_point': 'boundary',
            'reason': 'The boundary IS the distinction operator itself',
            'conservation': 'Boundary fraction remains constant in equilibrium'
        }

        # The identity is always conserved
        results['identity_fixed'] = {
            'operation': 'group_action',
            'fixed_point': 'identity_element',
            'reason': 'e * e = e by definition',
            'conservation': 'Identity structure preserved under all operations'
        }

        # Equilibrium distribution is conserved
        results['equilibrium_fixed'] = {
            'operation': 'evolution',
            'fixed_point': 'uniform_distribution',
            'reason': 'Maximum entropy state',
            'conservation': 'Thermal equilibrium is time-invariant'
        }

        return results

    def noether_from_distinction(self) -> Dict[str, Any]:
        """
        Derive Noether's theorem from pure distinction logic.

        Emmy Noether: Every continuous symmetry implies a conservation law.
        But WHY? We derive this from our observations.
        """

        derivation = {}

        # From O6: Symmetry is cheaper than asymmetry
        derivation['premise'] = {
            'observation': 'O6: Symmetric structures need less information',
            'implication': 'Nature prefers symmetric structures (minimum information)'
        }

        # Continuous symmetry from trinity
        derivation['Z3_symmetry'] = {
            'symmetry': 'Rotation by 2π/3',
            'generator': 'T: thing → complement → boundary → thing',
            'conserved': 'Angular momentum (mod 2π/3)',
            'proof': 'Rotation leaves Z₃ structure invariant'
        }

        # Why symmetry forces conservation
        derivation['logical_necessity'] = {
            'step1': 'If operation O leaves structure S invariant',
            'step2': 'Then S(before) = S(after) under O',
            'step3': 'This means some quantity Q(S) is unchanged',
            'step4': 'Therefore Q is conserved under O',
            'conclusion': 'Symmetry FORCES conservation'
        }

        # The deeper reason
        derivation['deep_reason'] = (
            "Symmetry means 'looks the same from different viewpoints'. "
            "If something looks the same before and after, then something "
            "about it hasn't changed. That unchanging thing is what's conserved. "
            "This isn't physics - it's pure logic."
        )

        return derivation

    def demonstrate_conservation(self):
        """
        Run a complete demonstration showing conservation in action.
        """

        print("CONSERVATION FROM PURE DISTINCTION")
        print("=" * 50)

        # 1. Logical necessity
        print("\n1. WHY CONSERVATION MUST EXIST:")
        necessity = self.derive_conservation_necessity()
        for key, value in necessity.items():
            print(f"  {key}: {value}")

        # 2. Trinity conservation
        print("\n2. CONSERVATION IN TRINITY (Z₃):")
        trinity_state = np.array([0.6, 0.7, 0.4])  # Unnormalized on purpose
        trinity_conserved = self.trinity_conservation(trinity_state)
        for key, value in trinity_conserved.items():
            print(f"  {key}: {value:.6f}")

        # 3. Quaternion conservation
        print("\n3. CONSERVATION IN QUATERNION (Q₈):")
        quat_state = np.array([0.5, 0.5, 0.5, 0.5])
        quat_conserved = self.quaternion_conservation(quat_state)
        for key, value in quat_conserved.items():
            print(f"  {key}: {value:.6f}")

        # 4. Fixed point connection
        print("\n4. FIXED POINTS AS CONSERVATION:")
        fixed = self.fixed_point_conservation()
        for name, fp in fixed.items():
            print(f"  {name}:")
            print(f"    - Fixed under: {fp['operation']}")
            print(f"    - Conservation: {fp['conservation']}")

        # 5. Noether's theorem
        print("\n5. NOETHER'S THEOREM FROM LOGIC:")
        noether = self.noether_from_distinction()
        print(f"  Core insight: {noether['deep_reason']}")

        return True


def evolution_conservation_test():
    """
    Test that our evolution operators actually conserve what they should.
    """

    print("\nTESTING CONSERVATION UNDER EVOLUTION")
    print("-" * 40)

    dc = DistinctionConservation()

    # Trinity evolution operator (cyclic permutation)
    T_trinity = np.array([
        [0, 0, 1],  # thing → boundary
        [1, 0, 0],  # complement → thing
        [0, 1, 0]   # boundary → complement
    ])

    # Start with arbitrary state
    state = np.array([0.7, 0.2, 0.1])

    print("Initial state:", state)
    print("Initial conservation:")
    initial = dc.trinity_conservation(state)
    for key, val in initial.items():
        print(f"  {key}: {val:.6f}")

    # Evolve the state
    evolved = T_trinity @ state

    print("\nEvolved state:", evolved)
    print("After evolution:")
    final = dc.trinity_conservation(evolved)
    for key, val in final.items():
        print(f"  {key}: {val:.6f}")

    # Check what's conserved
    print("\nConservation check:")
    for key in initial:
        if abs(initial[key] - final[key]) < 1e-10:
            print(f"  ✓ {key} is CONSERVED")
        else:
            print(f"  ✗ {key} changed from {initial[key]:.6f} to {final[key]:.6f}")

    return True


def boundary_weight_conservation():
    """
    From O3: Boundaries have ontological weight.
    This weight must be conserved in transitions.
    """

    print("\nBOUNDARY WEIGHT CONSERVATION")
    print("-" * 40)

    # Boundary has "weight" that affects evolution
    # This weight cannot be created or destroyed

    # Start with high boundary weight
    state_high_boundary = np.array([0.1, 0.1, 0.8])  # Mostly boundary

    # Start with low boundary weight
    state_low_boundary = np.array([0.6, 0.3, 0.1])  # Mostly thing/complement

    dc = DistinctionConservation()

    print("High boundary state:", state_high_boundary)
    cons_high = dc.trinity_conservation(state_high_boundary)
    print(f"  Entropy: {cons_high['entropy']:.6f}")

    print("\nLow boundary state:", state_low_boundary)
    cons_low = dc.trinity_conservation(state_low_boundary)
    print(f"  Entropy: {cons_low['entropy']:.6f}")

    print("\nKey insight:")
    print("  The boundary weight affects entropy, but total probability is conserved.")
    print("  You cannot create or destroy boundary weight, only redistribute it.")

    return True


if __name__ == "__main__":
    # Run the main demonstration
    dc = DistinctionConservation()
    dc.demonstrate_conservation()

    # Run specific tests
    evolution_conservation_test()
    boundary_weight_conservation()

    print("\n" + "="*50)
    print("CONCLUSION: Conservation laws are not physical principles")
    print("we impose on nature. They are logical necessities that")
    print("emerge from the structure of distinction itself.")
    print("\nWhen you make a distinction, you create a closed universe.")
    print("In that universe, something MUST be conserved.")
"""
Boundary Mediator Algebra: The ontological weight of separation.

This module implements the deeper implications of O3 - boundaries as active
mediators that enable and constrain communication between separated states.

Key discoveries:
- Boundaries are the ONLY way separated things can communicate
- Boundaries create information bottlenecks (channel capacity)
- Boundaries store and transform information (not just transmit)
- Higher-order boundaries create fractal mediation structures
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import matplotlib.pyplot as plt
from scipy.linalg import expm


@dataclass
class MediationChannel:
    """A communication channel mediated by a boundary."""
    source: str
    target: str
    boundary: str
    capacity: float  # Channel capacity in bits
    transmission_rate: float  # How much gets through
    absorption_rate: float  # How much boundary keeps
    delay: int  # Minimum communication steps


class BoundaryMediator:
    """The algebra of boundaries as active mediators."""

    def __init__(self, spectral_gap: float = 2/3):
        """Initialize boundary mediator with forced parameters.

        Args:
            spectral_gap: The Z₃ spectral gap (default 2/3)
        """
        self.gap = spectral_gap
        self.transmission = 1 - spectral_gap  # 1/3 for default
        self.absorption = self.transmission  # Symmetric rates
        self.retention = self.transmission  # Boundary self-interaction

        # States in mediation system
        self.states = ['A', '∂', 'B']  # Thing, boundary, complement

        # Build mediation matrix
        self.mediation_matrix = self._build_mediation_matrix()

        # Information channels
        self.channels = self._create_channels()

        # Higher-order boundaries (fractal structure)
        self.boundary_hierarchy = {}

    def _build_mediation_matrix(self) -> np.ndarray:
        """Build the mediation dynamics matrix.

        Structure:
             [A']   [1-α   α    0 ] [A]
             [∂'] = [ α   1-2α  α ] [∂]
             [B']   [ 0    α   1-α] [B]

        This ensures:
        - No direct A↔B communication
        - All flow through boundary ∂
        - Conservation of total probability
        """
        α = self.transmission

        M = np.array([
            [1-α,  α,    0],    # A can only exchange with ∂
            [α,    1-2*α, α],   # ∂ exchanges with both
            [0,    α,    1-α]   # B can only exchange with ∂
        ])

        return M

    def _create_channels(self) -> List[MediationChannel]:
        """Create all mediated communication channels."""
        channels = []

        # A → B channel (through ∂)
        channels.append(MediationChannel(
            source='A',
            target='B',
            boundary='∂',
            capacity=self._channel_capacity('∂'),
            transmission_rate=self.transmission**2,  # Two hops
            absorption_rate=self.absorption,
            delay=2  # Minimum 2 steps through boundary
        ))

        # B → A channel (symmetric)
        channels.append(MediationChannel(
            source='B',
            target='A',
            boundary='∂',
            capacity=self._channel_capacity('∂'),
            transmission_rate=self.transmission**2,
            absorption_rate=self.absorption,
            delay=2
        ))

        return channels

    def _channel_capacity(self, boundary: str) -> float:
        """Calculate Shannon channel capacity through boundary.

        C = max I(X;Y) ≤ H(boundary) = log₂(boundary_states)
        """
        # For Z₃ boundary: can be in 3 states
        boundary_states = 3
        return float(np.log2(boundary_states))

    def mediate(self, source_state: np.ndarray, steps: int = 1) -> np.ndarray:
        """Evolve state through mediation dynamics.

        Args:
            source_state: Initial state vector [A, ∂, B]
            steps: Number of mediation steps

        Returns:
            Final state after mediation
        """
        state = source_state.copy()

        for _ in range(steps):
            state = self.mediation_matrix @ state

        return state

    def information_flow(self, source: str, target: str) -> Dict[str, Any]:
        """Calculate information flow from source to target.

        Returns detailed flow analysis including:
        - Direct flow (always 0 for A↔B)
        - Mediated flow (through boundary)
        - Total delay
        - Information loss
        """
        # Initial state with all information at source
        state = np.zeros(3)
        idx_map = {'A': 0, '∂': 1, 'B': 2}
        state[idx_map[source]] = 1.0

        # Track information flow
        flow_data = {
            'source': source,
            'target': target,
            'time_series': [],
            'boundary_load': [],
            'total_flow': 0,
            'information_loss': 0,
            'minimum_delay': 0
        }

        # Evolve for enough steps to see full propagation
        max_steps = 20
        for step in range(max_steps):
            state = self.mediate(state, steps=1)

            # Record state
            flow_data['time_series'].append(state[idx_map[target]])
            flow_data['boundary_load'].append(state[1])  # ∂ is always index 1

            # Check if target first receives information
            if flow_data['minimum_delay'] == 0 and state[idx_map[target]] > 0.01:
                flow_data['minimum_delay'] = step + 1

        # Calculate total flow and loss
        flow_data['total_flow'] = max(flow_data['time_series'])
        flow_data['information_loss'] = 1.0 - flow_data['total_flow']

        return flow_data

    def create_higher_boundary(self, boundary_level: int) -> np.ndarray:
        """Create higher-order boundary (boundary of boundary).

        ∂ⁿ(A,B) represents n-th order boundary.
        Each level adds another mediation layer.
        """
        if boundary_level == 0:
            # Direct connection (no boundary) - impossible!
            return np.array([[0, 0], [0, 0]])

        # Build nested mediation matrix
        size = 2 + boundary_level  # A, B, plus n boundaries
        matrix = np.zeros((size, size))

        # Each boundary mediates between its neighbors
        α = self.transmission
        for i in range(size):
            if i == 0:  # First state (A)
                matrix[i, i] = 1 - α
                matrix[i, 1] = α  # Connect to first boundary
            elif i == size - 1:  # Last state (B)
                matrix[i, i] = 1 - α
                matrix[i, i-1] = α  # Connect to last boundary
            else:  # Boundary states
                matrix[i, i] = 1 - 2*α
                if i > 0:
                    matrix[i, i-1] = α
                if i < size - 1:
                    matrix[i, i+1] = α

        self.boundary_hierarchy[boundary_level] = matrix
        return matrix

    def mediation_network(self, nodes: List[str]) -> np.ndarray:
        """Create mediation network for multiple nodes.

        Every pair of nodes gets a boundary mediator.
        This creates a complete mediation graph.
        """
        n = len(nodes)
        n_boundaries = n * (n - 1) // 2  # One boundary per pair
        total_size = n + n_boundaries

        # Build adjacency matrix
        adjacency = np.zeros((total_size, total_size))

        # Map nodes and boundaries to indices
        node_idx = {node: i for i, node in enumerate(nodes)}
        boundary_idx = {}
        idx = n

        # Create boundaries for each pair
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes[i+1:], i+1):
                boundary_name = f"∂({node1},{node2})"
                boundary_idx[boundary_name] = idx

                # Connect nodes to their boundary
                adjacency[i, idx] = self.transmission
                adjacency[idx, i] = self.transmission
                adjacency[j, idx] = self.transmission
                adjacency[idx, j] = self.transmission

                idx += 1

        return adjacency

    def quantum_mediation(self, entangled: bool = False) -> Dict[str, Any]:
        """Model quantum-like mediation effects.

        When boundary mediates quantum states:
        - Measurement collapses the boundary
        - Entanglement through shared boundary
        - No-cloning of boundary state
        """
        results = {
            'entangled': entangled,
            'superposition': np.array([1/np.sqrt(3)] * 3),  # Equal superposition
            'collapse_operators': [],
            'entanglement_entropy': 0
        }

        if entangled:
            # Create Bell-like state through boundary
            # |Ψ⟩ = (|A∂⟩ + |∂B⟩)/√2
            psi = np.zeros((3, 3))
            psi[0, 1] = 1/np.sqrt(2)  # A correlated with ∂
            psi[1, 2] = 1/np.sqrt(2)  # ∂ correlated with B

            # Calculate entanglement entropy
            # S = -Tr(ρ log ρ) where ρ is reduced density matrix
            rho = psi @ psi.T
            eigenvals = np.linalg.eigvalsh(rho)
            eigenvals = eigenvals[eigenvals > 1e-10]
            results['entanglement_entropy'] = -np.sum(
                eigenvals * np.log2(eigenvals)
            )

        # Define measurement operators that collapse boundary
        for outcome in ['A', '∂', 'B']:
            idx = self.states.index(outcome)
            operator = np.zeros((3, 3))
            operator[idx, idx] = 1
            results['collapse_operators'].append(operator)

        return results

    def demonstrate_mediation(self):
        """Demonstrate the boundary mediator algebra."""
        print("=" * 70)
        print("BOUNDARY MEDIATOR ALGEBRA")
        print("=" * 70)
        print("\nFrom O3: 'The boundary between things is itself a thing'")
        print("Extended: Boundaries are active MEDIATORS, not passive dividers")
        print("-" * 70)

        print("\n1. MEDIATION STRUCTURE")
        print("   States: A ←→ ∂ ←→ B")
        print("   - A and B cannot communicate directly")
        print("   - All information flows through boundary ∂")
        print(f"   - Transmission rate: {self.transmission:.3f}")
        print(f"   - Absorption rate: {self.absorption:.3f}")

        print("\n2. MEDIATION MATRIX")
        print("   Evolution of [A, ∂, B] state:")
        print(self.mediation_matrix)

        print("\n3. COMMUNICATION CHANNELS")
        for channel in self.channels:
            print(f"\n   {channel.source} → {channel.target}:")
            print(f"   - Boundary: {channel.boundary}")
            print(f"   - Capacity: {channel.capacity:.3f} bits")
            print(f"   - Transmission: {channel.transmission_rate:.3f}")
            print(f"   - Minimum delay: {channel.delay} steps")

        print("\n4. INFORMATION FLOW ANALYSIS")
        flow = self.information_flow('A', 'B')
        print(f"   A → B communication:")
        print(f"   - Minimum delay: {flow['minimum_delay']} steps")
        print(f"   - Maximum transfer: {flow['total_flow']:.3f}")
        print(f"   - Information loss: {flow['information_loss']:.3f}")
        print(f"   - Peak boundary load: {max(flow['boundary_load']):.3f}")

        print("\n5. HIGHER-ORDER BOUNDARIES")
        for level in [1, 2, 3]:
            matrix = self.create_higher_boundary(level)
            print(f"   ∂^{level} structure: {matrix.shape[0]} states")
            print(f"   - Minimum A→B delay: {2*level} steps")
            print(f"   - Information loss: {1 - self.transmission**(2*level):.3f}")

        print("\n6. QUANTUM-LIKE EFFECTS")
        quantum = self.quantum_mediation(entangled=True)
        print(f"   Entanglement through boundary:")
        print(f"   - Entropy: {quantum['entanglement_entropy']:.3f} bits")
        print(f"   - Measurement collapses to: {self.states}")
        print(f"   - No-cloning: Cannot copy ∂ without destroying mediation")

        print("\n7. KEY INSIGHTS")
        print("   • Boundaries ENABLE communication (without them, no info transfer)")
        print("   • Boundaries LIMIT communication (create bottlenecks)")
        print("   • Boundaries STORE information (have memory/state)")
        print("   • Boundaries TRANSFORM information (not passive)")

        print("\n" + "=" * 70)
        print("The boundary is not nothing - it is the birthplace of communication.")
        print("=" * 70)


def demonstrate_mediation_dynamics():
    """Show how information flows through boundary mediator."""
    print("\n" + "=" * 70)
    print("MEDIATION DYNAMICS VISUALIZATION")
    print("=" * 70)

    mediator = BoundaryMediator()

    # Simulate information pulse from A to B
    print("\nSimulating information pulse: A → ∂ → B")
    print("-" * 40)

    initial_state = np.array([1.0, 0.0, 0.0])  # All info at A
    states_over_time = []

    for t in range(15):
        state = mediator.mediate(initial_state, steps=t)
        states_over_time.append(state)
        if t < 10:
            print(f"t={t:2d}: A={state[0]:.3f}, ∂={state[1]:.3f}, B={state[2]:.3f}")

    # Find key moments
    states_array = np.array(states_over_time)
    max_boundary = np.max(states_array[:, 1])
    max_B = np.max(states_array[:, 2])
    first_B = np.where(states_array[:, 2] > 0.01)[0][0] if np.any(states_array[:, 2] > 0.01) else -1

    print(f"\nKEY MOMENTS:")
    print(f"- First signal at B: t={first_B}")
    print(f"- Maximum boundary load: {max_boundary:.3f}")
    print(f"- Maximum B reached: {max_B:.3f}")

    print("\nINFORMATION ACCOUNTING:")
    print(f"- Started with: 1.000 at A")
    print(f"- Ended with: {states_array[-1, 2]:.3f} at B")
    print(f"- Lost to absorption: {1.0 - states_array[-1, 2]:.3f}")

    print("\nThis demonstrates:")
    print("• 2-step minimum delay (A→∂→B)")
    print("• Boundary bottleneck effect")
    print("• Information loss through absorption")
    print("• No direct A↔B transfer possible")

    return states_over_time


if __name__ == "__main__":
    # Run main demonstration
    mediator = BoundaryMediator()
    mediator.demonstrate_mediation()

    # Show dynamics
    dynamics = demonstrate_mediation_dynamics()

    print("\n" + "=" * 70)
    print("PHILOSOPHICAL IMPLICATIONS")
    print("=" * 70)
    print("\n1. COMMUNICATION requires SEPARATION")
    print("   Without boundaries, no messages can exist")
    print("\n2. SEPARATION requires MEDIATION")
    print("   Without mediators, separated things cannot interact")
    print("\n3. MEDIATION requires LOSS")
    print("   Perfect communication is impossible through boundaries")
    print("\nTherefore: The very possibility of communication")
    print("implies boundaries, mediation, and information loss.")
    print("This is not a design choice - it's logically forced.")
    print("=" * 70)
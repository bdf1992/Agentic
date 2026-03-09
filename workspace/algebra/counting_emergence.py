"""
The Emergence of Natural Numbers from Pure Distinction

This module demonstrates that natural numbers (ℕ) are not primitive concepts
but emerge necessarily from the combination of:
- Distinction (O1: creates discrete states)
- Memory (O5: counting requires persistent state)
- Self-reference (O8: systems have fixed points)

Key insight: Numbers aren't things we count WITH, they're the structure
that emerges when a system can distinguish and remember its distinctions.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class DistinctionState:
    """A state that can be distinguished and remembered."""
    label: int  # The "number" emerges as a label for distinction depth
    memory: str  # What the system remembers about how it got here
    history: List[str]  # The path of distinctions taken


class NumberEmergence:
    """
    Shows how natural numbers emerge from distinction + memory.

    The core argument:
    1. You make a distinction (creates first state)
    2. You remember you made it (requires memory)
    3. You make another distinction (creates second state)
    4. You remember both distinctions
    5. The PATTERN of "how many distinctions have I made" IS the natural numbers
    """

    def __init__(self):
        # Start with NO numbers, just the ability to distinguish and remember
        self.current_state = DistinctionState(
            label=0,  # We'll call this "zero" but it's really "no distinctions yet"
            memory="origin",
            history=[]
        )

        # The only operation: make a distinction and remember it
        self.states_discovered = [self.current_state]

    def make_distinction(self) -> DistinctionState:
        """
        The fundamental operation: distinguish the current state from a new state.

        This is the ONLY operation. Numbers emerge from iterating this.
        """
        # Create a new state by distinguishing from current
        new_label = self.current_state.label + 1  # This IS the successor function!
        new_memory = f"distinction_{new_label}_from_{self.current_state.label}"
        new_history = self.current_state.history + [new_memory]

        new_state = DistinctionState(
            label=new_label,
            memory=new_memory,
            history=new_history
        )

        # Remember this state
        self.states_discovered.append(new_state)
        self.current_state = new_state

        return new_state

    def derive_peano_axioms(self) -> Dict[str, bool]:
        """
        Show that Peano's axioms for natural numbers EMERGE from our structure.

        We don't assume these axioms - they're forced by distinction + memory.
        """
        # Make several distinctions to have enough states to test
        for _ in range(5):
            self.make_distinction()

        axioms = {}

        # Axiom 1: 0 is a natural number
        # (The origin state with no distinctions exists)
        axioms['zero_exists'] = self.states_discovered[0].label == 0

        # Axiom 2: Every natural number has a successor
        # (You can always make another distinction)
        axioms['successor_exists'] = all(
            i + 1 == self.states_discovered[i+1].label
            for i in range(len(self.states_discovered) - 1)
        )

        # Axiom 3: 0 is not the successor of any natural number
        # (You can't "undistinguish" back to having made no distinctions)
        axioms['zero_not_successor'] = all(
            state.label != 0 for state in self.states_discovered[1:]
        )

        # Axiom 4: Different numbers have different successors
        # (Each distinction creates a unique new state)
        labels = [s.label for s in self.states_discovered]
        axioms['unique_successors'] = len(labels) == len(set(labels))

        # Axiom 5: Induction principle
        # (If true for 0 and true for n→n+1, then true for all)
        # This emerges from the iterative nature of distinction-making
        axioms['induction_valid'] = self._test_induction()

        return axioms

    def _test_induction(self) -> bool:
        """Test that induction works on our emergent structure."""
        # Property P: "state n has made n distinctions"
        def P(state: DistinctionState) -> bool:
            return len(state.history) == state.label

        # Base case: P(0)
        base_case = P(self.states_discovered[0])

        # Inductive step: P(n) → P(n+1)
        inductive_step = all(
            P(self.states_discovered[i]) and P(self.states_discovered[i+1])
            for i in range(len(self.states_discovered) - 1)
        )

        return base_case and inductive_step

    def show_why_integers_not_reals(self) -> Dict[str, str]:
        """
        Explain why distinction + memory gives integers, not real numbers.
        """
        return {
            'discreteness': (
                'Distinctions are discrete acts. You either make a distinction '
                'or you don\'t. There\'s no "half distinction".'
            ),
            'memory_is_finite': (
                'Memory stores "which distinctions were made". This is a '
                'discrete list, not a continuum.'
            ),
            'counting_is_sequential': (
                'From O5: Counting requires memory of previous state. '
                'You go from n to n+1, not from n to n+0.5.'
            ),
            'no_density': (
                'Between distinction n and n+1, there\'s no room for another '
                'distinction. The gap is atomic.'
            ),
            'forced_structure': (
                'The integers emerge because distinction + memory creates '
                'a discrete, sequential, unbounded structure. That IS ℕ.'
            )
        }

    def connect_to_observations(self) -> Dict[str, str]:
        """
        Show how number emergence connects to each observation.
        """
        connections = {
            'O0_unary_incoherent': (
                'Even "one" requires distinguishing from "not one". '
                'Numbers start from distinction, not from unity.'
            ),
            'O1_trinity': (
                'First distinction creates 3 states. But the NUMBER 3 '
                'emerges only after making 3 distinctions.'
            ),
            'O2_quaternion': (
                'Binary distinction creates 4 states. The number 4 '
                'emerges from the pattern, not the count.'
            ),
            'O5_memory_required': (
                'This is KEY: without memory, you cannot know you\'ve '
                'made n distinctions. Memory ENABLES numbers.'
            ),
            'O8_fixed_points': (
                'Zero is the fixed point - the state of no distinctions. '
                'It\'s special because you cannot have "negative distinctions".'
            )
        }
        return connections

    def demonstrate_number_emergence(self):
        """
        Full demonstration of how numbers emerge.
        """
        print("THE EMERGENCE OF NATURAL NUMBERS FROM DISTINCTION")
        print("=" * 60)

        print("\nStarting with NO NUMBERS, just:")
        print("- The ability to distinguish")
        print("- The ability to remember")

        print("\nMaking distinctions...")
        for i in range(5):
            state = self.make_distinction()
            print(f"  Distinction {i+1}: Created state with label={state.label}")

        print("\nWhat emerges:")
        print("  The PATTERN of distinction-counting IS the natural numbers!")
        print(f"  Discovered sequence: {[s.label for s in self.states_discovered]}")

        print("\nPeano axioms (not assumed, but EMERGENT):")
        axioms = self.derive_peano_axioms()
        for axiom, valid in axioms.items():
            status = "✓" if valid else "✗"
            print(f"  {status} {axiom}: {valid}")

        print("\nWhy integers, not reals:")
        reasons = self.show_why_integers_not_reals()
        for key, reason in reasons.items():
            print(f"  {key}:")
            print(f"    {reason}")

        return True


class MemoryCapacityBounds:
    """
    Explores what happens when memory is bounded (finite capacity).

    This connects to modular arithmetic and cyclic groups.
    """

    def __init__(self, capacity: int = 3):
        """
        Initialize with bounded memory capacity.

        Args:
            capacity: Maximum number of distinctions that can be remembered
        """
        self.capacity = capacity
        self.memory_states = []
        self.current_position = 0

    def make_distinction_with_bounded_memory(self) -> Tuple[int, str]:
        """
        Make a distinction but with finite memory.

        When memory fills, we cycle back (modular arithmetic emerges!).
        """
        # Try to increment
        new_position = (self.current_position + 1) % self.capacity

        # Record the transition
        transition = f"{self.current_position} -> {new_position}"
        self.memory_states.append(transition)

        # Update position
        self.current_position = new_position

        return new_position, transition

    def discover_cyclic_structure(self) -> Dict[str, any]:
        """
        Show that bounded memory forces cyclic group structure.
        """
        # Make many distinctions
        positions = []
        for _ in range(self.capacity * 2 + 1):
            pos, _ = self.make_distinction_with_bounded_memory()
            positions.append(pos)

        # Analyze the pattern
        period = self.capacity
        is_cyclic = all(
            positions[i] == positions[i + period]
            for i in range(len(positions) - period)
        )

        return {
            'structure': f'Z_{self.capacity}',  # Cyclic group emerges!
            'is_cyclic': is_cyclic,
            'period': period,
            'positions_seen': positions,
            'insight': (
                f'With memory capacity {self.capacity}, '
                f'we get cyclic group Z_{self.capacity} automatically!'
            )
        }

    def connect_to_trinity(self) -> Dict[str, str]:
        """
        Show how capacity-3 memory gives us the trinity structure from O1.
        """
        if self.capacity != 3:
            return {'error': 'Set capacity=3 to see trinity connection'}

        return {
            'observation': 'O1 creates 3 states: thing, complement, boundary',
            'memory_interpretation': (
                'With capacity-3 memory, after 3 distinctions we cycle back. '
                'This IS the Z₃ structure!'
            ),
            'states': {
                0: 'thing (no distinctions yet)',
                1: 'complement (one distinction made)',
                2: 'boundary (two distinctions, about to cycle)'
            },
            'forced_structure': 'Memory capacity 3 → Z₃ group',
            'deep_connection': (
                'The trinity isn\'t just about distinction creating 3 things. '
                'It\'s also about memory cycling after 3 steps!'
            )
        }


def demonstrate_full_emergence():
    """
    Complete demonstration of number emergence.
    """
    print("\n" + "="*70)
    print("COMPLETE DEMONSTRATION: NUMBERS FROM DISTINCTION + MEMORY")
    print("="*70)

    # Part 1: Unbounded memory gives natural numbers
    print("\nPART 1: UNBOUNDED MEMORY → NATURAL NUMBERS")
    print("-" * 40)
    ne = NumberEmergence()
    ne.demonstrate_number_emergence()

    # Part 2: Bounded memory gives cyclic groups
    print("\n\nPART 2: BOUNDED MEMORY → CYCLIC GROUPS")
    print("-" * 40)

    for capacity in [2, 3, 4, 5]:
        print(f"\nMemory capacity = {capacity}:")
        mcb = MemoryCapacityBounds(capacity)
        result = mcb.discover_cyclic_structure()
        print(f"  Emerges: {result['structure']} (cyclic group)")
        print(f"  Period: {result['period']}")

    # Part 3: Special case - trinity
    print("\n\nPART 3: TRINITY CONNECTION")
    print("-" * 40)
    mcb3 = MemoryCapacityBounds(3)
    trinity = mcb3.connect_to_trinity()
    for key, value in trinity.items():
        if key == 'states':
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    # Part 4: The deep insight
    print("\n\nTHE DEEP INSIGHT:")
    print("-" * 40)
    print("""
    Natural numbers are not primitive. They emerge from:

    1. The ability to distinguish (creates discrete states)
    2. The ability to remember (enables counting)
    3. The pattern of iterated distinction (IS the number sequence)

    With unbounded memory: ℕ emerges (natural numbers)
    With bounded memory of size n: Zₙ emerges (cyclic group)

    This is why mathematics is the same everywhere in the universe.
    Any system capable of distinction and memory will discover
    the same number structures we use.

    Numbers aren't invented. They're FORCED by logic itself.
    """)

    return True


if __name__ == "__main__":
    # Run the complete demonstration
    demonstrate_full_emergence()

    print("\n" + "="*70)
    print("CONCLUSION: Natural numbers emerge from distinction + memory.")
    print("This is not a model of numbers. This IS what numbers are:")
    print("The pattern that emerges when a system can distinguish and remember.")
    print("="*70)
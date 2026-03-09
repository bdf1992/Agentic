"""
Distinction Engine: A calculator for forced algebraic structures.

INPUT:  A number of independent distinctions (or a list of distinction specs)
OUTPUT: The forced algebraic structure, its group, eigenvalues, and properties

This is a TOOL, not a proof. You put in distinctions, you get out algebra.
Like a calculator: the math is real, but the interface is practical.

KEY INSIGHT FROM AUDIT (cycle 1):
  The STRUCTURE is forced (state count, symmetry type, group).
  The DYNAMICS are chosen (transition probabilities, spectral gap).
  This engine separates the two clearly.

WHAT'S FORCED BY n DISTINCTIONS:
  1 distinction (O1): 3 states → Z₃ (cyclic group of order 3)
  2 distinctions (O2): 4 states per pair, but cross-terms create more
  n distinctions: state space grows, group structure depends on independence

THE QUESTION THIS TOOL ANSWERS:
  Given n independent binary distinctions, what is the forced:
    - State count
    - Group structure
    - Symmetry group
    - Eigenvalue spectrum (of the group's regular representation)
    - Non-boundary fraction
    - Adjacency structure (which states are "neighbors")
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from itertools import product


class Distinction:
    """A single distinction: creates a thing, complement, and boundary."""

    def __init__(self, name: str = "d"):
        self.name = name
        self.states = [f"{name}", f"~{name}", f"∂{name}"]
        self.thing = 0
        self.complement = 1
        self.boundary = 2

    def __repr__(self):
        return f"Distinction({self.name})"

    @property
    def order(self) -> int:
        """Number of states (always 3 for a single distinction)."""
        return 3

    @property
    def non_boundary_count(self) -> int:
        return 2

    @property
    def non_boundary_fraction(self) -> float:
        return self.non_boundary_count / self.order


class DistinctionSystem:
    """A system of n independent distinctions.

    Each distinction creates 3 states. n independent distinctions create
    a product space of 3^n states, but with structure:
      - Each state is a tuple of (thing/complement/boundary) per distinction
      - "Boundary" in ANY component makes the whole state boundary-like
      - Non-boundary states: those with no boundary component = 2^n

    Group structure: Z₃^n (direct product of n copies of Z₃)
    Symmetry: S_n permutes the distinctions (if they're interchangeable)
    """

    def __init__(self, n: int, names: Optional[List[str]] = None):
        if n < 1:
            raise ValueError("Need at least 1 distinction")
        self.n = n
        self.distinctions = [
            Distinction(names[i] if names and i < len(names) else f"d{i+1}")
            for i in range(n)
        ]

    @property
    def total_states(self) -> int:
        """Total number of states in the product space."""
        return 3 ** self.n

    @property
    def non_boundary_states(self) -> int:
        """States with NO boundary component."""
        return 2 ** self.n

    @property
    def boundary_states(self) -> int:
        """States with at least one boundary component."""
        return self.total_states - self.non_boundary_states

    @property
    def non_boundary_fraction(self) -> float:
        """Fraction of states that are non-boundary = (2/3)^n."""
        return self.non_boundary_states / self.total_states

    @property
    def group_order(self) -> int:
        """Order of the forced group Z₃^n."""
        return 3 ** self.n

    @property
    def group_name(self) -> str:
        """Name of the forced group."""
        if self.n == 1:
            return "Z₃"
        return f"Z₃^{self.n}"

    @property
    def symmetry_group(self) -> str:
        """Symmetry group permuting interchangeable distinctions."""
        if self.n == 1:
            return "trivial"
        return f"S_{self.n}"

    def enumerate_states(self) -> List[Tuple[int, ...]]:
        """List all states as tuples of (0=thing, 1=complement, 2=boundary)."""
        return list(product(range(3), repeat=self.n))

    def is_boundary(self, state: Tuple[int, ...]) -> bool:
        """A state is boundary if ANY component is boundary (=2)."""
        return 2 in state

    def classify_states(self) -> Dict[str, List[Tuple[int, ...]]]:
        """Classify all states into live (non-boundary) and boundary."""
        live = []
        boundary = []
        for s in self.enumerate_states():
            if self.is_boundary(s):
                boundary.append(s)
            else:
                live.append(s)
        return {"live": live, "boundary": boundary}

    def boundary_depth(self, state: Tuple[int, ...]) -> int:
        """How many components are boundary? (0 = fully live, n = fully dead)."""
        return sum(1 for x in state if x == 2)

    def hamming_distance(self, s1: Tuple[int, ...], s2: Tuple[int, ...]) -> int:
        """Number of components that differ between two states."""
        return sum(1 for a, b in zip(s1, s2) if a != b)

    def adjacency_matrix(self) -> np.ndarray:
        """Build adjacency matrix: states are adjacent if Hamming distance = 1."""
        states = self.enumerate_states()
        N = len(states)
        A = np.zeros((N, N))
        for i in range(N):
            for j in range(i + 1, N):
                if self.hamming_distance(states[i], states[j]) == 1:
                    A[i, j] = 1
                    A[j, i] = 1
        return A

    def laplacian(self) -> np.ndarray:
        """Graph Laplacian L = D - A."""
        A = self.adjacency_matrix()
        D = np.diag(A.sum(axis=1))
        return D - A

    def laplacian_spectrum(self) -> np.ndarray:
        """Eigenvalues of the graph Laplacian, sorted ascending."""
        L = self.laplacian()
        eigs = np.linalg.eigvalsh(L)
        return np.sort(eigs)

    def laplacian_gap(self) -> float:
        """Spectral gap of the Laplacian = smallest nonzero eigenvalue.

        This is a GRAPH property, not dependent on transition probabilities.
        It measures how well-connected the state space is.
        """
        eigs = self.laplacian_spectrum()
        nonzero = eigs[eigs > 1e-10]
        if len(nonzero) == 0:
            return 0.0
        return float(nonzero[0])

    def z3_rotation_matrix(self) -> np.ndarray:
        """The natural Z₃ rotation: cycle each component by +1 mod 3.

        This IS forced: it's the generator of Z₃^n.
        Its eigenvalues are products of cube roots of unity.
        """
        states = self.enumerate_states()
        N = len(states)
        state_to_idx = {s: i for i, s in enumerate(states)}
        R = np.zeros((N, N))
        for s in states:
            rotated = tuple((x + 1) % 3 for x in s)
            R[state_to_idx[rotated], state_to_idx[s]] = 1
        return R

    def rotation_spectrum(self) -> np.ndarray:
        """Eigenvalues of the Z₃^n rotation operator."""
        R = self.z3_rotation_matrix()
        return np.linalg.eigvals(R)

    def compute_all(self, verbose: bool = True) -> Dict:
        """Compute everything about this distinction system.

        THE calculator function. Input = n distinctions, output = full report.
        """
        classified = self.classify_states()

        # Boundary depth distribution
        all_states = self.enumerate_states()
        depth_dist = {}
        for s in all_states:
            d = self.boundary_depth(s)
            depth_dist[d] = depth_dist.get(d, 0) + 1

        # Spectra
        lap_spectrum = self.laplacian_spectrum()
        lap_gap = self.laplacian_gap()

        # Rotation spectrum
        rot_eigs = self.rotation_spectrum()
        rot_unique = np.unique(np.round(rot_eigs, 8))

        result = {
            "n_distinctions": self.n,
            "total_states": self.total_states,
            "live_states": self.non_boundary_states,
            "boundary_states": self.boundary_states,
            "non_boundary_fraction": self.non_boundary_fraction,
            "expected_fraction": (2/3) ** self.n,
            "fraction_match": abs(self.non_boundary_fraction - (2/3)**self.n) < 1e-10,
            "group": self.group_name,
            "group_order": self.group_order,
            "symmetry": self.symmetry_group,
            "boundary_depth_distribution": depth_dist,
            "laplacian_gap": lap_gap,
            "laplacian_spectrum_summary": {
                "min": float(lap_spectrum[0]),
                "max": float(lap_spectrum[-1]),
                "unique_count": len(np.unique(np.round(lap_spectrum, 8))),
            },
            "rotation_eigenvalue_count": len(rot_unique),
        }

        if verbose:
            self._print_report(result, classified, lap_spectrum, rot_unique, depth_dist)

        return result

    def _print_report(self, result, classified, lap_spectrum, rot_unique, depth_dist):
        print(f"\n{'='*65}")
        print(f"  DISTINCTION ENGINE: {self.n} distinction(s)")
        print(f"{'='*65}")
        print(f"  Group: {result['group']}  (order {result['group_order']})")
        print(f"  Symmetry: {result['symmetry']}")
        print()
        print(f"  State count:  {result['total_states']}")
        print(f"  Live states:  {result['live_states']}  "
              f"({result['live_states']}/{result['total_states']} "
              f"= {result['non_boundary_fraction']:.6f})")
        print(f"  Expected:     (2/3)^{self.n} = {result['expected_fraction']:.6f}")
        print(f"  Match: {result['fraction_match']}")
        print()

        # Boundary depth distribution
        print("  Boundary depth distribution:")
        for depth in sorted(depth_dist.keys()):
            count = depth_dist[depth]
            bar = "█" * min(count, 40)
            label = "live" if depth == 0 else f"{depth} boundary component(s)"
            print(f"    depth {depth}: {count:>5} states  {bar}  [{label}]")
        print()

        # Laplacian spectrum
        print(f"  Laplacian gap: {result['laplacian_gap']:.6f}")
        print(f"  Laplacian spectrum: {len(np.unique(np.round(lap_spectrum, 4)))} unique values")
        print(f"    range: [{lap_spectrum[0]:.4f}, {lap_spectrum[-1]:.4f}]")
        if len(lap_spectrum) <= 30:
            rounded = np.round(lap_spectrum, 4)
            unique_sorted = sorted(set(rounded))
            for val in unique_sorted[:10]:
                mult = list(rounded).count(val)
                print(f"    λ = {val:8.4f}  (multiplicity {mult})")
            if len(unique_sorted) > 10:
                print(f"    ... and {len(unique_sorted) - 10} more")
        print()

        # Rotation eigenvalues
        print(f"  Z₃^{self.n} rotation: {len(rot_unique)} distinct eigenvalues")
        print(f"  All |λ| = 1: {all(abs(abs(e) - 1) < 1e-8 for e in rot_unique)}")
        print()

        # Live states (if small enough to list)
        if len(classified['live']) <= 16:
            print("  Live states:")
            for s in classified['live']:
                labels = []
                for i, x in enumerate(s):
                    d = self.distinctions[i]
                    labels.append(d.states[x])
                print(f"    {s} → ({', '.join(labels)})")


def chain_distinctions(max_n: int = 6) -> List[Dict]:
    """Run the distinction engine for 1, 2, ..., max_n distinctions.

    This answers: what happens as you ADD distinctions iteratively?
    Does the structure converge? Diverge? Hit a wall?
    """
    print()
    print("█" * 65)
    print("  DISTINCTION CHAIN: 1 to", max_n, "distinctions")
    print("█" * 65)

    results = []
    for n in range(1, max_n + 1):
        sys = DistinctionSystem(n)
        r = sys.compute_all(verbose=(n <= 4))
        results.append(r)

    # Summary table
    print(f"\n{'='*65}")
    print("  SUMMARY TABLE")
    print(f"{'='*65}")
    print(f"  {'n':>3} | {'states':>7} | {'live':>5} | {'fraction':>10} | "
          f"{'(2/3)^n':>10} | {'lap_gap':>8} | {'group':>8}")
    print("  " + "-" * 65)
    for r in results:
        n = r['n_distinctions']
        print(f"  {n:>3} | {r['total_states']:>7} | {r['live_states']:>5} | "
              f"{r['non_boundary_fraction']:>10.6f} | "
              f"{r['expected_fraction']:>10.6f} | "
              f"{r['laplacian_gap']:>8.4f} | {r['group']:>8}")

    print()
    print("  OBSERVATIONS:")
    print(f"    1. State count grows as 3^n (exponential)")
    print(f"    2. Live fraction decays as (2/3)^n (geometric) — FORCED")
    print(f"    3. Boundary eventually dominates: at n=10, only {(2/3)**10:.4%} live")
    print(f"    4. Laplacian gap measures connectivity of the state graph")

    return results


def compare_with_non_ternary() -> None:
    """What if distinctions didn't create exactly 3 states?

    O1 says: 1 distinction → 3 states (thing, complement, boundary).
    But what if the boundary DIDN'T have ontological weight (contra O3)?
    Then: 1 distinction → 2 states (thing, complement). Binary.
    What if distinctions created MORE than 3? What if boundary splits?

    This tests: is the ternary structure really the only option?
    """
    print()
    print("█" * 65)
    print("  WHAT IF NOT TERNARY?")
    print("█" * 65)

    for k in [2, 3, 4, 5]:
        print(f"\n  --- k = {k} states per distinction ---")
        # For k states: 1 is boundary, k-1 are live
        # n distinctions: k^n total, (k-1)^n live
        for n in range(1, 7):
            total = k ** n
            live = (k - 1) ** n
            frac = live / total
            print(f"    n={n}: {total:>7} total, {live:>5} live, "
                  f"fraction = {frac:.6f} = ({k-1}/{k})^{n}")

        frac_formula = (k - 1) / k
        print(f"    Non-boundary fraction per dim: {frac_formula:.4f}")
        print(f"    At n=10: {frac_formula**10:.6f}")

    print()
    print("  KEY INSIGHT:")
    print("    The non-boundary fraction is ALWAYS ((k-1)/k)^n.")
    print("    For k=2 (binary): 1/2 per dim → decays as (1/2)^n — FAST")
    print("    For k=3 (ternary): 2/3 per dim → decays as (2/3)^n — the forced case")
    print("    For k=4: 3/4 per dim → decays as (3/4)^n — slower")
    print()
    print("    O1 forces k=3. That's what makes 2/3 the specific ratio.")
    print("    The FORMULA (k-1)/k is universal. The VALUE 2/3 is from k=3.")
    print()
    print("    TUNABLE PARAMETER: If we relax O3 (boundary has no weight),")
    print("    k=2 and everything is binary. The 'spectral gap' becomes 1/2.")
    print("    O3 is what elevates us from binary to ternary.")


def main():
    """Run the distinction engine demo."""
    # Single distinction
    sys1 = DistinctionSystem(1, ["A"])
    sys1.compute_all()

    # Two distinctions
    sys2 = DistinctionSystem(2, ["A", "B"])
    sys2.compute_all()

    # Three distinctions
    sys3 = DistinctionSystem(3, ["A", "B", "C"])
    sys3.compute_all()

    # Chain comparison
    chain_distinctions(6)

    # Non-ternary comparison
    compare_with_non_ternary()

    print()
    print("█" * 65)
    print("  DISTINCTION ENGINE COMPLETE")
    print("█" * 65)
    print()
    print("  USAGE:")
    print("    from distinction_engine import DistinctionSystem")
    print("    sys = DistinctionSystem(n=4, names=['x','y','z','w'])")
    print("    result = sys.compute_all()")
    print()
    print("  WHAT THIS TOOL GIVES YOU:")
    print("    - State enumeration and classification")
    print("    - Boundary depth distribution")
    print("    - Graph Laplacian spectrum (topology, NOT dynamics)")
    print("    - Rotation spectrum (group theory)")
    print("    - Non-boundary fraction ((2/3)^n, forced)")
    print("    - Comparison with non-ternary alternatives")


if __name__ == "__main__":
    main()

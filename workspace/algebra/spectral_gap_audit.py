"""
Spectral Gap Audit: Is 2/3 actually forced, or operator-dependent?

SKEPTICAL INVESTIGATION:
The existing spectral_gap_proof.py claims gap = 2/3 is invariant.
But it ASSUMES transition probabilities T→¬T = 1/3, T→∂ = 2/3.
Those probabilities are NOT derived from the observations.

This tool asks: what IS actually forced by the observations alone?

OBSERVATIONS USED:
  O1: Single distinction creates 3 things (thing, complement, boundary)
  O3: Boundary has ontological weight (is itself a thing)
  O8: Self-referential systems have fixed points

WHAT WE ACTUALLY KNOW:
  - There are 3 states (forced by O1)
  - Boundary absorbs (O3 says boundary is a thing — but does it ABSORB?)
  - The system is stochastic (something must happen at each step)

WHAT WE DON'T KNOW:
  - The exact transition probabilities
  - Whether the boundary is truly absorbing vs. reflecting
  - Whether the system is even Markovian

This tool explores the SPACE of possible operators on 3 states
and maps what gaps are achievable, what's forced, what's chosen.
"""

import numpy as np
from typing import Tuple, List, Dict


def general_3state_transition(p_exchange: float, p_absorb: float) -> np.ndarray:
    """Build a 3-state column-stochastic matrix with arbitrary parameters.

    States: T (thing), C (complement), B (boundary)

    From T: go to C with prob p_exchange, go to B with prob p_absorb, stay at T with 1-p_exchange-p_absorb
    From C: go to T with prob p_exchange, go to B with prob p_absorb, stay at C with 1-p_exchange-p_absorb
    From B: stays at B with prob 1 (absorbing — this IS forced by O3)

    Constraints: p_exchange >= 0, p_absorb >= 0, p_exchange + p_absorb <= 1
    """
    p_stay = 1.0 - p_exchange - p_absorb
    M = np.array([
        [p_stay,      p_exchange,  0],   # to T
        [p_exchange,  p_stay,      0],   # to C
        [p_absorb,    p_absorb,    1],   # to B
    ])
    return M


def spectral_gap(M: np.ndarray) -> float:
    """Compute spectral gap = |λ1| - |λ2| of a transition matrix."""
    eigs = np.sort(np.abs(np.linalg.eigvals(M)))[::-1]
    return eigs[0] - eigs[1]


def all_eigenvalues(M: np.ndarray) -> np.ndarray:
    """Return eigenvalues sorted by |λ| descending."""
    eigs = np.linalg.eigvals(M)
    idx = np.argsort(np.abs(eigs))[::-1]
    return eigs[idx]


# ============================================================================
# AUDIT 1: How does the gap depend on transition probabilities?
# ============================================================================

def audit_gap_landscape(resolution: int = 50) -> Dict:
    """Sweep the (p_exchange, p_absorb) parameter space.

    Returns a map of the entire gap landscape.
    This is the KEY tool: it shows what gaps are ACHIEVABLE.
    """
    results = []
    p_values = np.linspace(0.001, 0.999, resolution)

    for p_ex in p_values:
        for p_ab in p_values:
            if p_ex + p_ab > 1.0:
                continue
            M = general_3state_transition(p_ex, p_ab)
            gap = spectral_gap(M)
            eigs = all_eigenvalues(M)
            results.append({
                'p_exchange': p_ex,
                'p_absorb': p_ab,
                'p_stay': 1 - p_ex - p_ab,
                'gap': gap,
                'eigenvalues': eigs,
            })

    return results


def audit_symmetry_constraint() -> Dict:
    """What if we ONLY assume symmetry between T and C?

    O1 says thing and complement are symmetric (neither is privileged).
    This constrains the matrix but doesn't fix the probabilities.

    Under T↔C symmetry:
      P(T→C) = P(C→T) = p_exchange
      P(T→B) = P(C→B) = p_absorb
      P(T→T) = P(C→C) = p_stay = 1 - p_exchange - p_absorb

    This leaves TWO free parameters. The gap is NOT determined.
    """
    print("=" * 70)
    print("AUDIT: What does symmetry (O1) actually constrain?")
    print("=" * 70)
    print()
    print("O1 forces T↔C symmetry. This gives us the matrix:")
    print("  M = [[p_stay, p_ex,  0 ],")
    print("       [p_ex,   p_stay,0 ],")
    print("       [p_ab,   p_ab,  1 ]]")
    print()
    print("With p_stay = 1 - p_ex - p_ab")
    print("This has TWO free parameters: p_ex and p_ab.")
    print()

    # Compute gap analytically
    print("ANALYTICAL: The eigenvalues are:")
    print("  λ₁ = 1               (absorbing state)")
    print("  λ₂ = p_stay + p_ex   = 1 - p_ab    (symmetric mode of T,C)")
    print("  λ₃ = p_stay - p_ex   = 1 - p_ab - 2*p_ex  (antisymmetric mode)")
    print()
    print("The spectral gap = 1 - max(|λ₂|, |λ₃|)")
    print("  = 1 - max(|1 - p_ab|, |1 - p_ab - 2*p_ex|)")
    print()
    print("For p_ab > 0 (boundary absorbs something): |λ₂| = 1 - p_ab < 1")
    print("So gap = p_ab  (when p_ab dominates, which it does for p_ab > 2*p_ex)")
    print("Or gap = 1 - |1 - p_ab - 2*p_ex| otherwise")
    print()

    # Show this with numbers
    print("NUMERICAL: Gap for various (p_ex, p_ab):")
    print(f"  {'p_ex':>6} {'p_ab':>6} | {'λ₂':>8} {'λ₃':>8} | {'gap':>8} | note")
    print("-" * 65)

    test_cases = [
        (1/3, 2/3, "the ASSUMED case in existing proof"),
        (1/4, 1/2, "different split"),
        (1/2, 1/2, "maximal exchange, maximal absorb"),
        (0.1, 0.1, "low activity"),
        (0.0, 1.0, "no exchange, instant absorb"),
        (0.5, 0.0, "no absorption (not absorbing!)"),
        (1/3, 1/3, "equal exchange and absorb"),
        (0.1, 0.8, "high absorb, low exchange"),
        (0.45, 0.1, "high exchange, low absorb"),
    ]

    for p_ex, p_ab, note in test_cases:
        if p_ex + p_ab > 1.0:
            continue
        M = general_3state_transition(p_ex, p_ab)
        eigs = np.sort(np.abs(np.linalg.eigvals(M)))[::-1]
        gap = eigs[0] - eigs[1]
        lam2 = 1 - p_ab
        lam3 = 1 - p_ab - 2*p_ex
        print(f"  {p_ex:6.3f} {p_ab:6.3f} | {lam2:8.4f} {lam3:8.4f} | {gap:8.4f} | {note}")

    print()
    print("VERDICT: The gap is NOT 2/3 in general.")
    print("  gap = p_ab when the symmetric mode dominates (p_ab > 2*p_ex)")
    print("  gap = 2*p_ex + p_ab when the antisymmetric mode dominates")
    print("  The gap equals 2/3 ONLY when p_ab = 2/3 (or specific combos)")
    print()
    print("The existing proof ASSUMED p_ab = 2/3. That's where 2/3 comes from.")

    return test_cases


def audit_what_IS_forced() -> None:
    """What constraints DO the observations actually impose?

    Let's be rigorous about what O1-O8 force:
    """
    print()
    print("=" * 70)
    print("AUDIT: What IS actually forced by the observations?")
    print("=" * 70)
    print()

    print("FORCED (genuinely, no weaseling):")
    print("  1. There are exactly 3 states (O1: distinction creates triple)")
    print("  2. T and C are symmetric (O1: complement is the mirror of thing)")
    print("  3. B is special — it IS the distinction (O3: boundary has weight)")
    print("  4. The system has eigenvalues (any matrix does)")
    print("  5. |Z₃| = 3 (counting, forced by O1)")
    print()

    print("NOT FORCED (assumed in existing proof):")
    print("  1. That the boundary is absorbing (O3 says it HAS weight, not that it traps)")
    print("  2. The specific transition probabilities (1/3, 2/3)")
    print("  3. That the system is Markovian (memoryless)")
    print("  4. That the system is column-stochastic (probabilistic)")
    print("  5. That there's a single 'correct' operator")
    print()

    print("THE HONEST PICTURE:")
    print("  O1 forces: 3 states, symmetric pair + distinguished element")
    print("  O3 forces: the third state is special (not just another state)")
    print("  Together: a 3-state system with Z₂ symmetry in the non-boundary sector")
    print()
    print("  The STRUCTURE is forced. The DYNAMICS are not.")
    print("  The spectral gap depends on which operator you choose.")
    print("  Saying 'gap = 2/3 is forced' is saying 'I chose p_ab = 2/3'.")
    print()

    print("BUT WAIT — is there a NATURAL choice of operator?")
    print("  Candidate: the UNIFORM operator (maximum entropy)")
    print("  = each non-self transition equally likely")
    print("  = if boundary absorbs, then from T: P(→C) = P(→B) = 1/2")
    print()

    # Test the uniform operator
    M_uniform = general_3state_transition(1/2, 1/2)
    gap_uniform = spectral_gap(M_uniform)
    eigs_uniform = all_eigenvalues(M_uniform)
    print(f"  Uniform operator eigenvalues: {np.round(eigs_uniform, 4)}")
    print(f"  Uniform operator gap: {gap_uniform:.4f}")
    print(f"  That's 1/2, not 2/3!")
    print()

    # Test the Z3-rotation operator
    print("  Candidate: the Z₃ rotation (cyclic permutation)")
    omega = np.exp(2j * np.pi / 3)
    M_rot = np.array([
        [0, 0, 1],
        [1, 0, 0],
        [0, 1, 0],
    ], dtype=float)
    eigs_rot = np.linalg.eigvals(M_rot)
    # This is a permutation matrix, |eigenvalues| all = 1, gap = 0
    print(f"  Z₃ rotation eigenvalues: {np.round(eigs_rot, 4)}")
    print(f"  Z₃ rotation |eigenvalues|: {np.round(np.abs(eigs_rot), 4)}")
    print(f"  Z₃ rotation gap: {np.abs(eigs_rot[0]) - np.sort(np.abs(eigs_rot))[::-1][1]:.4f}")
    print(f"  All eigenvalues have |λ| = 1, so gap = 0!")
    print()

    # What about max-entropy given absorbing boundary?
    print("  Candidate: maximum entropy given B absorbs")
    print("  = from T: go to each of {C, B} with probability 1/2")
    print("  = from C: go to each of {T, B} with probability 1/2")
    print("  (no self-loops)")
    M_maxent = general_3state_transition(1/2, 1/2)
    print(f"  This is the same as uniform: gap = {spectral_gap(M_maxent):.4f} = 1/2")
    print()

    print("  Candidate: equal probability over ALL 3 targets including self")
    print("  = from T: P(→T) = P(→C) = P(→B) = 1/3")
    M_equal = general_3state_transition(1/3, 1/3)
    gap_equal = spectral_gap(M_equal)
    eigs_equal = all_eigenvalues(M_equal)
    print(f"  Equal-probability eigenvalues: {np.round(eigs_equal, 4)}")
    print(f"  Equal-probability gap: {gap_equal:.4f}")
    print(f"  That's 1/3, not 2/3!")


def audit_what_makes_two_thirds_special() -> None:
    """Despite not being forced by dynamics, is 2/3 special in OTHER ways?"""
    print()
    print("=" * 70)
    print("AUDIT: What IS special about 2/3 (honestly)?")
    print("=" * 70)
    print()

    print("2/3 IS genuinely special as a STATIC property:")
    print()
    print("  1. COUNTING: 2 out of 3 states are non-boundary → 2/3")
    print("     This IS forced. No dynamics needed. Pure combinatorics.")
    print()
    print("  2. VOLUME: In d dimensions, (2/3)^d is the non-boundary fraction")
    print("     Also forced. Pure combinatorics on Z₃^d lattice.")
    print()
    print("  3. RATIO: |Z₂|/|Z₃| = 2/3")
    print("     Forced by the group orders (2 and 3 are forced).")
    print()
    print("  4. But as a SPECTRAL GAP of a SPECIFIC OPERATOR: NOT forced.")
    print("     You can get any gap in (0, 1] by choosing transition probabilities.")
    print()

    print("THE HONEST CONCLUSION:")
    print("  2/3 is a forced RATIO (combinatorial).")
    print("  2/3 is NOT a forced SPECTRAL GAP (dynamical).")
    print("  The existing proof conflates these two things.")
    print()
    print("  To get 2/3 as a spectral gap, you need an operator where")
    print("  the absorption rate equals the non-boundary fraction.")
    print("  That's a CHOICE, not a derivation.")
    print()

    # But... is there a self-consistency argument?
    print("HOWEVER — a self-consistency argument:")
    print("  IF you demand that the spectral gap equals the non-boundary fraction,")
    print("  THEN p_absorb = 2/3 and p_exchange = 1/3.")
    print("  This is a FIXED POINT condition (O8!):")
    print("    'The fraction that survives = the gap of the dynamics'")
    print("    → gap = 2/3 is the UNIQUE self-consistent value")
    print()

    # Verify: if gap = non-boundary fraction, what's forced?
    # gap = p_ab (when symmetric mode dominates)
    # non-boundary fraction = 2/3
    # so p_ab = 2/3
    # then p_ex = 1 - p_ab - p_stay, and p_stay >= 0 requires p_ex <= 1/3
    # But for gap = p_ab, we need p_ab >= 2*p_ex → 2/3 >= 2*p_ex → p_ex <= 1/3
    # The maximal exchange under this constraint: p_ex = 1/3, p_stay = 0
    # That's EXACTLY the matrix in the existing proof!

    print("  Working it out:")
    print("    Demand: gap = 2/3 = non-boundary fraction")
    print("    → p_absorb = 2/3  (gap = p_ab when symmetric mode dominates)")
    print("    → p_exchange ≤ 1/3  (because p_ex + p_ab ≤ 1)")
    print("    → maximal exchange: p_ex = 1/3, p_stay = 0")
    print("    → this gives EXACTLY the matrix in spectral_gap_proof.py!")
    print()
    print("  So the existing proof's matrix IS special: it's the UNIQUE")
    print("  operator where:")
    print("    (a) gap = non-boundary fraction (self-consistency)")
    print("    (b) exchange is maximized (no lazy self-loops)")
    print("    (c) T↔C are symmetric (O1)")
    print()
    print("  That's a real result. But it's a self-consistency argument,")
    print("  not a 'forced by observations alone' argument.")


# ============================================================================
# TOOL: The Gap Calculator
# ============================================================================

def gap_calculator(p_exchange: float, p_absorb: float, verbose: bool = True) -> Dict:
    """Calculator: given transition probabilities, compute everything.

    This is the TOOL version. Input parameters, get spectral properties.

    Args:
        p_exchange: probability of T↔C exchange per step
        p_absorb: probability of absorption into boundary per step
        verbose: print detailed output

    Returns:
        dict with eigenvalues, gap, mixing time, stationary distribution
    """
    if p_exchange < 0 or p_absorb < 0:
        raise ValueError("Probabilities must be non-negative")
    if p_exchange + p_absorb > 1.0 + 1e-10:
        raise ValueError(f"p_exchange + p_absorb = {p_exchange + p_absorb} > 1")

    p_stay = max(0, 1.0 - p_exchange - p_absorb)
    M = general_3state_transition(p_exchange, p_absorb)

    eigs = np.linalg.eigvals(M)
    abs_eigs = np.sort(np.abs(eigs))[::-1]
    gap = abs_eigs[0] - abs_eigs[1]

    # Mixing time estimate (time to converge to stationary)
    if abs_eigs[1] > 0:
        mixing_time = 1.0 / np.log(1.0 / abs_eigs[1])
    else:
        mixing_time = 0.0  # instant mixing

    # Half-life of non-boundary states
    if p_absorb > 0:
        half_life = np.log(2) / p_absorb
    else:
        half_life = float('inf')

    # Stationary distribution (eigenvector for λ=1)
    # For absorbing boundary: stationary = [0, 0, 1]
    stationary = np.array([0.0, 0.0, 1.0]) if p_absorb > 0 else None

    result = {
        'p_exchange': p_exchange,
        'p_absorb': p_absorb,
        'p_stay': p_stay,
        'matrix': M,
        'eigenvalues': eigs,
        'abs_eigenvalues': abs_eigs,
        'spectral_gap': gap,
        'mixing_time': mixing_time,
        'half_life': half_life,
        'stationary': stationary,
        'is_self_consistent': abs(gap - 2/3) < 1e-10,
        'non_boundary_fraction': 2/3,
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"Gap Calculator: p_ex={p_exchange:.4f}, p_ab={p_absorb:.4f}")
        print(f"{'='*60}")
        print(f"  Transition matrix:")
        for row in M:
            print(f"    [{', '.join(f'{x:6.3f}' for x in row)}]")
        print(f"  Eigenvalues: {', '.join(f'{e:.4f}' for e in eigs)}")
        print(f"  |Eigenvalues|: {', '.join(f'{e:.4f}' for e in abs_eigs)}")
        print(f"  Spectral gap: {gap:.6f}")
        print(f"  Non-boundary fraction: {2/3:.6f}")
        print(f"  Gap = fraction? {result['is_self_consistent']}")
        print(f"  Mixing time: {mixing_time:.4f} steps")
        print(f"  Half-life: {half_life:.4f} steps")

    return result


def find_self_consistent_operators() -> List[Dict]:
    """Find ALL operators where gap = non-boundary fraction = 2/3.

    This is the key question: what operators satisfy the self-consistency condition?
    """
    print()
    print("=" * 70)
    print("SEARCH: All self-consistent operators (gap = 2/3)")
    print("=" * 70)
    print()

    solutions = []
    p_values = np.linspace(0, 1, 1000)

    for p_ex in p_values:
        for p_ab in p_values:
            if p_ex + p_ab > 1.0 + 1e-6:
                continue
            M = general_3state_transition(p_ex, p_ab)
            gap = spectral_gap(M)
            if abs(gap - 2/3) < 0.005:
                solutions.append({
                    'p_exchange': p_ex,
                    'p_absorb': p_ab,
                    'gap': gap,
                })

    # Remove near-duplicates
    filtered = []
    for sol in solutions:
        is_dup = False
        for existing in filtered:
            if (abs(sol['p_exchange'] - existing['p_exchange']) < 0.01 and
                abs(sol['p_absorb'] - existing['p_absorb']) < 0.01):
                is_dup = True
                break
        if not is_dup:
            filtered.append(sol)

    print(f"Found {len(filtered)} distinct self-consistent operators:")
    print(f"  {'p_ex':>6} {'p_ab':>6} | {'gap':>8}")
    print("-" * 30)
    for sol in filtered[:20]:
        print(f"  {sol['p_exchange']:6.3f} {sol['p_absorb']:6.3f} | {sol['gap']:8.4f}")

    if len(filtered) > 20:
        print(f"  ... and {len(filtered) - 20} more")

    print()
    print("OBSERVATION: gap = 2/3 is achieved along a CURVE in parameter space,")
    print("  not at a single point. The existing proof's matrix is one point on this curve.")

    return filtered


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the full spectral gap audit."""
    print()
    print("█" * 70)
    print("  SPECTRAL GAP AUDIT: Is 2/3 forced or chosen?")
    print("█" * 70)

    # Audit 1: What does symmetry constrain?
    audit_symmetry_constraint()

    # Audit 2: What IS forced?
    audit_what_IS_forced()

    # Audit 3: What's special about 2/3?
    audit_what_makes_two_thirds_special()

    # Audit 4: Find all self-consistent operators
    solutions = find_self_consistent_operators()

    # Audit 5: The specific existing proof matrix
    print()
    print("=" * 70)
    print("THE EXISTING PROOF'S MATRIX (for comparison)")
    print("=" * 70)
    gap_calculator(1/3, 2/3)

    print()
    print("=" * 70)
    print("ALTERNATIVE OPERATORS (for contrast)")
    print("=" * 70)
    gap_calculator(1/4, 1/2, verbose=True)
    gap_calculator(1/2, 1/2, verbose=True)
    gap_calculator(1/3, 1/3, verbose=True)

    print()
    print("█" * 70)
    print("  AUDIT COMPLETE")
    print("█" * 70)
    print()
    print("SUMMARY:")
    print("  1. 2/3 as a COUNTING RATIO is forced (2 of 3 states are non-boundary)")
    print("  2. 2/3 as a SPECTRAL GAP is NOT forced — it depends on the operator")
    print("  3. There IS a self-consistency argument: demand gap = non-boundary fraction")
    print("  4. This self-consistency picks out a specific curve of operators")
    print("  5. The maximal-exchange point on that curve gives the existing proof's matrix")
    print("  6. Honest status: 2/3 is a NATURAL choice, not a FORCED one")
    print("  7. The real invariant is the COUNT (2 out of 3), not the dynamics")


if __name__ == "__main__":
    main()

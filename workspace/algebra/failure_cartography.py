"""
Failure Cartography: Where does the distinction framework BREAK?

This module deliberately tests the limits of what the seed observations
can derive. For each test, we ask: "Can we derive X from O0-O8?"
If yes: the framework reaches further than expected.
If no: we've found a wall. Walls are VALUABLE — they define the boundary.

TESTS:
  1. Can we derive Z₅ (or any Z_p for p≠3) from the observations?
  2. Can we derive continuous groups WITHOUT embedding (raw observations)?
  3. Does the framework produce anything for 0 distinctions?
  4. Can we derive multiplication (not just addition) from distinction?
  5. Can we get non-abelian groups from single distinction?
  6. Does the framework handle INFINITE distinctions?
  7. Can we derive a metric (distance function) from distinction alone?
  8. Can we derive probability/measure from distinction alone?
  9. What happens with DEPENDENT (non-independent) distinctions?
  10. Can the framework derive its OWN observations? (circularity test)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


# ============================================================================
# TEST 1: Can we derive Z₅ or any Z_p for p≠3?
# ============================================================================

def test_z5_from_distinction() -> Dict:
    """Try to derive Z₅ from the observations.

    O1 says: 1 distinction → 3 things. NOT 5.
    Can we get to 5 by combining distinctions?

    2 distinctions: 3² = 9 states. NOT 5.
    n distinctions: 3^n states. 3^n is never 5 (or any prime except 3).

    Can we get Z₅ by quotient? 9/? ... no natural quotient gives 5.

    PREDICTION: Z₅ is NOT derivable. The framework is TERNARY.
    """
    results = {
        'target': 'Z₅',
        'derivable': False,
        'attempts': [],
    }

    # Attempt 1: direct derivation
    # 3^n for n=1..10: does any equal 5 or a multiple of 5?
    powers_of_3 = [3**n for n in range(1, 11)]
    has_factor_5 = [p for p in powers_of_3 if p % 5 == 0]
    results['attempts'].append({
        'method': 'direct 3^n',
        'values': powers_of_3,
        'contains_5_factor': has_factor_5,
        'works': len(has_factor_5) > 0,
    })

    # Attempt 2: subgroups of Z₃^n
    # Subgroups of Z₃^n have order 3^k for k ≤ n. Never 5.
    results['attempts'].append({
        'method': 'subgroups of Z₃^n',
        'note': 'Subgroup orders are powers of 3. 5 is not a power of 3.',
        'works': False,
    })

    # Attempt 3: product with Z₂ (from O1 symmetry)
    # Z₃ × Z₂ = Z₆. Still no Z₅.
    # Z₃^a × Z₂^b has order 3^a × 2^b. Never 5.
    products = []
    for a in range(5):
        for b in range(5):
            order = (3**a) * (2**b)
            products.append((a, b, order))
    has_5 = [p for p in products if p[2] == 5]
    results['attempts'].append({
        'method': 'Z₃^a × Z₂^b products',
        'orders': sorted(set(p[2] for p in products)),
        'contains_5': has_5,
        'works': len(has_5) > 0,
    })

    # Verdict
    results['verdict'] = ("Z₅ is NOT derivable from the distinction framework. "
                          "The framework only produces groups of order 2^a × 3^b. "
                          "Any prime p ∉ {2, 3} is UNREACHABLE.")
    results['wall'] = "The framework is confined to {2, 3}-groups."

    return results


# ============================================================================
# TEST 2: Can we derive a metric from distinction alone?
# ============================================================================

def test_metric_from_distinction() -> Dict:
    """Try to derive a distance function from O1-O3 alone.

    A metric needs: d(x,y) ≥ 0, d(x,y) = 0 iff x=y, d(x,y)=d(y,x), triangle inequality.

    Candidates:
    1. Hamming distance on Z₃^n states → IS a metric
    2. Graph distance on the Z₃ state graph → IS a metric
    3. Some algebraic distance from the group structure

    But: is the SPECIFIC metric forced, or are there many valid choices?
    """
    results = {
        'target': 'metric from distinction',
        'derivable': 'partially',
        'attempts': [],
    }

    # Attempt 1: Hamming distance
    # On Z₃: states are {T, C, B}. Hamming distance is always 0 or 1.
    # Not very informative — every pair of distinct states has distance 1.
    states = [(0,), (1,), (2,)]
    hamming = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            hamming[i, j] = sum(a != b for a, b in zip(states[i], states[j]))

    results['attempts'].append({
        'method': 'Hamming distance on Z₃',
        'matrix': hamming.tolist(),
        'is_metric': True,
        'note': 'Trivial — all pairs have distance 0 or 1. No structure beyond "same/different".',
        'forced': True,
    })

    # Attempt 2: Graph distance from adjacency
    # The Z₃ complete graph has all pairwise distances = 1.
    # No richer structure.
    results['attempts'].append({
        'method': 'Graph distance on K₃',
        'note': 'K₃ is the complete graph → all distances = 1. Same as Hamming.',
        'forced': True,
        'useful': False,
    })

    # Attempt 3: Can we get a RICHER metric?
    # What if we weight boundaries differently? O3 says boundary has weight.
    # Define: d(T, C) = 1, d(T, B) = w, d(C, B) = w where w = ?
    # For metric: triangle inequality requires d(T,C) ≤ d(T,B) + d(B,C) → 1 ≤ 2w → w ≥ 1/2
    # Also: d(T,B) ≤ d(T,C) + d(C,B) → w ≤ 1 + w → always true
    # So w ∈ [1/2, ∞) is valid. w is NOT determined by the observations.
    results['attempts'].append({
        'method': 'Weighted metric with boundary weight w',
        'note': 'd(T,C)=1, d(T,B)=d(C,B)=w. Triangle inequality requires w ≥ 1/2.',
        'w_range': '[1/2, ∞)',
        'forced': False,
        'wall': 'The metric exists but the boundary weight w is a FREE PARAMETER. '
                'The observations don\'t fix it. O3 says boundary has weight but doesn\'t say HOW MUCH.',
    })

    results['verdict'] = ("A discrete metric EXISTS (Hamming/graph) but is trivial. "
                          "A richer metric requires a free parameter (boundary weight). "
                          "The framework produces TOPOLOGY (what's connected) but not GEOMETRY (how far).")
    results['wall'] = "Distinction gives topology, not geometry. Distance requires additional structure."

    return results


# ============================================================================
# TEST 3: What about 0 distinctions?
# ============================================================================

def test_zero_distinctions() -> Dict:
    """What does the framework produce with 0 distinctions?

    O0 says: 'A unary logical position is incoherent.'
    So 0 distinctions should produce... nothing? Or paradox?
    """
    results = {
        'target': '0 distinctions',
        'derivable': 'edge case',
    }

    # 0 distinctions: Z₃^0 = Z₁ = {e} = trivial group
    # 1 state, 0 live states? No: 3^0 = 1, 2^0 = 1 → live fraction = 1/1 = 1
    # But what IS this state? No distinction has been made.
    # O0 says: you can't even have identity without distinction.

    results['state_count'] = 3**0  # = 1
    results['live_count'] = 2**0  # = 1
    results['live_fraction'] = 1.0
    results['notes'] = [
        "Z₃^0 = Z₁ = trivial group = 1 element",
        "Live fraction = 2^0/3^0 = 1/1 = 1.0 (everything is live)",
        "But O0 says identity alone is incoherent!",
        "The framework gives a well-defined answer (trivial group)",
        "but O0 says this answer is physically meaningless.",
        "TENSION: Math allows 0 distinctions; O0 forbids it.",
        "The framework doesn't break — it gives a trivially correct but",
        "philosophically vacuous answer.",
    ]
    results['wall'] = ("The math is fine with 0 distinctions (trivial group). "
                       "O0 is a PHILOSOPHICAL constraint, not a mathematical one. "
                       "The framework can't enforce O0 — it has to be imposed from outside.")

    return results


# ============================================================================
# TEST 4: Can we get non-abelian groups from SINGLE distinction?
# ============================================================================

def test_nonabelian_from_single() -> Dict:
    """Z₃ is abelian. Can we derive a non-abelian group from ONE distinction?

    The workspace claims Q₈ (quaternions) arise from O2 (binary distinction).
    But can we get non-abelian from O1 alone?
    """
    results = {
        'target': 'non-abelian from single distinction',
    }

    # Z₃ is abelian: a + b = b + a (mod 3) always.
    # From cycle 4 (operator zoo): {R, σ_TC} generate S₃ which IS non-abelian!
    # R·σ_TC ≠ σ_TC·R (commutator norm 2.449)

    # But S₃ acts on Z₃, it's not Z₃ itself.
    # The STATE SPACE is Z₃ (abelian).
    # The SYMMETRY GROUP is S₃ (non-abelian).
    # These are different things.

    R = np.array([[0,0,1],[1,0,0],[0,1,0]], dtype=float)
    sigma = np.array([[0,1,0],[1,0,0],[0,0,1]], dtype=float)

    # Check: R·σ ≠ σ·R
    RS = R @ sigma
    SR = sigma @ R

    results['R_sigma'] = RS.tolist()
    results['sigma_R'] = SR.tolist()
    results['commute'] = np.allclose(RS, SR)
    results['notes'] = [
        "Z₃ itself is abelian — always.",
        "But the SYMMETRY GROUP of Z₃ is S₃, which IS non-abelian.",
        "S₃ arises from O1 alone (rotation + complement swap).",
        "So non-abelian structure IS forced by single distinction,",
        "but it's the AUTOMORPHISM group, not the state group.",
        "The states are abelian; the symmetries are not.",
    ]
    results['verdict'] = ("YES — non-abelian S₃ arises from single distinction. "
                          "But it's the symmetry group, not the state group.")
    results['wall'] = None  # Not actually a wall — it works!

    return results


# ============================================================================
# TEST 5: Dependent distinctions
# ============================================================================

def test_dependent_distinctions() -> Dict:
    """What happens with DEPENDENT (non-independent) distinctions?

    Independent distinctions give Z₃^n (3^n states).
    But what if distinction B DEPENDS on distinction A?
    e.g., "B is the boundary of A" — then B and A are entangled.
    """
    results = {
        'target': 'dependent distinctions',
    }

    # If A and B are independent: 3×3 = 9 states
    # If B = "the boundary of A": then B is DETERMINED by A
    # States of A: {T_A, C_A, B_A}
    # B = "is this the boundary?" → B ∈ {yes, no} → 2 outcomes
    # But B is determined: B = yes iff A = B_A

    # This means dependent distinctions COLLAPSE the state space
    # Instead of 3^n, we get fewer states.

    # Example: A and B where B = f(A)
    # If f is injective: |states| = |A| = 3 (B adds no info)
    # If f is not injective: |states| = |A| = 3 (B still determined)

    # More interesting: A and B where B is PARTIALLY dependent
    # e.g., B can be {T_B, C_B, B_B} but P(B_B | A = B_A) = 1
    # (if A is boundary, B must be boundary too)

    # In this case: instead of 9 states, we have:
    # (T_A, T_B), (T_A, C_B), (T_A, B_B) — 3 states (A is thing)
    # (C_A, T_B), (C_A, C_B), (C_A, B_B) — 3 states (A is complement)
    # (B_A, B_B) — 1 state only (B is forced to boundary)
    # Total: 7 states instead of 9

    independent_states = 9
    dependent_states = 7  # with constraint B_A → B_B

    results['independent_count'] = independent_states
    results['dependent_count'] = dependent_states
    results['reduction'] = independent_states - dependent_states

    # Does the (2/3)^n formula still hold?
    # Independent: 4 live out of 9 → (2/3)² = 4/9 ✓
    # Dependent: live states are those with no B in either:
    # (T_A, T_B), (T_A, C_B), (C_A, T_B), (C_A, C_B) = 4 live
    # Out of 7 total → 4/7 ≈ 0.571 ≠ (2/3)² = 0.444
    live_dependent = 4
    live_fraction_dependent = live_dependent / dependent_states
    expected_independent = (2/3)**2

    results['live_dependent'] = live_dependent
    results['fraction_dependent'] = live_fraction_dependent
    results['fraction_independent'] = expected_independent
    results['formula_holds'] = abs(live_fraction_dependent - expected_independent) < 0.01

    results['notes'] = [
        f"Independent: {independent_states} states, {expected_independent:.4f} live fraction",
        f"Dependent: {dependent_states} states, {live_fraction_dependent:.4f} live fraction",
        f"The (2/3)^n formula BREAKS for dependent distinctions!",
        f"Dependent distinctions remove boundary states preferentially,",
        f"which INCREASES the live fraction above (2/3)^n.",
        f"The framework assumes independence. Dependencies break the formulas.",
    ]
    results['wall'] = ("Dependencies between distinctions break the (2/3)^n formula. "
                       "The framework assumes independent distinctions but doesn't derive this assumption.")

    return results


# ============================================================================
# TEST 6: Can the framework derive probability?
# ============================================================================

def test_probability_from_distinction() -> Dict:
    """Can we derive the concept of probability from distinction alone?

    The spectral gap proof USES probability (transition matrices are stochastic).
    But is probability itself derivable from O0-O8?
    """
    results = {
        'target': 'probability from distinction',
    }

    # O1 gives us 3 states. But why should they have PROBABILITIES?
    # Alternatives:
    # 1. All states equally weighted (maximum entropy) → p = 1/3 each
    # 2. Possibilistic (each state is possible or not, no weights)
    # 3. Quantum (complex amplitudes, not real probabilities)
    # 4. Fuzzy (partial membership in each state)

    # O6 says "symmetry is cheaper" → might justify uniform distribution
    # But O6 is about structures, not about dynamics

    # O8 says "self-referential systems have fixed points"
    # → the uniform distribution IS a fixed point of doubly stochastic operators
    # → but that assumes stochastic operators exist

    results['notes'] = [
        "The framework USES probability but doesn't DERIVE it.",
        "O1 gives states. O3 gives boundaries. Neither gives measures.",
        "Three alternatives are equally valid from the observations:",
        "  (a) Probabilistic: p_T + p_C + p_B = 1, p_i ≥ 0",
        "  (b) Possibilistic: each state is {possible, impossible}",
        "  (c) Quantum: complex amplitudes, |α_T|² + |α_C|² + |α_B|² = 1",
        "The choice between these is NOT forced by O0-O8.",
        "The spectral gap proof assumes (a). The existing algebra assumes (a).",
        "But nothing in the observations requires it.",
        "",
        "O6 (symmetry is cheaper) might justify uniform distribution",
        "but it doesn't justify probability ITSELF.",
    ]
    results['wall'] = ("Probability is assumed, not derived. "
                       "The framework needs an additional axiom: 'states have measures.' "
                       "Without this, the spectral gap and conservation law analyses are baseless.")

    return results


# ============================================================================
# TEST 7: Can we get to real numbers from distinction?
# ============================================================================

def test_reals_from_distinction() -> Dict:
    """Can the framework derive real numbers?

    Z₃ gives integers mod 3. Z₃^n gives integers mod 3 in each component.
    Can we get to ℝ or even ℚ?
    """
    results = {
        'target': 'real numbers from distinction',
    }

    # O4 says "a circle has two sides but one boundary"
    # U(1) = the circle group = {e^(iθ) : θ ∈ [0, 2π)}
    # Z₃ embeds in U(1) as cube roots of unity: ω = e^(2πi/3)
    # This gives a PATH from Z₃ to ℝ:
    #   Z₃ → U(1) → ℝ/2πℤ → ℝ

    # But the step from Z₃ to U(1) requires:
    # 1. The concept of a continuous circle
    # 2. The concept of embedding discrete in continuous

    # O4 arguably provides (1): it describes a circle.
    # O7 provides topology: "local vs global distinction"
    # Together they might justify U(1).

    # But going from U(1) to ℝ requires:
    # - Unwinding the circle to a line (logarithm)
    # - The concept of completeness (limits)

    # Can we do this from the observations?
    # O7: "A knot that looks trivial locally can be non-trivial globally"
    # → winding numbers → π₁(S¹) = ℤ
    # ℤ lives in ℝ, but ℤ ≠ ℝ

    # The gap: ℤ → ℚ → ℝ requires:
    # - Division (ℚ = field of fractions of ℤ)
    # - Completion (ℝ = Cauchy completion of ℚ)
    # Neither is forced by the observations.

    results['derivable_path'] = [
        "Z₃ → U(1)  via O4 (circle embedding) — plausible",
        "U(1) → ℤ   via O7 (winding numbers) — plausible",
        "ℤ → ℚ      requires division — NOT in observations",
        "ℚ → ℝ      requires completeness — NOT in observations",
    ]
    results['wall'] = ("The framework reaches ℤ (integers) via winding numbers, "
                       "but cannot reach ℝ (reals). The step ℤ → ℚ → ℝ requires "
                       "division and completeness, neither of which is in O0-O8.")

    return results


# ============================================================================
# TEST 8: Circularity test — can the framework derive its own observations?
# ============================================================================

def test_circularity() -> Dict:
    """Can O1-O8 derive THEMSELVES?

    If the framework can derive its own axioms, it might be circular.
    If it can't, the axioms are genuinely external inputs.
    """
    results = {
        'target': 'self-derivation (circularity)',
        'tests': [],
    }

    # Can O1 (distinction creates triple) derive itself?
    # Start with {T, C, B}. Can we derive that "defining one thing creates three"?
    # The statement O1 is ABOUT the act of distinguishing, not about Z₃ itself.
    # Z₃ doesn't contain the concept "I was created by an act of distinction."
    # O1 is meta-mathematical: it's about the PROCESS, not the RESULT.
    results['tests'].append({
        'observation': 'O1 (distinction creates triple)',
        'self_derivable': False,
        'reason': 'O1 is about the ACT of distinguishing. Z₃ is the RESULT. '
                  'The result cannot derive the process that created it.',
    })

    # Can O3 (boundary has weight) derive itself?
    # In Z₃, element 2 is "boundary." It's an element like any other.
    # Nothing in Z₃ says "element 2 is heavier than elements 0 and 1."
    # O3 is an external assertion about the MEANING of element 2.
    results['tests'].append({
        'observation': 'O3 (boundary has weight)',
        'self_derivable': False,
        'reason': 'Z₃ treats all elements equally. O3 is an external interpretation '
                  'that assigns different MEANING to one element.',
    })

    # Can O8 (self-reference has fixed points) derive itself?
    # Fixed point theorem: any continuous f: [0,1]→[0,1] has a fixed point.
    # But this requires topology (continuity), which requires more than Z₃.
    # Within Z₃: the identity map has 3 fixed points (trivially).
    # The rotation has 0 fixed points.
    # Fixed points exist but their SIGNIFICANCE is not derivable from Z₃.
    results['tests'].append({
        'observation': 'O8 (self-reference has fixed points)',
        'self_derivable': 'partially',
        'reason': 'Fixed points EXIST in Z₃ maps, but the theorem (Brouwer/Lawvere) '
                  'requires topology not present in the finite discrete structure.',
    })

    results['verdict'] = ("The framework is NOT circular. "
                          "O0-O8 are genuinely external inputs — the algebra they produce "
                          "cannot derive the observations that created it. "
                          "This is GOOD: it means the observations are real axioms, not tautologies.")

    return results


# ============================================================================
# MAIN: Run all failure tests
# ============================================================================

def main():
    tests = [
        ("Z₅ derivability", test_z5_from_distinction),
        ("Metric from distinction", test_metric_from_distinction),
        ("Zero distinctions", test_zero_distinctions),
        ("Non-abelian from single", test_nonabelian_from_single),
        ("Dependent distinctions", test_dependent_distinctions),
        ("Probability from distinction", test_probability_from_distinction),
        ("Real numbers from distinction", test_reals_from_distinction),
        ("Circularity test", test_circularity),
    ]

    print("█" * 70)
    print("  FAILURE CARTOGRAPHY: Where the framework breaks")
    print("█" * 70)

    walls = []
    passes = []

    for name, test_fn in tests:
        print(f"\n{'='*70}")
        print(f"  TEST: {name}")
        print(f"{'='*70}")

        result = test_fn()

        # Print key findings
        if 'verdict' in result:
            print(f"\n  VERDICT: {result['verdict']}")
        if 'wall' in result and result['wall']:
            print(f"  WALL: {result['wall']}")
            walls.append((name, result['wall']))
        else:
            passes.append(name)

        if 'notes' in result:
            for note in result['notes']:
                if note:
                    print(f"    {note}")

    # Summary
    print(f"\n{'='*70}")
    print(f"  FAILURE MAP SUMMARY")
    print(f"{'='*70}")
    print(f"\n  WALLS HIT ({len(walls)}):")
    for name, wall in walls:
        print(f"    ✗ {name}: {wall[:80]}...")

    print(f"\n  PASSED ({len(passes)}):")
    for name in passes:
        print(f"    ✓ {name}")

    print(f"\n  FRAMEWORK BOUNDARY:")
    print(f"    The distinction framework can derive:")
    print(f"      ✓ Finite groups of order 2^a × 3^b")
    print(f"      ✓ Topology (adjacency, connectivity)")
    print(f"      ✓ Symmetry groups (S₃ from single distinction)")
    print(f"      ✓ Integers (via winding numbers)")
    print(f"      ✓ Eigenvalue spectra (of any operator on the state space)")
    print(f"    The framework CANNOT derive:")
    print(f"      ✗ Groups of order involving primes > 3")
    print(f"      ✗ Geometry (distances, angles — only topology)")
    print(f"      ✗ Real numbers (stuck at ℤ)")
    print(f"      ✗ Probability (assumed, not derived)")
    print(f"      ✗ Independence of distinctions (assumed)")
    print(f"      ✗ Its own axioms (not circular — this is good)")


if __name__ == "__main__":
    main()

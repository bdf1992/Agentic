"""
Quadratic Residue Probe: What equations CAN and CAN'T be solved in Z₃?

Motivated by the user's observation:
  x² = -1 has solutions {2, 3} in Z₅
  x² = -1 has NO solutions in Z₃

This matters because:
  1. The distinction framework forces Z₃
  2. Z₃ is algebraically LIMITED — some natural equations have no solutions
  3. To solve them, you MUST extend to larger structures
  4. Those extensions might be FORCED (not chosen)

KEY QUESTION: Does trying to solve x² = -1 in Z₃ FORCE you toward Z₅?
Or does it force you to F₉ (the field of 9 elements)?
Or somewhere else entirely?

BACKGROUND:
  x² ≡ -1 (mod p) has solutions iff p ≡ 1 (mod 4)
    p=2: 1² = 1 ≡ -1, YES (degenerate)
    p=3: 1²=1, 2²=1, NO
    p=5: 2²=4≡-1, 3²=9≡4≡-1, YES
    p=7: NO (7 ≡ 3 mod 4)
    p=11: NO (11 ≡ 3 mod 4)
    p=13: YES (13 ≡ 1 mod 4)

  Z₃ is the "forced" prime. And it falls in the "NO" camp.
  This means the forced framework CANNOT solve x² = -1 natively.
  To solve it, you need to go OUTSIDE the framework.
"""

import numpy as np
from typing import Dict, List, Tuple


def quadratic_residues(p: int) -> Dict:
    """Compute all quadratic residues mod p and check if -1 is among them."""
    residues = set()
    square_map = {}
    for x in range(p):
        sq = (x * x) % p
        residues.add(sq)
        if sq not in square_map:
            square_map[sq] = []
        square_map[sq].append(x)

    minus_one = (p - 1) % p
    has_sqrt_minus_one = minus_one in residues
    sqrt_minus_one = square_map.get(minus_one, [])

    return {
        'p': p,
        'residues': sorted(residues),
        'non_residues': sorted(set(range(1, p)) - residues),
        'has_sqrt_minus_one': has_sqrt_minus_one,
        'sqrt_minus_one': sqrt_minus_one,
        'square_map': {k: sorted(v) for k, v in sorted(square_map.items())},
        'p_mod_4': p % 4,
    }


def all_equations_z3() -> Dict:
    """Catalog ALL polynomial equations over Z₃ and their solvability.

    For a 3-element field, check what's solvable and what's not.
    Every unsolvable equation reveals a LIMITATION of the forced framework.
    """
    results = {'solvable': [], 'unsolvable': []}

    # Quadratic equations: x² = a for a ∈ {0, 1, 2}
    for a in range(3):
        solutions = [x for x in range(3) if (x*x) % 3 == a]
        entry = {'equation': f'x² ≡ {a} (mod 3)', 'solutions': solutions}
        if solutions:
            results['solvable'].append(entry)
        else:
            results['unsolvable'].append(entry)

    # Cubic equations: x³ = a for a ∈ {0, 1, 2}
    for a in range(3):
        solutions = [x for x in range(3) if pow(x, 3, 3) == a]
        entry = {'equation': f'x³ ≡ {a} (mod 3)', 'solutions': solutions}
        if solutions:
            results['solvable'].append(entry)
        else:
            results['unsolvable'].append(entry)

    # General: ax² + bx + c ≡ 0 (mod 3)
    unsolvable_quadratics = []
    for a in range(1, 3):  # a ≠ 0
        for b in range(3):
            for c in range(3):
                solutions = [x for x in range(3) if (a*x*x + b*x + c) % 3 == 0]
                if not solutions:
                    unsolvable_quadratics.append({
                        'equation': f'{a}x² + {b}x + {c} ≡ 0 (mod 3)',
                        'a': a, 'b': b, 'c': c,
                    })

    results['unsolvable_general_quadratics'] = unsolvable_quadratics
    return results


def field_extension_f9() -> Dict:
    """When x² = -1 has no solution in Z₃, the natural extension is F₉.

    F₉ = Z₃[i] where i² = -1 = 2 (mod 3).
    This is a field of 9 elements: {a + bi : a, b ∈ Z₃}

    IS THIS FORCED? If the framework demands solutions to x² = -1,
    then F₉ is forced as the minimal extension.
    """
    # F₉ = {a + bi : a, b ∈ {0, 1, 2}} where i² = 2
    elements = []
    for a in range(3):
        for b in range(3):
            elements.append((a, b))

    # Multiplication: (a+bi)(c+di) = (ac + bd·i²) + (ad + bc)i
    # where i² = 2 (mod 3)
    def mul(x, y):
        a, b = x
        c, d = y
        real = (a*c + b*d*2) % 3  # i² = 2
        imag = (a*d + b*c) % 3
        return (real, imag)

    def add(x, y):
        return ((x[0]+y[0]) % 3, (x[1]+y[1]) % 3)

    # Verify it's a field: every nonzero element has a multiplicative inverse
    nonzero = [e for e in elements if e != (0, 0)]
    all_invertible = True
    inverses = {}
    for e in nonzero:
        found = False
        for f in nonzero:
            if mul(e, f) == (1, 0):
                inverses[e] = f
                found = True
                break
        if not found:
            all_invertible = False

    # Does x² = -1 = (2, 0) have solutions in F₉?
    minus_one = (2, 0)
    sqrt_minus_one = []
    for e in elements:
        if mul(e, e) == minus_one:
            sqrt_minus_one.append(e)

    # The element i = (0, 1) should be a sqrt of -1
    i_squared = mul((0, 1), (0, 1))

    return {
        'field_order': len(elements),
        'is_field': all_invertible,
        'has_sqrt_minus_one': len(sqrt_minus_one) > 0,
        'sqrt_minus_one': sqrt_minus_one,
        'i_squared': i_squared,
        'i_squared_equals_minus_one': i_squared == minus_one,
        'note': 'F₉ = Z₃[i] is a field of 9 elements where i² = -1 exists',
    }


def can_reach_z5() -> Dict:
    """The critical question: does solving x² = -1 lead to Z₅?

    SHORT ANSWER: No. It leads to F₉ = Z₃[i], which has 9 elements.

    Z₅ has 5 elements. 5 is prime. 5 ≠ 3^k for any k.
    F₉ has 9 = 3² elements. It's the NATURAL extension of Z₃.

    The distinction framework extends to F₉, not Z₅.
    Z₅ remains unreachable.

    BUT: Z₅ is where x² = -1 ALREADY has solutions.
    It doesn't NEED an extension. It's natively richer.

    This reveals an interesting asymmetry:
    - Z₃ is forced (minimal, from O1)
    - Z₃ LACKS sqrt(-1)
    - To get sqrt(-1), extend to F₉ (still in the Z₃ family)
    - Z₅ natively HAS sqrt(-1) but ISN'T forced by the observations
    - The framework pays a COST (9 elements instead of 5) for its ternary basis
    """
    return {
        'question': 'Does solving x²=-1 in the Z₃ framework lead to Z₅?',
        'answer': 'No',
        'actual_extension': 'F₉ = Z₃[i]',
        'f9_order': 9,
        'z5_order': 5,
        'z5_reachable': False,
        'insight': (
            'Z₃ is forced but algebraically LIMITED (no sqrt(-1)). '
            'The natural fix is F₉ (order 9), not Z₅ (order 5). '
            'Z₅ is NATIVELY richer but not in the Z₃ family. '
            'The ternary framework is stuck in the {3^k} tower: Z₃ → F₉ → F₂₇ → ...'
        ),
    }


def the_deeper_question() -> None:
    """Is there an observation that could FORCE Z₅?

    O1 forces 3 (one distinction → triple).
    What observation would force 5?

    Candidate: "Two overlapping distinctions create five regions."
    Think of a Venn diagram with 2 circles:
      region 1: A only
      region 2: B only
      region 3: A ∩ B (overlap)
      region 4: neither A nor B
      region 5: the boundary of the overlap

    Wait — that's just O2 (binary → 4 states) plus O3 (boundary of overlap).
    4 + 1 = 5? Let's see...

    O2 says: "Binary distinction creates four states: neither, A, B, both"
    If the OVERLAP (both) has its own boundary (per O3), that's a 5th thing.

    But this is a stretch. The "boundary of both" is the boundary of A
    intersected with the boundary of B — it's not necessarily a NEW element.
    """
    print("\n  THE DEEPER QUESTION: Is there a path to 5?")
    print()
    print("  O1 → 3 (distinction creates triple)")
    print("  O2 → 4 (binary creates quadruple)")
    print("  O2 + O3 → could the overlap boundary add a 5th?")
    print()
    print("  Candidate 1: Venn diagram regions")
    print("    A only, B only, A∩B, neither, ∂(A∩B)")
    print("    = 5 regions? But ∂(A∩B) ⊂ ∂A ∪ ∂B, not independent.")
    print()
    print("  Candidate 2: Distinction OF distinction")
    print("    Making a distinction ABOUT the act of distinguishing.")
    print("    O0 says unary is incoherent → you can't have a single meta-level.")
    print("    But if you distinguish between 'has been distinguished' and 'hasn't':")
    print("    {distinguished, undistinguished, boundary-of-meta}")
    print("    = 3 more states, giving 3 × 3 = 9, not 5.")
    print()
    print("  Candidate 3: Prime factorization argument")
    print("    5 = 2 + 3. Could Z₂ × Z₃ have a substructure of order 5?")
    print("    No. |Z₂ × Z₃| = 6. Subgroup orders divide 6: {1, 2, 3, 6}.")
    print("    5 doesn't divide 6. No Z₅ subgroup possible.")
    print()
    print("  Candidate 4: The equation x²=-1 itself as a 'distinction'")
    print("    'Can this equation be solved?' is a binary distinction.")
    print("    YES/NO. 2 states. Not 5.")
    print()
    print("  VERDICT: No natural path from O0-O8 to the number 5.")
    print("  5 is genuinely OUTSIDE the framework.")
    print("  The framework generates the tower {1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 27, ...}")
    print("  = numbers of the form 2^a × 3^b.")
    print("  5, 7, 10, 11, 13, 14, 15, 19, 20, 21, 22, 23, 25... all missing.")


def main():
    print("█" * 70)
    print("  QUADRATIC RESIDUE PROBE: What x²=-1 reveals about the framework")
    print("█" * 70)

    # Survey: which primes have sqrt(-1)?
    print(f"\n{'='*60}")
    print("  SURVEY: x² ≡ -1 (mod p) for small primes")
    print(f"{'='*60}")
    print(f"\n  {'p':>4} | {'p mod 4':>7} | {'has √(-1)':>10} | {'√(-1) values':>15} | {'all QRs'}")
    print("  " + "-" * 65)

    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
        qr = quadratic_residues(p)
        sqrt_str = str(qr['sqrt_minus_one']) if qr['sqrt_minus_one'] else "none"
        qr_str = str(qr['residues'])
        print(f"  {p:>4} | {qr['p_mod_4']:>7} | {'YES' if qr['has_sqrt_minus_one'] else 'NO':>10} "
              f"| {sqrt_str:>15} | {qr_str}")

    print()
    print("  PATTERN: x²≡-1 solvable iff p ≡ 1 (mod 4) (or p=2)")
    print("  Z₃: p=3 ≡ 3 (mod 4) → NO √(-1). The forced prime LACKS this.")
    print("  Z₅: p=5 ≡ 1 (mod 4) → HAS √(-1) = {2, 3}. Richer but not forced.")

    # What CAN Z₃ solve?
    print(f"\n{'='*60}")
    print("  WHAT CAN Z₃ SOLVE?")
    print(f"{'='*60}")

    eqs = all_equations_z3()
    print("\n  Solvable equations:")
    for eq in eqs['solvable']:
        print(f"    ✓ {eq['equation']}  →  x ∈ {eq['solutions']}")

    print("\n  UNSOLVABLE equations:")
    for eq in eqs['unsolvable']:
        print(f"    ✗ {eq['equation']}  →  no solution")

    print(f"\n  Unsolvable general quadratics (ax²+bx+c≡0):")
    for eq in eqs['unsolvable_general_quadratics'][:6]:
        print(f"    ✗ {eq['equation']}")
    if len(eqs['unsolvable_general_quadratics']) > 6:
        print(f"    ... and {len(eqs['unsolvable_general_quadratics'])-6} more")

    # F₉ extension
    print(f"\n{'='*60}")
    print("  F₉ = Z₃[i]: The forced extension")
    print(f"{'='*60}")

    f9 = field_extension_f9()
    print(f"\n  F₉ is a field: {f9['is_field']}")
    print(f"  i² = {f9['i_squared']} = (2, 0) = -1 in Z₃: {f9['i_squared_equals_minus_one']}")
    print(f"  √(-1) in F₉: {f9['sqrt_minus_one']}")
    print(f"  (These are ±i = (0,1) and (0,2) in Z₃²)")
    print(f"\n  F₉ has {f9['field_order']} elements = 3² — it's in the Z₃ tower.")
    print(f"  To solve x²=-1, the framework extends to F₉, NOT to Z₅.")

    # Can we reach Z₅?
    print(f"\n{'='*60}")
    print("  CAN WE REACH Z₅?")
    print(f"{'='*60}")

    z5_result = can_reach_z5()
    print(f"\n  {z5_result['question']}")
    print(f"  Answer: {z5_result['answer']}")
    print(f"  Natural extension: {z5_result['actual_extension']} (order {z5_result['f9_order']})")
    print(f"  Z₅ order: {z5_result['z5_order']} — not a power of 3")
    print(f"\n  {z5_result['insight']}")

    # The Z₃ tower
    print(f"\n{'='*60}")
    print("  THE Z₃ TOWER: What the framework CAN build")
    print(f"{'='*60}")

    print(f"\n  Z₃ → F₉ → F₂₇ → F₈₁ → F₂₄₃ → ...")
    print(f"  Orders: 3, 9, 27, 81, 243, ...")
    print(f"  Each is a field of 3^k elements.")
    print(f"  Each extends the previous by solving more equations.")
    print(f"\n  What equations does each level solve?")

    for k in range(1, 5):
        order = 3**k
        # The multiplicative group of F_{3^k} has order 3^k - 1
        mult_order = order - 1
        # x^n = 1 has gcd(n, mult_order) solutions
        print(f"\n  F_{order} (order 3^{k}):")
        print(f"    Multiplicative group: cyclic of order {mult_order}")
        print(f"    x² = -1 solvable: {mult_order % 4 == 0}")  # iff 4 | (3^k - 1)
        # For k=1: 3-1=2, 2%4≠0 → no
        # For k=2: 9-1=8, 8%4=0 → yes
        # For k=3: 27-1=26, 26%4=2 → no
        # For k=4: 81-1=80, 80%4=0 → yes

    print(f"\n  PATTERN: x²=-1 solvable in F_{{3^k}} iff k is EVEN.")
    print(f"  F₃ (k=1, odd): NO")
    print(f"  F₉ (k=2, even): YES ← first extension that solves x²=-1")
    print(f"  F₂₇ (k=3, odd): NO (lost again!)")
    print(f"  F₈₁ (k=4, even): YES")

    # The deeper question
    the_deeper_question()

    # What this means for the framework
    print(f"\n{'='*60}")
    print("  WHAT THIS MEANS")
    print(f"{'='*60}")
    print(f"""
  The user's observation x²=-1 → {{2,3}} in Z₅ reveals:

  1. Z₃ (the forced prime) is algebraically IMPOVERISHED
     - Can't solve x² = -1 (no square root of minus one)
     - Can't solve x² = 2 either (2 is not a QR mod 3)
     - Only squares in Z₃: {{0, 1}}. That's it.

  2. To solve x²=-1, the framework extends to F₉ = Z₃[i]
     - This IS reachable (it's 3²)
     - But it costs 9 elements to get what Z₅ does with 5
     - The ternary framework is LESS EFFICIENT than pentary for this task

  3. Z₅ is NATIVELY richer for algebraic equations
     - Squares in Z₅: {{0, 1, 4}} = {{0, 1, -1}}
     - So BOTH x²=1 and x²=-1 are solvable
     - Z₃ only solves x²=1

  4. The 'forced' framework pays an EFFICIENCY TAX
     - Need 9 elements where 5 would suffice
     - Because the starting prime (3) lacks quadratic richness
     - 3 ≡ 3 (mod 4) is the 'wrong' residue class for sqrt(-1)

  5. POSSIBLE NEW OBSERVATION needed:
     If the framework wants algebraic completeness (all quadratics solvable),
     it MUST extend beyond Z₃. The minimal extension for x²=-1 is F₉.
     No observation in O0-O8 FORCES this extension.
     It would require something like:
       "O9: Every equation that CAN be stated within a structure
        must have a solution in some extension of that structure."
     This is basically the axiom of algebraic closure.
     It's NOT in the seed. And it would be a HUGE addition.

  HONEST BOTTOM LINE:
    The user found a real limitation: Z₃ can't do what Z₅ does naturally.
    The framework's response (extend to F₉) is valid but expensive.
    The number 5 remains genuinely outside the framework.
    Algebraic closure is not forced by the observations.
    """)


if __name__ == "__main__":
    main()

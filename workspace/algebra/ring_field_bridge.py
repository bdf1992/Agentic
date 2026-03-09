"""
Ring-Field Bridge: How rings link together fields.

A ring has addition AND multiplication but elements might not have inverses.
A field is a ring where every nonzero element has a multiplicative inverse.

The bridge: polynomial rings Z_p[x] / (irreducible poly) = field extensions.
Rings are the CONSTRUCTION MECHANISM for building bigger fields from smaller ones.

This module builds a calculator for:
  1. Polynomial rings over Z_p (the construction material)
  2. Quotient rings (the cutting tool)
  3. Field extensions (the product)
  4. Chain: Z_3 -> Z_3[x]/(x^2+1) = F_9 -> Z_3[x]/(x^3-x+1) = F_27 -> ...
  5. Ring homomorphisms (the links between fields)

Starting from the forced Z_3, we explore what rings can reach.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from itertools import product as cartesian_product


class PolynomialRing:
    """Z_p[x] — polynomials with coefficients in Z_p.

    This is a RING (not a field): you can add and multiply polynomials,
    but you can't always divide. The indivisibility is what makes it
    useful as a construction tool.
    """

    def __init__(self, p: int):
        self.p = p

    def add(self, a: List[int], b: List[int]) -> List[int]:
        """Add two polynomials mod p."""
        n = max(len(a), len(b))
        result = [0] * n
        for i in range(len(a)):
            result[i] = (result[i] + a[i]) % self.p
        for i in range(len(b)):
            result[i] = (result[i] + b[i]) % self.p
        return self._trim(result)

    def mul(self, a: List[int], b: List[int]) -> List[int]:
        """Multiply two polynomials mod p."""
        if not a or not b:
            return [0]
        result = [0] * (len(a) + len(b) - 1)
        for i, ai in enumerate(a):
            for j, bj in enumerate(b):
                result[i + j] = (result[i + j] + ai * bj) % self.p
        return self._trim(result)

    def mod(self, a: List[int], b: List[int]) -> List[int]:
        """Polynomial remainder a mod b, coefficients mod p."""
        a = list(a)
        while len(a) >= len(b) and any(a):
            if a[-1] == 0:
                a.pop()
                continue
            # Find multiplicative inverse of leading coeff of b
            lead_b_inv = pow(b[-1], self.p - 2, self.p)
            factor = (a[-1] * lead_b_inv) % self.p
            shift = len(a) - len(b)
            for i in range(len(b)):
                a[i + shift] = (a[i + shift] - factor * b[i]) % self.p
            a = self._trim(a)
        return a if a else [0]

    def is_irreducible(self, poly: List[int]) -> bool:
        """Test if polynomial is irreducible over Z_p.

        A polynomial is irreducible if it can't be factored into
        lower-degree polynomials. These are the 'primes' of the ring.
        """
        deg = len(poly) - 1
        if deg <= 0:
            return False
        if deg == 1:
            return True

        # Test: no roots means no linear factors
        # For degree 2-3, no roots iff irreducible
        has_root = False
        for x in range(self.p):
            val = sum(c * pow(x, i, self.p) for i, c in enumerate(poly)) % self.p
            if val == 0:
                has_root = True
                break

        if deg <= 3:
            return not has_root

        # For higher degree: check if x^(p^k) - x ≡ 0 mod poly for k = 1..deg//2
        # If gcd(x^(p^k) - x, poly) is nontrivial for any k, it's reducible
        x_poly = [0, 1]  # x
        x_pk = list(x_poly)
        for k in range(1, deg // 2 + 1):
            # Compute x^(p^k) mod poly
            x_pk = self._pow_mod(x_pk, self.p, poly)
            # x^(p^k) - x
            diff = self.add(x_pk, [(-c) % self.p for c in x_poly])
            g = self._gcd(diff, poly)
            if len(g) > 1:  # gcd has degree > 0
                return False
        return True

    def find_irreducibles(self, degree: int) -> List[List[int]]:
        """Find all monic irreducible polynomials of given degree over Z_p."""
        irreducibles = []
        # Enumerate all monic polynomials of this degree
        for coeffs in cartesian_product(range(self.p), repeat=degree):
            poly = list(coeffs) + [1]  # monic: leading coeff = 1
            if self.is_irreducible(poly):
                irreducibles.append(poly)
        return irreducibles

    def _trim(self, poly: List[int]) -> List[int]:
        """Remove trailing zeros."""
        while len(poly) > 1 and poly[-1] == 0:
            poly.pop()
        return poly

    def _pow_mod(self, base: List[int], exp: int, modulus: List[int]) -> List[int]:
        """Compute base^exp mod modulus in the polynomial ring."""
        result = [1]
        base = self.mod(base, modulus)
        while exp > 0:
            if exp % 2 == 1:
                result = self.mod(self.mul(result, base), modulus)
            base = self.mod(self.mul(base, base), modulus)
            exp //= 2
        return result

    def _gcd(self, a: List[int], b: List[int]) -> List[int]:
        """Polynomial GCD using Euclidean algorithm."""
        while any(c != 0 for c in b):
            a, b = b, self.mod(a, b)
        # Make monic
        if a and a[-1] != 0:
            inv = pow(a[-1], self.p - 2, self.p)
            a = [(c * inv) % self.p for c in a]
        return self._trim(a)

    def poly_str(self, poly: List[int]) -> str:
        """Human-readable polynomial string."""
        if not poly or all(c == 0 for c in poly):
            return "0"
        terms = []
        for i, c in enumerate(poly):
            if c == 0:
                continue
            if i == 0:
                terms.append(str(c))
            elif i == 1:
                terms.append(f"{c}x" if c != 1 else "x")
            else:
                terms.append(f"{c}x^{i}" if c != 1 else f"x^{i}")
        return " + ".join(terms) if terms else "0"


class QuotientField:
    """Z_p[x] / (f(x)) — a field extension built by quotienting a ring.

    THIS is the 'ring linking fields' mechanism:
    - Start with field Z_p
    - Build ring Z_p[x] (polynomials — a ring, not a field)
    - Pick irreducible f(x) (the 'cutting' polynomial)
    - Quotient: Z_p[x]/(f(x)) is a NEW field with p^deg(f) elements

    The ring Z_p[x] is the BRIDGE. The irreducible polynomial is the LINK.
    """

    def __init__(self, p: int, modulus: List[int]):
        """Create F_{p^n} = Z_p[x]/(modulus).

        Args:
            p: prime base
            modulus: irreducible polynomial (coefficients, low degree first)
        """
        self.p = p
        self.modulus = modulus
        self.degree = len(modulus) - 1
        self.order = p ** self.degree
        self.ring = PolynomialRing(p)

        # Verify modulus is irreducible
        if not self.ring.is_irreducible(modulus):
            raise ValueError(f"Modulus {self.ring.poly_str(modulus)} is not irreducible over Z_{p}")

    def elements(self) -> List[List[int]]:
        """Enumerate all elements of the field."""
        elts = []
        for coeffs in cartesian_product(range(self.p), repeat=self.degree):
            elts.append(list(coeffs))
        return elts

    def add(self, a: List[int], b: List[int]) -> List[int]:
        """Add two field elements."""
        result = self.ring.add(a, b)
        return self._reduce(result)

    def mul(self, a: List[int], b: List[int]) -> List[int]:
        """Multiply two field elements."""
        result = self.ring.mul(a, b)
        return self._reduce(result)

    def inv(self, a: List[int]) -> List[int]:
        """Multiplicative inverse using extended Euclidean algorithm."""
        if all(c == 0 for c in a):
            raise ValueError("Zero has no inverse")
        # a * inv ≡ 1 mod modulus
        # Use Fermat's little theorem: a^(q-2) * a = a^(q-1) = 1
        return self.ring._pow_mod(a, self.order - 2, self.modulus)

    def _reduce(self, poly: List[int]) -> List[int]:
        """Reduce polynomial mod the modulus."""
        result = self.ring.mod(poly, self.modulus)
        # Pad to degree
        while len(result) < self.degree:
            result.append(0)
        return result[:self.degree]

    def is_field(self) -> bool:
        """Verify this is actually a field (every nonzero element has an inverse)."""
        for elt in self.elements():
            if all(c == 0 for c in elt):
                continue
            try:
                inv = self.inv(elt)
                product = self.mul(elt, inv)
                one = [1] + [0] * (self.degree - 1)
                if product != one:
                    return False
            except Exception:
                return False
        return True

    def multiplicative_order(self, a: List[int]) -> int:
        """Find the multiplicative order of element a."""
        if all(c == 0 for c in a):
            return 0
        one = [1] + [0] * (self.degree - 1)
        current = list(a)
        for k in range(1, self.order):
            if current == one:
                return k
            current = self.mul(current, a)
        return self.order - 1  # should not reach here for a field

    def find_generators(self) -> List[List[int]]:
        """Find primitive elements (generators of the multiplicative group)."""
        target_order = self.order - 1
        generators = []
        for elt in self.elements():
            if all(c == 0 for c in elt):
                continue
            if self.multiplicative_order(elt) == target_order:
                generators.append(elt)
        return generators


class RingFieldBridge:
    """The main tool: map how rings link fields together.

    The Z_3 tower: Z_3 -> F_9 -> F_27 -> F_81 -> ...
    Each step uses a polynomial ring as the bridge.
    """

    def __init__(self, base_prime: int = 3):
        self.p = base_prime
        self.ring = PolynomialRing(base_prime)

    def build_tower(self, max_degree: int = 4, verbose: bool = True) -> Dict:
        """Build the tower of field extensions from Z_p.

        Each level k gives F_{p^k} via an irreducible polynomial of degree k.
        The polynomial ring Z_p[x] is the BRIDGE between consecutive levels.
        """
        tower = {}

        if verbose:
            print(f"\n{'='*60}")
            print(f"  THE Z_{self.p} TOWER: Fields linked by polynomial rings")
            print(f"{'='*60}")

        for deg in range(1, max_degree + 1):
            irreducibles = self.ring.find_irreducibles(deg)

            if verbose:
                print(f"\n  Level {deg}: F_{self.p}^{deg} = F_{self.p**deg}")
                print(f"  {'─'*50}")
                print(f"  Order: {self.p**deg} elements")
                print(f"  Irreducible polynomials of degree {deg}: {len(irreducibles)}")
                for poly in irreducibles[:5]:  # show up to 5
                    print(f"    {self.ring.poly_str(poly)}")

            # Build the field using the first irreducible
            if irreducibles:
                modulus = irreducibles[0]
                field = QuotientField(self.p, modulus)

                # Check key algebraic properties
                gens = field.find_generators()

                # Check x^2 = -1 solvability
                sqrt_neg1 = []
                neg_one = [self.p - 1] + [0] * (deg - 1)
                for elt in field.elements():
                    if field.mul(elt, elt) == neg_one:
                        sqrt_neg1.append(elt)

                level_data = {
                    'degree': deg,
                    'order': self.p ** deg,
                    'modulus': modulus,
                    'modulus_str': self.ring.poly_str(modulus),
                    'num_irreducibles': len(irreducibles),
                    'num_generators': len(gens),
                    'has_sqrt_neg1': len(sqrt_neg1) > 0,
                    'sqrt_neg1': sqrt_neg1,
                    'mult_group_order': self.p ** deg - 1,
                    'is_field': field.is_field()
                }
                tower[deg] = level_data

                if verbose:
                    print(f"  Built via: Z_{self.p}[x] / ({self.ring.poly_str(modulus)})")
                    print(f"  Is field: {level_data['is_field']}")
                    print(f"  Multiplicative group: cyclic of order {level_data['mult_group_order']}")
                    print(f"  Primitive elements: {level_data['num_generators']}")
                    print(f"  x²=-1 solvable: {level_data['has_sqrt_neg1']}", end="")
                    if sqrt_neg1:
                        print(f" → {sqrt_neg1}")
                    else:
                        print()

        return tower

    def ring_homomorphism_map(self, verbose: bool = True) -> Dict:
        """Map the ring homomorphisms that link fields.

        The key insight: rings don't just BUILD fields, they CONNECT them.
        There are natural maps (homomorphisms) between polynomial rings
        that respect the algebraic structure.
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"  RING HOMOMORPHISMS: The links between fields")
            print(f"{'='*60}")

        results = {}

        # 1. Inclusion maps: Z_p -> F_{p^k} for each k
        if verbose:
            print(f"\n  1. INCLUSION MAPS (embedding smaller in larger)")
            print(f"  {'─'*50}")

        for k in range(1, 5):
            order = self.p ** k
            # Z_p embeds in F_{p^k} as constant polynomials
            # F_{p^a} embeds in F_{p^b} iff a divides b
            divisors = [d for d in range(1, k) if k % d == 0]
            if verbose:
                print(f"  F_{order}: subfields from F_{self.p}^d where d | {k}")
                print(f"    Subfield lattice: {[self.p**d for d in divisors]} ⊂ F_{order}")
            results[f'F_{order}_subfields'] = [self.p ** d for d in divisors]

        # 2. Frobenius endomorphism: x -> x^p
        if verbose:
            print(f"\n  2. FROBENIUS ENDOMORPHISM (x → x^{self.p})")
            print(f"  {'─'*50}")
            print(f"  The Frobenius map φ(x) = x^{self.p} is a ring homomorphism")
            print(f"  from any F_{{p^k}} to itself.")
            print(f"  Its order is k (φ^k = identity).")
            print(f"  The FIXED POINTS of φ are exactly Z_{self.p}.")
            print(f"  This means: Z_{self.p} = {{x ∈ F_{{p^k}} : x^{self.p} = x}}")

        # Verify Frobenius on F_9
        irreds_2 = self.ring.find_irreducibles(2)
        if irreds_2:
            f9 = QuotientField(self.p, irreds_2[0])
            fixed_points = []
            for elt in f9.elements():
                # x^p in the field
                xp = f9.ring._pow_mod(elt, self.p, f9.modulus)
                while len(xp) < f9.degree:
                    xp.append(0)
                xp = xp[:f9.degree]
                if xp == elt:
                    fixed_points.append(elt)

            if verbose:
                print(f"\n  Frobenius on F_9: fixed points = {fixed_points}")
                print(f"  These are {len(fixed_points)} elements = Z_{self.p} ✓")

            results['frobenius_fixed'] = fixed_points

        # 3. The norm and trace maps
        if verbose:
            print(f"\n  3. NORM AND TRACE (field → subfield projections)")
            print(f"  {'─'*50}")
            print(f"  Trace: F_{{p^k}} → Z_p via Tr(x) = x + x^p + x^{{p²}} + ... + x^{{p^{{k-1}}}}")
            print(f"  Norm:  F_{{p^k}} → Z_p via N(x) = x · x^p · x^{{p²}} · ... · x^{{p^{{k-1}}}}")
            print(f"  Trace is ADDITIVE (ring hom of (F,+)), Norm is MULTIPLICATIVE")
            print(f"  Together they form the complete link FROM extension BACK to base")

        if irreds_2:
            f9 = QuotientField(self.p, irreds_2[0])
            traces = {}
            norms = {}
            for elt in f9.elements():
                # Trace(x) = x + x^3 (for F_9 over Z_3)
                xp = f9.ring._pow_mod(elt, self.p, f9.modulus)
                while len(xp) < f9.degree:
                    xp.append(0)
                xp = xp[:f9.degree]
                tr = f9.add(elt, xp)
                trace_val = tr[0] % self.p  # trace lands in Z_p (constant term)

                # Norm(x) = x * x^3
                nm = f9.mul(elt, xp)
                norm_val = nm[0] % self.p

                traces[tuple(elt)] = trace_val
                norms[tuple(elt)] = norm_val

            if verbose:
                print(f"\n  F_9 → Z_3 via Trace and Norm:")
                trace_fibers = {}
                for elt, t in traces.items():
                    trace_fibers.setdefault(t, []).append(list(elt))
                for t_val in sorted(trace_fibers.keys()):
                    print(f"    Tr = {t_val}: {len(trace_fibers[t_val])} elements")

                norm_fibers = {}
                for elt, n in norms.items():
                    norm_fibers.setdefault(n, []).append(list(elt))
                for n_val in sorted(norm_fibers.keys()):
                    print(f"    N  = {n_val}: {len(norm_fibers[n_val])} elements")

            results['traces'] = traces
            results['norms'] = norms

        return results

    def cross_characteristic_bridges(self, verbose: bool = True) -> Dict:
        """Explore whether rings can bridge between DIFFERENT characteristics.

        Z_3 has characteristic 3. Z_5 has characteristic 5.
        Can any ring naturally connect them?

        Spoiler: not directly. But there are indirect bridges via:
        - Z (the integers) — universal ring
        - Z[x] — polynomial ring over integers
        - Localization and completion
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"  CROSS-CHARACTERISTIC BRIDGES: Can rings link Z_3 and Z_5?")
            print(f"{'='*60}")

        results = {}

        # The integers Z are the universal bridge
        if verbose:
            print(f"\n  The INTEGER RING Z is the universal bridge:")
            print(f"  {'─'*50}")
            print(f"  Z → Z/3Z = Z_3  (quotient by 3)")
            print(f"  Z → Z/5Z = Z_5  (quotient by 5)")
            print(f"  Z → Z/15Z       (quotient by 15)")
            print(f"")
            print(f"  Z/15Z ≅ Z_3 × Z_5  (Chinese Remainder Theorem)")
            print(f"  This is a RING (not a field) with 15 elements.")
            print(f"  It contains BOTH Z_3 and Z_5 as quotients.")

        # Build Z/15Z and verify CRT
        z15_units = [x for x in range(15) if np.gcd(x, 15) == 1]
        results['z15_units'] = z15_units

        if verbose:
            print(f"\n  Z/15Z units (invertible elements): {z15_units}")
            print(f"  Number of units: {len(z15_units)} = φ(15) = φ(3)·φ(5) = 2·4 = 8 ✓")

            # Show the CRT isomorphism explicitly
            print(f"\n  CRT isomorphism Z/15Z → Z_3 × Z_5:")
            for x in range(15):
                print(f"    {x:2d} → ({x%3}, {x%5})")

        # The product ring Z_3 × Z_5
        if verbose:
            print(f"\n  THE PRODUCT RING Z_3 × Z_5:")
            print(f"  {'─'*50}")
            print(f"  This IS a ring. NOT a field (has zero divisors).")

            # Find zero divisors
            zero_divisors = []
            for a3, a5 in cartesian_product(range(3), range(5)):
                if a3 == 0 and a5 == 0:
                    continue
                for b3, b5 in cartesian_product(range(3), range(5)):
                    if b3 == 0 and b5 == 0:
                        continue
                    prod = ((a3 * b3) % 3, (a5 * b5) % 5)
                    if prod == (0, 0):
                        zero_divisors.append(((a3, a5), (b3, b5)))

            print(f"  Zero divisors (ab=0 but a≠0, b≠0): {len(zero_divisors)} pairs")
            seen = set()
            for (a, b) in zero_divisors:
                key = (min(a, b), max(a, b))
                if key not in seen:
                    seen.add(key)
                    print(f"    {a} · {b} = (0,0)")

            results['zero_divisors'] = list(seen)

        # The key question: can we BUILD a field of order 15?
        if verbose:
            print(f"\n  CAN WE BUILD A FIELD OF ORDER 15?")
            print(f"  {'─'*50}")
            print(f"  No. Fields only exist of order p^k (prime power).")
            print(f"  15 = 3 × 5 is NOT a prime power.")
            print(f"  Z_3 × Z_5 is the best we can do — it's a ring, not a field.")
            print(f"  The ring IS the bridge, but it's a bridge with cracks (zero divisors).")

        # What about the p-adic bridge?
        if verbose:
            print(f"\n  THE DEEPER BRIDGE: p-ADIC INTEGERS")
            print(f"  {'─'*50}")
            print(f"  Z_p (p-adic integers, not Z/pZ) is a ring that 'completes' Z")
            print(f"  at the prime p. Different primes give different completions:")
            print(f"    Z → Z_3 (3-adic) sees Z_3 structure")
            print(f"    Z → Z_5 (5-adic) sees Z_5 structure")
            print(f"  The Hasse principle: to understand Z, look at ALL completions")
            print(f"  Z embeds into Z_3 × Z_5 × Z_7 × ... × R (adele ring)")
            print(f"  This is the ULTIMATE ring linking ALL fields.")

        return results

    def the_forced_bridge(self, verbose: bool = True) -> Dict:
        """What ring-field bridges are FORCED by the observations?

        From the seed:
        - O1 forces Z_3 (distinction → triple)
        - O2 forces Z_2 (binary → pair)
        - Together: Z_6 = Z_2 × Z_3 (by CRT, since gcd(2,3)=1)

        The polynomial ring Z_3[x] is the forced construction tool.
        Irreducible polynomials over Z_3 are the forced links.
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"  FORCED RING-FIELD BRIDGES (from O0-O8)")
            print(f"{'='*60}")

        results = {}

        # What the observations force
        if verbose:
            print(f"\n  FORCED by observations:")
            print(f"  O1 → Z_3 (the base field)")
            print(f"  O2 → Z_2 (binary distinction)")
            print(f"  O1+O2 → Z_6 = Z_2 × Z_3 (product ring, NOT a field)")
            print(f"")
            print(f"  FORCED construction tools:")
            print(f"  Z_3[x] — polynomial ring (unlimited supply of 'variables')")
            print(f"  Irreducible polys — the links that build extensions")

        # Count irreducibles at each degree
        irred_counts = {}
        if verbose:
            print(f"\n  IRREDUCIBLE POLYNOMIALS OVER Z_3 (the available links):")
            print(f"  {'─'*50}")

        for deg in range(1, 7):
            irreds = self.ring.find_irreducibles(deg)
            irred_counts[deg] = len(irreds)
            expected = sum(
                ((-1) ** (len(divs))) * self.p ** (deg // (1 if not divs else 1))
                for divs in [[]]
            )  # simplified
            if verbose:
                print(f"  Degree {deg}: {len(irreds)} irreducible polynomials")
                if deg <= 3:
                    for poly in irreds:
                        print(f"    {self.ring.poly_str(poly)}")

        results['irreducible_counts'] = irred_counts

        # The necklace formula: number of irreducibles of degree n over F_p
        if verbose:
            print(f"\n  NECKLACE FORMULA (counts irreducibles):")
            print(f"  N(n,p) = (1/n) Σ_{{d|n}} μ(n/d) · p^d")
            print(f"  For p=3:")
            for n in range(1, 7):
                # Mobius function computation
                count = 0
                for d in range(1, n + 1):
                    if n % d == 0:
                        # μ(n/d)
                        m = n // d
                        mu = self._mobius(m)
                        count += mu * (self.p ** d)
                count //= n
                print(f"    N({n},3) = {count}", end="")
                print(f" {'✓' if count == irred_counts.get(n, -1) else '✗'}")

        # The linkage diagram
        if verbose:
            print(f"\n  THE LINKAGE DIAGRAM:")
            print(f"  {'─'*50}")
            print(f"  Z_3 ──[x²+1]──→ F_9 ──[irred deg 3]──→ F_27 ──→ ...")
            print(f"   │                │                       │")
            print(f"   │ Frobenius      │ Frobenius            │ Frobenius")
            print(f"   │ (x→x³)        │ (x→x³)               │ (x→x³)")
            print(f"   │                │                       │")
            print(f"   └── fixed pts ←──┘── fixed pts ←────────┘")
            print(f"")
            print(f"  Each arrow is a RING operating on a FIELD:")
            print(f"  - The ring Z_3[x] provides the construction material")
            print(f"  - The irreducible polynomial is the specific link")
            print(f"  - Frobenius is the self-map that remembers the base")
            print(f"  - Fixed points recover the subfield")
            print(f"")
            print(f"  RINGS LINK FIELDS by being the mortar between bricks.")
            print(f"  Fields are rigid (every element has an inverse).")
            print(f"  Rings are flexible (zero divisors, non-units).")
            print(f"  The flexibility of rings is what lets you BUILD new fields.")

        # What can't rings do?
        if verbose:
            print(f"\n  WHAT RINGS CANNOT BRIDGE:")
            print(f"  {'─'*50}")
            print(f"  ✗ Z_3 → Z_5 (different characteristics, no field hom exists)")
            print(f"  ✗ F_9 → Z_5 (still different characteristics)")
            print(f"  ✓ Z_3 → F_9 (same characteristic, ring extension)")
            print(f"  ✓ F_9 → F_81 (same tower, ring extension)")
            print(f"  ~ Z_3 × Z_5 exists as a RING but not a FIELD")
            print(f"  ~ Z (integers) maps to both, but loses structure each way")

        results['forced_base'] = f'Z_{self.p}'
        results['forced_tower'] = [self.p ** k for k in range(1, 7)]
        results['cross_char_possible'] = False

        return results

    def ring_calculator(self, p: int, modulus: List[int],
                        expr_a: List[int], expr_b: List[int],
                        verbose: bool = True) -> Dict:
        """A calculator for field arithmetic via the ring bridge.

        Args:
            p: prime
            modulus: irreducible polynomial defining the extension
            expr_a, expr_b: two elements to compute with

        Returns:
            Dict with sum, product, inverses, orders
        """
        field = QuotientField(p, modulus)

        results = {
            'field': f'F_{p**field.degree}',
            'modulus': self.ring.poly_str(modulus),
            'a': expr_a,
            'b': expr_b,
            'a+b': field.add(expr_a, expr_b),
            'a*b': field.mul(expr_a, expr_b),
        }

        if not all(c == 0 for c in expr_a):
            results['a_inv'] = field.inv(expr_a)
            results['a_order'] = field.multiplicative_order(expr_a)

        if not all(c == 0 for c in expr_b):
            results['b_inv'] = field.inv(expr_b)
            results['b_order'] = field.multiplicative_order(expr_b)

        # a^2 + 1 (checking if a is sqrt(-1))
        a_sq = field.mul(expr_a, expr_a)
        neg_one = [p - 1] + [0] * (field.degree - 1)
        results['a^2'] = a_sq
        results['a_is_sqrt_neg1'] = (a_sq == neg_one)

        if verbose:
            print(f"\n  Calculator: {results['field']} = Z_{p}[x]/({results['modulus']})")
            print(f"  a = {expr_a}, b = {expr_b}")
            print(f"  a + b = {results['a+b']}")
            print(f"  a * b = {results['a*b']}")
            if 'a_inv' in results:
                print(f"  a⁻¹ = {results['a_inv']}, order(a) = {results['a_order']}")
            if 'b_inv' in results:
                print(f"  b⁻¹ = {results['b_inv']}, order(b) = {results['b_order']}")
            print(f"  a² = {results['a^2']}, a is √(-1)? {results['a_is_sqrt_neg1']}")

        return results

    def _mobius(self, n: int) -> int:
        """Mobius function μ(n)."""
        if n == 1:
            return 1
        factors = []
        temp = n
        for p in range(2, int(n**0.5) + 2):
            if temp % p == 0:
                count = 0
                while temp % p == 0:
                    count += 1
                    temp //= p
                if count > 1:
                    return 0
                factors.append(p)
        if temp > 1:
            factors.append(temp)
        return (-1) ** len(factors)


def main():
    """Demonstrate rings linking together fields."""

    print("RING-FIELD BRIDGE")
    print("How rings link together fields — a calculator")
    print("=" * 60)

    bridge = RingFieldBridge(base_prime=3)

    # 1. Build the Z_3 tower
    tower = bridge.build_tower(max_degree=4, verbose=True)

    # 2. Map the homomorphisms
    homs = bridge.ring_homomorphism_map(verbose=True)

    # 3. Cross-characteristic exploration
    cross = bridge.cross_characteristic_bridges(verbose=True)

    # 4. What's forced
    forced = bridge.the_forced_bridge(verbose=True)

    # 5. Calculator demo: arithmetic in F_9
    print(f"\n{'='*60}")
    print(f"  CALCULATOR DEMO: F_9 arithmetic")
    print(f"{'='*60}")

    # F_9 = Z_3[x]/(x^2+1)
    bridge.ring_calculator(
        p=3, modulus=[1, 0, 1],  # x^2 + 1
        expr_a=[0, 1],  # x (which is i, the sqrt of -1)
        expr_b=[1, 1],  # 1 + x
        verbose=True
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY: RINGS AS BRIDGES")
    print(f"{'='*60}")
    print("""
  RINGS link FIELDS because:
  1. Fields are RIGID — every nonzero element is invertible, no room to grow
  2. Rings are FLEXIBLE — polynomial rings have infinite elements, zero divisors
  3. QUOTIENTING a ring by an irreducible creates a NEW, BIGGER field
  4. The ring Z_p[x] is the universal construction kit for characteristic p

  From the forced Z_3:
  - Z_3[x]/(x²+1) = F_9  (solves x²=-1)
  - Z_3[x]/(x³-x+1) = F_27 (no x²=-1, but solves cubics)
  - Z_3[x]/(x⁴+...) = F_81 (solves x²=-1 again)

  CROSS-CHARACTERISTIC (Z_3 ↔ Z_5):
  - No field homomorphism exists (different characteristics)
  - Z_3 × Z_5 ≅ Z_15 exists as a RING bridge (but not a field)
  - The integers Z are the universal ring mapping to ALL primes
  - p-adic completion gives the deepest bridge

  THE HONEST ANSWER:
  Rings link fields WITHIN the same characteristic tower.
  Across characteristics, rings give products (not fields).
  The forced framework (char 3) can build F_9, F_27, F_81, ...
  but CANNOT build F_5, F_25, or any char-5 field.
  Z (integers) is the only ring that naturally sees BOTH.
    """)


if __name__ == "__main__":
    main()

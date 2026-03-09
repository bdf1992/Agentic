# Forced Math from Distinction — Work Journal

> Autonomous derivation work. Skeptical. Build tools, not proofs-of-identity.
> Every entry: 15-minute increment. What was tried, what broke, what works, what's next.
>
> Seed: `experiments/seeds/cartography_v1.json` (O0-O8, CL1-CL3, OB1-OB4)
> Constraint: derive everything, assume nothing, smuggle no constants.
> Philosophy: a calculator IS math but it's a CALCULATOR. Build usable systems.

---

## Ground Rules (for every session)

1. **Skepticism first.** If a claim says "forced," test whether it's actually forced or just convenient.
2. **No identity-hunting.** Don't just confirm Z3/Q8/2/3 again. Push into territory that might fail.
3. **Build tools.** Every derivation should produce a runnable function that takes inputs and gives outputs.
4. **Tunable systems.** Parameters that trace to the algebra — but usable like knobs on a mixer.
5. **Log failures.** What DIDN'T work is as valuable as what did.
6. **Question the 17 properties.** Are they all genuinely satisfied, or are some hand-waved?

## Existing Landscape (snapshot)

- `workspace/algebra/` — 11 modules (Z3, Q8, topology, conservation, spectral, memory, symmetry, etc.)
- `workspace/derivations/` — 7 proof documents
- `workspace/validation/verify_all_properties.py` — claims 17/17 pass
- Previous work focused on PROVING structures are forced
- Gap: almost no TOOLS that USE these structures computationally

## Open Questions (attack these)

1. Is the spectral gap really 2/3, or does that depend on the specific operator chosen?
2. Can you build a calculator where Z3 rotations compose and produce measurable outputs?
3. What happens when you chain O1 → O2 → O3 iteratively? Does it converge or diverge?
4. Can the forced structures generate actual geometry (meshes, tilings) without smuggling?
5. Are the conservation laws (CL1-CL3) actually checkable computationally, or just stated?
6. What breaks? Where does the forced-structure framework HIT A WALL?

---

## Session Log

(entries below, 15-minute increments, newest at bottom)

---

### 2026-03-09 T+00:00 – T+00:15 | Spectral Gap Audit — Is 2/3 forced?

**Task:** Open Question #1 — test whether spectral gap 2/3 is genuinely forced or operator-dependent.

**Built:** `algebra/spectral_gap_audit.py` — a calculator tool that takes arbitrary transition probabilities for the 3-state system and computes spectral gap, eigenvalues, mixing time, half-life.

**Key finding: 2/3 as a spectral gap is NOT forced.**

The existing `spectral_gap_proof.py` uses this transition matrix:
- T → C with prob 1/3, T → B with prob 2/3
- C → T with prob 1/3, C → B with prob 2/3
- B → B with prob 1 (absorbing)

But those probabilities are **assumed, not derived**. Different operators give different gaps:

| p_exchange | p_absorb | Gap   | Note |
|-----------|----------|-------|------|
| 1/3       | 2/3      | 0.667 | existing proof's choice |
| 1/2       | 1/2      | 0.500 | uniform (max entropy) |
| 1/3       | 1/3      | 0.333 | equal all targets |
| 1/4       | 1/2      | 0.500 | arbitrary |
| 0.1       | 0.8      | 0.800 | high absorb |

**What IS forced:**
- 2/3 as a **counting ratio** (2 of 3 states are non-boundary) — YES, forced
- 2/3 as a **volume fraction** ((2/3)^d in d dimensions) — YES, forced
- 2/3 as |Z₂|/|Z₃| — YES, forced
- 2/3 as a **spectral gap** — NO, depends on operator choice

**But there's a self-consistency argument (O8):**
If you DEMAND that the spectral gap equals the non-boundary fraction, you get p_absorb = 2/3 and p_exchange ≤ 1/3. The maximal-exchange point (no self-loops) gives exactly the existing proof's matrix. So the existing matrix is the unique operator satisfying:
1. gap = non-boundary fraction (self-consistency / O8)
2. maximal exchange (no lazy loops)
3. T↔C symmetry (O1)

**Honest status:** 2/3 is a *natural* choice via self-consistency, not a *forced* one. The existing proof conflates the combinatorial ratio with the dynamical gap.

**Tool output:** `gap_calculator(p_ex, p_ab)` — usable function, takes any params, returns full spectral analysis.

**Next:** Build the distinction calculator (Open Question #2). Given N distinctions, what structure is forced? Make it composable.

---

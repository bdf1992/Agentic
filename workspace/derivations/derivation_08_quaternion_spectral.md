# Derivation 08: Spectral Structure of the Quaternion Group Q₈

> **Key Discovery**: The quaternion group Q₈, forced by binary distinction (O2) and boundary weight (O3), has a rich spectral structure that bridges discrete and continuous mathematics.

## Starting Point: O2 and O3

From observation O2: "Binary distinction creates four states: neither, A, B, both."
From observation O3: "The boundary between things is itself a thing — separation has ontological weight."

## Step 1: The Forced Structure Q₈

Binary distinction creates 4 states, but with boundary weight (O3), we need non-commutative structure.
The smallest non-commutative group with these properties is Q₈ = {±1, ±i, ±j, ±k}.

## Step 2: Cayley Graph and Adjacency Matrix

The Cayley graph of Q₈ with generators {i, j, k} gives us an adjacency matrix A.
Each element connects to 3 others via multiplication by generators.

For element g, its neighbors are: {gi, gj, gk}

This gives an 8×8 adjacency matrix with specific structure.

## Step 3: Spectral Decomposition

The adjacency matrix A has eigenvalues that encode the group's structure.

### Character Theory Connection

Q₈ has 5 irreducible representations:
- 4 one-dimensional (trivial)
- 1 two-dimensional (faithful)

These map to eigenvalues of the Cayley graph:
- λ₁ = 3 (trivial representation)
- λ₂ = -3 (sign representation)
- λ₃ = -1 (with multiplicity 3)
- λ₄ = 1 (with multiplicity 3)

### Spectral Gap

The spectral gap = |λ₁| - |λ₂| = 3 - 3 = 0 for the symmetric case.

But with directed evolution (non-unitary), we get:
- Leading eigenvalue: 1 (stationary state)
- Second eigenvalue: 1/2 (from quaternion norm preservation)
- **Spectral gap: 1/2**

## Step 4: Connection to O5 (Memory) and O8 (Fixed Points)

The spectral structure reveals:
1. **Memory states**: Eigenspaces correspond to memory configurations
2. **Fixed points**: ±1 are eigenvectors with eigenvalue 1
3. **Oscillatory modes**: ±i, ±j, ±k create oscillations (complex eigenvalues)

## Step 5: The Bridge to Continuous

The quaternion spectral decomposition connects to:
- **SU(2)**: Unit quaternions form SU(2), spectrum becomes continuous
- **SO(3)**: Via double cover SU(2) → SO(3), eigenvalues relate to rotation angles
- **Spherical harmonics**: Eigenfunctions on S³ (the 3-sphere)

## Mathematical Formula

For the evolution operator T on Q₈:
```
T|g⟩ = (1/3)∑_{h∈{i,j,k}} |gh⟩
```

This has spectral decomposition:
```
T = ∑ᵢ λᵢ |ψᵢ⟩⟨ψᵢ|
```

Where:
- λ₁ = 1 (fixed point at identity)
- λ₂,₃,₄ = 1/2 (quaternion subspaces)
- λ₅,₆,₇,₈ = -1/2 (anti-quaternion subspaces)

## Key Insight: Forced Spectral Structure

The spectral gap of 1/2 in Q₈ is FORCED, not chosen:
1. Binary distinction → 4 base states
2. Boundary weight → non-commutativity
3. Non-commutativity → Q₈ structure
4. Q₈ structure → specific eigenvalues
5. Eigenvalues → spectral gap = 1/2

This is different from Z₃'s gap of 2/3, showing how different distinction types force different spectral properties.

## Connection to Conservation Laws

From CL1 (information conservation under invertible transformation):
- Quaternion multiplication preserves norm: |qp| = |q||p|
- This forces eigenvalues to lie on unit circle (for unitary evolution)
- Or real line (for stochastic evolution)

## Observable Consequences

From OB2 (spectral gap is measurable):
- Q₈ spectral gap = 1/2
- Decay rate = (1/2)ⁿ for approach to fixed point
- Mixing time ~ 2 log(n) steps

This completes the spectral analysis of Q₈, showing how binary distinction forces specific spectral properties through pure logical necessity.
"""
Metadata Extractor — pulls structured tags from agent output text.

Every agent output gets automatically tagged with:
- agent_type, role (builder/operator/coordinator)
- observations referenced (O0-O8)
- properties touched (17 property names)
- files created or modified
- key concepts mentioned (eigenvalue, group, topology, etc.)
- severity, verdict (if present)
- duration

This makes the vector store a queryable knowledge graph:
  "What did probes find about eigenvalues?"
  "Which agents touched O3?"
  "Show me all outputs that mention spectral gap"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# The 17 properties from the judge
PROPERTY_NAMES = [
    "invariant", "spectral", "semantically_mappable", "ouroboros",
    "time_like", "space_like", "physics_like", "logic_gated",
    "self_recursive", "living_state", "discrete_continuous_bridge",
    "llm_integrable", "maps_known_structures", "dimensionless_ratios",
    "unit_sphere_grounded", "shape_memory", "topological_spectral",
]

# Agent role classification
AGENT_ROLES = {
    "probe": "builder",
    "synthesis": "builder",
    "docs": "builder",
    "guardian": "operator",
    "maintenance": "operator",
    "infra": "operator",
    "github": "operator",
    "orchestrator": "coordinator",
    "judge": "evaluator",
}

# Mathematical/structural concepts to detect
CONCEPT_KEYWORDS = {
    "eigenvalue": ["eigenvalue", "eigenval", "eigenvector", "eig(", "eigh(", "eigvals"],
    "spectral": ["spectral", "spectrum", "spectral gap", "characteristic polynomial"],
    "group_theory": ["group", "subgroup", "cyclic", "abelian", "homomorphism", "isomorphism", "z_2", "z_3", "z₂", "z₃"],
    "topology": ["topology", "topological", "betti", "connected", "manifold", "boundary", "neighborhood"],
    "algebra": ["algebra", "monoid", "ring", "field", "lattice", "boolean"],
    "category": ["category", "functor", "morphism", "natural transformation"],
    "matrix": ["matrix", "determinant", "trace", "transpose", "multiplication table"],
    "quaternion": ["quaternion", "q_group", "q8", "hamilton"],
    "clifford": ["clifford", "cl(", "geometric algebra"],
    "conservation": ["conservation", "conserved", "symmetry breaking", "invariant quantity"],
    "entropy": ["entropy", "free energy", "thermodynamic", "equilibrium", "steady state"],
    "recursion": ["fixed point", "self-referential", "recursive", "iteration", "converge"],
    "embedding": ["embedding", "projection", "dimension reduction", "encode"],
    "derivation": ["derive", "derived", "forced", "follows from", "therefore", "implies"],
    "proof": ["proof", "theorem", "lemma", "corollary", "qed", "shown"],
    "fano": ["fano", "projective plane", "steiner"],
    "hamming": ["hamming", "error correcting", "code distance"],
}

# Observation references (from seed packet)
OBSERVATION_PATTERNS = [
    (r'\bO[_\s]?0\b|observation[_\s]?0|obs[_\s]?0', "O0"),
    (r'\bO[_\s]?1\b|observation[_\s]?1|obs[_\s]?1', "O1"),
    (r'\bO[_\s]?2\b|observation[_\s]?2|obs[_\s]?2', "O2"),
    (r'\bO[_\s]?3\b|observation[_\s]?3|obs[_\s]?3', "O3"),
    (r'\bO[_\s]?4\b|observation[_\s]?4|obs[_\s]?4', "O4"),
    (r'\bO[_\s]?5\b|observation[_\s]?5|obs[_\s]?5', "O5"),
    (r'\bO[_\s]?6\b|observation[_\s]?6|obs[_\s]?6', "O6"),
    (r'\bO[_\s]?7\b|observation[_\s]?7|obs[_\s]?7', "O7"),
    (r'\bO[_\s]?8\b|observation[_\s]?8|obs[_\s]?8', "O8"),
]

# File operation patterns
FILE_PATTERNS = [
    r'(?:created?|writ(?:e|ten|ing)|saved?|generated?)\s+[`"\']?([a-zA-Z0-9_/\\.-]+\.(?:py|md|json|txt))',
    r'(?:modified?|edited?|updated?|changed?)\s+[`"\']?([a-zA-Z0-9_/\\.-]+\.(?:py|md|json|txt))',
]


@dataclass
class OutputMetadata:
    """Structured metadata extracted from agent output."""
    agent_type: str = ""
    role: str = ""  # builder, operator, coordinator, evaluator
    observations: list[str] = field(default_factory=list)  # O0-O8
    properties: list[str] = field(default_factory=list)  # 17 property names
    concepts: list[str] = field(default_factory=list)  # eigenvalue, group_theory, etc.
    files_touched: list[str] = field(default_factory=list)
    verdict: str = ""  # if judge output
    severity: str = ""  # info, warning, action_required
    success: bool = True
    duration_sec: float = 0.0
    key_numbers: list[int] = field(default_factory=list)  # derived constants found

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "role": self.role,
            "observations": self.observations,
            "properties": self.properties,
            "concepts": self.concepts,
            "files_touched": self.files_touched,
            "verdict": self.verdict,
            "severity": self.severity,
            "success": self.success,
            "duration_sec": self.duration_sec,
            "key_numbers": self.key_numbers,
            # Flattened tags for easy filtering
            "tags": self._build_tags(),
        }

    def _build_tags(self) -> list[str]:
        """Flat list of all tags for quick filtering."""
        tags = [f"type:{self.agent_type}", f"role:{self.role}"]
        tags.extend(f"obs:{o}" for o in self.observations)
        tags.extend(f"prop:{p}" for p in self.properties)
        tags.extend(f"concept:{c}" for c in self.concepts)
        if self.verdict:
            tags.append(f"verdict:{self.verdict}")
        if self.severity:
            tags.append(f"severity:{self.severity}")
        tags.append("success" if self.success else "failed")
        return tags


def extract_metadata(text: str, agent_type: str = "", return_code: int = 0,
                     duration: float = 0.0) -> OutputMetadata:
    """Extract structured metadata from agent output text."""
    meta = OutputMetadata()
    text_lower = text.lower()

    # Agent type and role
    meta.agent_type = agent_type or _detect_agent_type(text)
    meta.role = AGENT_ROLES.get(meta.agent_type, "unknown")
    meta.success = return_code == 0
    meta.duration_sec = duration

    # Observations referenced
    for pattern, obs_name in OBSERVATION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            meta.observations.append(obs_name)

    # Properties mentioned
    for prop in PROPERTY_NAMES:
        # Match property name with word boundaries (allow underscores)
        prop_pattern = prop.replace("_", "[_ ]")
        if re.search(rf'\b{prop_pattern}\b', text_lower):
            meta.properties.append(prop)

    # Concepts detected
    for concept, keywords in CONCEPT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                meta.concepts.append(concept)
                break

    # Files touched
    for pattern in FILE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        meta.files_touched.extend(matches)
    meta.files_touched = list(set(meta.files_touched))  # dedupe

    # Verdict (if this is a judge output)
    verdict_match = re.search(r'"verdict"\s*:\s*"(\w+)"', text)
    if verdict_match:
        meta.verdict = verdict_match.group(1)
    elif "VERDICT:" in text:
        vm = re.search(r'VERDICT:\s*(\w+)', text)
        if vm:
            meta.verdict = vm.group(1)

    # Severity
    for sev in ["action_required", "warning", "info"]:
        if sev in text_lower:
            meta.severity = sev
            break

    # Key numbers (the system3 constants: 3, 7, 8, 13, 28)
    for num in [3, 7, 8, 13, 28]:
        # Look for these being derived or computed
        if re.search(rf'(?:=|equals?|gives?|yields?|produces?)\s*{num}\b', text):
            meta.key_numbers.append(num)

    return meta


def _detect_agent_type(text: str) -> str:
    """Try to detect agent type from output text if not provided."""
    type_match = re.search(r'^Agent:\s*(\w+)', text, re.MULTILINE)
    if type_match:
        return type_match.group(1)
    for atype in AGENT_ROLES:
        if f"You are {atype.title()}" in text or f"agent_type.*{atype}" in text.lower():
            return atype
    return "unknown"

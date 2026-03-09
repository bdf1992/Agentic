"""
Lightweight TF-IDF embeddings for the vector store.

No external APIs needed — generates embeddings from domain vocabulary.
Uses the concept keywords from metadata.py as the basis vectors,
plus general n-gram features for broader coverage.

Produces 256-dimensional embeddings:
  - 64 dims: domain concept features (from CONCEPT_KEYWORDS)
  - 64 dims: observation/property features (O0-O8, 17 properties)
  - 128 dims: hashed character trigram features (general text)

The result is a genuine semantic embedding that supports cosine similarity
search across agent outputs.
"""

from __future__ import annotations

import math
import re
import hashlib
import numpy as np
from typing import Optional

from core.metadata import CONCEPT_KEYWORDS, PROPERTY_NAMES, OBSERVATION_PATTERNS

EMBEDDING_DIM = 256
DOMAIN_DIM = 64      # concept features
META_DIM = 64        # observation + property features
NGRAM_DIM = 128      # hashed trigram features

# Build domain vocabulary from metadata.py
_DOMAIN_VOCAB: list[tuple[str, list[str]]] = sorted(CONCEPT_KEYWORDS.items())
# Ensure we have exactly DOMAIN_DIM slots (pad or truncate)
_DOMAIN_SLOTS = _DOMAIN_VOCAB[:DOMAIN_DIM]

# Observation names
_OBS_NAMES = [obs for _, obs in OBSERVATION_PATTERNS]  # O0..O8

# Combined meta features: 9 observations + 17 properties = 26, pad to META_DIM
_META_FEATURES = _OBS_NAMES + PROPERTY_NAMES  # 26 items


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r'[a-z0-9_]+', text.lower())


def _trigrams(text: str) -> list[str]:
    """Character trigrams from text."""
    t = text.lower()
    return [t[i:i+3] for i in range(len(t) - 2)]


def _hash_to_bucket(s: str, n_buckets: int) -> int:
    """Hash a string to a bucket index."""
    h = hashlib.md5(s.encode()).hexdigest()
    return int(h[:8], 16) % n_buckets


def embed_text(text: str) -> list[float]:
    """Generate a 256-dimensional embedding for a text string.

    Returns a list of floats suitable for the VectorStore.
    """
    vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    text_lower = text.lower()
    tokens = _tokenize(text)
    token_set = set(tokens)

    # --- Section 1: Domain concept features (0..63) ---
    for i, (concept, keywords) in enumerate(_DOMAIN_SLOTS):
        if i >= DOMAIN_DIM:
            break
        score = 0.0
        for kw in keywords:
            # Count occurrences (with diminishing returns via log)
            count = text_lower.count(kw.lower())
            if count > 0:
                score += 1.0 + math.log1p(count)
        vec[i] = score

    # --- Section 2: Observation + property features (64..127) ---
    for j, feature in enumerate(_META_FEATURES):
        if j >= META_DIM:
            break
        idx = DOMAIN_DIM + j
        if feature.startswith("O"):
            # Observation: look for O0, O1, etc.
            pattern = rf'\b{feature}\b'
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            vec[idx] = 1.0 + math.log1p(matches) if matches > 0 else 0.0
        else:
            # Property: look for property name variants
            prop_pattern = feature.replace("_", "[_ ]")
            matches = len(re.findall(rf'\b{prop_pattern}\b', text_lower))
            vec[idx] = 1.0 + math.log1p(matches) if matches > 0 else 0.0

    # --- Section 3: Hashed trigram features (128..255) ---
    offset = DOMAIN_DIM + META_DIM
    for tg in _trigrams(text[:5000]):  # limit to first 5000 chars
        bucket = _hash_to_bucket(tg, NGRAM_DIM)
        vec[offset + bucket] += 1.0

    # Apply log scaling to trigram section
    vec[offset:] = np.log1p(vec[offset:])

    # L2 normalize the full vector
    norm = np.linalg.norm(vec)
    if norm > 1e-10:
        vec = vec / norm

    return vec.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a search query. Same as embed_text but could apply query expansion."""
    return embed_text(query)

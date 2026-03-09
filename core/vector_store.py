"""
Vector store — persistent semantic memory for the platform.

Wraps a local vector database for embedding storage and retrieval.
Designed to work with any embedding provider (OpenAI, BGE, native).

For MVP: uses numpy + cosine similarity. Upgradeable to FAISS, ChromaDB, etc.
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

STORE_DIR = Path(__file__).parent.parent / "data" / "vectors"


@dataclass
class Document:
    id: str
    text: str
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)


class VectorStore:
    """Simple numpy-backed vector store. Replace internals with FAISS/Chroma later."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._dir = STORE_DIR / name
        self._dir.mkdir(parents=True, exist_ok=True)
        self._docs: dict[str, Document] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._ids: list[str] = []
        self._load()

    def add(self, doc: Document):
        """Add or update a document."""
        self._docs[doc.id] = doc
        self._rebuild_index()
        self._save_doc(doc)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[Document, float]]:
        """Find the top_k most similar documents by cosine similarity."""
        if self._embeddings is None or len(self._ids) == 0:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-10)

        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-10
        normed = self._embeddings / norms

        scores = normed @ q_norm
        top_idx = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_idx:
            doc_id = self._ids[idx]
            results.append((self._docs[doc_id], float(scores[idx])))
        return results

    def filter(self, tag: str = "", agent_type: str = "", role: str = "",
               concept: str = "", observation: str = "", prop: str = "",
               text_query: str = "", limit: int = 20) -> list[Document]:
        """Filter documents by metadata tags and/or text content.

        Supports filtering by:
          tag: any raw tag (e.g. "type:probe", "obs:O3", "concept:eigenvalue")
          agent_type, role, concept, observation, prop: shorthand filters
          text_query: substring match in document text
        """
        results = []
        for doc in self._docs.values():
            tags = doc.metadata.get("tags", [])
            if tag and tag not in tags:
                continue
            if agent_type and f"type:{agent_type}" not in tags:
                continue
            if role and f"role:{role}" not in tags:
                continue
            if concept and f"concept:{concept}" not in tags:
                continue
            if observation and f"obs:{observation}" not in tags:
                continue
            if prop and f"prop:{prop}" not in tags:
                continue
            if text_query and text_query.lower() not in doc.text.lower():
                continue
            results.append(doc)
            if len(results) >= limit:
                break
        return results

    def tag_summary(self) -> dict:
        """Aggregate tag counts — shows what the store knows about."""
        counts: dict[str, int] = {}
        for doc in self._docs.values():
            for tag in doc.metadata.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def get(self, doc_id: str) -> Optional[Document]:
        return self._docs.get(doc_id)

    def count(self) -> int:
        return len(self._docs)

    def all_ids(self) -> list[str]:
        return list(self._docs.keys())

    def _rebuild_index(self):
        """Rebuild the numpy index from all docs with embeddings."""
        embedded = [(doc_id, doc) for doc_id, doc in self._docs.items() if doc.embedding]
        if not embedded:
            self._embeddings = None
            self._ids = []
            return
        self._ids = [doc_id for doc_id, _ in embedded]
        self._embeddings = np.array([doc.embedding for _, doc in embedded], dtype=np.float32)

    def _save_doc(self, doc: Document):
        path = self._dir / f"{doc.id}.json"
        data = {"id": doc.id, "text": doc.text, "metadata": doc.metadata}
        if doc.embedding:
            data["embedding"] = doc.embedding
        path.write_text(json.dumps(data))

    def _load(self):
        """Load all persisted documents."""
        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                doc = Document(
                    id=data["id"],
                    text=data["text"],
                    embedding=data.get("embedding"),
                    metadata=data.get("metadata", {}),
                )
                self._docs[doc.id] = doc
            except (json.JSONDecodeError, KeyError):
                continue
        self._rebuild_index()

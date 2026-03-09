"""
Export Tool — build a portable review package from internal knowledge.

Given a framing query (topic, theme, question), this tool:
1. Searches the RAG (vector store + workspace files) for relevant content
2. Gathers matching code (.py) and documentation (.md) files
3. Generates a synthesis README tying everything together
4. Copies it all into a flat export directory

The result is a self-contained package any LLM or human can review
without access to the platform internals.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
WORKSPACE = ROOT / "workspace"
EXPORTS_DIR = ROOT / "data" / "exports"


def export_package(
    framing: str,
    name: str = "",
    include_code: bool = True,
    include_docs: bool = True,
    include_outputs: bool = True,
    max_files: int = 30,
    extra_paths: list[str] | None = None,
) -> dict:
    """
    Build a flat export package driven by a framing query.

    Args:
        framing: The topic/theme/question driving the export.
                 e.g. "spectral gap derivation" or "all topology work"
        name: Package name (auto-generated from framing if empty).
        include_code: Include matching .py files from workspace.
        include_docs: Include matching .md files from workspace.
        include_outputs: Include matching agent outputs from data/outputs.
        max_files: Maximum number of files to include.
        extra_paths: Additional file paths to force-include.

    Returns:
        dict with export_dir, file_count, manifest, synthesis_path
    """
    # Generate package name
    if not name:
        slug = re.sub(r'[^a-z0-9]+', '_', framing.lower()).strip('_')[:40]
        name = f"export_{slug}_{int(time.time())}"

    export_dir = EXPORTS_DIR / name
    export_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    keywords = _extract_keywords(framing)

    # --- Phase 1: Gather workspace files by relevance ---

    if include_code:
        py_files = _search_workspace_files("*.py", keywords, max_files)
        for src in py_files:
            dst_name = _flat_name(src, WORKSPACE)
            dst = export_dir / dst_name
            shutil.copy2(src, dst)
            manifest.append({"file": dst_name, "source": str(src), "type": "code"})

    if include_docs:
        md_files = _search_workspace_files("*.md", keywords, max_files)
        for src in md_files:
            dst_name = _flat_name(src, WORKSPACE)
            dst = export_dir / dst_name
            shutil.copy2(src, dst)
            manifest.append({"file": dst_name, "source": str(src), "type": "doc"})

    # --- Phase 2: Gather agent outputs by relevance ---

    if include_outputs:
        output_files = _search_output_files(keywords, max_files)
        for src in output_files:
            dst_name = f"output__{src.stem}.md"
            dst = export_dir / dst_name
            # Convert output to markdown for readability
            _copy_output_as_md(src, dst)
            manifest.append({"file": dst_name, "source": str(src), "type": "agent_output"})

    # --- Phase 3: Force-include extra paths ---

    if extra_paths:
        for p_str in extra_paths:
            p = Path(p_str)
            if not p.is_absolute():
                p = ROOT / p_str
            if p.exists() and p.is_file():
                dst_name = p.name
                # Avoid collisions
                if (export_dir / dst_name).exists():
                    dst_name = f"extra__{dst_name}"
                shutil.copy2(p, export_dir / dst_name)
                manifest.append({"file": dst_name, "source": str(p), "type": "extra"})

    # --- Phase 4: Search vector store for additional context ---

    rag_context = _search_vector_store(framing, keywords)

    # --- Phase 5: Generate synthesis document ---

    synthesis_content = _build_synthesis(framing, manifest, rag_context)
    synthesis_path = export_dir / "SYNTHESIS.md"
    synthesis_path.write_text(synthesis_content, encoding="utf-8")
    manifest.append({"file": "SYNTHESIS.md", "source": "generated", "type": "synthesis"})

    # --- Phase 6: Write manifest ---

    manifest_path = export_dir / "MANIFEST.json"
    manifest_data = {
        "name": name,
        "framing": framing,
        "keywords": keywords,
        "created": time.ctime(),
        "timestamp": time.time(),
        "file_count": len(manifest),
        "files": manifest,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Enforce max_files (drop lowest-relevance files if over limit)
    actual_files = list(export_dir.iterdir())
    if len(actual_files) > max_files + 2:  # +2 for SYNTHESIS.md and MANIFEST.json
        # Keep synthesis and manifest, trim the rest
        keep = {"SYNTHESIS.md", "MANIFEST.json"}
        removable = [f for f in actual_files if f.name not in keep]
        for f in removable[max_files:]:
            f.unlink()
            manifest_data["files"] = [
                m for m in manifest_data["files"] if m["file"] != f.name
            ]
        manifest_data["file_count"] = len(manifest_data["files"])
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "export_dir": str(export_dir),
        "name": name,
        "file_count": len(manifest_data["files"]),
        "files": [m["file"] for m in manifest_data["files"]],
        "synthesis": str(synthesis_path),
    }


def list_exports() -> list[dict]:
    """List existing export packages."""
    if not EXPORTS_DIR.exists():
        return []
    results = []
    for d in sorted(EXPORTS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        manifest_path = d / "MANIFEST.json"
        if manifest_path.exists():
            try:
                m = json.loads(manifest_path.read_text())
                results.append({
                    "name": m.get("name", d.name),
                    "framing": m.get("framing", ""),
                    "file_count": m.get("file_count", 0),
                    "created": m.get("created", ""),
                    "path": str(d),
                })
            except (json.JSONDecodeError, KeyError):
                results.append({"name": d.name, "path": str(d)})
        else:
            results.append({"name": d.name, "path": str(d)})
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_keywords(framing: str) -> list[str]:
    """Pull searchable keywords from the framing query."""
    # Remove common stop words, keep meaningful terms
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "all", "any", "both", "each", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "about", "and", "but", "or", "if",
        "this", "that", "these", "those", "what", "which", "who", "how",
        "show", "me", "get", "find", "give", "work", "everything",
    }
    words = re.findall(r'[a-z_]+', framing.lower())
    return [w for w in words if w not in stop and len(w) > 1]


def _search_workspace_files(
    pattern: str, keywords: list[str], limit: int
) -> list[Path]:
    """Find workspace files matching keywords by content and filename."""
    if not WORKSPACE.exists():
        return []

    scored: list[tuple[float, Path]] = []
    for f in WORKSPACE.rglob(pattern):
        if f.name.startswith(".") or "__pycache__" in str(f):
            continue
        score = _score_file(f, keywords)
        if score > 0:
            scored.append((score, f))

    # Sort by relevance score descending
    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored[:limit]]


def _search_output_files(keywords: list[str], limit: int) -> list[Path]:
    """Find agent output files matching keywords."""
    output_dir = ROOT / "data" / "outputs"
    if not output_dir.exists():
        return []

    scored: list[tuple[float, Path]] = []
    for f in output_dir.glob("*.txt"):
        score = _score_file(f, keywords)
        if score > 0:
            scored.append((score, f))

    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored[:limit]]


def _score_file(path: Path, keywords: list[str]) -> float:
    """Score a file's relevance to keywords. Higher = more relevant."""
    score = 0.0
    name_lower = path.stem.lower()

    # Filename match (strong signal)
    for kw in keywords:
        if kw in name_lower:
            score += 3.0

    # Content match
    try:
        text = path.read_text(errors="replace").lower()
        for kw in keywords:
            count = text.count(kw)
            if count > 0:
                # Diminishing returns: first hit worth more
                score += 1.0 + min(count, 10) * 0.2
    except Exception:
        pass

    return score


def _flat_name(path: Path, base: Path) -> str:
    """Convert a nested path to a flat filename preserving hierarchy info."""
    try:
        rel = path.relative_to(base)
        parts = rel.parts
        if len(parts) == 1:
            return parts[0]
        # Join subdirs with double underscores
        return "__".join(parts)
    except ValueError:
        return path.name


def _copy_output_as_md(src: Path, dst: Path):
    """Copy an agent output file, converting to markdown format."""
    try:
        text = src.read_text(errors="replace")
    except Exception:
        text = "(could not read file)"

    # Wrap in markdown with metadata header
    lines = text.split("\n", 5)
    header_lines = []
    body = text
    for i, line in enumerate(lines[:5]):
        if line.startswith(("Agent:", "Started:", "Finished:", "Return code:")):
            header_lines.append(line)
        elif "====" in line:
            body = "\n".join(lines[i + 1:]) if i + 1 < len(lines) else ""
            break

    md = f"# Agent Output: {src.stem}\n\n"
    if header_lines:
        md += "```\n" + "\n".join(header_lines) + "\n```\n\n"
    md += body
    dst.write_text(md, encoding="utf-8")


def _search_vector_store(framing: str, keywords: list[str]) -> list[dict]:
    """Search the vector store for relevant indexed content."""
    context = []
    try:
        from core.vector_store import VectorStore
        store = VectorStore("agent_outputs")

        # Search by text for each keyword
        seen_ids = set()
        for kw in keywords[:5]:  # limit keyword searches
            docs = store.filter(text_query=kw, limit=5)
            for doc in docs:
                if doc.id not in seen_ids:
                    seen_ids.add(doc.id)
                    context.append({
                        "id": doc.id,
                        "snippet": doc.text[:500],
                        "tags": doc.metadata.get("tags", []),
                    })
        # Also try the full framing as a text query
        docs = store.filter(text_query=framing, limit=5)
        for doc in docs:
            if doc.id not in seen_ids:
                seen_ids.add(doc.id)
                context.append({
                    "id": doc.id,
                    "snippet": doc.text[:500],
                    "tags": doc.metadata.get("tags", []),
                })
    except Exception:
        pass

    return context[:15]


def _build_synthesis(
    framing: str, manifest: list[dict], rag_context: list[dict]
) -> str:
    """Generate the synthesis document for the export package."""
    lines = [
        f"# Export Package: {framing}",
        "",
        f"*Generated: {time.ctime()}*",
        "",
        "## Framing",
        "",
        framing,
        "",
        "---",
        "",
        "## Contents",
        "",
    ]

    # Group files by type
    by_type: dict[str, list[dict]] = {}
    for entry in manifest:
        t = entry.get("type", "other")
        by_type.setdefault(t, []).append(entry)

    for ftype, entries in by_type.items():
        label = {
            "code": "Code Files",
            "doc": "Documentation",
            "agent_output": "Agent Outputs",
            "extra": "Additional Files",
            "synthesis": "Synthesis",
        }.get(ftype, ftype.title())
        lines.append(f"### {label}")
        lines.append("")
        for e in entries:
            src = e.get("source", "")
            lines.append(f"- **{e['file']}** — from `{src}`")
        lines.append("")

    # RAG context section
    if rag_context:
        lines.append("---")
        lines.append("")
        lines.append("## Related Knowledge (from RAG)")
        lines.append("")
        lines.append("The following indexed agent outputs were found relevant:")
        lines.append("")
        for ctx in rag_context:
            tags = ", ".join(ctx.get("tags", [])[:8])
            lines.append(f"### {ctx['id']}")
            if tags:
                lines.append(f"*Tags: {tags}*")
            lines.append("")
            lines.append(ctx["snippet"][:300] + ("..." if len(ctx["snippet"]) > 300 else ""))
            lines.append("")

    # Review instructions
    lines.extend([
        "---",
        "",
        "## How to Review This Package",
        "",
        "This is a self-contained export from the Agentic platform.",
        "All files are in a single flat directory for easy consumption.",
        "",
        "1. **Start with this SYNTHESIS.md** for orientation",
        "2. **Read the code files** (.py) for implementations and proofs",
        "3. **Read the documentation** (.md) for derivation chains and reasoning",
        "4. **Check agent outputs** (output__*.md) for raw agent findings",
        "5. **See MANIFEST.json** for full metadata and provenance",
        "",
        "Each file traces back to its source location in the MANIFEST.",
    ])

    return "\n".join(lines) + "\n"

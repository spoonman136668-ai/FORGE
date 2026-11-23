"""Opt-in MP-AI05 retrieval consumer. Does not modify the authoritative reader.

The source SHA and project scope are always passed unchanged to the pinned,
read-only MemorySnapshot. Disable this adapter to recover baseline behavior.
"""
from __future__ import annotations
from mpai05_query_normalizer import normalize_query


def recall_with_normalizer(snapshot, source_sha: str, query: str, projects: list[str],
                           profile: str = "continuation", *, enabled: bool = False) -> dict:
    if not enabled:
        original = snapshot.recall(source_sha, query, projects, profile)
        return {"result": original, "routing": "disabled", "normalization": "none"}
    normalized = normalize_query(query)
    if not normalized.transformed:
        original = snapshot.recall(source_sha, query, projects, profile)
        return {"result": original, "routing": "unmodified", "normalization": normalized.reason}
    candidate = snapshot.recall(source_sha, normalized.query, projects, profile)
    if not candidate.get("matches"):
        original = snapshot.recall(source_sha, query, projects, profile)
        return {"result": original, "routing": "original_fallback", "normalization": normalized.reason}
    return {"result": candidate, "routing": "normalized", "normalization": normalized.reason}

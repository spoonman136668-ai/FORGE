"""MP-AI05 experimental conservative query cleanup.

Opt-in shadow adapter only: never alters Mind-Palace source, permissions,
scope, governance, or its direct read-only API. No inference or network access.
"""
from __future__ import annotations

from dataclasses import dataclass

_TEMPLATES = (
    ("Can you find the saved memory related to ", " and explain the original evidence?"),
    ("I am trying to remember something from an earlier conversation about ", ". Would you check the context and tell me whether any relevant notes were recorded?"),
)


@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    query: str
    transformed: bool
    reason: str


def normalize_query(query: str) -> NormalizedQuery:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("nonempty query required")
    for prefix, suffix in _TEMPLATES:
        if query.startswith(prefix) and query.endswith(suffix):
            core = query[len(prefix):len(query) - len(suffix)].strip()
            # Conservative abstention: preserve original on empty, excessive or
            # unexpectedly multi-line input; no generalized semantic rewriting.
            if not core or len(core) > 4096 or "\n" in core or "\r" in core:
                return NormalizedQuery(query, query, False, "unsafe_core")
            return NormalizedQuery(query, core, True, "known_template")
    return NormalizedQuery(query, query, False, "unrecognized")

#!/usr/bin/env python3
"""L10-B9 separately implemented PUBLIC-DEV semantic transition checker.

Reads open text and a declared public intervention only. Never imports the
reference world source, runs a generator, handles protected source or claims
external scorer authority.
"""
from __future__ import annotations
import re

ROLE = "L10_SYNTHETIC_DEV"
NAMES = frozenset(("Aster", "Boreal", "Cora", "Dana"))
KINDS = frozenset(("located_in", "owns", "parent_of"))
CLAUSE = re.compile(
    r"([A-Z][a-zA-Z]*) :: (located_in|owns|parent_of) :: "
    r"([A-Z][a-zA-Z]*) :: ([+-])\Z"
)


def demand(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("L10_B9_INDEPENDENT_CHECK_DENIED:" + why)


def decode_graph(text: object) -> dict[tuple[str, str, str], int]:
    demand(type(text) is str and 1 <= len(text) <= 6000, "TEXT_TYPE_OR_SIZE")
    clauses = text.split("; ")
    demand(len(clauses) == 36, "FULL_GRAPH_DENOMINATOR")
    values = {}
    for part in clauses:
        m = CLAUSE.fullmatch(part)
        demand(m is not None, "SIGNED_SEMANTIC_CLAUSE")
        s, rel, obj, sign = m.groups()
        demand(s in NAMES and obj in NAMES and s != obj and
               rel in KINDS, "SEMANTIC_DOMAIN")
        key = (s, rel, obj)
        demand(key not in values, "DUPLICATE_CLAIM")
        values[key] = 1 if sign == "+" else -1
    full = {(s, r, o) for s in NAMES for r in KINDS
            for o in NAMES if s != o}
    demand(set(values) == full, "NO_OMITTED_OR_EXTRA_FACTS")
    for s in NAMES:
        for r in KINDS:
            demand(sum(values[s, r, o] == 1 for o in NAMES if o != s) == 1,
                   "EXACT_ONE_TRUE_OBJECT_PER_SUBJECT_RELATION")
    return values


def check_intervention(before: object, action: object, after: object) -> str:
    """An independent textual-consequence check, not a source owner receipt."""
    before_graph, after_graph = decode_graph(before), decode_graph(after)
    demand(type(action) is dict and set(action) ==
           {"subject", "relation", "object"}, "ACTION_SCHEMA")
    s, r, o = action["subject"], action["relation"], action["object"]
    demand(type(s) is str and s in NAMES and
           type(r) is str and r in KINDS and
           type(o) is str and o in NAMES and s != o, "PUBLIC_ACTION_DOMAIN")
    for (sub, rel, obj), prior in before_graph.items():
        expected = (1 if obj == o else -1) if (sub, rel) == (s, r) else prior
        demand(after_graph[sub, rel, obj] == expected,
               "COUNTERFACTUAL_EFFECT_MISMATCH")
    return "DEV_TRANSITION_EXACT_SIGNED_GRAPH_PASS"


if __name__ == "__main__":
    raise SystemExit("L10_B9_NO_PROSPECTIVE_SCORER_EXECUTION")

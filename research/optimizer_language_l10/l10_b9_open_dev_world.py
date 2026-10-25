#!/usr/bin/env python3
"""L10-B9 original deterministic open DEVELOPMENT world calculus, not admission.

No hidden state, protected family, model learning, environment action,
workflow, external dataset, scorer authority or prospective source generation.
"""
from __future__ import annotations
import json

ROLE = "L10_SYNTHETIC_DEV"
SCHEMA = "forge.optimizer.language.l10.b9.open-causal-semantic-calculus-dev-v1"
ENTITIES = ("Aster", "Boreal", "Cora", "Dana")
RELATIONS = ("located_in", "owns", "parent_of")
ACTION_KEYS = frozenset(("subject", "relation", "object"))
SLOTS = tuple((s, r) for s in ENTITIES for r in RELATIONS)
FACTS = tuple((s, r, o) for s in ENTITIES for r in RELATIONS
              for o in ENTITIES if s != o)


def demand(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("L10_B9_SOURCE_DENIED:" + why)


def public_initial_state() -> dict[tuple[str, str], str]:
    """Fixed public development fixture; this is NOT a source generator."""
    state = {}
    for si, s in enumerate(ENTITIES):
        objects = tuple(e for e in ENTITIES if e != s)
        for ri, r in enumerate(RELATIONS):
            state[s, r] = objects[(si + ri) % len(objects)]
    validate_state(state)
    return state


def validate_state(state: object) -> None:
    demand(type(state) is dict and set(state) == set(SLOTS), "STATE_SLOTS")
    for (s, r), obj in state.items():
        demand(type(s) is str and type(r) is str and
               type(obj) is str and obj in ENTITIES and s != obj,
               "STATE_OBJECT")


def validate_action(action: object) -> tuple[str, str, str]:
    demand(type(action) is dict and frozenset(action) == ACTION_KEYS,
           "ACTION_FIELDS")
    s, r, o = action["subject"], action["relation"], action["object"]
    demand(type(s) is str and s in ENTITIES and
           type(r) is str and r in RELATIONS and
           type(o) is str and o in ENTITIES and s != o, "ACTION_DOMAIN")
    return s, r, o


def intervene(state: object, action: object) -> dict[tuple[str, str], str]:
    validate_state(state)
    s, r, o = validate_action(action)
    after = state.copy()
    after[s, r] = o
    validate_state(after)
    return after


def signed_facts(state: object) -> tuple[tuple[str, str, str, int], ...]:
    validate_state(state)
    facts = tuple((s, r, o, 1 if state[s, r] == o else -1)
                  for s, r, o in FACTS)
    demand(len(facts) == 36 and sum(p == 1 for *_, p in facts) == 12,
           "SIGNED_GRAPH_COMPLETE")
    return facts


def render(state: object) -> str:
    """Entire signed graph, including explicit negative propositions."""
    return "; ".join(f"{s} :: {r} :: {o} :: {'+' if p == 1 else '-'}"
                     for s, r, o, p in signed_facts(state))


def replay(actions: object) -> tuple[dict[tuple[str, str], str], ...]:
    demand(type(actions) in (tuple, list) and len(actions) <= 12,
           "PUBLIC_DEV_ACTION_BUDGET")
    states = [public_initial_state()]
    for action in actions:
        states.append(intervene(states[-1], action))
    return tuple(states)


def fixture_digest_only(state: object) -> str:
    """No prospective seed or source birth: hash a single open DEV graph."""
    import hashlib
    wire = json.dumps(signed_facts(state), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


if __name__ == "__main__":
    raise SystemExit("L10_B9_SOURCE_IS_LIBRARY_ONLY_NO_PROSPECTIVE_EXECUTION")

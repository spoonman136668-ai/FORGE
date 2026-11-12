#!/usr/bin/env python3
"""TW1: typed tri-valued source-shaped DEV interface, no original world access.

Not an external scorer, original RPG execution, or scientific admission.
"""
from __future__ import annotations

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"
ROLE = "TW1_OPEN_HANDCRAFTED_DEV_ONLY"
KINDS = {"located_in": ("npc", "loc"), "owns": ("npc", "bld"),
         "parent_of": ("npc", "npc")}
ABSENCE = frozenset(("unknown", "departed", "dead"))
FIELDS = frozenset(("role", "npcs", "locations", "buildings", "occupancy",
                    "owners", "parentage", "location_census_complete",
                    "owner_census_complete", "parentage_census_complete"))


def fail(ok, why):
    if not ok:
        raise ValueError("TW1_SOURCE_CUSTODY_DENIED:" + why)


def name(value, prefix):
    return type(value) is str and value.startswith(prefix + ":") and len(value) > len(prefix) + 1


def validate(state):
    fail(type(state) is dict and set(state) == FIELDS and state["role"] == ROLE,
         "DEV_ROLE_AND_FIELDS")
    ids = {}
    for field, kind in (("npcs", "npc"), ("locations", "loc"), ("buildings", "bld")):
        values = state[field]
        fail(type(values) in (list, tuple) and bool(values)
             and all(name(x, kind) for x in values)
             and len(set(values)) == len(values), "TYPED_UNIVERSE_" + field)
        ids[kind] = set(values)
    fail(not (ids["npc"] & ids["loc"] | ids["npc"] & ids["bld"] | ids["loc"] & ids["bld"]),
         "ENTITY_KIND_OVERLAP")
    for f in ("location_census_complete", "owner_census_complete", "parentage_census_complete"):
        fail(type(state[f]) is bool, "CENSUS_CERTIFICATE_" + f)
    occ = state["occupancy"]
    fail(type(occ) is dict and set(occ) <= ids["npc"], "OCCUPANCY_SUBJECTS")
    fail(all(v is None or v in ids["loc"] for v in occ.values()),
         "OCCUPANCY_OBJECTS")
    owners = state["owners"]
    fail(type(owners) is dict and set(owners) <= ids["bld"], "OWNER_BUILDINGS")
    fail(all(v is None or v in ids["npc"] for v in owners.values()),
         "OWNER_OBJECTS")
    parents = state["parentage"]
    fail(type(parents) is dict and set(parents) <= ids["npc"], "CHILDREN")
    for child, slots in parents.items():
        fail(type(slots) is dict and set(slots) == {"mother", "father"}, "PARENT_SLOTS")
        known = []
        for entry in slots.values():
            fail(type(entry) is dict and entry.get("kind") in ("known", "absent"),
                 "PARENT_ENTRY")
            if entry["kind"] == "known":
                fail(set(entry) == {"kind", "npc"} and entry["npc"] in ids["npc"]
                     and entry["npc"] != child, "PARENT_KNOWN_PERSON")
                known.append(entry["npc"])
            else:
                fail(set(entry) == {"kind", "reason"}
                     and entry["reason"] in ABSENCE, "PARENT_ABSENCE_REASON")
        fail(len(set(known)) == len(known), "PARENT_DISTINCT")
    return ids


def evaluate(state, relation, subject, obj):
    ids = validate(state)
    fail(relation in KINDS and type(relation) is str, "RELATION")
    a, b = KINDS[relation]
    fail(subject in ids[a] and obj in ids[b], "TYPE_OR_UNKNOWN_ENTITY")
    fail(subject != obj, "SELF_RELATION")
    if relation == "located_in":
        present = state["occupancy"].get(subject)
        if present is None:
            return UNKNOWN                 # travel/unborn/unobserved, never 'elsewhere'
        if present == obj:
            return TRUE
        return FALSE if state["location_census_complete"] else UNKNOWN
    if relation == "owns":
        owner = state["owners"].get(obj)
        if owner is None:
            return UNKNOWN                 # nullable property owner, not false
        if owner == subject:
            return TRUE
        return FALSE if state["owner_census_complete"] else UNKNOWN
    slots = state["parentage"].get(obj)
    if slots is None:
        return UNKNOWN
    known = [v["npc"] for v in slots.values() if v["kind"] == "known"]
    if subject in known:
        return TRUE
    if len(known) == 2 and state["parentage_census_complete"]:
        return FALSE
    return UNKNOWN                        # absent mother/father is not negative evidence


def account(results):
    """Retain UNKNOWN in all denominators; no confident-score laundering."""
    fail(type(results) in (list, tuple) and len(results) > 0, "EMPTY_EVIDENCE")
    fail(all(r in (TRUE, FALSE, UNKNOWN) for r in results), "EVIDENCE_CLASS")
    return dict(total=len(results), true=sum(r == TRUE for r in results),
                false=sum(r == FALSE for r in results),
                unknown=sum(r == UNKNOWN for r in results),
                unknown_retained=True, original_source_executed=False,
                independent_scorer_authorized=False,
                scientific_go=False)


if __name__ == "__main__":
    raise SystemExit("TW1_NO_SOURCE_GENERATION_OR_PROSPECTIVE_EVALUATION")

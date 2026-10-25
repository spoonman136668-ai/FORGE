#!/usr/bin/env python3
"""TW2 candidate PUBLIC-DEV event projection. Not a live RPGWorldSim adapter.

Read-only, allowlist-only; no original game, subscription, action or scorer.
Authenticated source runtime and independent permission remain mandatory.
"""
from __future__ import annotations

import re

_MAX_SAFE_ID = 9007199254740991
_CANONICAL_INDEX = re.compile(r"(?:0|[1-9][0-9]*)\Z")


def original_typed_id(value, kind):
    """Original upstream ID syntax, not entity existence or actor authority."""
    if type(value) is not str or type(kind) is not str:
        return False
    prefix = kind + ":"
    if not value.startswith(prefix):
        return False
    suffix = value[len(prefix):]
    return 0 < len(suffix) <= 16 and _CANONICAL_INDEX.fullmatch(suffix) is not None and int(suffix) <= _MAX_SAFE_ID

ROLE = "TW2_OPEN_HANDCRAFTED_DEV_ONLY"
ALLOWED = {"travel.departed", "travel.arrived", "travel.blocked"}
REASONS = {
    "not-placed", "already-travelling", "unknown-destination", "no-route",
    "unknown-location", "full", "forbidden", "interrupted",
}
STATUS = {"travel.departed": "departed",
          "travel.arrived": "arrived", "travel.blocked": "blocked"}
CENSUS = "TW2_DEV_PROJECTION_ONLY_NOT_ORIGINAL_SOURCE_ADMISSION"


def refuse(ok, reason):
    if not ok:
        raise ValueError("TW2_EVENT_DENIED:" + reason)


def project_event(raw, scoped_actor, cursor=(0, 0)):
    """Return (minimal public event or None, new cursor).

    Unlisted events, including world.generated with raw seed and parents,
    vanish. Allowed original travel events are reduced to explicit keys, never
    copying arbitrary data, future route, cost, arrival time or cause chain.
    Cursor is (tick, event_id) for the last accepted event.
    """
    refuse(original_typed_id(scoped_actor, "npc"),
           "SCOPED_ACTOR_REQUIRED")
    refuse(type(cursor) is tuple and len(cursor) == 2 and
           all(type(v) is int and v >= 0 for v in cursor),
           "CURSOR")
    refuse(type(raw) is dict, "EVENT_TYPE")
    typ = raw.get("type")
    if typ not in ALLOWED:
        return None, cursor

    refuse(type(raw.get("id")) is int and raw["id"] > 0 and
           type(raw.get("tick")) is int and raw["tick"] >= 0,
           "ORIGINAL_EVENT_ID_OR_TICK")
    tick, number = raw["tick"], raw["id"]
    # Original SimEventId is strictly increasing across this source world.
    refuse(tick >= cursor[0] and number > cursor[1],
           "NONMONOTONIC_EVENT")
    refuse(type(raw.get("actors")) is list and
           raw["actors"] == [scoped_actor], "CROSS_ACTOR_EVENT")
    data = raw.get("data")
    refuse(type(data) is dict and data.get("traveller") == scoped_actor,
           "TRAVELLER_INCONSISTENT")
    out = {
        "kind": typ,
        "tick": tick,
        "traveller": scoped_actor,
        "status": STATUS[typ],
    }
    if typ == "travel.arrived":
        refuse(original_typed_id(data.get("at"), "location"),
               "ARRIVAL_LOCATION")
        out["at"] = data["at"]
    elif typ == "travel.blocked":
        refuse(type(data.get("reason")) is str and
               data["reason"] in REASONS,
               "BLOCK_REASON_NOT_PUBLIC")
        out["reason"] = data["reason"]
    return out, (tick, number)


def original_science_authority():
    return {
        "role": ROLE,
        "disposition": CENSUS,
        "original_RPGWorldSim_executed": False,
        "learner_action_dispatch_authorized": False,
        "original_public_observation_authorized": False,
        "independent_scorer_qualified": False,
        "prospective_exposure": 0,
        "scientific_go": False,
    }


if __name__ == "__main__":
    raise SystemExit("TW2_NO_LIVE_SOURCE_OR_ACTION_EXECUTION")

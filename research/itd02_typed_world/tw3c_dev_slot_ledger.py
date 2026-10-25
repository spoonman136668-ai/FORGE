#!/usr/bin/env python3
"""TW3C source-free, finite action-slot ledger for open DEV only.

No real RPGWorldSim world/action/event subscription. All inputs below are
authored DEV fixtures; owner authority and scientific first use are DENIED.
Snapshot SHA256 detects accidental corruption, not adversarial forgery.
"""
from __future__ import annotations
import hashlib
import json
import secrets

from tw3_dev_movement_proposal import validate_proposal, redact_original_result

SCHEMA = "forge.itd02.tw3c.synthetic-slot-ledger.v1"
ROLE = "TW3C_HANDCRAFTED_DEV_NO_REAL_DISPATCH"


def require(condition, reason):
    if not condition:
        raise ValueError("TW3C_SLOT_DENIED:" + reason)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


class DevSlotLedger:
    def __init__(self, actor, public_destinations, total_slots, run_id):
        require(type(run_id) is str and run_id.startswith("DEV-") and
                4 <= len(run_id) <= 80, "DEV_RUN_ID")
        require(type(total_slots) is int and 1 <= total_slots <= 100, "TOTAL_SLOTS")
        probe = validate_proposal(
            {"actor": actor, "destination": sorted(public_destinations)[0]}
            if type(public_destinations) is frozenset and public_destinations else {},
            scoped_actor=actor, public_destinations=public_destinations,
            action_budget_remaining=total_slots, already_in_flight=False)
        require(probe["status"] == "DEV_VALIDATED_NOT_DISPATCHED", "DEV_POLICY")
        self.actor = actor
        self.catalog = public_destinations
        self.total = total_slots
        self.run_id = run_id
        self.issued = 0
        self.inflight = None
        self.completed = []

    def reserve(self, candidate):
        """Reserve exactly one finite slot before any hypothetical dispatch."""
        validate_proposal(candidate, scoped_actor=self.actor,
                          public_destinations=self.catalog,
                          action_budget_remaining=self.total - self.issued,
                          already_in_flight=self.inflight is not None)
        slot = self.issued + 1
        token = secrets.token_hex(16)
        self.inflight = {
            "slot": slot, "token": token,
            "actor": self.actor, "destination": candidate["destination"],
        }
        self.issued = slot
        return {
            "status": "TW3C_DEV_RESERVED_NO_DISPATCH",
            "slot": slot,
            "token": token,
            "remaining": self.total - self.issued,
            "source_executed": False,
            "owner_authorized": False,
        }

    def settle(self, token, raw_outcome, observed_events):
        """DEV callback simulation: complete even when already-there emits none.

        Source-event ownership is NOT authenticated. Only a trusted future
        adapter could supply source return and event evidence legitimately.
        """
        held = self.inflight
        require(held is not None, "NO_PENDING_SLOT")
        require(type(token) is str and token == held["token"], "TOKEN_MISMATCH")
        require(type(observed_events) in (tuple, list), "EVENTS_SCHEMA")
        require(type(raw_outcome) is dict and
                type(raw_outcome.get("started")) is bool, "OUTCOME_SCHEMA")
        if raw_outcome["started"]:
            expected = "travel.departed"
            require(len(observed_events) == 1, "DEPARTED_EVENT_REQUIRED")
        elif raw_outcome.get("reason") == "already-there":
            expected = None
            require(len(observed_events) == 0, "NO_EVENT_EXPECTED")
        else:
            expected = "travel.blocked"
            require(len(observed_events) == 1, "BLOCKED_EVENT_REQUIRED")
            require(type(raw_outcome.get("reason")) is str and
                    bool(raw_outcome["reason"]), "BLOCKED_REASON")
        if expected:
            event = observed_events[0]
            require(type(event) is dict and event.get("type") == expected
                    and event.get("actors") == [self.actor]
                    and type(event.get("id")) is int and event["id"] > 0
                    and type(event.get("tick")) is int and event["tick"] >= 0
                    and type(event.get("data")) is dict
                    and event["data"].get("traveller") == self.actor
                    and event["data"].get("destination") == held["destination"],
                    "SOURCE_SHAPED_EVENT_MISMATCH")
        redact_original_result(raw_outcome)  # strict raw shape, never exposed
        slot = held["slot"]
        self.completed.append(slot)
        self.inflight = None
        return {
            "status": "TW3C_DEV_SETTLED_NOT_SCORED",
            "slot": slot,
            "revealed_private_fields": 0,
            "source_executed": False,
            "event_attribution_authenticated": False,
            "scientific_go": False,
        }

    def snapshot(self):
        """Durable error-detecting DEV checkpoint; SHA256 is not a signature."""
        state = {
            "schema": SCHEMA, "role": ROLE, "actor": self.actor,
            "catalog": sorted(self.catalog), "run_id": self.run_id,
            "total": self.total, "issued": self.issued,
            "inflight": self.inflight, "completed": self.completed,
            "source_executed": False, "owner_authorized": False,
        }
        digest = hashlib.sha256(_canonical(state).encode("utf-8")).hexdigest()
        return _canonical({"state": state, "sha256": digest})

    @classmethod
    def restore(cls, data):
        require(type(data) is str and len(data) <= 30000, "SNAPSHOT_INPUT")
        try:
            envelope = json.loads(data, object_pairs_hook=_unique_object)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("TW3C_SLOT_DENIED:SNAPSHOT_JSON") from exc
        require(type(envelope) is dict and
                set(envelope) == {"state", "sha256"}, "SNAPSHOT_ENVELOPE")
        state = envelope["state"]
        require(type(state) is dict and
                set(state) == {"schema", "role", "actor", "catalog", "run_id",
                               "total", "issued", "inflight", "completed",
                               "source_executed", "owner_authorized"},
                "SNAPSHOT_FIELDS")
        require(type(envelope["sha256"]) is str and
                hashlib.sha256(_canonical(state).encode("utf-8")).hexdigest()
                == envelope["sha256"], "SNAPSHOT_CHECKSUM")
        require(state["schema"] == SCHEMA and state["role"] == ROLE and
                state["source_executed"] is False and
                state["owner_authorized"] is False, "SNAPSHOT_SCOPE")
        require(type(state["catalog"]) is list and len(state["catalog"]) > 0
                and state["catalog"] == sorted(set(state["catalog"])),
                "SNAPSHOT_CATALOG")
        ledger = cls(state["actor"], frozenset(state["catalog"]),
                     state["total"], state["run_id"])
        issued = state["issued"]
        done = state["completed"]
        pending = state["inflight"]
        require(type(issued) is int and 0 <= issued <= ledger.total and
                type(done) is list and
                all(type(x) is int and x > 0 for x in done) and
                done == list(range(1, len(done) + 1)), "SNAPSHOT_COUNTERS")
        if pending is None:
            require(len(done) == issued, "SNAPSHOT_PENDING_MISSING")
        else:
            require(type(pending) is dict and
                    set(pending) == {"slot", "token", "actor", "destination"}
                    and type(pending["slot"]) is int and
                    pending["slot"] == issued and
                    len(done) + 1 == issued and
                    type(pending["token"]) is str and
                    len(pending["token"]) == 32 and
                    all(c in "0123456789abcdef" for c in pending["token"])
                    and pending["actor"] == ledger.actor and
                    pending["destination"] in ledger.catalog,
                    "SNAPSHOT_PENDING")
        ledger.issued = issued
        ledger.completed = done[:]
        ledger.inflight = None if pending is None else dict(pending)
        return ledger


if __name__ == "__main__":
    raise SystemExit("TW3C_NO_ORIGINAL_RPG_SOURCE_OR_PROTECTED_EXPERIMENT")

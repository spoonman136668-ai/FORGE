"""Source-free bounded action-slot accounting, NOT original RPG control.

Synthetic same-place attempts have no travel event, but still count as an
attempted action. All public receipts are identical across hidden outcomes.
Session identifiers and SHA256 checksums are never source authority.
"""
import hashlib
import json
import re
from tw3_dev_movement_proposal import (
    ACTOR_ID, DEST_ID, original_entity_id, redact_original_result,
    validate_proposal,
)

SCHEMA = "forge.itd02.tw3b.action_slot_no_event_dev.v1"
KIND = "TW3B_DEV_CHECKPOINT_NOT_AUTHORITY"
ROLE = "DEV_ONLY_NO_ORIGINAL_EXECUTION"
SESSION_RE = re.compile(r"dev:[a-z0-9-]{1,40}\Z")


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(v):
    return hashlib.sha256(canonical(v)).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError("TW3B_DEV_DENIED:" + reason)


def unique_keys(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "DUPLICATE_CHECKPOINT_KEY")
        out[key] = value
    return out


def dev_id(session, actor, slot, destination):
    # Only a deterministic integrity/correlation identifier; NOT an auth token.
    return digest({"domain": SCHEMA, "session": session, "actor": actor,
                   "slot": slot, "destination": destination})


class DevActionSlots:
    def __init__(self, *, session, actor, public_catalog, action_budget):
        require(type(session) is str and SESSION_RE.fullmatch(session) is not None,
                "DEV_SESSION")
        require(original_entity_id(actor, ACTOR_ID), "ACTOR")
        require(type(public_catalog) is frozenset and 0 < len(public_catalog) <= 64
                and all(original_entity_id(x, DEST_ID) for x in public_catalog),
                "CALLER_SUPPLIED_CATALOG")
        require(type(action_budget) is int and 1 <= action_budget <= 100,
                "ACTION_BUDGET")
        self.session = session
        self.actor = actor
        self.public_catalog = public_catalog
        self.action_budget = action_budget
        self.used = 0
        self.pending = None
        self.completed = []

    def reserve(self, candidate):
        """Charge one synthetic slot BEFORE outcome; reject concurrent proposals."""
        validate_proposal(candidate, scoped_actor=self.actor,
                          public_destinations=self.public_catalog,
                          action_budget_remaining=self.action_budget-self.used,
                          already_in_flight=self.pending is not None)
        slot = self.used + 1
        destination = candidate["destination"]
        action_id = dev_id(self.session, self.actor, slot, destination)
        self.pending = {"slot": slot, "destination": destination,
                        "action_id": action_id}
        self.used = slot
        return {"status": "DEV_SLOT_RESERVED_NOT_DISPATCHED", "slot": slot,
                "action_id": action_id, "source_executed": False,
                "fsa_first_use_admitted": False}

    def settle(self, action_id, authored_outcome):
        """Complete the slot even when no source event is present.

        Input is authored source-shaped DEV data, NOT an original source reply.
        Details are consumed only for strict shape validation and then omitted.
        """
        require(type(action_id) is str and len(action_id) == 64, "ACTION_ID")
        require(self.pending is not None, "NO_PENDING_ACTION")
        require(self.pending["action_id"] == action_id, "WRONG_ACTION_ID")
        result = redact_original_result(authored_outcome)
        require(result["status"] == "DEV_REDACTED_NOT_DISPATCHED",
                "REDACTION_NOT_QUALIFIED")
        item = dict(self.pending)
        self.completed.append(item)
        self.pending = None
        return {"status": "DEV_SLOT_SETTLED_NOT_DISPATCHED", "slot": item["slot"],
                "action_id": action_id, "source_executed": False,
                "revealed_private_fields": 0, "fsa_first_use_admitted": False}

    def checkpoint(self):
        body = {"schema": SCHEMA, "role": ROLE, "session": self.session,
                "actor": self.actor, "catalog": sorted(self.public_catalog),
                "budget": self.action_budget, "used": self.used,
                "pending": self.pending, "completed": self.completed,
                "source_executed": False, "fsa_first_use_admitted": False}
        return canonical({"kind": KIND, "body": body, "sha256": digest(body)})

    @classmethod
    def restore(cls, raw):
        require(type(raw) is bytes and len(raw) <= 131072,
                "CHECKPOINT_BYTES")
        try:
            data = json.loads(raw.decode("ascii"), object_pairs_hook=unique_keys)
        except (UnicodeError, ValueError, TypeError) as err:
            raise ValueError("TW3B_DEV_DENIED:CHECKPOINT_JSON") from err
        require(type(data) is dict and set(data) == {"kind", "body", "sha256"}
                and data["kind"] == KIND, "CHECKPOINT_ENVELOPE")
        require(raw == canonical(data), "CHECKPOINT_NONCANONICAL")
        body = data["body"]
        require(type(body) is dict and set(body) ==
                {"schema", "role", "session", "actor", "catalog", "budget",
                 "used", "pending", "completed", "source_executed",
                 "fsa_first_use_admitted"}, "CHECKPOINT_SCHEMA")
        require(body["schema"] == SCHEMA and body["role"] == ROLE
                and body["source_executed"] is False
                and body["fsa_first_use_admitted"] is False,
                "CHECKPOINT_ROLE")
        require(type(data["sha256"]) is str
                and digest(body) == data["sha256"], "CHECKPOINT_DIGEST")
        catalog = body["catalog"]
        require(type(catalog) is list and all(type(x) is str for x in catalog)
                and catalog == sorted(set(catalog)), "CHECKPOINT_CATALOG")
        result = cls(session=body["session"], actor=body["actor"],
                     public_catalog=frozenset(catalog),
                     action_budget=body["budget"])
        used, pending, complete = body["used"], body["pending"], body["completed"]
        require(type(used) is int and 0 <= used <= result.action_budget
                and type(complete) is list and len(complete) <= result.action_budget,
                "CHECKPOINT_COUNT")
        require(pending is None or type(pending) is dict,
                "CHECKPOINT_PENDING")
        require(used == len(complete) + int(pending is not None),
                "CHECKPOINT_SEQUENCE")
        records = list(complete) + ([pending] if pending is not None else [])
        for slot, record in enumerate(records, 1):
            require(type(record) is dict
                    and set(record) == {"slot", "destination", "action_id"}
                    and type(record["slot"]) is int and record["slot"] == slot
                    and type(record["destination"]) is str
                    and record["destination"] in result.public_catalog
                    and type(record["action_id"]) is str
                    and record["action_id"] == dev_id(
                        result.session, result.actor, slot, record["destination"]),
                    "CHECKPOINT_ACTION_SEQUENCE")
        result.used = used
        result.pending = dict(pending) if pending is not None else None
        result.completed = [dict(x) for x in complete]
        return result


if __name__ == "__main__":
    raise SystemExit("DEV_ONLY_NO_ORIGINAL_RPG_EVENT_OR_ACTION")

#!/usr/bin/env python3
"""TW5 synthetic owner-sealed public catalog: original worlds and authorization DENIED.

This pure verifier checks a predeclared mock public location menu without
seeing a simulator, path, private map, source owner key, real action or scorer.
HMAC proof is meaningful ONLY after a separate original owner authenticates
the key, run, source and release. Development fixtures do not supply that.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re

ROLE = "TW5_SYNTHETIC_DEV_OWNER_CATALOG_ONLY"
SCHEMA = "forge.itd02.tw5.synthetic_public_catalog.v1"
SOURCE = "0387a1322e8924625f4bdc6ddd6356d517901dfe"
FIELDS = frozenset(("schema", "source_commit", "run_id", "world_id",
                    "actor", "destinations", "max_actions", "audience"))
DOMAIN = b"FORGE-TW5-SYNTHETIC-CATALOG-v1\\0".replace(b"\\\\0", b"\\0")
ACTOR = re.compile(r"npc:(0|[1-9][0-9]*)\\Z".replace("\\\\", "\\"))
PLACE = re.compile(r"location:(0|[1-9][0-9]*)\\Z".replace("\\\\", "\\"))
SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{3,95}\\Z".replace("\\\\", "\\"))
MAX = 9007199254740991


def deny(ok, reason):
    if not ok:
        raise ValueError("TW5_CATALOG_DENIED:" + reason)


def valid_id(value, pattern):
    return (type(value) is str and pattern.fullmatch(value) is not None
            and int(value.split(":", 1)[1]) <= MAX)


def canon(data):
    return json.dumps(data, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def verify_synthetic_catalog(data, digest, *, dev_owner_key, run_id, world_id):
    """Verify a synthetically signed immutable menu; this NEVER grants source access."""
    deny(type(data) is dict and set(data) == FIELDS, "EXACT_FIELDS")
    deny(data["schema"] == SCHEMA and data["source_commit"] == SOURCE, "SOURCE_IDENTITY")
    deny(data["audience"] == ROLE, "SYNTHETIC_ROLE")
    deny(all(type(data[k]) is str and SCOPE.fullmatch(data[k]) is not None
             for k in ("run_id", "world_id")), "SCOPE_SHAPE")
    deny(type(run_id) is str and type(world_id) is str
         and data["run_id"] == run_id and data["world_id"] == world_id, "SCOPE_MISMATCH")
    deny(valid_id(data["actor"], ACTOR), "ACTOR_ID")
    destinations = data["destinations"]
    deny(type(destinations) is list and 1 <= len(destinations) <= 64
         and all(valid_id(d, PLACE) for d in destinations), "PUBLIC_LOCATIONS")
    deny(destinations == sorted(set(destinations)), "CANONICAL_DESTINATIONS")
    deny(type(data["max_actions"]) is int
         and 1 <= data["max_actions"] <= 100, "ACTION_LIMIT")
    deny(type(dev_owner_key) is bytes and len(dev_owner_key) >= 32, "EXTERNAL_TEST_KEY")
    deny(type(digest) is str and re.fullmatch("[0-9a-f]{64}", digest) is not None,
         "SEAL_FORMAT")
    expected = hmac.new(dev_owner_key, DOMAIN + canon(data), hashlib.sha256).hexdigest()
    deny(hmac.compare_digest(digest, expected), "SEAL_MISMATCH")
    return {
        "status": ROLE,
        "catalog_digest_sha256": hashlib.sha256(canon(data)).hexdigest(),
        "run_id": run_id, "world_id": world_id, "actor": data["actor"],
        "destinations": tuple(destinations), "max_actions": data["max_actions"],
        "source_owner_authenticated": False,
        "original_source_executed": False,
        "owner_action_dispatch_authorized": False,
        "fsa_first_use": False, "scientific_go": False,
    }


def check_synthetic_destination(verified, *, actor, destination):
    """Pure source-format/catalog-membership check, not dispatch or budget reservation."""
    deny(type(verified) is dict and verified.get("status") == ROLE
         and verified.get("source_owner_authenticated") is False, "DEV_ONLY")
    deny(valid_id(actor, ACTOR) and actor == verified["actor"], "ACTOR_CUSTODY")
    deny(valid_id(destination, PLACE), "DESTINATION_ID")
    deny(destination in verified["destinations"], "DESTINATION_NOT_PUBLIC")
    return {"status": "TW5_DEV_CATALOG_MEMBER_NOT_DISPATCHED",
            "costs_one_action_slot_if_separately_authorized": True,
            "budget_reserved": False, "source_executed": False, "scientific_go": False}


if __name__ == "__main__":
    raise SystemExit("TW5_NO_ORIGINAL_WORLD_OR_LEARNER_ACTION")

#!/usr/bin/env python3
"""TW3: source-shaped movement proposal PRECHECK, not an original executor.

No original world, source imports, network, controller, owner credentials,
protected samples or genuine action submitted. A public destination catalog
must come from a separately verified owner if/when a real adapter is admitted.
"""
from __future__ import annotations
import re

ROLE = "TW3_HANDCRAFTED_DEV_POLICY_ONLY"
PROPOSAL_KEYS = frozenset(("actor", "destination"))
ACTOR_ID = re.compile(r"npc:(?:0|[1-9][0-9]*)\Z")
DEST_ID = re.compile(r"location:(?:0|[1-9][0-9]*)\Z")
MAX_SOURCE_INDEX = 9007199254740991


def valid_source_id(value, pattern):
    return (type(value) is str and pattern.fullmatch(value) is not None
            and int(value.split(":", 1)[1]) <= MAX_SOURCE_INDEX)


RESULT = "DEV_VALIDATED_NOT_DISPATCHED"
RECEIPT = "DEV_REDACTED_NOT_DISPATCHED"


def demand(ok, reason):
    if not ok:
        raise ValueError("TW3_PROPOSAL_DENIED:" + reason)


def validate_proposal(candidate, *, scoped_actor, public_destinations,
                      action_budget_remaining, already_in_flight):
    """Pure, source-shaped synthetic DEV check, no dispatch or authority.

    The catalog is a CALLER-SUPPLIED fixture here, not a source-owner witness.
    Without original source owner custody, no validated proposal is admissible.
    """
    demand(type(candidate) is dict and set(candidate) == PROPOSAL_KEYS,
           "EXACT_REQUEST_FIELDS")
    demand(valid_source_id(scoped_actor, ACTOR_ID),
           "SCOPED_ACTOR")
    demand(type(public_destinations) is frozenset and
           len(public_destinations) > 0 and
           all(valid_source_id(x, DEST_ID)
               for x in public_destinations), "PUBLIC_CATALOG_SHAPE")
    demand(type(action_budget_remaining) is int and 0 < action_budget_remaining <= 100,
           "FINITE_ACTION_BUDGET")
    demand(type(already_in_flight) is bool and not already_in_flight,
           "IN_FLIGHT_OR_UNKNOWN")
    actor, dest = candidate["actor"], candidate["destination"]
    demand(type(actor) is str and actor == scoped_actor, "ACTOR_CUSTODY")
    demand(valid_source_id(dest, DEST_ID),
           "DESTINATION_FORMAT")
    demand(dest in public_destinations, "DESTINATION_NOT_PUBLIC")
    return {
        "status": RESULT,
        "actor": scoped_actor,
        "destination": dest,
        "costs_one_action_slot": True,
        "source_executed": False,
        "source_owner_catalog_authenticated": False,
        "fsa_first_use_admitted": False,
    }


def redact_original_result(raw):
    """Never return Journey, route, cost, arrival, refusal details or causes.

    Any source-shaped private outcome yields the SAME development receipt.
    In an admitted real adapter, TW2 separately owns post-action observations.
    """
    demand(type(raw) is dict, "SOURCE_RESULT_SHAPE")
    demand(type(raw.get("started")) is bool, "SOURCE_RESULT_STARTED")
    # Preserve neither a reason nor a Journey; only a non-informative dev
    # receipt. It is NOT a public event or a claim that the source ran.
    return {
        "status": RECEIPT,
        "revealed_private_fields": 0,
        "source_executed": False,
        "scientific_first_use": False,
    }


def source_authority():
    return {
        "status": "TW3_OWNER_CUSTODY_NOT_ESTABLISHED",
        "source_owner_check_run_id": 35487048503,
        "original_workflow_tests_passed": True,
        "independent_learner_action_custody": False,
        "source_owner_public_destination_catalog": False,
        "owner_qualified_independent_scorer": False,
        "fsa_admission": False,
        "science_go": False,
    }


if __name__ == "__main__":
    raise SystemExit("TW3_NO_ACTION_DISPATCH_OR_PROTECTED_EXECUTION")

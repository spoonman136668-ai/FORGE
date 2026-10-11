"""R7 source-attested, non-executing portfolio admission rehearsal.

R4-R6 decisions are advisory. R7 verifies *independent* current source evidence
before turning any proposed official handoff into a readiness claim. At the
current R53/Y095 boundary neither archived source is science-qualified:
nothing may be scheduled, dispatched, frozen or promoted by this package.

No filesystem, model, GitHub, broker, evaluator or CKB write capabilities.
"""
from __future__ import annotations

from typing import Any

from portfolio import check, digest
from portfolio_handoff import prepare_handoff

# Immutable archived R167 source identities, independently tested by R168.
# These source checks do not authenticate a future READY_RESEARCH receipt.
SOURCE_PINS = {
    "Wingless": {
        "candidate_sha256": "60a421d4ed786b92cd8d0e8a4b58988dd5d89229277ad2b91e5b11ca47f6cf8a",
        "parent_sha": "b6716df4d94bdac07fde526de4e3a37c5b4f23ee",
        "status": "PINNED_IMPLEMENTATION_COMPILES_SCIENCE_STILL_BLOCKED",
        "focused_go_test_invocations": 2,
        "verified_source_files": 2,
    },
    "Yggdrasil": {
        "candidate_sha256": "ead6681782763de8b953a705783bb3babd5858da30f94257545a394bad928f88",
        "parent_sha": "d5e3715c7124e1fd0fc91da5efbef850ec1d9254",
        "status": "BLOCKED_REQUIRE_FULL_PARENT_SOURCE",
        "focused_go_test_invocations": 0,
        "verified_source_files": 0,
    },
}
RECEIPT_FIELDS = {
    "schema", "lane", "candidate_sha256", "predecessor_receipt_sha256",
    "parent_sha", "status", "focused_go_test_invocations",
    "verified_source_files", "full_historical_disjointness_proven",
    "prospective_source_verification_count", "sealed_outcomes_seen",
    "scientific_classification", "source_qualification_authority",
    "ready_research_authority", "dispatch_authority",
    "accepted_ref_mutation", "production_authority", "broker_access",
    "ktrade_access", "model_calls",
}


def attest_r168(lane: str, source_receipt: dict[str, Any]) -> dict[str, Any]:
    """Read-only bound source check. Does not treat a source test as a seal."""
    check(lane in SOURCE_PINS, "R7_LANE_UNKNOWN")
    check(type(source_receipt) is dict and
          set(source_receipt) == RECEIPT_FIELDS, "R7_SOURCE_RECEIPT_SCHEMA")
    p = SOURCE_PINS[lane]
    check(source_receipt["schema"] ==
          "ckb-plane.research-source-qualification.r168" and
          source_receipt["lane"] == lane, "R7_SOURCE_LANE_MISMATCH")
    for key in ("candidate_sha256", "parent_sha", "status",
                "focused_go_test_invocations", "verified_source_files"):
        check(type(source_receipt[key]) is type(p[key]) and
              source_receipt[key] == p[key], "R7_SOURCE_PIN_DRIFT_" + key.upper())
    sha = source_receipt["predecessor_receipt_sha256"]
    check(type(sha) is str and len(sha) == 64 and
          all(c in "0123456789abcdef" for c in sha),
          "R7_PREDECESSOR_RECEIPT_DIGEST_INVALID")
    for key in ("full_historical_disjointness_proven", "sealed_outcomes_seen",
                "source_qualification_authority", "ready_research_authority",
                "dispatch_authority", "accepted_ref_mutation",
                "production_authority", "broker_access", "ktrade_access"):
        check(source_receipt[key] is False,
              "R7_FORBIDDEN_SCIENCE_OR_AUTHORITY_" + key.upper())
    check(source_receipt["model_calls"] == 0 and
          type(source_receipt["model_calls"]) is int and
          source_receipt["prospective_source_verification_count"] == 0 and
          type(source_receipt["prospective_source_verification_count"]) is int and
          source_receipt["scientific_classification"] == "NOT_EVALUATED",
          "R7_SEALED_EVIDENCE_NOT_PROVEN")
    return {
        "lane": lane,
        "archived_source_receipt_digest": digest(source_receipt),
        "candidate_sha256": p["candidate_sha256"],
        "source_status": p["status"],
        "ready_research": False,
        "full_historical_disjointness_proven": False,
    }


def review_r7(advisory: dict, journal: list[dict],
              contracts_by_candidate: dict, pins_by_candidate: dict,
              source_receipt: dict, max_parallel: int,
              max_per_family: int) -> dict:
    """Reconcile R4-R6 shadow state and current R168 source boundary.

    Every candidate remains blocked irrespective of a synthetic 'official'
    contract or QUALIFIED event; real science requires independent CKB
    qualification and a fresh sealed manifest, not another portfolio vote.
    """
    lane = advisory.get("program") if type(advisory) is dict else None
    source = attest_r168(lane, source_receipt)
    handoff = prepare_handoff(advisory, journal, contracts_by_candidate,
                              pins_by_candidate, max_parallel, max_per_family)
    check(handoff["schema"] == "ckb.research-shadow-handoff.v1" and
          handoff["ready_research_authority"] is False and
          handoff["dispatch_authority"] is False and
          handoff["accepted_ref_mutation"] is False,
          "R7_HANDOFF_AUTHORITY_DRIFT")
    blocked = []
    for proposal in handoff["requests"]:
        check(proposal["status"] in ("BLOCKED",
              "READY_FOR_OFFICIAL_AUTHORITY_REQUEST"), "R7_HANDOFF_UNKNOWN_STATE")
        blocked.append({
            "candidate_id": proposal["candidate_id"],
            "family_id": proposal["family_id"],
            "source_status": source["source_status"],
            "handoff_status": proposal["status"],
            "selection_status": "BLOCKED_FRESH_SEALED_EVIDENCE_AND_CKB_ADMISSION",
            "official_ready_research": False,
            "dispatch_authority": False,
        })
    body = {
        "schema": "ckb.evolutionary-portfolio-r7-shadow.v1",
        "lane": lane,
        "source_receipt_digest": source["archived_source_receipt_digest"],
        "source_candidate_sha256": source["candidate_sha256"],
        "advisory_sha256": handoff["advisory_sha256"],
        "shadow_handoff_sha256": handoff["handoff_sha256"],
        "journal_receipt_sha256": handoff["journal_receipt_sha256"],
        "candidates": blocked,
        "status": "R7_ADVISORY_REHEARSAL_COMPLETE_SCIENCE_BLOCKED",
        "requires_complete_historical_disjointness": True,
        "requires_fresh_sealed_evaluation": True,
        "requires_independent_ckb_ready_research": True,
        "scientific_classification_authority": False,
        "ready_research_authority": False,
        "dispatch_authority": False,
        "accepted_ref_mutation": False,
        "production_authority": False,
        "model_calls": 0,
        "live_activation": False,
    }
    return {**body, "review_sha256": digest(body)}

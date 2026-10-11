"""Shadow-only CKB research-contract handoff, never an authority receipt.

A real CKB READY_RESEARCH decision is still required. This module does not
read/write queues, dispatch runs, mint preregistrations or grant authority.
"""
from __future__ import annotations

from typing import Any

from portfolio import check, digest, identity, integer
from portfolio_scheduler import propose_ready

REQUIRED_SCIENTIFIC_FIELDS = {
    "schema", "experiment_id", "lane", "preregistration_sha",
    "parent_experiment", "parent_sha", "hypothesis", "experiment_family",
    "manifest_sha", "classification_rules", "successors", "invalid_behavior",
    "required_authority", "qualification_profile", "implementation_template",
    "codex_usage", "production_authority", "accepted_ref_mutation",
    "runtime_launch", "capacity_change_authorized", "authority_expansion",
    "broker_access", "ktrade_access"
}
PROVENANCE_FIELDS = {
    "source_advisory_sha256", "candidate_id", "candidate_code_sha256",
    "family_id", "qualified_package_sha", "historical_data_sha256"
}


def _sha(value: Any, length: int, reason: str) -> None:
    identity(value, reason)
    check(len(value) == length, reason + "_LENGTH")


def _validate_unchanged_authority_boundary(contract: dict, lane: str,
                                           candidate: dict) -> str | None:
    check(type(contract) is dict and REQUIRED_SCIENTIFIC_FIELDS <= set(contract),
          "RESEARCH_CONTRACT_REQUIRED_FIELDS")
    check(contract["schema"] == "ckb-plane.research-contract.v1",
          "RESEARCH_CONTRACT_SCHEMA")
    check(contract["lane"] == lane, "RESEARCH_CONTRACT_LANE_MISMATCH")
    check(type(contract["experiment_id"]) is str and
          bool(contract["experiment_id"].strip()),
          "EXPERIMENT_ID_INVALID")
    _sha(contract["parent_sha"], 40, "PARENT_SHA")
    _sha(contract["manifest_sha"], 64, "MANIFEST_SHA")
    check(contract["manifest_sha"] == candidate["sealed_manifest_sha"],
          "SEALED_MANIFEST_BINDING_MISMATCH")
    check(contract["codex_usage"] == "DISABLED", "UNEXPECTED_CODEX")
    for key in ("production_authority", "accepted_ref_mutation",
                "runtime_launch", "capacity_change_authorized",
                "authority_expansion", "broker_access", "ktrade_access"):
        check(contract[key] is False, "RESEARCH_AUTHORITY_WIDENING_" + key.upper())
    rules = contract["classification_rules"]
    successors = contract["successors"]
    check(type(rules) is dict and
          all(k in rules for k in ("supported", "mixed", "negative", "invalid")),
          "CLASSIFICATION_RULES_NOT_FROZEN")
    check(type(successors) is dict and
          all(k in successors for k in ("supported", "mixed", "negative")),
          "SUCCESSOR_RULES_NOT_FROZEN")
    required_authority = contract["required_authority"]
    check(type(required_authority) is dict and
          required_authority.get("disposition") == "READY_RESEARCH" and
          required_authority.get("manifest_sha256") == contract["manifest_sha"] and
          required_authority.get("production_authority") is False and
          required_authority.get("external_model_calls") is False,
          "UNEXPECTED_AUTHORITY_REQUEST")
    _sha(required_authority.get("ckb_plane_sha"), 40, "CKB_SOURCE_SHA")
    check(type(contract["qualification_profile"]) is dict,
          "QUALIFICATION_PROFILE_INVALID")
    prereg = contract["preregistration_sha"]
    check(type(prereg) is str, "PREREGISTRATION_FIELD_INVALID")
    if not prereg:
        return "PREREGISTRATION_IDENTITY_NOT_PINNED"
    _sha(prereg, 40, "PREREGISTRATION_SHA")
    declared_head = contract.get("preregistered_head_sha")
    if declared_head:
        check(declared_head == prereg, "PREREGISTRATION_HEAD_MISMATCH")
    impl = contract["implementation_template"]
    check(type(impl) is dict, "IMPLEMENTATION_TEMPLATE_INVALID")
    if impl.get("ready") is not True:
        return "IMPLEMENTATION_NOT_FROZEN"
    # This extra binding must be incorporated into the actual, independently
    # preregistered CKB contract. The proposal cannot add it on the fly.
    proof = contract.get("portfolio_provenance")
    if proof is None:
        return "PORTFOLIO_BINDING_NOT_PREREGISTERED"
    check(type(proof) is dict and set(proof) == PROVENANCE_FIELDS,
          "PORTFOLIO_PROOF_SCHEMA")
    expected = {
        "source_advisory_sha256": candidate["source_advisory_sha256"],
        "candidate_id": candidate["candidate_id"],
        "candidate_code_sha256": candidate["candidate_code_sha"],
        "family_id": candidate["family_id"],
        "qualified_package_sha": candidate["qualified_package_sha"],
        "historical_data_sha256": candidate["historical_data_sha"]
    }
    check(proof == expected, "PORTFOLIO_PROOF_BINDING_DRIFT")
    return None


def prepare_handoff(advisory: dict, journal: list[dict],
                    contracts_by_candidate: dict,
                    pinned_contract_sha256_by_candidate: dict,
                    max_parallel: int, max_per_family: int) -> dict:
    """Build an advisory authority-*request* dossier, never a launch.

    Pinned contract digests MUST come from a trusted CKB identity receipt,
    independently of the caller-provided contract bytes. Verifying a digest
    mathematically does not authenticate its provenance.
    """
    check(type(contracts_by_candidate) is dict and
          type(pinned_contract_sha256_by_candidate) is dict,
          "HANDOFF_INPUTS_INVALID")
    schedule = propose_ready(advisory, journal, max_parallel, max_per_family)
    historical = advisory.get("historical_data_sha256")
    _sha(historical, 64, "HISTORICAL_DATA_SHA")
    check(schedule["dispatch_authority"] is False,
          "SHADOW_SCHEDULE_UNEXPECTED_AUTHORITY")
    handoffs = []
    seen_experiments = set()
    for row in schedule["start_proposals"]:
        candidate_id = row["candidate_id"]
        frozen = dict(row)
        frozen["source_advisory_sha256"] = advisory["advisory_sha256"]
        frozen["historical_data_sha"] = historical
        contract = contracts_by_candidate.get(candidate_id)
        pinned = pinned_contract_sha256_by_candidate.get(candidate_id)
        if contract is None or pinned is None:
            check(contract is None and pinned is None,
                  "PARTIAL_CONTRACT_IDENTITY")
            handoffs.append({
                "candidate_id": candidate_id,
                "family_id": row["family_id"],
                "status": "BLOCKED",
                "reason": "OFFICIAL_CONTRACT_AND_PIN_REQUIRED",
                "official_experiment_id": None,
                "official_contract_sha256": None
            })
            continue
        _sha(pinned, 64, "PINNED_CONTRACT_SHA")
        check(digest(contract) == pinned, "CONTRACT_SOURCE_IDENTITY_MISMATCH")
        blocked = _validate_unchanged_authority_boundary(
            contract, advisory["program"], frozen
        )
        eid = contract["experiment_id"]
        check(eid not in seen_experiments, "OFFICIAL_EXPERIMENT_DUPLICATE")
        seen_experiments.add(eid)
        handoffs.append({
            "candidate_id": candidate_id,
            "family_id": row["family_id"],
            "status": ("BLOCKED" if blocked else
                       "READY_FOR_OFFICIAL_AUTHORITY_REQUEST"),
            "reason": blocked,
            "official_experiment_id": eid,
            "official_contract_sha256": pinned
        })
    result = {
        "schema": "ckb.research-shadow-handoff.v1",
        "advisory_sha256": advisory["advisory_sha256"],
        "schedule_sha256": schedule["schedule_sha256"],
        "journal_receipt_sha256": schedule["last_receipt_sha256"],
        "requests": handoffs,
        "requires_external_ckb_authority": True,
        "ready_research_authority": False,
        "dispatch_authority": False,
        "scientific_classification_authority": False,
        "production_authority": False,
        "accepted_ref_mutation": False
    }
    return {**result, "handoff_sha256": digest(result)}

"""Deterministic, authority-free research portfolio planning.

This module is deliberately independent of CKB-plane runtime, GitHub, models,
file I/O, and scientific classification. It emits advisory plans only.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40,64}$")
ID = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")
HISTORICAL = frozenset(("historical", "replay", "historical-replay"))
SCHEMA = "ckb.research-portfolio-plan.v1"
ARCHIVE_SCHEMA = "ckb.research-evidence-chain.v1"


class ContractError(ValueError):
    """Fail closed on ambiguous identity, budget, or evidence."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise ContractError(reason)


def identity(value: Any, name: str) -> str:
    check(isinstance(value, str) and SHA.fullmatch(value) is not None,
          name + "_INVALID")
    return value


def identifier(value: Any, name: str) -> str:
    check(isinstance(value, str) and ID.fullmatch(value) is not None,
          name + "_INVALID")
    return value


def number(value: Any, name: str) -> Decimal:
    check(not isinstance(value, bool), name + "_INVALID")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ContractError(name + "_INVALID") from None
    check(result.is_finite(), name + "_NONFINITE")
    return result


def integer(value: Any, name: str, lo: int, hi: int) -> int:
    check(type(value) is int and lo <= value <= hi, name + "_OUT_OF_RANGE")
    return value


def require_exact_keys(obj: Any, keys: set[str], name: str) -> None:
    check(type(obj) is dict and set(obj) == keys, name + "_SCHEMA_MISMATCH")


def validate_contract(contract: dict) -> None:
    require_exact_keys(contract, {
        "schema", "generation_id", "contract_sha", "historical_data_sha",
        "baseline_sha", "family_ids", "frozen", "max_screens_per_family",
        "max_finalists_total", "max_finalists_per_family", "screen_compute_budget",
        "sealed_compute_budget", "max_candidate_parameters"
    }, "CONTRACT")
    check(contract["schema"] == "ckb.research-portfolio-contract.v1", "SCHEMA_INVALID")
    identifier(contract["generation_id"], "GENERATION")
    for field in ("contract_sha", "historical_data_sha", "baseline_sha"):
        identity(contract[field], field.upper())
    check(contract["frozen"] is True, "CONTRACT_NOT_FROZEN")
    fam = contract["family_ids"]
    check(isinstance(fam, list) and 1 <= len(fam) <= 5, "FAMILIES_INVALID")
    check(len(set(fam)) == len(fam), "FAMILY_DUPLICATE")
    for f in fam:
        identifier(f, "FAMILY")
    integer(contract["max_screens_per_family"], "SCREENS", 1, 32)
    integer(contract["max_finalists_total"], "FINALISTS", 1, 5)
    integer(contract["max_finalists_per_family"], "PER_FAMILY", 1, 5)
    integer(contract["max_candidate_parameters"], "CAPACITY", 1, 100000)
    check(number(contract["screen_compute_budget"], "SCREEN_BUDGET") > 0,
          "SCREEN_BUDGET_INVALID")
    check(number(contract["sealed_compute_budget"], "SEALED_BUDGET") > 0,
          "SEALED_BUDGET_INVALID")


def validate_screen(record: dict, contract: dict) -> None:
    require_exact_keys(record, {
        "candidate_id", "family_id", "code_sha", "parent_shas", "operator_id",
        "signature", "data_class", "data_sha", "score", "screen_cost",
        "estimated_sealed_cost", "parameters", "sealed_outcomes_accessed",
        "post_freeze_mutation", "screen_complete"
    }, "SCREEN")
    identifier(record["candidate_id"], "CANDIDATE")
    check(record["family_id"] in contract["family_ids"], "UNKNOWN_FAMILY")
    identity(record["code_sha"], "CODE")
    identity(record["data_sha"], "DATA")
    check(record["data_sha"] == contract["historical_data_sha"],
          "HISTORICAL_IDENTITY_DRIFT")
    parents = record["parent_shas"]
    check(type(parents) is list and len(parents) <= 4, "PARENTS_INVALID")
    for parent in parents:
        identity(parent, "PARENT")
    check(len(set(parents)) == len(parents), "PARENT_DUPLICATE")
    identifier(record["operator_id"], "OPERATOR")
    identifier(record["signature"], "SIGNATURE")
    check(record["data_class"] in HISTORICAL, "SEALED_DATA_FORBIDDEN")
    check(record["sealed_outcomes_accessed"] is False, "SEALED_LEAK")
    check(record["post_freeze_mutation"] is False, "POST_FREEZE_TUNING")
    check(record["screen_complete"] is True, "INCOMPLETE_SCREEN")
    check(number(record["score"], "SCORE").is_finite(), "SCORE_INVALID")
    check(number(record["screen_cost"], "SCREEN_COST") > 0, "SCREEN_COST_INVALID")
    check(number(record["estimated_sealed_cost"], "SEALED_COST") > 0,
          "SEALED_COST_INVALID")
    integer(record["parameters"], "PARAMETERS", 0, contract["max_candidate_parameters"])


def replay_policy_scores(records: list[dict]) -> list[dict]:
    """Dream-style counterfactual *historical-only* policy scorecards.

    No past sealed outcomes are admitted as replay training rows; scoring does
    not select or evaluate a candidate on the sealed generation.
    """
    sums: dict[str, tuple[Decimal, Decimal, int]] = {}
    for row in records:
        require_exact_keys(row, {
            "policy_id", "evidence_sha", "data_class", "sealed_outcomes_accessed",
            "historical_gain", "compute_cost"
        }, "REPLAY_ROW")
        name = identifier(row["policy_id"], "POLICY")
        identity(row["evidence_sha"], "EVIDENCE")
        check(row["data_class"] in HISTORICAL and
              row["sealed_outcomes_accessed"] is False, "REPLAY_SEALED_LEAK")
        gain = number(row["historical_gain"], "GAIN")
        cost = number(row["compute_cost"], "COST")
        check(cost > 0, "REPLAY_COST_INVALID")
        g, c, n = sums.get(name, (Decimal(0), Decimal(0), 0))
        sums[name] = g + gain, c + cost, n + 1
    ranked = [{
        "policy_id": policy,
        "historical_gain_per_compute": str(g / c),
        "historical_evidence_count": n
    } for policy, (g, c, n) in sums.items()]
    ranked.sort(key=lambda r: (-Decimal(r["historical_gain_per_compute"]),
                               r["policy_id"]))
    return ranked


def shortlist(contract: dict, screened: list[dict]) -> dict:
    """Bounded round-robin finalist proposal; never dispatches science."""
    validate_contract(contract)
    check(isinstance(screened, list), "SCREEN_LIST_INVALID")
    check(len(screened) <=
          len(contract["family_ids"]) * contract["max_screens_per_family"],
          "SCREEN_COUNT_OVER_BUDGET")
    ids: set[str] = set()
    code_ids: set[str] = set()
    groups: dict[str, list[dict]] = {f: [] for f in contract["family_ids"]}
    total_cost = Decimal(0)
    for record in screened:
        validate_screen(record, contract)
        check(record["candidate_id"] not in ids, "CANDIDATE_DUPLICATE")
        check(record["code_sha"] not in code_ids, "CODE_IDENTITY_DUPLICATE")
        ids.add(record["candidate_id"])
        code_ids.add(record["code_sha"])
        total_cost += number(record["screen_cost"], "SCREEN_COST")
        groups[record["family_id"]].append(record)
    check(total_cost <= number(contract["screen_compute_budget"], "SCREEN_BUDGET"),
          "TOTAL_SCREEN_BUDGET_EXCEEDED")
    for family, rows in groups.items():
        check(len(rows) <= contract["max_screens_per_family"],
              "FAMILY_SCREEN_BUDGET_EXCEEDED")
        rows.sort(key=lambda r: (-number(r["score"], "SCORE"),
                                 number(r["estimated_sealed_cost"], "SEALED_COST"),
                                 r["candidate_id"]))
    selected: list[dict] = []
    signatures: set[str] = set()
    sealed_cost = Decimal(0)
    # One candidate per family in each pass. A family cannot monopolize the batch.
    for _ in range(contract["max_finalists_per_family"]):
        for family in sorted(groups):
            if len(selected) >= contract["max_finalists_total"]:
                break
            while groups[family]:
                row = groups[family].pop(0)
                cost = number(row["estimated_sealed_cost"], "SEALED_COST")
                if row["signature"] in signatures:
                    continue
                if sealed_cost + cost > number(contract["sealed_compute_budget"],
                                              "SEALED_BUDGET"):
                    continue
                signatures.add(row["signature"])
                sealed_cost += cost
                selected.append({
                    "candidate_id": row["candidate_id"],
                    "family_id": family,
                    "code_sha": row["code_sha"],
                    "historical_data_sha": row["data_sha"],
                    "signature": row["signature"],
                    "estimated_sealed_cost": row["estimated_sealed_cost"],
                    "parameters": row["parameters"]
                })
                break
        if len(selected) >= contract["max_finalists_total"]:
            break
    return {
        "selected": selected,
        "screened_count": len(screened),
        "screen_compute_spent": str(total_cost),
        "sealed_compute_reserved": str(sealed_cost)
    }


def propose_prompt_mutation(parent_sha: str, operator_sha: str,
                            training_data_sha: str, max_output_bytes: int) -> dict:
    """Promptbreeder analogue: a content-addressed, non-executing proposal."""
    for name, value in (("PARENT", parent_sha), ("OPERATOR", operator_sha),
                        ("TRAINING", training_data_sha)):
        identity(value, name)
    integer(max_output_bytes, "OUTPUT_BYTES", 1, 65536)
    body = {
        "schema": "ckb.prompt-mutation-proposal.v1",
        "parent_sha": parent_sha,
        "operator_sha": operator_sha,
        "training_data_sha": training_data_sha,
        "max_output_bytes": max_output_bytes,
        "sealed_outcomes_accessed": False,
        "execution_authority": False
    }
    return {**body, "proposal_sha256": digest(body)}


def propose_theta_adapter(candidate_sha: str, historical_data_sha: str,
                          state_dimension: int, update_budget: int) -> dict:
    """Theta-style bounded adaptation *contract*, not a running learner."""
    identity(candidate_sha, "CANDIDATE")
    identity(historical_data_sha, "HISTORICAL")
    integer(state_dimension, "STATE_DIMENSION", 1, 4096)
    integer(update_budget, "UPDATE_BUDGET", 0, 100000)
    body = {
        "schema": "ckb.bounded-adaptation-proposal.v1",
        "candidate_sha": candidate_sha,
        "historical_data_sha": historical_data_sha,
        "fixed_state_dimension": state_dimension,
        "max_training_updates": update_budget,
        "freeze_before_unseen": True,
        "sealed_test_time_update_allowed": False,
        "persistent_state_growth_allowed": False,
        "execution_authority": False
    }
    return {**body, "proposal_sha256": digest(body)}


def append_evidence(chain: list[dict], record: dict) -> list[dict]:
    """Append-only, content-addressed provenance chain; never edit old entries."""
    check(type(chain) is list, "CHAIN_INVALID")
    for index, entry in enumerate(chain):
        check(type(entry) is dict and "receipt_sha256" in entry, "ENTRY_INVALID")
        body = {k: v for k, v in entry.items() if k != "receipt_sha256"}
        check(digest(body) == entry["receipt_sha256"], "ARCHIVE_TAMPERED")
        check(entry.get("previous_receipt") ==
              (chain[index-1]["receipt_sha256"] if index else None),
              "ARCHIVE_LINK_BROKEN")
    require_exact_keys(record, {
        "kind", "experiment_id", "package_sha", "evidence_sha", "outcome",
        "data_class", "resource_cost"
    }, "EVIDENCE")
    check(record["kind"] in ("historical-screen", "sealed-classification",
                              "invalid-execution", "search-policy-replay"),
          "EVIDENCE_KIND_INVALID")
    identifier(record["experiment_id"], "EXPERIMENT")
    identity(record["package_sha"], "PACKAGE")
    identity(record["evidence_sha"], "EVIDENCE")
    check(record["data_class"] in HISTORICAL.union(("sealed",)), "DATA_CLASS_INVALID")
    if record["kind"] == "sealed-classification":
        check(record["data_class"] == "sealed" and
              record["outcome"] in ("supported", "mixed", "negative", "invalid"),
              "CLASSIFICATION_INVALID")
    else:
        check(record["data_class"] in HISTORICAL and
              record["outcome"] is None, "UNAUTHORIZED_CLASSIFICATION")
    check(number(record["resource_cost"], "RESOURCE_COST") >= 0,
          "RESOURCE_COST_INVALID")
    previous = chain[-1]["receipt_sha256"] if chain else None
    check(not any(e["experiment_id"] == record["experiment_id"] and
                  e["kind"] == record["kind"] and
                  e["package_sha"] == record["package_sha"] for e in chain),
          "DUPLICATE_EVIDENCE")
    body = {**record, "previous_receipt": previous, "schema": ARCHIVE_SCHEMA}
    return [*chain, {**body, "receipt_sha256": digest(body)}]


def make_plan(contract: dict, screened: list[dict],
              historical_policy_rows: list[dict], archive_head_sha: str) -> dict:
    identity(archive_head_sha, "ARCHIVE_HEAD")
    plan = {
        "schema": SCHEMA,
        "contract_sha": contract["contract_sha"],
        "generation_id": contract["generation_id"],
        "archive_head_sha": archive_head_sha,
        "shortlist": shortlist(contract, screened),
        "historical_policy_ranking": replay_policy_scores(historical_policy_rows),
        "scientific_classification": None,
        "dispatch_authority": False,
        "promotion_authority": False,
        "accepted_ref_mutation": False,
        "activation_authority": False
    }
    return {**plan, "plan_sha256": digest(plan)}

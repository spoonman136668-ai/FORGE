"""Pure, event-sourced *shadow* scheduler for independent research finalists.

No I/O, Actions dispatch, queue mutation, scientific classification, or CKB
authority. A controller adapter must independently verify all receipt sources
before translating these advisory decisions into official work.
"""
from __future__ import annotations

from typing import Any

from portfolio import (ContractError, check, digest, identity, identifier, integer)

KIND = ("QUALIFIED", "RUN_STARTED", "RUN_FAILED", "REQUALIFIED", "CLASSIFIED")
OUTCOMES = ("supported", "mixed", "negative", "invalid")
EVENT_KEYS = {
    "schema", "candidate_id", "family_id", "candidate_code_sha",
    "qualified_package_sha", "sealed_manifest_sha", "kind", "run_id",
    "result_sha", "classification", "error_signature", "authority_receipt_sha",
    "previous_receipt", "receipt_sha256"
}


def exact_keys(row: Any, allowed: set[str], reason: str) -> None:
    check(type(row) is dict and set(row) == allowed, reason)


def candidate_rows(advisory: dict) -> dict[str, dict]:
    check(type(advisory) is dict and advisory.get("schema") in (
              "ckb.fanout-portfolio-advisory.v1",
              "ckb.portfolio-multibatch-advisory.v1"), "ADVISORY_INVALID")
    sha = advisory.get("advisory_sha256")
    identity(sha, "ADVISORY_SHA")
    check(len(sha) == 64 and
          sha == digest({k: v for k, v in advisory.items() if k != "advisory_sha256"}),
          "ADVISORY_TAMPERED")
    check(advisory.get("dispatch_authority") is False and
          advisory.get("promotion_authority") is False and
          advisory.get("scientific_classification") is None and
          advisory.get("accepted_ref_mutation") is False,
          "ADVISORY_AUTHORITY_INVALID")
    rows = advisory.get("shortlist", {}).get("selected")
    check(type(rows) is list and 1 <= len(rows) <= 5,
          "SHORTLIST_INVALID")
    by_id = {}
    for row in rows:
        check(type(row) is dict and set(row) == {
            "candidate_id", "family_id", "code_sha",
            "historical_data_sha", "signature", "estimated_sealed_cost",
            "parameters"
        }, "CANDIDATE_ROW_SCHEMA")
        cid = identifier(row["candidate_id"], "CANDIDATE")
        identifier(row["family_id"], "FAMILY")
        identity(row["code_sha"], "CODE")
        check(cid not in by_id, "DUPLICATE_CANDIDATE")
        by_id[cid] = row
    return by_id


def reconcile(advisory: dict, journal: list[dict]) -> dict:
    """Reconstruct state from immutable events. Exact duplicate replays are
    idempotent; changed or out-of-order duplicates fail closed.
    """
    by_id = candidate_rows(advisory)
    check(type(journal) is list, "JOURNAL_INVALID")
    state = {cid: {
        "candidate_id": cid, "family_id": row["family_id"],
        "candidate_code_sha": row["code_sha"], "status": "PLANNED",
        "qualified_package_sha": None, "sealed_manifest_sha": None,
        "authority_receipt_sha": None, "run_id": None, "result_sha": None,
        "classification": None, "error_signature": None, "attempts": 0
    } for cid, row in by_id.items()}
    accepted = {}
    previous = None
    for event in journal:
        exact_keys(event, EVENT_KEYS, "EVENT_SCHEMA")
        body = {k: v for k, v in event.items() if k != "receipt_sha256"}
        receipt = digest(body)
        check(receipt == event["receipt_sha256"], "EVENT_TAMPERED")
        if receipt in accepted:
            check(accepted[receipt] == event, "EVENT_DUPLICATE_DRIFT")
            continue  # exact at-least-once delivery, no duplicate progression
        check(event["previous_receipt"] == previous, "EVENT_CHAIN_BROKEN")
        previous = receipt
        accepted[receipt] = event
        check(event["schema"] == "ckb.research-shadow-event.v1",
              "EVENT_SCHEMA_VERSION")
        cid = identifier(event["candidate_id"], "CANDIDATE")
        check(cid in state, "EVENT_UNKNOWN_CANDIDATE")
        entry = state[cid]
        check(event["family_id"] == entry["family_id"] and
              event["candidate_code_sha"] == entry["candidate_code_sha"],
              "EVENT_CANDIDATE_IDENTITY_DRIFT")
        package_sha = identity(event["qualified_package_sha"], "PACKAGE")
        manifest_sha = identity(event["sealed_manifest_sha"], "MANIFEST")
        authority = identity(event["authority_receipt_sha"], "AUTHORITY_RECEIPT")
        check(len(package_sha) == 40 and len(manifest_sha) == 64 and
              len(authority) == 64, "EVENT_SHA_LENGTH")
        kind = event["kind"]
        check(kind in KIND, "EVENT_KIND_INVALID")
        if entry["qualified_package_sha"] is not None:
            check(entry["qualified_package_sha"] == package_sha and
                  entry["sealed_manifest_sha"] == manifest_sha and
                  entry["authority_receipt_sha"] == authority,
                  "EVENT_FROZEN_IDENTITY_DRIFT")
        else:
            entry["qualified_package_sha"] = package_sha
            entry["sealed_manifest_sha"] = manifest_sha
            entry["authority_receipt_sha"] = authority
        if kind in ("QUALIFIED", "REQUALIFIED"):
            expected = "PLANNED" if kind == "QUALIFIED" else "BLOCKED"
            check(entry["status"] == expected, "INVALID_QUALIFICATION_TRANSITION")
            check(event["run_id"] is None and event["result_sha"] is None and
                  event["classification"] is None and
                  event["error_signature"] is None, "INVALID_QUALIFICATION_FIELDS")
            entry.update(status="QUALIFIED", run_id=None, error_signature=None)
        elif kind == "RUN_STARTED":
            check(entry["status"] == "QUALIFIED", "UNQUALIFIED_START")
            run_id = integer(event["run_id"], "RUN_ID", 1, 2**63-1)
            check(event["result_sha"] is None and
                  event["classification"] is None and
                  event["error_signature"] is None, "INVALID_START_FIELDS")
            entry.update(status="RUNNING", run_id=run_id,
                         attempts=entry["attempts"] + 1)
        elif kind == "RUN_FAILED":
            check(entry["status"] == "RUNNING" and
                  event["run_id"] == entry["run_id"] and
                  event["result_sha"] is None and
                  event["classification"] is None and
                  type(event["error_signature"]) is str and
                  bool(event["error_signature"].strip()),
                  "INVALID_FAILURE_TRANSITION")
            entry.update(status="BLOCKED", error_signature=event["error_signature"])
        else:
            check(entry["status"] == "RUNNING" and
                  event["run_id"] == entry["run_id"] and
                  event["classification"] in OUTCOMES and
                  event["error_signature"] is None,
                  "INVALID_CLASSIFICATION_TRANSITION")
            identity(event["result_sha"], "RESULT")
            check(len(event["result_sha"]) == 64, "RESULT_SHA_LENGTH")
            entry.update(status="CLASSIFIED", result_sha=event["result_sha"],
                         classification=event["classification"])
    return {
        "schema": "ckb.research-shadow-ledger.v1",
        "advisory_sha256": advisory["advisory_sha256"],
        "last_receipt_sha256": previous,
        "unique_event_count": len(accepted),
        "candidates": [state[cid] for cid in sorted(state)],
        "dispatch_authority": False,
        "scientific_classification_authority": False
    }


def propose_ready(advisory: dict, journal: list[dict],
                  max_parallel: int, max_per_family: int) -> dict:
    """Recommend capacity-respecting independent starts, never dispatch them."""
    integer(max_parallel, "MAX_PARALLEL", 0, 5)
    integer(max_per_family, "MAX_PER_FAMILY", 1, 5)
    state = reconcile(advisory, journal)
    active = [c for c in state["candidates"] if c["status"] == "RUNNING"]
    slots = max(0, max_parallel - len(active))
    family_active: dict[str, int] = {}
    for candidate in active:
        family = candidate["family_id"]
        family_active[family] = family_active.get(family, 0) + 1
    ready = []
    for candidate in state["candidates"]:
        if candidate["status"] != "QUALIFIED" or slots <= 0:
            continue
        family = candidate["family_id"]
        if family_active.get(family, 0) >= max_per_family:
            continue
        family_active[family] = family_active.get(family, 0) + 1
        slots -= 1
        ready.append({
            "candidate_id": candidate["candidate_id"],
            "family_id": family,
            "candidate_code_sha": candidate["candidate_code_sha"],
            "qualified_package_sha": candidate["qualified_package_sha"],
            "sealed_manifest_sha": candidate["sealed_manifest_sha"],
            "authority_receipt_sha": candidate["authority_receipt_sha"]
        })
    out = {
        "schema": "ckb.research-shadow-schedule.v1",
        "advisory_sha256": advisory["advisory_sha256"],
        "last_receipt_sha256": state["last_receipt_sha256"],
        "max_parallel": max_parallel, "max_per_family": max_per_family,
        "active_count": len(active), "start_proposals": ready,
        "dispatch_authority": False, "promotion_authority": False
    }
    return {**out, "schedule_sha256": digest(out)}


def event_for(previous_receipt: str | None, candidate: dict, kind: str,
              package_sha: str, sealed_manifest_sha: str, authority_receipt_sha: str,
              run_id: int | None = None, result_sha: str | None = None,
              classification: str | None = None,
              error_signature: str | None = None) -> dict:
    """Pure event formatter for tests/preview; caller still owns verification."""
    body = {
        "schema": "ckb.research-shadow-event.v1", "kind": kind,
        "candidate_id": candidate["candidate_id"],
        "family_id": candidate["family_id"],
        "candidate_code_sha": candidate["code_sha"],
        "qualified_package_sha": package_sha,
        "sealed_manifest_sha": sealed_manifest_sha,
        "authority_receipt_sha": authority_receipt_sha,
        "run_id": run_id, "result_sha": result_sha,
        "classification": classification, "error_signature": error_signature,
        "previous_receipt": previous_receipt
    }
    return {**body, "receipt_sha256": digest(body)}

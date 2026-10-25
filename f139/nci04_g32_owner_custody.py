"""G32 isolated, read-only original ledger and V2 dual-OS receipt review.

Only a caller holding the original owner mutex, knowing the authenticated
installed source and possessing separately authenticated provider artifacts
may use this. No dispatch, event writer, merge or science permission.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database
from f139.nci04_native_contract import digest
from f139.nci04_owner_ledger import (
    KIND, frozen_native_issue, verify_admission, verify_native_activation,
)
from f139.nci04_owner_issue import make_signed_dispatch_inputs
from f139.nci04_signed_native import NativeAdmission, admit_native_intent
from f139.nci04_provider_receipt_v2 import verify_v2_provider_zip
from f139.nci04_v2_owner_permit import (
    FIRST_NEW_EVENT, verify_v2_owner_permit,
)

SCHEMA = "forge.f139.g32.owner-v2-development-custody-readonly.v1"
OS_LABELS = frozenset(("ubuntu-latest", "windows-latest"))
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class V2CustodyDenied(ValueError):
    pass


def need(value: bool, why: str) -> None:
    if not value:
        raise V2CustodyDenied("F139_G32_" + why)


def event_rows(db: Database, kind: str, ticket: str):
    found = []
    for row in db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (kind,)
    ):
        value = json.loads(row["payload"])
        if isinstance(value, dict) and value.get("ticket") == ticket:
            found.append((row, value))
    return found


def authenticate_original_admission(db: Database,
                                    admission: NativeAdmission, *,
                                    owner_key: str) -> dict:
    """Check a real source-bound SQLite event and reconstruct the V1 HMAC.

    The authenticated original caller must supply the genuine owner key and
    hold SingleOwner. This is not a remote witness or independent lock proof.
    """
    need(type(db) is Database and isinstance(admission, NativeAdmission),
         "ORIGINAL_DATABASE_AND_ADMISSION_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and verify_native_activation(db)
         and admission.source_sha == meta["source_sha"]
         and type(meta["epoch"]) is int and meta["epoch"] > 0,
         "SOURCE_OR_OWNER_ACTIVATION_INVALID")
    found = event_rows(db, KIND, admission.ticket)
    need(len(found) == 1, "EXACT_ONE_NATIVE_ADMISSION_REQUIRED")
    row, event = found[0]
    need(type(row["seq"]) is int and row["seq"] > FIRST_NEW_EVENT
         and type(row["sha"]) is str
         and SHA64.fullmatch(row["sha"]) is not None,
         "HISTORICAL_NATIVE_REPLAY_DENIED")
    candidate = verify_admission(db, event, row["prior_sha"])
    issue = frozen_native_issue(db, admission.ticket)
    need(admission.intent == candidate == issue.candidate
         and admission.lane == event["lane"] == "Yggdrasil"
         and event["source_sha"] == admission.source_sha
         and event["issue_number"] == admission.issue_number
         and event["issue_id"] == admission.issue_id
         and issue.issue_body_sha256 == event["issue_body_sha256"],
         "ORIGINAL_CANDIDATE_ISSUE_IDENTITY_DRIFT")
    task = db.conn.execute(
        "SELECT stage,source_sha,manifest_sha,run_id FROM tasks "
        "WHERE ticket=?", (admission.ticket,)
    ).fetchone()
    # A V1 VERIFIED terminal is NOT retroactive proof of V2.
    need(task is not None and task["stage"] == "WAIT_PROVIDER"
         and task["source_sha"] == admission.source_sha
         and task["manifest_sha"] == event["manifest_sha256"]
         and task["run_id"] is None,
         "EXACT_INFLIGHT_NATIVE_STATE_REQUIRED")
    claimed = event_rows(db, "BEFORE_DISPATCH_INTENT", admission.ticket)
    posted = event_rows(db, "DISPATCH_POST_RETURNED", admission.ticket)
    terminal = event_rows(db, "PROVIDER_VERIFIED_TERMINAL",
                          admission.ticket)
    need(len(claimed) == 1 and len(posted) == 1 and not terminal
         and row["seq"] < claimed[0][0]["seq"] < posted[0][0]["seq"],
         "ORIGINAL_DISPATCH_SEQUENCE_INVALID")
    signed = make_signed_dispatch_inputs(
        issue, owner_hmac_key=owner_key, epoch=meta["epoch"])
    controller_inputs = {
        "key": owner_key, "ticket": issue.ticket,
        "lane": issue.lane, "source_sha": issue.source_sha,
        "epoch": str(meta["epoch"]), "signature": signed["signature"],
        "repository": "spoonman136668-ai/FORGE",
        "ref": "refs/heads/main", "event": "workflow_dispatch",
        "head_sha": issue.source_sha, "run_attempt": "1",
        "run_id": str(admission.run_id), "os": admission.runner_os,
    }
    reconstructed = admit_native_intent(
        controller_inputs, issue.intent_raw,
        native_signature=signed["native_signature"],
        issue_number=str(issue.number), issue_id=str(issue.issue_id),
        issue_body_sha256=issue.issue_body_sha256,
        authenticated_main_sha=meta["source_sha"],
        authenticated_target_commit=issue.candidate.target_commit,
        authenticated_target_tree=issue.candidate.target_tree_sha,
    )
    need(reconstructed == admission,
         "RECONSTRUCTED_ORIGINAL_SIGNED_ADMISSION_DRIFT")
    return {
        "source_sha": meta["source_sha"], "epoch": meta["epoch"],
        "event_seq": row["seq"], "event_sha256": row["sha"],
        "ticket": admission.ticket,
    }


def verify_v2_development_custody(db: Database, admissions: dict,
                                  permits: dict, provider: dict, *,
                                  owner_key: str) -> dict:
    """Read-only check of both V2 ZIPs; no terminal or science admission.

    GitHub workflow, run, jobs and artifact metadata must be authenticated
    independently by original owner; supplied metadata alone is not proof.
    """
    need(type(admissions) is dict and set(admissions) == OS_LABELS
         and type(permits) is dict and set(permits) == OS_LABELS
         and type(provider) is dict and set(provider) == OS_LABELS,
         "COMPLETE_DUAL_OS_CUSTODY_REQUIRED")
    proofs, authenticated = {}, {}
    for label in ("ubuntu-latest", "windows-latest"):
        a = admissions[label]
        need(isinstance(a, NativeAdmission) and a.runner_os == label,
             "SIGNED_ADMISSION_OS_DRIFT")
        owner = authenticate_original_admission(db, a, owner_key=owner_key)
        permit = verify_v2_owner_permit(
            permits[label], a, owner_key=owner_key,
            epoch=owner["epoch"],
            admission_event_seq=owner["event_seq"],
            admission_event_sha256=owner["event_sha256"],
            authenticated_source_sha=owner["source_sha"])
        need(permit["signed_v2_only"] is True
             and permit["worker_dispatched"] is False
             and permit["scientific_first_use_authorized"] is False,
             "OWNER_V2_PERMISSION_DRIFT")
        item = provider[label]
        need(type(item) is dict and set(item) == {"zip_bytes", "metadata"},
             "PROVIDER_INPUT_INVALID")
        result = verify_v2_provider_zip(
            item["zip_bytes"], item["metadata"], a,
            require_qualified=False)
        proofs[label] = {
            "permit_sha256": digest(permits[label]),
            "provider_zip_sha256": result["artifact_sha256"],
            "development_qualified": result["qualified"],
        }
        authenticated[label] = (owner, a)
    first, second = (authenticated[x] for x in
                     ("ubuntu-latest", "windows-latest"))
    owner_a, a = first
    owner_b, b = second
    need(a.ticket == b.ticket and a.source_sha == b.source_sha
         and a.run_id == b.run_id and a.issue_number == b.issue_number
         and a.issue_id == b.issue_id and a.intent == b.intent
         and owner_a == owner_b,
         "CROSS_PLATFORM_ORIGINAL_CUSTODY_DIVERGENCE")
    all_pass = all(p["development_qualified"] for p in proofs.values())
    return {
        "schema": SCHEMA,
        "source_sha": a.source_sha, "ticket": a.ticket,
        "run_id": a.run_id,
        "original_admission_event_seq": owner_a["event_seq"],
        "original_admission_event_sha256": owner_a["event_sha256"],
        "provider_os_receipts": proofs,
        "both_platforms_development_qualified": all_pass,
        "disposition": (
            "V2_DEVELOPMENT_POSITIVE_NOT_TERMINAL" if all_pass
            else "V2_DEVELOPMENT_NEGATIVE_RETAINED"),
        "provider_origin_independently_attested": False,
        "original_v2_terminal_custody_written": False,
        "worker_dispatched": False,
        "scientific_first_use_authorized": False,
        "accepted_ref_mutations": 0, "paid_model_calls": 0,
    }

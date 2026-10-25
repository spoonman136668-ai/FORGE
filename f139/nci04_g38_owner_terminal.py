"""F139 G38: single-original-owner, crash-safe, V2 provider terminal custody.

Only the existing F139 SingleOwner tick is allowed to invoke this. The
original G31/G32/G35 checks and frozen original DB are authoritative;
there is NO new controller, polling task, ticket, model API or science grant.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from f139.local_controller import Database, GitHub, store_evidence, utc_now
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import frozen_native_issue
from f139.nci04_owner_issue import make_signed_dispatch_inputs
from f139.nci04_signed_native import admit_native_intent
from f139.nci04_g32_owner_custody import (
    event_rows, verify_v2_development_custody,
)
from f139.nci04_g35_provider_origin import inspect_v2_provider_run
from f139.nci04_v2_owner_permit import issue_v2_owner_permit
from f139.nci04_g36_v2_dispatch import verify_claim

KIND = "NATIVE_V_TWO_PROVIDER_CUSTODY"
SCHEMA = "forge.f139.g38.original-v2-provider-custody.v1"
OS = ("ubuntu-latest", "windows-latest")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
RECORD_FIELDS = frozenset({
    "schema", "ticket", "source_sha", "run_id", "outcome",
    "original_admission_event_seq", "original_admission_event_sha256",
    "original_claim_event_seq", "original_claim_event_sha256",
    "provider_authorize_job_id", "provider_platforms", "v2_permit_sha256",
    "receipt_review_sha256", "evidence_dir", "evidence_manifest_sha256",
    "scientific_first_use", "paid_model_calls", "accepted_ref_mutations",
})


class G38Denied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise G38Denied("F139_G38_" + reason)


def _exact_original_events(db: Database, ticket: str):
    a = event_rows(db, "NATIVE_DEVELOPMENT_ADMITTED", ticket)
    c = event_rows(db, "BEFORE_DISPATCH_INTENT", ticket)
    p = event_rows(db, "DISPATCH_POST_RETURNED", ticket)
    terminal = event_rows(db, "PROVIDER_VERIFIED_TERMINAL", ticket)
    negatives = event_rows(db, "NATIVE_FAILED_PROVIDER_CUSTODY", ticket)
    v2 = event_rows(db, KIND, ticket)
    need(len(a) == len(c) == len(p) == 1
         and not terminal and not negatives and not v2
         and 220 < a[0][0]["seq"] < c[0][0]["seq"] < p[0][0]["seq"],
         "FRESH_ONCE_ONLY_ORIGINAL_POST_REQUIRED")
    return a[0][0], c[0][0], p[0][0]


def _original_admissions(db: Database, ticket: str, run_id: int,
                         owner_key: str):
    """Reconstruct both existing V1/native HMACs and G36 V2 claim HMAC."""
    meta = db.meta()
    issue = frozen_native_issue(db, ticket)
    need(issue.source_sha == meta["source_sha"]
         and issue.lane == "Yggdrasil"
         and type(run_id) is int and run_id > 0,
         "ORIGINAL_SOURCE_OR_RUN_DRIFT")
    a, claim, _ = _exact_original_events(db, ticket)
    signed = make_signed_dispatch_inputs(
        issue, owner_hmac_key=owner_key, epoch=meta["epoch"])
    verify_claim(
        owner_key, issue, meta["epoch"], a["seq"], a["sha"],
        claim["seq"], claim["sha"],
        __import__("f139.nci04_g36_v2_dispatch", fromlist=["signature"]).signature(
            owner_key, issue, meta["epoch"], a["seq"], a["sha"],
            claim["seq"], claim["sha"]))
    admissions, permits = {}, {}
    for label in OS:
        controller = {
            "key": owner_key, "ticket": ticket, "lane": issue.lane,
            "source_sha": issue.source_sha, "epoch": str(meta["epoch"]),
            "signature": signed["signature"],
            "repository": "spoonman136668-ai/FORGE",
            "ref": "refs/heads/main", "event": "workflow_dispatch",
            "head_sha": meta["source_sha"], "run_attempt": "1",
            "run_id": str(run_id), "os": label,
        }
        record = admit_native_intent(
            controller, issue.intent_raw,
            native_signature=signed["native_signature"],
            issue_number=str(issue.number), issue_id=str(issue.issue_id),
            issue_body_sha256=issue.issue_body_sha256,
            authenticated_main_sha=meta["source_sha"],
            authenticated_target_commit=issue.candidate.target_commit,
            authenticated_target_tree=issue.candidate.target_tree_sha)
        admissions[label] = record
        permits[label] = issue_v2_owner_permit(
            record, owner_key=owner_key, epoch=meta["epoch"],
            admission_event_seq=a["seq"],
            admission_event_sha256=a["sha"],
            authenticated_source_sha=meta["source_sha"])
    return admissions, permits, a, claim


def _compact_provider(proof: dict):
    need(isinstance(proof, dict)
         and proof.get("provider_api_metadata_crosschecked") is True
         and type(proof.get("authorize_job_id")) is int
         and proof["authorize_job_id"] > 0
         and set(proof.get("platforms", {})) == set(OS)
         and set(proof.get("outer_archives", {})) == set(OS),
         "ORIGINAL_GITHUB_PROVIDER_PROOF_INCOMPLETE")
    result = {}
    for label in OS:
        item = proof["platforms"][label]
        need(type(item) is dict and set(item) == {
            "job_id", "artifact_id", "outer_artifact_sha256",
            "inner_v2_sha256", "development_qualified"}
            and type(item["job_id"]) is int and item["job_id"] > 0
            and type(item["artifact_id"]) is int and item["artifact_id"] > 0
            and isinstance(item["development_qualified"], bool)
            and item["outer_artifact_sha256"] == digest(
                proof["outer_archives"][label])
            and SHA64.fullmatch(item["inner_v2_sha256"]) is not None,
            "ORIGINAL_PROVIDER_BYTES_OR_JOB_BINDING_DRIFT")
        result[label] = dict(item)
    return result


def settle_original_v2(db: Database, api: GitHub, db_path: Path, *,
                       ticket: str, run_id: int, started_at: str,
                       owner_key: str) -> dict:
    """Called ONLY under existing original SingleOwner lock.

    Real read-only G35 GitHub GET and G32 SQLite/G31 permit verification
    happen before storing any files. Original ZIPs are saved and fsynced
    before one atomic SQLite transaction; retry compares exact bytes.
    Provider failures/quarantine are terminal and cannot be redispatched.
    """
    need(type(db) is Database and isinstance(api, GitHub)
         and type(db_path) is Path and type(owner_key) is str
         and len(owner_key) >= 32
         and isinstance(ticket, str) and ticket.startswith("f139-nci04-")
         and isinstance(started_at, str), "EXCLUSIVE_ORIGINAL_CONTEXT_REQUIRED")
    db.verify()
    task = db.conn.execute(
        "SELECT * FROM tasks WHERE ticket=?", (ticket,)).fetchone()
    need(task is not None and task["stage"] == "WAIT_PROVIDER"
         and task["run_id"] is None
         and task["source_sha"] == db.meta()["source_sha"]
         and task["started_at"] == started_at,
         "EXACT_WAIT_PROVIDER_NO_REPLAY")
    admissions, permits, admission_event, claim_event = _original_admissions(
        db, ticket, run_id, owner_key)
    provider = inspect_v2_provider_run(
        api, run_id=run_id, ticket=ticket,
        started_at=started_at, admissions=admissions)
    checked = _compact_provider(provider)
    review = verify_v2_development_custody(
        db, admissions, permits, provider["provider_payloads"],
        owner_key=owner_key)
    positive = provider["both_platforms_development_qualified"]
    need(type(positive) is bool
         and review["both_platforms_development_qualified"] is positive
         and review["ticket"] == ticket and review["run_id"] == run_id
         and review["source_sha"] == task["source_sha"]
         and provider["source_sha"] == task["source_sha"],
         "INDEPENDENT_G32_G35_VERIFIERS_DISAGREE")
    # Existing storage has strict replay readback and refuses any partial
    # or changed evidence after a process crash.
    evidence_dir, evidence_sha = store_evidence(
        db_path.parent, ticket, run_id, provider["outer_archives"])
    receipt = {
        "schema": SCHEMA, "ticket": ticket,
        "source_sha": task["source_sha"], "run_id": run_id,
        "outcome": "VERIFIED" if positive else "QUARANTINED",
        "original_admission_event_seq": admission_event["seq"],
        "original_admission_event_sha256": admission_event["sha"],
        "original_claim_event_seq": claim_event["seq"],
        "original_claim_event_sha256": claim_event["sha"],
        "provider_authorize_job_id": provider["authorize_job_id"],
        "provider_platforms": checked,
        "v2_permit_sha256": {
            label: digest(permits[label]) for label in OS},
        "receipt_review_sha256": digest(canonical(review)),
        "evidence_dir": evidence_dir,
        "evidence_manifest_sha256": evidence_sha,
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
    }
    need(set(receipt) == RECORD_FIELDS, "V2_TERMINAL_RECORD_INVENTORY")
    with db.transaction():
        db.verify()
        current = db.conn.execute(
            "SELECT stage,source_sha,run_id,started_at FROM tasks WHERE ticket=?",
            (ticket,)).fetchone()
        need(current is not None and current["stage"] == "WAIT_PROVIDER"
             and current["run_id"] is None
             and current["source_sha"] == task["source_sha"]
             and current["started_at"] == started_at
             and not event_rows(db, KIND, ticket),
             "CONCURRENT_PROVIDER_OR_REPLAY_REFUSED")
        if positive:
            db.conn.execute(
                "UPDATE tasks SET stage='VERIFIED',run_id=?,evidence_dir=?,"
                "evidence_sha=?,completed_at=? WHERE ticket=?",
                (run_id,evidence_dir,evidence_sha,utc_now(),ticket))
            db.event("PROVIDER_VERIFIED_TERMINAL", {
                "ticket":ticket, "run_id":run_id, "evidence_sha":evidence_sha})
        else:
            jobs = {
                label: {
                    "job_id": checked[label]["job_id"],
                    "conclusion": (
                        "success" if checked[label]["development_qualified"]
                        else "failure")
                } for label in OS
            }
            report = {
                "ticket":ticket, "run_id":run_id,
                "source_sha":task["source_sha"], "jobs":jobs,
                "artifact_ids":sorted(checked[label]["artifact_id"] for label in OS),
                "provider_terminal":"FAILURE_NO_REPLAY",
                "scientific_first_use":False,
            }
            db.event("NATIVE_FAILED_PROVIDER_CUSTODY", {
                "schema":"forge.f139.owner-native-provider-negative.v1",
                "ticket":ticket, "run_id":run_id,
                "source_sha":task["source_sha"],
                "provider_sha256":digest(canonical(report)),
                "provider":report,"scientific_first_use":False})
            db.conn.execute(
                "UPDATE tasks SET stage='QUARANTINED',"
                "quarantine_reason='FAILED_OR_CANCELLED_NO_REPLAY' WHERE ticket=?",
                (ticket,))
            db.event("ATTEMPT_QUARANTINED",{
                "ticket":ticket,"reason":"FAILED_OR_CANCELLED_NO_REPLAY"})
        db.event(KIND, receipt)
        db.verify()
    return {
        "schema":SCHEMA, "ticket":ticket,"run_id":run_id,
        "outcome":receipt["outcome"],
        "event_head_sha256":db.meta()["head_hash"],
        "evidence_manifest_sha256":evidence_sha,
        "no_replay":True, "scientific_first_use":False,
    }


def verify_g38_custody(db: Database) -> None:
    """Cold-restart evidence verification added to existing Database.verify."""
    seen = set()
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq",(KIND,)):
        doc = json.loads(row["payload"])
        need(isinstance(doc, dict) and set(doc) == RECORD_FIELDS
             and doc.get("schema") == SCHEMA
             and isinstance(doc.get("ticket"), str)
             and doc["ticket"].startswith("f139-nci04-")
             and type(doc.get("run_id")) is int and doc["run_id"]>0
             and doc["ticket"] not in seen
             and doc.get("scientific_first_use") is False
             and doc.get("paid_model_calls") == 0
             and doc.get("accepted_ref_mutations") == 0
             and doc.get("outcome") in ("VERIFIED", "QUARANTINED"),
             "COLD_CUSTODY_RECORD_INVALID_OR_DUPLICATE")
        seen.add(doc["ticket"])
        task=db.conn.execute(
            "SELECT source_sha,stage,run_id,evidence_dir,evidence_sha,"
            "quarantine_reason FROM tasks WHERE ticket=?",
            (doc["ticket"],)).fetchone()
        need(task is not None and task["source_sha"] == doc["source_sha"]
             and task["stage"] == doc["outcome"]
             and ((doc["outcome"]=="VERIFIED"
                   and task["run_id"] == doc["run_id"]
                   and task["evidence_dir"] == doc["evidence_dir"]
                   and task["evidence_sha"] == doc["evidence_manifest_sha256"])
                  or (doc["outcome"]=="QUARANTINED"
                      and task["run_id"] is None
                      and task["quarantine_reason"] ==
                          "FAILED_OR_CANCELLED_NO_REPLAY")),
             "COLD_CUSTODY_TASK_DRIFT")
        folder = Path(doc["evidence_dir"])
        need(folder.is_dir() and not folder.is_symlink()
             and folder.name == str(doc["run_id"])
             and folder.parent.name == doc["ticket"]
             and {p.name for p in folder.iterdir()} ==
                {"ubuntu-latest.zip","windows-latest.zip","manifest.json"},
             "COLD_CUSTODY_FILES_MISSING_OR_EXTRA")
        manifest = {
            "schema":"forge.f139.windows-evidence-manifest.v1",
            "ticket":doc["ticket"],"run_id":doc["run_id"],
            "sha256":{},
            "scientific_originals":0,"approved_science":False,
        }
        platforms=doc["provider_platforms"]
        need(type(platforms) is dict and set(platforms) == set(OS)
             and type(doc["v2_permit_sha256"]) is dict
             and set(doc["v2_permit_sha256"]) == set(OS)
             and all(SHA64.fullmatch(doc["v2_permit_sha256"][x])
                     is not None for x in OS),
             "COLD_CUSTODY_PLATFORM_OR_HMAC_DRIFT")
        for label in OS:
            blob=folder.joinpath(label+".zip")
            need(blob.is_file() and not blob.is_symlink()
                 and digest(blob.read_bytes()) ==
                    platforms[label]["outer_artifact_sha256"],
                 "COLD_CUSTODY_GITHUB_ARCHIVE_TAMPERED")
            manifest["sha256"][label]=digest(blob.read_bytes())
        need(folder.joinpath("manifest.json").read_bytes()==canonical(manifest)
             and digest(canonical(manifest))==
                    doc["evidence_manifest_sha256"],
             "COLD_CUSTODY_MANIFEST_TAMPERED")

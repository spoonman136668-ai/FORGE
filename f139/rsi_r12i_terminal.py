"""R12-I: one original-owner post-dispatch terminal ledger record.

It describes a completed GitHub job in the existing original SQLite chain;
it is NOT a cryptographic original-only signing witness or worker admission.
The original-source writer is inactive until a separately authorized owner
cutover, 3-lane policy, workflow and fresh eligible failure exist.
"""
from __future__ import annotations

import hashlib
import json

from f139.local_controller import canonical
from f139.rsi_r11_owner_once import (
    _authentic_original_owner, _source_at_event, audit_owner_once,
    KIND as RESERVED_KIND,
)
from f139.rsi_r12_candidate_binding import (
    binding_from_reservation_event, original_owner_database,
)
from f139.rsi_r12b_signed_job import REPO, WORKFLOW, sha40, sha64
from f139.rsi_r12c_original_spend import (
    owner_self_policy_allows,
    KIND as LEGACY_ISSUED_KIND,
)
from f139.rsi_r12g_pre_dispatch import (
    audit_preissued, validate_bundle,
    KIND as PREISSUED_KIND,
)

KIND = "RSI_SELF_ORIGINAL_TERMINAL"
SCHEMA = "forge.f139.rsi-r12i.original-terminal-once.v1"
RESULTS = ("success", "failure", "cancelled", "timed_out")
FIELDS = frozenset({
    "schema", "owner_source_sha", "protected_main_sha",
    "protected_main_tree_sha", "ticket", "runner_os",
    "reservation_seq", "reservation_event_sha256",
    "preissue_seq", "preissue_event_sha256",
    "preissue_intent_sha256", "candidate_sha256",
    "worker_run_id", "worker_job_id", "worker_run_attempt",
    "worker_run_conclusion", "worker_job_conclusion",
    "provider_run_snapshot_sha256", "provider_job_snapshot_sha256",
    "prior_event_head_sha256", "one_terminal_maximum",
    "retry_allowed", "development_only", "original_owner_logged",
    "original_only_public_signature_verified",
    "credentialed_worker_signature_verified",
    "credential_free_worker_admitted", "scientific_first_use",
    "source_promoted", "autonomous_rsi_proven",
})


class TerminalDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise TerminalDenied("F139_RSI_R12I_" + reason)


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def snapshot(*, intent: dict, run: dict, job: dict) -> tuple[dict, dict]:
    """Strict COMPLETED provider origin; historical aliases cannot replay."""
    need(type(intent) is dict and type(run) is dict and type(job) is dict,
         "PROVIDER_OBJECT_REQUIRED")
    run_id, job_id = run.get("id"), job.get("id")
    need(type(run_id) is int and type(job_id) is int
         and run_id > intent["failed_run_id"] and job_id > 0
         and run.get("run_attempt") == 1
         and run.get("status") == "completed"
         and run.get("conclusion") in RESULTS
         and run.get("event") == "workflow_dispatch"
         and run.get("head_sha") == intent["source_sha"]
         and run.get("head_branch") == "main"
         and run.get("name") == "F139 " + intent["ticket"]
         and run.get("path") == ".github/workflows/" + WORKFLOW
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == "spoonman136668-ai"
         and type(run.get("repository")) is dict
         and run["repository"].get("full_name") == REPO
         and type(run.get("head_repository")) is dict
         and run["head_repository"].get("full_name") == REPO,
         "ORIGINAL_GITHUB_RUN_TERMINAL_IDENTITY_DRIFT")
    need(job.get("id") == job_id
         and job.get("run_id") == run_id
         and job.get("head_sha") == intent["source_sha"]
         and job.get("name") ==
             "rsi-self-qualification (" + intent["runner_os"] + ")"
         and job.get("labels") == [intent["runner_os"]]
         and job.get("status") == "completed"
         and job.get("conclusion") in RESULTS,
         "ORIGINAL_GITHUB_JOB_TERMINAL_IDENTITY_DRIFT")
    # Full workflow and per-job conclusions may differ. Preserve both;
    # neither a success nor a failure grants admission or replay.
    r = {
        "id": run_id, "attempt": 1, "event": run["event"],
        "status": run["status"], "conclusion": run["conclusion"],
        "head_sha": run["head_sha"], "branch": run["head_branch"],
        "name": run["name"], "path": run["path"],
        "actor": run["actor"]["login"],
        "repository": REPO,
    }
    j = {
        "id": job_id, "run_id": run_id, "head_sha": job["head_sha"],
        "name": job["name"], "labels": [intent["runner_os"]],
        "status": job["status"], "conclusion": job["conclusion"],
    }
    return r, j


def payload(*, preissue: dict, preissue_row, binding: dict,
            run: dict, job: dict, prior_head: str) -> dict:
    """Pure frozen source-and-result identity, never trusted on its own."""
    need(type(preissue) is dict and type(binding) is dict
         and sha64(prior_head)
         and type(preissue_row["seq"]) is int
         and sha64(preissue_row["sha"]),
         "PREISSUE_OR_HEAD_SHAPE")
    intent = preissue["intent"]
    validate_bundle(intent, binding)
    need(preissue["intent_sha256"] == digest(intent)
         and preissue["reservation_seq"] == binding["reservation_seq"]
         and preissue["reservation_event_sha256"] ==
             binding["reservation_event_sha256"]
         and preissue["binding_sha256"] ==
             binding["candidate_binding_sha256"]
         and preissue["owner_source_sha"] == binding["owner_source_sha"]
         and preissue_row["seq"] > binding["reservation_seq"],
         "PREISSUE_PROVENANCE_DRIFT")
    r, j = snapshot(intent=intent, run=run, job=job)
    return {
        "schema": SCHEMA,
        "owner_source_sha": intent["owner_source_sha"],
        "protected_main_sha": intent["source_sha"],
        "protected_main_tree_sha": intent["source_tree_sha"],
        "ticket": intent["ticket"],
        "runner_os": intent["runner_os"],
        "reservation_seq": intent["reservation_seq"],
        "reservation_event_sha256": intent["reservation_event_sha256"],
        "preissue_seq": preissue_row["seq"],
        "preissue_event_sha256": preissue_row["sha"],
        "preissue_intent_sha256": preissue["intent_sha256"],
        "candidate_sha256": intent["candidate_sha256"],
        "worker_run_id": r["id"], "worker_job_id": j["id"],
        "worker_run_attempt": 1,
        "worker_run_conclusion": r["conclusion"],
        "worker_job_conclusion": j["conclusion"],
        "provider_run_snapshot_sha256": digest(r),
        "provider_job_snapshot_sha256": digest(j),
        "prior_event_head_sha256": prior_head,
        "one_terminal_maximum": 1,
        "retry_allowed": False,
        "development_only": True,
        "original_owner_logged": True,
        "original_only_public_signature_verified": False,
        "credentialed_worker_signature_verified": False,
        "credential_free_worker_admitted": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }


def validate_event(*, document: dict, event_row, preissue: dict,
                   preissue_row, binding: dict,
                   source_at_event: str) -> None:
    need(type(document) is dict and set(document) == FIELDS
         and document["schema"] == SCHEMA
         and document["owner_source_sha"] == source_at_event
         and document["owner_source_sha"] == preissue["owner_source_sha"]
         and document["protected_main_sha"] ==
             preissue["intent"]["source_sha"]
         and document["protected_main_tree_sha"] ==
             preissue["intent"]["source_tree_sha"]
         and document["ticket"] == preissue["intent"]["ticket"]
         and document["runner_os"] == preissue["intent"]["runner_os"]
         and document["reservation_seq"] == binding["reservation_seq"]
         and document["reservation_event_sha256"] ==
             binding["reservation_event_sha256"]
         and document["preissue_seq"] == preissue_row["seq"]
         and document["preissue_event_sha256"] == preissue_row["sha"]
         and document["preissue_intent_sha256"] ==
             preissue["intent_sha256"] == digest(preissue["intent"])
         and document["candidate_sha256"] ==
             preissue["intent"]["candidate_sha256"]
         and type(document["worker_run_id"]) is int
         and document["worker_run_id"] >
             preissue["intent"]["failed_run_id"]
         and type(document["worker_job_id"]) is int
         and document["worker_job_id"] > 0
         and document["worker_run_attempt"] == 1
         and document["worker_run_conclusion"] in RESULTS
         and document["worker_job_conclusion"] in RESULTS
         and sha64(document["provider_run_snapshot_sha256"])
         and sha64(document["provider_job_snapshot_sha256"])
         and type(event_row["seq"]) is int
         and event_row["seq"] > preissue_row["seq"]
         and document["prior_event_head_sha256"] == event_row["prior_sha"]
         and type(document["one_terminal_maximum"]) is int
         and document["one_terminal_maximum"] == 1
         and document["retry_allowed"] is False
         and document["development_only"] is True
         and document["original_owner_logged"] is True
         and all(document[k] is False for k in (
             "original_only_public_signature_verified",
             "credentialed_worker_signature_verified",
             "credential_free_worker_admitted", "scientific_first_use",
             "source_promoted", "autonomous_rsi_proven")),
         "ORIGINAL_TERMINAL_HISTORY_OR_PERMISSION_DRIFT")


def audit_terminal(db) -> tuple[dict, ...]:
    """Cold one-use original chain audit, non-authorizing even on PASS."""
    need(original_owner_database(db), "ORIGINAL_DATABASE_REQUIRED")
    rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (KIND,)))
    if not rows:
        return ()
    need(len(rows) == 1, "TERMINAL_REPLAY_OR_DUPLICATE")
    need(not db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=?",
        (LEGACY_ISSUED_KIND,)).fetchone()[0],
        "LEGACY_POSTDISPATCH_ISSUANCE_CONFLICT")
    preissued = audit_preissued(db)
    reservations = audit_owner_once(db)
    need(len(preissued) == 1 and len(reservations) == 1,
         "AUTHENTIC_ORIGINAL_PREISSUE_OR_RESERVATION_MISSING")
    pre_rows = list(db.conn.execute(
        "SELECT seq,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (PREISSUED_KIND,)))
    res_rows = list(db.conn.execute(
        "SELECT seq,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (RESERVED_KIND,)))
    need(len(pre_rows) == len(res_rows) == 1
         and json.loads(pre_rows[0]["payload"]) == preissued[0],
         "PREISSUE_COLD_ROW_DRIFT")
    binding = binding_from_reservation_event(
        reservation=reservations[0], row=res_rows[0],
        expected_owner_source_sha=reservations[0]["owner_source_sha"])
    all_rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    transitions = [json.loads(row["payload"]) for row in all_rows
                   if row["kind"] == "SOURCE_TRANSITION_ADMITTED"]
    first_source = (transitions[0]["from_source_sha"]
                    if transitions else db.meta()["source_sha"])
    seen = []
    for row, source in _source_at_event(all_rows, first_source):
        if row["kind"] == KIND:
            document = json.loads(row["payload"])
            validate_event(document=document, event_row=row,
                           preissue=preissued[0], preissue_row=pre_rows[0],
                           binding=binding, source_at_event=source)
            seen.append(document)
    need(len(seen) == 1, "TERMINAL_EVENT_NOT_COLD_AUDITED")
    return tuple(seen)


def record_original_terminal_once(*, db, provider, run_id: int,
                                  job_id: int) -> dict:
    """Inactive authentic Windows owner-only future terminal recorder.

    Provider GET only, one SQLite append. No HMAC/exported signing key,
    workflow dispatch, fresh source promotion, retry, scientific first-use,
    worker admission or accepted terminal authorization is performed.
    """
    from f139.local_controller import SingleOwner
    source = _authentic_original_owner(
        db, provider, allow_used_reservation=True)
    need(type(run_id) is int and type(job_id) is int
         and run_id > 0 and job_id > 0, "RUN_JOB_IDENTITY_REQUIRED")
    before = db.meta()
    need(not audit_terminal(db), "ONE_TERMINAL_ALREADY_SPENT")
    preissued = audit_preissued(db)
    reserved = audit_owner_once(db)
    need(len(preissued) == len(reserved) == 1
         and preissued[0]["owner_source_sha"] == source,
         "ORIGINAL_ONE_USE_PREISSUE_REQUIRED")
    original = db.conn.execute(
        "SELECT seq,payload,sha FROM events WHERE kind=?",
        (PREISSUED_KIND,)).fetchone()
    need(original is not None
         and json.loads(original["payload"]) == preissued[0],
         "ORIGINAL_PREISSUE_SOURCE_DRIFT")
    reservation_row = db.conn.execute(
        "SELECT seq,payload,prior_sha,sha FROM events WHERE kind=?",
        (RESERVED_KIND,)).fetchone()
    binding = binding_from_reservation_event(
        reservation=reserved[0], row=reservation_row,
        expected_owner_source_sha=source)
    base = "repos/" + REPO + "/"
    issue = provider.get(base + "issues/807")
    need(type(issue) is dict
         and issue.get("number") == 807
         and issue.get("state") == "open"
         and issue.get("author_association") == "OWNER"
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == "spoonman136668-ai"
         and "pull_request" not in issue
         and type(issue.get("body")) is str,
         "ORIGINAL_OPERATOR_POLICY_IDENTITY_DRIFT")
    try:
        policy = json.loads(issue["body"])
    except (ValueError, TypeError) as exc:
        raise TerminalDenied(
            "F139_RSI_R12I_OPERATOR_POLICY_INVALID") from exc
    need(owner_self_policy_allows(
        policy, original_source_sha=source),
        "ORIGINAL_FORGE_SELF_POLICY_NOT_ACTIVE")
    intent = preissued[0]["intent"]
    need(provider.protected_main() == intent["source_sha"],
         "PROTECTED_MAIN_DRIFT")
    commit = provider.get(base + "git/commits/" + intent["source_sha"])
    need(type(commit) is dict and commit.get("sha") == intent["source_sha"]
         and type(commit.get("tree")) is dict
         and commit["tree"].get("sha") == intent["source_tree_sha"],
         "PROTECTED_MAIN_TREE_DRIFT")
    run = provider.get(base + "actions/runs/" + str(run_id))
    job = provider.get(base + "actions/jobs/" + str(job_id))
    doc = payload(preissue=preissued[0], preissue_row=original,
                  binding=binding, run=run, job=job,
                  prior_head=before["head_hash"])
    with db.transaction():
        db.verify()
        now = db.meta()
        need(now["head_hash"] == before["head_hash"]
             and now["source_sha"] == source
             and now["enabled"] == 1
             and now["legacy_suspended"] == 1
             and not db.actives() and db.ready() is None
             and SingleOwner.held(db.filename.with_suffix(".lock"))
             and not audit_terminal(db),
             "ORIGINAL_OWNER_SOURCE_OR_ONCE_CUSTODY_CHANGED")
        db.event(KIND, doc)
        db.verify()
    # Result is NOT a transferable authorization receipt. It is only a
    # description of original SQLite custody, without a public signature.
    return {
        "schema": SCHEMA,
        "event_seq": db.meta()["head_seq"],
        "event_sha256": db.meta()["head_hash"],
        "ticket": doc["ticket"],
        "run_id": run_id,
        "job_id": job_id,
        "terminal_event_recorded": True,
        "independent_public_signature_verified": False,
        "credential_free_worker_admitted": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }

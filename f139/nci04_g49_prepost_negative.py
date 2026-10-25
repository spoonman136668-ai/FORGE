"""G49 bounded original V7 pre-POST negative custody for authentic issue #970.

A guard for a separate, owner-approved release, NOT a background controller.
Do not invoke on the original running task or replay its consumed issue.

This records an absence-of-POST original software failure; it is NOT a
fictional failed GitHub workflow/provider receipt. The original claim is never
cleared or retried. Activation and first-use authority are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

SOURCE_V7 = "72301da157c27fc6fa7d22edce6842c7e4b2a432"
ISSUE = 970
TICKET = "f139-nci04-i970-72301da157c2-8f3fcf69"
CLAIM_SEQ = 225
CLAIM_SHA = "daac64effe3c1422449e44b0250786d4cd1a0e24fc40d3e248743d59fcc01129"
REASON = "PREDISPATCH_SIGNER_DENIED"
KIND = "NATIVE_PREDISPATCH_NEGATIVE_CUSTODY"
SCHEMA = "forge.f139.v7-original-predispatch-negative.v1"
DEFECT = "F139_G36_ORIGINAL_DATABASE_REQUIRED"


class G49Denied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise G49Denied("F139_G49_" + reason)


def _events(db, kind: str, ticket: str) -> list:
    return [r for r in db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind=? ORDER BY seq",
        (kind,)) if json.loads(r["payload"]).get("ticket") == ticket]


def verify_g49_custody(db) -> bool:
    """Read-only cold verification of the exact one-time negative record."""
    rows = list(db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind=? ORDER BY seq",
        (KIND,)))
    need(len(rows) <= 1, "DUPLICATE_NEGATIVE_CUSTODY")
    if not rows:
        return False
    doc = json.loads(rows[0]["payload"])
    need(type(doc) is dict and set(doc) == {
        "schema", "ticket", "source_sha", "issue_number",
        "claim_seq", "claim_sha", "quarantine_seq", "quarantine_sha",
        "provider_result", "defect", "new_dispatches", "scientific_first_use"},
        "NEGATIVE_RECORD_FIELDS")
    need(doc == {
        "schema": SCHEMA, "ticket": TICKET, "source_sha": SOURCE_V7,
        "issue_number": ISSUE, "claim_seq": CLAIM_SEQ, "claim_sha": CLAIM_SHA,
        "quarantine_seq": CLAIM_SEQ + 1,
        "quarantine_sha": doc["quarantine_sha"],
        "provider_result": "ABSENT_AT_ORIGINAL_OWNER_PREPOST_BOUNDARY",
        "defect": DEFECT, "new_dispatches": 0, "scientific_first_use": False},
        "NEGATIVE_RECORD_IDENTITY_DRIFT")
    need(type(doc["quarantine_sha"]) is str and
         re.fullmatch(r"[a-f0-9]{64}", doc["quarantine_sha"]) is not None
         and rows[0]["seq"] == CLAIM_SEQ + 2, "NEGATIVE_EVENT_SEQUENCE")
    claim = db.conn.execute(
        "SELECT sha,kind,payload FROM events WHERE seq=?", (CLAIM_SEQ,)).fetchone()
    quarantine = db.conn.execute(
        "SELECT sha,kind,payload FROM events WHERE seq=?", (CLAIM_SEQ+1,)).fetchone()
    need(claim is not None and claim["sha"] == CLAIM_SHA
         and claim["kind"] == "BEFORE_DISPATCH_INTENT"
         and json.loads(claim["payload"]).get("ticket") == TICKET
         and quarantine is not None and
         quarantine["sha"] == doc["quarantine_sha"] and
         quarantine["kind"] == "ATTEMPT_QUARANTINED" and
         json.loads(quarantine["payload"]) == {
             "ticket": TICKET, "reason": REASON},
         "NEGATIVE_EVENT_CHAIN_DRIFT")
    task = db.conn.execute("SELECT * FROM tasks WHERE ticket=?",
                           (TICKET,)).fetchone()
    need(task is not None and task["source_sha"] == SOURCE_V7
         and task["stage"] == "QUARANTINED"
         and task["quarantine_reason"] == REASON
         and task["run_id"] is None and task["evidence_sha"] is None
         and not task["evidence_dir"], "NEGATIVE_TASK_CUSTODY_DRIFT")
    need(not _events(db, "DISPATCH_POST_RETURNED", TICKET),
         "NEGATIVE_PROVIDER_POST_EVENT_FORBIDDEN")
    return True


def settle_g49_original_prepost(db, api, *, owner_quiesced: bool) -> dict:
    """One owner-approved exact-head negative, under existing SingleOwner.

    Caller must prove the ORIGINAL task disabled and all original controller
    children stopped, original SID/task route, backed-up SQLite, immutable
    installed source, protected-main identity and exclusive owner mutex.
    No blind retries, independent queue, live broker, paid model API or science.
    """
    from f139.local_controller import (
        Database, GitHub, SingleOwner, native_original_owner_profile,
    )
    need(type(db) is Database and type(api) is GitHub,
         "CANONICAL_OWNER_ONLY")
    need(owner_quiesced is True and
         SingleOwner.held(Path(db.filename).with_suffix(".lock")),
         "EXCLUSIVE_QUIESCENT_OWNER_REQUIRED")
    need(native_original_owner_profile(Path(db.filename)),
         "ORIGINAL_TASK_PROFILE_NOT_QUALIFIED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == SOURCE_V7
         and meta["head_seq"] == CLAIM_SEQ
         and meta["head_hash"] == CLAIM_SHA
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1,
         "EXACT_V7_CLAIM_HEAD_REQUIRED")
    need(api.protected_main() == SOURCE_V7,
         "PROTECTED_MAIN_SOURCE_DRIFT")
    active = list(db.actives())
    need(len(active) == 1 and active[0]["ticket"] == TICKET
         and active[0]["stage"] == "START_RISK"
         and active[0]["source_sha"] == SOURCE_V7
         and active[0]["run_id"] is None
         and db.ready() is None, "CONSUMED_START_RISK_NOT_EXCLUSIVE")
    admitted = _events(db, "NATIVE_DEVELOPMENT_ADMITTED", TICKET)
    intake = _events(db, "TASK_INTAKE", TICKET)
    claim = _events(db, "BEFORE_DISPATCH_INTENT", TICKET)
    need(len(admitted) == len(intake) == len(claim) == 1
         and admitted[0]["seq"] == CLAIM_SEQ-2
         and intake[0]["seq"] == CLAIM_SEQ-1
         and claim[0]["seq"] == CLAIM_SEQ
         and claim[0]["sha"] == CLAIM_SHA
         and json.loads(admitted[0]["payload"])["issue_number"] == ISSUE,
         "EXACT_IMMUTABLE_NATIVE_ADMISSION_REQUIRED")
    need(not _events(db, "DISPATCH_POST_RETURNED", TICKET)
         and not _events(db, KIND, TICKET),
         "PREPOST_ALREADY_CONSUMED")
    # Use the EXISTING controller's exact API lookup, after quiescence.
    # A transient HTTP error fails closed rather than counting as absence.
    need(api.candidates(TICKET, active[0]["started_at"]) is None,
         "ORIGINAL_PROVIDER_ATTEMPT_EXISTS")
    # One final provider read, still with the sole original owner mutex held.
    need(api.candidates(TICKET, active[0]["started_at"]) is None,
         "PROVIDER_CHANGED_BEFORE_CUSTODY")
    with db.transaction():
        db.conn.execute(
            "UPDATE tasks SET stage='QUARANTINED', quarantine_reason=? "
            "WHERE ticket=? AND stage='START_RISK'",
            (REASON, TICKET))
        need(db.conn.execute("SELECT changes()").fetchone()[0] == 1,
             "ORIGINAL_TASK_MUTATION_RACE")
        db.event("ATTEMPT_QUARANTINED", {"ticket": TICKET, "reason": REASON})
        quarantine = db.conn.execute(
            "SELECT sha FROM events WHERE seq=?", (CLAIM_SEQ+1,)).fetchone()
        need(quarantine is not None, "QUARANTINE_EVENT_MISSING")
        db.event(KIND, {
            "schema": SCHEMA, "ticket": TICKET, "source_sha": SOURCE_V7,
            "issue_number": ISSUE, "claim_seq": CLAIM_SEQ,
            "claim_sha": CLAIM_SHA, "quarantine_seq": CLAIM_SEQ+1,
            "quarantine_sha": quarantine["sha"],
            "provider_result": "ABSENT_AT_ORIGINAL_OWNER_PREPOST_BOUNDARY",
            "defect": DEFECT, "new_dispatches": 0,
            "scientific_first_use": False})
        need(verify_g49_custody(db), "NEGATIVE_CUSTODY_NOT_VERIFIED")
        db.verify()
    return {"disposition": "EXACT_PREPOST_NEGATIVE_CUSTODIED_NO_REPLAY",
            "ticket": TICKET, "head_seq": db.meta()["head_seq"],
            "head_sha": db.meta()["head_hash"],
            "scientific_first_use": False}

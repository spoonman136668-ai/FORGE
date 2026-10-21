"""F139 NCI04-A6 native issue ledger, original SQLite authority only.

All operations use the same Database transaction, task table, owner mutex,
append-only SHA chain, START_RISK and provider reconciliation as F139 D2K.
No table reset or additional controller/queue. Existing non-native records
are unchanged. Production native admission is disabled until a separately
qualified owner source transition and explicit native activation.
"""
from __future__ import annotations

import base64
import json
import re

from f139.nci04_native_contract import digest, canonical, parse_intent
from f139.nci04_owner_issue import NativeIssue, inspect_owner_issue, SCHEMA as ISSUE_SCHEMA

ADMISSION_SCHEMA = "forge.f139.nci04.owner-native-ledger.v1"
KIND = "NATIVE_DEVELOPMENT_ADMITTED"
MAX_DAILY = 2
MAX_TOTAL = 20
SEALED_OWNER_PREFIX_HEAD = "eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87"
FIELDS = frozenset({
    "schema", "ticket", "issue_number", "issue_id", "lane",
    "source_sha", "issue_body_sha256", "native_intent_sha256",
    "qualification_key", "native_target_commit", "native_target_tree",
    "native_path", "before_sha256", "after_sha256",
    "native_intent_base64", "prior_event_head_sha256",
    "admitted_day", "manifest_sha256", "scientific_first_use",
})
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class NativeLedgerDenied(ValueError):
    pass


def require(v: bool, why: str):
    if not v:
        raise NativeLedgerDenied("F139_NCI04_A6_" + why)


def native_events(db):
    return [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq", (KIND,))]


def verified_historical_foundation(db):
    meta = db.meta()
    verified = list(db.conn.execute(
        "SELECT ticket,stage,run_id,evidence_sha FROM tasks "
        "WHERE ticket LIKE 'f139-d2c-%' OR ticket LIKE 'f139-d2j-%'"))
    seal = db.conn.execute("SELECT sha FROM events WHERE seq=23").fetchone()
    require(seal is not None
            and seal["sha"] == SEALED_OWNER_PREFIX_HEAD,
            "ORIGINAL_23_EVENT_PIN_DRIFT")
    # Real authenticated first-use-safe D2K receipt transitions, not just
    # artificially constructed task records with a matching high-water.
    for number, runid in ((687, 39513293606), (688, 39513381790)):
        row = db.conn.execute(
            "SELECT stage,run_id,evidence_sha FROM tasks "
            "WHERE ticket LIKE ?", ("f139-d2k-i" + str(number) + "-%",)).fetchall()
        require(len(row) == 1 and row[0]["stage"] == "VERIFIED"
                and row[0]["run_id"] == runid
                and isinstance(row[0]["evidence_sha"], str)
                and SHA64.fullmatch(row[0]["evidence_sha"]) is not None,
                "D2K_LOCAL_CUSTODY_NOT_VERIFIED")
    require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
            and meta["head_seq"] >= 40
            and len(verified) == 4
            and sum(r["ticket"].startswith("f139-d2c-") for r in verified) == 2
            and sum(r["ticket"].startswith("f139-d2j-") for r in verified) == 2
            and all(r["stage"] == "VERIFIED" and type(r["run_id"]) is int
                    and isinstance(r["evidence_sha"], str)
                    and SHA64.fullmatch(r["evidence_sha"]) is not None
                    for r in verified), "ORIGINAL_HISTORY_NOT_QUALIFIED")


def frozen_issue_record(issue: NativeIssue, prior_head: str, day: str) -> dict:
    return {
        "schema": ADMISSION_SCHEMA,
        "ticket": issue.ticket, "issue_number": issue.number,
        "issue_id": issue.issue_id, "lane": issue.lane,
        "source_sha": issue.source_sha,
        "issue_body_sha256": issue.issue_body_sha256,
        "native_intent_sha256": issue.native_intent_sha256,
        "qualification_key": issue.qualification_key,
        "native_target_commit": issue.candidate.target_commit,
        "native_target_tree": issue.candidate.target_tree_sha,
        "native_path": issue.candidate.path,
        "before_sha256": issue.candidate.before_sha256,
        "after_sha256": issue.candidate.after_sha256,
        "native_intent_base64": base64.b64encode(issue.intent_raw).decode("ascii"),
        "prior_event_head_sha256": prior_head, "admitted_day": day,
        "scientific_first_use": False,
    }


def verify_admission(db, event: dict, prior_sha: str):
    require(isinstance(event, dict) and set(event) == FIELDS,
            "ADMISSION_FIELDS")
    require(event["schema"] == ADMISSION_SCHEMA
            and event["prior_event_head_sha256"] == prior_sha
            and event["scientific_first_use"] is False
            and isinstance(event["admitted_day"], str)
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["admitted_day"])
            and type(event["issue_number"]) is int and event["issue_number"] > 0
            and type(event["issue_id"]) is int and event["issue_id"] > 0,
            "ADMISSION_AUTHORITY")
    encoding = event["native_intent_base64"]
    require(isinstance(encoding, str) and len(encoding) < 59000,
            "INTENT_OVERSIZE")
    try:
        raw = base64.b64decode(encoding, validate=True)
        require(base64.b64encode(raw).decode("ascii") == encoding,
                "INTENT_NONCANONICAL")
        candidate = parse_intent(
            raw, protected_main=event["source_sha"],
            target_commit=event["native_target_commit"],
            target_tree_sha=event["native_target_tree"])
    except (ValueError, UnicodeError) as exc:
        raise NativeLedgerDenied("F139_NCI04_A6_INTENT_CORRUPT") from exc
    require(candidate.lane == event["lane"]
            and candidate.path == event["native_path"]
            and candidate.before_sha256 == event["before_sha256"]
            and candidate.after_sha256 == event["after_sha256"]
            and candidate.intent_sha256 == event["native_intent_sha256"]
            and candidate.qualification_key == event["qualification_key"]
            and event["ticket"] == "f139-nci04-i" + str(event["issue_number"]) +
                "-" + event["source_sha"][:12] + "-" + candidate.intent_sha256[:8],
            "INTENT_EVENT_IDENTITY_DRIFT")
    fragment = {k: v for k, v in event.items() if k != "manifest_sha256"}
    require(digest(canonical(fragment)) == event["manifest_sha256"],
            "MANIFEST_TAMPERED")
    row = db.conn.execute(
        "SELECT lane,source_sha,manifest_sha FROM tasks WHERE ticket=?",
        (event["ticket"],)).fetchone()
    require(row is not None and row["lane"] == event["lane"]
            and row["source_sha"] == event["source_sha"]
            and row["manifest_sha"] == event["manifest_sha256"],
            "TASK_ADMISSION_MISMATCH")
    return candidate


def audit_native_events(db):
    """Called by the existing Database.verify within its SHA-chain walk.

    Also rejects duplicate issue identity and preserving once-only intent
    after a previous negative attempt, even across source transitions.
    """
    seen_numbers, seen_ids, seen_tickets = set(), set(), set()
    for row in db.conn.execute(
            "SELECT kind,payload,prior_sha FROM events ORDER BY seq"):
        if row["kind"] == KIND:
            event = json.loads(row["payload"])
            verify_admission(db, event, row["prior_sha"])
            require(event["issue_number"] not in seen_numbers
                    and event["issue_id"] not in seen_ids
                    and event["ticket"] not in seen_tickets,
                    "DUPLICATE_NATIVE_ISSUE")
            seen_numbers.add(event["issue_number"])
            seen_ids.add(event["issue_id"])
            seen_tickets.add(event["ticket"])
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind='DEVELOPMENT_WORK_ADMITTED'"):
        ev = json.loads(row["payload"])
        require(ev["issue_number"] not in seen_numbers
                and ev["issue_id"] not in seen_ids,
                "D2K_NATIVE_ISSUE_REUSE")
    verify_native_activation(db)
    # A8B is additive: old 47 events retain their exact original hashes.
    # A custodied failed native original is checked again on every cold read,
    # not merely trusted because a prior SQL event claimed success.
    from f139.nci04_negative_owner_store import verify_original_negative_custody
    verify_original_negative_custody(db)


def admit_native_issue(db, issue: NativeIssue, now: str) -> bool:
    """Must be called only while the original SingleOwner mutex is held.

    Atomic SQLite transaction prevents re-admission after process crash.
    Production dispatch is blocked in run_once unless native_enabled is true,
    and native_enabled is NOT reachable through the original CLI.
    """
    require(isinstance(issue, NativeIssue), "ISSUE_UNTRUSTED")
    db.verify()
    verified_historical_foundation(db)
    meta = db.meta()
    require(issue.source_sha == meta["source_sha"]
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", now[:10])
            and len(issue.intent_raw) <= 44000,
            "SOURCE_OR_DAY_DRIFT")
    with db.transaction():
        db.verify()
        rows = native_events(db)
        require(len(rows) < MAX_TOTAL, "NATIVE_WORK_TOTAL_LIMIT")
        require(sum(x["admitted_day"] == now[:10] for x in rows) < MAX_DAILY,
                "NATIVE_DAILY_BUDGET")
        # Strict ticket, issue ID and number nonreplay even if previous
        # attempt was QUARANTINED or the protected source later transitioned.
        d2k = [json.loads(r["payload"]) for r in db.conn.execute(
            "SELECT payload FROM events WHERE kind='DEVELOPMENT_WORK_ADMITTED'")]
        if any(x["ticket"] == issue.ticket or x["issue_number"] == issue.number
               or x["issue_id"] == issue.issue_id for x in rows + d2k):
            return False
        require(db.active() is None and db.ready() is None,
                "OTHER_WORK_PENDING")
        intent = frozen_issue_record(issue, meta["head_hash"], now[:10])
        manifest_sha = digest(canonical(intent))
        db.event(KIND, {**intent, "manifest_sha256": manifest_sha})
        db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,'READY',?)",
            (issue.ticket, issue.lane, issue.source_sha, manifest_sha))
        db.event("TASK_INTAKE", {
            "ticket":issue.ticket, "lane":issue.lane, "manifest_sha":manifest_sha,
        })
        db.verify()
        return True



ACTIVATION_KIND = "NATIVE_DEVELOPMENT_ACTIVATED"
ACTIVATION_SCHEMA = "forge.f139.nci04.owner-native-activation.v1"
ACTIVATION_FIELDS = frozenset({
    "schema", "source_sha", "prior_event_head_sha256",
    "sealed_original_prefix_sha256", "verified_original_tasks",
    "verified_d2k_tasks", "new_dispatches",
    "scientific_first_use", "development_only",
})
APPROVAL_FIELDS = frozenset({
    "schema", "source_sha", "expected_event_head_sha256",
    "native_development_approved", "scientific_first_use",
    "create_controller", "paid_api_calls",
})
APPROVAL_SCHEMA = "forge.f139.nci04.owner-native-approval.v1"


def verify_native_activation(db):
    """Verify every existing owner activation while selecting current source.

    One native activation is allowed per strictly new source authority. Older
    activation records must remain byte-for-byte intact and can never activate
    a later source. Exact original v1 events and their SHA-chain are preserved.
    """
    rows = list(db.conn.execute(
        "SELECT seq,payload,prior_sha FROM events WHERE kind=? ORDER BY seq",
        (ACTIVATION_KIND,)))
    require(len(rows) <= 10, "ACTIVATION_COUNT_LIMIT")
    seen = set()
    last_source = None
    for row in rows:
        doc = json.loads(row["payload"])
        require(isinstance(doc,dict) and set(doc)==ACTIVATION_FIELDS
                and doc["schema"]==ACTIVATION_SCHEMA
                and doc["prior_event_head_sha256"]==row["prior_sha"]
                and doc["sealed_original_prefix_sha256"]==
                    SEALED_OWNER_PREFIX_HEAD
                and type(doc["verified_original_tasks"]) is int
                and doc["verified_original_tasks"]==4
                and type(doc["verified_d2k_tasks"]) is int
                and doc["verified_d2k_tasks"]==2
                and type(doc["new_dispatches"]) is int
                and doc["new_dispatches"]==0
                and doc["scientific_first_use"] is False
                and doc["development_only"] is True
                and isinstance(doc["source_sha"],str)
                and re.fullmatch(r"[a-f0-9]{40}",doc["source_sha"]),
                "NATIVE_ACTIVATION_AUTHORITY_DRIFT")
        # Establish effective original-source authority at each *historical*
        # activation sequence, not using today's protected source retroactively.
        transitions = [
            json.loads(t["payload"]) for t in db.conn.execute(
                "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'"
                " AND seq < ? ORDER BY seq", (row["seq"],))]
        origin=db.conn.execute(
            "SELECT source_sha FROM tasks WHERE ticket LIKE 'f139-d2c-%'"
            " ORDER BY ticket LIMIT 1").fetchone()
        source_at_activation=(
            transitions[-1]["to_source_sha"] if transitions else
            (origin["source_sha"] if origin else db.meta()["source_sha"]))
        require(doc["source_sha"] == source_at_activation
                and doc["source_sha"] not in seen,
                "NATIVE_ACTIVATION_SOURCE_REPLAY")
        seen.add(doc["source_sha"])
        last_source = doc["source_sha"]
    return bool(rows) and last_source == db.meta()["source_sha"]


def activate_native(db, approval: dict) -> bool:
    """Owner-only, explicit per-source activation; never autonomous approval."""
    require(isinstance(approval, dict) and set(approval) == APPROVAL_FIELDS
            and approval["schema"] == APPROVAL_SCHEMA
            and approval["native_development_approved"] is True
            and approval["scientific_first_use"] is False
            and approval["create_controller"] is False
            and type(approval["paid_api_calls"]) is int
            and approval["paid_api_calls"] == 0,
            "NATIVE_OWNER_APPROVAL_NOT_QUALIFIED")
    db.verify()
    verified_historical_foundation(db)
    with db.transaction():
        db.verify()
        meta=db.meta()
        require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
                and approval["source_sha"] == meta["source_sha"]
                and approval["expected_event_head_sha256"] == meta["head_hash"]
                and re.fullmatch(r"[a-f0-9]{64}",
                                 approval["expected_event_head_sha256"]),
                "APPROVAL_LEDGER_OR_SOURCE_DRIFT")
        require(db.active() is None and db.ready() is None,
                "PREEXISTING_PENDING_WORK")
        activations=[
            json.loads(row["payload"]) for row in db.conn.execute(
                "SELECT payload FROM events WHERE kind=? ORDER BY seq",
                (ACTIVATION_KIND,))]
        require(len(activations) < 10
                and all(a["source_sha"] != meta["source_sha"]
                        for a in activations),
                "NATIVE_ALREADY_ACTIVATED")
        failures=[
            r for r in db.conn.execute("SELECT ticket,stage FROM tasks")
            if r["stage"] != "VERIFIED"]
        if failures:
            from f139.nci04_negative_owner_store import (
                verify_original_negative_custody, TICKET as NEGATIVE_TICKET)
            require(len(failures)==1 and failures[0]["stage"]=="QUARANTINED"
                    and failures[0]["ticket"]==NEGATIVE_TICKET
                    and verify_original_negative_custody(db)
                    and any(
                        json.loads(row["payload"]).get("schema")==
                        "forge.f139.source-transition.v2"
                        for row in db.conn.execute(
                            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'")),
                    "UNVERIFIED_HISTORICAL_TASK")
        prior=meta["head_hash"]
        db.event(ACTIVATION_KIND,{
            "schema":ACTIVATION_SCHEMA,"source_sha":meta["source_sha"],
            "prior_event_head_sha256":prior,
            "sealed_original_prefix_sha256":SEALED_OWNER_PREFIX_HEAD,
            "verified_original_tasks":4,"verified_d2k_tasks":2,
            "new_dispatches":0,"scientific_first_use":False,
            "development_only":True,
        })
        db.verify()
        return True


def frozen_native_issue(db, ticket: str):
    """Reconstruct native issue only from immutable append-only ledger."""
    records = [x for x in native_events(db) if x["ticket"] == ticket]
    require(len(records) == 1, "NATIVE_ISSUE_NOT_FROZEN")
    event = records[0]
    candidate = parse_intent(
        base64.b64decode(event["native_intent_base64"], validate=True),
        protected_main=event["source_sha"],
        target_commit=event["native_target_commit"],
        target_tree_sha=event["native_target_tree"])
    return NativeIssue(
        number=event["issue_number"], issue_id=event["issue_id"],
        ticket=ticket, lane=event["lane"], source_sha=event["source_sha"],
        issue_body_sha256=event["issue_body_sha256"],
        native_intent_sha256=event["native_intent_sha256"],
        qualification_key=event["qualification_key"],
        intent_raw=base64.b64decode(event["native_intent_base64"], validate=True),
        candidate=candidate)

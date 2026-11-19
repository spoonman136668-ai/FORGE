"""Frozen, development-only exclusion snapshot for F139 fresh-epoch staging.

This is a READ-ONLY reduction of the fully authenticated original owner ledger.
It is NOT an activation grant, task handoff, issue authentication, or proof
that a remotely ambiguous write completed. The original SQLite and provider
artifact custody remain authoritative for all old work.

A future fresh owner MUST separately reauthenticate the sealed history, the
GitHub issue-catalog high-water mark at its actual cutover, its sole Windows
task/process/mutex and exact released source before any native admission.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_autonomy_feed import (
    candidate_identity, candidate_identity_from_intent_base64,
)
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)

SCHEMA = "forge.f139.fresh-development-consumed-exclusions.v1"
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class FreshExclusionsDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise FreshExclusionsDenied("F139_FRESH_EXCLUSIONS_" + code)


def derive_exclusions(*, source_sha: str, head_seq: int, head_hash: str,
                      events: list, tasks: list) -> dict:
    """Build conservative exclusions from previously authenticated rows.

    Pure reduction for synthetic negative tests. A caller may NOT treat
    arbitrary rows as authentic; freeze_original_exclusions authenticates
    the exact original event1864 before invoking this function.
    """
    need(source_sha == SOURCE and type(head_seq) is int
         and head_seq == HEAD_SEQ and head_hash == HEAD_SHA256
         and type(events) is list and type(tasks) is list
         and len(events) == head_seq,
         "ORIGINAL_HEAD_OR_INPUT_DRIFT")
    issue_numbers, issue_ids, tickets = set(), set(), set()
    candidate_ids, after_hashes, publication_ids = set(), set(), set()
    native_count = model_attempt_count = ambiguous_count = 0
    kinds = {}
    for row in tasks:
        need(type(row) is str and 0 < len(row) <= 250,
             "TASK_IDENTITY_INVALID")
        need(row not in tickets, "DUPLICATE_ORIGINAL_TASK")
        tickets.add(row)
    for row in events:
        need(type(row) is dict
             and set(row) == {"kind", "payload"}
             and type(row["kind"]) is str and len(row["kind"]) > 0
             and type(row["payload"]) is dict,
             "EVENT_SHAPE_INVALID")
        kind, doc = row["kind"], row["payload"]
        kinds[kind] = kinds.get(kind, 0) + 1
        number = doc.get("issue_number")
        if number is not None:
            need(type(number) is int and number > 0, "ISSUE_NUMBER_INVALID")
            issue_numbers.add(number)
        issue_id = doc.get("issue_id")
        if issue_id is not None:
            need(type(issue_id) is int and issue_id > 0, "ISSUE_ID_INVALID")
            issue_ids.add(issue_id)
        ticket = doc.get("ticket")
        if ticket is not None:
            need(type(ticket) is str and 0 < len(ticket) <= 250,
                 "EVENT_TICKET_INVALID")
            tickets.add(ticket)
        raw_after = doc.get("source_after_sha256")
        if raw_after is None:
            raw_after = doc.get("after_sha256")
        if raw_after is not None:
            need(type(raw_after) is str and SHA64.fullmatch(raw_after) is not None,
                 "AFTER_HASH_INVALID")
            after_hashes.add(raw_after)
        if kind == "NATIVE_DEVELOPMENT_ADMITTED":
            native_count += 1
            lane = doc.get("lane")
            need(lane in ("Wingless", "Yggdrasil", "TTT-Hybrid")
                 and type(doc.get("native_target_commit")) is str
                 and type(doc.get("native_path")) is str
                 and type(doc.get("after_sha256")) is str
                 and type(doc.get("native_intent_base64")) is str
                 and type(doc.get("issue_number")) is int
                 and type(doc.get("issue_id")) is int,
                 "NATIVE_ADMISSION_IDENTITY_INCOMPLETE")
            semantic = candidate_identity(
                lane, doc["native_target_commit"],
                doc["native_path"], doc["after_sha256"])
            need(candidate_identity_from_intent_base64(
                doc["native_intent_base64"]) == semantic,
                "NATIVE_INTENT_SEMANTIC_DRIFT")
            candidate_ids.add(semantic)
        if kind == "MODEL_DRAFT_ATTEMPTED":
            model_attempt_count += 1
            key = doc.get("candidate_identity")
            need(type(key) is str and SHA64.fullmatch(key) is not None
                 and raw_after is not None,
                 "MODEL_ATTEMPT_IDENTITY_INCOMPLETE")
            publication_ids.add(key)
        if kind in ("G3_DRAFT_ATTEMPTED", "FREE_REASONER_ATTEMPTED"):
            # These authenticated historical effects are retained by the
            # original cold archive. They cannot be declared unspent from
            # an empty fresh DB, even if a semantic after-hash is unavailable.
            ambiguous_count += 1
    need(native_count == kinds.get("NATIVE_DEVELOPMENT_ADMITTED", 0)
         and model_attempt_count == kinds.get("MODEL_DRAFT_ATTEMPTED", 0),
         "HISTORICAL_COUNTS_DRIFT")
    return {
        "schema": SCHEMA,
        "source_sha": source_sha,
        "original_head_seq": head_seq,
        "original_head_sha256": head_hash,
        "original_event_count": len(events),
        "original_task_count": len(tasks),
        "native_admission_count": native_count,
        "model_draft_attempt_count": model_attempt_count,
        "other_historical_remote_attempt_count": ambiguous_count,
        "old_issue_numbers": sorted(issue_numbers),
        "old_issue_ids": sorted(issue_ids),
        "old_tickets": sorted(tickets),
        "old_native_candidate_identities": sorted(candidate_ids),
        "old_source_after_sha256": sorted(after_hashes),
        "old_model_candidate_identities": sorted(publication_ids),
        "release_qualified": False,
        "fresh_activation_authorized": False,
        "previous_work_replay_authorized": False,
        "scientific_first_use": False,
        "new_controller": False,
        "paid_model_calls": 0,
        "owner_task_mutations": 0,
        "remote_issue_high_water_verified": False,
    }


def freeze_original_exclusions(original: Database) -> dict:
    """Freeze identities while holding the *original* kernel mutex."""
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.conn.total_changes == 0
         and SingleOwner.held(original.filename.with_suffix(".lock")) is True,
         "READONLY_ORIGINAL_MUTEX_REQUIRED")
    original.verify()
    before = audit_frozen_original_readonly(original)
    meta = original.meta()
    need(before.get("source_sha") == SOURCE
         and before.get("head_seq") == HEAD_SEQ
         and before.get("head_sha256") == HEAD_SHA256
         and meta["source_sha"] == SOURCE
         and meta["head_seq"] == HEAD_SEQ
         and meta["head_hash"] == HEAD_SHA256,
         "VERIFIED_ORIGINAL_PREIMAGE_DRIFT")
    events = []
    for row in original.conn.execute(
            "SELECT kind,payload FROM events ORDER BY seq"):
        try:
            doc = json.loads(row["payload"])
        except (ValueError, UnicodeError, TypeError) as exc:
            raise FreshExclusionsDenied(
                "F139_FRESH_EXCLUSIONS_EVENT_DECODING_INVALID") from exc
        events.append({"kind": row["kind"], "payload": doc})
    tasks = [row["ticket"] for row in original.conn.execute(
        "SELECT ticket FROM tasks ORDER BY ticket")]
    history = derive_exclusions(
        source_sha=meta["source_sha"], head_seq=meta["head_seq"],
        head_hash=meta["head_hash"], events=events, tasks=tasks)
    need(original.conn.total_changes == 0
         and audit_frozen_original_readonly(original) == before,
         "ORIGINAL_CHANGED_DURING_EXCLUSION_FREEZE")
    return history


def candidate_violates_frozen_exclusions(history: dict, *,
                                         issue_number: int, issue_id: int,
                                         ticket: str, lane: str,
                                         target_commit: str, path: str,
                                         after_sha256: str,
                                         authenticated_remote_issue_floor: int | None) -> bool:
    """Only a conservative rejection predicate, NEVER positive admission.

    No caller can claim that the GitHub issue high-water value is independently
    authenticated merely by passing a number. Missing floor FAILS CLOSED.
    Independent owner authority/remote readback is still required.
    """
    need(type(history) is dict and history.get("schema") == SCHEMA
         and history.get("source_sha") == SOURCE
         and history.get("original_head_seq") == HEAD_SEQ
         and history.get("original_head_sha256") == HEAD_SHA256
         and history.get("release_qualified") is False
         and history.get("fresh_activation_authorized") is False,
         "FROZEN_HISTORY_INVALID")
    need(type(issue_number) is int and issue_number > 0
         and type(issue_id) is int and issue_id > 0
         and type(ticket) is str and bool(ticket),
         "NEW_ISSUE_IDENTITY_INVALID")
    if (type(authenticated_remote_issue_floor) is not int
            or authenticated_remote_issue_floor < max(
                history["old_issue_numbers"], default=0)):
        return True
    semantic = candidate_identity(lane, target_commit, path, after_sha256)
    return (issue_number <= authenticated_remote_issue_floor
            or issue_number in history["old_issue_numbers"]
            or issue_id in history["old_issue_ids"]
            or ticket in history["old_tickets"]
            or semantic in history["old_native_candidate_identities"]
            or after_sha256 in history["old_source_after_sha256"])

"""Read-only V41 predecessor verification for the original V40 F139 owner.

This module never cuts over an owner, dispatches workers, appends events,
creates release refs, updates policy, or authorizes scientific first-use.
The caller must independently own the genuine Windows kernel mutex, supply
an authenticated GET-only GitHub reader, and separately verify task/SID.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_release_pin_continuity import prove_deployed_release_pin
from f139.nci04_v40_source_transition import verify_additional_publication_readback

REPO = "spoonman136668-ai/FORGE"
FROM = "2c7caad5a4502d4b874a11d57207a35cf033eb08"
PREDECESSOR = "42c70d74dd93ef90d0f4618fefefe2206b81eafe"
QUALIFIED_REPAIR_MERGE = "7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595"
FIRST_OBSERVED_SEQ = 1826
FIRST_OBSERVED_SHA256 = "71fd4554315093d74f5a9968b4766191413cfd18d6b1ce81863f8451d379d769"
MIN_VERIFIED = 153
MIN_QUARANTINED = 56
REPAIR_BLOBS = {
    "f139/local_controller.py": "5e050403726a7eebf3bcd46b949a1735c929a79c",
    "f139/test_nci04_native_successor_catalog.py": "04e8f19889d58cde67c8394daab32da630d15ff3",
}
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")


class RecoveryPreflightDenied(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise RecoveryPreflightDenied("F139_V41_READONLY_" + reason)


def verify_qualified_repair(get: Callable[[str], object], target: str) -> None:
    """Read only original owner Git metadata, including a final moving-ref veto."""
    need(callable(get) and type(target) is str and _SHA40.fullmatch(target) is not None
         and target != FROM, "TARGET_INVALID")
    first = get("repos/" + REPO + "/branches/main")
    need(type(first) is dict and first.get("protected") is True
         and type(first.get("commit")) is dict
         and first["commit"].get("sha") == target, "PROTECTED_MAIN_DRIFT")
    if target != QUALIFIED_REPAIR_MERGE:
        compare = get("repos/" + REPO + "/compare/" +
                      QUALIFIED_REPAIR_MERGE + "..." + target +
                      "?per_page=1&page=2")
        need(type(compare) is dict and compare.get("status") == "ahead"
             and type(compare.get("ahead_by")) is int and compare["ahead_by"] >= 1
             and compare.get("behind_by") == 0
             and type(compare.get("merge_base_commit")) is dict
             and compare["merge_base_commit"].get("sha") == QUALIFIED_REPAIR_MERGE,
             "QUALIFIED_REPAIR_ANCESTRY_DRIFT")
    for path, blob in REPAIR_BLOBS.items():
        found = get("repos/" + REPO + "/contents/" + path + "?ref=" + target)
        need(type(found) is dict and found.get("type") == "file"
             and found.get("sha") == blob, "REPAIR_SOURCE_BLOB_DRIFT")
    last = get("repos/" + REPO + "/branches/main")
    need(last == first, "PROTECTED_MAIN_MOVED")


def inspect_original(db: Database, get: Callable[[str], object], *,
                     target: str) -> dict:
    """Require a real read-only original DB under its existing external mutex.

    The frozen 1826 event is a historical ancestor, *not* a stale required
    latest head. Any newer head is read afresh while holding the owner lock.
    This does NOT verify the task, cold backup, approval, or release eligibility.
    """
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_READONLY_MUTEX_REQUIRED")
    db.verify()
    before = db.meta()
    need(before["source_sha"] == FROM
         and before["enabled"] == 1 and before["legacy_suspended"] == 1
         and type(before["head_seq"]) is int
         and before["head_seq"] >= FIRST_OBSERVED_SEQ
         and db.ready() is None and not db.actives()
         and verify_native_activation(db),
         "ORIGINAL_IDLE_SOURCE_OR_ACTIVATION_DRIFT")
    anchor = db.conn.execute(
        "SELECT sha FROM events WHERE seq=?", (FIRST_OBSERVED_SEQ,)).fetchone()
    need(anchor is not None and anchor[0] == FIRST_OBSERVED_SHA256,
         "OBSERVED_HISTORY_ANCHOR_DRIFT")
    transitions = db.conn.execute(
        "SELECT seq,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq").fetchall()
    need(bool(transitions), "ORIGINAL_V40_TRANSITION_MISSING")
    try:
        docs = [json.loads(row["payload"]) for row in transitions]
    except (ValueError, TypeError) as exc:
        raise RecoveryPreflightDenied("F139_V41_READONLY_SOURCE_EVENT_INVALID") from exc
    need(all(type(doc) is dict for doc in docs)
         and sum(doc.get("schema") == "forge.f139.source-transition.v35"
                 for doc in docs) == 1,
         "UNIQUE_V40_SOURCE_SEAL_REQUIRED")
    final = docs[-1]
    seal = transitions[-1]
    need(final.get("schema") == "forge.f139.source-transition.v35"
         and final.get("from_source_sha") == PREDECESSOR
         and final.get("to_source_sha") == FROM
         and type(final.get("original_head_seq")) is int
         and seal["seq"] == final["original_head_seq"] + 1
         and seal["seq"] <= FIRST_OBSERVED_SEQ
         and type(seal["sha"]) is str
         and re.fullmatch(r"[0-9a-f]{64}", seal["sha"]) is not None,
         "CURRENT_V40_SOURCE_SEAL_DRIFT")
    grouped = db.conn.execute(
        "SELECT stage,COUNT(*) FROM tasks GROUP BY stage").fetchall()
    need(all(type(r[0]) is str and type(r[1]) is int for r in grouped),
         "TASK_CENSUS_INVALID")
    counts = {r[0]: r[1] for r in grouped}
    need(set(counts).issubset({"VERIFIED", "QUARANTINED"})
         and counts.get("VERIFIED", 0) >= MIN_VERIFIED
         and counts.get("QUARANTINED", 0) >= MIN_QUARANTINED
         and sum(counts.values()) >= MIN_VERIFIED + MIN_QUARANTINED,
         "HISTORICAL_TERMINALS_OR_PENDING_WORK_DRIFT")
    prove_deployed_release_pin(get, deployed_source=FROM, protected_source=target)
    verify_qualified_repair(get, target)
    # A previously spent ref-only publication negative must be preserved
    # and authenticated with original history plus fresh read-only Git data.
    verify_additional_publication_readback(db, get)
    after = db.meta()
    need(after == before, "LEDGER_HEAD_MOVED")
    return {
        "schema": "forge.f139.v41.original-owner-readonly-preflight.v1",
        "installed_source_sha": FROM,
        "protected_target_sha": target,
        "head_seq": before["head_seq"],
        "head_sha256": before["head_hash"],
        "observed_history_anchor_seq": FIRST_OBSERVED_SEQ,
        "v40_transition_sha256": seal["sha"],
        "terminal_verified": counts.get("VERIFIED", 0),
        "terminal_quarantined": counts.get("QUARANTINED", 0),
        "active_ready_or_uncertain": 0,
        "owner_task_sid_and_binary_acceptance": "NOT_CHECKED",
        "cold_backup_and_owner_approval": "NOT_CHECKED",
        "original_owner_mutations": 0,
        "new_dispatches": 0,
        "source_transition_authorized": False,
        "scientific_first_use": False,
    }

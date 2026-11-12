"""V41 pre-cutover custody for one never-admitted V40 native proposal.

This is a source-only, read-only precursor to a NEW qualified V41 handoff.
It cannot pause/upgrade an owner, rewrite an issue, authorize a reissue,
append a transition, or dispatch. Every old proposal remains intact until
a separately owner-approved, crash-safe transition is implemented.
"""
from __future__ import annotations

import json
import re

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import NativeIssue
from f139.nci04_owner_ledger import native_events

FROM_V40 = "2c7caad5a4502d4b874a11d57207a35cf033eb08"
PENDING_NUMBER = 1715
# Authenticated live original readback at 2026-11-12 08:24 UTC.
# Never accept a newly initialized or counter-reset database as genuine V40.
MIN_ORIGINAL_HEAD = 1826
MIN_VERIFIED = 153
MIN_QUARANTINED = 56
SCHEMA = "forge.f139.v41.unadmitted-proposal-custody.v1"
REISSUE_SCHEMA = "forge.f139.v41.reissue-comparison.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
FROZEN_KEYS = frozenset({
    "schema", "source_sha", "original_head_seq", "original_head_sha256",
    "issue_number", "issue_id", "ticket", "issue_body_sha256",
    "native_intent_sha256", "target_commit", "target_tree_sha",
    "semantic_identity_sha256", "disposition", "source_transition_authorized",
    "reissue_authorized", "new_dispatches", "owner_mutations",
    "scientific_first_use",
})


class V41PendingDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise V41PendingDenied("F139_V41_" + code)


def _historical_native_issues(db):
    """Exactly one ledger-authenticated identity for every admitted issue."""
    historical = {}
    for event in native_events(db):
        n = event["issue_number"]
        need(type(n) is int and n not in historical, "DUPLICATE_ADMITTED_IDENTITY")
        historical[n] = (
            event["issue_id"], event["source_sha"],
            event["issue_body_sha256"], event["ticket"])
    return historical


def _semantic_identity(issue):
    """Bind *every* candidate field except the required controller source.

    Reissuing under a new source necessarily changes the source-bound
    canonical intent digest, ticket and qualification key. It must NOT
    change the actual candidate's material or the rest of its constraints.
    """
    need(isinstance(issue, NativeIssue), "UNAUTHENTICATED_ISSUE")
    try:
        doc = json.loads(issue.intent_raw)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise V41PendingDenied("F139_V41_INTENT_INVALID") from exc
    need(type(doc) is dict
         and doc.get("controller_source_sha") == issue.source_sha,
         "INTENT_SOURCE_DRIFT")
    semantic = {k: v for k, v in doc.items()
                if k != "controller_source_sha"}
    need(semantic.get("target_commit") == issue.candidate.target_commit
         and semantic.get("target_tree_sha") == issue.candidate.target_tree_sha
         and semantic.get("lane") == issue.lane
         and semantic.get("path") == issue.candidate.path
         and semantic.get("before_sha256") == issue.candidate.before_sha256
         and semantic.get("after_sha256") == issue.candidate.after_sha256,
         "CANDIDATE_OR_INTENT_DRIFT")
    return digest(canonical(semantic))


def inspect_never_admitted(db, api, *, expected_number=PENDING_NUMBER):
    """Read a genuine locked, query-only cold original and complete API catalog.

    Actual owner locks, archives, frozen head and post-copy readback remain
    separate requirements of the not-yet-implemented V41 live handoff.
    """
    need(type(db) is Database and type(api) is GitHub
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "QUERY_ONLY_ORIGINAL_MUTEX_REQUIRED")
    need(type(expected_number) is int and expected_number == PENDING_NUMBER,
         "UNEXPECTED_PENDING_NUMBER")
    db.verify()
    before = db.meta().copy()
    changes = db.conn.total_changes
    need(before["source_sha"] == FROM_V40
         and before["enabled"] == 1 and before["legacy_suspended"] == 1
         and before["head_seq"] >= MIN_ORIGINAL_HEAD
         and db.ready() is None and not db.actives(),
         "ORIGINAL_SOURCE_OR_IDLE_DRIFT")
    counts = {row["stage"]: row["n"] for row in db.conn.execute(
        "SELECT stage,COUNT(*) AS n FROM tasks GROUP BY stage")}
    need(counts.get("VERIFIED", 0) >= MIN_VERIFIED
         and counts.get("QUARANTINED", 0) >= MIN_QUARANTINED,
         "ORIGINAL_HISTORICAL_TASK_FLOOR")
    historic = _historical_native_issues(db)
    need(expected_number not in historic, "ALREADY_ADMITTED_NO_REISSUE")
    # The existing API verifies each issue's provider-authenticated owner,
    # label, body, source, target Git commit/tree, canonical intent and all
    # prior admitted issue identities, including across the three page
    # 100+100+empty bounded sentinel. No GET failure may mean empty intake.
    pending = api.native_eligible_issues(FROM_V40, historical_issues=historic)
    need(type(pending) is list
         and len(pending) == 1 and pending[0].number == expected_number
         and pending[0].lane == "Yggdrasil"
         and pending[0].source_sha == FROM_V40
         and db.conn.execute("SELECT 1 FROM tasks WHERE ticket=?",
                             (pending[0].ticket,)).fetchone() is None,
         "PENDING_NOT_EXACTLY_ONE_UNADMITTED_YGGDRASIL")
    issue = pending[0]
    need(db.meta() == before and db.conn.total_changes == changes,
         "ORIGINAL_READ_CHANGED")
    return {
        "schema": SCHEMA,
        "source_sha": FROM_V40,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "issue_number": issue.number,
        "issue_id": issue.issue_id,
        "ticket": issue.ticket,
        "issue_body_sha256": issue.issue_body_sha256,
        "native_intent_sha256": issue.native_intent_sha256,
        "target_commit": issue.candidate.target_commit,
        "target_tree_sha": issue.candidate.target_tree_sha,
        "semantic_identity_sha256": _semantic_identity(issue),
        "disposition": "UNADMITTED_RETAINED_NO_DISPATCH",
        "source_transition_authorized": False,
        "reissue_authorized": False,
        "new_dispatches": 0,
        "owner_mutations": 0,
        "scientific_first_use": False,
    }


def compare_source_bound_reissue(frozen, old, proposed, *, target_source):
    """Compare two separately authenticated issues without admitting either.

    The caller must use the existing inspect_owner_issue and *provider-read*
    immutable target/tree checks for each NativeIssue. This comparator never
    turns a matching proposal into a dispatch or a transition authorization.
    """
    need(type(frozen) is dict and set(frozen) == FROZEN_KEYS
         and frozen.get("schema") == SCHEMA
         and frozen.get("source_sha") == FROM_V40
         and type(frozen.get("original_head_seq")) is int
         and frozen["original_head_seq"] >= 0
         and isinstance(frozen.get("original_head_sha256"), str)
         and SHA64.fullmatch(frozen["original_head_sha256"]) is not None
         and frozen.get("issue_number") == PENDING_NUMBER
         and type(frozen.get("issue_id")) is int
         and frozen["issue_id"] > 0
         and frozen.get("disposition") == "UNADMITTED_RETAINED_NO_DISPATCH"
         and frozen.get("source_transition_authorized") is False
         and frozen.get("reissue_authorized") is False
         and frozen.get("new_dispatches") == 0
         and frozen.get("owner_mutations") == 0
         and frozen.get("scientific_first_use") is False
         and isinstance(target_source, str)
         and SHA40.fullmatch(target_source) is not None
         and target_source != FROM_V40,
         "FROZEN_SOURCE_OR_AUTHORITY_DRIFT")
    need(isinstance(old, NativeIssue) and isinstance(proposed, NativeIssue)
         and old.number == PENDING_NUMBER
         and old.issue_id == frozen.get("issue_id")
         and old.ticket == frozen.get("ticket")
         and old.source_sha == FROM_V40
         and old.issue_body_sha256 == frozen.get("issue_body_sha256")
         and old.native_intent_sha256 == frozen.get("native_intent_sha256")
         and _semantic_identity(old) == frozen.get("semantic_identity_sha256")
         and proposed.source_sha == target_source
         and proposed.number > old.number and proposed.issue_id != old.issue_id
         and proposed.ticket != old.ticket
         and _semantic_identity(proposed) == _semantic_identity(old),
         "REISSUE_IDENTITY_OR_CANDIDATE_DRIFT")
    need(old.candidate.target_commit == proposed.candidate.target_commit
         and old.candidate.target_tree_sha == proposed.candidate.target_tree_sha,
         "REISSUE_TARGET_DRIFT")
    return {
        "schema": REISSUE_SCHEMA,
        "original_source_sha": FROM_V40,
        "successor_source_sha": target_source,
        "old_issue_number": old.number,
        "old_issue_id": old.issue_id,
        "old_ticket": old.ticket,
        "old_issue_body_sha256": old.issue_body_sha256,
        "new_issue_number": proposed.number,
        "new_issue_id": proposed.issue_id,
        "new_ticket": proposed.ticket,
        "new_issue_body_sha256": proposed.issue_body_sha256,
        "semantic_identity_sha256": frozen["semantic_identity_sha256"],
        "original_head_seq": frozen["original_head_seq"],
        "original_head_sha256": frozen["original_head_sha256"],
        "source_transition_authorized": False,
        "reissue_authorized": False,
        "new_dispatches": 0,
        "owner_mutations": 0,
        "scientific_first_use": False,
    }

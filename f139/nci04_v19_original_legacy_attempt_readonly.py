"""V19 read-only projection of actual original F139 free/draft attempt custody.

This module never runs on the controller tick path. No new ledger event, free
request, credential use, task creation or original-authority change. Historical
attempts are spent even if the provider failed or draft publication is
ambiguous. A clean snapshot is NOT permission to create a future attempt.
"""
from __future__ import annotations

import hashlib
import json

from f139.local_controller import Database, SingleOwner, canonical
from f139.nci04_free_reasoner_provider import MODEL
from f139.nci04_model_owner_publication import (SCHEMA as DRAFT_SCHEMA, BRANCH as ORIGINAL_DRAFT_BRANCH)
from f139.nci04_owner_free_reasoner_proposal import (
    SCHEMA as FREE_SCHEMA, MAX_LIFETIME_REQUESTS, reasoner_scope,
)
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, LANES, day_value, is_sha40, is_sha64,
)

FREE = "FREE_REASONER_ATTEMPTED"
DRAFT = "MODEL_DRAFT_ATTEMPTED"
PUBLISHED = "MODEL_DRAFT_AUTHENTICATED"
FREE_FIELDS = frozenset({
    "schema", "source_sha", "model", "scope_sha256",
    "original_feedback_sha256", "lane", "target_commit", "path",
    "utc_day", "prior_event_head_sha256",
    "remote_request_retry_authorized", "paid_model_calls",
    "scientific_first_use",
})
DRAFT_FIELDS = frozenset({
    "schema", "candidate_identity", "source_after_sha256",
    "source_sha", "parent_commit", "branch",
    "prior_event_head_sha256", "scientific_first_use", "retry_allowed",
})
PUBLISHED_FIELDS = frozenset({
    "schema", "candidate_identity", "source_after_sha256",
    "pr_number", "head_commit", "scientific_first_use", "worker_dispatched",
})


def deny(reason: str) -> None:
    raise ShadowDenied("F139_V19_LEGACY_CUSTODY_" + reason)


def original_legacy_attempt_snapshot(db: Database) -> dict:
    """Only authentic original SQLite under the already-held original mutex.

    All original V17/V18 event semantics and immutable lifetime attempt
    budget are retained verbatim. Pure projection; no network or mutations.
    """
    if type(db) is not Database:
        deny("ORIGINAL_DB_REQUIRED")
    if not SingleOwner.held(db.filename.with_suffix(".lock")):
        deny("ORIGINAL_MUTEX_REQUIRED")
    db.verify()
    before = db.meta()
    if before["enabled"] != 1 or before["legacy_suspended"] != 1:
        deny("ORIGINAL_NOT_RUNNING")
    events = [dict(e) for e in db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events "
        "WHERE kind IN (?,?,?) ORDER BY seq", (FREE, DRAFT, PUBLISHED))]
    free_scopes = set()
    free_feedback = set()
    free_counts = dict.fromkeys(LANES, 0)
    free_last_seq = dict.fromkeys(LANES, 0)
    free_last_day = None
    draft_attempts = {}
    draft_successes = {}
    frozen = []
    for event in events:
        try:
            data = json.loads(event["payload"])
        except (ValueError, TypeError) as exc:
            raise ShadowDenied("F139_V19_LEGACY_CUSTODY_EVENT_JSON") from exc
        if type(data) is not dict:
            deny("EVENT_OBJECT_INVALID")
        kind = event["kind"]
        prior = data.get("prior_event_head_sha256")
        if kind == FREE:
            if (set(data) != FREE_FIELDS
                    or data["schema"] != FREE_SCHEMA
                    or data["model"] != MODEL
                    or not is_sha40(data["source_sha"])
                    or not is_sha40(data["target_commit"])
                    or not is_sha64(data["scope_sha256"])
                    or not is_sha64(data["original_feedback_sha256"])
                    or data["lane"] not in LANES
                    or type(data["path"]) is not str
                    or data["remote_request_retry_authorized"] is not False
                    or data["paid_model_calls"] != 0
                    or type(data["paid_model_calls"]) is not int
                    or data["scientific_first_use"] is not False
                    or prior != event["prior_sha"]):
                deny("FREE_ATTEMPT_FIELDS")
            day = day_value(data["utc_day"])
            if free_last_day is not None and day < free_last_day:
                deny("UTC_DAY_ROLLBACK")
            free_last_day = day
            try:
                expected = reasoner_scope(
                    source_sha=data["source_sha"], lane=data["lane"],
                    target_commit=data["target_commit"], path=data["path"],
                    original_feedback_sha256=data["original_feedback_sha256"],
                )
            except Exception as exc:
                raise ShadowDenied("F139_V19_LEGACY_CUSTODY_SCOPE_INVALID") from exc
            if expected != data["scope_sha256"] or expected in free_scopes:
                deny("FREE_SCOPE_REPLAY_OR_DRIFT")
            # Changing the FORGE source SHA is not fresh native outcomes.
            semantic = (data["lane"], data["target_commit"],
                        data["path"], data["original_feedback_sha256"])
            if semantic in free_feedback:
                deny("FREE_SEMANTIC_SCOPE_REPLAY")
            free_scopes.add(expected)
            free_feedback.add(semantic)
            free_counts[data["lane"]] += 1
            free_last_seq[data["lane"]] = event["seq"]
        elif kind == DRAFT:
            if (set(data) != DRAFT_FIELDS
                    or data["schema"] != DRAFT_SCHEMA
                    or not is_sha64(data["candidate_identity"])
                    or not is_sha64(data["source_after_sha256"])
                    or not is_sha40(data["source_sha"])
                    or not is_sha40(data["parent_commit"])
                    or data["scientific_first_use"] is not False
                    or data["retry_allowed"] is not False
                    or type(data["branch"]) is not str
                    or ORIGINAL_DRAFT_BRANCH.fullmatch(data["branch"]) is None
                    or prior != event["prior_sha"]):
                deny("DRAFT_ATTEMPT_FIELDS")
            key = data["candidate_identity"]
            if key in draft_attempts:
                deny("DRAFT_ATTEMPT_REPLAY")
            draft_attempts[key] = (event["seq"], data["source_after_sha256"])
        else:
            if (set(data) != PUBLISHED_FIELDS
                    or data["schema"] != DRAFT_SCHEMA
                    or not is_sha64(data["candidate_identity"])
                    or not is_sha64(data["source_after_sha256"])
                    or not is_sha40(data["head_commit"])
                    or type(data["pr_number"]) is not int
                    or data["pr_number"] <= 0
                    or data["scientific_first_use"] is not False
                    or data["worker_dispatched"] is not False):
                deny("DRAFT_SUCCESS_FIELDS")
            key = data["candidate_identity"]
            old = draft_attempts.get(key)
            if (old is None or key in draft_successes
                    or event["seq"] <= old[0]
                    or data["source_after_sha256"] != old[1]):
                deny("DRAFT_SUCCESS_NOT_CUSTODIED")
            draft_successes[key] = event["seq"]
        frozen.append({
            "seq": event["seq"], "kind": kind, "sha": event["sha"],
        })
    if len(free_scopes) > MAX_LIFETIME_REQUESTS:
        deny("FREE_LIFETIME_DRIFT")
    # Even if publication timed out, the original attempt remains spent.
    pending = len(set(draft_attempts) - set(draft_successes))
    # Cold verify after projection; never infer a future V19 attempt ledger
    # from arbitrary caller-provided lists or the presence of source files.
    db.verify()
    after = db.meta()
    if (before["head_seq"], before["head_hash"]) != (
            after["head_seq"], after["head_hash"]):
        deny("ORIGINAL_CHANGED_DURING_READ")
    return {
        "schema": "forge.f139.v19.original-legacy-attempt-readonly.v1",
        "disposition": (
            "BLOCKED_UNRESOLVED_ORIGINAL_MODEL_WRITE" if pending
            else "VERIFIED_SPENT_ORIGINAL_HISTORY_NOT_RENEWAL_AUTHORITY"
        ),
        "owner_source_sha": before["source_sha"],
        "original_event_head_seq": before["head_seq"],
        "original_event_head_sha256": before["head_hash"],
        "history_sha256": hashlib.sha256(canonical(frozen)).hexdigest(),
        "free_attempt_total": len(free_scopes),
        "free_attempt_counts": free_counts,
        "last_free_attempt_seq_by_lane": free_last_seq,
        "original_draft_attempts": len(draft_attempts),
        "original_draft_authenticated": len(draft_successes),
        "original_unresolved_draft_attempts": pending,
        "spent_free_scope_sha256": sorted(free_scopes),
        "v19_attempt_history_authenticated": False,
        "v19_provider_request_authorized": False,
        "provider_requests": 0,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
        "original_ledger_mutations": 0,
    }

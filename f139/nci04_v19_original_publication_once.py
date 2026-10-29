"""V19 original-owner draft writer. Source-only; never wired into live run_once.

The only allowed Git mutations are injected through the existing bounded
original publisher, after an immutable original SQLite attempt is committed.
Unknown remote outcomes permanently spend that attempt. No retries.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_model_owner_publication import (
    ATTEMPT, SUCCESS, SCHEMA as MODEL_SCHEMA, _publication_history, _write_draft,
)
from f139.nci04_native_contract import canonical
from f139.nci04_v19_original_publication_preflight_no_write import (
    preflight_original_v19_candidate_without_writing,
)
from f139.nci04_v19_original_proposal_validation_custody import (
    KIND as VALIDATION_KIND, SCHEMA as VALIDATION_SCHEMA,
)
from f139.nci04_v19_research_renewal_shadow import ShadowDenied

HEX40 = re.compile(r"[a-f0-9]{40}\Z")


def deny(reason: str) -> None:
    raise ShadowDenied("F139_V19_ORIGINAL_WRITER_" + reason)


def audit_original_v19_draft_attempts(db: Database) -> None:
    """Cold audit only attempts descending from a V19 validated proposal.

    Historical V17/V18 model publication attempts remain untouched.
    A stranded V19 attempt is valid evidence of a spent remote opportunity,
    not permission to retry or manufacture a success.
    """
    events = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    by_seq = {row["seq"]: row for row in events}
    seen = set()
    for row in events:
        if row["kind"] != ATTEMPT:
            continue
        parent = by_seq.get(row["seq"] - 1)
        if parent is None or parent["kind"] != VALIDATION_KIND:
            continue
        validated = json.loads(parent["payload"])
        doc = json.loads(row["payload"])
        if (type(validated) is not dict
                or validated.get("schema") != VALIDATION_SCHEMA
                or type(doc) is not dict
                or set(doc) != {"schema", "candidate_identity",
                                "source_after_sha256", "source_sha",
                                "parent_commit", "branch",
                                "prior_event_head_sha256",
                                "scientific_first_use", "retry_allowed"}
                or doc["schema"] != MODEL_SCHEMA
                or doc["candidate_identity"] != validated["candidate_identity"]
                or doc["source_after_sha256"] != validated["source_after_sha256"]
                or doc["source_sha"] != validated["owner_source_sha"]
                or doc["parent_commit"] != validated["target_commit"]
                or doc["prior_event_head_sha256"] != parent["sha"]
                or row["prior_sha"] != parent["sha"]
                or doc["scientific_first_use"] is not False
                or doc["retry_allowed"] is not False
                or doc["candidate_identity"] in seen):
            deny("COLD_ATTEMPT_IDENTITY_OR_REPLAY")
        expected_branch = (
            "f139/auto-model-"
            + ("w" if validated["lane"] == "Wingless" else "y")
            + "-" + validated["candidate_identity"][:20]
            + "-" + validated["target_commit"][:12]
        )
        if doc["branch"] != expected_branch:
            deny("COLD_ATTEMPT_BRANCH_DRIFT")
        seen.add(doc["candidate_identity"])
        later = by_seq.get(row["seq"] + 1)
        if later is None:
            continue  # Spent attempt with uncertain or interrupted remote result.
        if later["kind"] != SUCCESS:
            deny("COLD_UNRESOLVED_ATTEMPT_ADVANCED")
        outcome = json.loads(later["payload"])
        if (type(outcome) is not dict
                or set(outcome) != {"schema", "candidate_identity",
                                   "source_after_sha256", "pr_number",
                                   "head_commit", "scientific_first_use",
                                   "worker_dispatched"}
                or outcome["schema"] != MODEL_SCHEMA
                or outcome["candidate_identity"] != doc["candidate_identity"]
                or outcome["source_after_sha256"] != doc["source_after_sha256"]
                or type(outcome["pr_number"]) is not int
                or outcome["pr_number"] <= 0
                or type(outcome["head_commit"]) is not str
                or HEX40.fullmatch(outcome["head_commit"]) is None
                or outcome["scientific_first_use"] is not False
                or outcome["worker_dispatched"] is not False):
            deny("COLD_AUTHENTICATED_DRAFT_DRIFT")


def publish_original_v19_candidate_once(
    db: Database, *, validation_seq: int, validation_sha256: str,
    candidate_source: bytes, public_packet: dict,
    original_get: Callable[[str], object],
    public_reader: Callable[[str], dict],
    original_write: Callable[[str, str, dict], object],
    owner_witness: Callable[[], bool],
) -> dict:
    """Bounded original-owner attempt then existing single-file draft writer.

    Never called from the existing F139 tick. Callers must separately
    provide authorized original-owner credentials and a held SingleOwner.
    An interrupted/ambiguous POST may have succeeded; replay is forbidden.
    """
    if (type(db) is not Database or not callable(original_write)
            or not callable(owner_witness)
            or not SingleOwner.held(db.filename.with_suffix(".lock"))
            or owner_witness() is not True):
        deny("MISSING_ORIGINAL_OWNER_OR_WRITER")
    arguments = dict(
        validation_seq=validation_seq,
        validation_sha256=validation_sha256,
        candidate_source=candidate_source, public_packet=public_packet,
        original_get=original_get, public_reader=public_reader,
        owner_witness=owner_witness,
    )
    first = preflight_original_v19_candidate_without_writing(db, **arguments)
    second = preflight_original_v19_candidate_without_writing(db, **arguments)
    if first != second or first["publication_authorized"] is not False:
        deny("PREFLIGHT_MOVED_OR_GRANTED_AUTHORITY")
    before = db.meta().copy()
    if (before["head_seq"] != validation_seq
            or before["head_hash"] != validation_sha256):
        deny("ORIGINAL_VALIDATED_HEAD_MOVED")
    validated = json.loads(db.conn.execute(
        "SELECT payload FROM events WHERE seq=?", (validation_seq,)
    ).fetchone()["payload"])
    document = {
        "schema": "forge.f139.owner-model-draft-note.v1",
        "question": validated["question"],
        "hypothesis": validated["hypothesis"],
        "control": validated["control"],
        "history_sha256": validated["history_sha256"],
        "candidate_identity": first["candidate_identity"],
        "scientific_first_use": False,
        "dispatch_authorized": False,
        "independent_scientific_acceptance": False,
    }
    plan = {
        "repository": first["repository"], "branch": first["branch"],
        "path": first["path"], "parent_commit": first["target_commit"],
        "candidate_source": candidate_source,
        "before_blob": first["source_before_blob_sha1"],
        "after_blob": first["source_after_blob_sha1"],
        "source_sha": first["original_owner_source_sha"],
        "lane": first["lane"],
        "candidate_identity": first["candidate_identity"],
        "source_after_sha256": first["source_after_sha256"],
        "title": ("F139 autonomy DEV: bounded " + first["lane"]
                  + " learning proposal " + first["candidate_identity"][:12]),
        "body": canonical(document).decode("ascii"),
    }
    # This is the final original BEGIN IMMEDIATE before any remote mutation.
    with db.transaction():
        db.verify()
        if (db.meta() != before or db.ready() is not None
                or db.actives() or owner_witness() is not True
                or not SingleOwner.held(db.filename.with_suffix(".lock"))):
            deny("ORIGINAL_PREWRITE_STATE_MOVED")
        _publication_history(db, first["candidate_identity"],
                             first["source_after_sha256"])
        db.event(ATTEMPT, {
            "schema": MODEL_SCHEMA,
            "candidate_identity": first["candidate_identity"],
            "source_after_sha256": first["source_after_sha256"],
            "source_sha": first["original_owner_source_sha"],
            "parent_commit": first["target_commit"],
            "branch": first["branch"],
            "prior_event_head_sha256": validation_sha256,
            "scientific_first_use": False,
            "retry_allowed": False,
        })
        db.verify()
    frozen = db.meta().copy()
    # Revocation after the committed attempt spends the opportunity, even
    # when no POST occurs. Never re-open it on a future tick or restart.
    if owner_witness() is not True:
        return {"disposition": "OWNER_REVOKED_ATTEMPT_SPENT_NO_POST",
                "scientific_first_use": False, "worker_dispatched": False,
                "retry_allowed": False}
    try:
        result = _write_draft(original_get, original_write, plan)
        if (type(result) is not dict
                or type(result.get("pr_number")) is not int
                or result["pr_number"] <= 0
                or type(result.get("head_commit")) is not str
                or HEX40.fullmatch(result["head_commit"]) is None):
            raise ValueError("UNAUTHENTICATED_REMOTE_RESULT")
    except Exception:
        return {"disposition": "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY",
                "scientific_first_use": False, "worker_dispatched": False,
                "retry_allowed": False}
    # A successful verified remote result can be sealed only at the exact
    # immediately preceding attempt. A lost local commit is ambiguous too.
    with db.transaction():
        db.verify()
        if (db.meta() != frozen or owner_witness() is not True
                or not SingleOwner.held(db.filename.with_suffix(".lock"))):
            deny("ORIGINAL_MOVED_AFTER_REMOTE_WRITE_NO_RETRY")
        db.event(SUCCESS, {
            "schema": MODEL_SCHEMA,
            "candidate_identity": first["candidate_identity"],
            "source_after_sha256": first["source_after_sha256"],
            "pr_number": result["pr_number"],
            "head_commit": result["head_commit"],
            "scientific_first_use": False,
            "worker_dispatched": False,
        })
        db.verify()
    return {"disposition": "MODEL_DRAFT_AUTHENTICATED",
            "pr_number": result["pr_number"],
            "head_commit": result["head_commit"],
            "scientific_first_use": False, "worker_dispatched": False,
            "retry_allowed": False}

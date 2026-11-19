"""One-shot original-owner mode admission, intentionally NOT invoked by run_once.

Implements the source-only production path *without installing/activating* it.
A call requires the real Windows ORIGINAL running task and Python child, its
existing SingleOwner mutex, original canonical SQLite/epoch, exact protected
main, a complete provider-authenticated issue/comment read and fresh precise
comment readback. No new worker/queue/scheduler and never grants science or
RSI execution. The issue currently has no eligible commands.
"""
from __future__ import annotations

from pathlib import Path
import re

from f139.nci04_phase_comment_read import (
    ISSUE_ROUTE, _issue_policy, inspect_original_owner_pending_intents,
)
from f139.nci04_phase_manual_intent import ManualPhaseDenied, inspect_comment
from f139.nci04_phase_mode_replay import (
    KIND, SCHEMA, read_original_owner_mode,
)

SHA64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_ADMISSIONS = 128
ISSUE_COMMENT_ROUTE = "repos/spoonman136668-ai/FORGE/issues/comments/"


class OriginalModeAdmissionDenied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise OriginalModeAdmissionDenied("F139_PHASE_OWNER_" + reason)


def admit_original_owner_mode_once(
    *, db, db_path: Path, provider,
    selected_comment_id: int,
    expected_owner_head_sha256: str,
) -> dict:
    """Admit the oldest eligible comment ONCE, under the existing owner.

    This function is **not wired** to a CLI, tick, scheduled task or GitHub
    workflow and has never been run against the enabled original SQLite.
    Operator authorization for production rollout is NOT inferred from this
    source or from CI. Fail closed on ambiguous transport or ledger state.
    """
    from f139.local_controller import (
        Database, GitHub, SingleOwner,
        native_original_running_publisher_profile,
    )

    require(type(db) is Database and type(provider) is GitHub,
            "ORIGINAL_CANONICAL_HANDLES_REQUIRED")
    require(type(selected_comment_id) is int and selected_comment_id > 0,
            "COMMENT_ID_INVALID")
    require(type(expected_owner_head_sha256) is str
            and SHA64.fullmatch(expected_owner_head_sha256) is not None,
            "EXPECTED_LEDGER_HEAD_INVALID")
    try:
        path = Path(db.filename).resolve(strict=True)
        requested = Path(db_path).resolve(strict=True)
    except (OSError, TypeError, ValueError) as exc:
        raise OriginalModeAdmissionDenied("F139_PHASE_OWNER_DB_PATH_INVALID") from exc
    require(path == requested and SingleOwner.held(path.with_suffix(".lock")),
            "ORIGINAL_MUTEX_OR_DB_MISMATCH")
    # Not just a caller-provided bool: inspect the real Windows task state,
    # owner SID, scheduled root, database path and current Python child.
    require(native_original_running_publisher_profile(path) is True,
            "ORIGINAL_RUNNING_OWNER_WITNESS_INVALID")

    db.verify()
    before = db.meta()
    require(before["enabled"] == 1 and before["legacy_suspended"] == 1
            and before["head_hash"] == expected_owner_head_sha256,
            "OWNER_STATE_OR_HEAD_DRIFT")
    protected_main = provider.protected_main()
    require(protected_main == before["source_sha"],
            "ORIGINAL_SOURCE_NOT_PROTECTED_MAIN")

    report = inspect_original_owner_pending_intents(
        db=db, db_path=path, provider=provider,
        protected_main_sha=protected_main)
    require(report["original_head_sha256"] == expected_owner_head_sha256
            and report["owner_epoch"] == before["epoch"]
            and report["policy_source_sha"] == before["source_sha"]
            and report["original_owner_lock_verified"] is True,
            "READBACK_OR_POLICY_DRIFT")
    pending = report["pending"]
    require(len(pending) > 0 and pending[0]["comment_id"] == selected_comment_id,
            "NOT_OLDEST_ELIGIBLE_COMMENT")
    require(len(pending) <= MAX_ADMISSIONS,
            "PENDING_LIMIT_EXCEEDED")

    # Fetch the exact issue-comment endpoint again; an earlier paginated
    # listing cannot establish that the selected command remains unchanged.
    specific = provider.get(ISSUE_COMMENT_ROUTE + str(selected_comment_id))
    previously = read_original_owner_mode(
        db=db, installed_source_sha=before["source_sha"],
        protected_main_sha=protected_main, owner_epoch=before["epoch"])
    require(len(previously["consumed_comment_ids"]) < MAX_ADMISSIONS,
            "LIFETIME_COMMENT_BUDGET_EXHAUSTED")
    try:
        selected = inspect_comment(
            comment=specific, installed_source_sha=before["source_sha"],
            protected_main_sha=protected_main, owner_epoch=before["epoch"],
            consumed_comment_ids=previously["consumed_comment_ids"])
    except ManualPhaseDenied as exc:
        raise OriginalModeAdmissionDenied(
            "F139_PHASE_OWNER_EXACT_COMMENT_REVALIDATION_FAILED") from exc
    fields = ("comment_id", "body_sha256", "comment_created_at",
              "mode", "lane", "owner_source_sha", "owner_epoch")
    require(all(selected[field] == pending[0][field] for field in fields),
            "COMMENT_CHANGED_SINCE_CATALOG")
    # Re-fetch policy as an extra read-only defense against a policy mutation
    # during comment retrieval. This still cannot create operator authority.
    _issue_policy(provider, before["source_sha"])
    db.verify()
    require(db.meta() == before, "ORIGINAL_HEAD_CHANGED_DURING_GETS")

    payload = {
        "schema": SCHEMA, "source_sha": before["source_sha"],
        "owner_epoch": before["epoch"],
        "comment_id": selected_comment_id,
        "body_sha256": selected["body_sha256"],
        "mode": selected["mode"], "lane": selected["lane"],
        "prior_event_head_sha256": expected_owner_head_sha256,
        "scientific_first_use": False, "dispatch_authorized": False,
        "self_source_mutation": False, "checkpoint_mutation": False,
        "accepted_ref_mutation": False,
    }
    # Original F139 BEGIN IMMEDIATE / SHA-chained event in one transaction:
    # the original owner lock has never been surrendered. No API writes.
    with db.transaction():
        db.verify()
        current = db.meta()
        require(current == before
                and SingleOwner.held(path.with_suffix(".lock")),
                "ATOMIC_SOURCE_HEAD_OR_OWNER_CHANGED")
        fresh = read_original_owner_mode(
            db=db, installed_source_sha=before["source_sha"],
            protected_main_sha=protected_main, owner_epoch=before["epoch"])
        require(fresh["consumed_comment_ids"] ==
                previously["consumed_comment_ids"]
                and fresh["last_mode_event_seq"] ==
                    previously["last_mode_event_seq"],
                "ATOMIC_COMMENT_HISTORY_CHANGED")
        db.event(KIND, payload)
        db.verify()
        observed = read_original_owner_mode(
            db=db, installed_source_sha=before["source_sha"],
            protected_main_sha=protected_main, owner_epoch=before["epoch"])
        require(observed["last_comment_id"] == selected_comment_id
                and observed["mode"] == selected["mode"]
                and observed["lane"] == selected["lane"]
                and len(observed["consumed_comment_ids"]) ==
                    len(previously["consumed_comment_ids"]) + 1,
                "POST_COMMIT_OWNER_MODE_READBACK_FAILED")
        final = db.meta()

    return {
        "schema": "forge.f139.original-owner-phase-mode-admission.v1",
        "source_sha": final["source_sha"],
        "owner_epoch": final["epoch"],
        "event_head_sha256": final["head_hash"],
        "event_seq": final["head_seq"],
        "comment_id": selected_comment_id,
        "mode": observed["mode"], "lane": observed["lane"],
        "mode_admitted": True,
        "worker_dispatched": False,
        "scientific_first_use": False, "self_source_mutation": False,
        "checkpoint_mutation": False, "accepted_ref_mutation": False,
        "new_controller": False, "new_scheduler": False,
    }

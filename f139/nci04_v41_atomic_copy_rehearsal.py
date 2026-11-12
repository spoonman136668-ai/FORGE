"""V41 escrow + source-transition transaction on a disposable copied ledger.

No production CLI, no owner task mutation, no issue reissue/dispatch, no
source-policy update, and no scientific first-use. The only public entry
requires a query-only locked original and writes to a NEW separate copy.
A source-only demonstration does not qualify an original-owner release.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_pending_escrow as escrow
from f139 import nci04_v41_pending_custody as pending
from f139 import nci04_v41_owner_approval as approval
from f139 import nci04_v41_cold_copy_verifier as cold
from f139 import nci04_v41_source_transition as source
from f139.nci04_native_contract import digest

class V41AtomicDenied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise V41AtomicDenied("F139_V41_ATOMIC_" + reason)

def _approval_bound(original_meta, cold_receipt, pending_receipt, owner_intent, target):
    """Source-only input custody; no receipt is treated as execution authority."""
    approval._receipts(cold_receipt, pending_receipt, target)
    need(type(owner_intent) is dict
         and owner_intent.get("schema") == approval.RECEIPT
         and owner_intent.get("owner_comment_identity_verified") is True
         and owner_intent.get("provider_reads_only") is True
         and owner_intent.get("source_transition_authorized") is False
         and owner_intent.get("original_owner_release_qualified") is False
         and owner_intent.get("pending_disposition_implemented") is False
         and owner_intent.get("reissue_authorized") is False
         and owner_intent.get("scientific_first_use") is False
         and owner_intent.get("hybrid_admission") is False
         and owner_intent.get("pending_disposition_requested") == "EXPLICIT_ESCROW_ONCE"
         and owner_intent.get("original_source_sha") == source.FROM_V40
         and owner_intent.get("target_source_sha") == target
         and owner_intent.get("pending_issue_number") == 1715
         and owner_intent.get("original_head_seq") == pending_receipt["original_head_seq"]
         and owner_intent.get("original_head_sha256") == pending_receipt["original_head_sha256"]
         and type(owner_intent.get("owner_comment_id")) is int
         and owner_intent["owner_comment_id"] > 0
         and escrow._sha(owner_intent.get("owner_comment_body_sha256"), escrow.SHA64)
         and owner_intent.get("remote_writes") == 0
         and owner_intent.get("owner_mutations") == 0
         and owner_intent.get("new_dispatches") == 0
         and original_meta["source_sha"] == source.FROM_V40
         and original_meta["head_seq"] == pending_receipt["original_head_seq"]
         and original_meta["head_hash"] == pending_receipt["original_head_sha256"]
         and original_meta["enabled"] == 1
         and original_meta["legacy_suspended"] == 1, "PREIMAGE_OR_OWNER_INTENT_DRIFT")

def _escrow_doc(original_meta, preserved, owner):
    """Construct only from authenticated locked original custody receipts."""
    doc = dict(
        schema=escrow.SCHEMA, source_sha=source.FROM_V40,
        issue_number=preserved["issue_number"],
        issue_id=preserved["issue_id"], ticket=preserved["ticket"],
        issue_body_sha256=preserved["issue_body_sha256"],
        native_intent_sha256=preserved["native_intent_sha256"],
        semantic_identity_sha256=preserved["semantic_identity_sha256"],
        target_commit=preserved["target_commit"],
        target_tree_sha=preserved["target_tree_sha"],
        original_head_seq=original_meta["head_seq"],
        original_head_sha256=original_meta["head_hash"],
        frozen_observed_seq=escrow.OBSERVED_SEQ,
        frozen_observed_head_sha256=escrow.OBSERVED_HEAD,
        owner_comment_id=owner["owner_comment_id"],
        owner_comment_body_sha256=owner["owner_comment_body_sha256"],
        pending_disposition="EXPLICIT_ESCROW_ONCE", new_dispatches=0,
        reissue_authorized=False, scientific_first_use=False,
        hybrid_admission=False)
    escrow.verify_event_shape(
        {"seq": original_meta["head_seq"]+1,
         "prior_sha": original_meta["head_hash"]}, doc)
    return doc

def _atomic_on_copy(db, *, original_path, original_meta, target, binary_sha,
                    toolchain, cold_receipt, pending_receipt, owner_intent,
                    inject_failure=None):
    """Internal single-transaction *copy-only* test path; never use on owner."""
    need(type(db) is Database
         and not getattr(db, "_readonly_opened", False)
         and type(original_path) is Path
         and db.filename.resolve() != original_path.resolve()
         and SingleOwner.held(original_path.with_suffix(".lock"))
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and inject_failure in (None, "after_escrow", "after_source_event",
                                "after_verify"),
         "DISTINCT_LOCKED_COPY_REQUIRED")
    need(type(target) is str and source.HEX40.fullmatch(target)
         and type(binary_sha) is str and source.HEX64.fullmatch(binary_sha)
         and toolchain == source.TOOLCHAIN, "SOURCE_OR_BINARY_INVALID")
    _approval_bound(original_meta, cold_receipt, pending_receipt,
                    owner_intent, target)
    need(db.meta() == original_meta, "COPY_PREIMAGE_MOVED")
    db.verify()
    before_changes = db.conn.total_changes
    with db.transaction():
        db.verify()
        need(db.meta() == original_meta, "COPY_CHANGED_BEFORE_BEGIN")
        need(db.ready() is None and not db.actives(), "ORIGINAL_NOT_IDLE")
        need(db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?",
            (escrow.KIND,)).fetchone()[0] == 0, "ESCROW_REPLAY")
        escrow_doc = _escrow_doc(original_meta, pending_receipt, owner_intent)
        db.event(escrow.KIND, escrow_doc)
        if inject_failure == "after_escrow":
            raise V41AtomicDenied("F139_V41_ATOMIC_INJECTED_AFTER_ESCROW")
        proof = source.build_proof(
            db, target, owner_intent["owner_comment_id"], binary_sha, toolchain)
        need(type(proof) is dict and set(proof) == source.FIELDS
             and proof["to_source_sha"] == target
             and proof["original_head_seq"] == original_meta["head_seq"] + 1
             and proof["pending_1715_escrow_sha256"] == db.meta()["head_hash"],
             "SOURCE_PROOF_OR_ESCROW_DRIFT")
        # The source change and both append-only events are ONE SQLite commit.
        db.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (target,))
        db.event("SOURCE_TRANSITION_ADMITTED", proof)
        if inject_failure == "after_source_event":
            raise V41AtomicDenied("F139_V41_ATOMIC_INJECTED_AFTER_SOURCE")
        db.verify()
        need(db.meta()["head_seq"] == original_meta["head_seq"] + 2
             and db.meta()["source_sha"] == target
             and db.conn.execute(
                 "SELECT kind FROM events ORDER BY seq DESC LIMIT 2").fetchall()[0][0]
                 == "SOURCE_TRANSITION_ADMITTED", "COPY_POSTIMAGE_MISMATCH")
        if inject_failure == "after_verify":
            raise V41AtomicDenied("F139_V41_ATOMIC_INJECTED_AFTER_VERIFY")
    db.verify()
    return {
        "schema": "forge.f139.v41.atomic-copy-rehearsal.v1",
        "original_source_sha": source.FROM_V40,
        "copy_source_sha": db.meta()["source_sha"],
        "original_head_seq": original_meta["head_seq"],
        "copy_head_seq": db.meta()["head_seq"],
        "copy_head_sha256": db.meta()["head_hash"],
        "escrow_event_sha256": proof["pending_1715_escrow_sha256"],
        "original_unchanged": True, "copy_only": True,
        "source_transition_authorized": False,
        "release_qualified": False, "reissue_authorized": False,
        "new_dispatches": 0, "scientific_first_use": False,
        "hybrid_admission": False,
    }

def rehearse_locked_original(original, backup, get, api, *, target,
                              qualification_run_id, backup_sha256,
                              owner_comment_id, copy_path,
                              binary_sha, toolchain, inject_failure=None):
    """Verify genuine owner read-only and write only to a fresh cold copy.

    The caller owns the existing original-owner mutex. If any check fails,
    the original is untouched and no source activation or dispatch occurs.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock")),
         "ORIGINAL_QUERY_ONLY_MUTEX_REQUIRED")
    copy_path = Path(copy_path)
    backup = Path(backup)
    need(copy_path.is_absolute() and not copy_path.exists()
         and copy_path.parent.is_dir() and not copy_path.parent.is_symlink()
         and all(not p.is_symlink() for p in copy_path.parent.parents)
         and copy_path.resolve() != original.filename.resolve()
         and copy_path.resolve() != backup.resolve()
         and copy_path.suffix == ".sqlite", "FRESH_ISOLATED_COPY_PATH_REQUIRED")
    original.verify()
    before = original.meta().copy()
    changes = original.conn.total_changes
    cold_receipt = cold.verify_cold_copy(
        original, backup, get, target=target, run_id=qualification_run_id,
        expected_backup_sha256=backup_sha256)
    preserved = pending.inspect_never_admitted(original, api)
    owner_intent = approval.verify_owner_comment(
        get, target=target, cold=cold_receipt, pending_receipt=preserved,
        comment_id=owner_comment_id)
    _approval_bound(before, cold_receipt, preserved, owner_intent, target)
    need(original.meta() == before and original.conn.total_changes == changes,
         "ORIGINAL_MOVED_BEFORE_COPY")
    # The backup API produces a transaction-consistent SQLite copy; never
    # copy only the potentially WAL-incomplete original main-file bytes.
    destination = sqlite3.connect(str(copy_path), timeout=10)
    try:
        original.conn.backup(destination)
    finally:
        destination.close()
    need(copy_path.is_file() and not copy_path.is_symlink(),
         "COPIED_SQLITE_FILE_MISSING")
    with closing(Database(copy_path)) as working:
        with SingleOwner(copy_path.with_suffix(".lock")):
            need(working.meta() == before, "COLD_COPY_HEAD_DRIFT")
            outcome = _atomic_on_copy(
                working, original_path=original.filename, original_meta=before,
                target=target, binary_sha=binary_sha, toolchain=toolchain,
                cold_receipt=cold_receipt, pending_receipt=preserved,
                owner_intent=owner_intent, inject_failure=inject_failure)
    with closing(Database.open_readonly(copy_path)) as restored:
        restored.verify()
        need(restored.meta()["source_sha"] == target
             and restored.meta()["head_seq"] == before["head_seq"]+2
             and restored.meta()["head_hash"] == outcome["copy_head_sha256"],
             "COLD_REOPEN_DRIFT")
    original.verify()
    need(original.meta() == before and original.conn.total_changes == changes,
         "ORIGINAL_MUTATED_DURING_COPY_REHEARSAL")
    return outcome

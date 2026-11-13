"""V41 escrow + source-transition transaction on a disposable copied ledger.

No production CLI, no owner task mutation, no issue reissue/dispatch, no
source-policy update, and no scientific first-use. The only public entry
requires a query-only locked original and writes to a NEW separate copy.
A source-only demonstration does not qualify an original-owner release.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_pending_escrow as escrow
from f139 import nci04_v41_pending_custody as pending
from f139 import nci04_v41_owner_approval as approval
from f139 import nci04_v41_cold_copy_verifier as cold
from f139 import nci04_v41_offline_cold_bundle as offline
from f139 import nci04_v41_source_transition as source
from f139.nci04_native_contract import canonical, digest

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

def _atomic_on_copy(db, *, original, original_meta, target, binary_sha,
                    toolchain, cold_receipt, pending_receipt, owner_intent,
                    inject_failure=None):
    """Internal single-transaction *copy-only* test path; never use on owner."""
    need(type(db) is Database and type(original) is Database
         and not getattr(db, "_readonly_opened", False)
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and db.filename.resolve() != original.filename.resolve()
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and SingleOwner.held(db.filename.with_suffix(".lock"))
         and inject_failure in (None, "after_escrow", "after_source_event",
                                "after_verify"),
         "DISTINCT_LOCKED_COPY_REQUIRED")
    need(type(target) is str and source.HEX40.fullmatch(target)
         and type(binary_sha) is str and source.HEX64.fullmatch(binary_sha)
         and toolchain == source.TOOLCHAIN, "SOURCE_OR_BINARY_INVALID")
    _approval_bound(original_meta, cold_receipt, pending_receipt,
                    owner_intent, target)
    need(db.meta() == original_meta
         and original.meta() == original_meta, "COPY_OR_ORIGINAL_PREIMAGE_MOVED")
    original_changes = original.conn.total_changes
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
    original.verify()
    need(original.meta() == original_meta
         and original.conn.total_changes == original_changes,
         "ORIGINAL_MOVED_DURING_COPY_TRANSACTION")
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
    # A detached SQLite without its ledger-bound historical negative ZIPs
    # fails the real A8B/A8E2A2 Database.verify() cold replay. Do not put a
    # rehearsal in the original or backup custody directory.
    origin_root = original.filename.parent
    copy_root = copy_path.parent
    need(copy_root.resolve() != origin_root.resolve()
         and copy_root.resolve() != backup.parent.resolve(),
         "ISOLATED_CUSTODY_ROOT_REQUIRED")
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
    negative_custody = cold.required_negative_custody(original)
    # Copy only exact frozen, original-hash-matched negative provider evidence.
    # Exclude an existing destination root to avoid mixing independent custody
    # or overwriting a previous rehearsal. No source files are modified.
    need(not (copy_root / "native-negative").exists()
         and not (copy_root / "native-negative").is_symlink(),
         "COPIED_NEGATIVE_CUSTODY_ALREADY_EXISTS")
    need(original.meta() == before and original.conn.total_changes == changes,
         "ORIGINAL_MOVED_BEFORE_COPY")
    cold.copy_negative_custody(origin_root, copy_root, negative_custody,
                              copy_files=True)
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
                working, original=original, original_meta=before,
                target=target, binary_sha=binary_sha, toolchain=toolchain,
                cold_receipt=cold_receipt, pending_receipt=preserved,
                owner_intent=owner_intent, inject_failure=inject_failure)
    with closing(Database.open_readonly(copy_path)) as restored:
        # Check the recovered ledger's own negative event identities and the
        # original frozen ZIP hashes, not merely that two file paths exist.
        need(cold.required_negative_custody(restored) == negative_custody,
             "COPIED_NEGATIVE_LEDGER_DRIFT")
        cold.copy_negative_custody(origin_root, copy_root, negative_custody,
                                  copy_files=False)
        restored.verify()
        need(restored.meta()["source_sha"] == target
             and restored.meta()["head_seq"] == before["head_seq"]+2
             and restored.meta()["head_hash"] == outcome["copy_head_sha256"],
             "COLD_REOPEN_DRIFT")
    original.verify()
    need(original.meta() == before and original.conn.total_changes == changes,
         "ORIGINAL_MUTATED_DURING_COPY_REHEARSAL")
    return outcome


def rehearse_from_sealed_cold_bundle(original, bundle_root, get, api, *,
                                    target, run_id, manifest_sha256,
                                    original_head_seq, original_head_sha256,
                                    owner_comment_id, copy_path,
                                    binary_sha, toolchain,
                                    inject_failure=None):
    """Bind an independently sealed *same-target* recovery to copied replay.

    Reuses both independently qualified verifiers. A valid old backup bound
    to another target SHA is a recovery asset, NOT the source-release backup
    for a new candidate. No release approval is manufactured here.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock")),
         "SEALED_ORIGINAL_QUERY_ONLY_MUTEX_REQUIRED")
    need(type(target) is str and source.HEX40.fullmatch(target)
         and type(manifest_sha256) is str
         and re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is not None
         and type(original_head_seq) is int and original_head_seq > 0
         and type(original_head_sha256) is str
         and re.fullmatch(r"[0-9a-f]{64}", original_head_sha256) is not None
         and type(run_id) is int and run_id > 0
         and type(owner_comment_id) is int and owner_comment_id > 0,
         "SEALED_INPUTS_INVALID")
    before = original.meta().copy()
    changes = original.conn.total_changes
    need(before["source_sha"] == source.FROM_V40
         and before["head_seq"] == original_head_seq
         and before["head_hash"] == original_head_sha256,
         "SEALED_PREIMAGE_DRIFT")
    bundle_root = Path(bundle_root)
    # The offline verifier refuses aliases, symlinks, unlisted content and
    # every altered custody entry, and independently restores SQLite.
    receipt = offline.verify_sealed_bundle_offline(
        bundle_root, expected_manifest_sha256=manifest_sha256,
        target=target, run_id=run_id, expected_head_seq=original_head_seq,
        expected_head_sha256=original_head_sha256)
    need(type(receipt) is dict
         and receipt.get("independent_restore_verified") is True
         and receipt.get("manifest_sha256") == manifest_sha256
         and receipt.get("original_source_sha") == source.FROM_V40
         and receipt.get("target_source_sha") == target
         and receipt.get("original_head_seq") == original_head_seq
         and receipt.get("original_head_sha256") == original_head_sha256
         and receipt.get("source_transition_authorized") is False
         and receipt.get("release_qualified") is False
         and receipt.get("scientific_first_use") is False
         and receipt.get("hybrid_admission") is False,
         "INDEPENDENT_RESTORE_RECEIPT_DRIFT")
    sealed = bundle_root / "manifest.sha256.json"
    raw = sealed.read_bytes()
    need(digest(raw) == manifest_sha256, "SEALED_MANIFEST_MOVED")
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise V41AtomicDenied("F139_V41_ATOMIC_SEALED_MANIFEST_JSON") from exc
    need(type(manifest) is dict
         and canonical(manifest) == raw
         and manifest.get("schema") == offline.SCHEMA
         and manifest.get("original_source_sha") == source.FROM_V40
         and manifest.get("target_source_sha") == target
         and manifest.get("run_id") == run_id
         and manifest.get("original_head_seq") == original_head_seq
         and manifest.get("original_head_sha256") == original_head_sha256
         and type(manifest.get("files_sha256")) is dict
         and type(manifest["files_sha256"].get("state.sqlite")) is str
         and re.fullmatch(r"[0-9a-f]{64}",
                          manifest["files_sha256"]["state.sqlite"]) is not None,
         "SEALED_SOURCE_OR_BACKUP_IDENTITY_DRIFT")
    need(original.meta() == before and
         original.conn.total_changes == changes,
         "ORIGINAL_MOVED_DURING_OFFLINE_RESTORE")
    # The owner-authored comment is authenticated by the existing
    # rehearse_locked_original route, together with the original old-source
    # policy and pending #1715. It can only write to an isolated SQLite copy.
    outcome = rehearse_locked_original(
        original, bundle_root / "state.sqlite", get, api, target=target,
        qualification_run_id=run_id,
        backup_sha256=manifest["files_sha256"]["state.sqlite"],
        owner_comment_id=owner_comment_id, copy_path=copy_path,
        binary_sha=binary_sha, toolchain=toolchain,
        inject_failure=inject_failure)
    need(type(outcome) is dict
         and outcome.get("copy_only") is True
         and outcome.get("source_transition_authorized") is False
         and outcome.get("release_qualified") is False
         and outcome.get("scientific_first_use") is False
         and outcome.get("hybrid_admission") is False
         and outcome.get("original_head_seq") == original_head_seq
         and original.meta() == before
         and original.conn.total_changes == changes,
         "COPY_ORIGINAL_PARITY_OR_AUTHORITY_DRIFT")
    return dict(outcome, sealed_recovery_manifest_sha256=manifest_sha256,
                independent_restore_verified=True,
                original_owner_mutations=0)

"""Independent event-1831 cold-copy custody for a future V39 source successor.

Source-only, not a workflow or execution authority. The live original stays
query-only, under its existing SingleOwner mutex. A create-only sibling bundle
holds the *new* 1831 SQLite image plus the verified immutable V38 provider,
binary and negative custody. No replay, task restart or first-use.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139 import nci04_v41_hybrid_event1832_successor as successor
from f139 import nci04_v41_hybrid_forward_cold_bundle as preceding
from f139 import nci04_v41_hybrid_cold_bundle as bundle
from f139 import nci04_v41_cold_copy_verifier as cold

SCHEMA = "forge.f139.v39.original-event1831-complete-cold-bundle.v1"
FIELDS = frozenset({
    "schema", "original_source_sha", "target_source_sha", "run_id",
    "original_head_seq", "original_head_sha256",
    "predecessor_backup_run_id", "predecessor_backup_manifest_sha256",
    "files_sha256", "logical_all_tables_sha256",
    "provider_archives_manifest_sha256",
    "generation_binary_manifest_sha256",
    "negative_custody_manifest_sha256",
    "restored_sqlite_sha256", "original_owner_mutations",
    "new_dispatches", "source_transition_authorized",
    "owner_policy_modified", "task_resume_authorized",
    "hybrid_admission", "scientific_first_use",
})


class Event1831ColdDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise Event1831ColdDenied("F139_V39_COLD_" + code)


def folder_for(original, run_id):
    need(isinstance(original, Path) and original.is_absolute()
         and original.name == "state.sqlite"
         and type(run_id) is int and run_id > 0,
         "CANONICAL_ORIGINAL_AND_RUN_REQUIRED")
    return original.parent / ("f139-v39-before-" + str(run_id))


def _manifest(folder, target, run_id, manifest_sha):
    need(isinstance(folder, Path) and folder.is_absolute()
         and folder.name == "f139-v39-before-" + str(run_id)
         and folder.is_dir()
         and all(bundle._nonlink(p) for p in (folder, *folder.parents))
         and type(manifest_sha) is str
         and successor.SHA64.fullmatch(manifest_sha) is not None
         and type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and target != successor.SOURCE,
         "IMMUTABLE_COLD_FOLDER_REQUIRED")
    path = folder / "manifest.sha256.json"
    need(path.is_file() and bundle._nonlink(path)
         and 0 < path.stat().st_size <= 1_000_000,
         "SEALED_MANIFEST_MISSING")
    raw = path.read_bytes()
    need(digest(raw) == manifest_sha, "MANIFEST_SHA_MISMATCH")
    try:
        doc = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Event1831ColdDenied("F139_V39_COLD_MANIFEST_PARSE") from exc
    need(canonical(doc) == raw
         and type(doc) is dict and set(doc) == FIELDS
         and doc["schema"] == SCHEMA
         and doc["original_source_sha"] == successor.SOURCE
         and doc["target_source_sha"] == target
         and type(doc["run_id"]) is int and doc["run_id"] == run_id
         and doc["original_head_seq"] == successor.PREDECESSOR_SEQ
         and doc["original_head_sha256"] == successor.PREDECESSOR_SHA
         and type(doc["predecessor_backup_run_id"]) is int
         and doc["predecessor_backup_run_id"] > 0
         and all(type(doc[k]) is str
                 and successor.SHA64.fullmatch(doc[k]) is not None
                 for k in (
                     "predecessor_backup_manifest_sha256",
                     "logical_all_tables_sha256",
                     "provider_archives_manifest_sha256",
                     "generation_binary_manifest_sha256",
                     "negative_custody_manifest_sha256",
                     "restored_sqlite_sha256"))
         and type(doc["original_owner_mutations"]) is int
         and doc["original_owner_mutations"] == 0
         and type(doc["new_dispatches"]) is int
         and doc["new_dispatches"] == 0
         and all(doc[k] is False for k in (
             "source_transition_authorized", "owner_policy_modified",
             "task_resume_authorized", "hybrid_admission",
             "scientific_first_use")),
         "EVENT1831_COLD_MANIFEST_FIELDS_OR_AUTHORITY_DRIFT")
    return doc


def _original_meta(db, expected_source):
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == expected_source
         and meta["head_seq"] == successor.PREDECESSOR_SEQ
         and meta["head_hash"] == successor.PREDECESSOR_SHA
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and db.ready() is None and not db.actives(),
         "EXACT_EVENT1831_ORIGINAL_HOLD_REQUIRED")
    good = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]
    bad = db.conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0]
    need(good == 153 and bad == 56,
         "HISTORICAL_153_56_TASK_CUSTODY_REQUIRED")
    return dict(meta)


def verify_detached_restore(folder, *, target, run_id, manifest_sha):
    """Hash-bound independent SQLite WAL-inclusive restoration and file census."""
    doc = _manifest(folder, target, run_id, manifest_sha)
    files, negatives = bundle._validate_files(folder, doc)
    sqlite_file = folder / "state.sqlite"
    cold._require_standalone_sqlite(sqlite_file)
    with tempfile.TemporaryDirectory(prefix="f139-v39-detached-") as temp:
        restored = Path(temp) / "state.sqlite"
        with cold._hashed_private_sqlite_snapshot(
                sqlite_file, files["state.sqlite"]) as source:
            before = _original_meta(source, successor.SOURCE)
            need(cold.required_negative_custody(source) == negatives
                 and digest(canonical(rollback_view(source.conn))) ==
                     doc["logical_all_tables_sha256"],
                 "SEALED_EVENT1831_BYTES_OR_NEGATIVES_DRIFT")
            with closing(sqlite3.connect(
                    str(restored), isolation_level=None)) as output:
                source.conn.backup(output)
        cold._require_standalone_sqlite(restored)
        cold.copy_negative_custody(
            folder, Path(temp), negatives, copy_files=True)
        with closing(cold._open_immutable_hashed_backup(restored)) as final:
            _original_meta(final, successor.SOURCE)
            need(final.meta() == before
                 and digest(canonical(rollback_view(final.conn))) ==
                     doc["logical_all_tables_sha256"],
                 "DETACHED_ORIGINAL_HISTORY_OR_TABLES_DRIFT")
        need(cold._hash_standalone_sqlite(restored) ==
             doc["restored_sqlite_sha256"],
             "DETACHED_RESTORED_SQLITE_CHANGED")
    # Re-run full immutable file census and manifest digest after cold replay.
    bundle._validate_files(folder, doc)
    need(digest((folder / "manifest.sha256.json").read_bytes()) ==
         manifest_sha, "MANIFEST_CHANGED_DURING_VERIFICATION")
    return {
        "schema": successor.COLD_SCHEMA,
        "original_source_sha": successor.SOURCE,
        "original_head_seq": successor.PREDECESSOR_SEQ,
        "original_head_sha256": successor.PREDECESSOR_SHA,
        "target_source_sha": target,
        "backup_run_id": run_id,
        "backup_manifest_sha256": manifest_sha,
        "backup_logical_all_tables_sha256":
            doc["logical_all_tables_sha256"],
        "independent_detached_restore_verified": True,
        "provider_archives_bytes_verified": True,
        "generation_binary_bytes_verified": True,
        "negative_custody_bytes_verified": True,
        "original_owner_mutations": 0,
        "new_dispatches": 0,
        "scientific_first_use": False,
    }


def stage_complete_cold_bundle(original, *, target, run_id,
                               disabled_owner_witness, release_witness):
    """Create-only original 1831 backup. No caller can authorize a replay."""
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.filename.is_absolute()
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and callable(disabled_owner_witness)
         and callable(release_witness)
         and disabled_owner_witness() is True
         and release_witness() is True
         and type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and target != successor.SOURCE,
         "ORIGINAL_OWNER_COLD_AUTHORIZATION_REQUIRED")
    before = _original_meta(original, successor.SOURCE)
    event = original.conn.execute(
        "SELECT kind,payload,sha FROM events WHERE seq=?",
        (successor.PREDECESSOR_SEQ,)).fetchone()
    need(event is not None
         and event["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and event["sha"] == successor.PREDECESSOR_SHA,
         "EVENT1831_REQUIRED")
    prior = json.loads(event["payload"])
    need(type(prior) is dict and type(prior["backup_run_id"]) is int
         and successor.SHA64.fullmatch(
             prior["backup_manifest_sha256"]) is not None,
         "PREDECESSOR_BACKUP_REFERENCE_INVALID")
    old_folder = original.filename.parent / (
        "f139-v38-before-" + str(prior["backup_run_id"]))
    preceding.verify_detached_restore(
        old_folder, target=successor.SOURCE,
        run_id=prior["backup_run_id"],
        manifest_sha=prior["backup_manifest_sha256"])
    old_manifest = json.loads(
        (old_folder / "manifest.sha256.json").read_bytes())
    old_files, _ = bundle._validate_files(old_folder, old_manifest)
    new = folder_for(original.filename, run_id)
    need(not new.exists() and not new.is_symlink()
         and all(bundle._nonlink(p) for p in (
             original.filename.parent, *original.filename.parents)),
         "UNKNOWN_RESULT_BACKUP_REPLAY_FORBIDDEN")
    new.mkdir(mode=0o700, exist_ok=False)
    db_copy = new / "state.sqlite"
    with closing(sqlite3.connect(
            str(db_copy), isolation_level=None)) as output:
        original.conn.backup(output)
    cold._require_standalone_sqlite(db_copy)
    sqlite_sha = cold._hash_standalone_sqlite(db_copy)
    for relative, expected in sorted(old_files.items()):
        if relative == "state.sqlite":
            continue
        src = old_folder.joinpath(*relative.split("/"))
        dst = new.joinpath(*relative.split("/"))
        need(src.is_file() and bundle._nonlink(src)
             and digest(src.read_bytes()) == expected
             and not dst.exists(),
             "PREDECESSOR_PROVIDER_OR_NEGATIVE_BYTES_CHANGED")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as reader, dst.open("xb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
        need(digest(dst.read_bytes()) == expected,
             "COPIED_PROVIDER_OR_BINARY_BYTES_CHANGED")
    files = dict(old_files)
    files["state.sqlite"] = sqlite_sha
    logical = digest(canonical(rollback_view(original.conn)))
    negatives = cold.required_negative_custody(original)
    with tempfile.TemporaryDirectory(prefix="f139-v39-verify-") as temp:
        restored = Path(temp) / "state.sqlite"
        with cold._hashed_private_sqlite_snapshot(
                db_copy, sqlite_sha) as copied:
            need(_original_meta(copied, successor.SOURCE) == before
                 and digest(canonical(rollback_view(copied.conn))) == logical,
                 "EVENT1831_SQLITE_BACKUP_DRIFT")
            with closing(sqlite3.connect(
                    str(restored), isolation_level=None)) as output:
                copied.conn.backup(output)
        cold._require_standalone_sqlite(restored)
        cold.copy_negative_custody(
            new, Path(temp), negatives, copy_files=True)
        with closing(cold._open_immutable_hashed_backup(restored)) as final:
            need(_original_meta(final, successor.SOURCE) == before
                 and digest(canonical(rollback_view(final.conn))) == logical,
                 "DETACHED_EVENT1831_HISTORY_CHANGED")
        restored_sha = cold._hash_standalone_sqlite(restored)
    manifest = {
        "schema": SCHEMA, "original_source_sha": successor.SOURCE,
        "target_source_sha": target, "run_id": run_id,
        "original_head_seq": successor.PREDECESSOR_SEQ,
        "original_head_sha256": successor.PREDECESSOR_SHA,
        "predecessor_backup_run_id": prior["backup_run_id"],
        "predecessor_backup_manifest_sha256":
            prior["backup_manifest_sha256"],
        "files_sha256": dict(sorted(files.items())),
        "logical_all_tables_sha256": logical,
        "provider_archives_manifest_sha256":
            old_manifest["provider_archives_manifest_sha256"],
        "generation_binary_manifest_sha256":
            old_manifest["generation_binary_manifest_sha256"],
        "negative_custody_manifest_sha256":
            old_manifest["negative_custody_manifest_sha256"],
        "restored_sqlite_sha256": restored_sha,
        "original_owner_mutations": 0, "new_dispatches": 0,
        "source_transition_authorized": False,
        "owner_policy_modified": False,
        "task_resume_authorized": False,
        "hybrid_admission": False, "scientific_first_use": False,
    }
    need(set(manifest) == FIELDS, "MANIFEST_SHAPE_DRIFT")
    encoded = canonical(manifest)
    with (new / "manifest.sha256.json").open("xb") as handle:
        handle.write(encoded)
        handle.flush()
    manifest_sha = digest(encoded)
    receipt = verify_detached_restore(
        new, target=target, run_id=run_id,
        manifest_sha=manifest_sha)
    need(disabled_owner_witness() is True
         and release_witness() is True
         and original.meta() == before
         and original.conn.total_changes == 0,
         "ORIGINAL_MOVED_DURING_COLD_BACKUP")
    return receipt

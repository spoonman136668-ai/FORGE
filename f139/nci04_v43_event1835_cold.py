"""F139 V43 create-only full original event1835 backup and detached restore.

Copies the *actual* original WAL-consistent SQLite, existing provider archives,
generator binary, and original negative evidence. The original controller is
never stopped or modified by this module. No source event or installation.
Only original-owner authenticated callers holding the existing mutex may stage.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

from f139.local_controller import Database, SingleOwner, canonical as event_canonical
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.nci04_v41_cold_copy_verifier import (
    _hashed_private_sqlite_snapshot, _hash_standalone_sqlite,
    _open_immutable_hashed_backup, _require_standalone_sqlite,
    copy_negative_custody, required_negative_custody,
)
from f139 import nci04_v41_hybrid_event1833_cold as prior
from f139 import nci04_v41_hybrid_cold_bundle as bundle
from f139 import nci04_v42_owner_source_readiness as v42
from f139 import nci04_v43_event1836_successor as successor

SCHEMA = "forge.f139.v43.event1835-complete-cold-bundle.v1"
BACKUP_PREFIX = "f139-v43-before-"
MAX_MANIFEST = 2_000_000
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


class OriginalColdDenied(ValueError):
    pass


def need(valid, reason):
    if not valid:
        raise OriginalColdDenied("F139_V43_COLD_" + reason)


def backup_folder(original, run_id):
    need(isinstance(original, Path) and original.is_absolute()
         and original.name == "state.sqlite"
         and type(run_id) is int
         and run_id > successor.PREVIOUS_OWNER_READ_RUN,
         "ORIGINAL_PATH_AND_FRESH_RUN_REQUIRED")
    path = original.parent / (BACKUP_PREFIX + str(run_id))
    need(not path.is_symlink()
         and not getattr(path, "is_junction", lambda: False)(),
         "BACKUP_LINK_DENIED")
    return path


def _frozen_meta(db):
    """Cold copy verification does not require live owner mutex."""
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "COLD_QUERY_ONLY_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == v42.BEFORE
         and meta["head_seq"] == v42.FROZEN_SEQ
         and meta["head_hash"] == v42.FROZEN_HEAD
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.dual_native_schema()
         and db.ready() is None and not db.actives()
         and db.conn.total_changes == 0,
         "ORIGINAL_EVENT1835_COLD_STATE_DRIFT")
    counts = {
        x["stage"]: x["count"] for x in db.conn.execute(
            "SELECT stage,COUNT(*) AS count FROM tasks GROUP BY stage")}
    need(counts == {"VERIFIED": 153, "QUARANTINED": 56}
         and db.conn.total_changes == 0,
         "ORIGINAL_153_56_COLD_TASK_DRIFT")
    return meta


def _manifest(folder, *, target, run_id, manifest_sha):
    need(isinstance(folder, Path) and folder.is_absolute()
         and folder.name == BACKUP_PREFIX + str(run_id)
         and folder.is_dir()
         and all(bundle._nonlink(p) for p in (folder, *folder.parents))
         and type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and target != v42.BEFORE
         and type(manifest_sha) is str
         and successor.SHA64.fullmatch(manifest_sha) is not None,
         "MANIFEST_IDENTITY_OR_LINK_DRIFT")
    file = folder / "manifest.sha256.json"
    need(file.is_file() and bundle._nonlink(file)
         and 0 < file.stat().st_size <= MAX_MANIFEST,
         "SEALED_MANIFEST_MISSING")
    raw = file.read_bytes()
    need(digest(raw) == manifest_sha,
         "SEALED_MANIFEST_HASH_DRIFT")
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise OriginalColdDenied("F139_V43_COLD_MANIFEST_NOT_CANONICAL") from exc
    need(type(doc) is dict
         and canonical(doc) == raw and set(doc) == FIELDS
         and doc.get("schema") == SCHEMA
         and doc.get("original_source_sha") == v42.BEFORE
         and doc.get("target_source_sha") == target
         and type(doc.get("run_id")) is int
         and doc["run_id"] == run_id
         and type(doc.get("original_head_seq")) is int
         and doc["original_head_seq"] == v42.FROZEN_SEQ
         and doc.get("original_head_sha256") == v42.FROZEN_HEAD
         and type(doc.get("predecessor_backup_run_id")) is int
         and doc["predecessor_backup_run_id"] > 0
         and all(type(doc.get(k)) is str
                 and successor.SHA64.fullmatch(doc[k]) is not None
                 for k in (
                     "predecessor_backup_manifest_sha256",
                     "logical_all_tables_sha256",
                     "provider_archives_manifest_sha256",
                     "generation_binary_manifest_sha256",
                     "negative_custody_manifest_sha256",
                     "restored_sqlite_sha256"))
         and type(doc.get("original_owner_mutations")) is int
         and doc["original_owner_mutations"] == 0
         and type(doc.get("new_dispatches")) is int
         and doc["new_dispatches"] == 0
         and all(doc.get(k) is False for k in (
             "source_transition_authorized", "owner_policy_modified",
             "task_resume_authorized", "hybrid_admission",
             "scientific_first_use")),
         "MANIFEST_FIELDS_OR_AUTHORITY_INVALID")
    return doc


def verify_detached_restore(folder, *, target, run_id, manifest_sha):
    """Reopen every sealed byte, cold-restore SQLite and compare all table rows."""
    doc = _manifest(folder, target=target, run_id=run_id,
                    manifest_sha=manifest_sha)
    files, negatives = bundle._validate_files(folder, doc)
    sqlite_file = folder / "state.sqlite"
    _require_standalone_sqlite(sqlite_file)
    with tempfile.TemporaryDirectory(prefix="f139-v43-detached-") as scratch:
        restored = Path(scratch) / "state.sqlite"
        with _hashed_private_sqlite_snapshot(
                sqlite_file, files["state.sqlite"]) as frozen:
            before = _frozen_meta(frozen)
            need(digest(canonical(rollback_view(frozen.conn))) ==
                 doc["logical_all_tables_sha256"]
                 and required_negative_custody(frozen) == negatives,
                 "FROZEN_ORIGINAL_TABLE_BYTES_DRIFT")
            with closing(sqlite3.connect(
                    str(restored), isolation_level=None)) as target_conn:
                frozen.conn.backup(target_conn)
        _require_standalone_sqlite(restored)
        copy_negative_custody(folder, Path(scratch), negatives,
                              copy_files=True)
        with closing(_open_immutable_hashed_backup(restored)) as final:
            need(_frozen_meta(final) == before
                 and digest(canonical(rollback_view(final.conn))) ==
                     doc["logical_all_tables_sha256"],
                 "DETACHED_RESTORED_TABLES_CHANGED")
        need(_hash_standalone_sqlite(restored) ==
             doc["restored_sqlite_sha256"],
             "DETACHED_RESTORE_SHA_DRIFT")
    bundle._validate_files(folder, doc)
    need(digest((folder / "manifest.sha256.json").read_bytes()) ==
         manifest_sha, "POST_RESTORE_MANIFEST_DRIFT")
    return {
        "schema": SCHEMA, "source_sha": v42.BEFORE,
        "target_source_sha": target,
        "original_head_seq": v42.FROZEN_SEQ,
        "original_head_sha256": v42.FROZEN_HEAD,
        "backup_run_id": run_id,
        "backup_manifest_sha256": manifest_sha,
        "backup_logical_all_tables_sha256":
            doc["logical_all_tables_sha256"],
        "independent_detached_restore_verified": True,
        "provider_archives_bytes_verified": True,
        "generation_binary_bytes_verified": True,
        "negative_custody_bytes_verified": True,
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "task_resume_authorized": False,
        "new_dispatches": 0, "scientific_first_use": False,
    }




def last_source_transition(db):
    """Verify frozen head 1835 and immutable source event 1833 separately.

    The original ledger append-only history contains post-transition owner
    events. Event 1835 is the current *ledger head*, not the transition.
    A backup must validate both without rewriting or relabeling either.
    """
    need(type(db) is Database
         and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1,
         "REAL_COLD_SOURCE_QUERY_ONLY_REQUIRED")
    meta = _frozen_meta(db)
    anchor = db.conn.execute(
        "SELECT seq,sha FROM events WHERE seq=?",
        (v42.FROZEN_SEQ,)).fetchone()
    need(anchor is not None
         and anchor["seq"] == v42.FROZEN_SEQ
         and anchor["sha"] == v42.FROZEN_HEAD
         and meta["head_hash"] == v42.FROZEN_HEAD,
         "FROZEN_LEDGER_HEAD1835_DRIFT")
    row = db.conn.execute(
        "SELECT seq,kind,sha,payload FROM events "
        "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<=? "
        "ORDER BY seq DESC LIMIT 1",
        (v42.FROZEN_SEQ,)).fetchone()
    from f139 import nci04_v41_hybrid_event1833_successor as v40
    need(row is not None
         and row["seq"] == v40.PREDECESSOR_SEQ + 1
         and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and type(row["sha"]) is str
         and successor.SHA64.fullmatch(row["sha"]) is not None
         and type(row["payload"]) is str,
         "ORIGINAL_LAST_V40_SOURCE_EVENT_MISSING")
    try:
        doc = json.loads(row["payload"])
    except (ValueError, TypeError, UnicodeError) as exc:
        raise OriginalColdDenied(
            "F139_V43_COLD_SOURCE_EVENT_PAYLOAD_UNREADABLE") from exc
    need(type(doc) is dict and set(doc) == v40.FIELDS
         and doc.get("schema") == v40.SCHEMA
         and doc.get("to_source_sha") == v42.BEFORE
         and doc.get("from_source_sha") == v40.SOURCE
         and doc.get("original_head_seq") == v40.PREDECESSOR_SEQ
         and doc.get("purpose") == v40.PURPOSE
         and type(doc.get("backup_run_id")) is int
         and doc["backup_run_id"] > 0
         and type(doc.get("backup_manifest_sha256")) is str
         and successor.SHA64.fullmatch(
             doc["backup_manifest_sha256"]) is not None
         and doc.get("scientific_first_use") is False
         and doc.get("hybrid_admission") is False
         and doc.get("new_dispatches") == 0
         and doc.get("task_resume_authorized") is False
         and doc.get("owner_policy_update_authorized") is False
         and event_canonical(doc).decode("ascii") == row["payload"]
         and db.conn.total_changes == 0,
         "ORIGINAL_LAST_V40_SOURCE_PROOF_DRIFT")
    return doc

def stage_full_backup(original, *, target, run_id,
                      release_witness, original_witness):
    """Create-only backup on the existing Windows owner. No task/SQLite writes.

    Caller must authenticate the actual original task, SID and event before
    acquiring the original mutex. All backups and their names are single-use;
    a partial backup can never be silently overwritten or reused.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.filename.is_absolute()
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and type(target) is str
         and successor.SHA40.fullmatch(target) is not None
         and target != v42.BEFORE
         and callable(release_witness)
         and callable(original_witness)
         and release_witness() is True
         and original_witness() is True,
         "EXACT_OWNER_QUERY_ONLY_AND_RELEASE_REQUIRED")
    initial = v42.original_owner_cold_read(original)
    before = _frozen_meta(original)
    prior_doc = last_source_transition(original)
    prior_folder = original.filename.parent / (
        "f139-v40-before-" + str(prior_doc["backup_run_id"]))
    prior.verify_detached_restore(
        prior_folder, target=v42.BEFORE,
        run_id=prior_doc["backup_run_id"],
        manifest_sha=prior_doc["backup_manifest_sha256"])
    old_manifest = json.loads(
        (prior_folder / "manifest.sha256.json").read_bytes())
    old_files, negatives = bundle._validate_files(
        prior_folder, old_manifest)
    folder = backup_folder(original.filename, run_id)
    need(not folder.exists() and not folder.is_symlink()
         and all(bundle._nonlink(p) for p in (
             original.filename.parent, *original.filename.parents))
         and release_witness() is True and original_witness() is True,
         "EXISTING_RESULT_OR_ORIGINAL_OWNER_DRIFT")
    folder.mkdir(mode=0o700, exist_ok=False)
    copy_db = folder / "state.sqlite"
    with closing(sqlite3.connect(
            str(copy_db), isolation_level=None)) as output:
        original.conn.backup(output)
    _require_standalone_sqlite(copy_db)
    sqlite_sha = _hash_standalone_sqlite(copy_db)
    for rel, expected_sha in sorted(old_files.items()):
        if rel == "state.sqlite":
            continue
        src = prior_folder.joinpath(*rel.split("/"))
        dst = folder.joinpath(*rel.split("/"))
        need(src.is_file() and bundle._nonlink(src)
             and digest(src.read_bytes()) == expected_sha
             and not dst.exists() and not dst.is_symlink(),
             "PREDECESSOR_CUSTODY_FILE_DRIFT")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as reader, dst.open("xb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
        need(digest(dst.read_bytes()) == expected_sha,
             "NEW_CUSTODY_FILE_CHANGED")
    files = dict(old_files)
    files["state.sqlite"] = sqlite_sha
    logical = digest(canonical(rollback_view(original.conn)))
    actual_negatives = required_negative_custody(original)
    need(actual_negatives == negatives,
         "ORIGINAL_NEGATIVE_CUSTODY_CHANGED")
    with tempfile.TemporaryDirectory(prefix="f139-v43-verify-") as scratch:
        restored = Path(scratch) / "state.sqlite"
        with _hashed_private_sqlite_snapshot(
                copy_db, sqlite_sha) as copied:
            need(_frozen_meta(copied) == before
                 and digest(canonical(rollback_view(copied.conn))) ==
                     logical, "BACKUP_NOT_ORIGINAL_1835")
            with closing(sqlite3.connect(
                    str(restored), isolation_level=None)) as output:
                copied.conn.backup(output)
        _require_standalone_sqlite(restored)
        copy_negative_custody(folder, Path(scratch), negatives,
                              copy_files=True)
        with closing(_open_immutable_hashed_backup(restored)) as final:
            need(_frozen_meta(final) == before
                 and digest(canonical(rollback_view(final.conn))) ==
                     logical, "DETACHED_RESTORE_NOT_ORIGINAL")
        restored_sha = _hash_standalone_sqlite(restored)
    manifest = {
        "schema": SCHEMA, "original_source_sha": v42.BEFORE,
        "target_source_sha": target, "run_id": run_id,
        "original_head_seq": v42.FROZEN_SEQ,
        "original_head_sha256": v42.FROZEN_HEAD,
        "predecessor_backup_run_id": prior_doc["backup_run_id"],
        "predecessor_backup_manifest_sha256":
            prior_doc["backup_manifest_sha256"],
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
        "hybrid_admission": False,
        "scientific_first_use": False,
    }
    need(set(manifest) == FIELDS, "MANIFEST_SHAPE_DRIFT")
    with (folder / "manifest.sha256.json").open("xb") as stream:
        stream.write(canonical(manifest))
    manifest_sha = digest(canonical(manifest))
    verified = verify_detached_restore(
        folder, target=target, run_id=run_id,
        manifest_sha=manifest_sha)
    need(release_witness() is True
         and original_witness() is True
         and original.meta() == before
         and original.conn.total_changes == 0,
         "OWNER_MOVED_DURING_COLD_BACKUP")
    need(initial["original_head_seq"] == before["head_seq"]
         and initial["original_head_sha256"] == before["head_hash"],
         "ORIGINAL_READBACK_MISMATCH")
    return verified

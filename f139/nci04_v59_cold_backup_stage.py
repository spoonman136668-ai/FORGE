"""Create-only, source-bound V59 cold bundle library; no task or release route.

The independent owner caller must first quiesce the one original Windows
task AND hold the original kernel mutex. This source never controls it.
"""
from __future__ import annotations
from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import sqlite3

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)
from f139.nci04_v59_cold_backup_verify import MIN_RUN, verify_original_cold_backup
from f139.nci04_v32_original_owner_transition_cli import (
    copy_provider_archives, copy_generation_executable,
)
from f139 import nci04_v41_cold_copy_verifier as cold

SCHEMA = "forge.f139.v59.original-cold-createonly.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")

class V59ColdStageDenied(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise V59ColdStageDenied("F139_V59_COLD_STAGE_" + code)

def hash_file(path):
    digestor = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digestor.update(block)
    return digestor.hexdigest()

def inventory(folder):
    files = set()
    for parent, dirs, names in os.walk(folder, followlinks=False):
        for name in (*dirs, *names):
            child = Path(parent) / name
            need(not child.is_symlink()
                 and not getattr(child, "is_junction", lambda: False)(),
                 "BUNDLE_LINK_OR_JUNCTION")
            if name in names:
                need(child.is_file(), "UNEXPECTED_FILE_TYPE")
                files.add(child.relative_to(folder).as_posix())
    return files

def stage_original_cold_backup(original: Database, *, target: str,
                               owner_run_id: int) -> dict:
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.conn.total_changes == 0,
         "ORIGINAL_READONLY_REQUIRED")
    need(type(owner_run_id) is int and owner_run_id > MIN_RUN
         and type(target) is str and SHA40.fullmatch(target) is not None
         and target != SOURCE, "RUN_OR_TARGET_INVALID")
    origin = Path(original.filename)
    need(origin.is_absolute() and origin.name == "state.sqlite"
         and origin.parent.name == "FORGE-F139"
         and origin.is_file() and not origin.is_symlink()
         and not origin.parent.is_symlink()
         and not getattr(origin.parent, "is_junction", lambda: False)()
         and SingleOwner.held(origin.with_suffix(".lock")),
         "ORIGINAL_IDENTITY_OR_MUTEX_MISSING")
    original.verify()
    before = audit_frozen_original_readonly(original)
    need(before["source_sha"] == SOURCE
         and before["head_seq"] == HEAD_SEQ
         and before["head_sha256"] == HEAD_SHA256
         and original.conn.total_changes == 0,
         "ORIGINAL_PREIMAGE_DRIFT")
    folder = origin.parent / ("f139-v59-before-" + str(owner_run_id))
    need(not folder.exists() and not folder.is_symlink(),
         "CREATE_ONLY_EXISTING_RUN_DENIED")
    folder.mkdir(mode=0o700, exist_ok=False)
    backup = folder / "state.sqlite"
    # Native SQLite backup includes committed WAL contents.
    with closing(sqlite3.connect(str(backup), isolation_level=None)) as dst:
        original.conn.backup(dst, pages=256, sleep=0.02)
    cold._require_standalone_sqlite(backup)
    need(backup.is_file() and 1024 < backup.stat().st_size <= cold.MAX_BACKUP_BYTES,
         "SQLITE_BACKUP_INVALID")
    negatives = cold.copy_negative_custody(
        origin.parent, folder, cold.required_negative_custody(original),
        copy_files=True)
    archives = copy_provider_archives(original, folder, copy_files=True)
    binary = copy_generation_executable(original, folder, copy_files=True)
    need(bool(archives) and len(binary) == 1
         and not(set(negatives) & (set(archives) | set(binary)))
         and not(set(archives) & set(binary)), "CUSTODY_COLLISION_OR_MISSING")
    copy_sha = hash_file(backup)
    certified = verify_original_cold_backup(
        original, backup, owner_run_id=owner_run_id,
        target=target, expected_backup_sha256=copy_sha)
    need(certified["from_source_sha"] == SOURCE
         and certified["to_source_sha"] == target
         and certified["original_head_seq"] == HEAD_SEQ
         and certified["original_head_sha256"] == HEAD_SHA256
         and certified["backup_sqlite_sha256"] == copy_sha
         and certified["original_owner_mutations"] == 0
         and certified["source_transition_authorized"] is False
         and certified["scientific_first_use"] is False,
         "COLD_VERIFIER_REJECTED")
    files = {"state.sqlite": copy_sha, **negatives, **archives, **binary}
    need(len(files) == 1+len(negatives)+len(archives)+len(binary)
         and inventory(folder) == set(files),
         "CUSTODY_INVENTORY_INVALID")
    for name, wanted in files.items():
        need(type(name) is str and name != "manifest.sha256.json"
             and all(p not in ("", ".", "..") for p in name.split("/"))
             and type(wanted) is str and SHA64.fullmatch(wanted) is not None,
             "INVALID_FILE_IDENTITY")
        path = folder.joinpath(*name.split("/"))
        need(path.is_file() and not path.is_symlink()
             and path.resolve().is_relative_to(folder.resolve())
             and hash_file(path) == wanted, "COPIED_FILE_HASH_DRIFT")
    need(original.conn.total_changes == 0
         and audit_frozen_original_readonly(original) == before,
         "ORIGINAL_CHANGED_DURING_COPY")
    manifest = {
        "schema": SCHEMA, "owner_run_id": owner_run_id,
        "original_source_sha": SOURCE, "target_source_sha": target,
        "original_head_seq": HEAD_SEQ, "original_head_sha256": HEAD_SHA256,
        "files_sha256": dict(sorted(files.items())),
        "logical_all_tables_sha256": certified["logical_all_tables_sha256"],
        "negative_custody_sha256": certified["negative_custody_sha256"],
        "provider_archives_sha256": certified["provider_archives_sha256"],
        "genenv_executable_custody_sha256":
            certified["genenv_executable_custody_sha256"],
        "owner_quiescence_verified": False, "owner_mutations": 0,
        "source_transition_authorized": False, "scientific_first_use": False,
        "new_controller": False, "new_scheduler": False,
        "new_dispatches": 0, "replay_authorized": False,
    }
    encoded = canonical(manifest)
    seal = folder / "manifest.sha256.json"
    with seal.open("xb") as dst:
        dst.write(encoded)
    need(seal.read_bytes() == encoded
         and inventory(folder) == set(files) | {"manifest.sha256.json"}
         and hash_file(backup) == copy_sha, "SEALED_READBACK_DRIFT")
    return {
        "schema": SCHEMA, "owner_run_id": owner_run_id,
        "from_source_sha": SOURCE, "to_source_sha": target,
        "original_head_seq": HEAD_SEQ, "original_head_sha256": HEAD_SHA256,
        "backup_sqlite_sha256": copy_sha,
        "manifest_sha256": digest(encoded), "file_count": len(files),
        "original_mutations": 0, "owner_quiescence_verified": False,
        "source_transition_authorized": False, "scientific_first_use": False,
        "new_controller": False, "new_scheduler": False,
        "replay_authorized": False,
    }

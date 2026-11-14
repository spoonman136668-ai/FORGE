"""V41-to-public-Hybrid SQLite backup freshness: read-only component only.

This verifies SQLite backup parity with the *current* original owner ledger.
It does NOT produce a backup, verify external provider ZIP/binary custody,
authorize the source/policy transition, create a worker ref, or run any task.
It is a component for a later separately approved exact-owner release.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile

from f139.local_controller import Database, SingleOwner
from f139.hybrid_owner_admission import is_migrated
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view

V41_SOURCE = "1a40fe4e3ec6e93a1631d59863b95e90981d734e"
HYBRID_PR_NUMBER = 1660
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
MIN_V41_HEAD = 1829
MAX_SQLITE_BYTES = 1_000_000_000
RUN_NAME = re.compile(r"f139-hybrid-before-([1-9][0-9]*)\Z")


class HybridColdPairDenied(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise HybridColdPairDenied("F139_HYBRID_COLD_PAIR_" + code)


def _file_identity(path):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_size > 0
         and info.st_size <= MAX_SQLITE_BYTES and info.st_nlink == 1,
         "BACKUP_REGULAR_FILE_REQUIRED")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _no_sidecars(path):
    for suffix in ("-wal", "-shm", "-journal"):
        other = Path(str(path) + suffix)
        need(not other.exists() and not other.is_symlink(),
             "BACKUP_SIDECAR_FORBIDDEN")


def _hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _authenticate_candidate(get, target_sha):
    # Authenticated native GitHub provider is mandatory; a caller's SHA
    # string, issue text, or CI-success label alone is not source authority.
    need(callable(get) and type(target_sha) is str
         and SHA40.fullmatch(target_sha) is not None
         and target_sha != V41_SOURCE, "CANDIDATE_SHA_INVALID")
    main = get("repos/spoonman136668-ai/FORGE/branches/main")
    pr = get("repos/spoonman136668-ai/FORGE/pulls/1660")
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == V41_SOURCE
         and type(pr) is dict and pr.get("number") == HYBRID_PR_NUMBER
         and pr.get("state") == "open" and pr.get("merged") is False
         and type(pr.get("head")) is dict
         and pr["head"].get("sha") == target_sha
         and type(pr.get("base")) is dict
         and pr["base"].get("sha") == V41_SOURCE
         and pr["base"].get("ref") == "main",
         "PROTECTED_PR_SOURCE_DRIFT")
    return target_sha


def verify_original_sqlite_pair(original, backup, *, target_sha, get):
    """Cold-compare a standalone SQLite backup under the original owner lock.

    The caller must independently establish task SID/lease, exact provider
    custody, backup producer identity, GitHub refs/CI and owner approval.
    Synthetic fixtures are not original-owner acceptance evidence.
    """
    need(type(original) is Database and original.filename.is_absolute()
         and original.filename.name == "state.sqlite"
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock")),
         "READONLY_ORIGINAL_MUTEX_REQUIRED")
    _authenticate_candidate(get, target_sha)
    backup = Path(backup)
    original_root = original.filename.parent
    need(backup.is_absolute() and backup.name == "state.sqlite"
         and backup.parent.parent.resolve(strict=True) == original_root.resolve(strict=True)
         and RUN_NAME.fullmatch(backup.parent.name) is not None
         and backup.parent.is_dir() and not backup.parent.is_symlink()
         and not getattr(backup.parent, "is_junction", lambda: False)()
         and not backup.is_symlink()
         and not getattr(backup, "is_junction", lambda: False)()
         and backup != original.filename,
         "BACKUP_PATH_NOT_OWNER_SCOPED")
    _no_sidecars(backup)
    first_identity = _file_identity(backup)

    original.verify()
    before = original.meta().copy()
    need(before["source_sha"] == V41_SOURCE
         and before["enabled"] == 1 and before["legacy_suspended"] == 1
         and type(before["head_seq"]) is int
         and before["head_seq"] >= MIN_V41_HEAD
         and type(before["head_hash"]) is str
         and len(before["head_hash"]) == 64
         and original.dual_native_schema()
         and verify_native_activation(original)
         and original.ready() is None and not original.actives()
         and not is_migrated(original)
         and original.conn.total_changes == 0,
         "ORIGINAL_V41_HEAD_OR_OWNER_DRIFT")
    current = rollback_view(original.conn)

    # Snapshot the opened file descriptor once into verifier-owned scratch,
    # hashing the same bytes rather than reopening an attacker-swappable path.
    with tempfile.TemporaryDirectory(prefix="f139-hybrid-verified-") as temp:
        private = Path(temp) / "state.sqlite"
        h = hashlib.sha256()
        total = 0
        with backup.open("rb") as source, private.open("xb") as dest:
            opened = os.fstat(source.fileno())
            need((opened.st_dev, opened.st_ino, opened.st_size,
                  opened.st_mtime_ns) == first_identity,
                 "BACKUP_REPLACED_BEFORE_READ")
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                need(total <= MAX_SQLITE_BYTES, "BACKUP_TOO_LARGE")
                h.update(block)
                dest.write(block)
            dest.flush()
        need(total == first_identity[2] and
             _hash_file(private) == h.hexdigest(),
             "VERIFIER_SNAPSHOT_CONTENT_DRIFT")
        # immutable=1 never creates WAL/SHM sidecars on the frozen scratch.
        uri = private.as_uri() + "?mode=ro&immutable=1"
        with closing(sqlite3.connect(uri, uri=True, isolation_level=None)) as con:
            con.execute("PRAGMA query_only=ON")
            need(con.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                 "COLD_SQLITE_INTEGRITY_FAILED")
            copied = rollback_view(con)
            need(current == copied, "COLD_ALL_TABLE_PARITY_FAILED")
        need(_hash_file(private) == h.hexdigest(),
             "VERIFIER_SNAPSHOT_CHANGED")
        sealed_sqlite_sha256 = h.hexdigest()

    _no_sidecars(backup)
    need(_file_identity(backup) == first_identity
         and _hash_file(backup) == sealed_sqlite_sha256,
         "BACKUP_CHANGED_DURING_VERIFICATION")
    _authenticate_candidate(get, target_sha)
    original.verify()
    need(original.meta() == before
         and original.conn.total_changes == 0
         and rollback_view(original.conn) == current,
         "ORIGINAL_CHANGED_DURING_VERIFICATION")
    return {
        "schema": "forge.f139.v41-hybrid.sqlite-cold-pair-only.v1",
        "from_source_sha": V41_SOURCE,
        "to_source_sha": target_sha,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "standalone_sqlite_sha256": sealed_sqlite_sha256,
        "logical_all_tables_sha256": digest(canonical(current)),
        "original_sqlite_mutations": 0,
        "provider_archives_cold_restored": False,
        "generation_binary_cold_restored": False,
        "original_task_modified": False,
        "owner_release_authorized": False,
        "hybrid_policy_active": False,
        "signed_worker_dispatched": False,
        "scientific_first_use": False,
    }

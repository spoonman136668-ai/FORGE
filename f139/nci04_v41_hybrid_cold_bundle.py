"""Detached, current-V41 public-Hybrid cold backup + full custody rehearsal.

Source-only library.  The caller must *separately* prove the original Windows
task is quiesced and hold its native SingleOwner mutex.  No CLI, scheduler,
controller, policy writer, release ref, merge, first-use or task dispatch.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_v38_original_owner_transition_cli import rollback_view
from f139.nci04_v41_offline_cold_bundle import _manifest_entry
from f139 import nci04_v41_cold_copy_verifier as cold
from f139 import nci04_v41_hybrid_cold_pair as pair

SCHEMA = "forge.f139.v41-hybrid.complete-cold-bundle.v1"
RESTORE_SCHEMA = "forge.f139.v41-hybrid.independent-detached-restore.v1"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_FILES = 10000
FIELDS = frozenset({
    "schema", "original_source_sha", "candidate_sha", "run_id",
    "original_head_seq", "original_head_sha256", "files_sha256",
    "logical_all_tables_sha256", "provider_archives_manifest_sha256",
    "generation_binary_manifest_sha256", "negative_custody_manifest_sha256",
    "restored_sqlite_sha256", "owner_quiescence_verified",
    "source_transition_authorized", "owner_policy_modified",
    "original_owner_mutations", "new_dispatches", "scientific_first_use",
    "hybrid_admission", "worker_dispatched",
})


class HybridBundleDenied(ValueError):
    pass


def need(condition, why):
    if not condition:
        raise HybridBundleDenied("F139_V41_HYBRID_BUNDLE_" + why)


def _name(run_id):
    need(type(run_id) is int and run_id > 0, "RUN_ID_INVALID")
    return "f139-hybrid-before-" + str(run_id)


def _nonlink(path):
    return not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()


def _folder(folder, run_id):
    folder = Path(folder)
    need(folder.is_absolute() and folder.is_dir()
         and folder.name == _name(run_id)
         and all(_nonlink(p) for p in (folder, *folder.parents)),
         "BUNDLE_PATH_NOT_CANONICAL")
    return folder


def _actual_files(folder):
    result = set()
    count = 0
    for root, dirs, names in os.walk(folder, followlinks=False):
        for name in (*dirs, *names):
            entry = Path(root) / name
            count += 1
            need(count <= MAX_FILES and _nonlink(entry),
                 "UNTRUSTED_LINK_OR_UNBOUNDED_ENTRIES")
            if name in names:
                need(entry.is_file(), "BUNDLE_NONFILE")
                result.add(entry.relative_to(folder).as_posix())
    return result


def _validate_files(folder, manifest):
    files = manifest["files_sha256"]
    need(type(files) is dict and 3 <= len(files) <= MAX_FILES
         and "state.sqlite" in files
         and all(type(key) is str and type(val) is str
                 and SHA64.fullmatch(val) is not None
                 for key, val in files.items()), "MANIFEST_FILES_INVALID")
    archives = {k: v for k, v in files.items()
                if k.startswith("provider-custody/")}
    binaries = {k: v for k, v in files.items()
                if k.startswith("prior-generation-custody/")}
    negatives = {k: v for k, v in files.items()
                 if k.startswith("native-negative/")}
    negative_definitions = {relative: sha
                            for _, relative, sha in cold._negative_definitions()}
    want_binary = ("prior-generation-custody/"
                   + pair.V41_SOURCE + "/f139-genenv-source.exe")
    need(bool(archives) and set(binaries) == {want_binary}
         and set(negatives).issubset(negative_definitions)
         and all(negative_definitions[k] == v for k, v in negatives.items())
         and set(files) == {"state.sqlite", *archives, *binaries, *negatives}
         and digest(canonical(archives)) ==
             manifest["provider_archives_manifest_sha256"]
         and digest(canonical(binaries)) ==
             manifest["generation_binary_manifest_sha256"]
         and digest(canonical(negatives)) ==
             manifest["negative_custody_manifest_sha256"],
         "ARCHIVES_BINARY_OR_NEGATIVE_SET_DRIFT")
    need(_actual_files(folder) == set(files) | {"manifest.sha256.json"},
         "UNLISTED_OR_MISSING_FILE")
    for relative, expected in files.items():
        _manifest_entry(folder, relative, expected)

    packages = {}
    for relative in archives:
        parts = relative.split("/")
        need(len(parts) == 4 and parts[0] == "provider-custody"
             and re.fullmatch(r"f139-nci04-[a-z0-9-]{1,180}", parts[1]) is not None
             and parts[2].isdigit() and int(parts[2]) > 0
             and parts[3] in ("manifest.json", "ubuntu-latest.zip",
                               "windows-latest.zip"),
             "PROVIDER_ARCHIVE_PATH_INVALID")
        packages.setdefault(tuple(parts[:3]), set()).add(parts[3])
        bound = 16384 if parts[3] == "manifest.json" else 2_000_000
        need(folder.joinpath(*parts).stat().st_size <= bound,
             "PROVIDER_FILE_SIZE_EXCEEDED")
    for prefix, names in packages.items():
        need(names == {"manifest.json", "ubuntu-latest.zip",
                        "windows-latest.zip"}, "PROVIDER_ARCHIVE_INCOMPLETE")
        data = folder.joinpath(*prefix, "manifest.json").read_bytes()
        try:
            doc = json.loads(data)
        except (UnicodeError, ValueError) as error:
            raise HybridBundleDenied(
                "F139_V41_HYBRID_BUNDLE_PROVIDER_MANIFEST_UNREADABLE") from error
        expected = {platform: archives["/".join((*prefix, platform + ".zip"))]
                    for platform in ("ubuntu-latest", "windows-latest")}
        need(type(doc) is dict and doc.get("ticket") == prefix[1]
             and type(doc.get("run_id")) is int
             and doc["run_id"] == int(prefix[2])
             and doc.get("sha256") == expected,
             "PROVIDER_ARCHIVE_MANIFEST_DRIFT")
    need(0 < folder.joinpath(*want_binary.split("/")).stat().st_size
         <= 16_000_000, "GENERATOR_BINARY_SIZE")
    backup = folder / "state.sqlite"
    cold._require_standalone_sqlite(backup)
    need(0 < backup.stat().st_size <= cold.MAX_BACKUP_BYTES,
         "SQLITE_SIZE_OUT_OF_RANGE")
    return files, negatives


def verify_detached_restore(folder, *, expected_manifest_sha256, target_sha,
                            run_id, expected_head_seq, expected_head_sha256):
    """Independently exercise recovery without the original DB or any network.

    The receipt is for backup data and provider/binary *bytes*, not restoration
    of a running controller or live original provider paths.
    """
    need(type(expected_manifest_sha256) is str
         and SHA64.fullmatch(expected_manifest_sha256) is not None
         and type(expected_head_sha256) is str
         and SHA64.fullmatch(expected_head_sha256) is not None
         and type(expected_head_seq) is int
         and expected_head_seq >= pair.MIN_V41_HEAD
         and type(target_sha) is str
         and pair.SHA40.fullmatch(target_sha) is not None
         and target_sha != pair.V41_SOURCE,
         "INDEPENDENT_ANCHORS_MISSING")
    folder = _folder(folder, run_id)
    sealed = folder / "manifest.sha256.json"
    need(sealed.is_file() and _nonlink(sealed)
         and 0 < sealed.stat().st_size <= 1_000_000,
         "MANIFEST_MISSING_OR_OVERSIZE")
    raw = sealed.read_bytes()
    need(digest(raw) == expected_manifest_sha256,
         "INDEPENDENT_MANIFEST_HASH_MISMATCH")
    try:
        manifest = json.loads(raw)
    except (UnicodeError, ValueError) as error:
        raise HybridBundleDenied(
            "F139_V41_HYBRID_BUNDLE_MANIFEST_UNREADABLE") from error
    need(type(manifest) is dict and set(manifest) == FIELDS
         and canonical(manifest) == raw
         and manifest["schema"] == SCHEMA
         and manifest["original_source_sha"] == pair.V41_SOURCE
         and manifest["candidate_sha"] == target_sha
         and type(manifest["run_id"]) is int
         and manifest["run_id"] == run_id
         and type(manifest["original_head_seq"]) is int
         and manifest["original_head_seq"] == expected_head_seq
         and manifest["original_head_sha256"] == expected_head_sha256
         and all(type(manifest[k]) is str
                 and SHA64.fullmatch(manifest[k]) is not None for k in (
                     "logical_all_tables_sha256",
                     "provider_archives_manifest_sha256",
                     "generation_binary_manifest_sha256",
                     "negative_custody_manifest_sha256",
                     "restored_sqlite_sha256"))
         and all(manifest[k] is False for k in (
             "owner_quiescence_verified", "source_transition_authorized",
             "owner_policy_modified", "scientific_first_use",
             "hybrid_admission", "worker_dispatched"))
         and type(manifest["original_owner_mutations"]) is int
         and manifest["original_owner_mutations"] == 0
         and type(manifest["new_dispatches"]) is int
         and manifest["new_dispatches"] == 0,
         "MANIFEST_OR_RELEASE_BOUNDARY_DRIFT")
    files, negatives = _validate_files(folder, manifest)
    backup = folder / "state.sqlite"

    with tempfile.TemporaryDirectory(prefix="f139-v41-hybrid-detached-") as tmp:
        restored = Path(tmp) / "state.sqlite"
        # The original cannot be referenced; preserve all files needed for
        # independent Database.verify, including frozen negative ZIP evidence.
        with cold._hashed_private_sqlite_snapshot(
                backup, files["state.sqlite"]) as copied:
            copied.verify()
            need(cold.required_negative_custody(copied) == negatives
                 and copied.meta()["source_sha"] == pair.V41_SOURCE
                 and copied.meta()["head_seq"] == expected_head_seq
                 and copied.meta()["head_hash"] == expected_head_sha256
                 and digest(canonical(rollback_view(copied.conn))) ==
                     manifest["logical_all_tables_sha256"],
                 "INDEPENDENT_COLD_SQLITE_DRIFT")
            with closing(sqlite3.connect(str(restored), isolation_level=None)) as dst:
                copied.conn.backup(dst)
        cold._require_standalone_sqlite(restored)
        cold.copy_negative_custody(folder, Path(tmp), negatives, copy_files=True)
        with closing(cold._open_immutable_hashed_backup(restored)) as final:
            final.verify()
            need(final.meta()["source_sha"] == pair.V41_SOURCE
                 and final.meta()["head_seq"] == expected_head_seq
                 and final.meta()["head_hash"] == expected_head_sha256
                 and digest(canonical(rollback_view(final.conn))) ==
                     manifest["logical_all_tables_sha256"],
                 "DETACHED_RESTORED_HISTORY_OR_TABLES_DRIFT")
        need(cold._hash_standalone_sqlite(restored) ==
             manifest["restored_sqlite_sha256"],
             "DETACHED_RESTORE_DIGEST_DRIFT")

    _validate_files(folder, manifest)
    need(digest(sealed.read_bytes()) == expected_manifest_sha256,
         "MANIFEST_CHANGED_DURING_RESTORE")
    return {
        "schema": RESTORE_SCHEMA,
        "original_source_sha": pair.V41_SOURCE,
        "candidate_sha": target_sha, "original_head_seq": expected_head_seq,
        "original_head_sha256": expected_head_sha256,
        "manifest_sha256": expected_manifest_sha256,
        "logical_all_tables_sha256": manifest["logical_all_tables_sha256"],
        "provider_archives_bytes_verified": True,
        "generation_binary_bytes_verified": True,
        "independent_detached_restore_verified": True,
        "original_owner_host_verified": False,
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "hybrid_admission": False, "worker_dispatched": False,
        "scientific_first_use": False,
    }


def stage_complete_cold_bundle(original, get, *, target_sha, run_id):
    """Create-only, no-retry backup from separately quiesced original owner.

    An authentic SID/task/lease and controller stop are NOT established here;
    the caller must verify those in its separately qualified original workflow.
    """
    need(type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(original.filename.with_suffix(".lock"))
         and callable(get), "ORIGINAL_LOCKED_QUERY_ONLY_REQUIRED")
    origin = Path(original.filename)
    need(origin.is_absolute() and origin.name == "state.sqlite"
         and origin.is_file() and all(_nonlink(p) for p in
                                     (origin, origin.parent)),
         "ORIGINAL_PATH_OR_LINK_DRIFT")
    pair._authenticate_candidate(get, target_sha)
    original.verify()
    before = original.meta().copy()
    need(before["source_sha"] == pair.V41_SOURCE
         and before["head_seq"] >= pair.MIN_V41_HEAD
         and before["enabled"] == 1
         and before["legacy_suspended"] == 1
         and original.dual_native_schema()
         and pair.verify_native_activation(original)
         and original.ready() is None and not original.actives()
         and not pair.is_migrated(original)
         and original.conn.total_changes == 0,
         "ORIGINAL_V41_LEDGER_OR_OWNER_NOT_IDLE")

    folder = origin.parent / _name(run_id)
    need(not folder.exists() and not folder.is_symlink(),
         "BACKUP_RUN_REPLAY_OR_PARTIAL_STAGE")
    folder.mkdir(mode=0o700, exist_ok=False)
    backup = folder / "state.sqlite"
    # A raw copy of the live WAL database may lose committed data.
    with closing(sqlite3.connect(str(backup), isolation_level=None)) as dst:
        original.conn.backup(dst)
    cold._require_standalone_sqlite(backup)

    negatives = cold.copy_negative_custody(
        origin.parent, folder, cold.required_negative_custody(original),
        copy_files=True)
    archives = cold.copy_provider_archives(original, folder, copy_files=True)
    binary = cold.copy_generation_executable(original, folder, copy_files=True)
    need(type(archives) is dict and bool(archives)
         and type(binary) is dict and len(binary) == 1
         and type(negatives) is dict,
         "ORIGINAL_CUSTODY_MISSING")

    check = pair.verify_original_sqlite_pair(
        original, backup, target_sha=target_sha, get=get)
    backup_sha = check["standalone_sqlite_sha256"]
    files = {"state.sqlite": backup_sha, **archives, **binary, **negatives}
    need(len(files) == len(archives) + len(binary) + len(negatives) + 1,
         "DUPLICATE_FILES_IN_MANIFEST")
    # Independently restore the actual WAL-inclusive backup into a new DB,
    # instead of trusting only an in-place SQLite quick_check.
    with tempfile.TemporaryDirectory(prefix="f139-v41-hybrid-restore-") as tmp:
        restored = Path(tmp) / "state.sqlite"
        with cold._hashed_private_sqlite_snapshot(backup, backup_sha) as frozen:
            frozen.verify()
            need(frozen.meta() == before
                 and digest(canonical(rollback_view(frozen.conn))) ==
                     check["logical_all_tables_sha256"],
                 "COPY_NOT_CURRENT_ORIGINAL_HISTORY")
            with closing(sqlite3.connect(str(restored), isolation_level=None)) as dst:
                frozen.conn.backup(dst)
        cold._require_standalone_sqlite(restored)
        cold.copy_negative_custody(folder, Path(tmp), negatives, copy_files=True)
        with closing(cold._open_immutable_hashed_backup(restored)) as final:
            final.verify()
            need(final.meta() == before
                 and digest(canonical(rollback_view(final.conn))) ==
                     check["logical_all_tables_sha256"],
                 "DETACHED_RESTORE_NOT_IDENTICAL")
        restored_sha = cold._hash_standalone_sqlite(restored)

    need(original.meta() == before and original.conn.total_changes == 0,
         "ORIGINAL_CHANGED_WHILE_STAGING")
    manifest = {
        "schema": SCHEMA,
        "original_source_sha": pair.V41_SOURCE,
        "candidate_sha": target_sha, "run_id": run_id,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "files_sha256": dict(sorted(files.items())),
        "logical_all_tables_sha256": check["logical_all_tables_sha256"],
        "provider_archives_manifest_sha256": digest(canonical(archives)),
        "generation_binary_manifest_sha256": digest(canonical(binary)),
        "negative_custody_manifest_sha256": digest(canonical(negatives)),
        "restored_sqlite_sha256": restored_sha,
        "owner_quiescence_verified": False,
        "source_transition_authorized": False,
        "owner_policy_modified": False,
        "original_owner_mutations": 0, "new_dispatches": 0,
        "scientific_first_use": False, "hybrid_admission": False,
        "worker_dispatched": False,
    }
    need(set(manifest) == FIELDS, "MANIFEST_SCHEMA_ERROR")
    encoded = canonical(manifest)
    with (folder / "manifest.sha256.json").open("xb") as stream:
        stream.write(encoded)
        stream.flush()
    manifest_sha256 = digest(encoded)
    # Always require independent detached verification before reporting PASS.
    detached = verify_detached_restore(
        folder, expected_manifest_sha256=manifest_sha256,
        target_sha=target_sha, run_id=run_id,
        expected_head_seq=before["head_seq"],
        expected_head_sha256=before["head_hash"])
    pair._authenticate_candidate(get, target_sha)
    need(original.meta() == before and original.conn.total_changes == 0,
         "POST_BUNDLE_ORIGINAL_DRIFT")
    return {
        "schema": SCHEMA, "manifest_sha256": manifest_sha256,
        "original_head_seq": before["head_seq"],
        "original_head_sha256": before["head_hash"],
        "candidate_sha": target_sha,
        "independent_detached_restore_verified":
            detached["independent_detached_restore_verified"],
        "provider_archives_bytes_verified":
            detached["provider_archives_bytes_verified"],
        "generation_binary_bytes_verified":
            detached["generation_binary_bytes_verified"],
        "original_owner_mutations": 0,
        "source_transition_authorized": False,
        "hybrid_admission": False, "scientific_first_use": False,
    }

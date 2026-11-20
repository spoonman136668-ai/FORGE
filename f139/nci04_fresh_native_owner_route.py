"""Inert fresh F139 native-development route inside the EXISTING controller.

This is a source-only, non-mutating classifier for a separately staged F139
development SQLite, including a future versioned local activation event.
It prevents original legacy/native tick, D2K feed, G3/G29 publication and
worker dispatch under BOTH staged states. The existence of an activation
event is NOT original-host release, science or model-continuation authority.

Later versioned activation must be a distinct, independently authenticated
original-Windows-owner transition, not a reinterpretation of this result.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3

from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_dev_epoch import (
    SCHEMA as STAGE_SCHEMA, hash_file,
)
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSIONS_SCHEMA
from f139.nci04_fresh_yggdrasil_boundary import (
    RECEIPT_SCHEMA as YGG_SCHEMA,
    ACCEPTED, AMALGAM_HEAD, LINEAGE_HEAD,
)
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.local_controller import Database, ZERO

RUN = re.compile(r"f139-fresh-dev-([1-9][0-9]{0,19})\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA = "forge.f139.fresh-development-owner-route-disabled.v1"


class FreshNativeRouteDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise FreshNativeRouteDenied("F139_FRESH_NATIVE_ROUTE_" + code)


def _sealed_json(path: Path) -> tuple[dict, bytes]:
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size <= 256_000
         and path.stat().st_size > 2, "PROVENANCE_FILE_NOT_SEALED")
    data = path.read_bytes()
    try:
        doc = json.loads(data)
    except (UnicodeError, ValueError) as exc:
        raise FreshNativeRouteDenied(
            "F139_FRESH_NATIVE_ROUTE_PROVENANCE_JSON_INVALID") from exc
    need(type(doc) is dict and canonical(doc) == data,
         "PROVENANCE_NOT_CANONICAL")
    return doc, data


def inspect_staged_fresh_native_mode(db: Database, db_path: Path) -> dict | None:
    """Return a fixed inert status for the exact fresh-stage path; no writes.

    A non-fresh SQLite returns None and leaves the historical run_once path
    entirely unchanged. A fresh-shaped SQLite fails closed if any source,
    stage, provenance file or live state differs from its disabled stage.
    This routine has no provider client and deliberately never creates one.
    """
    # Legacy F139 test discovery can load local_controller via the
    # unqualified module alias, producing a distinct Python class object.
    # Do not apply fresh-only class/custody restrictions to NON-fresh DBs:
    # the existing historical run_once path must remain byte-compatible.
    need(isinstance(db_path, (Path, str)),
         "DATABASE_ARGUMENT_INVALID")
    path = Path(db_path)
    folder = path.parent
    run_match = RUN.fullmatch(folder.name)
    if run_match is None:
        need(not folder.name.startswith("f139-fresh-dev-"),
             "FRESH_DIRECTORY_NAME_INVALID")
        return None
    # python -m f139.local_controller executes that source as __main__, and
    # unittest discovery also uses local_controller; those are DISTINCT
    # Python class objects from an imported f139.local_controller.Database.
    # Validate the actual SQLite object and known module aliases instead of
    # rejecting the one genuine Windows CLI production entrypoint.
    cls = type(db)
    need(cls.__name__ == "Database"
         and cls.__module__ in (
             "f139.local_controller", "local_controller", "__main__")
         and isinstance(getattr(db, "filename", None), Path)
         and isinstance(getattr(db, "conn", None), sqlite3.Connection)
         and callable(getattr(db, "verify", None))
         and callable(getattr(db, "meta", None)),
         "FRESH_DATABASE_CLASS_INVALID")
    run_id = int(run_match.group(1))
    need(path.name == "state.sqlite" and path.is_file()
         and not path.is_symlink() and not folder.is_symlink()
         and folder.parent.name == "FORGE-F139"
         and not folder.parent.is_symlink()
         and not getattr(folder, "is_junction", lambda: False)()
         and not getattr(folder.parent, "is_junction", lambda: False)()
         and path.resolve() == db.filename.resolve(),
         "FRESH_PATH_OR_OWNER_IDENTITY_INVALID")
    # Every source-custody file is created by the independently qualified
    # original-owner inert staging path. Validate its bytes, never copy it.
    manifest, encoded = _sealed_json(
        folder / "fresh-dev-manifest.sha256.json")
    exclusions, exclusions_bytes = _sealed_json(
        folder / "consumed-development-identities.json")
    lineage, lineage_bytes = _sealed_json(
        folder / "yggdrasil-research-lineage.json")
    source = db.meta()
    need(manifest.get("schema") == STAGE_SCHEMA
         and type(manifest.get("owner_run_id")) is int
         and manifest["owner_run_id"] == run_id
         and manifest.get("previous_source_sha") == SOURCE
         and manifest.get("historical_head_seq") == HEAD_SEQ
         and manifest.get("historical_head_sha256") == HEAD_SHA256
         and manifest.get("yggdrasil_accepted_main_sha") == ACCEPTED
         and manifest.get("yggdrasil_amalgam_draft_head_sha") == AMALGAM_HEAD
         and manifest.get("yggdrasil_lineage_draft_head_sha") == LINEAGE_HEAD
         and manifest.get("original_sqlite_preserved") is True
         and manifest.get("original_owner_mutations") == 0
         and manifest.get("original_task_mutations") == 0
         and manifest.get("fresh_database_enabled") is False
         and manifest.get("fresh_queue_entries") == 0
         and manifest.get("old_work_replay_authorized") is False
         and manifest.get("scientific_first_use") is False
         and manifest.get("source_transition_authorized") is False
         and manifest.get("owner_task_rebind_authorized") is False
         and manifest.get("new_controller") is False
         and manifest.get("new_scheduler") is False
         and manifest.get("worker_dispatched") is False
         and manifest.get("paid_model_calls") == 0
         and manifest.get("release_qualified") is False,
         "STAGE_MANIFEST_NOT_DISABLED")
    root = folder.parent
    need(manifest.get("fresh_state_relative_path") ==
         (folder.name + "/state.sqlite")
         and manifest.get("historical_consumed_exclusions_path") ==
             (folder.name + "/consumed-development-identities.json")
         and manifest.get("yggdrasil_research_boundary_path") ==
             (folder.name + "/yggdrasil-research-lineage.json"),
         "PROVENANCE_PATH_IDENTITY_DRIFT")
    need(type(manifest.get("target_source_sha")) is str
         and re.fullmatch(r"[0-9a-f]{40}",
                          manifest["target_source_sha"]) is not None
         and manifest["target_source_sha"] != SOURCE
         and source["source_sha"] == manifest["target_source_sha"]
         and source["epoch"] == 1,
         "FRESH_DB_SOURCE_OR_EPOCH_INVALID")
    need(exclusions.get("schema") == EXCLUSIONS_SCHEMA
         and exclusions.get("source_sha") == SOURCE
         and exclusions.get("original_head_seq") == HEAD_SEQ
         and exclusions.get("original_head_sha256") == HEAD_SHA256
         and exclusions.get("release_qualified") is False
         and exclusions.get("fresh_activation_authorized") is False
         and lineage.get("schema") == YGG_SCHEMA
         and lineage.get("accepted_main_source_sha") == ACCEPTED
         and lineage.get("amalgam_draft_head_sha") == AMALGAM_HEAD
         and lineage.get("lineage_draft_head_sha") == LINEAGE_HEAD
         and lineage.get("checkpoint_imported") is False
         and lineage.get("model_continuation_authorized") is False
         and lineage.get("release_qualified") is False,
         "ARCHIVED_AND_RESEARCH_PROVENANCE_NOT_INERT")
    need(manifest.get("historical_consumed_exclusions_sha256") ==
             digest(exclusions_bytes)
         and manifest.get("yggdrasil_research_boundary_sha256") ==
             digest(lineage_bytes)
         and type(manifest.get("fresh_sqlite_sha256")) is str
         and SHA64.fullmatch(manifest["fresh_sqlite_sha256"]) is not None,
         "PROVENANCE_DIGEST_DRIFT")
    archive = root / ("f139-v59-before-" + str(run_id))
    archive_manifest = archive / "manifest.sha256.json"
    archived, raw_archive = _sealed_json(archive_manifest)
    need(archived.get("schema") ==
             "forge.f139.v59.original-cold-createonly.v1"
         and archived.get("owner_run_id") == run_id
         and archived.get("original_source_sha") == SOURCE
         and archived.get("target_source_sha") == source["source_sha"]
         and archived.get("original_head_seq") == HEAD_SEQ
         and archived.get("original_head_sha256") == HEAD_SHA256
         and archived.get("source_transition_authorized") is False
         and archived.get("scientific_first_use") is False
         and archived.get("owner_mutations") == 0
         and manifest.get("historical_cold_manifest_sha256") ==
             digest(raw_archive)
         and type(manifest.get("historical_sqlite_sha256")) is str
         and SHA64.fullmatch(manifest["historical_sqlite_sha256"]) is not None
         and archived.get("files_sha256", {}).get("state.sqlite") ==
             manifest["historical_sqlite_sha256"],
         "HISTORICAL_ARCHIVE_CUSTODY_DRIFT")
    # Local activation is a separately versioned record, never original v1
    # historical event23. A malformed fake is rejected before any provider GET.
    from f139.nci04_fresh_native_activation import (
        FreshActivationDenied, audit_fresh_native_activation,
        authenticate_fresh_activation_receipts,
    )
    try:
        activation = audit_fresh_native_activation(db)
    except FreshActivationDenied as exc:
        raise FreshNativeRouteDenied(
            "F139_FRESH_NATIVE_ROUTE_FRESH_DB_NOT_DISABLED_AND_EMPTY") from exc
    if activation is None:
        need(source["enabled"] == 0 and source["legacy_suspended"] == 0
             and source["head_seq"] == 0 and source["head_hash"] == ZERO,
             "FRESH_DB_NOT_DISABLED_AND_EMPTY")
        need(not db.conn.execute("SELECT 1 FROM events LIMIT 1").fetchone()
             and not db.conn.execute("SELECT 1 FROM tasks LIMIT 1").fetchone(),
             "NEW_WORK_OR_ACTIVATION_WITHOUT_OWNER_RELEASE")
        disposition = "FRESH_DEVELOPMENT_STAGED_DISABLED_NO_DISPATCH"
        floor = None
    else:
        need(activation["owner_run_id"] == run_id
             and activation["source_sha"] == source["source_sha"]
             and not db.conn.execute("SELECT 1 FROM tasks LIMIT 1").fetchone(),
             "FRESH_ACTIVATION_OWNER_OR_TASK_INVALID")
        floor, floor_bytes = _sealed_json(
            folder / "remote-issue-cutover-floor.json")
        owner, owner_bytes = _sealed_json(
            folder / "original-task-release.json")
        authenticate_fresh_activation_receipts(
            activation, stage=manifest, consumed=exclusions,
            yggdrasil_boundary=lineage, remote_floor=floor,
            owner_release=owner, manifest_bytes=encoded,
            consumed_bytes=exclusions_bytes, yggdrasil_bytes=lineage_bytes,
            floor_bytes=floor_bytes, release_bytes=owner_bytes)
        # A cold SQLite file and a matching local release document alone
        # cannot independently attest Windows SID/process or provider state
        # at this moment. This branch is still worker-dispatch INERT.
        disposition = "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED"
    # Archived DB is not reopened/modified here: the V59 original cold
    # verifier and original task quiescence must run at the actual handoff.
    # This receipt grants *no rights* even when all synthetic bytes match.
    return {
        "schema": SCHEMA,
        "disposition": disposition,
        "activation_event_recorded": activation is not None,
        "owner_release_independently_verified_runtime": False,
        "native_issue_admission_authorized": False,
        "source_sha": source["source_sha"],
        "original_source_sha": SOURCE,
        "original_head_seq": HEAD_SEQ,
        "original_head_sha256": HEAD_SHA256,
        "staged_owner_run_id": run_id,
        "manifest_sha256": digest(encoded),
        "consumed_work_sha256": digest(exclusions_bytes),
        "yggdrasil_research_boundary_sha256": digest(lineage_bytes),
        "fresh_native_activation_authorized": False,
        "original_task_rebind_authorized": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "new_controller": False,
        "new_scheduler": False,
        "worker_dispatched": False,
        "fresh_work_admitted": False,
        "yggdrasil_checkpoint_loaded": False,
        "no_replay": True,
    }

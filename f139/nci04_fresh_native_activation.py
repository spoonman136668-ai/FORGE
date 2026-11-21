"""Versioned fresh F139 native-development activation, verification ONLY.

A source-side verifier for the future original-Windows-owner one-shot cutover.
It does NOT provide a CLI/writer, task release, remote owner approval,
credential, worker dispatch, scientific first-use or Yggdrasil model owner.

The original v1 NATIVE_DEVELOPMENT_ACTIVATED contract and 23-event D2K
historical foundation remain completely unchanged. A future qualified owner
will need to append this new exact v2-style event only after independently
authenticating Windows SID/process, original cold custody and provider floor.
No local receipt alone authorizes the original task to move.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.nci04_fresh_remote_floor import SCHEMA as FLOOR_SCHEMA
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSION_SCHEMA
from f139.nci04_fresh_yggdrasil_boundary import ACCEPTED, RECEIPT_SCHEMA as YGG_SCHEMA

ACTIVATION_KIND = "FRESH_NATIVE_DEVELOPMENT_ACTIVATED"
ACTIVATION_SCHEMA = "forge.f139.fresh-native-development-activation.v1"
OWNER_RELEASE_SCHEMA = "forge.f139.fresh-native-original-task-release.v1"
FIELDS = frozenset({
    "schema", "source_sha", "prior_event_head_sha256", "owner_run_id",
    "original_source_sha", "original_head_seq", "original_head_sha256",
    "stage_manifest_sha256", "consumed_exclusions_sha256",
    "yggdrasil_research_boundary_sha256", "remote_cutover_receipt_sha256",
    "original_task_release_receipt_sha256", "remote_issue_number_floor",
    "accepted_yggdrasil_main_sha", "development_only", "scientific_first_use",
    "paid_model_calls", "new_controller", "new_scheduler", "new_queue",
    "worker_dispatch_authorized", "model_continuation_authorized",
})
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class FreshActivationDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise FreshActivationDenied("F139_FRESH_ACTIVATION_" + code)


def audit_fresh_native_activation(db) -> dict | None:
    """Audit the *local event chain*, never produce positive host authority.

    This audit can run on a SQLite copy; a valid record does not establish
    that the original Windows task was actually released. The native owner
    must authenticate external task release + live provider cutover separately.
    """
    rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events "
        "WHERE kind IN ('CUTOVER_ACTIVATED',?) ORDER BY seq",
        (ACTIVATION_KIND,)))
    activated = [r for r in rows if r["kind"] == ACTIVATION_KIND]
    if not activated:
        return None
    all_events = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    meta = db.meta()
    need(len(activated) == 1 and (len(all_events) == 2 or len(all_events) >= 4)
         and len(rows) == 2 and all_events[0]["kind"] == "CUTOVER_ACTIVATED"
         and all_events[0]["seq"] == 1
         and all_events[1]["kind"] == ACTIVATION_KIND
         and all_events[1]["seq"] == 2
         and all_events[1]["prior_sha"] == all_events[0]["sha"]
         and meta["head_seq"] == len(all_events)
         and meta["head_hash"] == all_events[-1]["sha"]
         and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1
         and meta["epoch"] == 1
         and (len(all_events) >= 4 or not db.conn.execute(
             "SELECT 1 FROM tasks LIMIT 1").fetchone()),
         "LOCAL_ACTIVATION_EVENT_SEQUENCE_INVALID")
    try:
        first = json.loads(all_events[0]["payload"])
        record = json.loads(all_events[1]["payload"])
    except (TypeError, ValueError, UnicodeError) as exc:
        raise FreshActivationDenied(
            "F139_FRESH_ACTIVATION_EVENT_JSON_INVALID") from exc
    need(first == {"source_sha": meta["source_sha"]}
         and type(record) is dict and set(record) == FIELDS
         and record["schema"] == ACTIVATION_SCHEMA
         and record["source_sha"] == meta["source_sha"]
         and type(record["source_sha"]) is str
         and SHA40.fullmatch(record["source_sha"]) is not None
         and record["source_sha"] != SOURCE
         and record["prior_event_head_sha256"] == all_events[1]["prior_sha"]
         and type(record["owner_run_id"]) is int and record["owner_run_id"] > 0
         and record["original_source_sha"] == SOURCE
         and record["original_head_seq"] == HEAD_SEQ
         and record["original_head_sha256"] == HEAD_SHA256
         and all(type(record[k]) is str and SHA64.fullmatch(record[k]) is not None
                 for k in (
                     "stage_manifest_sha256", "consumed_exclusions_sha256",
                     "yggdrasil_research_boundary_sha256",
                     "remote_cutover_receipt_sha256",
                     "original_task_release_receipt_sha256"))
         and type(record["remote_issue_number_floor"]) is int
         and record["remote_issue_number_floor"] > 0
         and record["accepted_yggdrasil_main_sha"] == ACCEPTED
         and record["development_only"] is True
         and record["scientific_first_use"] is False
         and type(record["paid_model_calls"]) is int
         and record["paid_model_calls"] == 0
         and all(record[k] is False for k in (
             "new_controller", "new_scheduler", "new_queue",
             "worker_dispatch_authorized", "model_continuation_authorized")),
         "LOCAL_ACTIVATION_EVENT_FIELDS_INVALID")
    if len(all_events) == 4:
        from f139.nci04_fresh_native_intake import audit_one_ready_tail
        audit_one_ready_tail(db, record, all_events[2:])
    elif len(all_events) > 4:
        from f139.nci04_fresh_lifecycle import audit_execution_tail
        audit_execution_tail(db, record, all_events[2:])
    return record


def authenticate_fresh_activation_receipts(
    activation: dict, *, stage: dict, consumed: dict,
    yggdrasil_boundary: dict, remote_floor: dict, owner_release: dict,
    manifest_bytes: bytes, consumed_bytes: bytes,
    yggdrasil_bytes: bytes, floor_bytes: bytes, release_bytes: bytes,
) -> None:
    """Bind *external* receipts to the event; no authority derived here.

    The separately qualified original Windows SID/process/Task Scheduler
    verifier must produce owner_release. Merely supplying matching dictionaries
    or an on-disk JSON file does NOT prove the Windows original was released.
    """
    need(type(activation) is dict
         and type(stage) is dict and type(consumed) is dict
         and type(yggdrasil_boundary) is dict and type(remote_floor) is dict
         and type(owner_release) is dict,
         "CUSTODY_RECEIPT_SHAPE_INVALID")
    need(stage.get("owner_run_id") == activation["owner_run_id"]
         and stage.get("target_source_sha") == activation["source_sha"]
         and stage.get("historical_consumed_exclusions_sha256") ==
             activation["consumed_exclusions_sha256"]
         and stage.get("yggdrasil_research_boundary_sha256") ==
             activation["yggdrasil_research_boundary_sha256"]
         and consumed.get("schema") == EXCLUSION_SCHEMA
         and consumed.get("source_sha") == SOURCE
         and consumed.get("original_head_seq") == HEAD_SEQ
         and consumed.get("original_head_sha256") == HEAD_SHA256
         and consumed.get("fresh_activation_authorized") is False
         and consumed.get("previous_work_replay_authorized") is False
         and type(consumed.get("old_issue_numbers")) is list
         and all(type(n) is int and n > 0
                 for n in consumed["old_issue_numbers"])
         and len(set(consumed["old_issue_numbers"])) ==
             len(consumed["old_issue_numbers"])
         and yggdrasil_boundary.get("schema") == YGG_SCHEMA
         and yggdrasil_boundary.get("accepted_main_source_sha") == ACCEPTED
         and yggdrasil_boundary.get("checkpoint_imported") is False
         and yggdrasil_boundary.get("model_continuation_authorized") is False,
         "ORIGINAL_OR_YGGDRASIL_RECEIPT_DRIFT")
    need(remote_floor.get("schema") == FLOOR_SCHEMA
         and remote_floor.get("original_source_sha") == SOURCE
         and remote_floor.get("original_head_seq") == HEAD_SEQ
         and remote_floor.get("original_head_sha256") == HEAD_SHA256
         and remote_floor.get("target_forge_source_sha") == activation["source_sha"]
         and remote_floor.get("consumed_exclusions_sha256") ==
             activation["consumed_exclusions_sha256"]
         and remote_floor.get("remote_cutover_issue_number_floor") ==
             activation["remote_issue_number_floor"]
         and type(remote_floor.get("remote_cutover_issue_number_floor")) is int
         and remote_floor["remote_cutover_issue_number_floor"] >= max(
             consumed["old_issue_numbers"], default=0)
         and remote_floor.get("remote_cutover_issue_provider_verified") is True
         and remote_floor.get("fresh_activation_authorized") is False
         and remote_floor.get("owner_task_rebind_authorized") is False
         and remote_floor.get("release_qualified") is False
         and remote_floor.get("scientific_first_use") is False,
         "ORIGINAL_PROVIDER_FLOOR_NOT_AUTHENTICATED")
    need(owner_release.get("schema") == OWNER_RELEASE_SCHEMA
         and owner_release.get("owner_task_name") ==
             "FORGE-F139-UnifiedController"
         and owner_release.get("target_forge_source_sha") ==
             activation["source_sha"]
         and owner_release.get("owner_run_id") == activation["owner_run_id"]
         and owner_release.get("original_source_sha") == SOURCE
         and owner_release.get("original_head_seq") == HEAD_SEQ
         and owner_release.get("original_head_sha256") == HEAD_SHA256
         and owner_release.get("remote_cutover_receipt_sha256") ==
             activation["remote_cutover_receipt_sha256"]
         and owner_release.get("original_task_quiesced") is True
         and owner_release.get("original_process_absent") is True
         and owner_release.get("original_mutex_held") is True
         and owner_release.get("original_sid_independently_verified") is True
         and owner_release.get("single_task_rebind_authorized") is True
         and owner_release.get("new_controller") is False
         and owner_release.get("new_scheduler") is False
         and owner_release.get("scientific_first_use") is False,
         "ORIGINAL_WINDOWS_OWNER_RELEASE_NOT_QUALIFIED")
    need(all(type(value) is bytes and canonical(doc) == value
             for doc, value in (
                 (stage, manifest_bytes), (consumed, consumed_bytes),
                 (yggdrasil_boundary, yggdrasil_bytes),
                 (remote_floor, floor_bytes), (owner_release, release_bytes)))
         and digest(manifest_bytes) == activation["stage_manifest_sha256"]
         and digest(consumed_bytes) == activation["consumed_exclusions_sha256"]
         and digest(yggdrasil_bytes) ==
             activation["yggdrasil_research_boundary_sha256"]
         and digest(floor_bytes) == activation["remote_cutover_receipt_sha256"]
         and digest(release_bytes) ==
             activation["original_task_release_receipt_sha256"],
         "ACTIVATION_RECEIPT_BYTES_OR_DIGEST_DRIFT")

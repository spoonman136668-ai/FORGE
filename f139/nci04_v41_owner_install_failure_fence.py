"""V41 original-owner installation safety fence: pure, disarmed state grammar.

A rollback after an original two-event SOURCE_TRANSITION_ADMITTED commit
must NEVER replace the live append-only SQLite with an older backup or
resurrect a V40 task that would be unable to verify the committed history.

This module never executes a step, updates policy, resumes a task, writes a
ref, constructs an executable release permit or runs scientific experiments.
It is a typed executable specification for a future separately approved
single-original-owner installer, not an installer or deployment authority.
"""
from __future__ import annotations

import re

from f139 import nci04_v41_guarded_release_preflight as release
from f139 import nci04_v41_source_transition as source
from f139 import nci04_v41_pending_escrow as escrow

SCHEMA = "forge.f139.v41.disarmed-owner-install-failure-fence.v1"
RECOVERY_SCHEMA = "forge.f139.v41.inert-interrupted-cutover-response.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")

PRE_COMMIT = frozenset({
    "OWNER_READONLY",
    "TASK_QUIESCED",
    "BACKUP_CONFIRMED",
    "COPIED_REHEARSAL_PASSED",
    "ORIGINAL_TRANSACTION_OPEN",
})
POST_COMMIT = frozenset({
    "SOURCE_PAIR_COMMITTED",
    "POLICY_UPDATED",
    "TARGET_INSTALLED",
    "TARGET_TASK_RESUMED",
})
ALL_STAGES = PRE_COMMIT | POST_COMMIT


class InstallSafetyDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise InstallSafetyDenied("F139_V41_INSTALL_FENCE_" + reason)


def _sha(value, width):
    return type(value) is str and (
        SHA40 if width == 40 else SHA64).fullmatch(value) is not None


def inert_handoff(readiness, copied, original_status):
    """Reconcile three independent *read-only* evidence sources.

    This is not a runtime check on the task or the owner. A live installer
    must independently authenticate quiescence, original SID, exact running
    task definition, release comment, no new dispatches, and held mutex.
    """
    need(type(readiness) is dict
         and readiness.get("schema") == release.SCHEMA
         and _sha(readiness.get("source_sha"), 40)
         and readiness["source_sha"] != source.FROM_V40
         and readiness.get("original_source_sha") == source.FROM_V40
         and _sha(readiness.get("source_tree_sha"), 40)
         and readiness.get("independent_restore_verified") is True
         and readiness.get("candidate_inputs_readonly_qualified") is True
         and readiness.get("pending_1715_escrow_intent_verified") is True
         and readiness.get("original_owner_installed") is False
         and readiness.get("release_qualified") is False
         and readiness.get("source_transition_authorized") is False
         and readiness.get("scientific_first_use") is False
         and readiness.get("hybrid_admission") is False
         and readiness.get("owner_mutations") == 0
         and readiness.get("new_dispatches") == 0
         and _sha(readiness.get("sealed_manifest_sha256"), 64)
         and type(readiness.get("backup_run_id")) is int
         and readiness["backup_run_id"] > 0
         and type(readiness.get("original_head_seq")) is int
         and readiness["original_head_seq"] >= escrow.OBSERVED_SEQ
         and _sha(readiness.get("original_head_sha256"), 64),
         "NON_AUTHORIZING_READINESS_REQUIRED")
    need(type(copied) is dict
         and copied.get("schema") == "forge.f139.v41.atomic-copy-rehearsal.v1"
         and copied.get("original_source_sha") == source.FROM_V40
         and copied.get("copy_source_sha") == readiness["source_sha"]
         and copied.get("original_head_seq") == readiness["original_head_seq"]
         and copied.get("copy_head_seq") == readiness["original_head_seq"] + 2
         and _sha(copied.get("copy_head_sha256"), 64)
         and _sha(copied.get("escrow_event_sha256"), 64)
         and copied.get("original_unchanged") is True
         and copied.get("copy_only") is True
         and copied.get("release_qualified") is False
         and copied.get("source_transition_authorized") is False
         and copied.get("reissue_authorized") is False
         and copied.get("scientific_first_use") is False
         and copied.get("hybrid_admission") is False
         and copied.get("new_dispatches") == 0,
         "EXACT_COPIED_HISTORY_REQUIRED")
    need(type(original_status) is dict
         and original_status.get("schema") ==
             "forge.f139.v41.original-locked-readonly-status.v1"
         and original_status.get("installed_source_sha") == source.FROM_V40
         and original_status.get("target_source_sha") == readiness["source_sha"]
         and original_status.get("original_head_seq") ==
             readiness["original_head_seq"]
         and original_status.get("original_head_sha256") ==
             readiness["original_head_sha256"]
         and original_status.get("verified_historical_tasks") >= 153
         and original_status.get("quarantined_historical_tasks") == 56
         and original_status.get("pending_issue_number") == 1715
         and original_status.get("sqlite_query_only") is True
         and original_status.get("original_owner_mutations") == 0
         and original_status.get("new_dispatches") == 0
         and original_status.get("reissue_authorized") is False
         and original_status.get("source_transition_authorized") is False
         and original_status.get("source_release_qualified") is False
         and original_status.get("scientific_first_use") is False
         and original_status.get("hybrid_admission") is False,
         "ORIGINAL_LOCKED_READONLY_STATUS_DRIFT")
    return {
        "schema": SCHEMA,
        "original_source_sha": source.FROM_V40,
        "target_source_sha": readiness["source_sha"],
        "source_tree_sha": readiness["source_tree_sha"],
        "original_head_seq": readiness["original_head_seq"],
        "original_head_sha256": readiness["original_head_sha256"],
        "expected_copy_head_seq": copied["copy_head_seq"],
        "expected_copy_head_sha256": copied["copy_head_sha256"],
        "expected_escrow_sha256": copied["escrow_event_sha256"],
        "sealed_manifest_sha256": readiness["sealed_manifest_sha256"],
        "independent_copy_and_cold_restore_verified": True,
        "owner_status_readonly_verified": True,
        "approved_live_release": False,
        "original_owner_installed": False,
        "original_owner_mutations": 0,
        "remote_writes": 0,
        "new_dispatches": 0,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "source_transition_authorized": False,
    }


def interrupted_cutover_response(plan, *, stage, observation):
    """Fail-closed recovery decision for an interrupted proposed cutover.

    'Resume V40 eligible' is only an observation requiring *separate* owner
    action/authority. It is not an instruction or native control permission.

    After the SQLite COMMIT, no destructive restore of the historical V40
    backup is allowed: preserve committed events, keep the original task
    disabled, and require independently qualified forward repair instead.
    """
    need(type(plan) is dict and plan.get("schema") == SCHEMA
         and plan.get("source_transition_authorized") is False
         and plan.get("approved_live_release") is False
         and plan.get("scientific_first_use") is False
         and plan.get("hybrid_admission") is False
         and _sha(plan.get("original_source_sha"), 40)
         and _sha(plan.get("target_source_sha"), 40)
         and _sha(plan.get("original_head_sha256"), 64)
         and _sha(plan.get("expected_copy_head_sha256"), 64)
         and _sha(plan.get("expected_escrow_sha256"), 64)
         and type(plan.get("original_head_seq")) is int
         and plan["original_head_seq"] >= escrow.OBSERVED_SEQ
         and plan.get("expected_copy_head_seq") ==
             plan["original_head_seq"] + 2,
         "INVALID_FROZEN_PREIMAGE_PLAN")
    need(type(stage) is str and stage in ALL_STAGES
         and type(observation) is dict and set(observation) == {
             "source_sha", "head_seq", "head_sha256",
             "task_disabled", "policy_source_sha", "installed_source_sha",
             "escrow_count", "source_transition_count",
             "new_dispatches", "scientific_first_use", "hybrid_admission",
         }, "INTERRUPTION_SHAPE_INVALID")
    need(_sha(observation["source_sha"], 40)
         and _sha(observation["head_sha256"], 64)
         and _sha(observation["policy_source_sha"], 40)
         and _sha(observation["installed_source_sha"], 40)
         and type(observation["task_disabled"]) is bool
         and type(observation["head_seq"]) is int
         and all(type(observation[k]) is int for k in
                 ("escrow_count", "source_transition_count",
                  "new_dispatches"))
         and observation["new_dispatches"] == 0
         and observation["scientific_first_use"] is False
         and observation["hybrid_admission"] is False,
         "OBSERVED_AUTHORITY_OR_SHAPE_DRIFT")
    original = plan["original_source_sha"]
    target = plan["target_source_sha"]
    if stage in PRE_COMMIT:
        need(observation["source_sha"] == original
             and observation["head_seq"] == plan["original_head_seq"]
             and observation["head_sha256"] == plan["original_head_sha256"]
             and observation["escrow_count"] == 0
             and observation["source_transition_count"] == 0
             and observation["policy_source_sha"] == original
             and observation["installed_source_sha"] == original
             and (stage == "OWNER_READONLY" or
                  observation["task_disabled"] is True),
             "PRECOMMIT_ORIGINAL_PRESERVATION_NOT_VERIFIED")
        decision = "V40_RECOVERY_ELIGIBLE_AFTER_SEPARATE_OWNER_VERIFICATION"
        hold = False
    else:
        need(observation["source_sha"] == target
             and observation["head_seq"] == plan["expected_copy_head_seq"]
             and observation["head_sha256"] == plan["expected_copy_head_sha256"]
             and observation["escrow_count"] == 1
             and observation["source_transition_count"] == 1,
             "COMMITTED_EVENT_PAIR_NOT_VERIFIED")
        if stage != "TARGET_TASK_RESUMED":
            need(observation["task_disabled"] is True,
                 "COMMITTED_ORIGINAL_TASK_MUST_REMAIN_DISABLED")
        if stage in {"POLICY_UPDATED", "TARGET_INSTALLED",
                     "TARGET_TASK_RESUMED"}:
            need(observation["policy_source_sha"] == target,
                 "NEW_POLICY_NOT_CUSTODIED")
        if stage in {"TARGET_INSTALLED", "TARGET_TASK_RESUMED"}:
            need(observation["installed_source_sha"] == target,
                 "NEW_CODE_NOT_CUSTODIED")
        if stage == "TARGET_TASK_RESUMED":
            need(observation["task_disabled"] is False,
                 "RESUMED_TASK_STATE_NOT_CUSTODIED")
        decision = ("POSTINSTALL_INDEPENDENT_ACCEPTANCE_REQUIRED"
                    if stage == "TARGET_TASK_RESUMED" else
                    "HOLD_DISABLED_FORWARD_REPAIR_ONLY")
        hold = stage != "TARGET_TASK_RESUMED"
    return {
        "schema": RECOVERY_SCHEMA,
        "stage": stage,
        "source_sha": observation["source_sha"],
        "head_seq": observation["head_seq"],
        "head_sha256": observation["head_sha256"],
        "recovery_decision": decision,
        "hold_original_task_disabled": hold,
        "sqlite_backup_restore_authorized": False,
        "automatic_rollback_or_replay_authorized": False,
        "actual_task_action_performed": False,
        "original_db_written": False,
        "source_transition_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }

"""Read-only original PR provenance shared by FORGE's existing Go qualifiers.

No dispatch, authorization, workflow mutation, network access, secret, cache or
test filtering. Generic source PRs cannot rewrite original Go CI harnesses.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Callable

REPO = "spoonman136668-ai/FORGE"
HYBRID_RELEASE_BRANCH = "release/f139-hybrid-qualified-worker-governance-20261109"
HYBRID_RELEASE_PR = 1642
HYBRID_RELEASE_ANCHOR = "0e122eb8e571ddddee1dea4168cf18cfc7dc019d"
HYBRID_WORKER_PATH = ".github/workflows/forge-f139-development-worker.yml"
HYBRID_WORKER_BEFORE = "8eab7972ba1b30eabf1e38477aff60b598cdeb2f"
HYBRID_WORKER_AFTER = "74dd90e6d71da6b53898c7a80d5362f1b0e6af27"
# One exact owner PR may extend the EXISTING owner workflow for a complete
# source HOLD -> Hybrid lane migration -> same-task restart. Unrelated workflow
# or harness changes remain denied by generic_paths_safe().
HYBRID_COMPLETE_BRANCH = "engineering/f139-v41-hybrid-original-owner-complete-cutover-20261114"
HYBRID_COMPLETE_PR = 1758
HYBRID_COMPLETE_BASE = "25edd09d77b87d248b7908f0b898881cc5fb27c3"
HYBRID_COMPLETE_BASE_TREE = "5c73f425f5936c11800e39be2f40141a8b608f3a"
HYBRID_COMPLETE_WORKFLOW = ".github/workflows/f139-v41-original-owner-live-install.yml"
HYBRID_COMPLETE_WORKFLOW_BEFORE = "ff11352d1d298361e97b1e7422338f608d4b2a70"
HYBRID_COMPLETE_WORKFLOW_AFTER = "6ad719d04639f96e3342f33bcbc9c5b379557e52"
HYBRID_COMPLETE_FILES = frozenset({
    HYBRID_COMPLETE_WORKFLOW,
    "f139/nci04_v41_hybrid_successor_release.py",
    "f139/test_nci04_v41_hybrid_successor_release.py",
    "f139/test_nci04_v41_hybrid_safe_abort.py",
    "f139/test_nci04_v41_hybrid_source_hold.py",
    "f139/test_v41_hybrid_original_activate.py",
    "f139/test_v41_hybrid_owner_workflow_bridge.py",
    "f139/v41_hybrid_original_activate.ps1",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

# One exact operator-approved, read-only original-owner V38 workflow route.
# This is CI source admission ONLY. It cannot authorize task, SQLite, policy,
# scheduling, first-use, merge, workflow invocation or privileged execution.
# Separate operator-approved bounded *diagnostic only* after failed original
# one-shot, authenticated to exact prior failed run/comment. Only grants source
# CI admission; no owner workflow execution, mutation, task control or science.
# Frozen operator-authorized original-owner stage localization (read-only).
# CI source admission ONLY: never a task, scheduler, first-use or runner right.
# Independent original Windows task metadata snapshot, one owner-authorized
# first-attempt read-only check. CI source admission is NOT live task authority.
V38_SNAPSHOT_BRANCH = "engineering/f139-v38-original-task-snapshot-once-20261114"
V38_SNAPSHOT_PR = 1763
V38_SNAPSHOT_BASE = "18ff9a91e999ca485c98c0b37414fbe3d0fe02b7"
V38_SNAPSHOT_BASE_TREE = "6ef37b29117d1eed4a161dabb61546f5ac478ae8"
V38_SNAPSHOT_WORKFLOW = ".github/workflows/f139-v38-original-task-snapshot-once.yml"
V38_SNAPSHOT_WORKFLOW_BLOB = "a40b94d13f19cba5e2ba4c2b33672a311bc9b483"
V38_SNAPSHOT_RESULT = "EXACT_PR1763_V38_ORIGINAL_TASK_SNAPSHOT_CI_ONLY"
V38_SNAPSHOT_FILES = frozenset({
    V38_SNAPSHOT_WORKFLOW,
    "f139/nci04_v38_original_task_snapshot.py",
    "f139/test_nci04_v38_original_task_snapshot.py",
    "docs/F139-V38-ORIGINAL-TASK-SNAPSHOT-ONCE.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})


# Isolated v2 of the EXISTING read-only snapshot route only. Exact PR/parent.
# Older owner workflows and the original task/guard cannot change.
V38_SNAPSHOT_V2_BRANCH = "engineering/f139-v38-snapshot-concurrency-isolation-20261114"
V38_SNAPSHOT_V2_PR = 1764
V38_SNAPSHOT_V2_BASE = "3bd918d8409fb4a8f10581aba5ae152776357cd9"
V38_SNAPSHOT_V2_BASE_TREE = "047caf400a932e01834f9e51dd29aaaf439905a1"
V38_SNAPSHOT_V2_WORKFLOW = ".github/workflows/f139-v38-original-task-snapshot-once.yml"
V38_SNAPSHOT_V2_BEFORE = "a40b94d13f19cba5e2ba4c2b33672a311bc9b483"
V38_SNAPSHOT_V2_AFTER = "696c86b1f21a6c11b6d8a9c1e3a0230b5ad6177f"
V38_SNAPSHOT_V2_RESULT = "EXACT_PR1764_V38_ISOLATED_SNAPSHOT_CI_ONLY"
V38_SNAPSHOT_V2_FILES = frozenset({
    V38_SNAPSHOT_V2_WORKFLOW,
    "f139/nci04_v38_original_task_snapshot.py",
    "f139/test_nci04_v38_original_task_snapshot.py",
    "docs/F139-V38-ORIGINAL-TASK-SNAPSHOT-ONCE.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

# V3 original owner one-pass protocol cause classification, source-only.
V38_SNAPSHOT_V3_BRANCH = "engineering/f139-v38-protocol-cause-categories-20261115"
V38_SNAPSHOT_V3_PR = 1765
V38_SNAPSHOT_V3_BASE = "652d42ca54fbf88044a1ef122d32cf06e3233687"
V38_SNAPSHOT_V3_BASE_TREE = "c97dbed6fee766bc4564fe5681190d7ef0bc4cf5"
V38_SNAPSHOT_V3_WORKFLOW = ".github/workflows/f139-v38-original-task-snapshot-once.yml"
V38_SNAPSHOT_V3_BEFORE = "696c86b1f21a6c11b6d8a9c1e3a0230b5ad6177f"
V38_SNAPSHOT_V3_AFTER = "4c86a9844d38e1d37bb70eee1800eee3e308bcd6"
V38_SNAPSHOT_V3_RESULT = "EXACT_PR1765_V38_PROTOCOL_CLASSIFICATION_CI_ONLY"
V38_SNAPSHOT_V3_FILES = V38_SNAPSHOT_V2_FILES

# V4 original read-only snapshot after native Windows PowerShell parser repair.
V38_SNAPSHOT_V4_BRANCH = "engineering/f139-v38-native-parsefix-owner-snapshot-v4-20261115"
V38_SNAPSHOT_V4_PR = 1767
V38_SNAPSHOT_V4_BASE = "5780c7cfefac246678e4ec66716fc22725d8ddef"
V38_SNAPSHOT_V4_BASE_TREE = "9680c6e137e4a25ec895c28690b692f57a3ca193"
V38_SNAPSHOT_V4_WORKFLOW = ".github/workflows/f139-v38-original-task-snapshot-once.yml"
V38_SNAPSHOT_V4_BEFORE = "4c86a9844d38e1d37bb70eee1800eee3e308bcd6"
V38_SNAPSHOT_V4_AFTER = "6857bf5c81d9662f7cf26f4a07eb59e463ac8253"
V38_SNAPSHOT_V4_RESULT = "EXACT_PR1767_V38_READONLY_PARSEFIX_SNAPSHOT_CI_ONLY"
V38_SNAPSHOT_V4_FILES = V38_SNAPSHOT_V3_FILES

# V39: exact one-shot GitHub CLI issue-comment vs Actions GET diagnostic.
V39_ACTIONS_GET_BRANCH = "engineering/f139-v39-original-actions-get-cause-20261115"
V39_ACTIONS_GET_PR = 1768
V39_ACTIONS_GET_BASE = "7b2b6bbd707ba80613b6f305615e9e8167b7ffaa"
V39_ACTIONS_GET_BASE_TREE = "fccf8c779110ceaa34dd13680d841b9c1cc40ea3"
V39_ACTIONS_GET_WORKFLOW = ".github/workflows/f139-v39-actions-get-diagnostic-once.yml"
V39_ACTIONS_GET_WORKFLOW_BLOB = "e5d8d7351ef5d627dd54efc5ce9f50c986611eaa"
V39_ACTIONS_GET_RESULT = "EXACT_PR1768_F139_V39_READONLY_ACTIONS_GET_DIAGNOSTIC_CI_ONLY"
V39_ACTIONS_GET_FILES = frozenset((
    ".github/workflows/f139-v39-actions-get-diagnostic-once.yml",
    "f139/nci04_v39_actions_get_diagnostic.py",
    "f139/test_nci04_v39_actions_get_diagnostic.py",
    "docs/F139-V39-ACTIONS-GET-READONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))

# V5 original-owner independent one-shot task snapshot after V39 GET proof.
V38_SNAPSHOT_V5_BRANCH = "engineering/f139-v38-original-task-snapshot-v5-after-get-proof-20261115"
V38_SNAPSHOT_V5_PR = 1769
V38_SNAPSHOT_V5_BASE = "1ffbcae47f71df31b0df88938c2f28e20545959b"
V38_SNAPSHOT_V5_BASE_TREE = "a1ad4bf06103f8d088722d775b82063d0c119a3d"
V38_SNAPSHOT_V5_WORKFLOW = ".github/workflows/f139-v38-original-task-snapshot-once.yml"
V38_SNAPSHOT_V5_BEFORE = "6857bf5c81d9662f7cf26f4a07eb59e463ac8253"
V38_SNAPSHOT_V5_AFTER = "f8a3a5c633929d9b292bed62b47b86855ef5caca"
V38_SNAPSHOT_V5_RESULT = "EXACT_PR1769_V38_READONLY_TASK_SNAPSHOT_AFTER_V39_GET_CI_ONLY"
V38_SNAPSHOT_V5_FILES = V38_SNAPSHOT_V4_FILES

# Exact read-only original Windows SQLite event-1830/cold-restoration diagnostic.
# Qualified forward original-owner install uses existing controller and source modules.
# Exact V38 forward owner GitHub concurrency isolation after zero-job cancellation.
V38_FORWARD_V2_BRANCH = "engineering/f139-v38-forward-original-owner-concurrency-v2-20261115"
V38_FORWARD_V2_PR = 1773
V38_FORWARD_V2_BASE = "756097420ea41d3884ef8ba0486e890d10e54e8e"
V38_FORWARD_V2_BASE_TREE = "eb0dce77ca6aed9c5407131f267e1cb3d5d51fa3"
V38_FORWARD_V2_WORKFLOW = ".github/workflows/f139-v38-original-forward-install.yml"
V38_FORWARD_V2_BEFORE = "bcf29aadb31c5189c81d61d6d291ce7eae3f156c"
V38_FORWARD_V2_AFTER = "4d502b1ac494f4c751af7b4c46b345615b94b933"
V38_FORWARD_V2_OLD_WORKFLOW = "6ad719d04639f96e3342f33bcbc9c5b379557e52"
V38_FORWARD_V2_READINESS_BLOB = "81f3f064ec1021653b95620a917ff2e689c439a7"
V38_FORWARD_V2_BACKUP = "44ed9e5faa16ff26ff85637db6137c0a6fc16689"
V38_FORWARD_V2_COMMIT = "9ad393a67becd881d8630ed7ab23125cd92f3f47"
V38_FORWARD_V2_RESULT = "EXACT_PR1773_V38_FORWARD_READONLY_QUEUE_ISOLATION_CI_ONLY"
V38_FORWARD_V2_FILES = frozenset({
    V38_FORWARD_V2_WORKFLOW,
    "f139/test_nci04_v38_original_forward_workflow.py",
    "f139/nci04_v41_hybrid_forward_readiness.py",
    "f139/test_nci04_v41_hybrid_forward_readiness.py",
    "docs/F139-V38-ORIGINAL-FORWARD-RELEASE.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V38_FORWARD_BRANCH = "engineering/f139-v38-forward-original-owner-release-20261115"
V38_FORWARD_PR = 1772
V38_FORWARD_BASE = "0b300ed59002ae12b810c3dacabd016605bb7daf"
V38_FORWARD_BASE_TREE = "eae427e3e0f7f19880b18fcd59b4245439a076e2"
V38_FORWARD_WORKFLOW = ".github/workflows/f139-v38-original-forward-install.yml"
V38_FORWARD_WORKFLOW_BLOB = "bcf29aadb31c5189c81d61d6d291ce7eae3f156c"
V38_FORWARD_READINESS_BLOB = "c9c33817182996f1d9bcd2ebdbc8bf8e5fdf6205"
V38_FORWARD_OLD_WORKFLOW_BLOB = "6ad719d04639f96e3342f33bcbc9c5b379557e52"
V38_FORWARD_ORIGINAL_BACKUP_BLOB = "44ed9e5faa16ff26ff85637db6137c0a6fc16689"
V38_FORWARD_SOURCE_COMMIT_BLOB = "9ad393a67becd881d8630ed7ab23125cd92f3f47"
V38_FORWARD_RESULT = "EXACT_PR1772_V38_FORWARD_OWNER_STAGE_RELEASE_CI_ONLY"
V38_FORWARD_FILES = frozenset({
    V38_FORWARD_WORKFLOW,
    "f139/nci04_v41_hybrid_forward_readiness.py",
    "f139/test_nci04_v41_hybrid_forward_readiness.py",
    "f139/test_nci04_v38_original_forward_workflow.py",
    "docs/F139-V38-ORIGINAL-FORWARD-RELEASE.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V38_COLD_BRANCH = "engineering/f139-v38-original-ledger-cold-readonly-20261115"
V38_COLD_PR = 1771
V38_COLD_BASE = "882806e3d849183651f601b4b319ad95a23864f7"
V38_COLD_BASE_TREE = "f4cb528844eeb4255528271c43a64d4e36dd8a08"
V38_COLD_WORKFLOW = ".github/workflows/f139-v38-original-owner-readonly-once.yml"
V38_COLD_BEFORE = "087348d173fac524195cf72dc78df222c5851485"
V38_COLD_AFTER = "eb27a1f6b8827d72874b14040dee234ce43c7314"
V38_COLD_RESULT = "EXACT_PR1771_V38_LEDGER_COLD_READONLY_CI_ONLY"
V38_COLD_FILES = frozenset({
    V38_COLD_WORKFLOW,
    "f139/nci04_v38_owner_ledger_cold_readonly.py",
    "f139/test_nci04_v38_owner_ledger_cold_readonly.py",
    "f139/test_v38_owner_readonly_workflow_scope.py",
    "docs/F139-V38-ORIGINAL-LEDGER-COLD-READONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V38_STAGE_BRANCH = "engineering/f139-v38-held-task-stage-diagnostic-20261114"
V38_STAGE_PR = 1762
V38_STAGE_BASE = "396a1a36aec66a47d798ac677bf3ed473c3fa27f"
V38_STAGE_BASE_TREE = "b59a9644b32a11ea5aafea004a54f2f6919d59dd"
V38_STAGE_WORKFLOW = ".github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"
V38_STAGE_WORKFLOW_BLOB = "6ead37ed976f65b54a8753471c4d4369826bdcc9"
V38_STAGE_RESULT = "EXACT_PR1762_V38_ORIGINAL_READONLY_STAGE_CI_ONLY"
V38_STAGE_FILES = frozenset({
    V38_STAGE_WORKFLOW,
    "f139/nci04_v38_held_task_stage_diagnostic.py",
    "f139/test_nci04_v38_held_task_stage_diagnostic.py",
    "docs/F139-V38-HELD-TASK-STAGE-ONE-SHOT.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V38_DIAG_BRANCH = "engineering/f139-v38-held-task-guard-diagnostic-once-20261114"
V38_DIAG_PR = 1761
V38_DIAG_BASE = "46a97e22ccd061ed799b53a8b92f27ed48b98f2b"
V38_DIAG_BASE_TREE = "2f6a8766fa8dac77531697e2990169464d600dc8"
V38_DIAG_WORKFLOW = ".github/workflows/f139-v38-held-task-guard-diagnostic-once.yml"
V38_DIAG_WORKFLOW_BLOB = "28924c2905d20e47d21a278ed763ad4a8904dda0"
V38_DIAG_RESULT = "EXACT_PR1761_V38_BOUNDED_HELD_TASK_GUARD_DIAG_CI_ONLY"
V38_DIAG_FILES = frozenset({
    V38_DIAG_WORKFLOW,
    "f139/nci04_v38_held_task_guard_diagnostic.py",
    "f139/test_nci04_v38_held_task_guard_diagnostic.py",
    "docs/F139-V38-HELD-GUARD-DIAGNOSTIC-ONCE.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V38_READONLY_BRANCH = "engineering/f139-v38-original-owner-readonly-once-20261114"
V38_READONLY_PR = 1760
V38_READONLY_BASE = "c611c4362e3cc867984448a03ecdf3be923d2ef1"
V38_READONLY_BASE_TREE = "f2f248c8d81654d88e943ed9b5ba9686225258c4"
V38_READONLY_WORKFLOW = ".github/workflows/f139-v38-original-owner-readonly-once.yml"
V38_READONLY_BLOB = "087348d173fac524195cf72dc78df222c5851485"
V38_READONLY_RESULT = "EXACT_PR1760_ONE_SHOT_ORIGINAL_READONLY_CI_ONLY"
V38_READONLY_FILES = frozenset({
    V38_READONLY_WORKFLOW,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
    "f139/test_v38_owner_readonly_workflow_scope.py",
    "docs/F139-V38-ONE-SHOT-ORIGINAL-OWNER-READONLY.md",
})

V41_PAUSE_BRANCH = "engineering/f139-v41-original-pause-backup-resume-20261112"
V41_PAUSE_PR = 1735
V41_PAUSE_BASE = "89f283492fd7ef171b4482b78baae88772880e51"
V41_PAUSE_WORKFLOW = ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_PAUSE_BEFORE = "5858519fbd335445d5a4518bb3c2fcc4d82b4b5e"
V41_PAUSE_AFTER = "b0dfd96bb86cdb834dd908a7518027d12cc9ad95"
V41_PAUSE_RESULT = "EXACT_PR1735_OWNER_SAME_TASK_PAUSE_BACKUP_RESUME_ONLY"
V41_PAUSE_FILES = frozenset({
    V41_PAUSE_WORKFLOW,
    "f139/v41_owner_pause_backup_resume.ps1",
    "f139/nci04_v41_owner_cold_backup.py",
    "f139/test_nci04_v41_owner_cold_backup.py",
    "docs/F139-V41-ORIGINAL-HOST-BACKUP-ONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V41_BACKUP_BRANCH = "dev/f139-v41-original-cold-backup-only-20261112"
V41_BACKUP_PR = 1734
V41_BACKUP_BASE = "2ee1d2e3894558a92231e5922980f8c96e731b36"
V41_BACKUP_WORKFLOW = ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_BACKUP_BEFORE = "fd5de64d7a8b44b6e8ac28a98c0c4fc33afbd9f3"
V41_BACKUP_AFTER = "5858519fbd335445d5a4518bb3c2fcc4d82b4b5e"
V41_BACKUP_RESULT = "EXACT_PR1734_OWNER_BACKUP_ONLY_WORKFLOW_SCOPE"
V41_BACKUP_FILES = frozenset({
    V41_BACKUP_WORKFLOW,
    "f139/nci04_v41_owner_cold_backup.py",
    "f139/test_nci04_v41_owner_cold_backup.py",
    "docs/F139-V41-ORIGINAL-HOST-BACKUP-ONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

V41_STATUS_BRANCH = "dev/f139-v41-original-locked-readonly-acceptance-20261112"
V41_STATUS_PR = 1731
V41_STATUS_BASE = "3edc2f930d915fddf040effda68b1a4770a4bb32"
V41_STATUS_WORKFLOW = ".github/workflows/f139-g54-v9-owner-cutover.yml"
V41_STATUS_BEFORE = "c8e6616d8203d27caccdb06084862bf8cfdbbd4c"
V41_STATUS_AFTER = "fd5de64d7a8b44b6e8ac28a98c0c4fc33afbd9f3"
V41_STATUS_RESULT = "EXACT_PR1731_V41_READONLY_OWNER_SCOPE_ONLY"
V41_STATUS_FILES = frozenset({
    V41_STATUS_WORKFLOW,
    "f139/nci04_v41_original_owner_status.py",
    "f139/test_nci04_v41_original_owner_status.py",
    "f139/test_v40_readonly_workflow_scope.py",
    "docs/F139-V41-ORIGINAL-LOCKED-READONLY-STATUS.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})

HYBRID_OWNER_WORKFLOW_BRANCH = "engineering/f139-hybrid-reader-route-20261110"
HYBRID_OWNER_WORKFLOW_PR = 1660
HYBRID_OWNER_WORKFLOW_BASE = "1a40fe4e3ec6e93a1631d59863b95e90981d734e"
HYBRID_OWNER_WORKFLOW_BASE_TREE = "e2d0322dd38baf8bc94bf32b6c3496b0471f3ed9"
HYBRID_OWNER_WORKFLOW = ".github/workflows/f139-v41-original-owner-live-install.yml"
HYBRID_OWNER_WORKFLOW_BEFORE = "b7abc3a9118a5c69dd24b4f351bf5697bfdf52f3"
HYBRID_OWNER_WORKFLOW_AFTER = "ff11352d1d298361e97b1e7422338f608d4b2a70"

FROZEN_SCOPES = {
    # Exact owner-scoped source PR: GITHUB_TOKEN may create the ONE
    # immutable 4ccbb847 worker ref after V46's original-host preflight.
    # Source CI is not remote-ref or original-task execution authority.
    "engineering/f139-v46-original-release-ref-once-20261116": (
        "2cc08f9b71a1f70d697fcd9d2d4a749eb8a39570",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/nci04_v46_live_source_commit.py",
            "f139/v46_original_owner_live_install.ps1",
            "f139/test_nci04_v46_live_source_commit.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # PR1786: copy-only proof of sealed original event1835 and simulated
    # event1836. Does not authorize live task/source/policy mutations.
    # Exact owner PR1788: existing G54 one-shot event1836 original task transition.
    # CI source admission only; live task/SID/SQLite release remains separately
    # authenticated on the original Windows host. No generic workflow exception.
    "engineering/f139-v46-event1836-live-source-transition-20261116": (
        "0a1523461fc54162c4d1104586dd69bb22d28a87",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/nci04_v46_live_source_commit.py",
            "f139/v46_original_owner_live_install.ps1",
            "f139/test_nci04_v46_live_source_commit.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/f139-v44-event1836-copy-rehearsal-20261116": (
        "4ccbb84785a43e038453d6f2bda5415ecb364084",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/nci04_v44_event1836_copy_rehearsal.py",
            "f139/nci04_v44_owner_copy_cli.py",
            "f139/test_nci04_v44_event1836_copy_rehearsal.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact PR1784: one existing original owner create-only cold-backup
    # route. Source/backup engineering only, never live source permission.
    "engineering/f139-v43-event1835-full-cold-backup-20261116": (
        "ac51b464e018b97099c7aa7fad4f6238c64b2500",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/nci04_v43_event1835_cold.py",
            "f139/nci04_v43_owner_backup_cli.py",
            "f139/test_nci04_v43_event1835_cold.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact original-owner PR1782: add one independently activated read-only
    # diagnostic on the existing G54 owner workflow. No mutation authority.
    "engineering/f139-v42-original-host-readonly-bridge-20261116": (
        "6006942116330ffc579784c88b1610d19b3f73cc",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/nci04_v42_original_owner_readonly.py",
            "f139/test_nci04_v42_original_owner_readonly.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact PR1779: repair one concrete-path class guard that failed the
    # original V40 backup before stage creation. Independent new owner release
    # must be qualified. No workflow/task/SQLite permission from this scope.
    "engineering/f139-v40-stage-path-instance-20261116": (
        "c5d2e94581565ff8e1b66d498d0b9a167e548454",
        {
            "f139/nci04_v41_hybrid_event1833_owner.py",
            "f139/test_nci04_v41_hybrid_event1833_owner.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact PR1777: V40 event1832 forward-only recovery plus one qualified
    # original owner route. Source-only admission is NOT execution authority.
    "engineering/f139-v39-event1832-postwrite-canonical-readback-20261115": (
        "1479f963160001037566e4cef33582c5293fb773",
        {
            ".github/workflows/f139-v39-original-source-successor.yml",
            "f139/hybrid_owner_admission.py",
            "f139/local_controller.py",
            "f139/nci04_owner_ledger.py",
            "f139/nci04_v41_hybrid_event1832_commit.py",
            "f139/nci04_v41_hybrid_event1832_postcommit.py",
            "f139/nci04_v41_hybrid_event1833_cold.py",
            "f139/nci04_v41_hybrid_event1833_commit.py",
            "f139/nci04_v41_hybrid_event1833_owner.py",
            "f139/nci04_v41_hybrid_event1833_postcommit.py",
            "f139/nci04_v41_hybrid_event1833_successor.py",
            "f139/test_nci04_v41_hybrid_event1832_commit.py",
            "f139/test_nci04_v41_hybrid_event1832_postcommit.py",
            "f139/test_nci04_v41_hybrid_event1833_cold.py",
            "f139/test_nci04_v41_hybrid_event1833_owner.py",
            "f139/test_nci04_v41_hybrid_event1833_successor.py",
            "f139/test_nci04_v41_hybrid_event1832_workflow.py",
            "f139/test_v41_hybrid_original_activate.py",
            "f139/v41_hybrid_original_activate.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact PR1776: isolate V39 issue_comment concurrency from skipped V41 runs.
    # Both workflow families keep existing first-attempt owner checks and
    # original SQLite SingleOwner; source admission is NOT runtime authority.
    "engineering/f139-v39-concurrency-isolation-v2-20261115": (
        "f9681850ec008b5d872de960544c46e6f5c7943b",
        {
            ".github/workflows/f139-v39-original-source-successor.yml",
            "f139/nci04_v41_hybrid_event1832_owner.py",
            "f139/test_nci04_v41_hybrid_event1832_owner.py",
            "f139/test_nci04_v41_hybrid_event1832_workflow.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Correct only the prior protected-main diff-check whitespace and
    # bind the follow-on original owner release to the new exact source.
    # Source CI admission ONLY; never authorization to execute the owner task,
    # commit event 1832, change policy, or perform scientific first-use.
    "engineering/f139-v39-postmerge-isolation-correction-20261115": (
        "f5507425859bee2f791efd6b0f82b090fddfe416",
        {
            ".github/workflows/f139-v39-original-source-successor.yml",
            "f139/nci04_v41_hybrid_event1832_owner.py",
            "f139/test_nci04_v41_hybrid_event1832_owner.py",
            "f139/test_nci04_v41_hybrid_event1832_workflow.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Frozen PR1774 source-only original V39 implementation and existing owner
    # workflow event routes. This is ENGINEERING CI admission, not native
    # activation, task ownership, scientific first-use or merge authority.
    "engineering/f139-v38-event1831-activation-bridge-20261115": (
        "eae38f6d0af27c41181da10c35685c6a3e8c68b4",
        {
            ".github/workflows/f139-v39-original-source-successor.yml",
            "f139/hybrid_owner_admission.py",
            "f139/local_controller.py",
            "f139/nci04_v41_hybrid_event1832_cold.py",
            "f139/nci04_v41_hybrid_event1832_commit.py",
            "f139/nci04_v41_hybrid_event1832_owner.py",
            "f139/nci04_v41_hybrid_event1832_postcommit.py",
            "f139/nci04_v41_hybrid_event1832_successor.py",
            "f139/test_nci04_v41_hybrid_event1832_cold.py",
            "f139/test_nci04_v41_hybrid_event1832_commit.py",
            "f139/test_nci04_v41_hybrid_event1832_owner.py",
            "f139/test_nci04_v41_hybrid_event1832_postcommit.py",
            "f139/test_nci04_v41_hybrid_event1832_successor.py",
            "f139/test_nci04_v41_hybrid_event1832_workflow.py",
            "f139/test_v41_hybrid_original_activate.py",
            "f139/v41_hybrid_original_activate.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # ONLY original owner PR #1660, original main, exact full workflow blob.
    "engineering/f139-hybrid-reader-route-20261110": (
        "1a40fe4e3ec6e93a1631d59863b95e90981d734e",
        {
            ".github/workflows/f139-v41-original-owner-live-install.yml",
            "docs/F139-HYBRID-NATIVE-READER-ROUTE.md",
            "docs/F139-PRIVATE-CPU-RUNTIME-CUSTODY.md",
            "docs/F139-PRIVATE-CPU-SANDBOX-PROBE.md",
            "docs/F139-V41-HYBRID-COLD-PAIR.md",
            "docs/F139-V41-HYBRID-COMPLETE-COLD-BUNDLE.md",
            "docs/F139-V41-HYBRID-OWNER-BACKUP-ADMISSION.md",
            "docs/F139-V41-HYBRID-PAIRED-MAINTENANCE-WRAPPER.md",
            "docs/F139-V41-HYBRID-PROTECTED-MAIN-SOURCE-BRIDGE.md",
            "docs/F139-V41-HYBRID-SCOPED-ORIGINAL-WORKFLOW-BRIDGE.md",
            "f139/local_controller.py",
            "f139/nci04_autonomy_feed.py",
            "f139/nci04_native_contract.py",
            "f139/nci04_native_worker.py",
            "f139/nci04_v41_hybrid_cold_bundle.py",
            "f139/nci04_v41_hybrid_cold_pair.py",
            "f139/nci04_v41_hybrid_owner_maintenance.py",
            "f139/nci04_v41_hybrid_pair_owner.py",
            "f139/nci04_v41_hybrid_protected_main.py",
            "f139/nci04_worker_entry.py",
            "f139/private_cpu_runtime.py",
            "f139/private_cpu_sandbox.py",
            "f139/private_hybrid_opaque_issue.py",
            "f139/private_hybrid_owner_binding.py",
            "f139/private_hybrid_reference.py",
            "f139/private_hybrid_terminal.py",
            "f139/public_hybrid_cpu_runtime.py",
            "f139/public_hybrid_cpu_wheel_lock.json",
            "f139/test_hybrid_root_native_source_family.py",
            "f139/test_nci04_autonomy_feed.py",
            "f139/test_nci04_v41_hybrid_cold_bundle.py",
            "f139/test_nci04_v41_hybrid_cold_pair.py",
            "f139/test_nci04_v41_hybrid_owner_maintenance.py",
            "f139/test_nci04_v41_hybrid_pair_owner.py",
            "f139/test_nci04_v41_hybrid_protected_main.py",
            "f139/test_nci04_v41_live_install_workflow.py",
            "f139/test_private_cpu_runtime.py",
            "f139/test_private_cpu_sandbox.py",
            "f139/test_private_hybrid_opaque_issue.py",
            "f139/test_private_hybrid_owner_binding.py",
            "f139/test_private_hybrid_reference.py",
            "f139/test_private_hybrid_terminal.py",
            "f139/test_public_hybrid_cpu_runtime.py",
            "f139/test_three_lane_fairness.py",
            "f139/test_v41_hybrid_owner_pause_backup_resume.py",
            "f139/test_v41_hybrid_owner_workflow_bridge.py",
            "f139/v41_hybrid_owner_pause_backup_resume.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact, one-shot original-owner V41 installation implementation scope.
    # CI source admission is not owner installation or science authority.
    "engineering/f139-v41-native-original-install-entry-20261113": (
        "98ec09b732a7764d1f2a38b98abd5927dab03dac",
        {
            ".github/workflows/f139-v41-original-owner-live-install.yml",
            ".github/workflows/f139-v41-install-focused-qualification.yml",
            "f139/nci04_v41_native_original_install_cli.py",
            "f139/v41_original_owner_live_install.ps1",
            "f139/test_nci04_v41_native_original_install_cli.py",
            "f139/test_nci04_v41_live_install_workflow.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact V41 native-stage route only; original owner, no SQLite/task mutation.
    "engineering/f139-v41-owner-native-stage-workflow-20261113": (
        "2a7f2f58f829e9de9bdf47fe963d3edbf9335982",
        {
            ".github/workflows/f139-v41-original-owner-native-stage.yml",
            "f139/test_nci04_v41_owner_native_stage_workflow.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact owner-approved V40 handoff engineering source; no live approval inferred.
    'engineering/f139-v40-explicit-owner-handoff-20261109': (
        'feb75e7490256a6930698742a43b8d12384fbbca',
        {'docs/F139-V40-EXPLICIT-OWNER-HANDOFF.md', 'f139/nci04_v40_guarded_owner_handoff.py', '.github/workflows/f139-v38-original-owner-release.yml', 'f139/test_nci04_v38_source_transition.py', 'f139/nci04_v32_original_owner_transition_cli.py', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g145_pr_scope.py', 'f139/check_v40_release_source.py', 'scripts/check_rar_g156_dynamic_base_cache.py', 'f139/test_nci04_v40_owner_handoff.py', 'f139/nci04_v40_owner_handoff_approval.py'},
    ),
    # Operator-authorized source-bound build and disposable-copy qualification only.
    'engineering/f139-v40-source-bound-copy-qualification-20261109': (
        'fa1a0477996bf1fb0568290a3692c57ee8b29b91',
        {'docs/F139-V40-SOURCE-BOUND-COPY-QUALIFICATION.md', 'f139/test_v40_readonly_workflow_scope.py', 'scripts/check_rar_g145_pr_scope.py', '.github/workflows/f139-g54-v9-owner-cutover.yml', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g156_dynamic_base_cache.py'},
    ),
    # Operator-authorized exact V40 read-only invocation qualification.
    'engineering/f139-v40-qualified-readonly-route-20261109': (
        '32de33753c874102de9672d2768e4b7c0b866b25',
        {'scripts/check_rar_g145_pr_scope.py', 'f139/test_v40_readonly_workflow_scope.py', '.github/workflows/f139-g54-v9-owner-cutover.yml', 'docs/F139-V40-QUALIFIED-READONLY-ROUTE.md', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g156_dynamic_base_cache.py'},
    ),
    # Explicit operator-authorized governance qualification, not a generic
    # workflow/harness allowance. The worker itself is a separate PR below.
    "engineering/f139-exact-worker-release-scope-20261109": (
        "0e122eb8e571ddddee1dea4168cf18cfc7dc019d",
        {
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
            "f139/test_hybrid_workflow_release_scope.py",
            "docs/F139-EXACT-HYBRID-WORKFLOW-RELEASE.md",
        },
    ),
    "engineering/rar-g141-parallel-complete-go-suites-20261108": (
        "1a1ba98dc821131d8a14182f72243540d008aaae",
        {
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g141_parallel_go.py",
        },
    ),
    "engineering/rar-g144-windows-native-go-vet-concurrent-20261108": (
        "0ea00f9b4587f5508dff39b65de2574f0b4fe681",
        {
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g144_windows_go.py",
        },
    ),
    "engineering/g145-generic-pr-original-qualification-20261108": (
        "69421a9d82bfb7b374d6635d3c60d7e41bfaf3b2",
        {
            "docs/FORGE-G145-GENERIC-PR-QUALIFICATION.md",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g144_windows_go.py",
            "scripts/check_rar_g145_pr_scope.py",
        },
    ),
    "engineering/rar-g148-main-safe-go-cache-20261108": (
        "ab2d239e2d079d2500ec5d91b253c11e6bd3b132",
        {
            "docs/FORGE-G148-GO-CACHE-RELEASE.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
        },
    ),
    "engineering/rar-g156-dynamic-main-cache-release-20261108": (
        "a62f469de1d5316c04d063246c30a5812bc8857d",
        {
            "docs/FORGE-G156-DYNAMIC-MAIN-GO-CACHE-RELEASE.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g158-optional-helper-compat-20261108": (
        "6a9bd9b87bc8d12cb0e8237c1da606aecf28c39b",
        {
            "docs/FORGE-G158-OPTIONAL-HELPER-COMPAT.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g160-partial-go-diagnostics-20261109": (
        "21b8649569bd9577c325da1ea99ecac81ff5df89",
        {
            "docs/FORGE-G160-G141-PARTIAL-GO-DIAGNOSTICS.md",
            "scripts/check_rar_g141_parallel_go.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    "engineering/rar-g161-verified-pr-ancestry-20261109": (
        "ad9026d2e551b054fc944d536ded37fe20a1aaa4",
        {
            "docs/FORGE-G161-G145-PR-ANCESTRY.md",
            ".github/workflows/qualify.yml",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
}


def is_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def admit_hybrid_complete(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Exact original-owner PR#1758 workflow and seven-file engineering scope.

    This ONLY admits running the unchanged G141/G145 performance check on
    the PR source. It does not authorize owner pause, release, merge, science
    first-use, policy changes or an unqualified workflow replacement.
    """
    if (not is_sha(head_sha) or base_sha != HYBRID_COMPLETE_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != HYBRID_COMPLETE_PR
            or request.get("user",{}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_HYBRID_COMPLETE_EXACT_PR_OWNER_REQUIRED")
    try:
        ancestor=git("merge-base",base_sha,head_sha)
        tree=git("rev-parse",base_sha+"^{tree}")
        paths=git("diff","--no-renames","--name-only",base_sha,head_sha).splitlines()
        old=git("ls-tree",base_sha,"--",HYBRID_COMPLETE_WORKFLOW)
        new=git("ls-tree",head_sha,"--",HYBRID_COMPLETE_WORKFLOW)
        worker=git("rev-parse",head_sha+":"+HYBRID_WORKER_PATH)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_HYBRID_COMPLETE_GIT_PROVENANCE_MISSING") from exc
    def blob(sha,path):
        return "100644 blob "+sha+"\t"+path
    if (ancestor != base_sha
            or tree != HYBRID_COMPLETE_BASE_TREE
            or len(paths) != len(HYBRID_COMPLETE_FILES)
            or set(paths) != HYBRID_COMPLETE_FILES
            or old != blob(HYBRID_COMPLETE_WORKFLOW_BEFORE,HYBRID_COMPLETE_WORKFLOW)
            or new != blob(HYBRID_COMPLETE_WORKFLOW_AFTER,HYBRID_COMPLETE_WORKFLOW)
            or worker != HYBRID_WORKER_AFTER):
        raise ValueError("G145_HYBRID_COMPLETE_EXACT_SOURCE_OR_WORKFLOW_CHANGED")
    return "EXACT_PR1758_HYBRID_ORIGINAL_ENGINEERING_QUALIFICATION_ONLY"


def hybrid_complete_negative_controls() -> None:
    base,head=HYBRID_COMPLETE_BASE,"e"*40
    request={"number":HYBRID_COMPLETE_PR,
             "user":{"login":"spoonman136668-ai"},
             "author_association":"OWNER"}
    def good(*args):
        if args==("merge-base",base,head):return base
        if args==("rev-parse",base+"^{tree}"):return HYBRID_COMPLETE_BASE_TREE
        if args==("diff","--no-renames","--name-only",base,head):
            return "\n".join(sorted(HYBRID_COMPLETE_FILES))
        if args==("ls-tree",base,"--",HYBRID_COMPLETE_WORKFLOW):
            return "100644 blob "+HYBRID_COMPLETE_WORKFLOW_BEFORE+"\t"+HYBRID_COMPLETE_WORKFLOW
        if args==("ls-tree",head,"--",HYBRID_COMPLETE_WORKFLOW):
            return "100644 blob "+HYBRID_COMPLETE_WORKFLOW_AFTER+"\t"+HYBRID_COMPLETE_WORKFLOW
        if args==("rev-parse",head+":"+HYBRID_WORKER_PATH):
            return HYBRID_WORKER_AFTER
        raise AssertionError("unexpected exact-cutover original source route")
    if (admit_hybrid_complete(head,base,request,good) !=
            "EXACT_PR1758_HYBRID_ORIGINAL_ENGINEERING_QUALIFICATION_ONLY"):
        raise ValueError("G145_HYBRID_COMPLETE_POSITIVE_CONTROL_FAILED")
    def reject(req=request,base_value=base,changed=None):
        def read(*args):
            return changed[1] if changed and args==changed[0] else good(*args)
        try:
            admit_hybrid_complete(head,base_value,req,read)
        except ValueError:
            return
        raise ValueError("G145_HYBRID_COMPLETE_NEGATIVE_CONTROL_ADMITTED")
    reject({**request,"number":1757})
    reject({**request,"user":{"login":"different"}})
    reject({**request,"author_association":"CONTRIBUTOR"})
    reject(base_value="f"*40)
    reject(changed=(("merge-base",base,head),"f"*40))
    reject(changed=(("rev-parse",base+"^{tree}"),"f"*40))
    reject(changed=(("diff","--no-renames","--name-only",base,head),
                    "\n".join(sorted(HYBRID_COMPLETE_FILES-{
                        HYBRID_COMPLETE_WORKFLOW}))))
    reject(changed=(("ls-tree",head,"--",HYBRID_COMPLETE_WORKFLOW),
                    "100644 blob "+"f"*40+"\t"+HYBRID_COMPLETE_WORKFLOW))
    reject(changed=(("rev-parse",head+":"+HYBRID_WORKER_PATH),"f"*40))



def admit_v38_snapshot_v2(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Source-only: one exact PR, exact workflow-before/after and unchanged owner."""
    if (not is_sha(head_sha) or base_sha != V38_SNAPSHOT_V2_BASE
            or type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V38_SNAPSHOT_V2_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_SNAPSHOT_V2_OWNER_OR_PARENT_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_SNAPSHOT_V2_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_SNAPSHOT_V2_WORKFLOW)
        owner = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_SNAPSHOT_V2_EXACT_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_SNAPSHOT_V2_BASE or tree != V38_SNAPSHOT_V2_BASE_TREE
            or len(paths) != len(V38_SNAPSHOT_V2_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_SNAPSHOT_V2_FILES
            or before != "100644 blob " + V38_SNAPSHOT_V2_BEFORE +
                         "\t" + V38_SNAPSHOT_V2_WORKFLOW
            or after != "100644 blob " + V38_SNAPSHOT_V2_AFTER +
                        "\t" + V38_SNAPSHOT_V2_WORKFLOW
            or owner != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or prior != "6ead37ed976f65b54a8753471c4d4369826bdcc9"):
        raise ValueError("G145_V38_SNAPSHOT_V2_SOURCE_OR_OWNER_GUARD_DRIFT")
    return V38_SNAPSHOT_V2_RESULT


def v38_snapshot_v2_negative_controls() -> None:
    base, head = V38_SNAPSHOT_V2_BASE, "e" * 40
    request = {"number": V38_SNAPSHOT_V2_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def valid(*args):
        cases = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_SNAPSHOT_V2_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_SNAPSHOT_V2_FILES)),
            ("ls-tree", base, "--", V38_SNAPSHOT_V2_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V2_BEFORE + "\t" + V38_SNAPSHOT_V2_WORKFLOW,
            ("ls-tree", head, "--", V38_SNAPSHOT_V2_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V2_AFTER + "\t" + V38_SNAPSHOT_V2_WORKFLOW,
            ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"):
                "6ead37ed976f65b54a8753471c4d4369826bdcc9",
        }
        if args not in cases:
            raise AssertionError("unexpected source test read")
        return cases[args]
    if admit_v38_snapshot_v2(head, base, request, valid) != V38_SNAPSHOT_V2_RESULT:
        raise ValueError("G145_V38_SNAPSHOT_V2_POSITIVE_FAILED")
    def reject(req=request, parent=base, changed=None):
        def reader(*args):
            if changed is not None and args == changed[0]:
                return changed[1]
            return valid(*args)
        try:
            admit_v38_snapshot_v2(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_SNAPSHOT_V2_NEGATIVE_ADMITTED")
    reject({**request, "number": 1763})
    reject({**request, "author_association": "CONTRIBUTOR"})
    reject({**request, "user": {"login": "OTHER"}})
    reject(parent="d" * 40)
    reject(changed=(("merge-base", base, head), "d" * 40))
    reject(changed=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_SNAPSHOT_V2_FILES - {V38_SNAPSHOT_V2_WORKFLOW}))))
    reject(changed=(("ls-tree", base, "--", V38_SNAPSHOT_V2_WORKFLOW), ""))
    reject(changed=(("ls-tree", head, "--", V38_SNAPSHOT_V2_WORKFLOW),
                    "100644 blob " + "d" * 40 + "\t" + V38_SNAPSHOT_V2_WORKFLOW))
    reject(changed=(("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                    "d" * 40))
    reject(changed=(("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"),
                    "d" * 40))


def admit_v38_snapshot_v3(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Source-only: one exact PR, exact workflow-before/after and unchanged owner."""
    if (not is_sha(head_sha) or base_sha != V38_SNAPSHOT_V3_BASE
            or type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V38_SNAPSHOT_V3_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_SNAPSHOT_V3_OWNER_OR_PARENT_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_SNAPSHOT_V3_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_SNAPSHOT_V3_WORKFLOW)
        owner = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_SNAPSHOT_V3_EXACT_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_SNAPSHOT_V3_BASE or tree != V38_SNAPSHOT_V3_BASE_TREE
            or len(paths) != len(V38_SNAPSHOT_V3_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_SNAPSHOT_V3_FILES
            or before != "100644 blob " + V38_SNAPSHOT_V3_BEFORE +
                         "\t" + V38_SNAPSHOT_V3_WORKFLOW
            or after != "100644 blob " + V38_SNAPSHOT_V3_AFTER +
                        "\t" + V38_SNAPSHOT_V3_WORKFLOW
            or owner != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or prior != "6ead37ed976f65b54a8753471c4d4369826bdcc9"):
        raise ValueError("G145_V38_SNAPSHOT_V3_SOURCE_OR_OWNER_GUARD_DRIFT")
    return V38_SNAPSHOT_V3_RESULT


def v38_snapshot_v3_negative_controls() -> None:
    base, head = V38_SNAPSHOT_V3_BASE, "e" * 40
    request = {"number": V38_SNAPSHOT_V3_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def valid(*args):
        cases = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_SNAPSHOT_V3_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_SNAPSHOT_V3_FILES)),
            ("ls-tree", base, "--", V38_SNAPSHOT_V3_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V3_BEFORE + "\t" + V38_SNAPSHOT_V3_WORKFLOW,
            ("ls-tree", head, "--", V38_SNAPSHOT_V3_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V3_AFTER + "\t" + V38_SNAPSHOT_V3_WORKFLOW,
            ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"):
                "6ead37ed976f65b54a8753471c4d4369826bdcc9",
        }
        if args not in cases:
            raise AssertionError("unexpected source test read")
        return cases[args]
    if admit_v38_snapshot_v3(head, base, request, valid) != V38_SNAPSHOT_V3_RESULT:
        raise ValueError("G145_V38_SNAPSHOT_V3_POSITIVE_FAILED")
    def reject(req=request, parent=base, changed=None):
        def reader(*args):
            if changed is not None and args == changed[0]:
                return changed[1]
            return valid(*args)
        try:
            admit_v38_snapshot_v3(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_SNAPSHOT_V3_NEGATIVE_ADMITTED")
    reject({**request, "number": 1764})
    reject({**request, "author_association": "CONTRIBUTOR"})
    reject({**request, "user": {"login": "OTHER"}})
    reject(parent="d" * 40)
    reject(changed=(("merge-base", base, head), "d" * 40))
    reject(changed=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_SNAPSHOT_V3_FILES - {V38_SNAPSHOT_V3_WORKFLOW}))))
    reject(changed=(("ls-tree", base, "--", V38_SNAPSHOT_V3_WORKFLOW), ""))
    reject(changed=(("ls-tree", head, "--", V38_SNAPSHOT_V3_WORKFLOW),
                    "100644 blob " + "d" * 40 + "\t" + V38_SNAPSHOT_V3_WORKFLOW))
    reject(changed=(("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                    "d" * 40))
    reject(changed=(("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"),
                    "d" * 40))


def admit_v38_snapshot_v4(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Source-only: one exact PR, exact workflow-before/after and unchanged owner."""
    if (not is_sha(head_sha) or base_sha != V38_SNAPSHOT_V4_BASE
            or type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V38_SNAPSHOT_V4_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_SNAPSHOT_V4_OWNER_OR_PARENT_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_SNAPSHOT_V4_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_SNAPSHOT_V4_WORKFLOW)
        owner = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_SNAPSHOT_V4_EXACT_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_SNAPSHOT_V4_BASE or tree != V38_SNAPSHOT_V4_BASE_TREE
            or len(paths) != len(V38_SNAPSHOT_V4_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_SNAPSHOT_V4_FILES
            or before != "100644 blob " + V38_SNAPSHOT_V4_BEFORE +
                         "\t" + V38_SNAPSHOT_V4_WORKFLOW
            or after != "100644 blob " + V38_SNAPSHOT_V4_AFTER +
                        "\t" + V38_SNAPSHOT_V4_WORKFLOW
            or owner != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or prior != "6ead37ed976f65b54a8753471c4d4369826bdcc9"):
        raise ValueError("G145_V38_SNAPSHOT_V4_SOURCE_OR_OWNER_GUARD_DRIFT")
    return V38_SNAPSHOT_V4_RESULT


def v38_snapshot_v4_negative_controls() -> None:
    base, head = V38_SNAPSHOT_V4_BASE, "e" * 40
    request = {"number": V38_SNAPSHOT_V4_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def valid(*args):
        cases = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_SNAPSHOT_V4_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_SNAPSHOT_V4_FILES)),
            ("ls-tree", base, "--", V38_SNAPSHOT_V4_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V4_BEFORE + "\t" + V38_SNAPSHOT_V4_WORKFLOW,
            ("ls-tree", head, "--", V38_SNAPSHOT_V4_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V4_AFTER + "\t" + V38_SNAPSHOT_V4_WORKFLOW,
            ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"):
                "6ead37ed976f65b54a8753471c4d4369826bdcc9",
        }
        if args not in cases:
            raise AssertionError("unexpected source test read")
        return cases[args]
    if admit_v38_snapshot_v4(head, base, request, valid) != V38_SNAPSHOT_V4_RESULT:
        raise ValueError("G145_V38_SNAPSHOT_V4_POSITIVE_FAILED")
    def reject(req=request, parent=base, changed=None):
        def reader(*args):
            if changed is not None and args == changed[0]:
                return changed[1]
            return valid(*args)
        try:
            admit_v38_snapshot_v4(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_SNAPSHOT_V4_NEGATIVE_ADMITTED")
    reject({**request, "number": 1765})
    reject({**request, "author_association": "CONTRIBUTOR"})
    reject({**request, "user": {"login": "OTHER"}})
    reject(parent="d" * 40)
    reject(changed=(("merge-base", base, head), "d" * 40))
    reject(changed=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_SNAPSHOT_V4_FILES - {V38_SNAPSHOT_V4_WORKFLOW}))))
    reject(changed=(("ls-tree", base, "--", V38_SNAPSHOT_V4_WORKFLOW), ""))
    reject(changed=(("ls-tree", head, "--", V38_SNAPSHOT_V4_WORKFLOW),
                    "100644 blob " + "d" * 40 + "\t" + V38_SNAPSHOT_V4_WORKFLOW))
    reject(changed=(("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                    "d" * 40))
    reject(changed=(("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"),
                    "d" * 40))


def admit_v38_snapshot_v5(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Source-only: one exact PR, exact workflow-before/after and unchanged owner."""
    if (not is_sha(head_sha) or base_sha != V38_SNAPSHOT_V5_BASE
            or type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V38_SNAPSHOT_V5_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_SNAPSHOT_V5_OWNER_OR_PARENT_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_SNAPSHOT_V5_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_SNAPSHOT_V5_WORKFLOW)
        owner = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_SNAPSHOT_V5_EXACT_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_SNAPSHOT_V5_BASE or tree != V38_SNAPSHOT_V5_BASE_TREE
            or len(paths) != len(V38_SNAPSHOT_V5_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_SNAPSHOT_V5_FILES
            or before != "100644 blob " + V38_SNAPSHOT_V5_BEFORE +
                         "\t" + V38_SNAPSHOT_V5_WORKFLOW
            or after != "100644 blob " + V38_SNAPSHOT_V5_AFTER +
                        "\t" + V38_SNAPSHOT_V5_WORKFLOW
            or owner != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or prior != "6ead37ed976f65b54a8753471c4d4369826bdcc9"):
        raise ValueError("G145_V38_SNAPSHOT_V5_SOURCE_OR_OWNER_GUARD_DRIFT")
    return V38_SNAPSHOT_V5_RESULT


def v38_snapshot_v5_negative_controls() -> None:
    base, head = V38_SNAPSHOT_V5_BASE, "e" * 40
    request = {"number": V38_SNAPSHOT_V5_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def valid(*args):
        cases = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_SNAPSHOT_V5_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_SNAPSHOT_V5_FILES)),
            ("ls-tree", base, "--", V38_SNAPSHOT_V5_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V5_BEFORE + "\t" + V38_SNAPSHOT_V5_WORKFLOW,
            ("ls-tree", head, "--", V38_SNAPSHOT_V5_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_V5_AFTER + "\t" + V38_SNAPSHOT_V5_WORKFLOW,
            ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"):
                "6ead37ed976f65b54a8753471c4d4369826bdcc9",
        }
        if args not in cases:
            raise AssertionError("unexpected source test read")
        return cases[args]
    if admit_v38_snapshot_v5(head, base, request, valid) != V38_SNAPSHOT_V5_RESULT:
        raise ValueError("G145_V38_SNAPSHOT_V5_POSITIVE_FAILED")
    def reject(req=request, parent=base, changed=None):
        def reader(*args):
            if changed is not None and args == changed[0]:
                return changed[1]
            return valid(*args)
        try:
            admit_v38_snapshot_v5(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_SNAPSHOT_V5_NEGATIVE_ADMITTED")
    reject({**request, "number": 1768})
    reject({**request, "author_association": "CONTRIBUTOR"})
    reject({**request, "user": {"login": "OTHER"}})
    reject(parent="d" * 40)
    reject(changed=(("merge-base", base, head), "d" * 40))
    reject(changed=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_SNAPSHOT_V5_FILES - {V38_SNAPSHOT_V5_WORKFLOW}))))
    reject(changed=(("ls-tree", base, "--", V38_SNAPSHOT_V5_WORKFLOW), ""))
    reject(changed=(("ls-tree", head, "--", V38_SNAPSHOT_V5_WORKFLOW),
                    "100644 blob " + "d" * 40 + "\t" + V38_SNAPSHOT_V5_WORKFLOW))
    reject(changed=(("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                    "d" * 40))
    reject(changed=(("rev-parse", head + ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"),
                    "d" * 40))


def admit_v38_forward_v2(head_sha: str, base_sha: str,
                         request: dict, git: Callable[..., str]) -> str:
    """One exact source-only PR1773; no new scheduler or task surface."""
    if (not is_sha(head_sha) or base_sha != V38_FORWARD_V2_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V38_FORWARD_V2_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_FORWARD_V2_OWNER_OR_BASE_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        files = git("diff", "--no-renames", "--name-only",
                    base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_FORWARD_V2_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_FORWARD_V2_WORKFLOW)
        readiness = git("rev-parse", head_sha +
                        ":f139/nci04_v41_hybrid_forward_readiness.py")
        old = git("rev-parse", head_sha +
                  ":.github/workflows/f139-v41-original-owner-live-install.yml")
        backup = git("rev-parse", head_sha +
                     ":f139/nci04_v41_hybrid_forward_backup.py")
        commit = git("rev-parse", head_sha +
                     ":f139/nci04_v41_hybrid_forward_original_commit.py")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_FORWARD_V2_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_FORWARD_V2_BASE
            or tree != V38_FORWARD_V2_BASE_TREE
            or len(files) != len(V38_FORWARD_V2_FILES)
            or len(set(files)) != len(files)
            or set(files) != V38_FORWARD_V2_FILES
            or before != "100644 blob " + V38_FORWARD_V2_BEFORE +
                         "\t" + V38_FORWARD_V2_WORKFLOW
            or after != "100644 blob " + V38_FORWARD_V2_AFTER +
                        "\t" + V38_FORWARD_V2_WORKFLOW
            or readiness != V38_FORWARD_V2_READINESS_BLOB
            or old != V38_FORWARD_V2_OLD_WORKFLOW
            or backup != V38_FORWARD_V2_BACKUP
            or commit != V38_FORWARD_V2_COMMIT):
        raise ValueError("G145_V38_FORWARD_V2_ORIGINAL_OWNER_SOURCE_DRIFT")
    return V38_FORWARD_V2_RESULT


def v38_forward_v2_negative_controls() -> None:
    base, head = V38_FORWARD_V2_BASE, "e" * 40
    request = {"number": V38_FORWARD_V2_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    values = {
        ("merge-base", base, head): base,
        ("rev-parse", base + "^{tree}"): V38_FORWARD_V2_BASE_TREE,
        ("diff", "--no-renames", "--name-only", base, head):
            "\n".join(sorted(V38_FORWARD_V2_FILES)),
        ("ls-tree", base, "--", V38_FORWARD_V2_WORKFLOW):
            "100644 blob " + V38_FORWARD_V2_BEFORE +
            "\t" + V38_FORWARD_V2_WORKFLOW,
        ("ls-tree", head, "--", V38_FORWARD_V2_WORKFLOW):
            "100644 blob " + V38_FORWARD_V2_AFTER +
            "\t" + V38_FORWARD_V2_WORKFLOW,
        ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_readiness.py"):
            V38_FORWARD_V2_READINESS_BLOB,
        ("rev-parse", head + ":.github/workflows/f139-v41-original-owner-live-install.yml"):
            V38_FORWARD_V2_OLD_WORKFLOW,
        ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_backup.py"):
            V38_FORWARD_V2_BACKUP,
        ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_original_commit.py"):
            V38_FORWARD_V2_COMMIT,
    }
    def valid(*args):
        if args not in values:
            raise AssertionError("unknown original owner source probe")
        return values[args]
    if admit_v38_forward_v2(head, base, request, valid) != V38_FORWARD_V2_RESULT:
        raise ValueError("G145_V38_FORWARD_V2_POSITIVE_FAILED")
    def reject(req=request, parent=base, modified=None):
        def reader(*args):
            return modified[1] if modified and args == modified[0] else valid(*args)
        try:
            admit_v38_forward_v2(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_FORWARD_V2_NEGATIVE_ADMITTED")
    reject({**request, "number": 1772})
    reject({**request, "author_association": "COLLABORATOR"})
    reject({**request, "user": {"login": "other"}})
    reject(parent="f" * 40)
    for pair in (
        (("merge-base", base, head), "f" * 40),
        (("rev-parse", base + "^{tree}"), "f" * 40),
        (("diff", "--no-renames", "--name-only", base, head),
         "\n".join(sorted(V38_FORWARD_V2_FILES - {V38_FORWARD_V2_WORKFLOW}))),
        (("ls-tree", base, "--", V38_FORWARD_V2_WORKFLOW), ""),
        (("ls-tree", head, "--", V38_FORWARD_V2_WORKFLOW),
         "100644 blob " + "f" * 40 + "\t" + V38_FORWARD_V2_WORKFLOW),
        (("rev-parse", head + ":f139/nci04_v41_hybrid_forward_readiness.py"),
         "f" * 40),
        (("rev-parse", head + ":.github/workflows/f139-v41-original-owner-live-install.yml"),
         "f" * 40),
        (("rev-parse", head + ":f139/nci04_v41_hybrid_forward_backup.py"),
         "f" * 40),
        (("rev-parse", head + ":f139/nci04_v41_hybrid_forward_original_commit.py"),
         "f" * 40),
    ):
        reject(modified=pair)


def admit_v38_forward_release(head_sha: str, base_sha: str,
                              request: dict, git: Callable[..., str]) -> str:
    """Exact PR1772, 8-file source scope, unmodified original owner guards."""
    if (not is_sha(head_sha) or base_sha != V38_FORWARD_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V38_FORWARD_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_FORWARD_OWNER_AND_BASE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        base_tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only",
                    base_sha, head_sha).splitlines()
        workflow = git("ls-tree", head_sha, "--", V38_FORWARD_WORKFLOW)
        before = git("ls-tree", base_sha, "--", V38_FORWARD_WORKFLOW)
        readiness = git("rev-parse", head_sha +
                        ":f139/nci04_v41_hybrid_forward_readiness.py")
        legacy = git("rev-parse", head_sha +
                     ":.github/workflows/f139-v41-original-owner-live-install.yml")
        original_backup = git("rev-parse", head_sha +
                              ":f139/nci04_v41_hybrid_forward_backup.py")
        source_commit = git("rev-parse", head_sha +
                            ":f139/nci04_v41_hybrid_forward_original_commit.py")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_FORWARD_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_FORWARD_BASE
            or base_tree != V38_FORWARD_BASE_TREE
            or before != ""
            or workflow != "100644 blob " + V38_FORWARD_WORKFLOW_BLOB +
                           "\t" + V38_FORWARD_WORKFLOW
            or len(paths) != len(V38_FORWARD_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_FORWARD_FILES
            or readiness != V38_FORWARD_READINESS_BLOB
            or legacy != V38_FORWARD_OLD_WORKFLOW_BLOB
            or original_backup != V38_FORWARD_ORIGINAL_BACKUP_BLOB
            or source_commit != V38_FORWARD_SOURCE_COMMIT_BLOB):
        raise ValueError("G145_V38_FORWARD_EXACT_SOURCE_AND_OLD_OWNER_DRIFT")
    return V38_FORWARD_RESULT


def v38_forward_negative_controls() -> None:
    base, head = V38_FORWARD_BASE, "e" * 40
    request = {"number": V38_FORWARD_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    values = {
        ("merge-base", base, head): base,
        ("rev-parse", base + "^{tree}"): V38_FORWARD_BASE_TREE,
        ("diff", "--no-renames", "--name-only", base, head):
            "\n".join(sorted(V38_FORWARD_FILES)),
        ("ls-tree", base, "--", V38_FORWARD_WORKFLOW): "",
        ("ls-tree", head, "--", V38_FORWARD_WORKFLOW):
            "100644 blob " + V38_FORWARD_WORKFLOW_BLOB +
            "\t" + V38_FORWARD_WORKFLOW,
        ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_readiness.py"):
            V38_FORWARD_READINESS_BLOB,
        ("rev-parse", head + ":.github/workflows/f139-v41-original-owner-live-install.yml"):
            V38_FORWARD_OLD_WORKFLOW_BLOB,
        ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_backup.py"):
            V38_FORWARD_ORIGINAL_BACKUP_BLOB,
        ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_original_commit.py"):
            V38_FORWARD_SOURCE_COMMIT_BLOB,
    }
    def valid(*args):
        if args not in values:
            raise AssertionError("unexpected source guard read")
        return values[args]
    if admit_v38_forward_release(head, base, request, valid) != V38_FORWARD_RESULT:
        raise ValueError("G145_V38_FORWARD_POSITIVE_FAILED")
    def reject(req=request, parent=base, modified=None):
        def reader(*args):
            return modified[1] if modified and args == modified[0] else valid(*args)
        try:
            admit_v38_forward_release(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_FORWARD_NEGATIVE_ADMITTED")
    reject({**request, "number": 1771})
    reject({**request, "author_association": "COLLABORATOR"})
    reject({**request, "user": {"login": "OTHER"}})
    reject(parent="f" * 40)
    for pair in (
        (("merge-base", base, head), "f" * 40),
        (("rev-parse", base + "^{tree}"), "f" * 40),
        (("diff", "--no-renames", "--name-only", base, head),
         "\n".join(sorted(V38_FORWARD_FILES - {V38_FORWARD_WORKFLOW}))),
        (("ls-tree", base, "--", V38_FORWARD_WORKFLOW), "100644 blob " + "a" * 40 +
         "\t" + V38_FORWARD_WORKFLOW),
        (("ls-tree", head, "--", V38_FORWARD_WORKFLOW), "100644 blob " + "a" * 40 +
         "\t" + V38_FORWARD_WORKFLOW),
        (("rev-parse", head + ":f139/nci04_v41_hybrid_forward_readiness.py"),
         "f" * 40),
        (("rev-parse", head + ":.github/workflows/f139-v41-original-owner-live-install.yml"),
         "f" * 40),
        (("rev-parse", head + ":f139/nci04_v41_hybrid_forward_backup.py"),
         "f" * 40),
        (("rev-parse", head + ":f139/nci04_v41_hybrid_forward_original_commit.py"),
         "f" * 40),
    ):
        reject(modified=pair)


def admit_v38_cold_ledger(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Source-only: one exact PR, exact workflow-before/after and unchanged owner."""
    if (not is_sha(head_sha) or base_sha != V38_COLD_BASE
            or type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V38_COLD_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_COLD_OWNER_OR_PARENT_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_COLD_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_COLD_WORKFLOW)
        owner = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v41-original-owner-live-install.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_COLD_EXACT_SOURCE_UNAVAILABLE") from exc
    if (ancestor != V38_COLD_BASE or tree != V38_COLD_BASE_TREE
            or len(paths) != len(V38_COLD_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_COLD_FILES
            or before != "100644 blob " + V38_COLD_BEFORE +
                         "\t" + V38_COLD_WORKFLOW
            or after != "100644 blob " + V38_COLD_AFTER +
                        "\t" + V38_COLD_WORKFLOW
            or owner != "4c0226a10eed5987ab30a4156e7c1b3f1550934e"
            or prior != "6ad719d04639f96e3342f33bcbc9c5b379557e52"):
        raise ValueError("G145_V38_COLD_SOURCE_OR_OWNER_GUARD_DRIFT")
    return V38_COLD_RESULT


def v38_cold_ledger_negative_controls() -> None:
    base, head = V38_COLD_BASE, "e" * 40
    request = {"number": V38_COLD_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def valid(*args):
        cases = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_COLD_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_COLD_FILES)),
            ("ls-tree", base, "--", V38_COLD_WORKFLOW):
                "100644 blob " + V38_COLD_BEFORE + "\t" + V38_COLD_WORKFLOW,
            ("ls-tree", head, "--", V38_COLD_WORKFLOW):
                "100644 blob " + V38_COLD_AFTER + "\t" + V38_COLD_WORKFLOW,
            ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "4c0226a10eed5987ab30a4156e7c1b3f1550934e",
            ("rev-parse", head + ":.github/workflows/f139-v41-original-owner-live-install.yml"):
                "6ad719d04639f96e3342f33bcbc9c5b379557e52",
        }
        if args not in cases:
            raise AssertionError("unexpected source test read")
        return cases[args]
    if admit_v38_cold_ledger(head, base, request, valid) != V38_COLD_RESULT:
        raise ValueError("G145_V38_COLD_POSITIVE_FAILED")
    def reject(req=request, parent=base, changed=None):
        def reader(*args):
            if changed is not None and args == changed[0]:
                return changed[1]
            return valid(*args)
        try:
            admit_v38_cold_ledger(head, parent, req, reader)
        except ValueError:
            return
        raise ValueError("G145_V38_COLD_NEGATIVE_ADMITTED")
    reject({**request, "number": 1770})
    reject({**request, "author_association": "CONTRIBUTOR"})
    reject({**request, "user": {"login": "OTHER"}})
    reject(parent="d" * 40)
    reject(changed=(("merge-base", base, head), "d" * 40))
    reject(changed=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_COLD_FILES - {V38_COLD_WORKFLOW}))))
    reject(changed=(("ls-tree", base, "--", V38_COLD_WORKFLOW), ""))
    reject(changed=(("ls-tree", head, "--", V38_COLD_WORKFLOW),
                    "100644 blob " + "d" * 40 + "\t" + V38_COLD_WORKFLOW))
    reject(changed=(("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                    "d" * 40))
    reject(changed=(("rev-parse", head + ":.github/workflows/f139-v41-original-owner-live-install.yml"),
                    "d" * 40))


def admit_v39_actions_get(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """One exact owner PR; only a read-only diagnostic, never task authority."""
    if (not is_sha(head_sha) or base_sha != V39_ACTIONS_GET_BASE
            or type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V39_ACTIONS_GET_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V39_OWNER_OR_BASE_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V39_ACTIONS_GET_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V39_ACTIONS_GET_WORKFLOW)
        owner = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        legacy = git("rev-parse", head_sha +
                     ":.github/workflows/f139-v38-original-task-snapshot-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V39_SOURCE_UNREADABLE") from exc
    if (ancestor != V39_ACTIONS_GET_BASE
            or tree != V39_ACTIONS_GET_BASE_TREE
            or len(paths) != len(V39_ACTIONS_GET_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V39_ACTIONS_GET_FILES
            or before != ""
            or after != "100644 blob " + V39_ACTIONS_GET_WORKFLOW_BLOB +
                        "\t" + V39_ACTIONS_GET_WORKFLOW
            or owner != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or legacy != "6857bf5c81d9662f7cf26f4a07eb59e463ac8253"):
        raise ValueError("G145_V39_EXACT_SOURCE_OR_OWNER_CHANGED")
    return V39_ACTIONS_GET_RESULT


def v39_actions_get_negative_controls() -> None:
    base, head = V39_ACTIONS_GET_BASE, "e" * 40
    owner = {"number": V39_ACTIONS_GET_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def valid(*args):
        cases = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V39_ACTIONS_GET_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V39_ACTIONS_GET_FILES)),
            ("ls-tree", base, "--", V39_ACTIONS_GET_WORKFLOW): "",
            ("ls-tree", head, "--", V39_ACTIONS_GET_WORKFLOW):
                "100644 blob " + V39_ACTIONS_GET_WORKFLOW_BLOB +
                "\t" + V39_ACTIONS_GET_WORKFLOW,
            ("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head + ":.github/workflows/f139-v38-original-task-snapshot-once.yml"):
                "6857bf5c81d9662f7cf26f4a07eb59e463ac8253",
        }
        if args not in cases:
            raise AssertionError("unexpected V39 source lookup")
        return cases[args]
    if admit_v39_actions_get(head, base, owner, valid) != V39_ACTIONS_GET_RESULT:
        raise ValueError("G145_V39_POSITIVE_FAILED")
    def reject(request=owner, parent=base, changed=None):
        def reader(*args):
            if changed is not None and args == changed[0]:
                return changed[1]
            return valid(*args)
        try:
            admit_v39_actions_get(head, parent, request, reader)
        except ValueError:
            return
        raise ValueError("G145_V39_NEGATIVE_ADMITTED")
    reject({**owner, "number": 1767})
    reject({**owner, "user": {"login": "OTHER"}})
    reject({**owner, "author_association": "CONTRIBUTOR"})
    reject(parent="f" * 40)
    reject(changed=(("merge-base", base, head), "d" * 40))
    reject(changed=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V39_ACTIONS_GET_FILES -
                                     {V39_ACTIONS_GET_WORKFLOW}))))
    reject(changed=(("ls-tree", base, "--", V39_ACTIONS_GET_WORKFLOW),
                    "unexpected pre-existing workflow"))
    reject(changed=(("ls-tree", head, "--", V39_ACTIONS_GET_WORKFLOW),
                    "100644 blob " + "d" * 40 + "\t" + V39_ACTIONS_GET_WORKFLOW))
    reject(changed=(("rev-parse", head + ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                    "d" * 40))
    reject(changed=(("rev-parse", head + ":.github/workflows/f139-v38-original-task-snapshot-once.yml"),
                    "d" * 40))


def admit_v38_snapshot(head_sha: str, base_sha: str,
                       request: dict, git: Callable[..., str]) -> str:
    """Pin exact source+unchanged original guard, never admit generic CI edits."""
    if (not is_sha(head_sha) or base_sha != V38_SNAPSHOT_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V38_SNAPSHOT_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_SNAPSHOT_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only",
                    base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_SNAPSHOT_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_SNAPSHOT_WORKFLOW)
        original = git("rev-parse", head_sha +
                       ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_SNAPSHOT_SOURCE_NOT_AVAILABLE") from exc
    if (ancestor != V38_SNAPSHOT_BASE or tree != V38_SNAPSHOT_BASE_TREE
            or len(paths) != len(V38_SNAPSHOT_FILES)
            or set(paths) != V38_SNAPSHOT_FILES
            or len(set(paths)) != len(paths)
            or before != ""
            or after != "100644 blob " + V38_SNAPSHOT_WORKFLOW_BLOB +
                        "\t" + V38_SNAPSHOT_WORKFLOW
            or original != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or prior != "6ead37ed976f65b54a8753471c4d4369826bdcc9"):
        raise ValueError("G145_V38_SNAPSHOT_SOURCE_ORIGINAL_GUARD_DRIFT")
    return V38_SNAPSHOT_RESULT


def v38_snapshot_negative_controls() -> None:
    base, head = V38_SNAPSHOT_BASE, "c" * 40
    owner = {"number": V38_SNAPSHOT_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def source(*args):
        available = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_SNAPSHOT_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_SNAPSHOT_FILES)),
            ("ls-tree", base, "--", V38_SNAPSHOT_WORKFLOW): "",
            ("ls-tree", head, "--", V38_SNAPSHOT_WORKFLOW):
                "100644 blob " + V38_SNAPSHOT_WORKFLOW_BLOB +
                "\t" + V38_SNAPSHOT_WORKFLOW,
            ("rev-parse", head +
             ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head +
             ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"):
                "6ead37ed976f65b54a8753471c4d4369826bdcc9",
        }
        if args not in available:
            raise AssertionError("unexpected original owner G145 GET")
        return available[args]
    if admit_v38_snapshot(head, base, owner, source) != V38_SNAPSHOT_RESULT:
        raise ValueError("G145_V38_SNAPSHOT_POSITIVE_CONTROL_FAILED")
    def reject(request=owner, candidate_base=base, change=None):
        def modified(*args):
            return change[1] if change and args == change[0] else source(*args)
        try:
            admit_v38_snapshot(head, candidate_base, request, modified)
        except ValueError:
            return
        raise ValueError("G145_V38_SNAPSHOT_NEGATIVE_CONTROL_ACCEPTED")
    reject({**owner, "number": 1762})
    reject({**owner, "author_association": "CONTRIBUTOR"})
    reject({**owner, "user": {"login": "OTHER"}})
    reject(candidate_base="d" * 40)
    reject(change=(("merge-base", base, head), "d" * 40))
    reject(change=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(change=(("diff", "--no-renames", "--name-only", base, head),
                   "\n".join(sorted(V38_SNAPSHOT_FILES -
                                      {V38_SNAPSHOT_WORKFLOW}))))
    reject(change=(("diff", "--no-renames", "--name-only", base, head),
                   "\n".join(sorted(V38_SNAPSHOT_FILES |
                                      {".github/workflows/qualify.yml"}))))
    reject(change=(("ls-tree", base, "--", V38_SNAPSHOT_WORKFLOW),
                   "100644 blob " + "d" * 40 + "\t" + V38_SNAPSHOT_WORKFLOW))
    reject(change=(("ls-tree", head, "--", V38_SNAPSHOT_WORKFLOW),
                   "100644 blob " + "d" * 40 + "\t" + V38_SNAPSHOT_WORKFLOW))
    reject(change=(("rev-parse", head +
                   ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                   "d" * 40))
    reject(change=(("rev-parse", head +
                   ":.github/workflows/f139-v38-held-task-stage-diagnostic-once.yml"),
                   "d" * 40))


def admit_v38_stage_diagnostic(head_sha: str, base_sha: str,
                               request: dict, git: Callable[..., str]) -> str:
    """Only exact PR1762, same protected base, seven paths, unchanged guard."""
    if (not is_sha(head_sha) or base_sha != V38_STAGE_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V38_STAGE_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_STAGE_OWNER_PR_OR_BASE_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only",
                    base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_STAGE_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_STAGE_WORKFLOW)
        original = git("rev-parse", head_sha +
                       ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        previous = git("rev-parse", head_sha +
                       ":.github/workflows/f139-v38-held-task-guard-diagnostic-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_STAGE_SOURCE_UNREADABLE") from exc
    if (ancestor != V38_STAGE_BASE
            or tree != V38_STAGE_BASE_TREE
            or len(paths) != len(V38_STAGE_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_STAGE_FILES
            or before != ""
            or after != "100644 blob " + V38_STAGE_WORKFLOW_BLOB +
                         "\t" + V38_STAGE_WORKFLOW
            or original != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or previous != "28924c2905d20e47d21a278ed763ad4a8904dda0"):
        raise ValueError("G145_V38_STAGE_SOURCE_OR_GUARD_BLOB_DRIFT")
    return V38_STAGE_RESULT


def v38_stage_negative_controls() -> None:
    head, base = "c" * 40, V38_STAGE_BASE
    owner = {"number": V38_STAGE_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def source(*args):
        results = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_STAGE_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_STAGE_FILES)),
            ("ls-tree", base, "--", V38_STAGE_WORKFLOW): "",
            ("ls-tree", head, "--", V38_STAGE_WORKFLOW):
                "100644 blob " + V38_STAGE_WORKFLOW_BLOB + "\t" + V38_STAGE_WORKFLOW,
            ("rev-parse", head +
             ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head +
             ":.github/workflows/f139-v38-held-task-guard-diagnostic-once.yml"):
                "28924c2905d20e47d21a278ed763ad4a8904dda0",
        }
        if args not in results:
            raise AssertionError("unexpected G145 original read route")
        return results[args]
    if admit_v38_stage_diagnostic(head, base, owner, source) != V38_STAGE_RESULT:
        raise ValueError("G145_V38_STAGE_POSITIVE_CONTROL_FAILED")
    def refuse(request=owner, candidate_base=base, change=None):
        def modified(*args):
            return change[1] if change and args == change[0] else source(*args)
        try:
            admit_v38_stage_diagnostic(head, candidate_base,
                                      request, modified)
        except ValueError:
            return
        raise ValueError("G145_V38_STAGE_NEGATIVE_CONTROL_BYPASS")
    refuse({**owner, "number": 1761})
    refuse({**owner, "author_association": "CONTRIBUTOR"})
    refuse({**owner, "user": {"login": "other"}})
    refuse(candidate_base="d" * 40)
    refuse(change=(("merge-base", base, head), "d" * 40))
    refuse(change=(("rev-parse", base + "^{tree}"), "d" * 40))
    refuse(change=(("diff", "--no-renames", "--name-only", base, head),
                   "\n".join(sorted(V38_STAGE_FILES - {V38_STAGE_WORKFLOW}))))
    refuse(change=(("diff", "--no-renames", "--name-only", base, head),
                   "\n".join(sorted(V38_STAGE_FILES |
                                      {".github/workflows/qualify.yml"}))))
    refuse(change=(("ls-tree", head, "--", V38_STAGE_WORKFLOW),
                   "100644 blob " + "d" * 40 + "\t" + V38_STAGE_WORKFLOW))
    refuse(change=(("ls-tree", base, "--", V38_STAGE_WORKFLOW),
                   "100644 blob " + "d" * 40 + "\t" + V38_STAGE_WORKFLOW))
    refuse(change=(("rev-parse", head +
                   ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                   "d" * 40))
    refuse(change=(("rev-parse", head +
                   ":.github/workflows/f139-v38-held-task-guard-diagnostic-once.yml"),
                   "d" * 40))


def admit_v38_guard_diagnostic(head_sha: str, base_sha: str,
                               request: dict, git: Callable[..., str]) -> str:
    """Only exact owner PR1761 on the protected prior-failure main source.

    Workflow immutable blob, exact seven paths, original profile bytes and
    consumed read-only workflow pinned. This is engineering CI admission
    only and never grants a task, first-use or privileged execution right.
    """
    if (not is_sha(head_sha) or base_sha != V38_DIAG_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V38_DIAG_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_GUARD_DIAG_OWNER_PR_BASE_DENIED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only",
                    base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_DIAG_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_DIAG_WORKFLOW)
        guard = git("rev-parse", head_sha +
                    ":f139/nci04_v41_hybrid_forward_owner_profile.py")
        prior = git("rev-parse", head_sha +
                    ":.github/workflows/f139-v38-original-owner-readonly-once.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_DIAGNOSTIC_SOURCE_UNREADABLE") from exc
    if (ancestor != V38_DIAG_BASE
            or tree != V38_DIAG_BASE_TREE
            or len(paths) != len(V38_DIAG_FILES)
            or len(set(paths)) != len(paths)
            or set(paths) != V38_DIAG_FILES
            or before != ""
            or after != "100644 blob " + V38_DIAG_WORKFLOW_BLOB +
                        "\t" + V38_DIAG_WORKFLOW
            or guard != "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6"
            or prior != "087348d173fac524195cf72dc78df222c5851485"):
        raise ValueError("G145_V38_DIAGNOSTIC_SCOPE_OR_ORIGINAL_GUARD_DRIFT")
    return V38_DIAG_RESULT


def v38_diagnostic_negative_controls() -> None:
    base, head = V38_DIAG_BASE, "c" * 40
    owner = {"number": V38_DIAG_PR, "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def good(*args):
        responses = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_DIAG_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_DIAG_FILES)),
            ("ls-tree", base, "--", V38_DIAG_WORKFLOW): "",
            ("ls-tree", head, "--", V38_DIAG_WORKFLOW):
                "100644 blob " + V38_DIAG_WORKFLOW_BLOB + "\t" + V38_DIAG_WORKFLOW,
            ("rev-parse", head +
             ":f139/nci04_v41_hybrid_forward_owner_profile.py"):
                "9bda78341bc3651e8b7b0a24ea6c7858dbff05c6",
            ("rev-parse", head +
             ":.github/workflows/f139-v38-original-owner-readonly-once.yml"):
                "087348d173fac524195cf72dc78df222c5851485",
        }
        if args not in responses:
            raise AssertionError("unexpected original owner CI source lookup")
        return responses[args]
    if admit_v38_guard_diagnostic(head, base, owner, good) != V38_DIAG_RESULT:
        raise ValueError("G145_V38_DIAG_POSITIVE_CONTROL_FAILED")
    def reject(request=owner, candidate_base=base, replacement=None):
        def changed(*args):
            return replacement[1] if replacement and args == replacement[0] else good(*args)
        try:
            admit_v38_guard_diagnostic(head, candidate_base, request, changed)
        except ValueError:
            return
        raise ValueError("G145_V38_DIAG_UNAUTHORIZED_SOURCE_ACCEPTED")
    reject({**owner, "number": 1759})
    reject({**owner, "author_association": "CONTRIBUTOR"})
    reject({**owner, "user": {"login": "OTHER"}})
    reject(candidate_base="d" * 40)
    reject(replacement=(("merge-base", base, head), "d" * 40))
    reject(replacement=(("rev-parse", base + "^{tree}"), "d" * 40))
    reject(replacement=(("diff", "--no-renames", "--name-only", base, head),
                        "\n".join(sorted(V38_DIAG_FILES -
                                           {V38_DIAG_WORKFLOW}))))
    reject(replacement=(("diff", "--no-renames", "--name-only", base, head),
                        "\n".join(sorted(V38_DIAG_FILES |
                                           {".github/workflows/qualify.yml"}))))
    reject(replacement=(("ls-tree", base, "--", V38_DIAG_WORKFLOW),
                        "100644 blob " + "d" * 40 + "\t" + V38_DIAG_WORKFLOW))
    reject(replacement=(("ls-tree", head, "--", V38_DIAG_WORKFLOW),
                        "100644 blob " + "d" * 40 + "\t" + V38_DIAG_WORKFLOW))
    reject(replacement=(("ls-tree", head, "--", V38_DIAG_WORKFLOW),
                        "100755 blob " + V38_DIAG_WORKFLOW_BLOB + "\t" +
                        V38_DIAG_WORKFLOW))
    reject(replacement=(("rev-parse", head +
                        ":f139/nci04_v41_hybrid_forward_owner_profile.py"),
                        "d" * 40))
    reject(replacement=(("rev-parse", head +
                        ":.github/workflows/f139-v38-original-owner-readonly-once.yml"),
                        "d" * 40))


def admit_v38_owner_readonly(head_sha: str, base_sha: str,
                             request: dict, git: Callable[..., str]) -> str:
    """Exactly PR1760's immutable read-only owner workflow, not generic CI.

    Pin protected predecessor SHA/tree, full source delta, verified PR owner,
    the absence of the new job on main, and exact reviewed workflow bytes.
    No running the job, ref update, source mutation, or science authorization.
    """
    if (not is_sha(head_sha) or base_sha != V38_READONLY_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V38_READONLY_PR
            or type(request.get("user")) is not dict
            or request["user"].get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V38_READONLY_EXACT_PR_OWNER_AND_BASE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        paths = git("diff", "--no-renames", "--name-only", base_sha,
                    head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V38_READONLY_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V38_READONLY_WORKFLOW)
        predecessor = git(
            "rev-parse", head_sha +
            ":.github/workflows/f139-v41-original-owner-live-install.yml")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V38_READONLY_FROZEN_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha
            or tree != V38_READONLY_BASE_TREE
            or len(paths) != len(V38_READONLY_FILES)
            or set(paths) != V38_READONLY_FILES
            or before != ""
            or after != "100644 blob " + V38_READONLY_BLOB + "\t" +
                V38_READONLY_WORKFLOW
            or predecessor != "6ad719d04639f96e3342f33bcbc9c5b379557e52"):
        raise ValueError("G145_V38_READONLY_SOURCE_OR_WORKFLOW_BLOB_DRIFT")
    return V38_READONLY_RESULT


def v38_readonly_negative_controls() -> None:
    """Self-test immutable route including negative owner/source/workflow cases."""
    base, head = V38_READONLY_BASE, "b" * 40
    owner = {
        "number": V38_READONLY_PR,
        "user": {"login": "spoonman136668-ai"},
        "author_association": "OWNER",
    }

    def original(*args):
        lookups = {
            ("merge-base", base, head): base,
            ("rev-parse", base + "^{tree}"): V38_READONLY_BASE_TREE,
            ("diff", "--no-renames", "--name-only", base, head):
                "\n".join(sorted(V38_READONLY_FILES)),
            ("ls-tree", base, "--", V38_READONLY_WORKFLOW): "",
            ("ls-tree", head, "--", V38_READONLY_WORKFLOW):
                "100644 blob " + V38_READONLY_BLOB + "\t" + V38_READONLY_WORKFLOW,
            ("rev-parse", head +
             ":.github/workflows/f139-v41-original-owner-live-install.yml"):
                "6ad719d04639f96e3342f33bcbc9c5b379557e52",
        }
        if args not in lookups:
            raise AssertionError("unexpected original owner G145 source lookup")
        return lookups[args]

    if admit_v38_owner_readonly(head, base, owner, original) != V38_READONLY_RESULT:
        raise ValueError("G145_V38_READONLY_POSITIVE_CONTROL_FAILED")

    def denied(request=owner, candidate_base=base, changed=None):
        def fake(*args):
            return changed[1] if changed and args == changed[0] else original(*args)
        try:
            admit_v38_owner_readonly(head, candidate_base, request, fake)
        except ValueError:
            return
        raise ValueError("G145_V38_READONLY_NEGATIVE_CONTROL_ADMITTED")

    denied({**owner, "number": 1759})
    denied({**owner, "user": {"login": "another"}})
    denied({**owner, "author_association": "CONTRIBUTOR"})
    denied(candidate_base="f" * 40)
    denied(changed=(("merge-base", base, head), "f" * 40))
    denied(changed=(("rev-parse", base + "^{tree}"), "f" * 40))
    denied(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_READONLY_FILES -
                                       {V38_READONLY_WORKFLOW}))))
    denied(changed=(("diff", "--no-renames", "--name-only", base, head),
                    "\n".join(sorted(V38_READONLY_FILES |
                                       {".github/workflows/qualify.yml"}))))
    denied(changed=(("ls-tree", base, "--", V38_READONLY_WORKFLOW),
                    "100644 blob " + "a" * 40 + "\t" + V38_READONLY_WORKFLOW))
    denied(changed=(("ls-tree", head, "--", V38_READONLY_WORKFLOW),
                    "100644 blob " + "a" * 40 + "\t" + V38_READONLY_WORKFLOW))
    denied(changed=(("ls-tree", head, "--", V38_READONLY_WORKFLOW),
                    "100755 blob " + V38_READONLY_BLOB + "\t" +
                    V38_READONLY_WORKFLOW))
    denied(changed=(("rev-parse", head +
                    ":.github/workflows/f139-v41-original-owner-live-install.yml"),
                    "a" * 40))


def generic_paths_safe(paths: list[str]) -> bool:
    if not paths or len(paths) > 128 or len(set(paths)) != len(paths):
        return False
    for path in paths:
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\\" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
            or any(ord(ch) < 32 for ch in path)
            or path.startswith(".github/workflows/")
            or path.startswith("scripts/check_rar_")
        ):
            return False
    return True


def negative_controls() -> None:
    valid = ["docs/EUREKA.md", "nativediscovery/f6_repair.go"]
    invalid = [
        [],
        ["nativediscovery/f6_repair.go"] * 2,
        ["nativediscovery/f6_repair.go"] * 129,
        [".github/workflows/qualify.yml"],
        ["scripts/check_rar_g141_parallel_go.py"],
        ["scripts/check_rar_g144_windows_go.py"],
        ["scripts/check_rar_g999_new_harness.py"],
        ["../unsafe.go"],
        ["/unsafe.go"],
        ["safe//unsafe.go"],
        ["safe\\unsafe.go"],
    ]
    if not generic_paths_safe(valid) or any(generic_paths_safe(x) for x in invalid):
        raise ValueError("G145_ADMISSION_NEGATIVE_CONTROL_FAILED")
    hybrid_release_negative_controls()
    hybrid_complete_negative_controls()
    v38_readonly_negative_controls()
    v38_diagnostic_negative_controls()
    v38_stage_negative_controls()
    v38_snapshot_negative_controls()
    v38_snapshot_v2_negative_controls()
    v38_snapshot_v3_negative_controls()
    v38_snapshot_v4_negative_controls()
    v38_snapshot_v5_negative_controls()
    v38_cold_ledger_negative_controls()
    v38_forward_negative_controls()
    v38_forward_v2_negative_controls()
    v39_actions_get_negative_controls()
    v41_status_negative_controls()
    v41_backup_negative_controls()
    v41_pause_negative_controls()


def admit_hybrid_workflow_release(head_sha: str, base_sha: str,
                                  request: dict, git: Callable[..., str]) -> str:
    """Qualify only #1642's exact old-to-new worker blob, never release it.

    Event head/base repository/ref identities are checked by github_event_base
    before this helper is called. No other file, harness, workflow, source
    allowlist, permission or task transition is admitted by this route.
    """
    if (not is_sha(head_sha) or not is_sha(base_sha)
            or not isinstance(request, dict)
            or not isinstance(request.get("user"), dict)
            or request.get("number") != HYBRID_RELEASE_PR
            or type(request.get("number")) is not int
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_HYBRID_RELEASE_ORIGINAL_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        anchor = git("merge-base", HYBRID_RELEASE_ANCHOR, base_sha)
        changed = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", HYBRID_WORKER_PATH)
        after = git("ls-tree", head_sha, "--", HYBRID_WORKER_PATH)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_HYBRID_RELEASE_SOURCE_UNAVAILABLE") from exc
    def entry(blob):
        return "100644 blob " + blob + "\t" + HYBRID_WORKER_PATH
    if (ancestor != base_sha or anchor != HYBRID_RELEASE_ANCHOR
            or changed != [HYBRID_WORKER_PATH]
            or before != entry(HYBRID_WORKER_BEFORE)
            or after != entry(HYBRID_WORKER_AFTER)):
        raise ValueError("G145_HYBRID_RELEASE_EXACT_SOURCE_REQUIRED")
    return "EXACT_PR1642_HYBRID_WORKER_BLOB_QUALIFICATION_ONLY"


def hybrid_release_negative_controls() -> None:
    """Run in both unchanged original full-Go qualifiers, without network."""
    head, base = "c" * 40, "b" * 40
    request = {"number": HYBRID_RELEASE_PR,
               "user": {"login": "spoonman136668-ai"},
               "author_association": "OWNER"}
    def git(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("merge-base", HYBRID_RELEASE_ANCHOR, base):
            return HYBRID_RELEASE_ANCHOR
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return HYBRID_WORKER_PATH
        if args in (("ls-tree", base, "--", HYBRID_WORKER_PATH),
                    ("ls-tree", head, "--", HYBRID_WORKER_PATH)):
            blob = HYBRID_WORKER_BEFORE if args[1] == base else HYBRID_WORKER_AFTER
            return "100644 blob " + blob + "\t" + HYBRID_WORKER_PATH
        raise AssertionError("unexpected frozen source read")
    admit_hybrid_workflow_release(head, base, request, git)
    bad_reads = (
        (("merge-base", base, head), "f" * 40),
        (("merge-base", HYBRID_RELEASE_ANCHOR, base), "f" * 40),
        (("diff", "--no-renames", "--name-only", base, head),
         HYBRID_WORKER_PATH + "\nscripts/check_rar_g145_pr_scope.py"),
        (("ls-tree", base, "--", HYBRID_WORKER_PATH),
         "100644 blob " + "f" * 40 + "\t" + HYBRID_WORKER_PATH),
        (("ls-tree", head, "--", HYBRID_WORKER_PATH),
         "100644 blob " + "f" * 40 + "\t" + HYBRID_WORKER_PATH),
        (("ls-tree", head, "--", HYBRID_WORKER_PATH),
         "100755 blob " + HYBRID_WORKER_AFTER + "\t" + HYBRID_WORKER_PATH),
    )
    for call, result in bad_reads:
        def changed_git(*args):
            return result if args == call else git(*args)
        try:
            admit_hybrid_workflow_release(head, base, request, changed_git)
        except ValueError:
            continue
        raise ValueError("G145_HYBRID_RELEASE_NEGATIVE_FAILED")
    try:
        admit_hybrid_workflow_release(head, base, dict(request, number=1643), git)
    except ValueError:
        return
    raise ValueError("G145_HYBRID_RELEASE_PR_NEGATIVE_FAILED")



def admit_v41_owner_pause(head_sha: str, base_sha: str,
                          request: dict, git: Callable[..., str]) -> str:
    """Owner PR#1735 source admission, not maintenance or deployment authority.

    Verify exact original base, owner-authored PR, 8 frozen files and the
    before/after G54 workflow blobs. No generic workflow or harness edit.
    """
    if (not is_sha(head_sha) or base_sha != V41_PAUSE_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V41_PAUSE_PR
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V41_PAUSE_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V41_PAUSE_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V41_PAUSE_WORKFLOW)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V41_PAUSE_PINNED_SOURCE_MISSING") from exc
    if (ancestor != base_sha
            or len(changed) != len(V41_PAUSE_FILES)
            or len(set(changed)) != len(changed)
            or set(changed) != V41_PAUSE_FILES
            or before != "100644 blob " + V41_PAUSE_BEFORE + "\t" + V41_PAUSE_WORKFLOW
            or after != "100644 blob " + V41_PAUSE_AFTER + "\t" + V41_PAUSE_WORKFLOW):
        raise ValueError("G145_V41_PAUSE_EXACT_WORKFLOW_OR_FILES_DRIFT")
    return V41_PAUSE_RESULT


def v41_pause_negative_controls() -> None:
    base, head = V41_PAUSE_BASE, "a"*40
    owner = {"number": V41_PAUSE_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def read(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return "\n".join(sorted(V41_PAUSE_FILES))
        if args == ("ls-tree", base, "--", V41_PAUSE_WORKFLOW):
            return "100644 blob " + V41_PAUSE_BEFORE + "\t" + V41_PAUSE_WORKFLOW
        if args == ("ls-tree", head, "--", V41_PAUSE_WORKFLOW):
            return "100644 blob " + V41_PAUSE_AFTER + "\t" + V41_PAUSE_WORKFLOW
        raise AssertionError("unexpected original source lookup")
    if admit_v41_owner_pause(head, base, owner, read) != V41_PAUSE_RESULT:
        raise ValueError("G145_V41_PAUSE_POSITIVE_CONTROL_FAILED")
    def reject(req=owner, candidate_base=base, override=None):
        def source(*args):
            return override[1] if override and args == override[0] else read(*args)
        try:
            admit_v41_owner_pause(head, candidate_base, req, source)
        except ValueError:
            return
        raise ValueError("G145_V41_PAUSE_NEGATIVE_ADMITTED")
    reject(dict(owner, number=1734))
    reject(dict(owner, user={"login": "other"}))
    reject(dict(owner, author_association="CONTRIBUTOR"))
    reject(candidate_base="f"*40)
    reject(override=(("merge-base", base, head), "f"*40))
    reject(override=(("diff", "--no-renames", "--name-only", base, head),
                     V41_PAUSE_WORKFLOW))
    reject(override=(("ls-tree", base, "--", V41_PAUSE_WORKFLOW),
                     "100644 blob " + "f"*40 + "\t" + V41_PAUSE_WORKFLOW))
    reject(override=(("ls-tree", head, "--", V41_PAUSE_WORKFLOW),
                     "100644 blob " + "f"*40 + "\t" + V41_PAUSE_WORKFLOW))
    reject(override=(("ls-tree", head, "--", V41_PAUSE_WORKFLOW),
                     "100755 blob " + V41_PAUSE_AFTER + "\t" + V41_PAUSE_WORKFLOW))


def admit_v41_owner_backup(head_sha: str, base_sha: str,
                           request: dict, git: Callable[..., str]) -> str:
    """Exact owner PR #1734 admission only; never authorizes maintenance.

    Pin old/new G54 workflow bytes, PR number/owner, exact protected base,
    and the entire seven-file change set. A generic workflow rewrite remains
    inadmissible. No task runner, science, cutover or backup is executed here.
    """
    if (not is_sha(head_sha) or base_sha != V41_BACKUP_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V41_BACKUP_PR
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V41_BACKUP_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V41_BACKUP_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V41_BACKUP_WORKFLOW)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V41_BACKUP_SOURCE_MISSING") from exc
    expected_before = ("100644 blob " + V41_BACKUP_BEFORE + "\t" +
                       V41_BACKUP_WORKFLOW)
    expected_after = ("100644 blob " + V41_BACKUP_AFTER + "\t" +
                      V41_BACKUP_WORKFLOW)
    if (ancestor != base_sha
            or len(changed) != len(V41_BACKUP_FILES)
            or len(set(changed)) != len(changed)
            or set(changed) != V41_BACKUP_FILES
            or before != expected_before or after != expected_after):
        raise ValueError("G145_V41_BACKUP_EXACT_SOURCE_OR_BLOB_REQUIRED")
    return V41_BACKUP_RESULT


def v41_backup_negative_controls() -> None:
    base, head = V41_BACKUP_BASE, "a" * 40
    owner = {"number": V41_BACKUP_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def original(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return "\n".join(sorted(V41_BACKUP_FILES))
        if args == ("ls-tree", base, "--", V41_BACKUP_WORKFLOW):
            return ("100644 blob " + V41_BACKUP_BEFORE +
                    "\t" + V41_BACKUP_WORKFLOW)
        if args == ("ls-tree", head, "--", V41_BACKUP_WORKFLOW):
            return ("100644 blob " + V41_BACKUP_AFTER +
                    "\t" + V41_BACKUP_WORKFLOW)
        raise AssertionError("unexpected git read")
    if admit_v41_owner_backup(head, base, owner, original) != V41_BACKUP_RESULT:
        raise ValueError("G145_V41_BACKUP_POSITIVE_NEGATIVE_CONTROL")
    def must_reject(req, start, overridden=None):
        def source(*args):
            if overridden and args == overridden[0]:
                return overridden[1]
            return original(*args)
        try:
            admit_v41_owner_backup(head, start, req, source)
        except ValueError:
            return
        raise ValueError("G145_V41_BACKUP_BAD_PR_OR_SOURCE_ACCEPTED")
    must_reject(dict(owner, number=1735), base)
    must_reject(dict(owner, author_association="CONTRIBUTOR"), base)
    must_reject(dict(owner, user={"login": "other"}), base)
    must_reject(owner, "f" * 40)
    must_reject(owner, base, (("merge-base", base, head), "f" * 40))
    must_reject(owner, base, (("diff", "--no-renames", "--name-only", base, head),
                             V41_BACKUP_WORKFLOW))
    must_reject(owner, base, (("ls-tree", head, "--", V41_BACKUP_WORKFLOW),
                             "100644 blob " + "f" * 40 + "\t" + V41_BACKUP_WORKFLOW))
    must_reject(owner, base, (("ls-tree", head, "--", V41_BACKUP_WORKFLOW),
                             "100755 blob " + V41_BACKUP_AFTER +
                             "\t" + V41_BACKUP_WORKFLOW))


def admit_v41_status(head_sha: str, base_sha: str,
                     request: dict, git: Callable[..., str]) -> str:
    """One original-owner-authored #1731 PR; no general workflow admission.

    Pin both the old and candidate workflow blob. The one inserted step is
    GET/query-only original owner evidence, never a task controller or release.
    This is ENGINEERING CI permission only, not execution or owner approval.
    """
    if (not is_sha(head_sha) or base_sha != V41_STATUS_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] != V41_STATUS_PR
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"):
        raise ValueError("G145_V41_EXACT_OWNER_PR_AND_BASE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        before = git("ls-tree", base_sha, "--", V41_STATUS_WORKFLOW)
        after = git("ls-tree", head_sha, "--", V41_STATUS_WORKFLOW)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V41_PINNED_SOURCE_UNREADABLE") from exc
    if (ancestor != base_sha
            or len(changed) != len(V41_STATUS_FILES)
            or len(set(changed)) != len(changed)
            or set(changed) != V41_STATUS_FILES
            or before != "100644 blob " + V41_STATUS_BEFORE + "\t" + V41_STATUS_WORKFLOW
            or after != "100644 blob " + V41_STATUS_AFTER + "\t" + V41_STATUS_WORKFLOW):
        raise ValueError("G145_V41_EXACT_WORKFLOW_BLOB_OR_FILES_DRIFT")
    return V41_STATUS_RESULT


def v41_status_negative_controls() -> None:
    base, head = V41_STATUS_BASE, "a"*40
    owner = {"number": V41_STATUS_PR,
             "user": {"login": "spoonman136668-ai"},
             "author_association": "OWNER"}
    def git(*args):
        if args == ("merge-base", base, head):
            return base
        if args == ("diff", "--no-renames", "--name-only", base, head):
            return "\n".join(sorted(V41_STATUS_FILES))
        if args == ("ls-tree", base, "--", V41_STATUS_WORKFLOW):
            return "100644 blob " + V41_STATUS_BEFORE + "\t" + V41_STATUS_WORKFLOW
        if args == ("ls-tree", head, "--", V41_STATUS_WORKFLOW):
            return "100644 blob " + V41_STATUS_AFTER + "\t" + V41_STATUS_WORKFLOW
        raise AssertionError("unexpected frozen source lookup")
    if admit_v41_status(head, base, owner, git) != V41_STATUS_RESULT:
        raise ValueError("G145_V41_STATUS_POSITIVE_CONTROL_FAILED")
    bad = (
        (dict(owner, number=1732), None, None),
        (dict(owner, author_association="CONTRIBUTOR"), None, None),
        (dict(owner, user={"login":"other"}), None, None),
        (owner, "f"*40, None),
        (owner, None, (("merge-base", base, head), "f"*40)),
        (owner, None, (("diff", "--no-renames", "--name-only", base, head),
                        "scripts/check_rar_g145_pr_scope.py")),
        (owner, None, (("ls-tree", base, "--", V41_STATUS_WORKFLOW),
                        "100644 blob " + "f"*40 + "\t" + V41_STATUS_WORKFLOW)),
        (owner, None, (("ls-tree", head, "--", V41_STATUS_WORKFLOW),
                        "100644 blob " + "f"*40 + "\t" + V41_STATUS_WORKFLOW)),
        (owner, None, (("ls-tree", head, "--", V41_STATUS_WORKFLOW),
                        "100755 blob " + V41_STATUS_AFTER + "\t" + V41_STATUS_WORKFLOW)),
    )
    for request, new_base, replacement in bad:
        def altered(*args):
            return replacement[1] if replacement and args == replacement[0] else git(*args)
        try:
            admit_v41_status(head, base if new_base is None else new_base,
                             request, altered)
        except ValueError:
            continue
        raise ValueError("G145_V41_STATUS_NEGATIVE_ACCEPTED")


def github_event_base(head_sha: str) -> str:
    """Read exact GitHub-hosted pull request event identity. No remote fetch."""
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if (
        not event_path
        or not Path(event_path).is_file()
        or Path(event_path).stat().st_size > (1 << 20)
    ):
        raise ValueError("G145_EVENT_PATH_INVALID")
    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        request = payload["pull_request"]
        head, base = request["head"], request["base"]
        base_sha = base["sha"]
        if (
            not is_sha(base_sha)
            or not is_sha(head_sha)
            or head["sha"] != head_sha
            or base["ref"] != "main"
            or base["repo"]["full_name"] != REPO
            or head["repo"]["full_name"] != REPO
            or head["ref"] != os.environ.get("GITHUB_HEAD_REF")
            or os.environ.get("GITHUB_BASE_REF") != "main"
        ):
            raise ValueError("G145_EVENT_IDENTITY_MISMATCH")
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError("G145_EVENT_IDENTITY_INVALID") from exc
    return base_sha


def admit_original_pr(head_sha: str, git: Callable[..., str]) -> str:
    """Engineering CI admission only; never research, merge or FSA authority."""
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request" or not callable(git):
        raise ValueError("G145_NOT_GITHUB_PR")
    branch = os.environ.get("GITHUB_HEAD_REF", "")
    base_sha = github_event_base(head_sha)
    if branch == V38_FORWARD_V2_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_forward_v2(head_sha, base_sha, request, git)
    if branch == V38_FORWARD_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_forward_release(head_sha, base_sha, request, git)
    if branch == V38_COLD_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_cold_ledger(head_sha, base_sha, request, git)
    if branch == V39_ACTIONS_GET_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v39_actions_get(head_sha, base_sha, request, git)
    if branch == V38_SNAPSHOT_V5_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_snapshot_v5(head_sha, base_sha, request, git)
    if branch == V38_SNAPSHOT_V4_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_snapshot_v4(head_sha, base_sha, request, git)
    if branch == V38_SNAPSHOT_V3_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_snapshot_v3(head_sha, base_sha, request, git)
    if branch == V38_SNAPSHOT_V2_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_snapshot_v2(head_sha, base_sha, request, git)
    if branch == V38_SNAPSHOT_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_snapshot(head_sha, base_sha, request, git)
    if branch == V38_STAGE_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_stage_diagnostic(head_sha, base_sha, request, git)
    if branch == V38_DIAG_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_guard_diagnostic(head_sha, base_sha, request, git)
    if branch == V38_READONLY_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v38_owner_readonly(head_sha, base_sha, request, git)
    if branch == V41_PAUSE_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v41_owner_pause(head_sha, base_sha, request, git)
    if branch == V41_BACKUP_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v41_owner_backup(head_sha, base_sha, request, git)
    if branch == V41_STATUS_BRANCH:
        payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        return admit_v41_status(head_sha, base_sha, payload["pull_request"], git)
    if branch == HYBRID_RELEASE_BRANCH:
        payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        request = payload["pull_request"]
        if payload.get("number") != HYBRID_RELEASE_PR:
            raise ValueError("G145_HYBRID_RELEASE_ORIGINAL_PR_REQUIRED")
        return admit_hybrid_workflow_release(head_sha, base_sha, request, git)
    if branch == HYBRID_COMPLETE_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_hybrid_complete(head_sha,base_sha,request,git)
    if branch in {'engineering/f139-v40-explicit-owner-handoff-20261109', 'engineering/f139-v40-qualified-readonly-route-20261109', 'engineering/f139-v40-source-bound-copy-qualification-20261109'}:
        request = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))['pull_request']
        if (request.get('user', {}).get('login') != 'spoonman136668-ai'
                or request.get('author_association') != 'OWNER'):
            raise ValueError('G145_V40_ORIGINAL_OWNER_PR_REQUIRED')
    if branch in FROZEN_SCOPES:
        if branch == "engineering/f139-v46-original-release-ref-once-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") !=
                       "2cc08f9b71a1f70d697fcd9d2d4a749eb8a39570"
                    or git("rev-parse", "2cc08f9b71a1f70d697fcd9d2d4a749eb8a39570^{tree}") !=
                       "3e4a827706a3be96d856ac50e67af736ca5ee956"
                    or git("rev-parse", "2cc08f9b71a1f70d697fcd9d2d4a749eb8a39570:" + workflow) !=
                       "557b4e5ba0daa2190c80dd53f32d31412ab14da4"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                       "267016423cf28e3c260223dbcdfc863d13adb053"):
                raise ValueError("G145_V46_EXACT_TOKEN_REF_PROVISION_SCOPE_DENIED")
        if branch == "engineering/f139-v46-event1836-live-source-transition-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("number")) is not int
                    or request["number"] != 1788
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "0a1523461fc54162c4d1104586dd69bb22d28a87^{tree}") !=
                       "385977369f3f5e22a1ff4c4ca0a2640c57287a3e"
                    or git("rev-parse", "0a1523461fc54162c4d1104586dd69bb22d28a87:" + workflow) !=
                       "3910158427d1ccd5a4b066f5481fbd9719a4e774"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                       "557b4e5ba0daa2190c80dd53f32d31412ab14da4"):
                raise ValueError("G145_V46_ORIGINAL_LIVE_RELEASE_PR1788_SCOPE_DENIED")
        if branch == "engineering/f139-v44-event1836-copy-rehearsal-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("number")) is not int
                    or request["number"] != 1786
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "4ccbb84785a43e038453d6f2bda5415ecb364084^{tree}") !=
                       "3c75fc418d1e3d9f6c8a4eb05b480003fe962bb3"
                    or git("rev-parse", "4ccbb84785a43e038453d6f2bda5415ecb364084:" + workflow) !=
                       "b812b308840c6fd20110f3819f843eb4e875602b"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                       "3910158427d1ccd5a4b066f5481fbd9719a4e774"):
                raise ValueError("G145_V44_ORIGINAL_COPY_REHEARSAL_PR1786_DENIED")
        if branch == "engineering/f139-v43-event1835-full-cold-backup-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("number")) is not int
                    or request["number"] != 1784
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "ac51b464e018b97099c7aa7fad4f6238c64b2500^{tree}") !=
                        "bc997acca85b6219cc175267e19bd7faafa3b8e3"
                    or git("rev-parse",
                           "ac51b464e018b97099c7aa7fad4f6238c64b2500:" + workflow) !=
                           "145456e37b097aafd42a3f190e538b71543115a1"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                           "b812b308840c6fd20110f3819f843eb4e875602b"):
                raise ValueError("G145_V43_ORIGINAL_COLD_BACKUP_PR1784_DENIED")
        if branch == "engineering/f139-v42-original-host-readonly-bridge-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("number")) is not int
                    or request["number"] != 1782
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "6006942116330ffc579784c88b1610d19b3f73cc^{tree}") !=
                        "1783004aec8c720ad28c47a68175264bad394d8c"
                    or git("rev-parse",
                           "6006942116330ffc579784c88b1610d19b3f73cc:" + workflow) !=
                           "b0dfd96bb86cdb834dd908a7518027d12cc9ad95"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                           "145456e37b097aafd42a3f190e538b71543115a1"):
                raise ValueError("G145_V42_ORIGINAL_READONLY_PR1782_PROOF_DENIED")
        if branch == "engineering/f139-v40-stage-path-instance-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (type(request.get("number")) is not int
                    or request["number"] != 1779
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "c5d2e94581565ff8e1b66d498d0b9a167e548454^{tree}") != "2329c68909523058669f52ddeed82ff4f8b4f4a5"
                    or git("rev-parse",
                           "c5d2e94581565ff8e1b66d498d0b9a167e548454:f139/nci04_v41_hybrid_event1833_owner.py") !=
                           "b6b394d600aebd1f878720841827e902b0277b7c"):
                raise ValueError("G145_V40_PR1779_BASE_AND_OWNER_BINDING_REQUIRED")
        if branch == "engineering/f139-v39-event1832-postwrite-canonical-readback-20261115":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-v39-original-source-successor.yml"
            if (type(request.get("number")) is not int
                    or request["number"] != 1777
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse",
                           "1479f963160001037566e4cef33582c5293fb773^{tree}") !=
                           "7f8a752a2244e00a7617dd113317ff365191b54d"
                    or git("rev-parse",
                           "1479f963160001037566e4cef33582c5293fb773:" + workflow) !=
                           "4954c55309f40637954ea9a3cdff8e2d7b08965f"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                           "7d5bbe468e7da2c23edec419bec5cf18294a6f39"):
                raise ValueError("G145_V40_ORIGINAL_OWNER_EXACT_PR1777_TREE_REQUIRED")
        if branch == "engineering/f139-v39-concurrency-isolation-v2-20261115":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (type(request.get("number")) is not int
                    or request["number"] != 1776
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "f9681850ec008b5d872de960544c46e6f5c7943b^{tree}") !=
                        "255b166ad2fc1e6febfde1077fd4e27cdcc7b603"):
                raise ValueError("G145_V39_V2_OWNER_BASE_TREE_REQUIRED")
        if branch == "engineering/f139-v39-postmerge-isolation-correction-20261115":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (type(request.get("number")) is not int
                    or request["number"] != 1775
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "f5507425859bee2f791efd6b0f82b090fddfe416^{tree}") !=
                        "af99f4dc9acc4031f25404f33d47129dabf47836"):
                raise ValueError("G145_V39_POSTMERGE_OWNER_BASE_TREE_REQUIRED")
        if branch == "engineering/f139-v38-event1831-activation-bridge-20261115":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (type(request.get("number")) is not int
                    or request["number"] != 1774
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", "eae38f6d0af27c41181da10c35685c6a3e8c68b4^{tree}") !=
                        "eb5dcc4e7aed43fc6f792fdf6bf8a54802206974"):
                raise ValueError("G145_V39_EXACT_PR1774_OWNER_BASE_TREE_REQUIRED")
        if branch == HYBRID_OWNER_WORKFLOW_BRANCH:
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (type(request.get("number")) is not int
                    or request["number"] != HYBRID_OWNER_WORKFLOW_PR
                    or request.get("user",{}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or git("rev-parse", HYBRID_OWNER_WORKFLOW_BASE + "^{tree}")
                           != HYBRID_OWNER_WORKFLOW_BASE_TREE
                    or git("rev-parse", HYBRID_OWNER_WORKFLOW_BASE + ":"
                           + HYBRID_OWNER_WORKFLOW) != HYBRID_OWNER_WORKFLOW_BEFORE
                    or git("rev-parse", head_sha + ":"
                           + HYBRID_OWNER_WORKFLOW) != HYBRID_OWNER_WORKFLOW_AFTER):
                raise ValueError("G145_HYBRID_OWNER_WORKFLOW_SCOPE_DENIED")
        frozen_base, expected = FROZEN_SCOPES[branch]
        try:
            changed = git(
                "diff", "--no-renames", "--name-only", frozen_base, head_sha
            ).splitlines()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValueError("G145_FROZEN_SCOPE_SOURCE_UNAVAILABLE") from exc
        if base_sha != frozen_base or set(changed) != expected or len(changed) != len(expected):
            raise ValueError("G145_FROZEN_BRANCH_SCOPE_CHANGED")
        return "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"
    # No arbitrary external PR can edit the runner's workflow or source guards.
    # The GitHub event's base must be a locally available exact ancestor of HEAD;
    # this fails closed for stale/unrelated checkouts, requiring a source sync.
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        changed = git(
            "diff", "--no-renames", "--name-only", base_sha, head_sha
        ).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_GENERIC_PR_BASE_SOURCE_UNAVAILABLE") from exc
    if ancestor != base_sha or not generic_paths_safe(changed):
        raise ValueError("G145_GENERIC_PR_CHANGED_OR_UNRELATED_HARNESS")
    return "EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR"

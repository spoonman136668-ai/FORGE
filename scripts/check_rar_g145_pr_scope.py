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
# Exactly one owner-authored V54 release-source PR, never a generic CI bypass.
V54_RELEASE_PR = 1807
V54_RELEASE_BASE = "2d6ca3ea8852f6c70ee0981da3f222d0b982c279"
V54_RELEASE_BASE_TREE = "b9f2b3ce315545bda38f3920d4e6c03e43094e48"
V54_RELEASE_GUARD_BEFORE = "9f88107db9788eb9dd21f5921d97393ce80fa761"
V54_RELEASE_BRANCH = "research/f139-v54-original-owner-readonly-preflight-20261117"
V54_RELEASE_GUARD = "scripts/check_rar_g145_pr_scope.py"
V54_RELEASE_PINNED = {
    ".github/workflows/f139-v54-original-owner-release.yml": "1efeae45523a6e9f75120fba6cdcac8692455652",
    "f139/local_controller.py": "cc06b6c2eea143498a30ea9478b9a8af1ffa7cf8",
    "f139/nci04_genenv_owner_backend.py": "ea4574f04e13ee711765ed86ef5274253636f7de",
    "f139/nci04_model_free_failure.py": "ef09d3dfa4b2c1aebb5839024b0f358955cbe290",
    "f139/nci04_model_owner_bridge.py": "cf5f7fcb6f661d9f0ad6b9ab9f1d44d544d57fde",
    "f139/nci04_owner_ledger.py": "cc4e89408f3fbbc1df2d57ef261ea930268d16c0",
    "f139/nci04_v54_detached_activation.py": "e66c3f239f334f09e571ef69f3216525b6f7ea15",
    "f139/nci04_v54_forward_transition.py": "418dfd7df785200449d068627db67d517e110441",
    "f139/nci04_v54_original_owner_readonly_preflight.py": "98d853bdd27e26ed38708c1237229cf9f429d3cc",
    "f139/nci04_v54_owner_release_cli.py": "54d7f0620397b62fb8cbd8aa71a47727ae1c2e3d",
    "f139/nci04_v54_owner_release.py": "0831ef9cd74dc01ef0070ca8f1bf7533bffdf4f0",
    "f139/test_nci04_genenv_owner_backend.py": "cc8c41918a454778ef69a4e34efe502ae2c1e545",
    "f139/test_nci04_model_free_failure.py": "89fb00e8adf325286785531dfab971fe753c483a",
    "f139/test_nci04_model_owner_bridge.py": "c796f4069c938f13603cb2b197dbb31286f117ca",
    "f139/test_nci04_v50_original_native_activation.py": "d059cc4286bae7c0372e1fe3aa848254a4d53eec",
    "f139/test_nci04_v54_detached_activation.py": "8fe09532e321dc06a13d4a54fa65596265014bab",
    "f139/test_nci04_v54_forward_transition.py": "e47e4f58e431f4576df39b08ce25e2bb1b38bc90",
    "f139/test_nci04_v54_original_owner_readonly_preflight.py": "756369492d08cf1d2d86d0b312ed185356bba34c",
    "f139/test_nci04_v54_owner_release.py": "0c066c2a6d96e82bbed084950b5a9662868f12b3",
    "f139/v54_original_owner_repair.ps1": "e8b68984255cc4e8f2be669c52c6e8552f863732",
    "scripts/check_rar_g148_go_cache.py": "5b2311417e12faba7acf6f776ee9707e59b8bb6b",
    "scripts/check_rar_g156_dynamic_base_cache.py": "7442c1b4bdb0311f09bcfbbfef990b03e5f2be67",
}

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

V59_READONLY_BRANCH = "engineering/f139-v59-original-cold-readonly-once-20261119"
V59_READONLY_BASE = "d620479254755e3fe375ecb293b38f97a6bebdba"
V59_READONLY_BASE_TREE = "4ac7e84573d9b4c9eb3ddbd811c52dd730f3db18"
V59_READONLY_WORKFLOW = ".github/workflows/f139-v59-original-owner-readonly.yml"
V59_READONLY_WORKFLOW_BLOB = "33d616f53bdc4cbe1a26f42f8e8f456907a7d625"
V59_READONLY_PATHS = frozenset((
    V59_READONLY_WORKFLOW,
    "f139/test_v59_original_owner_readonly_scope.py",
    "docs/F139-V59-ORIGINAL-OWNER-READONLY.md",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))

# V60: one owner-authored, exact-PR, read-only original Windows process
# census. The generic workflow/harness-edit ban remains unchanged. This is
# an engineering CI admission only, NOT live original-owner release authority.
V60_PROCESS_BRANCH = "engineering/f139-v60-owner-process-census-exact-20261120"
V60_PROCESS_PR = 1840
V60_PROCESS_BASE = "56feee68a02add2a6cc75529496d1ab3d9643225"
V60_PROCESS_BASE_TREE = "613e580a6bdb5a9ad1dcaab57e9f20690f79d31d"
V60_PROCESS_WORKFLOW = ".github/workflows/f139-v59-original-owner-readonly.yml"
V60_PROCESS_WORKFLOW_BEFORE = "33d616f53bdc4cbe1a26f42f8e8f456907a7d625"
V60_PROCESS_WORKFLOW_AFTER = "d50d606e70b985e7245141724097bd4a4aeb82d6"
V60_PROCESS_PATHS = frozenset((
    V60_PROCESS_WORKFLOW,
    "f139/test_nci04_v59_original_process_snapshot.py",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))

# V61: fix the PowerShell parser after genuine original-owner run
# #44724846172. This is exactly scoped to PR1842, old/new workflow blobs,
# protected main base and three existing CI guards; no live release authority.
V61_PROCESS_FIX_BRANCH = "engineering/f139-v61-owner-process-pwsh-parser-fix-20261120"
V61_PROCESS_FIX_PR = 1842
V61_PROCESS_FIX_BASE = "beac5f835c63937e22810700a209e695ead00589"
V61_PROCESS_FIX_BASE_TREE = "469dd4cac83e9b8a8ac62d5cab7351b192bd73ba"
V61_PROCESS_FIX_WORKFLOW = ".github/workflows/f139-v59-original-owner-readonly.yml"
V61_PROCESS_FIX_BEFORE = "d50d606e70b985e7245141724097bd4a4aeb82d6"
V61_PROCESS_FIX_AFTER = "82c00a16e1f3744cfb6483ed668654a072278688"
V61_PROCESS_FIX_PATHS = frozenset((
    V61_PROCESS_FIX_WORKFLOW,
    "f139/test_nci04_v59_original_process_snapshot.py",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))

FROZEN_SCOPES = {
    V61_PROCESS_FIX_BRANCH: (V61_PROCESS_FIX_BASE, V61_PROCESS_FIX_PATHS),
    V60_PROCESS_BRANCH: (V60_PROCESS_BASE, V60_PROCESS_PATHS),
    V59_READONLY_BRANCH: (V59_READONLY_BASE, V59_READONLY_PATHS),
    # V58: one owner-authored, exact-base read-only status projection.
    # No workflow triggers, original task, admission, SQLite or science changed.
    "engineering/f139-v58-model-free-status-readonly-20261119": (
        "c06403c8b6035c6c7013866a7ea08cef1244b507",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/test_nci04_v58_model_free_status_projection.py",
            "f139/test_v40_readonly_workflow_scope.py",
            "docs/F139-V58-MODEL-FREE-STATUS-READONLY.md",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # PR #1804: restore exact original owner after proved V53 precommit
    # failure, and fix the stale V50 guard without altering old schemas.
    "engineering/f139-v53-precommit-original-owner-restore-20261117": (
        "918a7a10a3f47e30b2ecd6d3d443ff16428b9c0b",
        {
            ".github/workflows/f139-v53-precommit-owner-restore.yml",
            "docs/F139-V53-PRECOMMIT-ORIGINAL-OWNER-RESTORE.md",
            "f139/nci04_v53_owner_forward_repair_cli.py",
            "f139/test_nci04_v53_owner_forward_repair.py",
            "f139/v53_precommit_owner_restore.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # PR #1803: exact 8-file one-shot owner assignment recovery;
    # CI admission does not permit owner/SQLite mutation or science.
    "engineering/f139-v53-owner-assignment-recovery-20261117": (
        "09d0f6639d1e9bc54e0c909ccd9fb7bfaaea87f8",
        {
            ".github/workflows/f139-v53-original-owner-source-repair.yml",
            "docs/F139-V53-OWNER-ASSIGNMENT-RECOVERY.md",
            "f139/v53_original_owner_repair.ps1",
            "f139/nci04_v53_owner_forward_repair_cli.py",
            "f139/test_nci04_v53_owner_forward_repair.py",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # PR #1802: one owner-authenticated workflow_dispatch successor; no
    # generic workflow/runner permission bypass or science authorization.
    "engineering/f139-v53-original-owner-dispatch-20261117": (
        "a63ea00a9046bf107b59d64b3557ebd78c8f4157",
        {
            ".github/workflows/f139-v53-original-owner-source-repair.yml",
            "docs/F139-V53-ONE-CLICK-OWNER-ROUTE.md",
            "f139/nci04_v53_owner_forward_repair.py",
            "f139/nci04_v53_owner_forward_repair_cli.py",
            "f139/test_nci04_v53_owner_forward_repair.py",
            "f139/v53_original_owner_repair.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Exact PR1793: original-owner DEV-only source activation. CI admission only.
    # Live owner, SQLite write, merge and scientific first-use remain separate.
    "engineering/f139-v50-v41-original-native-activation-20261116": (
        "2567775a9c06b306142812cc8c0e252278f87273",
        {
            ".github/workflows/f139-g54-v9-owner-cutover.yml",
            "f139/nci04_owner_ledger.py",
            "f139/nci04_v50_original_native_activation.py",
            "f139/test_nci04_v50_original_native_activation.py",
            "f139/v50_original_owner_native_activate.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # Source-only V48 recovery of ORIGINAL held event1835 task after failed
    # authenticated V47; read-only host receipt and separate owner release.
    "engineering/f139-v48-held-original-owner-safe-recovery-20261116": (
        "ce5d4e06d9466735030568f4e5576adca78d804f",
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
    # Original-owner precommit recovery after V46 one-shot created exactly one
    # immutable release ref; no re-PUSH, no new schedule/controller or science.
    "engineering/f139-v47-existing-ref-original-owner-recovery-20261116": (
        "ba6419cfa75879d23e8ae24c2bb8749d08e2b6d5",
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
    # PR #1797: exact original-owner source-only forward repair; CI scope only.
    "engineering/f139-v52-original-owner-forward-repair-20261116": (
        "d4e588f0fbd8486e1d34754ddcf0f540c2895590",
        {
            ".github/workflows/f139-v52-original-owner-source-repair.yml",
            "f139/local_controller.py",
            "f139/nci04_owner_ledger.py",
            "f139/nci04_v52_owner_forward_repair.py",
            "f139/nci04_v52_owner_forward_repair_cli.py",
            "f139/test_nci04_v50_original_native_activation.py",
            "f139/test_nci04_v52_owner_forward_repair.py",
            "f139/v52_original_owner_repair.ps1",
            "scripts/check_rar_g145_pr_scope.py",
            "scripts/check_rar_g148_go_cache.py",
            "scripts/check_rar_g156_dynamic_base_cache.py",
        },
    ),
    # PR #1796: one exact original-owner read-only V51 witness route.
    # Does not authorize runtime mutation, scientific first-use, or a release.
    "engineering/f139-v51-original-owner-preflight-20261116": (
        "e657a0b3f85120b72fcf3e191a0b1c1c289c97cb",
        {
            ".github/workflows/f139-v51-original-owner-readonly.yml",
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


# Single owner-authored workflow addition. CI admission only: never a
# Windows controller, live ticket, first-use, dispatch or acceptance grant.
FRESH_OWNER_ADMIT_BRANCH = "engineering/f139-fresh-original-owner-admission-20261120"
FRESH_OWNER_ADMIT_PR = 1845
FRESH_OWNER_ADMIT_BASE = "cd5e9a783f574577bb468b6d46b19abd8f40e666"
FRESH_OWNER_ADMIT_TREE = "74084114dd1ce166be4ac7ae012d728d239c382c"
FRESH_OWNER_ADMIT_WORKFLOW = ".github/workflows/f139-fresh-original-owner-admission.yml"
FRESH_OWNER_ADMIT_BLOB = "46bbf3ae4f9150c684cda138826c8ea8e88021a1"
FRESH_OWNER_ADMIT_FILES = frozenset({
    FRESH_OWNER_ADMIT_WORKFLOW,
    "f139/nci04_fresh_original_owner_admission_cli.py",
    "f139/test_nci04_fresh_original_owner_admission_cli.py",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})


def admit_fresh_owner_admission(head_sha: str, base_sha: str, request: dict,
                                git: Callable[..., str]) -> str:
    """Exact-branch owner-only CI exception, not a generic workflow waiver."""
    if (not is_sha(head_sha)
            or base_sha != FRESH_OWNER_ADMIT_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_OWNER_ADMIT_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_OWNER_ADMIT_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_OWNER_ADMIT_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_OWNER_EXACT_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        base_tree = git("rev-parse", base_sha + "^{tree}")
        actual_blob = git("rev-parse", head_sha + ":" + FRESH_OWNER_ADMIT_WORKFLOW)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_OWNER_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or base_tree != FRESH_OWNER_ADMIT_TREE
            or actual_blob != FRESH_OWNER_ADMIT_BLOB
            or len(changed) != len(FRESH_OWNER_ADMIT_FILES)
            or set(changed) != FRESH_OWNER_ADMIT_FILES):
        raise ValueError("G145_FRESH_OWNER_FROZEN_SCOPE_DENIED")
    return "EXACT_PR1845_F139_FRESH_OWNER_ADMISSION_CI_ONLY"


# Exact owner-authored PR #1846 changes ONLY the already-merged fresh
# admission job's concurrency scope. CI only; never an owner/process grant.
FRESH_CONCURRENCY_BRANCH = "engineering/f139-fresh-admission-job-concurrency-20261120"
FRESH_CONCURRENCY_PR = 1846
FRESH_CONCURRENCY_BASE = "30e9b49138e7e0bf359d34da91450ee9f228b2bf"
FRESH_CONCURRENCY_TREE = "ded71db9d6a416c846500cf1394ae5b279b3d36a"
FRESH_CONCURRENCY_WORKFLOW = ".github/workflows/f139-fresh-original-owner-admission.yml"
FRESH_CONCURRENCY_BLOB = "e5d2c7ac03f5281c60642db6701bb4a7893e8a63"
FRESH_CONCURRENCY_FILES = frozenset({
    FRESH_CONCURRENCY_WORKFLOW,
    "f139/test_nci04_fresh_admission_job_concurrency.py",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})


def admit_fresh_admission_job_concurrency(head_sha: str, base_sha: str,
                                          request: dict,
                                          git: Callable[..., str]) -> str:
    """No generic workflow waiver. One exact owner PR and complete file set."""
    if (not is_sha(head_sha)
            or base_sha != FRESH_CONCURRENCY_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_CONCURRENCY_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_CONCURRENCY_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_CONCURRENCY_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_CONCURRENCY_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        base_tree = git("rev-parse", base_sha + "^{tree}")
        actual_blob = git("rev-parse", head_sha + ":" + FRESH_CONCURRENCY_WORKFLOW)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_CONCURRENCY_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or base_tree != FRESH_CONCURRENCY_TREE
            or actual_blob != FRESH_CONCURRENCY_BLOB
            or len(changed) != len(FRESH_CONCURRENCY_FILES)
            or set(changed) != FRESH_CONCURRENCY_FILES):
        raise ValueError("G145_FRESH_CONCURRENCY_EXACT_SCOPE_DENIED")
    return "EXACT_PR1846_FRESH_ADMISSION_JOB_CONCURRENCY_CI_ONLY"


# Exact owner-authored PR #1847 wires existing, separately qualified fresh
# activation after the old Windows task is independently DISABLED.
# This only qualifies CI/source; not host task release or scientific first use.
FRESH_ACTIVATION_BRANCH = "engineering/f139-fresh-native-owner-activation-entry-20261120"
FRESH_ACTIVATION_PR = 1847
FRESH_ACTIVATION_BASE = "4744d0c7a37a600f9451c20ed717cd5623cbc0d6"
FRESH_ACTIVATION_TREE = "c2118fd05602fe92907d43ae2c92d581f5b10d01"
FRESH_ACTIVATION_WORKFLOW = ".github/workflows/f139-fresh-original-owner-activation.yml"
FRESH_ACTIVATION_BLOB = "b1eb94037716aa8084c02affe66da33288e3680c"
FRESH_ACTIVATION_NATIVE_WORKFLOW = ".github/workflows/forge-f139-source-qualification.yml"
FRESH_ACTIVATION_NATIVE_BLOB = "1d831004eed4df6227517d941ab561d2e2f59010"
FRESH_ACTIVATION_G137 = "scripts/check_rar_g137_f139_shards.py"
FRESH_ACTIVATION_G137_BLOB = "ee04c866aaa4522e9c490014b252f2953940dc2e"
FRESH_ACTIVATION_CRYPTO_TEST = "f139/test_rsi_r12j_owner_signature.py"
FRESH_ACTIVATION_CRYPTO_BLOB = "5ed53c5a81452b871f36662d0b49412c5e3e178d"
FRESH_ACTIVATION_FILES = frozenset({
    FRESH_ACTIVATION_WORKFLOW,
    FRESH_ACTIVATION_NATIVE_WORKFLOW,
    FRESH_ACTIVATION_G137,
    FRESH_ACTIVATION_CRYPTO_TEST,
    "f139/nci04_fresh_owner_activation_cli.py",
    "f139/test_nci04_fresh_owner_activation_cli.py",
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
})


def admit_fresh_owner_activation_bridge(head_sha: str, base_sha: str,
                                        request: dict,
                                        git: Callable[..., str]) -> str:
    """Exactly PR1847 owner provenance, protected ancestor, blob and nine paths."""
    if (not is_sha(head_sha) or base_sha != FRESH_ACTIVATION_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_ACTIVATION_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_ACTIVATION_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_ACTIVATION_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_ACTIVATION_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        base_tree = git("rev-parse", base_sha + "^{tree}")
        actual_blob = git("rev-parse", head_sha + ":" + FRESH_ACTIVATION_WORKFLOW)
        native_blob = git("rev-parse", head_sha + ":" + FRESH_ACTIVATION_NATIVE_WORKFLOW)
        g137_blob = git("rev-parse", head_sha + ":" + FRESH_ACTIVATION_G137)
        crypto_blob = git("rev-parse", head_sha + ":" + FRESH_ACTIVATION_CRYPTO_TEST)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_ACTIVATION_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or base_tree != FRESH_ACTIVATION_TREE
            or actual_blob != FRESH_ACTIVATION_BLOB
            or native_blob != FRESH_ACTIVATION_NATIVE_BLOB
            or g137_blob != FRESH_ACTIVATION_G137_BLOB
            or crypto_blob != FRESH_ACTIVATION_CRYPTO_BLOB
            or len(changed) != len(FRESH_ACTIVATION_FILES)
            or set(changed) != FRESH_ACTIVATION_FILES):
        raise ValueError("G145_FRESH_ACTIVATION_EXACT_SCOPE_DENIED")
    return "EXACT_PR1847_FRESH_NATIVE_OWNER_ACTIVATION_CI_ONLY"


# One original-owner-scoped standdown candidate. Engineering CI ONLY;
# never grants a live Windows stop, release, restart or scientific first-use.
FRESH_STANDDOWN_BRANCH = "engineering/f139-fresh-owner-standdown-20261120"
FRESH_STANDDOWN_PR = 1848
FRESH_STANDDOWN_BASE = "0727068e534c18ce73cf2de173f9b2a231556ff7"
FRESH_STANDDOWN_TREE = "e89a8ad7c5e16d9db385403910c50d691475d8d5"
FRESH_STANDDOWN_WORKFLOW = ".github/workflows/f139-fresh-original-owner-standdown.yml"
FRESH_STANDDOWN_SCRIPT = "f139/nci04_fresh_owner_standdown.ps1"
FRESH_STANDDOWN_TEST = "f139/test_nci04_fresh_owner_standdown_source.py"
FRESH_STANDDOWN_BLOBS = {
    FRESH_STANDDOWN_WORKFLOW: "13ee12816e0b0e4a94604a2e53c5072485de39ed",
    FRESH_STANDDOWN_SCRIPT: "0702b728e18cccdb6f5bf74d16845f09f1090035",
}
FRESH_STANDDOWN_FILES = frozenset((
    *FRESH_STANDDOWN_BLOBS, FRESH_STANDDOWN_TEST,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_original_standdown(head_sha: str, base_sha: str,
                                  request: dict, git: Callable[..., str]) -> str:
    """Exact owner/main/source admission; never a task-control permission."""
    if (not is_sha(head_sha) or base_sha != FRESH_STANDDOWN_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_STANDDOWN_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_STANDDOWN_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_STANDDOWN_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_STANDDOWN_OWNER_SOURCE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        parent_tree = git("rev-parse", base_sha + "^{tree}")
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        blobs = {p: git("rev-parse", head_sha + ":" + p)
                 for p in FRESH_STANDDOWN_BLOBS}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_STANDDOWN_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or parent_tree != FRESH_STANDDOWN_TREE
            or len(changed) != len(FRESH_STANDDOWN_FILES)
            or set(changed) != FRESH_STANDDOWN_FILES
            or blobs != FRESH_STANDDOWN_BLOBS):
        raise ValueError("G145_FRESH_STANDDOWN_SOURCE_OR_BLOB_DRIFT")
    return "EXACT_PR1848_F139_STANDDOWN_SOURCE_CI_ONLY"



# One exact original-owner single-task rebind candidate, source CI only.
# This does not approve or execute a host task change, worker or science.
FRESH_REBIND_BRANCH = "engineering/f139-fresh-original-task-rebind-20261120"
FRESH_REBIND_PR = 1851
FRESH_REBIND_BASE = "e8aebb5347f693c11c57092fe05406937dab80d0"
FRESH_REBIND_TREE = "4ea1b37fdda87f28d49f5d8f895cf57de4a802e6"
FRESH_REBIND_WORKFLOW = ".github/workflows/f139-fresh-original-owner-rebind.yml"
FRESH_REBIND_SCRIPT = "f139/nci04_fresh_owner_rebind.ps1"
FRESH_REBIND_TEST = "f139/test_nci04_fresh_owner_rebind_source.py"
FRESH_REBIND_BLOBS = {
    FRESH_REBIND_WORKFLOW: "e90e12d2eae3aabb774a7ae568df42d0b3d0beb3",
    FRESH_REBIND_SCRIPT: "468c73f9b80a23ac44297650d5f39cf4fae135d8",
}
FRESH_REBIND_FILES = frozenset((
    *FRESH_REBIND_BLOBS, FRESH_REBIND_TEST,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_original_rebind(head_sha: str, base_sha: str,
                                request: dict, git: Callable[..., str]) -> str:
    """Exact source/owner/PR admissibility for CI, not execution authority."""
    if (not is_sha(head_sha) or base_sha != FRESH_REBIND_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_REBIND_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_REBIND_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_REBIND_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_REBIND_OWNER_MAIN_SOURCE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        parent_tree = git("rev-parse", base_sha + "^{tree}")
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        blobs = {path: git("rev-parse", head_sha + ":" + path)
                 for path in FRESH_REBIND_BLOBS}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_REBIND_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or parent_tree != FRESH_REBIND_TREE
            or len(changed) != len(FRESH_REBIND_FILES)
            or set(changed) != FRESH_REBIND_FILES
            or blobs != FRESH_REBIND_BLOBS):
        raise ValueError("G145_FRESH_REBIND_SOURCE_OR_BLOB_DRIFT")
    return "EXACT_PR1851_F139_FRESH_DISABLED_TASK_REBIND_CI_ONLY"



# Exact Windows runner shell correction. Hosted jobs have pwsh; original
# Windows owner presently does not. CI source admission is not owner release.
FRESH_SHELL_BRANCH = "engineering/f139-fresh-rebind-windows-shell-20261120"
FRESH_SHELL_PR = 1852
FRESH_SHELL_BASE = "e23b39a558b84b230f6bf9d9e37d2ade7aaf3b3a"
FRESH_SHELL_TREE = "ef73d60881b6aed69e825d3b2aade89a26aa4909"
FRESH_SHELL_WORKFLOW = ".github/workflows/f139-fresh-original-owner-rebind.yml"
FRESH_SHELL_TEST = "f139/test_nci04_fresh_owner_rebind_source.py"
FRESH_SHELL_BLOBS = {
    FRESH_SHELL_WORKFLOW: "6f6944fefe2b589d0ea9e459e38af24c54c249a3",
}
FRESH_SHELL_FILES = frozenset((
    *FRESH_SHELL_BLOBS, FRESH_SHELL_TEST,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_owner_shell_fix(head_sha: str, base_sha: str,
                                request: dict, git: Callable[..., str]) -> str:
    """Admit exactly one native owner shell fix for CI; no live task authority."""
    if (not is_sha(head_sha) or base_sha != FRESH_SHELL_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_SHELL_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_SHELL_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_SHELL_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_SHELL_OWNER_MAIN_SOURCE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        parent_tree = git("rev-parse", base_sha + "^{tree}")
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        blobs = {path: git("rev-parse", head_sha + ":" + path)
                 for path in FRESH_SHELL_BLOBS}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_SHELL_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or parent_tree != FRESH_SHELL_TREE
            or len(changed) != len(FRESH_SHELL_FILES)
            or set(changed) != FRESH_SHELL_FILES
            or blobs != FRESH_SHELL_BLOBS):
        raise ValueError("G145_FRESH_SHELL_SOURCE_OR_BLOB_DRIFT")
    return "EXACT_PR1852_F139_NATIVE_POWERSHELL_HOST_FIX_CI_ONLY"



# Exact correction for owner run #44844005419, cancelled before any step
# by pending-slot replacement from unrelated legacy issue-comment workflows.
# Single-source CI ONLY; not a new scheduler, owner or task permission.
FRESH_REBIND_CANCEL_BRANCH = "engineering/f139-fresh-rebind-concurrency-20261120"
FRESH_REBIND_CANCEL_PR = 1853
FRESH_REBIND_CANCEL_BASE = "6f46998de6c5a5046d9364cfc39504b29a762680"
FRESH_REBIND_CANCEL_TREE = "3378894810c36e68ad72c6089905641dae2de879"
FRESH_REBIND_CANCEL_WORKFLOW = ".github/workflows/f139-fresh-original-owner-rebind.yml"
FRESH_REBIND_CANCEL_TEST = "f139/test_nci04_fresh_owner_rebind_source.py"
FRESH_REBIND_CANCEL_BLOBS = {
    FRESH_REBIND_CANCEL_WORKFLOW: "d1d65d0515b65af54f7791efee600e3d7c4c260c",
}
FRESH_REBIND_CANCEL_FILES = frozenset((
    *FRESH_REBIND_CANCEL_BLOBS, FRESH_REBIND_CANCEL_TEST,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_rebind_pending_collision_fix(head_sha: str, base_sha: str,
                                              request: dict, git: Callable[..., str]) -> str:
    """No broad workflow exception; only this exact cancelled-run correction."""
    if (not is_sha(head_sha) or base_sha != FRESH_REBIND_CANCEL_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_REBIND_CANCEL_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_REBIND_CANCEL_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_REBIND_CANCEL_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_REBIND_CANCEL_OWNER_SOURCE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        parent_tree = git("rev-parse", base_sha + "^{tree}")
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        blobs = {path: git("rev-parse", head_sha + ":" + path)
                 for path in FRESH_REBIND_CANCEL_BLOBS}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_REBIND_CANCEL_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or parent_tree != FRESH_REBIND_CANCEL_TREE
            or len(changed) != len(FRESH_REBIND_CANCEL_FILES)
            or set(changed) != FRESH_REBIND_CANCEL_FILES
            or blobs != FRESH_REBIND_CANCEL_BLOBS):
        raise ValueError("G145_FRESH_REBIND_CANCEL_SOURCE_OR_BLOB_DRIFT")
    return "EXACT_PR1853_F139_FRESH_OWNER_PENDING_CANCEL_FIX_CI_ONLY"



# Exact Windows PowerShell execution-policy refusal on original owner run
# #44848840279. Source CI only; neither task nor runner-wide policy authority.
FRESH_POLICY_BRANCH = "engineering/f139-fresh-rebind-executionpolicy-process-20261120"
FRESH_POLICY_PR = 1854
FRESH_POLICY_BASE = "5186697bde5d45f7ae695c57e914a211a1d3a3b3"
FRESH_POLICY_TREE = "6622b0bac3f0e53b9e93dba795198f7c72cceccf"
FRESH_POLICY_WORKFLOW = ".github/workflows/f139-fresh-original-owner-rebind.yml"
FRESH_POLICY_SCRIPT = "f139/nci04_fresh_owner_rebind.ps1"
FRESH_POLICY_TEST = "f139/test_nci04_fresh_owner_rebind_source.py"
FRESH_POLICY_BLOBS = {
    FRESH_POLICY_WORKFLOW: "82443bd4dfd55a15f5ea12328afedafc515a0b99",
    FRESH_POLICY_SCRIPT: "e7cbfa1373c5517a936060ef8fe62c6bfe917b7f",
}
FRESH_POLICY_FILES = frozenset((
    *FRESH_POLICY_BLOBS, FRESH_POLICY_TEST,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_owner_process_policy_fix(head_sha: str, base_sha: str,
                                         request: dict, git: Callable[..., str]) -> str:
    """Admit solely the failed original-owner process policy launcher correction."""
    if (not is_sha(head_sha) or base_sha != FRESH_POLICY_BASE
            or type(request) is not dict
            or request.get("number") != FRESH_POLICY_PR
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("ref") != FRESH_POLICY_BRANCH
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != FRESH_POLICY_BASE
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_POLICY_OWNER_MAIN_SOURCE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        parent_tree = git("rev-parse", base_sha + "^{tree}")
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        blobs = {path: git("rev-parse", head_sha + ":" + path)
                 for path in FRESH_POLICY_BLOBS}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_POLICY_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or parent_tree != FRESH_POLICY_TREE
            or len(changed) != len(FRESH_POLICY_FILES)
            or set(changed) != FRESH_POLICY_FILES
            or blobs != FRESH_POLICY_BLOBS):
        raise ValueError("G145_FRESH_POLICY_SOURCE_OR_BLOB_DRIFT")
    return "EXACT_PR1854_F139_FRESH_OWNER_PROCESS_POLICY_FIX_CI_ONLY"


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



def admit_v60_owner_process_census(
    head_sha: str, base_sha: str, request: dict,
    git: Callable[..., str],
) -> str:
    """Exactly scoped read-only owner-workflow *CI* admission, no host writes.

    The owner-authored PR number, protected base tree, old/new workflow blobs
    and entire diff are frozen. No generic workflow or harness exemption.
    """
    if (
        not is_sha(head_sha)
        or base_sha != V60_PROCESS_BASE
        or type(request) is not dict
        or type(request.get("number")) is not int
        or request["number"] != V60_PROCESS_PR
        or request.get("author_association") != "OWNER"
        or type(request.get("user")) is not dict
        or request["user"].get("login") != "spoonman136668-ai"
        or type(request.get("head")) is not dict
        or request["head"].get("sha") != head_sha
        or request["head"].get("ref") != V60_PROCESS_BRANCH
        or type(request["head"].get("repo")) is not dict
        or request["head"]["repo"].get("full_name") != REPO
        or type(request.get("base")) is not dict
        or request["base"].get("sha") != V60_PROCESS_BASE
        or request["base"].get("ref") != "main"
        or type(request["base"].get("repo")) is not dict
        or request["base"]["repo"].get("full_name") != REPO
    ):
        raise ValueError("G145_V60_EXACT_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        old_tree = git("rev-parse", base_sha + "^{tree}")
        before_blob = git("rev-parse", base_sha + ":" + V60_PROCESS_WORKFLOW)
        after_blob = git("rev-parse", head_sha + ":" + V60_PROCESS_WORKFLOW)
        changed = git(
            "diff", "--no-renames", "--name-only", base_sha, head_sha
        ).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V60_FROZEN_SOURCE_UNAVAILABLE") from exc
    if (
        ancestor != base_sha
        or old_tree != V60_PROCESS_BASE_TREE
        or before_blob != V60_PROCESS_WORKFLOW_BEFORE
        or after_blob != V60_PROCESS_WORKFLOW_AFTER
        or set(changed) != V60_PROCESS_PATHS
        or len(changed) != len(V60_PROCESS_PATHS)
    ):
        raise ValueError("G145_V60_READONLY_SCOPE_OR_SOURCE_CHANGED")
    return "G145_V60_FROZEN_OWNER_READONLY_PROCESS_CENSUS_CI_ONLY"


def v60_process_census_negative_controls() -> None:
    """Prove the narrow exception rejects PR, source and path substitutions."""
    head = "f" * 40
    base = V60_PROCESS_BASE
    request = {
        "number": V60_PROCESS_PR,
        "author_association": "OWNER",
        "user": {"login": "spoonman136668-ai"},
        "head": {
            "sha": head, "ref": V60_PROCESS_BRANCH,
            "repo": {"full_name": REPO},
        },
        "base": {
            "sha": base, "ref": "main",
            "repo": {"full_name": REPO},
        },
    }
    paths = sorted(V60_PROCESS_PATHS)
    expected = {
        ("merge-base", base, head): base,
        ("rev-parse", base + "^{tree}"): V60_PROCESS_BASE_TREE,
        ("rev-parse", base + ":" + V60_PROCESS_WORKFLOW):
            V60_PROCESS_WORKFLOW_BEFORE,
        ("rev-parse", head + ":" + V60_PROCESS_WORKFLOW):
            V60_PROCESS_WORKFLOW_AFTER,
        ("diff", "--no-renames", "--name-only", base, head):
            "\n".join(paths),
    }

    def fake_git(*args: str) -> str:
        if args not in expected:
            raise AssertionError("G145_V60_UNEXPECTED_GIT_ROUTE")
        return expected[args]

    if (admit_v60_owner_process_census(head, base, request, fake_git)
            != "G145_V60_FROZEN_OWNER_READONLY_PROCESS_CENSUS_CI_ONLY"):
        raise ValueError("G145_V60_POSITIVE_NEGATIVE_CONTROL_FAILED")

    invalid_requests = (
        {**request, "number": V60_PROCESS_PR + 1},
        {**request, "author_association": "CONTRIBUTOR"},
        {**request, "user": {"login": "other"}},
        {**request, "head": {**request["head"], "ref": "main"}},
        {**request, "head": {**request["head"], "sha": "a" * 40}},
        {**request, "head": {**request["head"],
                            "repo": {"full_name": "foreign/FORGE"}}},
        {**request, "base": {**request["base"], "ref": "test"}},
        {**request, "base": {**request["base"], "sha": "b" * 40}},
        {**request, "base": {**request["base"],
                            "repo": {"full_name": "foreign/FORGE"}}},
    )
    for bad in invalid_requests:
        try:
            admit_v60_owner_process_census(head, base, bad, fake_git)
        except ValueError:
            continue
        raise ValueError("G145_V60_OWNER_PR_NEGATIVE_CONTROL_FAILED")
    for args, bad_value in (
        (("merge-base", base, head), "0" * 40),
        (("rev-parse", base + "^{tree}"), "1" * 40),
        (("rev-parse", base + ":" + V60_PROCESS_WORKFLOW), "2" * 40),
        (("rev-parse", head + ":" + V60_PROCESS_WORKFLOW), "3" * 40),
        (("diff", "--no-renames", "--name-only", base, head),
         "\n".join(paths + [".github/workflows/foreign.yml"])),
        (("diff", "--no-renames", "--name-only", base, head),
         "\n".join(paths[:-1])),
    ):
        def bad_git(*parts: str) -> str:
            return bad_value if parts == args else fake_git(*parts)

        try:
            admit_v60_owner_process_census(head, base, request, bad_git)
        except ValueError:
            continue
        raise ValueError("G145_V60_SOURCE_NEGATIVE_CONTROL_FAILED")
    if (generic_paths_safe([V60_PROCESS_WORKFLOW])
            or generic_paths_safe(["scripts/check_rar_g145_pr_scope.py"])):
        raise ValueError("G145_V60_GENERIC_SCOPE_BYPASS")


def admit_v61_owner_parser_fix(
    head_sha: str, base_sha: str, request: dict, git: Callable[..., str],
) -> str:
    """Freeze exactly PR1842's Windows read-only syntax repair for CI only."""
    if (
        not is_sha(head_sha)
        or base_sha != V61_PROCESS_FIX_BASE
        or type(request) is not dict
        or type(request.get("number")) is not int
        or request.get("number") != V61_PROCESS_FIX_PR
        or request.get("author_association") != "OWNER"
        or type(request.get("user")) is not dict
        or request["user"].get("login") != "spoonman136668-ai"
        or type(request.get("head")) is not dict
        or request["head"].get("sha") != head_sha
        or request["head"].get("ref") != V61_PROCESS_FIX_BRANCH
        or type(request["head"].get("repo")) is not dict
        or request["head"]["repo"].get("full_name") != REPO
        or type(request.get("base")) is not dict
        or request["base"].get("sha") != V61_PROCESS_FIX_BASE
        or request["base"].get("ref") != "main"
        or type(request["base"].get("repo")) is not dict
        or request["base"]["repo"].get("full_name") != REPO
    ):
        raise ValueError("G145_V61_EXACT_OWNER_PR_REQUIRED")
    try:
        base_ancestor = git("merge-base", base_sha, head_sha)
        base_tree = git("rev-parse", base_sha + "^{tree}")
        original_workflow = git(
            "rev-parse", base_sha + ":" + V61_PROCESS_FIX_WORKFLOW)
        fixed_workflow = git(
            "rev-parse", head_sha + ":" + V61_PROCESS_FIX_WORKFLOW)
        files = git(
            "diff", "--no-renames", "--name-only", base_sha, head_sha
        ).splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V61_FROZEN_SOURCE_UNAVAILABLE") from exc
    if (
        base_ancestor != base_sha
        or base_tree != V61_PROCESS_FIX_BASE_TREE
        or original_workflow != V61_PROCESS_FIX_BEFORE
        or fixed_workflow != V61_PROCESS_FIX_AFTER
        or len(files) != len(V61_PROCESS_FIX_PATHS)
        or set(files) != V61_PROCESS_FIX_PATHS
    ):
        raise ValueError("G145_V61_PARSER_REPAIR_SCOPE_CHANGED")
    return "G145_V61_FROZEN_READONLY_PARSER_REPAIR_CI_ONLY"


def v61_parser_fix_negative_controls() -> None:
    """One valid frozen PR and substitutions that must all fail closed."""
    head = "f" * 40
    base = V61_PROCESS_FIX_BASE
    pr = {
        "number": V61_PROCESS_FIX_PR,
        "author_association": "OWNER",
        "user": {"login": "spoonman136668-ai"},
        "head": {"sha": head, "ref": V61_PROCESS_FIX_BRANCH,
                 "repo": {"full_name": REPO}},
        "base": {"sha": base, "ref": "main",
                 "repo": {"full_name": REPO}},
    }
    files = sorted(V61_PROCESS_FIX_PATHS)
    routes = {
        ("merge-base", base, head): base,
        ("rev-parse", base + "^{tree}"): V61_PROCESS_FIX_BASE_TREE,
        ("rev-parse", base + ":" + V61_PROCESS_FIX_WORKFLOW):
            V61_PROCESS_FIX_BEFORE,
        ("rev-parse", head + ":" + V61_PROCESS_FIX_WORKFLOW):
            V61_PROCESS_FIX_AFTER,
        ("diff", "--no-renames", "--name-only", base, head):
            "\n".join(files),
    }
    def exact_git(*args: str) -> str:
        if args not in routes:
            raise AssertionError("G145_V61_UNEXPECTED_GIT_ROUTE")
        return routes[args]

    if (admit_v61_owner_parser_fix(head, base, pr, exact_git)
            != "G145_V61_FROZEN_READONLY_PARSER_REPAIR_CI_ONLY"):
        raise ValueError("G145_V61_POSITIVE_CONTROL_FAILED")

    invalid = (
        {**pr, "number": V61_PROCESS_FIX_PR + 1},
        {**pr, "author_association": "CONTRIBUTOR"},
        {**pr, "user": {"login": "other"}},
        {**pr, "head": {**pr["head"], "sha": "a" * 40}},
        {**pr, "head": {**pr["head"], "ref": "other"}},
        {**pr, "head": {**pr["head"],
                       "repo": {"full_name": "foreign/FORGE"}}},
        {**pr, "base": {**pr["base"], "sha": "b" * 40}},
        {**pr, "base": {**pr["base"], "ref": "other"}},
        {**pr, "base": {**pr["base"],
                       "repo": {"full_name": "foreign/FORGE"}}},
    )
    for bad in invalid:
        try:
            admit_v61_owner_parser_fix(head, base, bad, exact_git)
        except ValueError:
            continue
        raise ValueError("G145_V61_PR_NEGATIVE_CONTROL_FAILED")

    for args, substitute in (
        (("merge-base", base, head), "0" * 40),
        (("rev-parse", base + "^{tree}"), "1" * 40),
        (("rev-parse", base + ":" + V61_PROCESS_FIX_WORKFLOW), "2" * 40),
        (("rev-parse", head + ":" + V61_PROCESS_FIX_WORKFLOW), "3" * 40),
        (("diff", "--no-renames", "--name-only", base, head),
         "\n".join(files + [".github/workflows/other.yml"])),
        (("diff", "--no-renames", "--name-only", base, head),
         "\n".join(files[:-1])),
    ):
        def altered_git(*parts: str) -> str:
            return substitute if parts == args else exact_git(*parts)
        try:
            admit_v61_owner_parser_fix(head, base, pr, altered_git)
        except ValueError:
            continue
        raise ValueError("G145_V61_SOURCE_NEGATIVE_CONTROL_FAILED")

    if generic_paths_safe([V61_PROCESS_FIX_WORKFLOW]):
        raise ValueError("G145_V61_GENERIC_WORKFLOW_BYPASS")


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
    v54_owner_release_negative_controls()
    v60_process_census_negative_controls()
    v61_parser_fix_negative_controls()
    if generic_paths_safe([V59_READONLY_WORKFLOW]):
        raise ValueError('G145_V59_WORKFLOW_GENERIC_SCOPE_BYPASS')


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


def admit_v54_owner_release(head_sha, base_sha, request, git):
    """Source-only CI exception for exactly PR1807's pinned Windows workflow."""
    if (type(request) is not dict or type(request.get("number")) is not int
            or request["number"] != V54_RELEASE_PR
            or request.get("state") != "open"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("author_association") != "OWNER"
            or request.get("head", {}).get("ref") != V54_RELEASE_BRANCH
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("sha") != base_sha
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO
            or base_sha != V54_RELEASE_BASE):
        raise ValueError("G145_V54_AUTHENTIC_OWNER_PR_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        base_tree = git("rev-parse", base_sha + "^{tree}")
        guard_before = git("rev-parse", base_sha + ":" + V54_RELEASE_GUARD)
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        pinned = {p: git("rev-parse", head_sha + ":" + p)
                  for p in V54_RELEASE_PINNED}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_V54_EXACT_SOURCE_UNAVAILABLE") from exc
    expected = set(V54_RELEASE_PINNED) | {V54_RELEASE_GUARD}
    if (ancestor != base_sha
            or base_tree != V54_RELEASE_BASE_TREE
            or guard_before != V54_RELEASE_GUARD_BEFORE
            or len(changed) != len(expected) or set(changed) != expected
            or pinned != V54_RELEASE_PINNED):
        raise ValueError("G145_V54_EXACT_SOURCE_OR_WORKFLOW_BLOB_DRIFT")
    return "EXACT_PR1807_V54_OWNER_RELEASE_CI_ONLY"


def v54_owner_release_negative_controls():
    """Reject foreign PRs, moved source blobs and unrelated workflow edits."""
    head = "b" * 40
    request = {
        "number": V54_RELEASE_PR,
        "state": "open",
        "user": {"login": "spoonman136668-ai"},
        "author_association": "OWNER",
        "head": {"ref": V54_RELEASE_BRANCH, "sha": head,
                 "repo": {"full_name": REPO}},
        "base": {"ref": "main", "sha": V54_RELEASE_BASE,
                 "repo": {"full_name": REPO}},
    }
    def git(*args):
        if args[0] == "merge-base":
            return V54_RELEASE_BASE
        if args[:2] == ("rev-parse", V54_RELEASE_BASE + "^{tree}"):
            return V54_RELEASE_BASE_TREE
        if args[:2] == ("rev-parse",
                        V54_RELEASE_BASE + ":" + V54_RELEASE_GUARD):
            return V54_RELEASE_GUARD_BEFORE
        if args[0] == "diff":
            return "\n".join(sorted(set(V54_RELEASE_PINNED)
                                    | {V54_RELEASE_GUARD}))
        if args[0] == "rev-parse" and args[1].startswith(head + ":"):
            return V54_RELEASE_PINNED.get(args[1][len(head) + 1:], "0"*40)
        raise ValueError("unexpected git read")
    if admit_v54_owner_release(head, V54_RELEASE_BASE, request, git) != (
            "EXACT_PR1807_V54_OWNER_RELEASE_CI_ONLY"):
        raise ValueError("G145_V54_NEGATIVE_CONTROL_FALSE_PASS")
    variants = (
        {"number": 1808},
        {"author_association": "CONTRIBUTOR"},
        {"user": {"login": "attacker"}},
        {"head": {**request["head"], "ref": "unrelated"}},
        {"base": {**request["base"], "sha": "0"*40}},
    )
    for changes in variants:
        try:
            admit_v54_owner_release(head, V54_RELEASE_BASE,
                                    {**request, **changes}, git)
        except ValueError:
            pass
        else:
            raise ValueError("G145_V54_FOREIGN_PR_ACCEPTED")
    def moved(*args):
        if args[:2] == ("rev-parse",
                        head + ":.github/workflows/f139-v54-original-owner-release.yml"):
            return "0"*40
        return git(*args)
    try:
        admit_v54_owner_release(head, V54_RELEASE_BASE, request, moved)
    except ValueError:
        pass
    else:
        raise ValueError("G145_V54_MOVED_WORKFLOW_ACCEPTED")
    def moved_g148(*args):
        if args[:2] == ("rev-parse",
                        head + ":scripts/check_rar_g148_go_cache.py"):
            return "0"*40
        return git(*args)
    try:
        admit_v54_owner_release(head, V54_RELEASE_BASE, request, moved_g148)
    except ValueError:
        pass
    else:
        raise ValueError("G145_V54_MOVED_COMPILER_GUARD_ACCEPTED")
    def moved_dynamic_cache(*args):
        if args[:2] == ("rev-parse",
                        head + ":scripts/check_rar_g156_dynamic_base_cache.py"):
            return "0"*40
        return git(*args)
    try:
        admit_v54_owner_release(
            head, V54_RELEASE_BASE, request, moved_dynamic_cache)
    except ValueError:
        pass
    else:
        raise ValueError("G145_V54_MOVED_DYNAMIC_CACHE_GUARD_ACCEPTED")



# Exact-source post-rebind read-only admission (no worker dispatch, no new owner).
FRESH_REBOUND_BRANCH = "engineering/f139-fresh-rebound-receipt-proof-20261120"
FRESH_REBOUND_BASE = "0f37922c8ccd9b218ef82987ef62d80087374937"
FRESH_REBOUND_TREE = "7e974a911083c73f4d75ba0947b6836583b303ed"
FRESH_REBOUND_BLOBS = {
    "f139/nci04_fresh_worker_release_gate.py": "c3606d7a1f8dd5f9405f6d14ac9e74f8a373db0e",
    "f139/test_nci04_fresh_worker_release_gate.py": "27e05ccc4dc788103b8542e6d5d79fa22ab5ae00",
}
FRESH_REBOUND_FILES = frozenset((
    *FRESH_REBOUND_BLOBS,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_rebound_readonly(head_sha: str, base_sha: str,
                                request: dict, git: Callable[..., str]) -> str:
    """Admission is CI-only; no owner mutation, dispatch or first use."""
    if (not is_sha(head_sha) or base_sha != FRESH_REBOUND_BASE
            or type(request) is not dict
            or type(request.get("number")) is not int
            or request["number"] <= 1854
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("ref") != FRESH_REBOUND_BRANCH
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("sha") != FRESH_REBOUND_BASE
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_REBOUND_OWNER_MAIN_SOURCE_REQUIRED")
    try:
        ancestor = git("merge-base", base_sha, head_sha)
        tree = git("rev-parse", base_sha + "^{tree}")
        changed = git("diff", "--no-renames", "--name-only",
                      base_sha, head_sha).splitlines()
        blobs = {path: git("rev-parse", head_sha + ":" + path)
                 for path in FRESH_REBOUND_BLOBS}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("G145_FRESH_REBOUND_SOURCE_UNAVAILABLE") from exc
    if (ancestor != base_sha or tree != FRESH_REBOUND_TREE
            or len(changed) != len(FRESH_REBOUND_FILES)
            or set(changed) != FRESH_REBOUND_FILES
            or blobs != FRESH_REBOUND_BLOBS):
        raise ValueError("G145_FRESH_REBOUND_SOURCE_OR_BLOB_DRIFT")
    return "EXACT_F139_FRESH_REBOUND_READONLY_PROOF_CI_ONLY"



# Fresh functional integration candidate: CI-only, never owner release authority.
FRESH_FUNCTIONAL_BRANCH = "engineering/f139-fresh-functional-integration-20261121"
FRESH_FUNCTIONAL_BASE = "8a4cee175aea05b57625d413e00493a93a027d92"
FRESH_FUNCTIONAL_TREE = "a3a5929728f06ae3a0641bd2bcc875d768f8e313"
FRESH_FUNCTIONAL_BLOBS = {
    "f139/nci04_fresh_worker_protocol.py": "5cf117f3525f44fdbf2098ddbf26c45ac365b12c",
    "f139/test_nci04_fresh_worker_protocol.py": "404c904205ec7e567c41b05294d65a099fcdb81e",
    "f139/nci04_original_v3_terminal.py": "09210bf184eb628b565d172b6281a128c94fdd6c",
    ".github/workflows/forge-f139-development-worker.yml": "75e53278b067d9749f367dc4e6028de7783b834d",
    "f139/nci04_fresh_native_intake.py": "adc1c0c8baca882d846980f3215e6e0441c2b7de",
    "f139/nci04_fresh_native_activation.py": "725b2533969b7a8c0a2131817873f57b22311c1f",
    "f139/nci04_fresh_lifecycle.py": "0b3d206a1652db6e9ac48db55b59c68458b1377f",
    "f139/test_nci04_fresh_lifecycle.py": "3c2dd3e0c5b1cfd4fa8e4b635c00d6a3221ab3ff",
    "f139/nci04_fresh_native_owner_route.py": "72804619c3d4eb4d03e39502d4c7d541fa8ad16e",
    "f139/local_controller.py": "63216e6482ee228cced46ffe87c124955e961f3b",
    "f139/nci04_fresh_owner_worker_release.py": "99d3fac6cb7d0a5e67edff779c48a3d21c088a78",
    ".github/workflows/f139-fresh-original-owner-rebind.yml": "dd94be6064b012cea1b31d24f44e297dcfc440a1",
    "f139/test_nci04_fresh_owner_rebind_source.py": "78784730a2e9e9d308ea00c0efe91d2304e00be3",
    "f139/test_nci04_fresh_owner_worker_release.py": "bb672bdca9b00d319c8540fc6a05b27069402487"
}
FRESH_FUNCTIONAL_FILES = frozenset((*FRESH_FUNCTIONAL_BLOBS, "scripts/check_rar_g145_pr_scope.py", "scripts/check_rar_g148_go_cache.py", "scripts/check_rar_g156_dynamic_base_cache.py"))


def admit_fresh_functional(head_sha, base_sha, request, git):
    if (not is_sha(head_sha) or base_sha != FRESH_FUNCTIONAL_BASE
            or type(request) is not dict
            or request.get("number") != 1856
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("ref") != FRESH_FUNCTIONAL_BRANCH
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("sha") != base_sha
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_FRESH_FUNCTIONAL_OWNER_SOURCE_REQUIRED")
    changed = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
    if (git("merge-base", base_sha, head_sha) != base_sha
            or git("rev-parse", base_sha + "^{tree}") != FRESH_FUNCTIONAL_TREE
            or len(changed) != len(FRESH_FUNCTIONAL_FILES)
            or set(changed) != FRESH_FUNCTIONAL_FILES
            or any(git("rev-parse", head_sha + ":" + p) != blob
                   for p, blob in FRESH_FUNCTIONAL_BLOBS.items())):
        raise ValueError("G145_FRESH_FUNCTIONAL_EXACT_BLOBS_REQUIRED")
    return "EXACT_F139_FRESH_FUNCTIONAL_DRAFT_CI_ONLY"


# One owner-authenticated read-only host recovery witness for failed run 44889700647.
# CI admission only. No task, worker, SQLite, ref or owner mutation authority.
FRESH_CUSTODY_AUDIT_BRANCH = "engineering/f139-owner-custody-readonly-20261121"
FRESH_CUSTODY_AUDIT_BASE = "dce4c672078d6b293286e13f051fdc9a0e54f1da"
FRESH_CUSTODY_AUDIT_TREE = "4cdf235280cc379102e0f2205a9a68d13dafc060"
FRESH_CUSTODY_AUDIT_BLOBS = {
    ".github/workflows/f139-fresh-original-owner-rebind.yml": "28cc3bf32afaa257c5c60d0c26a368dcd3da821f",
    "f139/test_nci04_fresh_owner_rebind_source.py": "472ee8f9e33ffdaa6d5c6ffcddf472a738f0e5de",
}
FRESH_CUSTODY_AUDIT_FILES = frozenset((
    *FRESH_CUSTODY_AUDIT_BLOBS,
    "scripts/check_rar_g145_pr_scope.py",
    "scripts/check_rar_g148_go_cache.py",
    "scripts/check_rar_g156_dynamic_base_cache.py",
))


def admit_fresh_custody_readonly(head_sha, base_sha, request, git):
    if (not is_sha(head_sha) or base_sha != FRESH_CUSTODY_AUDIT_BASE
            or type(request) is not dict
            or request.get("author_association") != "OWNER"
            or request.get("user", {}).get("login") != "spoonman136668-ai"
            or request.get("head", {}).get("ref") != FRESH_CUSTODY_AUDIT_BRANCH
            or request.get("head", {}).get("sha") != head_sha
            or request.get("head", {}).get("repo", {}).get("full_name") != REPO
            or request.get("base", {}).get("ref") != "main"
            or request.get("base", {}).get("sha") != base_sha
            or request.get("base", {}).get("repo", {}).get("full_name") != REPO):
        raise ValueError("G145_OWNER_CUSTODY_READONLY_SOURCE_DENIED")
    changed = git("diff", "--no-renames", "--name-only", base_sha, head_sha).splitlines()
    if (git("merge-base", base_sha, head_sha) != base_sha
            or git("rev-parse", base_sha + "^{tree}") != FRESH_CUSTODY_AUDIT_TREE
            or len(changed) != len(FRESH_CUSTODY_AUDIT_FILES)
            or set(changed) != FRESH_CUSTODY_AUDIT_FILES
            or any(git("rev-parse", head_sha + ":" + p) != sha
                   for p, sha in FRESH_CUSTODY_AUDIT_BLOBS.items())):
        raise ValueError("G145_OWNER_CUSTODY_READONLY_EXACT_BLOBS_REQUIRED")
    return "EXACT_F139_OWNER_CUSTODY_READONLY_CI_ONLY"


def admit_original_pr(head_sha: str, git: Callable[..., str]) -> str:
    """Engineering CI admission only; never research, merge or FSA authority."""
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request" or not callable(git):
        raise ValueError("G145_NOT_GITHUB_PR")
    branch = os.environ.get("GITHUB_HEAD_REF", "")
    base_sha = github_event_base(head_sha)
    if branch == FRESH_CUSTODY_AUDIT_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        return admit_fresh_custody_readonly(head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_FUNCTIONAL_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        return admit_fresh_functional(head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_REBOUND_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_rebound_readonly(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_POLICY_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_owner_process_policy_fix(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_REBIND_CANCEL_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_rebind_pending_collision_fix(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_SHELL_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_owner_shell_fix(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_REBIND_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_original_rebind(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_STANDDOWN_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_original_standdown(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_ACTIVATION_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_owner_activation_bridge(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_CONCURRENCY_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_admission_job_concurrency(
            head_sha, base_sha, event["pull_request"], git)
    if branch == FRESH_OWNER_ADMIT_BRANCH:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                           .read_text(encoding="utf-8"))
        return admit_fresh_owner_admission(
            head_sha, base_sha, event["pull_request"], git)
    if branch == V54_RELEASE_BRANCH:
        request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                             .read_text(encoding="utf-8"))["pull_request"]
        return admit_v54_owner_release(head_sha, base_sha, request, git)
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
        if branch == V61_PROCESS_FIX_BRANCH:
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            admit_v61_owner_parser_fix(head_sha, base_sha, request, git)
        if branch == V60_PROCESS_BRANCH:
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            admit_v60_owner_process_census(head_sha, base_sha, request, git)
        if branch == V59_READONLY_BRANCH:
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != V59_READONLY_BRANCH
                    or request.get("head", {}).get("sha") != head_sha
                    or request.get("base", {}).get("sha") != V59_READONLY_BASE
                    or request.get("base", {}).get("ref") != "main"
                    or git("rev-parse", V59_READONLY_BASE + "^{tree}")
                       != V59_READONLY_BASE_TREE
                    or git("rev-parse", head_sha + ":" + V59_READONLY_WORKFLOW)
                       != V59_READONLY_WORKFLOW_BLOB):
                raise ValueError("G145_V59_ORIGINAL_READONLY_EXACT_SOURCE_DENIED")
        if branch == "engineering/f139-v58-model-free-status-readonly-20261119":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != "c06403c8b6035c6c7013866a7ea08cef1244b507"
                    or git("rev-parse", "c06403c8b6035c6c7013866a7ea08cef1244b507:.github/workflows/f139-g54-v9-owner-cutover.yml") != "39f189fde3a6fece791cd3a6ca7dd0517cb6b430"
                    or git("rev-parse", head_sha + ":.github/workflows/f139-g54-v9-owner-cutover.yml") != "da2abe072131358e411a82df170aa66b7f59b724"):
                raise ValueError("G145_V58_EXACT_READONLY_WORKFLOW_DENIED")
        if branch == "engineering/f139-v53-precommit-original-owner-restore-20261117":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (request.get("number") != 1804
                    or request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != "918a7a10a3f47e30b2ecd6d3d443ff16428b9c0b"):
                raise ValueError("G145_V53_EXACT_PRECOMMIT_OWNER_RESTORE_DENIED")
        if branch == "engineering/f139-v53-owner-assignment-recovery-20261117":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (request.get("number") != 1803
                    or request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != "09d0f6639d1e9bc54e0c909ccd9fb7bfaaea87f8"):
                raise ValueError("G145_V53_OWNER_ASSIGNMENT_SCOPE_DENIED")
        if branch == "engineering/f139-v53-original-owner-dispatch-20261117":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            if (request.get("number") != 1802
                    or request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != "a63ea00a9046bf107b59d64b3557ebd78c8f4157"):
                raise ValueError("G145_V53_EXACT_OWNER_WORKFLOW_PR_DENIED")
        if branch == "engineering/f139-v52-original-owner-forward-repair-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-v52-original-owner-source-repair.yml"
            base = "d4e588f0fbd8486e1d34754ddcf0f540c2895590"
            if (type(request.get("number")) is not int
                    or request["number"] != 1797
                    or request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != base
                    or git("rev-parse", base + "^{tree}") != "b0a8cab352374b37eb774af0eefce5b43460e58a"
                    or git("rev-parse", head_sha + ":" + workflow) != "b850aff66736af77ddd2744fb22725a11add64e7"):
                raise ValueError("G145_V52_OWNER_REPAIR_FROZEN_SCOPE_DENIED")
        if branch == "engineering/f139-v51-original-owner-preflight-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-v51-original-owner-readonly.yml"
            base = "e657a0b3f85120b72fcf3e191a0b1c1c289c97cb"
            if (type(request.get("number")) is not int
                    or request["number"] != 1796
                    or request.get("user", {}).get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != base
                    or git("rev-parse", base + "^{tree}") != "838d0d9a78df327571efd0030b092721db8b8bc7"
                    or git("rev-parse", head_sha + ":" + workflow) != "9b0dd9544c36c00161779accac477002f2e79b8e"):
                raise ValueError("G145_V51_READONLY_FROZEN_OWNER_SCOPE_DENIED")
        if branch == "engineering/f139-v50-v41-original-native-activation-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            base = "2567775a9c06b306142812cc8c0e252278f87273"
            if (type(request.get("number")) is not int
                    or request["number"] != 1793
                    or type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") != base
                    or git("rev-parse", base + "^{tree}") !=
                       "ad98fa391638b59254534ddfffea1be5c538b958"
                    or git("rev-parse", base + ":" + workflow) !=
                       "72debcd8404e637c44af760f752d9287af0f0738"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                       "39f189fde3a6fece791cd3a6ca7dd0517cb6b430"):
                raise ValueError("G145_V50_ORIGINAL_NATIVE_ACTIVATION_SCOPE_DENIED")
        if branch == "engineering/f139-v48-held-original-owner-safe-recovery-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") !=
                       "ce5d4e06d9466735030568f4e5576adca78d804f"
                    or git("rev-parse", "ce5d4e06d9466735030568f4e5576adca78d804f^{tree}") !=
                       "b39e579521ef02cdd0037a91bd09184f04e69997"
                    or git("rev-parse", "ce5d4e06d9466735030568f4e5576adca78d804f:" + workflow) !=
                       "ab89c3ea185ba68b08ea83517bf36d48319e32d9"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                       "72debcd8404e637c44af760f752d9287af0f0738"):
                raise ValueError("G145_V48_ORIGINAL_HELD_RECOVERY_SCOPE_DENIED")
        if branch == "engineering/f139-v47-existing-ref-original-owner-recovery-20261116":
            request = json.loads(Path(os.environ["GITHUB_EVENT_PATH"])
                                 .read_text(encoding="utf-8"))["pull_request"]
            workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
            if (type(request.get("user")) is not dict
                    or request["user"].get("login") != "spoonman136668-ai"
                    or request.get("author_association") != "OWNER"
                    or request.get("head", {}).get("ref") != branch
                    or request.get("base", {}).get("sha") !=
                       "ba6419cfa75879d23e8ae24c2bb8749d08e2b6d5"
                    or git("rev-parse", "ba6419cfa75879d23e8ae24c2bb8749d08e2b6d5^{tree}") !=
                       "45a7d0089377269fcfa1dc5bf4c712445465f6b3"
                    or git("rev-parse", "ba6419cfa75879d23e8ae24c2bb8749d08e2b6d5:" + workflow) !=
                       "267016423cf28e3c260223dbcdfc863d13adb053"
                    or git("rev-parse", head_sha + ":" + workflow) !=
                       "ab89c3ea185ba68b08ea83517bf36d48319e32d9"):
                raise ValueError("G145_V47_ORIGINAL_RECOVERY_SCOPE_DENIED")
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

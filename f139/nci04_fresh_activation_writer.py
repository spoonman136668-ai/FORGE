"""One-shot F139 fresh development activation on the *existing* Windows owner.

Source-only library, NOT a CLI, workflow trigger, task rebind or new controller.
The original 1864-event SQLite is read-only. Only an independently staged,
disabled, separate fresh SQLite may receive the two versioned activation
events, after an actual owner-approved Windows issue-comment run proves that
the original task is disabled, child-free, same SID, same pinned installation.

There is intentionally no run_once caller. Even a successful transaction
remains dispatch-blocked pending independently qualified worker admission.
A partial create-only receipt is a spent attempt: do not delete/retry it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from f139.local_controller import Database, SingleOwner, ZERO
from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_native_activation import (
    ACTIVATION_KIND, ACTIVATION_SCHEMA, OWNER_RELEASE_SCHEMA,
    authenticate_fresh_activation_receipts, audit_fresh_native_activation,
)
from f139.nci04_fresh_native_owner_route import (
    inspect_staged_fresh_native_mode, _sealed_json,
)
from f139.nci04_fresh_remote_floor import (
    prove_fresh_native_issue_cutover_floor,
)
from f139.nci04_fresh_dev_epoch import hash_file
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED, read_yggdrasil_research_boundary,
)
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)
from f139.nci04_v59_cold_backup_verify import verify_original_cold_backup

REPO = "spoonman136668-ai/FORGE"
TASK = "FORGE-F139-UnifiedController"
OWNER = "spoonman136668-ai"
WORKFLOW = (
    "spoonman136668-ai/FORGE/.github/workflows/"
    "f139-fresh-original-owner-activation.yml@refs/heads/main"
)
APPROVAL_ISSUE = 1830
APPROVAL_PREFIX = "F139-FRESH-DEV-STAGE-ACTIVATE"
SCHEMA = "forge.f139.fresh-native-activation-write-receipt.v1"

# No Stop/Start/Register/Set-ScheduledTask, controller launch, process kill,
# network POST or task mutation. The first failure produces no PASS marker.
_WINDOWS_READONLY_PROBE = r"""
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try {
  $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).
    Translate([Security.Principal.SecurityIdentifier]).Value
} catch {}
if (@($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3 -or
    [string]$t.State -cne 'Disabled' -or $t.Settings.Enabled -ne $false -or
    ([string]$t.Principal.UserId -ine $who.Name -and
     $sid -cne $who.User.Value)) { exit 51 }
$a=$t.Actions[0]
if ([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe' -or
    [string]$a.Arguments -notmatch '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)') {
  exit 52
}
function Arg([string]$name) {
  $m=[regex]::Match([string]$a.Arguments,
    '(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  if (-not $m.Success) {exit 53}
  return [string]$m.Groups[1].Value
}
$root=Arg 'RepositoryRoot'
$db=Arg 'Database'
$wrapper=Arg 'File'
$py=Arg 'PythonExe'
$expected=Join-Path $env:LOCALAPPDATA (
  'FORGE-F139\release-candidates\'+'__FROZEN_SOURCE__')
if ([IO.Path]::GetFullPath($root) -ine [IO.Path]::GetFullPath($expected) -or
    [IO.Path]::GetFullPath($db) -ine
      [IO.Path]::GetFullPath($env:F139_FRESH_ORIGINAL_DB) -or
    [IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1' -or
    -not (Test-Path -LiteralPath $py -PathType Leaf)) {exit 54}
$head=(& git -C $root rev-parse HEAD | Out-String).Trim()
$dirty=@(& git -C $root status --porcelain --untracked-files=all)
if ($LASTEXITCODE -ne 0 -or $head -cne '__FROZEN_SOURCE__' -or
    $dirty.Count -ne 0) {exit 55}
$children=@(Get-CimInstance Win32_Process -Filter
  "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.CommandLine -and
    $_.CommandLine.Contains('f139.local_controller')})
if ($children.Count -ne 0) {exit 56}
Write-Output 'F139_FRESH_ORIGINAL_WINDOWS_TASK_DISABLED=PASS'
"""


class FreshActivationWriteDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise FreshActivationWriteDenied("F139_FRESH_WRITE_" + code)


def _owner_windows_quiesced(original_path: Path, target: str,
                            owner_run_id: int) -> bool:
    """Actual task/SID/process check; no caller-supplied Boolean witness."""
    need(os.name == "nt" and sys.platform == "win32"
         and os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and os.environ.get("GITHUB_REPOSITORY") == REPO
         and os.environ.get("GITHUB_ACTOR") == OWNER
         and os.environ.get("GITHUB_REF") == "refs/heads/main"
         and os.environ.get("GITHUB_EVENT_NAME") == "issue_comment"
         and os.environ.get("GITHUB_WORKFLOW_REF") == WORKFLOW
         and os.environ.get("GITHUB_SHA") == target
         and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
         and os.environ.get("GITHUB_RUN_ID") == str(owner_run_id)
         and not os.environ.get("OPENAI_API_KEY"),
         "ORIGINAL_WINDOWS_AUTHENTICATED_WORKFLOW_REQUIRED")
    profile = os.environ.get("LOCALAPPDATA", "")
    need(bool(profile) and original_path.resolve() ==
         (Path(profile) / "FORGE-F139" / "state.sqlite").resolve(),
         "ORIGINAL_DATABASE_PATH_DRIFT")
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    need(event_path.is_file() and not event_path.is_symlink()
         and 0 < event_path.stat().st_size <= 64_000,
         "OWNER_ISSUE_EVENT_NOT_PRESENT")
    try:
        event = json.loads(event_path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise FreshActivationWriteDenied(
            "F139_FRESH_WRITE_OWNER_ISSUE_EVENT_INVALID") from exc
    need(type(event) is dict
         and event.get("action") == "created"
         and type(event.get("repository")) is dict
         and event["repository"].get("full_name") == REPO
         and type(event.get("issue")) is dict
         and event["issue"].get("number") == APPROVAL_ISSUE
         and event["issue"].get("state") == "open"
         and type(event["issue"].get("user")) is dict
         and event["issue"]["user"].get("login") == OWNER
         and type(event.get("sender")) is dict
         and event["sender"].get("login") == OWNER
         and type(event.get("comment")) is dict
         and type(event["comment"].get("user")) is dict
         and event["comment"]["user"].get("login") == OWNER
         and event["comment"].get("body") ==
             f"{APPROVAL_PREFIX} {target} {owner_run_id}",
         "OWNER_RUN_BOUND_APPROVAL_NOT_AUTHENTICATED")
    powershell = shutil.which("powershell.exe")
    need(powershell is not None, "ORIGINAL_POWERSHELL_REQUIRED")
    probe = _WINDOWS_READONLY_PROBE.replace("__FROZEN_SOURCE__", SOURCE)
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", probe],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, check=False,
            env={**os.environ, "F139_FRESH_ORIGINAL_DB": str(original_path)})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FreshActivationWriteDenied(
            "F139_FRESH_WRITE_OWNER_TASK_PROBE_UNAVAILABLE") from exc
    need(result.returncode == 0 and result.stdout.strip() ==
         b"F139_FRESH_ORIGINAL_WINDOWS_TASK_DISABLED=PASS",
         "ORIGINAL_TASK_NOT_RELEASED_OR_PROCESS_ACTIVE")
    return True


def write_fresh_native_activation_once(
    original: Database, fresh: Database, *, get,
) -> dict:
    """Prepare create-only external receipts and atomically activate fresh DB.

    The original task must already be stopped/disabled by the independent
    authorized owner route. This function NEVER stops or rebinds that task.
    The new SQLite activation is not worker dispatch or science permission.
    """
    need(type(original) is Database and
         getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.conn.total_changes == 0
         and type(fresh) is Database and callable(get),
         "OWNER_OR_PROVIDER_ARGUMENT_INVALID")
    original_path = original.filename
    new_path = fresh.filename
    need(original_path.is_absolute()
         and original_path.name == "state.sqlite"
         and original_path.parent.name == "FORGE-F139"
         and new_path.is_absolute()
         and new_path.parent.parent == original_path.parent
         and SingleOwner.held(original_path.with_suffix(".lock")) is True
         and SingleOwner.held(new_path.with_suffix(".lock")) is True,
         "SINGLE_OWNER_MUTEX_OR_PATH_INVALID")
    meta = fresh.meta()
    target = meta["source_sha"]
    initial = inspect_staged_fresh_native_mode(fresh, new_path)
    need(type(initial) is dict
         and initial["disposition"] ==
             "FRESH_DEVELOPMENT_STAGED_DISABLED_NO_DISPATCH"
         and initial["source_sha"] == target
         and initial["original_head_seq"] == HEAD_SEQ
         and initial["original_head_sha256"] == HEAD_SHA256
         and meta["head_seq"] == 0 and meta["head_hash"] == ZERO
         and meta["enabled"] == 0 and meta["legacy_suspended"] == 0,
         "FRESH_STAGE_ALREADY_CONSUMED_OR_UNVERIFIED")
    run_id = initial["staged_owner_run_id"]
    need(_owner_windows_quiesced(original_path, target, run_id),
         "ORIGINAL_HOST_NOT_QUIESCED")
    original.verify()
    before = audit_frozen_original_readonly(original)
    need(before["source_sha"] == SOURCE and
         before["head_seq"] == HEAD_SEQ and
         before["head_sha256"] == HEAD_SHA256,
         "ORIGINAL_LEDGER_HEAD_DRIFT")
    root = original_path.parent
    archive = root / ("f139-v59-before-" + str(run_id))
    manifest, manifest_bytes = _sealed_json(
        new_path.parent / "fresh-dev-manifest.sha256.json")
    consumed, consumed_bytes = _sealed_json(
        new_path.parent / "consumed-development-identities.json")
    lineage, lineage_bytes = _sealed_json(
        new_path.parent / "yggdrasil-research-lineage.json")
    archived, _ = _sealed_json(archive / "manifest.sha256.json")
    backup = archive / "state.sqlite"
    need(backup.is_file() and not backup.is_symlink()
         and archived.get("files_sha256", {}).get("state.sqlite") ==
             hash_file(backup)
         and manifest.get("historical_sqlite_sha256") == hash_file(backup),
         "ORIGINAL_BACKUP_CHANGED")
    verified = verify_original_cold_backup(
        original, backup, owner_run_id=run_id, target=target,
        expected_backup_sha256=hash_file(backup))
    need(verified.get("original_head_seq") == HEAD_SEQ
         and verified.get("original_head_sha256") == HEAD_SHA256
         and verified.get("source_transition_authorized") is False
         and verified.get("original_owner_mutations") == 0,
         "ORIGINAL_ARCHIVE_NOT_REVERIFIED")
    need(canonical(read_yggdrasil_research_boundary(get)) == lineage_bytes,
         "YGGDRASIL_ACCEPTED_RESEARCH_BOUNDARY_MOVED")
    floor = prove_fresh_native_issue_cutover_floor(
        original, target_source_sha=target,
        consumed_exclusions=consumed, get=get,
        original_task_quiesced=lambda: _owner_windows_quiesced(
            original_path, target, run_id))
    floor_bytes = canonical(floor)
    release = {
        "schema": OWNER_RELEASE_SCHEMA,
        "owner_task_name": TASK,
        "target_forge_source_sha": target,
        "owner_run_id": run_id,
        "original_source_sha": SOURCE,
        "original_head_seq": HEAD_SEQ,
        "original_head_sha256": HEAD_SHA256,
        "remote_cutover_receipt_sha256": digest(floor_bytes),
        "original_task_quiesced": True,
        "original_process_absent": True,
        "original_mutex_held": True,
        "original_sid_independently_verified": True,
        "single_task_rebind_authorized": True,
        "new_controller": False,
        "new_scheduler": False,
        "scientific_first_use": False,
    }
    release_bytes = canonical(release)
    # Compute the exact first event SHA before doing any writes, allowing the
    # existing receipt verifier to reject a malformed record in advance.
    first_hash = digest(canonical({
        "seq": 1, "prior_sha": ZERO, "kind": "CUTOVER_ACTIVATED",
        "payload": {"source_sha": target},
    }))
    record = {
        "schema": ACTIVATION_SCHEMA,
        "source_sha": target,
        "prior_event_head_sha256": first_hash,
        "owner_run_id": run_id,
        "original_source_sha": SOURCE,
        "original_head_seq": HEAD_SEQ,
        "original_head_sha256": HEAD_SHA256,
        "stage_manifest_sha256": digest(manifest_bytes),
        "consumed_exclusions_sha256": digest(consumed_bytes),
        "yggdrasil_research_boundary_sha256": digest(lineage_bytes),
        "remote_cutover_receipt_sha256": digest(floor_bytes),
        "original_task_release_receipt_sha256": digest(release_bytes),
        "remote_issue_number_floor": floor["remote_cutover_issue_number_floor"],
        "accepted_yggdrasil_main_sha": ACCEPTED,
        "development_only": True,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
        "worker_dispatch_authorized": False,
        "model_continuation_authorized": False,
    }
    authenticate_fresh_activation_receipts(
        record, stage=manifest, consumed=consumed,
        yggdrasil_boundary=lineage, remote_floor=floor, owner_release=release,
        manifest_bytes=manifest_bytes, consumed_bytes=consumed_bytes,
        yggdrasil_bytes=lineage_bytes, floor_bytes=floor_bytes,
        release_bytes=release_bytes)
    floor_path = new_path.parent / "remote-issue-cutover-floor.json"
    release_path = new_path.parent / "original-task-release.json"
    need(not floor_path.exists() and not floor_path.is_symlink()
         and not release_path.exists() and not release_path.is_symlink(),
         "ONE_SHOT_RECEIPT_PATH_ALREADY_SPENT")
    need(_owner_windows_quiesced(original_path, target, run_id)
         and audit_frozen_original_readonly(original) == before
         and original.conn.total_changes == 0,
         "ORIGINAL_MOVED_BEFORE_ACTIVATION")
    # Both external receipts are create-only; an interrupted attempt is
    # explicitly non-retryable and never becomes an unspent issue/experiment.
    with floor_path.open("xb") as out:
        out.write(floor_bytes)
    with release_path.open("xb") as out:
        out.write(release_bytes)
    need(floor_path.read_bytes() == floor_bytes
         and release_path.read_bytes() == release_bytes,
         "CREATE_ONLY_RECEIPT_READBACK_DRIFT")
    with fresh.transaction():
        need(_owner_windows_quiesced(original_path, target, run_id)
             and fresh.meta()["head_seq"] == 0
             and fresh.meta()["enabled"] == 0
             and not fresh.conn.execute("SELECT 1 FROM tasks LIMIT 1").fetchone(),
             "ORIGINAL_RELEASE_OR_FRESH_HEAD_CHANGED")
        fresh.conn.execute(
            "UPDATE meta SET enabled=1, legacy_suspended=1 WHERE id=1")
        fresh.event("CUTOVER_ACTIVATED", {"source_sha": target})
        need(fresh.meta()["head_hash"] == first_hash,
             "FRESH_CUTOVER_HASH_DRIFT")
        fresh.event(ACTIVATION_KIND, record)
        fresh.verify()
        need(audit_fresh_native_activation(fresh) == record,
             "FRESH_ACTIVATION_COLD_AUDIT_FAILED")
        need(_owner_windows_quiesced(original_path, target, run_id)
             and audit_frozen_original_readonly(original) == before,
             "ORIGINAL_MOVED_DURING_ACTIVATION")
    final = inspect_staged_fresh_native_mode(fresh, new_path)
    need(final["disposition"] == "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED"
         and not final["fresh_work_admitted"]
         and not final["worker_dispatched"]
         and original.conn.total_changes == 0,
         "POSTACTIVATION_DISPATCH_OR_ORIGINAL_DRIFT")
    return {
        "schema": SCHEMA, "source_sha": target,
        "owner_run_id": run_id,
        "head_seq": fresh.meta()["head_seq"],
        "head_sha256": fresh.meta()["head_hash"],
        "remote_issue_number_floor": record["remote_issue_number_floor"],
        "original_sqlite_mutations": 0,
        "task_rebound": False,
        "worker_dispatched": False,
        "native_issue_admitted": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
    }

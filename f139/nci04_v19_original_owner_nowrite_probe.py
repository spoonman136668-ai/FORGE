"""Explicit zero-DB-write V19 original Windows readiness probe.

This is not a release, not a backup, and not a task quiescence operation.
Invocation must be a separate owner-authorized read-only action on the
existing original Windows runner. Do not dispatch from a pull_request.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_v19_original_release_readonly_preflight import (
    SOURCE, v19_original_release_readonly_preflight)


class OwnerReadOnlyDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise OwnerReadOnlyDenied("F139_V19_ORIGINAL_NOWRITE_" + code)


_TASK_PROBE = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$t = Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
if ([string]$t.State -cnotin @('Running','Ready') -or
    @($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3) { exit 31 }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [string]$t.Principal.UserId
$sid=''
try {
    $sid=(New-Object Security.Principal.NTAccount($principal)).Translate(
        [Security.Principal.SecurityIdentifier]).Value
} catch {}
if ($principal -ine $identity.Name -and $sid -cne $identity.User.Value) {
    exit 32
}
# V19_ACTION_ROUTE_BEGIN
$action=$t.Actions[0]
if ([IO.Path]::GetFileName([string]$action.Execute) -ine 'powershell.exe') {
    exit 37
}
$arguments=[string]$action.Arguments
if ($arguments -notmatch '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)') {
    exit 33
}
function Field([string]$key) {
    $match=[regex]::Match($arguments, '(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
    if (-not $match.Success) { exit 34 }
    return $match.Groups[1].Value
}
$wrapper=Field 'File'
if (-not ([IO.Path]::IsPathRooted($wrapper)) -or
    [IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1' -or
    -not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
    exit 38
}
# V19_ACTION_ROUTE_END
$db=Field 'Database'
$root=Field 'RepositoryRoot'
$py=Field 'PythonExe'
$expected=[Environment]::GetEnvironmentVariable('F139_V19_PROBE_DB')
if ([string]::IsNullOrWhiteSpace($expected) -or
    [IO.Path]::GetFullPath($db) -ine [IO.Path]::GetFullPath($expected) -or
    -not(Test-Path -LiteralPath $py -PathType Leaf) -or
    -not(Test-Path -LiteralPath $root -PathType Container)) { exit 35 }
$old=(& git -C $root rev-parse HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or
    $old -cne 'd8bccc604f8607bf10f9d8bc6aa568d1f98af559' -or
    @(& git -C $root status --porcelain --untracked-files=all).Count -ne 0) {
    exit 36
}
'F139_V19_READ_ONLY_ORIGINAL_OWNER_MATCH'
"""


def owner_witness(db_path: Path) -> bool:
    """Confirm same existing original task, SID, clean V18 source; no task edit."""
    need(os.name == "nt" and os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE",
         "ORIGINAL_WINDOWS_RUNNER_REQUIRED")
    profile = os.environ.get("LOCALAPPDATA", "")
    need(bool(profile), "LOCALAPPDATA_REQUIRED")
    expected = Path(profile) / "FORGE-F139" / "state.sqlite"
    need(db_path.resolve() == expected.resolve(), "ORIGINAL_SQLITE_PATH_DRIFT")
    powershell = shutil.which("powershell.exe")
    need(powershell is not None, "WINDOWS_OWNER_INSPECTOR_MISSING")
    environment = {**os.environ, "F139_V19_PROBE_DB": str(db_path)}
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", _TASK_PROBE],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, check=False, env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OwnerReadOnlyDenied("F139_V19_ORIGINAL_NOWRITE_TASK_PROBE_UNAVAILABLE") from exc
    need(result.returncode == 0
         and result.stdout.strip() == b"F139_V19_READ_ONLY_ORIGINAL_OWNER_MATCH",
         "TASK_PROFILE_SID_OR_INSTALLED_V18_DRIFT")
    return True


def inspect_original_owner(db_path: Path) -> dict:
    """No GitHub write, controller tick, task mutation or SQLite source update."""
    db_path = Path(db_path)
    owner_witness(db_path)
    with SingleOwner(db_path.with_suffix(".lock")):
        db = Database.open_readonly(db_path)
        try:
            proof = v19_original_release_readonly_preflight(
                db, original_get=GitHub().get,
                owner_witness=lambda: owner_witness(db_path))
        finally:
            db.close()
    need(proof["read_only"] is True
         and proof["runtime_cutover_authorized"] is False
         and proof["original_sqlite_writes"] == 0
         and proof["github_writes"] == 0,
         "UNEXPECTED_RELEASE_AUTHORITY")
    return proof


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only original V18 owner witness; NO release authority")
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(inspect_original_owner(args.db), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

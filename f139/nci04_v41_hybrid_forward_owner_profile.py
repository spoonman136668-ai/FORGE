"""Read-only F139 original task identity for the committed V37 forward hold.

The failed original V41 source activation retargeted the disabled original
task before its Hybrid schema migration failed. The historic V41-only
task reader is appropriate for *precommit* V41 but would reject this
postcommit 1830-event hold. Permit ONLY either clean exact old V41 checkout
or its one authenticated v37 successor, never arbitrary target/branch paths.

No task edits, process stops, restart, policy update or science. Callers
independently verify actual immutable 1830-event SQLite and cold bundle.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from f139 import nci04_v41_hybrid_source_transition as v37
from f139 import nci04_v41_hybrid_forward_repair as forward

ALLOWED_ACTION_SOURCE_SHAS = frozenset({v37.FROM_V41, forward.FROM})
PROOF = b"F139_V38_HELD_ORIGINAL_TASK_READONLY=PASS"


class HeldTaskIdentityDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise HeldTaskIdentityDenied(
            "F139_HYBRID_V38_HELD_TASK_" + reason)


def readback(db_path, *, runner=None):
    """Prove the same disabled Windows task/SID/trigger/db with no owner writes.

    Return no path or SID; the subprocess emits only the fixed PASS marker.
    This check alone is not source transition or runner execution authority.
    """
    need(os.name == "nt", "ORIGINAL_WINDOWS_HOST_REQUIRED")
    need(isinstance(db_path, Path) and db_path.is_absolute()
         and db_path.name == "state.sqlite" and db_path.is_file()
         and not db_path.is_symlink(),
         "EXACT_ORIGINAL_SQLITE_PATH_REQUIRED")
    powershell = shutil.which("powershell.exe")
    need(type(powershell) is str and bool(powershell),
         "WINDOWS_READONLY_POWERSHELL_REQUIRED")
    # Fixed program; no dynamically interpolated PowerShell script or
    # untrusted issue text. Allowed refs are the two sealed literal SHAs.
    script = r'''
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try {
  $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).
    Translate([Security.Principal.SecurityIdentifier]).Value
} catch {}
if(-not([string]$t.Principal.UserId -ieq $who.Name -or
        $sid -ceq $who.User.Value)) {exit 41}
if(@($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3){exit 42}
$a=$t.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 43}
function Arg([string]$key) {
  $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  if(-not $m.Success){exit 44}
  return [string]$m.Groups[1].Value
}
$db=Arg 'Database'
$root=Arg 'RepositoryRoot'
$exe=Arg 'PythonExe'
$wrapper=Arg 'File'
if([IO.Path]::GetFullPath($db) -ine
   [IO.Path]::GetFullPath($env:F139_V38_EXPECTED_DATABASE)){exit 45}
if([IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1'){exit 46}
if(-not(Test-Path -LiteralPath $root -PathType Container) -or
   -not(Test-Path -LiteralPath $exe -PathType Leaf) -or
   -not(Test-Path -LiteralPath $wrapper -PathType Leaf)){exit 47}
$now=(& git -C $root rev-parse HEAD|Out-String).Trim()
$allow=@($env:F139_V38_ALLOWED_ACTION_SOURCE_SHAS -split ';')
if($LASTEXITCODE -ne 0 -or -not($allow -ccontains $now) -or
   $allow.Count -ne 2){exit 48}
$dirty=@(& git -C $root status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){exit 49}
if([string]$t.State -cne 'Disabled' -or
   $t.Settings.Enabled -ne $false){exit 50}
$running=@(Get-CimInstance Win32_Process -Filter
  "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.CommandLine -and
    $_.CommandLine.Contains('f139.local_controller') -and
    $_.CommandLine.Contains($env:F139_V38_EXPECTED_DATABASE)})
if($running.Count -ne 0){exit 51}
Write-Output 'F139_V38_HELD_ORIGINAL_TASK_READONLY=PASS'
'''
    env = {**os.environ,
           "F139_V38_EXPECTED_DATABASE": str(db_path.resolve()),
           "F139_V38_ALLOWED_ACTION_SOURCE_SHAS": ";".join(sorted(
               ALLOWED_ACTION_SOURCE_SHAS))}
    execute = subprocess.run if runner is None else runner
    try:
        result = execute(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, env=env, timeout=25, check=False)
    except subprocess.TimeoutExpired as exc:
        raise HeldTaskIdentityDenied(
            "F139_HYBRID_V38_HELD_TASK_READBACK_TIMEOUT") from exc
    need(result.returncode == 0 and result.stdout.strip() == PROOF,
         "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED")
    return True

"""Native preinstall witness for the existing original V40 Windows task.

Read-only. This intentionally verifies the *old* task source checkout while
the new V41 candidate runs from a distinct, exact-SHA clean checkout. Using
native_original_owner_profile here would deadlock installation: that older
helper correctly insists the task already points at the new checkout.

It never disables/starts/registers the task, reads keys, mutates policy,
opens the original SQLite for write, or issues a source commit.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from f139 import nci04_v41_source_transition as source


class NativePreinstallDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise NativePreinstallDenied("F139_V41_PREINSTALL_" + code)


# The old task has exactly one source and owner; never accept unverified roots.
SCRIPT = r"""
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$p=[string]$t.Principal.UserId
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount($p)).Translate(
 [Security.Principal.SecurityIdentifier]).Value}catch{}
if($p -ine $who.Name -and $sid -ne $who.User.Value){exit 42}
if([string]$t.State -cne 'Disabled' -or $t.Settings.Enabled -ne $false){exit 43}
if(@($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3){exit 44}
$a=$t.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 45}
$opts=[string]$a.Arguments
$root=[regex]::Match($opts,'(?i)(?:^|\s)-RepositoryRoot\s+"([^"]+)"')
$db=[regex]::Match($opts,'(?i)(?:^|\s)-Database\s+"([^"]+)"')
$py=[regex]::Match($opts,'(?i)(?:^|\s)-PythonExe\s+"([^"]+)"')
$wrapper=[regex]::Match($opts,'(?i)(?:^|\s)-File\s+"([^"]+)"')
if(-not($root.Success -and $db.Success -and $py.Success -and $wrapper.Success)){exit 46}
if([IO.Path]::GetFileName($wrapper.Groups[1].Value) -cne 'Run-FORGE-F139.ps1'){exit 47}
if([IO.Path]::GetFullPath($db.Groups[1].Value) -ine
    [IO.Path]::GetFullPath($env:F139_EXPECTED_ORIGINAL_DATABASE)){exit 48}
if(-not (Test-Path -LiteralPath $py.Groups[1].Value -PathType Leaf)){exit 49}
$oldRoot=[IO.Path]::GetFullPath($root.Groups[1].Value)
if($oldRoot -ieq [IO.Path]::GetFullPath($env:F139_EXPECTED_CANDIDATE_ROOT)){exit 50}
$oldHead=(& git -C $oldRoot rev-parse HEAD | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $oldHead -cne $env:F139_EXPECTED_V40_SOURCE){exit 51}
$dirty=@(& git -C $oldRoot status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){exit 52}
if($opts -notmatch '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)'){exit 53}
$other=@(Get-CimInstance Win32_Process -Filter
    "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object { [int]$_.ProcessId -ne [int]$env:F139_CANDIDATE_PID -and
      $_.CommandLine -and
      $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($env:F139_EXPECTED_ORIGINAL_DATABASE) })
if($other.Count -ne 0){exit 54}
Write-Output 'F139_V41_OLD_TASK_DISABLED_STAGED_CANDIDATE=PASS'
"""


def verify_original_task_disabled_for_staged_candidate(
        db_path: Path, candidate_root: Path, target: str):
    """Require the real Windows owner SID/task, old root, and staged target.

    No exception path silently assumes old task quiescence. A fresh, distinct
    candidate checkout must be checked independently and must not collide
    with the old controller's actual source root.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and isinstance(db_path, Path)
         and isinstance(candidate_root, Path)
         and type(target) is str
         and source.HEX40.fullmatch(target) is not None
         and target != source.FROM_V40,
         "WINDOWS_EXACT_CANDIDATE_REQUIRED")
    need(db_path.is_absolute() and db_path.name == "state.sqlite"
         and db_path.is_file() and not db_path.is_symlink()
         and type(os.environ.get("LOCALAPPDATA")) is str
         and db_path.resolve() ==
             (Path(os.environ["LOCALAPPDATA"]) / "FORGE-F139" /
              "state.sqlite").resolve(),
         "CANONICAL_ORIGINAL_SQLITE_ONLY")
    root = Path(__file__).resolve().parents[1]
    need(candidate_root.is_absolute()
         and candidate_root.resolve() == root
         and not candidate_root.is_symlink()
         and all(not part.is_symlink() for part in
                 (candidate_root, *candidate_root.parents))
         and (root / ".git").exists()
         and (root / "f139" / "local_controller.py").is_file(),
         "CLEAN_DISTINCT_CANDIDATE_CHECKOUT_REQUIRED")
    def git(*argv):
        proc = subprocess.run(["git", "-C", str(root), *argv], check=False,
                              capture_output=True, timeout=20)
        need(proc.returncode == 0 and not proc.stderr.strip(),
             "CANDIDATE_GIT_READ_FAILED")
        return proc.stdout.decode("ascii").strip()
    need(git("rev-parse", "HEAD") == target
         and git("status", "--porcelain", "--untracked-files=all") == "",
         "CANDIDATE_SHA_OR_DIRTY_TREE")
    exe = shutil.which("powershell.exe")
    need(exe is not None, "NATIVE_POWERSHELL_UNAVAILABLE")
    env = dict(os.environ, F139_EXPECTED_ORIGINAL_DATABASE=str(db_path.resolve()),
               F139_EXPECTED_CANDIDATE_ROOT=str(root),
               F139_EXPECTED_V40_SOURCE=source.FROM_V40,
               F139_CANDIDATE_PID=str(os.getpid()))
    check = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
        check=False, capture_output=True, stdin=subprocess.DEVNULL,
        env=env, timeout=30)
    need(check.returncode == 0
         and check.stdout.strip() ==
             b"F139_V41_OLD_TASK_DISABLED_STAGED_CANDIDATE=PASS",
         "TASK_SID_ROOT_QUIESCENCE_DRIFT")
    return True

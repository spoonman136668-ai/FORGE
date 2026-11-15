"""Single-pass independent read-only original-owner task predicate snapshot.

Only two bounded masks or a fixed negative status leave the original Windows
host. No paths, SID, command lines, SQLite bytes, raw stderr/stdout or process
details are printed. Does NOT replace original acceptance or change its guard.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from f139.local_controller import GitHub
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_forward_owner_profile as original

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
ISSUE = 807
PREV_COMMENT = 6892011132
PREV_RUN = 43696957491
PREV_SHA = "5368464e6232cb503678353040eb88d302a40f7f"
PREV_BODY = ("F139-V38-ORIGINAL-TASK-SNAPSHOT-V3 " +
             PREV_SHA + " 6891778093")
PREFIX = "F139-V38-ORIGINAL-TASK-SNAPSHOT-V4 "
LABEL = "F139_V38_TASK_SNAPSHOT="
SHA = re.compile(r"[0-9a-f]{40}\Z")
DECIMAL = re.compile(r"[1-9][0-9]*\Z")
MASK = re.compile(r"F([0-9A-F]{4})-U([0-9A-F]{4})\Z")
MAX_MASK = (1 << 11) - 1
LITERALS = frozenset({"TASK_LOOKUP_FAILED", "POWERSHELL_PROTOCOL_FAILED",
                      "POWERSHELL_UNAVAILABLE", "POWERSHELL_TIMEOUT",
                      "POWERSHELL_SPAWN_FAILED", "POWERSHELL_EXIT_FAILED",
                      "POWERSHELL_OUTPUT_INVALID", "POWERSHELL_INTERNAL_ERROR",
                      "AUTH_INVARIANT", "AUTH_PROVIDER",
                      "PATH_UNAVAILABLE", "POSTCHECK_DENIED", "UNCLASSIFIED"})


class SnapshotDenied(ValueError):
    pass


def need(ok):
    if not ok:
        raise SnapshotDenied("F139_V38_SNAPSHOT_INVARIANT_FAILED")


def authenticate(get, env, event):
    """New exact owner intent, prior classified run and two-lane policy."""
    need(callable(get) and type(env) is dict and type(event) is dict)
    target = env.get("GITHUB_SHA")
    need(type(target) is str and SHA.fullmatch(target) is not None
         and target != PREV_SHA
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and DECIMAL.fullmatch(env["GITHUB_RUN_ID"]) is not None
         and not env.get("OPENAI_API_KEY"))
    issue, sender, comment = (event.get(k) for k in
                              ("issue", "sender", "comment"))
    body = PREFIX + target + " " + str(PREV_COMMENT)
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == ISSUE
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > PREV_COMMENT
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == body)
    uri = "repos/" + REPO + "/issues/comments/" + str(comment["id"])
    first, second = get(uri), get(uri)
    for item in (first, second):
        need(type(item) is dict and item.get("id") == comment["id"]
             and item.get("body") == body
             and item.get("author_association") == "OWNER"
             and type(item.get("user")) is dict
             and item["user"].get("login") == OWNER
             and item.get("issue_url") ==
                  "https://api.github.com/repos/" + REPO + "/issues/807"
             and type(item.get("created_at")) is str)
    need(first["created_at"] == second["created_at"])
    prior = get("repos/" + REPO + "/issues/comments/" + str(PREV_COMMENT))
    need(type(prior) is dict and prior.get("id") == PREV_COMMENT
         and prior.get("body") == PREV_BODY
         and prior.get("author_association") == "OWNER"
         and type(prior.get("user")) is dict
         and prior["user"].get("login") == OWNER
         and type(prior.get("created_at")) is str
         and prior["created_at"] < first["created_at"])
    done = get("repos/" + REPO + "/actions/runs/" + str(PREV_RUN))
    need(type(done) is dict and done.get("id") == PREV_RUN
         and done.get("head_sha") == PREV_SHA
         and done.get("run_attempt") == 1
         and done.get("event") == "issue_comment"
         and done.get("status") == "completed"
         and done.get("conclusion") == "success"
         and type(done.get("actor")) is dict
         and done["actor"].get("login") == OWNER)
    # Predecessor V3 exited with a sanitized PowerShell nonzero code.
    # It completed exactly one original Windows read-only snapshot job.
    prior_jobs = get("repos/" + REPO + "/actions/runs/" + str(PREV_RUN) +
                     "/jobs?per_page=100")
    need(type(prior_jobs) is dict and prior_jobs.get("total_count") == 1
         and type(prior_jobs.get("jobs")) is list
         and len(prior_jobs["jobs"]) == 1
         and prior_jobs["jobs"][0].get("name") ==
             "original-owner-readonly-task-snapshot"
         and prior_jobs["jobs"][0].get("status") == "completed"
         and prior_jobs["jobs"][0].get("conclusion") == "success")
    main = get("repos/" + REPO + "/branches/main")
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == target)
    issue_doc = get("repos/" + REPO + "/issues/807")
    need(type(issue_doc) is dict and issue_doc.get("state") == "open"
         and type(issue_doc.get("body")) is str)
    policy = json.loads(issue_doc["body"], object_pairs_hook=decode_unique)
    need(type(policy) is dict
         and policy.get("lanes") == ["Wingless", "Yggdrasil"]
         and policy.get("scientific_first_use") is False
         and policy.get("new_controller") is False
         and policy.get("new_scheduler") is False
         and policy.get("new_queue") is False
         and policy.get("paid_model_calls") == 0)
    return target


# Pure GET-only task registry/CIM, root Git identity and path-existence checks.
# Each bit is a predicate (0=SID,1=counts,2=executable,3=args,4=db,
# 5=wrapper,6=files,7=git source,8=git clean,9=disabled,10=quiescence).
# F is observed failure, U is unverified due to prerequisite/GET failure.
# A bit cannot be in both masks. No actual value is emitted.
SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$fail = 0
$unknown = 0
function Bad([int]$n) { $script:fail = $script:fail -bor (1 -shl $n) }
function Unk([int]$n) { $script:unknown = $script:unknown -bor (1 -shl $n) }
try {
  $taskMatches = @(Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop)
} catch {
  Write-Output 'TASK_LOOKUP_FAILED'
  exit 0
}
if($taskMatches.Count -ne 1) { Write-Output 'TASK_LOOKUP_FAILED'; exit 0 }
$task = $taskMatches[0]
try {
  $current=[Security.Principal.WindowsIdentity]::GetCurrent()
  $principalId=[string]$task.Principal.UserId
  $sid=''
  try { $sid=(New-Object -TypeName Security.Principal.NTAccount -ArgumentList $principalId).Translate([Security.Principal.SecurityIdentifier]).Value } catch {}
  if(-not ($principalId -ieq $current.Name -or $sid -ceq $current.User.Value)) { Bad 0 }
} catch { Unk 0 }
try {
  $actions=@($task.Actions)
  $triggers=@($task.Triggers)
  if($actions.Count -ne 1 -or $triggers.Count -ne 3) { Bad 1 }
} catch { Unk 1; $actions=@() }
$a=$null
if($actions.Count -eq 1){$a=$actions[0]}
if($null -eq $a){Unk 2; Unk 3; Unk 4; Unk 5; Unk 6; Unk 7; Unk 8}
else {
  try { if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe') { Bad 2 } }
  catch { Unk 2 }
  function Arg([string]$key) {
    $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
    if($m.Success) { return [string]$m.Groups[1].Value }
    return $null
  }
  try {
    $db=Arg 'Database'
    $root=Arg 'RepositoryRoot'
    $exe=Arg 'PythonExe'
    $wrapper=Arg 'File'
    if(-not $db -or -not $root -or -not $exe -or -not $wrapper) { Bad 3 }
  } catch { Bad 3; $db=$null; $root=$null; $exe=$null; $wrapper=$null }
  if(-not $db) { Unk 4 } else {
    try {
      if([IO.Path]::GetFullPath($db) -ine
         [IO.Path]::GetFullPath($env:F139_V38_SNAPSHOT_EXPECTED_DB)) { Bad 4 }
    } catch { Unk 4 }
  }
  if(-not $wrapper){Unk 5} else {
    try {if([IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1'){Bad 5}}
    catch { Unk 5 }
  }
  if(-not $root -or -not $exe -or -not $wrapper) { Unk 6 }
  else {
    try {
      if(-not (Test-Path -LiteralPath $root -PathType Container) -or
         -not (Test-Path -LiteralPath $exe -PathType Leaf) -or
         -not (Test-Path -LiteralPath $wrapper -PathType Leaf)) { Bad 6 }
    } catch { Unk 6 }
  }
  if(-not $root){Unk 7; Unk 8}
  else {
    try {
      $now=(& git -C $root rev-parse HEAD 2>$null | Out-String).Trim()
      $allow=@($env:F139_V38_SNAPSHOT_SOURCES -split ';')
      if($LASTEXITCODE -ne 0 -or -not($allow -ccontains $now) -or
         $allow.Count -ne 2){Bad 7}
    } catch { Unk 7 }
    try {
      $dirty=@(& git -C $root status --porcelain --untracked-files=all 2>$null)
      if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){Bad 8}
    } catch {Unk 8}
  }
}
try {
  if([string]$task.State -cne 'Disabled' -or
     $task.Settings.Enabled -ne $false){Bad 9}
} catch {Unk 9}
try {
  $procs=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {
      $_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($env:F139_V38_SNAPSHOT_EXPECTED_DB)})
  if($procs.Count -ne 0) {Bad 10}
} catch {Unk 10}
$mask = $fail -band 2047
$unverified = $unknown -band 2047
if(($mask -band $unverified) -ne 0) {
  Write-Output 'POWERSHELL_PROTOCOL_FAILED'
  exit 0
}
Write-Output ('F{0:X4}-U{1:X4}' -f $mask,$unverified)
'''


def parse_receipt(raw: bytes, code: int) -> str:
    """Validate the only two PowerShell output shapes without retaining raw."""
    if type(code) is not int or code != 0:
        return "POWERSHELL_EXIT_FAILED"
    if type(raw) is not bytes or len(raw) > 100:
        return "POWERSHELL_OUTPUT_INVALID"
    try:
        token = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        return "POWERSHELL_OUTPUT_INVALID"
    if token in ("TASK_LOOKUP_FAILED", "POWERSHELL_PROTOCOL_FAILED"):
        return token
    m = MASK.fullmatch(token)
    if m is None:
        return "POWERSHELL_OUTPUT_INVALID"
    failed, unknown = (int(m.group(i), 16) for i in (1, 2))
    if (failed & unknown or failed > MAX_MASK or unknown > MAX_MASK):
        return "POWERSHELL_OUTPUT_INVALID"
    return token


def powershell_once(executable: str, env: dict, *, runner=subprocess.run):
    """Classify one read-only PowerShell subprocess; never log raw evidence."""
    try:
        result = runner(
            [executable, "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, env=env, timeout=30, check=False)
        return parse_receipt(result.stdout, result.returncode)
    except subprocess.TimeoutExpired:
        return "POWERSHELL_TIMEOUT"
    except OSError:
        return "POWERSHELL_SPAWN_FAILED"
    except Exception:
        return "POWERSHELL_INTERNAL_ERROR"


def probe(db_path: Path, *, runner=subprocess.run):
    """One read-only PowerShell subprocess. Never retain or display raw output."""
    if (os.name != "nt" or not isinstance(db_path, Path)
            or not db_path.is_absolute() or db_path.name != "state.sqlite"
            or not db_path.is_file() or db_path.is_symlink()):
        return "PATH_UNAVAILABLE"
    powershell = shutil.which("powershell.exe")
    if type(powershell) is not str or not powershell:
        return "POWERSHELL_UNAVAILABLE"
    env = {**os.environ,
           "F139_V38_SNAPSHOT_EXPECTED_DB": str(db_path.resolve()),
           "F139_V38_SNAPSHOT_SOURCES": ";".join(sorted(
               original.ALLOWED_ACTION_SOURCE_SHAS))}
    return powershell_once(powershell, env, runner=runner)

def run(env, event, get, *, task_probe=probe):
    if sys.platform != "win32" or os.name != "nt":
        return "AUTH_INVARIANT"
    try:
        target = authenticate(get, env, event)
    except SnapshotDenied:
        return "AUTH_INVARIANT"
    except Exception:
        return "AUTH_PROVIDER"
    try:
        local = env.get("LOCALAPPDATA")
        if type(local) is not str or not Path(local).is_absolute():
            result = "PATH_UNAVAILABLE"
        else:
            db = Path(local) / "FORGE-F139" / "state.sqlite"
            result = task_probe(db)
    except Exception:
        result = "POWERSHELL_INTERNAL_ERROR"
    try:
        after = get("repos/" + REPO + "/branches/main")
        if (type(after) is not dict
                or after.get("commit", {}).get("sha") != target):
            return "POSTCHECK_DENIED"
    except Exception:
        return "POSTCHECK_DENIED"
    return result if result in LITERALS or MASK.fullmatch(result) else "UNCLASSIFIED"


def main():
    try:
        path = os.environ.get("GITHUB_EVENT_PATH")
        if type(path) is not str or not Path(path).is_file():
            result = "AUTH_INVARIANT"
        else:
            try:
                event = json.loads(Path(path).read_text("utf-8"),
                                   object_pairs_hook=decode_unique)
            except Exception:
                event = {}
            result = run(dict(os.environ), event, GitHub().native_repo_get)
    except Exception:
        result = "UNCLASSIFIED"
    if result not in LITERALS and MASK.fullmatch(result) is None:
        result = "UNCLASSIFIED"
    print(LABEL + result)
    return 1 if result in ("AUTH_INVARIANT", "AUTH_PROVIDER",
                           "POSTCHECK_DENIED", "UNCLASSIFIED") else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only original Windows owner identity and database preflight for H53.

No task modifications, controller calls, dispatch or database writes.
"""
from __future__ import annotations
import json
import os
import pathlib
import re
import subprocess
from f139 import h53_audit_guards as guard

def run(args):
    p=subprocess.run(args,capture_output=True,text=True,check=True,timeout=45)
    return p.stdout.strip()

def observe_owner():
    ps=r"""
$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$info=Get-ScheduledTaskInfo -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[string]$task.Principal.UserId
$sid=''
try {$sid=(New-Object Security.Principal.NTAccount($principal)).Translate([Security.Principal.SecurityIdentifier]).Value} catch {}
[pscustomobject]@{
 task_name=$task.TaskName;task_state=[string]$task.State
 task_sid=$sid;runner_sid=$who.User.Value
 actions=@($task.Actions).Count;triggers=@($task.Triggers).Count
 arguments=[string]$task.Actions[0].Arguments
 last_result=[int64]$info.LastTaskResult
} | ConvertTo-Json -Compress
"""
    return json.loads(run(["pwsh","-NoProfile","-NonInteractive","-Command",ps]))

def field(args, name):
    m=re.search(r"(?:^|\s)-"+re.escape(name)+r'\s+"([^"]+)"',args,re.I)
    guard.demand(m is not None,"TASK_ARGUMENT_"+name.upper())
    return m.group(1)

def verify_owner(o, *, localappdata, installed_sha, installed_dirty):
    args=o["arguments"]
    poll=re.search(r"(?:^|\s)-PollSeconds\s+(\d+)(?:\s|$)",args,re.I)
    db=field(args,"Database")
    expected=str(pathlib.Path(localappdata)/"FORGE-F139"/"state.sqlite")
    guard.owner_guard(task_name=o["task_name"],task_state=o["task_state"],
                      task_sid=o["task_sid"],runner_sid=o["runner_sid"],
                      actions=o["actions"],triggers=o["triggers"],
                      poll_seconds=int(poll.group(1)) if poll else -1,
                      db_path=db,expected_db=expected)
    guard.demand(pathlib.Path(db).is_file(),"ORIGINAL_DATABASE_MISSING")
    guard.demand(pathlib.Path(field(args,"PythonExe")).is_file(),"PYTHON_MISSING")
    guard.demand(pathlib.Path(field(args,"File")).name=="Run-FORGE-F139.ps1","WRAPPER_DRIFT")
    guard.demand(installed_sha==guard.SOURCE and not installed_dirty,"INSTALLED_SOURCE_DRIFT")
    return {"database":db,"repository_root":field(args,"RepositoryRoot"),
            "source_sha":installed_sha,"last_task_result":o["last_result"]}

def inspect_original():
    guard.demand(os.name=="nt","NOT_WINDOWS")
    guard.demand(os.environ.get("RUNNER_NAME")==guard.RUNNER,"WRONG_RUNNER")
    o=observe_owner()
    root=field(o["arguments"],"RepositoryRoot")
    sha=run(["git","-C",root,"rev-parse","HEAD"])
    dirty=run(["git","-C",root,"status","--porcelain","--untracked-files=all"])
    return verify_owner(o,localappdata=os.environ["LOCALAPPDATA"],
                        installed_sha=sha,installed_dirty=bool(dirty))

if __name__=="__main__":
    print(json.dumps(inspect_original(),sort_keys=True))

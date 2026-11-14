"""One original-owner V41 activation only; source-bound, fail-closed and no replay.

This operational script lives outside protected main. It invokes only the
existing original owner and its pinned installed source. No extra controller,
task, scheduler, scientific first-use or cross-project credentials.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
import base64

REPO = "spoonman136668-ai/FORGE"
TARGET = "1a40fe4e3ec6e93a1631d59863b95e90981d734e"
BRANCH = "operation/f139-v41-native-activation-once-20261113"
PRE_SEQ = 1828
PRE_HEAD = "104bfdfdbae30d4ec80a9d8f7d0d440cd5b15ced8995709383b66db761a2ceb2"
POST_SEQ = 1829
POST_HEAD = "55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8"
COMMENT_ID = 6868291097
EXPECTED_BODY = "F139-V41-NATIVE-ACTIVATION-OWNER-INTENT {\"activation_once\":true,\"copy_rehearsal_commit_sha\":\"c2fe773c431c484fe0482534afa99d9e6e5f79ef\",\"copy_rehearsal_run_id\":43532501640,\"development_only\":true,\"expected_post_activation_head_sha256\":\"55ded016778c8430bd4f6e3290972be1c5c5c796cbcb2a2ad38046283f78e3f8\",\"expected_post_activation_seq\":1829,\"expected_pre_activation_head_sha256\":\"104bfdfdbae30d4ec80a9d8f7d0d440cd5b15ced8995709383b66db761a2ceb2\",\"expected_pre_activation_seq\":1828,\"hybrid_admission\":false,\"new_controller\":false,\"new_queue\":false,\"new_scheduler\":false,\"no_replay\":true,\"original_install_comment_id\":6867798369,\"original_install_run_id\":43529353640,\"owner_comment_id\":6868291097,\"owner_policy_issue_number\":807,\"paid_api_calls\":0,\"pause_resume_existing_original_task\":true,\"schema\":\"forge.f139.v41.original-native-activation-owner-intent.v1\",\"scientific_first_use\":false,\"source_sha\":\"1a40fe4e3ec6e93a1631d59863b95e90981d734e\"}"
OWNER_TASK = "FORGE-F139-UnifiedController"

class OwnerDenied(RuntimeError):
    pass

def need(ok, code):
    if not ok:
        raise OwnerDenied("F139_V41_NATIVE_ACTIVATION_" + code)

def command(argv, *, cwd=None, timeout=40, env=None):
    p=subprocess.run(argv,cwd=cwd,env=env,check=False,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     stdin=subprocess.DEVNULL,timeout=timeout)
    need(p.returncode==0, "COMMAND_FAILED_" + re.sub("[^A-Z0-9_]", "_", argv[0].split("\\")[-1].upper())[:32])
    return p.stdout.decode("utf-8","replace").strip()

def github(route):
    return json.loads(command(["gh","api",route],timeout=30))

def powershell(src):
    encoded=base64.b64encode(src.encode("utf-16le")).decode("ascii")
    return command(["powershell.exe","-NoProfile","-NonInteractive",
                    "-EncodedCommand",encoded],timeout=55)

def task_state():
    script=r"""
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[string]$t.Principal.UserId
$sid=''
if($principal -match '^S-1-'){$sid=$principal}else{
try{$sid=(New-Object Security.Principal.NTAccount($principal)).Translate(
[Security.Principal.SecurityIdentifier]).Value}catch{}
}
$arg=[string]$t.Actions[0].Arguments
function Arg([string]$n){
$m=[regex]::Match($arg,'(?i)(?:^|\s)-'+$n+'\s+"([^"]+)"')
if($m.Success){return $m.Groups[1].Value}
return ''
}
$db=Arg 'Database'
$children=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop |
Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
$db -and $_.CommandLine.Contains($db)})
[ordered]@{
 state=[string]$t.State
 enabled=[bool]$t.Settings.Enabled
 principal_match=($principal -ieq $identity.Name -or $sid -ceq $identity.User.Value)
 action_count=@($t.Actions).Count
 trigger_count=@($t.Triggers).Count
 execute=[string]$t.Actions[0].Execute
 python=Arg 'PythonExe'
 root=Arg 'RepositoryRoot'
 database=$db
 wrapper=Arg 'File'
 poll_seconds=($arg -match '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)')
 process_count=$children.Count
} | ConvertTo-Json -Compress
"""
    return json.loads(powershell(script))

def pause():
    powershell(r"""
$ErrorActionPreference='Stop'
$n='FORGE-F139-UnifiedController'
$t=Get-ScheduledTask -TaskName $n -ErrorAction Stop
if([string]$t.State -cne 'Running' -or -not $t.Settings.Enabled){throw 'F139_V41_OWNER_NOT_RUNNING'}
Disable-ScheduledTask -TaskName $n -ErrorAction Stop | Out-Null
Stop-ScheduledTask -TaskName $n -ErrorAction Stop | Out-Null
""")
    for _ in range(45):
        t=task_state()
        if t["state"]=="Disabled" and t["process_count"]==0:
            return
        time.sleep(1)
    raise OwnerDenied("F139_V41_NATIVE_ACTIVATION_OWNER_NOT_QUIESCENT")

def resume():
    powershell(r"""
$ErrorActionPreference='Stop'
$n='FORGE-F139-UnifiedController'
$t=Get-ScheduledTask -TaskName $n -ErrorAction Stop
if([string]$t.State -ceq 'Disabled'){
  Enable-ScheduledTask -TaskName $n -ErrorAction Stop | Out-Null
}
$t=Get-ScheduledTask -TaskName $n -ErrorAction Stop
if([string]$t.State -cne 'Running'){
  Start-ScheduledTask -TaskName $n -ErrorAction Stop | Out-Null
}
""")
    for _ in range(25):
        t=task_state()
        if t["enabled"] and t["state"]=="Running" and t["process_count"]==1:
            return t
        time.sleep(1)
    raise OwnerDenied("F139_V41_NATIVE_ACTIVATION_OWNER_RESUME_UNVERIFIED")

def path_id(p):
    return os.path.normcase(os.path.realpath(os.fspath(p)))

def check_owner_scope():
    env=os.environ
    need(env.get("GITHUB_REPOSITORY")==REPO
         and env.get("GITHUB_REF")=="refs/heads/"+BRANCH
         and env.get("GITHUB_EVENT_NAME")=="push"
         and env.get("GITHUB_ACTOR")=="spoonman136668-ai"
         and env.get("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
         and env.get("GITHUB_RUN_ATTEMPT")=="1"
         and not env.get("OPENAI_API_KEY"), "RUNNER_EVENT_OR_PAID_API_DENIED")
    need(github("repos/"+REPO+"/git/ref/heads/main")["object"]["sha"]==TARGET,
         "PROTECTED_MAIN_MOVED")
    comment=github("repos/"+REPO+"/issues/comments/"+str(COMMENT_ID))
    need(comment.get("id")==COMMENT_ID
         and comment.get("user",{}).get("login")=="spoonman136668-ai"
         and comment.get("author_association")=="OWNER"
         and comment.get("issue_url")=="https://api.github.com/repos/"+REPO+"/issues/807"
         and comment.get("body")==EXPECTED_BODY, "OWNER_INTENT_MISSING_OR_CHANGED")
    for run_id,source in (
        (43529353640,TARGET),
        (43532501640,"c2fe773c431c484fe0482534afa99d9e6e5f79ef"),
    ):
        run=github("repos/"+REPO+"/actions/runs/"+str(run_id))
        need(run.get("head_sha")==source and run.get("status")=="completed"
             and run.get("conclusion")=="success" and run.get("run_attempt")==1
             and run.get("actor",{}).get("login")=="spoonman136668-ai",
             "PINNED_INSTALL_OR_REHEARSAL_UNQUALIFIED")
    issue=github("repos/"+REPO+"/issues/807")
    need(issue.get("state")=="open" and issue.get("user",{}).get("login")=="spoonman136668-ai",
         "OWNER_POLICY_ISSUE_IDENTITY")
    policy=issue.get("body")
    doc=json.loads(policy)
    need(doc.get("schema")=="forge.f139.native-autonomy-feed-owner-policy.v1"
         and doc.get("enabled") is True and doc.get("source_sha")==TARGET
         and doc.get("lanes")==["Wingless","Yggdrasil"]
         and doc.get("scientific_first_use") is False
         and doc.get("paid_model_calls")==0
         and doc.get("new_controller") is False and doc.get("new_scheduler") is False
         and doc.get("new_queue") is False,
         "DEVELOPMENT_OWNER_POLICY_DRIFT")
    return hashlib.sha256(policy.encode("utf-8")).hexdigest()

def original_stage():
    app=os.environ.get("LOCALAPPDATA","")
    need(bool(app), "LOCALAPPDATA_MISSING")
    data=Path(app)/"FORGE-F139"
    db=data/"state.sqlite"
    stage=data/"release-candidates"/TARGET
    need(db.is_file() and stage.is_dir() and not db.is_symlink()
         and not data.is_symlink() and not stage.is_symlink(),
         "OWNER_DATABASE_OR_STAGED_SOURCE_MISSING")
    need(command(["git","-C",str(stage),"rev-parse","HEAD"])==TARGET,
         "STAGED_SOURCE_DRIFT")
    need(command(["git","-C",str(stage),"status","--porcelain",
                  "--untracked-files=all"])=="", "STAGED_SOURCE_NOT_CLEAN")
    sys.path.insert(0,str(stage))
    return data,db,stage

def read_ledger(db):
    from f139.local_controller import Database
    from f139.nci04_owner_ledger import verify_native_activation
    with closing(Database.open_readonly(db)) as handle:
        m=handle.meta()
        return {"source_sha":m["source_sha"],"seq":m["head_seq"],
                "sha":m["head_hash"],"enabled":m["enabled"],
                "legacy_suspended":m["legacy_suspended"],
                "native":verify_native_activation(handle),
                "ready":handle.ready() is not None,
                "active":len(handle.actives()),
                "quarantined":handle.conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0]}

def before_expected(report):
    need(report["source_sha"]==TARGET and report["seq"]==PRE_SEQ
         and report["sha"]==PRE_HEAD and report["enabled"]==1
         and report["legacy_suspended"]==1 and report["native"] is False
         and report["active"]==0 and not report["ready"]
         and report["quarantined"]==56, "PRE_ACTIVATION_LEDGER_NOT_FROZEN")

def after_expected(report):
    return (report["source_sha"]==TARGET and report["seq"]==POST_SEQ
            and report["sha"]==POST_HEAD and report["native"] is True
            and report["enabled"]==1 and report["legacy_suspended"]==1)

def validate_task(t,db,stage):
    need(t["state"]=="Running" and t["enabled"] is True
         and t["process_count"]==1 and t["principal_match"] is True
         and t["action_count"]==1 and t["trigger_count"]==3
         and Path(t["execute"]).name.lower()=="powershell.exe"
         and Path(t["wrapper"]).name=="Run-FORGE-F139.ps1"
         and t["poll_seconds"] is True
         and path_id(t["database"])==path_id(db)
         and path_id(t["root"])==path_id(stage)
         and Path(t["python"]).is_file(), "EXISTING_ORIGINAL_TASK_OR_PROCESS_DRIFT")
    return Path(t["python"])

def stage_cold_backup(data,db,run_id):
    from f139.local_controller import Database
    from f139.nci04_v41_cold_copy_verifier import (
        required_negative_custody,copy_negative_custody)
    folder=data/("f139-v41-native-activation-before-"+str(run_id))
    folder.mkdir(parents=False,exist_ok=False)
    backup=folder/"state.sqlite"
    with closing(Database.open_readonly(db)) as origin:
        m=origin.meta()
        need(m["source_sha"]==TARGET and m["head_seq"]==PRE_SEQ
             and m["head_hash"]==PRE_HEAD, "BACKUP_SOURCE_MOVED")
        negatives=required_negative_custody(origin)
        copy_negative_custody(data,folder,negatives,copy_files=True)
    source_uri=db.resolve().as_uri()+"?mode=ro"
    with closing(sqlite3.connect(source_uri,uri=True,isolation_level=None,timeout=15)) as src:
        src.execute("PRAGMA query_only=ON")
        with closing(sqlite3.connect(backup)) as dest:
            src.backup(dest)
    with closing(Database(backup)) as copy:
        m=copy.meta()
        need(m["source_sha"]==TARGET and m["head_seq"]==PRE_SEQ
             and m["head_hash"]==PRE_HEAD, "COLD_BACKUP_HEAD_CHANGED")
    sha=hashlib.sha256(backup.read_bytes()).hexdigest()
    manifest={
      "schema":"forge.f139.v41.owner-native-activation-preimage.v1",
      "target_source_sha":TARGET,"owner_comment_id":COMMENT_ID,
      "original_head_seq":PRE_SEQ,"original_head_sha256":PRE_HEAD,
      "sqlite_backup_sha256":sha,
      "negative_evidence_files_sha256":negatives,
      "scientific_first_use":False,"original_database_rollback_authorized":False,
    }
    with (folder/"manifest.sha256.json").open("xb") as f:
        f.write(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode("ascii"))
    need(hashlib.sha256(backup.read_bytes()).hexdigest()==sha,
         "BACKUP_NOT_STABLE")
    return folder,sha

def apply(db,data,stage,python,policy_sha,run_id):
    disabled=False
    try:
        need(check_owner_scope()==policy_sha,"OWNER_POLICY_CHANGED")
        before_expected(read_ledger(db))
        validate_task(task_state(),db,stage)
        pause()
        disabled=True
        before_expected(read_ledger(db))
        folder,backup_sha=stage_cold_backup(data,db,run_id)
        need(check_owner_scope()==policy_sha,"POLICY_OR_SOURCE_DRIFT_AFTER_PAUSE")
        before_expected(read_ledger(db))
        approval={
          "schema":"forge.f139.nci04.owner-native-approval.v1",
          "source_sha":TARGET,
          "expected_event_head_sha256":PRE_HEAD,
          "native_development_approved":True,
          "scientific_first_use":False,
          "create_controller":False,
          "paid_api_calls":0
        }
        from f139.nci04_native_contract import canonical
        approval_path=Path(os.environ["RUNNER_TEMP"])/("f139-v41-native-activation-"+str(run_id)+".json")
        with approval_path.open("xb") as f:f.write(canonical(approval))
        try:
            env=dict(os.environ,PYTHONPATH=str(stage))
            p=subprocess.run(
                [str(python),"-B","-m","f139.local_controller",
                 "--db",str(db),"activate-native","--approval",str(approval_path)],
                cwd=stage,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,timeout=120,check=False)
            print("F139_V41_ACTIVATE_CLI_EXIT="+str(p.returncode),flush=True)
            need(p.returncode==0,"ORIGINAL_NATIVE_ACTIVATION_CLI_DENIED")
        finally:
            approval_path.unlink(missing_ok=True)
        state=read_ledger(db)
        need(after_expected(state),"ACTIVATION_EVENT_NOT_EXACT_COPIED_REHEARSAL")
        need(check_owner_scope()==policy_sha,"POLICY_MOVED_AFTER_ACTIVATION")
        live=resume()
        disabled=False
        print("F139_V41_NATIVE_ORIGINAL_ACTIVATION="+json.dumps({
          "schema":"forge.f139.v41.owner-native-activation-deployment.v1",
          "target_source_sha":TARGET,"owner_comment_id":COMMENT_ID,
          "backup_run_id":run_id,"pre_activation_head_seq":PRE_SEQ,
          "activated_head_seq":POST_SEQ,"activated_head_sha256":POST_HEAD,
          "backup_manifest_path_name":folder.name,
          "backup_sha256":backup_sha,"owner_task_running":True,
          "original_task_reused":True,"native_development_active":True,
          "scientific_first_use":False,"hybrid_admission":False,
          "new_controller":False,"new_scheduler":False,
          "new_queue":False,"paid_api_calls":0
        },sort_keys=True,separators=(",",":")),flush=True)
    except BaseException as err:
        if disabled:
            # Never restore a preactivation copy over a possibly committed ledger.
            # Resume only when the current ledger is provably exact either side.
            try:
                now=read_ledger(db)
                if (now["source_sha"]==TARGET and
                    ((now["seq"]==PRE_SEQ and now["sha"]==PRE_HEAD and not now["native"])
                     or after_expected(now))):
                    resume()
                    print("F139_V41_NATIVE_ACTIVATION_SAFE_EXISTING_TASK_RESUMED=PASS",flush=True)
                else:
                    print("F139_V41_NATIVE_ACTIVATION_AMBIGUOUS_LEDGER_HELD_DISABLED",flush=True)
            except BaseException:
                print("F139_V41_NATIVE_ACTIVATION_RECOVERY_UNVERIFIED_HOLD",flush=True)
        print("F139_V41_NATIVE_ACTIVATION_FAILURE_CLASS="+type(err).__name__,flush=True)
        raise

def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight",action="store_true")
    mode.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    policy_sha=check_owner_scope()
    data,db,stage=original_stage()
    before=read_ledger(db)
    before_expected(before)
    python=validate_task(task_state(),db,stage)
    if args.preflight:
        print("F139_V41_NATIVE_OWNER_PREFLIGHT="+json.dumps({
          "schema":"forge.f139.v41.native-owner-reactivation-preflight.v1",
          "source_sha":TARGET,"head_seq":PRE_SEQ,"head_sha256":PRE_HEAD,
          "owner_intent_comment_id":COMMENT_ID,"owner_task_running":True,
          "copy_rehearsal_run_id":43532501640,"native_active":False,
          "temp_pause_authorized":True,"original_mutations":0,
          "scientific_first_use":False,"hybrid_admission":False},sort_keys=True),flush=True)
        return
    apply(db,data,stage,python,policy_sha,int(os.environ["GITHUB_RUN_ID"]))

if __name__=="__main__":
    try:
        main()
    except (OwnerDenied,ValueError,RuntimeError,OSError,sqlite3.DatabaseError,
            subprocess.TimeoutExpired,KeyError,TypeError,AssertionError) as err:
        print("F139_V41_NATIVE_ACTIVATION_FAIL_CLOSED="+type(err).__name__
              +":"+str(err)[:180],flush=True)
        raise SystemExit(1)

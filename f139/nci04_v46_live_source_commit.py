"""Owner-authenticated V46 original event1836 source-commit-and-HOLD primitive.

The original task must be separately quiesced by the guarded V46 Windows
wrapper. This module changes ONLY original SQLite inside its kernel mutex.
The wrapper alone owns policy and task activation; uncertain outcomes HOLD.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v42_owner_source_readiness as v42
from f139 import nci04_v43_event1835_cold as cold
from f139 import nci04_v43_event1836_successor as successor
from f139 import nci04_v44_event1836_copy_rehearsal as v44
from f139 import nci04_v45_original_rehearsal_gate as v45
from f139 import nci04_release_pin_continuity as pin

SCHEMA = "forge.f139.v46.original-event1836-source-commit-hold.v1"
PREFIX = "F139-V46-LIVE-INSTALL "
TARGET = v44.RELEASE_SOURCE
EXPECTED_V44_COPY_HEAD = "4962c030cb2aae19ab16832260b39d941d40128b08176b3cc2875592d6123c10"
EXPECTED_V44_PROOF = "70474d338d4c379b42362ca3cd24d7d02a0e9ac82b4fb8b018454e7c1822112c"
ORIGINAL_TASK_MARKER = b"F139_V46_ORIGINAL_DISABLED_OWNER=PASS"


class OriginalV46Denied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalV46Denied("F139_V46_" + reason)


def request(get, env, event):
    """Authenticate a NEW explicit issue #807 release, not V44's copy permit."""
    need(type(env) is dict and type(event) is dict and callable(get)
         and sys.platform == "win32" and os.name == "nt"
         and env.get("GITHUB_REPOSITORY") == v42.REPO
         and env.get("GITHUB_ACTOR") == v42.OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and not env.get("OPENAI_API_KEY")
         and type(env.get("GITHUB_SHA")) is str
         and v42.SHA40.fullmatch(env["GITHUB_SHA"]) is not None
         and type(env.get("GITHUB_RUN_ID")) is str
         and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"]) is not None,
         "EXACT_ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED")
    issue, comment, sender = (event.get(k) for k in
                              ("issue", "comment", "sender"))
    body = PREFIX + env["GITHUB_SHA"] + " " + TARGET + " " + str(v45.V44_COMMENT)
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and issue.get("user", {}).get("login") == v42.OWNER
         and type(sender) is dict and sender.get("login") == v42.OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > v45.V44_COMMENT
         and comment.get("user", {}).get("login") == v42.OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == body
         and type(comment.get("created_at")) is str,
         "FRESH_EXACT_OWNER_RELEASE_COMMENT_REQUIRED")
    base = "repos/" + v42.REPO + "/"
    path = base + "issues/comments/" + str(comment["id"])
    prior = base + "issues/comments/" + str(v45.V44_COMMENT)
    first = get(path)
    earlier = get(prior)
    need(type(first) is dict and first.get("id") == comment["id"]
         and first.get("body") == body
         and first.get("user", {}).get("login") == v42.OWNER
         and first.get("author_association") == "OWNER"
         and first.get("issue_url") ==
             "https://api.github.com/repos/" + v42.REPO + "/issues/807"
         and first.get("created_at") == comment["created_at"]
         and first.get("updated_at") == comment.get("updated_at")
         and type(earlier) is dict
         and earlier.get("id") == v45.V44_COMMENT
         and earlier.get("body") == "F139-V44-COPY-REHEARSAL " +
             v45.V44_MAIN + " " + TARGET + " 6916414055"
         and earlier.get("created_at") < comment["created_at"],
         "ORIGINAL_GITHUB_RELEASE_PROVENANCE_REQUIRED")
    source = v45.qualify(get, main_sha=env["GITHUB_SHA"])
    ci = v42.release_source(get, env["GITHUB_SHA"])
    # A protected exact-source worker branch is required by the EXISTING
    # deployed_release_continuity check after the live source is activated.
    # A source-only start without this ref would remain dispatch-blocked.
    # NEVER create the ref here: creating it triggers legacy V40 workflow
    # jobs and needs an isolated owner release, not implicit CI authority.
    worker_name = pin.release_worker_branch(TARGET)
    worker_route = base + "branches/" + worker_name
    worker = get(worker_route)
    need(type(worker) is dict and
         worker.get("name") == worker_name and
         worker.get("protected") is True and
         worker.get("commit", {}).get("sha") == TARGET and
         pin.verify_release_worker_branch(get, TARGET) == worker_name and
         get(worker_route) == worker,
         "EXACT_PROTECTED_WORKER_RELEASE_REF_REQUIRED")
    ancestry = get(base + "compare/" + TARGET + "..." +
                   env["GITHUB_SHA"] + "?per_page=1&page=2")
    need(type(ancestry) is dict
         and ancestry.get("status") == "ahead"
         and ancestry.get("behind_by") == 0
         and ancestry.get("merge_base_commit", {}).get("sha") == TARGET
         and source["v44_original_job_status"] == "success"
         and ci["main_qualification_job_count"] == 8
         and get(path) == first, "RELEASE_OR_OWNER_INTENT_CHANGED")
    return {
        "workflow_sha": env["GITHUB_SHA"],
        "comment_id": comment["id"],
        "event_run_id": int(env["GITHUB_RUN_ID"]),
        "main_regression_run_id": ci["main_qualification_run_id"],
        "v44_run_id": v45.V44_RUN,
    }


def canonical_db(path, env):
    root = env.get("LOCALAPPDATA")
    need(type(root) is str and Path(root).is_absolute()
         and isinstance(path, Path) and path.is_absolute()
         and path.is_file() and not path.is_symlink()
         and not getattr(path, "is_junction", lambda: False)()
         and path.resolve() ==
         (Path(root) / "FORGE-F139" / "state.sqlite").resolve(),
         "EXACT_ORIGINAL_SQLITE_REQUIRED")
    return path


def sealed_original(path):
    """Reverify the actual V43 backup and V44 copied result, without writes."""
    evidence = cold.verify_detached_restore(
        cold.backup_folder(path, v44.BACKUP_RUN),
        target=TARGET, run_id=v44.BACKUP_RUN,
        manifest_sha=v44.BACKUP_MANIFEST)
    need(evidence["backup_manifest_sha256"] == v44.BACKUP_MANIFEST
         and evidence["backup_logical_all_tables_sha256"] == v44.BACKUP_TABLES
         and evidence["independent_detached_restore_verified"] is True,
         "V43_SEALED_COLD_RESTORE_CHANGED")
    copy_root = path.parent / "isolated-v44-event1836-copies"
    copied = copy_root / str(v45.V44_RUN) / "rehearsal.sqlite"
    need(copy_root.is_dir() and not copy_root.is_symlink()
         and not getattr(copy_root, "is_junction", lambda: False)()
         and copied.is_file() and not copied.is_symlink()
         and not getattr(copied, "is_junction", lambda: False)(),
         "V44_AUTHENTIC_ORIGINAL_COPY_REQUIRED")
    with closing(Database.open_readonly(copied)) as check:
        check.verify()
        meta = check.meta()
        row = check.conn.execute(
            "SELECT kind,payload FROM events WHERE seq=?",
            (successor.PREDECESSOR_SEQ + 1,)).fetchone()
        need(meta["source_sha"] == TARGET
             and meta["head_seq"] == successor.PREDECESSOR_SEQ + 1
             and meta["head_hash"] == EXPECTED_V44_COPY_HEAD
             and row is not None
             and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
             and digest(canonical(json.loads(row["payload"]))) ==
                 EXPECTED_V44_PROOF
             and check.conn.total_changes == 0,
             "V44_COPY_OR_PROOF_BYTES_DRIFT")
    return evidence


def disabled_original_task(path, *, runner=None):
    """Independent read-only witness of actual disabled original task/SID."""
    need(sys.platform == "win32" and os.name == "nt",
         "WINDOWS_ONLY")
    powershell = shutil.which("powershell.exe")
    need(type(powershell) is str and powershell,
         "WINDOWS_POWERSHELL_REQUIRED")
    script = r'''
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try { $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value } catch {}
if(-not([string]$t.Principal.UserId -ieq $who.Name -or $sid -ceq $who.User.Value)){exit 41}
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
$py=Arg 'PythonExe'
$wrapper=Arg 'File'
$expected=Join-Path $env:LOCALAPPDATA 'FORGE-F139\release-candidates\af204acc983719b382bc8daf2216ec6733ca3ee7'
if([IO.Path]::GetFullPath($db) -ine [IO.Path]::GetFullPath($env:F139_V46_EXPECTED_DB) -or
   [IO.Path]::GetFullPath($root) -ine [IO.Path]::GetFullPath($expected) -or
   [IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1' -or
   -not(Test-Path -LiteralPath $py -PathType Leaf)){exit 45}
if([string]$t.State -cne 'Disabled' -or $t.Settings.Enabled -ne $false){exit 46}
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
   $_.CommandLine.Contains($env:F139_V46_EXPECTED_DB)})
if($running.Count -ne 0){exit 47}
$installed=(& git -C $root rev-parse HEAD | Out-String).Trim()
$dirty=@(& git -C $root status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $installed -cne 'af204acc983719b382bc8daf2216ec6733ca3ee7' -or
   $dirty.Count -ne 0){exit 48}
Write-Output 'F139_V46_ORIGINAL_DISABLED_OWNER=PASS'
'''
    run = subprocess.run if runner is None else runner
    try:
        actual = run([powershell, "-NoProfile", "-NonInteractive",
                      "-Command", script],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     stdin=subprocess.DEVNULL,
                     env={**os.environ,"F139_V46_EXPECTED_DB":str(path)},
                     timeout=25,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise OriginalV46Denied("F139_V46_ORIGINAL_TASK_WITNESS_FAILURE") from exc
    need(actual.returncode == 0 and
         actual.stdout.strip() == ORIGINAL_TASK_MARKER,
         "ORIGINAL_TASK_NOT_DISABLED_OR_SOURCE_DRIFT")
    return True


def commit_original(path, env, event, api):
    need(type(api) is GitHub, "AUTHENTIC_GITHUB_PROVIDER_REQUIRED")
    get = api.native_repo_get
    req = request(get,env,event)
    path = canonical_db(path,env)
    held = lambda: disabled_original_task(path)
    release = lambda: request(get,env,event) == req
    need(held() and release(), "OWNER_HOLD_OR_RELEASE_MISSING")
    evidence = sealed_original(path)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as original:
            original.verify()
            before = original.meta().copy()
            need(before["source_sha"] == v42.BEFORE
                 and before["head_seq"] == successor.PREDECESSOR_SEQ
                 and before["head_hash"] == successor.PREDECESSOR_SHA
                 and before["enabled"] == 1
                 and before["legacy_suspended"] == 1
                 and original.ready() is None and not original.actives()
                 and original.conn.total_changes == 0,
                 "EXACT_ORIGINAL_EVENT1835_NOT_QUIESCENT")
            v44_proof = successor.build_proof(
                original,target=TARGET,owner_event_id=v45.V44_COMMENT,
                backup_run_id=v44.BACKUP_RUN,
                backup_manifest_sha256=v44.BACKUP_MANIFEST,
                backup_logical_all_tables_sha256=v44.BACKUP_TABLES)
            need(digest(canonical(v44_proof)) == EXPECTED_V44_PROOF,
                 "REAL_ORIGINAL_DOES_NOT_MATCH_V44_REHEARSAL")
            proof = successor.build_proof(
                original,target=TARGET,owner_event_id=req["comment_id"],
                backup_run_id=v44.BACKUP_RUN,
                backup_manifest_sha256=v44.BACKUP_MANIFEST,
                backup_logical_all_tables_sha256=v44.BACKUP_TABLES)
            need(before == original.meta() and
                 original.conn.total_changes == 0,
                 "ORIGINAL_READONLY_PREIMAGE_MUTATED")
        need(held() and release() and sealed_original(path) == evidence,
             "SOURCE_OWNER_OR_SEALED_BACKUP_DRIFT")
        with closing(Database(path)) as writer:
            need(writer.meta() == before,
                 "ORIGINAL_PRECOMMIT_PREIMAGE_DRIFT")
            with writer.transaction():
                need(writer.meta() == before and
                     held() and release(),
                     "PRECOMMIT_AUTHORITY_MOVED")
                expected = successor.build_proof(
                    writer,target=TARGET,owner_event_id=req["comment_id"],
                    backup_run_id=v44.BACKUP_RUN,
                    backup_manifest_sha256=v44.BACKUP_MANIFEST,
                    backup_logical_all_tables_sha256=v44.BACKUP_TABLES)
                need(canonical(proof) == canonical(expected),
                     "EVENT1836_PRECOMMIT_PROOF_CHANGED")
                writer.conn.execute(
                    "UPDATE meta SET source_sha=? WHERE id=1",(TARGET,))
                writer.event("SOURCE_TRANSITION_ADMITTED", proof)
                writer.verify()
                need(held() and release() and
                     writer.meta()["head_seq"] ==
                     successor.PREDECESSOR_SEQ + 1,
                     "PRECOMMIT_POSTWRITE_HOLD_REQUIRED")
        with closing(Database.open_readonly(path)) as final:
            final.verify()
            after = final.meta().copy()
            kinds = {x["stage"]:x["count"] for x in final.conn.execute(
                "SELECT stage,COUNT(*) AS count FROM tasks GROUP BY stage")}
            need(after["source_sha"] == TARGET
                 and after["head_seq"] == successor.PREDECESSOR_SEQ+1
                 and after["enabled"] == 1
                 and after["legacy_suspended"] == 1
                 and kinds == {"VERIFIED":153,"QUARANTINED":56}
                 and final.conn.total_changes == 0,
                 "POSTCOMMIT_SOURCE_OR_HISTORY_DRIFT")
        need(held() and release(), "POSTCOMMIT_OWNER_HOLD_MOVED")
    return {
        "schema": SCHEMA, "target_source_sha": TARGET,
        "workflow_sha": req["workflow_sha"],
        "owner_comment_id": req["comment_id"],
        "owner_run_id": req["event_run_id"],
        "prior_v44_rehearsal_run_id": req["v44_run_id"],
        "prior_v43_backup_run_id": v44.BACKUP_RUN,
        "new_head_seq": after["head_seq"],
        "new_head_sha256": after["head_hash"],
        "event1836_proof_sha256": digest(canonical(proof)),
        "original_task_still_disabled": True,
        "original_policy_unchanged": True,
        "source_committed_once": True,
        "activation_completed": False,
        "hybrid_scientific_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
        "database_rollback_authorized": False,
    }



def verify_poststart_event1836(path, env, expected_sha):
    """Read-only immutable event1836 witness, allowing later owner ticks."""
    need(sys.platform == "win32" and os.name == "nt"
         and type(expected_sha) is str
         and successor.SHA64.fullmatch(expected_sha) is not None,
         "POSTSTART_SHA_OR_HOST_INVALID")
    path = canonical_db(path, env)
    with closing(Database.open_readonly(path)) as db:
        db.verify()
        current = db.meta()
        row = db.conn.execute(
            "SELECT kind,prior_sha,sha,payload FROM events WHERE seq=?",
            (successor.PREDECESSOR_SEQ + 1,)).fetchone()
        need(current["source_sha"] == TARGET
             and current["enabled"] == 1
             and current["legacy_suspended"] == 1
             and current["head_seq"] >= successor.PREDECESSOR_SEQ + 1
             and row is not None
             and row["kind"] == "SOURCE_TRANSITION_ADMITTED"
             and row["prior_sha"] == successor.PREDECESSOR_SHA
             and row["sha"] == expected_sha
             and type(row["payload"]) is str
             and db.conn.total_changes == 0,
             "POSTSTART_IMMUTABLE_EVENT1836_OR_SOURCE_DRIFT")
    return True


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--target",required=True)
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--poststart-readonly",action="store_true")
    p.add_argument("--event1836-sha")
    args = p.parse_args(argv)
    need(args.target == TARGET, "FROZEN_TARGET_REQUIRED")
    env = dict(os.environ)
    epath = env.get("GITHUB_EVENT_PATH")
    need(type(epath) is str and Path(epath).is_absolute() and
         Path(epath).is_file(),"AUTHENTIC_EVENT_FILE_REQUIRED")
    try:
        event = json.loads(Path(epath).read_bytes(),object_pairs_hook=decode_unique)
    except (OSError,ValueError,UnicodeError,TypeError) as error:
        raise OriginalV46Denied("F139_V46_OWNER_EVENT_PARSE_FAILED") from error
    db = Path(env.get("LOCALAPPDATA",""))/"FORGE-F139"/"state.sqlite"
    need(not(args.preflight_only and args.poststart_readonly),
         "MUTUALLY_EXCLUSIVE_MODES_REQUIRED")
    if args.poststart_readonly:
        need(verify_poststart_event1836(db, env, args.event1836_sha),
             "POSTSTART_SOURCE_OR_EVENT1836_UNVERIFIED")
        print("F139_V46_LIVE_EVENT1836_ANCHOR=PASS")
        return 0
    need(args.event1836_sha is None, "POSTSTART_SHA_ONLY")
    if args.preflight_only:
        req = request(GitHub().native_repo_get,env,event)
        db = canonical_db(db,env)
        sealed_original(db)
        result = {"schema":"forge.f139.v46.preflight.v1",
                  "workflow_sha":req["workflow_sha"],"target_source_sha":TARGET,
                  "v44_copy_verified":True,"v43_backup_verified":True,
                  "owner_sqlite_mutations":0,"task_mutations":0,
                  "source_transition_authorized":False}
        print("F139_V46_PRECOMMIT_PREFLIGHT="+canonical(result).decode("ascii"))
    else:
        result=commit_original(db,env,event,GitHub())
        print("F139_V46_ORIGINAL_COMMIT_HOLD="+canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        message=str(exc)
        if not re.fullmatch(r"F139_[A-Z0-9_]{1,160}",message):
            message="F139_V46_UNCLASSIFIED_FAILURE"
        print(message,file=sys.stderr)
        sys.exit(1)

"""F139 V54 detached rehearsals and quiesced original-owner commit CLI.

The live mode must be called only by the separate GitHub owner-authenticated
Windows workflow after checking exact main, CI, issue approval, original SID,
task and source. This CLI independently enforces the existing task's hold.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from f139.local_controller import Database, SingleOwner
from f139 import nci04_v41_cold_copy_verifier as cold
from f139.nci04_v54_forward_transition import (
    SOURCE as FROM_SOURCE, ANCHOR_SEQ as HEAD_SEQ,
    ANCHOR_SHA as HEAD_SHA, MIN_OWNER_RUN as MIN_OWNER_RUN_ID,
    make_proof, need,
)
from f139.nci04_v54_owner_release import (
    original_snapshot, apply_copy_or_original,
)

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def require_owner_path(path, *, must_exist=True):
    p = Path(path).absolute()
    need(p.is_absolute() and not p.is_symlink()
         and (not must_exist or p.is_file()), "ORIGINAL_PATH_MISSING")
    return p


def read_frozen(path):
    with closing(Database.open_readonly(path)) as db:
        prior = original_snapshot(db)
        return {
            "source_sha": db.meta()["source_sha"],
            "head_seq": db.meta()["head_seq"],
            "head_sha256": db.meta()["head_hash"],
            # These verified counts are consumed by the original release
            # PowerShell preflight before staging or stopping the owner.
            "verified_historical_tasks": prior["verified_historical_tasks"],
            "custodied_negative_tasks": prior["custodied_negative_tasks"],
            "terminal_tasks_sha256": prior["terminal_tasks_sha256"],
        }


def backed_up(source, copy_path):
    """SQLite native online backup from RO source; never copy WAL bytes raw."""
    source = require_owner_path(source)
    copy_path = Path(copy_path).absolute()
    need(not copy_path.exists() and
         copy_path.parent.is_dir() and
         not copy_path.parent.is_symlink() and
         copy_path != source,
         "BACKUP_DESTINATION_NOT_FRESH")
    before = read_frozen(source)
    read = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True,
                           isolation_level=None, timeout=10)
    read.execute("PRAGMA query_only=ON")
    write = sqlite3.connect(str(copy_path), isolation_level=None, timeout=10)
    try:
        read.backup(write, pages=256, sleep=0.02)
        write.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        write.execute("PRAGMA journal_mode=DELETE")
    finally:
        write.close()
        read.close()
    # A detached SQLite database is not a complete cold restore by itself.
    # Database.verify() also checks the original historical negative ZIPs
    # relative to db.filename.parent. Reuse the existing hash-bound,
    # create-only two-artifact copier; never symlink, download or regenerate.
    # Nested live-rehearsal copies within one verified custody directory
    # already share those adjuncts and must not overwrite them.
    if source.parent.resolve() != copy_path.parent.resolve():
        with closing(Database.open_readonly(source)) as verified_source:
            negatives = cold.required_negative_custody(verified_source)
            need(verified_source.conn.total_changes == 0,
                 "SOURCE_CUSTODY_READ_WROTE")
        adjunct = copy_path.parent / "native-negative"
        need(not adjunct.is_symlink(), "DETACHED_NEGATIVE_CUSTODY_SYMLINK")
        # GitHub's self-hosted RUNNER_TEMP can persist across two distinct
        # owner-authenticated jobs. Recheck every original and copied SHA if
        # already staged; otherwise create files once, with exclusive 'xb'.
        # An incomplete or altered prior copy fails closed, never overwritten.
        cold.copy_negative_custody(
            source.parent, copy_path.parent, negatives,
            copy_files=not adjunct.exists())
    copied = read_frozen(copy_path)
    after = read_frozen(source)
    need(before == copied == after and
         copy_path.stat().st_size > 1024 and
         len(sha256(copy_path)) == 64,
         "BACKUP_COPY_OR_SOURCE_DRIFT")
    return sha256(copy_path)


def rehearsal(copy_path, args, backup_sha):
    path = require_owner_path(copy_path)
    need(sha256(path) == backup_sha,
         "DETACHED_BACKUP_SHA_CHANGED")
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database(path)) as db:
            prior = original_snapshot(db)
            proof = make_proof(
                db, target=args.target, owner_run_id=args.owner_run_id,
                qualified_main_run_id=args.main_run_id,
                rehearsal_run_id=args.rehearsal_run_id,
                backup_sqlite_sha256=backup_sha,
                genenv_executable_sha256=args.binary_sha,
                generation_mechanism_sha256=args.mechanism_sha,
            )
            outcome = apply_copy_or_original(db, proof)
    need(outcome["head_seq"] == prior["head_seq"]+2,
         "DETACHED_V44_AND_ACTIVATION_MISSING")
    return outcome


def original_v54_task_quiesced(db_path):
    """Verify original quiescence against the frozen V54 predecessor source.

    V50's historical helper still pins 4ccbb847 and must not be reused
    after the authentic original V52 owner source transition.
    """
    need(os.name == "nt" and sys.platform == "win32",
         "V54_ORIGINAL_WINDOWS_ONLY")
    cmd = shutil.which("powershell.exe")
    need(cmd is not None, "V54_ORIGINAL_POWERSHELL_REQUIRED")
    ps = r'''
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try {
  $sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).
    Translate([Security.Principal.SecurityIdentifier]).Value
} catch {}
if(@($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3 -or
   ([string]$t.Principal.UserId -ine $who.Name -and $sid -cne $who.User.Value) -or
   [string]$t.State -cne 'Disabled' -or $t.Settings.Enabled -ne $false) {
  exit 41
}
$a=$t.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe') {exit 42}
function Arg([string]$name) {
  $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  if(-not $m.Success){exit 43}
  return [string]$m.Groups[1].Value
}
$source=Arg 'RepositoryRoot'
$db=Arg 'Database'
$wrapper=Arg 'File'
$expected=Join-Path $env:LOCALAPPDATA ('FORGE-F139\release-candidates\'+'__EXPECTED_V54_SOURCE__')
if([IO.Path]::GetFullPath($source) -ine [IO.Path]::GetFullPath($expected) -or
   [IO.Path]::GetFullPath($db) -ine [IO.Path]::GetFullPath($env:F139_V54_DB_PATH) -or
   [IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1') {exit 44}
$children=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
                $_.CommandLine.Contains($db)})
if($children.Count -ne 0){exit 45}
Write-Output 'F139_V54_ORIGINAL_TASK_QUIESCED=PASS'
'''.replace("__EXPECTED_V54_SOURCE__", FROM_SOURCE)
    result = subprocess.run(
        [cmd, "-NoProfile", "-NonInteractive", "-Command", ps],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "F139_V54_DB_PATH": str(db_path.resolve())},
        stdin=subprocess.DEVNULL, timeout=30, check=False)
    need(result.returncode == 0 and
         result.stdout.strip() == b"F139_V54_ORIGINAL_TASK_QUIESCED=PASS",
         "V54_ORIGINAL_TASK_NOT_EXCLUSIVELY_QUIESCED")


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--mode", choices=("preflight","rehearse","backup","commit"),
                   required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--copy")
    p.add_argument("--target")
    p.add_argument("--owner-run-id",type=int)
    p.add_argument("--main-run-id",type=int)
    p.add_argument("--rehearsal-run-id",type=int)
    p.add_argument("--backup-sha")
    p.add_argument("--binary-sha")
    p.add_argument("--mechanism-sha")
    args=p.parse_args(argv)
    db_path=require_owner_path(args.db)
    need(db_path.name=="state.sqlite" and
         db_path.parent.name=="FORGE-F139" and
         os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE"
         and os.environ.get("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
         and os.environ.get("GITHUB_EVENT_NAME")=="issue_comment"
         and os.environ.get("GITHUB_ACTOR")=="spoonman136668-ai"
         and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
         and os.environ.get("GITHUB_RUN_ID","").isdigit()
         and not os.environ.get("OPENAI_API_KEY"),
         "EXACT_ORIGINAL_OWNER_ENVIRONMENT_REQUIRED")
    frozen=read_frozen(db_path)
    if args.mode=="preflight":
        print("F139_V54_PREFLIGHT="+json.dumps(frozen,sort_keys=True))
        return 0
    need(args.target == os.environ.get("GITHUB_SHA") and
         args.owner_run_id and args.owner_run_id > MIN_OWNER_RUN_ID and
         args.main_run_id and args.main_run_id > 0 and
         args.rehearsal_run_id and args.rehearsal_run_id > 0 and
         isinstance(args.binary_sha, str) and
         isinstance(args.mechanism_sha, str) and
         __import__("re").fullmatch(r"[0-9a-f]{64}", args.binary_sha) and
         __import__("re").fullmatch(r"[0-9a-f]{64}", args.mechanism_sha),
         "SOURCE_TARGET_OR_OWNER_RECEIPT_MISSING")
    need(args.owner_run_id == int(os.environ["GITHUB_RUN_ID"]),
         "ORIGINAL_OWNER_WORKFLOW_RUN_MISMATCH")
    if args.mode=="rehearse":
        copy_path=require_owner_path(args.copy,must_exist=False)
        backup_sha=backed_up(db_path,copy_path)
        result=rehearsal(copy_path,args,backup_sha)
        need(read_frozen(db_path)==frozen,"ORIGINAL_CHANGED_DURING_REHEARSAL")
        print("F139_V54_DETACHED_REHEARSAL="+json.dumps({
            **result,"original_mutations":0,
            "backup_sha256":backup_sha},sort_keys=True))
        return 0
    # Both backup and commit are forbidden until the actual original task is
    # disabled, stopped and child-free. Reusing the existing V50 guard is
    # intentional: a new helper must not enlarge original-owner authority.
    need(os.name=="nt" and sys.platform=="win32"
         and os.environ.get("F139_V54_NATIVE_LIVE_AUTHENTICATED")=="1",
         "LIVE_AUTHENTICATED_WINDOWS_ONLY")
    original_v54_task_quiesced(db_path)
    if args.mode=="backup":
        copy_path=require_owner_path(args.copy,must_exist=False)
        backup_sha=backed_up(db_path,copy_path)
        original_v54_task_quiesced(db_path)
        print("F139_V54_COLD_BACKUP="+json.dumps({
            "backup_sha256":backup_sha,"original":frozen,
            "source_mutations":0},sort_keys=True))
        return 0
    need(args.mode=="commit" and args.copy and args.backup_sha,
         "UNKNOWN_LIVE_OPERATION")
    copy_path=require_owner_path(args.copy)
    need(sha256(copy_path)==args.backup_sha and
         read_frozen(copy_path)==frozen,
         "COLD_BACKUP_NOT_EXACT_PREIMAGE")
    # Exercise the exact material source repair on a separate fresh clone of
    # the previously verified backup before committing original SQLite.
    # RUNNER_TEMP has a fresh, unique name and already-verified negative
    # custody files from the first cold rehearsal, separate from backup.
    test_path = Path(os.environ["RUNNER_TEMP"]) / (
        "f139-v54-original-rehearsal-" + str(args.owner_run_id) + "2.sqlite")

    need(not test_path.exists(), "DETACHED_REHEARSAL_ALREADY_CONSUMED")
    rehearsal_hash=backed_up(copy_path,test_path)
    need(read_frozen(test_path) == frozen,
         "BACKUP_LOGICAL_CUSTODY_CHANGED")
    rehearsal(test_path,args,rehearsal_hash)
    original_v54_task_quiesced(db_path)
    need(read_frozen(db_path)==frozen,
         "ORIGINAL_CHANGED_PRECOMMIT")
    with SingleOwner(db_path.with_suffix(".lock")):
        original_v54_task_quiesced(db_path)
        with closing(Database(db_path)) as db:
            proof=make_proof(db,target=args.target,
                owner_run_id=args.owner_run_id,
                qualified_main_run_id=args.main_run_id,
                rehearsal_run_id=args.rehearsal_run_id,
                backup_sqlite_sha256=args.backup_sha,
                genenv_executable_sha256=args.binary_sha,
                generation_mechanism_sha256=args.mechanism_sha)
            result=apply_copy_or_original(db,proof)
    original_v54_task_quiesced(db_path)
    with closing(Database.open_readonly(db_path)) as verified:
        verified.verify()
        need(verified.meta()["source_sha"]==args.target and
             verified.meta()["head_seq"]==frozen["head_seq"]+2 and
             verified.meta()["head_hash"]==result["head_sha256"],
             "POSTCOMMIT_ORIGINAL_SOURCE_DRIFT")
    print("F139_V54_ORIGINAL_EVENT1849="+json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("F139_V54_DENIED "+type(exc).__name__+": "+str(exc),
              file=sys.stderr,flush=True)
        raise SystemExit(1) from exc

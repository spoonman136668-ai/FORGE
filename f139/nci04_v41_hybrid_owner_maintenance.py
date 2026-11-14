"""Original V41 owner: explicit-request-only public Hybrid backup admission.

This is NOT a task pauser, new controller, owner workflow, policy writer or
deployment.  Original scheduled-task pause/resume is external and must be
separately authorized, qualified and witnessed.  An issue comment alone
cannot pause the task or enable a new development lane.
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

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_cold_pair as pair
from f139 import nci04_v41_hybrid_cold_bundle as bundle

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PREFIX = "F139-HYBRID-V41-BACKUP-ONLY "
TASK = "FORGE-F139-UnifiedController"
PROOF = "forge.f139.hybrid-v41.original-backup-only.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
POLICY_FIELDS = frozenset({
    "schema","enabled","source_sha","title_prefix","lanes",
    "max_issue_creations_per_cycle","require_owner_authored_pr",
    "require_single_head_commit_delta","require_single_allowed_source_file",
    "scientific_first_use","paid_model_calls","accepted_ref_mutations",
    "new_controller","new_scheduler","new_queue",
})


class HybridOwnerBackupDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise HybridOwnerBackupDenied("F139_HYBRID_V41_OWNER_BACKUP_" + code)


def _owner_comment(env, event, get, target):
    """One first-attempt original owner event, with two independent readbacks."""
    need(type(env) is dict and type(event) is dict and callable(get)
         and type(target) is str and SHA40.fullmatch(target) is not None
         and target != pair.V41_SOURCE
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == pair.V41_SOURCE
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0,
         "RUNNER_OR_EVENT_SOURCE_DRIFT")
    issue, comment, sender = (event.get(k) for k in ("issue","comment","sender"))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0 and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == PREFIX + target
         and type(comment.get("created_at")) is str,
         "EXACT_OWNER_BACKUP_REQUEST_REQUIRED")
    route = "repos/" + REPO + "/issues/comments/" + str(comment["id"])
    for _ in range(2):
        observed = get(route)
        need(type(observed) is dict and observed.get("id") == comment["id"]
             and observed.get("user",{}).get("login") == OWNER
             and observed.get("author_association") == "OWNER"
             and observed.get("issue_url") ==
                 "https://api.github.com/repos/" + REPO + "/issues/807"
             and observed.get("body") == PREFIX + target
             and observed.get("created_at") == comment["created_at"],
             "OWNER_COMMENT_READBACK_DRIFT")
    return int(env["GITHUB_RUN_ID"])


def _owner_policy(get):
    """Exact current two-lane policy; never treat policy access as authority."""
    raw = get("repos/" + REPO + "/issues/807")
    need(type(raw) is dict and raw.get("state") == "open"
         and raw.get("user",{}).get("login") == OWNER
         and type(raw.get("body")) is str, "POLICY_PROVIDER_DRIFT")
    try:
        doc = json.loads(raw["body"], object_pairs_hook=decode_unique)
    except (ValueError, TypeError) as error:
        raise HybridOwnerBackupDenied("F139_HYBRID_V41_OWNER_BACKUP_POLICY_PARSE") from error
    need(type(doc) is dict and set(doc) == POLICY_FIELDS
         and doc["schema"] == "forge.f139.native-autonomy-feed-owner-policy.v1"
         and doc["enabled"] is True
         and doc["source_sha"] == pair.V41_SOURCE
         and doc["title_prefix"] == "F139 autonomy DEV:"
         and doc["lanes"] == ["Wingless","Yggdrasil"]
         and type(doc["max_issue_creations_per_cycle"]) is int
         and doc["max_issue_creations_per_cycle"] == 2
         and all(doc[k] is True for k in (
             "require_owner_authored_pr","require_single_head_commit_delta",
             "require_single_allowed_source_file"))
         and all(doc[k] is False for k in (
             "scientific_first_use","new_controller","new_scheduler","new_queue"))
         and type(doc["paid_model_calls"]) is int and doc["paid_model_calls"] == 0
         and type(doc["accepted_ref_mutations"]) is int
         and doc["accepted_ref_mutations"] == 0,
         "ORIGINAL_TWO_LANE_POLICY_DRIFT")
    return raw["body"]


def _original_path(path, env):
    need(type(env.get("LOCALAPPDATA")) is str
         and bool(env["LOCALAPPDATA"])
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "LOCALAPPDATA_IDENTITY")
    db = Path(path)
    need(db.is_absolute() and db.name == "state.sqlite"
         and db.is_file() and not db.is_symlink()
         and not getattr(db, "is_junction", lambda:False)()
         and db.resolve() ==
             (Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite").resolve(),
         "ORIGINAL_DATABASE_PATH_DRIFT")
    return db


def _task_readback(db, *, disabled, runner=None):
    """Read-only task/SID/old-checkout proof, never control the task."""
    need(os.name == "nt", "ORIGINAL_WINDOWS_HOST_REQUIRED")
    powershell = shutil.which("powershell.exe")
    need(powershell is not None, "POWERSHELL_UNAVAILABLE")
    # No task command line, personal SID or path appears in the output.
    script = r'''
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
if(-not([string]$t.Principal.UserId -ieq $who.Name -or $sid -ceq $who.User.Value)){exit 41}
if(@($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3){exit 42}
$a=$t.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 43}
function Arg([string]$key){
  $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$key+'\s+"([^"]+)"')
  if(-not $m.Success){exit 44}
  return $m.Groups[1].Value
}
$root=Arg 'RepositoryRoot'
$db=Arg 'Database'
$exe=Arg 'PythonExe'
$wrapper=Arg 'File'
if([IO.Path]::GetFullPath($db) -ine [IO.Path]::GetFullPath($env:F139_EXPECTED_TASK_DATABASE)){exit 45}
if([IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1'){exit 46}
if(-not(Test-Path -LiteralPath $root -PathType Container) -or
   -not(Test-Path -LiteralPath $exe -PathType Leaf)){exit 47}
$rev=(& git -C $root rev-parse HEAD | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $rev -cne $env:F139_EXPECTED_SOURCE_SHA){exit 48}
$dirty=@(& git -C $root status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){exit 49}
if($env:F139_EXPECTED_TASK_MODE -ceq 'DISABLED'){
  if([string]$t.State -cne 'Disabled' -or $t.Settings.Enabled -ne $false){exit 50}
  $running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
    Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
      $_.CommandLine.Contains($env:F139_EXPECTED_TASK_DATABASE)})
  if($running.Count -ne 0){exit 51}
}else{
  if([string]$t.State -cnotin @('Ready','Running') -or $t.Settings.Enabled -ne $true){exit 52}
}
Write-Output 'F139_HYBRID_V41_ORIGINAL_TASK_READONLY=PASS'
'''
    env = {**os.environ,
           "F139_EXPECTED_TASK_DATABASE": str(db.resolve()),
           "F139_EXPECTED_SOURCE_SHA": pair.V41_SOURCE,
           "F139_EXPECTED_TASK_MODE": "DISABLED" if disabled else "ENABLED"}
    execute = subprocess.run if runner is None else runner
    try:
        result = execute([powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, env=env, timeout=25, check=False)
    except subprocess.TimeoutExpired as error:
        raise HybridOwnerBackupDenied(
            "F139_HYBRID_V41_OWNER_BACKUP_TASK_READBACK_TIMEOUT") from error
    need(result.returncode == 0
         and result.stdout.strip() ==
             b"F139_HYBRID_V41_ORIGINAL_TASK_READONLY=PASS",
         "ORIGINAL_TASK_SID_OR_SOURCE_OR_QUIESCENCE_DRIFT")
    return True


def _candidate_clean_checkout(target_sha, *, runner=None):
    """Check exact fully committed candidate source, not just remote PR text."""
    need(type(target_sha) is str and SHA40.fullmatch(target_sha) is not None,
         "CANDIDATE_CHECKOUT_ARGUMENTS")
    checkout = Path(__file__).resolve().parents[1]
    git = shutil.which("git")
    need(git is not None and checkout.is_dir(), "CANDIDATE_GIT_MISSING")
    run = subprocess.run if runner is None else runner
    for params, wanted in (
            (("rev-parse", "HEAD"), target_sha.encode("ascii")),
            (("status", "--porcelain", "--untracked-files=all"), b"")):
        try:
            result = run([git, "-C", str(checkout), *params],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, timeout=25, check=False)
        except subprocess.TimeoutExpired as error:
            raise HybridOwnerBackupDenied(
                "F139_HYBRID_V41_OWNER_BACKUP_CANDIDATE_GIT_TIMEOUT") from error
        need(result.returncode == 0 and result.stdout.strip() == wanted,
             "CANDIDATE_CHECKOUT_DIRTY_OR_WRONG_HEAD")
    return True


def _eligibility(db_path, env, event, get, *, target_sha, disabled):
    run_id = _owner_comment(env, event, get, target_sha)
    db = _original_path(db_path, env)
    pair._authenticate_candidate(get, target_sha)
    _candidate_clean_checkout(target_sha)
    prior_policy = _owner_policy(get)
    _task_readback(db, disabled=disabled)
    return run_id, db, prior_policy


def preflight_only(path, env, event, get, *, target_sha):
    """Read-only proof for a later separately approved same-task maintenance."""
    run_id, path, policy = _eligibility(
        path, env, event, get, target_sha=target_sha, disabled=False)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as original:
            original.verify()
            meta = original.meta().copy()
            need(meta["source_sha"] == pair.V41_SOURCE
                 and meta["head_seq"] >= pair.MIN_V41_HEAD
                 and meta["enabled"] == 1
                 and meta["legacy_suspended"] == 1
                 and original.dual_native_schema()
                 and pair.verify_native_activation(original)
                 and original.ready() is None and not original.actives()
                 and not pair.is_migrated(original)
                 and original.conn.total_changes == 0,
                 "LIVE_V41_ORIGINAL_LEDGER_UNQUALIFIED")
    need(_owner_policy(get) == policy, "POLICY_CHANGED_DURING_PREFLIGHT")
    pair._authenticate_candidate(get, target_sha)
    _owner_comment(env, event, get, target_sha)
    return {
        "schema": "forge.f139.hybrid-v41.original-maintenance-readonly.v1",
        "run_id": run_id, "original_source_sha": pair.V41_SOURCE,
        "candidate_sha": target_sha, "original_head_seq": meta["head_seq"],
        "original_head_sha256": meta["head_hash"],
        "same_original_task_only": True,
        "task_pause_authorized_by_this_receipt": False,
        "owner_mutations": 0, "new_dispatches": 0,
        "source_transition_authorized": False, "scientific_first_use": False,
    }


def backup_only(path, env, event, get, *, target_sha):
    """Run only AFTER an independently approved original-task pause."""
    run_id, path, policy = _eligibility(
        path, env, event, get, target_sha=target_sha, disabled=True)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as original:
            meta = original.meta().copy()
            receipt = bundle.stage_complete_cold_bundle(
                original, get, target_sha=target_sha, run_id=run_id)
            need(receipt["original_head_seq"] == meta["head_seq"]
                 and receipt["original_head_sha256"] == meta["head_hash"]
                 and receipt["independent_detached_restore_verified"] is True
                 and receipt["provider_archives_bytes_verified"] is True
                 and receipt["generation_binary_bytes_verified"] is True
                 and receipt["source_transition_authorized"] is False
                 and receipt["hybrid_admission"] is False
                 and receipt["scientific_first_use"] is False
                 and original.meta() == meta
                 and original.conn.total_changes == 0,
                 "BACKUP_ORIGINAL_OR_RESTORE_DRIFT")
    _task_readback(path, disabled=True)
    need(_owner_policy(get) == policy, "POLICY_CHANGED_DURING_BACKUP")
    pair._authenticate_candidate(get, target_sha)
    _owner_comment(env, event, get, target_sha)
    return {
        "schema": PROOF, "run_id": run_id,
        "original_source_sha": pair.V41_SOURCE,
        "candidate_sha": target_sha,
        "original_head_seq": meta["head_seq"],
        "original_head_sha256": meta["head_hash"],
        "manifest_sha256": receipt["manifest_sha256"],
        "independent_detached_restore_verified": True,
        "provider_archives_bytes_verified": True,
        "generation_binary_bytes_verified": True,
        "task_resumed": False, "task_pause_authorized_by_this_receipt": False,
        "original_owner_mutations": 0, "source_transition_authorized": False,
        "policy_modified": False, "hybrid_admission": False,
        "worker_dispatched": False, "new_dispatches": 0,
        "scientific_first_use": False,
    }


def main(argv=None, *, env=None, event=None, get=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    values = dict(os.environ if env is None else env)
    need(os.name == "nt", "ORIGINAL_WINDOWS_HOST_REQUIRED")
    if event is None:
        file = values.get("GITHUB_EVENT_PATH")
        need(type(file) is str and Path(file).is_file(),
             "GITHUB_EVENT_FILE_REQUIRED")
        event = json.loads(Path(file).read_text(encoding="utf-8"),
                           object_pairs_hook=decode_unique)
    get = GitHub().native_repo_get if get is None else get
    if args.preflight_only:
        receipt = preflight_only(args.db, values, event, get, target_sha=args.target)
        print("F139_HYBRID_V41_BACKUP_PREFLIGHT=" +
              canonical(receipt).decode("ascii"))
    else:
        receipt = backup_only(args.db, values, event, get, target_sha=args.target)
        print("F139_HYBRID_V41_BACKUP_ONLY=" +
              canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

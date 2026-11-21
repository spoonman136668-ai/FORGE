"""One-shot original Windows owner release for the existing fresh F139 task.

This is invoked only by the existing authenticated owner-comment workflow.
No new task, controller, scheduler, queue, ref, credential or provider dispatch.
The release branch must already exist and the complete merged candidate must
be qualified. A partial/ambiguous release stays consumed for owner recovery.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

from f139.local_controller import Database, GitHub, SingleOwner, legacy_windows_task_disabled
from f139.nci04_native_contract import canonical
from f139.nci04_fresh_native_activation import audit_fresh_native_activation
from f139.nci04_fresh_native_intake import audit_one_ready_tail
from f139.nci04_fresh_native_owner_route import inspect_staged_fresh_native_mode
from f139.nci04_fresh_worker_release_gate import (
    inspect_rebound_disabled_source, REBIND_FRESH_HEAD,
)
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE as OLD_SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)
from f139.nci04_autonomy_feed import inspect_policy
from f139.nci04_fresh_worker_protocol import REPO, SOURCE, FRESH_RUN, PREFIX, SHA40
from f139.nci04_fresh_lifecycle import (
    OWNER_WORKFLOW, OWNER_RELEASE_PREFIX, OWNER_RELEASE_JOB, RELEASE_KIND,
    RELEASE_SCHEMA, RELEASE_DOMAIN, check_release, verify_release_signature,
)

OWNER = "spoonman136668-ai"
ROOT = "repos/" + REPO
PR = 1859
BASE = "d1b94307536d490781dedb502d301a0c39cd10c7"
BRANCH = "engineering/f139-release-native-owner-ruleset-read-20261121"
QUALIFICATION = {
    ".github/workflows/qualify.yml",
    ".github/workflows/forge-f139-source-qualification.yml",
    ".github/workflows/forge-f139d-hosted-rehearsal.yml",
}


class OwnerReleaseDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OwnerReleaseDenied("F139_FRESH_RELEASE_" + reason)


def sha(v):
    return type(v) is str and SHA40.fullmatch(v) is not None


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=90, check=False,
                       env={k:v for k,v in os.environ.items()
                            if k not in ("F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN")})
    need(p.returncode == 0 and len(p.stdout) <= 64000, "GIT_SOURCE_OR_INSTALL_FAILED")
    return p.stdout.decode("utf-8").strip()


def read_json(path, limit=64000):
    need(path.is_file() and not path.is_symlink() and
         0 < path.stat().st_size <= limit, "OWNER_FILE_INVALID")
    doc = json.loads(path.read_bytes())
    need(type(doc) is dict, "OWNER_JSON_INVALID")
    return doc


def inspect_event(event, env):
    target = env.get("GITHUB_SHA")
    comment, issue = event.get("comment", {}), event.get("issue", {})
    run_id = env.get("GITHUB_RUN_ID", "")
    need(sha(target) and target != SOURCE and run_id.isdecimal() and int(run_id) > 0
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_WORKFLOW_REF") == REPO + "/" + OWNER_WORKFLOW + "@refs/heads/main"
         and bool(env.get("GH_TOKEN"))
         and not env.get("OPENAI_API_KEY") and not env.get("CLOUDFLARE_API_TOKEN")
         and event.get("action") == "created"
         and event.get("repository", {}).get("full_name") == REPO
         and event.get("sender", {}).get("login") == OWNER
         and issue.get("number") == 1830 and issue.get("state") == "open"
         and issue.get("user", {}).get("login") == OWNER
         and "pull_request" not in issue
         and type(comment.get("id")) is int and comment["id"] > 0
         and comment.get("user", {}).get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == OWNER_RELEASE_PREFIX + target + " " + str(FRESH_RUN),
         "SOURCE_BOUND_OWNER_EVENT_REQUIRED")
    return target, int(run_id), comment["id"]



def read_native_owner_ruleset(route):
    """Read the immutable-ref admin fields only through the existing local owner.

    The Actions GH_TOKEN may legitimately omit bypass_actors. Never confuse
    missing administration metadata with an empty bypass list or widen access.
    No write, secret, CLI error text, or automatic release retry is permitted.
    """
    need(route == ROOT + "/rulesets/26049392", "OWNER_RULESET_ROUTE_DENIED")
    safe_env = {k: v for k, v in os.environ.items()
                if k not in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN",
                             "F139_WORKER_HMAC_KEY", "GH_HOST")}

    def owner_read(*args):
        p = subprocess.run(["gh", "api", *args], env=safe_env,
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=30, check=False)
        need(p.returncode == 0 and 0 < len(p.stdout) <= 64000,
             "LOCAL_OWNER_READ_UNAVAILABLE")
        return p.stdout.decode("utf-8").strip()

    need(owner_read("user", "--jq", ".login") == OWNER,
         "LOCAL_OWNER_IDENTITY_DENIED")
    try:
        rule = json.loads(owner_read(route))
    except (ValueError, UnicodeDecodeError):
        raise OwnerReleaseDenied("F139_FRESH_RELEASE_OWNER_RULESET_INVALID") from None
    need(type(rule) is dict and type(rule.get("bypass_actors")) is list,
         "LOCAL_OWNER_RULESET_CUSTODY_REQUIRED")
    return rule


def safe_denial_code(exc):
    """Emit only a fixed-shape gate identifier, never a raw exception."""
    code = str(exc)
    return (code if isinstance(exc, OwnerReleaseDenied)
            and re.fullmatch(r"F139_FRESH_RELEASE_[A-Z0-9_]{1,85}", code)
            else "F139_FRESH_RELEASE_UNCLASSIFIED")


def qualify_release(get, target, tree, *, ruleset_get=None):
    """Verify exact merged final PR tree, all final suites and locked worker ref."""
    main = get(ROOT + "/branches/main")
    pr = get(ROOT + "/pulls/" + str(PR))
    head = pr.get("head", {}).get("sha")
    need(sha(target) and sha(tree) and sha(head)
         and main.get("protected") is True and main.get("commit", {}).get("sha") == target
         and pr.get("number") == PR and pr.get("merged") is True and pr.get("draft") is False
         and pr.get("state") == "closed" and pr.get("merge_commit_sha") == target
         and pr.get("user", {}).get("login") == OWNER
         and pr.get("head", {}).get("ref") == BRANCH
         and pr.get("head", {}).get("repo", {}).get("full_name") == REPO
         and pr.get("base", {}).get("ref") == "main"
         and pr.get("base", {}).get("repo", {}).get("full_name") == REPO,
         "QUALIFIED_MERGED_INTEGRATION_REQUIRED")
    merge = get(ROOT + "/git/commits/" + target)
    candidate = get(ROOT + "/git/commits/" + head)
    need(merge.get("sha") == target and candidate.get("sha") == head
         and merge.get("tree", {}).get("sha") == candidate.get("tree", {}).get("sha") == tree
         and [x.get("sha") for x in merge.get("parents", [])] == [BASE, head],
         "MERGED_TREE_OR_BASE_DRIFT")
    runs = get(ROOT + "/actions/runs?head_sha=" + head + "&event=pull_request&per_page=100")
    rows = runs.get("workflow_runs")
    need(type(rows) is list and runs.get("total_count") == len(rows)
         and len(rows) <= 100, "QUALIFICATION_INVENTORY_INVALID")
    for path in QUALIFICATION:
        match = [r for r in rows if r.get("path") == path]
        need(len(match) == 1 and match[0].get("head_sha") == head
             and match[0].get("event") == "pull_request"
             and match[0].get("run_attempt") == 1
             and match[0].get("status") == "completed"
             and match[0].get("conclusion") == "success"
             # GitHub may emit [] for genuine pull_request workflow runs.
             # The validated merged PR head, exact SHA, workflow path and event
             # still bind the source. Reject every foreign or malformed link.
             and type(match[0].get("pull_requests")) is list
             and all(type(p) is dict and p.get("number") == PR
                     for p in match[0]["pull_requests"]),
             "FULL_FINAL_EXACT_HEAD_QUALIFICATION_REQUIRED")
    name = PREFIX + target
    branch = get(ROOT + "/branches/" + name)
    rule = (ruleset_get or get)(ROOT + "/rulesets/26049392")
    need(branch.get("name") == name and branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == target
         and rule.get("id") == 26049392 and rule.get("target") == "branch"
         and rule.get("enforcement") == "active" and rule.get("bypass_actors") == []
         and rule.get("conditions") == {"ref_name": {"exclude": [],
                                                    "include": ["refs/heads/f139-owner-release-*"]}}
         and {r.get("type") for r in rule.get("rules", [])} == {"update", "deletion"},
         "IMMUTABLE_RELEASE_RULE_REQUIRED")
    need(get(ROOT + "/branches/main") == main
         and get(ROOT + "/branches/" + name) == branch,
         "RELEASE_SOURCE_MOVED")
    return head


def authenticate_event_provider(api, target, run_id, comment_id, event):
    comment = api.get(ROOT + "/issues/comments/" + str(comment_id))
    run = api.get(ROOT + "/actions/runs/" + str(run_id))
    jobs = api.get(ROOT + "/actions/runs/" + str(run_id) + "/jobs?per_page=100")
    rows = jobs.get("jobs")
    need(comment.get("id") == comment_id
         and comment.get("issue_url") == "https://api.github.com/" + ROOT + "/issues/1830"
         and comment.get("body") == event["comment"]["body"]
         and comment.get("created_at") == event["comment"]["created_at"]
         and comment.get("user", {}).get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and run.get("id") == run_id and run.get("head_sha") == target
         and run.get("run_attempt") == 1 and run.get("event") == "issue_comment"
         and run.get("path") == OWNER_WORKFLOW and run.get("status") == "in_progress"
         and run.get("actor", {}).get("login") == OWNER
         and run.get("repository", {}).get("full_name") == REPO
         and type(rows) is list and jobs.get("total_count") == len(rows)
         and sum(j.get("name") == OWNER_RELEASE_JOB and j.get("status") == "in_progress"
                 and j.get("runner_name") == "FORGE-CODEX-REMOTE" for j in rows) == 1,
         "OWNER_PROVIDER_OR_JOB_IDENTITY_INVALID")


# Fixed script, no interpolated command or user-provided path. It checks the
# existing native task and can replace only its exact original action.
TASK_SOURCE = r"""
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
if(-not ([Security.Principal.WindowsPrincipal]::new($who).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))){throw 'OWNER_ADMIN_REQUIRED'}
if([string]$t.Principal.UserId -ine $who.Name -and $sid -cne $who.User.Value){throw 'OWNER_SID_DRIFT'}
if($t.State -ne 'Disabled' -or $t.Settings.Enabled -ne $false -or @($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3){throw 'EXISTING_DISABLED_TASK_REQUIRED'}
$procs=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
if($procs.Count -ne 0){throw 'CONTROLLER_NOT_QUIESCED'}
$a=$t.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe' -or [string]$a.Arguments -notmatch '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)'){throw 'TASK_ACTION_DRIFT'}
function Arg([string]$name){
  $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  if(-not $m.Success){throw 'TASK_ARG_MISSING'}
  return [IO.Path]::GetFullPath($m.Groups[1].Value)
}
if((Arg 'RepositoryRoot') -ine [IO.Path]::GetFullPath($env:F139_RELEASE_OLD_ROOT) -or
   (Arg 'Database') -ine [IO.Path]::GetFullPath($env:F139_RELEASE_DB) -or
   (Arg 'File') -ine [IO.Path]::GetFullPath((Join-Path $env:F139_RELEASE_OLD_ROOT 'scripts\Run-FORGE-F139.ps1')) -or
   (Arg 'PythonExe') -ine [IO.Path]::GetFullPath($env:F139_RELEASE_PYTHON) -or
   -not (Test-Path -LiteralPath (Arg 'EncryptedKeyFile') -PathType Leaf)){throw 'REBOUND_TASK_ROUTE_DRIFT'}
if($env:F139_RELEASE_PHASE -eq 'PROBE'){
  Write-Output 'F139_FRESH_RELEASE_TASK_PROBE=PASS'
  exit 0
}
if($env:F139_RELEASE_PHASE -cne 'INSTALL'){throw 'RELEASE_PHASE_INVALID'}
$oldRoot=$env:F139_RELEASE_OLD_ROOT
$newRoot=$env:F139_RELEASE_NEW_ROOT
$before=[string]$a.Arguments
if($before.Split(@($oldRoot),[StringSplitOptions]::None).Count -ne 3){throw 'TASK_ACTION_REPLACEMENT_DRIFT'}
$argsNew=$before.Replace($oldRoot,$newRoot)
if($argsNew -ceq $before -or $argsNew.Contains($oldRoot) -or -not $argsNew.Contains($env:F139_RELEASE_DB)){throw 'TASK_ACTION_REPLACEMENT_INVALID'}
$work=[string]$a.WorkingDirectory
if($work -ieq $oldRoot){$work=$newRoot}
$newAction=if($work){New-ScheduledTaskAction -Execute ([string]$a.Execute) -Argument $argsNew -WorkingDirectory $work}else{New-ScheduledTaskAction -Execute ([string]$a.Execute) -Argument $argsNew}
Set-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -Action $newAction -ErrorAction Stop | Out-Null
$after=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
if($after.State -ne 'Disabled' -or $after.Settings.Enabled -ne $false -or
   @($after.Actions).Count -ne 1 -or [string]$after.Actions[0].Arguments -cne $argsNew -or
   [string]$after.Principal.UserId -cne [string]$t.Principal.UserId -or @($after.Triggers).Count -ne 3){throw 'TASK_REBIND_READBACK_FAILED'}
# This is the separately approved release, not the earlier disabled rebind.
Enable-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop | Out-Null
$enabled=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
if($enabled.Settings.Enabled -ne $true -or $enabled.State -eq 'Disabled' -or
   [string]$enabled.Actions[0].Arguments -cne $argsNew -or
   [string]$enabled.Principal.UserId -cne [string]$t.Principal.UserId){throw 'TASK_ENABLE_READBACK_FAILED'}
Write-Output 'F139_FRESH_EXISTING_TASK_RELEASED=PASS'
"""


def native_task(phase, *, old_root, new_root, db):
    env = dict(os.environ, F139_RELEASE_PHASE=phase,
               F139_RELEASE_OLD_ROOT=str(old_root), F139_RELEASE_NEW_ROOT=str(new_root),
               F139_RELEASE_DB=str(db), F139_RELEASE_PYTHON=str(Path(sys.executable).resolve()))
    for name in ("F139_WORKER_HMAC_KEY", "GH_TOKEN", "GITHUB_TOKEN"):
        env.pop(name, None)
    p = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", TASK_SOURCE],
                       env=env, capture_output=True, stdin=subprocess.DEVNULL,
                       timeout=60, check=False)
    expected = (b"F139_FRESH_RELEASE_TASK_PROBE=PASS" if phase == "PROBE"
                else b"F139_FRESH_EXISTING_TASK_RELEASED=PASS")
    need(p.returncode == 0 and p.stdout.strip() == expected,
         "NATIVE_TASK_CUSTODY_BLOCKED_NO_REPLAY")


def run_once():
    env = dict(os.environ)
    need(os.name == "nt" and sys.platform == "win32" and bool(env.get("LOCALAPPDATA")),
         "NATIVE_WINDOWS_OWNER_ONLY")
    event = read_json(Path(env.get("GITHUB_EVENT_PATH", "")))
    target, run_id, comment_id = inspect_event(event, env)
    key = env.get("F139_WORKER_HMAC_KEY", "")
    need(32 <= len(key) <= 4096, "ORIGINAL_DPAPI_WORKER_KEY_REQUIRED")
    checkout = Path(env["GITHUB_WORKSPACE"]).resolve()
    need(Path(__file__).resolve().parent.parent == checkout
         and git(checkout, "rev-parse", "HEAD") == target
         and git(checkout, "status", "--porcelain", "--untracked-files=all") == "",
         "OWNER_WORKFLOW_CHECKOUT_DRIFT")
    tree = git(checkout, "rev-parse", "HEAD^{tree}")
    api = GitHub()
    authenticate_event_provider(api, target, run_id, comment_id, event)
    qualify_release(api.get, target, tree, ruleset_get=read_native_owner_ruleset)
    policy = inspect_policy(api.get(ROOT + "/issues/807"), OLD_SOURCE)
    need(policy["enabled"] is True and "Yggdrasil" in policy["lanes"],
         "ORIGINAL_OWNER_POLICY_DISABLED")
    need(api.legacy_dispatchers_disabled() is True and legacy_windows_task_disabled() is True,
         "LEGACY_DISPATCHERS_NOT_DISABLED")
    root = Path(env["LOCALAPPDATA"]).resolve() / "FORGE-F139"
    original = root / "state.sqlite"
    fresh = root / ("f139-fresh-dev-" + str(FRESH_RUN)) / "state.sqlite"
    old_src = root / "release-candidates" / SOURCE
    new_src = root / "release-candidates" / target
    need(all(p.is_file() and not p.is_symlink() for p in (original, fresh))
         and all(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)()
                 for p in (root, fresh.parent, old_src, old_src.parent))
         and not new_src.exists() and not new_src.is_symlink()
         and git(old_src, "rev-parse", "HEAD") == SOURCE
         and git(old_src, "rev-parse", "HEAD^{tree}") == "4f35d3965bfd2d8688586600926445008e16f5b9"
         and git(old_src, "status", "--porcelain", "--untracked-files=all") == ""
         and git(old_src, "remote") == "",
         "INSTALL_OR_EXISTING_SOURCE_DRIFT_NO_REPLAY")
    with SingleOwner(original.with_suffix(".lock")), SingleOwner(fresh.with_suffix(".lock")):
        native_task("PROBE", old_root=old_src, new_root=new_src, db=fresh)
        old = Database.open_readonly(original)
        new = Database(fresh)
        try:
            old.verify()
            frozen = audit_frozen_original_readonly(old)
            need(frozen["source_sha"] == OLD_SOURCE and frozen["head_seq"] == HEAD_SEQ
                 and frozen["head_sha256"] == HEAD_SHA256 and old.conn.total_changes == 0,
                 "ORIGINAL_FROZEN_HISTORY_DRIFT")
            new.verify()
            m = new.meta()
            mode = inspect_staged_fresh_native_mode(new, fresh)
            need(m["head_seq"] == 4 and m["head_hash"] == REBIND_FRESH_HEAD
                 and mode["disposition"] == "FRESH_DEVELOPMENT_INTAKE_READY_DISPATCH_BLOCKED",
                 "FRESH_RELEASE_ALREADY_CONSUMED_OR_DRIFT")
            act = audit_fresh_native_activation(new)
            tail = list(new.conn.execute("SELECT * FROM events WHERE seq>=3 ORDER BY seq"))
            intake = audit_one_ready_tail(new, act, tail)
            receipt = read_json(fresh.parent / "fresh-owner-task-rebind.json")
            need(Path(receipt["new_database_path"]).resolve() == fresh.resolve(),
                 "ORIGINAL_REBIND_PATH_DRIFT")
            proof = inspect_rebound_disabled_source(act, intake, receipt, get=api.native_repo_get)
            need(proof["original_rebind_run_verified"] is True
                 and proof["rebind_receipt_source_consistent"] is True
                 and proof["worker_dispatch_authorized"] is False,
                 "ORIGINAL_REBIND_PROOF_INVALID")
            # Create-only source installation; never overwrite a prior attempt.
            git(checkout, "clone", "--no-local", "--no-checkout", "--quiet", "--",
                str(checkout), str(new_src))
            git(new_src, "checkout", "--quiet", "--detach", target)
            git(new_src, "remote", "remove", "origin")
            need(git(new_src, "rev-parse", "HEAD") == target
                 and git(new_src, "rev-parse", "HEAD^{tree}") == tree
                 and git(new_src, "status", "--porcelain", "--untracked-files=all") == ""
                 and git(new_src, "remote") == "",
                 "CREATE_ONLY_RELEASE_CHECKOUT_DRIFT")
            # Reverify the original provider and host immediately before writing.
            qualify_release(api.get, target, tree, ruleset_get=read_native_owner_ruleset)
            authenticate_event_provider(api, target, run_id, comment_id, event)
            native_task("PROBE", old_root=old_src, new_root=new_src, db=fresh)
            release = {
                "schema": RELEASE_SCHEMA, "admission_source_sha": SOURCE,
                "activation_run_id": FRESH_RUN, "initial_ready_sha256": m["head_hash"],
                "worker_release_sha": target, "worker_release_tree": tree,
                "owner_run_id": run_id, "owner_comment_id": comment_id,
                "original_rebind_run_id": 44852932511,
                "task_name": "FORGE-F139-UnifiedController", "development_only": True,
                "scientific_first_use": False, "model_continuation_authorized": False,
                "paid_model_calls": 0,
            }
            release["owner_signature"] = hmac.new(
                key.encode("utf-8"), RELEASE_DOMAIN + canonical(release), hashlib.sha256).hexdigest()
            check_release(release, m["head_hash"], act)
            verify_release_signature(release, key)
            with new.transaction():
                new.verify()
                need(new.meta() == m and old.conn.total_changes == 0
                     and audit_frozen_original_readonly(old) == frozen,
                     "OWNER_HISTORY_DRIFT_DURING_RELEASE")
                new.event(RELEASE_KIND, release)
                new.verify()
            # No worker POST here. The running controller will independently
            # require the completed successful owner job before its first claim.
            native_task("INSTALL", old_root=old_src, new_root=new_src, db=fresh)
            new.verify()
            need(new.meta()["head_seq"] == 5 and old.conn.total_changes == 0
                 and audit_frozen_original_readonly(old) == frozen,
                 "POST_RELEASE_LEDGER_DRIFT")
        finally:
            new.close()
            old.close()
    print("F139_FRESH_ORIGINAL_TASK_ENABLED=PASS")
    print("F139_FRESH_RELEASE_EVENT5=PASS")
    print("F139_WORKER_DISPATCHED=FALSE")
    print("F139_SCIENTIFIC_FIRST_USE=FALSE")


if __name__ == "__main__":
    try:
        run_once()
    except Exception as exc:
        # Release attempts are never replayed, including source-only failures.
        # The bounded gate identifier helps diagnose without exposing secrets.
        print("F139_FRESH_RELEASE_DENIAL_CODE=" + safe_denial_code(exc), file=sys.stderr)
        print("F139_FRESH_OWNER_RELEASE_BLOCKED_NO_REPLAY", file=sys.stderr)
        raise SystemExit(1)

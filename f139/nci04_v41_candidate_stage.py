"""Owner-authenticated V41 native candidate staging; no task/SQLite mutation.

This is a bounded, create-only local staging tool, NOT a controller,
scheduler, worker, live source activation, or policy editor. It leaves the
existing V40 owner untouched while preparing a durable clean candidate
checkout and its exact Go source-generation executable. No workflow invokes
this module until a separately qualified one-shot original-owner route exists.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from f139.local_controller import GitHub
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_guarded_release_preflight as release
from f139 import nci04_v41_source_transition as source


REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PREFIX = "F139-V41-NATIVE-STAGE "
SCHEMA = "forge.f139.v41.owner-candidate-stage-request.v1"
RECEIPT = "forge.f139.v41.owner-native-stage-only.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
FIELDS = frozenset({
    "schema", "target_source_sha", "release_pr_number",
    "scientific_first_use", "hybrid_admission", "new_controller",
    "new_scheduler", "new_queue", "paid_model_calls",
})


class V41StageDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise V41StageDenied("F139_V41_STAGE_" + reason)


def verify_stage_event(env, event, get):
    """Require an exact original OWNER issue #807 comment, twice read back."""
    required = {
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_ACTOR": OWNER,
        "GITHUB_EVENT_NAME": "issue_comment",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1",
        "RUNNER_NAME": "FORGE-CODEX-REMOTE",
    }
    need(type(env) is dict and type(event) is dict
         and callable(get) and all(env.get(k) == v for k, v in required.items())
         and type(env.get("GITHUB_SHA")) is str
         and SHA40.fullmatch(env["GITHUB_SHA"]) is not None
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit()
         and int(env["GITHUB_RUN_ID"]) > 0,
         "EXACT_FIRST_ATTEMPT_OWNER_RUN_REQUIRED")
    issue = event.get("issue")
    comment = event.get("comment")
    sender = event.get("sender")
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and issue.get("user", {}).get("login") == OWNER
         and "pull_request" not in issue
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0
         and comment.get("user", {}).get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("body")) is str
         and comment["body"].startswith(PREFIX),
         "ORIGINAL_OWNER_CREATED_COMMENT_REQUIRED")
    try:
        data = json.loads(comment["body"][len(PREFIX):],
                          object_pairs_hook=decode_unique)
    except (TypeError, UnicodeError, ValueError) as exc:
        raise V41StageDenied("F139_V41_STAGE_CANONICAL_JSON_INVALID") from exc
    need(type(data) is dict and set(data) == FIELDS
         and comment["body"] == PREFIX + canonical(data).decode("ascii")
         and data.get("schema") == SCHEMA
         and data.get("target_source_sha") == env["GITHUB_SHA"]
         and data["target_source_sha"] != source.FROM_V40
         and type(data.get("release_pr_number")) is int
         and data["release_pr_number"] > 0
         and all(data.get(k) is False for k in (
             "scientific_first_use", "hybrid_admission",
             "new_controller", "new_scheduler", "new_queue"))
         and type(data.get("paid_model_calls")) is int
         and data["paid_model_calls"] == 0,
         "STAGE_NONSCIENCE_EXACT_SOURCE_REQUIRED")
    route = "repos/" + REPO + "/issues/comments/" + str(comment["id"])
    for _ in range(2):
        stored = get(route)
        need(type(stored) is dict
             and stored.get("id") == comment["id"]
             and stored.get("user", {}).get("login") == OWNER
             and stored.get("author_association") == "OWNER"
             and stored.get("issue_url") ==
                 "https://api.github.com/repos/" + REPO + "/issues/807"
             and stored.get("body") == comment["body"]
             and stored.get("created_at") == comment.get("created_at")
             and stored.get("updated_at") == comment.get("updated_at"),
             "OWNER_COMMENT_READBACK_DRIFT")
    return dict(data, stage_comment_id=comment["id"],
                stage_run_id=int(env["GITHUB_RUN_ID"]))


def _call(argv, *, cwd=None, timeout=45, env=None):
    need(type(argv) is list and all(type(x) is str for x in argv)
         and 1 <= len(argv) <= 10, "BOUNDED_NATIVE_COMMAND")
    proc = subprocess.run(
        argv, cwd=str(cwd) if cwd is not None else None,
        capture_output=True, check=False,
        stdin=subprocess.DEVNULL, timeout=timeout, env=env)
    need(proc.returncode == 0 and len(proc.stdout) <= 2048
         and len(proc.stderr) <= 2048,
         "SOURCE_TOOLCHAIN_COMMAND_FAILED")
    return proc.stdout.decode("utf-8").strip()


STAGE_TASK_WITNESS = r"""
$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$p=[string]$t.Principal.UserId
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount($p)).Translate(
 [Security.Principal.SecurityIdentifier]).Value}catch{}
if($p -ine $who.Name -and $sid -ne $who.User.Value){exit 42}
if([string]$t.State -cnotin @('Running','Ready') -or
   $t.Settings.Enabled -ne $true){exit 43}
if(@($t.Actions).Count -ne 1 -or @($t.Triggers).Count -ne 3){exit 44}
$a=$t.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 45}
$args=[string]$a.Arguments
$root=[regex]::Match($args,'(?i)(?:^|\s)-RepositoryRoot\s+"([^"]+)"')
$db=[regex]::Match($args,'(?i)(?:^|\s)-Database\s+"([^"]+)"')
$py=[regex]::Match($args,'(?i)(?:^|\s)-PythonExe\s+"([^"]+)"')
$wrapper=[regex]::Match($args,'(?i)(?:^|\s)-File\s+"([^"]+)"')
if(-not($root.Success -and $db.Success -and $py.Success -and $wrapper.Success)){exit 46}
if([IO.Path]::GetFullPath($db.Groups[1].Value) -ine
    [IO.Path]::GetFullPath($env:F139_STAGE_EXPECTED_DB)){exit 47}
if([IO.Path]::GetFileName($wrapper.Groups[1].Value) -cne 'Run-FORGE-F139.ps1'){exit 48}
if(-not (Test-Path -LiteralPath $py.Groups[1].Value -PathType Leaf)){exit 49}
if($args -notmatch '(?i)(?:^|\s)-PollSeconds\s+300(?:\s|$)'){exit 50}
$oldRoot=[IO.Path]::GetFullPath($root.Groups[1].Value)
if($oldRoot -ieq [IO.Path]::GetFullPath($env:F139_STAGE_CANDIDATE_ROOT)){exit 51}
$oldHead=(& git -C $oldRoot rev-parse HEAD | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $oldHead -cne $env:F139_STAGE_V40_SOURCE){exit 52}
$dirty=@(& git -C $oldRoot status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0){exit 53}
Write-Output 'F139_V41_SAME_ORIGINAL_RUNNING_TASK_STAGE=PASS'
"""


def verify_running_old_task_before_stage(db_path, source_root):
    """Read-only SID, task action and V40 repository identity witness."""
    need(sys.platform == "win32" and os.name == "nt"
         and isinstance(db_path, Path) and isinstance(source_root, Path)
         and db_path.is_absolute() and db_path.is_file()
         and db_path.name == "state.sqlite" and not db_path.is_symlink()
         and source_root.is_absolute() and source_root.is_dir()
         and not source_root.is_symlink(),
         "NATIVE_OLD_TASK_WITNESS_INPUTS")
    powershell = shutil.which("powershell.exe")
    need(powershell is not None, "WINDOWS_POWERSHELL_REQUIRED")
    scoped = dict(os.environ, F139_STAGE_EXPECTED_DB=str(db_path.resolve()),
                  F139_STAGE_CANDIDATE_ROOT=str(source_root.resolve()),
                  F139_STAGE_V40_SOURCE=source.FROM_V40)
    status = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command",
         STAGE_TASK_WITNESS], check=False, capture_output=True,
        stdin=subprocess.DEVNULL, env=scoped, timeout=30)
    need(status.returncode == 0 and
         status.stdout.strip() ==
             b"F139_V41_SAME_ORIGINAL_RUNNING_TASK_STAGE=PASS",
         "ORIGINAL_OWNER_SID_TASK_OR_V40_ROOT_DRIFT")
    return True


def stage_owner_native_candidate(env, event, api):
    """Create only one new private candidate release and binary; no replay.

    On failure, any partially staged folder is left isolated for inspection.
    It is never silently replaced, deleted, or reused by a second request.
    """
    need(sys.platform == "win32" and os.name == "nt"
         and type(api) is GitHub,
         "WINDOWS_ORIGINAL_OWNER_ONLY")
    get = api.native_repo_get
    request = verify_stage_event(env, event, get)
    target = request["target_source_sha"]
    source_root = Path(__file__).resolve().parents[1]
    need(type(env.get("GITHUB_WORKSPACE")) is str
         and Path(env["GITHUB_WORKSPACE"]).resolve() == source_root
         and not source_root.is_symlink()
         and (source_root / ".git").exists()
         and (source_root / "go.mod").is_file(),
         "CANDIDATE_CHECKOUT_ROOT_DRIFT")
    need(_call(["git", "-C", str(source_root),
                "rev-parse", "HEAD"]) == target
         and _call(["git", "-C", str(source_root),
                    "status", "--porcelain",
                    "--untracked-files=all"]) == "",
         "CANDIDATE_CHECKOUT_NOT_EXACT_CLEAN_TARGET")
    source_receipt = release._remote_source(
        get, target=target, release_pr=request["release_pr_number"])
    need(_call(["git", "-C", str(source_root),
                "show", "-s", "--format=%T", "HEAD"]) ==
             source_receipt["tree_sha"],
         "TARGET_TREE_DIFFERENCE")
    policy = get("repos/" + REPO + "/issues/807")
    try:
        body = json.loads(policy.get("body"),
                          object_pairs_hook=decode_unique)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise V41StageDenied("F139_V41_STAGE_OWNER_POLICY_UNREADABLE") from exc
    need(policy.get("state") == "open"
         and policy.get("user", {}).get("login") == OWNER
         and type(body) is dict
         and body.get("source_sha") == source.FROM_V40
         and body.get("enabled") is True
         and body.get("lanes") == ["Wingless", "Yggdrasil"]
         and body.get("scientific_first_use") is False
         and body.get("paid_model_calls") == 0
         and body.get("new_controller") is False
         and body.get("new_scheduler") is False
         and body.get("new_queue") is False,
         "ORIGINAL_OWNER_POLICY_DRIFT")
    need(type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute(),
         "ORIGINAL_LOCALAPPDATA_REQUIRED")
    data = Path(env["LOCALAPPDATA"]) / "FORGE-F139"
    need(data.is_dir() and not data.is_symlink()
         and not getattr(data, "is_junction", lambda: False)()
         and (data / "state.sqlite").is_file()
         and not (data / "state.sqlite").is_symlink()
         and data.resolve() != source_root.resolve(),
         "EXISTING_ORIGINAL_DATA_ROOT_REQUIRED")
    need(verify_running_old_task_before_stage(
        data / "state.sqlite", source_root) is True,
        "ORIGINAL_OWNER_RUNNING_TASK_NOT_VERIFIED")
    install_base = data / "release-candidates"
    binary_base = data / "genenv-source"
    install = install_base / target
    binary_dir = binary_base / target
    binary = binary_dir / "f139-genenv-source.exe"
    need(not install.exists() and not install.is_symlink()
         and not binary_dir.exists() and not binary_dir.is_symlink()
         and (not install_base.exists() or
              (install_base.is_dir() and not install_base.is_symlink()))
         and binary_base.is_dir() and not binary_base.is_symlink(),
         "CREATE_ONLY_PRIVATE_STAGING_COLLISION")
    version = _call(["go", "version"])
    need(version == "go version " + source.TOOLCHAIN,
         "PINNED_NATIVE_GO_TOOLCHAIN_REQUIRED")
    # Final remote proof before any local source staging. The owner workflow
    # keeps GitHub token limited to repository, Actions and issue READs.
    need(verify_stage_event(env, event, get) == request
         and release._remote_source(
             get, target=target,
             release_pr=request["release_pr_number"]) == source_receipt
         and api.protected_main() == target,
         "RELEASE_OR_OWNER_INTENT_MOVED_BEFORE_STAGE")
    install_base.mkdir(parents=True, exist_ok=True)
    _call(["git", "clone", "--local", "--no-hardlinks", "--quiet",
           str(source_root), str(install)], timeout=180)
    need(install.is_dir() and not install.is_symlink(),
         "LOCAL_CLONE_NOT_CREATED")
    need(_call(["git", "-C", str(install), "rev-parse", "HEAD"]) == target
         and _call(["git", "-C", str(install),
                    "status", "--porcelain", "--untracked-files=all"]) == "",
         "DURABLE_CANDIDATE_CLONE_NOT_CLEAN")
    need(_call(["git", "-C", str(install),
                "show", "-s", "--format=%T", "HEAD"]) ==
             source_receipt["tree_sha"],
         "DURABLE_CANDIDATE_TREE_DRIFT")
    binary_dir.mkdir(parents=True, exist_ok=False)
    build_env = dict(os.environ, GOOS="windows", GOARCH="amd64",
                     CGO_ENABLED="0")
    _call(["go", "build", "-trimpath", "-buildvcs=false",
           "-o", str(binary), "./cmd/f139-genenv-source"],
          cwd=install, env=build_env, timeout=180)
    need(binary.is_file() and not binary.is_symlink()
         and 0 < binary.stat().st_size <= 16_000_000,
         "GENENV_EXECUTABLE_MISSING")
    binary_sha = digest(binary.read_bytes())
    need(verify_running_old_task_before_stage(
        data / "state.sqlite", source_root) is True,
        "ORIGINAL_OWNER_TASK_MOVED_AFTER_STAGE")
    need(_call(["git", "-C", str(install),
                "status", "--porcelain", "--untracked-files=all"]) == ""
         and release._remote_source(
             get, target=target,
             release_pr=request["release_pr_number"]) == source_receipt
         and verify_stage_event(env, event, get) == request,
         "CANDIDATE_OR_REMOTE_MOVED_AFTER_STAGE")
    return {
        "schema": RECEIPT, "target_source_sha": target,
        "source_tree_sha": source_receipt["tree_sha"],
        "release_pr_number": request["release_pr_number"],
        "stage_comment_id": request["stage_comment_id"],
        "stage_run_id": request["stage_run_id"],
        "binary_sha256": binary_sha,
        "binary_size": binary.stat().st_size,
        "owner_source_sha": source.FROM_V40,
        "candidate_staged_only": True,
        "original_owner_task_touched": False,
        "original_sqlite_touched": False,
        "owner_policy_touched": False,
        "source_transition_authorized": False,
        "scientific_first_use": False, "hybrid_admission": False,
        "new_dispatches": 0, "paid_model_calls": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    options = parser.parse_args(argv)
    need(sys.platform == "win32" and os.name == "nt"
         and type(options.target) is str
         and SHA40.fullmatch(options.target) is not None,
         "NATIVE_EXACT_TARGET_REQUIRED")
    env = dict(os.environ)
    path = env.get("GITHUB_EVENT_PATH")
    need(type(path) is str and Path(path).is_file(),
         "OWNER_ISSUE_EVENT_FILE_REQUIRED")
    event = json.loads(Path(path).read_text(encoding="utf-8"),
                       object_pairs_hook=decode_unique)
    need(env.get("GITHUB_SHA") == options.target,
         "TARGET_SHA_CLI_DRIFT")
    report = stage_owner_native_candidate(env, event, GitHub())
    print("F139_V41_NATIVE_CANDIDATE_STAGE=" +
          canonical(report).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

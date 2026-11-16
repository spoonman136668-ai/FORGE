"""One-shot, owner-authenticated activation after the genuine V41 source handoff.

Run only on the original isolated Windows owner. A new owner comment permits
one development-only activation at seq 1837; neither this module nor a PR
permits scientific first-use, dispatch, a source retarget or a second task.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_owner_ledger import (
    APPROVAL_SCHEMA, ACTIVATION_FIELDS, ACTIVATION_KIND, ACTIVATION_SCHEMA, activate_native,
    verify_native_activation,
)
from f139.nci04_release_pin_continuity import prove_deployed_release_pin

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
SOURCE = "4ccbb84785a43e038453d6f2bda5415ecb364084"
BEFORE = "af204acc983719b382bc8daf2216ec6733ca3ee7"
HEAD_SEQ = 1836
HEAD_HASH = "dbc4e12862c819812121adf1df905f74023c65633067bcabe906488d37468964"
PREVIOUS_RUN = 43973705548
PREVIOUS_COMMENT = 6931739592
PREVIOUS_HEAD = "2567775a9c06b306142812cc8c0e252278f87273"
PREFIX = "F139-V50-OWNER-NATIVE-ACTIVATE "
EIGHT = frozenset(("linux_genenv", "linux_native", "linux_f139",
                   "windows_genenv", "windows_native", "windows_f139",
                   "linux", "windows"))
SHA40 = re.compile(r"[a-f0-9]{40}\Z")


class NativeV50Denied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise NativeV50Denied("F139_V50_" + code)


def read(get, route):
    need(callable(get) and route.startswith("repos/" + REPO + "/"),
         "PROVIDER_SCOPE")
    x = get(route)
    need(type(x) is dict, "PROVIDER_OBJECT")
    return x


def request(get, env, event):
    """Pure remote owner/CI/release proof; does not contact SQLite or write."""
    main = env.get("GITHUB_SHA")
    need(type(main) is str and SHA40.fullmatch(main) is not None
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and not env.get("OPENAI_API_KEY"),
         "ORIGINAL_OWNER_EVENT_ENV")
    need(type(event) is dict and event.get("action") == "created",
         "OWNER_COMMENT_ACTION")
    issue, sender, comment = (
        event.get("issue"), event.get("sender"), event.get("comment"))
    need(type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and type(comment.get("id")) is int
         and comment["id"] > PREVIOUS_COMMENT
         and type(comment.get("created_at")) is str
         and comment.get("updated_at") == comment["created_at"],
         "OWNER_COMMENT_IDENTITY")
    body = PREFIX + main + " " + SOURCE + " " + str(PREVIOUS_RUN)
    need(comment.get("body") == body, "EXACT_SOURCE_APPROVAL_REQUIRED")
    p = "repos/" + REPO + "/"
    remote_comment = read(get, p + "issues/comments/" + str(comment["id"]))
    need(remote_comment.get("id") == comment["id"]
         and remote_comment.get("body") == body
         and remote_comment.get("created_at") == comment["created_at"]
         and remote_comment.get("author_association") == "OWNER"
         and type(remote_comment.get("user")) is dict
         and remote_comment["user"].get("login") == OWNER
         and remote_comment.get("issue_url") ==
             "https://api.github.com/repos/" + REPO + "/issues/807",
         "OWNER_COMMENT_REMOTE_AUTH")
    prior = read(get, p + "actions/runs/" + str(PREVIOUS_RUN))
    need(prior.get("id") == PREVIOUS_RUN
         and prior.get("name") == "FORGE G54 guarded V9 original-owner cutover"
         and prior.get("head_sha") == PREVIOUS_HEAD
         and prior.get("run_attempt") == 1
         and prior.get("status") == "completed"
         and prior.get("conclusion") == "success"
         and type(prior.get("actor")) is dict
         and prior["actor"].get("login") == OWNER,
         "PRIOR_ORIGINAL_RECOVERY_NOT_AUTHENTIC")
    # The current protected source is qualification input, not the installed
    # runtime. Never equate it with a new owner source promotion.
    branch = read(get, p + "branches/main")
    need(branch.get("protected") is True
         and branch.get("commit", {}).get("sha") == main,
         "PROTECTED_MAIN_NOT_EXACT")
    pin = prove_deployed_release_pin(
        get, deployed_source=SOURCE, protected_source=main)
    need(pin["existing_owner_policy_authorized"] is True
         and pin["new_commits_are_uninstalled"] is True,
         "SOURCE_PIN_UNVERIFIED")
    inventory = read(get, p + "actions/runs?head_sha=" + main +
                     "&event=push&branch=main&per_page=100")
    selected = [x for x in inventory.get("workflow_runs", [])
                if type(x) is dict and x.get("name") ==
                "FORGE public Linux and Windows qualification"]
    need(len(selected) == 1, "EXACT_MAIN_REGRESSION_REQUIRED")
    run = selected[0]
    need(run.get("head_sha") == main
         and run.get("head_branch") == "main"
         and run.get("run_attempt") == 1
         and run.get("event") == "push"
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == OWNER
         and type(run.get("id")) is int,
         "MAIN_REGRESSION_UNQUALIFIED")
    jobs = read(get, p + "actions/runs/" + str(run["id"]) +
                "/jobs?per_page=100").get("jobs")
    need(type(jobs) is list and len(jobs) == 8
         and {j.get("name") for j in jobs if type(j) is dict} == EIGHT
         and all(type(j) is dict and j.get("status") == "completed"
                 and j.get("conclusion") == "success" for j in jobs),
         "EIGHT_JOB_REGRESSION_FAILED")
    need(read(get, p + "branches/main").get("commit", {}).get("sha") == main,
         "PROTECTED_MAIN_MOVED")
    return dict(schema="forge.f139.v50.original-native-activation-request.v1",
                main_sha=main, source_sha=SOURCE,
                prior_run_id=PREVIOUS_RUN, owner_comment_id=comment["id"],
                main_regression_run_id=run["id"], job_count=8,
                scientific_first_use=False, new_controller=False,
                new_dispatches=0)


def snapshot(db, activated):
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == SOURCE
         and meta["head_seq"] == HEAD_SEQ + int(activated)
         and (meta["head_hash"] == HEAD_HASH if not activated else True)
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and db.ready() is None and not db.actives(),
         "ORIGINAL_HEAD_OR_PENDING_DRIFT")
    counts = Counter(row["stage"] for row in db.conn.execute(
        "SELECT stage FROM tasks"))
    need(counts == Counter(VERIFIED=153, QUARANTINED=56),
         "ORIGINAL_153_56_TASK_CUSTODY")
    event = db.conn.execute(
        "SELECT kind,payload FROM events WHERE seq=?", (meta["head_seq"],)
    ).fetchone()
    need(event is not None, "EVENT_MISSING")
    if activated:
        need(event["kind"] == ACTIVATION_KIND,
             "NEW_EVENT_NOT_NATIVE_ACTIVATION")
        record = json.loads(event["payload"])
        need(record.get("source_sha") == SOURCE
             and record.get("scientific_first_use") is False
             and record.get("development_only") is True
             and record.get("new_dispatches") == 0
             and verify_native_activation(db) is True,
             "NEW_NATIVE_ACTIVATION_UNVERIFIED")
    else:
        need(event["kind"] == "SOURCE_TRANSITION_ADMITTED"
             and json.loads(event["payload"]).get("schema") ==
             "forge.f139.source-transition.v41"
             and verify_native_activation(db) is False
             and verify_native_activation(db, expected_source=BEFORE) is True,
             "PREDECESSOR_NATIVE_ACTIVATION_DRIFT")
    return meta["head_hash"]


def poststart_snapshot(db):
    """Read-only source-bound activation proof; tolerate authentic later events.

    The original controller can append event1838+ immediately after restart.
    The full chain and immutable event1837, not a frozen task census, govern
    acceptance of that normal development activity.
    """
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == SOURCE
         and type(meta["head_seq"]) is int
         and meta["head_seq"] >= HEAD_SEQ + 1
         and meta["enabled"] == 1 and meta["legacy_suspended"] == 1,
         "POSTSTART_SOURCE_OR_LEDGER_DRIFT")
    event = db.conn.execute(
        "SELECT seq,sha,prior_sha,kind,payload FROM events WHERE seq=?",
        (HEAD_SEQ + 1,)).fetchone()
    need(event is not None and event["seq"] == HEAD_SEQ + 1
         and event["kind"] == ACTIVATION_KIND
         and event["prior_sha"] == HEAD_HASH
         and isinstance(event["sha"], str)
         and re.fullmatch(r"[a-f0-9]{64}", event["sha"]) is not None,
         "POSTSTART_EVENT1837_MISSING_OR_UNSEALED")
    record = json.loads(event["payload"])
    need(isinstance(record, dict) and set(record) == ACTIVATION_FIELDS
         and record["schema"] == ACTIVATION_SCHEMA
         and record["source_sha"] == SOURCE
         and record["prior_event_head_sha256"] == HEAD_HASH
         and record["scientific_first_use"] is False
         and record["development_only"] is True
         and record["new_dispatches"] == 0
         and verify_native_activation(db) is True,
         "POSTSTART_ACTIVATION_AUTHORITY_DRIFT")
    return dict(head_sha256=meta["head_hash"],
                event_seq=meta["head_seq"],
                activation_event_seq=HEAD_SEQ + 1,
                activation_event_sha256=event["sha"],
                native_development_activated=True,
                scientific_first_use=False,
                original_owner_mutations=0)


def original_task_quiesced(db_path):
    """Independent native guard against direct CLI while original task runs."""
    cmd = shutil.which("powershell.exe")
    need(cmd is not None, "NATIVE_POWERSHELL_REQUIRED")
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
$expected=Join-Path $env:LOCALAPPDATA 'FORGE-F139\release-candidates\4ccbb84785a43e038453d6f2bda5415ecb364084'
if([IO.Path]::GetFullPath($source) -ine [IO.Path]::GetFullPath($expected) -or
   [IO.Path]::GetFullPath($db) -ine [IO.Path]::GetFullPath($env:F139_V50_DB_PATH) -or
   [IO.Path]::GetFileName($wrapper) -cne 'Run-FORGE-F139.ps1') {exit 44}
$children=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop |
  Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller') -and
                $_.CommandLine.Contains($db)})
if($children.Count -ne 0){exit 45}
Write-Output 'F139_V50_ORIGINAL_TASK_QUIESCED=PASS'
'''
    result = subprocess.run(
        [cmd, "-NoProfile", "-NonInteractive", "-Command", ps],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "F139_V50_DB_PATH": str(db_path.resolve())},
        stdin=subprocess.DEVNULL, timeout=30, check=False)
    need(result.returncode == 0 and
         result.stdout.strip() == b"F139_V50_ORIGINAL_TASK_QUIESCED=PASS",
         "NATIVE_TASK_NOT_EXCLUSIVELY_QUIESCED")


def execute(db_path, mode):
    need(os.name == "nt" and sys.platform == "win32",
         "NATIVE_WINDOWS_ONLY")
    need(db_path.resolve() ==
         (Path(os.environ["LOCALAPPDATA"]) / "FORGE-F139" /
          "state.sqlite").resolve(),
         "ORIGINAL_DB_PATH_REQUIRED")
    if mode in ("preflight", "verify", "poststart"):
        db = Database.open_readonly(db_path)
        try:
            # One consistent SQLite read snapshot while the live writer runs.
            db.conn.execute("BEGIN")
            before = db.conn.total_changes
            if mode == "poststart":
                report = poststart_snapshot(db)
            else:
                head = snapshot(db, mode == "verify")
                report = dict(head_sha256=head,
                              event_seq=HEAD_SEQ + int(mode == "verify"),
                              native_development_activated=(mode == "verify"),
                              scientific_first_use=False,
                              original_owner_mutations=0)
            need(db.conn.total_changes == before == 0,
                 "READ_ONLY_CHANGED_DATABASE")
            return report
        finally:
            db.conn.rollback()
            db.close()
    need(mode == "commit", "UNKNOWN_MODE")
    # PowerShell has already disabled and quiesced the one original task.
    # The original SQLite SingleOwner mutex is the only writer authority.
    original_task_quiesced(db_path)
    with SingleOwner(db_path.with_suffix(".lock")):
        original_task_quiesced(db_path)
        db = Database(db_path)
        try:
            snapshot(db, False)
            approved = dict(
                schema=APPROVAL_SCHEMA, source_sha=SOURCE,
                expected_event_head_sha256=HEAD_HASH,
                native_development_approved=True,
                scientific_first_use=False, create_controller=False,
                paid_api_calls=0)
            need(activate_native(db, approved) is True,
                 "NATIVE_ACTIVATION_NOT_COMMITTED")
            head = snapshot(db, True)
        finally:
            db.close()
    return dict(head_sha256=head, event_seq=HEAD_SEQ + 1,
                native_development_activated=True,
                scientific_first_use=False, original_owner_mutations=1,
                new_dispatches=0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("preflight", "commit", "verify", "poststart"),
                   required=True)
    p.add_argument("--db", type=Path, required=True)
    args = p.parse_args()
    need(args.db.is_absolute() and not args.db.is_symlink()
         and args.db.is_file(), "EXACT_ORIGINAL_DB_REQUIRED")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text("utf-8"))
    # A poststart readback has no remote provider dependency: the original
    # owner comment, release pin and exact CI were already authenticated on
    # preflight, commit and frozen (pre-restart) verification.
    proof = ({} if args.mode == "poststart" else
             request(GitHub().native_repo_get, os.environ, event))
    report = execute(args.db, args.mode)
    print("F139_V50_OWNER_" + args.mode.upper() + "=" +
          json.dumps(dict(**proof, **report), sort_keys=True))


if __name__ == "__main__":
    main()

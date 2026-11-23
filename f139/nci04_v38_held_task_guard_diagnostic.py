"""Single-use diagnostic of the unchanged original held Windows task guard.

Only returns one bounded exit-predicate code (41..51), PASS_ONLY, or
UNCLASSIFIED. The original profile.readback PowerShell text is re-used
unchanged. No original SQLite is opened or modified. No scheduling, owner
source transition, runner mutation, first use, worker dispatch, or restart.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from f139.local_controller import GitHub
from f139.nci04_owner_issue import decode_unique
from f139 import nci04_v41_hybrid_forward_owner_profile as profile

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PREVIOUS_COMMENT = 6886633573
PREVIOUS_RUN = 43658624013
PREVIOUS_SHA = "46a97e22ccd061ed799b53a8b92f27ed48b98f2b"
PREVIOUS_BODY = ("F139-HYBRID-V41-FORWARD-READINESS "
                 + PREVIOUS_SHA + " 6883036903")
PREFIX = "F139-V38-HELD-TASK-GUARD-DIAG "
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
DECIMAL = re.compile(r"[1-9][0-9]*\Z")
G_CODES = frozenset(range(41, 52))
POSITIVE = "F139_V38_HELD_TASK_GUARD=PASS_PREDICATES_ONLY"
LABEL = "F139_V38_HELD_TASK_GUARD="


class GuardDiagnosticDenied(ValueError):
    pass


def need(yes: bool, reason: str):
    if not yes:
        raise GuardDiagnosticDenied(reason)


def _comment(get, number, body):
    need(type(number) is int and number > PREVIOUS_COMMENT,
         "OWNER_COMMENT_ID_INVALID")
    route = "repos/" + REPO + "/issues/comments/" + str(number)
    first, second = get(route), get(route)
    for row in (first, second):
        need(type(row) is dict and row.get("id") == number
             and row.get("body") == body
             and row.get("author_association") == "OWNER"
             and type(row.get("user")) is dict
             and row["user"].get("login") == OWNER
             and row.get("issue_url") ==
                 "https://api.github.com/repos/" + REPO + "/issues/807"
             and type(row.get("created_at")) is str,
             "COMMENT_PROVIDER_MISMATCH")
    need(first["created_at"] == second["created_at"],
         "COMMENT_CHANGED")
    return first["created_at"]


def authenticate(get, env, event) -> str:
    """One distinct owner-authored event and the frozen failed read-only run."""
    need(callable(get) and type(env) is dict and type(event) is dict,
         "EVENT_UNAVAILABLE")
    target = env.get("GITHUB_SHA")
    need(type(target) is str and SHA40.fullmatch(target) is not None
         and target != PREVIOUS_SHA
         and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GITHUB_RUN_ID")) is str
         and DECIMAL.fullmatch(env["GITHUB_RUN_ID"]) is not None
         and not env.get("OPENAI_API_KEY"),
         "NATIVE_OWNER_FIRST_ATTEMPT_REQUIRED")
    issue, sender, comment = (event.get(k) for k in
                              ("issue", "sender", "comment"))
    body = PREFIX + target + " " + str(PREVIOUS_COMMENT)
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict
         and type(comment.get("id")) is int
         and comment["id"] > PREVIOUS_COMMENT
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == body,
         "DISTINCT_CANONICAL_OWNER_DIAGNOSTIC_REQUIRED")
    created = _comment(get, comment["id"], body)
    old = get("repos/" + REPO + "/issues/comments/" +
              str(PREVIOUS_COMMENT))
    need(type(old) is dict and old.get("id") == PREVIOUS_COMMENT
         and old.get("body") == PREVIOUS_BODY
         and old.get("author_association") == "OWNER"
         and type(old.get("user")) is dict
         and old["user"].get("login") == OWNER
         and type(old.get("created_at")) is str
         and old["created_at"] < created,
         "PREVIOUS_APPROVED_FAILURE_RECORD_DRIFT")
    run = get("repos/" + REPO + "/actions/runs/" + str(PREVIOUS_RUN))
    need(type(run) is dict and run.get("id") == PREVIOUS_RUN
         and run.get("head_sha") == PREVIOUS_SHA
         and run.get("run_attempt") == 1
         and run.get("event") == "issue_comment"
         and run.get("status") == "completed"
         and run.get("conclusion") == "failure"
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == OWNER,
         "FAILED_FIRST_READONLY_ATTEMPT_NOT_CONFIRMED")
    main = get("repos/" + REPO + "/branches/main")
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == target,
         "PROTECTED_MAIN_SOURCE_DRIFT")
    issue_read = get("repos/" + REPO + "/issues/807")
    need(type(issue_read) is dict and issue_read.get("state") == "open"
         and type(issue_read.get("body")) is str,
         "POLICY_UNAVAILABLE")
    try:
        policy = json.loads(issue_read["body"],
                            object_pairs_hook=decode_unique)
    except (TypeError, ValueError) as error:
        raise GuardDiagnosticDenied("ORIGINAL_POLICY_PARSE") from error
    need(type(policy) is dict
         and policy.get("lanes") == ["Wingless", "Yggdrasil"]
         and policy.get("scientific_first_use") is False
         and policy.get("new_controller") is False
         and policy.get("new_scheduler") is False
         and policy.get("new_queue") is False,
         "POLICY_BOUNDARY_DRIFT")
    return target


def classify(db_path: Path, *, readback=profile.readback,
             execute=subprocess.run) -> str:
    """Run the pre-existing task identity guard ONCE; never print its output."""
    calls = 0
    result_code = None

    def observed(argv, **kwargs):
        nonlocal calls, result_code
        calls += 1
        if calls != 1:
            raise GuardDiagnosticDenied("SECOND_TASK_PROBE_DENIED")
        result = execute(argv, **kwargs)
        result_code = result.returncode
        return result

    error = None
    try:
        passed = readback(db_path, runner=observed)
    except profile.HeldTaskIdentityDenied as exc:
        error = str(exc)
        passed = False
    if (calls == 1 and result_code == 0 and passed is True
            and error is None):
        return "PASS_PREDICATES_ONLY"
    if (calls == 1 and result_code in G_CODES and
            error == "F139_HYBRID_V38_HELD_TASK_"
                     "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED"):
        return "EXIT_" + str(result_code)
    raise GuardDiagnosticDenied("UNCLASSIFIED_GUARD_RESULT")


def main():
    """Emit only one code. All other details, paths and provider errors hidden."""
    try:
        env = dict(os.environ)
        need(sys.platform == "win32" and os.name == "nt",
             "ORIGINAL_WINDOWS_HOST_REQUIRED")
        event_file = env.get("GITHUB_EVENT_PATH")
        need(type(event_file) is str and Path(event_file).is_file(),
             "EVENT_FILE_UNAVAILABLE")
        event = json.loads(Path(event_file).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
        get = GitHub().native_repo_get
        target = authenticate(get, env, event)
        need(env.get("GITHUB_SHA") == target, "SOURCE_RACE")
        local = env.get("LOCALAPPDATA")
        need(type(local) is str and bool(local) and Path(local).is_absolute(),
             "ORIGINAL_OWNER_LOCAL_ROOT_UNAVAILABLE")
        db = Path(local) / "FORGE-F139" / "state.sqlite"
        result = classify(db)
        need(get("repos/" + REPO + "/branches/main")
             .get("commit", {}).get("sha") == target,
             "POSTREADBACK_MAIN_DRIFT")
        print(LABEL + result)
        return 0
    except Exception:
        # Failure details (including potentially sensitive paths/SIDs/command
        # lines) are deliberately not printed. No retry after uncertainty.
        print(LABEL + "UNCLASSIFIED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""One-shot staged localization of a failed original owner task readback.

Unchanged historical PowerShell task guard called at most once. Bounded class
only; never print raw responses, paths, SIDs, commands or task state. No SQLite
content read, task mutation, restart, queue, science or source transition.
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
from f139 import nci04_v41_hybrid_forward_owner_profile as guard

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
ISSUE = 807
PREV_COMMENT = 6886931814
PREV_RUN = 43660563209
PREV_SHA = "396a1a36aec66a47d798ac677bf3ed473c3fa27f"
PREV_BODY = "F139-V38-HELD-TASK-GUARD-DIAG " + PREV_SHA + " 6886633573"
PREFIX = "F139-V38-HELD-TASK-STAGE-DIAG "
LABEL = "F139_V38_HELD_TASK_STAGE="
SHA = re.compile(r"[0-9a-f]{40}\Z")
DECIMAL = re.compile(r"[1-9][0-9]*\Z")
CODES = frozenset(range(41, 52))
ALLOWED_RESULTS = frozenset({
    "AUTH_INVARIANT", "AUTH_PROVIDER", "TASK_PREREQUISITE",
    "TASK_UNEXPECTED", "SHELL_TIMEOUT", "SHELL_UNEXPECTED",
    "POSTCHECK_DENIED", "EXIT_41", "EXIT_42", "EXIT_43", "EXIT_44",
    "EXIT_45", "EXIT_46", "EXIT_47", "EXIT_48", "EXIT_49",
    "EXIT_50", "EXIT_51", "PASS_PREDICATES_ONLY", "UNCLASSIFIED",
})


class StageDenied(ValueError):
    pass


def need(value):
    if not value:
        raise StageDenied("F139_V38_STAGE_DENIED")


def authenticate(get, env: dict, event: dict) -> str:
    """Authenticate a new original-owner event and exact two prior failures."""
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
    failed = get("repos/" + REPO + "/actions/runs/" + str(PREV_RUN))
    need(type(failed) is dict and failed.get("id") == PREV_RUN
         and failed.get("head_sha") == PREV_SHA
         and failed.get("run_attempt") == 1
         and failed.get("event") == "issue_comment"
         and failed.get("status") == "completed"
         and failed.get("conclusion") == "failure"
         and type(failed.get("actor")) is dict
         and failed["actor"].get("login") == OWNER)
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


def classify(db_path: Path, *, reader=guard.readback,
             execute=subprocess.run) -> str:
    """Use original unedited task PowerShell exactly once; no raw result output."""
    calls = 0
    code = None

    def observed(argv, **kwargs):
        nonlocal calls, code
        calls += 1
        if calls != 1:
            raise StageDenied("SECOND_TASK_PROBE_FORBIDDEN")
        result = execute(argv, **kwargs)
        code = result.returncode
        return result

    try:
        passed = reader(db_path, runner=observed)
    except guard.HeldTaskIdentityDenied as failure:
        msg = str(failure)
        if calls == 0:
            return "TASK_PREREQUISITE"
        if msg == "F139_HYBRID_V38_HELD_TASK_READBACK_TIMEOUT":
            return "SHELL_TIMEOUT"
        if (calls == 1 and code in CODES
                and msg == "F139_HYBRID_V38_HELD_TASK_"
                           "SID_SOURCE_OR_QUIESCENCE_NOT_VERIFIED"):
            return "EXIT_" + str(code)
        return "SHELL_UNEXPECTED"
    except (subprocess.TimeoutExpired, OSError):
        return "SHELL_TIMEOUT" if calls == 1 else "TASK_UNEXPECTED"
    except Exception:
        return "TASK_UNEXPECTED"
    if calls == 1 and code == 0 and passed is True:
        return "PASS_PREDICATES_ONLY"
    return "TASK_UNEXPECTED"


def run(env, event, get, *, reader=guard.readback, execute=subprocess.run):
    """Split authentication, original probe and post-check without disclosure."""
    if sys.platform != "win32" or os.name != "nt":
        return "AUTH_INVARIANT"
    try:
        target = authenticate(get, env, event)
    except StageDenied:
        return "AUTH_INVARIANT"
    except Exception:
        return "AUTH_PROVIDER"
    try:
        local = env.get("LOCALAPPDATA")
        if type(local) is not str or not local or not Path(local).is_absolute():
            return "TASK_PREREQUISITE"
        db_path = Path(local) / "FORGE-F139" / "state.sqlite"
        result = classify(db_path, reader=reader, execute=execute)
    except Exception:
        return "TASK_UNEXPECTED"
    try:
        latest = get("repos/" + REPO + "/branches/main")
        if (type(latest) is not dict
                or latest.get("commit", {}).get("sha") != target):
            return "POSTCHECK_DENIED"
    except Exception:
        return "POSTCHECK_DENIED"
    return result if result in ALLOWED_RESULTS else "UNCLASSIFIED"


def main():
    """One bounded public class, zero private content, no retry."""
    try:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if type(event_path) is not str or not Path(event_path).is_file():
            result = "AUTH_INVARIANT"
        else:
            try:
                event = json.loads(Path(event_path).read_text("utf-8"),
                                   object_pairs_hook=decode_unique)
            except Exception:
                event = {}
            result = run(dict(os.environ), event,
                         GitHub().native_repo_get)
    except Exception:
        result = "UNCLASSIFIED"
    if result not in ALLOWED_RESULTS:
        result = "UNCLASSIFIED"
    print(LABEL + result)
    # Even an informative code is not original owner acceptance. Only
    # classification itself succeeds; denied authorization fails closed.
    return 1 if result in ("AUTH_INVARIANT", "AUTH_PROVIDER",
                           "POSTCHECK_DENIED", "UNCLASSIFIED") else 0


if __name__ == "__main__":
    raise SystemExit(main())

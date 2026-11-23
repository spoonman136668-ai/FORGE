"""One-shot, read-only GitHub CLI provider comparison on the original Windows runner.

No task, SQLite, controller, scheduler, or local owner source is inspected.
Never print request URLs, response bytes, credentials or raw CLI diagnostics.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from f139.nci04_owner_issue import decode_unique

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PREV_COMMENT = 6892377331
V4_RUN, V3_RUN = 43699712064, 43696957491
V4_SHA = "7b2b6bbd707ba80613b6f305615e9e8167b7ffaa"
V3_SHA = "5368464e6232cb503678353040eb88d302a40f7f"
PREFIX = "F139-V39-ACTIONS-GET-DIAG "
LABEL = "F139_V39_ACTIONS_GET_DIAG="
SHA = re.compile(r"[0-9a-f]{40}\Z")
HTTP = re.compile(r"\bhttp(?:/\d(?:\.\d)?)?\s*[: ]\s*([45]\d\d)\b", re.I)
MAX_STDOUT = 256 * 1024
ALLOWED_RESULTS = frozenset({
    "OK", "HTTP_AUTH", "HTTP_NOT_FOUND", "HTTP_LIMIT", "HTTP_SERVER",
    "HTTP_OTHER", "RATE_LIMIT", "TRANSPORT", "CLI_AUTH", "CLI_ARGUMENT",
    "CLI_OTHER", "CLI_MISSING", "SPAWN_FAILED", "TIMEOUT", "INVALID_JSON",
    "INVALID_RESPONSE", "OVERSIZE", "INTERNAL",
})


class Denied(ValueError):
    pass


def need(condition):
    if not condition:
        raise Denied("V39_READONLY_OWNER_INTENT_DENIED")


def authorize(env, event):
    """Bind GitHub-signed owner event to protected original two-lane policy."""
    need(type(env) is dict and type(event) is dict)
    head = env.get("GITHUB_SHA")
    need(type(head) is str and SHA.fullmatch(head) is not None
         and head != V4_SHA and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and type(env.get("GH_TOKEN")) is str and bool(env["GH_TOKEN"])
         and not env.get("OPENAI_API_KEY"))
    issue, sender, comment = (event.get(k) for k in ("issue", "sender", "comment"))
    need(event.get("action") == "created" and type(issue) is dict
         and issue.get("number") == 807 and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > PREV_COMMENT
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == PREFIX + head + " " + str(PREV_COMMENT)
         and type(issue.get("body")) is str)
    policy = json.loads(issue["body"], object_pairs_hook=decode_unique)
    need(type(policy) is dict
         and policy.get("lanes") == ["Wingless", "Yggdrasil"]
         and policy.get("scientific_first_use") is False
         and policy.get("new_controller") is False
         and policy.get("new_scheduler") is False
         and policy.get("new_queue") is False
         and policy.get("paid_model_calls") == 0)
    return comment["id"], head


def classify_stderr(stderr):
    """Return only fixed categories, never any raw stderr or host details."""
    if type(stderr) is not bytes:
        return "CLI_OTHER"
    data = stderr[:8192].decode("utf-8", "replace").lower()
    match = HTTP.search(data)
    if match:
        status = int(match.group(1))
        if status in (401, 403):
            return "HTTP_AUTH"
        if status == 404:
            return "HTTP_NOT_FOUND"
        if status == 429:
            return "HTTP_LIMIT"
        return "HTTP_SERVER" if status >= 500 else "HTTP_OTHER"
    if "rate limit" in data or "abuse detection" in data:
        return "RATE_LIMIT"
    if any(s in data for s in ("connection reset", "connection refused",
          "connection timed out", "could not resolve", "network is unreachable",
          "tls handshake", "unexpected eof", "server closed connection",
          "connectex:", "dial tcp", "i/o timeout")):
        return "TRANSPORT"
    if any(s in data for s in ("gh auth login", "authentication required",
          "not logged in", "please authenticate", "no authentication token")):
        return "CLI_AUTH"
    if any(s in data for s in ("unknown flag", "unknown command",
          "invalid argument", "invalid api endpoint", "not enough arguments")):
        return "CLI_ARGUMENT"
    return "CLI_OTHER"


def gh_read(route, expected, *, runner=subprocess.run):
    """One same-form gh api GET as original provider; no retry or mutation."""
    need(type(route) is str and type(expected) is dict)
    root = "repos/" + REPO + "/"
    if expected.get("kind") == "comment":
        need(type(expected.get("id")) is int
             and expected["id"] > PREV_COMMENT
             and route == root + "issues/comments/" + str(expected["id"]))
    elif expected.get("kind") == "run":
        need(expected.get("id") in (V4_RUN, V3_RUN)
             and route == root + "actions/runs/" + str(expected["id"]))
    else:
        raise Denied("V39_NOT_AN_APPROVED_GET_ROUTE")
    if runner is subprocess.run and not shutil.which("gh"):
        return "CLI_MISSING"
    try:
        proc = runner(["gh", "api", route], stdin=subprocess.DEVNULL,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      timeout=35, check=False)
    except FileNotFoundError:
        return "CLI_MISSING"
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except OSError:
        return "SPAWN_FAILED"
    except Exception:
        return "INTERNAL"
    if type(proc.returncode) is not int or proc.returncode != 0:
        return classify_stderr(proc.stderr)
    if type(proc.stdout) is not bytes:
        return "INVALID_RESPONSE"
    if len(proc.stdout) > MAX_STDOUT:
        return "OVERSIZE"
    try:
        payload = json.loads(proc.stdout)
    except (ValueError, UnicodeDecodeError, TypeError):
        return "INVALID_JSON"
    if type(payload) is not dict or payload.get("id") != expected["id"]:
        return "INVALID_RESPONSE"
    if expected["kind"] == "comment":
        valid = (payload.get("body") == expected["body"]
                 and payload.get("author_association") == "OWNER"
                 and type(payload.get("user")) is dict
                 and payload["user"].get("login") == OWNER)
    else:
        valid = (payload.get("head_sha") == expected["sha"]
                 and payload.get("run_attempt") == 1
                 and payload.get("event") == "issue_comment"
                 and payload.get("status") == "completed"
                 and payload.get("conclusion") == expected["conclusion"]
                 and type(payload.get("actor")) is dict
                 and payload["actor"].get("login") == OWNER)
    return "OK" if valid else "INVALID_RESPONSE"


def diagnose(env, event, *, reader=gh_read):
    """Exactly three GETs, only fixed labels; not original task acceptance."""
    comment, head = authorize(env, event)
    root = "repos/" + REPO + "/"
    requests = (
        ("C", root + "issues/comments/" + str(comment),
         {"kind": "comment", "id": comment,
          "body": PREFIX + head + " " + str(PREV_COMMENT)}),
        ("V4", root + "actions/runs/" + str(V4_RUN),
         {"kind": "run", "id": V4_RUN, "sha": V4_SHA,
          "conclusion": "failure"}),
        ("V3", root + "actions/runs/" + str(V3_RUN),
         {"kind": "run", "id": V3_RUN, "sha": V3_SHA,
          "conclusion": "success"}),
    )
    labels = []
    for name, route, expected in requests:
        try:
            value = reader(route, expected)
        except Exception:
            value = "INTERNAL"
        labels.append(name + "_" +
                      (value if value in ALLOWED_RESULTS else "INTERNAL"))
    return "-".join(labels)


def main():
    try:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if (sys.platform != "win32" or os.name != "nt"
            or type(event_path) is not str
            or not Path(event_path).is_file()
            or Path(event_path).stat().st_size > 1000000):
            raise Denied("BAD_HOST")
        event = json.loads(Path(event_path).read_text("utf-8"),
                           object_pairs_hook=decode_unique)
        result = diagnose(dict(os.environ), event)
    except Exception:
        print(LABEL + "AUTH_DENIED", flush=True)
        return 1
    print(LABEL + result, flush=True)
    print("F139_V39_TASK_INSPECTED=FALSE", flush=True)
    print("F139_V39_SQLITE_OPENED=FALSE", flush=True)
    print("F139_V39_GH_API_GET_ONLY=TRUE", flush=True)
    print("F139_V39_SCIENTIFIC_FIRST_USE=FALSE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

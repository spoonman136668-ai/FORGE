"""Read-only exact-source release authentication for FORGE V41->Hybrid.

No original-owner writes, scheduler, workflow registration, deployment,
Hybrid admission or science first-use. A comment is NEVER commit authority.
"""
from __future__ import annotations
import re

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
BASE = "b98dae4c6b0a78b145cfca06aeb465d6d85d3597"
PR = 1757
BRANCH = "engineering/f139-v41-hybrid-v37-successor-20261114"
PREFIX = "F139-HYBRID-V41-SOURCE-READINESS "
PAIR = "F139-HYBRID-V41-PAUSE-HOLD "
BACKUP = "F139-HYBRID-V41-BACKUP-ONLY "
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
CI = frozenset({
    "FORGE public Linux and Windows qualification",
    "FORGE F139 native Windows controller qualification",
    "FORGE F139-D hosted development rehearsal",
})


class HybridSuccessorDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise HybridSuccessorDenied("F139_HYBRID_SUCCESSOR_" + reason)


def source_identity(get, target):
    prefix = "repos/" + REPO + "/"
    main = get(prefix + "branches/main")
    pr = get(prefix + "pulls/1757")
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and type(main.get("commit")) is dict
         and main["commit"].get("sha") == target
         and type(pr) is dict and pr.get("number") == PR
         and pr.get("state") == "closed" and pr.get("merged") is True
         and pr.get("merge_commit_sha") == target
         and type(pr.get("user")) is dict
         and pr["user"].get("login") == OWNER
         and type(pr.get("head")) is dict
         and pr["head"].get("ref") == BRANCH
         and type(pr["head"].get("repo")) is dict
         and pr["head"]["repo"].get("full_name") == REPO
         and type(pr["head"].get("sha")) is str
         and SHA40.fullmatch(pr["head"]["sha"]) is not None
         and type(pr.get("base")) is dict
         and pr["base"].get("ref") == "main"
         and pr["base"].get("sha") in (BASE, target)
         and type(pr["base"].get("repo")) is dict
         and pr["base"]["repo"].get("full_name") == REPO,
         "EXACT_MERGED_PR1757_PROTECTED_MAIN_REQUIRED")
    head = pr["head"]["sha"]
    comparison = get(prefix + "compare/" + BASE + "..." + target +
                     "?per_page=1&page=2")
    need(type(comparison) is dict
         and comparison.get("status") == "ahead"
         and type(comparison.get("ahead_by")) is int
         and comparison["ahead_by"] > 0
         and type(comparison.get("behind_by")) is int
         and comparison["behind_by"] == 0
         and type(comparison.get("merge_base_commit")) is dict
         and comparison["merge_base_commit"].get("sha") == BASE,
         "PROTECTED_BASE_ANCESTRY_DRIFT")
    left, right = [get(prefix + "git/commits/" + sha)
                   for sha in (target, head)]
    need(all(type(doc) is dict and doc.get("sha") == sha
             and type(doc.get("tree")) is dict
             and type(doc["tree"].get("sha")) is str
             and SHA40.fullmatch(doc["tree"]["sha"]) is not None
             for doc, sha in ((left, target), (right, head)))
         and left["tree"]["sha"] == right["tree"]["sha"],
         "MERGED_TREE_DIFFERS_FROM_QUALIFIED_HEAD")
    return head, left["tree"]["sha"]


def _ci_run(row, sha, event, branch):
    return (type(row) is dict and row.get("head_sha") == sha
            and row.get("event") == event
            and row.get("head_branch") == branch
            and row.get("status") == "completed"
            and row.get("conclusion") == "success"
            and type(row.get("run_attempt")) is int
            and row["run_attempt"] == 1
            and type(row.get("id")) is int and row["id"] > 0
            and type(row.get("actor")) is dict
            and row["actor"].get("login") == OWNER)


def _runs(get, route):
    raw = get(route)
    need(type(raw) is dict and type(raw.get("workflow_runs")) is list
         and len(raw["workflow_runs"]) <= 100, "CI_INVENTORY_INVALID")
    return raw["workflow_runs"]


def require_successor_source(get, target, *, env=None):
    """Read-only merged-source and exact-SHA mandatory CI proof."""
    need(callable(get) and type(target) is str
         and SHA40.fullmatch(target) is not None and target != BASE
         and target != "1a40fe4e3ec6e93a1631d59863b95e90981d734e",
         "TARGET_SHA_INVALID")
    if env is not None:
        need(type(env) is dict
             and env.get("GITHUB_REPOSITORY") == REPO
             and env.get("GITHUB_ACTOR") == OWNER
             and env.get("GITHUB_EVENT_NAME") == "issue_comment"
             and env.get("GITHUB_REF") == "refs/heads/main"
             and env.get("GITHUB_SHA") == target
             and env.get("GITHUB_RUN_ATTEMPT") == "1"
             and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
             and type(env.get("GITHUB_RUN_ID")) is str
             and re.fullmatch(r"[1-9][0-9]*", env["GITHUB_RUN_ID"])
             and not env.get("OPENAI_API_KEY"),
             "ORIGINAL_FIRST_ATTEMPT_REQUIRED")
    head, tree = source_identity(get, target)
    prefix = "repos/" + REPO + "/actions/runs?"
    pr_runs = _runs(get, prefix + "head_sha=" + head +
                    "&event=pull_request&per_page=100")
    passed = {}
    for row in pr_runs:
        if type(row) is dict and row.get("name") in CI:
            name = row["name"]
            need(name not in passed and _ci_run(
                row, head, "pull_request", BRANCH),
                "PR_CI_INCOMPLETE_DUPLICATE_OR_REPLAY")
            passed[name] = row["id"]
    need(set(passed) == CI, "ALL_THREE_PR_WORKFLOWS_REQUIRED")
    push_runs = _runs(get, prefix + "head_sha=" + target +
                      "&event=push&branch=main&per_page=100")
    post = [row for row in push_runs if type(row) is dict and
            row.get("name") == "FORGE public Linux and Windows qualification"]
    need(len(post) == 1 and _ci_run(
        post[0], target, "push", "main"),
        "POSTMERGE_MAIN_CI_REQUIRED")
    need(source_identity(get, target) == (head, tree),
         "PROTECTED_MAIN_OR_TREE_MOVED")
    return {
        "schema": "forge.f139.hybrid-successor.protected-main.v1",
        "source_sha": target, "source_tree_sha": tree,
        "qualified_pr_sha": head,
        "pr_run_ids": dict(sorted(passed.items())),
        "main_run_id": post[0]["id"],
        "source_transition_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False, "new_dispatches": 0,
    }


def _comment(get, id, body):
    doc = get("repos/" + REPO + "/issues/comments/" + str(id))
    need(type(doc) is dict and type(doc.get("id")) is int
         and doc["id"] == id and doc.get("body") == body
         and type(doc.get("user")) is dict
         and doc["user"].get("login") == OWNER
         and doc.get("author_association") == "OWNER"
         and doc.get("issue_url") ==
             "https://api.github.com/repos/" + REPO + "/issues/807"
         and type(doc.get("created_at")) is str
         and STAMP.fullmatch(doc["created_at"]) is not None
         and doc.get("updated_at", doc["created_at"]) == doc["created_at"],
         "EXACT_UNEDITED_OWNER_COMMENT_REQUIRED")
    return doc["created_at"]


def authenticate_owner_intent(get, env, event, *, target, run_id,
                              manifest_sha, approval_id):
    """Three ordered original-owner comments; evidence, never write authority."""
    need(type(run_id) is int and run_id > 0
         and type(approval_id) is int and approval_id > 0
         and type(manifest_sha) is str and SHA64.fullmatch(manifest_sha),
         "TARGET_BOUND_SEALED_BACKUP_REQUIRED")
    need(type(env) is dict and env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_ACTOR") == OWNER
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == target
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and not env.get("OPENAI_API_KEY")
         and type(event) is dict, "ORIGINAL_OWNER_EVENT_REQUIRED")
    issue, comment, sender = (event.get(k) for k in ("issue", "comment", "sender"))
    body = (PREFIX + target + " " + str(run_id) + " "
            + manifest_sha + " " + str(approval_id))
    need(event.get("action") == "created"
         and type(issue) is dict and issue.get("number") == 807
         and "pull_request" not in issue
         and type(issue.get("user")) is dict
         and issue["user"].get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0 and comment["id"] != approval_id
         and comment.get("body") == body
         and comment.get("author_association") == "OWNER"
         and type(comment.get("user")) is dict
         and comment["user"].get("login") == OWNER,
         "EXPLICIT_SOURCE_READINESS_COMMENT_REQUIRED")
    release_id = comment["id"]
    for _ in range(2):
        release_time = _comment(get, release_id, body)
        need(release_time == comment.get("created_at"),
             "RELEASE_COMMENT_READBACK_MOVED")
        approval = get("repos/" + REPO + "/issues/comments/" + str(approval_id))
        need(type(approval) is dict and type(approval.get("body")) is str,
             "PAIRED_APPROVAL_UNREADABLE")
        match = re.fullmatch(
            re.escape(PAIR + target) + r" ([1-9][0-9]*)",
            approval["body"])
        need(match is not None, "PAIRED_APPROVAL_TARGET_DRIFT")
        backup_id = int(match.group(1))
        need(backup_id not in (approval_id, release_id),
             "THREE_INDEPENDENT_COMMENTS_REQUIRED")
        approval_time = _comment(get, approval_id, approval["body"])
        backup_time = _comment(get, backup_id, BACKUP + target)
        need(backup_time < approval_time < release_time,
             "THREE_OWNER_COMMENTS_NOT_ORDERED")
    return {"owner_event_id": release_id, "backup_run_id": run_id,
            "backup_manifest_sha256": manifest_sha,
            "backup_request_comment_id": backup_id,
            "paired_approval_id": approval_id,
            "to_source_sha": target,
            "source_transition_authorized": False,
            "hybrid_admission": False,
            "scientific_first_use": False}

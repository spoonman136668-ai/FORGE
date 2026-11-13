"""Exact owner-host backup-only V41 route, no task/policy/source mutation."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139 import nci04_v41_catalog_recovery_preflight as preflight
from f139 import nci04_v41_offline_cold_bundle as cold
from f139 import nci04_v41_pending_custody as pending

REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
PREFIX = "F139-V41-PAUSE-BACKUP-RESUME "
SHA = re.compile(r"[a-f0-9]{40}\Z")
# Original first qualified recovery anchor, not a permanently pinned target.
AUDITED_COLD_BACKUP_MERGE = "616b87b01c8abd37ee0e0a2d5b5571c51272ba9e"


class OwnerBackupDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OwnerBackupDenied("F139_V41_OWNER_BACKUP_" + reason)


def verify_owner_event(env, event, get, *, target):
    """Check owner issue comment twice; this is NOT deployment approval."""
    required = {
        "GITHUB_REPOSITORY": REPO, "GITHUB_ACTOR": OWNER,
        "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_REF": "refs/heads/main",
        "RUNNER_NAME": "FORGE-CODEX-REMOTE", "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": target,
    }
    need(type(env) is dict and type(event) is dict and callable(get)
         and type(target) is str and SHA.fullmatch(target)
         and all(env.get(k) == v for k, v in required.items())
         and type(env.get("GITHUB_RUN_ID")) is str
         and env["GITHUB_RUN_ID"].isdigit() and int(env["GITHUB_RUN_ID"]) > 0,
         "WRONG_OWNER_RUN")
    issue, comment, sender = (event.get(k) for k in ("issue", "comment", "sender"))
    need(event.get("action") == "created" and type(issue) is dict
         and issue.get("number") == 807 and "pull_request" not in issue
         and issue.get("user", {}).get("login") == OWNER
         and type(sender) is dict and sender.get("login") == OWNER
         and type(comment) is dict and type(comment.get("id")) is int
         and comment["id"] > 0 and comment.get("user", {}).get("login") == OWNER
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == PREFIX + target,
         "OWNER_COMMENT_REQUIRED")
    route = "repos/" + REPO + "/issues/comments/" + str(comment["id"])
    for _ in range(2):
        remote = get(route)
        need(type(remote) is dict and remote.get("id") == comment["id"]
             and remote.get("user", {}).get("login") == OWNER
             and remote.get("author_association") == "OWNER"
             and remote.get("body") == PREFIX + target
             and remote.get("issue_url") ==
                 "https://api.github.com/repos/" + REPO + "/issues/807"
             and remote.get("created_at") == comment.get("created_at"),
             "OWNER_COMMENT_READBACK_DRIFT")
    return int(env["GITHUB_RUN_ID"])


def verify_qualified_main(get, target):
    """Verify current protected release is a descendant of the audited fix.

    The first recovery run used PR #1740. Requiring the *current* target
    to be that one historical merge SHA permanently blocks subsequent
    protected, fully qualified V41 release candidates. Preserve the audit
    anchor, prove exact ancestry, and validate the candidate's own first-
    attempt postmerge Linux/Windows + signed GitHub-origin runs.
    This gate does NOT authorize owner pause, source transition or first-use.
    """
    need(callable(get) and type(target) is str and SHA.fullmatch(target),
         "QUALIFICATION_ARGUMENTS")
    prefix = "repos/" + REPO + "/"
    original = get(prefix + "pulls/1740")
    need(type(original) is dict and original.get("number") == 1740
         and original.get("merged") is True
         and original.get("merge_commit_sha") == AUDITED_COLD_BACKUP_MERGE
         and original.get("user", {}).get("login") == OWNER
         and original.get("base", {}).get("ref") == "main"
         and type(original.get("head", {}).get("sha")) is str
         and SHA.fullmatch(original["head"]["sha"]),
         "AUDITED_NEGATIVE_CUSTODY_MERGE_MISSING")
    main = get(prefix + "branches/main")
    need(type(main) is dict and main.get("protected") is True
         and main.get("commit", {}).get("sha") == target,
         "CURRENT_PROTECTED_MAIN_REQUIRED")
    compare = get(prefix + "compare/" + AUDITED_COLD_BACKUP_MERGE
                  + "..." + target + "?per_page=1&page=2")
    need(type(compare) is dict
         and compare.get("status") in ("ahead", "identical")
         and type(compare.get("ahead_by")) is int
         and compare["ahead_by"] >= 0
         and compare.get("behind_by") == 0
         and compare.get("merge_base_commit", {}).get("sha") ==
             AUDITED_COLD_BACKUP_MERGE
         and (compare["status"] == "identical") ==
             (target == AUDITED_COLD_BACKUP_MERGE),
         "AUDITED_RELEASE_ANCESTRY_DRIFT")
    commit = get(prefix + "git/commits/" + target)
    need(type(commit) is dict and commit.get("sha") == target
         and type(commit.get("tree", {}).get("sha")) is str
         and SHA.fullmatch(commit["tree"]["sha"]),
         "TARGET_COMMIT_OR_TREE_DRIFT")
    report = get(prefix + "actions/runs?head_sha=" +
                 target + "&event=push&branch=main&per_page=30")
    need(type(report) is dict
         and type(report.get("workflow_runs")) is list
         and len(report["workflow_runs"]) <= 30,
         "POSTMERGE_RUN_CATALOG_INVALID")
    wanted = (
        "FORGE public Linux and Windows qualification",
        "FORGE F73 protected-main cryptographic origin (no science permission)",
    )
    for name in wanted:
        selected = [row for row in report["workflow_runs"]
                    if type(row) is dict and row.get("name") == name
                    and row.get("head_sha") == target
                    and row.get("head_branch") == "main"
                    and row.get("event") == "push"]
        need(len(selected) == 1
             and selected[0].get("status") == "completed"
             and selected[0].get("conclusion") == "success"
             and selected[0].get("run_attempt") == 1
             and selected[0].get("actor", {}).get("login") == OWNER
             and type(selected[0].get("id")) is int
             and selected[0]["id"] > 0,
             "QUALIFIED_POSTMERGE_RUN_REQUIRED")
    # Read the protected target again before returning; the caller will
    # independently recheck it after detached backup and before resuming.
    again = get(prefix + "branches/main")
    need(type(again) is dict and again == main,
         "MAIN_MOVED_DURING_QUALIFICATION")
    return True

def preflight_only(path, env, event, api, *, target):
    """Read-only exact owner and postmerge CI authorization before task pause."""
    need(type(api) is GitHub and isinstance(path, Path) and path.is_absolute()
         and path.name == "state.sqlite" and path.is_file()
         and not path.is_symlink() and type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute()
         and path.resolve() ==
             (Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite").resolve(),
         "MAINTENANCE_PROFILE_DRIFT")
    run_id = verify_owner_event(env, event, api.native_repo_get, target=target)
    verify_qualified_main(api.native_repo_get, target)
    need(api.protected_main() == target, "MAINTENANCE_MAIN_DRIFT")
    policy = api.native_repo_get("repos/" + REPO + "/issues/807")
    try:
        p = json.loads(policy["body"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OwnerBackupDenied("F139_V41_OWNER_BACKUP_POLICY_UNAVAILABLE") from exc
    need(type(p) is dict
         and p.get("schema") == "forge.f139.native-autonomy-feed-owner-policy.v1"
         and p.get("enabled") is True
         and p.get("source_sha") == preflight.OWNER_SOURCE
         and p.get("lanes") == ["Wingless", "Yggdrasil"]
         and p.get("scientific_first_use") is False
         and p.get("paid_model_calls") == 0
         and p.get("new_controller") is False
         and p.get("new_scheduler") is False
         and p.get("new_queue") is False, "MAINTENANCE_OWNER_POLICY_DRIFT")
    return dict(schema="forge.f139.v41.owner-maintenance-preflight.v1",
                run_id=run_id, original_source_sha=preflight.OWNER_SOURCE,
                target_sha=target, same_task_pause_resume_only=True,
                source_transition_authorized=False, owner_mutations=0,
                scientific_first_use=False, hybrid_admission=False,
                new_dispatches=0)


def backup_only(path, env, event, api, *, target):
    """Runs only after existing G54 workflow proves task disabled and SID."""
    need(type(api) is GitHub and isinstance(path, Path) and path.is_absolute()
         and path.name == "state.sqlite" and path.is_file()
         and not path.is_symlink()
         and type(env.get("LOCALAPPDATA")) is str
         and Path(env["LOCALAPPDATA"]).is_absolute()
         and path.resolve() ==
             (Path(env["LOCALAPPDATA"]) / "FORGE-F139" / "state.sqlite").resolve(),
         "ORIGINAL_PROFILE_SCOPE")
    run_id = verify_owner_event(env, event, api.native_repo_get, target=target)
    verify_qualified_main(api.native_repo_get, target)
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            original = db.meta().copy()
            changes = db.conn.total_changes
            proposal = pending.inspect_never_admitted(db, api)
            need(proposal["issue_number"] == 1715
                 and proposal["disposition"] == "UNADMITTED_RETAINED_NO_DISPATCH"
                 and proposal["original_head_seq"] == original["head_seq"]
                 and proposal["original_head_sha256"] == original["head_hash"],
                 "PENDING_ORIGINAL_CUSTODY_DRIFT")
            receipt = cold.stage_offline_cold_bundle(
                db, api.native_repo_get, target=target, run_id=run_id)
            restored = cold.verify_sealed_bundle_offline(
                path.parent / ("f139-v41-before-" + str(run_id)),
                expected_manifest_sha256=receipt["manifest_sha256"], target=target,
                run_id=run_id, expected_head_seq=original["head_seq"],
                expected_head_sha256=original["head_hash"])
            after = pending.inspect_never_admitted(db, api)
            need(restored["independent_restore_verified"] is True
                 and restored["source_transition_authorized"] is False
                 and after["semantic_identity_sha256"] ==
                     proposal["semantic_identity_sha256"]
                 and db.meta() == original and db.conn.total_changes == changes == 0,
                 "RESTORE_OR_ORIGINAL_DRIFT")
    verify_owner_event(env, event, api.native_repo_get, target=target)
    verify_qualified_main(api.native_repo_get, target)
    need(api.protected_main() == target, "MAIN_MOVED")
    policy = api.native_repo_get("repos/" + REPO + "/issues/807")
    try:
        p = json.loads(policy["body"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OwnerBackupDenied("F139_V41_OWNER_BACKUP_POLICY_UNREADABLE") from exc
    need(type(p) is dict and p.get("enabled") is True
         and p.get("source_sha") == preflight.OWNER_SOURCE
         and p.get("scientific_first_use") is False, "POLICY_MOVED")
    return dict(schema="forge.f139.v41.original-host-backup-only.v1",
                target_sha=target, original_source_sha=preflight.OWNER_SOURCE,
                original_head_seq=original["head_seq"],
                original_head_sha256=original["head_hash"],
                pending_issue_number=proposal["issue_number"],
                manifest_sha256=receipt["manifest_sha256"],
                run_id=run_id, detached_restore_verified=True,
                source_transition_authorized=False, release_qualified=False,
                reissue_authorized=False, scientific_first_use=False,
                hybrid_admission=False, owner_mutations=0,
                remote_writes=0, new_dispatches=0)


def main(argv=None, *, env=None, event=None):
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--target", required=True)
    p.add_argument('--preflight-only', action='store_true')
    args = p.parse_args(argv)
    values = dict(os.environ if env is None else env)
    need(os.name == "nt", "WINDOWS_ONLY")
    if event is None:
        file = values.get("GITHUB_EVENT_PATH")
        need(type(file) is str and Path(file).is_file(), "EVENT_FILE_REQUIRED")
        event = json.loads(Path(file).read_text(encoding="utf-8"))
    if args.preflight_only:
        result = preflight_only(args.db, values, event, GitHub(), target=args.target)
        print("F139_V41_MAINTENANCE_PREFLIGHT=" + canonical(result).decode("ascii"))
    else:
        result = backup_only(args.db, values, event, GitHub(), target=args.target)
        print("F139_V41_BACKUP_ONLY=" + canonical(result).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

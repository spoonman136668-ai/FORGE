"""Source-only original Windows V40 ledger and pending #1715 acceptance.

Reuses the existing read-only status route and kernel owner mutex. This
module never creates a task, backup, source transition, issue or release.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139 import nci04_v41_catalog_recovery_preflight as source
from f139 import nci04_v41_pending_custody as pending

SCHEMA = "forge.f139.v41.original-locked-readonly-status.v1"
PREFIX = "F139-V9-STATUS "
SHA = re.compile(r"[0-9a-f]{40}\Z")


class V41StatusDenied(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise V41StatusDenied("F139_V41_OWNER_STATUS_" + code)


def inspect_original(path, api, *, target):
    """Actual original read-only ledger + authenticated catalog, no cutover."""
    path = Path(path)
    need(type(api) is GitHub
         and type(target) is str and SHA.fullmatch(target)
         and target != source.OWNER_SOURCE
         and path.is_absolute() and path.is_file()
         and not path.is_symlink() and path.name == "state.sqlite",
         "ARGUMENT_OR_DATABASE_SCOPE")

    candidate = source.source_preflight(api.native_repo_get, target)
    # The original mutex is held only while checking original SQLite and
    # the source-authenticated unadmitted issue. No background ownership.
    with SingleOwner(path.with_suffix(".lock")):
        with closing(Database.open_readonly(path)) as db:
            db.conn.execute("BEGIN")
            try:
                before = db.meta().copy()
                count = db.conn.total_changes
                ledger = source.original_ledger_preflight(db)
                issue = pending.inspect_never_admitted(db, api)
                need(db.meta() == before and db.conn.total_changes == count
                     and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
                     and ledger["original_head_seq"] == issue["original_head_seq"]
                     and ledger["original_head_sha256"] == issue["original_head_sha256"]
                     and issue["issue_number"] == 1715
                     and issue["disposition"] == "UNADMITTED_RETAINED_NO_DISPATCH"
                     and issue["new_dispatches"] == 0
                     and issue["owner_mutations"] == 0,
                     "LEDGER_OR_PENDING_CUSTODY_DRIFT")
            finally:
                db.conn.rollback()

    # Verify moving remote anchors after releasing the original mutex.
    need(api.protected_main() == target, "MAIN_MOVED_AFTER_ORIGINAL_READ")
    policy = api.native_repo_get("repos/" + source.REPO + "/issues/807")
    try:
        data = json.loads(policy["body"])
    except (TypeError, ValueError, KeyError, UnicodeError) as exc:
        raise V41StatusDenied("F139_V41_OWNER_STATUS_POLICY_UNREADABLE") from exc
    need(type(data) is dict and data.get("enabled") is True
         and data.get("source_sha") == source.OWNER_SOURCE
         and data.get("scientific_first_use") is False
         and data.get("paid_model_calls") == 0,
         "POLICY_MOVED_AFTER_ORIGINAL_READ")

    return {
        "schema": SCHEMA,
        "target_source_sha": target,
        "installed_source_sha": source.OWNER_SOURCE,
        "original_head_seq": ledger["original_head_seq"],
        "original_head_sha256": ledger["original_head_sha256"],
        "verified_historical_tasks": ledger["verified_historical_tasks"],
        "quarantined_historical_tasks": ledger["quarantined_historical_tasks"],
        "spent_free_reasoner_calls": ledger["spent_free_reasoner_calls"],
        "eligible_issue_page_sizes": candidate["issues_per_page"],
        "eligible_unique_issues": candidate["unique_eligible_issues"],
        "pending_issue_number": issue["issue_number"],
        "pending_issue_id": issue["issue_id"],
        "pending_semantic_identity_sha256": issue["semantic_identity_sha256"],
        "sqlite_query_only": True,
        "original_owner_mutations": 0,
        "remote_writes": 0,
        "new_dispatches": 0,
        "original_cold_backup_qualified": False,
        "source_release_qualified": False,
        "source_transition_authorized": False,
        "reissue_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
    }


def main(argv=None, *, environ=None, event=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    env = os.environ if environ is None else environ
    need(os.name == "nt"
         and env.get("GITHUB_REPOSITORY") == source.REPO
         and env.get("GITHUB_ACTOR") == "spoonman136668-ai"
         and env.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and env.get("GITHUB_EVENT_NAME") == "issue_comment"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_SHA") == args.target
         and type(args.target) is str and SHA.fullmatch(args.target),
         "EXACT_ORIGINAL_OWNER_RUNNER_EVENT")
    if event is None:
        event_path = env.get("GITHUB_EVENT_PATH")
        need(type(event_path) is str and Path(event_path).is_file(),
             "OWNER_EVENT_MISSING")
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    need(type(event) is dict and event.get("action") == "created"
         and event.get("issue", {}).get("number") == 807
         and event.get("issue", {}).get("user", {}).get("login")
             == "spoonman136668-ai"
         and event.get("comment", {}).get("body") == PREFIX + args.target
         and event.get("comment", {}).get("user", {}).get("login")
             == "spoonman136668-ai"
         and event.get("comment", {}).get("author_association") == "OWNER"
         and type(event.get("comment", {}).get("id")) is int
         and event["comment"]["id"] > 0
         and event.get("sender", {}).get("login") == "spoonman136668-ai",
         "SOURCE_BOUND_READONLY_COMMENT")
    appdata = env.get("LOCALAPPDATA")
    need(type(appdata) is str and Path(appdata).is_absolute()
         and args.db.resolve() ==
             (Path(appdata) / "FORGE-F139" / "state.sqlite").resolve(),
         "CANONICAL_ORIGINAL_DATABASE_PATH")

    receipt = inspect_original(args.db, GitHub(), target=args.target)
    print("F139_V41_ORIGINAL_OWNER_READONLY=" + canonical(receipt).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

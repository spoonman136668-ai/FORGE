"""Source-only original Windows V40 ledger and pending #1715 acceptance.

Reuses the existing read-only status route and kernel owner mutex. This
module never creates a task, backup, source transition, issue or release.
"""
import argparse
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import re
import time

from f139.local_controller import Database, F139Error, GitHub, SingleOwner
from f139.nci04_native_contract import canonical
from f139 import nci04_v41_catalog_recovery_preflight as source
from f139 import nci04_v41_pending_custody as pending

SCHEMA = "forge.f139.v41.original-locked-readonly-status.v1"
PREFIX = "F139-V9-STATUS "
SHA = re.compile(r"[0-9a-f]{40}\Z")
# Read-only status only: never wait while holding a lease or original SQLite.
OWNER_MUTEX_MAX_RETRIES = 60
OWNER_MUTEX_RETRY_SECONDS = 1.0


class V41StatusDenied(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise V41StatusDenied("F139_V41_OWNER_STATUS_" + code)



@contextmanager
def _read_only_owner_lease(path: Path, *, wait=time.sleep):
    """Observe an idle owner tick with bounded, non-mutating lock attempts.

    The live F139 owner holds this same exclusive kernel mutex during its
    reconciliation ticks. A read-only status query must not mistake ordinary
    contention for corrupt owner custody or bypass exclusivity. Only the
    *exact* existing contention error may be retried, and no original SQLite
    is opened until the lock is genuinely acquired.
    """
    need(isinstance(path, Path) and path.is_absolute()
         and path.name == "state.sqlite", "OWNER_MUTEX_PATH_INVALID")
    for retry in range(OWNER_MUTEX_MAX_RETRIES + 1):
        lease = SingleOwner(path.with_suffix(".lock"))
        try:
            lease.__enter__()
        except F139Error as exc:
            if str(exc) != "F139_CONTROLLER_ALREADY_RUNNING":
                raise
            if retry == OWNER_MUTEX_MAX_RETRIES:
                raise V41StatusDenied(
                    "F139_V41_OWNER_STATUS_ORIGINAL_MUTEX_STILL_BUSY") from exc
            wait(OWNER_MUTEX_RETRY_SECONDS)
            continue
        # Never catch body exceptions as a lock conflict and never perform
        # another attempt after the original mutex has been acquired.
        try:
            yield
        finally:
            lease.__exit__(None, None, None)
        return



# Only this completed failed-run folder may be inspected. No future run is
# authorized by this diagnostic; no original or backup contents are opened.
FAILED_BACKUP_RUN = 43332363875
FAILED_BACKUP_SCHEMA = "forge.f139.v41.failed-cold-bundle-inventory-only.v1"
# Bound the original 300-entry truncated inventory without reading any bytes.
MAX_FORENSIC_ENTRIES = 4096


def inspect_failed_backup_stage(original_db: Path) -> dict:
    """Read filename categories, never filenames/bytes/paths in the receipt."""
    path = Path(original_db)
    need(path.is_absolute() and path.name == "state.sqlite"
         and path.parent.is_dir() and not path.parent.is_symlink()
         and not getattr(path.parent, "is_junction", lambda: False)(),
         "FORENSIC_CANONICAL_PARENT")
    folder = path.parent / ("f139-v41-before-" + str(FAILED_BACKUP_RUN))
    status = dict(schema=FAILED_BACKUP_SCHEMA, failed_run_id=FAILED_BACKUP_RUN,
                  classification="ABSENT", sqlite_snapshot_present=False,
                  sealed_manifest_present=False, provider_file_count=0,
                  prior_binary_file_count=0, provider_complete_groups=0,
                  provider_incomplete_groups=0, unexpected_entry_count=0,
                  inventory_complete=False, entries_scanned=0,
                  contents_read=False, original_db_written=False,
                  task_mutations=0, backup_retried=False)
    if folder.is_symlink() or getattr(folder, "is_junction", lambda: False)():
        status["classification"] = "UNTRUSTED_LINK"
        return status
    if not folder.exists():
        return status
    if not folder.is_dir():
        status["classification"] = "NON_DIRECTORY"
        return status
    total = 0
    for parent, dirs, files in os.walk(folder, followlinks=False):
        prefix = Path(parent).relative_to(folder).parts
        if len(prefix) > 4:
            status["classification"] = "DEPTH_LIMIT"
            return status
        if len(prefix) == 3 and prefix[0] == "provider-custody":
            if (set(files) == {"manifest.json", "ubuntu-latest.zip",
                               "windows-latest.zip"} and not dirs):
                status["provider_complete_groups"] += 1
            else:
                status["provider_incomplete_groups"] += 1
        for name in (*dirs, *files):
            total += 1
            if total > MAX_FORENSIC_ENTRIES:
                status["classification"] = "ENTRY_LIMIT"
                return status
            status["entries_scanned"] = total
            entry = Path(parent) / name
            if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
                status["classification"] = "UNTRUSTED_LINK"
                return status
            parts = (*prefix, name)
            if name in files:
                if not entry.is_file():
                    status["classification"] = "NONREGULAR_ENTRY"
                    return status
                if parts == ("state.sqlite",):
                    status["sqlite_snapshot_present"] = True
                elif parts == ("manifest.sha256.json",):
                    status["sealed_manifest_present"] = True
                elif parts[0] == "provider-custody" and len(parts) == 4:
                    status["provider_file_count"] += 1
                elif parts[0] == "prior-generation-custody" and len(parts) == 3:
                    status["prior_binary_file_count"] += 1
                else:
                    status["unexpected_entry_count"] += 1
            elif (len(parts) > 3 or parts[0] not in
                  ("provider-custody", "prior-generation-custody")):
                status["unexpected_entry_count"] += 1
    status["inventory_complete"] = True
    if status["sealed_manifest_present"]:
        status["classification"] = "SEALED_MARKER_PRESENT_UNVERIFIED"
    elif status["prior_binary_file_count"]:
        status["classification"] = "PARTIAL_AFTER_PRIOR_BINARY"
    elif status["provider_file_count"]:
        status["classification"] = "PARTIAL_AFTER_PROVIDER"
    elif status["sqlite_snapshot_present"]:
        status["classification"] = "PARTIAL_AFTER_SQLITE"
    else:
        status["classification"] = "EMPTY_OR_NONSTANDARD_STAGE"
    return status


# Replay only the READ-ONLY cold-copy verifier on the non-replayable failed
# run's copied material. No task pause, backup staging, sealed manifest,
# source transition, or owner/remote mutation occurs here.
COLD_COPY_PROBE_SCHEMA = "forge.f139.v41.failed-cold-copy-readonly-probe.v1"


def inspect_failed_backup_cold_copy(original: Database, get, *,
                                    target: str, inventory: dict) -> dict:
    """Identify the first cold-copy integrity failure without exposing paths."""
    from f139 import nci04_v41_cold_copy_verifier as cold

    result = dict(schema=COLD_COPY_PROBE_SCHEMA,
                  failed_run_id=FAILED_BACKUP_RUN,
                  attempted=False, snapshot_hash_checked=False,
                  cold_copy_verified=False, failure_code="NOT_ELIGIBLE",
                  original_db_written=False, copied_backup_written=False,
                  task_mutations=0, new_dispatches=0, backup_retried=False,
                  source_transition_authorized=False,
                  scientific_first_use=False, hybrid_admission=False)
    if (type(original) is not Database
            or getattr(original, "_readonly_opened", False) is not True
            or original.conn.execute("PRAGMA query_only").fetchone()[0] != 1
            or not SingleOwner.held(original.filename.with_suffix(".lock"))
            or type(target) is not str or not SHA.fullmatch(target)
            or type(inventory) is not dict
            or inventory.get("failed_run_id") != FAILED_BACKUP_RUN
            or inventory.get("classification") != "PARTIAL_AFTER_PRIOR_BINARY"
            or inventory.get("inventory_complete") is not True
            or inventory.get("unexpected_entry_count") != 0
            or inventory.get("provider_incomplete_groups") != 0
            or inventory.get("provider_complete_groups", 0) < 1
            or inventory.get("prior_binary_file_count") != 1
            or inventory.get("sqlite_snapshot_present") is not True
            or inventory.get("sealed_manifest_present") is not False):
        return result
    folder = (original.filename.parent /
              ("f139-v41-before-" + str(FAILED_BACKUP_RUN)))
    backup = folder / "state.sqlite"
    if (not folder.is_dir() or folder.is_symlink()
            or getattr(folder, "is_junction", lambda: False)()
            or not backup.is_file() or backup.is_symlink()
            or getattr(backup, "is_junction", lambda: False)()
            or not 0 < backup.stat().st_size <= cold.MAX_BACKUP_BYTES):
        result["failure_code"] = "UNTRUSTED_OR_OVERSIZE_STAGE"
        return result
    result["attempted"] = True
    try:
        cold._require_standalone_sqlite(backup)
        backup_sha = cold._hash_standalone_sqlite(backup)
        result["snapshot_hash_checked"] = True
        cold.verify_cold_copy(original, backup, get, target=target,
                              run_id=FAILED_BACKUP_RUN,
                              expected_backup_sha256=backup_sha)
    except Exception as exc:
        # Error strings outside a strict machine-code grammar may contain
        # private filesystem paths, API routes or provider data: never emit.
        reason = str(exc)
        result["failure_code"] = (reason if re.fullmatch(
            r"F139_[A-Z0-9_]{1,120}", reason) else "UNCLASSIFIED_EXCEPTION")
        return result
    result["cold_copy_verified"] = True
    result["failure_code"] = "NONE"
    return result


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
    with _read_only_owner_lease(path):
        with closing(Database.open_readonly(path)) as db:
            failed_inventory = inspect_failed_backup_stage(path)
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
                failed_copy = inspect_failed_backup_cold_copy(
                    db, api.native_repo_get, target=target,
                    inventory=failed_inventory)
                need(db.meta() == before and db.conn.total_changes == count,
                     "FORENSIC_CHANGED_ORIGINAL")
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
        "failed_backup_forensic": failed_inventory,
        "failed_backup_copy_probe": failed_copy,
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

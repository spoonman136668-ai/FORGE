"""Original-owner, exact-scope negative custody. Never dispatches or installs."""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

OWNER = "spoonman136668-ai"
REASON = "AMBIGUOUS_START_NO_PROVIDER_RUN"


@dataclass(frozen=True)
class Scope:
    source: str
    ticket: str
    started: str
    sequence: int
    head: str
    issue: int
    lane: str
    protected_main: str


LIVE = Scope("5680e7448276a9f257413570e0283fcab7e392ec",
    "f139-nci04-i1464-5680e7448276-1422163f", "2026-11-04T09:35:01.440970Z",
    1083, "3fce5647caeee3d1fcc0e9cc8e64db8bb9d3a96fc5eb356f6c09392f2714f94c",
    1464, "Yggdrasil", "80ae30719bcd9f179da4aa4e8f14dc36fd15818e")


class RecoveryDenied(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise RecoveryDenied("F139_I1464_" + reason)


def seal(db):
    meta = db.meta()
    return meta["head_seq"], meta["head_hash"]


def task(db, ticket):
    row = db.conn.execute("SELECT * FROM tasks WHERE ticket=?", (ticket,)).fetchone()
    return dict(row) if row else None


def reconcile(db, api, scope, backup, *, clock=None, pause=time.sleep,
              monotonic=time.monotonic):
    """Caller supplies independently admitted owner context; Scope is no grant.

    Tests use isolated real SQLite with synthetic admission witnesses. Production
    CLI always uses LIVE, the installed canonical modules and the original mutex.
    """
    from f139.local_controller import Database, SingleOwner
    from f139.nci04_owner_ledger import frozen_native_issue, verify_native_activation
    from f139.nci04_owner_issue import inspect_owner_issue
    clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    need(type(db) is Database and SingleOwner.held(Path(db.filename).with_suffix(".lock")),
         "CANONICAL_ORIGINAL_OWNER_LOCK_REQUIRED")
    db.verify()
    meta = db.meta()
    need(meta["source_sha"] == scope.source and meta["enabled"] == 1
         and meta["legacy_suspended"] == 1 and verify_native_activation(db), "ACTIVATION_DRIFT")
    need(seal(db) == (scope.sequence, scope.head), "LEDGER_SEAL_DRIFT")
    original = task(db, scope.ticket)
    need(original is not None and original["stage"] == "START_RISK"
         and original["lane"] == scope.lane and original["source_sha"] == scope.source
         and original["started_at"] == scope.started
         and all(original[k] is None for k in
             ("run_id", "evidence_dir", "evidence_sha", "completed_at", "quarantine_reason")),
         "EXACT_TASK_DRIFT")
    active = [dict(x) for x in db.actives()]
    need(len(active) == 1 and active[0]["ticket"] == scope.ticket, "ACTIVE_SLOT_DRIFT")
    started = dt.datetime.fromisoformat(scope.started.replace("Z", "+00:00"))
    need(clock() - started >= dt.timedelta(minutes=30), "GRACE_PERIOD_REQUIRED")
    native = frozen_native_issue(db, scope.ticket)
    need(native.number == scope.issue and native.lane == scope.lane
         and native.source_sha == scope.source, "FROZEN_ADMISSION_DRIFT")
    remote = api.get(f"repos/{OWNER}/FORGE/issues/{scope.issue}")
    try:
        authenticated = inspect_owner_issue(remote, protected_main=scope.source,
            authenticated_target_commit=native.candidate.target_commit,
            authenticated_target_tree=native.candidate.target_tree_sha)
    except (ValueError, TypeError, KeyError):
        raise RecoveryDenied("F139_I1464_REMOTE_ISSUE_IDENTITY_DRIFT") from None
    need(authenticated == native, "REMOTE_ISSUE_IDENTITY_DRIFT")
    need(api.protected_main() == scope.protected_main and
         api.deployed_release_continuity(db, scope.source, scope.protected_main) is True,
         "RELEASE_CONTINUITY_DRIFT")
    reads = []
    begin = monotonic()
    for index in range(2):
        need(api.candidates_for_source(scope.ticket, scope.started, scope.source) is None,
             "PROVIDER_RUN_EXISTS")
        reads.append(clock().isoformat())
        if index == 0:
            pause(60)
    need(monotonic() - begin >= 60, "OBSERVATION_INTERVAL_REQUIRED")
    db.verify()
    need(seal(db) == (scope.sequence, scope.head) and task(db, scope.ticket) == original,
         "STATE_CHANGED_DURING_OBSERVATION")
    backup = Path(backup)
    need(backup.parent.resolve() == Path(db.filename).resolve().parent
         and backup.resolve() != Path(db.filename).resolve(), "PRIVATE_BACKUP_ROUTE_REQUIRED")
    with backup.open("xb"):
        pass
    with closing(sqlite3.connect(str(backup))) as out:
        db.conn.backup(out)
        need(out.execute("PRAGMA quick_check").fetchone()[0] == "ok", "BACKUP_INVALID")
    others = [tuple(x) for x in db.conn.execute(
        "SELECT * FROM tasks WHERE ticket<>? ORDER BY ticket", (scope.ticket,))]
    # Validate the identical transition on a private disposable copy BEFORE
    # committing to the original. The preserved pre-state backup stays unchanged.
    fd, name = tempfile.mkstemp(prefix="f139-i1464-preview-", suffix=".sqlite", dir=backup.parent)
    os.close(fd)
    preview = Path(name)
    shadow = None
    try:
        with closing(sqlite3.connect(str(preview))) as out:
            db.conn.backup(out)
        # Keep the instance reachable even if constructor verification fails,
        # so its SQLite handle is closed before deleting the private copy.
        shadow = Database.__new__(Database)
        Database.__init__(shadow, preview)
        shadow.verify()
        shadow.quarantine(scope.ticket, REASON)
        shadow.verify()
        expected = seal(shadow)
        need(expected[0] == scope.sequence + 1, "PREVIEW_EVENT_COUNT_DRIFT")
    finally:
        if shadow is not None and getattr(shadow, "conn", None) is not None:
            shadow.close()
        for path in (preview, Path(str(preview) + "-wal"), Path(str(preview) + "-shm")):
            path.unlink(missing_ok=True)
    need(seal(db) == (scope.sequence, scope.head) and task(db, scope.ticket) == original,
         "STATE_CHANGED_BEFORE_COMMIT")
    db.quarantine(scope.ticket, REASON)
    db.verify()
    final = task(db, scope.ticket)
    need(seal(db) == expected and final == {**original, "stage": "QUARANTINED",
                                          "quarantine_reason": REASON}, "COMMIT_READBACK_DRIFT")
    need(others == [tuple(x) for x in db.conn.execute(
        "SELECT * FROM tasks WHERE ticket<>? ORDER BY ticket", (scope.ticket,))], "OTHER_TASK_CHANGED")
    after_meta = db.meta()
    need({k: v for k, v in after_meta.items() if k not in ("head_seq", "head_hash")} ==
         {k: v for k, v in meta.items() if k not in ("head_seq", "head_hash")}, "OWNER_META_CHANGED")
    return {"schema": "forge.f139.i1464.negative-custody.v1", "ticket": scope.ticket,
            "source_sha": scope.source, "before_seq": scope.sequence, "before_head": scope.head,
            "after_seq": expected[0], "after_head": expected[1], "reason": REASON,
            "provider_observations": reads, "provider_results": ["ABSENT", "ABSENT"],
            "backup_created": True,
            "original_events_appended": 1, "redispatches": 0, "installed_source_changes": 0,
            "task_configuration_changes": 0, "scientific_first_use": False}


def main():
    need(len(sys.argv) == 4, "ARGUMENTS_REQUIRED")
    root, dbpath, output = (Path(x).resolve() for x in sys.argv[1:])
    sha = os.environ.get("GITHUB_SHA", "")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    need(len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)
         and os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and os.environ.get("GITHUB_REPOSITORY") == f"{OWNER}/FORGE"
         and os.environ.get("GITHUB_ACTOR") == OWNER
         and os.environ.get("GITHUB_EVENT_NAME") == "push"
         and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
         and os.environ.get("GITHUB_REF") == "refs/heads/recovery/f139-i1464-negative-" + sha
         and event.get("created") is True and event.get("forced") is False
         and event.get("deleted") is False and event.get("before") == "0" * 40
         and event.get("after") == sha and event.get("sender", {}).get("login") == OWNER,
         "AUTHENTIC_ONCE_EVENT_REQUIRED")
    need(not output.exists(), "RECEIPT_COLLISION")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    need(git("rev-parse", "HEAD") == LIVE.source
         and not git("status", "--porcelain", "--untracked-files=all"), "INSTALLED_SOURCE_DRIFT")
    sys.path.insert(0, str(root))
    from f139 import local_controller as original
    need(Path(original.__file__).resolve() == root / "f139" / "local_controller.py",
         "CANONICAL_IMPORT_DRIFT")
    lock = original.SingleOwner(dbpath.with_suffix(".lock"))
    acquired = False
    for attempt in range(60):
        try:
            lock.__enter__()
            acquired = True
            break
        except original.F139Error as exc:
            need(str(exc) == "F139_CONTROLLER_ALREADY_RUNNING", "UNEXPECTED_LOCK_FAILURE")
            if attempt < 59:
                time.sleep(10)
    need(acquired, "ORIGINAL_OWNER_LOCK_BUSY")
    db = None
    try:
        db = original.Database(dbpath)
        backup = dbpath.with_name("f139-i1464-before-quarantine-" + os.environ["GITHUB_RUN_ID"] + ".sqlite")
        receipt = reconcile(db, original.GitHub(), LIVE, backup)
        receipt.update(execution_source_sha=sha, run_id=int(os.environ["GITHUB_RUN_ID"]))
        with output.open("x", encoding="utf-8") as out:
            out.write(json.dumps(receipt, sort_keys=True) + "\n")
        print("F139_I1464_NEGATIVE_CUSTODY=" + json.dumps(receipt, sort_keys=True))
    finally:
        if db is not None:
            db.close()
        lock.__exit__(None, None, None)


if __name__ == "__main__":
    main()

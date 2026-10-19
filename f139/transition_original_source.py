"""Frozen F139 D2 original-run source transition, preserving all original evidence.

No scheduling, dispatch, workflow mutation, secret access, or scientific authority.
Explicitly disabled F139 task and isolated owner lease required before a DB write.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3

from local_controller import (
    Database, GitHub, REPO, SingleOwner, canonical, hash_bytes,
    legacy_windows_task_disabled, receipt_from_zip, require, utc_now,
)
from reconcile_original import (
    ORIGINALS, ORIGINAL_KINDS, SOURCE, require_stopped_controller,
)

def inspect_original_completed(connection, db_path):
    connection.row_factory = sqlite3.Row
    meta = connection.execute("SELECT * FROM meta WHERE id=1").fetchone()
    require(meta is not None and meta["source_sha"] == SOURCE and
            meta["epoch"] == 1 and meta["enabled"] == 1 and
            meta["legacy_suspended"] == 1 and meta["starts"] == 2 and
            meta["head_seq"] == 11, "TRANSITION_ORIGINAL_SOURCE_OR_HEAD_DRIFT")
    records = list(connection.execute("SELECT * FROM events ORDER BY seq"))
    require(len(records) == 11 and tuple(
        row["kind"] for row in records[:9]) == ORIGINAL_KINDS and
        all(row["kind"] == "QUARANTINE_ORIGINAL_RECONCILED" for row in records[9:]),
        "TRANSITION_ORIGINAL_APPEND_ONLY_EVENTS_DRIFT")
    tasks = {row["ticket"]: dict(row) for row in
             connection.execute("SELECT * FROM tasks ORDER BY ticket")}
    require(set(tasks) == set(ORIGINALS), "TRANSITION_ORIGINAL_TICKET_SET_DRIFT")
    for ticket, frozen in ORIGINALS.items():
        task = tasks[ticket]
        require(task["source_sha"] == SOURCE and task["lane"] == frozen["lane"]
                and task["stage"] == "VERIFIED" and
                task["run_id"] == frozen["run_id"] and
                task["quarantine_reason"] == "PROVIDER_SOURCE_EVENT_SPOOFED" and
                task["evidence_sha"] is not None and
                task["started_at"] is not None, "TRANSITION_ORIGINAL_COMPLETION_DRIFT")
        expected_folder = db_path.parent / "evidence" / ticket / str(frozen["run_id"])
        actual_folder = Path(task["evidence_dir"])
        require(actual_folder.resolve() == expected_folder.resolve() and
                expected_folder.is_dir() and not expected_folder.is_symlink(),
                "TRANSITION_ORIGINAL_ARCHIVE_PATH_DRIFT")
        paths = {p.name: p for p in expected_folder.iterdir()}
        require(set(paths) == {"ubuntu-latest.zip", "windows-latest.zip", "manifest.json"}
                and all(p.is_file() and not p.is_symlink() for p in paths.values()),
                "TRANSITION_ORIGINAL_ARCHIVE_MEMBER_DRIFT")
        digest_map = {}
        for label in ("ubuntu-latest", "windows-latest"):
            _, known_sha = frozen[label]
            raw = paths[label + ".zip"].read_bytes()
            require(hash_bytes(raw) == known_sha, "TRANSITION_ORIGINAL_ZIP_CHANGED")
            receipt_from_zip(raw, {"digest": "sha256:" + known_sha,
                                   "size_in_bytes": len(raw)},
                             task, frozen["run_id"], label, epoch=1)
            digest_map[label] = known_sha
        manifest = {
            "schema": "forge.f139.windows-evidence-manifest.v1",
            "ticket": ticket, "run_id": frozen["run_id"],
            "sha256": digest_map, "scientific_originals": 0,
            "approved_science": False,
        }
        expected = canonical(manifest)
        require(paths["manifest.json"].read_bytes() == expected and
                task["evidence_sha"] == hash_bytes(expected),
                "TRANSITION_ORIGINAL_MANIFEST_CHANGED")
        record = json.loads(records[9 + list(ORIGINALS).index(ticket)]["payload"])
        require(record["ticket"] == ticket and record["run_id"] == frozen["run_id"]
                and record["manifest_sha256"] == task["evidence_sha"]
                and record["original_science"] is False
                and record["replay"] is False,
                "TRANSITION_ORIGINAL_ADJUDICATION_DRIFT")
    return dict(meta)

def verify_inactive_owners(api, db_path):
    require_stopped_controller(db_path)
    require(api.legacy_dispatchers_disabled() is True,
            "TRANSITION_LEGACY_GITHUB_OWNER_ACTIVE")
    require(legacy_windows_task_disabled() is True,
            "TRANSITION_F137_OWNER_ACTIVE")

def reconcile_source(db_path, new_sha, *, apply=False, api=None):
    db_path = Path(db_path)
    require(not db_path.is_symlink(), "TRANSITION_DB_ABSENT_OR_SYMLINK")
    db_path = db_path.resolve()
    require(db_path.is_file(), "TRANSITION_DB_ABSENT_OR_SYMLINK")
    require(isinstance(new_sha, str) and len(new_sha) == 40 and
            all(ch in "0123456789abcdef" for ch in new_sha) and
            new_sha != SOURCE, "TRANSITION_NEW_SHA_INVALID")
    api = api or GitHub()
    with SingleOwner(db_path.with_suffix(".lock")):
        verify_inactive_owners(api, db_path)
        require(api.protected_main() == new_sha, "TRANSITION_NEW_MAIN_NOT_PROTECTED_EXACT")
        if not apply:
            conn = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
            try:
                conn.execute("PRAGMA query_only=ON")
                meta = inspect_original_completed(conn, db_path)
            finally:
                conn.close()
            return {"disposition": "F139_SOURCE_TRANSITION_DRY_RUN_PASS",
                    "from_source": SOURCE, "to_source": new_sha,
                    "previous_head": meta["head_hash"], "db_writes": 0, "dispatches": 0}
        db = Database(db_path)
        try:
            meta = inspect_original_completed(db.conn, db_path)
            db.verify()
            # A source-pinned, distinct offline backup before the sole DB mutation.
            backup_dir = db_path.parent / "source-transition-custody"
            require(not backup_dir.exists(), "TRANSITION_BACKUP_ALREADY_EXISTS")
            backup_dir.mkdir(parents=False, exist_ok=False)
            backup = backup_dir / "pre-transition-source.sqlite"
            backconn = sqlite3.connect(str(backup))
            try:
                db.conn.backup(backconn)
            finally:
                backconn.close()
            probe = sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)
            try:
                probe.execute("PRAGMA query_only=ON")
                require(probe.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                        "TRANSITION_BACKUP_SQLITE_INTEGRITY")
                require(inspect_original_completed(probe, db_path)["head_hash"] == meta["head_hash"],
                        "TRANSITION_BACKUP_HEAD_NOT_SAME")
            finally:
                probe.close()
            snapshot_sha = hash_bytes(backup.read_bytes())
            # Retry-resistant final owner, source and ledger check.
            verify_inactive_owners(api, db_path)
            require(api.protected_main() == new_sha, "TRANSITION_MAIN_CHANGED_BEFORE_COMMIT")
            require(inspect_original_completed(db.conn, db_path)["head_hash"] == meta["head_hash"],
                    "TRANSITION_DB_CHANGED_BEFORE_COMMIT")
            db.transition_source(new_sha)
            status = db.status()
            require(status["meta"]["head_seq"] == 12 and
                    status["meta"]["source_sha"] == new_sha and
                    status["meta"]["starts"] == 2 and
                    all(row["stage"] == "VERIFIED" and row["source_sha"] == SOURCE
                        for row in status["tasks"]), "TRANSITION_COMMIT_DRIFT")
            return {"disposition": "F139_SOURCE_TRANSITION_COMMITTED_HISTORICAL_SOURCE_PRESERVED",
                    "from_source": SOURCE, "to_source": new_sha,
                    "backup": str(backup), "backup_sha256": snapshot_sha,
                    "new_event_head": status["meta"]["head_hash"],
                    "head_seq": status["meta"]["head_seq"], "dispatches": 0,
                    "historic_ticket_sources_rewritten": 0}
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--new-main-sha", required=True)
    parser.add_argument("--apply", action="store_true")
    opts = parser.parse_args()
    print(json.dumps(reconcile_source(opts.db, opts.new_main_sha, apply=opts.apply),
                     sort_keys=True))

if __name__ == "__main__":
    main()

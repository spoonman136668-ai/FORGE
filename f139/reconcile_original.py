"""One-time no-replay repair for F139-D2's two authentic quarantined development runs.

Frozen, narrow scope only: two known tickets, old exact source and run IDs.
Default mode audits and downloads; --apply records original ZIP custody and appends
explicit adjudication events, preserving both historic QUARANTINED events/reasons.
Never dispatches, rekeys, changes owner state, or authorizes original science.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess

from local_controller import (
    Database, F139Error, GitHub, REPO, SingleOwner, ZERO, canonical,
    hash_bytes, legacy_windows_task_disabled, receipt_from_zip,
    require, store_evidence, utc_now,
)

SOURCE = "f569b827aeeddcbb2865bec49c062d2a7e523886"
ORIGINALS = {
    "f139-d2c-qualification-659bb1f4d751": {
        "lane": "Qualification", "run_id": 39178196331,
        "ubuntu-latest": (12154911952, "0cd38a967f9b6359a55e6e5427255cf00e3e8ef74aff94a3368f99d7e74d9626"),
        "windows-latest": (12155630506, "8b372073f7ec24dc07bb826d9488f7f0647b1416e249b121aef9430a22ca3bd6"),
    },
    "f139-d2c-wingless-659bb1f4d751": {
        "lane": "Wingless", "run_id": 39178299792,
        "ubuntu-latest": (12155047905, "9e81d661d90386384875db8d6a46b9e71d2356d8934bb47c9c73f7c9b85a1e76"),
        "windows-latest": (12154993204, "43ff3ee4619f0557cb6f635cace38b278a01c846aa6bb6a00199229de0e4606e"),
    },
}
ORIGINAL_KINDS = (
    "TASK_INTAKE", "TASK_INTAKE", "CUTOVER_ACTIVATED",
    "BEFORE_DISPATCH_INTENT", "DISPATCH_POST_RETURNED", "ATTEMPT_QUARANTINED",
    "BEFORE_DISPATCH_INTENT", "DISPATCH_POST_RETURNED", "ATTEMPT_QUARANTINED",
)

def original_state(conn):
    conn.row_factory = sqlite3.Row
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "REPAIR_SQLITE_INTEGRITY")
    meta = conn.execute("SELECT * FROM meta WHERE id=1").fetchone()
    require(meta is not None and meta["source_sha"] == SOURCE and meta["epoch"] == 1
            and meta["enabled"] == 1 and meta["legacy_suspended"] == 1
            and meta["starts"] == 2 and meta["head_seq"] == 9, "REPAIR_FROZEN_STATE_DRIFT")
    events = list(conn.execute("SELECT * FROM events ORDER BY seq"))
    require(tuple(e["kind"] for e in events) == ORIGINAL_KINDS,
            "REPAIR_ORIGINAL_EVENTS_CHANGED")
    prior = ZERO
    for index, event in enumerate(events, 1):
        payload = json.loads(event["payload"])
        require(event["seq"] == index and event["prior_sha"] == prior and
                canonical(payload).decode() == event["payload"], "REPAIR_EVENT_CHAIN_INVALID")
        expected = hash_bytes(canonical({"seq": index, "prior_sha": prior,
                                         "kind": event["kind"], "payload": payload}))
        require(event["sha"] == expected, "REPAIR_EVENT_CHAIN_INVALID")
        prior = expected
    require(meta["head_hash"] == prior, "REPAIR_EVENT_HEAD_INVALID")
    tasks = {row["ticket"]: dict(row) for row in conn.execute("SELECT * FROM tasks")}
    require(set(tasks) == set(ORIGINALS), "REPAIR_TICKET_SET_DRIFT")
    for ticket, row in tasks.items():
        expected = ORIGINALS[ticket]
        require(row["lane"] == expected["lane"] and row["source_sha"] == SOURCE
                and row["stage"] == "QUARANTINED"
                and row["quarantine_reason"] == "PROVIDER_SOURCE_EVENT_SPOOFED"
                and row["run_id"] is None and row["evidence_dir"] is None
                and row["evidence_sha"] is None and row["started_at"] is not None,
                "REPAIR_QUARANTINE_STATE_DRIFT")
    return tasks, prior

def provider_evidence(api, tasks):
    require(api.legacy_dispatchers_disabled() is True, "REPAIR_LEGACY_OWNER_NOT_DISABLED")
    require(legacy_windows_task_disabled() is True, "REPAIR_F137_NOT_DISABLED")
    accepted = {}
    for ticket, frozen in ORIGINALS.items():
        task = tasks[ticket]
        run = api.candidates(ticket, task["started_at"])
        require(run is not None and run.get("id") == frozen["run_id"],
                "REPAIR_ORIGINAL_RUN_NOT_UNIQUE")
        result = api.run_proof(run, ticket, SOURCE, task["started_at"])
        require(result is not None and result[0] == frozen["run_id"],
                "REPAIR_ORIGINAL_RUN_NOT_COMPLETE")
        artifacts = result[1]
        received = {}
        for oslabel in ("ubuntu-latest", "windows-latest"):
            matching = [v for v in artifacts if v.get("name") ==
                        "forge-f139-dev-receipt-" + oslabel]
            require(len(matching) == 1, "REPAIR_ARTIFACT_NOT_UNIQUE")
            item = matching[0]
            artifact_id, known_sha = frozen[oslabel]
            require(item.get("id") == artifact_id and item.get("digest") == "sha256:" + known_sha,
                    "REPAIR_EXTERNAL_ARTIFACT_IDENTITY")
            raw = api.artifact(artifact_id)
            require(hash_bytes(raw) == known_sha, "REPAIR_EXTERNAL_ARTIFACT_BYTES")
            receipt_from_zip(raw, item, task, frozen["run_id"], oslabel, epoch=1)
            received[oslabel] = raw
        accepted[ticket] = received
    return accepted

def require_stopped_controller(db_path):
    require(os.name == "nt", "REPAIR_NATIVE_WINDOWS_REQUIRED")
    statement = (
        "$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' "
        "-ErrorAction Stop; if ($t.State -ne 'Disabled') { exit 2 }; "
        "$needle=" + "'" + str(db_path).replace("'", "''") + "'; "
        "$p=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -and $_.CommandLine.Contains($needle) "
        "-and $_.CommandLine.Contains('f139.local_controller') }); "
        "if ($p.Count -ne 0) { exit 3 }; 'STOPPED'"
    )
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                           "-Command", statement], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=20, check=False)
    require(proc.returncode == 0 and proc.stdout.strip() == b"STOPPED",
            "REPAIR_F139_CONTROLLER_NOT_STOPPED")

def reconcile(db_path: Path, *, apply=False, api=None):
    db_path = db_path.resolve()
    require(db_path.is_file(), "REPAIR_PRODUCTION_DB_ABSENT")
    require(not db_path.is_symlink(), "REPAIR_PRODUCTION_DB_SYMLINK")
    api = api or GitHub()
    with SingleOwner(db_path.with_suffix(".lock")):
        if apply:
            require_stopped_controller(db_path)
            db = Database(db_path)
            try:
                tasks, head = original_state(db.conn)
                archives = provider_evidence(api, tasks)
                # Recheck authority immediately after network access and before any write.
                require_stopped_controller(db_path)
                require(api.legacy_dispatchers_disabled() is True, "REPAIR_OWNER_DRIFT")
                require(legacy_windows_task_disabled() is True, "REPAIR_F137_OWNER_DRIFT")
                _, latest = original_state(db.conn)
                require(latest == head, "REPAIR_STATE_CHANGED_DURING_PROOF")
                paths = {}
                for ticket, blobs in archives.items():
                    path, manifest = store_evidence(db_path.parent, ticket,
                                                    ORIGINALS[ticket]["run_id"], blobs)
                    paths[ticket] = (path, manifest)
                with db.transaction():
                    _, latest = original_state(db.conn)
                    require(latest == head, "REPAIR_STATE_CHANGED_DURING_WRITE")
                    for ticket, frozen in ORIGINALS.items():
                        path, manifest = paths[ticket]
                        row = db.conn.execute(
                            "UPDATE tasks SET stage='VERIFIED',run_id=?,evidence_dir=?,"
                            "evidence_sha=?,completed_at=? WHERE ticket=? "
                            "AND stage='QUARANTINED' "
                            "AND quarantine_reason='PROVIDER_SOURCE_EVENT_SPOOFED'",
                            (frozen["run_id"], path, manifest, utc_now(), ticket))
                        require(row.rowcount == 1, "REPAIR_CONCURRENT_STATE_DRIFT")
                        db.event("QUARANTINE_ORIGINAL_RECONCILED", {
                            "ticket": ticket, "run_id": frozen["run_id"],
                            "previous_reason": "PROVIDER_SOURCE_EVENT_SPOOFED",
                            "manifest_sha256": manifest,
                            "original_head_sha256": head,
                            "original_science": False,
                            "replay": False,
                        })
                db.verify()
                require(all(row["stage"] == "VERIFIED" and
                            row["quarantine_reason"] == "PROVIDER_SOURCE_EVENT_SPOOFED"
                            for row in db.status()["tasks"]), "REPAIR_POSTCOMMIT_INVALID")
                return {"disposition": "F139D2E_ORIGINAL_RUNS_RECONCILED_NO_REPLAY",
                        "event_head_seq": db.meta()["head_seq"], "run_ids":
                        [v["run_id"] for v in ORIGINALS.values()], "dispatches": 0}
            finally:
                db.close()
        with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as conn:
            conn.execute("PRAGMA query_only=ON")
            tasks, head = original_state(conn)
        archives = provider_evidence(api, tasks)
        return {"disposition": "F139D2E_PROVIDER_AND_DB_DRY_RUN_PASS",
                "original_event_head_sha256": head,
                "run_ids": [v["run_id"] for v in ORIGINALS.values()],
                "original_zip_shas": {
                    ticket: {oslabel: hash_bytes(raw) for oslabel, raw in blobs.items()}
                    for ticket, blobs in archives.items()},
                "dispatches": 0, "db_writes": 0}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    print(json.dumps(reconcile(options.db, apply=options.apply), sort_keys=True))

if __name__ == "__main__":
    try:
        main()
    except (F139Error, sqlite3.Error, OSError) as exc:
        raise SystemExit("F139D2E_FAIL_CLOSED " + str(exc)) from exc

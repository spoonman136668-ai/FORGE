"""Original F139 V20: guarded once-only settlement of the ALREADY dispatched V3 run.

Operator-approved, original Windows owner only; NOT a new controller, poller,
queue, scheduler, worker dispatch, source transition or scientific first-use.
The original task must be quiesced externally, and source-custody checked before
this helper is ever invoked. All provider receipts are reauthenticated from
GitHub under the original owner key and original SingleOwner lock.
"""
from __future__ import annotations

import os
from pathlib import Path

from f139.local_controller import Database, GitHub, SingleOwner
from f139.nci04_original_v3_terminal import (
    audit_v3_original_custody,
    settle_original_v3,
)
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_release_pin_continuity import verify_release_worker_branch

SOURCE = "db7a1d0f324478183c54df417624053448d6b08b"
TICKET = "f139-nci04-i1207-db7a1d0f3244-5c8ae8b6"
RUN_ID = 40969568784
STARTED = "2026-10-29T22:55:50.742518Z"
HEAD_SEQ = 328
HEAD_HASH = "004aab55338a08230bd8644566e564293d41dbcee5b397521566dfbbbdc3eed4"


class OriginalTerminalDenied(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise OriginalTerminalDenied("F139_V20_ONCE_" + why)


def inspect_original(db: Database) -> None:
    """Read-only state preflight; exact LIVE owner event head, not a replay."""
    need(type(db) is Database
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_DATABASE_AND_OWNER_LOCK_REQUIRED")
    db.verify()
    m = db.meta()
    need(m["source_sha"] == SOURCE and m["enabled"] == 1
         and m["legacy_suspended"] == 1
         and m["head_seq"] == HEAD_SEQ and m["head_hash"] == HEAD_HASH
         and verify_native_activation(db), "ORIGINAL_EVENT_HEAD_CHANGED")
    active = [dict(x) for x in db.actives()]
    need(len(active) == 1 and active[0]["ticket"] == TICKET
         and active[0]["stage"] == "WAIT_PROVIDER"
         and active[0]["source_sha"] == SOURCE
         and active[0]["started_at"] == STARTED
         and active[0]["run_id"] is None
         and db.ready() is None, "ORIGINAL_PENDING_TICKET_CHANGED")
    need(not list(db.conn.execute(
        "SELECT seq FROM events WHERE kind IN "
        "('PROVIDER_VERIFIED_TERMINAL','NATIVE_V_THREE_PROVIDER_CUSTODY') "
        "AND json_extract(payload,'$.ticket')=?",
        (TICKET,))), "ORIGINAL_TERMINAL_ALREADY_EXISTS")


def settle_one_original(db_path: Path, owner_key: str) -> dict:
    """One existing original-owner terminal, never a POST or synthetic receipt."""
    need(isinstance(db_path, Path) and db_path.is_file()
         and type(owner_key) is str and len(owner_key) >= 32,
         "ORIGINAL_DB_PATH_OR_OWNER_KEY_INVALID")
    with SingleOwner(db_path.with_suffix(".lock")):
        db = Database(db_path)
        try:
            inspect_original(db)
            api = GitHub()
            need(verify_release_worker_branch(api.native_repo_get, SOURCE)
                 == "f139-owner-release-" + SOURCE,
                 "IMMUTABLE_ORIGINAL_WORKER_RELEASE_MISSING")
            # This function reconstitutes the original HMAC/claim and checks
            # the unique GitHub V3 authorizer, both independently successful
            # worker jobs, exact source SHA and both canonical signed ZIPs.
            receipt = settle_original_v3(
                db, api, db_path, ticket=TICKET, run_id=RUN_ID,
                started_at=STARTED, owner_key=owner_key)
            db.verify()
            audit_v3_original_custody(db)
            row = db.conn.execute(
                "SELECT stage,run_id,completed_at FROM tasks WHERE ticket=?",
                (TICKET,)).fetchone()
            events = db.conn.execute(
                "SELECT kind FROM events WHERE seq IN (?,?) ORDER BY seq",
                (HEAD_SEQ + 1, HEAD_SEQ + 2)).fetchall()
            need(row is not None and row["stage"] == "VERIFIED"
                 and row["run_id"] == RUN_ID and bool(row["completed_at"])
                 and db.meta()["head_seq"] == HEAD_SEQ + 2
                 and [x["kind"] for x in events] ==
                 ["PROVIDER_VERIFIED_TERMINAL",
                  "NATIVE_V_THREE_PROVIDER_CUSTODY"]
                 and receipt["original_sqlite_terminal_verified"] is True
                 and receipt["scientific_first_use"] is False,
                 "ORIGINAL_POSTSETTLEMENT_EVENT_CUSTODY_INVALID")
            return {
                "original_v20_terminal": "PASS",
                "ticket": TICKET, "run_id": RUN_ID,
                "event_seq": db.meta()["head_seq"],
                "event_sha256": db.meta()["head_hash"],
                "scientific_first_use": False,
                "new_controller": False, "paid_model_calls": 0,
            }
        finally:
            db.close()


def main() -> None:
    import json
    import sys
    need(len(sys.argv) == 2, "ARGUMENT_INVENTORY_INVALID")
    # Only exact original Windows DPAPI custodian supplies this in the
    # child process; never accept command-line keys or persist a secret.
    key = os.environ.get("F139_WORKER_HMAC_KEY", "")
    result = settle_one_original(Path(sys.argv[1]), key)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

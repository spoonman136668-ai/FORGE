"""H53 original V26 native read-only ledger verification.

Never open a write-capable SQLite handle. The original Database verifier remains
authoritative; the successor observer is an additional conservative witness.
"""
from __future__ import annotations
from contextlib import closing
import pathlib
import sqlite3
from f139 import h53_audit_guards as guard
from f139 import h53_successor_readonly_observer as witness
from f139.local_controller import Database

def verify_native(db: pathlib.Path):
    db = pathlib.Path(db).resolve(strict=True)
    cold = Database.open_readonly(db)
    try:
        cold.verify()
        meta = cold.meta()
        guard.demand(meta["source_sha"] == guard.SOURCE, "NATIVE_SOURCE_DRIFT")
        guard.demand(meta["head_seq"] >= witness.BASELINE_SEQ, "NATIVE_HEAD_REGRESSION")
    finally:
        cold.close()
    uri = db.as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=20)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        query_only = conn.execute("PRAGMA query_only").fetchone()[0]
        conn.execute("BEGIN")
        quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
        row = conn.execute("SELECT * FROM meta WHERE id=1").fetchone()
        guard.demand(row is not None, "NATIVE_META_MISSING")
        m = dict(row)
        baseline = conn.execute("SELECT sha FROM events WHERE seq=?", (witness.BASELINE_SEQ,)).fetchone()
        guard.demand(baseline is not None, "NATIVE_BASELINE_MISSING")
        guard.ledger_guard(source_sha=m["source_sha"],enabled=m["enabled"],
                           legacy_suspended=m["legacy_suspended"],
                           head_seq=m["head_seq"],baseline_sha=baseline["sha"],
                           query_only=query_only,quick_check=quick_check,cold_verified=True)
    observed = witness.ledger_observation(db)
    guard.demand(observed["head_seq"] >= witness.BASELINE_SEQ, "WITNESS_HEAD_REGRESSION")
    return {"native_cold_verify": "PASS", "query_only": True,
            "baseline_seq": observed["baseline_seq"],
            "head_seq": observed["head_seq"],
            "head_sha256": observed["head_sha256"],
            "new_events_observed": observed["new_events_observed"],
            "unattended_cycle_verified": False}

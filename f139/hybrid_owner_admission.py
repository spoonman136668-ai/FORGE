"""Explicit in-place owner migration for one TTT-Hybrid F139 native task lane.

This is NOT a second controller/queue, automatic tick migration, signed science
grant, trainer, or GPU lease. It preserves every original task and append-only
event byte and is callable only by the original owner after exact-source
qualification under the original SingleOwner lock.
"""
from __future__ import annotations

import hashlib
import json

KIND="HYBRID_LANE_SCHEMA_ADMITTED"
SCHEMA="forge.f139.hybrid-native-development-lane-migration.v1"
OLD_CHECK="lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil','Qualification'))"
NEW_CHECK="lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil','Qualification','TTT-Hybrid'))"
EXPECTED_INDEX={"only_one_active_f139_task"}
EXPECTED_TRIGGERS={"guard_two_native_active","prevent_task_delete"}
FIELDS={"schema","source_sha","prior_event_head_sha256",
        "old_task_rows_sha256","new_task_rows_sha256","new_task_sql_sha256",
        "scientific_first_use","model_promoted","worker_dispatched",
        "operator_owner_migration"}


def require(value,reason):
    if not value:
        raise ValueError("F139_HYBRID_OWNER_"+reason)


def sha_bytes(value:bytes)->str:
    return hashlib.sha256(value).hexdigest()


def exact(value)->str:
    return sha_bytes((json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode())


def _sql(db):
    row=db.conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()
    require(row is not None and isinstance(row["sql"],str),"TASK_SCHEMA_MISSING")
    return row["sql"]


def _rows(db):
    return [dict(x) for x in db.conn.execute("SELECT * FROM tasks ORDER BY ticket")]


def is_migrated(db):
    sql=_sql(db)
    require((OLD_CHECK in sql) != (NEW_CHECK in sql),"TASK_SCHEMA_UNRECOGNIZED")
    return NEW_CHECK in sql


def _source_at_event(db,seq):
    changes=[json.loads(row["payload"]) for row in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
        "AND seq<? ORDER BY seq",(seq,))]
    if changes:
        return changes[-1]["to_source_sha"]
    row=db.conn.execute("SELECT source_sha FROM tasks "
                        "WHERE ticket LIKE 'f139-d2c-%' "
                        "ORDER BY ticket LIMIT 1").fetchone()
    return row["source_sha"] if row else db.meta()["source_sha"]


def audit_hybrid_lane(db):
    """Cold-verify event source, original chain head, canonical task SQL and rows."""
    sql=_sql(db)
    upgraded=is_migrated(db)
    events=list(db.conn.execute(
        "SELECT seq,payload,prior_sha FROM events WHERE kind=? ORDER BY seq",
        (KIND,)))
    require(len(events)==(1 if upgraded else 0),
            "SCHEMA_EVENT_MISMATCH_OR_REPLAY")
    if not upgraded:
        require(not any(row["lane"]=="TTT-Hybrid" for row in
                        db.conn.execute("SELECT lane FROM tasks")),
                "HYBRID_TASK_ON_OLD_SCHEMA")
        return False
    # The expanded SQL CHECK is only a type allowlist: it is NOT an owner
    # signature. Every actual Hybrid task must have an independent matching
    # native signed issue admission event. Existing native ledger validation
    # authenticates each event's immutable source, original ticket and
    # manifest. This reverse direction prevents direct SQL insertion.
    from f139.nci04_owner_ledger import KIND as NATIVE_ADMITTED
    original_issues = {}
    for event in db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq",
        (NATIVE_ADMITTED,)):
        doc = json.loads(event["payload"])
        if doc["lane"] != "TTT-Hybrid":
            continue
        ticket = doc["ticket"]
        require(ticket not in original_issues, "DUPLICATE_HYBRID_NATIVE_EVENT")
        original_issues[ticket] = (
            doc["source_sha"], doc["manifest_sha256"])
    actual_tasks = {
        task["ticket"]: (task["source_sha"], task["manifest_sha"])
        for task in db.conn.execute(
            "SELECT ticket,source_sha,manifest_sha FROM tasks "
            "WHERE lane='TTT-Hybrid'")
    }
    require(actual_tasks == original_issues,
            "HYBRID_TASK_WITHOUT_NATIVE_OWNER_ADMISSION")
    row=events[0]
    doc=json.loads(row["payload"])
    require(type(doc) is dict and set(doc)==FIELDS
            and doc["schema"]==SCHEMA
            and doc["source_sha"]==_source_at_event(db,row["seq"])
            and doc["prior_event_head_sha256"]==row["prior_sha"]
            and doc["scientific_first_use"] is False
            and doc["model_promoted"] is False
            and doc["worker_dispatched"] is False
            and doc["operator_owner_migration"] is True
            and doc["old_task_rows_sha256"]==doc["new_task_rows_sha256"]
            # The migration binds the original copied row snapshot, not
            # today's growing mutable task table. Original per-ticket events
            # and signed receipts independently protect subsequent rows.
            and doc["new_task_sql_sha256"]==sha_bytes(sql.encode()),
            "COLD_SCHEMA_CUSTODY_DRIFT")
    return True


def migrate_hybrid_lane(db):
    """Original owner only, once, in its existing SQLite transaction.

    Never invoked by run_once or by a worker. Release/owner/clean-tree and
    runner checks are performed in the original CLI BEFORE calling this.
    """
    db.verify()
    if is_migrated(db):
        return False
    from f139.nci04_owner_ledger import verify_native_activation
    require(verify_native_activation(db),"NATIVE_ORIGINAL_OWNER_NOT_ACTIVE")
    meta=db.meta()
    require(meta["enabled"]==1 and meta["legacy_suspended"]==1
            and db.dual_native_schema() and not db.actives()
            and db.ready() is None,"ORIGINAL_OWNER_NOT_IDLE")
    old=_sql(db)
    require(OLD_CHECK in old and NEW_CHECK not in old
            and old.startswith("CREATE TABLE tasks ("),
            "ORIGINAL_TASK_CHECK_CONSTRAINT_DRIFT")
    indexes={row["name"]:row["sql"] for row in db.conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='index' "
        "AND tbl_name='tasks' AND sql IS NOT NULL")}
    triggers={row["name"]:row["sql"] for row in db.conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='tasks'")}
    # SQLite synthesizes two implicit PK/UNIQUE indexes (sql=NULL). They
    # are recreated by the new table constraints, not source DDL.
    auto_indexes=list(db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND tbl_name='tasks' AND sql IS NULL"))
    require(len(auto_indexes)==2,"IMPLICIT_TASK_UNIQUE_INDEX_DRIFT")
    require(set(indexes)==EXPECTED_INDEX and set(triggers)==EXPECTED_TRIGGERS
            and all(isinstance(x,str) for x in (*indexes.values(),*triggers.values())),
            "INDEX_OR_TRIGGER_IDENTITY_DRIFT")
    fields=[row["name"] for row in db.conn.execute("PRAGMA table_info(tasks)")]
    require(fields==["ticket","lane","source_sha","stage","manifest_sha",
                    "run_id","started_at","completed_at","evidence_dir",
                    "evidence_sha","quarantine_reason"],"TASK_COLUMNS_DRIFT")
    before=exact(_rows(db))
    new=old.replace("CREATE TABLE tasks (","CREATE TABLE tasks_hybrid_upgrade (",1).replace(
        OLD_CHECK,NEW_CHECK,1)
    with db.transaction():
        db.verify()
        # CREATE/COPY/SWAP/RECREATE atomic under the original WAL owner.
        db.conn.execute(new)
        db.conn.execute("INSERT INTO tasks_hybrid_upgrade SELECT * FROM tasks")
        require(before==exact([dict(row) for row in db.conn.execute(
            "SELECT * FROM tasks_hybrid_upgrade ORDER BY ticket")]),
            "TASK_BYTES_NOT_COPIED")
        db.conn.execute("DROP TABLE tasks")
        db.conn.execute("ALTER TABLE tasks_hybrid_upgrade RENAME TO tasks")
        for name in sorted(indexes):
            db.conn.execute(indexes[name])
        for name in sorted(triggers):
            db.conn.execute(triggers[name])
        after=exact(_rows(db))
        require(after==before and is_migrated(db) and db.dual_native_schema(),
                "MIGRATED_TASKS_OR_TWO_SLOT_DRIFT")
        new_sql=_sql(db)
        db.event(KIND,{
            "schema":SCHEMA,"source_sha":meta["source_sha"],
            "prior_event_head_sha256":meta["head_hash"],
            "old_task_rows_sha256":before,"new_task_rows_sha256":after,
            "new_task_sql_sha256":sha_bytes(new_sql.encode()),
            "scientific_first_use":False,"model_promoted":False,
            "worker_dispatched":False,"operator_owner_migration":True,
        })
        db.verify()
    return True

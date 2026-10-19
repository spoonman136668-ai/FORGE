"""F139 D1 migration statement contract; no network or side effects on import.

A production Cloudflare caller must submit ALL returned DDL statements as a
single D1Database.batch() call, which rolls back every statement on failure.
D1 rejects manual BEGIN/COMMIT over Worker SQL. Never use serial exec()
or wrangler execution without an independently proven atomic migration path.
This module does NOT provision or deploy any database or admit first-use.
"""
from __future__ import annotations

import pathlib
import re
import sqlite3

HERE = pathlib.Path(__file__).resolve().parent
OBJECTS = (
    ("TABLE", "forge_fsa_authority_state"),
    ("TABLE", "forge_fsa_original_firstuse"),
    ("TRIGGER", "forge_fsa_close_global_slot_after_firstuse"),
    ("TRIGGER", "forge_fsa_no_update_firstuse"),
    ("TRIGGER", "forge_fsa_no_delete_firstuse"),
    ("TRIGGER", "forge_fsa_no_replace_firstuse"),
)
class SourceDrift(ValueError):
    pass

def statements():
    path = HERE / "schema.sql"
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < 18000:
        raise SourceDrift("F139_SCHEMA_SOURCE_UNAVAILABLE")
    text = path.read_text(encoding="utf-8")
    buf, statements = "", []
    for line in text.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            statements.append(buf.strip())
            buf = ""
    if buf.strip() or len(statements) != len(OBJECTS):
        raise SourceDrift("F139_SCHEMA_STATEMENT_COUNT_DRIFT")
    for statement, (kind, name) in zip(statements, OBJECTS):
        stripped = re.sub(r"\A(?:\s*--[^\n]*(?:\n|\Z))*\s*", "", statement)
        if not re.match(r"CREATE " + kind + r" " + name + r"\s*[(\s]", stripped):
            raise SourceDrift("F139_SCHEMA_OBJECT_IDENTITY_DRIFT")
        if "IF NOT EXISTS" in stripped.upper() or kind == "TRIGGER" and "RAISE(ABORT" not in stripped:
            raise SourceDrift("F139_SCHEMA_GUARD_DRIFT")
    return tuple(statements)

def qualify_atomic_sqlite(db):
    """EXCLUSIVELY an in-memory/fixture SQLite migration regression helper.

    Never use this for Cloudflare D1; D1 must use one true provider batch.
    """
    batch = statements()
    db.execute("BEGIN IMMEDIATE")
    try:
        for statement in batch:
            db.execute(statement)
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise

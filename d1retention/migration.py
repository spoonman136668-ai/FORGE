"""Fail-closed offline preview of an additive FORGE D1 archive migration.
Never accepts live or file-backed DB connections; never deploys or authorizes science.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib, json, re, sqlite3

SCHEMA_PATH=Path(__file__).with_name("schema.sql")
PREFIX="forge_research_"
TABLES={"forge_research_originals","forge_research_chunks","forge_research_seals"}
TRIGGERS={
 "forge_research_chunks_bounds","forge_research_seals_complete",
 "forge_research_originals_update_immutable","forge_research_originals_delete_immutable",
 "forge_research_chunks_update_immutable","forge_research_chunks_delete_immutable",
 "forge_research_seals_update_immutable","forge_research_seals_delete_immutable",
}
class MigrationBlocked(ValueError): pass

@dataclass(frozen=True)
class MigrationPreview:
    source_sha256: str
    original_schema_sha256: str
    existing_objects_preserved: bool
    archive_tables: int
    archive_triggers: int
    live_migration_performed: bool=False
    research_authorized: bool=False

def sha(b): return hashlib.sha256(b).hexdigest()

def foreign_schema(db):
    rows=db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name,tbl_name"
    ).fetchall()
    if not all(isinstance(n,str) for _,n,_,_ in rows):
        raise MigrationBlocked("MALFORMED_SQLITE_METADATA")
    foreign=[list(row) for row in rows if not row[1].startswith(PREFIX)]
    digest=sha(json.dumps(foreign,ensure_ascii=True,separators=(",",":")).encode())
    return digest,rows

def preview(db,*,source_sha256,foreign_sha256):
    if not isinstance(db,sqlite3.Connection):
        raise MigrationBlocked("CONNECTION_INVALID")
    # This is an offline simulation, not a live migration tool.
    attached=db.execute("PRAGMA database_list").fetchall()
    if len(attached)!=1 or attached[0][1]!="main" or attached[0][2]!="":
        raise MigrationBlocked("MEMORY_ONLY")
    if db.in_transaction: raise MigrationBlocked("OPEN_TRANSACTION")
    content=SCHEMA_PATH.read_bytes()
    actual=sha(content)
    if not isinstance(source_sha256,str) or not re.fullmatch("[0-9a-f]{64}",source_sha256) or actual!=source_sha256:
        raise MigrationBlocked("SOURCE_PIN_MISMATCH")
    before,objects=foreign_schema(db)
    if before!=foreign_sha256: raise MigrationBlocked("SCHEMA_PIN_MISMATCH")
    if any(name.startswith(PREFIX) for _,name,_,_ in objects):
        raise MigrationBlocked("RESERVED_NAMESPACE_COLLISION")
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("BEGIN IMMEDIATE;\n"+content.decode("utf-8")+"\nCOMMIT;")
        after,new_objects=foreign_schema(db)
        t={name for kind,name,_,_ in new_objects if kind=="table" and name.startswith(PREFIX)}
        triggers={name for kind,name,_,_ in new_objects if kind=="trigger" and name.startswith(PREFIX)}
        if after!=before or t!=TABLES or triggers!=TRIGGERS or db.execute("PRAGMA foreign_key_check").fetchall():
            raise MigrationBlocked("POSTCONDITION_FAILED")
    except Exception as error:
        if db.in_transaction: db.rollback()
        if isinstance(error,MigrationBlocked): raise
        raise MigrationBlocked("ATOMIC_MIGRATION_FAILURE") from error
    return MigrationPreview(actual,before,True,len(t),len(triggers))

"""Offline schema-profile qualification for Cloudflare D1 table-only R18B.

D1's remote SQL splitter does not reliably qualify the compound triggers in
the R18 original. This profile retains structural constraints but intentionally
does not claim database-enforced immutability. NEVER use this report as an
independent scientific custody/retention/first-use acceptance receipt.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib, re, sqlite3
try:
    from .migration import foreign_schema
except ImportError:  # unittest discovery with d1retention as test root
    from migration import foreign_schema

PATH=Path(__file__).with_name("schema_d1_compat.sql")
NAMES=("forge_research_originals","forge_research_chunks","forge_research_seals")

class CompatibilityBlocked(ValueError):
    pass

@dataclass(frozen=True)
class CompatibilityReview:
    sql_sha256: str
    original_foreign_schema_sha256: str
    existing_data_preserved: bool
    tables_installed: int
    remote_install_performed: bool=False
    db_enforced_immutability_verified: bool=False
    original_custody_verified: bool=False
    first_use_reconciled: bool=False
    scientific_accepted: bool=False
    dispatch_authorized: bool=False

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def statements(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<16000 or b"\r" in raw or b"\x00" in raw:
        raise CompatibilityBlocked("SQL_SOURCE_BOUNDS_OR_LINE_ENDING_DRIFT")
    try:src=raw.decode("utf-8")
    except UnicodeError as exc:raise CompatibilityBlocked("SQL_UTF8_INVALID") from exc
    result=[]
    buf=""
    for line in src.splitlines(keepends=True):
        buf+=line
        if sqlite3.complete_statement(buf):
            body=re.sub(r"(?m)^[ \t]*--[^\n]*(?:\n|$)","",buf).strip()
            result.append(body)
            buf=""
    if buf.strip() or len(result)!=3:
        raise CompatibilityBlocked("REQUIRE_EXACT_THREE_D1_TABLES")
    for statement,name in zip(result,NAMES):
        if not re.match(r"(?is)\ACREATE TABLE "+name+r"\s*\(",statement):
            raise CompatibilityBlocked("UNEXPECTED_DDL_OBJECT_OR_ORDER")
        # Exact source is pinned by byte-SHA and commit; forbid dangerous
        # alternate DDL from entering this narrowly scoped profile.
        if re.search(r"(?i)\b(TRIGGER|DROP|ALTER|DELETE|UPDATE|INSERT|REPLACE|ATTACH|PRAGMA)\b",statement):
            raise CompatibilityBlocked("UNSUPPORTED_D1_DDL")
        if statement.count(";")!=1 or not statement.endswith(";"):
            raise CompatibilityBlocked("UNEXPECTED_STATEMENT_SPLIT")
    return tuple(result)

def offline_qualify(db,expected_sql_sha256,expected_foreign_sha256):
    if not isinstance(db,sqlite3.Connection):
        raise CompatibilityBlocked("DB_CONNECTION_REQUIRED")
    attached=db.execute("PRAGMA database_list").fetchall()
    if len(attached)!=1 or attached[0][1]!="main" or attached[0][2]!="":
        raise CompatibilityBlocked("IN_MEMORY_ONLY")
    if db.in_transaction:raise CompatibilityBlocked("OPEN_TRANSACTION")
    raw=PATH.read_bytes()
    if not isinstance(expected_sql_sha256,str) or sha(raw)!=expected_sql_sha256:
        raise CompatibilityBlocked("SOURCE_IDENTITY_DRIFT")
    current,objects=foreign_schema(db)
    if current!=expected_foreign_sha256:
        raise CompatibilityBlocked("FOREIGN_SCHEMA_IDENTITY_DRIFT")
    if any(name.startswith("forge_research_") for _,name,_,_ in objects):
        raise CompatibilityBlocked("RESERVED_NAMESPACE_COLLISION")
    sql=statements(raw)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("BEGIN IMMEDIATE;\n"+"\n".join(sql)+"\nCOMMIT;")
        observed,entries=foreign_schema(db)
        names={name for kind,name,_,_ in entries
               if name.startswith("forge_research_") and kind=="table"}
        unexpected=[name for kind,name,_,_ in entries
                    if name.startswith("forge_research_") and kind!="table"]
        if observed!=current or names!=set(NAMES) or unexpected:
            raise CompatibilityBlocked("POST_INSTALL_SCHEMA_DRIFT")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise CompatibilityBlocked("POST_INSTALL_FOREIGN_KEY_FAILURE")
    except Exception as exc:
        if db.in_transaction:db.rollback()
        if isinstance(exc,CompatibilityBlocked):raise
        raise CompatibilityBlocked("SQLITE_ATOMIC_INSTALL_FAILURE") from exc
    return CompatibilityReview(sha(raw),current,True,len(names))

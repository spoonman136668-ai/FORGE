"""F62: actual existing Cloudflare D1 first-use schema recovery preflight.

READ ONLY. This module never issues SQL other than bounded SELECT queries,
never installs a migration, never creates a Worker route, never reveals the
Time Travel bookmark, and never authorizes a protected original.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sqlite3
import sys

import install_remote as cf
import r18c_witness as witness

HERE = pathlib.Path(__file__).resolve().parent
R35 = HERE / "r35_atomic_preuse_candidate.sql"
R38 = HERE / "r38_monotonic_preuse_candidate.sql"
SCHEMA = "forge.f62.existing-d1-firstuse-readonly-recovery-preflight.v1"
MIGRATION_OBJECTS = frozenset((
    "forge_original_preuse_claims",
    "forge_original_preuse_claims_update_immutable",
    "forge_original_preuse_claims_delete_immutable",
    "forge_original_preuse_claims_insert_monotonic",
))
ORIGINALS = frozenset(cf.EXPECTED_OBJECTS)

class Denied(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise Denied("F62_" + reason)

def migration_sql() -> tuple[list[str], str]:
    parts = []
    bytes_all = []
    for path in (R35, R38):
        require(path.is_file() and not path.is_symlink() and
                0 < path.stat().st_size <= 20000, "SOURCE_SQL_NOT_REGULAR")
        raw = path.read_bytes()
        require(len(raw) == path.stat().st_size, "SOURCE_SQL_READ_RACE")
        bytes_all.append(raw)
        try:
            src = raw.decode("utf-8")
        except UnicodeError as exc:
            raise Denied("F62_SOURCE_ENCODING_INVALID") from exc
        buffer = ""
        for line in src.splitlines(keepends=True):
            buffer += line
            if sqlite3.complete_statement(buffer):
                parts.append(buffer.strip())
                buffer = ""
        require(not buffer.strip(), "MIGRATION_INCOMPLETE")
    require(len(parts) == 4, "MIGRATION_UNEXPECTED_STATEMENT_COUNT")
    syntax = []
    for statement in parts:
        without_comments = re.sub(r"\A(?:\s*--[^\n]*(?:\n|\Z))*", "",
                                  statement).strip()
        syntax.append(without_comments)
    require(syntax[0].startswith("CREATE TABLE IF NOT EXISTS forge_original_preuse_claims (") and
            syntax[1].startswith("CREATE TRIGGER IF NOT EXISTS forge_original_preuse_claims_update_immutable") and
            syntax[2].startswith("CREATE TRIGGER IF NOT EXISTS forge_original_preuse_claims_delete_immutable") and
            syntax[3].startswith("CREATE TRIGGER IF NOT EXISTS forge_original_preuse_claims_insert_monotonic") and
            all(not re.search(r"\b(?:DROP|ALTER|DELETE|UPDATE|INSERT|REPLACE|ATTACH|PRAGMA)\b",s,
                              re.I) for s in syntax[:1]),
            "UNEXPECTED_MIGRATION_SQL")
    # Source-only proof: preservation of existing scientific archive tables,
    # and every R35/R38 immutable/monotonic object actually appears.
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE forge_research_originals (id INTEGER PRIMARY KEY, seal TEXT)")
        db.execute("CREATE TABLE forge_research_seals (id INTEGER PRIMARY KEY, seal TEXT)")
        for i in range(1,7):
            db.execute("INSERT INTO forge_research_originals VALUES (?,?)", (i,"unchanged"))
            db.execute("INSERT INTO forge_research_seals VALUES (?,?)", (i,"unchanged"))
        previous = tuple(db.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name LIKE 'forge_research_%' ORDER BY name"))
        db.executescript("\n".join(parts))
        current = tuple(db.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name LIKE 'forge_research_%' ORDER BY name"))
        require(current == previous and
                db.execute("SELECT COUNT(*) FROM forge_research_originals").fetchone()[0] == 6 and
                db.execute("SELECT COUNT(*) FROM forge_research_seals").fetchone()[0] == 6,
                "PRESERVED_ARCHIVE_SCHEMA_DRIFT")
        observed = frozenset(row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'forge_original_preuse_%'"))
        require(observed == MIGRATION_OBJECTS, "MIGRATION_OBJECTS_DRIFT")
        record = ("a"*64,"Wingless",7,"b"*40,"c"*64,"d"*64,100)
        db.execute("INSERT INTO forge_original_preuse_claims "
            "(original_key_sha256,lane,owner_epoch,source_commit_sha,"
            "frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) "
            "VALUES (?,?,?,?,?,?,?)",record)
        for impossible in (
            ("e"*64,"Wingless",7,"b"*40,"c"*64,"d"*64,99),
            ("a"*64,"Wingless",7,"b"*40,"c"*64,"d"*64,101),
            ("f"*64,"Yggdrasil",6,"b"*40,"c"*64,"d"*64,102),
        ):
            try:
                db.execute("INSERT INTO forge_original_preuse_claims "
                    "(original_key_sha256,lane,owner_epoch,source_commit_sha,"
                    "frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) "
                    "VALUES (?,?,?,?,?,?,?)",impossible)
            except sqlite3.DatabaseError:
                pass
            else:
                raise Denied("F62_REPLAY_OR_EPOCH_ROLLBACK_ACCEPTED")
        require(db.execute("SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0] == 1,
                "MIGRATION_DUPLICATE_UNEXPECTED")
    h = hashlib.sha256(bytes_all[0] + b"\x00" + bytes_all[1]).hexdigest()
    return parts, h

def audit(api) -> dict:
    """Remote D1 reads are authoritative for current deployment metadata only."""
    parts, migration_sha = migration_sql()
    require(len(parts) == 4, "MIGRATION_NOT_VALID")
    database = cf.single_deployed_database(api)
    names, foreign = cf.schema_snapshot(api, database)
    require(names == ORIGINALS and foreign == witness.BASELINE_SCHEMA_SHA256,
            "EXISTING_ARCHIVE_SCHEMA_OR_FOREIGN_DRIFT")
    for name in ("forge_research_originals","forge_research_seals"):
        rows = cf.sql_query(api,database,"SELECT COUNT(*) AS n FROM "+name)
        require(len(rows)==1 and type(rows[0].get("n")) is int and rows[0]["n"]==6,
                "SIX_SEALED_ARCHIVE_COUNT_DRIFT")
    absent = cf.sql_query(api,database,
        "SELECT type,name FROM sqlite_master WHERE name IN "
        "('forge_original_preuse_claims',"
        "'forge_original_preuse_claims_update_immutable',"
        "'forge_original_preuse_claims_delete_immutable',"
        "'forge_original_preuse_claims_insert_monotonic')")
    require(absent == [], "F62_MIGRATION_ALREADY_PRESENT_STOP")
    # D2R: classify only the live D1 namespace, not a separately hosted signer.
    # Unexpected FORGE FSA objects require a different independently pinned audit;
    # never infer their trust or silently reinterpret the known schema.
    fsa_objects = cf.sql_query(api,database,
        "SELECT type,name FROM sqlite_master WHERE "
        "name GLOB 'forge_fsa_*' OR name GLOB 'forge_original_preuse_*' "
        "ORDER BY name LIMIT 32")
    require(fsa_objects == [], "UNRECONCILED_NATIVE_FSA_NAMESPACE")
    # An observation-only bookmark is not a private verified backup or
    # permission to restore. Never print, store or export the bookmark.
    bookmark = cf.recovery_bookmark(api,database)
    require(isinstance(bookmark,str) and len(bookmark)>=20, "BOOKMARK_UNAVAILABLE")
    return {
        "schema": SCHEMA,
        "existing_worker_and_database_identity_verified": True,
        "six_previous_original_archives_and_seals_unchanged": True,
        "r35_r38_additive_migration_source_locally_qualified": True,
        "proposed_migration_sha256":migration_sha,
        "d1_time_travel_bookmark_readable":True,
        "private_verified_backup_created":False,
        "real_atomic_preuse_table_deployed":False,
        "native_fsa_namespace_objects_in_bound_d1":0,
        "independent_witness_and_highwater_authenticated":False,
        "complete_consumed_active_uncertain_two_lane_ledger_authenticated":False,
        "independently_authenticated_current_owner_and_all_lane_history":False,
        "protected_main_oidc_scientific_issuer_authorized":False,
        "worker_firstuse_cas_performed":False,
        "worker_permit_issued":False,
        "research_originals_dispatched":0,
        "scientific_execution_authorized":False,
        "owner_cutover_authorized":False,
        "disposition":"BLOCKED_OWNER_CUSTODY_AND_D1_MIGRATION_NOT_DEPLOYED",
    }

def main() -> None:
    import os
    token = os.environ.get("CLOUDFLARE_API_TOKEN","")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
    api = cf.Cloudflare(account,token)
    data = audit(api)
    print(json.dumps(data,sort_keys=True,separators=(",",":")))

if __name__ == "__main__":
    try:
        main()
    except (Denied,cf.InstallBlocked,sqlite3.DatabaseError) as exc:
        print("F62_LIVE_D1_READONLY_BLOCKED="+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)

"""R18C: read-only pre/post witness for a single protected D1 file import.

Only the separately fenced operator workflow calls wrangler d1 execute --file.
This module makes read-only metadata queries and is safe to test in mock CI.
Never prints token/account/DB UUID/backup bookmark/row contents.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from install_remote import Cloudflare, InstallBlocked, single_deployed_database, schema_snapshot, recovery_bookmark, check_pins, sql_query, EXPECTED_OBJECTS

BASELINE_SCHEMA_SHA256 = "b23212f1837fd9255597490098f7d7777db23006a89f3facc0f5d0ae3f01fac2"
SQL_SHA256 = "d5b3e4c1999afe1d5b61fe27a7be17c4ed446c4b85418c0859e4acf4482e765c"
ORIGINAL_KINDS = {
    "forge_research_originals":"table",
    "forge_research_chunks":"table",
    "forge_research_seals":"table",
}
EXPECTED_KINDS = {**ORIGINAL_KINDS, **{name:"trigger" for name in EXPECTED_OBJECTS if name not in ORIGINAL_KINDS}}
SAFE_NAME = re.compile(r"[a-zA-Z0-9_.-]{1,100}\Z")

def reject(reason):
    raise InstallBlocked(reason)

def table_row_count(api, db):
    print('R18C_READONLY_STAGE=DISCOVER_FOREIGN_TABLE')
    rows=sql_query(api,db,"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT GLOB 'forge_research_*' LIMIT 2")
    if len(rows)!=1:
        reject("EXACTLY_ONE_FOREIGN_TABLE_REQUIRED")
    name=rows[0].get("name")
    if not isinstance(name,str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}",name) is None:
        reject("UNSAFE_FOREIGN_TABLE_IDENTIFIER")
    print('R18C_READONLY_STAGE=COUNT_FOREIGN_ROWS')
    count=sql_query(api,db,'SELECT COUNT(*) AS n FROM "'+name+'"')
    if len(count)!=1 or not isinstance(count[0].get("n"),int) or count[0]["n"]<0:
        reject("FOREIGN_TABLE_COUNT_INVALID")
    return count[0]["n"]

def read_archive_schema(api,db):
    rows=sql_query(api,db,
        "SELECT type,name,sql FROM sqlite_master WHERE name GLOB 'forge_research_*' ORDER BY name LIMIT 32")
    if len(rows)>=32 or not all(isinstance(x,dict) and
          isinstance(x.get("type"),str) and isinstance(x.get("name"),str)
          and isinstance(x.get("sql"),str) for x in rows):
        reject("ARCHIVE_DDL_READ_UNQUALIFIED")
    return rows

def read_originals_empty(api,db):
    for name in ORIGINAL_KINDS:
        rows=sql_query(api,db,"SELECT COUNT(*) AS n FROM "+name)
        if len(rows)!=1 or rows[0].get("n")!=0:
            reject("ARCHIVE_CONTAINS_DATA_STOP")

def verify_after(api,db,state):
    objects=read_archive_schema(api,db)
    seen={x["name"]:x["type"] for x in objects}
    if len(objects)!=len(EXPECTED_KINDS) or seen!=EXPECTED_KINDS:
        reject("POST_INSTALL_OBJECTS_MISSING_OR_UNEXPECTED")
    for row in objects:
        if row["type"]=="trigger" and not all(token in row["sql"].upper()
            for token in ("BEFORE ", "BEGIN", "END", "RAISE(ABORT")):
            reject("POST_INSTALL_TRIGGER_GUARD_ABSENT")
    own,foreign=schema_snapshot(api,db)
    if own!=EXPECTED_OBJECTS or foreign!=state["foreign_sha"]:
        reject("POST_INSTALL_FOREIGN_SCHEMA_DRIFT")
    if table_row_count(api,db)!=state["original_rows"]:
        reject("POST_INSTALL_ORIGINAL_ROW_COUNT_DRIFT")
    read_originals_empty(api,db)
    return len(objects)

def preflight(api,db):
    print('R18C_READONLY_STAGE=EXISTING_DDL')
    own,foreign=schema_snapshot(api,db)
    if own or foreign!=BASELINE_SCHEMA_SHA256:
        reject("PRE_INSTALL_SCHEMA_IDENTITY_DRIFT_OR_COLLISION")
    print('R18C_READONLY_STAGE=EXISTING_TABLE_COUNT')
    count=table_row_count(api,db)
    print('R18C_READONLY_STAGE=TIME_TRAVEL_BOOKMARK')
    bookmark=recovery_bookmark(api,db)
    return {"foreign_sha":foreign,"original_rows":count,
            "recovery_bookmark":bookmark}

def run(argv=None,api=None):
    p=argparse.ArgumentParser()
    p.add_argument("--stage",required=True,choices=("preflight","postflight"))
    p.add_argument("--head",required=True)
    p.add_argument("--private-dir",required=True)
    a=p.parse_args(argv)
    check_pins(a.head,SQL_SHA256)
    dest=Path(a.private_dir).resolve()
    if not dest.is_dir():reject("PRIVATE_DIR_ABSENT")
    if api is None:
        token=os.environ.get("CLOUDFLARE_API_TOKEN","")
        account=os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
        api=Cloudflare(account,token)
    print('R18C_READONLY_STAGE=PINNED_BINDING')
    db=single_deployed_database(api)
    if a.stage=="preflight":
        print('R18C_READONLY_STAGE=SCHEMA_AND_COUNT')
        state=preflight(api,db)
        print('R18C_READONLY_STAGE=METADATA_RESOLVED')
        # No database changes until both objects have been created privately.
        statepath=dest/"r18c.json"
        cfgpath=dest/"r18c-wrangler.json"
        database=api.call("accounts/"+api.account+"/d1/database/"+db)
        dbname=database.get("name") if isinstance(database,dict) else None
        if not isinstance(dbname,str) or SAFE_NAME.fullmatch(dbname) is None:
            reject("D1_NAME_NOT_SAFE_FOR_PINNED_WRANGLER")
        payload={"foreign_sha":state["foreign_sha"],
            "original_rows":state["original_rows"],
            "recovery_bookmark":state["recovery_bookmark"],
            "pinned_head":a.head,"sql_sha256":SQL_SHA256,
            "db_id":db}
        wrangler={"name":"forge-r18c-qualification-only",
            "compatibility_date":"2026-10-15",
            "d1_databases":[{"binding":"forge","database_name":dbname,
                              "database_id":db}]}
        for target,content in ((statepath,payload),(cfgpath,wrangler)):
            fd=os.open(str(target), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as file:
                json.dump(content,file,separators=(",",":"))
                file.flush();os.fsync(file.fileno())
        print("R18C_PREFLIGHT=PASS")
        print("R18C_BASELINE_SCHEMA=EXACT_PIN")
        print("R18C_PROTECTED_DDL=11_OBJECTS_PINNED")
        print("R18C_BOOKMARK=SAVED_PRIVATELY")
        print("R18C_SCHEMA_WRITE=NOT_STARTED")
    else:
        payload=json.loads((dest/"r18c.json").read_text())
        if (payload.get("db_id")!=db or payload.get("pinned_head")!=a.head
            or payload.get("sql_sha256")!=SQL_SHA256
            or payload.get("foreign_sha")!=BASELINE_SCHEMA_SHA256):
            reject("POSTFLIGHT_PRIVATE_PIN_DRIFT")
        count=verify_after(api,db,payload)
        print("R18C_INSTALLATION=LIVE_SCHEMA_VERIFIED")
        print("R18C_GUARDED_OBJECTS="+str(count))
        print("R18C_ORIGINAL_USER_ROWS=UNCHANGED")
        print("R18C_IMPORTED_ORIGINALS=0")
        print("R18C_SCIENTIFIC_FIRST_USE=NOT_QUALIFIED")
        print("R18C_DISPATCH_AUTHORIZED=FALSE")

if __name__=="__main__":
    try:run()
    except (InstallBlocked,FileNotFoundError,ValueError,subprocess.CalledProcessError) as exc:
        print("R18C_BLOCKED="+(str(exc) if isinstance(exc,InstallBlocked) else "STATE_OR_SOURCE_INVALID"),file=sys.stderr)
        raise SystemExit(1)

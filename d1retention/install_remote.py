"""FORGE R18: controlled, explicitly invoked Cloudflare D1 schema installation.

Does NOT run in routine CI, start science, alter Cloudflare Workers, or create
resources. The operator must supply an existing account-scoped D1 Write token
OUTSIDE GitHub's public PR jobs and a private one-time recovery-file path.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

SQL_PATH = pathlib.Path(__file__).with_name("schema.sql")
SCRIPT = "curly-hat-6a9e"
BINDING = "forge"
EXPECTED_OBJECTS = {
    "forge_research_originals", "forge_research_chunks", "forge_research_seals",
    "forge_research_chunks_bounds", "forge_research_seals_complete",
    "forge_research_originals_update_immutable",
    "forge_research_originals_delete_immutable",
    "forge_research_chunks_update_immutable",
    "forge_research_chunks_delete_immutable",
    "forge_research_seals_update_immutable",
    "forge_research_seals_delete_immutable",
}
UUID = re.compile(r"[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}\Z")

class InstallBlocked(RuntimeError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_pins(expected_head, expected_sql):
    if not re.fullmatch(r"[a-f0-9]{40}", expected_head or ""):
        raise InstallBlocked("SOURCE_HEAD_PIN_REQUIRED")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sql or ""):
        raise InstallBlocked("SQL_SHA256_PIN_REQUIRED")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if source != expected_head:
        raise InstallBlocked("SOURCE_HEAD_DRIFT")
    raw = SQL_PATH.read_bytes()
    if sha(raw) != expected_sql:
        raise InstallBlocked("SQL_CONTENT_DRIFT")
    return raw

def split_sql(raw):
    # sqlite3.complete_statement handles semicolons INSIDE trigger BEGIN/END.
    # Never split trigger bodies by simply using str.split(";").
    try:
        src = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InstallBlocked("SQL_INVALID_UTF8") from exc
    statements, buf = [], ""
    for line in src.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            statements.append(buf.strip())
            buf = ""
    if buf.strip():
        raise InstallBlocked("SQL_PARTIAL_STATEMENT")
    if len(statements) != 11:
        raise InstallBlocked("SQL_UNEXPECTED_STATEMENT_COUNT")
    for i, stmt in enumerate(statements):
        without_comments = re.sub(r"\A(?:\s*--[^\n]*(?:\n|\Z))*", "", stmt).strip()
        allowed = "CREATE TABLE IF NOT EXISTS" if i < 3 else "CREATE TRIGGER IF NOT EXISTS"
        if not without_comments.upper().startswith(allowed):
            raise InstallBlocked("SQL_UNEXPECTED_STATEMENT_TYPE")
    return statements

class Cloudflare:
    def __init__(self, account, token):
        if not re.fullmatch("[a-f0-9]{32}", account or "") or not token:
            raise InstallBlocked("ACCOUNT_OR_TOKEN_ABSENT")
        self.account, self.token = account, token

    def call(self, path, method="GET", data=None):
        if not path.startswith("accounts/"+self.account+"/") or ".." in path:
            raise InstallBlocked("API_SCOPE_ESCAPE")
        body = None if data is None else json.dumps(data, separators=(",", ":")).encode()
        req = urllib.request.Request(
            "https://api.cloudflare.com/client/v4/"+path,
            headers={"Authorization":"Bearer "+self.token,
                     "Accept":"application/json",
                     "Content-Type":"application/json"},
            data=body, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read(262145)
        except urllib.error.HTTPError as exc:
            raise InstallBlocked("CLOUDFLARE_HTTP_"+str(exc.code)) from None
        except Exception as exc:
            raise InstallBlocked("CLOUDFLARE_TRANSPORT_FAILED") from exc
        if len(raw) > 262144:
            raise InstallBlocked("RESPONSE_TOO_LARGE")
        try:
            item = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise InstallBlocked("CLOUDFLARE_RESPONSE_MALFORMED") from None
        if not isinstance(item, dict) or item.get("success") is not True:
            raise InstallBlocked("CLOUDFLARE_API_REJECTED")
        return item.get("result")

def single_deployed_database(api):
    a = api.account
    deploys = api.call("accounts/"+a+"/workers/scripts/"+SCRIPT+"/deployments")
    versions = deploys.get("deployments",[{}])[0].get("versions",[]) if isinstance(deploys,dict) else []
    serving = [v for v in versions if isinstance(v,dict) and
               isinstance(v.get("percentage"),(int,float)) and v["percentage"]>0]
    if len(serving)!=1 or serving[0]["percentage"]!=100:
        raise InstallBlocked("NOT_EXACTLY_ONE_LIVE_VERSION")
    version_id = serving[0].get("version_id")
    if not isinstance(version_id,str) or UUID.fullmatch(version_id) is None:
        raise InstallBlocked("LIVE_VERSION_ID_INVALID")
    ver = api.call("accounts/"+a+"/workers/scripts/"+SCRIPT+"/versions/"+version_id)
    resources = ver.get("resources") if isinstance(ver,dict) else None
    bindings = resources.get("bindings") if isinstance(resources,dict) else None
    bound = [b for b in bindings if isinstance(b,dict) and b.get("type")=="d1"
             and b.get("name")==BINDING] if isinstance(bindings,list) else []
    if len(bound)!=1:
        raise InstallBlocked("LIVE_FORGE_D1_BINDING_MISSING")
    dbid = bound[0].get("database_id") or bound[0].get("id")
    if not isinstance(dbid,str) or UUID.fullmatch(dbid) is None:
        raise InstallBlocked("LIVE_FORGE_D1_ID_INVALID")
    databases = api.call("accounts/"+a+"/d1/database?per_page=10&page=1")
    if not isinstance(databases,list) or len(databases)!=1 or databases[0].get("uuid")!=dbid:
        raise InstallBlocked("D1_DATABASE_IDENTITY_NOT_UNIQUE")
    db = api.call("accounts/"+a+"/d1/database/"+dbid)
    if not isinstance(db,dict) or db.get("uuid")!=dbid or db.get("version")!="production":
        raise InstallBlocked("D1_NOT_PRODUCTION_OR_ID_DRIFT")
    return dbid

def sql_query(api, dbid, sql):
    if not sql.lstrip().upper().startswith("SELECT "):
        raise InstallBlocked("READ_ONLY_SQL_EXPECTED")
    result = api.call("accounts/"+api.account+"/d1/database/"+dbid+"/query",
                      method="POST", data={"sql":sql,"params":[]})
    if not isinstance(result,list) or len(result)!=1 or not isinstance(result[0],dict):
        raise InstallBlocked("SQL_RESULT_SHAPE_INVALID")
    item = result[0]
    meta = item.get("meta")
    if item.get("success") is not True or not isinstance(meta,dict) or (
        meta.get("changes",0)!=0 or meta.get("changed_db") is True):
        raise InstallBlocked("READ_ONLY_SQL_FAILED_OR_CHANGED_DATABASE")
    rows = item.get("results")
    if not isinstance(rows,list) or len(rows)>128:
        raise InstallBlocked("SQL_ROW_BOUNDS")
    return rows

def schema_snapshot(api, dbid):
    rows = sql_query(api,dbid,
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name,tbl_name LIMIT 128")
    if len(rows)==128 or not all(
        isinstance(r,dict) and all(isinstance(r.get(k),str) for k in ("type","name","tbl_name","sql"))
        for r in rows):
        raise InstallBlocked("SCHEMA_SNAPSHOT_INCOMPLETE")
    own={r["name"] for r in rows if r["name"].startswith("forge_research_")}
    foreign=[[r[k] for k in ("type","name","tbl_name","sql")] for r in rows
             if not r["name"].startswith("forge_research_")]
    foreign_hash=sha(json.dumps(foreign,separators=(",",":"),ensure_ascii=True).encode())
    return own,foreign_hash

def recovery_bookmark(api, dbid):
    obj = api.call("accounts/"+api.account+"/d1/database/"+dbid+"/time_travel/bookmark")
    value = obj.get("bookmark") if isinstance(obj,dict) else None
    if not isinstance(value,str) or len(value)>160 or not re.fullmatch(r"[0-9a-fA-F-]{20,160}",value):
        raise InstallBlocked("TIME_TRAVEL_BOOKMARK_NOT_QUALIFIED")
    return value

def apply_once(api, dbid, statements, *, recovery_file, bookmark, schema_sha, foreign_sha):
    if not recovery_file:
        raise InstallBlocked("PRIVATE_RECOVERY_FILE_REQUIRED")
    dest=pathlib.Path(recovery_file).expanduser().resolve()
    if not dest.parent.is_dir():
        raise InstallBlocked("RECOVERY_PARENT_UNAVAILABLE")
    # Write once, private, BEFORE any attempt to mutate the database.
    # Preserve the checkpoint if remote SQL fails; never auto-restore.
    fd=os.open(str(dest),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        payload=json.dumps({"schema_sha256":schema_sha,
            "foreign_schema_sha256":foreign_sha,
            "recovery_bookmark":bookmark,
            "recovery_notice":"DESTRUCTIVE_RESTORE_REQUIRES_SEPARATE_OPERATOR_AUTHORIZATION"},
            separators=(",",":")).encode()
        with os.fdopen(fd,"wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        raise InstallBlocked("RECOVERY_RECORD_WRITE_FAILED") from None
    # Cloudflare's D1 batch body sends all statements as one batch.
    # Do not retry automatically: interruption or a partial result requires
    # manual reconciliation against the saved bookmark.
    results=api.call("accounts/"+api.account+"/d1/database/"+dbid+"/query",
                     method="POST",data={"batch":[{"sql":stmt,"params":[]}
                                                 for stmt in statements]})
    if not isinstance(results,list) or len(results)!=len(statements) or any(
        not isinstance(row,dict) or row.get("success") is not True for row in results):
        raise InstallBlocked("REMOTE_MIGRATION_FAILED_INSPECT_BOOKMARK")
    return True

def run(argv=None, api=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--expected-head",required=True)
    parser.add_argument("--expected-sql-sha256",required=True)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--recovery-file")
    args=parser.parse_args(argv)
    raw=check_pins(args.expected_head,args.expected_sql_sha256)
    statements=split_sql(raw)
    if api is None:
        token_var="CLOUDFLARE_D1_WRITE_TOKEN" if args.apply else "CLOUDFLARE_API_TOKEN"
        api=Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID",""),
                       os.environ.get(token_var,""))
    dbid=single_deployed_database(api)
    own,before=schema_snapshot(api,dbid)
    if own:
        raise InstallBlocked("ARCHIVE_NAMESPACE_ALREADY_EXISTS")
    bookmark=recovery_bookmark(api,dbid)
    if args.apply:
        if os.environ.get("FORGE_R18_APPLY_AUTHORIZATION") != "INSTALL_EXISTING_FORGE_D1_ONCE":
            raise InstallBlocked("EXPLICIT_ONE_TIME_AUTHORIZATION_MISSING")
        apply_once(api,dbid,statements,recovery_file=args.recovery_file,
                   bookmark=bookmark,schema_sha=sha(raw),foreign_sha=before)
        after_names,after=schema_snapshot(api,dbid)
        if after!=before or after_names!=EXPECTED_OBJECTS:
            raise InstallBlocked("POST_INSTALL_DRIFT_USE_PRIVATE_RECOVERY_BOOKMARK")
        print("R18_D1_MIGRATION=INSTALLED_AND_SCHEMA_MATCHED")
    else:
        print("R18_D1_MIGRATION=PRECHECK_ONLY")
    print("R18_LIVE_DATABASE_ID_MATCH=PASS")
    print("R18_RECOVERY_BOOKMARK=AVAILABLE_REDACTED")
    print("R18_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("R18_ORIGINAL_EXPERIMENTS_EXECUTED=0")

if __name__=="__main__":
    try:
        run()
    except (InstallBlocked,subprocess.CalledProcessError) as error:
        print("R18_BLOCKED="+(str(error) if isinstance(error,InstallBlocked)
                             else "GIT_SOURCE_UNAVAILABLE"),file=sys.stderr)
        raise SystemExit(1)

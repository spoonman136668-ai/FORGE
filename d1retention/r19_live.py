"""R19 authenticated once-only D1 archive intake pre/post readback.

Makes no autonomous research decisions; original source must have passed
FORGE researcharchive.Verify. All rows remain UNQUALIFIED. Provenance and
first-use custody remain separate independent-science admission gates.
"""
import argparse,hashlib,json,os,pathlib,re,sys
import install_remote as cf
import r18c_witness as witness
import r19_intake as intake

DB_TABLES=("forge_research_originals","forge_research_chunks","forge_research_seals")

class R19Blocked(Exception):pass
def block(why):raise R19Blocked(why)

def get_client():
    api=cf.Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID",""),
        os.environ.get("CLOUDFLARE_API_TOKEN",""))
    return api,cf.single_deployed_database(api)

def archive_ready(api,db):
    objects=witness.read_archive_schema(api,db)
    kinds={item["name"]:item["type"] for item in objects}
    if kinds!=witness.EXPECTED_KINDS or len(objects)!=11:
        block("R19_ARCHIVE_GUARDS_MISSING")
    own,foreign=cf.schema_snapshot(api,db)
    if own!=cf.EXPECTED_OBJECTS or foreign!=witness.BASELINE_SCHEMA_SHA256:
        block("R19_EXISTING_DATABASE_SCHEMA_DRIFT")

def clean_rows(api,db):
    for table in DB_TABLES:
        rows=cf.sql_query(api,db,"SELECT COUNT(*) AS n FROM "+table)
        if len(rows)!=1 or rows[0].get("n")!=0:
            block("R19_ARCHIVE_NOT_EMPTY_FAIL_CLOSED")

def save_private(folder,name,obj):
    p=folder/name
    if p.exists():block("R19_RECOVERY_OR_CONFIG_REPLAY")
    fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="utf8") as f:
        json.dump(obj,f,separators=(",",":"))
        f.flush();os.fsync(f.fileno())

def before(api,db,folder,sha):
    archive_ready(api,db)
    clean_rows(api,db)
    doc=api.call("accounts/"+api.account+"/d1/database/"+db)
    name=doc.get("name") if isinstance(doc,dict) else None
    if not isinstance(name,str) or re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}",name) is None:
        block("R19_EXISTING_DB_NAME_INVALID")
    checkpoint=cf.recovery_bookmark(api,db)
    save_private(folder,"r19-recovery.json",{
        "current_head":sha, "source":"6_PINNED_ORIGINALS",
        "database":db,
        "foreign_schema_sha256":witness.BASELINE_SCHEMA_SHA256,
        "bookmark":checkpoint,"scientific_authority":False})
    save_private(folder,"r19-wrangler.json",{
        "name":"forge-r19-one-time-archive-import",
        "compatibility_date":"2026-10-15",
        "d1_databases":[{"binding":"forge","database_name":name,"database_id":db}]})
    print("R19_PREWRITE=EXACT_11_GUARDS_AND_EMPTY_ARCHIVE")
    print("R19_TIME_TRAVEL=BOOKMARK_SAVED_PRIVATELY")
    print("R19_WRITE_AUTHORITY=SOURCE_ONLY_NOT_SCIENCE")

def assert_original_rows(api,db,e,manifest_sha,zip_raw):
    sha=e["archive_sha256"]
    # IDs derive exclusively from source-pinned manifest and are strict hex.
    if re.fullmatch(r"[0-9a-f]{64}",sha) is None:block("R19_SOURCE_HASH_INVALID")
    rows=cf.sql_query(api,db,
      "SELECT lane,experiment,repository,run_id,artifact_id,source_sha,"
      "frozen_manifest_sha256,original_length,chunk_count,scientific_state "
      "FROM forge_research_originals WHERE archive_sha256='"+sha+"'")
    if len(rows)!=1:block("R19_ORIGINAL_MISSING")
    r=rows[0]
    expected={"lane":e["lane"],"experiment":e["experiment"],
        "repository":e["repository"],"run_id":e["run_id"],
        "artifact_id":e["artifact_id"],"source_sha":e["head_sha"],
        "frozen_manifest_sha256":manifest_sha,
        "original_length":len(zip_raw),
        "chunk_count":(len(zip_raw)+intake.CHUNK_SIZE-1)//intake.CHUNK_SIZE,
        "scientific_state":"UNQUALIFIED"}
    if any(r.get(k)!=v for k,v in expected.items()):
        block("R19_ORIGINAL_IDENTITY_OR_STATE_DRIFT")
    seals=cf.sql_query(api,db,
        "SELECT declared_restored_sha256,declared_restored_length,seal_receipt_sha256 "
        "FROM forge_research_seals WHERE archive_sha256='"+sha+"'")
    if len(seals)!=1 or seals[0].get("declared_restored_sha256")!=sha or (
        seals[0].get("declared_restored_length")!=len(zip_raw)):
        block("R19_SEAL_MISSING_OR_DRIFT")
    wanted=intake.sha(b"FORGE_R19_UNQUALIFIED_SEAL_v1\0"+
       bytes.fromhex(sha)+bytes.fromhex(manifest_sha))
    if seals[0].get("seal_receipt_sha256")!=wanted:
        block("R19_SEAL_RECEIPT_DRIFT")
    chunks=cf.sql_query(api,db,
        "SELECT chunk_index,chunk_sha256,lower(hex(chunk_bytes)) AS chunk_hex "
        "FROM forge_research_chunks WHERE archive_sha256='"+sha+
        "' ORDER BY chunk_index LIMIT 65")
    if len(chunks)!=expected["chunk_count"]:block("R19_CHUNK_COUNT_DRIFT")
    observed=bytearray()
    for i,row in enumerate(chunks):
        h=row.get("chunk_hex")
        if row.get("chunk_index")!=i or not isinstance(h,str) or (
          not re.fullmatch(r"[0-9a-f]{2,32768}",h) or len(h)%2):
            block("R19_CHUNK_ORDER_OR_TYPE_DRIFT")
        blockbytes=bytes.fromhex(h)
        if row.get("chunk_sha256")!=intake.sha(blockbytes):
            block("R19_CHUNK_SHA_DRIFT")
        observed.extend(blockbytes)
    if len(observed)!=len(zip_raw) or intake.sha(observed)!=sha or bytes(observed)!=zip_raw:
        block("R19_RESTORED_BYTES_NOT_EQUAL_ORIGINAL")
    return len(zip_raw)

def after(api,db,folder,manifest_path,evidence):
    beforepin=json.loads((folder/"r19-recovery.json").read_text())
    if beforepin.get("database")!=db or beforepin.get("foreign_schema_sha256")!=(
       witness.BASELINE_SCHEMA_SHA256):
        block("R19_PINNED_ACCOUNT_OR_FOREIGN_SCHEMA_DRIFT")
    archive_ready(api,db)
    raw=manifest_path.read_bytes()
    entries=intake.manifest_entries(raw)
    manifest_sha=intake.sha(raw)
    total=0
    for e in entries:
        zip_raw=(evidence/(str(e["run_id"])+".zip")).read_bytes()
        if not zip_raw or intake.sha(zip_raw)!=e["archive_sha256"]:
            block("R19_SOURCE_ZIP_NO_LONGER_VALID")
        total+=assert_original_rows(api,db,e,manifest_sha,zip_raw)
    for table in DB_TABLES:
        rows=cf.sql_query(api,db,"SELECT COUNT(*) AS n FROM "+table)
        if len(rows)!=1:block("R19_POSTFLIGHT_TABLE_COUNT_MISSING")
        expected={"forge_research_originals":6,
                  "forge_research_chunks":sum(
                    (len((evidence/(str(e["run_id"])+".zip")).read_bytes())+intake.CHUNK_SIZE-1)//intake.CHUNK_SIZE
                    for e in entries),"forge_research_seals":6}[table]
        if rows[0].get("n")!=expected:block("R19_POSTFLIGHT_ROWS_UNEXPECTED")
    print("R19_REAL_ORIGINALS_D1_RESTORED=6")
    print("R19_WINGLESS_ARCHIVES=3")
    print("R19_YGGDRASIL_ARCHIVES=3")
    print("R19_SOURCE_ZIP_SHA_AND_BYTES=VERIFIED")
    print("R19_TOTAL_ORIGINAL_BYTES="+str(total))
    print("R19_ORIGINAL_EVIDENCE_CLASSIFICATION=UNQUALIFIED")
    print("R19_INDEPENDENT_FIRST_USE=NOT_RECONCILED")
    print("R19_EXPERIMENT_DISPATCH=NONE")

def run(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--phase",required=True,choices=("before","after"))
    p.add_argument("--manifest",required=True)
    p.add_argument("--evidence",required=True)
    p.add_argument("--private-dir",required=True)
    p.add_argument("--expected-head",required=True)
    a=p.parse_args(argv)
    if not re.fullmatch(r"[a-f0-9]{40}",a.expected_head):block("R19_BAD_GIT_PIN")
    import subprocess
    if subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()!=a.expected_head:
        block("R19_GIT_HEAD_DRIFT")
    folder=pathlib.Path(a.private_dir).resolve()
    if not folder.is_dir():block("R19_PRIVATE_DIR_ABSENT")
    api,db=get_client()
    if a.phase=="before":before(api,db,folder,a.expected_head)
    else:after(api,db,folder,pathlib.Path(a.manifest),pathlib.Path(a.evidence))

if __name__=="__main__":
    try:run()
    except (R19Blocked,cf.InstallBlocked,intake.IntakeBlocked,FileNotFoundError,
            ValueError,KeyError) as err:
        print("R19_LIVE_BLOCKED="+(
            str(err) if isinstance(err,(R19Blocked,cf.InstallBlocked,intake.IntakeBlocked))
            else "PIN_OR_SOURCE_MISSING"),file=sys.stderr)
        raise SystemExit(1)

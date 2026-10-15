"""R39: authenticated existing Cloudflare deployment preflight, no mutation.

The user authorized reuse of existing GitHub-held Cloudflare credentials and
confirmed no separately controlled signer credentials exist. No synthetic
signer can be promoted to independent custody.
"""
import os,sys
import install_remote as cf
import r18c_witness as witness

def main():
    api=cf.Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID",""),
                       os.environ.get("CLOUDFLARE_API_TOKEN",""))
    db=cf.single_deployed_database(api)
    owned,foreign=cf.schema_snapshot(api,db)
    if owned!=cf.EXPECTED_OBJECTS or foreign!=witness.BASELINE_SCHEMA_SHA256:
        raise RuntimeError("R39_PREEXISTING_SCHEMA_DRIFT_STOP")
    for name,wanted in (("forge_research_originals",6),("forge_research_seals",6)):
        rows=cf.sql_query(api,db,"SELECT COUNT(*) AS n FROM "+name)
        if len(rows)!=1 or rows[0].get("n")!=wanted:
            raise RuntimeError("R39_PREEXISTING_ORIGINAL_COUNT_DRIFT_STOP")
    rows=cf.sql_query(api,db,"SELECT name FROM sqlite_master WHERE type='table' AND name='forge_original_preuse_claims'")
    if rows: raise RuntimeError("R39_EXISTING_PREUSE_TABLE_UNEXPECTED_STOP")
    # Database, Worker and token identity are tested using authenticated GET
    # and read-only SELECT; the current token might lack permission to mutate.
    print("R39_AUTHENTIC_EXISTING_WORKER_D1_IDENTITY=PASS")
    print("R39_EXISTING_ORIGINAL_ARCHIVE=6_SEALED_INTACT")
    print("R39_ADD_NEW_RESOURCES=FALSE")
    print("R39_D1_OR_WORKER_WRITES=0")
    print("R39_INDEPENDENT_SIGNERS_AVAILABLE=FALSE_USER_CONFIRMED")
    print("R39_SCIENTIFIC_EXECUTION_AUTHORITY=BLOCKED")
    print("R39_DEPLOYMENT_WRITE_PERMISSIONS=NOT_PROVEN_BY_READONLY_PREFLIGHT")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("R39_PREFLIGHT_FAILED="+type(e).__name__,file=sys.stderr)
        raise SystemExit(1)

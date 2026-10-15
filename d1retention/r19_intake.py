"""R19: exact-byte SQL staging for authentic, previously executed research ZIPs.

Input is only a frozen six-original cohort already qualified using
researcharchive.Verify (original GitHub run, artifact metadata, ZIP bytes).
Produces a private write-once SQL file; never contacts Cloudflare and never
launches an experiment. Seal receipts are SELF-DECLARED, not signed first-use.
"""
from __future__ import annotations
import argparse,hashlib,json,os,pathlib,re,sys

CHUNK_SIZE=16384
EXPECTED_LANES={"Wingless","Yggdrasil"}
EXPECTED_COUNT=6
MAX_ZIP_BYTES=4<<20
HEX64=re.compile(r"[0-9a-f]{64}\Z")
HEX40=re.compile(r"[0-9a-f]{40}\Z")
SAFE_NAME=re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")

class IntakeBlocked(ValueError): pass

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def fail(reason):raise IntakeBlocked(reason)
def sql_string(value:str)->str:
    if (not isinstance(value,str) or not
        (SAFE_NAME.fullmatch(value) or re.fullmatch(r"spoonman136668-ai/(Wingless|Yggdrasil)",value))):
        fail("UNSAFE_SQL_IDENTITY")
    return "'"+value+"'"

def manifest_entries(raw:bytes):
    if not 0<len(raw)<=16384:fail("MANIFEST_SIZE_INVALID")
    try:document=json.loads(raw)
    except Exception as ex:raise IntakeBlocked("MANIFEST_INVALID") from ex
    if not isinstance(document,dict) or set(document)!={"schema","entries"} or (
      document["schema"]!="forge.research-archive.frozen-cohort.v1"
      or not isinstance(document["entries"],list) or len(document["entries"])!=EXPECTED_COUNT):
        fail("MANIFEST_IDENTITY_OR_COUNT")
    keys=set()
    for e in document["entries"]:
        if not isinstance(e,dict) or set(e)!={"lane","experiment","repository",
            "run_id","head_sha","workflow_path","artifact_id","artifact_name","archive_sha256"}:
            fail("MANIFEST_UNEXPECTED_FIELDS")
        lane=e["lane"]
        if lane not in EXPECTED_LANES or e["repository"]!="spoonman136668-ai/"+lane:
            fail("CROSS_LANE_IDENTITY")
        if not SAFE_NAME.fullmatch(e["experiment"]) or not SAFE_NAME.fullmatch(e["artifact_name"]):
            fail("UNSAFE_EXPERIMENT")
        if not all(isinstance(e[k],int) and not isinstance(e[k],bool) and e[k]>0
                   for k in ("run_id","artifact_id")):fail("SOURCE_NUMERIC_IDENTITY")
        if not HEX40.fullmatch(e["head_sha"]) or not HEX64.fullmatch(e["archive_sha256"]):
            fail("SOURCE_DIGEST_IDENTITY")
        if not re.fullmatch(r"\.github/workflows/qualify-[A-Za-z0-9_.-]+\.yml",e["workflow_path"]):
            fail("WORKFLOW_IDENTITY")
        key=(lane,e["experiment"])
        if key in keys:fail("DUPLICATE_EXPERIMENT")
        keys.add(key)
    if {e["lane"] for e in document["entries"]}!=EXPECTED_LANES:fail("MISSING_RESEARCH_LANE")
    return document["entries"]

def verify_observation(raw:bytes,entries:list,manifest_sha:str):
    try:obj=json.loads(raw)
    except Exception as ex:raise IntakeBlocked("OBSERVATION_MALFORMED") from ex
    if not isinstance(obj,dict) or obj.get("schema")!=(
        "forge.research-archive.original-byte-inventory.v1") or (
        obj.get("mode")!="ORIGINAL_ARCHIVE_BYTE_PRESERVATION_NOT_SCIENTIFIC_CUSTODY"
        or obj.get("manifest_sha256")!=manifest_sha
        or obj.get("archive_count")!=EXPECTED_COUNT
        or obj.get("wingless_count")!=3 or obj.get("yggdrasil_count")!=3):
        fail("NOT_AUTHENTIC_SIX_SOURCE_VERIFIER")
    for key in ("original_execution_authorized","complete_ckb_custody",
                "scientific_accepted","accepted_ref_mutation"):
        if obj.get(key) is not False:fail("OBSERVATION_ILLEGITIMATE_AUTHORITY")
    observed=obj.get("observations")
    if not isinstance(observed,list) or len(observed)!=len(entries):fail("OBSERVATION_COUNT")
    for entry,o in zip(entries,observed):
        if not isinstance(o,dict) or (
          o.get("lane")!=entry["lane"] or o.get("experiment")!=entry["experiment"]
          or o.get("original_run_id")!=entry["run_id"]
          or o.get("original_head_sha")!=entry["head_sha"]
          or o.get("artifact_id")!=entry["artifact_id"]
          or o.get("archive_sha256")!=entry["archive_sha256"]
          or o.get("archival_integrity_verified") is not True
          or o.get("scientific_classification")!="UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED"):
            fail("OBSERVATION_SOURCE_DRIFT")
        for key in ("preregistration_verified","first_use_reconciled","scientific_accepted"):
            if o.get(key) is not False:fail("OBSERVATION_AUTHORITY_DRIFT")

def statements(manifest_raw:bytes, observation_raw:bytes, evidence_dir:pathlib.Path):
    entries=manifest_entries(manifest_raw)
    manifest_sha=sha(manifest_raw)
    verify_observation(observation_raw,entries,manifest_sha)
    statements=[]
    for e in entries:
        raw=(evidence_dir/(str(e["run_id"])+".zip")).read_bytes()
        if not 0<len(raw)<=MAX_ZIP_BYTES or sha(raw)!=e["archive_sha256"]:
            fail("REAL_ZIP_MISSING_OR_HASH_DRIFT")
        chunks=[raw[i:i+CHUNK_SIZE] for i in range(0,len(raw),CHUNK_SIZE)]
        if len(chunks)>64:fail("TOO_MANY_CHUNKS")
        digest=sql_string(e["archive_sha256"])
        statements.append(
          "INSERT INTO forge_research_originals "
          "(archive_sha256,lane,experiment,repository,run_id,artifact_id,"
          "source_sha,frozen_manifest_sha256,original_length,chunk_count) VALUES ("+
          ",".join((digest,sql_string(e["lane"]),sql_string(e["experiment"]),
                    sql_string(e["repository"]),str(e["run_id"]),str(e["artifact_id"]),
                    sql_string(e["head_sha"]),sql_string(manifest_sha),
                    str(len(raw)),str(len(chunks))))+");")
        for i,c in enumerate(chunks):
            statements.append(
              "INSERT INTO forge_research_chunks "
              "(archive_sha256,chunk_index,chunk_sha256,chunk_bytes) VALUES ("+
              ",".join((digest,str(i),sql_string(sha(c)),"X'"+c.hex()+"'"))+");")
        # This is a deterministic structural receipt ONLY. It is not a signer,
        # and must never be considered first-use or independent FSA evidence.
        receipt=sha(b"FORGE_R19_UNQUALIFIED_SEAL_v1\0"+
                    bytes.fromhex(e["archive_sha256"])+bytes.fromhex(manifest_sha))
        statements.append("INSERT INTO forge_research_seals "
          "(archive_sha256,declared_restored_sha256,declared_restored_length,seal_receipt_sha256) VALUES ("+
          ",".join((digest,digest,str(len(raw)),sql_string(receipt)))+");")
    return statements

def prepare(manifest,evidence,out):
    evidence=pathlib.Path(evidence).resolve()
    statements_list=statements(pathlib.Path(manifest).read_bytes(),
                               (evidence/"observation.json").read_bytes(),evidence)
    output=pathlib.Path(out).resolve()
    if not output.parent.is_dir() or output.exists():fail("PRIVATE_NEW_SQL_PATH_REQUIRED")
    data=("\n".join(statements_list)+"\n").encode()
    fd=os.open(str(output),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as handle:
        handle.write(data);handle.flush();os.fsync(handle.fileno())
    print("R19_VERIFIED_ORIGINAL_COUNT=6")
    print("R19_SOURCE_BYTES_PRESENT=TRUE")
    print("R19_D1_IMPORT_SQL=STAGED_PRIVATELY")
    print("R19_FIRST_USE_AUTHORITY=NOT_QUALIFIED")
    print("R19_SCIENTIFIC_ACCEPTED=FALSE")
    print("R19_AUTONOMOUS_DISPATCH=FALSE")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--evidence-dir",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    try:prepare(args.manifest,args.evidence_dir,args.output)
    except (IntakeBlocked,FileNotFoundError) as ex:
        print("R19_PREPARATION_BLOCKED="+(str(ex) if isinstance(ex,IntakeBlocked) else "MISSING_SOURCE_FILE"),file=sys.stderr)
        raise SystemExit(1)

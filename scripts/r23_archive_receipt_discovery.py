"""R23 read-only custody receipt DISCOVERY inside six genuine original ZIP artifacts.

No evidence here qualifies physical signer separation or first-use consumption.
Never emits raw ZIP data, signature bytes, or a scientific admission.
"""
from __future__ import annotations
import hashlib
import io
import json
import pathlib
import re
import stat
import sys
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"reference/research-originals/20261013-six-recent-archive-cohort.json"
MAX_ZIP=4<<20
MAX_ENTRY=2<<20
SAFE=re.compile(r"[A-Za-z0-9_.-]{1,160}\Z")
class Blocked(ValueError): pass

def no_duplicate_keys(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise Blocked("DUPLICATE_JSON_KEY")
        out[k]=v
    return out

def parse(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_ENTRY:
        raise Blocked("INVALID_JSON_SIZE")
    try:
        return json.loads(raw,object_pairs_hook=no_duplicate_keys)
    except (ValueError,UnicodeError) as exc:
        raise Blocked("MALFORMED_JSON") from exc

def inspect_zip(raw,expected_sha):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_ZIP or (
        hashlib.sha256(raw).hexdigest()!=expected_sha):
        raise Blocked("SOURCE_ARCHIVE_SHA256_DRIFT")
    try:
        archive=zipfile.ZipFile(io.BytesIO(raw),"r")
        entries=archive.infolist()
    except (zipfile.BadZipFile,ValueError) as exc:
        raise Blocked("UNSAFE_ZIP") from exc
    if not 0<len(entries)<=24:
        raise Blocked("UNEXPECTED_ARCHIVE_STRUCTURE")
    seen=set()
    receipts={"birth":0,"started":0,"terminal":0}
    unreadable_json=0
    total=0
    for e in entries:
        name=e.filename
        mode=(e.external_attr>>16)&0xffff
        if (not SAFE.fullmatch(name) or name in seen or e.is_dir() or
            stat.S_IFMT(mode) not in (0,stat.S_IFREG) or
            e.file_size<=0 or e.file_size>MAX_ENTRY or
            e.compress_type not in (zipfile.ZIP_DEFLATED,zipfile.ZIP_STORED)):
            raise Blocked("UNSAFE_ARCHIVE_ENTRY")
        total+=e.file_size
        if total>MAX_ZIP:raise Blocked("ZIP_BOMB")
        seen.add(name)
        if not name.endswith(".json"): continue
        try:
            with archive.open(e) as fd:
                body=fd.read(MAX_ENTRY+1)
            if len(body)!=e.file_size:
                raise Blocked("ZIP_LENGTH_MISMATCH")
            doc=parse(body)
        except Blocked as exc:
            if str(exc) in ("ZIP_LENGTH_MISMATCH",):raise
            unreadable_json+=1
            continue
        if not isinstance(doc,dict):
            continue
        statement=doc.get("statement")
        if (isinstance(statement,dict) and
            statement.get("schema")=="forge.sourcebirth.signed-birth.v1" and
            isinstance(doc.get("issuer_signature_hex"),str) and
            isinstance(doc.get("witness_signature_hex"),str)):
            receipts["birth"]+=1
        signed=doc.get("receipt")
        if (isinstance(signed,dict) and
            signed.get("schema")=="forge.worker.original-receipt.v1" and
            isinstance(doc.get("signature_hex"),str) and
            signed.get("stage") in ("STARTED","TERMINAL")):
            receipts["started" if signed["stage"]=="STARTED" else "terminal"]+=1
    archive.close()
    return {"files_checked":len(entries),"json_unreadable":unreadable_json,
            "sourcebirth_candidate_files":receipts["birth"],
            "started_candidate_files":receipts["started"],
            "terminal_candidate_files":receipts["terminal"],
            "independent_signatures_verified":False,
            "complete_consumed_first_use_verified":False,
            "scientific_acceptance":False}

def inspect_cohort(raw_manifest,folder):
    m=parse(raw_manifest)
    if not isinstance(m,dict) or set(m)!={"schema","entries"} or m["schema"]!="forge.research-archive.frozen-cohort.v1":
        raise Blocked("INVALID_MANIFEST")
    rows=m["entries"]
    if not isinstance(rows,list) or len(rows)!=6:raise Blocked("EXPECTED_SIX_ORIGINALS")
    output=[]
    seen=set()
    for e in rows:
        if not isinstance(e,dict) or set(e)!={"lane","experiment","repository","run_id","head_sha","workflow_path","artifact_id","artifact_name","archive_sha256"}:
            raise Blocked("INVALID_MANIFEST_ROW")
        lane,experiment=e["lane"],e["experiment"]
        if lane not in ("Wingless","Yggdrasil") or e["repository"]!="spoonman136668-ai/"+lane or (lane,experiment) in seen:
            raise Blocked("LANE_DRIFT")
        seen.add((lane,experiment))
        rid=e["run_id"]
        if type(rid) is not int or rid<=0 or len(str(rid))>15:
            raise Blocked("INVALID_RUN_ID")
        raw=(folder/(str(rid)+".zip")).read_bytes()
        outcome=inspect_zip(raw,e["archive_sha256"])
        output.append({"lane":lane,"experiment":experiment,"run_id":rid,**outcome,
                       "classification":"ORIGINAL_ARCHIVE_SCOPED_ONLY_UNQUALIFIED"})
    if sum(p["lane"]=="Wingless" for p in output)!=3 or sum(p["lane"]=="Yggdrasil" for p in output)!=3:
        raise Blocked("TWO_LANE_SPLIT")
    return {
        "schema":"forge.research-archive.r23-receipt-discovery.v1",
        "originals":output,"archive_count":6,
        "scope":"SIX_AUTHENTIC_GITHUB_ORIGINAL_ZIPS_ONLY",
        "independent_custody_verified":False,
        "complete_first_use_high_water_verified":False,
        "live_optimizer_admitted":False,
        "new_originals_executed":0,
        "cloudflare_writes":0
    }

def main(argv):
    if len(argv)!=2:return 2
    try:
        output=inspect_cohort(MANIFEST.read_bytes(),pathlib.Path(argv[1]))
    except (Blocked,OSError,TypeError,KeyError,ValueError) as exc:
        print("R23_DISCOVERY_BLOCKED="+type(exc).__name__,file=sys.stderr)
        return 1
    print(json.dumps(output,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv))

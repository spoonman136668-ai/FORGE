"""R26 genuinely checks two existing F34 research artifacts for R25 owner inputs.

Archives must match independently fetched GitHub run/artifact metadata and frozen
ZIP digests. The scan is scoped to the two exact artifacts; absence never
means no evidence exists elsewhere. No scientific or first-use authority.
"""
import hashlib
import io
import json
import pathlib
import re
import stat
import sys
import zipfile

BASE=pathlib.Path(__file__).resolve().parents[1]
PIN=BASE/"reference/research-originals/20261015-r26-live-artifact-probe.json"
MAX_ARCHIVE=2*1024*1024
MAX_ENTRY=1024*1024
MAX_TOTAL=2*1024*1024
R25_OWNER="forge.dreamrsi.r25-prospective-owner-evidence.v1"
R25_PINS="forge.dreamrsi.r25-independent-source-pins.v1"
class Blocked(ValueError):pass

def pairs(values):
    out={}
    for key,value in values:
        if key in out:raise Blocked("DUPLICATE_JSON_FIELD")
        out[key]=value
    return out

def decode(data,limit):
    if not isinstance(data,bytes) or len(data)<1 or len(data)>limit:
        raise Blocked("UNBOUNDED_JSON")
    try:return json.loads(data,object_pairs_hook=pairs)
    except (ValueError,UnicodeError) as exc:raise Blocked("UNTRUSTED_JSON") from exc

def hex_digest(s):
    return isinstance(s,str) and len(s)==64 and all(c in "0123456789abcdef" for c in s)

def validate(manifest):
    if not isinstance(manifest,dict) or set(manifest)!={"schema","mode","entries"} or manifest["schema"]!="forge.r26.authentic-latest-owner-artifact-probe.v1" or manifest["mode"]!="READ_ONLY_TWO_REAL_RESEARCH_ARTIFACTS_NOT_INDEPENDENT_SCIENTIFIC_CUSTODY":
        raise Blocked("MANIFEST_SCHEMA")
    rows=manifest["entries"]
    if not isinstance(rows,list) or len(rows)!=2:raise Blocked("TWO_LANE_SCOPE_REQUIRED")
    for row,lane in zip(rows,("Wingless","Yggdrasil")):
        if not isinstance(row,dict) or set(row)!={"lane","repository","run_id","head_sha","workflow_path","artifact_id","artifact_name","artifact_zip_sha256"} or row["lane"]!=lane or row["repository"]!="spoonman136668-ai/"+lane or type(row["run_id"])!=int or row["run_id"]<=0 or type(row["artifact_id"])!=int or row["artifact_id"]<=0 or not isinstance(row["head_sha"],str) or len(row["head_sha"])!=40 or not isinstance(row["artifact_name"],str) or len(row["artifact_name"])>120 or not hex_digest(row["artifact_zip_sha256"]):
            raise Blocked("LIVE_SOURCE_PIN_INVALID")
    return rows

def inspect_zip(raw,sha):
    if not isinstance(raw,bytes) or len(raw)<1 or len(raw)>MAX_ARCHIVE or hashlib.sha256(raw).hexdigest()!=sha:
        raise Blocked("ARTIFACT_ZIP_DIGEST_DRIFT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw),"r") as z:
            entries=z.infolist()
            if not entries or len(entries)>40:raise Blocked("ARCHIVE_MEMBER_COUNT")
            seen=set()
            candidate={"owner":0,"pins":0,"regular_json":0}
            n=0
            for entry in entries:
                name=entry.filename
                mode=(entry.external_attr>>16)&0xffff
                segments=name.split("/")
                if name in seen or len(name)>220 or not name or name.startswith("/") or "\\" in name or any(s in ("",".","..") for s in segments) or stat.S_IFMT(mode) not in (0,stat.S_IFREG) or entry.file_size<0 or entry.file_size>MAX_ENTRY:
                    raise Blocked("ARCHIVE_PATH_OR_FILE_TYPE_UNSAFE")
                seen.add(name)
                n+=entry.file_size
                if n>MAX_TOTAL:raise Blocked("ARCHIVE_EXPANSION_LIMIT")
                if not name.endswith(".json"):continue
                with z.open(entry) as f:body=f.read(MAX_ENTRY+1)
                if len(body)!=entry.file_size:raise Blocked("ARCHIVE_SIZE_DRIFT")
                try:doc=decode(body,MAX_ENTRY)
                except Blocked:continue
                if isinstance(doc,dict):
                    candidate["regular_json"]+=1
                    if doc.get("schema")==R25_OWNER:candidate["owner"]+=1
                    if doc.get("schema")==R25_PINS:candidate["pins"]+=1
            return candidate
    except (zipfile.BadZipFile,RuntimeError,EOFError) as exc:
        raise Blocked("ZIP_UNTRUSTED") from exc

def inspect(manifest,folder):
    entries=validate(manifest)
    outputs=[]
    for row in entries:
        run=decode((folder/(str(row["run_id"])+".run.json")).read_bytes(),256*1024)
        meta=decode((folder/(str(row["run_id"])+".artifacts.json")).read_bytes(),256*1024)
        if not isinstance(run,dict) or run.get("id")!=row["run_id"] or run.get("run_attempt")!=1 or run.get("head_sha")!=row["head_sha"] or run.get("path")!=row["workflow_path"] or run.get("event")!="push" or run.get("status")!="completed" or run.get("conclusion")!="success" or not isinstance(run.get("repository"),dict) or run["repository"].get("full_name")!=row["repository"]:
            raise Blocked("AUTHENTIC_RUN_IDENTITY_MISMATCH")
        if not isinstance(meta,dict) or not isinstance(meta.get("artifacts"),list):
            raise Blocked("GITHUB_ARTIFACTS_UNAVAILABLE")
        candidates=[a for a in meta["artifacts"] if isinstance(a,dict) and a.get("id")==row["artifact_id"]]
        if len(candidates)!=1:
            raise Blocked("PINNED_GITHUB_ARTIFACT_NOT_FOUND")
        a=candidates[0]
        if a.get("name")!=row["artifact_name"] or a.get("expired") is not False or a.get("digest")!="sha256:"+row["artifact_zip_sha256"] or not isinstance(a.get("workflow_run"),dict) or a["workflow_run"].get("id")!=row["run_id"]:
            raise Blocked("AUTHENTIC_ARTIFACT_IDENTITY_MISMATCH")
        found=inspect_zip((folder/(str(row["run_id"])+".zip")).read_bytes(),row["artifact_zip_sha256"])
        outputs.append({"lane":row["lane"],"authentic_run_id":row["run_id"],"authentic_artifact_id":row["artifact_id"],"json_files":found["regular_json"],"r25_owner_bundle_candidates":found["owner"],"r25_detached_pin_candidates":found["pins"],"original_class":"TRAIN_ONLY_NOT_ELIGIBLE_FOR_FUTURE_R25_HOLDOUT"})
    return {"schema":"forge.r26.authentic-public-owner-intake-discovery.v1",
        "source_run_count":2,"sources":outputs,
        "r25_live_owner_bundle_available_in_scoped_artifacts":any(z["r25_owner_bundle_candidates"] for z in outputs),
        "r25_live_independent_pins_available_in_scoped_artifacts":any(z["r25_detached_pin_candidates"] for z in outputs),
        "r25_genuine_prospective_comparison_executed":False,
        "real_optimizer_gain_proven":False,
        "independently_authenticated_first_use":False,
        "scientific_admission":False,
        "new_originals_executed":0,"cloudflare_writes":0}

def main(argv):
    if len(argv)!=2:return 2
    try:
        outcome=inspect(decode(PIN.read_bytes(),256*1024),pathlib.Path(argv[1]))
    except (OSError,TypeError,KeyError,Blocked) as exc:
        print("R26_REAL_EVIDENCE_DISCOVERY_BLOCKED:"+type(exc).__name__,file=sys.stderr)
        return 1
    print(json.dumps(outcome,sort_keys=True,separators=(",",":")))
    return 0
if __name__=="__main__":raise SystemExit(main(sys.argv))

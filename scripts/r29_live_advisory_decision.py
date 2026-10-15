"""R29: live research PR source -> content-bound OBSERVATIONAL advisory choices.

Consumes the existing FORGE research-observer's ACTUAL two-lane GitHub
pull-request snapshot. The deterministic advisory choice is not the
scientific owner's choice, is NOT pre-outcome randomized, and has NO
dispatch, first-use, causal or signing authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys

SCHEMA="forge.cross-lane-research-pr-snapshot.v1"
OUTPUT="forge.dreamrsi.r29-live-advisory-observation.v1"
LANES=("Wingless","Yggdrasil")
HEX40=re.compile(r"[0-9a-f]{40}\Z")
MAX_BYTES=2*1024*1024
MAX_PER_LANE=100
MAX_SAMPLES=3

class Blocked(ValueError):pass

def distinct_fields(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise Blocked("R29_DUPLICATE_JSON_KEY")
        out[key]=value
    return out

def parse_bytes(raw:bytes):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:
        raise Blocked("R29_SOURCE_BOUNDED_BYTES_REQUIRED")
    try:return json.loads(raw,object_pairs_hook=distinct_fields)
    except (ValueError,UnicodeError) as exc:raise Blocked("R29_SOURCE_JSON_INVALID") from exc

def decision(source:bytes,workflow_run_id:int):
    if type(workflow_run_id) is not int or workflow_run_id<1 or workflow_run_id>10**16:
        raise Blocked("R29_ACTUAL_OBSERVER_RUN_REQUIRED")
    doc=parse_bytes(source)
    if not isinstance(doc,dict) or set(doc)!={"schema","sources"} or doc["schema"]!=SCHEMA:
        raise Blocked("R29_SOURCE_SCHEMA_INVALID")
    rows=doc["sources"]
    if not isinstance(rows,list) or not 2<=len(rows)<=MAX_PER_LANE*2:
        raise Blocked("R29_SOURCE_RUN_COUNT")
    seen=set()
    by_lane={lane:[] for lane in LANES}
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"lane","pr","head_sha","title","url","state","draft","updated_at"}:
            raise Blocked("R29_ROW_SCHEMA")
        lane=row["lane"]
        pr=row["pr"]
        head=row["head_sha"]
        if lane not in LANES or type(pr) is not int or pr<1 or pr>10**9 or not isinstance(head,str) or not HEX40.fullmatch(head):
            raise Blocked("R29_SOURCE_LANE_OR_PR")
        title=row["title"]
        if not isinstance(title,str) or not 0<len(title)<=512 or row["state"] not in ("open","closed") or type(row["draft"]) is not bool:
            raise Blocked("R29_PR_METADATA_INVALID")
        url=f"https://github.com/spoonman136668-ai/{lane}/pull/{pr}"
        if row["url"]!=url or not isinstance(row["updated_at"],str) or not re.fullmatch(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z",row["updated_at"]):
            raise Blocked("R29_EXTERNAL_SOURCE_IDENTITY_INVALID")
        key=(lane,pr)
        if key in seen:raise Blocked("R29_PR_IDENTITY_REPEATED")
        seen.add(key)
        by_lane[lane].append(row)
    out=[]
    for lane in LANES:
        items=by_lane[lane]
        if not items or len(items)>MAX_PER_LANE:
            raise Blocked("R29_MISSING_OR_UNBOUNDED_LANE")
        # Advisory source ordering is deterministic and ignores any
        # authored scientific outcomes. It is NOT a research policy gain.
        items.sort(key=lambda r:(r["updated_at"],r["pr"],r["head_sha"]),reverse=True)
        shortlist=items[:MAX_SAMPLES]
        chosen=shortlist[0]
        identity=lambda row:hashlib.sha256(f'{lane}/{row["pr"]}/{row["head_sha"]}'.encode("ascii")).hexdigest()
        out.append({
            "lane":lane,
            "candidate_source":"ACTUAL_GITHUB_PR_METADATA",
            "selection_kind":"OBSERVATIONAL_MOST_RECENT_PR_NOT_OWNER_SELECTION",
            "chosen_pr":chosen["pr"],
            "chosen_head_sha":chosen["head_sha"],
            "chosen_identity_sha256":identity(chosen),
            "finalists":[{"pr":r["pr"],"head_sha":r["head_sha"],"identity_sha256":identity(r)} for r in shortlist],
            "available_source_count":len(items),
            "logging_mode":"OBSERVATIONAL",
            "logged_action_probability_bp":0,
            "randomization_proof_sha256":None,
            "decision_made_before_research_outcome":False,
            "selected_by_existing_scientific_owner":False,
            "original_first_use_claimed":False,
            "candidate_dispatched":False,
            "scientific_result_accepted":False,
        })
    return {
        "schema":OUTPUT,
        "mode":"LIVE_ADVISORY_SOURCE_OBSERVATION_NO_RANDOMIZED_SCIENTIFIC_TRIAL",
        "observer_run_id":workflow_run_id,
        "source_snapshot_sha256":hashlib.sha256(source).hexdigest(),
        "decisions":out,
        "independent_randomization_verified":False,
        "independent_first_use_verified":False,
        "genuine_dreamrsi_optimizer_improvement_proven":False,
        "live_optimizer_dispatch_authorized":False,
        "research_originals_executed":0,
        "cloudflare_writes":0,
    }

def main(argv=None):
    a=argparse.ArgumentParser()
    a.add_argument("--snapshot",required=True)
    a.add_argument("--workflow-run-id",required=True,type=int)
    args=a.parse_args(argv)
    try:
        with open(args.snapshot,"rb") as f:raw=f.read(MAX_BYTES+1)
        result=decision(raw,args.workflow_run_id)
    except (OSError,Blocked,TypeError,AttributeError) as exc:
        print("R29_LIVE_ADVISORY_DENIED:"+type(exc).__name__,file=sys.stderr)
        return 1
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":raise SystemExit(main())

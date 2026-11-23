"""F118: source-bound, model-free, bounded development decision/execution feedback.

Runs within FORGE's EXISTING six-hour integrated synthetic workflow after
protected integration, not a new scheduler. This is engineering readiness
checking of untested advisory candidates, NOT scientific experiment evaluation,
scientific first use, policy promotion, or an autonomous GPT researcher.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"reference/research-intake/f118-autonomous-feedback-freeze.json"
FROZEN_BLOB="0dc092d9fdba981eed4df1441d1b92c7afa8a77f"
SCHEMA="forge.autonomy.f118.model-free-development-feedback.v1"
INPUT="forge.model-free.two-lane-untested-advisory.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
MAP={"Wingless":("./promptlineage","./genenv","./optimizerstages","./evoportfolio"),
     "Yggdrasil":("./genenv","./promptlineage","./optimizerstages","./dreamrsi")}
LANES=("Wingless","Yggdrasil")
class Quarantined(ValueError):pass

def need(ok,why):
    if not ok:raise Quarantined("F118_"+why)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()

def gitblob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def frozen():
    raw=FROZEN.read_bytes().replace(b"\r\n",b"\n")
    need(gitblob(raw)==FROZEN_BLOB,"PREREGISTRATION_DRIFT")
    cfg=json.loads(raw)
    q=cfg.get("qualification",{})
    need(cfg.get("schema")=="forge.autonomy.f118.unattended-model-free-development-feedback-freeze.v1"
         and cfg.get("parent_main_exact_sha")==
              "8b8b9a162d947e0e773128d2268744342f1c2ba1"
         and q.get("cycles_per_run")==2 and q.get("one_each_lane") is True
         and q.get("minimum_distinct_candidates_per_run")==2
         and q.get("proposal_count_each_lane")==4
         and q.get("max_seconds_per_test")==90
         and q.get("previous_max_candidate_records")==32
         and q.get("candidate_package_map")=={k:list(v) for k,v in MAP.items()}
         and cfg.get("first_use_denied") is True
         and cfg.get("scientific_originals_executed")==0
         and cfg.get("accepted_refs_mutated")==0
         and cfg.get("optimizer_promotions")==0
         and all(cfg.get("forbidden",{}).values()),
         "MODEL_FREE_AUTHORITY_OR_CONTRACT_DRIFT")
    return cfg,digest(raw)

def load_report(path):
    raw=Path(path).read_bytes()
    need(0<len(raw)<2_000_000,"REPORT_BYTES_BUDGET")
    return json.loads(raw.decode("utf-8-sig"))

def validate_advisory(a,source):
    need(isinstance(a,dict) and a.get("schema")==INPUT
         and a.get("source_commit_sha")==source and
         a.get("evidence_type")==
         "SYNTHETIC_FROZEN_SOURCE_ONLY_NOT_NEW_SCIENTIFIC_EVIDENCE"
         and a.get("model_invocations")==0 and a.get("codex_invocations")==0
         and a.get("network_calls")==0 and a.get("new_scientific_originals")==0
         and a.get("scientific_first_use_authorized") is False
         and a.get("real_research_progress_established") is False
         and a.get("policy_promotion_authorized") is False
         and a.get("accepted_ref_mutations")==0,"ADVISORY_PROVENANCE_OR_SCIENCE")
    lanes=a.get("lanes")
    need(type(lanes) is list and len(lanes)==2 and
         [x.get("lane") for x in lanes]==list(LANES),"MISSING_TWO_REAL_ADVISORY_LANES")
    seen=set()
    for entry in lanes:
        ids=entry.get("proposal_ids")
        need(type(ids) is list and len(ids)==4 and
             entry.get("prompt_candidates")==2 and entry.get("environment_candidates")==2 and
             entry.get("negative_records")==1 and entry.get("invalid_records")==1 and
             entry.get("mixed_records")==1 and
             entry.get("all_candidates_untested") is True and
             entry.get("full_population_screened") is True and
             entry.get("science_accepted") is False and
             entry.get("original_dispatch_authorized") is False and
             entry.get("advisory_assessment")==
             "BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY","ADVISORY_GENERATOR_UNQUALIFIED")
        for pid in ids:
            need(type(pid) is str and HEX64.fullmatch(pid) is not None
                 and pid not in seen,"DUPLICATE_OR_MALFORMED_PROPOSALS")
            seen.add(pid)
    return lanes

def verify_previous(previous,meta,source,run_id):
    if previous is None:
        need(meta is None,"PREVIOUS_META_WITHOUT_STATE")
        return {},None,0,"BOOTSTRAP_NO_PREVIOUS_F118_ARTIFACT"
    need(type(previous) is dict and type(meta) is dict,"PREVIOUS_STATE_AND_GITHUB_META_REQUIRED")
    need(previous.get("schema")==SCHEMA and
         previous.get("run_id")==meta.get("id") and
         previous.get("source_sha")==meta.get("head_sha") and
         previous.get("event")=="schedule" and
         meta.get("event")=="schedule" and
         meta.get("head_branch")=="main" and
         meta.get("conclusion")=="success" and
         meta.get("run_attempt")==1 and
         type(meta.get("id")) is int and 0<meta["id"]<run_id and
         type(meta.get("head_sha")) is str and
         HEX40.fullmatch(meta["head_sha"]) is not None and
         previous.get("new_scientific_originals")==0 and
         previous.get("accepted_ref_mutations")==0 and
         previous.get("optimizer_promotions")==0 and
         previous.get("qualified_unattended_repetitions") is not True,
         "PREVIOUS_SCHEDULED_RUN_UNTRUSTED")
    progress=previous.get("history")
    need(type(progress) is dict and len(progress)<=32,"PREVIOUS_HISTORY_INVALID")
    checked={}
    for key,item in progress.items():
        need(type(key) is str and re.fullmatch(r"(Wingless|Yggdrasil):[0-3]",key)
             and type(item) is dict
             and set(item)=={"count","failures","last","consecutive_failures"}
             and type(item["count"]) is int and 0<=item["count"]<=100000
             and type(item["failures"]) is int and 0<=item["failures"]<=item["count"]
             and item["last"] in ("PASS","FAIL","TIMEOUT")
             and type(item["consecutive_failures"]) is int and
             0<=item["consecutive_failures"]<=2,
             "PREVIOUS_HISTORICAL_FEEDBACK_CORRUPTED")
        checked[key]=dict(item)
    previous_records=previous.get("evaluations")
    need(type(previous_records) is list and len(previous_records)==2 and
         sorted(x.get("lane") for x in previous_records)==sorted(LANES) and
         type(previous.get("generation")) is int and previous["generation"]>=2 and
         previous["generation"]<=100000 and
         all(type(x.get("outcome")) is str and x["outcome"] in
            ("PASS","FAIL","TIMEOUT") and type(x.get("stdout_sha256")) is str and
            HEX64.fullmatch(x["stdout_sha256"]) for x in previous_records),
         "PREVIOUS_EXECUTION_PROOF_MISSING")
    return checked,digest(canonical(previous)),previous["generation"],"VERIFIED_PREVIOUS_SCHEDULED_RESULT"

def select(lane,history):
    """Deterministic source-bound decision from retained outcomes.
    Failures get one additional bounded recheck, then rotate; no fake fitness."""
    pending=[]
    for i in range(4):
        item=history.get(f"{lane}:{i}")
        count=item["count"] if item else 0
        recent_fail=bool(item and item["last"]!="PASS" and item["consecutive_failures"]<2)
        pending.append((-int(recent_fail),count,i))
    return min(pending)[2]

def update(history,lane,index,outcome):
    key=f"{lane}:{index}"
    prev=history.get(key,{"count":0,"failures":0,"last":"PASS","consecutive_failures":0})
    need(outcome in ("PASS","FAIL","TIMEOUT"),"UNRECOGNIZED_TEST_OUTCOME")
    row={"count":prev["count"]+1,"failures":prev["failures"]+int(outcome!="PASS"),
         "last":outcome,"consecutive_failures":min(2,prev["consecutive_failures"]+1)
          if outcome!="PASS" else 0}
    history[key]=row

def execute_check(package,timeout=90):
    need(package in {suite for group in MAP.values() for suite in group} and
         type(timeout) is int and timeout==90,"UNAPPROVED_ENGINEERING_CHECK")
    try:
        result=subprocess.run(["go","test","-count=1",package],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=False,timeout=timeout,check=False)
        raw=result.stdout[:1000000]
        return ("PASS" if result.returncode==0 else "FAIL",
                digest(raw),result.returncode)
    except subprocess.TimeoutExpired as exc:
        raw=exc.stdout or b""
        if isinstance(raw,str):raw=raw.encode()
        return "TIMEOUT",digest(raw[:1000000]),124

def build(advisory,source,run_id,event,previous=None,previous_meta=None,executor=execute_check):
    cfg,freeze_sha=frozen()
    need(type(source) is str and HEX40.fullmatch(source) is not None
         and type(run_id) is int and run_id>0 and
         event in ("schedule","pull_request","push","workflow_dispatch"),
         "GITHUB_SOURCE_OR_EVENT_INVALID")
    expected=os.environ.get("GITHUB_SHA")
    need(not expected or expected==source,"GITHUB_SOURCE_SHA_MISMATCH")
    lanes=validate_advisory(advisory,source)
    if event!="schedule":
        need(previous is None and previous_meta is None,"NON_SCHEDULED_CANNOT_CONSUME_CONTINUITY")
    history,previous_digest,prior_generation,continuity=verify_previous(
        previous,previous_meta,source,run_id)
    evaluations=[]
    for entry in lanes:
        lane=entry["lane"]
        idx=select(lane,history)
        package=MAP[lane][idx]
        outcome,outsha,exit_code=executor(package,90)
        need(outcome in ("PASS","FAIL","TIMEOUT") and
             type(outsha) is str and HEX64.fullmatch(outsha) and
             type(exit_code) is int,"ENGINEERING_EXECUTOR_RESULT_INVALID")
        update(history,lane,idx,outcome)
        evaluations.append({
            "lane":lane,"proposal_id":entry["proposal_ids"][idx],
            "proposal_position":idx,"engineering_readiness_suite":package,
            "outcome":outcome,"stdout_sha256":outsha,"exit_code":exit_code,
            "this_is_scientific_candidate_validation":False
        })
    need(len({x["proposal_id"] for x in evaluations})==2 and
         len(history)<=32 and len(evaluations)==2,"CANDIDATE_REPEAT_OR_SIZE_DRIFT")
    return {
        "schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
        "freeze_sha256":freeze_sha,"advisory_sha256":digest(canonical(advisory)),
        "generation":prior_generation+2,"continuity":continuity,
        "previous_record_sha256":previous_digest,
        "history":history,"evaluations":evaluations,
        "model_free_selection_and_execution_performed":True,
        "feedback_available_to_next_run":True,
        "qualified_unattended_repetitions":False,
        "science_screen_performed":False,
        "new_scientific_originals":0,"accepted_ref_mutations":0,
        "optimizer_promotions":0,"paid_model_calls":0,"codex_calls":0,
        "ckb_plane_contact":False,"cloudflare_writes":0,
        "new_schedulers":0,"independent_science_accepted":False,
        "real_model_inference":False
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--advisory",required=True)
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--run-id",required=True,type=int)
    parser.add_argument("--event",required=True)
    parser.add_argument("--previous")
    parser.add_argument("--previous-meta")
    parser.add_argument("--output",required=True)
    options=parser.parse_args()
    need(bool(options.previous)==bool(options.previous_meta),
         "PREVIOUS_STATE_META_PAIR_REQUIRED")
    previous=load_report(options.previous) if options.previous else None
    meta=load_report(options.previous_meta) if options.previous_meta else None
    result=build(load_report(options.advisory),options.source_ref,
                 options.run_id,options.event,previous,meta)
    out=Path(options.output)
    need(not out.exists() and out.parent.is_dir(),"IMMUTABLE_OUTPUT_PATH_REQUIRED")
    with out.open("xb") as writer:
        writer.write(canonical(result))

if __name__=="__main__":
    try:main()
    except (Quarantined,OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
        print("FORGE_F118_MODEL_FREE_FEEDBACK=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)

"""F129 fail-closed staged GitHub schedule admission and bootstrap receipts.

Admission means an earlier verified GitHub *run and artifact index* contains both
runner records; the admitting F125/127/128 mechanisms independently open,
checksum and validate the artifact contents. PR admission is a separate,
explicitly NON-SCHEDULED development mode, never continuity evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import f118_autonomy_feedback as f118

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f129-staged-continuity-freeze.json"
BLOB="392a81927bcee1029a163f9f75ad11c565530284"
SCHEMA="forge.autonomy.f129.staged-scheduled-bootstrap-development.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")

class Blocked(ValueError):pass

def need(ok,code):
    if not ok:raise Blocked("F129_"+code)

def canonical(x):return f118.canonical(x)

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(f118.gitblob(raw)==BLOB,"FROZEN_PROTOCOL_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.autonomy.f129.frozen-staged-scheduled-continuity.v1"
         and p["parent_f128_head"]=="bbe10fc6c37e2cbcf3cd567c9fd30680ec60c99a"
         and set(p["parents"])=={"F125","F127","F128"}
         and p["known_main_schedule"]["qualified_f124_artifacts"]==0
         and all(p["limits"].values()),"FROZEN_METHOD_OR_AUTHORITY_CHANGED")
    return p,hashlib.sha256(raw).hexdigest()

def strict(raw):
    need(type(raw) is bytes and 0<len(raw)<1500000,"INPUT_BOUNDS")
    def pairs(kv):
        result={}
        for k,v in kv:
            need(k not in result,"DUPLICATE_JSON_KEY")
            result[k]=v
        return result
    try:return json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,
                          parse_constant=lambda z:need(False,"JSON_NONFINITE"))
    except Blocked:raise
    except (ValueError,UnicodeError) as exc:
        raise Blocked("F129_MALFORMED_SOURCE_JSON") from exc

def admit(run_id,source,event,history):
    p,freeze_hash=frozen()
    need(type(run_id) is int and run_id>0
         and type(source) is str and HEX40.fullmatch(source)
         and event in ("schedule","pull_request","push","workflow_dispatch")
         and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "CURRENT_SOURCE_NOT_PINNED")
    names=p["parents"]
    choice={k:None for k in names}
    if event=="schedule":
        need(type(history) is dict and set(history)=={"runs"}
             and type(history["runs"]) is list and len(history["runs"])<=40,
             "INCOMPLETE_SCHEDULED_INDEX")
        used=set()
        last=run_id
        for item in history["runs"]:
            need(type(item) is dict and set(item)=={"run","artifacts"}
                 and type(item["run"]) is dict and type(item["artifacts"]) is dict,
                 "MALFORMED_SCHEDULED_RUN_ENTRY")
            run,index=item["run"],item["artifacts"]
            old=run.get("id")
            need(type(old) is int and 0<old<last
                 and old not in used
                 and run.get("status")=="completed"
                 and run.get("conclusion")=="success"
                 and run.get("event")=="schedule"
                 and run.get("head_branch")=="main"
                 and run.get("run_attempt")==1
                 and run.get("path")==".github/workflows/forge-integrated-synthetic-cycle.yml"
                 and type(run.get("head_sha")) is str
                 and HEX40.fullmatch(run["head_sha"])
                 and run.get("repository",{}).get("full_name")=="spoonman136668-ai/FORGE"
                 and run.get("head_repository",{}).get("full_name")=="spoonman136668-ai/FORGE",
                 "SCHEDULED_GITHUB_RUN_INVALID")
            used.add(old);last=old
            artifacts=index.get("artifacts")
            need(type(artifacts) is list and type(index.get("total_count")) is int
                 and index["total_count"]==len(artifacts)
                 and len(artifacts)<=100
                 and all(type(x) is dict for x in artifacts)
                 and len({a.get("id") for a in artifacts})==len(artifacts),
                 "SCHEDULED_ARTIFACT_INDEX_INCOMPLETE")
            for stage,expected in names.items():
                found=[a for a in artifacts if a.get("name") in expected]
                # Fail closed if only one OS is available, even if a previous
                # older success had a complete pair: partial newest evidence
                # may be a changed/replayed custody chain.
                need(len(found) in (0,2)
                     and len({a.get("name") for a in found})==len(found),
                     "SCHEDULED_HALF_PAIR_OR_DUPLICATE_"+stage)
                if found:
                    for a in found:
                        need(a.get("expired") is False
                             and type(a.get("size_in_bytes")) is int
                             and a["size_in_bytes"]>0
                             and type(a.get("digest")) is str
                             and re.fullmatch(r"sha256:[a-f0-9]{64}",a["digest"])
                             and type(a.get("workflow_run")) is dict
                             and a["workflow_run"].get("id")==old
                             and a["workflow_run"].get("head_sha")==run["head_sha"],
                             "SCHEDULED_ARTIFACT_SOURCE_"+stage)
                    if choice[stage] is None:
                        choice[stage]={"prior_run_id":old,
                                       "prior_source_sha":run["head_sha"]}
    else:
        need(history=={"runs":[]},
             "NONSCHEDULED_PRIOR_HISTORY_NOT_AUTHORITY")
    state={key:{
        "admitted":bool(choice[key]) if event=="schedule" else event=="pull_request",
        "prior_run_id":choice[key]["prior_run_id"] if choice[key] else None,
        "prior_source_sha":choice[key]["prior_source_sha"] if choice[key] else None}
        for key in names}
    # Only an actual pull_request event may use pinned PR-development evidence.
    # A post-merge push or manual dispatch is NOT a PR and cannot resurrect
    # historic pull_requests associations that GitHub has since cleared.
    # Scheduled runs remain confined to prior genuine main scheduled evidence.
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
        "freeze_sha256":freeze_hash,"admissions":state,
        "development_pr_evidence_mode":event=="pull_request",
        "non_scheduled_source_bootstrap":event in ("push","workflow_dispatch"),
        "genuine_scheduled_source":event=="schedule",
        "F124_base_execution":True,"F126_base_execution":True,
        "first_schedule_bootstrap":event=="schedule" and not any(
            v["admitted"] for v in state.values()),
        "scientific_originals_dispatched":0,"scientific_first_use_authorized":False,
        "accepted_ref_mutations":0,"optimizer_promotions":0,
        "Codex_calls":0,"paid_model_calls":0,"new_schedulers":0,
        "ckb_plane_contact":False,"cloudflare_writes":0,"mind_palace_writes":0,
        "two_genuine_scheduled_main_runs_proven":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--run-id",required=True,type=int)
    parser.add_argument("--event",required=True)
    parser.add_argument("--history-json",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    result=admit(a.run_id,a.source_ref,a.event,
                 strict(Path(a.history_json).read_bytes()))
    output=Path(a.output)
    need(output.parent.is_dir() and not output.exists(),"OUTPUT_NOT_APPEND_ONLY")
    with output.open("xb") as f:f.write(canonical(result))

if __name__=="__main__":
    try:main()
    except (Blocked,f118.Quarantined,ValueError,TypeError,KeyError,OSError) as exc:
        print("F129_SCHEDULED_STAGE_ADMISSION_QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)

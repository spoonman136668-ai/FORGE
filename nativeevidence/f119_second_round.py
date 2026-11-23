"""F119 autonomously executes a second bounded research-development decision round.

F119 consumes actual F118 same-run output, never mock retrospective scores.
It runs two MORE real allowlisted Go package checks, carries all four
engineering outcomes into the next scheduled F118 feedback state, and archives
both rounds without implying scientific candidate evaluation or authority.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

import f118_autonomy_feedback as f118

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f119-two-round-autonomy-freeze.json"
FREEZE_BLOB="d8491705e61ddd1e8b49751641b90d9e6fec91f4"
F118_BLOB="9ed9127a06d1a22b5ef8519e67730f3dc90e1c6c"
SCHEMA="forge.autonomy.f119.actual-two-round-development-feedback.v1"
RUN_MODES=("schedule","push","pull_request","workflow_dispatch")

def require(ok,reason):
    if not ok:raise f118.Quarantined("F119_"+reason)

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(f118.gitblob(raw)==FREEZE_BLOB and
        f118.gitblob((ROOT/"nativeevidence/f118_autonomy_feedback.py")
                     .read_bytes().replace(b"\r\n",b"\n"))==F118_BLOB,
        "FIRST_FREEZE_OR_F118_ENGINE_CHANGED")
    cfg=json.loads(raw)
    p=cfg["pinned_parent"]
    algorithm=cfg["frozen_algorithm"]
    require(cfg["schema"]==
        "forge.autonomy.f119.two-round-source-feedback-freeze.v1"
        and cfg["parent_main_exact_sha"]==
            "50a4639b0f2218caed713f27f0e602821a74d49f"
        and p["f118_engine_blob"]==F118_BLOB
        and p["existing_schedule"]=="19 */6 * * *"
        and p["existing_f118_state_schema"]==f118.SCHEMA
        and algorithm["min_actual_checks"]==4
        and algorithm["actual_disjoint_choices_on_initial_success"]==4
        and algorithm["do_not_modify_F118_engine"] is True
        and algorithm["no_synthetic_claim_of_unattended_schedule"] is True
        and algorithm["two_authentic_scheduled_main_runs_still_required"] is True
        and all(cfg["denied"].values()),"FROZEN_SCOPE_OR_BOUNDARIES_CHANGED")
    _,f118_sha=f118.frozen()
    return cfg,hashlib.sha256(raw).hexdigest(),f118_sha

def valid_first(state,advisory,source,run_id,event,first_frozen_sha):
    lanes=f118.validate_advisory(advisory,source)
    require(type(run_id) is int and run_id>0 and
        event in RUN_MODES and
        type(source) is str and f118.HEX40.fullmatch(source) is not None
        and (not os.environ.get("GITHUB_SHA") or
             os.environ["GITHUB_SHA"]==source),"CURRENT_RUN_SOURCE_IDENTITY")
    require(type(state) is dict and state.get("schema")==f118.SCHEMA
        and state.get("source_sha")==source
        and state.get("run_id")==run_id and state.get("event")==event
        and state.get("freeze_sha256")==first_frozen_sha
        and state.get("advisory_sha256")==
            f118.digest(f118.canonical(advisory))
        and type(state.get("generation")) is int
        and state["generation"]>=2 and state["generation"]%2==0
        and state.get("continuity") in (
            "BOOTSTRAP_NO_PREVIOUS_F118_ARTIFACT",
            "VERIFIED_PREVIOUS_SCHEDULED_RESULT")
        and state.get("model_free_selection_and_execution_performed") is True
        and state.get("feedback_available_to_next_run") is True
        and state.get("qualified_unattended_repetitions") is False
        and state.get("science_screen_performed") is False
        and state.get("new_scientific_originals")==0
        and state.get("accepted_ref_mutations")==0
        and state.get("optimizer_promotions")==0
        and state.get("codex_calls")==0
        and state.get("paid_model_calls")==0
        and state.get("ckb_plane_contact") is False
        and state.get("cloudflare_writes")==0
        and state.get("new_schedulers")==0
        and state.get("independent_science_accepted") is False,
        "FIRST_ROUND_OR_AUTHORITY_UNVERIFIED")
    record=state.get("evaluations")
    history=state.get("history")
    require(type(record) is list and len(record)==2 and
            type(history) is dict and len(history)<=8 and
            [x.get("lane") for x in record]==list(f118.LANES),
            "FIRST_ROUND_MISSING_LANE_OR_HISTORY")
    for entry,first in zip(lanes,record):
        lane=entry["lane"]
        idx=first.get("proposal_position")
        require(type(idx) is int and idx in range(4) and
            first.get("proposal_id")==entry["proposal_ids"][idx] and
            first.get("engineering_readiness_suite")==f118.MAP[lane][idx] and
            first.get("outcome") in ("PASS","FAIL","TIMEOUT") and
            type(first.get("stdout_sha256")) is str and
            f118.HEX64.fullmatch(first["stdout_sha256"]) is not None and
            type(first.get("exit_code")) is int and
            first.get("this_is_scientific_candidate_validation") is False,
            "FIRST_ROUND_IS_NOT_ACTUAL_APPROVED_ACTION")
        row=history.get(f"{lane}:{idx}")
        require(type(row) is dict and row.get("last")==first["outcome"]
            and type(row.get("count")) is int and row["count"]>=1
            and type(row.get("failures")) is int
            and 0<=row["failures"]<=row["count"]
            and type(row.get("consecutive_failures")) is int
            and 0<=row["consecutive_failures"]<=2,
            "FIRST_ROUND_FEEDBACK_MISMATCH")
    for key,row in history.items():
        require(key in {f"{l}:{i}" for l in f118.LANES for i in range(4)}
            and type(row) is dict
            and set(row)=={"count","failures","last","consecutive_failures"}
            and type(row["count"]) is int and row["count"]>=1
            and type(row["failures"]) is int
            and 0<=row["failures"]<=row["count"]
            and row["last"] in ("PASS","FAIL","TIMEOUT")
            and type(row["consecutive_failures"]) is int
            and 0<=row["consecutive_failures"]<=2,
            "FIRST_ROUND_HISTORY_TAMPER")
    return lanes

def select_next(lane,first,history):
    idx=first["proposal_position"]
    row=history[f"{lane}:{idx}"]
    if first["outcome"] in ("FAIL","TIMEOUT") and \
       row["consecutive_failures"]==1:
        return idx,"ONE_BOUNDED_REAL_FAILURE_RETRY"
    counts=[(history.get(f"{lane}:{i}",{}).get("count",0),i)
            for i in range(4) if i!=idx]
    return min(counts)[1],"REAL_FEEDBACK_LEAST_TESTED_DIFFERENT_CANDIDATE"

def execute(advisory,first,source,run_id,event,executor=f118.execute_check):
    cfg,freeze_sha,first_freeze_sha=frozen()
    lanes=valid_first(first,advisory,source,run_id,event,first_freeze_sha)
    history=copy.deepcopy(first["history"])
    second=[]
    for lane_info,prior in zip(lanes,first["evaluations"]):
        lane=lane_info["lane"]
        index,reason=select_next(lane,prior,history)
        suite=f118.MAP[lane][index]
        result,outsha,returncode=executor(suite,90)
        require(result in ("PASS","FAIL","TIMEOUT") and
            type(outsha) is str and f118.HEX64.fullmatch(outsha) and
            type(returncode) is int,"SECOND_ACTUAL_PROCESS_OUTCOME_INVALID")
        f118.update(history,lane,index,result)
        second.append({
            "lane":lane,"proposal_id":lane_info["proposal_ids"][index],
            "proposal_position":index,"engineering_readiness_suite":suite,
            "outcome":result,"stdout_sha256":outsha,"exit_code":returncode,
            "selection_reason":reason,
            "this_is_scientific_candidate_validation":False})
    require(len(second)==2 and len(history)<=8,
        "SECOND_ROUND_EVALUATION_COUNT_OR_SIZE")
    # F118 can consume this exact same-schema state on the next SCHEDULED run.
    # The first-round artifact remains separately archived and immutable.
    carried=copy.deepcopy(first)
    carried["generation"]=first["generation"]+2
    carried["history"]=history
    carried["evaluations"]=[{k:v for k,v in row.items() if k!="selection_reason"}
                            for row in second]
    carried["qualified_unattended_repetitions"]=False
    carried["f119_two_round_feedback_sha256"]=freeze_sha
    require(carried["event"]==event and carried["source_sha"]==source and
        carried["new_scientific_originals"]==0 and
        carried["optimizer_promotions"]==0 and
        carried["accepted_ref_mutations"]==0,"CARRIED_STATE_UNSUPPORTED_AUTHORITY")
    followup={lane:min(range(4),key=lambda i:(
        history.get(f"{lane}:{i}",{}).get("count",0),i))
        for lane in f118.LANES}
    audit={
        "schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
        "prereg_sha256":freeze_sha,
        "first_round_state_sha256":f118.digest(f118.canonical(first)),
        "second_round_carried_state_sha256":f118.digest(f118.canonical(carried)),
        "first_round":first["evaluations"],"second_round":second,
        "total_real_package_checks_this_run":4,
        "model_free_autonomous_feedback_decisions":4,
        "prior_scheduled_feedback_state":first["continuity"],
        "next_development_candidate_positions":followup,
        "negative_outcomes_count":sum(x["outcome"]!="PASS" for x in
            first["evaluations"]+second),
        "feedback_retained_for_next_scheduled_run":True,
        "two_distinct_GitHub_scheduled_runs_observed":False,
        "research_hypothesis_fitness_established":False,
        "unrestricted_learning_established":False,
        "original_science_executed":0,"accepted_refs_mutated":0,
        "optimizer_promotions":0,"Codex_calls":0,"paid_model_calls":0,
        "new_schedulers":0,"ckb_plane_contact":False,
        "cloudflare_writes":0,"Mind_Palace_writes":0}
    return audit,carried

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--advisory",required=True)
    parser.add_argument("--first",required=True)
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--run-id",type=int,required=True)
    parser.add_argument("--event",required=True)
    parser.add_argument("--audit-out",required=True)
    parser.add_argument("--next-state-out",required=True)
    args=parser.parse_args()
    audit,carried=execute(f118.load_report(args.advisory),
        f118.load_report(args.first),args.source_ref,args.run_id,args.event)
    paths=(Path(args.audit_out),Path(args.next_state_out))
    require(paths[0]!=paths[1] and all(p.parent.is_dir() and not p.exists()
        for p in paths),"IMMUTABLE_AND_DISTINCT_OUTPUT_PATHS")
    for path,report in zip(paths,(audit,carried)):
        with path.open("xb") as out:
            out.write(f118.canonical(report))
if __name__=="__main__":
    try:main()
    except (f118.Quarantined,OSError,ValueError,KeyError,TypeError) as exc:
        print("F119_WITHIN_RUN_AUTONOMY=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)

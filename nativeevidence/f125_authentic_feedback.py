"""F125 authentic GitHub F124 outcome -> source-derived GenEnv autonomy (development only).

A prior *genuine* completed GitHub run, independently fetched via read-only
authenticated API, must be tied to both exact F124 artifact contents. This is
FORGE DEVELOPMENT evidence, not Wingless/Yggdrasil accepted science. The
negative outcomes choose the *dimension* of the next challenge; current
source-verified GenEnv candidates are screened on TRAIN only.
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
import f120_generated_environment as f120
import f124_feedback_curriculum as f124

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f125-authentic-development-feedback-freeze.json"
BLOB="2a95893f6ae1a213c21fb626f295e1d685b0e8d2"
SCHEMA="forge.autonomy.f125.authenticated-development-feedback-selection.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
class Quarantined(ValueError): pass

def require(ok, reason):
    if not ok:raise Quarantined("F125_"+reason)

def canonical(x):return f118.canonical(x)
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha(x):return sha_bytes(canonical(x))

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(f118.gitblob(raw)==BLOB,"FROZEN_PROTOCOL_IDENTITY")
    p=json.loads(raw)
    h=p["historical_pr_evidence"]
    require(p["schema"]=="forge.autonomy.f125.frozen-authentic-development-feedback-intake.v1"
            and p["parent_f124_head"]=="f2c8ccb502ad8c26a25be86a127fa4497530d0e3"
            and p["parent_f124_code_blob"]=="6979816c988bf8be2877ba9a8d439a68f433ac19"
            and h["run_id"]==39038465506 and h["artifact_ubuntu"]["id"]==12103406537
            and h["artifact_windows"]["id"]==12102913536
            and h["report_sha256"]=="9300b2b1b93f49b4117f9bb08f183671f5cbd4515d5d873b2962e2790f02454b"
            and p["cohort"]["per_lane_train_pairs"]==8
            and p["cohort"]["per_lane_confirmation_pairs"]==16
            and all(p["authority"].values()),"UNFROZEN_AUTHORITY_OR_METHOD")
    return p,sha_bytes(raw)

def strict_json(raw):
    require(type(raw) is bytes and 0<len(raw)<1600000,"EVIDENCE_BYTES_INVALID")
    def pairs(items):
        out={}
        for k,v in items:
            require(k not in out,"JSON_DUPLICATE_KEY")
            out[k]=v
        return out
    try:
        data=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,
                        parse_constant=lambda _:require(False,"NONFINITE_JSON"))
    except (ValueError,UnicodeError) as e:
        raise Quarantined("F125_EVIDENCE_JSON_INVALID") from e
    require(type(data) is dict,"EVIDENCE_NOT_AN_OBJECT")
    return data

def read_evidence(run,artifacts,ubuntu,ureceipt,windows,wreceipt,current_run_id,event,protocol=None):
    p=protocol if protocol is not None else frozen()[0]
    h=p["historical_pr_evidence"]
    require(type(run) is dict and type(artifacts) is dict
            and type(current_run_id) is int and current_run_id>0
            and event in ("pull_request","schedule","push","workflow_dispatch"),
            "INVALID_GITHUB_EVIDENCE_ENVELOPE")
    prior=run.get("id")
    is_sched=(event=="schedule")
    require(type(prior) is int and 0<prior<current_run_id
            and run.get("repository",{}).get("full_name")==h["repository"]
            and run.get("head_repository",{}).get("full_name")==h["repository"]
            and run.get("path")==h["workflow_path"]
            and run.get("status")=="completed" and run.get("conclusion")=="success"
            and type(run.get("run_attempt")) is int and run["run_attempt"]==1
            and type(run.get("head_sha")) is str
            and HEX40.fullmatch(run["head_sha"]), "PRIOR_GITHUB_SOURCE_OR_SUCCESS")
    if is_sched:
        require(run.get("event")=="schedule" and run.get("head_branch")=="main",
                "PR_RUN_CANNOT_IMPERSONATE_SCHEDULE")
    else:
        require(prior==h["run_id"] and run.get("event")=="pull_request"
                and run.get("head_sha")==h["run_head_sha"]
                and run.get("head_branch")=="research/f124-autonomy-feedback-curriculum"
                and type(run.get("pull_requests")) is list
                and len(run["pull_requests"])==1
                and run["pull_requests"][0].get("number")==h["pr_number"]
                and run["pull_requests"][0].get("head",{}).get("sha")==h["run_head_sha"],
                "DEVELOPMENT_FIXTURE_SOURCE_NOT_AUTHENTIC")
    items=artifacts.get("artifacts")
    require(type(items) is list and type(artifacts.get("total_count")) is int
            and artifacts["total_count"]==len(items) and len(items)<=100,
            "ARTIFACT_QUERY_INCOMPLETE")
    require(len({x.get("id") for x in items if type(x) is dict})==len(items),
            "DUPLICATE_ARTIFACT_IDS")
    matched={}
    for item in items:
        if type(item) is not dict:continue
        if item.get("name") in (h["artifact_ubuntu"]["name"],
                               h["artifact_windows"]["name"]):
            name=item["name"]
            require(name not in matched
                    and item.get("expired") is False
                    and type(item.get("size_in_bytes")) is int
                    and item["size_in_bytes"]>0
                    and type(item.get("digest")) is str
                    and re.fullmatch(r"sha256:[0-9a-f]{64}",item["digest"])
                    and type(item.get("workflow_run")) is dict
                    and item["workflow_run"].get("id")==prior
                    and item["workflow_run"].get("head_sha")==run["head_sha"],
                    "ARTIFACT_SOURCE_OR_DIGEST_UNQUALIFIED")
            matched[name]=item
    require(len(matched)==2,"DUAL_OS_EVIDENCE_NOT_AVAILABLE")
    if not is_sched:
        for key in ("artifact_ubuntu","artifact_windows"):
            f=h[key]
            item=matched[f["name"]]
            require(item["id"]==f["id"]
                    and item["digest"]=="sha256:"+f["zip_sha256"],
                    "FROZEN_ARTIFACT_DIGEST_DRIFT")
    def verify_data(raw,receipt):
        require(type(receipt) is bytes and len(receipt)<256,"RECEIPT_UNSAFE")
        checksum=sha_bytes(raw)
        need=receipt.replace(b"\r\n",b"\n").strip()
        require(need==(checksum+"  state.json").encode(),
                "CORRUPT_EXTRACTED_ARTIFACT_RECEIPT")
        return checksum
    uhash=verify_data(ubuntu,ureceipt)
    whash=verify_data(windows,wreceipt)
    require(uhash==whash and ubuntu==windows,
            "CROSS_OS_RECORDS_DISAGREE")
    if not is_sched:require(uhash==h["report_sha256"],"PINNED_REPORT_BYTES_DRIFT")
    proof=strict_json(ubuntu)
    expected_source=run["head_sha"] if is_sched else h["checked_merge_source_sha"]
    require(proof.get("schema")==f124.SCHEMA
            and proof.get("run_id")==prior
            and proof.get("source_sha")==expected_source
            and proof.get("event")==run["event"]
            and proof.get("scientific_originals")==0
            and proof.get("accepted_ref_mutations")==0
            and proof.get("optimizer_promotions")==0
            and proof.get("scientific_hypothesis_invention_proven") is False
            and proof.get("unattended_two_run_continuity_proven") is False
            and proof.get("actual_controlled_graph_pairs")==96
            and proof.get("model_free_source_only_challenge_selection") is True,
            "PRIOR_ARTIFACT_NOT_QUALIFIED_F124")
    rounds=proof.get("rounds")
    require(type(rounds) is list and len(rounds)==4
            and [r.get("lane") for r in rounds]==["Wingless","Yggdrasil"]*2,
            "LOSS_OF_HISTORICAL_LANE")
    preserve={}
    for lane in ("Wingless","Yggdrasil"):
        rec=[r for r in rounds if r["lane"]==lane]
        hist=proof.get("history")
        require(type(hist) is dict and len(hist)<=6
                and [x.get("round") for x in rec]==[1,2]
                and all(x.get("direction") in f124.DIRECTIONS
                        and type(x.get("feedback_discrimination")) is int
                        and type(x.get("confirmation")) is dict
                        and x["confirmation"].get("cases")==16
                        and x["feedback_discrimination"]==x["confirmation"].get("discrimination")
                        and x["confirmation"].get("oracle_correct")==16
                        and type(x.get("generated_vector")) is list
                        and len(x["generated_vector"])==3
                        and all(type(v) is int and 0<=v<=3 for v in x["generated_vector"])
                        for x in rec), "SPOOFED_OR_INCOMPLETE_RESEARCH_DEV_OUTCOMES")
        observed={}
        for x in rec:
            key=lane+":"+x["direction"]
            observed.setdefault(key,[]).append(x["feedback_discrimination"])
        for key,values in observed.items():
            row=hist.get(key)
            require(type(row) is dict and row.get("count")>=len(values)
                    and row.get("last_discrimination")==values[-1]
                    and row.get("negatives")>=sum(v==0 for v in values)
                    and row.get("total_discrimination")>=sum(values),
                    "HISTORICAL_NEGATIVE_OR_OUTCOME_ERASED")
        preserve[lane]={"last":rec[-1],
                        "negative_count":sum(x["feedback_discrimination"]==0 for x in rec),
                        "positive_count":sum(x["feedback_discrimination"]>0 for x in rec),
                        "archived_vectors":[x["generated_vector"] for x in rec],
                        "source_confirmation_hashes":[x["confirmation"]["sha256"] for x in rec]}
    return {"source_run_id":prior,"source_git_head":run["head_sha"],
            "source_report_sha256":uhash,
            "mode":"REAL_SCHEDULED_MAIN_DEVELOPMENT" if is_sched else "PINNED_REAL_PR_DEVELOPMENT",
            "lanes":preserve,"authenticated_github_development_readback":True,
            "scientifically_accepted_originals":0}

def current_candidates(advisory,source):
    return f120.validate(advisory,source)

def derive_options(candidates,prior,lane):
    last=prior["last"]
    # No hindsight: select focus from previous *completed* published outcome.
    focus=last["direction"] if last["feedback_discrimination"]==0 else "DEPTH_SHORTCUT"
    column=f124.DIRECTIONS.index(focus)
    old={tuple(x) for x in prior["archived_vectors"]}
    options=[]
    for candidate in candidates:
        vec=list(candidate["vector"])
        if vec[column]>=3:continue
        vec[column]+=1
        if tuple(vec) in old:continue
        require(vec!=candidate["vector"],"NONEXISTENT_GENENV_MUTATION")
        options.append({"family":"DGM/GenEnv",
             "parent_source_sha256":candidate["source_candidate_sha256"],
             "candidate_index":candidate["candidate_index"],
             "vector":vec,"focus":focus,
             "candidate_sha256":sha({"origin":candidate["source_candidate_sha256"],
                                      "focus":focus,"vector":vec})})
    require(bool(options) and len(options)<=2
            and len({x["candidate_sha256"] for x in options})==len(options),
            "NO_NEW_GENERATED_CANDIDATE")
    return options

def evaluate(vector,lane,phase):
    base=122000 if lane=="Wingless" else 123000
    seeds=range(base,base+8) if phase=="TRAIN" else range(base+100,base+116)
    result=[]
    for seed in seeds:
        case=f120.graph(seed,vector)
        gold=f120.readout(case,f120.binding_solver)
        control=f120.readout(case,lambda x,y:f120.binding_solver(x,y,max_hops=2))
        role=f120.readout(case,f120.role_only)
        require(gold["paired_correct"] and not role["paired_correct"],
                "CURRENT_NEW_DEVELOPMENT_GRAPH_INVALID")
        result.append({"seed":seed,"graph_sha256":sha(case),
                       "oracle":bool(gold["paired_correct"]),
                       "depth2":bool(control["paired_correct"]),
                       "role_only":bool(role["paired_correct"])})
    n=len(result)
    return {"pairs":n,"graph_sha256":sha(result),
            "oracle_correct":sum(r["oracle"] for r in result),
            "depth2_correct":sum(r["depth2"] for r in result),
            "role_only_correct":sum(r["role_only"] for r in result),
            "discrimination":sum(r["oracle"] for r in result)-
                            max(sum(r["depth2"] for r in result),
                                sum(r["role_only"] for r in result))}

def execute(advisory,source,run_id,event,evidence):
    protocol,freeze_hash=frozen()
    require(type(source) is str and HEX40.fullmatch(source)
            and type(run_id) is int and run_id>0
            and event in ("pull_request","schedule","push","workflow_dispatch")
            and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source)
            and type(evidence) is dict
            and evidence.get("authenticated_github_development_readback") is True
            and evidence.get("source_run_id")<run_id,
            "UNQUALIFIED_CURRENT_SOURCE_OR_HISTORICAL_RECEIPT")
    if event=="schedule":
        require(evidence.get("mode")=="REAL_SCHEDULED_MAIN_DEVELOPMENT",
                "PR_PREVIEW_CANNOT_BECOME_SCHEDULED_CONTINUITY")
    else:
        require(evidence.get("mode")=="PINNED_REAL_PR_DEVELOPMENT",
                "PR_DEV_REQUIRES_REAL_PINNED_SOURCE")
    population=current_candidates(advisory,source)
    output=[]
    for lane in ("Wingless","Yggdrasil"):
        source_data=evidence["lanes"][lane]
        candidates=derive_options(population[lane],source_data,lane)
        screens=[{**x,"training":evaluate(x["vector"],lane,"TRAIN")} for x in candidates]
        selected=sorted(screens,key=lambda x:(-x["training"]["discrimination"],
                                               x["candidate_index"]))[0]
        confirmation=evaluate(selected["vector"],lane,"CONFIRM")
        output.append({"lane":lane,"prior_run_id":evidence["source_run_id"],
             "negative_observations_preserved":source_data["negative_count"],
             "positive_observations_preserved":source_data["positive_count"],
             "chosen_from_prior_development_outcome":selected["focus"],
             "source_derived_proposals":screens,"train_only_winner_sha256":selected["candidate_sha256"],
             "confirmation":confirmation,
             "scientifically_validated_model_mechanism":False})
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
         "freeze_sha256":freeze_hash,"prior_source_run_id":evidence["source_run_id"],
         "prior_development_report_sha256":evidence["source_report_sha256"],
         "prior_source_mode":evidence["mode"],
         "source_advisory_sha256":sha(advisory),
         "lanes":output,"authenticated_prior_development_outcomes_consumed":True,
         "two_independent_scientific_originals_accepted":False,
         "actual_confirmed_development_pairs":32,
         "new_autonomous_mechanism_discovered":False,
         "scientific_first_use_authorized":False,"scientific_originals_dispatched":0,
         "optimizer_promotions":0,"accepted_ref_mutations":0,
         "Codex_calls":0,"paid_model_calls":0,"new_scheduler":False,
         "cloudflare_writes":0,"ckb_plane_contact":False,"mind_palace_writes":0}

def main():
    parser=argparse.ArgumentParser()
    for key in ("advisory","run-json","artifacts-json","ubuntu-state",
                "ubuntu-receipt","windows-state","windows-receipt",
                "source-ref","event","output"):
        parser.add_argument("--"+key,required=True)
    parser.add_argument("--run-id",required=True,type=int)
    opts=parser.parse_args()
    protocol,_=frozen()
    read=lambda p:Path(p).read_bytes()
    evidence=read_evidence(strict_json(read(opts.run_json)),
                           strict_json(read(opts.artifacts_json)),
                           read(opts.ubuntu_state),read(opts.ubuntu_receipt),
                           read(opts.windows_state),read(opts.windows_receipt),
                           opts.run_id,opts.event,protocol)
    report=execute(f118.load_report(opts.advisory),
                   opts.source_ref,opts.run_id,opts.event,evidence)
    output=Path(opts.output)
    require(output.parent.is_dir() and not output.exists(),
            "OUTPUT_MUST_BE_NEW")
    with output.open("xb") as fp: fp.write(canonical(report))

if __name__=="__main__":
    try:main()
    except (Quarantined,f118.Quarantined,f120.Invalid,f124.Quarantined,
            OSError,TypeError,ValueError,KeyError) as exc:
        print("F125_AUTHENTIC_DEV_INTAKE_QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)

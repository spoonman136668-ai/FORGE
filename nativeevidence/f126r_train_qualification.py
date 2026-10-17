"""F126-R exact-head source-verified public TRAIN and frozen comparisons.

All sources are TRAIN only; native frozen control incompatibilities are
reported, never hidden, modified or asserted scientifically qualified.
Protected CONFIRM never constructed, fitted, scored or imported.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f123_learned_routing as dense
import f123_controls as controls
import f124r_sparse_model as sparse2
import f125r_path_model as preserving
import f126r_freeze_admission as freeze
import f126r_train_environment as env
import f126r_contrastive_model as learner

SCHEMA="forge.research.f126r.public-train-and-all-frozen-controls.v1"
F123_BLOB="6f90560c331e20967d0b13892668da8060e06cdc"
F124R_BLOB="35c05045b8dbbe95a36c5643699461555927fe7b"
F125R_BLOB="f53c82ed7d49ce31968d23ad60da4840cf500788"
def need(x,why):env.need(bool(x),"QUALIFICATION_"+why)
def git_blob(filename):
    raw=Path(filename).read_bytes().replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def seal(path):
    raw=Path(path).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    p=Path(path)
    return raw,digest
def trained_dense(rows):
    # The original F123-B model and frozen 100-epoch SGD, only denominator
    # adapted to the new 128-row public TRAIN cohort; source is NOT modified.
    need(len(rows)==128 and dense.EPOCHS==100,"DENSE_SCHEDULE")
    w=[-1.2]+[.17]*16+[.05,3.,.5]
    for _ in range(100):
        g=[0.]*20
        for graph,y in rows:
            p,d=dense.predict_b(graph,w)
            for k in range(20):g[k]+=(p-y)*d[k]
        for k in range(20):
            w[k]=max(-8.,min(8.,w[k]-.22*max(-1.,min(1.,g[k]/128))))
    return w
def trained_query(rows):
    w=[0.]*20
    for _ in range(100):
        g=[0.]*20
        for obs,y in rows:
            f=controls.topology_features(obs)
            p=learner.sigmoid(sum(a*b for a,b in zip(w,f)))
            for k in range(20):g[k]+=(p-y)*f[k]
        for k in range(20):
            w[k]=max(-8.,min(8.,w[k]-.25*max(-1.,min(1.,g[k]/128))))
    return w

def oracle_work(g):
    # Every visible edge reexamined for each exact state; bit tests cost 16.
    states=[(g["start"],None)]
    work={"edge_scans":0,"bit_comparisons":0,
          "state_allocations":0,"peak_states":1}
    for role in g["roles"]:
        nextstates=[]
        for node,previous in states:
            for edge in g["edges"]:
                work["edge_scans"]+=1
                if edge["from"]!=node or edge["role"]!=role:continue
                if previous is not None:
                    work["bit_comparisons"]+=16
                    if previous!=edge["src_bits"]:continue
                nextstates.append((edge["to"],edge["dst_bits"]))
                work["state_allocations"]+=1
        states=nextstates
        work["peak_states"]=max(work["peak_states"],len(states))
    return int(any(node==g["target"] for node,_ in states)),work

def evaluate(lane,vectors,raw_ids):
    rows=env.train_rows(lane,vectors)
    need(len(rows)==128 and
         all((rows[k][1],rows[k+1][1])==(1,0) for k in range(0,128,2)),
         "MISSING_CASES")
    trained,movement=learner.fit(rows)
    native_dense=trained_dense(rows)
    native_preserving,_=preserving.fit(rows)
    native_query=trained_query(rows)
    mechanisms={
        "F126R_TRAINED":lambda o:learner.forward(o,trained)[0],
        "CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE":lambda o:float(env.graph_paths(o,True)>0),
        "CTRL_F123_DENSE_B_FRESH":lambda o:dense.predict_b(o,native_dense)[0],
        "CTRL_F125R_PATH_PRESERVING_FRESH":lambda o:preserving.forward(o,native_preserving)[0],
        "CTRL_FIXED_SOFT_12_16":lambda o:float(controls.fixed_soft_path(o)),
        "CTRL_ROLE_ONLY":lambda o:float(env.graph_paths(o)>0),
        "CTRL_QUERY_ONLY":lambda o:learner.sigmoid(
            sum(a*b for a,b in zip(native_query,controls.topology_features(o)))),
        "CTRL_NO_NORMALIZATION_ABLATION":
            lambda o:learner.forward(o,trained,ablation="NO_NORMALIZATION")[0],
        "CTRL_NO_NULL_SUBTRACTION_ABLATION":
            lambda o:learner.forward(o,trained,ablation="NO_NULL")[0],
    }
    scores={}
    for name,predict in mechanisms.items():
        start=time.perf_counter_ns()
        result=learner.paired_score(rows,predict)
        elapsed=time.perf_counter_ns()-start
        scores[name]={**result,
            "inference_wallclock_ns_one_pass_uncontrolled":elapsed}
    # Frozen F124R rejects depth-5 PUBLIC observations; preserve this
    # incompatibility. Never shrink denominator or change its validator.
    incompatible=0;compatible=0
    for g,y in rows:
        if len(g["roles"])>4:
            incompatible+=1
        else:compatible+=1
    need(incompatible>0 and compatible>0,"EXPECTED_F124R_FROZEN_SCOPE")
    scores["CTRL_F124R_SPARSE2_FRESH"]={
        "status":"BLOCKED_FROZEN_INTERFACE_DEPTH_5",
        "frozen_source_unchanged":True,
        "full_cohort_score_available":False,
        "incompatible_public_train_graphs":incompatible,
        "compatible_public_train_graphs":compatible,
        "denominator_reduction_prohibited":True}
    work_learner={};work_exact={}
    causal_null_flip=0
    for graph,y in rows:
        _,_,trace=learner.forward(graph,trained,trace=True)
        exact,ew=oracle_work(graph)
        need(exact==y,"EXACT_PUBLIC_ELIGIBLE_REF_FAILED")
        for k,v in trace["work"].items():
            work_learner[k]=work_learner.get(k,0)+v
        for k,v in ew.items():
            work_exact[k]=work_exact.get(k,0)+v
    # Heterogeneous event units cannot honestly certify actual cost reduction.
    learned=scores["F126R_TRAINED"]
    exact=scores["CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE"]
    need(exact["paired_correct"]==64,"EXACT_REF_NONELIGIBLE")
    controls_max=max((x["paired_correct"] for k,x in scores.items()
             if k.startswith("CTRL_") and "paired_correct" in x
             and k not in ("CTRL_NO_NORMALIZATION_ABLATION",
                           "CTRL_NO_NULL_SUBTRACTION_ABLATION")),default=0)
    return {
        "lane":lane,"source_candidate_shas":raw_ids,
        "source_vectors_sha256":env.digest(vectors),
        "train_rows_sha256":env.digest(rows),
        "learned_weights":trained,
        "learned_weights_sha256":learner.sha(trained),
        "weight_movement":movement,"train_pairs":64,
        "frozen_epochs":100,"learned_parameters":20,
        "scores":scores,"strongest_eligible_control_paired":controls_max,
        "learned_meets_90pct_exact_on_train":learned["paired_correct"]>=58,
        "learned_rank_at_least_90pct_on_train":learned["rank_correct"]>=58,
        "total_uncontrolled_work_learner":work_learner,
        "total_uncontrolled_work_exact":work_exact,
        "homogeneous_cost_equivalence_established":False,
        "scientific_success":False,
        "protected_confirmation_read":False,
        "full_cohort_including_failures":True
    }

def experiment(advisory,source):
    cfg,_=freeze.frozen()
    need(isinstance(source,str) and re.fullmatch("[a-f0-9]{40}",source)
         and (not os.environ.get("GITHUB_SHA")
              or os.environ["GITHUB_SHA"]==source),"INVALID_GITHUB_HEAD")
    need(git_blob(dense.__file__)==F123_BLOB and
         git_blob(preserving.__file__)==F125R_BLOB,
         "FROZEN_COMPARATOR_SOURCE_IDENTITY")
    candidates=f120.validate(advisory,source)
    need(set(candidates)=={"Wingless","Yggdrasil"},"TWO_SOURCE_LANES")
    lanes=[]
    for lane in ("Wingless","Yggdrasil"):
        entries=candidates[lane]
        need(len(entries)==2 and
             [e["candidate_index"] for e in entries]==[2,3] and
             entries[0]["vector"]!=entries[1]["vector"],
             "TWO_INDEPENDENT_SOURCE_VECTORS")
        lanes.append(evaluate(lane,[e["vector"] for e in entries],
           [e["source_candidate_sha256"] for e in entries]))
    return {"schema":SCHEMA,"source_sha":source,
       "freeze_git_blob":freeze.SOURCE_BLOB,
       "advisory_sha256":learner.sha(advisory),
       "phase":"PUBLIC_SYNTHETIC_TRAIN_ONLY",
       "lanes":lanes,
       "eligible_exact_symbolic_is_not_excluded":True,
       "scientific_first_use":False,"scientific_acceptance":False,
       "optimizer_promotion":False,"protected_confirmation_read":False,
       "originals_dispatched":0,"codex_calls":0,"paid_model_calls":0,
       "accepted_refs_mutated":0,"new_scheduler":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--advisory",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    advisory=f118.load_report(args.advisory)
    result=experiment(advisory,args.source_sha)
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"OVERWRITE_DENIED")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    out.open("xb").write(raw)
    print("F126R_TRAIN_SOURCE_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        print("F126R_"+lane["lane"].upper()+"_TRAIN="+
              str(lane["scores"]["F126R_TRAINED"]["paired_correct"])+"/64")
        print("F126R_"+lane["lane"].upper()+"_ELIGIBLE_EXACT="+
              str(lane["scores"]["CTRL_EXACT_PUBLIC_SYMBOLIC_ELIGIBLE"]["paired_correct"])+"/64")
        print("F126R_"+lane["lane"].upper()+"_SPARSE2_STATUS="+
              lane["scores"]["CTRL_F124R_SPARSE2_FRESH"]["status"])
    print("F126R_CONFIRM_UNTOUCHED=true")
    print("F126R_SCIENTIFIC_ACCEPTANCE=false")

if __name__=="__main__":
    try:main()
    except (env.Invalid,freeze.Invalid,f118.Quarantined,f120.Invalid,
            ValueError,TypeError,KeyError,OSError,ZeroDivisionError) as ex:
        print("F126R_TRAIN_QUARANTINED="+str(ex),file=sys.stderr)
        raise SystemExit(1)

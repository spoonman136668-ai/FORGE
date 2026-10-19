"""F124-BP: prospective source-blind compositional causal FIT experiment.

12 genuinely new A + 12 genuinely new B source cases, never before consumed.
Unchanged eligible F124-AZ route (including abstention) versus frozen 32-bit
learner on identical public 40 FIT + 8 CHECK and paired native graphs.
Original receipt files are written immediately, one first use only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE=ROOT/"nativeevidence"
COHORT={"procedural":range(922000,922012),
        "feedback":range(923000,923012)}
SOURCE={"procedural":"f124bp_procedural_source.py",
        "feedback":"f124bp_feedback_source.py"}
BLOBS={
    "procedural":"c5c2ee4fd88748f955af758889f83709fde3308d",
    "feedback":"78646cd8b4e0a13a95e3f18df043b7ba1277d696",
    "learner":"fec421e5e0f4501125e5c8307a290e7a473d3b38",
    "AZ":"0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7",
    "native":"94d2ae8266da792d254ac54baf3056bbd9b49412"
}


def need(ok,reason):
    if not ok:raise RuntimeError("F124BP_FIRSTUSE_"+reason)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"IMPORT")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def object_id(path):
    x=subprocess.run(["git","rev-parse","HEAD:"+str(path.relative_to(ROOT))
                      .replace("\\","/")],cwd=ROOT,capture_output=True,text=True)
    need(x.returncode==0,"PIN_GIT_SOURCE")
    return x.stdout.strip()


def identity(case):
    need(type(case) is int,"INTEGER_CASE")
    for family,ids in COHORT.items():
        if case in ids:return family
    raise RuntimeError("F124BP_FIRSTUSE_UNAUTHORIZED_OR_CONSUMED_CASE")


def bits(x):
    return [(x>>i)&1 for i in range(16)]


def digest(obj):
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def evaluate(case,arm):
    need(sys.platform=="linux" and arm in ("AZ","compact"),
         "ORIGINAL_LINUX_AND_FROZEN_ARM_ONLY")
    import resource
    family=identity(case)
    path=HERE/SOURCE[family]
    need(object_id(path)==BLOBS[family]
         and object_id(HERE/"f124bp_compact_learner.py")==BLOBS["learner"]
         and object_id(NATIVE/"f124az_joint_public_inverse.py")==BLOBS["AZ"]
         and object_id(NATIVE/"f124ag_transition_models.py")==BLOBS["native"],
         "ORIGINAL_SOURCE_IDENTITY")
    tic=time.process_time_ns()
    original_source=load("f124bp_private_source_"+family,path)
    issued,private_truth=original_source.make(case)
    need(private_truth["private_positive_routes"]==1
         and private_truth["private_hard_routes"]==0,
         "UNAMBIGUOUS_SOURCE_TRUTH")
    fit,check=issued["FIT"],issued["CHECK"]
    g,h=issued["positive"],issued["hard_negative"]
    need(len(fit)==40 and len(check)==8 and
         g["demos"]==h["demos"],"SAME_PUBLIC_48")
    support=fit+check
    demonstrations=[{"input_bits":bits(x),"output_bits":bits(y)}
                    for x,y in support]
    need(g["demos"]==demonstrations[:24],
         "UNPRIVILEGED_GRAPH_PUBLIC_SUPPORT")
    task_SHA=digest({"support":support,"g":g,"h":h})
    sys.path.insert(0,str(NATIVE))
    import f124az_joint_public_inverse as az
    import f124ag_transition_models as native
    import f124aj_example_operator_learner as parser
    base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
    delta=[0.0,0.0]
    if arm=="AZ":
        orig=az.train(demonstrations,"BP-NEW-FROZEN-PUBLIC",0)
        score_p,work_p,_=az.score(g,list(base),list(delta),orig,demonstrations)
        score_h,work_h,_=az.score(h,list(base),list(delta),orig,demonstrations)
        note={"original_AZ_policy":True,"AZ_route":orig["choice"],
              "AZ_forced_diagnostic":False,
              "native_positive_executed":work_p is not None,
              "native_hard_executed":work_h is not None,
              "AZ_model_bits_lower":orig["extra_task_model_bits_lower"]}
    else:
        learner=load("f124bp_frozen_public_only_learner",
                     HERE/"f124bp_compact_learner.py")
        model,fit_receipt,plausible=learner.learn(fit,check)
        if model is None:
            score_p=score_h=-1e9
            note={"original_AZ_policy":False,"fitted":False,
                  "native_scorer_calls":0,
                  "public_only_fit_receipt":fit_receipt,
                  "model_state_bits":32}
        else:
            decisions=[]
            traces=[]
            for graph in (g,h):
                is_valid,judgment=learner.causal_consensus(
                    graph,model,plausible)
                parsed,public,nonce=parser.public_task(graph)
                need(public==demonstrations[:24],
                     "EXACT_NATIVE_PUBLIC_DEMONSTRATIONS")
                native.frozen.prior.parent.validate_15(parsed)
                for edge in parsed["edges"]:
                    yy=sum(b<<j for j,b in enumerate(edge["src_bits"]))
                    xx=learner.inverse(yy,model)
                    edge["src_bits"]=bits(xx)
                native.frozen.prior.parent.validate_15(parsed)
                value,raw,ratio,work=native.ygg_transition(
                    parsed,list(base),list(delta),.1)
                need(math.isfinite(value) and work["max_active"]<=7
                     and work["max_retained"]<=9,
                     "NATIVE_7_ACTIVE_9_RETAINED")
                decisions.append(1. if is_valid else -1.)
                traces.append({"causal_consensus":judgment,
                               "native_value_diagnostic":value,
                               "native_work":work})
            score_p,score_h=decisions
            note={"original_AZ_policy":False,"fitted":True,
                  "public_only_fit_receipt":fit_receipt,
                  "model_state_bits":32,
                  "source_private_operator_used":False,
                  "native_scorer_calls":2,
                  "positive_trace":traces[0],"hard_trace":traces[1]}
    cpu=time.process_time_ns()-tic
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0,"REAL_PROCESS_COST")
    return {"schema":"mass.f124bp.original-sourceborn-development-pair.v1",
            "case":case,"family":family,"arm":arm,
            "same_public_graph_SHA256":task_SHA,
            "private_source_evaluator_only":{"positive":1,"negative":0},
            "positive_accepted":score_p>=0,
            "hard_negative_false_positive":score_h>=0,
            "positive_score":score_p,"hard_negative_score":score_h,
            "measured_CPU_ns":cpu,"measured_whole_process_RSS_bytes":rss,
            "model_trace":note,
            "previous_FIT_cases_replayed":False,
            "old_TRAIN_replayed":False,
            "protected_128_and_BH_U_R_used":False,
            "scientific_accepted":False,
            "optimizer_promoted":False}


def aggregate(rows):
    need(len(rows)==48,"ORIGINAL_24X2_RECORDS")
    outcome={}
    for family,ids in COHORT.items():
        pairs=[]
        for case in ids:
            subset=[r for r in rows if r["case"]==case]
            need(len(subset)==2 and {r["arm"] for r in subset}==
                 {"AZ","compact"} and
                 all(r["family"]==family for r in subset),
                 "EXACT_CASE_TWO_ARMS")
            a=next(x for x in subset if x["arm"]=="AZ")
            c=next(x for x in subset if x["arm"]=="compact")
            need(a["same_public_graph_SHA256"]==
                 c["same_public_graph_SHA256"] and
                 a["private_source_evaluator_only"]==
                 c["private_source_evaluator_only"]==
                 {"positive":1,"negative":0},
                 "UNMATCHED_SOURCE_OR_PRIVATE_TRUTH")
            pairs.append({
              "case":case,
              "AZ_positive":a["positive_accepted"],
              "AZ_hard_FP":a["hard_negative_false_positive"],
              "compact_positive":c["positive_accepted"],
              "compact_hard_FP":c["hard_negative_false_positive"],
              "compact_fitted":c["model_trace"].get("fitted",False),
              "AZ_CPU_ns":a["measured_CPU_ns"],
              "compact_CPU_ns":c["measured_CPU_ns"],
              "AZ_OS_RSS_bytes":a["measured_whole_process_RSS_bytes"],
              "compact_OS_RSS_bytes":c["measured_whole_process_RSS_bytes"],
              "task_SHA256":a["same_public_graph_SHA256"]})
        losses=[p["case"] for p in pairs
                if p["AZ_positive"] and not p["compact_positive"]]
        hard_fp=[p["case"] for p in pairs if p["compact_hard_FP"]]
        best={p["case"] for p in pairs
              if p["AZ_positive"] and not p["AZ_hard_FP"]}
        new={p["case"] for p in pairs
             if p["compact_positive"] and not p["compact_hard_FP"]}
        per_case_resource=all(p["compact_CPU_ns"]<=p["AZ_CPU_ns"]
                              and p["compact_OS_RSS_bytes"]<=p["AZ_OS_RSS_bytes"]
                              for p in pairs)
        fit_success=(not losses and not hard_fp and len(new-best)>=2
                     and per_case_resource)
        outcome[family]={
          "pair_count":len(pairs),
          "baseline_positive_count":sum(p["AZ_positive"] for p in pairs),
          "baseline_hard_false_positive_count":sum(p["AZ_hard_FP"] for p in pairs),
          "compact_positive_count":sum(p["compact_positive"] for p in pairs),
          "compact_hard_false_positive_ids":hard_fp,
          "baseline_positive_lost_ids":losses,
          "compact_correct_pairs":len(new),
          "new_correct_pairs":sorted(new-best),
          "compact_identifiable_cases":sum(p["compact_fitted"] for p in pairs),
          "resource_parity_every_case":per_case_resource,
          "frozen_FIT_admissible":fit_success,
          "per_case":pairs}
    return {"schema":"mass.f124bp.original-new-composition-development.v1",
            "cases":24,"arm_records":48,
            "results":outcome,
            "preregistered_joint_FIT_admissible":all(
                x["frozen_FIT_admissible"] for x in outcome.values()),
            "source_private_operator_never_model_input":True,
            "prior_BM_BN_BO_cases_used":False,
            "original_192_TRAIN_replayed":False,
            "BO_BP_protected_and_prior_BH_U_R_used":False,
            "external_thirdparty_source_novelty_certified":False,
            "full_scientific_resource_parity_certified":False,
            "science_accepted":False,
            "optimizer_policy_promoted":False,
            "disposition":"ORIGINAL_PROSPECTIVE_FIT_ONLY_NOT_SCIENTIFIC_ACCEPTANCE"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--case",type=int)
    p.add_argument("--arm",choices=("AZ","compact"))
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    if args.child:
        need(args.case is not None and args.arm is not None,"CHILD_ARGS")
        print(json.dumps(evaluate(args.case,args.arm),sort_keys=True))
        return
    need(args.output is not None,"ARCHIVE_PATH")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case in list(COHORT["procedural"])+list(COHORT["feedback"]):
        for arm in ("AZ","compact"):
            x=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                              "--child","--case",str(case),"--arm",arm],
                             cwd=ROOT,capture_output=True,text=True,timeout=240)
            need(x.returncode==0,"SOURCE_FIRSTUSE_CHILD_FAILED_"+
                 str(case)+"_"+arm+":"+x.stderr[-2000:])
            record=json.loads(x.stdout)
            # A failed later case never erases or silently replaces earlier ones.
            target=args.output.parent/("firstuse_"+str(case)+"_"+arm+".json")
            with target.open("x",encoding="utf-8") as f:
                json.dump(record,f,indent=2,sort_keys=True)
                f.write("\n")
            rows.append(record)
    evidence={"summary":aggregate(rows)}
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(evidence,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BP_ORIGINAL_SOURCE_CASES=24")
    print("F124BP_ORIGINAL_ARM_RECORDS=48")
    for family,results in evidence["summary"]["results"].items():
        print("F124BP_"+family.upper()+"_CORRECT_PAIRS="+
              str(results["compact_correct_pairs"]))
        print("F124BP_"+family.upper()+"_HARD_FP="+
              str(len(results["compact_hard_false_positive_ids"])))
        print("F124BP_"+family.upper()+"_RSS_PARITY="+
              str(results["resource_parity_every_case"]))
        print("F124BP_"+family.upper()+"_FROZEN_GATE="+
              str(results["frozen_FIT_admissible"]))
    print("F124BP_JOINT_DEVELOPMENT_PASS="+
          str(evidence["summary"]["preregistered_joint_FIT_admissible"]))
    print("F124BP_PROTECTED_FIRSTUSE=false")
    print("F124BP_SCIENTIFIC_ACCEPTED=false")


if __name__=="__main__":
    main()

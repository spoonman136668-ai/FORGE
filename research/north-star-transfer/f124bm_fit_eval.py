"""F124-BM source-blind causal transfer FIT screen: original controls only.

Two separately committed model-free sources, new prospective public FIT only,
not protected original U/R or reserved BM 128 holdout. Genuine original F124-AZ
policy (not forced diagnostic) versus frozen 32-bit learned inverse, on paired
public graphs with independent symbolic truth sealed to evaluator.
No learning or model choice may depend on results.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
NATIVE=ROOT/"nativeevidence"
GF=range(914000,914016)
ARX=range(915000,915016)
T1="bf81ed56cc0daa2c413ad7d9c698969f92befe3d"
AZ="0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7"
NATIVE_SHA="94d2ae8266da792d254ac54baf3056bbd9b49412"
SOURCE_BLOBS={
    "GF2":"e7df91c7270567d56ce62243196d8f67aa09c024",
    "ARX":"f3fbb5d04bff86d51a5a9ddb0c52979bb67924fe",
}
PRIOR=bytes.fromhex("5a00cd00")


def need(ok,reason):
    if not ok:
        raise RuntimeError("F124BM_FIT_"+reason)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"MODULE_IMPORT")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def git_blob(path):
    p=subprocess.run(["git","rev-parse","HEAD:"+str(path.relative_to(ROOT))
                      .replace("\\","/")],cwd=ROOT,text=True,capture_output=True)
    need(p.returncode==0,"GIT_ID")
    return p.stdout.strip()


def sha(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def source_for(seed):
    if type(seed) is int and seed in GF:
        return "GF2","f124bm_gf2_source.py"
    if type(seed) is int and seed in ARX:
        return "ARX","f124bm_arx_source.py"
    raise RuntimeError("F124BM_FIT_PROTECTED_OR_UNREGISTERED_ID_DENIED")


def models():
    sys.path.insert(0,str(NATIVE))
    import f124az_joint_public_inverse as az
    import f124ag_transition_models as native
    import f124aj_example_operator_learner as parser
    kernel=load("bm_frozen_kernel",HERE/"20261018-mass-learned-kernel.py")
    return az,native,parser,kernel


def score_native(g,model,kernel,native,parser,base,delta):
    parsed,demos,nonce=parser.public_task(g)
    need(demos==g["demos"],"UNCHANGED_24_PUBLIC_SUPPORT")
    native.frozen.prior.parent.validate_15(parsed)
    for edge in parsed["edges"]:
        x=kernel.inverse(sum(b<<i for i,b in enumerate(edge["src_bits"])),
                         model)
        edge["src_bits"]=[(x>>i)&1 for i in range(16)]
    value,_,_,work=native.ygg_transition(parsed,list(base),list(delta),.1)
    need(math.isfinite(value) and work["max_active"]<=7
         and work["max_retained"]<=9,"NATIVE_COGNITION_BOUNDS")
    return value,work


def one(seed,arm):
    need(arm in ("learned","AZ"),"FROZEN_ARM")
    name,file=source_for(seed)
    need(git_blob(HERE/file)==SOURCE_BLOBS[name]
         and git_blob(HERE/"20261018-mass-learned-kernel.py")==T1
         and git_blob(NATIVE/"f124az_joint_public_inverse.py")==AZ
         and git_blob(NATIVE/"f124ag_transition_models.py")==NATIVE_SHA,
         "SOURCE_OR_MODEL_IDENTITY")
    need(sys.platform=="linux","REAL_LINUX_PROCESS_RESOURCES")
    import resource
    t0=time.process_time_ns()
    source=load("bm_independent_source_"+name,HERE/file)
    issued,private=source.make(seed)
    # Private symbols and relation inverse are only used by source authority,
    # not supplied to either model or its graph-normalization functions.
    expected_pos=private.get("oracle_positive_routes",private.get("oracle_positive"))
    expected_neg=private.get("oracle_negative_routes",private.get("oracle_negative"))
    need(expected_pos==1 and expected_neg==0,"UNAMBIGUOUS_PRIVATE_SYMBOLIC_LABEL")
    public=issued["FIT"]+issued["CHECK"]
    graph_p=issued["positive"]
    graph_n=issued["hard_negative"]
    need(len(public)==48 and len(graph_p["demos"])==24
         and graph_p["demos"]==graph_n["demos"],
         "PUBLIC_SOURCE_MATCH")
    payload={"seed":seed,"public":public,"positive":graph_p,
             "hard_negative":graph_n}
    original, native, parser, kernel=models()
    base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
    delta=[0.0,0.0]
    demos=[{"input_bits":[(x>>i)&1 for i in range(16)],
            "output_bits":[(y>>i)&1 for i in range(16)]}
           for x,y in public]
    need(graph_p["demos"]==demos[:24],"EXACT_PUBLIC_SOURCE_FOR_EACH_ARM")
    if arm=="learned":
        model,fit=kernel.fit_public(issued["FIT"],issued["CHECK"],init=PRIOR)
        need(len(model)==4 and fit["public_forward_evaluations"]==2608,
             "UNMODIFIED_FROZEN_KERNEL")
        pos,poswork=score_native(graph_p,model,kernel,native,parser,base,delta)
        neg,negwork=score_native(graph_n,model,kernel,native,parser,base,delta)
        report={"original_scientific_policy":True,"policy_abstained":False,
                "fitted_mask_sha256":hashlib.sha256(model).hexdigest(),
                "fit_bits":fit["public_FIT_bit_errors"],
                "check_bits":fit["public_CHECK_bit_errors"],
                "positive_work":poswork,"negative_work":negwork,
                "native_scorer_calls":2,
                "learned_model_extra_parameter_bits_lower":32}
    else:
        original_fit=original.train(demos,str(seed),0)
        pos,pwork,pdiag=original.score(graph_p,base,delta,original_fit,demos)
        neg,nwork,ndiag=original.score(graph_n,base,delta,original_fit,demos)
        report={"original_scientific_policy":True,
                "policy_abstained":original_fit["choice"]=="abstain",
                "original_policy_route":original_fit["choice"],
                "positive_work":pwork,"negative_work":nwork,
                "positive_diagnostic":pdiag,"negative_diagnostic":ndiag,
                "native_scorer_calls":int(pwork is not None)+int(nwork is not None),
                "additional_model_bits_lower":original_fit["extra_task_model_bits_lower"]}
    elapsed=time.process_time_ns()-t0
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(elapsed>0 and rss>0,"OS_RESOURCE_MISSING")
    return {"schema":"mass.f124bm.original-frozen-prospective-public-FIT-only.v1",
            "source_family":name,"seed":seed,"arm":arm,
            "same_public_and_graph_sha256":sha(payload),
            "positive_graph_sha256":sha(graph_p),
            "hard_graph_sha256":sha(graph_n),
            "private_symbolic_truth_only_for_evaluation":{
                "positive_routes":expected_pos,"hard_negative_routes":expected_neg},
            "positive_score":pos,"hard_negative_score":neg,
            "positive_accepted":pos>=0,"hard_negative_accepted":neg>=0,
            "source_is_new_FIT_only":True,
            "no_private_relation_passed_to_model":True,
            "native_policy_trace":report,
            "task_CPU_ns":elapsed,"whole_process_peak_RSS_bytes":rss,
            "platform":platform.platform(),
            "original_TRAIN_replayed":False,
            "original_BH_U_R_heldout_used":False,
            "BM_128case_holdout_used":False,
            "science_accepted":False,
            "optimizer_promotion":False}


def aggregate(items):
    need(len(items)==64,"32_CASES_TIMES_TWO_ARMS")
    families={}
    for family,seeds in (("GF2",GF),("ARX",ARX)):
        per=[]
        for seed in seeds:
            pair=[x for x in items if x["seed"]==seed]
            need(len(pair)==2 and {x["arm"] for x in pair}=={"learned","AZ"},
                 "IDENTICAL_TASK_TWO_ARMS")
            models={x["arm"]:x for x in pair}
            a=models["AZ"]
            b=models["learned"]
            need(a["same_public_and_graph_sha256"]==b["same_public_and_graph_sha256"]
                 and all(x["source_family"]==family for x in pair),
                 "SOURCE_SHAPE_DRIFT")
            need(all(x["private_symbolic_truth_only_for_evaluation"]==
                     {"positive_routes":1,"hard_negative_routes":0}
                     for x in pair), "SOURCE_LABEL_DRIFT")
            per.append({"seed":seed,
                        "AZ_positive":a["positive_accepted"],
                        "AZ_hard_FP":a["hard_negative_accepted"],
                        "AZ_abstain":a["native_policy_trace"]["policy_abstained"],
                        "learned_positive":b["positive_accepted"],
                        "learned_hard_FP":b["hard_negative_accepted"],
                        "both_task_sha256":a["same_public_and_graph_sha256"],
                        "AZ_CPU_ns":a["task_CPU_ns"],"learned_CPU_ns":b["task_CPU_ns"],
                        "AZ_peak_RSS":a["whole_process_peak_RSS_bytes"],
                        "learned_peak_RSS":b["whole_process_peak_RSS_bytes"]})
        baseline_correct_pos={r["seed"] for r in per if r["AZ_positive"] and not r["AZ_hard_FP"]}
        learned_correct_pos={r["seed"] for r in per if r["learned_positive"] and not r["learned_hard_FP"]}
        baseline_pos={r["seed"] for r in per if r["AZ_positive"]}
        candidate_pos={r["seed"] for r in per if r["learned_positive"]}
        missed=sorted(baseline_pos-candidate_pos)
        hard_fp=[r["seed"] for r in per if r["learned_hard_FP"]]
        fit_gate=(not missed and not hard_fp and
                  len(learned_correct_pos-baseline_correct_pos)>=2 and
                  len(baseline_pos)>0)
        families[family]={
          "pairs":len(per),
          "baseline_positive_count":len(baseline_pos),
          "baseline_correct_pair_count":len(baseline_correct_pos),
          "candidate_correct_pair_count":len(learned_correct_pos),
          "candidate_positive_count":len(candidate_pos),
          "baseline_positive_lost_ids":missed,
          "candidate_hard_false_positive_ids":hard_fp,
          "newly_correct_pair_ids":sorted(learned_correct_pos-baseline_correct_pos),
          "baseline_abstentions":sum(r["AZ_abstain"] for r in per),
          "FIT_mechanistic_gate":fit_gate,
          "paired_outcomes":per}
    return {
      "schema":"mass.f124bm.first-original-fitscreen-source-blind-causal-contrast.v1",
      "frozen_source_birth_only":True,
      "first_use": "new_public_FIT_only",
      "total_pair_count":32,
      "total_task_arm_evaluations":64,
      "families":families,
      "FIT_gain_and_FP_constraints_met_in_both":all(
          f["FIT_mechanistic_gate"] for f in families.values()),
      "original_192_TRAIN_replayed":False,
      "original_TRAIN_raw_firstuse_receipt_recovered":False,
      "original_U_R_protected_used":False,
      "BM_protected_128pair_cohorts_used":False,
      "independent_external_novelty_certified":False,
      "scientific_out_of_distribution_accepted":False,
      "complete_equal_cost_science_proven":False,
      "optimizer_policy_update":False,
      "disposition":"DEVELOPMENT_FIT_ONLY_NO_SCIENTIFIC_ADMISSION"
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--seed",type=int)
    p.add_argument("--arm",choices=("AZ","learned"))
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    if args.child:
        need(args.seed is not None and args.arm is not None,"CHILD_ARGUMENTS")
        print(json.dumps(one(args.seed,args.arm),sort_keys=True))
        return
    need(args.output is not None,"OUTPUT")
    # Use a unique non-overwriting first-use receipt location, including on
    # failure. Each original spawned child uses only its single registered
    # FIT case; no protected source constructors.
    ids=list(GF)+list(ARX)
    samples=[]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for seed in ids:
        for arm in ("AZ","learned"):
            proc=subprocess.run(
                [sys.executable,"-B",str(Path(__file__).resolve()),
                 "--child","--seed",str(seed),"--arm",arm],
                cwd=ROOT,text=True,capture_output=True,timeout=180)
            if proc.returncode:
                raise RuntimeError("F124BM_ORIGINAL_FIRST_USE_CHILD_FAILED_"+
                                   str(seed)+"_"+arm+":"+proc.stderr[-2500:])
            sample=json.loads(proc.stdout)
            # Append each individual first-use observation immediately before
            # any later aggregation, preserving partial custody after errors.
            individual=args.output.parent/("firstuse_"+str(seed)+"_"+arm+".json")
            with individual.open("x",encoding="utf-8") as f:
                json.dump(sample,f,indent=2,sort_keys=True)
                f.write("\n")
            samples.append(sample)
    receipt={"summary":aggregate(samples)}
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(receipt,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BM_ORIGINAL_FIRST_USE_FIT_CASES=32")
    print("F124BM_ORIGINAL_RAW_RECORDS=64")
    print("F124BM_FIT_SCREEN_GATE="+str(receipt["summary"][
        "FIT_gain_and_FP_constraints_met_in_both"]))
    print("F124BM_PROTECTED_U_R_AND_128_HOLDOUT_USE=0")
    print("F124BM_SCIENTIFIC_ACCEPTED=false")


if __name__=="__main__":
    main()

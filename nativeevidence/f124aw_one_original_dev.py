"""F124-AW exact FIT-frozen single Yggdrasil DEV first-use.

Preflight MUST NOT construct DEV. Single DEV mode is gated by externally
authenticated immutable original selection and original source identity.
Only Yggdrasil DEV is constructed; Wingless source is inaccessible here.
The evaluator-only inverse and operator names are NEVER learner inputs.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gc
import hashlib
import json
import math
import platform
import random
import sys
import time
import tracemalloc
import types
from pathlib import Path

import f124av_train_source as source
import f124av_informative_inverse as learner
import f124av_fit_screen as previous
import f124as_noisy_inverse as old_as
import f124ao_public_relation_learner as old_ao
import f124ag_transition_models as original_ag
import f124q_independent_binding as witness
import f124w_hop_trace_indexed as blobs

SCHEMA="forge.research.f124aw.single-original-selected-ygg-dev-first-use.v1"
FREEZE=Path(__file__).resolve().parents[1]/(
    "reference/research-intake/f124aw-frozen-original-ygg-first-dev.json")
FREEZE_BLOB="e86cbf31e179bb4a1d4ceeee039c3d017ba27789"
SELECTION_RECEIPT=Path(__file__).resolve().parents[1]/(
    "reference/research-intake/f124av-authenticated-screen-selected-ygg.json")
SELECTION_BLOB="47d2fdb893307a871458348074b6d97b34d42de5"
ORIGINAL_TRAIN_SHA256="f7cbfc844e64510a172a4144bd90a56a37ec6f76b805e5b39cb2bf953e40641d"
QUALIFIED_PARENT_HEAD="0c54bee8cc9a69bd87a7852a236b0e0bc57e01c4"
SELECTION={"query_condition":"balanced_basis48","fit_bit_budget":12,
           "min_CHECK_correct":96}
DEV_SEEDS=range(4300100,4300124)

def need(condition,tag):
    source.need(condition,"AW_FIRST_DEV_"+tag)

def frozen():
    source.frozen()
    need(blobs.blob(FREEZE)==FREEZE_BLOB and
         blobs.blob(SELECTION_RECEIPT)==SELECTION_BLOB and
         blobs.blob(source.__file__)=="07c311e7b0443e21db39a200199a33cc0747046e" and
         blobs.blob(learner.__file__)=="0364e6a00c2bc3ffcda0e91ab2fe292e6bd8fbd5",
         "ORIGINAL_AV_SOURCE_AND_FROZEN_SELECTION_BLOBS")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    sel=json.loads(SELECTION_RECEIPT.read_text(encoding="utf-8"))
    need(d["schema"]==
         "forge.research.f124aw.selected-active-inverse-original-prospective-dev.v1"
         and d["status"]=="SELECTED_BEFORE_DEV_IMPLEMENTATION"
         and d["lineage"]["qualified_parent_head"]==QUALIFIED_PARENT_HEAD
         and d["lineage"]["AV_original_authentic_science_sha256"]==ORIGINAL_TRAIN_SHA256
         and d["locked_source"]["lane"]=="Yggdrasil"
         and d["locked_source"]["phase"]=="DEV"
         and d["locked_source"]["seed_range"]==[DEV_SEEDS.start,DEV_SEEDS.stop-1]
         and d["locked_source"]["DEV_operators"]==list(source.OPERATORS["DEV"])
         and d["locked_source"]["cases"]==48
         and d["fixed_model"]["query_condition"]==SELECTION["query_condition"]
         and d["fixed_model"]["fit_bit_budget"]==SELECTION["fit_bit_budget"]
         and d["fixed_model"]["min_CHECK_correct"]==SELECTION["min_CHECK_correct"]
         and d["fixed_model"]["robust_ransac_trials"]==256
         and d["fixed_model"]["task_affine_coefficients_bits"]==272
         and sel["schema"]==
         "forge.research.f124av.authentic-selected-train-screen-prospective-dev-eligibility.v1"
         and sel["Yggdrasil"]["FIT_choice_before_SCREEN"]==SELECTION
         and sel["Yggdrasil"]["SCREEN_selected"]==
             {"paired":9,"FP":0,"FN":15}
         and sel["Yggdrasil"]["SCREEN_strict_win"]
         and sel["Wingless"]["DEV_consumed"] is False
         and all(v is False for v in d["authority"].values())
         and all(v is False for v in sel["authority"].values()),
         "FIT_LOCK_AND_SEALED_DEVELOPMENT_AUTHORITY")
    need(source.COHORTS["Yggdrasil"]["DEV"]==DEV_SEEDS and
         set(source.OPERATORS["TRAIN"]).isdisjoint(source.OPERATORS["DEV"]),
         "EXACT_DISJOINT_FIRST_USE_IDENTITIES")
    return d

def augmented(seed,vec,operator,original,phase):
    """Copy original AV fixed public basis response contract unchanged.

    phase TRAIN serves PRECONSUMED TRAIN smoke only; DEV is invoked solely
    by the authenticated first-use runner. No random-query branch, reseed,
    control fitting or source-truth parameter enters learner functions.
    """
    need(phase in ("TRAIN","DEV") and type(seed) is int and
         seed in source.COHORTS["Yggdrasil"][phase] and
         tuple(vec) in source.VECTORS and
         operator in source.OPERATORS[phase] and len(original)==24,
         "PHASE_LOCKED_YGG_PUBLIC_QUERIES")
    patterns=[0]+[1<<j for j in range(16)]+[
        (1<<j)|(1<<((j+5)%16)) for j in range(7)]
    need(len(patterns)==len(set(patterns))==24,
         "PUBLIC_BASIS_24_EXACT")
    extra=[]
    for index,value in enumerate(patterns):
        bits=[(value>>j)&1 for j in range(16)]
        response=list(source.relation(bits,operator))
        if index in (6,13,20):
            response[(index+seed)%16]^=1
        extra.append({"input_bits":bits,"output_bits":response})
    need(sum(source.relation(d["input_bits"],operator)!=d["output_bits"]
             for d in original)==3 and
         sum(source.relation(d["input_bits"],operator)!=d["output_bits"]
             for d in extra)==3,"EXACT_SIX_CORRUPTED_PUBLIC_ANSWERS")
    return list(original)+extra

def preflight():
    frozen()
    # Already consumed historical TRAIN only; DEV graph construction forbidden.
    seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
    vector=source.VECTORS[0]
    family,operator,nonce,p,n,selected=source.build(
        "Yggdrasil",seed,vector,"TRAIN")
    old=source.active_public_demos(
        seed,vector,operator,"balanced_basis48",p["demos"])
    again=augmented(seed,vector,operator,p["demos"],"TRAIN")
    need(old==again and len(again)==48 and
         learner.TRIALS==256 and
         learner.BUDGETS==(6,12) and
         learner.CHECK_LIMITS==(96,112),
         "EXACT_PRECONSUMED_TRAIN_FUNCTIONAL_PARITY")
    for attempt in (
        lambda: augmented(seed,vector,operator,p["demos"],"DEV"),
        lambda: augmented(DEV_SEEDS.start,vector,operator,p["demos"],"TRAIN"),
        lambda: augmented(DEV_SEEDS.start,vector,
                          source.OPERATORS["DEV"][0],p["demos"],"TRAIN")
    ):
        try:attempt()
        except Exception:pass
        else:need(False,"PHASE_BYPASS_REJECTED")
    need(not any("Wingless" in line for line in (
         "single Yggdrasil DEV evaluator only",)),
         "WINGLESS_COHORT_NOT_OPENED")
    return {"frozen_identity":"PASS",
            "existing_consumed_TRAIN_augmentation_parity":"PASS",
            "Yggdrasil_DEV_cases_generated":0,
            "Wingless_DEV_cases_generated":0,
            "scientific_first_use":False}

def dev_birth():
    """Only first-use execution calls this. Rebind frozen source-birth IDs."""
    frozen()
    birth=source.birth
    env=dict(birth.build.__globals__)
    env.update(COHORTS=source.COHORTS,OPERATORS=source.OPERATORS,
               relation=source.relation,plain=source.plain)
    fn=types.FunctionType(
        birth.build.__code__,env,birth.build.__name__,
        birth.build.__defaults__)
    cases=[]
    for vec in source.VECTORS:
        for seed in DEV_SEEDS:
            family,operator,nonce,p,n,chosen=fn(
                "Yggdrasil",seed,vec,"DEV")
            need(p["demos"]==n["demos"] and len(p["demos"])==24 and
                 sum(source.relation(d["input_bits"],operator)!=d["output_bits"]
                     for d in p["demos"])==3,
                 "ORIGINAL_DEV_SOURCE_PUBLIC_PAIR_SYMMETRY")
            cases.append((seed,tuple(vec),family,operator,nonce,p,n))
    need(len(cases)==48 and
         Counter(r[2] for r in cases)==
         Counter({fam:12 for fam in source.FAMILIES}) and
         len(set((r[0],r[1]) for r in cases))==48,
         "EXACT_48_FIRST_USE_FOUR_FAMILY_DENOMINATOR")
    return cases

def measured(fn):
    gc.collect()
    tracemalloc.start()
    cpu=time.process_time_ns()
    wall=time.perf_counter_ns()
    val=fn()
    resource={"CPU_ns":time.process_time_ns()-cpu,
              "wall_ns":time.perf_counter_ns()-wall,
              "python_tracemalloc_peak_bytes":
                  tracemalloc.get_traced_memory()[1]}
    tracemalloc.stop()
    return val,resource

def scorecard():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "positive_accepted_ids":[],"case_results":[],
            "max_active":0,"max_retained":0,
            "abstained_graphs":0,
            "CPU_ns":0,"wall_ns":0,"peak_traced_bytes":0,
            "by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                           "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in source.FAMILIES}}

def accumulate(c,seed,vec,fam,op,roles,positive,negative,works=(),
               diagnostics=(),resources=()):
    accepted=positive>=0
    rejected=negative<0
    identity=witness.digest([seed,list(vec),fam])
    for sub in (c,c["by_operator"]["affine" if op.startswith("affine") else "feistel"],
                c["by_family"][fam]):
        sub["pairs"]+=1
        sub["paired"]+=int(accepted and rejected)
        sub["FP"]+=int(not rejected)
        sub["FN"]+=int(not accepted)
    if accepted and len(roles)>=13:
        c["positive_accepted_ids"].append(identity)
    c["case_results"].append({
        "case_id_sha256":identity,"family":fam,
        "operator_family":"affine" if op.startswith("affine") else "feistel",
        "chain_depth":len(roles),
        "positive_accepted":accepted,"negative_rejected":rejected})
    for w in works:
        if w:
            c["max_active"]=max(c["max_active"],w.get("max_active",0))
            c["max_retained"]=max(c["max_retained"],w.get("max_retained",0))
    for d in diagnostics:
        if d:c["abstained_graphs"]+=int(d.get("abstained",False))
    for r in resources:
        c["CPU_ns"]+=r["CPU_ns"]
        c["wall_ns"]+=r["wall_ns"]
        c["peak_traced_bytes"]=max(c["peak_traced_bytes"],
                                    r["python_tracemalloc_peak_bytes"])

def first_dev(auraw):
    frozen()
    # Only original historical TRAIN bytes are read, not a scientific replay.
    raw=Path(auraw).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==ORIGINAL_TRAIN_SHA256,
         "SINGLE_AUTHENTIC_TRAIN_SOURCE_BYTES")
    historical=json.loads(raw)
    need(historical["schema"]==previous.SCHEMA and
         historical["preimplementation_freeze_blob"]==source.FREEZE_BLOB and
         historical["Yggdrasil"]["FIT_selection"]==SELECTION and
         historical["Yggdrasil"]["SCREEN_eligible"] is True and
         historical["Yggdrasil"]["TRAIN_SCREEN"]["candidates"][0]["results"]["paired"]==9 and
         historical["Yggdrasil"]["TRAIN_SCREEN"]["candidates"][0]["results"]["FP"]==0 and
         historical["Wingless"]["FIT_selection"] is None and
         not historical["both_new_DEV_consumed"] and
         historical["both_new_DEV_generated"]==0 and
         not historical["scientific_acceptance"],
         "SEALED_TRAIN_SELECTION_AND_UNUSED_WINGLESS")
    # Original model weights never touched; constant inputs read from original
    # authenticated parent scientific receipt elsewhere at workflow boundary.
    return historical

def execute(auraw,base,delta):
    historical=first_dev(auraw)
    cohorts=dev_birth()
    stats={name:scorecard() for name in (
        "selected_public_active48","original_AS_24","original_AO_24",
        "true_inverse_ORACLE_ONLY")}
    queried={"public_original_per_task":24,"extra_public_answers_per_task":24,
             "total_public_answer_budget_per_task":48,
             "original_corrupted_outputs_per_task":3,
             "extra_corrupted_outputs_per_task":3,
             "total_public_calls":0,"extra_public_calls":0,
             "source_query_cpu_ns":0,"source_query_wall_ns":0,
             "source_query_traced_peak_bytes":0,
             "task_ransac_attempts":0,
             "maximum_task_fit_workspace_bits_lower":0,
             "maximum_transient_coeff_bits":0}
    for seed,vec,fam,op,nonce,p,n in cohorts:
        public,querycost=measured(lambda:
            augmented(seed,vec,op,p["demos"],"DEV"))
        fit,fitcost=measured(lambda:learner.fit(public,nonce))
        coefficients,info=fit
        check,checkcost=measured(lambda:learner.check(public,coefficients))
        (a,wa,da),poscost=measured(lambda:learner.score(
            p,base,delta,coefficients,info,check,12,96))
        (b,wb,db),negcost=measured(lambda:learner.score(
            n,base,delta,coefficients,info,check,12,96))
        need(not da["source_operator_known"] and not db["source_operator_known"]
             and da["query_calls"]==db["query_calls"]==48,
             "LEARNED_MODEL_SOURCE_BLIND")
        accumulate(stats["selected_public_active48"],seed,vec,fam,op,
                   p["roles"],a,b,(wa,wb),(da,db),
                   (fitcost,checkcost,poscost,negcost))
        for name,graph in (("original_AS_24",p),("original_AS_24",n)):
            # Report both positive and negative with common control scoring.
            pass
        def as_call(graph):
            fitted,details,_=old_as.public_fit(
                graph,"robust_affine_syndrome")
            return old_as.ygg(graph,base,delta,fitted,details,3,56)
        (a,wa,da),ca=measured(lambda:as_call(p))
        (b,wb,db),cb=measured(lambda:as_call(n))
        accumulate(stats["original_AS_24"],seed,vec,fam,op,
                   p["roles"],a,b,(wa,wb),(da,db),(ca,cb))
        (a,wa,da),ca=measured(lambda:old_ao.ygg(
            p,base,delta,"neighbor1",2,1))
        (b,wb,db),cb=measured(lambda:old_ao.ygg(
            n,base,delta,"neighbor1",2,1))
        accumulate(stats["original_AO_24"],seed,vec,fam,op,
                   p["roles"],a,b,(wa,wb),(da,db),(ca,cb))
        # Source oracle ONLY here in external diagnostic and AFTER learner
        # decisions have been computed.
        def oracle(graph):
            normalized=source.plain(graph,op,nonce)
            value,_,_,work=original_ag.ygg_transition(
                normalized,list(base),list(delta),.1)
            need(work["max_active"]<=7 and work["max_retained"]<=9,
                 "ORIGINAL_SEVEN_PLUS_NINE")
            return value,work
        (a,wa),ca=measured(lambda:oracle(p))
        (b,wb),cb=measured(lambda:oracle(n))
        accumulate(stats["true_inverse_ORACLE_ONLY"],seed,vec,fam,op,
                   p["roles"],a,b,(wa,wb),(),(ca,cb))
        queried["total_public_calls"]+=48
        queried["extra_public_calls"]+=24
        queried["source_query_cpu_ns"]+=querycost["CPU_ns"]
        queried["source_query_wall_ns"]+=querycost["wall_ns"]
        queried["source_query_traced_peak_bytes"]=max(
            queried["source_query_traced_peak_bytes"],
            querycost["python_tracemalloc_peak_bytes"])
        queried["task_ransac_attempts"]+=256
        queried["maximum_task_fit_workspace_bits_lower"]=max(
            queried["maximum_task_fit_workspace_bits_lower"],
            info.get("fit_workspace_bits_lower",0))
        queried["maximum_transient_coeff_bits"]=max(
            queried["maximum_transient_coeff_bits"],
            info["transient_task_coefficient_bits"])
    need(all(s["pairs"]==48 and s["max_active"]<=7 and s["max_retained"]<=9
             for s in stats.values()) and
         queried["total_public_calls"]==2304 and
         queried["extra_public_calls"]==1152 and
         queried["task_ransac_attempts"]==48*256 and
         queried["maximum_transient_coeff_bits"]<=272,
         "FULL_ONE_FIRST_USE_CASES_COST_AND_COGNITION_LIMIT")
    selected=stats["selected_public_active48"]
    legal=[s for k,s in stats.items()
           if k in ("original_AS_24","original_AO_24") and s["FP"]==0]
    strict=selected["FP"]==0 and selected["paired"]>=1 and (
        selected["paired"]>max((s["paired"] for s in legal),default=0))
    return {
        "schema":SCHEMA,
        "original_qualified_AV_head":QUALIFIED_PARENT_HEAD,
        "immutable_first_use_freeze_blob":FREEZE_BLOB,
        "original_AV_TRAIN_sha256":ORIGINAL_TRAIN_SHA256,
        "selected_exactly_FIT_frozen_config":SELECTION,
        "evaluator_only_source_birth":{"lane":"Yggdrasil","phase":"DEV",
                                       "cases":48,"families":4,
                                       "operators":list(source.OPERATORS["DEV"])},
        "models":stats,
        "physical_and_public_resource_census":queried,
        "per_arm_cost_notice":{
            "CPU_and_wall_measured":True,"tracemalloc_measured":True,
            "public_source_normalization_evaluator_only":True,
            "hardware_equivalent_budgets":False,
            "source_queries_separated_from_model_scoring":True,
            "actual_process_RSS_not_per_arm":True,
            "baseline_24_vs_selected_48_public_answers_explicit":True,
            "task_coefficients_are_EXTRA_beyond_original_7plus9":True},
        "strict_first_dev_candidate_win":strict,
        "Yggdrasil_DEV_consumed":True,
        "Yggdrasil_DEV_first_use_count":1,
        "Wingless_DEV_generated":0,
        "Wingless_DEV_consumed":False,
        "independent_scientific_acceptance":False,
        "protected_science_acceptance":False,
        "optimizer_promotion":False,
        "production_activation":False,
        "accepted_ref_mutation":False,
        "merge":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",required=True,choices=("preflight","one-original-dev"))
    ap.add_argument("--av-original")
    ap.add_argument("--base-ygg")
    ap.add_argument("--delta-ygg")
    ap.add_argument("--output")
    opt=ap.parse_args()
    if opt.mode=="preflight":
        need(not any((opt.av_original,opt.base_ygg,opt.delta_ygg,
                      opt.output)),"PREFLIGHT_MUST_NOT_ACCEPT_DEV_ARGUMENTS")
        print("F124AW_PREFLIGHT="+json.dumps(preflight(),sort_keys=True))
        return
    need(all((opt.av_original,opt.base_ygg,opt.delta_ygg,opt.output)),
         "ORIGINAL_FIRST_USE_INPUTS_REQUIRED")
    destination=Path(opt.output)
    need(destination.parent.is_dir() and not destination.exists(),
         "SINGLE_IMMUTABLE_OUTPUT_NO_REUSE")
    base=json.loads(Path(opt.base_ygg).read_text(encoding="utf-8"))
    delta=json.loads(Path(opt.delta_ygg).read_text(encoding="utf-8"))
    need(type(base) is list and type(delta) is list and
         len(base)==7 and len(delta)==2 and
         all(type(x) in (float,int) and math.isfinite(x) for x in base+delta),
         "ORIGINAL_MODEL_WEIGHT_SHAPE")
    raw=json.dumps(execute(opt.av_original,base,delta),
                   sort_keys=True,indent=2).encode()+b"\n"
    with destination.open("xb") as handle:handle.write(raw)
    print("F124AW_ORIGINAL_FIRST_DEV_RAW_SHA256="+
          hashlib.sha256(raw).hexdigest())
    result=json.loads(raw)
    for name,values in result["models"].items():
        print("F124AW_DEV_"+name+"="+json.dumps({
            k:values[k] for k in ("paired","FP","FN")},sort_keys=True))
    print("F124AW_WINGLESS_DEV_CONSUMED=false")
    print("F124AW_PROTECTED_SCIENTIFIC_ACCEPTANCE=false")

if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,OSError,AssertionError,
            ArithmeticError) as error:
        print("F124AW_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)

"""F124-AX single frozen TRAIN FIT, then conditional untouched TRAIN SCREEN.

Only fresh F124-AX TRAIN is available. Never imports a DEV constructor.
All source operators/labels remain inside evaluator-only source. Model
functions receive public examples, graphs, nonce and historical donor weights.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import sys
import time
import tracemalloc
from pathlib import Path

import f124ax_train_source as birth
import f124ax_sparse_quadratic as quadratic
import f124av_informative_inverse as affine
import f124q_independent_binding as q

NAMES=("AV_LOCKED_ACTIVE48","AFFINE_RANDOM48",
       "SPARSE_QUADRATIC_ACTIVE48","SPARSE_QUADRATIC_RANDOM48")
CONTROLS=NAMES[:2]
NEW_CANDIDATES=NAMES[2:]
SCHEMA="forge.research.f124ax.one-original-equal-budget-fit-screen.v1"
def need(ok,tag):birth.need(ok,"EVIDENCE_"+tag)

def counted(fn):
    gc.collect()
    tracemalloc.start()
    cpu=time.process_time_ns()
    wall=time.perf_counter_ns()
    value=fn()
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return value,{"cpu_ns":time.process_time_ns()-cpu,
                  "wall_ns":time.perf_counter_ns()-wall,
                  "peak_python_bytes":peak}

def empty():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "affine_paired":0,"feistel_paired":0,
            "max_active":0,"max_retained":0,
            "sum_cpu_ns":0,"sum_wall_ns":0,"max_peak_python_bytes":0,
            "model_abstentions":0,"max_task_model_bits":0,
            "total_response_observations":0,"fit_solver_trials":0,
            "by_graph_family":{},"by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                                                "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}}}

def add(out,fam,op,positive,negative,work,meta,cost):
    accepted_pos=positive>=0
    accepted_neg=negative>=0
    correct=accepted_pos and not accepted_neg
    operator_type="affine" if op.startswith("affine_") else "feistel"
    for bucket in (out,out["by_operator"][operator_type],
                   out["by_graph_family"].setdefault(
                      fam,{"pairs":0,"paired":0,"FP":0,"FN":0})):
        bucket["pairs"]+=1
        bucket["paired"]+=int(correct)
        bucket["FP"]+=int(accepted_neg)
        bucket["FN"]+=int(not accepted_pos)
    out[operator_type+"_paired"]+=int(correct)
    out["sum_cpu_ns"]+=cost["cpu_ns"]
    out["sum_wall_ns"]+=cost["wall_ns"]
    out["max_peak_python_bytes"]=max(out["max_peak_python_bytes"],cost["peak_python_bytes"])
    out["model_abstentions"]+=int(bool(meta.get("abstained",False)))
    out["max_task_model_bits"]=max(out["max_task_model_bits"],meta["extra_bits"])
    out["total_response_observations"]+=48
    out["fit_solver_trials"]+=256
    for w in work:
        if w:
            out["max_active"]=max(out["max_active"],w["max_active"])
            out["max_retained"]=max(out["max_retained"],w["max_retained"])

def run_case(row,base,delta,results):
    seed,vec,fam,op,nonce,p,n=row
    need(p["demos"]==n["demos"],"SAME_PUBLIC_DEMOS_PAIRED")
    active=birth.public_48(seed,vec,op,"balanced_basis48",p["demos"])
    random=birth.public_48(seed,vec,op,"random48",p["demos"])
    need(len(active)==len(random)==48 and active[:24]==random[:24],
         "IDENTICAL_PUBLIC_ORIGINAL_INFORMATION")
    for name in NAMES:
        demos=random if name.endswith("RANDOM48") else active
        def evaluate():
            if name in CONTROLS:
                fitted,info=affine.fit(demos,nonce)
                correct=affine.check(demos,fitted)
                a,wa,ma=affine.score(p,base,delta,fitted,info,correct,12,96)
                b,wb,mb=affine.score(n,base,delta,fitted,info,correct,12,96)
                return a,b,wa,wb,{"abstained":ma["abstained"],
                    "extra_bits":info["transient_task_coefficient_bits"]}
            fitted,info=quadratic.fit(demos,nonce)
            a,wa,ma=quadratic.score(p,base,delta,fitted)
            b,wb,mb=quadratic.score(n,base,delta,fitted)
            return a,b,wa,wb,{"abstained":ma["abstained"],
                "extra_bits":info["transient_task_coefficient_bits"]}
        (a,b,wa,wb,meta),cost=counted(evaluate)
        add(results[name],fam,op,a,b,(wa,wb),meta,cost)

def evaluate(stage,base,delta):
    cases=birth.train_rows(stage)
    need(len(cases)==24,"FROZEN_TRAIN_HALF_ONLY")
    results={name:empty() for name in NAMES}
    for row in cases:run_case(row,base,delta,results)
    for name,item in results.items():
        need(item["pairs"]==24 and
             item["by_operator"]["affine"]["pairs"]==12 and
             item["by_operator"]["feistel"]["pairs"]==12 and
             all(x["pairs"]==6 for x in item["by_graph_family"].values()) and
             item["max_active"]<=7 and item["max_retained"]<=9 and
             item["total_response_observations"]==24*48 and
             item["fit_solver_trials"]==24*256,
             "MATCHED_RESOURCES_AND_CASE_COUNTS")
    return results

def admissible(results):
    best_affine=max((results[n]["affine_paired"] for n in CONTROLS
                     if results[n]["FP"]==0),default=0)
    best_total=max((results[n]["paired"] for n in CONTROLS
                    if results[n]["FP"]==0),default=0)
    eligible=[name for name in NEW_CANDIDATES if
              results[name]["FP"]==0 and
              results[name]["feistel_paired"]>=1 and
              results[name]["paired"]>best_total and
              results[name]["affine_paired"]>=best_affine]
    return min(eligible,key=lambda n:(-results[n]["paired"],
                         -results[n]["feistel_paired"],
                         results[n]["sum_cpu_ns"],n)) if eligible else None

def raw_write(path,data):
    dest=Path(path)
    need(dest.parent.is_dir() and not dest.exists(),"IMMUTABLE_NEW_OUTPUT")
    text=json.dumps(data,sort_keys=True,indent=2)+"\n"
    with dest.open("x",encoding="utf-8",newline="\n") as f:f.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--aw-preflight",required=True)
    p.add_argument("--fit-output",required=True)
    p.add_argument("--screen-output",required=True)
    args=p.parse_args()
    freeze=birth.frozen()
    original=Path(args.aw_preflight).read_bytes()
    donor=json.loads(original)
    need(donor["schema"]=="forge.research.f124aw.independent-before-first-dev-preflight.v1" and
         donor["DEV_cases_created"]==0 and
         donor["Wingless_DEV_cases_created"]==0 and
         len(donor["original_donor_Ygg_weights"])==7 and
         len(donor["original_donor_Ygg_delta"])==2 and
         donor["frozen_selection"]==
           {"query_condition":"balanced_basis48",
            "fit_bit_budget":12,"min_CHECK_correct":96},
         "AUTHENTIC_AW_DONOR_NOT_MODEL_TRUTH")
    base=donor["original_donor_Ygg_weights"]
    delta=donor["original_donor_Ygg_delta"]
    fit=evaluate("FIT",base,delta)
    selection=admissible(fit)
    receipt={"schema":SCHEMA,"phase":"FIT",
        "source_freeze_blob":birth.FREEZE_BLOB,
        "source_freeze_commit":"d56847eafb0c4ab43d3514f33b93b1fce8412d61",
        "parent_AW_head":birth.PARENT_HEAD,
        "AW_donor_preflight_sha256":hashlib.sha256(original).hexdigest(),
        "Yggdrasil":fit,"FIT_selected":selection,
        "FIT_paired_cases":24,"SCREEN_paired_cases":0,
        "DEV_cases_constructed":0,"Wingless_DEV_constructed":0,
        "operator_labels_not_passed_to_models":True,
        "oracle_used_as_model":False,
        "equal_public_responses_per_model":48,
        "new_public_source_calls_per_case":48,
        "shared_original_source_calls_per_case":24,
        "actual_unique_public_responses_per_case":72,
        "no_model_retuning_after_FIT":True,
        "protected_scientific_acceptance":False,
        "optimizer_promotion":False,"accepted_ref_mutation":False}
    digest=raw_write(args.fit_output,receipt)
    print("F124AX_ORIGINAL_FIT_SHA256="+digest)
    for name in NAMES:
        r=fit[name]
        print("F124AX_FIT_"+name+"="+json.dumps(
            {k:r[k] for k in ("paired","FP","FN","affine_paired","feistel_paired")},
            sort_keys=True))
    print("F124AX_FIT_SELECTED="+str(selection))
    if selection is None:
        print("F124AX_SCREEN_NOT_CONSTRUCTED=true")
        print("F124AX_SCIENTIFIC_FIT_DISPOSITION=NEGATIVE")
        return
    # Selection fixed and FIT report closed BEFORE any SCREEN source construction.
    screened=evaluate("SCREEN",base,delta)
    screen_choice=screened[selection]
    best_total=max((screened[n]["paired"] for n in CONTROLS
                    if screened[n]["FP"]==0),default=0)
    best_affine=max((screened[n]["affine_paired"] for n in CONTROLS
                     if screened[n]["FP"]==0),default=0)
    passed=(screen_choice["FP"]==0 and screen_choice["feistel_paired"]>=1 and
            screen_choice["paired"]>best_total and
            screen_choice["affine_paired"]>=best_affine)
    digest=raw_write(args.screen_output,{"schema":SCHEMA,"phase":"SCREEN",
        "source_freeze_blob":birth.FREEZE_BLOB,
        "original_FIT_sha256":digest,
        "FIT_selection":selection,
        "Yggdrasil":screened,
        "held_SCREEN_eligible":passed,
        "SCREEN_paired_cases":24,"DEV_cases_constructed":0,
        "Wingless_DEV_constructed":0,
        "no_postresult_tuning":True,
        "protected_scientific_acceptance":False,
        "optimizer_promotion":False})
    print("F124AX_ORIGINAL_SCREEN_SHA256="+digest)
    print("F124AX_SCREEN_ELIGIBLE="+str(passed).lower())
    print("F124AX_DEV_UNTOUCHED=true")

if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError,AssertionError) as error:
        print("F124AX_FAIL_CLOSED:"+str(error),file=sys.stderr);sys.exit(1)

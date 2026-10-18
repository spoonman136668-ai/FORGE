"""F124-AY original source-new 24 FIT + held 24 SCREEN; exactly 48 queries/arm.

Frozen source/operator IDs live ONLY in evaluator. Model receives public
demos and graphs, never oracle key or operator. All 6 arms are evaluated on
the same source-new paired challenges. FIT chooses; SCREEN cannot retune.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,sys,time,tracemalloc
from pathlib import Path
import f124ay_train_source as source
import f124ay_learned_composition as learned
import f124av_informative_inverse as old_affine
import f124q_independent_binding as witness

SCHEMA="forge.research.f124ay.original-equal48-structural-composition-fit-screen.v1"
ARMS=(
 ("affine_basis48","balanced_basis48","AV_original_affine"),
 ("affine_random48","random48","AV_original_affine"),
 ("learned_roundkey_basis48","balanced_basis48","learned_two_round_keyed"),
 ("learned_roundkey_random48","random48","learned_two_round_keyed"),
 ("learned_roundtable_basis48","balanced_basis48","learned_public_round_table"),
 ("learned_roundtable_random48","random48","learned_public_round_table"))
def need(ok,name):source.need(ok,"ORIGINAL_SCREEN_"+name)
def meter(fn):
    gc.collect()
    tracemalloc.start()
    c=time.process_time_ns();w=time.perf_counter_ns()
    result=fn()
    peak=tracemalloc.get_traced_memory()[1]
    elapsed={"CPU_ns":time.process_time_ns()-c,
             "wall_ns":time.perf_counter_ns()-w,
             "peak_traced_Python_bytes":peak}
    tracemalloc.stop()
    return result,elapsed
def card():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "public_answers":0,"extra_public_answers":0,
            "query_CPU_ns":0,"model_CPU_ns":0,"model_wall_ns":0,
            "Python_peak_bytes":0,"trained_fit_round_evaluations":0,
            "max_additional_model_bits":0,"max_active":0,"max_retained":0,
            "abstained_graphs":0,"case_records":[],
            "by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                           "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in source.FAMILIES}}
def account(dst,row,a,b,wa,wb,da,db,qcost,mcost,modelinfo):
    seed,vec,fam,operator,nonce,pos,neg=row
    admit_pos=a>=0; admit_neg=b>=0
    opfamily="feistel" if operator.startswith("feistel_") else "affine"
    for s in (dst,dst["by_operator"][opfamily],dst["by_family"][fam]):
        s["pairs"]+=1
        s["paired"]+=int(admit_pos and not admit_neg)
        s["FP"]+=int(admit_neg)
        s["FN"]+=int(not admit_pos)
    dst["case_records"].append({
       "sha256":witness.digest([seed,list(vec),fam]),
       "family":fam,"operator_family":opfamily,
       "positive_accepted":admit_pos,"negative_accepted":admit_neg,
       "check_correct":modelinfo.get("check_correct"),
       "public_fit_bit_errors":modelinfo.get("fit_bit_errors")})
    dst["public_answers"]+=48
    dst["extra_public_answers"]+=24
    dst["query_CPU_ns"]+=qcost["CPU_ns"]
    dst["model_CPU_ns"]+=mcost["CPU_ns"]
    dst["model_wall_ns"]+=mcost["wall_ns"]
    dst["Python_peak_bytes"]=max(dst["Python_peak_bytes"],
                                 qcost["peak_traced_Python_bytes"],
                                 mcost["peak_traced_Python_bytes"])
    dst["trained_fit_round_evaluations"]+=modelinfo["fit_round_evaluations"]
    dst["max_additional_model_bits"]=max(dst["max_additional_model_bits"],
                                         modelinfo["additional_model_bits"])
    for w in (wa,wb):
        if w:
            dst["max_active"]=max(dst["max_active"],w.get("max_active",0))
            dst["max_retained"]=max(dst["max_retained"],w.get("max_retained",0))
    for diag in (da,db):
        if diag:dst["abstained_graphs"]+=int(diag.get("abstained",False))

def arm(rows,base,delta,name,condition,mode):
    need((name,condition,mode) in ARMS,"FROZEN_ONLY")
    d=card()
    for row in rows:
        seed,vec,fam,operator,nonce,pos,neg=row
        demos,qcost=meter(lambda:source.public48(
            seed,vec,operator,condition,pos["demos"]))
        def eval_public():
            if mode=="AV_original_affine":
                coeff,info=old_affine.fit(demos,nonce)
                check=old_affine.check(demos,coeff)
                a,wa,da=old_affine.score(pos,base,delta,coeff,info,check,12,96)
                b,wb,db=old_affine.score(neg,base,delta,coeff,info,check,12,96)
                modelinfo={"check_correct":check,
                           "fit_bit_errors":info["fit_bit_errors"],
                           "fit_round_evaluations":info["all_ransac_attempts"]*40*17,
                           "additional_model_bits":info["transient_task_coefficient_bits"]}
            else:
                fit=learned.train(demos,mode)
                check=learned.public_check(fit,demos)
                a,wa,da=learned.score(pos,base,delta,fit,demos,check)
                b,wb,db=learned.score(neg,base,delta,fit,demos,check)
                modelinfo={"check_correct":check,
                           "fit_bit_errors":fit["public_FIT_bit_errors"],
                           "fit_round_evaluations":fit["training_round_evaluations"],
                           "additional_model_bits":fit["parameters_bits_lower"]}
                need(not fit["operator_token_used"] and not fit["source_key_used"],
                     "MODEL_PUBLIC_ONLY")
            return a,b,wa,wb,da,db,modelinfo
        (a,b,wa,wb,da,db,info),mcost=meter(eval_public)
        account(d,row,a,b,wa,wb,da,db,qcost,mcost,info)
    need(d["pairs"]==24 and d["public_answers"]==1152 and
         d["extra_public_answers"]==576 and d["max_active"]<=7
         and d["max_retained"]<=9 and
         all(x["pairs"]==12 for x in d["by_operator"].values()) and
         all(x["pairs"]==6 for x in d["by_family"].values()),
         "EXACT_24_FOUR_FAMILY_7_9_LIMIT")
    return d

def select_only_fit(fit):
    best_baseline=max((fit[n]["paired"] for n in ("affine_basis48","affine_random48")
                       if fit[n]["FP"]==0),default=0)
    candidate=[name for name in ("learned_roundkey_basis48",
                                 "learned_roundkey_random48",
                                 "learned_roundtable_basis48",
                                 "learned_roundtable_random48")
               if fit[name]["FP"]==0 and
                  fit[name]["by_operator"]["feistel"]["paired"]>=1 and
                  fit[name]["paired"]>best_baseline]
    pick=min(candidate,key=lambda name:(
        -fit[name]["paired"],fit[name]["FN"],fit[name]["model_CPU_ns"],name)
        ) if candidate else None
    return pick,best_baseline

def run(base,delta):
    source.frozen()
    need(type(base) is list and type(delta) is list and
         len(base)==7 and len(delta)==2 and
         all(type(v) in (int,float) and math.isfinite(v) for v in base+delta),
         "ORIGINAL_BASE_UNCHANGED")
    fitrows=source.rows("FIT")
    fit={}
    for name,condition,mode in ARMS:
        fit[name]=arm(fitrows,base,delta,name,condition,mode)
    selected,fit_control=select_only_fit(fit)
    screenrows=source.rows("SCREEN")
    screen={}
    for name,condition,mode in ARMS:
        screen[name]=arm(screenrows,base,delta,name,condition,mode)
    held_control=max((screen[n]["paired"] for n in (
        "affine_basis48","affine_random48") if screen[n]["FP"]==0),default=0)
    science_ok=bool(selected and
                    screen[selected]["FP"]==0 and
                    screen[selected]["by_operator"]["feistel"]["paired"]>=1 and
                    screen[selected]["paired"]>held_control)
    return {
        "schema":SCHEMA,
        "original_source_freeze_git_blob":source.FREEZE_BLOB,
        "parent_AX_qualified_head":source.PARENT_SHA,
        "FIT_models":fit,"FIT_selected_before_held_SCREEN":selected,
        "FIT_best_equal48_affine_control":fit_control,
        "SCREEN_models":screen,
        "SCREEN_best_equal48_affine_control":held_control,
        "SCREEN_frozen_nonlinear_success":science_ok,
        "SCREEN_used_for_fit_or_reselection":False,
        "FIT_pair_count":24,"SCREEN_pair_count":24,
        "model_info_explicit":"Learned keyed-round function is structurally source-family aligned; not an operator-agnostic proof.",
        "resource_scope":{
            "original_active":7,"original_retained":9,
            "candidate_model_memory_outside_original_cells":True,
            "48_public_responses_matched_all_arms":True,
            "query_CPU_separate_from_model_CPU":True,
            "Python_alloc_peak_per_arm_traced":True,
            "OS_RSS_attributed_per_arm":False,
            "equal_computation_claim":False},
        "Ygg_DEV_generated":0,"Ygg_DEV_consumed":False,
        "Wingless_DEV_generated":0,"Wingless_DEV_consumed":False,
        "protected_first_use":False,
        "independent_science_acceptance":False,
        "optimizer_promotion":False,"production_activation":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True);p.add_argument("--delta",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    dest=Path(args.output)
    need(dest.parent.exists() and not dest.exists(),"ORIGINAL_APPEND_ONLY_RECEIPT")
    base=json.loads(Path(args.base).read_text())
    delta=json.loads(Path(args.delta).read_text())
    doc=run(base,delta)
    raw=json.dumps(doc,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as f:f.write(raw)
    print("F124AY_ORIGINAL_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124AY_FIT_ONLY_PICK="+str(doc["FIT_selected_before_held_SCREEN"]))
    print("F124AY_HELD_SCREEN_SUCCESS="+str(doc["SCREEN_frozen_nonlinear_success"]))
    for name,row in doc["SCREEN_models"].items():
        print("F124AY_SCREEN_"+name+"="+json.dumps({
            "paired":row["paired"],"FP":row["FP"],"FN":row["FN"],
            "Feistel_paired":row["by_operator"]["feistel"]["paired"],
            "query_count":row["public_answers"]},sort_keys=True))
    print("F124AY_NEW_DEV_UNCONSUMED=true")
if __name__=="__main__":
    try:main()
    except (TypeError,KeyError,ValueError,OSError,AssertionError,
            ArithmeticError) as exc:
        print("F124AY_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)

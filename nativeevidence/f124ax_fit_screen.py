"""F124-AX original FIT selection / held TRAIN-SCREEN on new Ygg source.

Six frozen exact-48-public-response models, same source each condition.
Selection is FIT only; SCREEN evaluated once, no model adaptation afterward.
No DEV source adapter and NO AW DEV data used for selection or fitting.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,platform,sys,time,tracemalloc
from pathlib import Path
import f124ax_train_source as source
import f124ax_nonlinear_public_inverse as new
import f124av_informative_inverse as affine
import f124ag_transition_models as ag
import f124q_independent_binding as q

SCHEMA="forge.research.f124ax.original-equal-budget-nonlinear-train-fit-screen.v1"
SPECS=(
 ("AV_original_affine_basis48","balanced_basis48","affine"),
 ("AV_original_affine_random48","random48","affine"),
 ("quadratic_public_inverse_basis48","balanced_basis48","quadratic_sparse"),
 ("quadratic_public_inverse_random48","random48","quadratic_sparse"),
 ("nearest_public_inverse_basis48","balanced_basis48","weighted_hamming"),
 ("nearest_public_inverse_random48","random48","weighted_hamming"))
def need(ok,tag):source.need(ok,"FIT_SCREEN_"+tag)

def measure(fn):
    gc.collect()
    tracemalloc.start()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    val=fn()
    _,peak=tracemalloc.get_traced_memory()
    cost={"cpu_ns":time.process_time_ns()-cpu,
          "wall_ns":time.perf_counter_ns()-wall,
          "Python_peak_traced_bytes":peak}
    tracemalloc.stop()
    return val,cost

def blank():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "positive_case_hashes":[],"case_outcomes":[],
            "max_active":0,"max_retained":0,"abstained_graphs":0,
            "public_queries":0,"extra_public_queries":0,
            "query_CPU_ns":0,"model_CPU_ns":0,"model_wall_ns":0,
            "peak_python_traced_bytes":0,"training_operations_lower":0,
            "inference_operations_lower":0,"task_model_bits_lower":0,
            "by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                           "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in source.FAMILIES}}
def record(card,row,a,b,w1,w2,details,querycost,modelcost):
    seed,vec,fam,op,nonce,p,n=row
    positive=a>=0; negative=b>=0
    family="affine" if op.startswith("affine_") else "feistel"
    for target in (card,card["by_operator"][family],card["by_family"][fam]):
        target["pairs"]+=1;target["paired"]+=int(positive and not negative)
        target["FP"]+=int(negative);target["FN"]+=int(not positive)
    cid=q.digest([seed,list(vec),fam])
    card["positive_case_hashes"].append(cid if positive else None)
    card["case_outcomes"].append({"case_sha256":cid,"family":fam,
                                 "operator_family":family,
                                 "positive_accepted":positive,
                                 "negative_accepted":negative})
    for w in (w1,w2):
        if w:
            card["max_active"]=max(card["max_active"],w.get("max_active",0))
            card["max_retained"]=max(card["max_retained"],w.get("max_retained",0))
    for d in details:
        if d:card["abstained_graphs"]+=int(d.get("abstained",False))
    card["public_queries"]+=48
    card["extra_public_queries"]+=24
    card["query_CPU_ns"]+=querycost["cpu_ns"]
    card["model_CPU_ns"]+=modelcost["cpu_ns"]
    card["model_wall_ns"]+=modelcost["wall_ns"]
    card["peak_python_traced_bytes"]=max(
        card["peak_python_traced_bytes"],
        querycost["Python_peak_traced_bytes"],
        modelcost["Python_peak_traced_bytes"])

def test_arm(rows,base,delta,name,condition,mode):
    need((name,condition,mode) in SPECS,"ONLY_SIX_FROZEN_CONFIGURATIONS")
    stats=blank()
    for row in rows:
        seed,vec,fam,op,nonce,p,n=row
        (demos,qcost)=measure(lambda:source.public48(
            seed,vec,op,condition,p["demos"]))
        def fit_and_evaluate():
            if mode=="affine":
                coeff,info=affine.fit(demos,nonce)
                checked=affine.check(demos,coeff)
                a,wa,da=affine.score(p,base,delta,coeff,info,checked,12,96)
                b,wb,db=affine.score(n,base,delta,coeff,info,checked,12,96)
                ops=info["all_ransac_attempts"]*40*17
                model_bits=info["transient_task_coefficient_bits"]
            else:
                learned=new.train(demos,mode)
                checked=new.public_check(learned,demos)
                a,wa,da=new.score(p,base,delta,learned,demos,checked)
                b,wb,db=new.score(n,base,delta,learned,demos,checked)
                ops=learned["fit_operations_lower"]
                model_bits=learned["extra_model_bits_lower"]
            return a,b,wa,wb,(da,db),ops,model_bits
        (a,b,wa,wb,details,ops,bits),mcost=measure(fit_and_evaluate)
        stats["training_operations_lower"]+=ops
        stats["task_model_bits_lower"]=max(
            stats["task_model_bits_lower"],bits)
        stats["inference_operations_lower"]+=sum(
            d.get("inference_operations_lower",0) for d in details)
        record(stats,row,a,b,wa,wb,details,qcost,mcost)
    need(stats["pairs"]==24 and stats["public_queries"]==24*48
         and stats["extra_public_queries"]==24*24
         and stats["max_active"]<=7 and stats["max_retained"]<=9
         and all(x["pairs"]==6 for x in stats["by_family"].values())
         and all(x["pairs"]==12 for x in stats["by_operator"].values()),
         "COMPLETE_EQUAL_QUERY_SAME_SOURCE")
    return stats

def choose(fit):
    candidates=[]
    for k,c in fit.items():
        if k.startswith(("quadratic","nearest")) and c["FP"]==0 and c["paired"]>=1:
            candidates.append(k)
    return min(candidates,key=lambda k:(
        -fit[k]["paired"],fit[k]["FN"],fit[k]["model_CPU_ns"],k)
        ) if candidates else None

def run(base,delta):
    source.frozen()
    need(len(base)==7 and len(delta)==2 and
         all(type(x) in (int,float) and math.isfinite(x) for x in base+delta),
         "ORIGINAL_DONOR_MODEL_WEIGHTS")
    fitrows=source.rows("FIT")
    screenrows=source.rows("SCREEN")
    need(not set((r[0],r[1]) for r in fitrows).intersection(
        (r[0],r[1]) for r in screenrows),"TRAIN_SPLIT_SOURCE_INDEPENDENT")
    fit={}
    for name,condition,mode in SPECS:
        fit[name]=test_arm(fitrows,base,delta,name,condition,mode)
    fixed_nonlinear=choose(fit)
    # Holdout is instantiated only after frozen FIT selection is completed.
    screen={}
    for name,condition,mode in SPECS:
        screen[name]=test_arm(screenrows,base,delta,name,condition,mode)
    strongest_affine=max((screen[k]["paired"] for k in (
        "AV_original_affine_basis48","AV_original_affine_random48")
        if screen[k]["FP"]==0),default=0)
    selected=screen.get(fixed_nonlinear) if fixed_nonlinear else None
    transfer=bool(selected and selected["FP"]==0 and
        selected["paired"]>strongest_affine and
        selected["by_operator"]["feistel"]["paired"]>=1)
    balanced=screen["AV_original_affine_basis48"]
    random=screen["AV_original_affine_random48"]
    active_query_better=(balanced["FP"]==0 and random["FP"]==0 and
                         balanced["paired"]>random["paired"])
    return {
        "schema":SCHEMA,
        "source_freeze_blob":source.FREEZE_BLOB,
        "qualified_parent_AW_HEAD":source.PARENT_HEAD,
        "FIT_case_count":24,"SCREEN_case_count":24,
        "FIT_candidates":fit,"FIT_selected_nonlinear":fixed_nonlinear,
        "SCREEN_candidates":screen,
        "SCREEN_selective_nonlinear_transfer":transfer,
        "SCREEN_equal_48_query_balanced_strictly_better_random":
            active_query_better,
        "SCREEN_strongest_equal_48_affine":strongest_affine,
        "SCREEN_used_to_select_or_retrain":False,
        "source_operator_used_by_models":False,
        "total_public_responses_per_arm_on_each_stage":24*48,
        "resource_interpretation":{
            "original_cognitive_cells":16,"active_cells":7,"retained_cells":9,
            "all_extra_model_bits_outside_original_cells":True,
            "same_host_fit_plus_inference_CPU_wall_traced_memory":True,
            "public_source_queries_timed_separately":True,
            "per_arm_OS_peak_RSS_attributed":False,
            "hardware_equalized":False,
            "matched_public_answers_across_all_six_arms":True},
        "Yggdrasil_DEV_generated":0,"Yggdrasil_DEV_consumed":False,
        "Wingless_DEV_generated":0,"Wingless_DEV_consumed":False,
        "protected_science_acceptance":False,
        "independent_science_acceptance":False,
        "optimizer_promotion":False,"production_activation":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-ygg",required=True)
    ap.add_argument("--delta-ygg",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"ORIGINAL_APPEND_ONLY_REPORT")
    base=json.loads(Path(a.base_ygg).read_text(encoding="utf-8"))
    delta=json.loads(Path(a.delta_ygg).read_text(encoding="utf-8"))
    doc=run(base,delta)
    raw=json.dumps(doc,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as f:f.write(raw)
    print("F124AX_ORIGINAL_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124AX_FIT_LOCKED_NONLINEAR="+str(doc["FIT_selected_nonlinear"]))
    print("F124AX_HELD_SCREEN_NONLINEAR_WIN="+str(
        doc["SCREEN_selective_nonlinear_transfer"]))
    print("F124AX_BALANCED_EQUAL48_BEATS_RANDOM_EQUAL48="+str(
        doc["SCREEN_equal_48_query_balanced_strictly_better_random"]))
    for n,s in doc["SCREEN_candidates"].items():
        print("F124AX_HELD_"+n+"="+json.dumps({
            k:s[k] for k in ("paired","FP","FN","public_queries")},
            sort_keys=True))
    print("F124AX_NEW_DEV_GENERATED=0")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,AssertionError,
            ArithmeticError) as e:
        print("F124AX_FAIL_CLOSED:"+str(e),file=sys.stderr);sys.exit(1)

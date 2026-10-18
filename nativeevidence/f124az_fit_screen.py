"""F124-AZ original fresh FIT+held SCREEN, eight equal-48 public-answer arms.

One preregistered task-wide public selection; FIT-only arm election, then
independently held SCREEN without retuning. Mandatory ORIGINAL affine
accepted-positive case-identity conservation, FP0 and Feistel sensitivity.
No DEV construction, and no imports of consumed AY research outcomes.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,sys,time,tracemalloc
from pathlib import Path
import f124az_train_source as source
import f124az_joint_public_inverse as joint
import f124av_informative_inverse as affine
import f124ay_learned_composition as feistel
import f124q_independent_binding as q

SCHEMA="forge.research.f124az.original-joint-inverse-equal48-first-TRAIN.v1"
SPECS=(("affine_balanced48","balanced_basis48","affine",None),
       ("affine_random48","random48","affine",None),
       ("feistel_balanced48","balanced_basis48","feistel",None),
       ("feistel_random48","random48","feistel",None),
       ("public_joint_balanced_margin0","balanced_basis48","joint",0),
       ("public_joint_random_margin0","random48","joint",0),
       ("public_joint_balanced_margin8","balanced_basis48","joint",8),
       ("public_joint_random_margin8","random48","joint",8))
def need(ok,name):source.need(ok,"ORIGINAL_TRAIN_"+name)

def measured(fn):
    gc.collect()
    tracemalloc.start()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    val=fn()
    peak=tracemalloc.get_traced_memory()[1]
    cost={"CPU_ns":time.process_time_ns()-cpu,
          "wall_ns":time.perf_counter_ns()-wall,
          "Python_tracemalloc_peak_bytes":peak}
    tracemalloc.stop()
    return val,cost

def fresh():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "accepted_positive_case_ids":[],"case_outcomes":[],
            "router_choices":{"affine":0,"feistel":0,"abstain":0},
            "by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                           "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in source.FAMILIES},
            "max_active":0,"max_retained":0,
            "public_response_calls":0,"extra_public_response_calls":0,
            "query_CPU_ns":0,"model_CPU_ns":0,"model_wall_ns":0,
            "peak_Python_bytes":0,"fit_operations_lower":0,
            "max_extra_model_bits_lower":0,
            "abstained_graphs":0}

def arm(rows,base,delta,name,query,mode,margin):
    need((name,query,mode,margin) in SPECS,"FROZEN_ARMS_ONLY")
    out=fresh()
    for seed,vec,fam,op,nonce,p,n in rows:
        demos,qcost=measured(lambda:source.public48(
            seed,vec,op,query,p["demos"]))
        def build_and_score():
            if mode=="affine":
                coeff,info=affine.fit(demos,nonce)
                checked=affine.check(demos,coeff)
                (a,wa,da)=affine.score(p,base,delta,coeff,info,checked,12,96)
                (b,wb,db)=affine.score(n,base,delta,coeff,info,checked,12,96)
                meta={"choice":"affine","ops":info["all_ransac_attempts"]*40*17,
                      "bits":info["transient_task_coefficient_bits"]}
            elif mode=="feistel":
                model=feistel.train(demos,"learned_two_round_keyed")
                checked=feistel.public_check(model,demos)
                (a,wa,da)=feistel.score(p,base,delta,model,demos,checked)
                (b,wb,db)=feistel.score(n,base,delta,model,demos,checked)
                meta={"choice":"feistel",
                      "ops":model["training_round_evaluations"],
                      "bits":model["parameters_bits_lower"]}
            else:
                model=joint.train(demos,nonce,margin)
                (a,wa,da)=joint.score(p,base,delta,model,demos)
                (b,wb,db)=joint.score(n,base,delta,model,demos)
                meta={"choice":model["choice"],
                      "ops":model["fit_operations_lower"],
                      "bits":model["extra_task_model_bits_lower"],
                      "affine_check":model["affine_check"],
                      "feistel_check":model["feistel_check"]}
            return a,b,wa,wb,da,db,meta
        (a,b,wa,wb,da,db,meta),mcost=measured(build_and_score)
        pos=a>=0;neg=b>=0
        identity=q.digest([seed,list(vec),fam])
        opfamily="affine" if op.startswith("affine_") else "feistel"
        for row in (out,out["by_operator"][opfamily],out["by_family"][fam]):
            row["pairs"]+=1
            row["paired"]+=int(pos and not neg)
            row["FP"]+=int(neg)
            row["FN"]+=int(not pos)
        if pos:out["accepted_positive_case_ids"].append(identity)
        out["case_outcomes"].append({
            "case_sha256":identity,"operator_family":opfamily,
            "family":fam,"positive_accepted":pos,
            "negative_accepted":neg,"route":meta["choice"],
            "model_public_check_affine":meta.get("affine_check"),
            "model_public_check_feistel":meta.get("feistel_check")})
        out["router_choices"][meta["choice"]]+=1
        out["public_response_calls"]+=48
        out["extra_public_response_calls"]+=24
        out["query_CPU_ns"]+=qcost["CPU_ns"]
        out["model_CPU_ns"]+=mcost["CPU_ns"]
        out["model_wall_ns"]+=mcost["wall_ns"]
        out["peak_Python_bytes"]=max(out["peak_Python_bytes"],
             qcost["Python_tracemalloc_peak_bytes"],
             mcost["Python_tracemalloc_peak_bytes"])
        out["fit_operations_lower"]+=meta["ops"]
        out["max_extra_model_bits_lower"]=max(
            out["max_extra_model_bits_lower"],meta["bits"])
        for w in (wa,wb):
            if w:
                out["max_active"]=max(out["max_active"],w.get("max_active",0))
                out["max_retained"]=max(out["max_retained"],w.get("max_retained",0))
        for diag in (da,db):
            if diag:out["abstained_graphs"]+=int(diag.get("abstained",False))
    need(out["pairs"]==24 and out["public_response_calls"]==24*48
         and out["extra_public_response_calls"]==24*24
         and out["max_active"]<=7 and out["max_retained"]<=9
         and all(v["pairs"]==12 for v in out["by_operator"].values())
         and all(v["pairs"]==6 for v in out["by_family"].values())
         and sum(out["router_choices"].values())==24,
         "EXACT_8_ARM_EQUAL48_AND_7_PLUS_9")
    return out

def matched_control(name):
    return "affine_balanced48" if "balanced" in name else "affine_random48"

def candidate_eligible(cards,name,strongest):
    c=cards[name]
    baseline=cards[matched_control(name)]
    retained=set(baseline["accepted_positive_case_ids"])
    positive=set(c["accepted_positive_case_ids"])
    return bool(c["FP"]==0 and c["by_operator"]["feistel"]["paired"]>=1
                and c["paired"]>strongest
                and retained.issubset(positive)),{
        "accepted_control_positive_count":len(retained),
        "preserved_control_positives":len(retained&positive),
        "all_control_positive_ids_preserved":retained.issubset(positive),
        "false_positives":c["FP"],
        "Feistel_paired":c["by_operator"]["feistel"]["paired"],
        "paired":c["paired"],"strongest_affine_paired":strongest}

def choose_fit(cards):
    strongest=max((cards[k]["paired"] for k in
        ("affine_balanced48","affine_random48")
        if cards[k]["FP"]==0),default=0)
    eligibility={}
    allowed=[]
    for name,_,mode,margin in SPECS:
        if mode=="joint":
            yes,detail=candidate_eligible(cards,name,strongest)
            eligibility[name]={"eligible":yes,**detail}
            if yes:allowed.append(name)
    pick=min(allowed,key=lambda k:(
        -cards[k]["paired"],cards[k]["model_CPU_ns"],k)) if allowed else None
    return pick,strongest,eligibility

def run(base,delta):
    source.frozen()
    need(type(base) is list and type(delta) is list
         and len(base)==7 and len(delta)==2
         and all(type(v) in (float,int) and math.isfinite(v)
                 for v in base+delta),"ORIGINAL_7_BASE_2_DELTA")
    fitrows=source.rows("FIT")
    fit={name:arm(fitrows,base,delta,name,query,mode,margin)
         for name,query,mode,margin in SPECS}
    selected,strongest,fit_elig=choose_fit(fit)
    heldrows=source.rows("SCREEN")
    need(not set((a[0],a[1]) for a in fitrows).intersection(
        (a[0],a[1]) for a in heldrows),"FROZEN_DISJOINT_SCREEN")
    screen={name:arm(heldrows,base,delta,name,query,mode,margin)
            for name,query,mode,margin in SPECS}
    screened,strongest_screen,screen_elig=choose_fit(screen)
    success=bool(selected and
                 screen_elig[selected]["eligible"])
    return {"schema":SCHEMA,"source_freeze_blob":source.FREEZE_BLOB,
            "original_AY_qualified_parent_head":source.PARENT_SHA,
            "FIT_models":fit,"FIT_selected_before_held_SCREEN":selected,
            "FIT_control_paired":strongest,
            "FIT_joint_eligibility":fit_elig,
            "SCREEN_models":screen,"SCREEN_control_paired":strongest_screen,
            "SCREEN_joint_eligibility":screen_elig,
            "SCREEN_diagnostic_best_eligible_not_selection":screened,
            "SCREEN_strict_frozen_joint_success":success,
            "SCREEN_did_not_retrain_or_respecify":True,
            "FIT_paired_cases":24,"SCREEN_paired_cases":24,
            "matched_48_public_responses_per_task":True,
            "original_cognitive_active":7,"original_cognitive_retained":9,
            "model_memory_extra_outside_cognitive_cells":True,
            "single_process_OS_RSS_arm_attribution":False,
            "equal_compute_budget_claim":False,
            "AY_consumed_results_as_training_input":False,
            "Ygg_DEV_generated":0,"Ygg_DEV_consumed":False,
            "Wingless_DEV_generated":0,"Wingless_DEV_consumed":False,
            "scientific_protected_acceptance":False,
            "optimizer_promotion":False,"production_activation":False}
def main():
    p=argparse.ArgumentParser()
    for field in ("base","delta","output"):
        p.add_argument("--"+field,required=True)
    x=p.parse_args();out=Path(x.output)
    need(out.parent.is_dir() and not out.exists(),"APPEND_ONLY_FIRST_ORIGINAL")
    result=run(json.loads(Path(x.base).read_text()),
               json.loads(Path(x.delta).read_text()))
    raw=json.dumps(result,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:f.write(raw)
    print("F124AZ_ORIGINAL_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124AZ_FIT_SELECTED="+str(result["FIT_selected_before_held_SCREEN"]))
    print("F124AZ_SCREEN_STRICT_SUCCESS="+str(result["SCREEN_strict_frozen_joint_success"]))
    for name,r in result["SCREEN_models"].items():
        print("F124AZ_SCREEN_"+name+"="+json.dumps({
            "paired":r["paired"],"FP":r["FP"],"FN":r["FN"],
            "Feistel_paired":r["by_operator"]["feistel"]["paired"],
            "public_calls":r["public_response_calls"]},sort_keys=True))
    print("F124AZ_NEW_DEV_CONSUMED=false")
if __name__=="__main__":
    try:main()
    except (OSError,KeyError,TypeError,ValueError,AssertionError,
            ArithmeticError) as e:
        print("F124AZ_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)

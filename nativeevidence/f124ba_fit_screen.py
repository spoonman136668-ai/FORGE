"""F124-BA one frozen TRAIN FIT decision, conditional held SCREEN if eligible.

Public query cost, extra model state and explicit CPU/wall/trace allocations
are counted per arm. Exact positive identity preservation is mandatory.
Never construct held SCREEN on a negative FIT. No DEV constructor exists.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,sys,time,tracemalloc
from pathlib import Path
import f124ba_train_source as source
import f124ba_public_confidence as confidence
import f124az_joint_public_inverse as joint
import f124av_informative_inverse as affine
import f124q_independent_binding as q

SCHEMA="forge.research.f124ba.original-confidence-new-train.v1"
CONTROLS=(("affine_balanced48","balanced_basis48","affine",None),
          ("affine_random48","random48","affine",None),
          ("joint_balanced_margin0","balanced_basis48","joint",None),
          ("joint_random_margin0","random48","joint",None))
CONFIGS=confidence.CONFIGS
NEW=tuple(("confidence_"+("balanced" if c[0]=="balanced_basis48" else "random")+
           "_check"+str(c[1])+"_row"+str(c[2])+"_gap"+str(c[3]),
           c[0],"confidence",c) for c in CONFIGS)
SPECS=CONTROLS+NEW
def need(ok,name):source.need(ok,"ORIGINAL_"+name)

def measured(fn):
    gc.collect();tracemalloc.start()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    ret=fn()
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    return ret,{"CPU_ns":time.process_time_ns()-cpu,
                "wall_ns":time.perf_counter_ns()-wall,
                "peak_Python_bytes":peak}

def fresh():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "accepted_positive_case_ids":[],"case_outcomes":[],
            "by_operator":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                           "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in source.FAMILIES},
            "router_choices":{"affine":0,"feistel":0,"abstain":0},
            "public_response_calls":0,"extra_public_response_calls":0,
            "query_CPU_ns":0,"model_CPU_ns":0,"model_wall_ns":0,
            "peak_Python_bytes":0,"fit_operations_lower":0,
            "max_extra_model_bits_lower":0,"extra_key_evaluations":0,
            "new_feistel_public_rejections":0,
            "max_active":0,"max_retained":0}

def arm(rows,base,delta,spec):
    name,query,mode,config=spec
    need(spec in SPECS,"ONLY_FROZEN_ARMS")
    out=fresh()
    for seed,vec,fam,op,nonce,p,n in rows:
        demos,qcost=measured(lambda:source.public48(
            seed,vec,op,query,p["demos"]))
        def model_predict():
            if mode=="affine":
                coeff,info=affine.fit(demos,nonce)
                checked=affine.check(demos,coeff)
                a,wa,_=affine.score(p,base,delta,coeff,info,checked,12,96)
                b,wb,_=affine.score(n,base,delta,coeff,info,checked,12,96)
                meta={"choice":"affine","bits":info["transient_task_coefficient_bits"],
                      "ops":info["all_ransac_attempts"]*40*17,
                      "extra_key":0,"reject":False,
                      "affine_CHECK":checked,"feistel_CHECK":None}
            elif mode=="joint":
                model=joint.train(demos,nonce,0)
                a,wa,_=joint.score(p,base,delta,model,demos)
                b,wb,_=joint.score(n,base,delta,model,demos)
                meta={"choice":model["choice"],"bits":model["extra_task_model_bits_lower"],
                      "ops":model["fit_operations_lower"],"extra_key":0,
                      "reject":False,"affine_CHECK":model["affine_check"],
                      "feistel_CHECK":model["feistel_check"]}
            else:
                model=confidence.train(demos,nonce,*config)
                a,wa,_=confidence.score(p,base,delta,model,demos)
                b,wb,_=confidence.score(n,base,delta,model,demos)
                rej=model["f124ba_confidence"]
                meta={"choice":model["choice"],"bits":model["extra_task_model_bits_lower"],
                      "ops":model["fit_operations_lower"],
                      "extra_key":rej["extra_key_fit_observation_evaluations"],
                      "reject":rej["feistel_public_rejection"],
                      "affine_CHECK":model["affine_check"],
                      "feistel_CHECK":model["feistel_check"],
                      "public_key_gap":rej["sourceblind_FIT_runnerup_gap"],
                      "per_CHECK_row":rej["public_CHECK_each"]}
            return a,b,wa,wb,meta
        (a,b,wa,wb,meta),cost=measured(model_predict)
        yes=a>=0;false_positive=b>=0
        case=q.digest([seed,list(vec),fam])
        family="affine" if op.startswith("affine_") else "feistel"
        for bucket in (out,out["by_operator"][family],out["by_family"][fam]):
            bucket["pairs"]+=1;bucket["paired"]+=int(yes and not false_positive)
            bucket["FP"]+=int(false_positive);bucket["FN"]+=int(not yes)
        if yes:out["accepted_positive_case_ids"].append(case)
        out["case_outcomes"].append({"case_sha256":case,"operator_family":family,
            "graph_family":fam,"positive_accepted":yes,
            "negative_accepted":false_positive,
            "route":meta["choice"],"affine_CHECK":meta["affine_CHECK"],
            "feistel_CHECK":meta["feistel_CHECK"],
            "feistel_public_rejected":meta["reject"],
            "public_key_gap":meta.get("public_key_gap"),
            "per_CHECK_row":meta.get("per_CHECK_row")})
        out["router_choices"][meta["choice"]]+=1
        out["public_response_calls"]+=48
        out["extra_public_response_calls"]+=24
        out["query_CPU_ns"]+=qcost["CPU_ns"]
        out["model_CPU_ns"]+=cost["CPU_ns"]
        out["model_wall_ns"]+=cost["wall_ns"]
        out["peak_Python_bytes"]=max(out["peak_Python_bytes"],
            qcost["peak_Python_bytes"],cost["peak_Python_bytes"])
        out["fit_operations_lower"]+=meta["ops"]
        out["max_extra_model_bits_lower"]=max(out["max_extra_model_bits_lower"],meta["bits"])
        out["extra_key_evaluations"]+=meta["extra_key"]
        out["new_feistel_public_rejections"]+=int(meta["reject"])
        for w in (wa,wb):
            if w:
                out["max_active"]=max(out["max_active"],w["max_active"])
                out["max_retained"]=max(out["max_retained"],w["max_retained"])
    need(out["pairs"]==24 and out["public_response_calls"]==1152 and
         out["extra_public_response_calls"]==576 and
         out["by_operator"]["affine"]["pairs"]==12
         and out["by_operator"]["feistel"]["pairs"]==12 and
         all(v["pairs"]==6 for v in out["by_family"].values()) and
         sum(out["router_choices"].values())==24 and
         out["max_active"]<=7 and out["max_retained"]<=9,
         "ORIGINAL_EQUAL_PUBLIC_BUDGET_AND_COGNITION")
    return out

def baseline(name):
    return "affine_balanced48" if "balanced" in name else "affine_random48"

def eligible(cards,name):
    target=cards[name]
    control=cards[baseline(name)]
    control_ids=set(control["accepted_positive_case_ids"])
    candidate_ids=set(target["accepted_positive_case_ids"])
    strongest=max((cards[k]["paired"] for k in ("affine_balanced48","affine_random48")
                   if cards[k]["FP"]==0),default=0)
    detail={"paired":target["paired"],"FP":target["FP"],
        "FN":target["FN"],"Feistel_paired":target["by_operator"]["feistel"]["paired"],
        "control_accepted_positive_cases":len(control_ids),
        "preserved_matched_affine_positives":len(control_ids&candidate_ids),
        "all_matched_control_positive_cases_preserved":control_ids.issubset(candidate_ids),
        "strongest_affine_control_paired":strongest}
    return bool(target["FP"]==0 and
        detail["Feistel_paired"]>=1 and
        target["paired"]>strongest and
        detail["all_matched_control_positive_cases_preserved"]),detail

def run(base,delta):
    source.frozen()
    need(type(base) is list and len(base)==7 and type(delta) is list
         and len(delta)==2 and all(type(x) in (float,int)
         and math.isfinite(x) for x in base+delta),"ORIGINAL_7_PLUS_2_DONOR_WEIGHTS")
    fitrows=source.rows("FIT")
    fit={spec[0]:arm(fitrows,base,delta,spec) for spec in SPECS}
    records={}
    candidates=[]
    for spec in NEW:
        name=spec[0]
        ok,detail=eligible(fit,name)
        records[name]=dict(detail,eligible=ok)
        if ok:candidates.append(name)
    chosen=min(candidates,key=lambda name:(
        -fit[name]["paired"],fit[name]["model_CPU_ns"],name)) if candidates else None
    result={"schema":SCHEMA,"frozen_source_blob":source.FREEZE_BLOB,
        "source_freeze_first_commit":"2e31e732ba2bce2ef850c8b3832fb2a4edb116fa",
        "parent_qualified_AZ_head":source.PARENT_SHA,
        "FIT_models":fit,"FIT_selection":chosen,"FIT_candidate_eligibility":records,
        "FIT_pairs":24,"SCREEN_pairs":0,"SCREEN_models":None,
        "SCREEN_elected_eligibility":None,"SCREEN_strict_success":False,
        "used_parent_AZ_FIT_or_SCREEN_for_training":False,
        "equal48_public_answers_per_task":True,
        "original_cognitive_active":7,"original_cognitive_retained":9,
        "extra_parameters_outside_cognitive_cells":True,
        "equal_compute_claim":False,"DEV_constructed":0,"Wingless_DEV_constructed":0,
        "protected_scientific_acceptance":False,"optimizer_promotion":False,
        "production_activation":False,"accepted_ref_mutation":False}
    if chosen is None:
        result["SCREEN_unconstructed_due_to_negative_FIT"]=True
        return result
    # FIT-only choice is frozen before any independent SCREEN source birth.
    held=source.rows("SCREEN")
    selected_name=next(x for x in NEW if x[0]==chosen)
    specs=CONTROLS[:2]+(selected_name,)
    screened={spec[0]:arm(held,base,delta,spec) for spec in specs}
    yes,detail=eligible(screened,chosen)
    result.update({"SCREEN_models":screened,"SCREEN_pairs":24,
                   "SCREEN_elected_eligibility":dict(detail,eligible=yes),
                   "SCREEN_strict_success":yes,
                   "SCREEN_unconstructed_due_to_negative_FIT":False})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True)
    p.add_argument("--delta",required=True)
    p.add_argument("--output",required=True)
    opt=p.parse_args();out=Path(opt.output)
    need(out.parent.is_dir() and not out.exists(),"NO_REUSE_OR_OVERWRITE_FIRST_FIT")
    d=run(json.loads(Path(opt.base).read_text()),
          json.loads(Path(opt.delta).read_text()))
    raw=(json.dumps(d,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(raw)
    print("F124BA_ORIGINAL_SCIENCE_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124BA_FIT_SELECTED="+str(d["FIT_selection"]))
    for name in d["FIT_models"]:
        x=d["FIT_models"][name]
        print("F124BA_FIT_"+name+"="+json.dumps({k:x[k] for k in ("paired","FP","FN",
        "new_feistel_public_rejections","model_CPU_ns")},sort_keys=True))
    print("F124BA_HELD_SCREEN_USED="+str(d["SCREEN_pairs"]>0).lower())
    print("F124BA_DEV_USED=false")
    print("F124BA_PROTECTED_ADMISSION=false")
if __name__=="__main__":
    try:main()
    except (OSError,KeyError,TypeError,ValueError,AssertionError,ArithmeticError) as e:
        print("F124BA_STOP:"+str(e),file=sys.stderr);sys.exit(1)

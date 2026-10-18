"""F124-BC original source-new 48-response matched hard-negative falsification.

No model-based source selection. A model gets identical public 48 observations
for positive, source-born negative, and model-blind oracle-confirmed one-bit
negative. If no one-bit candidate exists, fallback is marked and EXCLUDED
from hard-negative numerator, not silently relabeled a success. Held SCREEN
is opened only by the preregistered challenge-coverage + baseline-FP rule.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,sys,time,tracemalloc
from pathlib import Path
import f124bc_hard_negative_source as source
import f124az_joint_public_inverse as joint
import f124av_informative_inverse as affine
import f124q_independent_binding as q

SCHEMA="forge.research.f124bc.original-source-new-hard-negative-falsification.v1"
ARMS=(("affine_balanced48","balanced_basis48","affine"),
      ("affine_random48","random48","affine"),
      ("joint_balanced48","balanced_basis48","joint"),
      ("joint_random48","random48","joint"))
def need(ok,key):source.need(ok,"FALSIFICATION_"+key)

def measured(fn):
    gc.collect();tracemalloc.start()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    out=fn()
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    return out,{"CPU_ns":time.process_time_ns()-cpu,
                "wall_ns":time.perf_counter_ns()-wall,
                "Python_peak_bytes":peak}

def blank():
    return {"pairs":0,"positive_accepted":0,"original_negative_FP":0,
         "hard_negative_eligible_cases":0,"hard_negative_FP":0,
         "fallback_negative_cases":0,"fallback_negative_FP":0,
         "paired_original":0,"paired_hard":0,
         "positive_case_ids":[],"source_near_miss_case_ids":[],
         "case_outcomes":[],"model_CPU_ns":0,"model_wall_ns":0,
         "public_query_CPU_ns":0,"Python_peak_bytes":0,
         "max_task_coefficient_bits_lower":0,
         "additional_hard_negative_score_runs":0,
         "original_cognition_max_active":0,"original_cognition_max_retained":0,
         "by_operator":{"affine":{"pairs":0,"hard_cases":0,"hard_FP":0,"positive_accepted":0},
                        "feistel":{"pairs":0,"hard_cases":0,"hard_FP":0,"positive_accepted":0}},
         "by_graph_family":{f:{"pairs":0,"hard_cases":0,"hard_FP":0}
                              for f in source.FAMILIES}}

def arm(cases,base,delta,spec):
    name,query,kind=spec
    need(spec in ARMS,"ONLY_FROZEN_ORIGINAL_MODELS")
    out=blank()
    for seed,vec,fam,op,nonce,p,n,hard,meta in cases:
        demos,qcost=measured(lambda:source.public48(seed,vec,op,query,p["demos"]))
        need(p["demos"]==n["demos"]==hard["demos"],
             "IDENTICAL_PUBLIC_SUPPORT_ALL_LABELS")
        def classify():
            if kind=="affine":
                coeff,info=affine.fit(demos,nonce)
                checked=affine.check(demos,coeff)
                def single(g):
                    return affine.score(g,base,delta,coeff,info,checked,12,96)
                bits=info["transient_task_coefficient_bits"]
            else:
                model=joint.train(demos,nonce,0)
                def single(g):return joint.score(g,base,delta,model,demos)
                bits=model["extra_task_model_bits_lower"]
            pos,wp,_=single(p)
            neg,wn,_=single(n)
            near,wh,_=single(hard)
            return pos,neg,near,(wp,wn,wh),bits
        (positive,negative,challenged,works,bits),cost=measured(classify)
        yes=positive>=0;origFP=negative>=0;nearFP=challenged>=0
        ishard=meta["hard"]
        key=q.digest([seed,list(vec),fam])
        family="affine" if op.startswith("affine_") else "feistel"
        out["pairs"]+=1;out["positive_accepted"]+=int(yes)
        out["original_negative_FP"]+=int(origFP)
        out["hard_negative_eligible_cases"]+=int(ishard)
        out["hard_negative_FP"]+=int(ishard and nearFP)
        out["fallback_negative_cases"]+=int(not ishard)
        out["fallback_negative_FP"]+=int(not ishard and nearFP)
        out["paired_original"]+=int(yes and not origFP)
        out["paired_hard"]+=int(yes and not nearFP)
        if yes:out["positive_case_ids"].append(key)
        if ishard:out["source_near_miss_case_ids"].append(key)
        d=out["by_operator"][family]
        d["pairs"]+=1;d["hard_cases"]+=int(ishard)
        d["hard_FP"]+=int(ishard and nearFP)
        d["positive_accepted"]+=int(yes)
        f=out["by_graph_family"][fam]
        f["pairs"]+=1;f["hard_cases"]+=int(ishard)
        f["hard_FP"]+=int(ishard and nearFP)
        out["case_outcomes"].append({
            "case_id":key,"seed":seed,"vector":list(vec),"operator_family":family,
            "graph_family":fam,"positive_accepted":yes,
            "original_negative_accepted":origFP,
            "challenger_negative_accepted":nearFP,
            "valid_one_bit_hard_source":ishard,
            "oracle_source_probes":meta["source_oracle_probes"],
            "one_bit_edge":meta["edit_edge_index"],
            "one_bit_field":meta["edit_field"],"one_bit_index":meta["edit_bit"]})
        out["model_CPU_ns"]+=cost["CPU_ns"]
        out["model_wall_ns"]+=cost["wall_ns"]
        out["public_query_CPU_ns"]+=qcost["CPU_ns"]
        out["Python_peak_bytes"]=max(out["Python_peak_bytes"],
              cost["Python_peak_bytes"],qcost["Python_peak_bytes"])
        out["max_task_coefficient_bits_lower"]=max(out["max_task_coefficient_bits_lower"],bits)
        out["additional_hard_negative_score_runs"]+=1
        for work in works:
            if work:
                out["original_cognition_max_active"]=max(out["original_cognition_max_active"],work["max_active"])
                out["original_cognition_max_retained"]=max(out["original_cognition_max_retained"],work["max_retained"])
    need(out["pairs"]==24 and
         out["hard_negative_eligible_cases"]+out["fallback_negative_cases"]==24
         and len(out["case_outcomes"])==24
         and out["additional_hard_negative_score_runs"]==24
         and all(v["pairs"]==12 for v in out["by_operator"].values())
         and all(v["pairs"]==6 for v in out["by_graph_family"].values())
         and out["original_cognition_max_active"]<=7
         and out["original_cognition_max_retained"]<=9,
         "ORIGINAL_SAME_INFO_AND_COGNITION_LIMITS")
    return out

def run(base,delta):
    source.frozen()
    need(type(base) is list and len(base)==7
         and type(delta) is list and len(delta)==2
         and all(type(v) in (int,float) and math.isfinite(v)
                 for v in base+delta),"AUTHENTIC_DONOR_BUT_NOT_SCIENCE_LABELS")
    started=time.process_time_ns()
    rows=source.rows("FIT")
    source_cpu=time.process_time_ns()-started
    coverage=sum(r[8]["hard"] for r in rows)
    checks=sum(r[8]["source_oracle_probes"] for r in rows)
    fit={spec[0]:arm(rows,base,delta,spec) for spec in ARMS}
    need(all(r["hard_negative_eligible_cases"]==coverage for r in fit.values()),
         "IDENTICAL_ORIGINAL_HARD_NEGATIVE_CASES")
    base_with_hard_FPs=[name for name in ("joint_balanced48","joint_random48")
                        if fit[name]["hard_negative_FP"]>0]
    open_screen=(coverage>=18 and bool(base_with_hard_FPs))
    result={"schema":SCHEMA,"frozen_blob":source.FREEZE_BLOB,
       "first_frozen_commit":source.FIRST_COMMIT,
       "qualified_parent_archival_head":source.PARENT,
       "FIT_pairs":24,"FIT_hard_source_count":coverage,
       "FIT_hard_source_coverage":coverage/24,
       "FIT_source_oracle_probes":checks,"FIT_source_construction_CPU_ns":source_cpu,
       "one_bit_model_blind_learner_independent":True,
       "FIT_models":fit,"FIT_existing_joint_has_hard_negative_FP":bool(base_with_hard_FPs),
       "FIT_joint_conditions_with_hard_negative_FP":base_with_hard_FPs,
       "held_SCREEN_opened_by_frozen_coverage_and_FP_rule":open_screen,
       "SCREEN_pairs":0,"SCREEN_hard_source_count":0,"SCREEN_models":None,
       "new_model_elected":None,"protected_DEV_constructed":0,
       "Wingless_DEV_constructed":0,"scientific_protected_acceptance":False,
       "optimizer_promotion":False,"production_activation":False,
       "accepted_ref_mutation":False,"source_positive_ids_not_used_for_candidate_fitting":True,
       "equal_compute_claim":False}
    if open_screen:
        held=source.rows("SCREEN")
        result["SCREEN_pairs"]=24
        result["SCREEN_hard_source_count"]=sum(r[8]["hard"] for r in held)
        result["SCREEN_models"]={spec[0]:arm(held,base,delta,spec) for spec in ARMS}
    else:result["SCREEN_not_constructed_due_to_frozen_rule"]=True
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("base","delta","output"):p.add_argument("--"+key,required=True)
    args=p.parse_args()
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"SINGLE_IMMUTABLE_ORIGINAL")
    data=run(json.loads(Path(args.base).read_text()),json.loads(Path(args.delta).read_text()))
    raw=(json.dumps(data,indent=2,sort_keys=True)+"\n").encode()
    with out.open("xb") as f:f.write(raw)
    print("F124BC_ORIGINAL_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124BC_FIT_HARD_CASES="+str(data["FIT_hard_source_count"]))
    print("F124BC_FIT_SOURCE_ORACLE_PROBES="+str(data["FIT_source_oracle_probes"]))
    for name,r in data["FIT_models"].items():
        print("F124BC_FIT_"+name+"="+json.dumps({
           k:r[k] for k in ("positive_accepted","original_negative_FP",
          "hard_negative_eligible_cases","hard_negative_FP",
          "fallback_negative_cases","paired_original")},sort_keys=True))
    print("F124BC_SCREEN_OPENED="+str(data["SCREEN_pairs"]>0).lower())
    print("F124BC_NO_MODEL_PROMOTION=true")
    print("F124BC_DEV_UNTOUCHED=true")
if __name__=="__main__":
    try:main()
    except (OSError,KeyError,ValueError,TypeError,ArithmeticError,AssertionError) as exc:
        print("F124BC_FAIL_CLOSED:"+str(exc),file=sys.stderr);sys.exit(1)

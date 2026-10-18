"""F124-BD original frozen hard-negative causal-certificate science.

Ten same-48-response arms. FIT selects ONLY if a new PUBLIC path certificate
eliminates matched joint hard-negative false positives while retaining every
positive acceptance, original-negative rejection, and Feistel sensitivity.
SCREEN is never born if FIT fails. No DEV source constructor.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,sys,time,tracemalloc
from pathlib import Path
import f124bd_source_only as source
import f124bd_public_path_witness as witness
import f124az_joint_public_inverse as joint
import f124av_informative_inverse as affine
import f124q_independent_binding as q

SCHEMA="forge.research.f124bd.original-source-new-public-path-certificate.v1"
ARMS=(("affine_balanced48","balanced_basis48","affine",None),
      ("affine_random48","random48","affine",None),
      ("joint_balanced48","balanced_basis48","joint",None),
      ("joint_random48","random48","joint",None),
      ("witness_balanced_exact","balanced_basis48","witness","exact0"),
      ("witness_balanced_relaxed","balanced_basis48","witness","tolerant1"),
      ("witness_balanced_adaptive","balanced_basis48","witness","public_adaptive"),
      ("witness_random_exact","random48","witness","exact0"),
      ("witness_random_relaxed","random48","witness","tolerant1"),
      ("witness_random_adaptive","random48","witness","public_adaptive"))
BASELINE=ARMS[:4]
NEW=ARMS[4:]
def need(ok,tag):source.need(ok,"ORIGINAL_"+tag)

def measured(fn):
    gc.collect();tracemalloc.start()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    result=fn()
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    return result,{"CPU_ns":time.process_time_ns()-cpu,
                   "wall_ns":time.perf_counter_ns()-wall,
                   "Python_peak_bytes":peak}

def fresh():
    return {"cases":0,"positive":0,"original_FP":0,
        "hard_cases":0,"hard_FP":0,"fallback_cases":0,"fallback_FP":0,
        "paired_original":0,"paired_hard":0,
        "accepted_positive_case_ids":[],"accepted_Feistel_positive_case_ids":[],
        "case_outcomes":[],
        "by_operator":{"affine":{"cases":0,"positives":0,"hard_FP":0},
                       "feistel":{"cases":0,"positives":0,"hard_FP":0}},
        "by_graph_family":{fam:{"cases":0,"hard_FP":0} for fam in source.FAMILIES},
        "public_observations_total":0,"extra_query_responses":0,
        "public_query_CPU_ns":0,"model_CPU_ns":0,"model_wall_ns":0,
        "Python_peak_bytes":0,"extra_witness_scans":0,
        "extra_witness_bit_compares":0,"witness_searched_graphs":0,
        "positive_witness_vetoes":0,"negative_witness_vetoes":0,
        "hard_negative_witness_vetoes":0,
        "max_graph_decode_bits_lower":0,"max_frontier_bits_lower":0,
        "model_parameter_bits_lower":0,
        "max_cognitive_active":0,"max_cognitive_retained":0}

def evaluate(rows,base,delta,arm):
    name,query,kind,policy=arm
    need(arm in ARMS,"FROZEN_ARMS_ONLY")
    out=fresh()
    for seed,vec,fam,op,nonce,p,n,h,meta in rows:
        demos,qcost=measured(lambda:source.public48(seed,vec,op,query,p["demos"]))
        need(p["demos"]==n["demos"]==h["demos"],
             "SAME_PUBLIC_48_FOR_POS_NEG_AND_HARD")
        def model_task():
            if kind=="affine":
                coeff,info=affine.fit(demos,nonce)
                checked=affine.check(demos,coeff)
                def predict(g):return affine.score(g,base,delta,coeff,info,checked,12,96)
                cost_bits=info["transient_task_coefficient_bits"]
            else:
                fit=joint.train(demos,nonce,0)
                if kind=="joint":
                    def predict(g):return joint.score(g,base,delta,fit,demos)
                else:
                    def predict(g):return witness.score(g,base,delta,fit,demos,policy)
                cost_bits=fit["extra_task_model_bits_lower"]
            return [predict(g) for g in (p,n,h)],cost_bits
        (preds,costbits),cost=measured(model_task)
        (pv,pwork,pdiag),(nv,nwork,ndiag),(hv,hwork,hdiag)=preds
        positive=pv>=0;ordinary_fp=nv>=0;hard_fp=hv>=0
        case=q.digest([seed,list(vec),fam])
        family="affine" if op.startswith("affine_") else "feistel"
        ishard=bool(meta["hard"])
        out["cases"]+=1;out["positive"]+=int(positive)
        out["original_FP"]+=int(ordinary_fp)
        out["hard_cases"]+=int(ishard)
        out["hard_FP"]+=int(ishard and hard_fp)
        out["fallback_cases"]+=int(not ishard)
        out["fallback_FP"]+=int(not ishard and hard_fp)
        out["paired_original"]+=int(positive and not ordinary_fp)
        out["paired_hard"]+=int(positive and not hard_fp)
        if positive:
            out["accepted_positive_case_ids"].append(case)
            if family=="feistel":out["accepted_Feistel_positive_case_ids"].append(case)
        out["by_operator"][family]["cases"]+=1
        out["by_operator"][family]["positives"]+=int(positive)
        out["by_operator"][family]["hard_FP"]+=int(ishard and hard_fp)
        out["by_graph_family"][fam]["cases"]+=1
        out["by_graph_family"][fam]["hard_FP"]+=int(ishard and hard_fp)
        for k,diag in enumerate((pdiag,ndiag,hdiag)):
            out["witness_searched_graphs"]+=int(diag.get("certificate_searched",False))
            out["extra_witness_scans"]+=diag.get("public_edge_scans",0)
            out["extra_witness_bit_compares"]+=diag.get("public_bit_comparisons",0)
            out["max_graph_decode_bits_lower"]=max(out["max_graph_decode_bits_lower"],
                diag.get("additional_16bit_inverse_graph_decoding",0))
            out["max_frontier_bits_lower"]=max(out["max_frontier_bits_lower"],
                diag.get("extra_frontier_bits",0))
            if diag.get("veto",False):
                if k==0:out["positive_witness_vetoes"]+=1
                elif k==1:out["negative_witness_vetoes"]+=1
                else:out["hard_negative_witness_vetoes"]+=1
        out["case_outcomes"].append({"case_id":case,
           "operator_family":family,"graph_family":fam,
           "source_true_one_bit_negative":ishard,
           "positive_accepted":positive,"ordinary_negative_FP":ordinary_fp,
           "hard_negative_FP":hard_fp,
           "veto_positive":pdiag.get("veto",False),
           "veto_original_negative":ndiag.get("veto",False),
           "veto_hard_negative":hdiag.get("veto",False),
           "public_radius_positive":pdiag.get("radius"),
           "public_radius_hard":hdiag.get("radius")})
        out["public_observations_total"]+=48
        out["extra_query_responses"]+=24
        out["public_query_CPU_ns"]+=qcost["CPU_ns"]
        out["model_CPU_ns"]+=cost["CPU_ns"]
        out["model_wall_ns"]+=cost["wall_ns"]
        out["Python_peak_bytes"]=max(out["Python_peak_bytes"],qcost["Python_peak_bytes"],cost["Python_peak_bytes"])
        out["model_parameter_bits_lower"]=max(out["model_parameter_bits_lower"],costbits)
        for w in (pwork,nwork,hwork):
            if w:
                out["max_cognitive_active"]=max(out["max_cognitive_active"],w["max_active"])
                out["max_cognitive_retained"]=max(out["max_cognitive_retained"],w["max_retained"])
    need(out["cases"]==24 and out["public_observations_total"]==24*48
         and out["extra_query_responses"]==24*24
         and out["hard_cases"]+out["fallback_cases"]==24
         and all(v["cases"]==12 for v in out["by_operator"].values())
         and all(v["cases"]==6 for v in out["by_graph_family"].values())
         and out["max_cognitive_active"]<=7 and out["max_cognitive_retained"]<=9,
         "EQUAL_PUBLIC_BUDGET_AND_HARD_COGNITION")
    return out

def matched(name):
    return "joint_balanced48" if "balanced" in name else "joint_random48"

def eligibility(all_models,name,hard_coverage):
    pred=all_models[name];baseline=all_models[matched(name)]
    positives=set(pred["accepted_positive_case_ids"])
    previous=set(baseline["accepted_positive_case_ids"])
    old_feistel=set(baseline["accepted_Feistel_positive_case_ids"])
    new_feistel=set(pred["accepted_Feistel_positive_case_ids"])
    fp_drop=baseline["hard_FP"]-pred["hard_FP"]
    ok=(hard_coverage>=18 and baseline["hard_FP"]>0 and
        pred["hard_FP"]==0 and pred["original_FP"]==0
        and fp_drop>0 and pred["positive"]==baseline["positive"]
        and previous==positives and old_feistel==new_feistel)
    return {"eligible":ok,
            "matched_original_joint":matched(name),
            "source_hard_count":hard_coverage,
            "matched_joint_positive_count":baseline["positive"],
            "candidate_positive_count":pred["positive"],
            "matched_joint_hard_FP":baseline["hard_FP"],
            "candidate_hard_FP":pred["hard_FP"],
            "strict_hard_FP_reduction":fp_drop,
            "matched_joint_Feistel_positive_ids":len(old_feistel),
            "candidate_Feistel_positive_ids":len(new_feistel),
            "joint_positive_ids_preserved":previous==positives,
            "Feistel_positive_ids_preserved":old_feistel==new_feistel,
            "candidate_original_negative_FP":pred["original_FP"]}

def run(base,delta):
    source.frozen()
    need(type(base) is list and len(base)==7 and
         type(delta) is list and len(delta)==2 and
         all(type(x) in (int,float) and math.isfinite(x) for x in base+delta),
         "AUTHENTIC_DONOR_SHAPE")
    fit_rows=source.rows("FIT")
    hard_count=sum(row[8]["hard"] for row in fit_rows)
    probes=sum(row[8]["source_oracle_probes"] for row in fit_rows)
    fit={arm[0]:evaluate(fit_rows,base,delta,arm) for arm in ARMS}
    need(all(x["hard_cases"]==hard_count for x in fit.values()),
         "INDEPENDENT_SAME_HARD_SOURCE_IDENTITY")
    choices={arm[0]:eligibility(fit,arm[0],hard_count) for arm in NEW}
    accepted=[key for key,val in choices.items() if val["eligible"]]
    chosen=min(accepted,key=lambda name:(
        fit[name]["model_CPU_ns"],name)) if accepted else None
    result={"schema":SCHEMA,"source_freeze_blob":source.FREEZE_BLOB,
        "source_first_commit":source.FIRST_FREEZE_COMMIT,
        "parent_archived_head":source.PARENT,
        "FIT_pairs":24,"FIT_hard_cases":hard_count,
        "FIT_source_oracle_probes":probes,"FIT_models":fit,
        "FIT_eligibility":choices,"FIT_selected":chosen,
        "SCREEN_pairs":0,"SCREEN_models":None,
        "SCREEN_elected_eligibility":None,"SCREEN_strict_success":False,
        "source_oracle_not_available_in_model":True,
        "old_BC_results_not_used_as_model_input":True,
        "same_48_public_responses_per_arm":True,
        "original_Ygg_active":7,"original_Ygg_retained":9,
        "equal_compute_claim":False,"DEV_constructed":0,
        "Wingless_DEV_constructed":0,"protected_science_acceptance":False,
        "optimizer_promotion":False,"production_activation":False,
        "accepted_ref_mutation":False}
    if chosen is None:
        result["SCREEN_not_constructed_due_to_negative_FIT"]=True
        return result
    # Strictly unchanged FIT selected policy, and only matched baseline.
    held=source.rows("SCREEN")
    elected=next(arm for arm in NEW if arm[0]==chosen)
    base_control=next(arm for arm in BASELINE if arm[0]==matched(chosen))
    screen={arm[0]:evaluate(held,base,delta,arm)
            for arm in (base_control,elected)}
    ok=eligibility(screen,chosen,
                  sum(row[8]["hard"] for row in held))
    result.update({"SCREEN_pairs":24,"SCREEN_models":screen,
        "SCREEN_elected_eligibility":ok,"SCREEN_strict_success":ok["eligible"],
        "SCREEN_not_constructed_due_to_negative_FIT":False})
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("base","delta","output"):p.add_argument("--"+name,required=True)
    opts=p.parse_args()
    path=Path(opts.output)
    need(path.parent.is_dir() and not path.exists(),"ORIGINAL_NEW_OUTPUT_ONLY")
    result=run(json.loads(Path(opts.base).read_text()),
               json.loads(Path(opts.delta).read_text()))
    raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with path.open("xb") as f:f.write(raw)
    print("F124BD_FIRST_ORIGINAL_JSON_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124BD_FIT_SOURCE_HARD_NEGATIVES="+str(result["FIT_hard_cases"]))
    print("F124BD_FIT_SELECTED="+str(result["FIT_selected"]))
    for name,out in result["FIT_models"].items():
        print("F124BD_FIT_"+name+"="+json.dumps({
          k:out[k] for k in ("positive","original_FP","hard_FP",
                            "positive_witness_vetoes","hard_negative_witness_vetoes")},sort_keys=True))
    print("F124BD_SCREEN_OPENED="+str(result["SCREEN_pairs"]>0).lower())
    print("F124BD_DEV_UNTOUCHED=true")
    print("F124BD_PROTECTED_PROMOTION=false")
if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,OSError,AssertionError,ArithmeticError) as e:
        print("F124BD_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)

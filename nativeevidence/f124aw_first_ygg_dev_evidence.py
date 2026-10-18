"""F124-AW original Ygg-only DEV first-use and honest resource accounting.

This evaluator is separate from the independent TRAIN preflight. Exactly one
AV FIT-frozen configuration runs on all 48 fresh paired Ygg DEV cases. All
unchanged source-blind controls run on the SAME cases. The original graph
inverse remains evaluator-only and is computed after source-blind outputs.
No task results can retune, reseed or select another model. No Wingless calls.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,platform,sys,time,tracemalloc
from pathlib import Path
import f124aw_original_first_dev_source as born
import f124av_informative_inverse as model
import f124av_fit_screen as previous
import f124as_noisy_inverse as as_original
import f124ao_public_relation_learner as ao_original
import f124ag_transition_models as ag
import f124q_independent_binding as q
import f124w_hop_trace_indexed as witness

SCHEMA="forge.research.f124aw.authentic-first-ygg-dev-original-outcome.v1"
ORIGINAL_AV_SHA="f7cbfc844e64510a172a4144bd90a56a37ec6f76b805e5b39cb2bf953e40641d"
LOCKED={"query_condition":"balanced_basis48","fit_bit_budget":12,
        "min_CHECK_correct":96}
def need(ok,key):born.need(ok,"REPORT_"+key)

def preflight(original_av,original_refs):
    p=born.frozen()
    need(witness.blob(model.__file__)==born.AV_MODEL_BLOB,
         "IMMUTABLE_SELECTED_LEARNER_SOURCE")
    raw=Path(original_av).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==ORIGINAL_AV_SHA,
         "ORIGINAL_AV_RAW_BYTES")
    old=json.loads(raw)
    selected=old["Yggdrasil"]
    need(old["schema"]=="forge.research.f124av.fresh-public-query-inverse-handoff-train.v1"
         and old["preimplementation_freeze_blob"]==
            "d27f98324c348ce3a8b113df9caa0f9be74b286f"
         and old["original_parent_head"]==
             "c5cdb9ba55772b4b69a2534dd48cfc8b7abe20b2"
         and selected["FIT_selection"]==LOCKED
         and selected["TRAIN_SCREEN"]["candidates"][0]["config"]==LOCKED
         and selected["TRAIN_SCREEN"]["candidates"][0]["results"]["paired"]==9
         and selected["TRAIN_SCREEN"]["candidates"][0]["results"]["FP"]==0
         and selected["SCREEN_eligible"] is True
         and old["Wingless"]["FIT_selection"] is None
         and old["both_new_DEV_generated"]==0 and
         old["both_new_DEV_consumed"] is False
         and not old["scientific_acceptance"] and not old["optimizer_promotion"]
         and p["fixed_model"]["original_SCREEN"]["paired"]==9
         and p["lineage"]["AV_original_authentic_science_sha256"]==ORIGINAL_AV_SHA
         and p["fixed_model"]["query_condition"]==LOCKED["query_condition"]
         and p["fixed_model"]["fit_bit_budget"]==LOCKED["fit_bit_budget"]
         and p["fixed_model"]["min_CHECK_correct"]==LOCKED["min_CHECK_correct"],
         "ONLY_GENUINELY_ADMITTED_FIT_FROZEN_SINGLE_CANDIDATE")
    # Reauthenticate the ORIGINAL historical donor weights independently.
    base,delta=previous.parent.lineage(*original_refs)
    need(len(base["Yggdrasil"])==7 and len(delta["Yggdrasil"])==2,
         "ORIGINAL_DONOR_WEIGHTS")
    return base["Yggdrasil"],delta["Yggdrasil"]

def measure(fn):
    gc.collect()
    tracemalloc.start()
    start_wall=time.perf_counter_ns()
    start_cpu=time.process_time_ns()
    result=fn()
    cpu=time.process_time_ns()-start_cpu
    wall=time.perf_counter_ns()-start_wall
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result,{"cpu_ns":cpu,"wall_ns":wall,
                    "peak_python_allocated_bytes":peak}

def fresh():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,"max_active":0,
            "max_retained":0,"max_extra_coeff_bits":0,
            "total_cpu_ns":0,"total_wall_ns":0,"max_python_peak_bytes":0,
            "extra_public_issued_response_pairs":0,
            "total_public_support_pairs":0,
            "fit_solver_trials":0,"model_abstained_pairs":0,
            "by_family":{"affine":{"pairs":0,"paired":0,"FP":0,"FN":0},
                         "feistel":{"pairs":0,"paired":0,"FP":0,"FN":0}},
            "by_graph_family":{}}
def add(out,family,operator,pos,neg,works,cost,meta=None):
    selected=pos>=0 and neg<0
    fp=neg>=0;fn=pos<0
    op_family="affine" if operator.startswith("affine_") else "feistel"
    for bucket in (out,out["by_family"][op_family],
                   out["by_graph_family"].setdefault(
                       family,{"pairs":0,"paired":0,"FP":0,"FN":0})):
        bucket["pairs"]+=1;bucket["paired"]+=int(selected)
        bucket["FP"]+=int(fp);bucket["FN"]+=int(fn)
    out["total_cpu_ns"]+=cost["cpu_ns"]
    out["total_wall_ns"]+=cost["wall_ns"]
    out["max_python_peak_bytes"]=max(
        out["max_python_peak_bytes"],cost["peak_python_allocated_bytes"])
    for w in works:
        if not w:continue
        out["max_active"]=max(out["max_active"],w["max_active"])
        out["max_retained"]=max(out["max_retained"],w["max_retained"])
    if meta:
        out["max_extra_coeff_bits"]=max(out["max_extra_coeff_bits"],
                                          meta["extra_model_bits"])
        out["total_public_support_pairs"]+=meta["public_total"]
        out["extra_public_issued_response_pairs"]+=meta["extra_public"]
        out["fit_solver_trials"]+=meta["fit_solver_trials"]
        out["model_abstained_pairs"]+=int(meta["abstained"])

def evaluate(cases,base,delta):
    need(len(cases)==48,"FROZEN_PROSPECTIVE_48_PAIRS")
    outcome={key:fresh() for key in ("AV_locked_public48",
                "AS_unchanged_public24","AO_unchanged_public24",
                "AG_evaluator_true_inverse_ONLY")}
    cases_digest=[]
    for seed,vec,fam,op,nonce,p,n in cases:
        identity=q.digest([seed,list(vec),fam])
        need(p["demos"]==n["demos"],"SOURCE_PAIRS_PUBLIC_SYMMETRY")
        # SOURCE ISSUES 24 additional public example responses to the model.
        # Operator is kept in source-only public oracle and never in fit/score.
        query_start=time.process_time_ns()
        public=born.original_public_48(seed,vec,op,p["demos"])
        public_query_cpu_ns=time.process_time_ns()-query_start
        need(len(public)==48,"ONE_FIXED_PUBLIC_SUPPORT_BUDGET")
        def selected():
            fitted,fitinfo=model.fit(public,nonce)
            check=model.check(public,fitted)
            a,wa,ma=model.score(p,base,delta,fitted,fitinfo,check,12,96)
            b,wb,mb=model.score(n,base,delta,fitted,fitinfo,check,12,96)
            return a,b,wa,wb,ma,mb,fitinfo,check
        (a,b,wa,wb,ma,mb,fitinfo,check),cost=measure(selected)
        add(outcome["AV_locked_public48"],fam,op,a,b,(wa,wb),cost,
            {"extra_model_bits":fitinfo["transient_task_coefficient_bits"],
             "public_total":48,"extra_public":24,
             "fit_solver_trials":fitinfo["all_ransac_attempts"],
             "abstained":ma["abstained"]})
        # Public request cost measured separately from model CPU.
        outcome["AV_locked_public48"].setdefault("total_extra_public_query_cpu_ns",0)
        outcome["AV_locked_public48"]["total_extra_public_query_cpu_ns"]+=public_query_cpu_ns
        outcome["AV_locked_public48"].setdefault("total_corrupted_public_output_bits",0)
        outcome["AV_locked_public48"]["total_corrupted_public_output_bits"]+=6
        # The unchanged historical control implementations are not refitted.
        def prior_AS():
            fitted,info,_=as_original.public_fit(p,"robust_affine_syndrome")
            a,wa,ma=as_original.ygg(p,base,delta,fitted,info,3,56)
            b,wb,mb=as_original.ygg(n,base,delta,fitted,info,3,56)
            return a,b,wa,wb
        (a,b,wa,wb),cost=measure(prior_AS)
        add(outcome["AS_unchanged_public24"],fam,op,a,b,(wa,wb),cost,
            {"extra_model_bits":272,"public_total":24,"extra_public":0,
             "fit_solver_trials":256,"abstained":wa is None})
        def prior_AO():
            a,wa,ma=ao_original.ygg(p,base,delta,"neighbor1",2,1)
            b,wb,mb=ao_original.ygg(n,base,delta,"neighbor1",2,1)
            return a,b,wa,wb
        (a,b,wa,wb),cost=measure(prior_AO)
        add(outcome["AO_unchanged_public24"],fam,op,a,b,(wa,wb),cost)
        # EVALUATOR TRUTH PROVIDED ONLY AFTER ALL PUBLIC MODELS FINISH.
        def evaluator_oracle():
            gp=born.av.plain(p,op,nonce)
            gn=born.av.plain(n,op,nonce)
            value_p,_,_,wa=ag.ygg_transition(gp,list(base),list(delta),.1)
            value_n,_,_,wb=ag.ygg_transition(gn,list(base),list(delta),.1)
            return value_p,value_n,wa,wb
        (a,b,wa,wb),cost=measure(evaluator_oracle)
        add(outcome["AG_evaluator_true_inverse_ONLY"],fam,op,a,b,(wa,wb),cost)
        cases_digest.append(q.digest([identity,
            outcome["AV_locked_public48"]["paired"],
            outcome["AV_locked_public48"]["FP"],check]))
    for name,r in outcome.items():
        need(r["pairs"]==48 and all(f["pairs"]==24 for f in r["by_family"].values())
             and all(g["pairs"]==12 for g in r["by_graph_family"].values())
             and r["max_active"]<=7 and r["max_retained"]<=9,
             "ORIGINAL_EVALUATION_DENOMINATOR_AND_SEVEN_NINE")
    chosen=outcome["AV_locked_public48"]
    strongest=max((outcome[x]["paired"] for x in
                   ("AS_unchanged_public24","AO_unchanged_public24")
                   if outcome[x]["FP"]==0),default=0)
    eligible=(chosen["paired"]>=1 and chosen["FP"]==0 and
              chosen["paired"]>strongest)
    return {"Yggdrasil":{"models":outcome,"paired_cases":48,
            "strongest_eligible_unchanged_sourceblind_control":strongest,
            "strict_original_prospective_DEV_improvement":eligible,
            "by_case_sha256":cases_digest,
            "original_cognitive_cells":{"active":7,"retained":9},
            "new_transient_task_model_memory_outside_cognition":True,
            "comparisons_not_equalized_by_public_query_budget":True,
            "operator_or_source_inverse_used_by_model":False},
            "Wingless":{"DEV_cases_constructed":0,"DEV_used":False,
                        "TRAIN_rejected":True}}

def run(original_av,refs):
    base,delta=preflight(original_av,refs)
    return evaluate(born.pairs(),base,delta)

def main():
    parser=argparse.ArgumentParser()
    for key in ("av","o","t","an","ao","ap","aq","ar","as_train",
                "as_dev","at","au","output"):
        parser.add_argument("--"+key,required=True)
    a=parser.parse_args()
    path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),
         "NEW_ONLY_NO_FIRST_USE_RECEIPT_OVERWRITE")
    refs=[getattr(a,key) for key in ("o","t","an","ao","ap","aq",
                                    "ar","as_train","as_dev","at")]
    data=run(a.av,refs)
    data.update({"schema":SCHEMA,
         "original_preregistration_git_blob":born.FREEZE_BLOB,
         "qualified_parent_sha":"0c54bee8cc9a69bd87a7852a236b0e0bc57e01c4",
         "original_AV_science_raw_sha256":ORIGINAL_AV_SHA,
         "resource_protocol":{"runner_platform":platform.platform(),
             "python":platform.python_version(),"model_CPU_and_wall":True,
             "python_peak_malloc_tracemalloc_not_RSS":True,
             "public_query_issuance_measured_separately":True,
             "extra_public_response_access_paid_API":False,
             "matched_same_runner_not_same_query_budget":True},
         "only_Ygg_DEV_first_use":True,"Wingless_DEV_generated":0,
         "Wingless_DEV_consumed":False,"protected_science_first_use":False,
         "independent_science_acceptance":False,"optimizer_promotion":False,
         "production_activation":False,"accepted_ref_mutation":False})
    raw=json.dumps(data,sort_keys=True,indent=2).encode()+b"\n"
    with path.open("xb") as dest:dest.write(raw)
    print("F124AW_ORIGINAL_DEV_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    m=data["Yggdrasil"]["models"]
    for key,row in m.items():
        print("F124AW_DEV_"+key+"="+json.dumps({k:row[k] for k in
            ("paired","FP","FN","pairs","total_cpu_ns",
             "total_wall_ns","max_python_peak_bytes")},sort_keys=True))
    print("F124AW_DEV_STRICT_WIN="+str(
        data["Yggdrasil"]["strict_original_prospective_DEV_improvement"]).lower())
    print("F124AW_WINGLESS_DEV_UNUSED=true")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AW_FIRST_DEV_STOP:"+str(exc),file=sys.stderr);sys.exit(1)

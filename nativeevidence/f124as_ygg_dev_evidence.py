"""F124-AS first frozen Yggdrasil DEV, original controls, cost census.

Do not call --mode dev before independently passing --mode preflight. The
first-use workflow checks the earlier run, exact original file SHA, selected
config blob and immutable Git commit before enabling this evaluator.
Protected scientific first-use is NOT granted; this is prospective DEV only.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys,gc,platform,statistics,time,tracemalloc
from pathlib import Path
import f124as_train_source as source
import f124as_ygg_first_dev_source as devsrc
import f124as_noisy_inverse as novel
import f124as_train_selection as ancestry
import f124ao_public_relation_learner as ao
import f124ap_dual_kernel_learner as ap
import f124aq_sparse_composition as aq
import f124ag_transition_models as ag
import f124q_independent_binding as q

SCHEMA="forge.research.f124as.original-first-ygg-dev-outcome.v1"
FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124as-posttrain-frozen-single-ygg-dev.json"
FREEZE_BLOB="465ea2ebd5519f61ccf179c5a871490c78abebd4"
TRAIN_SHA="f012c3c34ee7f859932b5d4274e53d675f683568b2cda74cbeeee6407c785b7b"
PRECOMMITTED={"mode":"robust_affine_syndrome","error_budget":3,
              "minimum_check_correct":56,"paired":2,"FP":0,"FN":46,
              "abstained_graphs":90,"max_transient_coefficients_bits":272,
              "model_bit_ops":74752}

def need(ok,why):source.need(ok,"DEV_"+why)

def custody(o,t,an,ao_raw,ap_raw,aq_raw,ar_raw,as_raw):
    source.frozen()
    need(source.witness.blob(FREEZE)==FREEZE_BLOB,
         "PRE_FIRST_USE_IMMUTABLE_SELECTED_CONFIG")
    selected=json.loads(FREEZE.read_text(encoding="utf-8"))
    raw=Path(as_raw).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==TRAIN_SHA,
         "ORIGINAL_RAW_TRAIN_BYTES")
    train=json.loads(raw)
    need(selected["schema"]=="forge.research.f124as.posttrain-first-dev-selected-ygg.v1"
         and selected["status"]=="TRAIN_COMPLETE_DEV_UNCONSUMED"
         and selected["train_evidence"]["raw_sha256"]==TRAIN_SHA
         and selected["train_evidence"]["run_id"]==39136517506
         and selected["preimplementation_freeze_blob"]==source.FREEZE_BLOB
         and selected["Yggdrasil"]["selected"]==PRECOMMITTED
         and selected["Yggdrasil"]["admitted_for_single_original_DEV_candidate"]
         and not selected["Wingless"]["admitted_for_DEV"]
         and selected["Wingless"]["DEV_cases_generated"]==0
         and all(not value for value in selected["authority"].values())
         and train["schema"]==ancestry.SCHEMA
         and train["preimplementation_freeze_blob"]==source.FREEZE_BLOB
         and train["TRAIN"]["Yggdrasil"]["selected"]==PRECOMMITTED
         and train["TRAIN"]["Yggdrasil"]["strict_original_TRAIN_DEV_admissibility"]
         and not train["TRAIN"]["Wingless"]["strict_original_TRAIN_DEV_admissibility"]
         and train["DEV_cases_generated"]==0
         and not train["DEV_consumed"],
         "PREREGISTERED_TRAIN_ELIGIBILITY_ONLY")
    base,delta,original_ar=ancestry.original(
        o,t,an,ao_raw,ap_raw,aq_raw,ar_raw)
    return base["Yggdrasil"],delta["Yggdrasil"],selected

def empty():
    return {"paired":0,"FP":0,"FN":0,"pairs":0,
            "by_family":{f:{"paired":0,"FP":0,"FN":0,"pairs":0}
                         for f in source.FAMILIES},
            "abstained_graphs":0,"fit_wrong_bits_total":0,
            "check_correct_bits_total":0,
            "max_active":0,"max_retained":0,
            "declared_extra_task_coeff_bits":0,"model_bit_ops":0,
            "case_signature_sha256":[]}

def record(out,fam,identity,pos,neg,metrics=None,works=None):
    for x in (out,out["by_family"][fam]):
        x["pairs"]+=1;x["paired"]+=int(pos and not neg)
        x["FP"]+=int(neg);x["FN"]+=int(not pos)
    out["case_signature_sha256"].append(q.digest([identity,fam,pos,neg]))
    for meta in metrics or ():
        if meta:
            out["abstained_graphs"]+=int(meta.get("abstained",False))
            out["fit_wrong_bits_total"]+=meta.get("fit_wrong_bits") or 0
            out["check_correct_bits_total"]+=meta.get("check_correct_bits") or 0
            out["declared_extra_task_coeff_bits"]=max(
                out["declared_extra_task_coeff_bits"],
                meta.get("transient_coefficients") or 0)
            out["model_bit_ops"]+=meta.get("model_bit_ops",0)
    for w in works or ():
        if w:
            out["max_active"]=max(out["max_active"],w["max_active"])
            out["max_retained"]=max(out["max_retained"],w["max_retained"])

def evaluate(rows,base,delta,choice):
    need(len(rows)==48,"NEW_ONE_FIRST_DEV_SOURCE")
    names=("AS_selected","AO_nearest","AP_kernel","AQ_sparse",
           "AG_unparsed","AG_evaluator_true_inverse_ceiling_ONLY")
    out={k:empty() for k in names}
    diagnostics={"correct_positive":0,"correct_negative":0,
                 "three_corrupted":0,"old_literal_positive":0,
                 "model_oracle_input":False,
                 "Wingless_DEV_cases_generated":0,
                 "Yggdrasil_original_7_plus_9_cells":True}
    oracle=source.prior.parent.parent.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    sample_graphs=[]
    for seed,vec,fam,op,nonce,p,n in rows:
        case=q.digest([seed,list(vec),fam])
        # Compute all learned model decisions before true inverse is used.
        fit,fitinfo,_=novel.public_fit(p,choice["mode"])
        learned_funcs={
          "AS_selected":lambda g:novel.ygg(
              g,base,delta,fit,fitinfo,choice["error_budget"],
              choice["minimum_check_correct"]),
          "AO_nearest":lambda g:ao.ygg(g,base,delta,"neighbor1",2,1),
          "AP_kernel":lambda g:ap.ygg(
              g,base,delta,"dual_linear_kernel_ridge",1.,4,0.),
          "AQ_sparse":lambda g:aq.ygg(
              g,base,delta,"sparse_xor_basis",2,12)}
        for label,fn in learned_funcs.items():
            a,wa,ma=fn(p);b,wb,mb=fn(n)
            need(math.isfinite(a) and math.isfinite(b),
                 "FINITE_LEARNED_SCORING")
            record(out[label],fam,case,a>=0,b>=0,
                   (ma,mb),(wa,wb))
        raw_p={k:p[k] for k in ("start","target","roles","edges")}
        raw_n={k:n[k] for k in ("start","target","roles","edges")}
        def original_scorer(g):
            value,_,_,work=ag.ygg_transition(g,base,delta,.1)
            need(work["max_active"]<=7 and work["max_retained"]<=9,
                 "UNCHANGED_COGNITIVE_SCORER")
            return value,work
        a,wa=original_scorer(raw_p);b,wb=original_scorer(raw_n)
        record(out["AG_unparsed"],fam,case,a>=0,b>=0,works=(wa,wb))
        # EVALUATOR ONLY, after all learned predictions have been recorded.
        original_p=source.plain(p,op,nonce)
        original_n=source.plain(n,op,nonce)
        if len(sample_graphs)<24:sample_graphs.append(p)
        a,wa=original_scorer(original_p)
        b,wb=original_scorer(original_n)
        record(out["AG_evaluator_true_inverse_ceiling_ONLY"],fam,case,
               a>=0,b>=0,works=(wa,wb))
        relax=fam=="rotate4_tolerant"
        diagnostics["correct_positive"]+=int(oracle(original_p,relaxed=relax)==1)
        diagnostics["correct_negative"]+=int(oracle(original_n,relaxed=relax)==0)
        diagnostics["three_corrupted"]+=int(
            sum(source.relation(d["input_bits"],op)!=d["output_bits"]
                for d in p["demos"])==3)
        diagnostics["old_literal_positive"]+=int(
            oracle(raw_p,relaxed=True)>0)
    need(diagnostics["correct_positive"]==diagnostics["correct_negative"]==
         diagnostics["three_corrupted"]==48 and
         diagnostics["old_literal_positive"]==0,
         "COMPLETE_ORIGINAL_SOURCE_LABELS")
    for name,row in out.items():
        need(row["pairs"]==48 and len(row["case_signature_sha256"])==48
             and all(v["pairs"]==12 for v in row["by_family"].values())
             and row["max_active"]<=7 and row["max_retained"]<=9,
             "ORIGINAL_FOUR_FAMILY_AND_COGNITIVE_CAPACITY")
    strongest=max((out[k]["paired"] for k in
                   ("AO_nearest","AP_kernel","AQ_sparse")
                   if out[k]["FP"]==0),default=0)
    proposal=out["AS_selected"]
    strict=proposal["FP"]==0 and proposal["paired"]>strongest and proposal["paired"]>0
    return {"models":out,"source_diagnostic":diagnostics,
            "paired_cases":48,"matched_model_only_resource_sample":sample_graphs,
            "strongest_eligible_sourceblind_original_control":strongest,
            "strict_scientific_candidate_improvement":strict,
            "protected_scientific_acceptance":False}

def cost(graphs,base,delta,choice):
    need(len(graphs)==24,"MATCHED_24_RESOURCE_SAMPLES")
    results={}
    for name in ("AS_selected","AO_nearest"):
        times=[];peaks=[]
        for graph in graphs:
            def fn():
                if name=="AS_selected":
                    fitted,meta,_=novel.public_fit(graph,choice["mode"])
                    return novel.ygg(graph,base,delta,fitted,meta,
                                     choice["error_budget"],
                                     choice["minimum_check_correct"])[0]
                return ao.ygg(graph,base,delta,"neighbor1",2,1)[0]
            fn()
            start=time.perf_counter_ns();fn()
            times.append(time.perf_counter_ns()-start)
            gc.collect();tracemalloc.start();fn()
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            peaks.append(peak)
        results[name]={"graphs":24,"timed_calls":24,
                       "p50_model_plus_public_fit_ns":int(statistics.median(times)),
                       "p50_python_peak_bytes":int(statistics.median(peaks)),
                       "model_extra_memory_outside_16_cells":True,
                       "samples_digest":q.digest([times,peaks])}
    return {"platform":platform.platform(),
            "python":platform.python_version(),
            "source_oracle_inverse_excluded_from_model_time":True,
            "matched_same_runner_but_not_equalized_hardware":True,
            "results":results}

def run(mode,o,t,an,ao_raw,ap_raw,aq_raw,ar_raw,as_raw):
    need(mode in ("preflight","dev"),"EXPLICIT_STAGE_REQUIRED")
    base,delta,selection=custody(o,t,an,ao_raw,ap_raw,aq_raw,ar_raw,as_raw)
    cases=(source.pairs("Yggdrasil","TRAIN") if mode=="preflight"
           else devsrc.pairs())
    result=evaluate(cases,base,delta,selection["Yggdrasil"]["selected"])
    resources=result.pop("matched_model_only_resource_sample")
    if mode=="preflight":
        check=result["models"]["AS_selected"]
        need(check["paired"]==2 and check["FP"]==0 and check["FN"]==46
             and check["abstained_graphs"]==90
             and result["strict_scientific_candidate_improvement"],
             "REPRODUCE_ORIGINAL_TRAIN_ELIGIBILITY")
    else:
        result["cost"]=cost(resources,base,delta,selection["Yggdrasil"]["selected"])
    return {"schema":SCHEMA,"mode":mode,
            "phase":"TRAIN" if mode=="preflight" else "DEV",
            "preselected_source_blob":source.FREEZE_BLOB,
            "preselected_config_blob":FREEZE_BLOB,
            "original_TRAIN_RAW_SHA256":TRAIN_SHA,
            "Yggdrasil":result,
            "Wingless":{"DEV_cases_generated":0,"DEV_consumed":False,
                        "TRAIN_rejected":True},
            "no_DEV_selection_or_retuning":True,
            "independent_science_acceptance":False,
            "protected_first_use":False,
            "optimizer_promotion":False,
            "production_activation":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","dev"),required=True)
    for k in ("o","t","an","ao","ap","aq","ar","as_train","output"):
        p.add_argument("--"+k,required=True)
    z=p.parse_args();out=Path(z.output)
    need(out.parent.is_dir() and not out.exists(),"NO_EVIDENCE_OVERWRITE")
    data=run(z.mode,z.o,z.t,z.an,z.ao,z.ap,z.aq,z.ar,z.as_train)
    raw=json.dumps(data,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:f.write(raw)
    print("F124AS_"+z.mode.upper()+"_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    m=data["Yggdrasil"]["models"]
    print("F124AS_"+z.mode.upper()+"_YGG="+json.dumps({
        "selected_paired":m["AS_selected"]["paired"],
        "selected_FP":m["AS_selected"]["FP"],
        "selected_FN":m["AS_selected"]["FN"],
        "strongest_learned_control":data["Yggdrasil"][
                "strongest_eligible_sourceblind_original_control"],
        "strict":data["Yggdrasil"]["strict_scientific_candidate_improvement"]
    },sort_keys=True))
    print("F124AS_WINGLESS_DEV_UNUSED=true")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as ex:
        print("F124AS_FIRST_DEV_FAIL_CLOSED:"+str(ex),file=sys.stderr)
        sys.exit(1)

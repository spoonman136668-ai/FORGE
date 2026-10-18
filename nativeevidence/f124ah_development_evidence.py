"""F124-AH original 14-source authentic transfer challenge + loss diagnostics.

No model tuning or acceptance: 48 new FIT and 48 disjoint DEV cases per
project. Public novel XOR/rotation semantics are known from role prefixes
but none of the historically frozen predictors implements their translation.
Scoring oracle, labels and witness recovery are downstream only.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
from collections import defaultdict
import f124ah_frozen_source as source
import f124ah_original_model_challenge as model
import f124ag_development_evidence as previous
import f124aa_development_evidence as original
import f124q_independent_binding as q

SCHEMA="forge.research.f124ah.fresh-alternate-causal-rule-transfer-and-packed-survival.v1"
AG_RAW="eaf00275cdf010414c95caac0243622bf5bc9a419d9ae5cfa30b4df2d54b4d3d"
Y_ARMS=("AG_eta_0_1","AG_eta_0","AD_anchor10","AB_anchor16","T_original","strong_fixed")
W_ARMS=("AA_original_one","AB_original_three","strong_fixed")

def need(ok,label):source.need(ok,"RECEIPT_"+label)

def authenticate(paths):
    base,delta=previous.custody(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AG_RAW,"ORIGINAL_AG_RAW")
    r=json.loads(raw)
    need(r["schema"]=="forge.research.f124ag.prospective-transition-consistency.v1"
         and r["freeze_git_blob"]=="f533b36c0e978bfc60c6ff97b83585fd546207c3"
         and r["protected_first_use"] is False
         and r["independent_science_acceptance"] is False
         and r["optimizer_promotion"] is False
         and r["selected"]["Yggdrasil"]["eta"]==.1
         and r["selected"]["Wingless"]["eta"]==0
         and r["lanes"][1]["DEV"]["controls"]["new_hop_consistency"]["correct_pairs"]==46
         and r["lanes"][0]["DEV"]["controls"]["new_packed_hop"]["correct_pairs"]==15,
         "ORIGINAL_AG_POSITIVE_AND_WING_NEGATIVE_IMMUTABLE")
    return base,delta

def predict(lane,arm,g,base,delta,fixed):
    if arm=="strong_fixed":
        if len(g["roles"])>9:return None,None,None
        truth,work=fixed(g)
        return bool(truth),work,None
    if lane=="Yggdrasil":score,work=model.ygg(g,base,delta,arm)
    else:score,work=model.wing(g,base,delta,arm)
    return bool(score>=0),work,score

def diagnostic_empty():
    return {"positives":0,"first_packed_proxy_pruned":{},
            "first_missing_candidate":{},"final_proxy_present":0,
            "final_proxy_missing":0,"false_negative_with_packed_proxy":0,
            "public_key_checksum_alias_sets":0,
            "same_node_role_key_alias_sets":0,
            "hopwise":{},"positive_case_digest":[]}

def diagnostic_positive(g,family,base,delta,model_yes):
    score,work,trace=model.wing_source_blind_trace(g,base,delta)
    observed=model.report_wing_positive(g,family,trace)
    need(len(observed["per_hop_proxy"])==len(g["roles"]),
         "COMPLETE_PASSIVE_HOP_TRACE")
    return score,work,observed

def stage(lane,phase,base,delta,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    results={arm:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
           "families":{f:{"pairs":0,"unsupported":0,"paired":0,
                          "FP":0,"FN":0,"depth":{}}
                       for f in source.FAMILIES},
           "max_active":0,"max_retained":0,"max_states_per_node":0,
           "edge_scans":0,"bit_operations":0,"case_sha256":[]}
             for arm in arms}
    analysis={"new_public_oracle_in_scorer_only":True,
              "positive_admitted":0,"negative_rejected":0,
              "legacy_exact_positive_success":0,
              "wing_positive_proxy":diagnostic_empty() if lane=="Wingless" else None}
    for seed,v,fam,pos,neg in source.pairs(lane,phase):
        predictions={}
        for arm in arms:
            output=[]
            for graph in (pos,neg):
                yes,work,score=predict(lane,arm,graph,base,delta,fixed)
                output.append(yes)
                if work is None:continue
                row=results[arm]
                row["max_active"]=max(row["max_active"],work.get("max_active",0))
                row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
                row["max_states_per_node"]=max(row["max_states_per_node"],
                                               work.get("max_states_per_node",0))
                row["edge_scans"]+=work.get("edge_inspections",
                                             work.get("public_edge_scans",0))
                row["bit_operations"]+=work.get("raw_bit_reads",
                                                 work.get("raw_bit_ops",0))
            yes,no=output
            row=results[arm];f=row["families"][fam]
            if yes is None:
                need(no is None and arm=="strong_fixed"
                     and len(pos["roles"])>=13,
                     "UNSUPPORTED_ORIGINAL_FIXED_ONLY")
                row["unsupported"]+=1;f["unsupported"]+=1
                continue
            predictions[arm]=(yes,no)
            correct=int(yes and not no)
            for rec in (row,f):
                rec["pairs"]+=1;rec["paired"]+=correct
                rec["FP"]+=int(no);rec["FN"]+=int(not yes)
            d=f["depth"].setdefault(str(len(pos["roles"])),
                         {"pairs":0,"paired":0,"FP":0,"FN":0})
            d["pairs"]+=1;d["paired"]+=correct
            d["FP"]+=int(no);d["FN"]+=int(not yes)
            row["case_sha256"].append(q.digest({
                "family":fam,"seed":seed,"v":v,"phase":phase,
                "arm":arm,"yes":yes,"no":no}))
        # Original AG eta0 and prior AD source-blind models must retain
        # exactly their original raw scores on the transformed public input.
        if lane=="Yggdrasil":
            for g in (pos,neg):
                sc,work=model.ygg(g,base,delta,"AG_eta_0")
                need(work["max_active"]<=7 and work["max_retained"]<=9,
                     "UNCHANGED_SEVEN_PLUS_NINE")
        else:
            for g in (pos,neg):
                baseline,work=model.wing(g,base,delta,"AA_original_one")
                observed,tracework,path=model.wing_source_blind_trace(
                    g,base,delta)
                need(baseline==observed and work==tracework,
                     "UNCHANGED_ONE_STATE_OBSERVER_PARITY")
            raw,work,obs=diagnostic_positive(
                   pos,fam,base,delta,
                   predictions["AA_original_one"][0])
            diag=analysis["wing_positive_proxy"]
            diag["positives"]+=1
            diag["final_proxy_present"]+=int(obs["packed_proxy_present_final"])
            diag["final_proxy_missing"]+=int(not obs["packed_proxy_present_final"])
            diag["false_negative_with_packed_proxy"]+=int(
                not predictions["AA_original_one"][0] and
                obs["packed_proxy_present_final"])
            for name,key in (("first_packed_proxy_pruned",
                              obs["first_packed_proxy_pruned_hop"]),
                             ("first_missing_candidate",
                              obs["first_missing_candidate_hop"])):
                k=str(key) if key is not None else "SURVIVED"
                diag[name][k]=diag[name].get(k,0)+1
            diag["public_key_checksum_alias_sets"]+=obs[
                "raw_keys_with_same_packed_code"]
            diag["same_node_role_key_alias_sets"]+=obs[
                "same_node_role_src_key_collision"]
            for hop in obs["per_hop_proxy"]:
                z=diag["hopwise"].setdefault(str(hop["hop"]),{
                   "graphs":0,"candidate_proxy_present":0,
                   "selected_proxy_present":0,"evicted_candidates":0})
                z["graphs"]+=1
                z["candidate_proxy_present"]+=int(
                    hop["candidate_reference_seen"])
                z["selected_proxy_present"]+=int(
                    hop["reference_survived"])
                z["evicted_candidates"]+=hop["evictions"]
            diag["positive_case_digest"].append(q.digest({
                "seed":seed,"vector":v,"phase":phase,
                "family":fam,"observed":obs}))
        # Public semantics/labels exclusively in downstream scorer.
        analysis["positive_admitted"]+=int(source.routes(pos,fam)==1)
        analysis["negative_rejected"]+=int(source.routes(neg,fam)==0)
        analysis["legacy_exact_positive_success"]+=int(
            source.parent.prior.parent.routes15(pos,relaxed=True)>0)
    need(analysis["positive_admitted"]==48 and
         analysis["negative_rejected"]==48 and
         analysis["legacy_exact_positive_success"]==0,
         "INDEPENDENT_NEW_RULE_ORACLE_CENSUS")
    if lane=="Wingless":
        d=analysis["wing_positive_proxy"]
        need(d["positives"]==48 and len(d["positive_case_digest"])==48 and
             d["final_proxy_present"]+d["final_proxy_missing"]==48,
             "PASSIVE_ONLY_WING_DIAGNOSTIC_CENSUS")
    for arm,row in results.items():
        required=24 if arm=="strong_fixed" else 48
        need(row["pairs"]==required and row["unsupported"]==48-required
             and len(row["case_sha256"])==required
             and all(x["pairs"]+x["unsupported"]==12
                     for x in row["families"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "HARD_BOUND_AND_NEW_FAMILY_COUNT")
        if arm=="AA_original_one":
            need(row["max_active"]<=64 and row["max_states_per_node"]==1,
                 "NO_NEW_PACKED_STATES")
    return {"phase":phase,"source_pairs":48,"models":results,
            "posthoc":analysis}

def runtime(base,delta,fixed):
    families={f:[] for f in source.FAMILIES}
    for _,_,fam,p,n in source.pairs("Wingless","DEV"):
        if len(families[fam])<6:families[fam].extend((p,n))
    need(all(len(x)==6 for x in families.values()),"RUNTIME_FOUR_FAMILY_CENSUS")
    arms={"AA_original_one":lambda g:model.wing(g,base,delta,"AA_original_one"),
          "AB_original_three":lambda g:model.wing(g,base,delta,"AB_original_three"),
          "strong_fixed":lambda g:fixed(g)}
    data={arm:{"times":[],"peaks":[],"graphs":0} for arm in arms}
    serial=0
    for fam in source.FAMILIES:
        for g in families[fam]:
            serial+=1;order=list(arms)
            random.Random("F124AH/original_graph_cost/"+fam+"/"+str(serial)).shuffle(order)
            for arm in order:
                if arm=="strong_fixed" and len(g["roles"])>9:continue
                fn=arms[arm];fn(g)
                for _ in range(3):
                    t=time.perf_counter_ns();fn(g)
                    data[arm]["times"].append(time.perf_counter_ns()-t)
                gc.collect();tracemalloc.start()
                fn(g);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                data[arm]["peaks"].append(peak);data[arm]["graphs"]+=1
    summary={}
    for arm,x in data.items():
        n=12 if arm=="strong_fixed" else 24
        need(x["graphs"]==n and len(x["times"])==3*n
             and len(x["peaks"])==n,"RUNTIME_SAMPLES")
        sorted_t=sorted(x["times"])
        summary[arm]={"graphs":n,"timed_calls":3*n,
            "p50_ns":int(statistics.median(x["times"])),
            "p95_ns":sorted_t[min(len(sorted_t)-1,math.ceil(.95*len(sorted_t))-1)],
            "p50_peak_bytes":int(statistics.median(x["peaks"])),
            "samples_sha256":q.digest(x)}
    return {"linux_runner":os.environ.get("RUNNER_NAME","unspecified"),
            "python":platform.python_version(),"os":platform.platform(),
            "model_inference_only_not_passive_observer":True,
            "fixed_only_7to9":True,"independent_compute_superiority":False,
            "results":summary}

def run(paths):
    source.frozen()
    base,delta=authenticate(paths)
    fixed=original.original_fixed()
    r={"schema":SCHEMA,"freeze_git_blob":source.FREEZE_BLOB,
       "AG_parent_raw_sha256":AG_RAW,
       "original_models_parameters_unchanged":True,
       "independent_public_causal_rule":True,
       "no_fit_tuning":True,
       "protected_first_use":False,
       "independent_science_acceptance":False,
       "optimizer_promotion":False,
       "accepted_ref_mutations":0,
       "matched_compute_superiority":False,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        part={"lane":lane,"FIT":stage(lane,"FIT",base[lane],delta[lane],fixed),
              "DEV":stage(lane,"DEV",base[lane],delta[lane],fixed),
              "base_sha256":q.digest(base[lane]),
              "delta_sha256":q.digest(delta[lane])}
        if lane=="Wingless":part["benchmark"]=runtime(base[lane],delta[lane],fixed)
        r["lanes"].append(part)
    return r

def main():
    p=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae","af","ag","output"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args();dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),"NO_OVERWRITE_AUTHENTIC_JSON")
    report=run([getattr(a,name) for name in
        ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae","af","ag")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as file:file.write(raw)
    print("F124AH_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        d=lane["DEV"]["models"]
        if lane["lane"]=="Yggdrasil":
            print("F124AH_YGG_DEV=AG:"+str(d["AG_eta_0_1"]["paired"])+
                  "/48;AD:"+str(d["AD_anchor10"]["paired"])+"/48")
        else:
            print("F124AH_WING_DEV=one:"+str(d["AA_original_one"]["paired"])+
                  "/48;three:"+str(d["AB_original_three"]["paired"])+"/48")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AH_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)

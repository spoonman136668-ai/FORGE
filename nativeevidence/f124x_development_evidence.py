"""F124-X authenticated new-cohort validation and source-blind readout analysis.

Read frozen O/T/U/W artifacts. Nothing from DEV selects a model or threshold.
Timing and tracemalloc are one-run, same-runner development measurements;
not independently matched resources or science authorization.
"""
from __future__ import annotations
import argparse, gc, hashlib, json, math, os, platform, statistics, sys
import time, tracemalloc
from collections import defaultdict
from pathlib import Path

import f124x_frozen_models as x
import f124w_frozen_development as previous
import f124w_hop_trace_indexed as w
import f124v_collision_centered as v
import f124q_independent_binding as q
import f124q_fresh_source as source

SCHEMA="forge.research.f124x.fresh-validation-and-depth-readout.v1"
W_RAW_SHA="122c0f1db5547a1ce2074c73c0b4b4d089c7f00eaf4573327676be3b7b521698"
WING_ARMS=("selected_indexed","original_v_uncached","T_original","strong_fixed")
YGG_ARMS=("T_original","V_centered","V_depth_minus_one","strong_fixed")


def need(ok,code):
    x.need(ok,"RECEIPT_"+code)


def custody(o_path,t_path,u_path,w_path):
    weights,deltas=previous.previous.authenticate(o_path,t_path,u_path)
    raw=Path(w_path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==W_RAW_SHA,"W_ORIGINAL_RAW_SHA")
    witness=json.loads(raw)
    need(witness["schema"]=="forge.research.f124w.original-frozen-hop-survival-and-compute-development.v1"
         and witness["freeze_git_blob"]=="54489aa0ec10cd487270ff2925dd502f86f5d169"
         and witness["source_v_raw_sha256"]==
             "ce9e63e7e78daa470007df03a2447dab5c64f12f1a767d50df7a6b89740a31b3"
         and witness["immutable_qualified_originals"]
         and witness["fit_selected_checksum"]==list(x.SELECTED)
         and witness["scientific_acceptances"]==0
         and witness["optimizer_promotions"]==0
         and witness["training_steps"]==0
         and witness["lanes"][0]["DEV"]["arms"]["W_fit_selected"]["paired"]==46
         and witness["lanes"][0]["DEV"]["arms"]["fixed_12of16"]["paired"]==44
         and witness["lanes"][1]["DEV"]["arms"]["V_centered"]["paired"]==16,
         "W_FROZEN_MECHANISM_OR_NEGATIVE_DRIFT")
    return weights,deltas


def fixed_factory():
    return previous.previous.earlier.parent.original_adapter.clone_single_validator(
        previous.previous.earlier.previous.old_control.fixed_comparator,"graph")


def wing_arm(arm,graph,base,delta,fixed):
    if arm=="selected_indexed":
        logit,work=w.indexed_wingless(graph,base,delta,x.SELECTED)
        return bool(logit>=0),work,logit
    if arm=="original_v_uncached":
        logit,work=v.wingless_collision_reassignment(graph,base,delta)
        return bool(logit>=0),work,logit
    if arm=="T_original":
        logit,work=q.forward("Wingless",graph,list(base),list(delta))
        return bool(logit>=0),work,logit
    if arm=="strong_fixed":
        yes,work=fixed(graph)
        return bool(yes),work,None
    raise source.Quarantined("F124X_UNKNOWN_WING_ARM")


def ygg_arm(arm,graph,base,delta,fixed):
    if arm=="strong_fixed":
        yes,work=fixed(graph)
        return bool(yes),work,None,None
    mode={"T_original":"T_rank_only","V_centered":"V_centered",
          "V_depth_minus_one":"V_depth_minus_one"}[arm]
    score,work,trace=x.frozen_yggdrasil_score(graph,base,delta,mode)
    if mode!="V_depth_minus_one":
        model_score,model_work=(q.forward("Yggdrasil",graph,list(base),list(delta))
                       if mode=="T_rank_only" else
                       v.yggdrasil_centered_evidence(graph,base,delta))
        need(score==model_score and
             all(work[k]==model_work[k] for k in model_work),
             "INSTRUMENTED_ORIGINAL_LOGIT_OR_COST_DRIFT")
    return bool(score>=0),work,score,trace


def fresh_score(lane,phase,base,delta,fixed):
    arms=WING_ARMS if lane=="Wingless" else YGG_ARMS
    values={arm:{"paired":0,"pairs":0,"false_positive":0,"false_negative":0,
          "depth":{str(i):{"pairs":0,"paired":0} for i in (7,8,9)},
          "edge_scans_or_index_inspections":0,"raw_bits_or_one_time_reads":0,
          "max_cache_entries":0,"max_active":0,"max_retained":0,
          "case_hashes":[]} for arm in arms}
    witness_summary={m:{
          "loss_hop":{},"terminal_survived":0,
          "hop":{str(depth):{} for depth in (7,8,9)},
          "terminal_logit_by_depth":{str(depth):{"positive":[],"negative":[]} for depth in (7,8,9)},
          "paired_by_depth":{str(depth):0 for depth in (7,8,9)}}
        for m in ("T_original","V_centered","V_depth_minus_one")} if lane=="Yggdrasil" else None
    for seed,vector,pos,neg in x.pairs(lane,phase):
        depth=str(len(pos["roles"]))
        need(source.public_routes(pos)==1 and source.public_routes(neg)==0
             and source.public_routes(pos,True)==source.public_routes(neg,True),
             "ORIGINAL_SOURCE_REFERENCE_ADMISSION")
        results={}
        for arm in arms:
            pair=[]
            for graph in (pos,neg):
                if lane=="Wingless":
                    pred,work,logit=wing_arm(arm,graph,base,delta,fixed)
                else:
                    pred,work,logit,trace=ygg_arm(arm,graph,base,delta,fixed)
                pair.append((pred,work,logit,trace if lane=="Yggdrasil" else None))
                stats=values[arm]
                stats["edge_scans_or_index_inspections"]+=work.get(
                    "public_edge_inspections",work.get("public_edge_scans",0))
                stats["raw_bits_or_one_time_reads"]+=work.get(
                    "compressed_bit_reads",work.get("raw_bit_ops",work.get("bit_comparisons",0)))
                stats["max_cache_entries"]=max(stats["max_cache_entries"],
                    work.get("max_index_entries",0)+work.get("max_encoded_entries",0)+
                    work.get("max_lookahead_cache_entries",0))
                stats["max_active"]=max(stats["max_active"],work.get("max_active",0))
                stats["max_retained"]=max(stats["max_retained"],work.get("max_retained",0))
            yes,no=pair[0][0],pair[1][0]
            record=values[arm]
            record["pairs"]+=1
            record["paired"]+=int(yes and not no)
            record["false_positive"]+=int(no)
            record["false_negative"]+=int(not yes)
            record["depth"][depth]["pairs"]+=1
            record["depth"][depth]["paired"]+=int(yes and not no)
            record["case_hashes"].append(q.digest({
               "phase":phase,"arm":arm,"seed":seed,"vector":vector,
               "yes":yes,"no":no}))
            results[arm]=pair
        if lane=="Wingless":
            # Same primary model must still be bit-for-bit equivalent to V,
            # including all 96 newly generated public FIT/DEV graphs.
            for graph in (pos,neg):
                first,_=w.indexed_wingless(graph,base,delta,w.PRIMARY)
                original,_=v.wingless_collision_reassignment(graph,base,delta)
                need(first==original,"BITWISE_ORIGINAL_V_CACHE_PARITY")
        else:
            # No reference route or truth enters either model; only join after.
            reference=previous.exact_reference_path(pos)
            t_result=results["T_original"]
            v_result=results["V_centered"]
            cf_result=results["V_depth_minus_one"]
            need(v_result[0][3]==cf_result[0][3] and
                 v_result[1][3]==cf_result[1][3] and
                 v_result[0][1]==cf_result[0][1],
                 "COUNTERFACTUAL_MUST_CHANGE_READOUT_ONLY")
            t_join=previous.witness_join(t_result[0][3],reference)
            v_join=previous.witness_join(v_result[0][3],reference)
            need(t_join["causal_path_survives_terminal"] and
                 v_join["causal_path_survives_terminal"],
                 "FROZEN_PREVIOUS_PATH_SURVIVAL_UNEXPECTED_DRIFT")
            for arm in ("T_original","V_centered","V_depth_minus_one"):
                trace=results[arm][0][3]
                witness=(t_join if arm=="T_original" else v_join)
                row=witness_summary[arm]
                row["terminal_survived"]+=int(witness["causal_path_survives_terminal"])
                lost=str(witness["first_causal_path_loss"])
                row["loss_hop"][lost]=row["loss_hop"].get(lost,0)+1
                row["terminal_logit_by_depth"][depth]["positive"].append(results[arm][0][2])
                row["terminal_logit_by_depth"][depth]["negative"].append(results[arm][1][2])
                row["paired_by_depth"][depth]+=int(results[arm][0][0] and not results[arm][1][0])
                for step,tick in enumerate(witness["hops"]):
                    entry=row["hop"][depth].setdefault(str(step+1),{
                      "cases":0,"in_candidate_before_prune":0,
                      "in_active":0,"in_retained":0,"in_final":0,"evictions":0,
                      "witness_score_sum":0.,"witness_score_count":0,
                      "score_gap_sum":0.,"score_gap_count":0,
                      "score_drift_from_T_sum":0.,"score_drift_from_T_count":0})
                    entry["cases"]+=1
                    entry["in_candidate_before_prune"]+=int(tick["candidate_reachable_before_prune"])
                    entry["in_active"]+=int(tick["survived_active"])
                    entry["in_retained"]+=int(tick["survived_retained"])
                    entry["in_final"]+=int(tick["survived_total"])
                    entry["evictions"]+=tick["hop_evictions"]
                    if tick["witness_value"] is not None:
                        entry["witness_score_sum"]+=tick["witness_value"]
                        entry["witness_score_count"]+=1
                    if tick["witness_minus_competitor"] is not None:
                        entry["score_gap_sum"]+=tick["witness_minus_competitor"]
                        entry["score_gap_count"]+=1
                    t_value=t_join["hops"][step]["witness_value"]
                    if tick["witness_value"] is not None and t_value is not None:
                        entry["score_drift_from_T_sum"]+=tick["witness_value"]-t_value
                        entry["score_drift_from_T_count"]+=1
    for arm,row in values.items():
        need(row["pairs"]==48 and len(row["case_hashes"])==48
             and all(x["pairs"]==16 for x in row["depth"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil" else row["max_active"]<=192),
             "EXACT_DENOMINATORS_AND_ORIGINAL_CAPACITY")
    return {"phase":phase,"pairs":48,"arms":values,
            "causal_reference_positive_pairs":48,
            "causal_reference_role_only":0,
            "posthoc_trace":witness_summary}


def percentile(values,quantile):
    need(len(values)>0,"NONEMPTY_MEASUREMENTS")
    ordered=sorted(values)
    return ordered[min(len(ordered)-1,math.ceil(quantile*len(ordered))-1)]


def paired_runtime_memory(base,delta,fixed):
    """Frozen same-runner measurement of first four DEV pairs at each depth.

    Timings 3 calls per graph/arm with one warmup. Independently repeat
    a tracemalloc peak per graph/arm, excluding timer contamination.
    """
    case_by_depth={i:[] for i in (7,8,9)}
    for _,_,pos,neg in x.pairs("Wingless","DEV"):
        depth=len(pos["roles"])
        if len(case_by_depth[depth])<4:case_by_depth[depth].append((pos,neg))
    need(all(len(v)==4 for v in case_by_depth.values()),"STRATIFIED_BENCHMARK_SAMPLE")
    arm_map={
       "selected_indexed":lambda graph:w.indexed_wingless(graph,base,delta,x.SELECTED),
       "frozen_primary_uncached":lambda graph:v.wingless_collision_reassignment(graph,base,delta),
       "strong_fixed":lambda graph:fixed(graph)
    }
    samples={key:{"time_ns":[],"tracemalloc_peak_bytes":[]}
             for key in arm_map}
    for depth in (7,8,9):
        for pos,neg in case_by_depth[depth]:
            for graph in (pos,neg):
                for name,method in arm_map.items():
                    method(graph)
                    for _ in range(3):
                        started=time.perf_counter_ns()
                        method(graph)
                        samples[name]["time_ns"].append(time.perf_counter_ns()-started)
                    gc.collect()
                    tracemalloc.start()
                    method(graph)
                    _,peak=tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    samples[name]["tracemalloc_peak_bytes"].append(peak)
    out={}
    for name,r in samples.items():
        need(len(r["time_ns"])==72 and len(r["tracemalloc_peak_bytes"])==24,
             "MATCHED_SAMPLE_CENSUS")
        out[name]={
            "calls":72,"cases":24,
            "median_wall_ns":int(statistics.median(r["time_ns"])),
            "p95_wall_ns":percentile(r["time_ns"],.95),
            "median_peak_tracemalloc_bytes":int(statistics.median(r["tracemalloc_peak_bytes"])),
            "p95_peak_tracemalloc_bytes":percentile(r["tracemalloc_peak_bytes"],.95),
            "raw_sample_sha256":q.digest(r)}
    return {"setup":"one runner same process, 4 pairs per depth, 2 graphs/pair, 3 timed repetitions, 1 warmup; per-call tracemalloc sampled separately",
      "python":sys.version.split()[0],"platform":platform.platform(),
      "processor":platform.processor(),"machine":platform.machine(),
      "github_runner":os.environ.get("RUNNER_NAME","unavailable"),
      "matched_hardware_or_scientific_superiority":False,
      "arms":out}


def run(o,t,u,w_raw):
    x.frozen()
    bases,deltas=custody(o,t,u,w_raw)
    fixed=fixed_factory()
    data={"schema":SCHEMA,"freeze_git_blob":x.FREEZE_BLOB,
          "qualified_w_parent_sha256":W_RAW_SHA,
          "original_weight_receipts_immutable":True,
          "new_training_steps":0,"DEV_only_after_source_frozen":True,
          "protected_first_use":False,"science_accepted":False,
          "optimizer_promotions":0,"accepted_ref_mutations":0,
          "model_or_source_leak":False,
          "matched_resource_superiority":False,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,
             "FIT":fresh_score(lane,"FIT",bases[lane],deltas[lane],fixed),
             "DEV":fresh_score(lane,"DEV",bases[lane],deltas[lane],fixed),
             "original_delta_sha256":q.digest(deltas[lane])}
        if lane=="Wingless":
            row["runtime_memory"]=paired_runtime_memory(bases[lane],deltas[lane],fixed)
        data["lanes"].append(row)
    return data


def main():
    p=argparse.ArgumentParser()
    for option in ("o","t","u","w","output"):
        p.add_argument("--"+option,required=True)
    a=p.parse_args()
    target=Path(a.output)
    need(target.parent.is_dir() and not target.exists(),"IMMUTABLE_NEW_RECEIPT")
    r=run(a.o,a.t,a.u,a.w)
    raw=json.dumps(r,indent=2,sort_keys=True).encode()+b"\n"
    with target.open("xb") as f:f.write(raw)
    print("F124X_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in r["lanes"]:
        z=row["DEV"]["arms"]
        if row["lane"]=="Wingless":
            print("F124X_WING_DEV=selected="+str(z["selected_indexed"]["paired"])+
                  "/48:V="+str(z["original_v_uncached"]["paired"])+
                  "/48:fixed="+str(z["strong_fixed"]["paired"])+"/48")
        else:
            print("F124X_YGG_DEV=T="+str(z["T_original"]["paired"])+
                  "/48:V="+str(z["V_centered"]["paired"])+
                  "/48:VdepthMinusOne="+str(z["V_depth_minus_one"]["paired"])+
                  "/48:fixed="+str(z["strong_fixed"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,KeyError,ValueError,TypeError,ArithmeticError) as e:
        print("F124X_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)

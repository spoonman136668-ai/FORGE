"""F124-Y source-authenticated fresh experiment and fairer paired-resource census.

No protected source, post-DEV tuning, model retraining or matched-compute
claim. Runtime and allocation budget are evaluated against the same control
on the same graph, runner, process, Python version and fixed sample order.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path

import f124y_frozen_models as y
import f124x_development_evidence as parent
import f124x_frozen_models as x
import f124w_hop_trace_indexed as w
import f124q_independent_binding as q
import f124q_fresh_source as source

SCHEMA="forge.research.f124y.authentic-budgeted-replication-and-fit-readout.v1"
X_SHA="457f7be9312bd30b4ce052aed11edfd929fd02e715aa85ede7b9a58b2be355ba"
WING_ARMS=("selected_indexed","same_checksum_uncached","strong_fixed")
YGG_ARMS=("T_original","V_original","X_depth_minus_one","Y_fit_calibrated","strong_fixed")


def need(value,why):
    y.need(value,"RECEIPT_"+why)


def authentic(o,t,u,w_path,x_path):
    bases,deltas=parent.custody(o,t,u,w_path)
    raw=Path(x_path).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==X_SHA,"PARENT_X_RAW_SHA")
    old=json.loads(raw)
    need(old["schema"]=="forge.research.f124x.fresh-validation-and-depth-readout.v1"
         and old["freeze_git_blob"]=="3eb6e32c29505aa2b88ecb8860291f27241ea3e4"
         and old["protected_first_use"] is False
         and old["science_accepted"] is False
         and old["optimizer_promotions"]==0
         and old["matched_resource_superiority"] is False
         and old["lanes"][0]["DEV"]["arms"]["selected_indexed"]["paired"]==44
         and old["lanes"][0]["DEV"]["arms"]["strong_fixed"]["paired"]==40
         and old["lanes"][1]["DEV"]["arms"]["V_depth_minus_one"]["paired"]==29,
         "ORIGINAL_NEGATIVES_AND_IDENTITY")
    return bases,deltas


def outputs(lane,arm,g,base,delta,fixed,learned):
    if arm=="strong_fixed":
        result,work=fixed(g)
        return bool(result),work,None
    if lane=="Wingless":
        if arm=="selected_indexed":
            score,work=w.indexed_wingless(g,base,delta,y.CHECKSUM)
        elif arm=="same_checksum_uncached":
            score,work=y.checksum_uncached(g,base,delta)
        else:
            raise source.Quarantined("F124Y_UNKNOWN_WING_ARM")
    else:
        mode={"T_original":"T_rank_only","V_original":"V_centered",
              "X_depth_minus_one":"V_depth_minus_one",
              "Y_fit_calibrated":"V_centered"}[arm]
        score,work,_=x.frozen_yggdrasil_score(g,base,delta,mode)
        if arm=="Y_fit_calibrated":
            score=y.calibrated_logit(score,len(g["roles"]),learned["bias"],learned["slope"])
    return bool(score>=0),work,score


def score(lane,phase,base,delta,fixed,learned):
    arms=WING_ARMS if lane=="Wingless" else YGG_ARMS
    stats={arm:{"paired":0,"pairs":0,"false_positive":0,"false_negative":0,
            "depth":{str(d):{"pairs":0,"paired":0} for d in (7,8,9)},
            "max_active":0,"max_retained":0,"edge_scans_or_inspections":0,
            "bit_reads_or_ops":0,"peak_extra_cache_entries":0,
            "case_sha256":[]} for arm in arms}
    for seed,vec,pos,neg in y.pairs(lane,phase):
        need(source.public_routes(pos)==1 and source.public_routes(neg)==0
             and source.public_routes(pos,True)==source.public_routes(neg,True),
             "FULL_ORIGINAL_CAUSAL_PUBLIC_ADMISSION")
        depth=str(len(pos["roles"]))
        for arm in arms:
            preds=[]
            raw_logits=[]
            for g in (pos,neg):
                pred,work,raw=outputs(lane,arm,g,base,delta,fixed,learned)
                preds.append(pred)
                raw_logits.append(raw)
                rec=stats[arm]
                rec["max_active"]=max(rec["max_active"],work.get("max_active",0))
                rec["max_retained"]=max(rec["max_retained"],work.get("max_retained",0))
                rec["edge_scans_or_inspections"]+=work.get(
                    "public_edge_inspections",work.get("public_edge_scans",0))
                rec["bit_reads_or_ops"]+=work.get(
                    "compressed_bit_reads",work.get("raw_bit_ops",work.get("bit_comparisons",0)))
                rec["peak_extra_cache_entries"]=max(rec["peak_extra_cache_entries"],
                    work.get("max_index_entries",0)+work.get("max_encoded_entries",0)+
                    work.get("max_lookahead_cache_entries",0))
            if lane=="Wingless" and arm=="same_checksum_uncached":
                a,_=w.indexed_wingless(pos,base,delta,y.CHECKSUM)
                b,_=w.indexed_wingless(neg,base,delta,y.CHECKSUM)
                need(raw_logits==[a,b],"SAME_ENCODING_CACHE_PARITY")
            a=stats[arm]
            yes,no=preds
            success=bool(yes and not no)
            a["pairs"]+=1
            a["paired"]+=int(success)
            a["false_positive"]+=int(no)
            a["false_negative"]+=int(not yes)
            a["depth"][depth]["pairs"]+=1
            a["depth"][depth]["paired"]+=int(success)
            a["case_sha256"].append(q.digest({
                "seed":seed,"vector":vec,"phase":phase,"arm":arm,
                "positive":yes,"negative":no,"pair":success}))
    for name,row in stats.items():
        need(row["pairs"]==48 and len(row["case_sha256"])==48
             and all(d["pairs"]==16 for d in row["depth"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil" else
                  row["max_active"]<=192),"CAPACITY_OR_COHORT_DENOMINATOR")
    if lane=="Wingless":
        left,right=stats["selected_indexed"],stats["same_checksum_uncached"]
        need(all(left[k]==right[k] for k in ("paired","false_positive",
                "false_negative","case_sha256")),"SAME_CHECKSUM_PARITY")
    return {"phase":phase,"pairs":48,"reference_exact":48,"reference_role_only":0,
            "arms":stats}


def quantile(seq,fraction):
    s=sorted(seq)
    return s[min(len(s)-1,math.ceil(fraction*len(s))-1)]


def benchmark(base,delta,fixed):
    grouped={7:[],8:[],9:[]}
    for _,_,pos,neg in y.pairs("Wingless","DEV"):
        d=len(pos["roles"])
        if len(grouped[d])<4:grouped[d].append((pos,neg))
    need(all(len(g)==4 for g in grouped.values()),"BENCHMARK_STRATA")
    funcs={
       "selected_indexed":lambda g:w.indexed_wingless(g,base,delta,y.CHECKSUM),
       "same_checksum_uncached":lambda g:y.checksum_uncached(g,base,delta),
       "strong_fixed":lambda g:fixed(g)
    }
    result={name:{"times":[],"peak_alloc_bytes":[]} for name in funcs}
    graph_count=0
    for depth in (7,8,9):
        for pos,neg in grouped[depth]:
            for g in (pos,neg):
                graph_count+=1
                names=list(funcs)
                random.Random("F124Y-ORDER-v1/"+str(depth)+"/"+str(graph_count)).shuffle(names)
                for name in names:
                    f=funcs[name]
                    f(g)  # fixed warmup
                    for _ in range(5):
                        start=time.perf_counter_ns()
                        f(g)
                        result[name]["times"].append(time.perf_counter_ns()-start)
                    gc.collect()
                    tracemalloc.start()
                    f(g)
                    _,peak=tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    result[name]["peak_alloc_bytes"].append(peak)
    out={}
    for name,part in result.items():
        need(len(part["times"])==120 and len(part["peak_alloc_bytes"])==24,
             "BENCHMARK_COMPLETE")
        out[name]={
          "graphs":24,"timed_repetitions":120,
          "median_wall_ns":int(statistics.median(part["times"])),
          "p95_wall_ns":quantile(part["times"],.95),
          "median_tracemalloc_peak_bytes":int(statistics.median(part["peak_alloc_bytes"])),
          "p95_tracemalloc_peak_bytes":quantile(part["peak_alloc_bytes"],.95),
          "sample_sha256":q.digest(part)}
    fixed_m=out["strong_fixed"]
    selected=out["selected_indexed"]
    eligibility={
        "runtime_at_or_below_fixed":
            selected["median_wall_ns"]<=fixed_m["median_wall_ns"],
        "allocation_at_or_below_fixed":
            selected["median_tracemalloc_peak_bytes"]<=fixed_m["median_tracemalloc_peak_bytes"]}
    return {
      "platform":platform.platform(),"python":platform.python_version(),
      "machine":platform.machine(),"runner":os.environ.get("RUNNER_NAME","unavailable"),
      "sampling":"same public graphs runner process, seeded alternating order, 1 warmup + 5 timed repetitions per graph and separately sampled peak allocations; GC between timed block and tracemalloc",
      "measured":out,"budget_eligibility":eligibility,
      "resource_matched_superiority_eligible":all(eligibility.values()),
      "independent_hardware_speedup_proven":False}


def run(o,t,u,w_file,x_file):
    y.frozen()
    bases,deltas=authentic(o,t,u,w_file,x_file)
    fixed=parent.fixed_factory()
    selected,grid=y.select_fit_bias(y.pairs("Yggdrasil","FIT"),
                                     bases["Yggdrasil"],deltas["Yggdrasil"])
    result={
      "schema":SCHEMA,"frozen_protocol_git_blob":y.FREEZE_BLOB,
      "original_x_raw_sha256":X_SHA,"source_disjoint":True,
      "weights_or_source_modified":False,"fit_selected_only_using_fit":True,
      "new_model_training_steps":0,"science_acceptances":0,
      "optimizer_promotions":0,"protected_first_use":False,
      "accepted_ref_mutations":0,"resource_matched_superiority_proven":False,
      "readout_selected_fit":selected,"readout_fit_grid":grid,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        learned=selected if lane=="Yggdrasil" else None
        row={"lane":lane,"FIT":score(lane,"FIT",bases[lane],deltas[lane],fixed,learned),
             "DEV":score(lane,"DEV",bases[lane],deltas[lane],fixed,learned),
             "delta_sha256":q.digest(deltas[lane]),
             "hard_cell_budget":{"active":7,"retained":9} if lane=="Yggdrasil"
                                else {"per_node":3,"channels":4,"levels":5}}
        if lane=="Wingless":
            row["matched_resource_observation"]=benchmark(bases[lane],deltas[lane],fixed)
        result["lanes"].append(row)
    return result


def main():
    p=argparse.ArgumentParser()
    for option in ("o","t","u","w","x","output"):
        p.add_argument("--"+option,required=True)
    args=p.parse_args()
    output=Path(args.output)
    need(output.parent.is_dir() and not output.exists(),"IMMUTABLE_OUTPUT")
    report=run(args.o,args.t,args.u,args.w,args.x)
    raw=json.dumps(report,indent=2,sort_keys=True).encode()+b"\n"
    with output.open("xb") as f:f.write(raw)
    print("F124Y_RAW_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        a=lane["DEV"]["arms"]
        if lane["lane"]=="Wingless":
            print("F124Y_WING_DEV=selected="+str(a["selected_indexed"]["paired"])+
              "/48:same_uncached="+str(a["same_checksum_uncached"]["paired"])+
              "/48:fixed="+str(a["strong_fixed"]["paired"])+"/48")
        else:
            print("F124Y_YGG_DEV=calibrated="+str(a["Y_fit_calibrated"]["paired"])+
              "/48:V="+str(a["V_original"]["paired"])+"/48:T="+
              str(a["T_original"]["paired"])+"/48:fixed="+
              str(a["strong_fixed"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124Y_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)

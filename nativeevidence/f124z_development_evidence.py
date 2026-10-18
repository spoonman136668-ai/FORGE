"""F124-Z authentic O/T/U/W/X/Y source-custody, fresh FIT-only candidate,
full independent DEV, resource budget and negative-retention receipts.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path

import f124z_sparse_continuity as z
import f124y_development_evidence as preceding
import f124w_hop_trace_indexed as original_index
import f124q_independent_binding as original_t
import f124q_fresh_source as source
import f124x_frozen_models as prior_x
import f124v_collision_centered as prior_v

SCHEMA="forge.research.f124z.authentic-sparse-continuity-new-development.v1"
Y_RAW_SHA="13608eabec0d63103199f48cea0fdc861fe84ee64527007229d4bcf422d05353"
WING_ARMS=("sparse_on_demand","parent_indexed","parent_uncached_same_checksum","strong_fixed")
YGG_ARMS=("continuity_penalty","original_T","original_V","strong_fixed")


def need(ok,code):
    z.need(ok,"EVIDENCE_"+code)


def original_custody(o,t,u,w,x,y):
    base,deltas=preceding.authentic(o,t,u,w,x)
    raw=Path(y).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==Y_RAW_SHA,"ORIGINAL_Y_RAW_RECEIPT")
    parent=json.loads(raw)
    need(parent["schema"]=="forge.research.f124y.authentic-budgeted-replication-and-fit-readout.v1"
         and parent["frozen_protocol_git_blob"]==preceding.y.FREEZE_BLOB
         and parent["original_x_raw_sha256"]==preceding.X_SHA
         and parent["science_acceptances"]==0
         and parent["optimizer_promotions"]==0
         and parent["protected_first_use"] is False
         and parent["resource_matched_superiority_proven"] is False
         and parent["lanes"][0]["DEV"]["arms"]["selected_indexed"]["paired"]==45
         and parent["lanes"][0]["DEV"]["arms"]["strong_fixed"]["paired"]==40
         and parent["lanes"][1]["DEV"]["arms"]["Y_fit_calibrated"]["paired"]==16
         and parent["lanes"][1]["DEV"]["arms"]["strong_fixed"]["paired"]==42,
         "ORIGINAL_PARENT_SCIENTIFIC_NEGATIVE_RETAINED")
    return base,deltas


def forward(lane,arm,graph,base,delta,penalty,fixed):
    if arm=="strong_fixed":
        result,work=fixed(graph)
        return bool(result),work,None
    if lane=="Wingless":
        if arm=="sparse_on_demand":
            score,work=z.sparse_wingless(graph,base,delta)
        elif arm=="parent_indexed":
            score,work=original_index.indexed_wingless(graph,base,delta,z.CHECKSUM)
        elif arm=="parent_uncached_same_checksum":
            score,work=preceding.y.checksum_uncached(graph,base,delta)
        else:raise source.Quarantined("F124Z_BAD_WINGLESS_ARM")
    else:
        if arm=="continuity_penalty":
            score,ratio,work=z.continuity_head(graph,base,delta)
            score=z.corrected_logit(score,ratio,penalty)
            original,orig_work=original_t.forward("Yggdrasil",graph,list(base),list(delta))
            need(all(work[k]==orig_work[k] for k in orig_work)
                 and abs(z.corrected_logit(score+penalty*(1.-ratio),ratio,0.)-original)<1e-12,
                 "BASE_YGG_HEAD_MUST_BE_UNCHANGED")
        elif arm=="original_T":
            score,work=original_t.forward("Yggdrasil",graph,list(base),list(delta))
        elif arm=="original_V":
            score,work=prior_v.yggdrasil_centered_evidence(graph,list(base),list(delta))
        else:raise source.Quarantined("F124Z_BAD_YGG_ARM")
    return bool(score>=0),work,score


def score_cohort(lane,phase,base,delta,penalty,fixed):
    names=WING_ARMS if lane=="Wingless" else YGG_ARMS
    rows={arm:{"pairs":0,"paired":0,"false_positive":0,"false_negative":0,
               "depth":{str(i):{"pairs":0,"paired":0} for i in (7,8,9)},
               "edge_inspections_or_scans":0,"raw_bit_reads_or_ops":0,
               "continuity_bit_comparisons":0,"max_active":0,"max_retained":0,
               "max_extra_cell_counter_slots":0,"max_extra_adjacent_index":0,
               "case_sha256":[]} for arm in names}
    for seed,vector,pos,neg in z.pairs(lane,phase):
        need(source.public_routes(pos)==1 and source.public_routes(neg)==0 and
             source.public_routes(pos,True)==source.public_routes(neg,True),
             "ORIGINAL_PUBLIC_SOURCE_CEILING")
        d=str(len(pos["roles"]))
        predictions={}
        for arm in names:
            for which,g in (("positive",pos),("negative",neg)):
                pred,work,logit=forward(lane,arm,g,base,delta,penalty,fixed)
                predictions[(arm,which)]=(pred,logit)
                row=rows[arm]
                row["edge_inspections_or_scans"]+=work.get(
                    "edge_inspections",work.get(
                    "public_edge_inspections",work.get("public_edge_scans",0)))
                row["raw_bit_reads_or_ops"]+=work.get(
                    "on_demand_raw_bit_reads",work.get(
                    "compressed_bit_reads",work.get(
                    "raw_bit_ops",work.get("bit_comparisons",0))))
                row["continuity_bit_comparisons"]+=work.get(
                    "continuity_raw_bit_comparisons",0)
                row["max_active"]=max(row["max_active"],work.get("max_active",0))
                row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
                row["max_extra_cell_counter_slots"]=max(
                    row["max_extra_cell_counter_slots"],work.get(
                    "continuity_counter_slots_max",0))
                row["max_extra_adjacent_index"]=max(
                    row["max_extra_adjacent_index"],work.get(
                    "max_adjacent_index_entries",0))
            yes=predictions[(arm,"positive")][0]
            no=predictions[(arm,"negative")][0]
            row=rows[arm]
            row["pairs"]+=1
            row["paired"]+=int(yes and not no)
            row["false_positive"]+=int(no)
            row["false_negative"]+=int(not yes)
            row["depth"][d]["pairs"]+=1
            row["depth"][d]["paired"]+=int(yes and not no)
            row["case_sha256"].append(original_t.digest({
                "seed":seed,"vector":vector,"phase":phase,
                "arm":arm,"yes":yes,"no":no}))
        if lane=="Wingless":
            cached=[predictions[("parent_indexed",which)][1] for which in ("positive","negative")]
            uncached=[predictions[("parent_uncached_same_checksum",which)][1] for which in ("positive","negative")]
            sparse=[predictions[("sparse_on_demand",which)][1] for which in ("positive","negative")]
            need(cached==uncached==sparse,"SOURCE_IDENTICAL_COMPRESSION_FLOATS")
    for row in rows.values():
        need(row["pairs"]==48 and len(row["case_sha256"])==48
             and all(x["pairs"]==16 for x in row["depth"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192)
             and row["max_extra_cell_counter_slots"]<=16,
             "FULL_STRATA_AND_CELL_MEMORY_LIMIT")
    return {"phase":phase,"pairs":48,"source_exact_paired":48,
            "role_only_negative_paired":0,"arms":rows}


def quantile(s,p):
    a=sorted(s)
    return a[min(len(a)-1,math.ceil(len(a)*p)-1)]


def resource_census(base,delta,fixed):
    by_depth={d:[] for d in (7,8,9)}
    for _,_,pos,neg in z.pairs("Wingless","DEV"):
        if len(by_depth[len(pos["roles"])])<4:by_depth[len(pos["roles"])].append((pos,neg))
    need(all(len(a)==4 for a in by_depth.values()),"FULL_BENCHMARK_DEPTH")
    arms={
      "sparse_on_demand":lambda g:z.sparse_wingless(g,base,delta),
      "parent_indexed":lambda g:original_index.indexed_wingless(g,base,delta,z.CHECKSUM),
      "parent_uncached_same_checksum":lambda g:preceding.y.checksum_uncached(g,base,delta),
      "strong_fixed":lambda g:fixed(g)
    }
    collected={n:{"time":[],"allocated":[]} for n in arms}
    serial=0
    for d in (7,8,9):
        for pos,neg in by_depth[d]:
            for g in (pos,neg):
                serial+=1
                order=list(arms)
                random.Random("F124Z/MATCHED/v1/"+str(d)+"/"+str(serial)).shuffle(order)
                for name in order:
                    f=arms[name]
                    f(g)
                    for i in range(5):
                        start=time.perf_counter_ns()
                        f(g)
                        collected[name]["time"].append(time.perf_counter_ns()-start)
                    gc.collect()
                    tracemalloc.start()
                    f(g)
                    _,peak=tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    collected[name]["allocated"].append(peak)
    summary={}
    for name,vals in collected.items():
        need(len(vals["time"])==120 and len(vals["allocated"])==24,
             "BENCHMARK_REPRESENTATION")
        summary[name]={
          "graph_count":24,"repetitions":120,
          "median_time_ns":int(statistics.median(vals["time"])),
          "p95_time_ns":quantile(vals["time"],.95),
          "median_peak_alloc_bytes":int(statistics.median(vals["allocated"])),
          "p95_peak_alloc_bytes":quantile(vals["allocated"],.95),
          "raw_sample_sha256":original_t.digest(vals)}
    a=summary["sparse_on_demand"];b=summary["strong_fixed"]
    flags={"time_le_fixed":a["median_time_ns"]<=b["median_time_ns"],
           "peak_allocation_le_fixed":
              a["median_peak_alloc_bytes"]<=b["median_peak_alloc_bytes"]}
    return {"same_runner":True,"environment":platform.platform(),
            "python":platform.python_version(),"arch":platform.machine(),
            "runner":os.environ.get("RUNNER_NAME","unavailable"),
            "sampling":"24 identical graph inputs stratified 7/8/9; 5 timed calls per graph/arm, one warmup, fixed-seed alternating arm order, peak tracemalloc separately with GC",
            "arms":summary,"budget":flags,
            "both_resource_budgets_satisfied":all(flags.values()),
            "protected_matched_superiority_claim":False}


def run(o,t,u,w,x,y):
    z.frozen()
    bases,deltas=original_custody(o,t,u,w,x,y)
    fixed=preceding.parent.fixed_factory()
    selection,grid=z.choose_fit_penalty(z.pairs("Yggdrasil","FIT"),
                                        bases["Yggdrasil"],deltas["Yggdrasil"])
    need(selection["penalty"] in z.PENALTIES and len(grid)==6,
         "FIT_SELECTION_QUARANTINE")
    answer={"schema":SCHEMA,"frozen_protocol_blob":z.FREEZE_BLOB,
      "authentic_parent_y_raw_sha256":Y_RAW_SHA,"original_models_immutable":True,
      "new_source_disjoint":True,"new_development_after_fit_selection":True,
      "new_training_steps":0,"ygg_selected_FIT":selection,"ygg_frozen_penalty_grid":grid,
      "protected_cases_generated":0,"independent_science_acceptance":False,
      "optimizer_promotions":0,"accepted_ref_mutations":0,
      "matched_compute_superiority_proven":False,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        penalty=selection["penalty"] if lane=="Yggdrasil" else 0.
        row={"lane":lane,"fit":score_cohort(lane,"FIT",bases[lane],deltas[lane],penalty,fixed),
             "dev":score_cohort(lane,"DEV",bases[lane],deltas[lane],penalty,fixed),
             "original_delta_sha256":original_t.digest(deltas[lane]),
             "memory_capacity_preserved":True}
        if lane=="Wingless":
            row["runtime_memory"]=resource_census(bases[lane],deltas[lane],fixed)
        answer["lanes"].append(row)
    return answer


def main():
    ap=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","output"):
        ap.add_argument("--"+name,required=True)
    p=ap.parse_args()
    path=Path(p.output)
    need(path.parent.is_dir() and not path.exists(),"NEW_DURABLE_NONOVERWRITE")
    receipt=run(p.o,p.t,p.u,p.w,p.x,p.y)
    raw=json.dumps(receipt,sort_keys=True,indent=2).encode()+b"\n"
    with path.open("xb") as f:f.write(raw)
    print("F124Z_RAW_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in receipt["lanes"]:
        s=lane["dev"]["arms"]
        if lane["lane"]=="Wingless":
            print("F124Z_WING_DEV=sparse="+str(s["sparse_on_demand"]["paired"])+
                  "/48:indexed="+str(s["parent_indexed"]["paired"])+
                  "/48:fixed="+str(s["strong_fixed"]["paired"])+"/48")
        else:
            print("F124Z_YGG_DEV=key_continuity="+
                  str(s["continuity_penalty"]["paired"])+
                  "/48:T="+str(s["original_T"]["paired"])+
                  "/48:fixed="+str(s["strong_fixed"]["paired"])+"/48")


if __name__=="__main__":
    try:main()
    except (OSError,KeyError,TypeError,ValueError,ArithmeticError) as ex:
        print("F124Z_FAIL_CLOSED:"+str(ex),file=sys.stderr)
        sys.exit(1)

"""F124-AB authenticated independent FIT and four-family DEV development evidence.

The 25 gamma+penalty FIT choices see only permuted and one-bit-relaxed
FIT data. DEV is generated after selection. Original Z exact-key, original
T 7+9, strong fixed and AA/packed controls stay present and unchanged.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
from collections import Counter

import f124ab_frozen_source as s
import f124ab_soft_hamming_pareto as m
import f124aa_development_evidence as prior
import f124aa_packed_transfer as aa
import f124q_independent_binding as q

AA_RAW="fda2f1dbf130062b347e0e46862fe409b5af2c95a98fd3ca97c0e8642ff7d034"
SCHEMA="forge.research.f124ab.frozen-soft-hamming-packed-pareto-development.v1"
WING_ARMS=("packed_1","packed_2","packed_3","original_AA_1","original_Z_3","strong_fixed")
YGG_ARMS=("FIT_soft_head","original_T","frozen_Z_exact_0_5","strong_fixed")

def need(ok,code):s.need(ok,"RECEIPT_"+code)

def authentic(o,t,u,w,x,y,z,aa_original):
    base,delta=prior.original_custody(o,t,u,w,x,y,z)
    b=Path(aa_original).read_bytes()
    need(hashlib.sha256(b).hexdigest()==AA_RAW,"PARENT_AA_RAW_SHA")
    p=json.loads(b)
    need(p["schema"]=="forge.research.f124aa.frozen-transfer-and-packed-representation-development.v1"
         and p["freeze_git_blob"]=="44520db702ef71623d6bc17d1daa035b50095a3c"
         and p["scientific_acceptance"] is False
         and p["optimizer_promotion"] is False
         and p["not_a_learned_generalization_claim"] is True
         and p["lanes"][1]["DEV"]["arms"]["frozen_Z_continuity_0_5"]["paired"]==28
         and p["lanes"][0]["DEV"]["arms"]["new_packed_one_state"]["paired"]==29,
         "PRESERVE_HISTORICAL_CAUSAL_NEGATIVE")
    return base,delta

def predict(lane,arm,graph,base,delta,fixed,fit_params):
    if arm=="strong_fixed":
        if len(graph["roles"])>9:return None,None
        p,work=fixed(graph)
        return bool(p),work
    if lane=="Wingless":
        if arm.startswith("packed_"):
            raw,work=m.packed_frontier(graph,base,delta,int(arm[-1]))
        elif arm=="original_AA_1":
            raw,work=aa.packed_one_state(graph,base,delta)
        elif arm=="original_Z_3":
            raw,work=prior.prior_sparse(graph,base,delta)
        else:raise s.q.Quarantined("F124AB_WING_ARM")
    else:
        if arm=="FIT_soft_head":
            raw,ratio,work=m.soft_continuity(graph,base,delta,fit_params["gamma"])
            score=m.logit(raw,ratio,fit_params["penalty"])
            frozen_raw,orig_work=aa.ygg_original(graph,base,delta)
            need(raw==frozen_raw and
                 all(work[k]==orig_work[k] for k in orig_work),
                 "ORIGINAL_T_SORT_AND_LOGIT_EXACT")
            return bool(score>=0),work
        if arm=="original_T":
            raw,work=aa.ygg_original(graph,base,delta)
        elif arm=="frozen_Z_exact_0_5":
            raw,ratio,frozen,work=aa.ygg_continuity(graph,base,delta)
            t,original_work=aa.ygg_original(graph,base,delta)
            need(frozen==t and all(work[k]==original_work[k] for k in original_work),
                 "ORIGINAL_Z_7_9_SCIENCE")
        else:raise s.q.Quarantined("F124AB_YGG_ARM")
    return bool(raw>=0),work

def stage(lane,phase,base,delta,fixed,selection):
    names=WING_ARMS if lane=="Wingless" else YGG_ARMS
    stats={arm:{"pairs":0,"unsupported":0,"paired":0,"false_positive":0,
                "false_negative":0,"family":{family:{"pairs":0,"unsupported":0,
                  "paired":0,"false_positive":0,"false_negative":0,
                  "by_depth":{}} for family in s.FAMILIES},
                "max_active":0,"max_retained":0,"max_slots_per_node":0,
                "max_counter_slots":0,"edge_or_inspections":0,
                "raw_bit_ops":0,"case_sha256":[]} for arm in names}
    for seed,v,family,pos,neg in s.pairs(lane,phase):
        d=str(len(pos["roles"]))
        for arm in names:
            result=[]
            for graph in (pos,neg):
                prediction,work=predict(lane,arm,graph,base,delta,fixed,selection)
                result.append(prediction)
                if work is None:continue
                r=stats[arm]
                r["max_active"]=max(r["max_active"],work.get("max_active",0))
                r["max_retained"]=max(r["max_retained"],work.get("max_retained",0))
                r["max_slots_per_node"]=max(r["max_slots_per_node"],
                     work.get("max_states_per_node",work.get("state_limit",0)))
                r["max_counter_slots"]=max(r["max_counter_slots"],
                     work.get("soft_counter_slots_max",
                     work.get("continuity_counter_slots_max",0)))
                r["edge_or_inspections"]+=work.get("edge_inspections",
                                                  work.get("public_edge_scans",0))
                r["raw_bit_ops"]+=work.get("raw_bit_reads",
                                          work.get("raw_bit_ops",0))
            row=stats[arm];f=row["family"][family]
            if result[0] is None:
                need(result[1] is None and family=="extended_depth" and
                     arm=="strong_fixed","HISTORICAL_FIXED_DOMAIN_ONLY")
                row["unsupported"]+=1;f["unsupported"]+=1
                continue
            yes,no=result
            row["pairs"]+=1;f["pairs"]+=1
            ok=bool(yes and not no)
            row["paired"]+=int(ok);f["paired"]+=int(ok)
            row["false_positive"]+=int(no);f["false_positive"]+=int(no)
            row["false_negative"]+=int(not yes);f["false_negative"]+=int(not yes)
            by=f["by_depth"].setdefault(d,{"pairs":0,"paired":0})
            by["pairs"]+=1;by["paired"]+=int(ok)
            row["case_sha256"].append(q.digest({"arm":arm,"family":family,
               "phase":phase,"seed":seed,"vector":v,"positive":yes,
               "negative":no}))
        if lane=="Wingless":
            # All three-state packed bins reconstruct original frozen Z
            # evidence/scoring; fail if arithmetic or tie-breaking changes.
            for g in (pos,neg):
                score_p,_=m.packed_frontier(g,base,delta,3)
                score_z,_=prior.prior_sparse(g,base,delta)
                need(score_p==score_z,"THREE_PACKED_SAME_FROZEN_THREE_STATE_LOGIT")
                one,_=m.packed_frontier(g,base,delta,1)
                baseline,_=aa.packed_one_state(g,base,delta)
                need(one==baseline,"ONE_PACKED_SAME_AA_LOGIT")
    need(len(s.pairs(lane,phase))==48,"SOURCE_COMPLETE")
    for arm,row in stats.items():
        required=36 if arm=="strong_fixed" else 48
        need(row["pairs"]==required and row["unsupported"]==48-required
             and len(row["case_sha256"])==required
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil" else
                  row["max_active"]<=192)
             and row["max_counter_slots"]<=16,
             "COMPLETE_CONTROLS_CAPACITY_AND_DENOMINATOR")
        for family in s.FAMILIES:
            f=row["family"][family]
            need(f["pairs"]+f["unsupported"]==12,
                 "ONE_FAMILY_MISSING")
    return {"phase":phase,"total_pairs":48,"family_counts":{f:12 for f in s.FAMILIES},
            "controls":stats,"reference_only_outside_inference":True}

def percentile(seq,q):
    items=sorted(seq);return items[min(len(items)-1,math.ceil(q*len(items))-1)]

def benchmarks(base,delta,fixed):
    selected={f:[] for f in s.FAMILIES}
    for _,_,family,pos,neg in s.pairs("Wingless","DEV"):
        if len(selected[family])<6:selected[family].extend((pos,neg))
    need(all(len(x)==6 for x in selected.values()),"FROZEN_BENCH_GRAPH_CENSUS")
    arms={f"packed_{k}":(lambda g,k=k:m.packed_frontier(g,base,delta,k))
          for k in m.CAPACITIES}
    arms["original_Z_3"]=lambda g:prior.prior_sparse(g,base,delta)
    arms["strong_fixed"]=lambda g:fixed(g)
    obs={name:{"times":[],"peaks":[],"graphs":0} for name in arms}
    i=0
    for family in s.FAMILIES:
        for graph in selected[family]:
            i+=1;order=list(arms)
            random.Random("F124AB/FROZEN-BENCH/v1/"+family+"/"+str(i)).shuffle(order)
            for name in order:
                if name=="strong_fixed" and len(graph["roles"])>9:continue
                f=arms[name]
                f(graph)
                for _ in range(3):
                    start=time.perf_counter_ns();f(graph)
                    obs[name]["times"].append(time.perf_counter_ns()-start)
                gc.collect();tracemalloc.start()
                f(graph)
                _,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                obs[name]["peaks"].append(peak)
                obs[name]["graphs"]+=1
    summary={}
    for name,row in obs.items():
        n=18 if name=="strong_fixed" else 24
        need(row["graphs"]==n and len(row["times"])==n*3
             and len(row["peaks"])==n,"BENCHMARK_SAMPLES")
        summary[name]={"graphs":n,"timed_calls":n*3,
           "median_runtime_ns":int(statistics.median(row["times"])),
           "p95_runtime_ns":percentile(row["times"],.95),
           "median_peak_python_bytes":int(statistics.median(row["peaks"])),
           "p95_peak_python_bytes":percentile(row["peaks"],.95),
           "raw_sample_sha256":q.digest(row)}
    return {"environment":platform.platform(),"python":platform.python_version(),
            "runner":os.environ.get("RUNNER_NAME","unspecified"),
            "sample":"24 equal graph inputs for 1/2/3/Z; 18 supported original-domain fixed graphs; 1 warmup+3 timed runs+1 separate tracemalloc each; frozen arm order",
            "results":summary,"matched_hardware_superiority":False,
            "fixed_control_extended_domain_unsupported":True}

def run(o,t,u,w,x,y,z,aa_path):
    s.frozen()
    from f124ab_soft_hamming_pareto import GAMMAS,PENALTIES
    need(len(GAMMAS)*len(PENALTIES)==25,"FROZEN_GRID")
    base,delta=authentic(o,t,u,w,x,y,z,aa_path)
    fit_Y=s.pairs("Yggdrasil","FIT")
    winner,grid=m.learn_fit(fit_Y,base["Yggdrasil"],delta["Yggdrasil"])
    fixed=prior.original_fixed()
    out={"schema":SCHEMA,"freeze_git_blob":s.FREEZE_BLOB,
         "parent_raw_sha256":AA_RAW,"frozen_model_source_unchanged":True,
         "training_sources_only_new_FIT":True,
         "first_DEV_only_after_FIT_selection":True,"scientific_acceptance":False,
         "optimizer_promotion":False,"protected_first_use":False,
         "matched_compute_superiority_proven":False,"accepted_ref_mutations":0,
         "candidate_fit_selection":winner,"fit_grid":grid,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,"FIT":stage(lane,"FIT",base[lane],delta[lane],fixed,winner),
             "DEV":stage(lane,"DEV",base[lane],delta[lane],fixed,winner),
             "original_weights_sha256":q.digest(base[lane]),
             "original_delta_sha256":q.digest(delta[lane])}
        if lane=="Wingless":row["benchmarks"]=benchmarks(base[lane],delta[lane],fixed)
        out["lanes"].append(row)
    return out

def main():
    ap=argparse.ArgumentParser()
    for key in ("o","t","u","w","x","y","z","aa","output"):
        ap.add_argument("--"+key,required=True)
    p=ap.parse_args();destination=Path(p.output)
    need(destination.parent.is_dir() and not destination.exists(),
         "FAIL_CLOSED_IMMUTABLE_NEW_OUTPUT")
    result=run(p.o,p.t,p.u,p.w,p.x,p.y,p.z,p.aa)
    raw=json.dumps(result,indent=2,sort_keys=True).encode()+b"\n"
    with destination.open("xb") as f:f.write(raw)
    print("F124AB_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        d=lane["DEV"]["controls"]
        if lane["lane"]=="Wingless":
            print("F124AB_WING_DEV="+",".join(
              k+":"+str(d[k]["paired"])+"/"+str(d[k]["pairs"])
              for k in ("packed_1","packed_2","packed_3","original_Z_3","strong_fixed")))
        else:
            print("F124AB_YGG_DEV="+",".join(
              k+":"+str(d[k]["paired"])+"/"+str(d[k]["pairs"])
              for k in ("FIT_soft_head","original_T","frozen_Z_exact_0_5","strong_fixed")))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AB_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)

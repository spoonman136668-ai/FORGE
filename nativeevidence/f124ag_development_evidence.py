"""F124-AG authentic 13-parent historical custody and new FIT/DEV experiment.

Models see graph source and their original frozen weights, never paired labels.
Return results independently for 48 pairs in four source-fixed transfer domains.
No science acceptance or post-DEV selection. All negatives retained.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124ag_frozen_source as frozen
import f124ag_transition_models as candidate
import f124af_development_evidence as prior
import f124ae_scoring_transfer as old
import f124aa_development_evidence as aa_evidence
import f124q_independent_binding as q

SCHEMA="forge.research.f124ag.prospective-transition-consistency.v1"
PARENT_RAW="42c8c34a67f02efbfac26ab030ecb1db0361a335f25b0a0540442562d6aa9e3c"
Y_ARMS=("new_hop_consistency","AF_AD_anchor10","AB_unanchored","original_T","original_Z","strong_fixed")
W_ARMS=("new_packed_hop","AF_original_one","AB_original_three","strong_fixed")

def need(ok,tag):frozen.need(ok,"RECEIPT_"+tag)

def custody(paths):
    bases,deltas=prior.ancestry(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_RAW,"AF_AUTHENTIC_SOURCE_RAW_SHA256")
    report=json.loads(raw)
    need(report["schema"]=="forge.research.f124af.authentic-terminal-contrast-one-state-margin-development.v1"
         and report["freeze_git_blob"]=="646b203a33929e0f63a31db5b11f0850fec0b954"
         and report["protected_first_use"] is False
         and report["independent_science_acceptance"] is False
         and report["optimizer_promotion"] is False
         and report["selected"]["Yggdrasil"]["lambda"]==0
         and report["selected"]["Wingless"]["beta"]==0
         and report["lanes"][1]["DEV"]["arms"]["new_contrast"]["paired"]==25
         and report["lanes"][0]["DEV"]["arms"]["new_margin"]["paired"]==16,
         "AF_NEGATIVE_EVIDENCE_PRESERVED")
    return bases,deltas

def predict(lane,arm,g,base,delta,choice,fixed):
    if arm=="strong_fixed":
        if len(g["roles"])>9:return None,None,None
        label,work=fixed(g)
        return bool(label),work,None
    if lane=="Yggdrasil":
        if arm=="new_hop_consistency":
            raw_score,raw,ratio,work=candidate.ygg_transition(
                    g,base,delta,choice["Yggdrasil"]["eta"])
            # Source-blind zero-penalty historical witness always available,
            # but compare exact original control below at eta=0.
            score=raw_score
        elif arm=="AF_AD_anchor10":
            score,raw,ratio,work=old.anchored_score(g,base,delta,10)
        elif arm=="AB_unanchored":
            score,raw,ratio,work=old.anchored_score(g,base,delta,16)
        elif arm=="original_T":
            score,work=old.frozen_t(g,base,delta)
        else:
            score,raw,ratio,work=old.frozen_z(g,base,delta)
    else:
        if arm=="new_packed_hop":
            score,work=candidate.wing_transition(
                g,base,delta,choice["Wingless"]["eta"])
        elif arm=="AF_original_one":
            score,work=old.frozen_packed(g,base,delta)
        else:
            score,work=old.frozen_three(g,base,delta)
    return bool(score>=0),work,score

def phase(lane,period,base,delta,choice,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    res={arm:{"pairs":0,"unsupported":0,"correct_pairs":0,"FP":0,"FN":0,
          "per_family":{family:{"pairs":0,"unsupported":0,"correct_pairs":0,
                           "FP":0,"FN":0,"depth":{}}
                        for family in frozen.FAMILIES},
          "max_active":0,"max_retained":0,"max_slots_per_node":0,
          "edge_operations":0,"raw_bit_reads":0,
          "extra_transition_comparisons":0,"extra_violation_cost":0,
          "case_sha256":[]} for arm in arms}
    source=frozen.pairs(lane,period)
    for seed,vector,fam,p,n in source:
        depth=str(len(p["roles"]))
        for arm in arms:
            outcomes=[]
            for graph in (p,n):
                label,work,score=predict(lane,arm,graph,base,delta,choice,fixed)
                outcomes.append(label)
                if work is None:continue
                record=res[arm]
                record["max_active"]=max(record["max_active"],work.get("max_active",0))
                record["max_retained"]=max(record["max_retained"],work.get("max_retained",0))
                record["max_slots_per_node"]=max(record["max_slots_per_node"],
                                                 work.get("max_states_per_node",0))
                record["edge_operations"]+=work.get("edge_inspections",work.get("public_edge_scans",0))
                record["raw_bit_reads"]+=work.get("raw_bit_reads",work.get("raw_bit_ops",0))
                record["extra_transition_comparisons"]+=work.get(
                    "transition_packed_channel_comparisons",
                    work.get("transition_penalty_evaluations",0))
                record["extra_violation_cost"]+=work.get(
                    "sum_excess_channel_mismatch",
                    work.get("sum_transition_violation_bits",0))
            rec=res[arm];family=rec["per_family"][fam]
            if outcomes[0] is None:
                need(outcomes[1] is None and arm=="strong_fixed"
                     and fam in ("long_dense_13_15","extended_13_15"),
                     "ORIGINAL_FIXED_UNSUPPORTED_ONLY")
                rec["unsupported"]+=1;family["unsupported"]+=1
                continue
            yes,no=outcomes
            good=int(yes and not no)
            for target in (rec,family):
                target["pairs"]+=1;target["correct_pairs"]+=good
                target["FP"]+=int(no);target["FN"]+=int(not yes)
            df=family["depth"].setdefault(depth,{"pairs":0,"correct_pairs":0,"FP":0,"FN":0})
            df["pairs"]+=1;df["correct_pairs"]+=good
            df["FP"]+=int(no);df["FN"]+=int(not yes)
            rec["case_sha256"].append(q.digest({
                "period":period,"seed":seed,"vector":vector,"family":fam,
                "arm":arm,"positive":yes,"negative":no}))
        # Historical baseline must be reproducced even when a different
        # eta is FIT selected, without altering the new model's prediction.
        if lane=="Yggdrasil":
            for graph in (p,n):
                a,raw,ratio,work=candidate.ygg_transition(graph,base,delta,0.)
                b,oldraw,oldratio,w=old.anchored_score(graph,base,delta,10)
                need((a,raw,ratio)==(b,oldraw,oldratio)
                     and all(work[k]==w[k] for k in w),
                     "ZERO_ETA_ORIGINAL_T_PRESERVED")
        else:
            for graph in (p,n):
                a,work=candidate.wing_transition(graph,base,delta,0.)
                b,w=old.frozen_packed(graph,base,delta)
                need(a==b and all(work[k]==w[k] for k in w),
                     "ZERO_ETA_ORIGINAL_AA_PRESERVED")
        # Source admission remains independent from every model prediction.
        need(frozen.prior.parent.routes15(
             p,relaxed=fam=="one_bit_relaxed_keys")==1
             and frozen.prior.parent.routes15(
             n,relaxed=fam=="one_bit_relaxed_keys")==0,
             "PUBLIC_GROUND_TRUTH_ONLY_AFTER_MODEL")
    need(len(source)==48,"PROSPECTIVE_COMPLETE")
    for arm,row in res.items():
        denom=24 if arm=="strong_fixed" else 48
        need(row["pairs"]==denom and row["unsupported"]==48-denom
             and len(row["case_sha256"])==denom
             and all(d["pairs"]+d["unsupported"]==12
                     for d in row["per_family"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),"SOURCE_AND_HARD_BUDGET")
        if arm in ("new_packed_hop","AF_original_one"):
            need(row["max_active"]<=64 and row["max_slots_per_node"]==1,
                 "WING_SINGLE_PACKED_SLOT")
    return {"period":period,"source_pairs":48,"controls":res,
            "source_reference_never_used_by_predictor":True}

def percentile(a,p):
    data=sorted(a)
    return data[min(len(data)-1,math.ceil(len(data)*p)-1)]

def benchmark(base,delta,eta,fixed):
    samples={family:[] for family in frozen.FAMILIES}
    for _,_,fam,p,n in frozen.pairs("Wingless","DEV"):
        if len(samples[fam])<6:samples[fam].extend((p,n))
    need(all(len(x)==6 for x in samples.values()),"SAME_FOUR_FAMILY_GRAPH_INPUTS")
    funcs={"new_packed_hop":lambda g:candidate.wing_transition(g,base,delta,eta),
           "AF_original_one":lambda g:old.frozen_packed(g,base,delta),
           "AB_original_three":lambda g:old.frozen_three(g,base,delta),
           "strong_fixed":lambda g:fixed(g)}
    seen={arm:{"timings":[],"allocations":[],"graphs":0} for arm in funcs}
    count=0
    for family in frozen.FAMILIES:
        for graph in samples[family]:
            count+=1
            order=list(funcs)
            random.Random("F124AG/frozen-resource/"+family+"/"+str(count)).shuffle(order)
            for arm in order:
                if arm=="strong_fixed" and len(graph["roles"])>9:continue
                fn=funcs[arm];fn(graph)
                for _ in range(3):
                    t=time.perf_counter_ns();fn(graph)
                    seen[arm]["timings"].append(time.perf_counter_ns()-t)
                gc.collect()
                tracemalloc.start()
                fn(graph)
                _,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                seen[arm]["allocations"].append(peak)
                seen[arm]["graphs"]+=1
    output={}
    for arm,rec in seen.items():
        n=12 if arm=="strong_fixed" else 24
        need(rec["graphs"]==n and len(rec["timings"])==3*n
             and len(rec["allocations"])==n,"RESOURCE_CENSUS")
        output[arm]={"graphs":n,"timed_calls":n*3,
            "p50_runtime_ns":int(statistics.median(rec["timings"])),
            "p95_runtime_ns":percentile(rec["timings"],.95),
            "p50_python_peak_bytes":int(statistics.median(rec["allocations"])),
            "p95_python_peak_bytes":percentile(rec["allocations"],.95),
            "sample_sha256":q.digest(rec)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),"os":platform.platform(),
            "python":platform.python_version(),"same_new_24_graphs_for_three_learned":True,
            "original_strong_fixed_restricted_to_12_supported_graphs":True,
            "scientific_hardware_matched_superiority":False,"arms":output}

def run(paths):
    frozen.frozen()
    bases,deltas=custody(paths)
    y,ygrid=candidate.fit("Yggdrasil",frozen.pairs("Yggdrasil","FIT"),
                         bases["Yggdrasil"],deltas["Yggdrasil"])
    w,wgrid=candidate.fit("Wingless",frozen.pairs("Wingless","FIT"),
                         bases["Wingless"],deltas["Wingless"])
    choice={"Yggdrasil":y,"Wingless":w}
    fixed=aa_evidence.original_fixed()
    report={"schema":SCHEMA,"freeze_git_blob":frozen.FREEZE_BLOB,
          "original_AF_raw_sha256":PARENT_RAW,"original_weights_intact":True,
          "true_new_FIT_before_first_DEV":True,"protected_first_use":False,
          "independent_science_acceptance":False,"optimizer_promotion":False,
          "accepted_ref_mutations":0,"matched_compute_superiority":False,
          "selected":choice,"FIT_grid":{"Yggdrasil":ygrid,"Wingless":wgrid},
          "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,"FIT":phase(lane,"FIT",bases[lane],deltas[lane],choice,fixed),
             "DEV":phase(lane,"DEV",bases[lane],deltas[lane],choice,fixed),
             "original_weights_sha256":q.digest(bases[lane]),
             "original_deltas_sha256":q.digest(deltas[lane])}
        if lane=="Wingless":
            row["resources"]=benchmark(bases[lane],deltas[lane],w["eta"],fixed)
        report["lanes"].append(row)
    return report

def main():
    p=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae","af","output"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args();dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),"NO_OVERWRITE_RECEIPT")
    report=run([getattr(args,n) for n in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae","af")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as f:f.write(raw)
    print("F124AG_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        d=lane["DEV"]["controls"]
        if lane["lane"]=="Wingless":
            print("F124AG_WING_DEV=new:"+str(d["new_packed_hop"]["correct_pairs"])+
                  "/48;old:"+str(d["AF_original_one"]["correct_pairs"])+
                  "/48;eta:"+str(report["selected"]["Wingless"]["eta"]))
        else:
            print("F124AG_YGG_DEV=new:"+str(d["new_hop_consistency"]["correct_pairs"])+
                  "/48;AD:"+str(d["AF_AD_anchor10"]["correct_pairs"])+
                  "/48;eta:"+str(report["selected"]["Yggdrasil"]["eta"]))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as error:
        print("F124AG_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)

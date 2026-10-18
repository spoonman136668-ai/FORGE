"""F124-AE source-authenticated 11-parent transfer and one-state readout.

No label or ground-truth path enters a predictor. Long-depth external scorer
only runs after all original source-blind model predictions. Original frozen
controls retained on every supported input with separate denominators.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
from collections import defaultdict
import f124ae_frozen_source as source
import f124ae_scoring_transfer as model
import f124ad_development_evidence as prior
import f124aa_development_evidence as aa_evidence
import f124q_independent_binding as q
import f124ab_soft_hamming_pareto as ab
import f124aa_packed_transfer as aa

SCHEMA="forge.research.f124ae.frozen-13-15-transfer-and-one-state-score.v1"
AD_RAW="2a22462f0292f8fe23df3c5bae21bbd2e2a0e9c6e92f21d2f8179cd621c4de3f"
YGG_ARMS=("AD_anchor10","AB_anchor16","T_original","Z_exact","strong_fixed")
WING_ARMS=("FIT_threshold","original_one_state","original_three","strong_fixed")

def need(ok,name):source.need(ok,"EVIDENCE_"+name)

def custody(paths):
    base,delta=prior.custody(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AD_RAW,"AUTHENTIC_AD_PARENT_SHA")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124ad.authentic-long-readout-and-4bit-fingerprint.v1"
         and p["freeze_git_blob"]=="69a0a65c561e2c901ea2ad13310657cc16e6f997"
         and p["scientific_acceptance"] is False
         and p["protected_first_use"] is False
         and p["optimizer_promotion"] is False
         and p["selections"]["Yggdrasil"]["anchor"]==10
         and p["selections"]["Wingless"]["alpha"]==0
         and p["lanes"][1]["DEV"]["arms"]["new_anchored"]["paired"]==41
         and p["lanes"][0]["DEV"]["arms"]["new_4bit"]["paired"]==28,
         "PRESERVE_AD_LEARNED_RESULT_AND_NEGATIVE")
    return base,delta

def witness(graph,relaxed):
    """Scorer only. Read from public graph after ALL model scores."""
    frontier=[(graph["start"],None,[])]
    for role in graph["roles"]:
        after=[]
        for node,carried,path in frontier:
            for edge in graph["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                mismatch=0 if carried is None else sum(
                    a!=b for a,b in zip(carried,edge["src_bits"]))
                if carried is None or mismatch<=(1 if relaxed else 0):
                    after.append((edge["to"],tuple(edge["dst_bits"]),
                                  path+[(edge["to"],tuple(edge["dst_bits"]))]))
                    need(len(after)<=256,"PUBLIC_REFERENCE_FRONTIER")
        frontier=after
    selected=[p for node,_,p in frontier if node==graph["target"]]
    need(len(selected)==1,"EXACT_PUBLIC_REFERENCE_POSITIVE")
    return selected[0]

def classify(lane,arm,g,base,delta,bias,fixed):
    if arm=="strong_fixed":
        if len(g["roles"])>9:return None,None,None
        p,work=fixed(g)
        return bool(p),work,None
    if lane=="Yggdrasil":
        if arm=="AD_anchor10":
            score,raw,ratio,work=model.anchored_score(g,base,delta,10)
            # Original raw T and original AB exact work equality.
            t,tw=model.frozen_t(g,base,delta)
            unchanged,rr,rw=model.frozen_ab_soft(g,base,delta)
            need(raw==t==unchanged and ratio==rr and work==rw
                 and all(work[k]==tw[k] for k in tw),
                 "EXACT_ORIGINAL_T_RAW_AND_7_9_CELLS")
        elif arm=="AB_anchor16":
            score,raw,ratio,work=model.anchored_score(g,base,delta,16)
        elif arm=="T_original":
            score,work=model.frozen_t(g,base,delta)
        else:
            score,raw,ratio,work=model.frozen_z(g,base,delta)
    else:
        if arm=="FIT_threshold":
            score,raw,work=model.wing_threshold(g,base,delta,bias)
            old,original_work=model.frozen_packed(g,base,delta)
            need(raw==old and work==original_work,"ORIGINAL_ONE_STATE_SCORE")
        elif arm=="original_one_state":
            score,work=model.frozen_packed(g,base,delta)
        else:
            score,work=model.frozen_three(g,base,delta)
    return bool(score>=0),work,score

def stage(lane,phase,base,delta,bias,fixed):
    arms=YGG_ARMS if lane=="Yggdrasil" else WING_ARMS
    rows={name:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
                "family":{f:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
                          "depth":{}} for f in source.FAMILIES},
                "max_active":0,"max_retained":0,"max_states_per_node":0,
                "operations":0,"bit_reads":0,"case_sha256":[]} for name in arms}
    posthoc={"positives":0,"reference_valid":0,"by_family":{}}
    cases=source.pairs(lane,phase)
    for seed,vec,fam,pos,neg in cases:
        d=str(len(pos["roles"]))
        outcomes={}
        for arm in arms:
            pair=[]
            for g in (pos,neg):
                decision,work,logit=classify(lane,arm,g,base,delta,bias,fixed)
                pair.append((decision,logit))
                if work is not None:
                    row=rows[arm]
                    row["max_active"]=max(row["max_active"],work.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
                    row["max_states_per_node"]=max(row["max_states_per_node"],
                        work.get("max_states_per_node",work.get("state_limit",0)))
                    row["operations"]+=work.get("edge_inspections",work.get(
                                              "public_edge_scans",0))
                    row["bit_reads"]+=work.get("raw_bit_reads",work.get(
                                              "raw_bit_ops",0))
            a,b=pair
            row=rows[arm];family=row["family"][fam]
            if a[0] is None:
                need(b[0] is None and arm=="strong_fixed"
                     and fam in ("long_dense_13_15","extended_13_15"),
                     "ONLY_UNSUPPORTED_ORIGINAL_FIXED")
                row["unsupported"]+=1;family["unsupported"]+=1
                continue
            outcomes[arm]=pair
            yes,no=a[0],b[0]
            correct=int(yes and not no)
            for target in (row,family):
                target["pairs"]+=1;target["paired"]+=correct
                target["FP"]+=int(no);target["FN"]+=int(not yes)
            depth=family["depth"].setdefault(d,{"pairs":0,"paired":0,
                          "FP":0,"FN":0})
            depth["pairs"]+=1;depth["paired"]+=correct
            depth["FP"]+=int(no);depth["FN"]+=int(not yes)
            row["case_sha256"].append(q.digest({
                "seed":seed,"vector":vec,"phase":phase,
                "family":fam,"arm":arm,"positive":yes,"negative":no}))
        # Original model/domain parity on nonextended cases.
        if len(pos["roles"])<=9:
            for g in (pos,neg):
                if lane=="Yggdrasil":
                    observed,ratio,work=model.frozen_ab_soft(g,base,delta)
                    base_score,original_ratio,original_work=ab.soft_continuity(
                        g,base,delta,.25)
                    need(observed==base_score and ratio==original_ratio
                         and work==original_work,
                         "ORIGINAL_AB_BITWISE_PARITY")
                else:
                    original,work=aa.packed_one_state(g,base,delta)
                    reused,copy=model.frozen_packed(g,base,delta)
                    need(original==reused and work==copy,
                         "ORIGINAL_PACKED_PARITY")
        route=witness(pos,fam=="one_bit_relaxed_keys")
        posthoc["positives"]+=1
        posthoc["reference_valid"]+=int(len(route)==len(pos["roles"]))
        fam_stats=posthoc["by_family"].setdefault(fam,{"pairs":0,"long":0})
        fam_stats["pairs"]+=1;fam_stats["long"]+=int(len(route)>=13)
    for name,row in rows.items():
        required=24 if name=="strong_fixed" else 48
        need(row["pairs"]==required and row["unsupported"]==48-required
             and len(row["case_sha256"])==required
             and all(row["family"][f]["pairs"]+row["family"][f]["unsupported"]==12
                 for f in source.FAMILIES)
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "ORIGINAL_COHORT_AND_MEMORY_BUDGET")
        if name in ("FIT_threshold","original_one_state"):
            need(row["max_states_per_node"]==1
                 and row["max_active"]<=64,"SINGLE_STATE_NO_CAPACITY_INCREASE")
    need(posthoc["positives"]==48 and posthoc["reference_valid"]==48,
         "ORACLE_OUTSIDE_MODEL_COMPLETE")
    return {"phase":phase,"pairs":48,"controls":rows,
            "posthoc_public_reference":posthoc}

def quantile(a,p):
    x=sorted(a);return x[min(len(x)-1,math.ceil(len(x)*p)-1)]

def resource(base,delta,bias,fixed):
    samples={f:[] for f in source.FAMILIES}
    for _,_,fam,pos,neg in source.pairs("Wingless","DEV"):
        if len(samples[fam])<6:samples[fam].extend((pos,neg))
    need(all(len(v)==6 for v in samples.values()),"RESOURCE_SOURCE_24")
    arms={"FIT_threshold":lambda g:model.wing_threshold(g,base,delta,bias),
          "original_one_state":lambda g:model.frozen_packed(g,base,delta),
          "original_three":lambda g:model.frozen_three(g,base,delta),
          "strong_fixed":lambda g:fixed(g)}
    collected={name:{"timings":[],"allocations":[],"graphs":0} for name in arms}
    i=0
    for fam in source.FAMILIES:
        for g in samples[fam]:
            i+=1
            order=list(arms)
            random.Random("F124AE/resource/"+fam+"/"+str(i)).shuffle(order)
            for name in order:
                if name=="strong_fixed" and len(g["roles"])>9:continue
                fn=arms[name]
                fn(g)
                for _ in range(3):
                    t=time.perf_counter_ns();fn(g)
                    collected[name]["timings"].append(time.perf_counter_ns()-t)
                gc.collect();tracemalloc.start()
                fn(g)
                _,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                collected[name]["allocations"].append(peak)
                collected[name]["graphs"]+=1
    summary={}
    for name,row in collected.items():
        n=12 if name=="strong_fixed" else 24
        need(row["graphs"]==n and len(row["timings"])==3*n and
             len(row["allocations"])==n,"RESOURCE_DENOMINATOR")
        summary[name]={"graphs":n,"timed_repetitions":3*n,
             "median_ns":int(statistics.median(row["timings"])),
             "p95_ns":quantile(row["timings"],.95),
             "median_peak_bytes":int(statistics.median(row["allocations"])),
             "p95_peak_bytes":quantile(row["allocations"],.95),
             "sample_sha256":q.digest(row)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
            "python":platform.python_version(),"host":platform.platform(),
            "original_fixed_only_7_to_9_supported":True,
            "same_24_public_graphs_between_new_and_one_state":True,
            "protected_resource_matched_superiority":False,
            "results":summary}

def run(paths):
    source.frozen()
    bases,deltas=custody(paths)
    bias_fit,bias_grid=model.fit_threshold(
       source.pairs("Wingless","FIT"),
       bases["Wingless"],deltas["Wingless"])
    bias=bias_fit["bias"]
    fixed=aa_evidence.original_fixed()
    result={"schema":SCHEMA,"freeze_git_blob":source.FREEZE_BLOB,
           "original_AD_raw_sha256":AD_RAW,
           "original_weights_and_inference_unchanged":True,
           "fresh_fit_before_dev":True,"first_prospective_dev":True,
           "protected_first_use":False,"scientific_acceptance":False,
           "optimizer_promotion":False,"accepted_ref_mutations":0,
           "matched_resource_superiority":False,
           "wing_fit_selection":bias_fit,"wing_fit_grid":bias_grid,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        data={"lane":lane,"FIT":stage(lane,"FIT",bases[lane],deltas[lane],bias,fixed),
              "DEV":stage(lane,"DEV",bases[lane],deltas[lane],bias,fixed),
              "weights_sha256":q.digest(bases[lane]),
              "delta_sha256":q.digest(deltas[lane])}
        if lane=="Wingless":
            data["resource"]=resource(bases[lane],deltas[lane],bias,fixed)
        result["lanes"].append(data)
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","z","aa","ab","ac","ad","output"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args();path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),"NEVER_OVERWRITE_RECEIPT")
    result=run([getattr(a,n) for n in (
        "o","t","u","w","x","y","z","aa","ab","ac","ad")])
    raw=json.dumps(result,indent=2,sort_keys=True).encode()+b"\n"
    with path.open("xb") as output:output.write(raw)
    print("F124AE_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        arms=lane["DEV"]["controls"]
        if lane["lane"]=="Wingless":
            print("F124AE_WING_DEV="+str(arms["FIT_threshold"]["paired"])+
                  "/48;one="+str(arms["original_one_state"]["paired"])+
                  "/48;bias="+str(bias))
        else:
            print("F124AE_YGG_DEV=AD="+str(arms["AD_anchor10"]["paired"])+
                  "/48;AB="+str(arms["AB_anchor16"]["paired"])+
                  "/48;T="+str(arms["T_original"]["paired"])+"/48")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AE_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)

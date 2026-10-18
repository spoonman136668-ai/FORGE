"""F124-AD authentic ten-parent receipt, frozen FIT selection and fresh DEV.

All source labels and reference-path checks are in evaluator after source-
blind predictions. Parent O..AC artifacts and SHA checks happen in workflow.
One packed state/node and original Yggdrasil 7+9 hard cells preserved.
"""
from __future__ import annotations
from collections import defaultdict
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124ad_frozen_source as f
import f124ad_depth_fingerprint as model
import f124ac_development_evidence as prior
import f124aa_packed_transfer as aa
import f124ab_soft_hamming_pareto as ab
import f124q_independent_binding as q
import f124z_sparse_continuity as z
import f124aa_development_evidence as aa_evidence

SCHEMA="forge.research.f124ad.authentic-long-readout-and-4bit-fingerprint.v1"
AC_RAW="1ab3f8228e6f361783abf9fd052d28d60462432511653978b8b3ce966d609dc7"
WING_ARMS=("new_4bit","original_AA_1","original_AB_3","strong_fixed")
YGG_ARMS=("new_anchored","original_AB_soft","original_T","original_Z_exact","strong_fixed")

def need(x,name):f.need(x,"EVIDENCE_"+name)

def custody(paths):
    bases,deltas=prior.original_custody(*paths[:-1])
    ac_raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(ac_raw).hexdigest()==AC_RAW,"AUTHENTIC_AC_RAW")
    old=json.loads(ac_raw)
    need(old["schema"]=="forge.research.f124ac.fresh-long-depth-packed-failure-diagnostics.v1"
         and old["freeze_git_blob"]=="be5f9a3121beca097ca81f4451e73c1927aae595"
         and old["optimizer_promotion"] is False
         and old["protected_first_use"] is False
         and old["lanes"][1]["DEV"]["arms"]["soft_AB"]["paired"]==39
         and old["lanes"][0]["DEV"]["arms"]["one_state_AB"]["paired"]==30,
         "AC_NEGATIVE_RETAINED")
    return bases,deltas

def forward(lane,arm,g,base,delta,selection,fixed):
    if arm=="strong_fixed":
        if len(g["roles"])>9:return None,None,None
        decision,work=fixed(g)
        return bool(decision),work,None
    if lane=="Yggdrasil":
        if arm=="new_anchored":
            logit,raw,ratio,work=model.anchored_readout(
                g,base,delta,selection["Yggdrasil"]["anchor"])
            original_raw,original_ratio,orig_work=ab.soft_continuity(
                g,base,delta,.25)
            need(raw==original_raw and ratio==original_ratio and
                 work==orig_work,"ORIGINAL_AB_UNCHANGED_7_9")
        elif arm=="original_AB_soft":
            raw,ratio,work=ab.soft_continuity(g,base,delta,.25)
            logit=ab.logit(raw,ratio,.25)
        elif arm=="original_T":
            logit,work=aa.ygg_original(g,base,delta)
        else:
            logit,_,_,work=aa.ygg_continuity(g,base,delta)
    else:
        if arm=="new_4bit":
            logit,work=model.packed_with_fingerprint(
                g,base,delta,selection["Wingless"]["alpha"])
        elif arm=="original_AA_1":
            logit,work=aa.packed_one_state(g,base,delta)
        else:
            logit,work=ab.packed_frontier(g,base,delta,3)
    return bool(logit>=0),work,logit

def score(lane,phase,base,delta,selection,fixed):
    arms=WING_ARMS if lane=="Wingless" else YGG_ARMS
    stats={name:{"applicable_pairs":0,"unsupported_pairs":0,
           "paired":0,"FP":0,"FN":0,
           "by_family":{fam:{"applicable_pairs":0,"unsupported_pairs":0,
                 "paired":0,"FP":0,"FN":0,"by_depth":{}}
                 for fam in f.FAMILIES},
           "max_active":0,"max_retained":0,"max_fingerprint_bits":0,
           "max_total_key_bits":0,"edge_operations":0,"bit_operations":0,
           "fingerprint_compares":0,"case_sha256":[]} for name in arms}
    survival={"positives":0,"terminal_reference_survived":0,
              "terminal_reference_lost":0,
              "extended_survived_and_new_false_negative":0}
    for seed,vec,family,pos,neg in f.pairs(lane,phase):
        depths=len(pos["roles"])
        decisions={}
        for arm in arms:
            outcomes=[]
            for graph in (pos,neg):
                decision,work,logit=forward(lane,arm,graph,base,delta,
                                            selection,fixed)
                outcomes.append((decision,logit))
                if work is None:continue
                r=stats[arm]
                r["max_active"]=max(r["max_active"],work.get("max_active",0))
                r["max_retained"]=max(r["max_retained"],work.get("max_retained",0))
                r["max_fingerprint_bits"]=max(r["max_fingerprint_bits"],
                    work.get("max_fingerprint_bits_per_state",0))
                r["max_total_key_bits"]=max(r["max_total_key_bits"],
                    work.get("max_total_key_bits_per_state",0))
                r["edge_operations"]+=work.get("edge_inspections",
                                               work.get("public_edge_scans",0))
                r["bit_operations"]+=work.get("raw_bit_reads",
                                              work.get("raw_bit_ops",0))
                r["fingerprint_compares"]+=work.get("fingerprint_comparisons",0)
            out=stats[arm];fam=out["by_family"][family]
            yes,no=outcomes
            if yes[0] is None:
                need(arm=="strong_fixed" and family=="extended_depth"
                     and no[0] is None,"FIXED_UNSUPPORTED_ONLY")
                out["unsupported_pairs"]+=1;fam["unsupported_pairs"]+=1
                continue
            decisions[arm]=(yes,no)
            paired=int(yes[0] and not no[0])
            out["applicable_pairs"]+=1;fam["applicable_pairs"]+=1
            out["paired"]+=paired;fam["paired"]+=paired
            out["FP"]+=int(no[0]);fam["FP"]+=int(no[0])
            out["FN"]+=int(not yes[0]);fam["FN"]+=int(not yes[0])
            d=fam["by_depth"].setdefault(str(depths),{"pairs":0,"paired":0})
            d["pairs"]+=1;d["paired"]+=paired
            out["case_sha256"].append(q.digest({
                "arm":arm,"family":family,"seed":seed,"vector":vec,
                "phase":phase,"positive":yes[0],"negative":no[0]}))
        if lane=="Wingless":
            # alpha0 is an absolute original-model regression on all cases;
            # the selected alternative does not modify that frozen control.
            original,_=aa.packed_one_state(pos,base,delta)
            zero,_=model.packed_with_fingerprint(pos,base,delta,0.)
            original_neg,_=aa.packed_one_state(neg,base,delta)
            zero_neg,_=model.packed_with_fingerprint(neg,base,delta,0.)
            need((original,original_neg)==(zero,zero_neg),
                 "ZERO_ALPHA_ORIGINAL_BITWISE_SCORE")
        else:
            original,ratio,ow=ab.soft_continuity(pos,base,delta,.25)
            unchanged,raw,newratio,newwork=model.anchored_readout(
                pos,base,delta,16)
            need(unchanged==ab.logit(original,ratio,.25)
                 and original==raw and ratio==newratio and ow==newwork,
                 "ANCHOR16_ORIGINAL_SCORE")
        # Evaluate causal reference only once scoring of both labels ends.
        if lane=="Yggdrasil":
            reference=prior.public_reference(
                pos,relaxed=family=="one_bit_relaxed_keys")
            _,_,_,_,trace=prior.obs.observe_ygg(pos,base,delta)
            joined=prior.causal_join(trace,reference)
            survival["positives"]+=1
            survived=joined["reference_survived_final"]
            survival["terminal_reference_survived"]+=int(survived)
            survival["terminal_reference_lost"]+=int(not survived)
            if depths>9 and survived and not decisions["new_anchored"][0][0]:
                survival["extended_survived_and_new_false_negative"]+=1
    for arm,row in stats.items():
        n=36 if arm=="strong_fixed" else 48
        need(row["applicable_pairs"]==n
             and row["unsupported_pairs"]==48-n
             and len(row["case_sha256"])==n
             and all(row["by_family"][k]["applicable_pairs"]+
                     row["by_family"][k]["unsupported_pairs"]==12
                     for k in f.FAMILIES)
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "SOURCE_CAPACITY_AND_CONTROL_CENSUS")
        if arm=="new_4bit":
            need(row["max_active"]<=64 and row["max_fingerprint_bits"]==4
                 and row["max_total_key_bits"]==16,"FOUR_BIT_PER_NODE_LIMIT")
    if lane=="Yggdrasil":need(survival["positives"]==48,"PATH_CENSUS")
    return {"phase":phase,"pairs":48,"arms":stats,
            "posthoc_reference":{"scorer_only":True,**survival}}

def pct(items,p):
    ordered=sorted(items)
    return ordered[min(len(ordered)-1,math.ceil(len(ordered)*p)-1)]

def resources(base,delta,selected,fixed):
    by_family={fam:[] for fam in f.FAMILIES}
    for _,_,fam,p,n in f.pairs("Wingless","DEV"):
        if len(by_family[fam])<6:by_family[fam].extend((p,n))
    need(all(len(v)==6 for v in by_family.values()),"FROZEN_RESOURCE_GRAPHS")
    arms={
      "new_4bit":lambda g:model.packed_with_fingerprint(g,base,delta,selected),
      "original_AA_1":lambda g:aa.packed_one_state(g,base,delta),
      "original_AB_3":lambda g:ab.packed_frontier(g,base,delta,3),
      "strong_fixed":lambda g:fixed(g)}
    measures={k:{"time":[],"peak":[],"graphs":0} for k in arms}
    counter=0
    for family in f.FAMILIES:
        for graph in by_family[family]:
            counter+=1
            order=list(arms)
            random.Random("F124AD/FROZEN-RESOURCE/"+family+"/"+str(counter)).shuffle(order)
            for name in order:
                if name=="strong_fixed" and len(graph["roles"])>9:continue
                func=arms[name]
                func(graph)
                for _ in range(3):
                    start=time.perf_counter_ns();func(graph)
                    measures[name]["time"].append(time.perf_counter_ns()-start)
                gc.collect();tracemalloc.start()
                func(graph)
                _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                measures[name]["peak"].append(peak)
                measures[name]["graphs"]+=1
    summary={}
    for name,v in measures.items():
        n=18 if name=="strong_fixed" else 24
        need(v["graphs"]==n and len(v["time"])==n*3 and
             len(v["peak"])==n,"RESOURCE_DENOMINATOR")
        summary[name]={"graphs":n,"calls":n*3,
           "median_ns":int(statistics.median(v["time"])),
           "p95_ns":pct(v["time"],.95),
           "median_peak_bytes":int(statistics.median(v["peak"])),
           "p95_peak_bytes":pct(v["peak"],.95),
           "sample_sha256":q.digest(v)}
    return {"runtime":platform.platform(),"python":platform.python_version(),
            "runner":os.environ.get("RUNNER_NAME","unknown"),
            "source_matched_24_graphs":True,
            "fixed_unsupported_long_family_explicit":True,
            "original_source_graph_memory_included_in_inputs":True,
            "matched_resource_superiority_claim":False,
            "arms":summary}

def run(paths):
    f.frozen()
    base,delta=custody(paths)
    y_sel,y_grid=model.readout_fit(f.pairs("Yggdrasil","FIT"),
                                   base["Yggdrasil"],delta["Yggdrasil"])
    w_sel,w_grid=model.fingerprint_fit(f.pairs("Wingless","FIT"),
                                      base["Wingless"],delta["Wingless"])
    selections={"Wingless":w_sel,"Yggdrasil":y_sel}
    fixed=aa_evidence.original_fixed()
    result={"schema":SCHEMA,"freeze_git_blob":f.FREEZE_BLOB,
            "original_AC_raw_sha256":AC_RAW,
            "model_weights_unchanged":True,"new_FIT_only":True,
            "DEV_first_use_after_FIT":True,
            "scientific_acceptance":False,"protected_first_use":False,
            "optimizer_promotion":False,"accepted_ref_mutations":0,
            "matched_hardware_superiority":False,
            "selections":selections,"FIT_grid":{"Wingless":w_grid,"Yggdrasil":y_grid},
            "lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,"FIT":score(lane,"FIT",base[lane],delta[lane],selections,fixed),
             "DEV":score(lane,"DEV",base[lane],delta[lane],selections,fixed),
             "weights_sha256":q.digest(base[lane]),
             "delta_sha256":q.digest(delta[lane])}
        if lane=="Wingless":
            row["resources"]=resources(base[lane],delta[lane],w_sel["alpha"],fixed)
        result["lanes"].append(row)
    return result

def main():
    ap=argparse.ArgumentParser()
    for opt in ("o","t","u","w","x","y","z","aa","ab","ac","output"):
        ap.add_argument("--"+opt,required=True)
    a=ap.parse_args()
    path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),"NO_RECEIPT_OVERWRITE")
    report=run([getattr(a,k) for k in ("o","t","u","w","x","y","z","aa","ab","ac")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with path.open("xb") as out:out.write(raw)
    print("F124AD_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        v=lane["DEV"]["arms"]
        if lane["lane"]=="Wingless":
            print("F124AD_WING_DEV="+str(v["new_4bit"]["paired"])+"/48;original="+
                  str(v["original_AA_1"]["paired"])+"/48;three="+
                  str(v["original_AB_3"]["paired"])+"/48")
        else:
            print("F124AD_YGG_DEV="+str(v["new_anchored"]["paired"])+"/48;AB="+
                  str(v["original_AB_soft"]["paired"])+"/48;T="+
                  str(v["original_T"]["paired"])+"/48;Z="+
                  str(v["original_Z_exact"]["paired"])+"/48")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AD_FAIL_CLOSED:"+str(e),file=sys.stderr);sys.exit(1)

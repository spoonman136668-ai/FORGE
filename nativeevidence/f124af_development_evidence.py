"""F124-AF authentic lineage, independent FIT selection and 13-15 DEV receipt.

One model sees only one graph; labels and independent reference are scorer-
only. Original hard limits and exact 0-coefficient scores fail closed.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124af_frozen_source as source
import f124af_contrast_margin as model
import f124ae_development_evidence as previous
import f124ae_scoring_transfer as old
import f124aa_development_evidence as aa_evidence
import f124q_independent_binding as q

SCHEMA="forge.research.f124af.authentic-terminal-contrast-one-state-margin-development.v1"
AE_RAW="3b7cce04a678601c503df588ee2f17de6a8116cfcd875347e0395f2632decc40"
Y_ARMS=("new_contrast","AD_anchor10","AB_anchor16","T_original","Z_exact","strong_fixed")
W_ARMS=("new_margin","AA_one_state","AB_three_state","strong_fixed")

def need(ok,label):source.need(ok,"EVIDENCE_"+label)

def ancestry(paths):
    base,delta=previous.custody(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AE_RAW,"AUTHENTIC_AE_SHA")
    record=json.loads(raw)
    need(record["schema"]=="forge.research.f124ae.frozen-13-15-transfer-and-one-state-score.v1"
         and record["freeze_git_blob"]=="248666af8425bb786269a61f047f43c494be8a3e"
         and record["scientific_acceptance"] is False
         and record["optimizer_promotion"] is False
         and record["protected_first_use"] is False
         and record["lanes"][1]["DEV"]["controls"]["AD_anchor10"]["paired"]==28
         and record["lanes"][0]["DEV"]["controls"]["FIT_threshold"]["paired"]==17,
         "PARENT_DEVELOPMENT_NEGATIVE_RETAINED")
    return base,delta

def predict(lane,arm,g,base,delta,selection,fixed):
    if arm=="strong_fixed":
        if len(g["roles"])>9:return None,None,None,None
        p,work=fixed(g)
        return bool(p),work,None,None
    if lane=="Yggdrasil":
        if arm=="new_contrast":
            score,orig,soft,hard,work,zw=model.ygg_contrast(
                g,base,delta,selection["Yggdrasil"]["lambda"])
            need(0<=soft<=1 and 0<=hard<=1
                 and work["max_active"]<=7 and work["max_retained"]<=9,
                 "ORIGINAL_7_PLUS_9")
            meta={"soft_exact_gap":max(0.,soft-hard),
                  "extra_sequential_continuity_scans":zw.get("public_edge_scans",0),
                  "z_read_only_work_sha256":q.digest(zw)}
        elif arm=="AD_anchor10":
            score,raw,ratio,work=old.anchored_score(g,base,delta,10)
            meta=None
        elif arm=="AB_anchor16":
            score,raw,ratio,work=old.anchored_score(g,base,delta,16)
            meta=None
        elif arm=="T_original":
            score,work=old.frozen_t(g,base,delta);meta=None
        else:
            score,raw,ratio,work=old.frozen_z(g,base,delta);meta=None
    else:
        if arm=="new_margin":
            score,raw,contrast,work=model.wing_terminal(
                g,base,delta,selection["Wingless"]["beta"])
            orig,original_work=old.frozen_packed(g,base,delta)
            need(raw==orig and original_work==work
                 and work["max_states_per_node"]==1 and work["max_active"]<=64,
                 "ONE_STATE_SAME_RAW_SCORE_AND_COST")
            meta={"terminal_margin":contrast}
        elif arm=="AA_one_state":
            score,work=old.frozen_packed(g,base,delta);meta=None
        else:
            score,work=old.frozen_three(g,base,delta);meta=None
    return bool(score>=0),work,score,meta

def stage(lane,phase,base,delta,selection,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    counts={arm:{"paired":0,"FP":0,"FN":0,"supported_pairs":0,
           "unsupported_pairs":0,"max_active":0,"max_retained":0,
           "max_states_per_node":0,"scans":0,"bit_reads":0,
           "by_family":{fam:{"pairs":0,"unsupported":0,"paired":0,
                             "FP":0,"FN":0,"depth":{}}
                        for fam in source.FAMILIES},
           "case_sha256":[],"score_summary":{"positive_margin_sign":0,
                                              "negative_margin_sign":0,
                                              "extra_sequential_scans":0}}
            for arm in arms}
    cases=source.pairs(lane,phase)
    for seed,vec,fam,pos,neg in cases:
        for arm in arms:
            tested=[]
            for graph in (pos,neg):
                yes,work,score,meta=predict(lane,arm,graph,base,delta,selection,fixed)
                tested.append((yes,score))
                if work is None:continue
                row=counts[arm]
                row["max_active"]=max(row["max_active"],work.get("max_active",0))
                row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
                row["max_states_per_node"]=max(row["max_states_per_node"],
                                               work.get("max_states_per_node",0))
                row["scans"]+=work.get("edge_inspections",work.get("public_edge_scans",0))
                row["bit_reads"]+=work.get("raw_bit_reads",work.get("raw_bit_ops",0))
                if meta:
                    v=(meta.get("terminal_margin",
                                -meta.get("soft_exact_gap",0.)))
                    k="positive_margin_sign" if graph is pos else "negative_margin_sign"
                    row["score_summary"][k]+=int(v>0)
                    row["score_summary"]["extra_sequential_scans"]+=meta.get(
                         "extra_sequential_continuity_scans",0)
            a,b=tested; row=counts[arm];f=row["by_family"][fam]
            if a[0] is None:
                need(b[0] is None and arm=="strong_fixed"
                     and fam in ("long_dense_13_15","extended_13_15"),
                     "ORIGINAL_DOMAIN_UNSUPPORTED_ONLY")
                row["unsupported_pairs"]+=1;f["unsupported"]+=1
                continue
            good=int(a[0] and not b[0])
            row["paired"]+=good;f["paired"]+=good
            row["supported_pairs"]+=1;f["pairs"]+=1
            row["FP"]+=int(b[0]);f["FP"]+=int(b[0])
            row["FN"]+=int(not a[0]);f["FN"]+=int(not a[0])
            depth=f["depth"].setdefault(str(len(pos["roles"])),{"pairs":0,"paired":0,
                                                                "FP":0,"FN":0})
            depth["pairs"]+=1;depth["paired"]+=good
            depth["FP"]+=int(b[0]);depth["FN"]+=int(not a[0])
            row["case_sha256"].append(q.digest({"phase":phase,"seed":seed,
              "vector":vec,"arm":arm,"family":fam,
              "positive":a,"negative":b}))
        # No oracle inspection before predictions. Then verify the public
        # counterfactual pairs are really different and source-correct.
        need(source.parent.routes15(pos,relaxed=fam=="one_bit_relaxed_keys")==1
             and source.parent.routes15(neg,relaxed=fam=="one_bit_relaxed_keys")==0,
             "EVALUATOR_ONLY_CAUSAL_REFERENCE")
    need(len(cases)==48,"NEW_DISJOINT_FIT_DEV_CENSUS")
    for arm,row in counts.items():
        n=24 if arm=="strong_fixed" else 48
        need(row["supported_pairs"]==n and row["unsupported_pairs"]==48-n
             and len(row["case_sha256"])==n
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192)
             and all(f["pairs"]+f["unsupported"]==12
                     for f in row["by_family"].values()),
             "SOURCE_AND_ORIGINAL_HARD_CAPACITY")
        if arm in ("new_margin","AA_one_state"):
            need(row["max_active"]<=64 and row["max_states_per_node"]==1,
                 "NO_WINGLESS_EXTRA_STATES")
    return {"phase":phase,"pairs":48,"arms":counts,
            "all_causes_admitted_only_in_scorer":True}

def percentile(seq,p):
    s=sorted(seq);return s[min(len(s)-1,math.ceil(p*len(s))-1)]

def resource(base,delta,beta,fixed):
    graphs={fam:[] for fam in source.FAMILIES}
    for _,_,family,p,n in source.pairs("Wingless","DEV"):
        if len(graphs[family])<6:graphs[family].extend((p,n))
    need(all(len(x)==6 for x in graphs.values()),"RESOURCE_24_GRAPH_IDENTITY")
    funcs={
      "new_margin":lambda g:model.wing_terminal(g,base,delta,beta),
      "AA_one_state":lambda g:old.frozen_packed(g,base,delta),
      "AB_three_state":lambda g:old.frozen_three(g,base,delta),
      "strong_fixed":lambda g:fixed(g)}
    obs={name:{"samples":[],"allocations":[],"graphs":0} for name in funcs}
    k=0
    for family in source.FAMILIES:
        for graph in graphs[family]:
            k+=1
            order=list(funcs)
            random.Random("F124AF/original-budget/"+family+"/"+str(k)).shuffle(order)
            for arm in order:
                if arm=="strong_fixed" and len(graph["roles"])>9:continue
                fn=funcs[arm];fn(graph)
                for _ in range(3):
                    t=time.perf_counter_ns();fn(graph)
                    obs[arm]["samples"].append(time.perf_counter_ns()-t)
                gc.collect();tracemalloc.start()
                fn(graph)
                _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                obs[arm]["allocations"].append(peak)
                obs[arm]["graphs"]+=1
    summary={}
    for arm,row in obs.items():
        n=12 if arm=="strong_fixed" else 24
        need(row["graphs"]==n and len(row["samples"])==3*n
             and len(row["allocations"])==n,"RESOURCE_COST_SAMPLES")
        summary[arm]={"graphs":n,"timed_calls":3*n,
           "p50_ns":int(statistics.median(row["samples"])),
           "p95_ns":percentile(row["samples"],.95),
           "p50_peak_alloc_bytes":int(statistics.median(row["allocations"])),
           "p95_peak_alloc_bytes":percentile(row["allocations"],.95),
           "sample_sha256":q.digest(row)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
            "os":platform.platform(),"python":platform.python_version(),
            "original_fixed_only_7to9":True,"matched_same_24_graphs":True,
            "hardware_equalized_scientific_superiority":False,"arms":summary}

def run(paths):
    source.frozen()
    base,delta=ancestry(paths)
    yw,yg=model.ygg_fit(source.pairs("Yggdrasil","FIT"),
                         base["Yggdrasil"],delta["Yggdrasil"])
    ww,wg=model.wing_fit(source.pairs("Wingless","FIT"),
                          base["Wingless"],delta["Wingless"])
    selection={"Yggdrasil":yw,"Wingless":ww}
    fixed=aa_evidence.original_fixed()
    report={"schema":SCHEMA,"freeze_git_blob":source.FREEZE_BLOB,
       "AE_parent_raw_sha256":AE_RAW,"original_weights_source_unmodified":True,
       "selection_new_FIT_before_first_DEV":True,
       "protected_first_use":False,"independent_science_acceptance":False,
       "optimizer_promotion":False,"accepted_ref_mutations":0,
       "matched_hardware_superiority":False,"FIT_grid":{"Yggdrasil":yg,"Wingless":wg},
       "selected":selection,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,"FIT":stage(lane,"FIT",base[lane],delta[lane],selection,fixed),
             "DEV":stage(lane,"DEV",base[lane],delta[lane],selection,fixed),
             "original_weights_sha256":q.digest(base[lane]),
             "original_delta_sha256":q.digest(delta[lane])}
        if lane=="Wingless":
            row["resource"]=resource(base[lane],delta[lane],ww["beta"],fixed)
        report["lanes"].append(row)
    return report

def main():
    p=argparse.ArgumentParser()
    for k in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae","output"):
        p.add_argument("--"+k,required=True)
    args=p.parse_args();destination=Path(args.output)
    need(destination.parent.is_dir() and not destination.exists(),
         "IMMUTABLE_NONOVERWRITE_EVIDENCE")
    report=run([getattr(args,k) for k in
      ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with destination.open("xb") as file:file.write(raw)
    print("F124AF_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in report["lanes"]:
        arms=row["DEV"]["arms"]
        if row["lane"]=="Wingless":
            print("F124AF_WING_DEV=margin:"+str(arms["new_margin"]["paired"])+
                  "/48;one:"+str(arms["AA_one_state"]["paired"])+
                  "/48;beta:"+str(report["selected"]["Wingless"]["beta"]))
        else:
            print("F124AF_YGG_DEV=contrast:"+str(arms["new_contrast"]["paired"])+
                  "/48;AD:"+str(arms["AD_anchor10"]["paired"])+
                  "/48;AB:"+str(arms["AB_anchor16"]["paired"])+
                  "/48;lambda:"+str(report["selected"]["Yggdrasil"]["lambda"]))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AF_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)

"""F124-AL original 18-receipt identity, independent TRAIN and new DEV.

All inference sees public graph+demonstrations, never source-only relation,
class label or reference. Extra noisy examples only in the first vector.
Both output/state budgets and runtime are measured, negatives retained.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124al_frozen_source as s
import f124al_noisy_operator_learner as m
import f124ak_development_evidence as prior_evidence
import f124ak_nonlinear_learner as prior_model
import f124ak_one_packed_contrast as ak_packed
import f124al_packed_confidence as capped
import f124ae_scoring_transfer as old
import f124ag_transition_models as ag
import f124aa_development_evidence as aa
import f124q_independent_binding as q

SCHEMA="forge.research.f124al.authentic-noisy-outofclass-and-packed-fp.v1"
AK_SHA="f80512cd8cd7d639623f89cfa9d5decb1d158bf1949ce65fa1b82287dc63cded"
Y_ARMS=("new_outofclass","AK_original_hypothesis","original_no_demos","oracle_original_AG","strong_fixed_shallow")
W_ARMS=("new_bonus_cap","AK_original_cap1","one_state_beta0","original_raw","oracle_three","strong_fixed_shallow")

def need(ok,tag):s.need(ok,"EVIDENCE_"+tag)

def ancestry(paths):
    bases,deltas=prior_evidence.custody(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AK_SHA,"AUTHENTIC_AK_RAW")
    report=json.loads(raw)
    need(report["schema"]=="forge.research.f124ak.fresh-nonlinear-and-single-packed-contrast.v1"
         and report["freeze_git_blob"]=="c052cabc1e1ad5b762337ea31f606883fb6cb234"
         and report["protected_first_use"] is False
         and report["independent_science_acceptance"] is False
         and report["optimizer_promotion"] is False
         and report["lanes"][0]["HOLDOUT"]["arms"]["new_nonlinear_examples"]["paired"]==48
         and report["lanes"][1]["HOLDOUT"]["arms"]["new_within_hop"]["paired"]==34,
         "ORIGINAL_POSITIVE_AND_FALSE_POSITIVE_CUSTODY")
    return bases,deltas

def init():
    return {"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
       "by_family":{fam:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
                         "by_depth":{}}
                    for fam in s.FAMILIES},
       "max_active":0,"max_retained":0,"max_packed_states_per_node":0,
       "max_packed_bits":0,"edge_scans":0,"extra_competitor_ops":0,
       "public_learner_ambiguous":0,"public_bit_ops":0,"case_sha256":[]}

def classify(lane,arm,graph,base,delta,amount,cap):
    if arm in ("oracle_original_AG","oracle_three","strong_fixed_shallow"):
        return None,None,None
    if arm=="original_raw" or arm=="original_no_demos":
        orig={k:graph[k] for k in ("start","target","roles","edges")}
        if lane=="Yggdrasil":
            score,raw,soft,w=ag.ygg_transition(orig,base,delta,.1)
        else:
            score,w=old.frozen_packed(orig,base,delta)
        return score,w,None
    if arm=="AK_original_hypothesis":
        return prior_model.ygg(graph,base,delta,24)
    if lane=="Yggdrasil":return m.ygg(graph,base,delta,amount)
    if arm=="new_bonus_cap":return m.wing(graph,base,delta,amount,cap)
    normalized,meta=m.normalize(graph,amount)
    if normalized is None:return -1.e9,None,meta
    if arm=="AK_original_cap1":
        score,w=ak_packed.wing_competitive(normalized,base,delta,.5)
    else:
        score,w=old.frozen_packed(normalized,base,delta)
    return score,w,meta

def record(row,family,depth,seed,v,op,arm,phase,yes,no):
    f=row["by_family"][family]
    if yes is None:
        need(no is None and arm=="strong_fixed_shallow" and depth>9,
             "FIXED_CONTROL_SUPPORT_ONLY")
        row["unsupported"]+=1;f["unsupported"]+=1
        return
    ok=int(yes and not no)
    for c in (row,f):
        c["pairs"]+=1;c["paired"]+=ok
        c["FP"]+=int(no);c["FN"]+=int(not yes)
    z=f["by_depth"].setdefault(str(depth),{"pairs":0,"paired":0,"FP":0,"FN":0})
    z["pairs"]+=1;z["paired"]+=ok
    z["FP"]+=int(no);z["FN"]+=int(not yes)
    row["case_sha256"].append(q.digest({"phase":phase,"seed":seed,
        "v":v,"op":op,"arm":arm,"positive":yes,"negative":no}))

def stage(lane,phase,base,delta,amount,cap,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    counts={arm:init() for arm in arms}
    observations={"source_valid_positive":0,"source_valid_negative":0,
       "prior_equality_positive":0,"clean_pairs":0,"noisy_ambiguous_pairs":0,
       "exact_inferred_positive_maps":0,"ambiguous_positive_maps":0,
       "source_oracle_used_by_model":False,
       "noisy_support_symmetrically_applied":True}
    for seed,v,fam,op,tag,pos,neg in s.pairs(lane,phase):
        observations["noisy_ambiguous_pairs" if v==tuple(s.VECTORS[0])
                     else "clean_pairs"]+=1
        model_predictions={}
        for arm in arms:
            if arm in ("oracle_original_AG","oracle_three","strong_fixed_shallow"):
                continue
            results=[]
            for g in (pos,neg):
                score,w,meta=classify(lane,arm,g,base,delta,amount,cap)
                results.append(score>=0)
                row=counts[arm]
                if w is not None:
                    row["max_active"]=max(row["max_active"],w.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],w.get("max_retained",0))
                    row["max_packed_states_per_node"]=max(
                      row["max_packed_states_per_node"],w.get("max_states_per_node",0))
                    row["max_packed_bits"]=max(
                      row["max_packed_bits"],w.get("max_packed_bits_per_state",0))
                    row["edge_scans"]+=w.get("edge_inspections",
                                             w.get("public_edge_scans",0))
                    row["extra_competitor_ops"]+=w.get(
                        "extra_competitor_packed_evaluations",0)
                if meta is not None:
                    sub=meta.get("learn",meta.get("learning",{}))
                    row["public_learner_ambiguous"]+=int(
                        sub.get("ambiguous",not sub.get("unique_bijective_mapping",True)))
                    row["public_bit_ops"]+=meta.get("bit_ops",
                                                  meta.get("edge_bit_operations",0))
            model_predictions[arm]=tuple(results)
            record(counts[arm],fam,len(pos["roles"]),seed,v,op,
                   arm,phase,*results)
        # EVALUATOR ONLY: true inverse transformed source is unavailable to
        # predictor, training candidates, or model normalization.
        pp=s.plain(pos,op,tag);nn=s.plain(neg,op,tag)
        relaxed=fam=="rotate4_tolerant"
        real=s.prior.parent.original.parent.prior.parent.routes15
        observations["source_valid_positive"]+=int(real(pp,relaxed=relaxed)==1)
        observations["source_valid_negative"]+=int(real(nn,relaxed=relaxed)==0)
        observations["prior_equality_positive"]+=int(real(
               {k:pos[k] for k in ("start","target","roles","edges")},
               relaxed=True)>0)
        restored,meta=m.normalize(pos,amount)
        if restored is None:
            observations["ambiguous_positive_maps"]+=1
        else:
            observations["exact_inferred_positive_maps"]+=int(restored==pp)
            need(restored==pp,"POSTHOC_MAPPING_ERROR")
        control="oracle_original_AG" if lane=="Yggdrasil" else "oracle_three"
        for use in ((control,),):
            decisions=[]
            for graph in (pp,nn):
                if lane=="Yggdrasil":
                    score,raw,soft,work=ag.ygg_transition(graph,base,delta,.1)
                else:score,work=old.frozen_three(graph,base,delta)
                decisions.append(score>=0)
                counts[control]["max_active"]=max(
                    counts[control]["max_active"],work.get("max_active",0))
                counts[control]["max_retained"]=max(
                    counts[control]["max_retained"],work.get("max_retained",0))
            record(counts[control],fam,len(pos["roles"]),seed,v,
                   op,control,phase,*decisions)
        if len(pp["roles"])>9:
            counts["strong_fixed_shallow"]["unsupported"]+=1
            counts["strong_fixed_shallow"]["by_family"][fam]["unsupported"]+=1
        else:
            decisions=[]
            for graph in (pp,nn):
                val,w=fixed(graph);decisions.append(bool(val))
                counts["strong_fixed_shallow"]["max_active"]=max(
                    counts["strong_fixed_shallow"]["max_active"],w.get("max_active",0))
            record(counts["strong_fixed_shallow"],fam,len(pos["roles"]),seed,
                   v,op,"strong_fixed_shallow",phase,*decisions)
    need(observations["source_valid_positive"]==48
         and observations["source_valid_negative"]==48
         and observations["prior_equality_positive"]==0
         and observations["clean_pairs"]==24
         and observations["noisy_ambiguous_pairs"]==24
         and observations["exact_inferred_positive_maps"]+
             observations["ambiguous_positive_maps"]==48,
         "PROSPECTIVE_PUBLIC_SOURCE_AND_CLEAN_NOISY_BALANCE")
    for arm,row in counts.items():
        n=24 if arm=="strong_fixed_shallow" else 48
        need(row["pairs"]==n and row["unsupported"]==48-n
             and len(row["case_sha256"])==n
             and all(v["pairs"]+v["unsupported"]==12
                     for v in row["by_family"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "HISTORICAL_STATE_AND_FAMILY_BUDGET")
        if arm in ("new_bonus_cap","AK_original_cap1",
                   "one_state_beta0","original_raw"):
            need(row["max_active"]<=64
                 and row["max_packed_states_per_node"]==1
                 and row["max_packed_bits"]==12,
                 "ONE_PACKED_12BIT_ONLY")
    return {"phase":phase,"pairs":48,"arms":counts,"observations":observations}

def percentile(seq,p):
    v=sorted(seq);return v[min(len(v)-1,math.ceil(p*len(v))-1)]

def resource(base,delta,amount,cap):
    cases={f:[] for f in s.FAMILIES}
    for seed,v,fam,op,tag,p,n in s.pairs("Wingless","DEV"):
        if len(cases[fam])<6:cases[fam].extend((p,n))
    need(all(len(x)==6 for x in cases.values()),"BENCHMARK_24")
    functions={"new_cap":lambda g:m.wing(g,base,delta,amount,cap),
       "AK_cap1":lambda g:m.wing(g,base,delta,amount,1.),
       "raw_original":lambda g:old.frozen_packed(
                   {k:g[k] for k in ("start","target","roles","edges")},
                   base,delta)}
    out={k:{"times":[],"peaks":[],"graphs":0} for k in functions}
    for family,graphs in cases.items():
        for idx,g in enumerate(graphs):
            order=list(functions)
            random.Random("F124AL/resource/"+family+"/"+str(idx)).shuffle(order)
            for arm in order:
                fn=functions[arm];fn(g)
                for i in range(3):
                    start=time.perf_counter_ns();fn(g)
                    out[arm]["times"].append(time.perf_counter_ns()-start)
                gc.collect();tracemalloc.start()
                fn(g);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                out[arm]["peaks"].append(peak);out[arm]["graphs"]+=1
    result={}
    for arm,recorded in out.items():
        need(recorded["graphs"]==24 and
             len(recorded["times"])==72 and len(recorded["peaks"])==24,
             "RESOURCE_SAME_GRAPH_SAMPLES")
        result[arm]={"graphs":24,"calls":72,
           "median_ns":int(statistics.median(recorded["times"])),
           "p95_ns":percentile(recorded["times"],.95),
           "median_peak_python_bytes":int(statistics.median(recorded["peaks"])),
           "sample_digest":q.digest(recorded)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
        "platform":platform.platform(),"python":platform.python_version(),
        "model_only_including_support_learning":True,
        "oracle_evaluator_excluded":True,
        "hardware_superiority_claim":False,"arms":result}

def run(paths):
    s.frozen()
    base,delta=ancestry(paths)
    support,sgrid=m.select_support(s.pairs("Yggdrasil","TRAIN"),
                                   base["Yggdrasil"],delta["Yggdrasil"])
    amount=support["count"]
    cap,cgrid=m.select_wing_cap(s.pairs("Wingless","TRAIN"),
                                base["Wingless"],delta["Wingless"],amount)
    fixed=aa.original_fixed()
    report={"schema":SCHEMA,"freeze_git_blob":s.FREEZE_BLOB,
       "parent_AK_raw_sha256":AK_SHA,"authentic_new_TRAIN_before_DEV":True,
       "frozen_new_operator_families":True,
       "noisy_demo_symmetry":True,"no_DEV_tuning":True,
       "protected_first_use":False,"independent_science_acceptance":False,
       "optimizer_promotion":False,"production":False,
       "accepted_ref_mutations":0,"new_retained_capacity":False,
       "hardware_superiority_claim":False,
       "selected":{"Yggdrasil":support,"Wingless":cap},
       "TRAIN_ygg_grid":sgrid,"TRAIN_wing_grid":cgrid,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        row={"lane":lane,"TRAIN":stage(lane,"TRAIN",base[lane],delta[lane],
                    amount,cap["cap"],fixed),
             "DEV":stage(lane,"DEV",base[lane],delta[lane],
                    amount,cap["cap"],fixed),
             "original_weights_digest":q.digest(base[lane]),
             "original_delta_digest":q.digest(delta[lane])}
        if lane=="Wingless":row["resource"]=resource(
                           base[lane],delta[lane],amount,cap["cap"])
        report["lanes"].append(row)
    return report

def main():
    parser=argparse.ArgumentParser()
    for key in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae",
                "af","ag","ah","ai","aj","ak","output"):
        parser.add_argument("--"+key,required=True)
    args=parser.parse_args();dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),
         "APPEND_ONLY_FIRST_FROZEN_RECEIPT")
    report=run([getattr(args,k) for k in
        ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae",
         "af","ag","ah","ai","aj","ak")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as f:f.write(raw)
    print("F124AL_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        d=lane["DEV"]["arms"]
        if lane["lane"]=="Yggdrasil":
            print("F124AL_YGG_DEV=new:"+str(d["new_outofclass"]["paired"])+
                  "/48;AK_old:"+str(d["AK_original_hypothesis"]["paired"])+
                  "/48;oracle:"+str(d["oracle_original_AG"]["paired"])+
                  "/48;demos:"+str(report["selected"]["Yggdrasil"]["count"]))
        else:
            print("F124AL_WING_DEV=new:"+str(d["new_bonus_cap"]["paired"])+
                  "/48;old_cap1:"+str(d["AK_original_cap1"]["paired"])+
                  "/48;cap:"+str(report["selected"]["Wingless"]["cap"]))
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AL_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)

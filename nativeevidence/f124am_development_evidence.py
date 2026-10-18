"""F124-AM scientific custody, fresh TRAIN selection then independent DEV.

True inverse and semantic family names are used only in evaluator AFTER
all model predictions. Train selection is source-blind and uses new TRAIN
labels alone; separate protected scientific first-use never touched.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124am_frozen_source as s
import f124am_example_affine_learner as m
import f124al_development_evidence as last
import f124al_noisy_operator_learner as prior_model
import f124ak_one_packed_contrast as ak
import f124ae_scoring_transfer as oldwing
import f124ag_transition_models as oldygg
import f124aa_development_evidence as old_fixed
import f124q_independent_binding as q

SCHEMA="forge.research.f124am.authentic-affine-feistel-noisy-and-one-packed-margin.v1"
PARENT_SHA="d9e68ab7ad37518224811033251be20e49f0c6c40bee9030c25ad075c67d2720"
Y_ARMS=("learned_affine","AL_previous_or_and_multiplier",
        "original_no_examples","oracle_original_AG","strong_fixed_shallow")
W_ARMS=("gamma_selected","gamma_0_AK","raw_original_one",
        "oracle_original_AK","oracle_original_three","strong_fixed_shallow")

def need(ok,tag):s.need(ok,"RECEIPT_"+tag)
def ancestry(paths):
    base,delta=last.ancestry(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_SHA,
         "ORIGINAL_AL_RAW_BYTES")
    r=json.loads(raw)
    need(r["schema"]=="forge.research.f124al.authentic-noisy-outofclass-and-packed-fp.v1"
         and r["freeze_git_blob"]=="952b2dea33837c3176112861ecf612c9f488dc35"
         and r["protected_first_use"] is False
         and r["independent_science_acceptance"] is False
         and r["optimizer_promotion"] is False
         and r["lanes"][0]["DEV"]["arms"]["new_outofclass"]["paired"]==45
         and r["lanes"][1]["DEV"]["arms"]["new_bonus_cap"]["paired"]==38,
         "AUTHENTIC_PARENT_AL_STATISTICS")
    return base,delta

def blank():
    return {"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
        "family":{f:{"pairs":0,"unsupported":0,"paired":0,"FP":0,"FN":0,
                     "long_positive_accepted":0,"long_positive_total":0}
                  for f in s.FAMILIES},
        "max_active":0,"max_retained":0,
        "max_states_per_node":0,"max_bits_per_state":0,
        "learner_ambiguous":0,"mapping_support_output_mismatches":0,
        "state_extra_competitor_ops":0,"cases":[]}

def read_model(lane,arm,g,base,delta,count,gamma):
    if lane=="Yggdrasil":
        if arm=="learned_affine":
            score,w,meta=m.ygg(g,base,delta,count)
        elif arm=="AL_previous_or_and_multiplier":
            score,w,meta=prior_model.ygg(g,base,delta,24)
        else:
            raw={k:g[k] for k in ("start","target","roles","edges")}
            score,_,_,w=oldygg.ygg_transition(raw,base,delta,.1)
            meta=None
    else:
        if arm in ("gamma_selected","gamma_0_AK"):
            score,w,meta=m.wing(g,base,delta,count,
                               gamma if arm=="gamma_selected" else 0.)
        else:
            raw={k:g[k] for k in ("start","target","roles","edges")}
            score,w=oldwing.frozen_packed(raw,base,delta)
            meta=None
    return bool(score>=0),w,meta,score

def report(row,fam,depth,seed,vec,op,phase,arm,positive,negative):
    f=row["family"][fam]
    if positive is None:
        need(negative is None and arm=="strong_fixed_shallow" and depth>9,
             "ORIGINAL_FIXED_SHALLOW_ONLY")
        row["unsupported"]+=1;f["unsupported"]+=1;return
    paired=int(positive and not negative)
    for place in (row,f):
        place["pairs"]+=1;place["paired"]+=paired
        place["FP"]+=int(negative);place["FN"]+=int(not positive)
    if depth>=13:
        f["long_positive_accepted"]+=int(positive)
        f["long_positive_total"]+=1
    row["cases"].append(q.digest({
        "seed":seed,"vector":vec,"fam":fam,"op":op,"phase":phase,
        "arm":arm,"positive":positive,"negative":negative}))

def stage(lane,phase,base,delta,count,gamma,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    rows={arm:blank() for arm in arms}
    state={"valid_positive":0,"valid_negative":0,
        "old_equality_positive_paths":0,
        "affine_pairs":0,"feistel_pairs":0,
        "exact_inferred_positive":0,"ambiguous_positive":0,
        "noisy_tasks":0,"true_operator_available_in_model":False,
        "source_reference_only_after_predict":True}
    for seed,vec,fam,op,tag,p,n in s.pairs(lane,phase):
        results={}
        for arm in arms:
            if arm.startswith("oracle_") or arm=="strong_fixed_shallow":
                continue
            decisions=[]
            for graph in (p,n):
                accept,work,meta,score=read_model(
                    lane,arm,graph,base,delta,count,gamma)
                decisions.append(accept)
                row=rows[arm]
                if work is not None:
                    row["max_active"]=max(row["max_active"],
                                          work.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],
                                            work.get("max_retained",0))
                    row["max_states_per_node"]=max(
                        row["max_states_per_node"],work.get("max_states_per_node",0))
                    row["max_bits_per_state"]=max(
                        row["max_bits_per_state"],work.get("max_packed_bits_per_state",0))
                    row["state_extra_competitor_ops"]+=work.get(
                        "extra_competitor_packed_evaluations",0)
                if meta is not None:
                    a=meta.get("learner",meta.get("learn",{}))
                    row["learner_ambiguous"]+=int(
                        not a.get("unique",not a.get("ambiguous",False)))
                    row["mapping_support_output_mismatches"]+=a.get(
                        "best_mismatched_output_bits") or 0
            results[arm]=tuple(decisions)
            report(rows[arm],fam,len(p["roles"]),seed,vec,op,
                   phase,arm,*decisions)
        # *Only after source-blind model predictions* inspect true
        # inverse semantics, labels and evaluator-only oracle controls.
        pp=s.plain(p,op,tag);nn=s.plain(n,op,tag)
        reference=s.old.prior.parent.original.parent.prior.parent.routes15
        relaxed=fam=="rotate4_tolerant"
        state["valid_positive"]+=int(reference(pp,relaxed=relaxed)==1)
        state["valid_negative"]+=int(reference(nn,relaxed=relaxed)==0)
        state["old_equality_positive_paths"]+=int(
          reference({k:p[k] for k in ("start","target","roles","edges")},
                    relaxed=True)>0)
        key="affine_pairs" if op.startswith("affine_") else "feistel_pairs"
        state[key]+=1
        state["noisy_tasks"]+=int(sum(s.relation(d["input_bits"],op)!=
                                        d["output_bits"] for d in p["demos"])==2)
        recovered,meta=m.normalize(p,count)
        if recovered is None:state["ambiguous_positive"]+=1
        else:
            need(recovered==pp,"MODEL_INFERRED_AFFINE_MAP_MISMATCH")
            state["exact_inferred_positive"]+=1
        target="oracle_original_AG" if lane=="Yggdrasil" else "oracle_original_AK"
        decisions=[]
        for graph in (pp,nn):
            if lane=="Yggdrasil":
                score,raw,soft,work=oldygg.ygg_transition(graph,base,delta,.1)
            else:score,work=ak.wing_competitive(graph,base,delta,.5)
            decisions.append(score>=0)
            rows[target]["max_active"]=max(rows[target]["max_active"],
                                          work.get("max_active",0))
            rows[target]["max_retained"]=max(rows[target]["max_retained"],
                                            work.get("max_retained",0))
            rows[target]["max_states_per_node"]=max(
                rows[target]["max_states_per_node"],work.get("max_states_per_node",0))
            rows[target]["max_bits_per_state"]=max(
                rows[target]["max_bits_per_state"],work.get("max_packed_bits_per_state",0))
        report(rows[target],fam,len(p["roles"]),seed,vec,op,
               phase,target,*decisions)
        if lane=="Wingless":
            decisions=[]
            for graph in (pp,nn):
                score,work=oldwing.frozen_three(graph,base,delta)
                decisions.append(score>=0)
                rows["oracle_original_three"]["max_active"]=max(
                    rows["oracle_original_three"]["max_active"],
                    work.get("max_active",0))
                rows["oracle_original_three"]["max_retained"]=max(
                    rows["oracle_original_three"]["max_retained"],
                    work.get("max_retained",0))
            report(rows["oracle_original_three"],fam,len(p["roles"]),
                   seed,vec,op,phase,"oracle_original_three",*decisions)
        if len(p["roles"])>9:
            rows["strong_fixed_shallow"]["unsupported"]+=1
            rows["strong_fixed_shallow"]["family"][fam]["unsupported"]+=1
        else:
            decisions=[]
            for graph in (pp,nn):
                truth,work=fixed(graph)
                decisions.append(bool(truth))
                rows["strong_fixed_shallow"]["max_active"]=max(
                    rows["strong_fixed_shallow"]["max_active"],
                    work.get("max_active",0))
            report(rows["strong_fixed_shallow"],fam,len(p["roles"]),
                   seed,vec,op,phase,"strong_fixed_shallow",*decisions)
    need(state["valid_positive"]==48 and state["valid_negative"]==48
         and state["old_equality_positive_paths"]==0
         and state["affine_pairs"]==24 and state["feistel_pairs"]==24
         and state["noisy_tasks"]==48
         and state["exact_inferred_positive"]+state["ambiguous_positive"]==48,
         "NEW_NOISY_AFFINE_FEISTEL_CENSUS")
    for arm,row in rows.items():
        n=24 if arm=="strong_fixed_shallow" else 48
        need(row["pairs"]==n and row["unsupported"]==48-n
             and len(row["cases"])==n
             and all(f["pairs"]+f["unsupported"]==12
                     for f in row["family"].values())
             and row["max_retained"]<=9
             and (row["max_active"]<=7 if lane=="Yggdrasil"
                  else row["max_active"]<=192),
             "HARD_UNCHANGED_STATE_OR_BALANCED_STRUCTURE")
        if arm in ("gamma_selected","gamma_0_AK",
                   "raw_original_one","oracle_original_AK"):
            need(row["max_active"]<=64
                 and row["max_states_per_node"]==1
                 and row["max_bits_per_state"]==12,
                 "HISTORICAL_ONE_PACKED_12BIT_STATE")
    return {"phase":phase,"paired_source_count":48,"models":rows,
            "source_validation":state}

def resources(base,delta,count,gamma):
    family={f:[] for f in s.FAMILIES}
    for seed,vec,f,op,nonce,p,n in s.pairs("Wingless","DEV"):
        if len(family[f])<6:family[f].extend((p,n))
    need(all(len(x)==6 for x in family.values()),"MEASURED_24_PUBLIC_GRAPHS")
    fn={"new_gamma":lambda g:m.wing(g,base,delta,count,gamma),
        "AK_gamma0":lambda g:m.wing(g,base,delta,count,0.),
        "raw_original":lambda g:oldwing.frozen_packed(
            {k:g[k] for k in ("start","target","roles","edges")},
            base,delta)}
    data={k:{"times":[],"peaks":[],"graphs":0} for k in fn}
    for f in s.FAMILIES:
        for i,g in enumerate(family[f]):
            order=list(fn)
            random.Random("F124AM/runtime/"+f+"/"+str(i)).shuffle(order)
            for arm in order:
                call=fn[arm];call(g)
                for _ in range(3):
                    t=time.perf_counter_ns();call(g)
                    data[arm]["times"].append(time.perf_counter_ns()-t)
                gc.collect();tracemalloc.start()
                call(g);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                data[arm]["peaks"].append(peak);data[arm]["graphs"]+=1
    result={}
    for arm,x in data.items():
        need(x["graphs"]==24 and len(x["times"])==72
             and len(x["peaks"])==24,"SAME_RESOURCE_SAMPLE_DENOMINATOR")
        result[arm]={"graphs":24,"timed_calls":72,
            "median_ns":int(statistics.median(x["times"])),
            "median_peak_bytes":int(statistics.median(x["peaks"])),
            "trace_sha256":q.digest(x)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
        "python":platform.python_version(),"platform":platform.platform(),
        "model_plus_example_learner_no_oracle":True,
        "equal_hardware_superiority_claim":False,"arms":result}

def run(paths):
    s.frozen()
    base,delta=ancestry(paths)
    support,sgrid=m.fit_support(s.pairs("Yggdrasil","TRAIN"),
                                base["Yggdrasil"],delta["Yggdrasil"])
    count=support["count"]
    gamma,ggrid=m.fit_gamma(s.pairs("Wingless","TRAIN"),
                             base["Wingless"],delta["Wingless"],count)
    control=old_fixed.original_fixed()
    result={"schema":SCHEMA,"freeze_git_blob":s.FREEZE_BLOB,
            "parent_AL_raw_sha256":PARENT_SHA,
            "frozen_TRAIN_before_first_DEV":True,
            "all_demo_noise_symmetrical":True,
            "feistel_outside_Gf2_hypothesis_class":True,
            "no_DEV_tuning":True,"no_protected_first_use":True,
            "independent_science_acceptance":False,
            "optimizer_promotion":False,"production":False,
            "accepted_ref_mutations":0,"extra_retained_state":False,
            "matched_hardware_superiority_claim":False,
            "selected":{"Yggdrasil":support,"Wingless":gamma},
            "TRAIN_Ygg_grid":sgrid,"TRAIN_Wing_grid":ggrid,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        r={"lane":lane,
           "TRAIN":stage(lane,"TRAIN",base[lane],delta[lane],
                         count,gamma["gamma"],control),
           "DEV":stage(lane,"DEV",base[lane],delta[lane],
                       count,gamma["gamma"],control),
           "historical_weights_digest":q.digest(base[lane])}
        if lane=="Wingless":
            r["resources"]=resources(base[lane],delta[lane],
                                      count,gamma["gamma"])
            a=r["DEV"]["models"]["gamma_selected"]
            b=r["DEV"]["models"]["gamma_0_AK"]
            af=sum(a["family"][f]["long_positive_accepted"]
                   for f in ("rotate4_dense_13_15","xor16_extended_13_15"))
            bf=sum(b["family"][f]["long_positive_accepted"]
                   for f in ("rotate4_dense_13_15","xor16_extended_13_15"))
            r["strict_heldout_preserved_long_positives"]=af>=bf
            r["strict_heldout_FP_reduced"]=a["FP"]<b["FP"]
            r["strict_win"]=af>=bf and a["FP"]<b["FP"]
        result["lanes"].append(r)
    return result

def main():
    p=argparse.ArgumentParser()
    for n in ("o","t","u","w","x","y","z","aa","ab","ac",
              "ad","ae","af","ag","ah","ai","aj","ak","al","output"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args();dest=Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),
         "NEW_APPEND_ONLY_FIRST_USE_RECEIPT")
    report_data=run([getattr(a,n) for n in
       ("o","t","u","w","x","y","z","aa","ab","ac",
        "ad","ae","af","ag","ah","ai","aj","ak","al")])
    raw=json.dumps(report_data,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as f:f.write(raw)
    print("F124AM_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report_data["lanes"]:
        rows=lane["DEV"]["models"]
        if lane["lane"]=="Yggdrasil":
            print("F124AM_YGG_DEV=new:"+str(rows["learned_affine"]["paired"])+
                  "/48;oracle:"+str(rows["oracle_original_AG"]["paired"])+
                  "/48;AL:"+str(rows["AL_previous_or_and_multiplier"]["paired"])+
                  "/48;demos:"+str(report_data["selected"]["Yggdrasil"]["count"]))
        else:
            print("F124AM_WING_DEV=new:"+str(rows["gamma_selected"]["paired"])+
                  "/48;gamma0:"+str(rows["gamma_0_AK"]["paired"])+
                  "/48;strict:"+str(lane["strict_win"])+
                  ";gamma:"+str(report_data["selected"]["Wingless"]["gamma"]))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as ex:
        print("F124AM_FAIL_CLOSED:"+str(ex),file=sys.stderr)
        sys.exit(1)

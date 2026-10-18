"""F124-AK new semantic-family scientific source, original 17-run custody.

Only prospective TRAIN labels select demonstration count and Wingless beta.
HOLDOUT structural families remain unseen until both are frozen.
Original oracle-normalized models are evaluator-only reference ceilings.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124ak_frozen_source as source
import f124ak_nonlinear_learner as model
import f124aj_development_evidence as previous
import f124aj_example_operator_learner as aj_model
import f124ah_original_model_challenge as trace
import f124ac_development_evidence as join
import f124ae_scoring_transfer as old
import f124ag_transition_models as ygg_original
import f124aa_development_evidence as old_fixed
import f124q_independent_binding as q

SCHEMA="forge.research.f124ak.fresh-nonlinear-and-single-packed-contrast.v1"
AJ_RAW="56d3af7122ba4ec1bf5d0f50567f68920eb8c7f087f98a3e0c864b4aa3d66aef"
Y_ARMS=("new_nonlinear_examples","prior_AJ_bit_permutation","raw_original_AG",
        "oracle_original_AG","strong_fixed_shallow")
W_ARMS=("new_within_hop","original_packed_beta0","raw_one",
        "oracle_original_one","oracle_original_three",
        "strong_fixed_shallow")

def need(ok,label):source.need(ok,"EVIDENCE_"+label)

def custody(paths):
    base,delta=previous.ancestry(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==AJ_RAW,"ORIGINAL_AJ_RAW_SHA256")
    previous_report=json.loads(raw)
    need(previous_report["schema"]==
         "forge.research.f124aj.authentic-incontext-operator-induction.v1"
         and previous_report["freeze_git_blob"]==
             "c6f370fe58c3a4aec38ddc45bfad2d65f6b7f17f"
         and previous_report["protected_first_use"] is False
         and previous_report["optimizer_promotion"] is False
         and previous_report["lanes"][0]["HOLDOUT"]["arms"][
               "TRAIN_selected_demonstrations"]["correct_pairs"]==44
         and previous_report["lanes"][1]["HOLDOUT"]["arms"][
               "example_one_packed"]["correct_pairs"]==12,
         "PARENT_AI_AJ_EVIDENCE_RETAINED")
    return base,delta

def outcome(lane,arm,g,base,delta,amount,beta,fixed):
    if arm in ("oracle_original_AG","oracle_original_one",
               "oracle_original_three","strong_fixed_shallow"):
        return None,None,None  # Only in evaluator after ALL model predictions
    if lane=="Yggdrasil":
        if arm=="new_nonlinear_examples":
            score,work,meta=model.ygg(g,base,delta,amount)
        elif arm=="prior_AJ_bit_permutation":
            score,work,meta=aj_model.ygg(g,base,delta,16)
        else:
            sample={k:g[k] for k in ("start","target","roles","edges")}
            score,raw,ratio,work=ygg_original.ygg_transition(
                 sample,base,delta,.1)
            meta=None
    else:
        if arm in ("new_within_hop","original_packed_beta0"):
            score,work,meta=model.wing(
                g,base,delta,amount,beta if arm=="new_within_hop" else 0.)
        else:
            sample={k:g[k] for k in ("start","target","roles","edges")}
            score,work=old.frozen_packed(sample,base,delta)
            meta=None
    return score,work,meta

def counters():
    return {"paired":0,"pairs":0,"unsupported":0,"FP":0,"FN":0,
            "by_family":{f:{"paired":0,"pairs":0,"unsupported":0,
                            "FP":0,"FN":0,"by_depth":{}}
                         for f in source.FAMILIES},
            "max_active":0,"max_retained":0,
            "max_states_per_node":0,"max_packed_bits_per_state":0,
            "model_scans":0,"model_bit_ops":0,"learner_tested_support":0,
            "learner_ambiguous_graphs":0,"extra_comparison_calls":0,
            "case_sha256":[]}

def append(rec,family,depth,seed,vec,op,arm,phase,a,b):
    fam=rec["by_family"][family]
    if a is None:
        need(b is None and arm=="strong_fixed_shallow" and depth>9,
             "ORIGINAL_FIXED_SHALLOW_ONLY")
        rec["unsupported"]+=1;fam["unsupported"]+=1
        return
    good=int(a and not b)
    for cell in (rec,fam):
        cell["pairs"]+=1;cell["paired"]+=good
        cell["FP"]+=int(b);cell["FN"]+=int(not a)
    bydepth=fam["by_depth"].setdefault(str(depth),{
           "pairs":0,"paired":0,"FP":0,"FN":0})
    bydepth["pairs"]+=1;bydepth["paired"]+=good
    bydepth["FP"]+=int(b);bydepth["FN"]+=int(not a)
    rec["case_sha256"].append(q.digest({
         "seed":seed,"vector":vec,"op":op,"phase":phase,
         "arm":arm,"positive":a,"negative":b}))

def packed_diagnose(g,op,tag,fam,base,delta,amount,model_accepts):
    normalized,meta=model.normalize(g,amount)
    if normalized is None:return {
        "mapping_ambiguous":True,"final_proxy_visible":False,
        "missed_with_proxy":False,"first_missing":None,
        "first_pruned":None,"passive_source_blind":False}
    original_score,work,chain=trace.wing_source_blind_trace(
        normalized,base,delta)
    historical,oldwork=old.frozen_packed(normalized,base,delta)
    need(original_score==historical and oldwork==work,
         "UNMODIFIED_ONE_PACKED_PASSIVE_PARITY")
    plain=source.plain(g,op,tag)
    # Posthoc witness; never used by model, source selection or beta fitting.
    frontier=[(plain["start"],None,[])]
    for role in plain["roles"]:
        new=[]
        for node,key,hist in frontier:
            for e in plain["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                d=0 if key is None else sum(a!=b for a,b in
                                             zip(key,e["src_bits"]))
                if key is None or d<=(1 if fam=="rotate4_tolerant" else 0):
                    new.append((e["to"],tuple(e["dst_bits"]),
                                hist+[(e["to"],tuple(e["dst_bits"]))]))
                    need(len(new)<=256,"SCORER_ONLY_WITNESS_BOUNDED")
        frontier=new
    paths=[hist for node,key,hist in frontier if node==plain["target"]]
    need(len(paths)==1,"HONEST_PUBLIC_TRUE_PATH_SCORER_ONLY")
    related=join.causal_join(chain,paths[0],wing=True)
    return {"mapping_ambiguous":False,
            "final_proxy_visible":related["reference_survived_final"],
            "missed_with_proxy":bool(not model_accepts and
                                      related["reference_survived_final"]),
            "first_missing":related["first_reference_missing_candidate_hop"],
            "first_pruned":related["first_reference_pruned_hop"],
            "passive_source_blind":True,
            "proxy_not_proof_of_raw_key_identity":True}

def stage(lane,phase,base,delta,amount,beta,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    measured={arm:counters() for arm in arms}
    observations={"phase":phase,"public_support_examples":24,
         "valid_new_rule_positives":0,"valid_new_rule_negatives":0,
         "old_raw_equality_positive_routes":0,
         "mapping_exact_positive_graphs":0,"mapping_ambiguous_positive_graphs":0,
         "new_operators_frozen_before_first_holdout":True,
         "labels_evaluator_only":True}
    if lane=="Wingless":
        observations["passive_one_slot"]={"positive_cases":0,
            "final_proxy_visible":0,"final_proxy_missing":0,
            "FN_with_final_proxy":0,"first_missing":{},
            "first_pruned":{},"case_digest":[]}
    for seed,vec,fam,op,tag,p,n in source.pairs(lane,phase):
        outcomes={}
        for arm in arms:
            if arm in ("oracle_original_AG","oracle_original_one",
                        "oracle_original_three","strong_fixed_shallow"):
                continue
            decisions=[]
            for graph in (p,n):
                score,work,meta=outcome(
                      lane,arm,graph,base,delta,amount,beta,fixed)
                decisions.append(score>=0)
                row=measured[arm]
                if work is not None:
                    row["max_active"]=max(row["max_active"],
                                           work.get("max_active",0))
                    row["max_retained"]=max(row["max_retained"],
                                           work.get("max_retained",0))
                    row["max_states_per_node"]=max(row["max_states_per_node"],
                                              work.get("max_states_per_node",0))
                    row["max_packed_bits_per_state"]=max(
                                              row["max_packed_bits_per_state"],
                                              work.get("max_packed_bits_per_state",0))
                    row["model_scans"]+=work.get("edge_inspections",
                                                work.get("public_edge_scans",0))
                    row["model_bit_ops"]+=work.get("raw_bit_reads",
                                                 work.get("raw_bit_ops",0))
                    row["extra_comparison_calls"]+=work.get(
                                                 "extra_competitor_packed_evaluations",0)
                if meta is not None:
                    # Previous AJ baseline uses a different read-only
                    # diagnostic schema. Normalize receipt counters only;
                    # the frozen model and new source remain unchanged.
                    if "learn" in meta:
                        row["learner_ambiguous_graphs"]+=int(
                            not meta["learn"]["unique"])
                        row["learner_tested_support"]+=meta["learn"]["demos"]
                    else:
                        need("learning" in meta,
                             "HISTORICAL_DIAGNOSTIC_SCHEMA")
                        row["learner_ambiguous_graphs"]+=int(
                            not meta["learning"]["unique_bijective_mapping"])
                        row["learner_tested_support"]+=meta["learning"]["pairs_used"]
            outcomes[arm]=tuple(decisions)
            append(measured[arm],fam,len(p["roles"]),seed,vec,op,
                   arm,phase,*decisions)
        # AFTER actual predictors: source/evaluator-only normalized references
        pp=source.plain(p,op,tag);nn=source.plain(n,op,tag)
        relaxed=fam=="rotate4_tolerant"
        observations["valid_new_rule_positives"]+=int(
            source.parent.original.parent.prior.parent.routes15(pp,relaxed=relaxed)==1)
        observations["valid_new_rule_negatives"]+=int(
            source.parent.original.parent.prior.parent.routes15(nn,relaxed=relaxed)==0)
        rawp={k:p[k] for k in ("start","target","roles","edges")}
        observations["old_raw_equality_positive_routes"]+=int(
            source.parent.original.parent.prior.parent.routes15(
                rawp,relaxed=True)>0)
        normalized,meta=model.normalize(p,amount)
        if normalized is not None:
            need(normalized==pp,"EXACT_MAPPING_RECONSTRUCTION_OBSERVER_ONLY")
            observations["mapping_exact_positive_graphs"]+=1
        else:observations["mapping_ambiguous_positive_graphs"]+=1
        ceiling=("oracle_original_AG" if lane=="Yggdrasil"
                 else "oracle_original_one")
        decisions=[]
        for graph in (pp,nn):
            if lane=="Yggdrasil":
                score,raw,ratio,work=ygg_original.ygg_transition(
                     graph,base,delta,.1)
            else:score,work=old.frozen_packed(graph,base,delta)
            decisions.append(score>=0)
            row=measured[ceiling]
            row["max_active"]=max(row["max_active"],work.get("max_active",0))
            row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
            row["max_states_per_node"]=max(row["max_states_per_node"],
                                            work.get("max_states_per_node",0))
            row["max_packed_bits_per_state"]=max(
                                       row["max_packed_bits_per_state"],
                                       work.get("max_packed_bits_per_state",0))
        append(measured[ceiling],fam,len(p["roles"]),seed,vec,op,
               ceiling,phase,*decisions)
        if lane=="Wingless":
            triple=[]
            for graph in (pp,nn):
                score,work=old.frozen_three(graph,base,delta)
                triple.append(score>=0)
                row=measured["oracle_original_three"]
                row["max_active"]=max(row["max_active"],work.get("max_active",0))
                row["max_retained"]=max(row["max_retained"],work.get("max_retained",0))
            append(measured["oracle_original_three"],fam,len(p["roles"]),
                   seed,vec,op,"oracle_original_three",phase,*triple)
            diag=packed_diagnose(
                   p,op,tag,fam,base,delta,amount,
                   outcomes["new_within_hop"][0])
            d=observations["passive_one_slot"]
            d["positive_cases"]+=1
            d["final_proxy_visible"]+=int(diag["final_proxy_visible"])
            d["final_proxy_missing"]+=int(not diag["final_proxy_visible"])
            d["FN_with_final_proxy"]+=int(diag["missed_with_proxy"])
            for field,val in (("first_missing",diag["first_missing"]),
                              ("first_pruned",diag["first_pruned"])):
                key=str(val) if val is not None else "SURVIVED"
                d[field][key]=d[field].get(key,0)+1
            d["case_digest"].append(q.digest({
                "seed":seed,"op":op,"diagnostic":diag}))
        if len(p["roles"])>9:
            row=measured["strong_fixed_shallow"]
            row["unsupported"]+=1
            row["by_family"][fam]["unsupported"]+=1
        else:
            pairs=[]
            for graph in (pp,nn):
                val,work=fixed(graph)
                pairs.append(bool(val))
                row=measured["strong_fixed_shallow"]
                row["max_active"]=max(row["max_active"],
                                       work.get("max_active",0))
            append(measured["strong_fixed_shallow"],fam,len(p["roles"]),
                   seed,vec,op,"strong_fixed_shallow",phase,*pairs)
    need(observations["valid_new_rule_positives"]==48
         and observations["valid_new_rule_negatives"]==48
         and observations["old_raw_equality_positive_routes"]==0
         and observations["mapping_exact_positive_graphs"]+
             observations["mapping_ambiguous_positive_graphs"]==48,
         "PUBLIC_RELATION_HONEST_CLASSIFICATIONS")
    if lane=="Wingless":
        d=observations["passive_one_slot"]
        need(d["positive_cases"]==48 and
             d["final_proxy_visible"]+d["final_proxy_missing"]==48
             and len(d["case_digest"])==48,
             "PASSIVE_SOURCE_BLIND_HOP_REPORT")
    for arm,row in measured.items():
        required=24 if arm=="strong_fixed_shallow" else 48
        need(row["pairs"]==required and row["unsupported"]==48-required
             and len(row["case_sha256"])==required
             and all(f["pairs"]+f["unsupported"]==12
                     for f in row["by_family"].values())
             and row["max_retained"]<=9 and
             (row["max_active"]<=7 if lane=="Yggdrasil"
              else row["max_active"]<=192),
             "ALL_FOUR_FAMILIES_OR_HARD_ORIGINAL_CAPACITY")
        if arm in ("new_within_hop","original_packed_beta0",
                   "raw_one","oracle_original_one"):
            need(row["max_active"]<=64 and row["max_states_per_node"]==1
                 and row["max_packed_bits_per_state"]==12,
                 "NO_NEW_ONE_PACKED_STATE")
    return {"phase":phase,"pairs":48,"arms":measured,"observations":observations}

def percentile(xs,p):
    a=sorted(xs);return a[min(len(a)-1,math.ceil(p*len(a))-1)]

def benchmark(base,delta,amount,beta):
    samples={f:[] for f in source.FAMILIES}
    for seed,vec,fam,op,tag,p,n in source.pairs("Wingless","HOLDOUT"):
        if len(samples[fam])<6:samples[fam].extend((p,n))
    need(all(len(v)==6 for v in samples.values()),"STRATIFIED_24_PUBLIC_SAMPLES")
    funcs={
        "new_within_hop":lambda g:model.wing(g,base,delta,amount,beta),
        "original_packed_beta0":lambda g:model.wing(g,base,delta,amount,0.),
        "raw_original":lambda g:old.frozen_packed(
            {k:g[k] for k in ("start","target","roles","edges")},base,delta)}
    tally={name:{"times":[],"peaks":[],"graphs":0} for name in funcs}
    i=0
    for fam in source.FAMILIES:
        for g in samples[fam]:
            i+=1;arms=list(funcs)
            random.Random("F124AK/frozen-cost/"+fam+"/"+str(i)).shuffle(arms)
            for arm in arms:
                fn=funcs[arm];fn(g)
                for repetition in range(3):
                    start=time.perf_counter_ns();fn(g)
                    tally[arm]["times"].append(time.perf_counter_ns()-start)
                gc.collect();tracemalloc.start()
                fn(g);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                tally[arm]["peaks"].append(peak);tally[arm]["graphs"]+=1
    output={}
    for arm,row in tally.items():
        need(row["graphs"]==24 and len(row["times"])==72
             and len(row["peaks"])==24,
             "FULL_COMPARABLE_MODEL_ONLY_SAMPLES")
        output[arm]={"graphs":24,"timed_calls":72,
                     "median_ns":int(statistics.median(row["times"])),
                     "p95_ns":percentile(row["times"],.95),
                     "median_python_peak_bytes":int(statistics.median(row["peaks"])),
                     "sample_sha256":q.digest(row)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
            "platform":platform.platform(),"python":platform.python_version(),
            "model_including_public_support_learning":True,
            "oracle_and_diagnostics_excluded":True,
            "hardware_equalized_resource_superiority_claim":False,
            "arms":output}

def run(paths):
    source.frozen()
    base,delta=custody(paths)
    support,grid=model.fit_support(
         source.pairs("Yggdrasil","TRAIN"),
         base["Yggdrasil"],delta["Yggdrasil"])
    amount=support["count"]
    beta,beta_grid=model.fit_wing_beta(
         source.pairs("Wingless","TRAIN"),
         base["Wingless"],delta["Wingless"],amount)
    fixed=old_fixed.original_fixed()
    receipt={"schema":SCHEMA,"freeze_git_blob":source.FREEZE_BLOB,
         "original_AJ_raw_sha256":AJ_RAW,
         "nonlinear_structural_holdout":True,
         "TRAIN_only_support_selection":True,
         "TRAIN_only_wing_beta_selection":True,
         "no_HOLDOUT_label_tuning":True,
         "handdesigned_hypothesis_class_not_general_cognition":True,
         "protected_first_use":False,
         "independent_science_acceptance":False,
         "optimizer_promotion":False,"production":False,
         "accepted_ref_mutations":0,"new_retained_state":False,
         "matched_compute_superiority":False,
         "selection":{"Yggdrasil":support,"Wingless":beta},
         "TRAIN_support_grid":grid,"TRAIN_wing_beta_grid":beta_grid,
         "lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        item={"lane":lane,
              "TRAIN":stage(lane,"TRAIN",base[lane],delta[lane],
                            amount,beta["beta"],fixed),
              "HOLDOUT":stage(lane,"HOLDOUT",base[lane],delta[lane],
                              amount,beta["beta"],fixed),
              "original_weights_sha256":q.digest(base[lane]),
              "original_delta_sha256":q.digest(delta[lane])}
        if lane=="Wingless":
            item["benchmark"]=benchmark(base[lane],delta[lane],
                                        amount,beta["beta"])
        receipt["lanes"].append(item)
    return receipt

def main():
    p=argparse.ArgumentParser()
    for key in ("o","t","u","w","x","y","z","aa","ab","ac","ad",
                "ae","af","ag","ah","ai","aj","output"):
        p.add_argument("--"+key,required=True)
    args=p.parse_args();dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),
         "NEVER_OVERWRITE_QUALIFIED_SCIENCE")
    receipt=run([getattr(args,key) for key in
      ("o","t","u","w","x","y","z","aa","ab","ac","ad",
       "ae","af","ag","ah","ai","aj")])
    raw=json.dumps(receipt,sort_keys=True,indent=2).encode()+b"\n"
    with dest.open("xb") as output:output.write(raw)
    print("F124AK_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in receipt["lanes"]:
        c=lane["HOLDOUT"]["arms"]
        if lane["lane"]=="Yggdrasil":
            print("F124AK_YGG_HOLDOUT=new:"+
                  str(c["new_nonlinear_examples"]["paired"])+
                  "/48;oracle:"+str(c["oracle_original_AG"]["paired"])+
                  "/48;prior_linear:"+str(c["prior_AJ_bit_permutation"]["paired"])+
                  "/48;demos:"+str(receipt["selection"]["Yggdrasil"]["count"]))
        else:
            print("F124AK_WING_HOLDOUT=new:"+
                  str(c["new_within_hop"]["paired"])+
                  "/48;one:"+str(c["original_packed_beta0"]["paired"])+
                  "/48;beta:"+str(receipt["selection"]["Wingless"]["beta"]))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AK_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)

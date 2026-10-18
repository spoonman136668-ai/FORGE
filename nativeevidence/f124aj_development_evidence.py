"""F124-AJ 16-original-receipt, TRAIN-only few-shot learner, unseen-rule HOLDOUT.

Labels and full symbolic maps belong solely to the evaluator. Model derives
16-bit coordinate alignment from unlabeled public support examples PER TASK.
HOLDOUT examples are public demonstration context, not tuned outcome labels.
All original hard-state budgets unchanged and all negatives retained.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124aj_frozen_source as source
import f124aj_example_operator_learner as learner
import f124ai_development_evidence as previous
import f124ah_original_model_challenge as original_trace
import f124ac_development_evidence as joins
import f124aa_development_evidence as old_control
import f124ag_transition_models as old_ygg
import f124ae_scoring_transfer as old_wing
import f124q_independent_binding as q

SCHEMA="forge.research.f124aj.authentic-incontext-operator-induction.v1"
PARENT_RAW="7f129ca575dcb6c546150d1019dd32c786c0df8c7be372162e75d48335eb1449"
Y_ARMS=("TRAIN_selected_demonstrations","original_AG_without_examples",
        "oracle_normalized_upper_bound","strong_fixed_normalized_supported")
W_ARMS=("example_one_packed","raw_original_one","example_three_packed",
        "oracle_normalized_one_ceiling","strong_fixed_normalized_supported")

def need(ok,label):source.need(ok,"RECEIPT_"+label)

def ancestry(paths):
    base,delta=previous.authentic(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_RAW,"AUTHENTIC_AI_RAW_BYTE_IDENTITY")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124ai.authentic-parameter-heldout-compositional-rule.v1"
         and p["freeze_git_blob"]=="5f1a0acf498b6bfec4414ccafc2efebfd581e512"
         and p["protected_first_use"] is False
         and p["independent_science_acceptance"] is False
         and p["optimizer_promotion"] is False
         and p["lanes"][0]["HOLDOUT"]["models"]["TRAIN_selected_parser"]["correct_pairs"]==47
         and p["lanes"][1]["HOLDOUT"]["models"]["parser_one_packed"]["correct_pairs"]==16,
         "ORIGINAL_AI_COMPOSITIONAL_INTERPRETER_PROVENANCE")
    return base,delta

def public_graph(g):
    return {k:g[k] for k in ("start","target","roles","edges")}

def baseline(lane,g,base,delta):
    if lane=="Yggdrasil":return learner.old_ygg(g,base,delta)
    return learner.old_wing(g,base,delta)

def prediction(lane,arm,g,base,delta,amount,fixed):
    if arm=="original_AG_without_examples" or arm=="raw_original_one":
        value,work=baseline(lane,g,base,delta)
        return value,work,None
    if arm in ("oracle_normalized_upper_bound","oracle_normalized_one_ceiling",
               "strong_fixed_normalized_supported"):
        return None,None,None  # Posthoc evaluator ONLY after all actual models.
    if lane=="Yggdrasil":
        score,work,meta=learner.ygg(g,base,delta,amount)
    else:
        score,work,meta=learner.wing(
            g,base,delta,amount,three=(arm=="example_three_packed"))
    return score,work,meta

def new_stats():
    return {"pairs":0,"unsupported":0,"correct_pairs":0,"FP":0,"FN":0,
            "by_family":{x:{"pairs":0,"unsupported":0,
                            "correct_pairs":0,"FP":0,"FN":0,
                            "by_depth":{}}
                         for x in source.FAMILIES},
            "max_active":0,"max_retained":0,"max_states_per_node":0,
            "max_packed_bits_per_state":0,"model_edge_scans":0,
            "model_raw_bit_ops":0,"support_constraints":0,
            "support_ambiguous_graphs":0,"support_source_bit_ops":0,
            "case_sha256":[]}

def apply_record(row,family,depth,seed,vector,operator,arm,period,positive,negative):
    f=row["by_family"][family]
    if positive is None:
        row["unsupported"]+=1;f["unsupported"]+=1
        return
    correct=int(positive and not negative)
    for r in (row,f):
        r["pairs"]+=1;r["correct_pairs"]+=correct
        r["FP"]+=int(negative);r["FN"]+=int(not positive)
    d=f["by_depth"].setdefault(str(depth),{"pairs":0,"correct_pairs":0,
                                          "FP":0,"FN":0})
    d["pairs"]+=1;d["correct_pairs"]+=correct
    d["FP"]+=int(negative);d["FN"]+=int(not positive)
    row["case_sha256"].append(q.digest({
        "seed":seed,"vector":vector,"operator":operator,"period":period,
        "family":family,"arm":arm,"positive":positive,"negative":negative}))

def wing_observe(g,family,operator,tag,base,delta,amount,selected_yes):
    normalized,meta=learner.normalize(g,amount)
    if normalized is None:
        return {"ambiguous":True,"final_proxy":False,
                "FN_with_proxy":False,"first_missing":None,
                "first_pruned":None,"record":None}
    value,work,trace=original_trace.wing_source_blind_trace(
        normalized,base,delta)
    selected,swork,_=learner.wing(g,base,delta,amount)
    need(selected==value and swork==work,
         "ONE_STATE_POSTLEARNING_ORIGINAL_EXACT_TRACE")
    plain=source.plain_for_oracle(g,operator,tag)
    # Scorer-only reconstruction of original public causal witness.
    frontier=[(plain["start"],None,[])]
    for role in plain["roles"]:
        following=[]
        for node,carried,path in frontier:
            for edge in plain["edges"]:
                if edge["from"]!=node or edge["role"]!=role:continue
                dist=0 if carried is None else sum(a!=b for a,b in zip(
                    carried,edge["src_bits"]))
                if carried is None or dist<=(1 if family=="rotate4_tolerant" else 0):
                    following.append((edge["to"],tuple(edge["dst_bits"]),
                                      path+[(edge["to"],tuple(edge["dst_bits"]))]))
                    need(len(following)<=256,"SCORER_ONLY_PATH_BOUND")
        frontier=following
    paths=[p for node,c,p in frontier if node==plain["target"]]
    need(len(paths)==1,"PUBLIC_POSITIVE_WITNESS_ONE")
    joined=joins.causal_join(trace,paths[0],wing=True)
    return {"ambiguous":False,"final_proxy":joined["reference_survived_final"],
            "FN_with_proxy":bool(not selected_yes and
                                  joined["reference_survived_final"]),
            "first_missing":joined["first_reference_missing_candidate_hop"],
            "first_pruned":joined["first_reference_pruned_hop"],
            "record":q.digest(joined),
            "packed_proxy_not_raw_key_identity":True}

def stage(lane,period,base,delta,amount,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    stats={arm:new_stats() for arm in arms}
    obs={"period":period,"public_support_per_graph":24,
         "no_test_label_based_fit":True,
         "semantic_labels_absent_from_public_roles":True,
         "oracle_only_after_model":True,
         "positive_oracle_valid":0,"negative_oracle_invalid":0,
         "literal_untransformed_positive_paths":0,
         "learning_ambiguities":0,"learner_exact_operator_recovered":0}
    if lane=="Wingless":
        obs["packed_one_state"]={"positive_cases":0,
            "final_proxy_present":0,"final_proxy_absent":0,
            "FN_with_terminal_proxy":0,"first_candidate_missing":{},
            "first_proxy_pruned":{},"positive_digests":[]}
    for seed,vector,family,operator,tag,pos,neg in source.pairs(lane,period):
        results={}
        for arm in arms:
            if arm in ("oracle_normalized_upper_bound","oracle_normalized_one_ceiling",
                       "strong_fixed_normalized_supported"):
                continue
            calls=[]
            for graph in (pos,neg):
                val,work,meta=prediction(lane,arm,graph,base,delta,amount,fixed)
                calls.append(val>=0)
                if work is None:
                    need(meta is not None and
                         not meta["learning"]["unique_bijective_mapping"],
                         "ONLY_SOURCE_BLIND_SUPPORT_AMBIGUITY")
                    stats[arm]["support_ambiguous_graphs"]+=1
                    obs["learning_ambiguities"]+=1
                    continue
                r=stats[arm]
                r["max_active"]=max(r["max_active"],work.get("max_active",0))
                r["max_retained"]=max(r["max_retained"],work.get("max_retained",0))
                r["max_states_per_node"]=max(r["max_states_per_node"],
                                                work.get("max_states_per_node",0))
                r["max_packed_bits_per_state"]=max(r["max_packed_bits_per_state"],
                                                   work.get("max_packed_bits_per_state",0))
                r["model_edge_scans"]+=work.get("edge_inspections",
                                              work.get("public_edge_scans",0))
                r["model_raw_bit_ops"]+=work.get("raw_bit_reads",
                                                work.get("raw_bit_ops",0))
                if meta is not None:
                    r["support_constraints"]+=meta["learning"]["comparisons_declared"]
                    r["support_source_bit_ops"]+=meta["edge_bit_operations"]
            results[arm]=tuple(calls)
            apply_record(stats[arm],family,len(pos["roles"]),seed,vector,
                         operator,arm,period,*calls)
        # Scores have already been calculated without any oracle. The
        # following oracle-normalized controls are explicitly separate ceilings.
        ceiling=source.plain_for_oracle(pos,operator,tag)
        floor=source.plain_for_oracle(neg,operator,tag)
        evaluator_ctrl=("oracle_normalized_upper_bound" if lane=="Yggdrasil"
                        else "oracle_normalized_one_ceiling")
        scored=[]
        for graph in (ceiling,floor):
            if lane=="Yggdrasil":
                s,raw,ratio,work=old_ygg.ygg_transition(graph,base,delta,.1)
            else:s,work=old_wing.frozen_packed(graph,base,delta)
            scored.append(s>=0)
            r=stats[evaluator_ctrl]
            r["max_active"]=max(r["max_active"],work.get("max_active",0))
            r["max_retained"]=max(r["max_retained"],work.get("max_retained",0))
            r["max_states_per_node"]=max(r["max_states_per_node"],
                                            work.get("max_states_per_node",0))
            r["max_packed_bits_per_state"]=max(r["max_packed_bits_per_state"],
                                             work.get("max_packed_bits_per_state",0))
        results[evaluator_ctrl]=tuple(scored)
        apply_record(stats[evaluator_ctrl],family,len(pos["roles"]),seed,
                     vector,operator,evaluator_ctrl,period,*scored)
        # Original fixed control is only defined for depth<=9.
        if len(pos["roles"])>9:
            stats["strong_fixed_normalized_supported"]["unsupported"]+=1
            stats["strong_fixed_normalized_supported"]["by_family"][family]["unsupported"]+=1
        else:
            fixed_scores=[]
            for graph in (ceiling,floor):
                result,work=fixed(graph)
                fixed_scores.append(bool(result))
                r=stats["strong_fixed_normalized_supported"]
                r["max_active"]=max(r["max_active"],work.get("max_active",0))
            apply_record(stats["strong_fixed_normalized_supported"],family,
                         len(pos["roles"]),seed,vector,operator,
                         "strong_fixed_normalized_supported",period,
                         *fixed_scores)
        # AFTER predictions+ceilings: reference validation and diagnostics.
        relaxed=family=="rotate4_tolerant"
        obs["positive_oracle_valid"]+=int(source.original.parent.prior.parent.routes15(
            ceiling,relaxed=relaxed)==1)
        obs["negative_oracle_invalid"]+=int(source.original.parent.prior.parent.routes15(
            floor,relaxed=relaxed)==0)
        obs["literal_untransformed_positive_paths"]+=int(
            source.original.parent.prior.parent.routes15(
                public_graph(pos),relaxed=True)>0)
        # Evaluator-only exact map recovery census, never used for prediction.
        learned,info=learner.learn_mapping(pos["demos"],amount)
        if learned is not None:
            required_map,mask=source.truth_mapping(operator)
            obs["learner_exact_operator_recovered"]+=int(all(
                learned[i]==(required_map[i],(mask>>i)&1)
                for i in range(16)))
        if lane=="Wingless":
            diag=wing_observe(pos,family,operator,tag,base,delta,amount,
                             results["example_one_packed"][0])
            d=obs["packed_one_state"]
            d["positive_cases"]+=1
            d["final_proxy_present"]+=int(diag["final_proxy"])
            d["final_proxy_absent"]+=int(not diag["final_proxy"])
            d["FN_with_terminal_proxy"]+=int(diag["FN_with_proxy"])
            for field,key in (("first_candidate_missing",diag["first_missing"]),
                              ("first_proxy_pruned",diag["first_pruned"])):
                name=str(key) if key is not None else "SURVIVED"
                d[field][name]=d[field].get(name,0)+1
            d["positive_digests"].append(q.digest({
                 "seed":seed,"operator":operator,"diag":diag}))
    need(obs["positive_oracle_valid"]==48 and
         obs["negative_oracle_invalid"]==48 and
         obs["literal_untransformed_positive_paths"]==0,
         "NO_CAUSAL_REFERENCE_OR_OLD_SHORTCUT_LEAK")
    if lane=="Wingless":
        d=obs["packed_one_state"]
        need(d["positive_cases"]==48 and len(d["positive_digests"])==48 and
             d["final_proxy_present"]+d["final_proxy_absent"]==48,
             "UNMODIFIED_ONE_SLOT_DIAGNOSTIC_COMPLETE")
    for arm,r in stats.items():
        expected=24 if arm=="strong_fixed_normalized_supported" else 48
        need(r["pairs"]==expected and r["unsupported"]==48-expected
             and len(r["case_sha256"])==expected
             and all(f["pairs"]+f["unsupported"]==12
                     for f in r["by_family"].values())
             and r["max_retained"]<=9
             and (r["max_active"]<=7 if lane=="Yggdrasil"
                  else r["max_active"]<=192),
             "COHORT_AND_HARD_BOUND")
        if arm in ("example_one_packed","raw_original_one",
                   "oracle_normalized_one_ceiling"):
            need(r["max_active"]<=64 and r["max_states_per_node"]==1 and
                 r["max_packed_bits_per_state"]==12,
                 "ORIGINAL_ONE_PACKED_SLOT_ONLY")
    return {"period":period,"pairs":48,"arms":stats,"observations":obs}

def percentile(values,p):
    v=sorted(values);return v[min(len(v)-1,math.ceil(len(v)*p)-1)]

def benchmark(base,delta,amount):
    samples={f:[] for f in source.FAMILIES}
    for seed,vec,f,op,tag,p,n in source.pairs("Wingless","HOLDOUT"):
        if len(samples[f])<6:samples[f].extend((p,n))
    need(all(len(x)==6 for x in samples.values()),"SAME_NEW_PUBLIC_GRAPHS")
    arms={"example_one":lambda x:learner.wing(x,base,delta,amount),
          "raw_one":lambda x:learner.old_wing(x,base,delta),
          "example_three":lambda x:learner.wing(x,base,delta,amount,True)}
    data={arm:{"times":[],"peaks":[],"graphs":0} for arm in arms}
    i=0
    for f in source.FAMILIES:
        for g in samples[f]:
            i+=1;names=list(arms)
            random.Random("F124AJ/resource/"+f+"/"+str(i)).shuffle(names)
            for name in names:
                fn=arms[name];fn(g)
                for _ in range(3):
                    start=time.perf_counter_ns();fn(g)
                    data[name]["times"].append(time.perf_counter_ns()-start)
                gc.collect();tracemalloc.start()
                fn(g);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                data[name]["peaks"].append(peak);data[name]["graphs"]+=1
    out={}
    for name,row in data.items():
        need(row["graphs"]==24 and len(row["times"])==72 and
             len(row["peaks"])==24,"RUNTIME_GRAPH_DENOMINATOR")
        out[name]={"graphs":24,"timed_calls":72,
                   "p50_ns":int(statistics.median(row["times"])),
                   "p95_ns":percentile(row["times"],.95),
                   "p50_peak_python_bytes":int(statistics.median(row["peaks"])),
                   "samples_sha256":q.digest(row)}
    return {"host":os.environ.get("RUNNER_NAME","unknown"),
            "os":platform.platform(),"python":platform.python_version(),
            "measured_learning_plus_model_not_oracle_diagnostics":True,
            "identical_24_public_graphs":True,
            "matched_hardware_superiority_claim":False,
            "arms":out}

def run(paths):
    source.frozen()
    base,delta=ancestry(paths)
    choice,grid=learner.fit_demo_count(
        source.pairs("Yggdrasil","TRAIN"),
        base["Yggdrasil"],delta["Yggdrasil"])
    amount=choice["demos"]
    fixed=old_control.original_fixed()
    report={"schema":SCHEMA,"freeze_git_blob":source.FREEZE_BLOB,
            "original_AI_raw_sha256":PARENT_RAW,
            "support_fit_only_TRAIN":True,
            "HOLDOUT_operators_new_structural_families":True,
            "never_fit_on_HOLDOUT_labels":True,
            "inductive_bias_limited_to_bit_permutation_XOR":True,
            "no_handcoded_operator_classifier":True,
            "protected_first_use":False,
            "independent_science_acceptance":False,
            "optimizer_promotion":False,
            "production":False,
            "accepted_ref_mutations":0,
            "additional_retained_memory":False,
            "matched_hardware_superiority":False,
            "selected_demo_count":choice,"TRAIN_grid":grid,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        item={"lane":lane,
              "TRAIN":stage(lane,"TRAIN",base[lane],delta[lane],
                            amount,fixed),
              "HOLDOUT":stage(lane,"HOLDOUT",base[lane],delta[lane],
                              amount,fixed),
              "original_weights_sha256":q.digest(base[lane]),
              "original_delta_sha256":q.digest(delta[lane])}
        if lane=="Wingless":
            item["benchmark"]=benchmark(base[lane],delta[lane],amount)
        report["lanes"].append(item)
    return report

def main():
    p=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae",
                 "af","ag","ah","ai","output"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args();out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),"NEVER_OVERWRITE_RECEIPT")
    report=run([getattr(args,n) for n in
       ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae",
        "af","ag","ah","ai")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:f.write(raw)
    print("F124AJ_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for item in report["lanes"]:
        d=item["HOLDOUT"]["arms"]
        if item["lane"]=="Yggdrasil":
            print("F124AJ_YGG_HOLDOUT=learned:"+
                 str(d["TRAIN_selected_demonstrations"]["correct_pairs"])+
                 "/48;no_support:"+str(d["original_AG_without_examples"]["correct_pairs"])+
                 "/48;oracle_ceiling:"+str(d["oracle_normalized_upper_bound"]["correct_pairs"])+
                 "/48;demos:"+str(report["selected_demo_count"]["demos"]))
        else:
            print("F124AJ_WING_HOLDOUT=learned_one:"+
                 str(d["example_one_packed"]["correct_pairs"])+
                 "/48;raw:"+str(d["raw_original_one"]["correct_pairs"])+
                 "/48;oracle_ceiling:"+str(d["oracle_normalized_one_ceiling"]["correct_pairs"])+
                 "/48")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as e:
        print("F124AJ_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)

"""F124-AI: 15-source-authenticated TRAIN and new-rule HOLDOUT evaluation.

No protected or previously evaluated relation seeds used. Yggdrasil learns
only the scalar eta (not the engineered public syntax or old weights).
HOLDOUT contains four never-trained operator argument values. Both lanes
preserve original hard state capacity. Model always sees only public graph;
reference restoration and path oracle are downstream after all scoring.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc
from pathlib import Path
import f124ai_frozen_source as source
import f124ai_compositional_model as model
import f124ah_development_evidence as previous
import f124ah_original_model_challenge as original_trace
import f124ac_development_evidence as original_join
import f124ae_scoring_transfer as old
import f124aa_development_evidence as old_fixed
import f124q_independent_binding as q

SCHEMA="forge.research.f124ai.authentic-parameter-heldout-compositional-rule.v1"
PARENT_SHA="fc5e3b4581982d271d8bd87229796addb6c3a579e024463efeb8bb2ffc34abce"
Y_ARMS=("TRAIN_selected_parser","parser_eta_0","parser_historical_AG_eta_0_1",
        "original_AG_without_parser","fixed_supported_parsed")
W_ARMS=("parser_one_packed","original_one_unparsed","parser_three_packed",
        "original_three_unparsed","fixed_supported_parsed")

def need(ok,label):source.need(ok,"RECEIPT_"+label)

def authentic(paths):
    bases,deltas=previous.authenticate(paths[:-1])
    raw=Path(paths[-1]).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==PARENT_SHA,
         "ORIGINAL_AH_RAW_BYTE_SHA")
    receipt=json.loads(raw)
    need(receipt["schema"]=="forge.research.f124ah.fresh-alternate-causal-rule-transfer-and-packed-survival.v1"
         and receipt["freeze_git_blob"]=="3076167057b20eac050b9b0514665614381a6d06"
         and receipt["protected_first_use"] is False
         and receipt["independent_science_acceptance"] is False
         and receipt["optimizer_promotion"] is False
         and receipt["lanes"][0]["DEV"]["models"]["AG_eta_0_1"]["paired"]==0
         and receipt["lanes"][1]["DEV"]["models"]["AA_original_one"]["paired"]==0,
         "AH_NEGATIVE_AND_STATE_IMMUTABLE")
    return bases,deltas

def predict(lane,arm,g,base,delta,eta,fixed):
    if arm=="fixed_supported_parsed":
        if len(g["roles"])>9:return None,None,None,None
        normalized,pre=model.normalize_public_graph(g)
        result,work=fixed(normalized)
        return bool(result),work,None,pre
    if lane=="Yggdrasil":
        if arm=="original_AG_without_parser":
            score,work=model.old_ygg(g,base,delta)
            pre=None
        else:
            coeff=eta if arm=="TRAIN_selected_parser" else (
                 0. if arm=="parser_eta_0" else .1)
            score,raw,ratio,work,pre=model.ygg(g,base,delta,coeff)
    else:
        if arm=="parser_one_packed":
            score,work,pre=model.wing(g,base,delta)
        elif arm=="original_one_unparsed":
            score,work=model.old_wing(g,base,delta);pre=None
        elif arm=="parser_three_packed":
            normalized,pre=model.normalize_public_graph(g)
            score,work=old.frozen_three(normalized,base,delta)
        else:
            score,work=old.frozen_three(g,base,delta);pre=None
    return bool(score>=0),work,score,pre

def positive_path_for_scorer(graph,operator,family):
    """Public reference ONLY after original and normalized predictors finish."""
    original=source.restore_public(graph,operator)
    frontier=[(original["start"],None,[])]
    for role in original["roles"]:
        next_frontier=[]
        for node,carry,hist in frontier:
            for e in original["edges"]:
                if e["from"]!=node or e["role"]!=role:continue
                dist=0 if carry is None else sum(a!=b for a,b in zip(
                    carry,e["src_bits"]))
                if carry is None or dist<=(1 if family=="rotate4_tolerant" else 0):
                    next_frontier.append((e["to"],tuple(e["dst_bits"]),
                                          hist+[(e["to"],tuple(e["dst_bits"]))]))
                    need(len(next_frontier)<=256,"ORACLE_SCORER_ONLY_LIMIT")
        frontier=next_frontier
    result=[hist for node,carry,hist in frontier if node==original["target"]]
    need(len(result)==1,"SINGLE_POSITIVE_PUBLIC_CAUSAL_PATH")
    return result[0]

def wing_audit(pos,operator,family,base,delta,selected_positive):
    # Original source-blind observer on RULE-PARSED source. No state added to
    # model; diagnostic replay and true route join are EXCLUDED from runtime.
    normalized,pre=model.normalize_public_graph(pos)
    original_score,oldwork,trace=original_trace.wing_source_blind_trace(
        normalized,base,delta)
    actual,actualwork,actualpre=model.wing(pos,base,delta)
    need(actual==original_score and actualwork==oldwork
         and pre==actualpre and len(trace)==len(pos["roles"]),
         "ORIGINAL_ONE_STATE_RULE_PARSED_PARITY")
    witness=positive_path_for_scorer(pos,operator,family)
    joined=original_join.causal_join(trace,witness,wing=True)
    return {"first_candidate_missing":joined["first_reference_missing_candidate_hop"],
            "first_packed_proxy_evicted":joined["first_reference_pruned_hop"],
            "final_packed_proxy_visible":joined["reference_survived_final"],
            "missed_positive_with_proxy":bool(
                not selected_positive and joined["reference_survived_final"]),
            "hop_count":len(joined["by_hop"]),
            "packed_proxy_is_not_raw_key_survival":True}

def empty_stats():
    return {"pairs":0,"unsupported":0,"correct_pairs":0,"FP":0,"FN":0,
            "by_family":{f:{"pairs":0,"unsupported":0,
                             "correct_pairs":0,"FP":0,"FN":0,
                             "by_depth":{}}
                         for f in source.FAMILIES},
            "max_active":0,"max_retained":0,"max_states_per_node":0,
            "max_stored_packed_bits":0,
            "model_edge_operations":0,"model_raw_bit_ops":0,
            "extra_rule_bit_ops":0,"case_digest":[]}

def score(lane,period,base,delta,eta,fixed):
    arms=Y_ARMS if lane=="Yggdrasil" else W_ARMS
    records={arm:empty_stats() for arm in arms}
    observed={"posthoc_new_rule_positives":0,"posthoc_new_rule_negatives":0,
              "old_literal_rule_positive_routes":0,
              "training_operator_family_values":list(source.OPERATORS["TRAIN"]),
              "evaluated_unseen_values":list(source.OPERATORS["HOLDOUT"])
                                     if period=="HOLDOUT" else [],
              "no_hidden_oracle_in_model":True}
    if lane=="Wingless":
        observed["packed_survival"]={
            "positives":0,"final_proxy_present":0,"final_proxy_missing":0,
            "missed_positive_despite_proxy":0,
            "first_missing_candidate":{},
            "first_proxy_pruned":{},"positive_digests":[]}
    for seed,vector,family,operator,pos,neg in source.pairs(lane,period):
        preds={}
        for arm in arms:
            pair=[]
            for graph in (pos,neg):
                truth,work,logit,pre=predict(lane,arm,graph,base,delta,eta,fixed)
                pair.append(truth)
                if work is None:continue
                r=records[arm]
                r["max_active"]=max(r["max_active"],work.get("max_active",0))
                r["max_retained"]=max(r["max_retained"],work.get("max_retained",0))
                r["max_states_per_node"]=max(r["max_states_per_node"],
                                               work.get("max_states_per_node",0))
                r["max_stored_packed_bits"]=max(r["max_stored_packed_bits"],
                                                work.get("max_packed_bits_per_state",0))
                r["model_edge_operations"]+=work.get("edge_inspections",
                                                      work.get("public_edge_scans",0))
                r["model_raw_bit_ops"]+=work.get("raw_bit_reads",
                                                 work.get("raw_bit_ops",0))
                if pre is not None:
                    r["extra_rule_bit_ops"]+=pre["additional_raw_bit_ops"]
            yes,no=pair
            r=records[arm];f=r["by_family"][family]
            if yes is None:
                need(no is None and arm=="fixed_supported_parsed"
                     and len(pos["roles"])>=13,
                     "ORIGINAL_FIXED_UNSUPPORTED_LONG_ONLY")
                r["unsupported"]+=1;f["unsupported"]+=1
                continue
            preds[arm]=(yes,no)
            good=int(yes and not no)
            for dest in (r,f):
                dest["pairs"]+=1;dest["correct_pairs"]+=good
                dest["FP"]+=int(no);dest["FN"]+=int(not yes)
            sub=f["by_depth"].setdefault(str(len(pos["roles"])),{
                 "pairs":0,"correct_pairs":0,"FP":0,"FN":0})
            sub["pairs"]+=1;sub["correct_pairs"]+=good
            sub["FP"]+=int(no);sub["FN"]+=int(not yes)
            r["case_digest"].append(q.digest({
               "seed":seed,"v":vector,"period":period,
               "family":family,"operator":operator,"arm":arm,
               "positive":yes,"negative":no}))
        # Only after ALL source-blind predictions, evaluate hidden truth.
        observed["posthoc_new_rule_positives"]+=int(
            source.oracle(pos,operator,family)==1)
        observed["posthoc_new_rule_negatives"]+=int(
            source.oracle(neg,operator,family)==0)
        observed["old_literal_rule_positive_routes"]+=int(
            source.ah.parent.prior.parent.routes15(pos,relaxed=True)>0)
        if lane=="Wingless":
            diag=wing_audit(pos,operator,family,base,delta,
                            preds["parser_one_packed"][0])
            d=observed["packed_survival"]
            d["positives"]+=1
            d["final_proxy_present"]+=int(diag["final_packed_proxy_visible"])
            d["final_proxy_missing"]+=int(not diag["final_packed_proxy_visible"])
            d["missed_positive_despite_proxy"]+=int(
                diag["missed_positive_with_proxy"])
            for field,name in (("first_missing_candidate",
                                diag["first_candidate_missing"]),
                               ("first_proxy_pruned",
                                diag["first_packed_proxy_evicted"])):
                key=str(name) if name is not None else "SURVIVED"
                d[field][key]=d[field].get(key,0)+1
            d["positive_digests"].append(q.digest({
                "seed":seed,"period":period,"family":family,"diagnostic":diag}))
    need(observed["posthoc_new_rule_positives"]==48
         and observed["posthoc_new_rule_negatives"]==48
         and observed["old_literal_rule_positive_routes"]==0,
         "HONEST_NEW_RULE_HOLDOUT_ORIGINAL_SHORTCUT_BLOCKED")
    if lane=="Wingless":
        d=observed["packed_survival"]
        need(d["positives"]==48 and len(d["positive_digests"])==48
             and d["final_proxy_present"]+d["final_proxy_missing"]==48,
             "ONE_STATE_HOPWISE_EVIDENCE")
    for arm,r in records.items():
        required=24 if arm=="fixed_supported_parsed" else 48
        need(r["pairs"]==required and r["unsupported"]==48-required
             and len(r["case_digest"])==required
             and all(k["pairs"]+k["unsupported"]==12
                     for k in r["by_family"].values())
             and r["max_retained"]<=9
             and (r["max_active"]<=7 if lane=="Yggdrasil"
                  else r["max_active"]<=192),
             "FROZEN_SOURCE_AND_MODEL_BUDGET")
        if arm in ("parser_one_packed","original_one_unparsed"):
            need(r["max_active"]<=64 and r["max_states_per_node"]==1
                 and r["max_stored_packed_bits"]==12,
                 "NO_ONE_SLOT_CAPACITY_OR_PAYLOAD_GROWTH")
    return {"period":period,"pairs":48,"models":records,"evaluation":observed}

def percentile(a,p):
    v=sorted(a);return v[min(len(v)-1,math.ceil(p*len(v))-1)]

def benchmark(base,delta,fixed):
    # Original model-only runtime; no expensive science/oracle replay counted.
    items={f:[] for f in source.FAMILIES}
    for seed,v,f,op,pos,neg in source.pairs("Wingless","HOLDOUT"):
        if len(items[f])<6:items[f].extend((pos,neg))
    need(all(len(v)==6 for v in items.values()),"RESOURCE_STRATIFIED_24")
    funcs={"parsed_one":lambda g:model.wing(g,base,delta),
           "unparsed_one":lambda g:model.old_wing(g,base,delta),
           "parsed_three":lambda g:old.frozen_three(
               model.normalize_public_graph(g)[0],base,delta),
           "fixed_supported":lambda g:fixed(model.normalize_public_graph(g)[0])}
    seen={name:{"times":[],"peaks":[],"graphs":0} for name in funcs}
    count=0
    for family in source.FAMILIES:
        for graph in items[family]:
            count+=1
            order=list(funcs)
            random.Random("F124AI/public-operator-cost/"+family+"/"+str(count)).shuffle(order)
            for name in order:
                if name=="fixed_supported" and len(graph["roles"])>9:continue
                run=funcs[name];run(graph)
                for _ in range(3):
                    t=time.perf_counter_ns();run(graph)
                    seen[name]["times"].append(time.perf_counter_ns()-t)
                gc.collect();tracemalloc.start()
                run(graph)
                _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                seen[name]["peaks"].append(peak);seen[name]["graphs"]+=1
    result={}
    for name,r in seen.items():
        n=12 if name=="fixed_supported" else 24
        need(r["graphs"]==n and len(r["times"])==n*3
             and len(r["peaks"])==n,
             "SOURCE_MATCHED_BENCHMARK_DENOMINATORS")
        result[name]={"graphs":n,"timed_repetitions":n*3,
                      "p50_ns":int(statistics.median(r["times"])),
                      "p95_ns":percentile(r["times"],.95),
                      "p50_python_peak_bytes":int(statistics.median(r["peaks"])),
                      "samples_sha256":q.digest(r)}
    return {"runner":os.environ.get("RUNNER_NAME","unknown"),
            "python":platform.python_version(),"platform":platform.platform(),
            "model_only_diagnostic_excluded":True,
            "equal_24_public_graphs_except_fixed_restricted_12":True,
            "hardware_equalized_scientific_superiority":False,
            "results":result}

def run(paths):
    source.frozen()
    bases,deltas=authentic(paths)
    ysel,grid=model.train_eta(source.pairs("Yggdrasil","TRAIN"),
                               bases["Yggdrasil"],deltas["Yggdrasil"])
    selection=ysel["eta"]
    fixed=old_fixed.original_fixed()
    r={"schema":SCHEMA,"freeze_git_blob":source.FREEZE_BLOB,
       "original_AH_raw_sha256":PARENT_SHA,
       "engineered_public_operator_grammar":True,
       "learned_semantics_not_claimed":True,
       "ygg_only_train_scalar_eta":True,
       "holdout_operators_unseen_in_train":True,
       "first_holdout_after_train_selection":True,
       "protected_first_use":False,
       "independent_science_acceptance":False,"optimizer_promotion":False,
       "accepted_ref_mutations":0,"production":False,
       "same_memory_capacity":True,"hardware_matched_superiority":False,
       "selection":ysel,"TRAIN_grid":grid,"lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        row={"lane":lane,
             "TRAIN":score(lane,"TRAIN",bases[lane],deltas[lane],selection,fixed),
             "HOLDOUT":score(lane,"HOLDOUT",bases[lane],deltas[lane],selection,fixed),
             "original_weights_digest":q.digest(bases[lane]),
             "original_deltas_digest":q.digest(deltas[lane])}
        if lane=="Wingless":
            row["benchmark"]=benchmark(bases[lane],deltas[lane],fixed)
        r["lanes"].append(row)
    return r

def main():
    p=argparse.ArgumentParser()
    for n in ("o","t","u","w","x","y","z","aa","ab","ac","ad","ae","af","ag","ah","output"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args();output=Path(a.output)
    need(output.parent.is_dir() and not output.exists(),"NO_OVERWRITE_EVIDENCE")
    report=run([getattr(a,n) for n in (
       "o","t","u","w","x","y","z","aa","ab","ac","ad","ae","af","ag","ah")])
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with output.open("xb") as f:f.write(raw)
    print("F124AI_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        d=lane["HOLDOUT"]["models"]
        if lane["lane"]=="Yggdrasil":
            print("F124AI_YGG_HOLDOUT=parsed:"+str(d["TRAIN_selected_parser"]["correct_pairs"])+
                  "/48;parsed_eta0:"+str(d["parser_eta_0"]["correct_pairs"])+
                  "/48;no_parser:"+str(d["original_AG_without_parser"]["correct_pairs"])+
                  "/48;eta:"+str(report["selection"]["eta"]))
        else:
            print("F124AI_WING_HOLDOUT=parsed_one:"+str(d["parser_one_packed"]["correct_pairs"])+
                  "/48;unparsed:"+str(d["original_one_unparsed"]["correct_pairs"])+"/48")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print("F124AI_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)

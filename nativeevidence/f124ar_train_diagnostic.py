"""F124-AR immutable diagnostic interventions on NEW TRAIN ONLY.

All candidate predictions are evaluated before the source truth is used for
diagnostic attribution. No thresholds, fitted weights or source identities
are selected using previous consumed DEV or the fresh diagnostic truth.
The forced-decoder and oracle arms are evaluator-only, NOT deployable models.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from collections import Counter
from pathlib import Path
import f124ar_frozen_train_source as source
import f124aq_sparse_composition as learned
import f124aq_local_contrast as packed
import f124am_terminal_competition as original
import f124ag_transition_models as ag
import f124aq_train_selection as previous
import f124q_independent_binding as q

SCHEMA="forge.research.f124ar.original-train-failure-attribution.v1"
AQ_TRAIN_SHA="d3a3935cc58d0fe69f46a496ae130a434360bee4169dc22bdad72385af3aa5b0"
AQ_DEV_SHA="0f7a75905ba68851819e10a5e2c308f3955daa84eec0a1fa0184d1b392f2746b"

def need(ok,key):source.need(ok,"DIAGNOSTIC_"+key)

def ancestry(o,t,an,ao,ap,aq,aq_dev):
    base,delta=previous.ancestry(o,t,an,ao,ap)
    a=Path(aq).read_bytes()
    d=Path(aq_dev).read_bytes()
    need(hashlib.sha256(a).hexdigest()==AQ_TRAIN_SHA and
         hashlib.sha256(d).hexdigest()==AQ_DEV_SHA,"ORIGINAL_AQ_RAW_CUSTODY")
    recent=json.loads(a);science=json.loads(d)
    need(recent["schema"]==previous.SCHEMA
         and recent["DEV_cases_generated"]==0
         and recent["DEV_consumed"] is False
         and recent["selected"]["Yggdrasil"]==
             {"mode":"sparse_xor_basis","max_terms":2,
              "validation_wrong_bit_limit":12,"paired":0,"FP":0,"FN":48,
              "abstained_graphs":96,"declared_model_ops":148116,
              "peak_extra_fit_feature_bits":320}
         and recent["selected"]["Wingless"]["mode"]=="relative_lookahead_contrast"
         and recent["selected"]["Wingless"]["alpha"]==.12
         and science["schema"]==
             "forge.research.f124aq.verified-single-wing-first-dev-evidence.v1"
         and science["mode"]=="dev"
         and science["Wingless"]["strict_scientific_candidate_win"] is False
         and science["Yggdrasil"]["DEV_consumed"] is False
         and science["optimizer_promotion"] is False
         and science["independent_science_acceptance"] is False,
         "RETAIN_PRIOR_NEGATIVE_AND_FROZEN_SELECTION")
    return base,delta

def source_oracle(graph,operator,nonce):
    # Only evaluator calls this, after all model predictions are fixed.
    return source.plain(graph,operator,nonce)

def transition(g,base,delta):
    val,_,_,work=ag.ygg_transition(g,list(base),list(delta),.1)
    need(math.isfinite(val) and work["max_active"]<=7
         and work["max_retained"]<=9,"UNCHANGED_ORIGINAL_COGNITION")
    return val

def ytally():
    return {"pairs":0,"paired":0,"FP":0,"FN":0}
def yadd(table,p,n):
    table["pairs"]+=1;table["paired"]+=int(p and not n)
    table["FP"]+=int(n);table["FN"]+=int(not p)

def ygg_diagnostic(rows,base,delta):
    need(len(rows)==48,"FRESH_48_YGG_CASES")
    names=("frozen_public_calibrated","forced_public_mapping",
           "original_raw_unparsed","source_only_correct_inverse")
    stats={k:ytally() for k in names}
    by_family={f:{k:ytally() for k in names} for f in source.FAMILIES}
    by_operator={"affine":{k:ytally() for k in names},
                 "feistel":{k:ytally() for k in names}}
    calibration=Counter()
    wrong_maps=Counter()
    checked={"public_demos":0,"corruptions":0,"paired_support_symmetry":0,
             "fit_bits_reported":0,"mapping_exact_pairs":0,
             "mapping_wrong_pairs":0,"public_validation_abstained_pairs":0,
             "raw_unparsed_vs_oracle_different_pairs":0,
             "forced_vs_oracle_different_pairs":0,
             "forced_positive_with_abstention":0,
             "oracle_positive_with_forced_negative":0}
    for seed,vec,fam,op,nonce,pos,neg in rows:
        # NO ORACLE ACCESSED before public learned predictions below.
        raw,demos,opaque=learned.public.public_task(pos)
        model,fit=learned.train(demos,"sparse_xor_basis",2)
        wrong=0
        for d in demos[20:]:
            prediction,_=learned.predict(model,d["output_bits"])
            wrong+=sum(a!=b for a,b in zip(prediction,d["input_bits"]))
        admitted=wrong<=12
        predictions={}
        normalized={}
        unparsed={}
        for label,g in (("pos",pos),("neg",neg)):
            r,_,_=learned.public.public_task(g)
            for edge in r["edges"]:
                edge["src_bits"],_=learned.predict(model,edge["src_bits"])
            normalized[label]=r
            predictions[label]=transition(r,base,delta)>=0
            unparsed[label]=transition({k:g[k] for k in
                ("start","target","roles","edges")},base,delta)>=0
        decisions={
            "forced_public_mapping":(predictions["pos"],predictions["neg"]),
            "frozen_public_calibrated":(predictions["pos"],predictions["neg"])
                                     if admitted else (False,False),
            "original_raw_unparsed":(unparsed["pos"],unparsed["neg"])}
        oracle_p=source_oracle(pos,op,nonce)
        oracle_n=source_oracle(neg,op,nonce)
        decisions["source_only_correct_inverse"]=(
            transition(oracle_p,base,delta)>=0,
            transition(oracle_n,base,delta)>=0)
        need(pos["demos"]==neg["demos"] and len(demos)==24,
             "AUTHENTIC_SOURCE_SUPPORT_SYMMETRY")
        count=sum(source.relation(x["input_bits"],op)!=x["output_bits"]
                  for x in demos)
        need(count==3,"THREE_AUTHENTIC_CORRUPTIONS")
        checked["public_demos"]+=len(demos)
        checked["corruptions"]+=count
        checked["paired_support_symmetry"]+=1
        checked["fit_bits_reported"]=max(checked["fit_bits_reported"],
                                       fit["fit_feature_bitset_storage_bits"])
        calibration[str(wrong)]+=1
        if not admitted:checked["public_validation_abstained_pairs"]+=1
        bit_wrong=sum(sum(a!=b for a,b in zip(rawedge["src_bits"],truth["src_bits"]))
                      for label,oracle in (("pos",oracle_p),("neg",oracle_n))
                      for rawedge,truth in zip(normalized[label]["edges"],
                                               oracle["edges"]))
        wrong_maps[str(bit_wrong)]+=1
        checked["mapping_exact_pairs"]+=int(bit_wrong==0)
        checked["mapping_wrong_pairs"]+=int(bit_wrong>0)
        checked["raw_unparsed_vs_oracle_different_pairs"]+=int(
            decisions["original_raw_unparsed"]!=decisions["source_only_correct_inverse"])
        checked["forced_vs_oracle_different_pairs"]+=int(
            decisions["forced_public_mapping"]!=decisions["source_only_correct_inverse"])
        checked["forced_positive_with_abstention"]+=int(
            not admitted and decisions["forced_public_mapping"][0])
        checked["oracle_positive_with_forced_negative"]+=int(
            decisions["source_only_correct_inverse"][0] and
            not decisions["forced_public_mapping"][0])
        op_family="affine" if op.startswith("affine_") else "feistel"
        for arm,(p,n) in decisions.items():
            for dest in (stats[arm],by_family[fam][arm],by_operator[op_family][arm]):
                yadd(dest,p,n)
    need(all(x["pairs"]==48 for x in stats.values()) and
         checked["paired_support_symmetry"]==48 and
         checked["corruptions"]==144 and
         checked["mapping_exact_pairs"]+checked["mapping_wrong_pairs"]==48
         and sum(calibration.values())==48 and
         all(y["pairs"]==12 for by in by_family.values() for y in by.values()),
         "INDEPENDENT_ATTRIBUTION_DENOMINATOR")
    return {"lane":"Yggdrasil","source_cases":48,"models":stats,
            "by_family":by_family,"by_operator_type":by_operator,
            "public_validation_wrong_bit_histogram":dict(sorted(calibration.items())),
            "mapped_edge_wrong_bit_histogram":dict(sorted(wrong_maps.items())),
            "diagnostic":checked,
            "oracle_supplied_to_learned_model":False,
            "forced_decoder_is_admissible_model":False,
            "source_only_inverse_is_admissible_model":False,
            "cognitive_cells":{"active":7,"retained":9},
            "transient_fit_feature_bits":checked["fit_bits_reported"]}

def wtally():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,"long_baseline_accept":0,
            "long_new_accept":0,"long_baseline_rejected_by_new":0,
            "negative_fp_resolved":0,"negative_fp_newly_introduced":0,
            "positive_FN_newly_introduced":0,"positive_FN_resolved":0}

def wadd(dest,pp,np,pb,nb,is_long):
    dest["pairs"]+=1
    dest["paired"]+=int(pp and not np)
    dest["FP"]+=int(np)
    dest["FN"]+=int(not pp)
    if is_long:
        dest["long_baseline_accept"]+=int(pb)
        dest["long_new_accept"]+=int(pp)
        dest["long_baseline_rejected_by_new"]+=int(pb and not pp)
    dest["negative_fp_resolved"]+=int(nb and not np)
    dest["negative_fp_newly_introduced"]+=int(not nb and np)
    dest["positive_FN_newly_introduced"]+=int(pb and not pp)
    dest["positive_FN_resolved"]+=int(not pb and pp)

def wing_diagnostic(rows,base,delta):
    need(len(rows)==48,"FRESH_48_WING_CASES")
    total=wtally()
    byfam={f:wtally() for f in source.FAMILIES}
    byop={"affine":wtally(),"feistel":wtally()}
    bydepth={str(d):wtally() for d in (7,8,9,13,14,15)}
    pairs=[]
    extra_ops=0
    for seed,vec,fam,op,nonce,pos,neg in rows:
        # Normalization is evaluator-only and identical for both fixed scorers.
        restored_p=source_oracle(pos,op,nonce)
        restored_n=source_oracle(neg,op,nonce)
        original_values=[original.terminal_competitive(g,base,delta,0.)
                         for g in (restored_p,restored_n)]
        new_values=[packed.score(g,base,delta,
                   "relative_lookahead_contrast",.12)
                   for g in (restored_p,restored_n)]
        pb,nb=(x[0]>=0 for x in original_values)
        pp,np=(x[0]>=0 for x in new_values)
        depth=len(restored_p["roles"])
        need(depth in (7,8,9,13,14,15),"ORIGINAL_FROZEN_DEPTH")
        is_long=depth>=13
        for dest in (total,byfam[fam],
                     byop["affine" if op.startswith("affine_") else "feistel"],
                     bydepth[str(depth)]):
            wadd(dest,pp,np,pb,nb,is_long)
        for _,work in new_values:
            need(work["max_states_per_node"]==1 and
                 work["max_packed_bits_per_state"]==12 and
                 work["max_active"]<=64 and work["extra_retained_states"]==0,
                 "NO_SECOND_STATE_OR_CAPACITY_GROWTH")
            extra_ops+=work["extra_hop_evidence_ops"]
        pairs.append({"case_sha256":q.digest([seed,list(vec),fam]),
                      "family":fam,
                      "operator_type":"affine" if op.startswith("affine_") else "feistel",
                      "depth":depth,
                      "positive_original_score":original_values[0][0],
                      "negative_original_score":original_values[1][0],
                      "positive_candidate_score":new_values[0][0],
                      "negative_candidate_score":new_values[1][0],
                      "baseline_positive_accepted":bool(pb),
                      "candidate_positive_accepted":bool(pp),
                      "baseline_long_positive_accepted":bool(pb and is_long),
                      "candidate_long_positive_accepted":bool(pp and is_long),
                      "baseline_negative_FP":bool(nb),
                      "candidate_negative_FP":bool(np)})
    # No use of consumed AQ DEV outcomes for tuning/selection here.
    aggregate_baseline_fp=sum(int(row["baseline_negative_FP"]) for row in pairs)
    aggregate_baseline_fn=sum(int(not row["baseline_positive_accepted"]) for row in pairs)
    baseline_paired=sum(int(row["baseline_positive_accepted"] and
                            not row["baseline_negative_FP"]) for row in pairs)
    robust=(total["FP"]<aggregate_baseline_fp and
            total["paired"]>=baseline_paired and
            total["long_baseline_rejected_by_new"]==0 and
            all(v["negative_fp_newly_introduced"]==0 for v in byfam.values()))
    need(total["pairs"]==48 and
         all(x["pairs"]==12 for x in byfam.values()) and
         sum(x["pairs"] for x in byop.values())==48 and
         sum(x["pairs"] for x in bydepth.values())==48,
         "WINGLESS_FULL_STRATIFIED_DENOMINATOR")
    return {"lane":"Wingless","source_cases":48,"selected_mode":"relative_lookahead_contrast",
            "selected_alpha":.12,"candidate":total,
            "original_baseline":{"pairs":48,"paired":baseline_paired,
                                 "FP":aggregate_baseline_fp,"FN":aggregate_baseline_fn},
            "by_family":byfam,"by_operator_type":byop,"by_depth":bydepth,
            "individual_case_diagnostics":pairs,
            "additional_hop_ops":extra_ops,
            "robust_diagnostic_signal":robust,
            "source_only_normalization_applied_equally":True,
            "retained_states_per_node":1,"packed_bits":12,"max_active_nodes":64,
            "source_oracle_was_model_input":False}

def run(o,t,an,ao,ap,aq,aq_dev):
    source.frozen()
    base,delta=ancestry(o,t,an,ao,ap,aq,aq_dev)
    y=source.pairs("Yggdrasil","TRAIN")
    w=source.pairs("Wingless","TRAIN")
    return {"schema":SCHEMA,"frozen_source_blob":source.FREEZE_BLOB,
            "qualified_parent_AQ_head":"cb2d4ff16e8054e790a0f1dfb4e558b97ebcb3a1",
            "Yggdrasil":ygg_diagnostic(y,base["Yggdrasil"],delta["Yggdrasil"]),
            "Wingless":wing_diagnostic(w,base["Wingless"],delta["Wingless"]),
            "only_fresh_TRAIN":True,"historical_DEV_used_for_selection":False,
            "new_DEV_generated":0,"new_DEV_consumed":False,
            "source_only_oracle_diagnostics_are_scientific_wins":False,
            "independent_science_acceptance":False,
            "optimizer_promotion":False,"production_activation":False}

def main():
    ap=argparse.ArgumentParser()
    for name in ("o","t","an","ao","ap","aq","aq_dev","output"):
        ap.add_argument("--"+name,required=True)
    a=ap.parse_args()
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(),"APPEND_ONLY_DIAGNOSTIC")
    d=run(a.o,a.t,a.an,a.ao,a.ap,a.aq,a.aq_dev)
    raw=json.dumps(d,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:f.write(raw)
    print("F124AR_TRAIN_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124AR_YGG="+json.dumps(d["Yggdrasil"]["models"],sort_keys=True))
    print("F124AR_YGG_ATTRIBUTION="+json.dumps(d["Yggdrasil"]["diagnostic"],sort_keys=True))
    w=d["Wingless"]
    print("F124AR_WING="+json.dumps({"candidate":{k:w["candidate"][k] for k in
              ("paired","FP","FN","long_baseline_rejected_by_new")},
              "control":w["original_baseline"],
              "robust":w["robust_diagnostic_signal"]},sort_keys=True))
    print("F124AR_NEW_DEV_CONSUMED=false")
    print("F124AR_SCIENTIFIC_ACCEPTANCE=false")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AR_DIAGNOSTIC_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)

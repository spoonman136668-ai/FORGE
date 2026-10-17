"""F124-E immutable TRAIN eviction/identity audit, never a candidate retraining.

Public-graph inference is independently reimplemented as a floating-point
*witness* with extra scorer-only causal lineage. The qualified original
forward() at slot capacity 3 must agree numerically before any interpretation.
A capacity-32 pass is an explicitly non-preregistered posthoc counterfactual,
NOT a permitted model, optimizer policy, threshold, or scientific result.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import f123_cross_os_custody as f123
import f124e_key_value_environment as environment
import f124e_learned_associative_memory as model

BASE_HEAD="878ba8e558a6f5fc122ff7468af0d02362750143"
TRAIN_SHA="f54ff4be9b3b567a2faf913e3348da114e2701ee4eab4bcc1f52c8be07aa8585"
F123_SHA="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
GENERATOR_BLOB="a310c8f285b18a73bdce864335153beba4e1ea3d"
MODEL_BLOB="83c55510d329f11c6552c927e80f2435b855a427"
SCHEMA="forge.research.f124e.posthoc-frozen-eviction-causal-audit.v1"
D=8
CAPS=(3,32)

def need(test,code):
    environment.require(test,"FROZEN_EVICTION_"+code)

def sigmoid(x):
    return 1./(1.+math.exp(-max(-40.,min(40.,x))))

def key(e):
    return (e["from"],e["to"],e["role"],tuple(e["src_bits"]),tuple(e["dst_bits"]))

def witness(graph, weights, arm, capacity=3):
    """Replay public inference and retain exact-key matching as scorer metadata.

    The model sees only mass and eight learned dimensions. Fields 'valid' and
    'raw_carried' here never feed a model gate, salience or record selection.
    """
    environment.validate(graph)
    need(capacity in CAPS and arm in ("A","B")
         and len(weights)==(132 if arm=="A" else 156)
         and all(type(v) in (int,float) and math.isfinite(v) for v in weights),
         "BAD_FROZEN_MODEL_OR_DIAGNOSTIC_CAPACITY")
    edges=sorted(graph["edges"],key=key)
    cache={}
    def embed(bits):
        k=tuple(bits)
        if k not in cache:
            cache[k]=tuple(math.tanh(sum(weights[j*16+i]*((2*v-1)/4.)
                                               for i,v in enumerate(bits)))
                           for j in range(D))
        return cache[k]
    def dot(x,y):
        return sum(a*b for a,b in zip(x,y))/D
    # Each trace holds mass, learned latent key, *scorer-only* exact raw key
    # and publicly checkable causal-prefix validity.
    states={graph["start"]:[(1.,None,None,True)]}
    evictions=valid_evictions=scans=messages=0
    terminal_valid=terminal_invalid=0
    per_hop=[]
    for role in graph["roles"]:
        arriving={}
        for node in sorted(states):
            local=[e for e in edges if e["from"]==node and e["role"]==role]
            for mass,latent,rawkey,valid in states[node]:
                scans+=len(edges)
                for e in local:
                    if latent is None: gate=1.
                    else:
                        gate=sigmoid(weights[128]*dot(latent,embed(e["src_bits"]))+weights[129])
                    destination=embed(e["dst_bits"])
                    new_mass=mass*gate
                    if arm=="B":
                        projection=[dot(destination,weights[132+s*D:132+(s+1)*D])
                                    for s in range(3)]
                        strongest=max(range(3),key=lambda s:(projection[s],-s))
                        new_mass*=sigmoid(projection[strongest])
                    # This comparison is strictly posthoc scorer provenance;
                    # it cannot influence learned output or memory priority.
                    consistent=valid and (rawkey is None or rawkey==tuple(e["src_bits"]))
                    arriving.setdefault(e["to"],[]).append(
                        (new_mass,destination,tuple(e["dst_bits"]),consistent,key(e)))
                    messages+=1
                    need(messages<=8192,"DIAGNOSTIC_WORK_BUDGET")
        states={}
        hop_dropped=hop_valid_dropped=0
        for node in sorted(arriving):
            candidates=arriving[node]
            # Identical model salience and tie break as original F124-E.
            candidates.sort(key=lambda item:(-item[0],item[4]))
            discarded=candidates[capacity:]
            hop_dropped+=len(discarded)
            hop_valid_dropped+=sum(bool(item[3]) for item in discarded)
            states[node]=[(mass,latent,rawkey,valid)
                          for mass,latent,rawkey,valid,_ in candidates[:capacity]]
        evictions+=hop_dropped
        valid_evictions+=hop_valid_dropped
        per_hop.append({"dropped":hop_dropped,
                        "causally_valid_prefix_dropped":hop_valid_dropped,
                        "live_records":sum(len(v) for v in states.values())})
        need(sum(len(v) for v in states.values())<=128,
             "DIAGNOSTIC_MEMORY_BUDGET")
    target=states.get(graph["target"],[])
    total=sum(mass for mass,_,_,_ in target)
    terminal_valid=sum(bool(x[3]) for x in target)
    terminal_invalid=len(target)-terminal_valid
    prediction=sigmoid(weights[130]*(total-weights[131]))
    return {"score":prediction,"causal_target_records":terminal_valid,
            "noncausal_target_records":terminal_invalid,
            "all_record_evictions":evictions,
            "causally_consistent_prefix_evictions":valid_evictions,
            "public_edge_scans":scans,"messages_propagated":messages,
            "peak_live_records":max((h["live_records"] for h in per_hop),default=0),
            "per_hop":per_hop}

def source_identity():
    environment.frozen();model.contract()
    for mod,expected in ((environment,GENERATOR_BLOB),(model,MODEL_BLOB)):
        raw=Path(mod.__file__).read_bytes().replace(b"\r\n",b"\n")
        need(environment.git_blob(raw)==expected,"ORIGINAL_MODEL_OR_SOURCE_DRIFT")

def source_receipt(file):
    data=Path(file).read_bytes()
    need(hashlib.sha256(data).hexdigest()==TRAIN_SHA,"ORIGINAL_TRAIN_DIGEST_MISMATCH")
    out=json.loads(data)
    need(out["schema"]=="forge.research.f124e.train-only-associative-key-value-custody.v1"
         and out["source_sha"]==BASE_HEAD and out["phase"]=="TRAIN_ONLY"
         and out["generator_git_blob"]==GENERATOR_BLOB and out["model_git_blob"]==MODEL_BLOB
         and out["confirmation_cases_generated"]==0 and not out["scientific_first_use"]
         and out["scientific_acceptances"]==0 and len(out["lanes"])==2,
         "ORIGINAL_EVIDENCE_IDENTITY")
    return out

def diagnostics(report_path, parent_dir):
    source_identity()
    source=source_receipt(report_path)
    origin,orig_sha=f123.read_receipt(parent_dir)
    need(orig_sha==F123_SHA and origin["source_sha"]==
         "7882849a59964f412a87589be653114e7bf64d52"
         and [x["lane"] for x in origin["lanes"]]==["Wingless","Yggdrasil"],
         "ORIGINAL_VECTOR_BIRTH_DRIFT")
    out=[]
    for recorded,parents in zip(source["lanes"],origin["lanes"]):
        lane=recorded["lane"]
        vectors=parents["training_vectors"]
        need(lane==parents["lane"] and vectors==recorded["train_vectors"]
             and recorded["frozen_selector_arm"]=="A"
             and set(recorded["model_arms"])=={"A","B"},"LANE_SOURCE_IDENTITY")
        graphs=[]
        for v in vectors:
            for seed in environment.TRAIN[lane]:
                p,n=environment.build(seed,v,lane,"TRAIN")
                graphs.append((p,n))
        need(len(graphs)==48,"FROZEN_TRAIN_COHORT_SIZE")
        arm_results={}
        for arm in ("A","B"):
            info=recorded["model_arms"][arm]
            weights=info["weights"]
            need(model.identity(weights)==info["trained_weight_sha256"]
                 and info["train_pairs"]==48 and info["epochs"]==100
                 and info["train_paired_correct"]==0,"FROZEN_WEIGHT_IDENTITY")
            cap_reports={}
            for cap in CAPS:
                cases=[]
                for p,n in graphs:
                    yes=witness(p,weights,arm,cap)
                    no=witness(n,weights,arm,cap)
                    if cap==3:
                        for raw,wit in ((p,yes),(n,no)):
                            original=model.forward(raw,weights,arm)[0]
                            need(abs(original-wit["score"])<=1e-12,
                                 "INDEPENDENT_EXACT_REPLAY_MISMATCH")
                    need(yes["causal_target_records"]<=1 and
                         no["causal_target_records"]==0,
                         "IMPOSSIBLE_PUBLIC_CAUSAL_PROVENANCE")
                    cases.append({"positive_score":round(yes["score"],12),
                                  "negative_score":round(no["score"],12),
                                  "positive_has_causal_target":bool(yes["causal_target_records"]),
                                  "positive_record_evictions":yes["all_record_evictions"],
                                  "negative_record_evictions":no["all_record_evictions"],
                                  "positive_causal_prefix_drops":yes["causally_consistent_prefix_evictions"],
                                  "negative_causal_prefix_drops":no["causally_consistent_prefix_evictions"],
                                  "positive_noncausal_target_records":yes["noncausal_target_records"],
                                  "negative_noncausal_target_records":no["noncausal_target_records"]})
                paired=sum(x["positive_score"]>=.5 and x["negative_score"]<.5 for x in cases)
                if cap==3:
                    need(paired==info["train_paired_correct"],"FROZEN_PAIRED_RESULT_DRIFT")
                cap_reports[str(cap)]={
                    "train_paired_correct":paired,
                    "positive_ranks_above_negative":sum(x["positive_score"]>x["negative_score"] for x in cases),
                    "causal_target_retained":sum(x["positive_has_causal_target"] for x in cases),
                    "positive_cases_with_eviction":sum(x["positive_record_evictions"]>0 for x in cases),
                    "positive_cases_with_valid_prefix_eviction":sum(x["positive_causal_prefix_drops"]>0 for x in cases),
                    "mean_positive_evictions":round(sum(x["positive_record_evictions"] for x in cases)/48,9),
                    "mean_positive_valid_prefix_evictions":round(sum(x["positive_causal_prefix_drops"] for x in cases)/48,9),
                    "mean_positive_noncausal_target_records":round(sum(x["positive_noncausal_target_records"] for x in cases)/48,9),
                    "cases":cases}
            a=cap_reports["3"];b=cap_reports["32"]
            arm_results[arm]={
                "capacity_3_qualified_frozen_model":a,
                "capacity_32_nonpreregistered_diagnostic":b,
                "causal_target_restored_by_relaxation":sum(
                    not x["positive_has_causal_target"] and y["positive_has_causal_target"]
                    for x,y in zip(a["cases"],b["cases"])),
                "lost_causal_target_from_relaxation":sum(
                    x["positive_has_causal_target"] and not y["positive_has_causal_target"]
                    for x,y in zip(a["cases"],b["cases"])),
                "training_label_oracle_used_for_retention":False}
        out.append({"lane":lane,"arms":arm_results,
                    "source_vectors_sha256":model.identity(vectors)})
    return {"schema":SCHEMA,"original_source_head":BASE_HEAD,
            "original_immutable_train_receipt_sha256":TRAIN_SHA,
            "original_candidate_vector_receipt_sha256":F123_SHA,
            "freeze_git_blob":environment.FREEZE_BLOB,
            "no_weights_changed":True,"training_rerun":False,
            "capacity32_is_posthoc_non_scientific":True,
            "reserved_confirmation_generated":0,
            "original_first_use_authorized":False,
            "science_accepted":False,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"resource_matched_superiority_proven":False,
            "lanes":out}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--f124e-report",required=True)
    ap.add_argument("--f123-train-dir",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"REFUSE_REPORT_OVERWRITE")
    report=diagnostics(args.f124e_report,args.f123_train_dir)
    target.write_text(json.dumps(report,sort_keys=True,separators=(",",":"))+"\n",
                      encoding="utf-8")

if __name__=="__main__":
    try:main()
    except (environment.Invalid,f123.Invalid,ValueError,KeyError,TypeError,OSError) as e:
        print("F124E_DIAGNOSTIC=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)

"""Independent F10 training and pinned-Y070 validation replay.

Training table is recomputed from F9's historical PUBLIC samples by an
independent calibrated-residual implementation; no call to F10.train.
After exact training-model comparison, each of 96 F10 source trials is
replayed and compared at public-value and physical-matching level.
"""
import argparse,hashlib,json
from pathlib import Path
from worker import load_source,evaluate,SOURCE_COMMIT
from train import canonical
from policy import PROBES,EPISODES,TRAIN,CHECK,PAIRS,SCHEMA

def need(value,why):
    if not value:raise ValueError("F10_INDEPENDENT_"+why)

def independently_refit(parent):
    rows=parent["training"]
    need(type(rows) is list and len(rows)==192
         and all(r["seed"] in TRAIN for r in rows),"TRAIN_ONLY")
    counts={(t,flag,k):[0,0] for t in PROBES for flag in (0,1) for k in range(14)}
    identities=set()
    for row in rows:
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"],row["rule"])
        need(key not in identities,"TRAINING_DUPLICATE")
        identities.add(key)
        sample=row["sample_trace"]
        h={t:dict(zip(sample["addresses"][i],sample["public_values"][i]))
           for i,t in enumerate(EPISODES)}
        need(all(len(h[t])==2 for t in EPISODES),"PUBLIC_ONLY_SAMPLES")
        base=h[0][0]
        slope=(h[0][1]-base)%16
        velocity=(h[1][0]-base)%16
        need(slope%2==1 and h[1][1]==(base+slope+velocity)%16,
             "PUBLIC_ANCHOR")
        start=(base+3*slope+5*velocity)%14
        inverse=pow(slope,-1,16)
        anomaly_seen=False
        for t in PROBES:
            previously_anomalous=int(anomaly_seen)
            for cell,value in h[t].items():
                need(type(cell) is int and 2<=cell<16
                     and type(value) is int and 0<=value<16,"PUBLIC_SCALAR")
                offset=(cell-2-start)%14
                inferred=(inverse*(value-base-t*velocity))%16
                bad=int(inferred!=cell)
                counts[(t,previously_anomalous,offset)][0]+=1
                counts[(t,previously_anomalous,offset)][1]+=bad
                anomaly_seen=anomaly_seen or bool(bad)
    need(len(identities)==192,"TRAINING_CASE_ID")
    result=[{"episode":t,"prior_anomaly":flag,"offset":offset,
             "observations":counts[(t,flag,offset)][0],
             "anomalies":counts[(t,flag,offset)][1]}
            for t in PROBES for flag in (0,1) for offset in range(14)]
    need(sum(x["observations"] for x in result)==1152,"TRAIN_OBSERVATIONS")
    return result

def review(result,parent_raw,witness_raw,root):
    parent=json.loads(parent_raw);witness=json.loads(witness_raw)
    model=result.get("model",{})
    need(result.get("schema")=="forge.f10.automatic-public-information-value-engineering.v1"
         and result.get("status")=="F3_USED_ONLY_NO_SCIENTIFIC_AUTHORITY"
         and result.get("parent_f9_sha256")==hashlib.sha256(parent_raw).hexdigest()
         and result.get("parent_f9_independent_sha256")==hashlib.sha256(witness_raw).hexdigest()
         and result.get("parent_source_commit")==SOURCE_COMMIT
         and parent.get("schema")=="forge.f9.automatic-public-order-training.v1"
         and parent.get("source_commit")==SOURCE_COMMIT
         and parent.get("status")=="F3_PREVIOUSLY_USED_ENGINEERING_ONLY"
         and parent.get("first_use_claims")==0
         and witness.get("schema")=="forge.f9.independent-public-timing-training-review.v1"
         and witness.get("status")=="PREVIOUSLY_USED_F3_SPLIT_QUALIFIED_NOT_NEW_SCIENCE"
         and witness.get("replayed_training_arms")==192
         and witness.get("replayed_validation_arms")==288
         and witness.get("selected_rule")=="START_GE7_EARLY"
         and witness.get("scientific_dispatch_authorized") is False,
         "PARENT_OR_SOURCE_IDENTITY")
    need(model.get("schema")==SCHEMA
         and model.get("status")=="PREVIOUSLY_USED_F3_TRAIN_ONLY_NOT_SCIENCE"
         and model.get("parent_f9_sha256")==hashlib.sha256(parent_raw).hexdigest()
         and model.get("parent_f9_independent_sha256")==hashlib.sha256(witness_raw).hexdigest()
         and model.get("train_seeds")==list(TRAIN)
         and model.get("validation_seeds")==list(CHECK)
         and model.get("train_public_observations")==1152
         and model.get("learned_objective")==
           "posterior_expected_Brier_uncertainty_reduction_p_times_one_minus_p"
         and model.get("smoothing_prior")=="Beta(1,1)"
         and model.get("training_label")==
           "publicly_calibrated_coordinate_residual_nonzero"
         and model.get("public_scalar_reads")==10
         and model.get("retained_limit")==9
         and model.get("first_use_claims")==0
         and model.get("scientific_dispatch_authorized") is False,
         "FROZEN_MODEL_BOUNDARY")
    need(model.get("table")==independently_refit(parent),
         "FITTED_VALUE_OR_TRAINING_LABEL_TAMPER")
    source=load_source(root)
    rows=result.get("validation")
    need(type(rows) is list and len(rows)==96,"VALIDATION_CASES")
    stats={"cases":0,"pre":0,"post":0,"detections":0,
           "steady_errors":0,"earliest_detection":None,
           "anomalous_before_episode_5":0}
    i=0
    for pair in PAIRS:
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in CHECK:
                    for match in source.POLICIES:
                        item=rows[i]
                        expected=evaluate(source,model,seed,pair,regime,family,match)
                        need(item==expected,"REAL_Y070_OR_PUBLIC_TRACE_DRIFT")
                        stats["cases"]+=1
                        stats["pre"]+=expected["pre_mismatch"]
                        stats["post"]+=expected["post_mismatch"]
                        stats["detections"]+=int(expected["first_detection"] is not None)
                        if regime=="steady":
                            stats["steady_errors"]+=expected["pre_mismatch"]+expected["post_mismatch"]
                        if expected["sample_trace"]["decision"]["anomaly_after_3"]:
                            stats["anomalous_before_episode_5"]+=1
                        first=expected["first_detection"]
                        if first is not None:
                            stats["earliest_detection"]=first if stats["earliest_detection"] is None else min(first,stats["earliest_detection"])
                        i+=1
    need(stats==result.get("validation_summary"),"F10_AGGREGATE")
    controls={}
    for rule in ("ALWAYS_EARLY","ALWAYS_SWAP",parent["model"]["selected_rule"]):
        data=[r for r in parent["validation"] if r["rule"]==rule]
        need(len(data)==96 and all(r["seed"] in CHECK for r in data),
             "DISJOINT_F9_CONTROLS")
        controls[rule]={"cases":96,
                        "mismatches":sum(r["pre_mismatch"]+r["post_mismatch"] for r in data),
                        "detections":sum(r["first_detection"] is not None for r in data)}
    need(controls==result.get("f9_used_validation_controls")
         and controls["ALWAYS_SWAP"]["mismatches"]==66,
         "HISTORICAL_CONTROLS")
    need(result.get("scientific_winner_selected") is False
         and result.get("scientific_dispatch_authorized") is False
         and all(result.get(k)==0 for k in (
             "new_cohort_uses","new_first_use_claims",
             "new_scientific_originals","paid_api_calls")),"SCIENTIFIC_AUTHORITY")
    return {"schema":"forge.f10.independent-learned-information-value-review.v1",
            "status":"F3_USED_SOURCE_REPLAY_QUALIFIED_NOT_SCIENCE",
            "training_public_labels":1152,"replayed_validation":96,
            "validation_summary":stats,
            "best_fixed_historical_mismatches":66,
            "f10_historical_mismatches":stats["pre"]+stats["post"],
            "new_first_use_claims":0,
            "scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for name in ("record","parent","witness","source-root","out"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args()
    result=review(json.loads(Path(a.record).read_bytes()),
                  Path(a.parent).read_bytes(),Path(a.witness).read_bytes(),
                  a.source_root)
    encoded=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    with Path(a.out).open("xb") as output:output.write(encoded)
    print("F10_INDEPENDENT_EXPECTED_INFORMATION_VALUE_TRAINING=PASS")
    print("F10_INDEPENDENT_PINNED_SOURCE_REPLAY=PASS")
    print("F10_HISTORICAL_MISMATCHES="+str(result["f10_historical_mismatches"]))
    print("F10_BEST_FIXED_CONTROL=66")
    print("F10_WITNESS_SHA256="+hashlib.sha256(encoded).hexdigest())
    print("F10_SCIENTIFIC_FIRST_USE=ZERO")
if __name__=="__main__":main()

"""F6 independent source-identity and split-check replay.

No import of F6 learner.fit. Threshold is recomputed from F5 paired
training labels and independently regenerated PUBLIC development reads.
Frozen threshold is then evaluated again on the pinned real Y070 source.
This is independent engineering review only, NOT original science.
"""
import argparse,hashlib,json
from pathlib import Path
from learner import choose_f6,THRESHOLDS,TRAIN_SEEDS,CHECK_SEEDS
from worker import evaluate,load_source,SOURCE_COMMIT
from run_engineering import canon

def require(ok,why):
    if not ok:raise ValueError("F6_INDEPENDENT_"+why)

def independently_select(source,parent):
    arms={}
    for row in parent["records"]:
        if row["arm"] not in ("F5-MEMORY","F5-COVERAGE"):continue
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"])
        arms.setdefault(key,{})
        require(row["arm"] not in arms[key],"DUPLICATE_PARENT")
        arms[key][row["arm"]]=row
    require(len(arms)==192 and all(len(v)==2 for v in arms.values()),
            "PARENT_PAIRS")
    examples=[]
    for key,values in sorted(arms.items()):
        seed,pair,regime,family,_=key
        if seed not in TRAIN_SEEDS:continue
        require(pair in ((8,10),(11,13)) and regime in ("steady","onset1"),
                "PARENT_SCOPE")
        m=source.m
        m.y58.install_transposition(None if regime=="steady" else 1,pair,
                                    {"anchor_pair_checks":0})
        try:
            public={}
            for episode in (0,1,3,5):
                cells=choose_f6(episode,public,1)
                public[episode]={cell:m.y64.y46.coordinate(
                    cell,seed,episode,family,"late_shock") for cell in cells}
            b=public[0][0];slope=(public[0][1]-b)%16
            velocity=(public[1][0]-b)%16
            require(slope%2==1,"PUBLIC_SLOPE")
            strength=0
            for cell,val in public[5].items():
                projected=(pow(slope,-1,16)*(val-(b+5*velocity)))%16
                residual=(projected-cell)%16
                strength=max(strength,min(residual,16-residual))
        finally:
            m.y49.restore_environment()
        left=values["F5-COVERAGE"]
        right=values["F5-MEMORY"]
        rechecked=set(right["sample_trace"]["addresses"][3])==set(
                      right["sample_trace"]["addresses"][4])
        require(rechecked==(strength>0),"PARENT_MEMORY_FIDELITY")
        examples.append((strength,left["pre_mismatch"]+left["post_mismatch"],
                         right["pre_mismatch"]+right["post_mismatch"]))
    require(len(examples)==96,"TRAIN_CASES")
    ranked=[]
    for threshold in THRESHOLDS:
        total=0;rechecks=0
        for strength,cost_base,cost_memory in examples:
            recheck=strength>0 and strength>=threshold
            total+=cost_memory if recheck else cost_base
            rechecks+=int(recheck)
        ranked.append((total,rechecks,threshold))
    return min(ranked),ranked

def verify(report,parent_raw,successor_raw,root):
    parent=json.loads(parent_raw)
    successor=json.loads(successor_raw)
    require(report.get("schema")=="forge.f6.automatic-trained-engineering-evidence.v1"
            and report.get("status")=="HISTORICAL_F3_USED_ONLY_INDEPENDENT_REVIEW_REQUIRED"
            and report.get("parent_y070_commit")==SOURCE_COMMIT
            and report.get("parent_evidence_sha256")==hashlib.sha256(parent_raw).hexdigest()
            and report.get("automatic_successor_sha256")==hashlib.sha256(successor_raw).hexdigest(),
            "EVIDENCE_IDENTITY")
    require(successor.get("selected",{}).get("proposal_id")==
            "Y-FORGE-F6-UNCERTAINTY-CALIBRATION-PROPOSAL"
            and successor.get("scientific_dispatch_authorized") is False
            and successor.get("new_first_use_claims")==0
            and successor.get("new_seed_allocations")==0,"SUCCESOR_ORIGINAL_AUTHORITY")
    require(parent.get("status")=="F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE"
            and parent.get("historical_seeds")==[67204,67205,67206,67207]
            and parent.get("historical_pairs")==[[8,10],[11,13]]
            and parent.get("scientific_authority") is False
            and parent.get("scientific_originals_executed")==0,"PARENT")
    model=report.get("model",{})
    require(model.get("status")=="TRAINED_ON_PREVIOUSLY_USED_F3_DEVELOPMENT_ONLY"
            and model.get("schema")=="forge.f6.public-only.calibrated-memory-threshold.v1"
            and model.get("hypothesis_id")==successor["selected"]["proposal_id"]
            and model.get("training_seed_ids")==[67204,67205]
            and model.get("untouched_validation_seed_ids")==[67206,67207]
            and model.get("training_cases")==96
            and model.get("evaluated_thresholds")==list(THRESHOLDS)
            and model.get("public_scalar_reads")==10
            and model.get("retained_capacity")==9
            and model.get("new_f6_cohort_accesses")==0
            and model.get("new_first_use_claims")==0
            and model.get("scientific_dispatch_authorized") is False,
            "MODEL")
    source=load_source(root)
    winner,rows=independently_select(source,parent)
    require(model["frozen_threshold"]==winner[2] and
            model["training_objective_mismatches"]==winner[0] and
            model["training_recheck_count"]==winner[1] and
            model["threshold_scores"]==[
                {"threshold":t,"training_mismatches":m,"training_rechecks":n}
                for m,n,t in rows],"FROZEN_TRAINING_OPTIMUM")
    observed=report.get("validation_records")
    require(type(observed) is list and len(observed)==96,"VALIDATION_N")
    totals={"cases":0,"pre":0,"post":0,"detections":0,"steady_errors":0,"rechecks":0}
    index=0
    for pair in ((8,10),(11,13)):
        for regime in ("steady","onset1"):
            for family in source.FAMILIES:
                for seed in CHECK_SEEDS:
                    for policy in source.POLICIES:
                        expected=evaluate(source,model,seed,pair,regime,family,policy)
                        require(observed[index]==expected,"TRACE_OR_METRIC_MISMATCH")
                        totals["cases"]+=1
                        totals["pre"]+=expected["pre_mismatch"]
                        totals["post"]+=expected["post_mismatch"]
                        totals["detections"]+=int(expected["first_detection"] is not None)
                        totals["rechecks"]+=int(expected["sample_trace"]["recheck"])
                        if regime=="steady":
                            totals["steady_errors"]+=expected["pre_mismatch"]+expected["post_mismatch"]
                        index+=1
    require(totals==report.get("validation_summary"),"SUMMARY")
    controls={arm:{"cases":0,"total":0,"rechecks":0}
              for arm in ("F5-COVERAGE","F5-MEMORY")}
    for row in parent["records"]:
        if row["seed"] not in CHECK_SEEDS or row["arm"] not in controls:continue
        total=controls[row["arm"]]
        total["cases"]+=1
        total["total"]+=row["pre_mismatch"]+row["post_mismatch"]
        total["rechecks"]+=int(set(row["sample_trace"]["addresses"][3])==
                              set(row["sample_trace"]["addresses"][4]))
    require(controls==report.get("matched_f5_validation_controls"),"CONTROL")
    require(all(report.get(k)==0 for k in (
        "new_first_use_claims","new_originals","new_cohort_accesses","paid_api_calls"))
        and report.get("scientific_authority") is False
        and report.get("scientific_winner_selected") is False,
        "NO_SCIENTIFIC_AUTHORITY")
    return {"schema":"forge.f6.independent-learned-uncertainty-engineering-review.v1",
            "status":"F3_USED_SPLIT_REPLAY_QUALIFIED_NOT_PROSPECTIVE_SCIENCE",
            "validation_cases":index,"learned_threshold":winner[2],
            "validation_summary":totals,"controls":controls,
            "new_first_use_claims":0,"scientific_dispatch_authorized":False}

def main():
    p=argparse.ArgumentParser()
    for k in ("record","parent","successor","source-root","out"):
        p.add_argument("--"+k,required=True)
    a=p.parse_args()
    evidence=Path(a.record).read_bytes()
    outcome=verify(json.loads(evidence),Path(a.parent).read_bytes(),
                   Path(a.successor).read_bytes(),a.source_root)
    with Path(a.out).open("xb") as f:f.write(canon(outcome))
    print("F6_INDEPENDENT_TRAIN_ONLY_AND_SOURCE_REPLAY=PASS")
    print("F6_REPLAYED_VALIDATION="+str(outcome["validation_cases"]))
    print("F6_WITNESS_SHA256="+hashlib.sha256(canon(outcome)).hexdigest())
    print("F6_UNSEEN_FIRST_USE=ZERO")

if __name__=="__main__":main()

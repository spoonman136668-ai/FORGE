"""R36/F3 frozen development-only adjudication, strictly no science admission.

Consumes both the real Y070 policy development record and independently
replayed witness. Recomputes the pre-registered development ranking from
case-level data without selecting a sealed original or mutating a controller.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from run_wingless_development import audit_frozen
from ygg_methods import METHODS
from run_ygg_policy_development import TRAIN,VALIDATION,PAIRS

CONTROL="CONTROL"
ARMS=(CONTROL,)+METHODS

def require(ok,reason):
    if not ok:raise ValueError("F3_DEV_ADMISSION_"+reason)

def adjudicate(data,witness):
    frozen=audit_frozen()
    req=frozen["yggdrasil"]
    require(data.get("schema")=="forge.f3.yggdrasil.policy-development.v1","SCHEMA")
    require(data.get("status")=="DEVELOPMENT_SCORED_FIDELITY_REVIEW_REQUIRED","STATUS")
    require(data.get("source_commit")==req["method_source_commit"],"SOURCE")
    require(data.get("training_seeds")==list(TRAIN) and data.get("validation_seeds")==list(VALIDATION),"COHORT")
    require(not set(TRAIN)&set(VALIDATION),"COHORT_OVERLAP")
    require(not set(TRAIN+VALIDATION)&set(req["reserved_sealed_heldout_seeds"]),"SEALED_OVERLAP")
    require(data.get("scientific_winners_selected")==0 and data.get("sealed_first_uses_consumed")==0,"NO_AUTHORITY")
    require(set(data.get("rankings",{}))==set(METHODS),"METHOD_IDS")
    require(witness.get("schema")=="forge.f3.yggdrasil.independent-policy-development-witness.v1","WITNESS_SCHEMA")
    require(witness.get("status")=="ALL_FOUR_DEVELOPMENT_SCORES_REPLAYED_SCIENCE_NOT_ADMITTED","WITNESS_STATUS")
    require(witness.get("records_replayed")==960 and witness.get("scientific_winners_selected")==0 and
            witness.get("sealed_first_uses_consumed")==0,"WITNESS_AUTHORITY")
    changes=witness.get("actual_sensor_intervention_trials",{})
    require(set(changes)==set(METHODS) and all(changes[k]==192 for k in METHODS),"INSTRUMENTATION")
    records=data.get("records")
    require(isinstance(records,list) and len(records)==960,"CASE_COUNT")
    count=defaultdict(int)
    metrics=defaultdict(lambda:{"pre":0,"post":0,"detections":0})
    per_pair=defaultdict(lambda:{"pre":0,"post":0})
    unique=set()
    baseline=[[0,1],[0,1],[0,1],[2,4],[2,4]]
    for row in records:
        method=row.get("candidate")
        pair=tuple(row.get("pair",[]))
        regime=row.get("regime")
        seed=row.get("seed")
        require(method in ARMS and pair in PAIRS and regime in ("onset1","steady") and
                seed in VALIDATION and row.get("policy") in ("matched_sham","full","quorum2"),"CASE_IDENTITY")
        case=(method,pair,regime,tuple(row.get("family",[])),seed,row["policy"])
        require(case not in unique,"DUPLICATE_CASE")
        unique.add(case)
        require(row.get("reads")==10 and row["pre_mismatch"]>=0 and row["post_mismatch"]>=0,"BUDGET_SCORE")
        trace=row.get("public_addresses")
        require(isinstance(trace,list) and len(trace)==5 and all(len(x)==2 for x in trace),"TRACE")
        if method==CONTROL:require(trace==baseline,"CONTROL_TRACE")
        else:require(trace!=baseline,"INTERVENTION_ABSENT")
        count[method]+=1
        metrics[method]["pre"]+=row["pre_mismatch"]
        metrics[method]["post"]+=row["post_mismatch"]
        metrics[method]["detections"]+=row["first_detection"] is not None
        piece=per_pair[(method,pair,regime)]
        piece["pre"]+=row["pre_mismatch"]
        piece["post"]+=row["post_mismatch"]
    require(set(count)==set(ARMS) and all(count[m]==192 for m in ARMS),"COUNTS")
    for method in ARMS:
        attested=witness["aggregates"].get(method)
        require(attested=={"pre":metrics[method]["pre"],"post":metrics[method]["post"],"trials":192},"SCORE_WITNESS")
        for pair in PAIRS:
            require(per_pair[(method,pair,"steady")]=={"pre":0,"post":0},"STEADY_HARM")
    def selection_score(method):
        return (sum(per_pair[(method,pair,"onset1")]["pre"] for pair in PAIRS),
                sum(per_pair[(method,pair,"onset1")]["post"] for pair in PAIRS),
                method)
    ranked=sorted(METHODS,key=selection_score)
    per_method={}
    for key in ARMS:
        totals=metrics[key]
        per_method[key]={"pre":totals["pre"],"post":totals["post"],
                         "total":totals["pre"]+totals["post"],
                         "detections":totals["detections"],
                         "onset_by_pair":{f"{pair[0]}_{pair[1]}":per_pair[(key,pair,"onset1")] for pair in PAIRS}}
    control=per_method[CONTROL]
    gain={key:{"improved_pre_on_both_pairs":all(per_pair[(key,p,"onset1")]["pre"]<
        per_pair[(CONTROL,p,"onset1")]["pre"] for p in PAIRS),
        "pre_mismatch_reduction":control["pre"]-per_method[key]["pre"]}
        for key in METHODS}
    return {"schema":"forge.r36-f3.independent-dev-only-closeout.v1",
            "status":"DEVELOPMENT_REVIEW_PASS_SCIENCE_METHOD_FIDELITY_PENDING",
            "frozen_source":req["method_source_commit"],"record_count":len(records),
            "rank_order_development_only":ranked,
            "provisional_leader_development_only":ranked[0],
            "metrics":per_method,"candidate_gain":gain,
            "first_use_consumed":0,"sealed_original_executed":False,
            "scientific_winner_selected":False,"scientific_admission":False,
            "promotion_authorized":False,"independent_full_method_fidelity_required":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True)
    p.add_argument("--witness",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args()
    record=Path(x.record).read_bytes()
    witness=Path(x.witness).read_bytes()
    result=adjudicate(json.loads(record),json.loads(witness))
    result["record_sha256"]=hashlib.sha256(record).hexdigest()
    result["witness_sha256"]=hashlib.sha256(witness).hexdigest()
    encoded=(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(x.out).open("xb") as f:f.write(encoded)
    print("F3_DEVELOPMENT_NEGATIVE_AND_GAIN_CLASSIFICATION=PASS")
    print("F3_PROVISIONAL_DEV_LEADER="+result["provisional_leader_development_only"])
    print("F3_SCIENCE_PROMOTION=BLOCKED_FIDELITY_PENDING")
    print("F3_REVIEW_SHA256="+hashlib.sha256(encoded).hexdigest())
if __name__=="__main__":main()

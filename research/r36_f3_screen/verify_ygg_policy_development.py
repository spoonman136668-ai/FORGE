"""Independent F3 development policy-score replay against frozen Y070.

Recomputes observed scores using the pinned simulator and validates each
archived validation case. Training rank identity is checked independently
against the public-only development records.
"""
import argparse,json
from pathlib import Path
from run_yggdrasil_development import DEV,PAIRS,ARM,load_pinned,validate_portfolio
from run_ygg_policy_development import TRAIN,VALIDATION,train_public
from ygg_methods import METHODS
from ygg_public_instrument import install_public_policy

def require(ok,reason):
    if not ok:raise ValueError("F3_POLICY_WITNESS_"+reason)

def verify(record,root):
    validate_portfolio()
    require(record.get("schema")=="forge.f3.yggdrasil.policy-development.v1","SCHEMA")
    require(record.get("status")=="DEVELOPMENT_SCORED_FIDELITY_REVIEW_REQUIRED","STATUS")
    require(record.get("training_seeds")==list(TRAIN) and record.get("validation_seeds")==list(VALIDATION),"FOLDS")
    require(not(set(TRAIN)&set(VALIDATION)) and set(TRAIN+VALIDATION)==set(DEV),"OVERLAP")
    require(record.get("scientific_winners_selected")==0 and record.get("sealed_first_uses_consumed")==0,"AUTHORITY")
    z=load_pinned(root);m=z.m
    expected={k:list(v) for k,v in train_public(z).items()}
    require(record.get("rankings")==expected,"RANKING_REPRODUCTION")
    data=record.get("records")
    require(isinstance(data,list) and len(data)==960,"CASE_COUNT")
    index=0
    aggregates={key:{"pre":0,"post":0,"trials":0} for key in ("CONTROL",)+METHODS}
    try:
        for pair in PAIRS:
            for regime,onset in (("steady",None),("onset1",1)):
                m.y58.install_transposition(onset,pair,{"anchor_pair_checks":0})
                for family in z.FAMILIES:
                    for seed in VALIDATION:
                        for policy in z.POLICIES:
                            reference=m.y50.evaluate(seed,policy,"canonical","continue",family)
                            for method in ("CONTROL",)+METHODS:
                                row=data[index];index+=1
                                require(row["candidate"]==method and row["pair"]==list(pair) and row["regime"]==regime
                                        and row["seed"]==seed and row["family"]==list(family) and row["policy"]==policy,"ROW_IDENTITY")
                                audit=[]
                                if method=="CONTROL":
                                    candidate=m.candidate(seed,family,policy,ARM)
                                    trace=[[0,1],[0,1],[0,1],[2,4],[2,4]]
                                else:
                                    with install_public_policy(z,method,tuple(expected[method]),audit=audit):
                                        candidate=m.candidate(seed,family,policy,ARM)
                                    require(len(audit)==1,"SENSOR_HOOK_NOT_CALLED")
                                    trace=audit[0]
                                require(row.get("public_addresses")==trace,"SENSOR_TRACE_TAMPER")
                                require(candidate["public_scalar_reads"]==10 and row["reads"]==10,"READS")
                                first=None
                                for item in candidate["rows"]:
                                    if item["public_detected_swap_first_episode"] is not None:
                                        first=item["public_detected_swap_first_episode"]
                                require(first==row["first_detection"],"DETECTION")
                                pre=post=0
                                require(len(reference["rows"])==len(candidate["rows"]),"LENGTH")
                                for a,b in zip(reference["rows"],candidate["rows"]):
                                    require(a["episode"]==b["episode"],"EPISODE")
                                    error=int(any(a["physical_assignment"][k]!=b["physical_assignment_evaluator_only"][k]
                                                  for k in a["physical_assignment"]))
                                    if first is None or b["episode"]<first:pre+=error
                                    else:post+=error
                                    require(b["illegal_physical_assignments"]==0 and b["candidate_retained_cache_occupancy"]<=9,"CAPACITY")
                                require((pre,post)==(row["pre_mismatch"],row["post_mismatch"]),"SCORE")
                                aggregates[method]["pre"]+=pre
                                aggregates[method]["post"]+=post
                                aggregates[method]["trials"]+=1
                m.y49.restore_environment()
    finally:m.y49.restore_environment()
    baseline=[[0,1],[0,1],[0,1],[2,4],[2,4]]
    affected={}
    for method in METHODS:
        observed=[row["public_addresses"] for row in data if row["candidate"]==method]
        changed=sum(trace!=baseline for trace in observed)
        require(len(observed)==192 and changed>0,"NO_OBSERVED_INTERVENTION")
        affected[method]=changed
    return {"schema":"forge.f3.yggdrasil.independent-policy-development-witness.v1",
            "status":"ALL_FOUR_DEVELOPMENT_SCORES_REPLAYED_SCIENCE_NOT_ADMITTED",
            "records_replayed":index,"aggregates":aggregates,
            "actual_sensor_intervention_trials":affected,"scientific_winners_selected":0,
            "sealed_first_uses_consumed":0}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True);p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True);a=p.parse_args()
    result=verify(json.loads(Path(a.record).read_bytes()),a.yggdrasil_root)
    with Path(a.out).open("xb") as f:f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("F3_ALL_FOUR_REAL_DEV_SCORES_INDEPENDENTLY_REPLAYED=PASS")
    print("F3_REPLAYED_TRIALS="+str(result["records_replayed"]))

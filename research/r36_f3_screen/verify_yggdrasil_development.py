"""Independent F3 Yggdrasil development-baseline replay.

Re-executes the immutable simulator and independently reconstructs
pre/post detection mismatches for each reserved development trial.
No sealed cohorts, candidate selection, or first-use claims.
"""
import argparse
import json
from pathlib import Path
from run_yggdrasil_development import DEV, PAIRS, ARM, SOURCE_COMMIT, load_pinned, validate_portfolio

def need(condition,why):
    if not condition:raise ValueError("F3_YGG_WITNESS_"+why)

def verify(record, root):
    validate_portfolio()
    need(record.get("schema")=="forge.f3.yggdrasil.real-development-baseline.v1","SCHEMA")
    need(record.get("status")=="PINNED_BASELINE_DEVELOPMENT_ONLY_CANDIDATES_NOT_QUALIFIED","STATUS")
    need(record.get("source_commit")==SOURCE_COMMIT,"SOURCE")
    need(record.get("development_seeds")==list(DEV) and record.get("baseline_arm")==ARM,"DEVELOPMENT")
    for field in ("scientific_winners_selected","scientific_originals_executed","sealed_first_uses_consumed","model_api_calls"):
        need(record.get(field)==0, "AUTHORITY")
    y070=load_pinned(root)
    m=y070.m
    records=record.get("records",[])
    need(isinstance(records,list) and len(records)==384,"COUNT")
    counter=0
    summaries=[]
    try:
        for pair in PAIRS:
            for regime,onset in (("steady",None),("onset1",1)):
                m.y58.install_transposition(onset,pair,{"anchor_pair_checks":0})
                before=after=0
                for family in y070.FAMILIES:
                    for seed in DEV:
                        for policy in y070.POLICIES:
                            entry=records[counter]
                            counter+=1
                            need(entry["pair"]==list(pair) and entry["regime"]==regime and
                                 entry["seed"]==seed and entry["family"]==list(family) and entry["policy"]==policy,
                                 "CASE_IDENTITY")
                            truth=m.y50.evaluate(seed,policy,"canonical","continue",family)
                            cand=m.candidate(seed,family,policy,ARM)
                            need(cand["public_scalar_reads"]==10 and entry["public_reads"]==10,"READ_LIMIT")
                            first=None
                            for r in cand["rows"]:
                                if r["public_detected_swap_first_episode"] is not None:
                                    first=r["public_detected_swap_first_episode"]
                            need(first==entry["first_detection"],"DETECTION")
                            pre=post=illegal=0
                            need(len(truth["rows"])==len(cand["rows"]),"EPISODES")
                            for a,b in zip(truth["rows"],cand["rows"]):
                                need(a["episode"]==b["episode"],"EPISODE_IDENTITY")
                                mismatch=int(any(a["physical_assignment"][k]!=b["physical_assignment_evaluator_only"][k]
                                                 for k in a["physical_assignment"]))
                                if first is None or b["episode"]<first:pre+=mismatch
                                else:post+=mismatch
                                illegal+=b["illegal_physical_assignments"]
                                need(b["candidate_retained_cache_occupancy"]<=9 and
                                     len(b["physical_assignment_evaluator_only"])==7,"CAPACITY")
                            need(illegal==0 and entry["illegal_assignments"]==0,"PHYSICAL_ILLEGAL")
                            need((pre,post)==(entry["pre_mismatch"],entry["post_mismatch"]),"METRIC_TAMPER")
                            before+=pre;after+=post
                summaries.append({"pair":list(pair),"regime":regime,"replayed_pre_mismatch":before,
                                  "replayed_post_mismatch":after,"trial_count":96})
                m.y49.restore_environment()
    finally:
        m.y49.restore_environment()
    need(counter==len(records),"EXTRA_RECORD")
    return {"schema":"forge.f3.yggdrasil.independent-development-baseline-review.v1",
            "status":"PINNED_DEV_BASELINE_REPLAY_VERIFIED_NO_CANDIDATE_ADMISSION",
            "source_commit":SOURCE_COMMIT,"replayed_trials":counter,"cases":summaries,
            "scientific_winners_selected":0,"sealed_first_uses_consumed":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--record",required=True)
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args()
    result=verify(json.loads(Path(x.record).read_bytes()),x.yggdrasil_root)
    with Path(x.out).open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("F3_YGG_REAL_DEV_BASELINE_INDEPENDENT_REPLAY=PASS")
    print("F3_YGG_REPLAYED_TRIALS="+str(result["replayed_trials"]))
    print("F3_YGG_SCIENCE_FIRST_USE=ZERO")

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""MG09 fail-closed two-process authenticated public-only orientation witness."""
import argparse
import json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg09_original_orientation_retention import (
 SCHEMA,ROLES,NATIVE,BLOCKED,ABSENT,EXPOSED,DOOR,diagnostic,new_counts
)
from mg07_temporal_original_doorkey import ROLES as ORIGINAL_ROLES
SEEDS=(69301,69303,69307)
ACCEPTED=(ABSENT,EXPOSED,DOOR)

def verify(r):
    if (r.get("schema")!=SCHEMA or r.get("classification") not in ACCEPTED
        or r.get("scientific_first_use") is not False
        or r.get("FORGE_controller_changed") is not False
        or r.get("accepted_native_model_changed") is not False
        or r.get("original_Wingless_R8_or_Ygg_R10_R12_changed") is not False
        or r.get("three_new_original_source_seeds") is not True
        or r.get("real_original_episode_count")!=21
        or r.get("original_source_selected_FIT_each")!=1664
        or r.get("actual_original_live_external_actions")!=0):
        raise ValueError("MG09_NO_AUTHENTIC_SOURCE_AUTHORITY")
    e=r.get("canonical_original_source_evidence")
    if (type(e)is not dict or sha(canon(e).encode())!=r.get("canonical_original_source_sha")
        or e.get("identical_original_FIT_selected_samples_per_model")!=1664
        or e.get("external_live_actions")!=0
        or e.get("original_models_unchanged") is not True
        or e.get("source_original_public_data_only") is not True):
        raise ValueError("MG09_FALSIFIED_ORIGINAL_SOURCE_RECORD")
    records=e["source_only_new_real_original_selected_step_records"]
    audits=e["source_only_orientation_retention_per_episode"]
    summary=e["source_only_orientation_retention_per_role"]
    if type(records)is not list or len(records)!=21 or len(audits)!=21:
        raise ValueError("MG09_MISSING_SOURCE_OR_INDEPENDENT_CONTROL")
    for seed in SEEDS:
        subset=[x for x in records if x.get("evaluator_seed_only",
                                               x.get("seed_evaluator_only"))==seed]
        if len(subset)!=7 or {x["role"] for x in subset}!=set(ROLES):
            raise ValueError("MG09_UNFAIR_SOURCE_ROLE_EXPOSURE")
        if len({x.get("original_public_start_sha",x.get("original_public_start_sha256")) for x in subset})!=1:
            raise ValueError("MG09_DIFFERENT_PUBLIC_ORIGINAL_RESET")
    for original,measured in zip(records,audits):
        role=original["role"]
        sourcekind="mg07" if role in ORIGINAL_ROLES else "mg06"
        fresh=diagnostic(original,sourcekind)
        if measured!=fresh:
            raise ValueError("MG09_SOURCE_PUBLIC_CREDIT_NOT_REPRODUCIBLE")
        n=fresh["source_only_counts"]["original_selected_action_count"]
        if n<1 or n>192 or sum(fresh["source_selected_action_counts"].values())!=n:
            raise ValueError("MG09_ORIGINAL_ACTION_SEQUENCE_NOT_COMPLETE")
        if (sum(fresh["source_only_counts"][name] for name in
                ("turns_expected_public_direction","turns_wrong_public_direction"))
            !=fresh["source_only_counts"]["turn_left_selected"]+
              fresh["source_only_counts"]["turn_right_selected"]):
            raise ValueError("MG09_ORIENTATION_SOURCE_ACTIONS_NOT_ACCOUNTED")
        if fresh["source_only_counts"]["true_public_key_pickups"]!=(
            len(fresh["key_retention_completed_spans"])+
            len(fresh["key_retention_censored_spans"])):
            raise ValueError("MG09_KEY_RETENTION_CREDIT_NOT_ACCOUNTED")
    for role in ROLES:
        subset=[a for a in audits if a["role"]==role]
        if len(subset)!=3 or summary[role]["original_real_episodes"]!=3:
            raise ValueError("MG09_ROLE_SUMMARY_MISSING")
        for key in new_counts():
            if summary[role][key]!=sum(s["source_only_counts"][key] for s in subset):
                raise ValueError("MG09_ORIGINAL_SOURCE_ROLE_RECOUNT_FAIL")
    both=all(summary[role]["real_door_state_changes"]>=1 for role in NATIVE)
    conjunction=any(summary[role]["key_front_door_frames"]>=1 for role in NATIVE)
    expected=DOOR if both else EXPOSED if conjunction else ABSENT
    if r["classification"]!=expected:
        raise ValueError("MG09_PROSPECTIVE_DECISION_CHANGED_AFTER_DATA")
    return e

def main():
    a=argparse.ArgumentParser()
    for name in ("first","second","output"):
        a.add_argument("--"+name,type=Path,required=True)
    args=a.parse_args()
    first=json.loads(args.first.read_text(encoding="utf-8"))
    second=json.loads(args.second.read_text(encoding="utf-8"))
    a=verify(first);b=verify(second)
    if (a!=b or first["classification"]!=second["classification"] or
        first["canonical_original_source_sha"]!=second["canonical_original_source_sha"]):
        raise ValueError("MG09_TWO_INDEPENDENT_ORIGINAL_WORLD_PROCESSES_DIVERGED")
    out={"schema":"itd02.mg09.original-public-orientation-two-independent-processes.v1",
        "classification":first["classification"],"original_complete_processes":2,
        "canonical_public_selected_source_sha256":first["canonical_original_source_sha"],
        "per_role_public_egocentric_and_retention":a["source_only_orientation_retention_per_role"],
        "external_original_actions":0,"scientific_first_use":False}
    args.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG09_TWO_PROCESS",out["classification"])
    print("MG09_VERIFIED_SHA",out["canonical_public_selected_source_sha256"])
    print("MG09_VERIFIED_ROLES",json.dumps(out["per_role_public_egocentric_and_retention"],sort_keys=True))
if __name__=="__main__":main()

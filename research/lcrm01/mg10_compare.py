#!/usr/bin/env python3
"""MG10 two independent complete original-world/public-source process checks."""
import argparse
import json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg10_stage_free_original_doorkey import (
 SCHEMA,NEGATIVE,POSITIVE,ROLES
)
SEEDS=(70301,70303,70307)
VALID=(NEGATIVE,POSITIVE)

def verify(x):
    if (x.get("schema")!=SCHEMA or x.get("classification") not in VALID
        or x.get("scientific_first_use") is not False
        or x.get("accepted_native_model_changed") is not False
        or x.get("FORGE_controller_changed") is not False
        or x.get("original_Wingless_R8_or_Ygg_R10_R12_changed") is not False
        or x.get("same_original_FIT_selected_per_actor")!=1664
        or x.get("original_source_episodes")!=15
        or x.get("external_selected_original_live_actions")!=0):
        raise ValueError("MG10_UNVERIFIED_ORIGINAL_SOURCE_AUTHORITY")
    e=x.get("canonical_original_public_evidence")
    if (type(e)is not dict
        or sha(canon(e).encode())!=x.get("canonical_original_selected_public_sha")
        or e.get("same_original_selected_FIT_for_each_learned_actor")!=1664
        or e.get("all_eligible_actors_use_raw_original_public_only") is not True
        or e.get("no_manual_stage_or_hidden_answer") is not True
        or e.get("external_live_actions")!=0):
        raise ValueError("MG10_ORIGINAL_SOURCE_CANONICAL_OR_INFORMATION_FAIRNESS")
    records=e.get("all_source_selected_public_events")
    if type(records)is not list or len(records)!=15:
        raise ValueError("MG10_INCOMPLETE_ORIGINAL_SELECTED_FEEDBACK")
    for seed in SEEDS:
        batch=[r for r in records if r.get("seed_evaluator_only")==seed]
        if len(batch)!=5 or {r["role"] for r in batch}!=set(ROLES):
            raise ValueError("MG10_ORIGINAL_SELECTED_SOURCE_ROLE_INCOMPLETE")
        if len({r["original_public_start_sha"] for r in batch})!=1:
            raise ValueError("MG10_UNEQUAL_ORIGINAL_SOURCE_RESET")
        for r in batch:
            steps=r["true_original_public_selected_events"]
            if (not 1<=len(steps)<=192 or r["true_original_live_steps"]!=len(steps)
                or r["external_actions"]!=0):
                raise ValueError("MG10_NONSOURCE_ACTION_OR_HIDDEN_ASSISTANCE")
            for i,event in enumerate(steps):
                if (event["ordinal"]!=i+1 or
                    type(event["selected_real_action"])is not int
                    or event["selected_real_action"] not in range(7)
                    or type(event["original_reward"])is not float
                    or event["external_selected_action_count"]!=0
                    or type(event["terminal"])is not bool
                    or type(event["truncated"])is not bool
                    or set(event["public_before"])!={"image","direction","mission"}
                    or set(event["public_after"])!={"image","direction","mission"}
                    or event["original_public_before_sha"]!=sha(canon(event["public_before"]).encode())
                    or event["original_public_after_sha"]!=sha(canon(event["public_after"]).encode())):
                    raise ValueError("MG10_FAKE_REAL_PUBLIC_SELECTED_ENV_EVENT")
    summary=e["original_source_per_role_metrics"]
    for role in ROLES:
        items=[y for y in records if y["role"]==role]
        s=summary[role]
        if (s["episodes"]!=3 or s["external_actions"]!=0
            or s["true_original_selected_actions"]!=sum(z["true_original_live_steps"] for z in items)
            or s["real_original_goal_rewards"]!=sum(z["true_original_goal_rewards"] for z in items)
            or s["real_door_state_changes"]!=sum(z["real_door_state_changes"] for z in items)
            or s["key_and_front_door_frames"]!=sum(z["key_front_door_frames"] for z in items)):
            raise ValueError("MG10_CONVENTIONAL_AND_NATIVE_SOURCE_RESULT_DRIFT")
    both=all(summary[role]["real_original_goal_rewards"]>=1 for role in
           ("wingless_go_dk11","yggdrasil_r15"))
    if x["classification"]!=(POSITIVE if both else NEGATIVE):
        raise ValueError("MG10_PREREGISTERED_CLASSIFICATION_CHANGED")
    return e

def main():
    p=argparse.ArgumentParser()
    for key in ("first","second","output"):
        p.add_argument("--"+key,type=Path,required=True)
    opts=p.parse_args()
    a=json.loads(opts.first.read_text(encoding="utf-8"))
    b=json.loads(opts.second.read_text(encoding="utf-8"))
    ea=verify(a);eb=verify(b)
    if (ea!=eb or a["classification"]!=b["classification"]
        or a["canonical_original_selected_public_sha"]!=b["canonical_original_selected_public_sha"]):
        raise ValueError("MG10_TWO_AUTHENTIC_SOURCE_PROCESSES_NOT_IDENTICAL")
    out={"schema":"itd02.mg10.two-independent-original-door-key-processes.v1",
        "classification":a["classification"],"original_process_count":2,
        "canonical_original_selected_public_sha":a["canonical_original_selected_public_sha"],
        "per_role_original_source_results":ea["original_source_per_role_metrics"],
        "real_live_external_actions":0,"scientific_first_use":False}
    opts.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG10_TWO_PROCESS",out["classification"])
    print("MG10_VERIFIED_SOURCE_SHA",out["canonical_original_selected_public_sha"])
    print("MG10_VERIFIED_RESULTS",json.dumps(out["per_role_original_source_results"],sort_keys=True))
if __name__=="__main__":main()

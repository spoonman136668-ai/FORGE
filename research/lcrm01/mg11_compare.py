#!/usr/bin/env python3
"""Strict independent original Farama MG11 public action/feedback comparator."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg11_authentic_selected_novelty import SCHEMA,NEGATIVE,POSITIVE,ROLES,NATIVE
SEEDS=(71301,71303,71307)
def verify(r):
    if (r.get("schema")!=SCHEMA or r.get("classification") not in (NEGATIVE,POSITIVE)
        or r.get("scientific_first_use") is not False or
        r.get("native_model_promoted") is not False or
        r.get("FORGE_controller_changed") is not False or
        r.get("accepted_original_source_changed") is not False or
        r.get("source_FIT_original_count")!=1664 or
        r.get("actual_source_episodes")!=21 or
        r.get("external_live_actions")!=0):
        raise ValueError("MG11_NOT_ORIGINAL_PROSPECTIVE_SOURCE_AUTHORITY")
    e=r.get("original_public_source_evidence")
    if (type(e)is not dict or sha(canon(e).encode())!=r.get("canonical_original_selected_sha")
        or e.get("no_manual_stage_or_external_route") is not True
        or e.get("external_actions")!=0):
        raise ValueError("MG11_TAMPERED_SELECTED_PUBLIC_CANONICAL_SOURCE")
    records=e.get("original_public_selected_records")
    if type(records)is not list or len(records)!=21:
        raise ValueError("MG11_NOT_SEVEN_INDEPENDENT_SOURCE_ROLES")
    for seed in SEEDS:
        group=[x for x in records if x["evaluator_seed_only"]==seed]
        if len(group)!=7 or {r["role"] for r in group}!=set(ROLES) or
            len({r["original_public_start_sha"] for r in group})!=1:
            raise ValueError("MG11_FAIR_SOURCE_RESET_MISSING")
        for arm in group:
            events=arm["all_original_public_selected_events"]
            if (not 1<=len(events)<=192 or arm["real_original_source_actions"]!=len(events)
                or arm["external_actions"]!=0
                or arm["distinct_original_selected_actions"]!=len(set(x["action"] for x in events))):
                raise ValueError("MG11_ACTOR_NOT_ACTUALLY_SELECTED")
            for i,event in enumerate(events):
                if (event["index"]!=i+1 or
                    type(event["action"])is not int or
                    event["action"] not in range(7) or
                    type(event["original_reward"])is not float or
                    type(event["terminated"])is not bool or
                    type(event["truncated"])is not bool or
                    event["external_action_count"]!=0 or
                    set(event["public_before"])!={"image","direction","mission"} or
                    set(event["public_after"])!={"image","direction","mission"} or
                    event["before_sha"]!=sha(canon(event["public_before"]).encode()) or
                    event["after_sha"]!=sha(canon(event["public_after"]).encode())):
                    raise ValueError("MG11_FAKE_GENUINE_FARAMA_PUBLIC_ACTION")
    totals=e["per_role_original_results"]
    for role in ROLES:
        rows=[r for r in records if r["role"]==role]
        if (len(rows)!=3 or totals[role]["episodes"]!=3 or
            totals[role]["external_actions"]!=0 or
            totals[role]["true_original_selected_actions"]!=sum(r["real_original_source_actions"] for r in rows) or
            totals[role]["original_goal_rewards"]!=sum(r["original_goal_rewards"] for r in rows) or
            totals[role]["real_door_changes"]!=sum(r["actual_original_door_changes"] for r in rows)):
            raise ValueError("MG11_SOURCE_RECOUNT_DIVERGED")
    positive=all(totals[n]["original_goal_rewards"]>=1
        and totals[n]["min_distinct_actions_per_episode"]>=3 for n in NATIVE)
    if r["classification"]!=(POSITIVE if positive else NEGATIVE):
        raise ValueError("MG11_FROZEN_SUCCESS_RULE_CHANGED")
    return e
def main():
    p=argparse.ArgumentParser()
    for n in ("first","second","output"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    x=json.loads(a.first.read_text());y=json.loads(a.second.read_text())
    e=verify(x);z=verify(y)
    if (e!=z or x["classification"]!=y["classification"]
        or x["canonical_original_selected_sha"]!=y["canonical_original_selected_sha"]):
        raise ValueError("MG11_INDEPENDENT_REAL_SOURCE_PROCESSES_DIFFER")
    report={"schema":"itd02.mg11.real-original-doorkey-two-independent-processes.v1",
        "classification":x["classification"],"original_processes":2,
        "canonical_sha":x["canonical_original_selected_sha"],
        "original_selected_results":e["per_role_original_results"],
        "actual_external_actions":0,"scientific_first_use":False}
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("MG11_TWO_PROCESS",report["classification"])
    print("MG11_VERIFIED_SOURCE_SHA",report["canonical_sha"])
    print("MG11_VERIFIED_RESULTS",json.dumps(report["original_selected_results"],sort_keys=True))
if __name__=="__main__":main()

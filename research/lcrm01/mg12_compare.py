#!/usr/bin/env python3
"""Independent original public-source MG12 two-process verifier."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg12_postdoor_original import SCHEMA,NEGATIVE,POSITIVE,ROLES,NATIVE,examine_episode
SEEDS=(72301,72303,72307)

def verify(r):
    if (r.get("schema")!=SCHEMA or r.get("classification") not in (NEGATIVE,POSITIVE)
        or r.get("scientific_first_use") is not False
        or r.get("accepted_native_changed") is not False
        or r.get("FORGE_controller_changed") is not False
        or r.get("source_original_FIT_count")!=1664
        or r.get("original_source_episodes")!=24
        or r.get("external_original_actions")!=0):
        raise ValueError("MG12_UNTRUSTED_SOURCE_AUTHORITY")
    e=r.get("original_source_evidence")
    if (type(e)is not dict or sha(canon(e).encode())!=r.get("canonical_original_public_source_sha")
        or e.get("external_original_selected_actions")!=0
        or e.get("no_oracle_or_global_pose") is not True
        or e.get("no_native_policy_change_since_MG11") is not True):
        raise ValueError("MG12_ORIGINAL_SOURCE_CANONICAL_FAIL")
    existing=e["unchanged_native_and_original_seven_arm_evidence"]["original_public_selected_records"]
    new=e["eighth_independent_original_selected_control"]
    rows=existing+new
    audits=e["postdoor_public_diagnostic_per_episode"]
    if len(existing)!=21 or len(new)!=3 or len(rows)!=24 or len(audits)!=24:
        raise ValueError("MG12_ORIGINAL_SOURCE_ARMS_MISSING")
    for seed in SEEDS:
        group=[r for r in rows if r["evaluator_seed_only"]==seed]
        if (len(group)!=8 or {r["role"] for r in group}!=set(ROLES)
            or len({r["original_public_start_sha"] for r in group})!=1):
            raise ValueError("MG12_SOURCE_ROLE_OR_PUBLIC_START_UNFAIR")
        for role in group:
            events=role["all_original_public_selected_events"]
            if not 1<=len(events)<=192 or role["real_original_source_actions"]!=len(events):
                raise ValueError("MG12_ORIGINAL_ACTIONS_MISSING")
            for index,event in enumerate(events):
                if (event["index"]!=index+1 or
                    type(event["action"])is not int or event["action"] not in range(7)
                    or event["external_action_count"]!=0
                    or type(event["original_reward"])is not float
                    or event["before_sha"]!=sha(canon(event["public_before"]).encode())
                    or event["after_sha"]!=sha(canon(event["public_after"]).encode())):
                    raise ValueError("MG12_ORIGINAL_SELECTED_SOURCE_EVENT_FALSE")
    if any(examine_episode(source)!=result for source,result in zip(rows,audits)):
        raise ValueError("MG12_POSTDOOR_DIAGNOSTIC_NOT_REAL_SOURCE")
    summary=e["postdoor_public_diagnostic_per_role"]
    for role in ROLES:
        group=[x for x in audits if x["role"]==role]
        if len(group)!=3:raise ValueError("MG12_INCOMPLETE_ROLE")
        if (summary[role]["original_goal_rewards"]!=sum(x["original_true_goal_rewards"] for x in group)
            or summary[role]["public_door_openings"]!=sum(x["source_public_front_door_openings"] for x in group)
            or summary[role]["original_goal_rewards_after_open"]!=sum(x["original_goals_after_any_own_door_opening"] for x in group)):
            raise ValueError("MG12_SOURCE_TALLY_FALSE")
    win=all(summary[n]["original_goal_rewards_after_open"]>=1 for n in NATIVE)
    if r["classification"]!=(POSITIVE if win else NEGATIVE):
        raise ValueError("MG12_PREDECLARED_CLASSIFICATION_FALSE")
    return e

def main():
    p=argparse.ArgumentParser()
    for k in ("first","second","output"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    x=json.loads(a.first.read_text());y=json.loads(a.second.read_text())
    first=verify(x);second=verify(y)
    if (first!=second or x["classification"]!=y["classification"]
        or x["canonical_original_public_source_sha"]!=y["canonical_original_public_source_sha"]):
        raise ValueError("MG12_TWO_INDEPENDENT_PROCESSES_DIVERGED")
    out={"schema":"itd02.mg12.real-original-two-processes.v1",
         "classification":x["classification"],"verified_original_processes":2,
         "canonical_original_sha":x["canonical_original_public_source_sha"],
         "results":first["postdoor_public_diagnostic_per_role"],
         "scientific_first_use":False}
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG12_TWO_PROCESS",out["classification"])
    print("MG12_VERIFIED_SHA",out["canonical_original_sha"])
    print("MG12_VERIFIED_RESULTS",json.dumps(out["results"],sort_keys=True))
if __name__=="__main__":main()

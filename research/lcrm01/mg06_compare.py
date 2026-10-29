#!/usr/bin/env python3
"""MG06 two separate original process native selected-world custody."""
import argparse
import json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg06_original_doorkey_exploration import SCHEMA,NEGATIVE,POSITIVE,ROLES
SEEDS=(66301,66303,66307)
def validate(r):
    if (r.get("schema")!=SCHEMA or r.get("classification") not in (NEGATIVE,POSITIVE)
        or r.get("scientific_first_use") is not False
        or r.get("accepted_model_promoted") is not False
        or r.get("FORGE_controller_modified") is not False
        or r.get("original_Wingless_R8_modified") is not False
        or r.get("original_Ygg_R12_modified") is not False
        or r.get("matched_original_source_FIT_per_role")!=1664
        or r.get("zero_external_actions") is not True
        or r.get("role_count")!=5 or r.get("real_episode_count")!=15):
        raise ValueError("MG06_ORIGINAL_SOURCE_ACCURACY_BLOCKED")
    e=r.get("original_source_canonical_evidence")
    if type(e)is not dict or sha(canon(e).encode())!=r.get("canonical_original_selected_trace_sha256"):
        raise ValueError("MG06_CANONICAL_ORIGINAL_SELECTED_FEEDBACK_TAMPERED")
    if (e.get("source_fit_per_role")!=1664 or
        e.get("no_external_collector_used_during_any_live_episode") is not True or
        e.get("no_learning_shadow_original_source_unchanged") is not True or
        e.get("old_wingless_R8_unchanged") is not True):
        raise ValueError("MG06_UNTRUSTED_SOURCE_OR_EXTERNAL_NAVIGATION")
    records=e.get("original_real_selected_traces")
    if type(records)is not list or len(records)!=15:
        raise ValueError("MG06_MISSING_AUTHENTIC_REAL_EXPOSURES")
    for seed in SEEDS:
        group=[x for x in records if x.get("seed_evaluator_only")==seed]
        if len(group)!=5 or {x["role"] for x in group}!=set(ROLES):
            raise ValueError("MG06_NOT_ALL_INDEPENDENT_ORIGINAL_ROLES")
        if len({x["original_public_start_sha"] for x in group})!=1:
            raise ValueError("MG06_INEQUIVALENT_SOURCE_RESET")
        for x in group:
            s=x["real_selected_source_feedback"]
            if (not s or x["external_actions"]!=0
                or len(s)!=x["real_selected_action_count"] or len(s)>192):
                raise ValueError("MG06_SILENT_EXTERNAL_ASSISTANCE_OR_EMPTY_ACTOR")
            for i,event in enumerate(s):
                if (event["ordinal"]!=i+1 or
                    type(event["selected_action"]) is not int or
                    event["selected_action"] not in range(7) or
                    type(event["original_reward"]) is not float or
                    type(event["terminated"]) is not bool or
                    type(event["truncated"]) is not bool or
                    event["external_assistance_count"]!=0 or
                    set(event["real_source_before"])!={"image","direction","mission"} or
                    set(event["real_source_after"])!={"image","direction","mission"}):
                    raise ValueError("MG06_FALSE_AUTHENTIC_PUBLIC_SELECTED_EVENT")
    summary=e["per_actor_original_environment_summary"]
    for role in ROLES:
        rows=[x for x in records if x["role"]==role]
        v=summary[role]
        if (v["original_episodes"]!=3 or v["external_actions"]!=0
            or v["original_actions_selected_by_actor"]!=sum(x["real_selected_action_count"] for x in rows)
            or v["real_goal_rewards"]!=sum(x["original_goal_rewards"] for x in rows)):
            raise ValueError("MG06_CONVENTIONAL_OR_NATIVE_ACCOUNTING_NOT_REPRODUCED")
    positive=all(summary[x]["real_goal_rewards"]>=1 and
                 summary[x]["episodes_executing_at_least_64_native_actions_or_terminal"]==3
                 for x in ("wingless_go_dk9","yggdrasil_r13"))
    if r["classification"]!=(POSITIVE if positive else NEGATIVE):
        raise ValueError("MG06_PREREG_CLASSIFICATION_VIOLATED")
    return e

def main():
    a=argparse.ArgumentParser()
    for arg in ("first","second","output"):
        a.add_argument("--"+arg,type=Path,required=True)
    p=a.parse_args()
    x=json.loads(p.first.read_text());y=json.loads(p.second.read_text())
    fx=validate(x);fy=validate(y)
    if fx!=fy or x["classification"]!=y["classification"] or x["canonical_original_selected_trace_sha256"]!=y["canonical_original_selected_trace_sha256"]:
        raise ValueError("MG06_TWO_INDEPENDENT_PROCESSES_DIFFER")
    result={"schema":"itd02.mg06.real-original-world-two-process-reproduction.v1",
      "classification":x["classification"],"independent_complete_source_processes":2,
      "canonical_original_trace_sha256":x["canonical_original_selected_trace_sha256"],
      "per_role_original_source_metrics":fx["per_actor_original_environment_summary"],
      "native_only_no_collector":True,"scientific_first_use":False}
    p.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("MG06_TWO_PROCESS",result["classification"])
    print("MG06_VERIFIED_CANONICAL_SHA",result["canonical_original_trace_sha256"])
    print("MG06_VERIFIED_ACTOR_RESULTS",json.dumps(result["per_role_original_source_metrics"],sort_keys=True))
if __name__=="__main__":main()

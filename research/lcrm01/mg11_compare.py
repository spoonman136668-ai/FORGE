#!/usr/bin/env python3
"""MG11 exact original source two-process custody and attribution verifier."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg11_original_motion import SCHEMA,ROLES,POS,NEG

def check(condition,msg):
    if not condition:raise ValueError("MG11_SOURCE_COMPARISON_"+msg)

def verify(r):
    check(r.get("schema")==SCHEMA and r.get("classification") in (POS,NEG),"CLASSIFICATION")
    check(r.get("scientific_first_use") is False and
          r.get("accepted_native_model_promoted") is False and
          r.get("FORGE_or_CKB_controller_modified") is False and
          r.get("external_live_actions")==0 and
          r.get("original_episode_count")==12 and
          r.get("same_original_selected_FIT_samples")==1664,"AUTHORITY")
    e=r["canonical_original_source_evidence"]
    check(sha(canon(e).encode())==r["canonical_original_source_sha256"],"EVIDENCE_SHA")
    check(e["original_training_stream_sha256"]=="9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24"
          and e["no_manually_derived_stage_input_to_any_policy"] is True and
          e["no_original_live_external_actions"] is True,"EXACT_SOURCE_AND_RAW_ONLY")
    rows=e["native_and_conventional_public_source_records"]
    check(len(rows)==12 and
          {(r["role"],r["seed_evaluator_only"]) for r in rows}==
          {(role,seed) for role in ROLES for seed in (71301,71303,71307)},"MATRIX")
    summary=e["per_role_original_source_metrics"]
    for seed in (71301,71303,71307):
        subset=[row for row in rows if row["seed_evaluator_only"]==seed]
        check(len({row["original_start_public_sha256"] for row in subset})==1,"EQUAL_SOURCE_RESETS")
        for row in subset:
            events=row["real_source_events"]
            check(0<len(events)<=192 and
                  len(events)==row["original_live_selected_steps"] and
                  row["external_actions"]==0,"ORIGINAL_SELECTED_COUNT")
            for i,event in enumerate(events):
                b,a=event["public_before"],event["public_after"]
                check(event["step"]==i+1 and type(event["actual_original_source_action"]) is int
                      and event["actual_original_source_action"] in range(7)
                      and set(b)=={"image","direction","mission"}
                      and set(a)=={"image","direction","mission"}
                      and event["original_public_before_sha256"]==sha(canon(b).encode())
                      and event["original_public_after_sha256"]==sha(canon(a).encode())
                      and type(event["source_reward"]) is float
                      and type(event["terminated"]) is bool
                      and type(event["truncated"]) is bool
                      and event["external_live_actions"]==0,"UNAUTHENTICATED_SOURCE_ACTION")
            check(all(not e["terminated"] and not e["truncated"] for e in events[:-1]),
                  "ACTIONS_AFTER_TERMINAL")
    for role in ROLES:
        rs=[row for row in rows if row["role"]==role]
        check(summary[role]["episodes"]==3 and summary[role]["external_actions"]==0,
              "AGGREGATE_CUSTODY")
        for name in ("original_live_selected_steps","source_key_pickups",
                     "source_key_drops","forward_while_held","front_door_while_held",
                     "source_visible_door_openings","source_goal_rewards","distinct_public_views",
                     "distinct_action_ids","same_heading_scene_change_count",
                     "heading_change_count"):
            check(summary[role][name]==sum(row[name] for row in rs),"AGGREGATE_"+name)
    success=all(summary[role]["source_goal_rewards"]>=1 for role in ROLES[:2])
    check(r["classification"]==(POS if success else NEG),"FROZEN_GOAL_RULE")
    return e

def main():
    p=argparse.ArgumentParser()
    for name in ("first","second","output"):p.add_argument("--"+name,required=True,type=Path)
    args=p.parse_args()
    r1=json.loads(args.first.read_text())
    r2=json.loads(args.second.read_text())
    a=verify(r1);b=verify(r2)
    check(a==b and r1["classification"]==r2["classification"] and
          r1["canonical_original_source_sha256"]==r2["canonical_original_source_sha256"],
          "INDEPENDENT_PROCESSES_NOT_IDENTICAL")
    d={"schema":"itd02.mg11.two-process-selected-original-evidence.v1",
       "classification":r1["classification"],"canonical_original_source_sha256":r1["canonical_original_source_sha256"],
       "two_independent_fresh_original_source_processes":True,
       "selected_source_actions_not_external":True,
       "equal_policy_public_observation":True,
       "matched_empirical_conventional_and_random_controls":True,
       "original_source_metrics":a["per_role_original_source_metrics"],"scientific_first_use":False}
    args.output.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print("MG11_TWO_PROCESS",d["classification"])
    print("MG11_VERIFIED_SOURCE_SHA",d["canonical_original_source_sha256"])
    print("MG11_VERIFIED_ORIGINAL_RESULTS",json.dumps(d["original_source_metrics"],sort_keys=True))

if __name__=="__main__":main()

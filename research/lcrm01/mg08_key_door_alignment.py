#!/usr/bin/env python3
"""MG08 prospective authentic DoorKey *public* key/door alignment diagnostic.

Uses unchanged frozen MG07 Go DK10/DK9, Ygg R14/R13 and conventional C30.
Only three new preregistered real Farama seeds change; exact source training,
original public action selection, feedback and native checkpoints unchanged.
NEVER read env.grid, agent_pos, carrying, seed as model input, or a private map.
"""
import argparse
import json
import resource
import time
import traceback
from pathlib import Path

from k4r_minigrid_source import canon,sha
import mg07_temporal_original_doorkey as parent

PREREG=Path(__file__).with_name("mg08_key_door_alignment_prereg.json")
SCHEMA="itd02.mg08.original-public-key-door-opportunity-diagnostic.v1"
BLOCKED="MG08_SOURCE_OR_PUBLIC_KEY_DOOR_DIAGNOSTIC_BLOCKED__NO_SCIENCE"
ABSENT="MG08_KEY_HELD_FRONT_DOOR_CONJUNCTION_ABSENT__NO_SCIENCE"
MISSING="MG08_KEY_DOOR_CONJUNCTION_WITHOUT_BOTH_NATIVE_DOOR_EFFECTS__NO_SCIENCE"
OBSERVED="MG08_BOTH_NATIVE_VISIBLE_DOOR_EFFECTS_OBSERVED__NO_SCIENCE"
NATIVE=("wingless_go_dk10","yggdrasil_r14")

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    x=p["frozen_exposure"]
    if (p.get("schema")!="itd02.mg08.authentic-original-doorkey-public-key-door-alignment-audit.v1"
        or p["parent"]["head"]!="a8a7a2e01c51c1676d39ab9a7a46c91dfee78c24"
        or p["sources"]["MG07_evaluator_blob"]!="c028d36c8cc45ab1ba7d3acd7aa0ef78c3ceebc3"
        or x["development_original_seeds"]!=[68301,68303,68307]
        or x["original_steps_cap_per_seed_role"]!=192
        or x["roles"]!=list(parent.ROLES)
        or x["training_original_same_selected_public_count"]!=1664
        or x["original_live_external_action_count"]!=0
        or x["original_public_observation_fields"]!=["image","direction","mission"]
        or p["frozen_outcome_rules"]["no_key_door_conjunction"]!=ABSENT
        or p["frozen_outcome_rules"]["conjunction_without_both_door_changes"]!=MISSING
        or p["frozen_outcome_rules"]["both_native_door_changes"]!=OBSERVED):
        raise ValueError("MG08_PROSPECTIVE_SOURCE_PREREG_DRIFT")
    return p

def public_diagnostic(role_record):
    counters={
      "original_real_selected_actions":0,
      "public_key_held_before_action_frames":0,
      "public_door_anywhere_before_action_frames":0,
      "public_door_directly_in_front_frames":0,
      "key_held_and_visible_door_anywhere_frames":0,
      "key_held_and_door_directly_in_front_frames":0,
      "front_door_without_public_key_frames":0,
      "selected_toggle_on_key_held_front_door":0,
      "selected_toggle_on_front_door_without_key":0,
      "selected_forward_when_key_held_door_anywhere":0,
      "original_public_key_pickups":0,
      "original_public_key_drops":0,
      "real_original_visible_door_state_changes":0,
      "original_source_positive_goal_rewards":0,
      "unchanged_public_before_after_frames":0,
    }
    action_counts={str(a):0 for a in range(7)}
    opportunities=[]
    for i,event in enumerate(role_record["all_original_public_selected_action_consequences"]):
        before=event["original_public_before"]
        after=event["original_public_after"]
        if (set(before)!={"image","direction","mission"}
            or set(after)!={"image","direction","mission"}):
            raise ValueError("MG08_MODEL_RECEIVED_NONPUBLIC_INPUT")
        b=before["image"];a=after["image"]
        action=event["original_selected_action"]
        if type(action)is not int or action not in range(7):
            raise ValueError("MG08_FALSE_SOURCE_ACTION")
        if (len(b)!=7 or any(len(row)!=7 for row in b)
            or len(a)!=7 or any(len(row)!=7 for row in a)):
            raise ValueError("MG08_NOT_7X7_ORIGINAL_PUBLIC_IMAGE")
        held=b[3][6][0]==5
        held_after=a[3][6][0]==5
        door_any=any(cell[0]==4 for row in b for cell in row)
        door_front=b[3][5][0]==4
        combined=held and door_front
        if event["external_selected_actions"]!=0:
            raise ValueError("MG08_HIDDEN_EXTERNAL_NAVIGATION")
        counters["original_real_selected_actions"]+=1
        action_counts[str(action)]+=1
        counters["public_key_held_before_action_frames"]+=int(held)
        counters["public_door_anywhere_before_action_frames"]+=int(door_any)
        counters["public_door_directly_in_front_frames"]+=int(door_front)
        counters["key_held_and_visible_door_anywhere_frames"]+=int(held and door_any)
        counters["key_held_and_door_directly_in_front_frames"]+=int(combined)
        counters["front_door_without_public_key_frames"]+=int(door_front and not held)
        counters["selected_toggle_on_key_held_front_door"]+=int(action==5 and combined)
        counters["selected_toggle_on_front_door_without_key"]+=int(action==5 and door_front and not held)
        counters["selected_forward_when_key_held_door_anywhere"]+=int(action==2 and held and door_any)
        counters["original_public_key_pickups"]+=int(not held and held_after)
        counters["original_public_key_drops"]+=int(held and not held_after)
        counters["real_original_visible_door_state_changes"]+=int(event["visible_door_changed"])
        counters["original_source_positive_goal_rewards"]+=int(event["original_reward"]>0)
        counters["unchanged_public_before_after_frames"]+=int(
            event["actual_public_before_sha256"]==event["actual_public_after_sha256"])
        if combined:
            opportunities.append({"ordinal":i+1,"actual_selected_action":action,
                "source_public_state_sha":event["actual_public_before_sha256"],
                "original_door_public_state":b[3][5][2],
                "original_reward":event["original_reward"]})
    if counters["original_real_selected_actions"]!=role_record["original_real_selected_steps"]:
        raise ValueError("MG08_INCORRECT_REAL_SOURCE_EPISODE_LENGTH")
    if (counters["real_original_visible_door_state_changes"]!=role_record["observed_public_door_changes"]
        or counters["original_source_positive_goal_rewards"]!=role_record["original_goal_rewards"]):
        raise ValueError("MG08_SOURCE_PUBLIC_EFFECT_OR_GOAL_RECOUNT_DRIFT")
    return {"role":role_record["role"],"seed_evaluator_only":role_record["evaluator_seed_only"],
        "source_only_counters":counters,"original_real_action_counts":action_counts,
        "actual_key_and_front_door_opportunities":opportunities}

def run(go10,go9,prereg):
    frozen_parent=parent.freeze()
    # Modify ONLY the preregistered fresh *evaluator* development seeds.
    # Do not change MG07's own frozen file, source, action selector, or FIT.
    x=dict(frozen_parent)
    x["new_original_development_seeds"]=prereg["frozen_exposure"]["development_original_seeds"]
    result=parent.run(go10,go9,x)
    if (result["external_live_actions"]!=0 or
        result["original_authentic_episode_count"]!=15 or
        result["identical_original_source_fit_per_actor"]!=1664):
        raise ValueError("MG08_NOT_THE_UNCHANGED_ORIGINAL_SOURCE_LEARNERS")
    original_records=result["canonical_full_original_source_evidence"][
        "original_source_15_native_and_conventional_episode_records"]
    if len(original_records)!=15:raise ValueError("MG08_NOT_ALL_NEW_SOURCE_EPISODES")
    observed=[public_diagnostic(row) for row in original_records]
    byrole={}
    for role in parent.ROLES:
        episodes=[x for x in observed if x["role"]==role]
        if len(episodes)!=3:raise ValueError("MG08_MISSING_EQUAL_PUBLIC_CONTROL")
        keys=episodes[0]["source_only_counters"].keys()
        byrole[role]={k:sum(z["source_only_counters"][k] for z in episodes) for k in keys}
        byrole[role]["actual_original_seed_episodes"]=3
    positive=all(byrole[r]["real_original_visible_door_state_changes"]>=1 for r in NATIVE)
    hasopportunity=any(byrole[r]["key_held_and_door_directly_in_front_frames"]>=1 for r in NATIVE)
    classification=OBSERVED if positive else (MISSING if hasopportunity else ABSENT)
    evidence={"schema":SCHEMA,
      "original_source_commit":prereg["sources"]["farama_original"],
      "preregistered_before_new_source_execution":True,
      "original_unchanged_MG07_model_and_parent_pins":prereg["sources"],
      "source_fit_same_selected_sha256":result["canonical_full_original_source_evidence"]["unchanged_original_source_fit_sha"],
      "fresh_source_original_selected_trace_sha256":result["canonical_full_original_source_trace_sha256"],
      "no_native_source_or_scoring_rule_change":True,
      "real_original_public_selected_actions_and_outcomes":original_records,
      "public_source_alignment_per_episode":observed,
      "public_source_alignment_per_actor":byrole,
      "no_hidden_world_state_or_external_navigation":True}
    return {"schema":SCHEMA,"classification":classification,
        "scientific_first_use":False,"controller_modified":False,
        "native_model_promoted":False,"original_source_actors_unchanged":True,
        "actual_source_episode_count":15,
        "same_source_selected_fit_per_actor":1664,
        "external_live_actions":0,
        "canonical_source_diagnostic_sha256":sha(canon(evidence).encode()),
        "canonical_public_diagnostic_evidence":evidence}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk10",type=Path,required=True)
    parser.add_argument("--wingless-dk9",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    start=time.perf_counter();cpu=time.process_time()
    try:
        result=run(args.wingless_dk10,args.wingless_dk9,freeze())
    except Exception as exc:
        result={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
          "error_type":type(exc).__name__,"error":str(exc),
          "traceback_tail":traceback.format_exc().splitlines()[-14:]}
    result["host_wall_seconds"]=round(time.perf_counter()-start,6)
    result["host_cpu_seconds"]=round(time.process_time()-cpu,6)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG08_CLASSIFICATION",result["classification"])
    print("MG08_CANONICAL_SHA",result.get("canonical_source_diagnostic_sha256","NONE"))
    print("MG08_PER_ACTOR_PUBLIC_DIAGNOSTIC",json.dumps(result.get("canonical_public_diagnostic_evidence",{}).get("public_source_alignment_per_actor",{}),sort_keys=True))
    if result["classification"]==BLOCKED:print("MG08_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0
if __name__=="__main__":
    raise SystemExit(main())

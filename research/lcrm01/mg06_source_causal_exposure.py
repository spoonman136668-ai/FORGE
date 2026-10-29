#!/usr/bin/env python3
"""MG06 read-only original MG05 public causal exposure and repetition audit.

The only inputs are the two independently sourced original selected-step JSON
files from immutable GitHub Actions run 40798859783. No new simulator actions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA="itd02.mg06.causal-exposure-repetition-audit.v1"
ROLES=("wingless_go_dk8u","yggdrasil_r13_on_r11","uniform_seven_action_random")
SEEDS=(65301,65303,65307)
PARENT_SHA="5f1c1aec388d4d2e0ff23701b80bbc9bc84db6d781ab943f0ceec29a5314bc6c"
POS="MG06_REPETITION_AND_CAUSAL_CONTACT_DEFICIT_REPRODUCED__NO_SCIENCE"
NEG="MG06_CAUSAL_CONTACT_DEFICIT_HYPOTHESIS_NOT_SUPPORTED__NO_SCIENCE"


def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()

def require(ok,why):
    if not ok:
        raise ValueError("MG06_ORIGINAL_SOURCE_CUSTODY:"+why)

def observation(source):
    require(type(source)is dict and set(source)=={"image","direction","mission"},"PUBLIC_KEYS")
    image=source["image"]
    require(type(image)is list and len(image)==7 and
            all(type(row)is list and len(row)==7 and
                all(type(pixel)is list and len(pixel)==3 and
                    all(type(n)is int for n in pixel) for pixel in row)
                for row in image),"PUBLIC_IMAGE_SHAPE")
    require(type(source["direction"])is int and 0<=source["direction"]<=3,"PUBLIC_DIRECTION")
    require(source["mission"]=="use the key to open the door and then get to the goal","PUBLIC_MISSION")
    return image

def inspect_record(record):
    role=record["role"];seed=record["seed_evaluator_only"]
    require(role in ROLES and seed in SEEDS,"UNREGISTERED_ARM_OR_SEED")
    events=record["real_original_selected_events"]
    require(type(events)is list and len(events)==record["original_source_steps"]
            and len(events)==record["native_or_control_actions"]
            and record["external_collector_actions"]==0
            and record["native_abstentions"]==0
            and len(events)==256,"NATIVE_ONLY_EVENT_COUNTS")
    seen=set(); repeated=unchanged=carried=carried_forward=0
    any_door=front_door=carried_any_door=carried_front_door=0
    carried_locked_front=pickup=openings=goals=0
    actual_actions={str(i):0 for i in range(7)}
    for i,event in enumerate(events):
        require(event["ordinal"]==i+1 and event["selected_feedback_delta"]==i+1
                and type(event["actual_source_action"])is int
                and event["actual_source_action"] in range(7)
                and event["actual_source_action"]==event["model_selected_action"]
                and type(event["actual_original_reward"])is float
                and type(event["terminated"])is bool
                and type(event["truncated"])is bool,"SOURCE_SELECTED_ACTION")
        before=event["public_before"]; after=event["public_after"]
        frame=observation(before);observation(after)
        require(event["public_before_sha"]==digest(before) and
                event["public_after_sha"]==digest(after),"PUBLIC_DIGEST_CHANGED")
        actual_actions[str(event["actual_source_action"])]+=1
        h=digest(before)
        if h in seen: repeated+=1
        else:seen.add(h)
        unchanged+=int(before==after)
        has_key=(frame[3][6][0]==5)
        carried+=int(has_key)
        carried_forward+=int(has_key and event["actual_source_action"]==2)
        door_visible=any(pixel[0]==4 for row in frame for pixel in row)
        at_door=(frame[3][5][0]==4)
        any_door+=int(door_visible);front_door+=int(at_door)
        carried_any_door+=int(has_key and door_visible)
        carried_front_door+=int(has_key and at_door)
        carried_locked_front+=int(has_key and at_door and frame[3][5][2]==2)
        # Source-public event effects are explicitly distinguished from
        # objective labels, reward or inference about hidden causal state.
        carried_before=frame[3][6][0]==5
        carried_after=after["image"][3][6][0]==5
        pickup_now=not carried_before and carried_after
        opening_now=(frame[3][5][0]==4 and after["image"][3][5][0]==4
                     and frame[3][5][2]!=after["image"][3][5][2])
        require(event["source_visible_pickup"]==pickup_now and
                event["source_visible_door_open"]==opening_now,"VISIBLE_EFFECT_MISMATCH")
        pickup+=int(pickup_now);openings+=int(opening_now)
        goals+=int(event["actual_original_reward"]>0)
    require(pickup==record["source_key_pickups"] and
            openings==record["source_door_openings"] and
            goals==record["source_goal_rewards"],"SOURCE_EFFECT_TOTAL_DRIFT")
    return {"role":role,"seed":seed,"steps":len(events),
            "distinct_public_observations":len(seen),"repeat_observations":repeated,
            "unchanged_public_transitions":unchanged,
            "public_key_carried_steps":carried,"key_carried_forward_actions":carried_forward,
            "visible_door_steps":any_door,"front_door_steps":front_door,
            "key_and_door_visible_steps":carried_any_door,
            "key_and_front_door_steps":carried_front_door,
            "key_and_locked_front_door_steps":carried_locked_front,
            "source_visible_key_pickups":pickup,"source_visible_door_openings":openings,
            "original_positive_goal_rewards":goals,"original_action_counts":actual_actions}

def inspect_parent(source):
    require(source.get("schema")=="itd02.mg05.authentic-native-only-seven-action.original-source.v1","PARENT_SCHEMA")
    require(source.get("scientific_first_use")is False and
            source.get("classification")=="MG05_NATIVE_ONLY_AUTHENTIC_SEVEN_ACTION_SELECTED_FEEDBACK_VERIFIED__NO_SCIENCE",
            "PARENT_CLASS")
    evidence=source["canonical_evidence"]
    require(digest(evidence)==PARENT_SHA and
            source["canonical_evidence_sha256"]==PARENT_SHA,"PINNED_EXACT_PARENT_TRACE")
    records=evidence["original_source_action_records"]
    require(len(records)==9 and
            {(r["role"],r["seed_evaluator_only"]) for r in records}==
            {(r,s) for r in ROLES for s in SEEDS},"NINE_ORIGINAL_ROLE_SEED_PAIRS")
    rows=[inspect_record(x) for x in records]
    return sorted(rows,key=lambda x:(x["role"],x["seed"]))

def classify(rows):
    groups={role:sorted((x for x in rows if x["role"]==role),key=lambda y:y["seed"]) for role in ROLES}
    h1=all(sum(1 for x in groups[role]
                  if x["repeat_observations"]/x["steps"]>0.85)>=2 for role in ROLES[:2])
    h2=all(sum(x["key_carried_forward_actions"] for x in groups[role])==0 for role in ROLES[:2])
    h3=all(sum(x["key_and_locked_front_door_steps"] for x in groups[role])==0
           for role in ROLES[:2])
    summary={role:{
        "steps":sum(x["steps"] for x in groups[role]),
        "sum_per_episode_distinct_views":sum(x["distinct_public_observations"] for x in groups[role]),
        "repeat_public_views":sum(x["repeat_observations"] for x in groups[role]),
        "unchanged_public_transitions":sum(x["unchanged_public_transitions"] for x in groups[role]),
        "key_carry_steps":sum(x["public_key_carried_steps"] for x in groups[role]),
        "carried_key_forward_actions":sum(x["key_carried_forward_actions"] for x in groups[role]),
        "key_and_door_visible_steps":sum(x["key_and_door_visible_steps"] for x in groups[role]),
        "key_and_locked_front_door_steps":sum(x["key_and_locked_front_door_steps"] for x in groups[role]),
        "key_pickups":sum(x["source_visible_key_pickups"] for x in groups[role]),
        "door_openings":sum(x["source_visible_door_openings"] for x in groups[role]),
        "goal_rewards":sum(x["original_positive_goal_rewards"] for x in groups[role])} for role in ROLES}
    return {"classification":POS if h1 and h2 and h3 else NEG,
            "preregistered_hypotheses":{"H1_repetition":h1,"H2_zero_forward_while_key":h2,
                                        "H3_no_locked_door_ahead_with_key":h3},
            "per_role":summary,"per_seed":rows}

def main():
    p=argparse.ArgumentParser()
    for a in ("first","second","output"):p.add_argument("--"+a,required=True,type=Path)
    args=p.parse_args()
    first=inspect_parent(json.loads(args.first.read_text(encoding="utf-8")))
    second=inspect_parent(json.loads(args.second.read_text(encoding="utf-8")))
    require(first==second,"TWO_INDEPENDENT_PROCESSES_DISAGREE")
    results=classify(first)
    output={"schema":SCHEMA,"source_run":40798859783,
            "original_parent_sha256":PARENT_SHA,
            "two_independent_original_processes_identical":True,
            **results,"scientific_first_use":False,
            "model_promoted":False,"controller_mutated":False}
    args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG06_CLASSIFICATION",output["classification"])
    print("MG06_HYPOTHESES",json.dumps(output["preregistered_hypotheses"],sort_keys=True))
    print("MG06_SOURCE_COUNTS",json.dumps(output["per_role"],sort_keys=True))

if __name__=="__main__":main()

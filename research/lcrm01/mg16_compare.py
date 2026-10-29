#!/usr/bin/env python3
"""Verify MG13-T two complete original, unassisted Farama layout cohorts."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg16_original_state_credit import SCHEMA,ROLES,POS,NEG

EXPECTED={
 "MiniGrid-DoorKey-6x6-v0":(77301,77303,77307),
 "MiniGrid-Empty-Random-6x6-v0":(77501,77503,77507)
}
EXPECTED_FIT="9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24"
FIELDS=("original_live_selected_steps","source_key_pickups","source_key_drops",
  "forward_while_held","front_door_while_held","source_visible_door_openings",
  "source_goal_rewards","distinct_public_views","distinct_action_ids",
  "same_heading_scene_change_count","heading_change_count","source_public_revisit_count")

def check(ok,msg):
    if not ok:raise ValueError("MG16_AUTHENTIC_ORIGINAL_SOURCE_"+msg)

def authentic_public(p):
    check(type(p)is dict and set(p)=={"image","direction","mission"},"PUBLIC_KEYS")
    check(type(p["direction"])is int and p["direction"] in range(4),"DIRECTION")
    check(type(p["mission"])is str and p["mission"] in (
          "use the key to open the door and then get to the goal",
          "get to the green goal square"),"MISSION")
    image=p["image"]
    check(type(image)is list and len(image)==7 and
          all(type(line)is list and len(line)==7 for line in image),"ORIGINAL_PUBLIC_7x7")
    check(all(type(px)is list and len(px)==3 and
              all(type(v)is int for v in px) for line in image for px in line),"PUBLIC_PIXEL")

def verify(r):
    check(r.get("schema")==SCHEMA and r.get("classification") in (POS,NEG),"CLASS")
    check(r.get("scientific_first_use") is False and r.get("accepted_native_model_promoted") is False and
          r.get("FORGE_or_CKB_controller_modified") is False and
          r.get("external_live_actions")==0 and
          r.get("original_episode_count")==42 and
          r.get("original_episode_count")==42,"AUTHORITY")
    e=r["canonical_original_source_evidence"]
    check(sha(canon(e).encode())==r["canonical_original_source_sha256"],"CANONICAL_HASH")
    check(e["original_training_stream_sha256"]==EXPECTED_FIT and
          e["original_source_fit_samples_each"]==1664 and
          e["original_cold_start_per_episode"] is True and
          e["native_original_missions_preserved"] is True and
          e["zero_externally_selected_live_actions"] is True and
          True,"ORIGINAL_UNASSISTED_FIT")
    expected={(env,seed,role) for env,seeds in EXPECTED.items() for seed in seeds for role in ROLES}
    rows=e["native_and_controls_original_source_records"]
    check(len(rows)==42 and {(r["environment"],r["seed_evaluator_only"],r["role"])
          for r in rows}==expected,"ORIGINAL_COHORT_ROLE_MATRIX")
    for env,seeds in EXPECTED.items():
        for seed in seeds:
            group=[row for row in rows if row["environment"]==env and
                   row["seed_evaluator_only"]==seed]
            check(len(group)==7 and len({row["original_start_public_sha256"] for row in group})==1,
                  "SAME_ORIGINAL_START_PUBLIC")
            for row in group:
                events=row["real_source_events"]
                check(0<len(events)<=192 and
                      row["original_live_selected_steps"]==len(events) and
                      row["external_actions"]==0,"EVENT_COUNT_OR_EXTERNAL")
                expected_mission=("get to the green goal square"
                    if env=="MiniGrid-Empty-Random-6x6-v0"
                    else "use the key to open the door and then get to the goal")
                check(row["actual_source_mission"]==expected_mission,"SOURCE_MISSION_PROVENANCE")
                view_hashes=set()
                counted={
                    "source_key_pickups":0,"source_key_drops":0,
                    "forward_while_held":0,"front_door_while_held":0,
                    "source_visible_door_openings":0,"source_goal_rewards":0,
                    "same_heading_scene_change_count":0,"heading_change_count":0
                }
                for i,entry in enumerate(events):
                    before=entry["public_before"];after=entry["public_after"]
                    authentic_public(before);authentic_public(after)
                    check(before["mission"]==expected_mission and
                          after["mission"]==expected_mission,
                          "ORIGINAL_SOURCE_GENUINE_MISSION")
                    if row["role"] in ROLES[:4]:
                        check(entry["native_mission_input"]==expected_mission and
                              entry["mission_conditioned_conventional_input"] is None and
                              entry["control_mission_blind"] is False,
                              "NATIVE_GENUINE_MISSION_NOT_PASSED")
                    elif row["role"]==ROLES[4]:
                        check(entry["mission_conditioned_conventional_input"]==expected_mission
                              and entry["native_mission_input"] is None,
                              "CONVENTIONAL_ORIGINAL_MISSION_NOT_PASSED")
                    else:
                        check(entry["native_mission_input"] is None
                              and entry["mission_conditioned_conventional_input"] is None,
                              "CONTROL_MISSION_CONDITIONAL_LEAK")
                    a=entry["actual_original_source_action"]
                    check(type(a)is int and a in range(7) and entry["step"]==i+1
                          and entry["external_live_actions"]==0,"LIVE_SELECTED_ACTION")
                    h=sha(canon(before).encode())
                    check(entry["original_public_before_sha256"]==h and
                          entry["original_public_after_sha256"]==sha(canon(after).encode()),
                          "SOURCE_PUBLIC_SHA")
                    check(type(entry["source_reward"])is float and
                          type(entry["terminated"])is bool and
                          type(entry["truncated"])is bool,"SOURCE_OUTCOME")
                    check(entry["public_forward_while_held"] ==
                          (before["image"][3][6][0] in (5,6,7) and a==2),
                          "FORWARD_WITH_HELD")
                    check(entry["public_pickup"]==
                          (before["image"][3][6][0] not in (5,6,7) and
                           after["image"][3][6][0] in (5,6,7)),
                          "PICKUP_PUBLIC")
                    check(entry["public_drop"]==
                          (before["image"][3][6][0] in (5,6,7) and
                           after["image"][3][6][0] not in (5,6,7)),
                          "DROP_PUBLIC")
                    check(entry["repeated_before_public_view"]==(h in view_hashes),
                          "PUBLIC_REPEAT")
                    view_hashes.add(h)
                    counted["source_key_pickups"]+=int(entry["public_pickup"])
                    counted["source_key_drops"]+=int(entry["public_drop"])
                    counted["forward_while_held"]+=int(entry["public_forward_while_held"])
                    counted["front_door_while_held"]+=int(entry["public_door_front_while_held"])
                    counted["source_visible_door_openings"]+=int(entry["source_visible_door_opened"])
                    counted["source_goal_rewards"]+=int(entry["source_reward"]>0)
                    counted["same_heading_scene_change_count"]+=int(
                         before["direction"]==after["direction"] and
                         before["image"]!=after["image"])
                    counted["heading_change_count"]+=int(before["direction"]!=after["direction"])
                    if i+1<len(events):
                        check(not entry["terminated"] and not entry["truncated"],
                              "POST_TERMINAL_ACTION")
                        check(entry["original_public_after_sha256"]==
                              events[i+1]["original_public_before_sha256"],
                              "DISCONNECTED_SOURCE_EVENTS")
                check(row["distinct_public_views"]==len(view_hashes) and
                      row["source_public_revisit_count"]==len(events)-len(view_hashes) and
                      row["distinct_action_ids"]==len({v["actual_original_source_action"]
                                                       for v in events}),"VIEW_ACTION_COUNTS")
                check(all(row[k]==v for k,v in counted.items()),"SOURCE_EPISODE_AGGREGATES")
    by_layout=e["per_layout_original_source_metrics"]
    summary=e["per_role_original_source_metrics"]
    check(set(by_layout)==set(EXPECTED) and set(summary)==set(ROLES),"AGGREGATE_ROLES")
    for role in ROLES:
        all_rows=[r for r in rows if r["role"]==role]
        check(summary[role]["episodes"]==6 and summary[role]["external_actions"]==0,
              "ROLE_EPISODE_TOTAL")
        for name in FIELDS:
            check(summary[role][name]==sum(r[name] for r in all_rows),"ROLE_"+name)
        for env in EXPECTED:
            subset=[r for r in all_rows if r["environment"]==env]
            entry=by_layout[env][role]
            check(entry["episodes"]==3 and entry["external_actions"]==0,
                  "ENV_EPISODE_TOTAL")
            for name in FIELDS:
                check(entry[name]==sum(r[name] for r in subset),"ENV_"+name)
    positive=all(by_layout[env][role]["source_goal_rewards"]>=1
                 for env in EXPECTED for role in ROLES[:2])
    no_collapse=all(not (
        row["environment"]=="MiniGrid-DoorKey-6x6-v0"
        and len(row["real_source_events"])==192
        and len({e["actual_original_source_action"] for e in row["real_source_events"]})==1)
        for row in rows if row["role"] in ROLES[:2])
    check(e["positive_task_criteria"] is positive and
          e["no_forward_single_action_collapse"] is no_collapse,
          "FROZEN_ORIGINAL_ACTION_LOOP_METRICS")
    check(r["classification"]==(POS if positive and no_collapse else NEG),
          "FROZEN_ORIGINAL_GOAL_RULE")
    return e

def main():
    ap=argparse.ArgumentParser()
    for k in ("first","second","output"):ap.add_argument("--"+k,type=Path,required=True)
    a=ap.parse_args()
    first=json.loads(a.first.read_text());second=json.loads(a.second.read_text())
    e=verify(first);other=verify(second)
    check(e==other and first["classification"]==second["classification"] and
          first["canonical_original_source_sha256"]==second["canonical_original_source_sha256"],
          "TWO_INDEPENDENT_SOURCE_PROCESSES_DISAGREE")
    report={"schema":"itd02.mg16.original-unassisted-cross-layout-source-verified.v1",
            "classification":first["classification"],
            "complete_independent_source_processes":2,
            "same_canonical_original_selected_source":True,
            "canonical_original_source_sha256":first["canonical_original_source_sha256"],
            "per_role":e["per_role_original_source_metrics"],
            "per_layout":e["per_layout_original_source_metrics"],
            "scientific_first_use":False}
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("MG16_TWO_PROCESS_CLASSIFICATION",report["classification"])
    print("MG16_VERIFIED_SOURCE_SHA",report["canonical_original_source_sha256"])
    print("MG16_VERIFIED_PER_LAYOUT",json.dumps(report["per_layout"],sort_keys=True))

if __name__=="__main__":main()

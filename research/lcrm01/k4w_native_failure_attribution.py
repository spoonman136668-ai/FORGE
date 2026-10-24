#!/usr/bin/env python3
"""K4W: source-authenticated retrospective native failure attribution.

No new MiniGrid episodes, no inference of missing DEV action traces,
no new policy or mechanism, no claimed causal identification.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import zipfile

FROZEN=Path(__file__).with_name("k4w_frozen_failure_attribution.json")
SCHEMA="mass.lcrm01.k4w.original-native-failure-factors-v1"
FAMILIES=("empty","fourrooms")
METHODS=("wingless_native","yggdrasil_native","learned_model_bfs",
  "public_bfs_expert","tabular_q","uniform_random","fixed_forward")
LIMITS={"empty":96,"fourrooms":192}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)


def archive(path):
    pin=json.loads(FROZEN.read_text(encoding="utf-8"))
    spec=pin["source"]
    if sha(path.read_bytes())!=spec["original_zip_sha256"]:
        raise ValueError("K4W_ORIGINAL_ZIP_AUTHENTICATION_FAILED")
    payload={}
    with zipfile.ZipFile(path) as z:
        if set(z.namelist())!=set(spec["members_sha256"]):
            raise ValueError("K4W_ORIGINAL_ARTIFACT_MEMBER_DRIFT")
        for name,hash_value in spec["members_sha256"].items():
            blob=z.read(name)
            if sha(blob)!=hash_value:
                raise ValueError("K4W_ORIGINAL_MEMBER_HASH_DRIFT:"+name)
            if name.endswith(".json"):
                payload[name]=json.loads(blob)
    c=payload["comparison.json"]
    if (c.get("schema")!="mass.lcrm01.k4u.original-source-cross-process.v1"
      or c.get("science_identical") is not True
      or c.get("differing_scientific_fields")!=[]
      or c.get("result")!="NO_REPEATABLE_NATIVE_MINIGRID_TRANSFER_ADVANCEMENT"
      or c.get("scientific_accepted") is not False
      or c.get("new_scientific_first_use") is not False):
        raise ValueError("K4W_FROZEN_NATIVE_NO_GO_NOT_AUTHENTICATED")
    for name in ("process-a.json","process-b.json"):
        r=payload[name]
        if (r.get("schema")!="mass.lcrm01.k4u.original-native-learning-minigrid-development.v1"
          or r.get("gate")!="LCRM01-K4U"
          or r.get("result")!="COMPLETE_PROSPECTIVE_NATIVE_MINIGRID_DEVELOPMENT"
          or r.get("source_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d"
          or r.get("native_Wingless_commit")!=spec["native_sources"]["wingless"]["head"]
          or r.get("native_Yggdrasil_commit")!=spec["native_sources"]["yggdrasil"]["head"]
          or r.get("FIT_episodes")!=48
          or r.get("FIT_public_experience_count")!=6114
          or len(r.get("FIT_public_experiences",[]))!=6114
          or (r.get("CHECK_evaluations"),r.get("DEV_evaluations"))!=(56,112)
          or len(r.get("DEV_public_outcomes",[]))!=112
          or r.get("native_science",{}).get("result")!="NO_QUALIFIED_NATIVE_UNFAMILIAR_WORLD_TRANSFER"
          or r.get("native_FIT_checks",{}).get("authentic_independent_native_cold_process_restores") is not True
          or r.get("scientific_first_use") is not False
          or r.get("scientific_accepted") is not False
          or r.get("K4R_original_scientific_benchmark_qualified") is not True
          or r.get("K4S_original_source_negative_preserved") is not True):
            raise ValueError("K4W_ORIGINAL_SCIENCE_OR_SOURCE_DRIFT:"+name)
    return pin,payload


def fit_factors(rows,expected_count=6114):
    report={}
    for family in FAMILIES:
        rs=[r for r in rows if r["family"]==family]
        by_action=Counter()
        positive=0;nonzero=0;terminal=0;terminal_positive=0
        toward=0;away=0;unchanged=0;blocked=0
        prior=defaultdict(lambda:defaultdict(set))
        public_states=set()
        per_episode=defaultdict(int)
        for r in rs:
            action=r["action"];before=r["before"];after=r["after"]
            if type(action) is not int or action not in (0,1,2):
                raise ValueError("K4W_FIT_INVALID_NAVIGATION_ACTION")
            expected_keys={"X","Y","GoalX","GoalY","Direction","FrontBlocked"}
            if set(before)!=expected_keys or set(after)!=expected_keys:
                raise ValueError("K4W_FIT_PUBLIC_SENSOR_SCHEMA_DRIFT")
            if any(type(before[k]) is not int for k in ("X","Y","GoalX","GoalY","Direction")):
                raise ValueError("K4W_PUBLIC_SENSOR_TYPE_DRIFT")
            if (type(before["FrontBlocked"]) is not bool or
                type(after["FrontBlocked"]) is not bool):
                raise ValueError("K4W_PUBLIC_BLOCKED_SENSOR_DRIFT")
            if (before["GoalX"],before["GoalY"])!=(after["GoalX"],after["GoalY"]):
                raise ValueError("K4W_FIT_GOAL_NONSTATIONARY")
            rv=r["reward"]
            if type(rv) not in (float,int) or not math.isfinite(rv):
                raise ValueError("K4W_FIT_PUBLIC_REWARD_NONFINITE")
            by_action[action]+=1;positive+=rv>0;nonzero+=rv!=0
            terminal+=bool(r["terminal"])
            terminal_positive+=bool(r["terminal"] and rv>0)
            blocked+=bool(before["FrontBlocked"])
            prev_distance=abs(before["X"]-before["GoalX"])+abs(before["Y"]-before["GoalY"])
            next_distance=abs(after["X"]-after["GoalX"])+abs(after["Y"]-after["GoalY"])
            if next_distance<prev_distance:toward+=1
            elif next_distance>prev_distance:away+=1
            else:unchanged+=1
            key=tuple(before[k] for k in ("X","Y","GoalX","GoalY","Direction","FrontBlocked"))
            out=tuple(after[k] for k in ("X","Y","Direction","FrontBlocked"))
            public_states.add(key)
            prior[key][action].add(out)
            per_episode[r["seed"]]+=1
        ambiguous=sum(len(successors)>1 for actions in prior.values()
              for successors in actions.values())
        report[family]={
         "FIT_actual_steps":len(rs),
         "FIT_unique_world_seeds":len(per_episode),
         "FIT_action_counts":{str(i):by_action[i] for i in range(3)},
         "FIT_positive_public_reward_events":positive,
         "FIT_nonzero_public_reward_events":nonzero,
         "FIT_positive_reward_fraction":positive/len(rs),
         "FIT_positive_rewards_are_terminal":positive==terminal_positive,
         "FIT_terminal_events":terminal,
         "FIT_successful_terminal_events":terminal_positive,
         "FIT_reward_free_transitions":len(rs)-nonzero,
         "FIT_steps_toward_goal_manhattan":toward,
         "FIT_steps_away_goal_manhattan":away,
         "FIT_steps_same_goal_manhattan":unchanged,
         "FIT_front_blocked_observation_count":blocked,
         "FIT_distinct_public_native_states":len(public_states),
         "FIT_reused_source_state_action_conflicting_results":ambiguous,
         "feature_collision_absence_does_not_prove_representation_sufficiency":True
        }
        if (len(per_episode)!=24 or set(by_action)!={0,1,2}
          or positive!=terminal_positive or terminal!=24
          or toward+away+unchanged!=len(rs)):
            raise ValueError("K4W_ORIGINAL_EXPERIENCE_PARITY_DRIFT:"+family)
    if sum(v["FIT_actual_steps"] for v in report.values())!=expected_count:
        raise ValueError("K4W_FIT_SOURCE_SIZE_CHANGED")
    return report


def dev_factors(data):
    summary={}
    for family in FAMILIES:
        universe=[r for r in data if r["family"]==family]
        if len(universe)!=56:
            raise ValueError("K4W_DEV_POLICY_WORLD_PARITY_DRIFT")
        detail={}
        for method in METHODS:
            rows=[r for r in universe if r["policy"]==method]
            if len(rows)!=8 or sorted(r["seed"] for r in rows)!=list(range(6100,6108)):
                raise ValueError("K4W_EXPECTED_FRESH_DEV_WORLDS_MISSING")
            if any(type(r["first_action"]) is not int or r["first_action"] not in (0,1,2)
               or not 1<=r["steps"]<=LIMITS[family]
               or not isinstance(r["actual_public_trace_sha256"],str)
               or len(r["actual_public_trace_sha256"])!=64 for r in rows):
                raise ValueError("K4W_DEV_SOURCE_CORRUPTION")
            winners=sum(bool(r["success"]) for r in rows)
            detail[method]={
              "worlds":8,"real_goal_successes":winners,
              "total_steps":sum(r["steps"] for r in rows),
              "full_horizon_episodes":sum(r["steps"]==LIMITS[family] for r in rows),
              "first_action_counts":{str(i):sum(r["first_action"]==i for r in rows)
                  for i in range(3)},
              "mean_original_reward":sum(r["real_reward"] for r in rows)/8,
              "per_step_DEV_action_trace_recoverable":False}
        summary[family]=detail
    return summary


def inspect(original):
    report=fit_factors(original["FIT_public_experiences"])
    outcomes=dev_factors(original["DEV_public_outcomes"])
    for family in FAMILIES:
        orig=original["native_science"]["family_results"][family]
        for name in METHODS:
            actual=outcomes[family][name]
            if (actual["real_goal_successes"]!=8*orig["success_rate"][name] or
                abs(actual["mean_original_reward"]-orig["mean_public_reward"][name])>1e-12):
                raise ValueError("K4W_ORIGINAL_POLICY_RESULT_CUSTODY_DRIFT")
    return {"fit":report,"dev":outcomes}


def diagnose(archive_path):
    pin,payload=archive(archive_path)
    first=inspect(payload["process-a.json"])
    second=inspect(payload["process-b.json"])
    if first!=second:
        raise ValueError("K4W_ORIGINAL_PROCESS_CAUSAL_FACTS_DIVERGE")
    total=sum(v["FIT_actual_steps"] for v in first["fit"].values())
    positives=sum(v["FIT_positive_public_reward_events"] for v in first["fit"].values())
    return {
      "schema":SCHEMA,"gate":"LCRM01-K4W",
      "result":"RETROSPECTIVE_FAILURE_FACTORS_IDENTIFIED_WITH_CAUSAL_LIMITS",
      "original_science_verdict":"NO_REPEATABLE_NATIVE_MINIGRID_TRANSFER_ADVANCEMENT",
      "immutable_K4U_zip_sha256":pin["source"]["original_zip_sha256"],
      "two_original_processes_agree":True,"FIT_real_experiences":total,
      "FIT_positive_environment_reward_events":positives,
      "FIT_positive_reward_fraction":positives/total,
      "FIT_source":first["fit"],"DEV_original_observed_outcomes":first["dev"],
      "observed":{
        "FIT_environment_reward_extremely_sparse":positives/total<.01,
        "Both_natives_failed_FourRooms":all(first["dev"]["fourrooms"][m]["real_goal_successes"]==0
                           for m in ("wingless_native","yggdrasil_native")),
        "Learned_dynamics_planner_succeeded_all_DEV_worlds":all(
           first["dev"][family]["learned_model_bfs"]["real_goal_successes"]==8
           for family in FAMILIES),
        "All_native_DEV_worlds_have_retained_full_per_step_action_trace":False},
      "not_causally_identified":{
        "primary_failure_due_to_sparse_reward":None,
        "primary_failure_due_to_local_representation":None,
        "primary_failure_due_to_temporal_credit":None,
        "primary_failure_due_to_lack_of_multi_step_planning":None,
        "optimal_unobserved_counterfactual_actions":None},
      "next_prospective_requirement":"Freeze qualitatively distinct local credit/planning hypotheses, actual unfamiliar seeds and competent matched controls before any new native learning trial; no K4U DEV tuning.",
      "new_MINIGRID_episodes":0,
      "new_native_learning_runs":0,
      "native_cognition_breakthrough":False,
      "scientific_first_use":False,"scientific_accepted":False,
      "K4U_scientific_NO_GO_preserved":True
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--artifact-zip",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or not a.output.parent.is_dir():
        raise RuntimeError("K4W_RECEIPT_ALREADY_EXISTS")
    result=diagnose(a.artifact_zip)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("K4W_DIAGNOSIS="+result["result"])
    print("K4W_POSITIVE_FIT_REWARDS="+str(result["FIT_positive_environment_reward_events"]))
    print("K4W_FIT_EVENT_COUNT="+str(result["FIT_real_experiences"]))
    print("K4W_NO_CAUSAL_PRIMARY_FAILURE_CLAIM=PASS")
    print("K4W_K4U_SCIENTIFIC_NO_GO_PRESERVED=PASS")


if __name__=="__main__":
    main()

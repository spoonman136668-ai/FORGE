"""AC-27 retrospective independent original MG12 goal / action attribution.

Read exact two-process original Farama source-owned selected public traces.
NO new source episodes, native model training, actor evaluation or scientific
first use. This was written AFTER the MG12 result; no prospective claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from itertools import combinations

SCHEMA="forge.ac27.mg12-original-source-retrospective-attribution.v1"
PARENT_HEAD="7293165c299f4ff9d5b945e0bb601d5b929219e1"
SOURCE_SHA="4c5b48288f1d8c61561527da5b4f0767c220d06d3f1fbeaf07f27b3d8ca6675c"
SOURCE_COMMIT="7f5853792ea7f04f75614661006d87fcf949f26d"
FIT_SHA="9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24"
WING_HEAD="2992a25e3fe05783bfa80ecf70d737bb2a21e281"
YGG_HEAD="770244b04d011466458b2335d3951daf7653dc8f"
ROLES=("wingless_dk13","yggdrasil_r17","conventional_public_successor","random")
SEEDS=(72301,72303,72307)
EXPECTED_CLASS="MG12_BOTH_NATIVE_ORIGINAL_GOAL_REWARDS__ENGINEERING_ONLY"
PUB_FIELDS=frozenset(("image","direction","mission"))
EVENT_FIELDS=frozenset(("actual_original_source_action","external_live_actions",
  "native_or_control_origin","original_public_after_sha256",
  "original_public_before_sha256","public_after","public_before",
  "public_door_front_while_held","public_drop","public_forward_while_held",
  "public_pickup","repeated_before_public_view","role","selected_reason",
  "source_reward","source_visible_door_opened","step","terminated","truncated"))

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("utf-8")
def sha(x):return hashlib.sha256(x).hexdigest()

def verify_public(p):
    if (type(p) is not dict or set(p)!=PUB_FIELDS or
        type(p["direction"]) is not int or p["direction"] not in range(4) or
        type(p["mission"]) is not str or
        type(p["image"]) is not list or len(p["image"])!=7 or
        any(type(row) is not list or len(row)!=7 or
          any(type(pixel) is not list or len(pixel)!=3 or
            any(type(v) is not int or v not in range(256) for v in pixel)
          for pixel in row) for row in p["image"])):
        raise RuntimeError("AC27_PRIVATE_OR_FORGED_PUBLIC_VISUAL")
    return sha(canonical(p))

def verify_parent(first,second,comparison):
    if (type(first) is not dict or type(second) is not dict or
        first.get("schema")!="itd02.mg12.original-public-successor-persistence-world.v1" or
        second.get("schema")!=first["schema"] or
        first.get("classification")!=EXPECTED_CLASS or
        second.get("classification")!=EXPECTED_CLASS or
        comparison.get("schema")!="itd02.mg12.two-process-selected-original-evidence.v1" or
        comparison.get("classification")!=EXPECTED_CLASS or
        comparison.get("two_independent_fresh_original_source_processes") is not True or
        comparison.get("selected_source_actions_not_external") is not True or
        comparison.get("equal_policy_public_observation") is not True or
        first.get("scientific_first_use") is not False or
        second.get("scientific_first_use") is not False or
        comparison.get("scientific_first_use") is not False or
        first.get("external_live_actions")!=0 or
        second.get("external_live_actions")!=0 or
        first.get("original_episode_count")!=12 or
        second.get("original_episode_count")!=12 or
        first.get("accepted_native_model_promoted") is not False):
        raise RuntimeError("AC27_MG12_PARENT_QUALIFICATION_FAILED")
    if ("canonical_original_source_evidence" not in first or
        "canonical_original_source_evidence" not in second):
        raise RuntimeError("AC27_ORIGINAL_SOURCE_EVIDENCE_MISSING")
    a=first["canonical_original_source_evidence"]
    b=second["canonical_original_source_evidence"]
    if (a!=b or sha(canonical(a))!=SOURCE_SHA or
        first.get("canonical_original_source_sha256")!=SOURCE_SHA or
        second.get("canonical_original_source_sha256")!=SOURCE_SHA or
        comparison.get("canonical_original_source_sha256")!=SOURCE_SHA or
        a.get("original_upstream_farama")!=SOURCE_COMMIT or
        a.get("original_training_stream_sha256")!=FIT_SHA or
        a.get("original_source_fit_samples_each")!=1664 or
        a.get("frozen_original_world_seeds")!=list(SEEDS) or
        a.get("frozen_source_pins")!={"Wingless_DK13_head":WING_HEAD,
                                     "Yggdrasil_R17_head":YGG_HEAD} or
        a.get("no_manually_derived_stage_input_to_any_policy") is not True or
        a.get("no_original_live_external_actions") is not True):
        raise RuntimeError("AC27_TWO_PROCESS_SOURCE_SHA_OR_NATIVE_SOURCE_DRIFT")
    return a

def verify_record(r):
    if (type(r) is not dict or
        r.get("role") not in ROLES or r.get("seed_evaluator_only") not in SEEDS or
        r.get("external_actions")!=0 or
        type(r.get("real_source_events")) is not list or
        len(r["real_source_events"])!=r.get("original_live_selected_steps") or
        not 1<=len(r["real_source_events"])<=192):
        raise RuntimeError("AC27_UNREGISTERED_SELECTED_SOURCE_EPISODE")
    events=r["real_source_events"]
    before_hashes=[]
    prior_after=None
    action_hist=Counter()
    positive=[]
    door_open=[]
    pickups=drops=forward_while_held=front_while_held=0
    for i,e in enumerate(events,1):
        if (type(e) is not dict or set(e)!=EVENT_FIELDS or
            e["role"]!=r["role"] or e["step"]!=i or
            type(e["actual_original_source_action"]) is not int or
            e["actual_original_source_action"] not in range(7) or
            e["external_live_actions"]!=0 or
            type(e["source_reward"]) not in (int,float) or
            not 0<=e["source_reward"]<=1 or
            type(e["terminated"]) is not bool or
            type(e["truncated"]) is not bool or
            type(e["selected_reason"]) is not str or
            type(e["native_or_control_origin"]) is not str):
            raise RuntimeError("AC27_SELECTED_SOURCE_EVENT_INPUT_INVALID")
        for key in ("public_door_front_while_held","public_drop",
                    "public_forward_while_held","public_pickup",
                    "source_visible_door_opened","repeated_before_public_view"):
            if type(e[key]) is not bool:
                raise RuntimeError("AC27_ORIGINAL_SOURCE_AUDIT_FIELD_DRIFT")
        b=verify_public(e["public_before"])
        after=verify_public(e["public_after"])
        if (b!=e["original_public_before_sha256"] or
            after!=e["original_public_after_sha256"] or
            (prior_after is not None and prior_after!=b)):
            raise RuntimeError("AC27_ORIGINAL_SOURCE_PUBLIC_TIMELINE_DRIFT")
        before_hashes.append(b)
        prior_after=after
        action_hist[e["actual_original_source_action"]]+=1
        if e["source_reward"]>0:
            positive.append({"step":i,"source_reward":e["source_reward"]})
            if not e["terminated"]:
                raise RuntimeError("AC27_GOAL_REWARD_WITHOUT_REAL_TERMINAL")
        if e["source_visible_door_opened"]:door_open.append(i)
        pickups+=int(e["public_pickup"])
        drops+=int(e["public_drop"])
        forward_while_held+=int(e["public_forward_while_held"])
        front_while_held+=int(e["public_door_front_while_held"])
    if (events[0]["original_public_before_sha256"]!=r["original_start_public_sha256"] or
        len(set(before_hashes))!=r["distinct_public_views"] or
        len(events)-len(set(before_hashes))!=r["source_public_revisit_count"] or
        len(action_hist)!=r["distinct_action_ids"] or
        len(positive)!=r["source_goal_rewards"] or
        len(door_open)!=r["source_visible_door_openings"] or
        pickups!=r["source_key_pickups"] or drops!=r["source_key_drops"] or
        forward_while_held!=r["forward_while_held"] or
        front_while_held!=r["front_door_while_held"]):
        raise RuntimeError("AC27_ORIGINAL_SOURCE_RECOMPUTED_METRICS_DRIFT")
    return {
      "role":r["role"],"seed":r["seed_evaluator_only"],
      "steps":len(events),"unique_selected_public_before_views":len(set(before_hashes)),
      "source_public_revisit_count":r["source_public_revisit_count"],
      "distinct_legal_actions_selected":len(action_hist),
      "actual_goals":positive,"source_door_open_step_audit_only":door_open,
      "action_histogram":{str(a):action_hist[a] for a in range(7)},
      "external_actions":0,
    }

def comparison_replay(a,b):
    ev_a=a["real_source_events"];ev_b=b["real_source_events"]
    length=min(len(ev_a),len(ev_b))
    disagree_actions=sum(ev_a[i]["actual_original_source_action"]!=ev_b[i]["actual_original_source_action"]
                         for i in range(length))
    disagree_transitions=sum(
        (ev_a[i]["actual_original_source_action"],
         ev_a[i]["original_public_before_sha256"],
         ev_a[i]["original_public_after_sha256"])!=
        (ev_b[i]["actual_original_source_action"],
         ev_b[i]["original_public_before_sha256"],
         ev_b[i]["original_public_after_sha256"])
        for i in range(length))
    return {
      "aligned_source_action_steps":length,
      "action_disagreements":disagree_actions,
      "selected_before_action_after_disagreements":disagree_transitions,
      "episode_lengths_equal":len(ev_a)==len(ev_b),
      "complete_original_selected_episode_identical":
         len(ev_a)==len(ev_b) and disagree_transitions==0,
    }

def analyze(first,second,comparison):
    source=verify_parent(first,second,comparison)
    records=source["native_and_conventional_public_source_records"]
    if (type(records) is not list or len(records)!=12 or
        {(z["role"],z["seed_evaluator_only"]) for z in records}!={
            (role,seed) for role in ROLES for seed in SEEDS}):
        raise RuntimeError("AC27_ORIGINAL_SOURCE_ROLE_SEED_COHORT_DRIFT")
    bykey={(z["role"],z["seed_evaluator_only"]):z for z in records}
    audits=[verify_record(z) for z in records]
    role_totals={}
    for role in ROLES:
        rr=[x for x in audits if x["role"]==role]
        role_totals[role]={
            "original_goal_completed_episodes":sum(bool(x["actual_goals"]) for x in rr),
            "original_selected_step_count":sum(x["steps"] for x in rr),
            "summed_per_episode_public_view_counts":sum(x["unique_selected_public_before_views"] for x in rr),
            "external_action_count":0,
        }
        parent_metrics=source["per_role_original_source_metrics"][role]
        if (role_totals[role]["original_goal_completed_episodes"]!=parent_metrics["source_goal_rewards"] or
            role_totals[role]["original_selected_step_count"]!=parent_metrics["original_live_selected_steps"] or
            role_totals[role]["summed_per_episode_public_view_counts"]!=parent_metrics["distinct_public_views"] or
            parent_metrics!=comparison["original_source_metrics"][role]):
            raise RuntimeError("AC27_ORIGINAL_ROLE_REPORTED_METRIC_DRIFT")
    if [role_totals[x]["original_goal_completed_episodes"] for x in ROLES]!=[1,1,1,0]:
        raise RuntimeError("AC27_ORIGINAL_GOAL_RESULTS_NOT_RETAINED")
    pairs=[]
    for seed in SEEDS:
        for a,b in (("wingless_dk13","yggdrasil_r17"),
                    ("wingless_dk13","conventional_public_successor"),
                    ("yggdrasil_r17","conventional_public_successor")):
            pairs.append({"seed":seed,"role_a":a,"role_b":b,
                          **comparison_replay(bykey[(a,seed)],bykey[(b,seed)])})
    if not all(x["complete_original_selected_episode_identical"] for x in pairs
        if x["role_a"]=="yggdrasil_r17"):
        raise RuntimeError("AC27_YGG_ORIGINAL_PUBLIC_TRAJECTORY_CONTROL_PARITY_DRIFT")
    goals=[x for x in audits if x["actual_goals"]]
    if ({(x["role"],x["seed"]) for x in goals}!=
        {("wingless_dk13",72307),("yggdrasil_r17",72307),
         ("conventional_public_successor",72307)}):
        raise RuntimeError("AC27_GOAL_SOURCE_SEEDS_DRIFT")
    return {
       "schema":SCHEMA,
       "scope":"RETROSPECTIVE_SOURCE_REPLAY_NOT_NATIVE_MODEL_TRAINING",
       "retrospective_not_preregistered_before_source_execution":True,
       "mg12_exact_qualified_head":PARENT_HEAD,
       "farama_original_source_commit":SOURCE_COMMIT,
       "original_two_independent_processes_source_sha256":SOURCE_SHA,
       "original_training_selected_fit_stream_sha256":FIT_SHA,
       "original_source_development_seed_list":list(SEEDS),
       "original_two_process_selected_evidence_identical":True,
       "original_source_episode_count":12,
       "original_source_selected_actions_replayed":sum(x["steps"] for x in audits),
       "original_source_new_actions_executed":0,
       "selected_action_trajectories":audits,
       "role_summary":role_totals,
       "exact_source_action_and_transition_comparisons":pairs,
       "all_ygg_original_actions_and_transitions_identical_to_conventional":True,
       "wingless_finished_15_steps_ahead_of_ygg_and_conventional_on_one_goal_seed":True,
       "native_architecture_superiority_established":False,
       "unknown_family_transfer_tested":False,
       "private_agent_pose_or_source_oracle_used":False,
       "original_models_controller_or_queue_modified":False,
       "scientific_first_use":False,
       "scientific_admission":False,
       "classification":"AC27_MG12_BOTH_NATIVE_GOALS_REAL_CONVENTIONAL_PARITY__ENGINEERING_ONLY",
    }

def run(first_path,second_path,compare_path,out):
    first=json.loads(Path(first_path).read_text(encoding="utf-8"))
    second=json.loads(Path(second_path).read_text(encoding="utf-8"))
    comparison=json.loads(Path(compare_path).read_text(encoding="utf-8"))
    r=analyze(first,second,comparison)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    return r

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for x in ("first","second","comparison","out"):
        p.add_argument("--"+x,type=Path,required=True)
    x=p.parse_args()
    r=run(x.first,x.second,x.comparison,x.out)
    print("AC27_ORIGINAL_NATIVE_BOTH_REACHED_GOAL=PASS")
    print("AC27_ORIGINAL_YGG_CONVENTIONAL_SELECTED_TRACE_IDENTICAL=PASS")
    print("AC27_SCIENTIFIC_NATIVE_SUPERIORITY=NOT_ESTABLISHED")
    print("AC27_ORIGINAL_SOURCE_ACTIONS_EXECUTED=ZERO")

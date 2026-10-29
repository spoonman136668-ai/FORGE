#!/usr/bin/env python3
"""AC31 independent original two-process selected source evidence verifier."""
from __future__ import annotations
import argparse,json,hashlib,math
from pathlib import Path
from k4r_minigrid_source import canon,sha
from ac31_original_multifamily import SCHEMA,ROLES,POS,NEG,freeze

COMPARE="forge.ac31.two-independent-original-selected-source-processes.v1"

def check(condition,marker):
    if not condition:raise ValueError("AC31_AUTHENTIC_ORIGINAL_SOURCE_"+marker)

def public(p,expected_mission):
    check(type(p)is dict and set(p)=={"image","direction","mission"},"PUBLIC_PRIVATE_FIELDS")
    check(type(p["mission"])is str and p["mission"]==expected_mission,"VERBATIM_MISSION")
    check(type(p["direction"])is int and p["direction"] in (0,1,2,3),"PUBLIC_DIRECTION")
    x=p["image"]
    check(type(x)is list and len(x)==7,"PUBLIC_IMAGE_SHAPE")
    for row in x:
        check(type(row)is list and len(row)==7,"PUBLIC_ROW")
        for v in row:
            check(type(v)is list and len(v)==3 and
                  all(type(i)is int for i in v),"PUBLIC_TILE_TYPE")
            kind,color,state=v
            check(0<=kind<=10 and 0<=color<=5 and 0<=state<=255 and
                  (kind!=4 or state in (0,1,2)),"PUBLIC_TILE_RANGE")
    return sha(canon(p).encode())

def verify(r):
    p=freeze()
    check(type(r)is dict and r.get("schema")==SCHEMA and
          r.get("classification") in (POS,NEG),"CLASSIFICATION")
    check(r.get("scientific_first_use") is False and
          r.get("scientific_admission") is False and
          r.get("accepted_native_model_promoted") is False and
          r.get("FORGE_or_CKB_controller_modified") is False and
          r.get("original_episode_count")==45 and
          r.get("external_live_actions")==0,"SCIENCE_AND_EPISODE_SCOPE")
    evidence=r.get("canonical_original_source_evidence")
    check(type(evidence)is dict and sha(canon(evidence).encode())==
          r.get("canonical_original_source_sha256"),"CANONICAL_SELECTED_EVIDENCE")
    check(evidence.get("original_upstream_farama")==p["parent"]["original_farama"] and
          evidence.get("original_training_stream_sha256")==p["FIT"]["require_canonical_history_sha256"] and
          evidence.get("original_source_fit_samples_each")==1664 and
          evidence.get("frozen_source_pins")==p["native"] and
          evidence.get("original_world_cohorts")==p["worlds"] and
          evidence.get("original_missions_preserved_at_all_actor_boundaries") is True and
          evidence.get("no_external_rescue_or_manually_derived_stage_actions") is True,
          "SOURCE_FIT_COHORT_OR_ROLE_PROVENANCE")
    rows=evidence.get("real_original_source_episodes")
    check(type(rows)is list and len(rows)==45,"ORIGINAL_SOURCE_45_ROWS")
    expected={(role,w["environment"],seed) for role in ROLES for w in p["worlds"]
              for seed in w["seeds"]}
    check({(z["role"],z["environment"],z["seed_evaluator_only"]) for z in rows}==expected,
          "ORIGINAL_ROLE_WORLD_SEED_SET")
    by_family=evidence["per_family_original_source_metrics"]
    for w in p["worlds"]:
        env=w["environment"];mission=w["mission"]
        for seed in w["seeds"]:
            group=[q for q in rows if q["environment"]==env and q["seed_evaluator_only"]==seed]
            check(len(group)==5 and
                  len({q["original_start_public_sha256"] for q in group})==1,
                  "ORIGINAL_SAME_SEED_PUBLIC_RESET")
        for role in ROLES:
            subset=[z for z in rows if z["environment"]==env and z["role"]==role]
            check(len(subset)==3 and role in by_family[env],"PER_FAMILY_ROLE")
            check(sum(z["source_goal_completed"] for z in subset)==
                  by_family[env][role]["original_goal_completions"],"ORIGINAL_GOAL_AGGREGATE")
            check(sum(z["original_live_selected_steps"] for z in subset)==
                  by_family[env][role]["original_selected_actions"],"ORIGINAL_ACTION_AGGREGATE")
            for z in subset:
                events=z["real_source_events"]
                check(z["external_actions"]==0 and
                      z["actual_source_mission"]==mission and
                      type(events)is list and len(events)==z["original_live_selected_steps"] and
                      1<=len(events)<=w["limit"],"ORIGINAL_SOURCE_STEP_BOUND")
                last=None;num_positive=0
                for i,e in enumerate(events,1):
                    check(type(e)is dict and e["role"]==role and e["environment"]==env and
                          e["seed_evaluator_only"]==z["seed_evaluator_only"] and
                          e["step"]==i and e["external_live_actions"]==0 and
                          e["true_original_mission_preserved_at_actor_boundary"] is True,
                          "ACTOR_REAL_SELECTED_SOURCE_PROVENANCE")
                    action=e["actual_original_source_action"]
                    check(type(action)is int and 0<=action<=6,"SOURCE_7_ACTION")
                    b=public(e["public_before"],mission)
                    after=public(e["public_after"],mission)
                    check(b==e["original_public_before_sha256"] and
                          after==e["original_public_after_sha256"] and
                          (last is None or last==b),"SOURCE_PUBLIC_HASH_OR_TIMELINE")
                    last=after
                    rw=e["source_reward"]
                    check(type(rw)in (int,float) and math.isfinite(rw) and
                          0<=rw<=1 and type(e["terminated"])is bool and
                          type(e["truncated"])is bool,"SOURCE_TRUE_REWARD_TYPE")
                    num_positive+=int(rw>0)
                    if rw>0:check(e["terminated"] is True,"POSITIVE_ORIGINAL_TERMINAL")
                    if i<len(events):check(not e["terminated"] and not e["truncated"],
                                           "SOURCE_END_BEFORE_LAST_EVENT")
                check(public(events[0]["public_before"],mission)==
                      z["original_start_public_sha256"] and
                      (num_positive>0)==bool(z["source_goal_completed"]),
                      "SOURCE_GOAL_START_ORIGINAL")
    by_role={k:sum(by_family[env][k]["original_goal_completions"] for env in by_family)
             for k in ROLES}
    qualified=all(by_family[env][role]["original_goal_completions"]>=1
                  for env in by_family for role in ROLES[:2]) and all(
                by_role[n]>max(by_role[ROLES[2]],by_role[ROLES[3]]) for n in ROLES[:2])
    check(r["classification"]==(POS if qualified else NEG),"PREDECLARED_SUCCESS_RULE")
    return {"classification":r["classification"],"source_sha256":r["canonical_original_source_sha256"],
            "selected_source_step_count":evidence["original_source_selected_actions_total"],
            "original_episodes":45,"goal_summary":by_family}

def main():
    ap=argparse.ArgumentParser()
    for n in ("first","second","output"):ap.add_argument("--"+n,type=Path,required=True)
    q=ap.parse_args()
    first=json.loads(q.first.read_text(encoding="utf-8"))
    second=json.loads(q.second.read_text(encoding="utf-8"))
    a=verify(first);b=verify(second)
    check(a==b and first["canonical_original_source_evidence"]==
          second["canonical_original_source_evidence"],
          "TWO_INDEPENDENT_SOURCE_PROCESSES_MISMATCH")
    record={"schema":COMPARE,"classification":a["classification"],
      "original_source_development_valid":True,
      "two_independent_original_processes_equal":True,
      "canonical_original_source_sha256":a["source_sha256"],
      "source_selected_actions":a["selected_source_step_count"],
      "original_source_episodes":45,"goal_summary":a["goal_summary"],
      "scientific_first_use":False,"scientific_admission":False,
      "native_architecture_superiority_established":False,
      "protected_main_controller_original_models_changed":False}
    q.output.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("AC31_AUTHENTIC_ORIGINAL_TWO_PROCESS_SOURCE=PASS")
    print("AC31_SOURCE_SHA",record["canonical_original_source_sha256"])
    print("AC31_ORIGINAL_DEV_CLASSIFICATION",record["classification"])
    print("AC31_ORIGINAL_REAL_GOALS",json.dumps(
          {env:{role:d["original_goal_completions"] for role,d in rows.items()}
           for env,rows in record["goal_summary"].items()},sort_keys=True))
if __name__=="__main__":
    main()

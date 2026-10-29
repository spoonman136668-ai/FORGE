#!/usr/bin/env python3
"""Independent MG05 exact-source native-only and assistance-budget custody."""
import argparse
import json
from pathlib import Path

from k4r_minigrid_source import canon,sha
from mg05_native_only_capped_original_doorkey import (
    SCHEMA,NEGATIVE,POSITIVE,original
)
ROLES=tuple(original.ROLES)
CAPS=(0,32,64)
SEEDS=(65301,65303,65307)
def validate(d):
    if (d.get("schema")!=SCHEMA
        or d.get("classification") not in (NEGATIVE,POSITIVE)
        or d.get("scientific_first_use") is not False
        or d.get("scientific_acceptance") is not False
        or d.get("model_or_checkpoint_promoted") is not False
        or d.get("FORGE_controller_modified") is not False
        or d.get("original_go_r8_modified") is not False
        or d.get("original_ygg_r12_modified") is not False
        or d.get("same_source_public_training_per_actor")!=1664
        or d.get("authenticated_original_episode_count")!=27):
        raise ValueError("MG05_WRONG_SOURCE_NATIVE_AUTHORITY")
    evidence=d.get("source_only_canonical_evidence")
    if (type(evidence) is not dict
        or sha(canon(evidence).encode())!=d.get("canonical_original_selected_actions_sha256")
        or evidence.get("source_only_stage_objective_not_learned") is not True
        or evidence.get("native_go_dk8_is_not_original_wingless_r8") is not True):
        raise ValueError("MG05_TAMPERED_ORIGINAL_SELECTED_ACTION_EVIDENCE")
    events=evidence["real_original_minigrid_new_seed_events"]
    if len(events)!=27 or len(set((x["role"],x["seed_evaluator_only"],
                                   x["allowed_external_budget"]) for x in events))!=27:
        raise ValueError("MG05_MISSING_INDEPENDENT_ORIGINAL_WORLD_ARMS")
    for seed in SEEDS:
        for cap in CAPS:
            trio=[e for e in events if e["seed_evaluator_only"]==seed
                  and e["allowed_external_budget"]==cap]
            if len(trio)!=3 or {e["role"] for e in trio}!=set(ROLES):
                raise ValueError("MG05_MISSING_SOURCE_ACTOR")
            if len({e["original_public_start_sha256"] for e in trio})!=1:
                raise ValueError("MG05_NOT_EQUAL_ORIGINAL_PUBLIC_RESET")
            if len({canon(e["source_public_initial_frame"]) for e in trio})!=1:
                raise ValueError("MG05_NOT_EQUAL_ORIGINAL_PUBLIC_OBSERVATIONS")
            for e in trio:
                rows=e["all_original_env_selected_feedback"]
                n=e["original_real_env_steps"]
                if (n!=len(rows)
                    or e["native_or_control_actions"]+e["external_collector_actions"]!=n
                    or e["external_collector_actions"]>cap
                    or e["native_only_complete_task"] and (cap!=0 or
                      e["external_collector_actions"]!=0 or not e["ordered_key_door_goal_sequence"])):
                    raise ValueError("MG05_FAKE_NATIVE_ONLY_COMPLETION_OR_BUDGET")
                if cap==0 and e["external_collector_actions"]!=0:
                    raise ValueError("MG05_HIDDEN_NATIVE_ONLY_ASSISTANCE")
                if cap==0 and e["stop_reason"]=="native_only_abstained_before_env_step" and e["abstention_attempts"]<1:
                    raise ValueError("MG05_NATIVE_ONLY_ABSTENTION_NOT_RECORDED")
                if cap>0 and e["stop_reason"]=="external_budget_exhausted_before_env_step" and e["external_collector_actions"]!=cap:
                    raise ValueError("MG05_ASSISTANCE_LIMIT_NOT_ACTUALLY_EXHAUSTED")
                for j,step in enumerate(rows):
                    if (step["index"]!=j+1
                        or step["selected_feedback_count"]!=j+1
                        or type(step["selected_real_env_action"]) is not int
                        or step["selected_real_env_action"] not in range(7)
                        or type(step["selected_actual_reward"]) is not float
                        or type(step["terminated"]) is not bool
                        or type(step["truncated"]) is not bool
                        or type(step["real_public_carrying_changed"]) is not bool
                        or type(step["real_public_visible_door_changed"]) is not bool
                        or set(step["public_before"])!={"image","direction","mission"}
                        or set(step["public_after"])!={"image","direction","mission"}
                        or step["external_objective"] not in ("carrying_changed","visible_door_state_changed")):
                        raise ValueError("MG05_NOT_SELECTED_REAL_PUBLIC_DOORKEY_FEEDBACK")
                    if step["native_or_control_proposal"] is None:
                        if step["action_origin"]!="handcoded_public_collector_budgeted":
                            raise ValueError("MG05_NATIVE_ACTION_IMPERSONATION")
                    else:
                        if (step["action_origin"]!="model_selected_original_public_effect"
                            or step["native_or_control_proposal"]!=step["selected_real_env_action"]):
                            raise ValueError("MG05_REAL_NATIVE_ACTION_REPLACED")
                    if cap==0 and step["native_or_control_proposal"] is None:
                        raise ValueError("MG05_NATIVE_ONLY_CONTAINS_FALLBACK_EVENT")
    summary=evidence["per_actor_per_budget_summary"]
    for role in ROLES:
        for cap in CAPS:
            s=summary[role][str(cap)]
            chosen=[e for e in events if e["role"]==role
                    and e["allowed_external_budget"]==cap]
            if (s["episodes"]!=3 or
                s["model_selected_steps"]!=sum(e["native_or_control_actions"] for e in chosen)
                or s["external_collector_steps"]!=sum(e["external_collector_actions"] for e in chosen)
                or s["original_live_steps"]!=sum(e["original_real_env_steps"] for e in chosen)
                or s["native_only_complete_tasks"]!=sum(e["native_only_complete_task"] for e in chosen)):
                raise ValueError("MG05_ACTOR_SOURCE_SUMMARY_MISMATCH")
    should_win=all(summary[r]["0"]["native_only_complete_tasks"]>=1
                   for r in ("wingless_go_dk8","yggdrasil_r12_on_r11"))
    if (d["native_only_success_both_models"] is not should_win
        or d["classification"]!=(POSITIVE if should_win else NEGATIVE)):
        raise ValueError("MG05_PREDECLARED_SCIENCE_CLASSIFICATION_REWRITTEN")
    return evidence

def main():
    parser=argparse.ArgumentParser()
    for name in ("first","second","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    a=parser.parse_args()
    x=json.loads(a.first.read_text(encoding="utf-8"))
    y=json.loads(a.second.read_text(encoding="utf-8"))
    cx=validate(x);cy=validate(y)
    if (cx!=cy or x["classification"]!=y["classification"]
        or x["canonical_original_selected_actions_sha256"]!=y["canonical_original_selected_actions_sha256"]):
        raise ValueError("MG05_TWO_REAL_ORIGINAL_SOURCE_PROCESSES_NOT_EQUAL")
    result={"schema":"itd02.mg05.two-separate-real-source-processes.v1",
      "classification":x["classification"],
      "original_farama_source_reproductions":2,
      "exact_selected_original_history_and_native_action_sha":x["canonical_original_selected_actions_sha256"],
      "native_only_assistance_actually_zero":True,
      "native_only_both_models_complete":x["native_only_success_both_models"],
      "per_role_assistance_results":cx["per_actor_per_budget_summary"],
      "scientific_first_use":False}
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("MG05_TWO_PROCESS_CLASSIFICATION",result["classification"])
    print("MG05_TWO_PROCESS_CANONICAL_SHA",result["exact_selected_original_history_and_native_action_sha"])
    print("MG05_ASSISTANCE_RESULTS",json.dumps(result["per_role_assistance_results"],sort_keys=True))
if __name__=="__main__":main()

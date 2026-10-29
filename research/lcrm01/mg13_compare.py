#!/usr/bin/env python3
"""MG13 independent source comparator: previous replay vs NEW real actor actions."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg13_authentic_postopen_fork import SCHEMA,NEGATIVE,POSITIVE,ROLES,NATIVE

def verify(data):
    if (data.get("schema")!=SCHEMA or data.get("classification") not in (NEGATIVE,POSITIVE)
        or data.get("scientific_first_use") is not False
        or data.get("native_model_promoted") is not False
        or data.get("accepted_checkpoint_changed") is not False
        or data.get("controller_changed") is not False
        or data.get("authenticated_source_forks")!=3
        or data.get("independent_live_episodes")!=24
        or data.get("matched_original_source_FIT_count")!=1664
        or data.get("live_external_actions")!=0):
        raise ValueError("MG13_SOURCE_FORK_AUTHORITY_INVALID")
    ev=data.get("canonical_original_source_evidence")
    if (type(ev)is not dict or sha(canon(ev).encode())!=data.get("canonical_source_digest")
        or ev.get("no_replay_prefix_given_to_actors") is not True
        or ev.get("live_original_external_navigator_actions")!=0
        or ev.get("replay_before_measurement_is_evaluator_controlled") is not True
        or ev.get("no_native_model_changed") is not True
        or ev.get("source_FIT_selected_history_sha")!=ev.get("independent_two_step_same_source_FIT_sha")):
        raise ValueError("MG13_SOURCE_EVIDENCE_OR_MATCHED_FIT_MISSING")
    boundaries=ev.get("original_known_development_boundaries")
    if ([b["id"] for b in boundaries]!=["71303_go116","71303_ygg37","71307_ygg118"]
        or any(len(b["replay_selected_actions"])!=b["original_open_ordinal"] for b in boundaries)):
        raise ValueError("MG13_SOURCE_ORIGINAL_REPLAY_BOUNDARIES_CHANGED")
    rows=ev.get("true_original_source_fork_and_actor_events")
    if not isinstance(rows,list) or len(rows)!=24:
        raise ValueError("MG13_EIGHT_REAL_SOURCE_ACTORS_INCOMPLETE")
    for boundary in boundaries:
        group=[r for r in rows if r["source_replay_boundary_id"]==boundary["id"]]
        if (len(group)!=8 or {r["role"] for r in group}!=set(ROLES)
            or len({r["original_public_start_sha"] for r in group})!=1
            or group[0]["original_public_start_sha"]!=boundary["original_open_public_after_sha256"]
            or len({r["source_replay_prefix_sha"] for r in group})!=1
            or group[0]["source_replay_prefix_sha"]!=boundary["exact_prefix_trace_sha256"]):
            raise ValueError("MG13_REAL_ORIGINAL_PUBLIC_SOURCE_FORK_NOT_IDENTICAL")
        for arm in group:
            events=arm["all_original_public_selected_events"]
            if (not 1<=len(events)<=16 or
                arm["real_original_source_actions"]!=len(events) or
                arm["source_replay_prefix_length"]!=len(boundary["replay_selected_actions"])
                or arm["external_actions"]!=0 or
                arm["distinct_original_selected_actions"]!=len({x["action"] for x in events})):
                raise ValueError("MG13_SOURCE_ACTIONS_NOT_INDEPENDENT")
            for ordinal,x in enumerate(events,1):
                if (x["index"]!=ordinal or
                    type(x["action"])is not int or x["action"] not in range(7) or
                    type(x["original_reward"])is not float or
                    type(x["terminated"])is not bool or type(x["truncated"])is not bool or
                    x["external_action_count"]!=0 or
                    set(x["public_before"])!={"image","direction","mission"} or
                    set(x["public_after"])!={"image","direction","mission"} or
                    x["before_sha"]!=sha(canon(x["public_before"]).encode()) or
                    x["after_sha"]!=sha(canon(x["public_after"]).encode())):
                    raise ValueError("MG13_NOT_GENUINE_SELECTED_PUBLIC_REWARD_EVENT")
                if ordinal==1 and x["before_sha"]!=boundary["original_open_public_after_sha256"]:
                    raise ValueError("MG13_MODEL_NOT_AT_AUTHENTICATED_OPEN_DOOR_PUBLIC_STATE")
    metrics=ev["per_role_public_fork_metrics"]
    for role in ROLES:
        rows_for=[r for r in rows if r["role"]==role]
        if (metrics[role]["authenticated_postopen_forks"]!=3
            or metrics[role]["real_independently_selected_actions"]!=sum(r["real_original_source_actions"] for r in rows_for)
            or metrics[role]["original_positive_goal_rewards"]!=sum(r["original_goal_rewards"] for r in rows_for)
            or metrics[role]["original_actual_door_state_changes"]!=sum(r["actual_original_door_changes"] for r in rows_for)):
            raise ValueError("MG13_ORIGINAL_SOURCE_ROLE_SUMMARY_INCORRECT")
    both=all(metrics[role]["original_positive_goal_rewards"]>=1 for role in NATIVE)
    if data["classification"]!=(POSITIVE if both else NEGATIVE):
        raise ValueError("MG13_FROZEN_SOURCE_OUTCOME_RULE_CHANGED")
    return ev

def main():
    p=argparse.ArgumentParser()
    for name in ("first","second","output"):
        p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    a=json.loads(args.first.read_text(encoding="utf-8"))
    b=json.loads(args.second.read_text(encoding="utf-8"))
    ea=verify(a);eb=verify(b)
    if (ea!=eb or a["classification"]!=b["classification"]
        or a["canonical_source_digest"]!=b["canonical_source_digest"]):
        raise ValueError("MG13_TWO_WHOLE_ORIGINAL_STATE_FORK_PROCESSES_DIVERGED")
    out={"schema":"itd02.mg13.original-open-door-two-independent-processes.v1",
         "classification":a["classification"],"independent_full_source_processes":2,
         "canonical_true_original_source_sha":a["canonical_source_digest"],
         "authentic_prior_source_opening_forks":3,
         "source_evaluator_replayed_pretest_actions":sum(len(x["replay_selected_actions"]) for x in ea["original_known_development_boundaries"])*8,
         "new_actor_live_external_navigator_actions":0,
         "results":ea["per_role_public_fork_metrics"],
         "scientific_first_use":False}
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("MG13_TWO_PROCESS",out["classification"])
    print("MG13_VERIFIED_SHA",out["canonical_true_original_source_sha"])
    print("MG13_VERIFIED_METRICS",json.dumps(out["results"],sort_keys=True))
if __name__=="__main__":main()

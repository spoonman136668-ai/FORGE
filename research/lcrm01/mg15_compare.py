#!/usr/bin/env python3
"""MG15 independent source-selected event custody and two complete process parity."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg15_online_frozen_original import SCHEMA,NEGATIVE,POSITIVE,ROLES,NATIVE,SEEDS

def verify(d):
    if (d.get("schema")!=SCHEMA or d.get("classification") not in (POSITIVE,NEGATIVE)
        or d.get("scientific_first_use") is not False
        or d.get("accepted_model_changed") is not False or
        d.get("FORGE_controller_changed") is not False
        or d.get("original_seeds")!=list(SEEDS) or
        d.get("independent_original_episodes")!=21 or
        d.get("FIT_original_selected_count")!=1664 or
        d.get("live_external_actions")!=0):
        raise ValueError("MG15_ORIGINAL_SOURCE_AUTHORITY_FALSE")
    e=d.get("canonical_source_evidence")
    if (type(e)is not dict or sha(canon(e).encode())!=d.get("canonical_source_sha")
        or e.get("original_FIT_samples_per_learner")!=1664
        or e.get("frozen_no_online_and_no_episode_memory_bundled") is not True
        or e.get("external_live_selected_actions")!=0 or
        e.get("no_original_native_source_changed") is not True or
        e.get("zero_oracle_hidden_state_or_manual_stage") is not True):
        raise ValueError("MG15_TAMPERED_FIT_OR_ORIGINAL_SOURCE_EVIDENCE")
    rows=e.get("source_original_selected_episode_events")
    totals=e.get("original_source_per_role")
    if type(rows)is not list or len(rows)!=21:
        raise ValueError("MG15_ORIGINAL_SELECTED_EVENTS_MISSING")
    for seed in SEEDS:
        g=[r for r in rows if r.get("seed_evaluator_only")==seed]
        if (len(g)!=7 or {r["role"] for r in g}!=set(ROLES)
            or len({r["original_start_public_sha256"] for r in g})!=1):
            raise ValueError("MG15_UNEQUAL_ORIGINAL_SOURCE_RESET")
        for actor in g:
            events=actor["real_source_events"]
            if (not 1<=len(events)<=192 or actor["original_live_selected_steps"]!=len(events)
                or actor["external_actions"]!=0
                or actor["distinct_action_ids"]!=len({a["actual_original_source_action"] for a in events})):
                raise ValueError("MG15_NOT_TRUE_ACTOR_SELECTED_ORIGINAL_EVENT")
            for i,s in enumerate(events,1):
                if (s["step"]!=i or
                    s["role"]!=actor["role"] and not (
                     actor["role"].endswith("_online") and s["role"]==
                       actor["role"].replace("_online","").replace("conventional_successor","conventional_public_successor"))
                    or type(s["actual_original_source_action"])is not int
                    or s["actual_original_source_action"] not in range(7)
                    or type(s["source_reward"])is not float
                    or type(s["terminated"])is not bool or
                    type(s["truncated"])is not bool or s["external_live_actions"]!=0
                    or set(s["public_before"])!={"image","direction","mission"}
                    or set(s["public_after"])!={"image","direction","mission"}
                    or s["original_public_before_sha256"]!=sha(canon(s["public_before"]).encode())
                    or s["original_public_after_sha256"]!=sha(canon(s["public_after"]).encode())):
                    raise ValueError("MG15_SELECTED_ORIGINAL_PUBLIC_EVENT_INVALID")
            if actor["role"].endswith("_frozen"):
                if actor.get("frozen_original_fit_samples_unchanged")!=1664:
                    raise ValueError("MG15_FROZEN_FEEDBACK_WAS_APPLIED")
    if set(totals)!=set(ROLES):raise ValueError("MG15_ROLE_METRICS_MISSING")
    for role in ROLES:
        group=[r for r in rows if r["role"]==role]
        if (len(group)!=3 or totals[role]["episodes"]!=3 or
            totals[role]["external_actions"]!=0 or
            totals[role]["source_goal_rewards"]!=sum(r["source_goal_rewards"] for r in group) or
            totals[role]["source_visible_door_openings"]!=sum(r["source_visible_door_openings"] for r in group) or
            totals[role]["original_live_selected_steps"]!=sum(r["original_live_selected_steps"] for r in group)):
            raise ValueError("MG15_SOURCE_RECOUNT_DIFFERENT")
    gains=e["live_vs_frozen_native_goal_differences"]
    for live,frozen in NATIVE:
        if gains[live]!=totals[live]["source_goal_rewards"]-totals[frozen]["source_goal_rewards"]:
            raise ValueError("MG15_FROZEN_COUNTERFACTUAL_GOAL_DRIFT")
    met=all(totals[live]["source_goal_rewards"]>=1 and gains[live]>=1 for live,_ in NATIVE)
    if d["classification"]!=(POSITIVE if met else NEGATIVE):
        raise ValueError("MG15_PROSPECTIVE_GOAL_RULE_CHANGED")
    return e

def main():
    ap=argparse.ArgumentParser()
    for n in ("first","second","output"):
        ap.add_argument("--"+n,type=Path,required=True)
    x=ap.parse_args()
    a=json.loads(x.first.read_text());b=json.loads(x.second.read_text())
    first=verify(a);second=verify(b)
    if (first!=second or a["classification"]!=b["classification"]
        or a["canonical_source_sha"]!=b["canonical_source_sha"]):
        raise ValueError("MG15_TWO_INDEPENDENT_ORIGINAL_SOURCE_PROCESSES_NOT_IDENTICAL")
    out={"schema":"itd02.mg15.two-independent-original-source-processes.v1",
        "classification":a["classification"],
        "original_complete_processes":2,
        "canonical_original_public_sha":a["canonical_source_sha"],
        "actual_source_per_role":first["original_source_per_role"],
        "online_vs_frozen_goals":first["live_vs_frozen_native_goal_differences"],
        "original_live_external_actions":0,"scientific_first_use":False}
    x.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG15_TWO_PROCESS",out["classification"])
    print("MG15_VERIFIED_SHA",out["canonical_original_public_sha"])
    print("MG15_VERIFIED_RESULTS",json.dumps(out["actual_source_per_role"],sort_keys=True))
if __name__=="__main__":main()

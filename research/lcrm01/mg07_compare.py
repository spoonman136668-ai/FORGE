#!/usr/bin/env python3
"""MG07 independent exact-source repro: true original selected actions only."""
import argparse,json
from pathlib import Path
from k4r_minigrid_source import canon,sha
from mg07_temporal_original_doorkey import SCHEMA,NEGATIVE,POSITIVE,ROLES

def verify(r):
    if (r.get("schema")!=SCHEMA or r.get("classification") not in (NEGATIVE,POSITIVE)
        or r.get("scientific_first_use") is not False
        or r.get("native_model_promoted") is not False
        or r.get("controller_modified") is not False
        or r.get("original_accepted_sources_unchanged") is not True
        or r.get("external_live_actions")!=0
        or r.get("original_authentic_episode_count")!=15
        or r.get("identical_original_source_fit_per_actor")!=1664):
        raise ValueError("MG07_ORIGINAL_SOURCE_OR_AUTHORITY_MISSING")
    e=r.get("canonical_full_original_source_evidence")
    if (type(e)is not dict or
        sha(canon(e).encode())!=r.get("canonical_full_original_source_trace_sha256")
        or e.get("no_external_navigation") is not True
        or e.get("original_wingless_r8_untouched") is not True
        or e.get("original_ygg_r10_r11_r12_untouched") is not True
        or e.get("same_source_fit_per_native_and_conventional")!=1664):
        raise ValueError("MG07_ORIGINAL_CANONICAL_EVIDENCE_CORRUPTED")
    records=e.get("original_source_15_native_and_conventional_episode_records")
    if type(records)is not list or len(records)!=15:
        raise ValueError("MG07_INCOMPLETE_FIFTEEN_ORIGINAL_ROLES")
    for seed in (67301,67303,67307):
        group=[v for v in records if v.get("evaluator_seed_only")==seed]
        if len(group)!=5 or {v["role"] for v in group}!=set(ROLES):
            raise ValueError("MG07_INCOMPATIBLE_ORIGINAL_SEED_MATRIX")
        if len({v["original_public_start_sha256"] for v in group})!=1:
            raise ValueError("MG07_NON_EQUALLY_INFORMED_ORIGINAL_START")
        for row in group:
            seq=row["all_original_public_selected_action_consequences"]
            if (not seq or len(seq)!=row["original_real_selected_steps"] or
                len(seq)>192 or row["external_actions"]!=0):
                raise ValueError("MG07_FALSE_NATIVE_ACTION_OR_MISSING_ORIGINAL_SOURCE")
            for i,x in enumerate(seq):
                if (x["ordinal"]!=i+1 or
                    type(x["original_selected_action"])is not int or
                    x["original_selected_action"] not in range(7) or
                    type(x["original_reward"])is not float or
                    type(x["terminated"])is not bool or
                    type(x["truncated"])is not bool or
                    type(x["carrying_changed"])is not bool or
                    type(x["visible_door_changed"])is not bool or
                    x["external_selected_actions"]!=0 or
                    set(x["original_public_before"])!={"image","direction","mission"} or
                    set(x["original_public_after"])!={"image","direction","mission"}):
                    raise ValueError("MG07_NOT_ORIGINAL_SELECTED_PUBLIC_ENV_STEP")
                if x["actual_public_before_sha256"]!=sha(canon(x["original_public_before"]).encode()) or x["actual_public_after_sha256"]!=sha(canon(x["original_public_after"]).encode()):
                    raise ValueError("MG07_ORIGINAL_PUBLIC_IMAGE_CHECKSUM_INVALID")
    summary=e["per_role_source_metrics"]
    for role in ROLES:
        individual=[r for r in records if r["role"]==role]
        if (summary[role]["episodes"]!=3 or summary[role]["external_actions"]!=0 or
            summary[role]["actual_original_native_actions"]!=sum(x["original_real_selected_steps"] for x in individual)
            or summary[role]["original_goal_rewards"]!=sum(x["original_goal_rewards"] for x in individual)):
            raise ValueError("MG07_ACTOR_METRICS_DIFFER_FROM_GENUINE_SOURCE")
    ok=all(summary[k]["original_goal_rewards"]>=1 for k in ("wingless_go_dk10","yggdrasil_r14"))
    if r["classification"]!=(POSITIVE if ok else NEGATIVE):
        raise ValueError("MG07_PREDECLARED_OUTCOME_REWRITTEN")
    return e

def main():
    parser=argparse.ArgumentParser()
    for arg in ("first","second","output"):
        parser.add_argument("--"+arg,type=Path,required=True)
    opts=parser.parse_args()
    a=json.loads(opts.first.read_text(encoding="utf-8"))
    b=json.loads(opts.second.read_text(encoding="utf-8"))
    ea=verify(a); eb=verify(b)
    if (ea!=eb or a["classification"]!=b["classification"]
        or a["canonical_full_original_source_trace_sha256"]!=b["canonical_full_original_source_trace_sha256"]):
        raise ValueError("MG07_TWO_SEPARATE_ORIGINAL_SOURCE_PROCESSES_DIFFER")
    out={"schema":"itd02.mg07.original-farama-two-process-custody.v1",
         "classification":a["classification"],"original_source_independent_processes":2,
         "canonical_original_selected_trace_sha256":a["canonical_full_original_source_trace_sha256"],
         "original_source_per_role_metrics":ea["per_role_source_metrics"],
         "external_original_live_actions":0,"scientific_first_use":False}
    opts.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("MG07_TWO_PROCESS",out["classification"])
    print("MG07_VERIFIED_ORIGINAL_SHA",out["canonical_original_selected_trace_sha256"])
    print("MG07_VERIFIED_RESULTS",json.dumps(out["original_source_per_role_metrics"],sort_keys=True))
if __name__=="__main__":main()

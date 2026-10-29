#!/usr/bin/env python3
"""MG24 original-world selected development for 9 independent frozen learners.

Fresh original world DEV evidence, not sealed first-use or scientific superiority.
Pre-executable frozen prereg + independent 15-history lineage gate is REQUIRED.
"""
from __future__ import annotations
import argparse,hashlib,json,traceback,time
from pathlib import Path
import gymnasium as gym
import minigrid

from mg17_original_family_source_qual import attest_source,frozen,digest
from mg24_source_lineage_audit import validate as validate_source_lineage
from mg24_original_selected_dev_actors import ROLES,episode

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg24_fresh_development_prereg.json"
SCHEMA="itd02.mg24.real-original-nine-arm-selected-source-development.v1"
FARAMA="7f5853792ea7f04f75614661006d87fcf949f26d"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
SEEDS=((948101,948103),(948201,948203),(948301,948303),(948401,948403))

def record(source_root,go23,go19):
    # Source-history audit MUST complete before even importing/instantiating an env.
    lineage=validate_source_lineage()
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    d=p["development"]
    if (p["schema"]!="itd02.mg24.authentic-original-fresh-development-and-controls.v1" or
        p["phase"]!="PROSPECTIVE_PRE_EXECUTABLE_SOURCE_LINEAGE__NO_SCIENTIFIC_FIRST_USE" or
        p["parents"]["farama"]!=FARAMA or
        p["parents"]["wingless_mg23"]!="f4b29adfac260150e7ed83b37f69ee9f0371056f" or
        p["parents"]["yggdrasil_mg23"]!="a052b06b010ec9e61e4a46e0d57f544a76590c33" or
        tuple(p["arms"])!=ROLES or
        [x["environment"] for x in d["source_family_seeds"]]!=list(FAMILIES) or
        [x["seeds"] for x in d["source_family_seeds"]]!=[list(v) for v in SEEDS] or
        d["max_actions_per_episode"]!=128):
        raise ValueError("MG24_FROZEN_BEFORE_SOURCE_TRIAL_CHANGED")
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG24_IMPORTED_UNFROZEN_FARAMA")
    original=frozen()
    attest_source(source_root,original)
    lookup={row["id"]:row["entry_point"] for row in original["families"]}
    rows=[];resources=[];per_family={}
    for family,seeds in zip(FAMILIES,SEEDS):
        if gym.spec(family).entry_point!=lookup[family]:
            raise ValueError("MG24_WRONG_ORIGINAL_SOURCE_REGISTRATION")
        memory={role:None for role in ROLES}
        for seed in seeds:
            peers=[]
            for role in ROLES:
                result,usage,checkpoint=episode(gym,family,seed,role,128,
                                                memory[role],go23,go19,lookup[family])
                peers.append(result)
                rows.append(result)
                resources.append(usage)
                if role!=ROLES[-1]:
                    memory[role]=checkpoint
            if len(peers)!=9 or len(set(r["original_start_sha256"] for r in peers))!=1:
                raise ValueError("MG24_NINE_ARMS_DO_NOT_START_IDENTICAL_ORIGINAL_WORLD")
        totals={}
        for role in ROLES:
            selected=[r for r in rows if r["family"]==family and r["role"]==role]
            if len(selected)!=2 or selected[0]["prior_selected_source_samples"]!=0:
                raise ValueError("MG24_NOT_TWO_SEQUENTIAL_FRESH_DEV_EPISODES")
            if role!=ROLES[-1] and selected[1]["prior_selected_source_samples"]!=selected[0]["selected_source_samples_after"]:
                raise ValueError("MG24_OWN_SELECTED_FEEDBACK_NOT_PERSISTED")
            totals[role]={"episodes":2,
                          "real_original_actions":sum(x["selected_actions"] for x in selected),
                          "original_terminal_goals":sum(x["original_terminal_goal_reward_count"] for x in selected),
                          "mission_target_public_pickups":sum(x["selected_public_target_pickup_count"] for x in selected),
                          "source_locked_door_opens":sum(x["selected_public_locked_door_open_count"] for x in selected),
                          "public_pickup_door_reward_temporal_chains":sum(x["observed_public_pickup_then_door_then_terminal_reward"] for x in selected)}
        per_family[family]=totals
    if len(rows)!=72 or any(not 1<=x["selected_actions"]<=128 for x in rows):
        raise ValueError("MG24_ORIGINAL_ROLE_SOURCE_MATRIX_INCOMPLETE")
    source={"schema":SCHEMA,"classification":"EXPOSED_ORIGINAL_DEV_NOT_SEALED_NOT_SCIENCE",
            "pinned_original_farama":FARAMA,
            "native_source_heads":{"wingless_mg23":p["parents"]["wingless_mg23"],
                                   "yggdrasil_mg23":p["parents"]["yggdrasil_mg23"],
                                   "wingless_mg19":p["parents"]["wingless_parent_mg19"],
                                   "yggdrasil_mg19":p["parents"]["yggdrasil_parent_mg19"]},
            "original_public_history_lineage_digest":lineage["canonical_receipt_sha256"],
            "quarantined_original_dev_seeds":[s for pair in SEEDS for s in pair],
            "new_source_development_actions":sum(r["selected_actions"] for r in rows),
            "full_original_selected_source_72_episodes":rows,
            "per_family_per_role_original_outcomes":per_family,
            "external_source_actions":0,"sealed_first_use":False,
            "accepted_native_models_changed":False,
            "forge_original_controller_changed":False}
    return {"schema":SCHEMA,"source":source,"canonical_source_sha256":digest(source),
            "resources_outside_reproducible_source_digest":resources,
            "not_equal_cpu_capacity_or_generalization_proof":True}

def compare(a,b):
    first=json.loads(Path(a).read_text(encoding="utf-8"))
    second=json.loads(Path(b).read_text(encoding="utf-8"))
    if (first.get("source")!=second.get("source") or
        first.get("canonical_source_sha256")!=second.get("canonical_source_sha256") or
        first.get("canonical_source_sha256")!=digest(first["source"]) or
        first.get("schema")!=SCHEMA or
        len(first["source"]["full_original_selected_source_72_episodes"])!=72 or
        first["source"]["sealed_first_use"] is not False or
        any(r["selected_source_events_sha256"]!=digest(r["selected_source_events"])
            for r in first["source"]["full_original_selected_source_72_episodes"])):
        raise ValueError("MG24_AUTHENTIC_ORIGINAL_SOURCE_INDEPENDENT_PROCESSES_DISAGREE")
    print("MG24_ORIGINAL_72_EPISODES_NINE_ARM_SOURCE_REPLAY_PASS_NOT_SCIENCE "+first["canonical_source_sha256"])
    print("MG24_ACTUAL_ORIGINAL_SOURCE_GOAL_TARGET_DOOR_SUMMARY "+
          json.dumps(first["source"]["per_family_per_role_original_outcomes"],sort_keys=True,separators=(",",":")))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--go-mg23",type=Path)
    ap.add_argument("--go-mg19",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--compare",nargs=2,type=Path)
    args=ap.parse_args()
    if args.compare:
        compare(*args.compare);return
    if not all((args.source_root,args.go_mg23,args.go_mg19,args.output)):
        ap.error("require --source-root, --go-mg23, --go-mg19, --output")
    begin=time.perf_counter()
    try:
        output=record(args.source_root.resolve(),args.go_mg23.resolve(),args.go_mg19.resolve())
    except Exception as exc:
        output={"schema":SCHEMA,"classification":"MG24_REAL_SOURCE_DEVELOPMENT_BLOCKED",
                "reason":str(exc),"exception_type":type(exc).__name__,
                "trace_tail":traceback.format_exc().splitlines()[-12:],
                "sealed_first_use":False}
    output["wall_seconds_outside_canonical_source"]=round(time.perf_counter()-begin,6)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    if "reason" in output:
        print("MG24_ORIGINAL_DEV_BLOCKED_REASON "+output["reason"])
        raise RuntimeError(output["reason"])
    print("MG24_REAL_ORIGINAL_WORLD_72_DEV_EPISODES_COMPLETE_NOT_SCIENCE "+output["canonical_source_sha256"])
    print("MG24_ACTUAL_ORIGINAL_SOURCE_OUTCOME_SUMMARY "+
          json.dumps(output["source"]["per_family_per_role_original_outcomes"],sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()

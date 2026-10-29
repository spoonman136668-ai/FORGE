#!/usr/bin/env python3
"""MG20 quarantined true-source admissions, NOT FIT/DEV/sealed learning."""
import argparse
import json
from pathlib import Path

import gymnasium as gym
import minigrid
from mg17_original_family_source_qual import attest_source,frozen,digest
from mg20_native_original_episode import episode,ROLES

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg20_original_native_selected_source_prereg.json"
SOURCE="7f5853792ea7f04f75614661006d87fcf949f26d"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")


def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    c=p["cohort"]
    if (p["schema"]!="itd02.mg20.original-native-source-smoke.v1" or
        p["phase"]!="PROSPECTIVE_SOURCE_ONLY_NO_SCIENCE" or
        p["parents"]["MiniGrid"]!=SOURCE or
        tuple(c["source_families"])!=FAMILIES or
        tuple(c["actors"])!=ROLES or
        c["seed"]!=918201 or
        c["max_actions_per_native_or_control_episode"]!=2 or
        c["kind"]!="QUARANTINED_ENGINEERING" or
        not c["permanently_ineligible_for_fit_dev_sealed"] or
        not all(p["controls"].values()) or
        not all(p["interpretation"].values())):
        raise ValueError("MG20_PROSPECTIVE_PROTOCOL_DRIFT")
    return p


def execute(source_root,go_exe):
    p=protocol()
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG20_IMPORTED_SOURCE_NOT_FROZEN")
    original=frozen()
    attest_source(source_root,original)
    registry={f["id"]:f["entry_point"] for f in original["families"]}
    results=[]
    for family in FAMILIES:
        if gym.spec(family).entry_point!=registry[family]:
            raise ValueError("MG20_FARAMA_SOURCE_REGISTRATION_DRIFT")
        for role in ROLES:
            results.append(episode(gym,family,role,p["cohort"]["seed"],
                                   p["cohort"]["max_actions_per_native_or_control_episode"],
                                   go_exe))
    if len(results)!=12 or any(r["steps"] not in (1,2) or
                              not r["original_mission"] for r in results):
        raise ValueError("MG20_INCOMPLETE_NATIVE_SELECTED_SOURCE_GATE")
    for family in FAMILIES:
        three=[r for r in results if r["family"]==family]
        if len(three)!=3 or len(set(r["start_sha256"] for r in three))!=1:
            raise ValueError("MG20_STARTING_SOURCE_PARITY")
    return {"schema":"itd02.mg20.original-native-selected-source-engineering.v1",
            "classification":"NATIVE_REAL_SOURCE_SELECTED_SMOKE_NO_SCIENCE",
            "original_minigrid":SOURCE,
            "wingless_source":p["parents"]["Wingless_MG19"],
            "yggdrasil_source":p["parents"]["Yggdrasil_MG19"],
            "quarantine":"SEED_918201_PERMANENTLY_INELIGIBLE",
            "records":results,"canonical_sha256":digest(results)}


def comparison(a,b):
    x=json.loads(Path(a).read_text(encoding="utf-8"))
    y=json.loads(Path(b).read_text(encoding="utf-8"))
    if (x!=y or x["schema"]!="itd02.mg20.original-native-selected-source-engineering.v1" or
        len(x["records"])!=12 or x["canonical_sha256"]!=digest(x["records"]) or
        any(r["trace_sha256"]!=digest(r["events"]) for r in x["records"])):
        raise ValueError("MG20_INDEPENDENT_NATIVE_REAL_WORLD_SOURCE_REPLAY_FAILED")
    print("MG20_REAL_ORIGINAL_SELECTED_ACTION_TRACE_PARITY_PASS_NOT_SCIENCE "+x["canonical_sha256"])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--native-go",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--compare",nargs=2)
    args=parser.parse_args()
    if args.compare:
        comparison(*args.compare)
        return
    if not (args.source_root and args.native_go and args.output):
        parser.error("require --source-root --native-go --output")
    output=execute(args.source_root,args.native_go)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG20_ORIGINAL_SOURCE_NATIVE_SELECTED_ADMISSION_PASS_NOT_SCIENCE "+output["canonical_sha256"])


if __name__=="__main__":
    main()

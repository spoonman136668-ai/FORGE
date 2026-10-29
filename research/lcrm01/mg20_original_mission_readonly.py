#!/usr/bin/env python3
"""MG20 source-custody verification of genuine mission admission only.

Uses formerly qualified MG17 original public smoke frames as READ-ONLY prompts.
Never learns, acts on an environment, or promotes quarantined seeds to FIT/DEV.
"""
import argparse, collections, hashlib, json, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg20_authentic_source_readonly_prereg.json"
SCHEMA="itd02.mg20.authentic-quarantined-source-native-readonly-mission-probe.v1"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
EXPECTED_SHA="a275aa709abc787e54c0d61270a83ad818d7de7bbe994673a49bf889450eda1f"
UPSTREAM="7f5853792ea7f04f75614661006d87fcf949f26d"

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def digest(x):
    return hashlib.sha256(canon(x)).hexdigest()

def check_frame(frame, mission):
    if type(frame) is not dict or set(frame)!={"image","direction","mission"} or frame["mission"]!=mission:
        raise ValueError("MG20_ORIGINAL_MISSION_REPLACED")
    if type(frame["direction"]) is not int or frame["direction"] not in range(4):
        raise ValueError("MG20_WRONG_ORIGINAL_HEADING")
    pixels=frame["image"]
    if (type(pixels) is not list or len(pixels)!=7 or any(
       type(row) is not list or len(row)!=7 or any(
       type(cell) is not list or len(cell)!=3 or any(
       type(value) is not int or not 0<=value<256 for value in cell)
       for cell in row) for row in pixels)):
        raise ValueError("MG20_ORIGINAL_PUBLIC_PIXELS_INVALID")

def original_source(path):
    obj=json.loads(path.read_text(encoding="utf-8"))
    if (obj.get("schema")!="itd02.mg17.original-source-qualification-replay.v1" or
        obj.get("scope")!="ENGINEERING_SOURCE_SMOKE_NO_NATIVE_TRAINING_NO_SCIENCE" or
        obj.get("source_commit")!=UPSTREAM or
        obj.get("canonical_trace_sha256")!=EXPECTED_SHA or
        type(obj.get("records")) is not list or len(obj["records"])!=8 or
        digest(obj["records"])!=EXPECTED_SHA):
        raise ValueError("MG20_ORIGINAL_QUARANTINED_SOURCE_SHA_OR_SCOPE")
    frame_list=[]
    summary=[]
    for family in FAMILIES:
        members=[r for r in obj["records"] if r.get("environment")==family]
        if len(members)!=2 or sorted(r.get("smoke_seed_not_eligible") for r in members)!=[917001,917003]:
            raise ValueError("MG20_SOURCE_FAMILY_OR_SEED_MISMATCH")
        for r in sorted(members,key=lambda t:t["smoke_seed_not_eligible"]):
            mission=r.get("original_mission")
            if type(mission) is not str or not mission:
                raise ValueError("MG20_NOT_ORIGINAL_MISSION")
            if family=="MiniGrid-DoorKey-6x6-v0":
                if mission!="use the key to open the door and then get to the goal":
                    raise ValueError("MG20_DOORKEY_ORIGINAL_MISSION_CHANGED")
            elif not mission.startswith("pick up the "):
                raise ValueError("MG20_COMPOSITION_ORIGINAL_MISSION_CHANGED")
            events=r.get("original_selected_source_events")
            if type(events) is not list or len(events)!=12 or digest(events)!=r.get("trace_sha256"):
                raise ValueError("MG20_QUARANTINED_SELECTED_TRACE_BAD")
            previous=None
            for i,e in enumerate(events,1):
                check_frame(e["before"],mission)
                check_frame(e["after"],mission)
                if (e.get("index")!=i or
                    type(e.get("source_action")) is not int or e["source_action"] not in range(7) or
                    e.get("policy")!="QUARANTINED_SOURCE_SMOKE_RANDOM_NOT_AGENT" or
                    digest(e["before"])!=e["before_sha256"] or
                    digest(e["after"])!=e["after_sha256"] or
                    type(e.get("terminated")) is not bool or
                    type(e.get("truncated")) is not bool or
                    type(e.get("original_reward")) is not float or
                    (previous is not None and previous!=e["before"])):
                    raise ValueError("MG20_ORIGINAL_SELECTED_ACTION_CONTINUITY")
                previous=e["after"]
                frame_list.append(e["before"])
            summary.append({"family":family,"seed_quarantined":r["smoke_seed_not_eligible"],
                            "original_mission":mission,"source_steps":12})
    if len(frame_list)!=96:
        raise ValueError("MG20_NOT_ALL_AUTHENTIC_PUBLIC_FRAMES")
    return obj,frame_list,summary

def native_probes(frames,go_executable):
    from research.native.itd02.mg19.genuine_mission_cells import MissionCells
    from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
    ygg_rows=[]
    for index,frame in enumerate(frames):
        native=MissionCells()
        adapter=OriginalMissionAdapter()
        adapter.reset_public(frame)
        native.start_session(adapter,"mg20-authentic-public-readonly-"+str(index),live=False)
        frozen=native.checkpoint()
        chosen=native.choose(frame)
        if (type(chosen) is not dict or
            type(chosen.get("action")) is not int or chosen["action"] not in range(7) or
            chosen.get("external_fallback") is not False or
            type(chosen.get("status")) is not str or not chosen["status"]):
            raise ValueError("MG20_YGG_NATIVE_READONLY_ACTION_ABSTAIN")
        if native.checkpoint()!=frozen or native.samples!=0 or adapter.events!=0:
            raise ValueError("MG20_YGG_QUARANTINED_MEMORY_WRITE")
        ygg_rows.append({"mission":frame["mission"],"action":chosen["action"],
                         "status":chosen["status"]})
    proc=subprocess.run([str(go_executable)],input=json.dumps(frames),text=True,
                        capture_output=True,timeout=120,check=False)
    if proc.returncode:
        raise ValueError("MG20_GO_NATIVE_READONLY_FAILURE:"+proc.stderr[-1000:])
    result=json.loads(proc.stdout)
    go_rows=result.get("rows")
    if (result.get("schema")!="itd02.mg20.go-original-mission-readonly.v1" or
        result.get("count")!=96 or result.get("no_memory_mutation") is not True or
        type(go_rows) is not list or len(go_rows)!=96):
        raise ValueError("MG20_GO_NATIVE_READONLY_96_ACTIONS_MISSING")
    for frame,row in zip(frames,go_rows):
        if (row.get("mission")!=frame["mission"] or
            type(row.get("action")) is not int or row["action"] not in range(7) or
            type(row.get("status")) is not str or not row["status"]):
            raise ValueError("MG20_GO_NATIVE_MISSION_CHANGED_OR_ABSTAINED")
    return ygg_rows,go_rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--second",type=Path,required=True)
    p.add_argument("--go-binary",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (frozen.get("schema")!=SCHEMA or
        frozen["source_archive"]["trace_sha256"]!=EXPECTED_SHA or
        frozen["source_archive"]["original_actions"]!=96 or
        frozen["source_archive"]["quarantined_smoke_seeds"]!=[917001,917003] or
        frozen["acceptance"]["no_native_fit_or_learn_or_commit_or_feedback"] is not True or
        frozen["acceptance"]["source_admission_is_not_learning"] is not True):
        raise ValueError("MG20_PREREG_DRIFT")
    first,frames,episodes=original_source(args.first)
    second,again,_=original_source(args.second)
    if first!=second or frames!=again:
        raise ValueError("MG20_ORIGINAL_TWO_SOURCE_PROCESS_MISMATCH")
    ygg,wing=native_probes(frames,args.go_binary)
    counts={}
    for name,rows in (("wingless_mg19",wing),("yggdrasil_mg19",ygg)):
        counts[name]=dict(collections.Counter(r["action"] for r in rows))
    proof={"schema":"itd02.mg20.original-quarantined-readonly-native-parity-receipt.v1",
           "classification":"MG20_AUTHENTIC_GENUINE_MISSION_READONLY_ADMITTED_NOT_SCIENCE",
           "source_mg17_complete_trace_sha256":EXPECTED_SHA,
           "read_only_quarantined_original_episodes":8,
           "read_only_quarantined_original_frames_per_model":96,
           "source_episode_missions":episodes,
           "native_actions":counts,
           "native_choice_sha256":{"wingless_mg19":digest(wing),"yggdrasil_mg19":digest(ygg)},
           "native_training_or_feedback_events":0,
           "new_original_source_steps":0,
           "scientific_first_use":False,"controller_modified":False,
           "canonical_receipt_sha256":digest({"wingless":wing,"yggdrasil":ygg})}
    args.output.write_text(json.dumps(proof,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG20_ORIGINAL_MISSION_READONLY_ENGINEERING_PASS",proof["canonical_receipt_sha256"])
    print("MG20_SOURCE_NATIVE_ACTION_COUNTS",json.dumps(counts,sort_keys=True))
if __name__=="__main__":
    main()

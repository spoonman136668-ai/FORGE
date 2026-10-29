#!/usr/bin/env python3
"""MG02: genuine MiniGrid env.step for original Wingless Go R8 and Ygg local R1.

Incremental native compatibility witness. Do not call this Yggdrasil R12,
scientific first use, shared memory, or accepted independent cognitive transfer.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

from k4r_minigrid_source import make_env, public, canon, sha
from k4u_native_minigrid import train_experiences, WingBridge
from mg01_paired_live_minigrid import (
    FIELDS, FAMILIES, SEEDS, public_wire, canonical_from_k4u, colony_input, exact,
)

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg02_r8_paired_live_preregistration.json"
PASS="MG02_WINGLESS_R8_AND_YGGDRASIL_R1_PAIRED_LIVE_ORIGINAL_MINIGRID__NO_SCIENCE"
FAIL="MG02_NATIVE_R8_OR_EQUAL_PUBLIC_BOUNDARY_BLOCKED__NO_SCIENCE"
SCHEMA="itd02.mg02.original-farama-wingless-r8-yggdrasil-r1-source-only.v1"

def protocol():
    d=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (d["schema"]!="itd02.mg02.original-minigrid-wingless-r8-yggdrasil-r1-paired-source-only.v1"
        or d["parent"]["head"]!="ffe3103fc451b248df23f118cb8ebeed85a02e8a"
        or d["source"]["farama_minigrid_commit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or tuple(d["protocol"]["selected_observation_fields"])!=FIELDS
        or d["protocol"]["legal_actions"]!=[0,1,2]
        or d["source"]["yggdrasil_r12_separate_not_admitted"]["status"]!="BLOCKED_FOR_MG01_SIX_FIELD_THREE_ACTION_CONTRACT"
        or d["classification"]["pass"]!=PASS):
        raise ValueError("MG02_FROZEN_PUBLIC_NATIVE_PROTOCOL_DRIFT")
    return d

def fit(executable,ymod):
    stream,records,starts,source_cpu=train_experiences()
    if len(starts)!=48 or len(stream)!=len(records) or len(stream)<500:
        raise ValueError("MG02_NOT_ORIGINAL_SOURCE_FIT")
    colony=ymod.GridColony()
    wing=WingBridge(executable)
    selected=hashlib.sha256()
    try:
        for n,event in enumerate(stream):
            before=canonical_from_k4u(event["before"])
            after=canonical_from_k4u(event["after"])
            action=event["action"]
            reward=float(event["reward"])
            terminal=event["terminal"]
            if type(action) is not int or action not in (0,1,2) or type(terminal) is not bool:
                raise ValueError("MG02_ORIGINAL_SELECTED_FIT_NOT_LEGAL")
            go=wing.request("learn",before=before,action=action,after=after,
                            reward=reward,terminal=terminal)
            if go.get("updates")!=n+1:
                raise ValueError("MG02_NATIVE_R8_FIT_NOT_ACCEPTED_ONCE")
            colony.observe(colony_input(ymod,before),action,
                           colony_input(ymod,after),reward,terminal)
            if colony.feedback_updates!=n+1:
                raise ValueError("MG02_ORIGINAL_YGG_LOCAL_FIT_NOT_ONCE")
            selected.update((canon({"before":before,"action":action,
                                    "after":after,"reward":reward,
                                    "terminal":terminal})+"\n").encode())
        go_bytes=wing.snapshot()
        ygg_bytes=colony.save()
        if len(go_bytes)>3*1024*1024 or len(ygg_bytes)>16384:
            raise ValueError("MG02_NATIVE_FIT_CHECKPOINT_OVER_BOUND")
    finally:
        wing.close()
    # Truly new native process, not the object used for fitting.
    cold_go=WingBridge(executable)
    try:
        reply=cold_go.request("load",state=base64.b64encode(go_bytes).decode("ascii"))
        if reply.get("updates")!=len(stream) or reply.get("steps")!=0:
            raise ValueError("MG02_R8_FRESH_PROCESS_FIT_RESTORE_MISMATCH")
        if cold_go.snapshot()!=go_bytes:
            raise ValueError("MG02_R8_FRESH_PROCESS_FIT_CHECKPOINT_CHANGED")
    finally:
        cold_go.close()
    cold_ygg=ymod.GridColony.restore(ygg_bytes)
    if cold_ygg.feedback_updates!=len(stream) or cold_ygg.save()!=ygg_bytes:
        raise ValueError("MG02_YGG_FIT_RESTORE_MISMATCH")
    return {"wingless":go_bytes,"yggdrasil":ygg_bytes,
            "count":len(stream),"selected_fit_sha256":selected.hexdigest(),
            "wingless_sha256":sha(go_bytes),"yggdrasil_sha256":sha(ygg_bytes),
            "source_fit_cpu_seconds_host_only":source_cpu}

def episode(family,seed,native,fit_state,go_binary,ymod):
    env=make_env(family)
    go=None
    colony=None
    try:
        observation,_=env.reset(seed=seed)
        state=public(observation)
        start_image=state["grid_sha256"]
        start_wire=public_wire(state)
        if native=="wingless_go_r8":
            go=WingBridge(go_binary)
            cold=go.request("load",state=base64.b64encode(fit_state["wingless"]).decode())
            if cold.get("updates")!=fit_state["count"] or cold.get("steps")!=0:
                raise ValueError("MG02_R8_EPISODE_FIT_RESTORE_FAILED")
            started=go.request("episode_start")
            if started.get("steps")!=0:raise ValueError("MG02_R8_BEGIN_EPISODE_NOT_RESET")
        elif native=="yggdrasil_r1_local_cells":
            colony=ymod.GridColony.restore(fit_state["yggdrasil"])
            if colony.feedback_updates!=fit_state["count"]:
                raise ValueError("MG02_YGG_EPISODE_FIT_RESTORE_FAILED")
        else:
            raise ValueError("MG02_INVALID_NATIVE_ROLE")
        steps=[]
        for i in range(96 if family=="empty" else 192):
            before=public_wire(state)
            if go is not None:
                answer=go.request("choose",before=before)
                action=answer.get("action")
            else:
                action=colony.choose(colony_input(ymod,before))
            if type(action) is not int or action not in (0,1,2):
                raise ValueError("MG02_ILLEGAL_PUBLIC_NATIVE_ACTION")
            # Only ONE real upstream env.step() per actually chosen action.
            nxt_obs,reward,terminated,truncated,_=env.step(action)
            nxt=public(nxt_obs,state["goal"])
            after=public_wire(nxt)
            if (type(terminated) is not bool or type(truncated) is not bool
                or type(reward) not in (int,float)):
                raise ValueError("MG02_INVALID_ORIGINAL_STEP_RESULT")
            terminal=bool(terminated or truncated)
            if go is not None:
                # R8's native online consequence learner uses selected
                # before/action/after public dynamics. Reward is still logged
                # unchanged but not consumed by the native R8 Feedback API.
                ack=go.request("feedback",before=before,action=action,after=after,
                               reward=float(reward),terminal=terminal)
                if ack.get("steps")!=i+1 or ack.get("updates")!=fit_state["count"]:
                    raise ValueError("MG02_R8_SELECTED_FEEDBACK_CUSTODY_NOT_ONCE")
                updates=i+1
            else:
                colony.observe(colony_input(ymod,before),action,
                               colony_input(ymod,after),float(reward),terminal)
                updates=colony.feedback_updates-fit_state["count"]
                if updates!=i+1:
                    raise ValueError("MG02_YGG_SELECTED_FEEDBACK_NOT_ONCE")
            steps.append({
                "ordinal":i+1,
                "before_public_image_sha256":state["grid_sha256"],
                "before_six_public_fields":before,
                "actual_selected_action":action,
                "after_public_image_sha256":nxt["grid_sha256"],
                "after_six_public_fields":after,
                "actual_original_reward":float(reward),
                "terminated":terminated,"truncated":truncated,
                "local_native_online_feedback_count":updates,
                "wingless_r8_uses_selected_reward_for_online_learning":False if go is not None else None
            })
            state=nxt
            if terminal:break
        last=go.snapshot() if go is not None else colony.save()
        if (len(last)>3*1024*1024 if go is not None else len(last)>16384):
            raise ValueError("MG02_LIVE_CHECKPOINT_OVER_BOUND")
        if go is not None:
            cold_go=WingBridge(go_binary)
            try:
                reply=cold_go.request("load",state=base64.b64encode(last).decode())
                if reply.get("steps")!=len(steps) or reply.get("updates")!=fit_state["count"]:
                    raise ValueError("MG02_R8_FINAL_COLD_RESTORE_LOST_LIVE_CREDIT")
                if cold_go.snapshot()!=last:
                    raise ValueError("MG02_R8_FINAL_COLD_RESTORE_SHA_CHANGED")
            finally:
                cold_go.close()
        else:
            restore=ymod.GridColony.restore(last)
            if (restore.feedback_updates!=fit_state["count"]+len(steps)
                or restore.save()!=last):
                raise ValueError("MG02_YGG_FINAL_COLD_RESTORE_NOT_EQUAL")
        return {
            "family":family,"seed_evaluator_only":seed,
            "native_model":native,
            "initial_full_original_public_image_sha256":start_image,
            "initial_exact_six_public_fields":start_wire,
            "true_original_step_count":len(steps),
            "native_final_checkpoint_sha256":sha(last),
            "native_final_checkpoint_bytes":len(last),
            "actual_selected_public_consequences":steps,
        }
    finally:
        env.close()
        if go is not None:go.close()

def run(go_binary,ygg_src):
    protocol()
    if not (ygg_src/"native_policy.py").is_file():
        raise ValueError("MG02_ORIGINAL_YGG_SOURCE_NOT_PRESENT")
    if str(ygg_src) not in sys.path:sys.path.insert(0,str(ygg_src))
    import native_policy as ymod
    f=fit(go_binary,ymod)
    paired=[]
    for family in FAMILIES:
        for seed in SEEDS:
            pair=[
                episode(family,seed,native,f,go_binary,ymod)
                for native in ("wingless_go_r8","yggdrasil_r1_local_cells")
            ]
            if (pair[0]["initial_full_original_public_image_sha256"]!=
                pair[1]["initial_full_original_public_image_sha256"] or
                pair[0]["initial_exact_six_public_fields"]!=
                pair[1]["initial_exact_six_public_fields"]):
                raise ValueError("MG02_PAIRED_ORIGINAL_WORLD_START_NOT_IDENTICAL")
            paired.extend(pair)
    if len(paired)!=8 or any(not e["actual_selected_public_consequences"] for e in paired):
        raise ValueError("MG02_MISSING_AUTHENTIC_LIVE_EXPOSURE")
    canonical={"schema":SCHEMA,
        "original_Farama_git_commit":"7f5853792ea7f04f75614661006d87fcf949f26d",
        "native_source":protocol()["source"],
        "identical_actual_selected_fit_history_sha":f["selected_fit_sha256"],
        "both_independent_native_fit_feedback_counts":f["count"],
        "frozen_fit_wingless_r8_checkpoint_sha":f["wingless_sha256"],
        "frozen_fit_ygg_r1_checkpoint_sha":f["yggdrasil_sha256"],
        "original_environment_live_pairings":paired,
        "r12_original_sixfield_contract_compatible":False,
        "independent_models_receive_same_initial_public_six_fields":True,
        "actual_original_env_step":True,
        "no_unselected_rewards_shared":True,
        "native_original_sources_untouched":True}
    trace_sha=sha(canon(canonical).encode())
    return {"schema":SCHEMA,"classification":PASS,
        "scientific_first_use":False,"accepted_model_promoted":False,
        "FORGE_controller_modified":False,
        "r12_currently_connected":False,
        "authentic_original_source":True,
        "original_live_episode_count":8,
        "both_native_fit_feedback_count":f["count"],
        "same_six_field_public_interface":True,
        "canonical_original_trace_sha256":trace_sha,
        "canonical_original_evidence":canonical}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-r8",type=Path,required=True)
    parser.add_argument("--ygg-r1",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    t=time.perf_counter()
    try:
        result=run(args.wingless_r8,args.ygg_r1)
        result["wall_seconds_host_only"]=time.perf_counter()-t
    except Exception as error:
        result={"schema":SCHEMA,"classification":FAIL,
            "scientific_first_use":False,
            "error_type":type(error).__name__,"error":str(error),
            "trace_tail":traceback.format_exc().splitlines()[-10:],
            "wall_seconds_host_only":time.perf_counter()-t}
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG02_CLASSIFICATION",result["classification"])
    print("MG02_PAIRED_ORIGINAL_EPISODES",result.get("original_live_episode_count",0))
    print("MG02_SELECTED_PUBLIC_FIT_PER_MODEL",result.get("both_native_fit_feedback_count",0))
    print("MG02_CANONICAL_AUTHENTIC_TRACE_SHA",result.get("canonical_original_trace_sha256","NONE"))
    if result["classification"]!=PASS:print("MG02_BLOCKER",result.get("error_type"),result.get("error"))
    return 0 if result["classification"]==PASS else 1

if __name__=="__main__":
    raise SystemExit(main())

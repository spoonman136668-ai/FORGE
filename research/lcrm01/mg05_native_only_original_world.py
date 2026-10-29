#!/usr/bin/env python3
"""MG05 authentic Farama DoorKey, independent native-only policy actions.

Original public image/direction/mission only. Real source outcomes, no external
live collector, no hand-coded mission-stage objective. Development / NO SCIENCE.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import resource
import time
import traceback
from pathlib import Path

from k4u_native_minigrid import WingBridge
from k4r_minigrid_source import canon, sha
import mg03_equal_public_doorkey_live as original
import mg04_public_effect_native_agency as preceding

FROZEN=Path(__file__).resolve().parent/"mg05_native_only_preregistration.json"
SCHEMA="itd02.mg05.authentic-native-only-seven-action.original-source.v1"
PASS="MG05_NATIVE_ONLY_AUTHENTIC_SEVEN_ACTION_SELECTED_FEEDBACK_VERIFIED__NO_SCIENCE"
NEG="MG05_NATIVE_ONLY_ABSTAINED_OR_GOAL_TRANSFER_NEGATIVE__NO_SCIENCE"
FAIL="MG05_SOURCE_OR_NATIVE_ACTION_PROVENANCE_BLOCKED__NO_SCIENCE"
ROLES=("wingless_go_dk8u","yggdrasil_r13_on_r11","uniform_seven_action_random")


def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (p.get("schema")!="itd02.mg05.authentic-doorkey-native-only-observational-development.v1"
        or p["parent"]["head"]!="f4e08d27776248f6f075db6fb93d3f4195bd941c"
        or p["FIT"]["samples"]!=1664
        or p["DEV"]["arms"]!=list(ROLES)
        or p["DEV"]["seeds"]!=[65301,65303,65307]
        or p["DEV"]["cap_per_episode"]!=256
        or p["DEV"]["no_external_collector_at_runtime"] is not True):
        raise ValueError("MG05_FROZEN_PUBLIC_OR_ROLE_CONTRACT_DRIFT")
    return p


def one(role,seed,trained,binary,p):
    gym,owner,Cell,_,collector,conventional=preceding.get_modules()
    from research.native.itd02.r13.explore_choice import propose_native_action
    env=gym.make(p["public"]["environment"])
    adapter=owner.DoorKeyPublicAdapter()
    wing=None; ygg=None; control=None
    try:
        raw,_=env.reset(seed=seed)
        start=original.normalize(collector,owner,raw)
        start_hash=owner.digest(start)
        adapter.reset_public(start)
        if role==ROLES[0]:
            wing=WingBridge(binary)
            ack=wing.request("load",state=base64.b64encode(trained["native_go"]).decode("ascii"))
            if ack.get("updates")!=1664 or wing.snapshot()!=trained["native_go"]:
                raise ValueError("MG05_GO_INDEPENDENT_COLD_FIT_INVALID")
            wing.request("begin_episode")
        elif role==ROLES[1]:
            ygg=Cell.restore(trained["native_ygg"])
            if ygg.samples!=1664 or ygg.checkpoint()!=trained["native_ygg"]:
                raise ValueError("MG05_YGG_INDEPENDENT_COLD_FIT_INVALID")
            ygg.start_session(adapter,"mg05-original-native-"+str(seed))
        elif role==ROLES[2]:
            control=conventional.Control.restore(trained["conventional"])
            if control.samples!=1664:
                raise ValueError("MG05_RANDOM_CONTROL_SOURCE_FIT_INVALID")
        else:raise ValueError("MG05_ROLE_NOT_FROZEN")
        rng=random.Random(p["DEV"]["random_baseline_seed_offset"]+seed)
        events=[];proposals=abstentions=0
        key_changes=door_changes=goals=0
        for i in range(p["DEV"]["cap_per_episode"]):
            before=original.normalize(collector,owner,raw)
            if adapter.current!=before:
                raise ValueError("MG05_PUBLIC_STATE_DRIFT")
            if wing is not None:
                decision=wing.request("choose",before=before)
                action=decision.get("action")
                status=decision.get("status")
                actor="NATIVE_WINGLESS_GO_DK8U"
            elif ygg is not None:
                decision=propose_native_action(ygg,before)
                action=decision["action"]
                status=decision["status"]
                actor="NATIVE_YGGDRASIL_LOCAL_R13"
            else:
                action=rng.randrange(7)
                status="CONVENTIONAL_UNIFORM_SEVEN_ACTION_RANDOM"
                actor="EXPLICIT_CONVENTIONAL_RANDOM_CONTROL"
            if role!=ROLES[2] and (action is None or status not in (
                "SELECT_NATIVE_OBSERVED_POSITIVE_REWARD","SELECT_NATIVE_LEAST_OBSERVED_ACTION")):
                abstentions+=1
                # No rescue. No env.step for an abstention; this is a negative.
                break
            if type(action) is not int or action not in range(7):
                raise ValueError("MG05_ILLEGAL_NATIVE_OR_CONTROL_ACTION")
            if wing is not None:
                wing.request("commit",before=before,action=action)
            if adapter.submit(action)!=action:
                raise ValueError("MG05_ORIGINAL_ACTION_CHANGED")
            next_raw,reward,terminated,truncated,_=env.step(action)
            after=original.normalize(collector,owner,next_raw)
            consequence=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if wing is not None:
                ack=wing.request("feedback",before=before,action=action,after=after,
                         reward=float(reward),terminal=bool(terminated or truncated))
                count=ack.get("updates",0)-1664
                if count!=i+1 or ack.get("live",0)!=i+1:
                    raise ValueError("MG05_GO_SELECTED_FEEDBACK_DRIFT")
            elif ygg is not None:
                receipt=ygg.learn_selected(adapter)
                count=ygg.samples-1664
                if count!=i+1 or receipt["sample_index"]!=1664+i+1:
                    raise ValueError("MG05_YGG_SELECTED_FEEDBACK_DRIFT")
            else:
                control.learn(consequence)
                count=control.samples-1664
                if count!=i+1:
                    raise ValueError("MG05_CONVENTIONAL_SELECTED_FEEDBACK_DRIFT")
            proposals+=1
            key_changes+=int(consequence["visible_key_pickup"])
            door_changes+=int(consequence["visible_door_opened"])
            goals+=int(float(reward)>0)
            events.append({
                "ordinal":i+1,"public_before":before,"public_after":after,
                "public_before_sha":owner.digest(before),
                "public_after_sha":owner.digest(after),
                "action_origin":actor,"choice_status":status,
                "model_selected_action":action,
                "actual_source_action":action,
                "actual_original_reward":float(reward),
                "source_visible_pickup":bool(consequence["visible_key_pickup"]),
                "source_visible_door_open":bool(consequence["visible_door_opened"]),
                "terminated":bool(terminated),"truncated":bool(truncated),
                "selected_feedback_delta":count})
            raw=next_raw
            if terminated or truncated:break
        checkpoint=(wing.snapshot() if wing is not None else
                    (ygg.checkpoint() if ygg is not None else control.checkpoint()))
        if wing is not None:
            restored=WingBridge(binary)
            try:
                ack=restored.request("load",state=base64.b64encode(checkpoint).decode("ascii"))
                if ack.get("updates")!=1664+len(events) or restored.snapshot()!=checkpoint:
                    raise ValueError("MG05_GO_COLD_SELECTED_CHECKPOINT_DRIFT")
            finally:restored.close()
        elif ygg is not None:
            copy=Cell.restore(checkpoint)
            if copy.samples!=1664+len(events) or copy.checkpoint()!=checkpoint:
                raise ValueError("MG05_YGG_COLD_SELECTED_CHECKPOINT_DRIFT")
        else:
            copy=conventional.Control.restore(checkpoint)
            if copy.samples!=1664+len(events) or copy.checkpoint()!=checkpoint:
                raise ValueError("MG05_CONVENTIONAL_COLD_SELECTED_CHECKPOINT_DRIFT")
        if proposals!=len(events):
            raise ValueError("MG05_NATIVE_PROPOSAL_ACCOUNTING_DRIFT")
        return {"role":role,"seed_evaluator_only":seed,"start_exact_public_sha":start_hash,
                "native_or_control_actions":proposals,"native_abstentions":abstentions,
                "external_collector_actions":0,"original_source_steps":len(events),
                "source_key_pickups":key_changes,"source_door_openings":door_changes,
                "source_goal_rewards":goals,"cold_checkpoint_sha256":sha(checkpoint),
                "real_original_selected_events":events}
    finally:
        env.close()
        if wing is not None:wing.close()


def run(binary,p):
    # Original 1664 source transitions, source-only external FIT collector.
    # NOT a runtime policy; no collector action during any MG05 live episode.
    trained=preceding.fit(binary,preceding.freeze())
    if trained["samples"]!=1664:
        raise ValueError("MG05_SOURCE_IDENTICAL_FIT_MISSING")
    rows=[]
    for seed in p["DEV"]["seeds"]:
        trio=[one(role,seed,trained,binary,p) for role in ROLES]
        if len({r["start_exact_public_sha"] for r in trio})!=1:
            raise ValueError("MG05_UNEQUAL_ORIGINAL_PUBLIC_RESET")
        rows.extend(trio)
    if len(rows)!=9:
        raise ValueError("MG05_INCOMPLETE_ORIGINAL_WORLD_DESIGN")
    summary={}
    for role in ROLES:
        r=[x for x in rows if x["role"]==role]
        summary[role]={
            "episodes":len(r),
            "native_or_control_actions":sum(x["native_or_control_actions"] for x in r),
            "original_source_steps":sum(x["original_source_steps"] for x in r),
            "native_abstentions":sum(x["native_abstentions"] for x in r),
            "external_collector_actions":0,
            "source_key_pickups":sum(x["source_key_pickups"] for x in r),
            "source_door_openings":sum(x["source_door_openings"] for x in r),
            "source_goal_rewards":sum(x["source_goal_rewards"] for x in r)}
    native_enough=all(summary[role]["native_or_control_actions"]>0 and
         summary[role]["native_abstentions"]==0 for role in ROLES[:2])
    classification=PASS if native_enough else NEG
    evidence={"original_farama":p["source"]["farama_commit"],
        "original_public_eight_by_eight_doorkey":True,
        "same_1664_original_fit_selected_sha256":trained["source_history_sha256"],
        "separate_frozen_checkpoints_sha256":trained["checkpoint_sha256"],
        "original_source_action_records":rows,
        "no_external_live_collector":True,
        "native_wingless_is_new_DK8U_not_R8":True,
        "native_yggdrasil_is_R13_on_original_R11":True,
        "random_is_explicit_conventional_control":True}
    return {"schema":SCHEMA,"classification":classification,"scientific_first_use":False,
        "accepted_model_promoted":False,"FORGE_controller_modified":False,
        "original_wingless_R8_modified":False,"original_yggdrasil_R12_modified":False,
        "same_1664_source_fit":trained["samples"],"source_origin_summary":summary,
        "canonical_evidence_sha256":sha(canon(evidence).encode()),"canonical_evidence":evidence}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk8u-go",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    before=time.perf_counter();cpu=time.process_time()
    try: report=run(args.wingless_dk8u_go,freeze())
    except Exception as exc:
        report={"schema":SCHEMA,"classification":FAIL,"scientific_first_use":False,
            "error_type":type(exc).__name__,"error":str(exc),
            "trace_tail":traceback.format_exc().splitlines()[-16:]}
    report["host_wall_seconds"]=round(time.perf_counter()-before,6)
    report["python_only_cpu_seconds"]=round(time.process_time()-cpu,6)
    report["python_host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report["go_child_CPU_included_in_python_cpu"]=False
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("MG05_CLASSIFICATION",report["classification"])
    print("MG05_SOURCE_SHA",report.get("canonical_evidence_sha256","NONE"))
    print("MG05_NATIVE_ONLY_COUNTS",json.dumps(report.get("source_origin_summary",{}),sort_keys=True))
    if report["classification"]==FAIL:
        print("MG05_BLOCKER",report.get("error_type"),report.get("error"))
    return int(report["classification"]==FAIL)

if __name__=="__main__":
    raise SystemExit(main())

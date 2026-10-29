#!/usr/bin/env python3
"""MG21 source-only experiment: shared authentic FIT; cold native probe; not science.

The experiment is descriptive: action counts, observed source returns, exact
public-state diversity, episode termination, and cold checkpoint evidence.
No hidden goal, planner, reward shaping, capacity-match, or sealed evaluation.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path

import gymnasium as gym
import minigrid

from mg17_original_family_source_qual import attest_source,frozen,public,digest
from mg21_native_retention_actors import ROLES,family_fit,prepare
from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
from research.native.itd02.mg19.genuine_mission_cells import MissionCells

ROOT=Path(__file__).resolve().parent
CONTRACT=ROOT/"mg21_original_source_shared_fit_prereg.json"
UPSTREAM="7f5853792ea7f04f75614661006d87fcf949f26d"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")


def contract():
    p=json.loads(CONTRACT.read_text(encoding="utf-8"))
    w=p["world"];e=p["experiment"]
    if (p["schema"]!="itd02.mg21.original-source-shared-fit-cold-retention-engineering.v1" or
        p["phase"]!="FROZEN_BEFORE_ENGINEERING_EXECUTABLE__NO_SCIENTIFIC_FIRST_USE" or
        p["parent"]["Farama_MiniGrid"]!=UPSTREAM or
        p["parent"]["FORGE_MG20_HEAD"]!="be533627e9cbc7f35314257ceadbf21f5e873d4e" or
        tuple(w["families"])!=FAMILIES or
        (w["quarantined_fit_seed"],w["quarantined_probe_seed"])!=(918301,918303) or
        (w["original_fit_cap"],w["original_eval_cap"])!=(24,24) or
        w["action_space"]!=list(range(7)) or
        not w["permanently_disqualify_both_seeds_from_scientific_fit_dev_sealed"] or
        not w["no_hidden_map_or_goal_pos"] or
        not all(v for v in e.values() if type(v) is bool) or
        not all(p["authority"].values())):
        raise ValueError("MG21_FROZEN_SOURCE_PROTOCOL_DRIFT")
    return p


def select(role,actor,before):
    if role.startswith("go_"):
        msg=actor.request("choose",before=before)
        action=msg.get("action");status=msg.get("status")
    elif role.startswith("ygg_"):
        msg=actor.choose(before)
        if msg.get("external_fallback"):
            raise ValueError("MG21_UNAUTHORIZED_EXTERNAL_DECISION")
        action=msg.get("action");status=msg.get("status")
    elif role.startswith("tabular_"):
        action,status=actor.choose(before)
    else:
        action=actor.randrange(7)
        status="UNASSISTED_UNTRAINED_ORIGINAL_RANDOM_CONTROL"
    if type(action) is not int or action not in range(7) or not status:
        raise ValueError("MG21_INVALID_ORACLE_INSTEAD_OF_SELECTED_ACTION")
    return action,status


def probe(family,role,seed,cap,go_exe,fit):
    env=gym.make(family)
    actor,adapter=prepare(role,fit,go_exe,family)
    try:
        if getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG21_ORIGINAL_ACTION_SPACE_DRIFT")
        obs,_=env.reset(seed=seed);before=public(obs);first=before
        if role.startswith("go_"):
            actor.request("begin_episode")
        if role.startswith("ygg_"):
            adapter.reset_public(first)
            actor.start_session(adapter,"mg21-probe:"+family,live=True)
        fit_count=len(fit) if role.endswith("_fit") else 0
        selected=[]
        for index in range(1,cap+1):
            action,status=select(role,actor,before)
            if role.startswith("go_"):
                actor.request("commit",before=before,action=action)
            if role.startswith("ygg_") and adapter.submit(action)!=action:
                raise ValueError("MG21_SOURCE_ACTION_SUBSTITUTED")
            after_raw,reward,terminated,truncated,_=env.step(action)
            after=public(after_raw)
            if (after["mission"]!=first["mission"] or
                type(terminated) is not bool or type(truncated) is not bool or
                not math.isfinite(float(reward))):
                raise ValueError("MG21_ORIGINAL_SOURCE_CONSEQUENCE_INVALID")
            terminal=terminated or truncated
            if role.startswith("go_"):
                ack=actor.request("feedback",before=before,action=action,
                                  after=after,reward=float(reward),terminal=terminal)
                count=ack.get("updates")
            elif role.startswith("ygg_"):
                adapter.complete(after,float(reward),terminated,truncated)
                actor.learn_selected(adapter,before,after)
                count=actor.samples
            elif role.startswith("tabular_"):
                actor.learn(before,action,after,float(reward),terminal)
                count=actor.samples
            else:
                count=None
            if role!="random" and count!=fit_count+index:
                raise ValueError("MG21_SELECTED_SOURCE_ACTION_COUNT_DRIFT")
            selected.append({"index":index,"before_sha256":digest(before),
                             "public_before":before,"chosen_action":action,
                             "native_status":status,"public_after":after,
                             "after_sha256":digest(after),
                             "source_reward":float(reward),
                             "terminated":terminated,"truncated":truncated,
                             "cumulative_native_source_events":count})
            before=after
            if terminal:break
        if not selected or len(selected)>cap:raise ValueError("MG21_EMPTY_PROBE")
        if role.startswith("go_"):
            snap=actor.snapshot()
            size=len(snap)
            checkpoint=hashlib.sha256(snap).hexdigest()
        elif role.startswith("ygg_") or role.startswith("tabular_"):
            snap=actor.checkpoint()
            size=len(snap)
            checkpoint=hashlib.sha256(snap).hexdigest()
        else:
            size=0;checkpoint=None
        if role.startswith("ygg_"):
            if MissionCells.restore(snap).checkpoint()!=snap:
                raise ValueError("MG21_PROBE_NATIVE_RETENTION_COLD_DRIFT")
        if role.startswith("tabular_"):
            from mg21_original_tabular_control import Tabular
            if Tabular.restore(snap).checkpoint()!=snap:
                raise ValueError("MG21_PROBE_CONTROL_RETENTION_COLD_DRIFT")
        if role.startswith("go_"):
            from mg18_native_mission_boundary_audit import WingBridge
            cold=WingBridge(go_exe)
            try:
                ack=cold.request("load",state=base64.b64encode(snap).decode("ascii"))
                if ack.get("updates")!=fit_count+len(selected) or cold.snapshot()!=snap:
                    raise ValueError("MG21_PROBE_GO_RETENTION_COLD_DRIFT")
            finally:cold.close()
        returns=sum(event["source_reward"] for event in selected)
        seen=set(x["before_sha256"] for x in selected)
        seen.add(selected[-1]["after_sha256"])
        return {"family":family,"role":role,"quarantine_probe_seed":seed,
                "initial_public_sha256":digest(first),"original_mission":first["mission"],
                "fit_source_samples":fit_count,"source_probe_steps":len(selected),
                "source_episode_terminated":selected[-1]["terminated"],
                "source_episode_truncated":selected[-1]["truncated"],
                "observed_reward_sum":returns,"public_state_diversity":len(seen),
                "native_source_events_at_end":count,
                "checkpoint_sha256":checkpoint,"checkpoint_bytes":size,
                "selected_actions":selected,"source_trace_sha256":digest(selected)}
    finally:
        if role.startswith("go_"):actor.close()
        env.close()


def run(original_root,native_go):
    p=contract()
    if not Path(minigrid.__file__).resolve().is_relative_to(original_root.resolve()):
        raise ValueError("MG21_FARAMA_MODULE_NOT_PINNED")
    witness=frozen()
    attest_source(original_root,witness)
    registry={x["id"]:x["entry_point"] for x in witness["families"]}
    data=[]
    for family in FAMILIES:
        if gym.spec(family).entry_point!=registry[family]:
            raise ValueError("MG21_REAL_ORIGINAL_REGISTRY_DRIFT")
        initial,fit=family_fit(gym,family,p["world"]["quarantined_fit_seed"],
                               p["world"]["original_fit_cap"])
        if any(e["before"]["mission"]!=initial["mission"] or
               e["after"]["mission"]!=initial["mission"] for e in fit):
            raise ValueError("MG21_FIT_SOURCE_MISSION_MISMATCH")
        arm=[]
        for role in ROLES:
            arm.append(probe(family,role,p["world"]["quarantined_probe_seed"],
                             p["world"]["original_eval_cap"],native_go,fit))
        if len(set(x["initial_public_sha256"] for x in arm))!=1:
            raise ValueError("MG21_ORIGINAL_PROBE_INITIAL_STATE_UNEQUAL")
        data.append({"family":family,"fit_seed":p["world"]["quarantined_fit_seed"],
                     "fit_start_sha256":digest(initial),
                     "fit_events":fit,"fit_original_source_sha256":digest(fit),
                     "probe_actors":arm,
                     "admission":"ENGINEERING_ONLY_NO_GENERALIZATION_CLAIM"})
    return {"schema":"itd02.mg21.original-source-shared-fit-cold-probe.v1",
            "status":"ENGINEERING_QUARANTINED_NO_SCIENCE",
            "upstream":UPSTREAM,
            "go_native_head":p["parent"]["Wingless_MG19"],
            "ygg_native_head":p["parent"]["Yggdrasil_MG19"],
            "fit_probe_seeds_permanently_quarantined":[918301,918303],
            "arms":list(ROLES),"families":data,
            "canonical_sha256":digest(data)}


def compare(a,b):
    first=json.loads(Path(a).read_text(encoding="utf-8"))
    second=json.loads(Path(b).read_text(encoding="utf-8"))
    if (first!=second or len(first["families"])!=4 or
        first["schema"]!="itd02.mg21.original-source-shared-fit-cold-probe.v1" or
        first["canonical_sha256"]!=digest(first["families"]) or
        any(len(f["probe_actors"])!=7 for f in first["families"])):
        raise ValueError("MG21_INDEPENDENT_COLD_NATIVE_REPLAY_MISMATCH")
    print("MG21_ORIGINAL_SOURCE_SHARED_FIT_COLD_RETENTION_REPLAY_PASS_NOT_SCIENCE "+first["canonical_sha256"])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--native-go",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--compare",nargs=2)
    a=ap.parse_args()
    if a.compare:
        compare(*a.compare);return
    if not (a.source_root and a.native_go and a.output):
        ap.error("provide pinned original root, native Go and output")
    result=run(a.source_root,a.native_go)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("MG21_ORIGINAL_WORLD_COLD_FIT_VS_UNTRAINED_ADMISSION_PASS_NO_SCIENCE "+result["canonical_sha256"])


if __name__=="__main__":main()

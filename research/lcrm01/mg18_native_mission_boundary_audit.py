#!/usr/bin/env python3
"""MG18 original MiniGrid genuine-mission native admission audit.

This is an engineering selected-action/source-custody test on one *quarantined*
seed. Unsupported mission strings must FAIL CLOSED: no environment step for
those candidates, no fabricated cross-family skill or generalization claim.
"""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path

import gymnasium as gym
import minigrid
from k4u_native_minigrid import WingBridge
from mg17_original_family_source_qual import attest_source, public, canonical, digest
from research.native.itd02.r18.mission_cells import OriginalMissionAdapter
from research.native.itd02.r20.state_credit_cells import StateCreditCells

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "mg18_native_mission_admission_prereg.json"
EXPECTED_SOURCE = "7f5853792ea7f04f75614661006d87fcf949f26d"
KNOWN = "use the key to open the door and then get to the goal"
TARGETS = (
    "MiniGrid-DoorKey-6x6-v0",
    "MiniGrid-UnlockPickup-v0",
    "MiniGrid-BlockedUnlockPickup-v0",
    "MiniGrid-KeyCorridorS3R1-v0",
)


def prereg():
    data = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert data["schema"] == "itd02.mg18.native-mission-admission-boundary.v1"
    assert data["status"] == "FROZEN_PROSPECTIVE_BEFORE_EXECUTABLE_BOUNDARY_AUDIT"
    assert data["ancestry"]["original_minigrid"] == EXPECTED_SOURCE
    assert data["engineering"]["seed"] == 918001
    assert data["engineering"]["per_candidate_max_actions"] == 1
    assert data["engineering"]["engineering_seed_permanently_ineligible_for_fit_dev_sealed"]
    assert tuple(data["mission_contract"]["candidate_families"]) == TARGETS
    assert data["mission_contract"]["never_substitute_door_key_or_goal_mission_for_new_environment"]
    assert data["mission_contract"]["require_exact_original_source_mission"]
    assert all(data["authority"].values())
    groups = data["prospective_cohort_reservations"]
    sets = [set(groups[x]["seeds"]) for x in ("FIT", "DEV", "SEALED")]
    assert not (sets[0] & sets[1] or sets[1] & sets[2] or sets[0] & sets[2])
    assert not any(918001 in ss or 917001 in ss or 917003 in ss for ss in sets)
    return data


def source_reset(name, seed):
    env = gym.make(name)
    raw, _ = env.reset(seed=seed)
    return env, public(raw)


def source_step(env, before, chosen):
    raw, reward, terminated, truncated, _ = env.step(chosen)
    after = public(raw)
    if before["mission"] != after["mission"]:
        raise ValueError("MG18_ORIGINAL_MISSION_CHANGED")
    return {
        "before": before,
        "selected_native_action": chosen,
        "after": after,
        "source_reward": float(reward),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "before_sha256": digest(before),
        "after_sha256": digest(after),
    }


def wingless(name, go_bin, seed):
    env, before = source_reset(name, seed)
    bridge = WingBridge(go_bin)
    try:
        response = bridge.request("begin_episode")
        if response.get("updates", 0) != 0:
            raise ValueError("MG18_WINGLESS_UNEXPECTED_PRIOR_SAMPLES")
        try:
            suggestion = bridge.request("choose", before=before)
        except ValueError as exc:
            if before["mission"] == KNOWN or "DK16_BAD_MISSION" not in str(exc):
                raise
            return {"role": "Wingless_DK16", "environment": name,
                    "mission": before["mission"], "original_before_sha256": digest(before),
                    "status": "NATIVE_EXPLICIT_MISSION_REJECTION_NO_SOURCE_STEP",
                    "native_error": "DK16_BAD_MISSION", "steps": 0}
        if before["mission"] != KNOWN:
            raise ValueError("MG18_UNEXPECTED_WINGLESS_ADMISSION_OF_NEW_MISSION")
        action = suggestion.get("action")
        if type(action) is not int or action not in range(7):
            raise ValueError("MG18_GO_NON_NATIVE_ACTION")
        bridge.request("commit", before=before, action=action)
        event = source_step(env, before, action)
        result = bridge.request("feedback", before=before, action=action,
                                after=event["after"], reward=event["source_reward"],
                                terminal=event["terminated"] or event["truncated"])
        if result["updates"] != 1:
            raise ValueError("MG18_GO_SOURCE_EVENT_COUNT")
        snap = bridge.snapshot()
        cold = WingBridge(go_bin)
        try:
            if cold.request("load", state=base64.b64encode(snap).decode())["updates"] != 1:
                raise ValueError("MG18_GO_COLD_UPDATE_COUNT")
            if cold.snapshot() != snap:
                raise ValueError("MG18_GO_COLD_SOURCE_CUSTODY")
        finally:
            cold.close()
        return {"role": "Wingless_DK16", "environment": name,
                "mission": before["mission"], "status": "ONE_GENUINE_NATIVE_SELECTED_SOURCE_EVENT",
                "native_choice_status": suggestion["status"],
                "steps": 1, "source_event": event,
                "checkpoint_sha256": __import__("hashlib").sha256(snap).hexdigest()}
    finally:
        bridge.close()
        env.close()


def yggdrasil(name, seed):
    env, before = source_reset(name, seed)
    try:
        agent = StateCreditCells()
        adapter = OriginalMissionAdapter()
        try:
            adapter.reset_public(before)
        except ValueError as exc:
            if before["mission"] == KNOWN or "R18_UNREGISTERED_ORIGINAL_MISSION" not in str(exc):
                raise
            return {"role": "Yggdrasil_R20", "environment": name,
                    "mission": before["mission"], "original_before_sha256": digest(before),
                    "status": "NATIVE_EXPLICIT_MISSION_REJECTION_NO_SOURCE_STEP",
                    "native_error": "R18_UNREGISTERED_ORIGINAL_MISSION", "steps": 0}
        if before["mission"] != KNOWN:
            raise ValueError("MG18_UNEXPECTED_YGG_ADMISSION_OF_NEW_MISSION")
        agent.start_session(adapter, "mg18-genuine-source-" + name, live=True)
        suggestion = agent.choose(before)
        if suggestion["external_fallback"] or type(suggestion["action"]) is not int:
            raise ValueError("MG18_YGG_UNTRUSTED_SOURCE_ACTION")
        action = suggestion["action"]
        if action not in range(7) or adapter.submit(action) != action:
            raise ValueError("MG18_YGG_ACTION_REMAP")
        event = source_step(env, before, action)
        adapter.complete(event["after"], event["source_reward"],
                         event["terminated"], event["truncated"])
        agent.learn_selected(adapter, before, event["after"])
        if agent.samples != 1:
            raise ValueError("MG18_YGG_SOURCE_SELECTED_UPDATE_COUNT")
        snap = agent.checkpoint()
        if StateCreditCells.restore(snap).checkpoint() != snap:
            raise ValueError("MG18_YGG_COLD_SOURCE_CHECKPOINT")
        return {"role": "Yggdrasil_R20", "environment": name,
                "mission": before["mission"],
                "status": "ONE_GENUINE_NATIVE_SELECTED_SOURCE_EVENT",
                "native_choice_status": suggestion["status"],
                "steps": 1, "source_event": event,
                "checkpoint_sha256": __import__("hashlib").sha256(snap).hexdigest()}
    finally:
        env.close()


def execute(source_root, go_bin):
    data = prereg()
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG18_NOT_USING_PINNED_MINIGRID")
    attest_source(source_root, {
        "source": {
            "git_blob_sha1": {
                "minigrid/__init__.py": "41b4a731255d19bdf61072b7100e752a759a3ae4",
                "minigrid/minigrid_env.py": "eb29e9a902de0715ab77ec981a2113576d7664fa",
                "minigrid/envs/doorkey.py": "df5b29ef063be34e6d83b8b478e092c6e3e01512",
                "minigrid/envs/unlockpickup.py": "82e75ec536b5dfa2ea0b24b3ec43bcb8811d4cdb",
                "minigrid/envs/blockedunlockpickup.py": "b4edd95dfa61f195fe0a577b312aa5b812140589",
                "minigrid/envs/keycorridor.py": "3a5dbaef50d97848c23ad315e4f17f8aad6264c0",
            }
        }
    })
    rows = []
    for name in TARGETS:
        rows.append(wingless(name, go_bin, data["engineering"]["seed"]))
        rows.append(yggdrasil(name, data["engineering"]["seed"]))
    supported = [v for v in rows if v["steps"] == 1]
    rejected = [v for v in rows if v["steps"] == 0]
    if (len(supported) != 2 or len(rejected) != 6 or
        any(v["environment"] != TARGETS[0] for v in supported) or
        any(v["environment"] == TARGETS[0] for v in rejected)):
        raise ValueError("MG18_NATIVE_MISSION_BOUNDARY_CHANGED")
    return {
        "schema": "itd02.mg18.native-mission-boundary-source-only.v1",
        "classification": "MG18_NEW_ORIGINAL_MISSION_NATIVE_SUPPORT_BLOCKED__ENGINEERING",
        "farama_sha": EXPECTED_SOURCE,
        "wingless_sha": data["ancestry"]["wingless_dk16"],
        "yggdrasil_sha": data["ancestry"]["yggdrasil_r20"],
        "engineering_seed_not_fit_dev_sealed": 918001,
        "source_public_only": True,
        "not_native_learning_on_new_families": True,
        "records": rows,
        "canonical_sha256": digest(rows),
    }


def compare(paths):
    a,b=[json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]
    if a != b or a["canonical_sha256"] != digest(a["records"]) or len(a["records"]) != 8:
        raise ValueError("MG18_INDEPENDENT_NATIVE_SOURCE_CUSTODY_MISMATCH")
    print("MG18_INDEPENDENT_NATIVE_MISSION_BOUNDARY_REPLAY_PASS_NO_SCIENCE " + a["canonical_sha256"])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--native-go",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--compare",nargs=2)
    args=parser.parse_args()
    if args.compare:
        compare(args.compare)
    else:
        if not (args.source_root and args.native_go and args.output):
            parser.error("require --source-root, --native-go, --output")
        result=execute(args.source_root,args.native_go)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print(result["classification"],result["canonical_sha256"])


if __name__=="__main__":
    main()

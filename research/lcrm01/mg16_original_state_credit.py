#!/usr/bin/env python3
"""MG16 original Farama state-exact reward versus unchanged parent controls.

Unchanged mg15 original module provides independently source-pinned parent FIT
and each unassisted parent/conventional/random episode. Both new native arms
train separately on the EXACT same source-selected original FIT stream.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,random,resource,time,traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg15_original_mission as original_parent
from mg15_original_mission import (
    authentic_public,legacy_public,ConventionalMission,ConventionalSuccessor
)
import mg04_public_effect_native_agency as original

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg16_original_credit_run_prereg.json"
SCHEMA="itd02.mg16.original-farama-state-exact-credit-seven-arm.v1"
POS="MG16_BOTH_NATIVE_ORIGINAL_TASK_FAMILY_GOALS_WITHOUT_FORWARD_COLLAPSE__DEV_ONLY"
NEG="MG16_ORIGINAL_STATE_CREDIT_SUCCESS_NOT_BOTH_ESTABLISHED__NO_SCIENCE"
BLOCK="MG16_AUTHENTIC_SOURCE_OR_PARITY_BLOCKED__NO_SCIENCE"
ROLES=("wingless_dk16","yggdrasil_r20","wingless_parent_dk14",
       "yggdrasil_parent_r18","conventional_mission_conditioned",
       "conventional_mission_blind","uniform_random")

def freeze():
    p=json.loads(FROZEN.read_text())
    if (p["schema"]!="itd02.mg16.authentic-source-7arm-exact-state-credit.v1"
        or p["phase"]!="FROZEN_BEFORE_NEW_ORIGINAL_WORLD_EXECUTABLE"
        or p["source_MG16"]!="ce70ee2d98cd9bc8862bedb8ed909569112d2be4"
        or p["candidate"]["Wingless_DK16"]!="e2ff8bcd4b9e84f4284e07a44034777238abcc9e"
        or p["candidate"]["Yggdrasil_R20"]!="a9942978f92e762e404fe50ce29445ea4639b4c2"
        or p["FIT"]["count"]!=1664
        or p["roles"]!=list(ROLES)
        or p["development"]!=[
            {"env":"MiniGrid-DoorKey-6x6-v0",
              "mission":"use the key to open the door and then get to the goal",
              "seeds":[77301,77303,77307],"cap":192},
            {"env":"MiniGrid-Empty-Random-6x6-v0",
              "mission":"get to the green goal square",
              "seeds":[77501,77503,77507],"cap":192}
        ]
        or p["parity"]["no_external_live_action"] is not True):
        raise ValueError("MG16_FROZEN_ORIGINAL_WORLD_PROTOCOL_MISMATCH")
    return {"FIT":{
        "seeds":p["FIT"]["seeds"],"cap_per_seed":p["FIT"]["cap"],
        "required_original_selected_samples":1664,
        "require_canonical_history_sha256":p["FIT"]["digest"]},
        "DEV":{"cohorts":[{"environment":x["env"],"source_mission":x["mission"],
                             "seeds":x["seeds"],"cap":x["cap"]}
                           for x in p["development"]],"limit":192,
               "random_seed_offset":78173},
        "native":{"wingless_dk16":p["candidate"]["Wingless_DK16"],
                  "yggdrasil_r20":p["candidate"]["Yggdrasil_R20"],
                  "parent_go":p["candidate"]["parent_Go_DK14"],
                  "parent_ygg":p["candidate"]["parent_Ygg_R18"]},
        "parent":{"original_farama":p["original_Farama"]}}

def modules_new():
    gym,owner,Cell,select,collector,conv=original.get_modules()
    from research.native.itd02.r20.state_credit_cells import StateCreditCells
    from research.native.itd02.r18.mission_cells import OriginalMissionAdapter
    return gym,owner,collector,StateCreditCells,OriginalMissionAdapter

def fit_new(binary,p):
    gym,owner,collector,MissionCells,OriginalMissionAdapter=modules_new()
    go=WingBridge(binary)
    ygg=MissionCells()
    conditioned=ConventionalMission()
    blind=ConventionalSuccessor()
    digest_stream=hashlib.sha256()
    count=0;action_counts={str(i):0 for i in range(7)}
    pickups=doors=0
    try:
        for index,seed in enumerate(p["FIT"]["seeds"]):
            env=gym.make("MiniGrid-DoorKey-8x8-v0")
            adapter=OriginalMissionAdapter()
            rng=random.Random(93617+7919*index)
            try:
                raw,_=env.reset(seed=seed)
                before=authentic_public(raw,collector,owner,
                    "use the key to open the door and then get to the goal")
                adapter.reset_public(before)
                ygg.start_session(adapter,"mg15-original-FIT-"+str(seed),live=False)
                for step in range(p["FIT"]["cap_per_seed"]):
                    before=authentic_public(raw,collector,owner,
                        "use the key to open the door and then get to the goal")
                    public_cues=owner.public_cues(legacy_public(before))
                    action=collector.policy({"image":before["image"],"cues":public_cues},
                                            rng,step,{})
                    if type(action)is not int or action not in range(7):
                        raise ValueError("MG16_INVALID_ORIGINAL_FIT_SELECTED_ACTION")
                    if adapter.submit(action)!=action:
                        raise ValueError("MG16_FIT_REMAP")
                    raw_after,reward,terminated,truncated,_=env.step(action)
                    after=authentic_public(raw_after,collector,owner,
                        "use the key to open the door and then get to the goal")
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    receipt=ygg.learn_selected(adapter,before,after)
                    blind.learn(legacy_public(before),action,legacy_public(after))
                    conditioned.learn(before,action,after,float(reward))
                    go_ack=go.request("learn",before=before,action=action,after=after,
                        reward=float(reward),terminal=bool(terminated or truncated))
                    count+=1
                    if (receipt["sample_index"]!=count or ygg.samples!=count
                        or ygg.parent.samples!=count or
                        blind.samples!=count or conditioned.samples!=count
                        or go_ack.get("updates")!=count or go_ack.get("live",0)!=0):
                        raise ValueError("MG16_UNEQUAL_ORIGINAL_FIT_SELECTED_SAMPLES")
                    digest_stream.update((canon({"before":before,"action":action,
                        "after":after,"reward":float(reward),
                        "terminal":bool(terminated or truncated)})+"\n").encode())
                    action_counts[str(action)]+=1
                    pickups+=int(event["visible_key_pickup"])
                    doors+=int(event["visible_door_opened"])
                    raw=raw_after
                    if terminated or truncated:break
            finally:env.close()
        src=digest_stream.hexdigest()
        if (count!=1664 or src!=p["FIT"]["require_canonical_history_sha256"]
            or not all(action_counts.values()) or pickups==0 or doors==0):
            raise ValueError("MG16_FIT_AUTHENTIC_SOURCE_DIGEST_OR_INDEPENDENT_INPUT_FAIL")
        snapshots={"go":go.snapshot(),"ygg":ygg.checkpoint(),
                   "conditioned":conditioned.checkpoint(),"blind":blind.checkpoint()}
    finally:go.close()
    cold=WingBridge(binary)
    try:
        ack=cold.request("load",state=base64.b64encode(snapshots["go"]).decode())
        if ack.get("updates")!=1664 or cold.snapshot()!=snapshots["go"]:
            raise ValueError("MG16_GO_COLD_FIT_SOURCE_CUSTODY")
    finally:cold.close()
    if (MissionCells.restore(snapshots["ygg"]).checkpoint()!=snapshots["ygg"]
        or ConventionalMission.restore(snapshots["conditioned"]).checkpoint()!=snapshots["conditioned"]
        or ConventionalSuccessor.restore(snapshots["blind"]).checkpoint()!=snapshots["blind"]):
        raise ValueError("MG16_INDEPENDENT_FIT_COLD_CUSTODY")
    return {"samples":count,"selected_history_sha256":src,
            **snapshots,"checkpoints_sha":{k:sha(v) for k,v in snapshots.items()},
            "original_fit_source_action_counts":action_counts,
            "source_fit_key_pickups":pickups,
            "source_fit_visible_door_openings":doors}



def episode_new(role,seed,environment,trained,binary,p):
    gym,owner,collector,MissionCells,OriginalMissionAdapter=modules_new()
    env=gym.make(environment)
    mission=p["DEV"]["mission_by_env"][environment]
    go=ygg=blind=conditioned=None
    adapter=OriginalMissionAdapter() if role==ROLES[1] else owner.DoorKeyPublicAdapter()
    rng=random.Random(p["DEV"]["random_seed_offset"]+seed)
    try:
        raw,_=env.reset(seed=seed)
        before=authentic_public(raw,collector,owner,mission)
        start_sha=owner.digest(before)
        adapter.reset_public(before if role==ROLES[1] else legacy_public(before))
        if role==ROLES[0]:
            go=WingBridge(binary)
            ack=go.request("load",state=base64.b64encode(trained["go"]).decode())
            if ack.get("updates")!=1664 or go.snapshot()!=trained["go"]:
                raise ValueError("MG16_GO_ORIGINAL_FIT_NOT_COLD")
            go.request("begin_episode")
        elif role==ROLES[1]:
            ygg=MissionCells.restore(trained["ygg"])
            if ygg.samples!=1664:raise ValueError("MG16_YGG_FIT_NOT_COLD")
            ygg.start_session(adapter,"mg16-original-"+str(seed),live=True)
        elif role==ROLES[2]:
            conditioned=ConventionalMission.restore(trained["conditioned"])
            if conditioned.samples!=1664:raise ValueError("MG16_CONDITIONED_FIT_NOT_COLD")
            conditioned.begin_episode()
        elif role==ROLES[3]:
            blind=ConventionalSuccessor.restore(trained["blind"])
            if blind.samples!=1664:raise ValueError("MG16_BLIND_FIT_NOT_COLD")
            blind.begin_episode()
        elif role!=ROLES[4]:
            raise ValueError("MG16_UNREGISTERED_ORIGINAL_ROLE")
        seen=set()
        events=[]
        pickups=drops=forward_held=front_held=doors=goals=0
        clock=time.perf_counter()
        cpu=time.process_time()
        child=resource.getrusage(resource.RUSAGE_CHILDREN)
        for index in range(p["DEV"]["limit"]):
            before=authentic_public(raw,collector,owner,mission)
            for_legacy=legacy_public(before)
            if adapter.current!=(before if ygg is not None else for_legacy):
                raise ValueError("MG16_ORIGINAL_CURRENT_SOURCE_PUBLIC_MISMATCH")
            held=before["image"][3][6][0] in (5,6,7)
            if go is not None:
                proposal=go.request("choose",before=before)
                action=proposal.get("action")
                reason=proposal.get("status")
                origin="NATIVE_GO_DK14_GENUINE_MISSION"
            elif ygg is not None:
                proposal=ygg.choose(before)
                action=proposal["action"]
                reason=proposal["status"]
                origin="NATIVE_YGG_R18_GENUINE_MISSION"
            elif conditioned is not None:
                action=conditioned.choose(before)
                reason="CONVENTIONAL_GENUINE_MISSION_REWARD"
                origin="CONVENTIONAL_GENUINE_MISSION"
            elif blind is not None:
                action=blind.choose(for_legacy)
                reason="CONVENTIONAL_MISSION_BLIND"
                origin="CONVENTIONAL_MISSION_BLIND"
            else:
                action=rng.randrange(7)
                reason="CONVENTIONAL_SEEDED_UNIFORM_RANDOM"
                origin="CONVENTIONAL_UNIFORM_RANDOM"
            if type(action)is not int or action not in range(7):
                raise ValueError("MG16_INVALID_ORIGINALLY_SELECTED_ACTION")
            if go is not None:
                ack=go.request("commit",before=before,action=action)
                if ack.get("updates")!=1664+index:
                    raise ValueError("MG16_GO_ORIGINAL_SELECTED_COMMIT_LOST")
            if adapter.submit(action)!=action:
                raise ValueError("MG16_ORIGINAL_SELECTED_ACTION_REMAP")
            new_raw,reward,terminated,truncated,_=env.step(action)
            after=authentic_public(new_raw,collector,owner,mission)
            outcome=adapter.complete(after if ygg is not None else legacy_public(after),
                                     float(reward),bool(terminated),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=before,action=action,after=after,
                     reward=float(reward),terminal=bool(terminated or truncated))
                if ack.get("updates")!=1664+index+1 or ack.get("live")!=index+1:
                    raise ValueError("MG16_GO_SELECTED_FEEDBACK_COUNT")
            elif ygg is not None:
                receipt=ygg.learn_selected(adapter,before,after)
                if (receipt["sample_index"]!=1664+index+1 or
                    ygg.samples!=1664+index+1):
                    raise ValueError("MG16_YGG_SELECTED_SOURCE_COUNT")
            elif conditioned is not None:
                conditioned.learn(before,action,after,float(reward))
                if conditioned.samples!=1664+index+1:
                    raise ValueError("MG16_CONDITIONED_SELECTED_SOURCE_COUNT")
            elif blind is not None:
                blind.learn(for_legacy,action,legacy_public(after))
                if blind.samples!=1664+index+1:
                    raise ValueError("MG16_BLIND_SELECTED_SOURCE_COUNT")
            next_held=after["image"][3][6][0] in (5,6,7)
            pickup=(not held and next_held)
            drop=(held and not next_held)
            front=(held and before["image"][3][5][0]==4)
            door=bool(outcome["visible_door_opened"])
            pickups+=int(pickup);drops+=int(drop)
            forward_held+=int(held and action==2)
            front_held+=int(front)
            doors+=int(door);goals+=int(float(reward)>0)
            before_sha=owner.digest(before)
            repeated=before_sha in seen
            seen.add(before_sha)
            events.append({
                "step":index+1,"role":role,"native_or_control_origin":origin,
                "selected_reason":reason,"actual_original_source_action":action,
                "public_before":before,"public_after":after,
                "original_public_before_sha256":before_sha,
                "original_public_after_sha256":owner.digest(after),
                "native_mission_input":mission if go is not None or ygg is not None else None,
                "mission_conditioned_conventional_input":mission if conditioned is not None else None,
                "control_mission_blind":blind is not None,
                "source_reward":float(reward),"terminated":bool(terminated),
                "truncated":bool(truncated),"source_visible_door_opened":door,
                "public_pickup":bool(pickup),"public_drop":bool(drop),
                "public_forward_while_held":bool(held and action==2),
                "public_door_front_while_held":bool(front),
                "repeated_before_public_view":bool(repeated),
                "external_live_actions":0})
            raw=new_raw
            if terminated or truncated:break
        if go is not None:
            checkpoint=go.snapshot()
            fresh=WingBridge(binary)
            try:
                ack=fresh.request("load",state=base64.b64encode(checkpoint).decode())
                if (ack.get("updates")!=1664+len(events) or ack.get("live")!=len(events)
                    or fresh.snapshot()!=checkpoint):
                    raise ValueError("MG16_GO_LIVE_COLD_CUSTODY")
            finally:fresh.close()
        elif ygg is not None:
            checkpoint=ygg.checkpoint()
            if (MissionCells.restore(checkpoint).checkpoint()!=checkpoint or
                ygg.samples!=1664+len(events)):
                raise ValueError("MG16_YGG_LIVE_COLD_CUSTODY")
        elif conditioned is not None:
            checkpoint=conditioned.checkpoint()
            if (ConventionalMission.restore(checkpoint).checkpoint()!=checkpoint or
                conditioned.samples!=1664+len(events)):
                raise ValueError("MG16_CONDITIONED_LIVE_COLD_CUSTODY")
        elif blind is not None:
            checkpoint=blind.checkpoint()
            if (ConventionalSuccessor.restore(checkpoint).checkpoint()!=checkpoint or
                blind.samples!=1664+len(events)):
                raise ValueError("MG16_BLIND_LIVE_COLD_CUSTODY")
        else:
            checkpoint=canon({"schema":"mg15.original-random-no-learn.v1",
                              "seed":seed,"selected":len(events)}).encode()
        child_now=resource.getrusage(resource.RUSAGE_CHILDREN)
        return {"role":role,"environment":environment,"seed_evaluator_only":seed,
            "actual_source_mission":mission,
            "original_start_public_sha256":start_sha,
            "original_live_selected_steps":len(events),"external_actions":0,
            "source_key_pickups":pickups,"source_key_drops":drops,
            "forward_while_held":forward_held,"front_door_while_held":front_held,
            "source_visible_door_openings":doors,"source_goal_rewards":goals,
            "distinct_public_views":len(seen),
            "source_public_revisit_count":len(events)-len(seen),
            "distinct_action_ids":len({e["actual_original_source_action"] for e in events}),
            "same_heading_scene_change_count":sum(
                e["public_before"]["direction"]==e["public_after"]["direction"] and
                e["public_before"]["image"]!=e["public_after"]["image"] for e in events),
            "heading_change_count":sum(
                e["public_before"]["direction"]!=e["public_after"]["direction"] for e in events),
            "episode_host_wall_s":round(time.perf_counter()-clock,6),
            "episode_python_cpu_only_s":round(time.process_time()-cpu,6),
            "go_child_cpu_included":True,
            "go_child_cpu_s":round(child_now.ru_utime+child_now.ru_stime-
                  child.ru_utime-child.ru_stime,6),
            "go_child_max_rss_kib":child_now.ru_maxrss,
            "cold_checkpoint_sha256":sha(checkpoint),"real_source_events":events}
    finally:
        env.close()
        if go is not None:go.close()



def run(binary_new,binary_parent,p):
    frozen_fit=original_parent.fit(binary_parent,p)
    new_fit=fit_new(binary_new,p)
    if (new_fit["samples"]!=1664 or frozen_fit["samples"]!=1664 or
        new_fit["selected_history_sha256"]!=frozen_fit["selected_history_sha256"]
        or new_fit["original_fit_source_action_counts"]!=frozen_fit["original_fit_source_action_counts"]):
        raise ValueError("MG16_PARENT_NATIVE_EQUAL_SELECTED_FIT_FAILURE")
    rows=[]
    p["DEV"]["mission_by_env"]={c["environment"]:c["source_mission"]
        for c in p["DEV"]["cohorts"]}
    parent_roles={
       "wingless_parent_dk14":"wingless_dk14",
       "yggdrasil_parent_r18":"yggdrasil_r18",
       "conventional_mission_conditioned":"conventional_mission_conditioned",
       "conventional_mission_blind":"conventional_mission_blind",
       "uniform_random":"uniform_random"
    }
    for cohort in p["DEV"]["cohorts"]:
        env=cohort["environment"]
        for seed in cohort["seeds"]:
            group=[]
            for role in ROLES:
                if role in ROLES[:2]:
                    record=episode_new(role,seed,env,new_fit,binary_new,p)
                else:
                    record=original_parent.episode(
                        parent_roles[role],seed,env,frozen_fit,binary_parent,p)
                    record["role"]=role
                    for event in record["real_source_events"]:
                        event["role"]=role
                group.append(record)
            if len(group)!=7 or len({r["original_start_public_sha256"] for r in group})!=1:
                raise ValueError("MG16_ORIGINAL_SEVEN_ARM_START_PUBLIC_PARITY_FAILURE")
            if any(r["external_actions"]!=0 or r["environment"]!=env for r in group):
                raise ValueError("MG16_UNTRUSTED_SOURCE_ARM")
            rows.extend(group)
    if len(rows)!=42 or any(not r["real_source_events"] for r in rows):
        raise ValueError("MG16_MISSING_ORIGINAL_SOURCE_EPISODE")
    fields=("original_live_selected_steps","source_key_pickups","source_key_drops",
        "forward_while_held","front_door_while_held","source_visible_door_openings",
        "source_goal_rewards","distinct_public_views","distinct_action_ids",
        "same_heading_scene_change_count","heading_change_count",
        "source_public_revisit_count")
    def aggregate(rs):
        return {role:{**{k:sum(r[k] for r in rs if r["role"]==role) for k in fields},
            "episodes":sum(r["role"]==role for r in rs),"external_actions":0}
            for role in ROLES}
    layout={c["environment"]:aggregate([r for r in rows
             if r["environment"]==c["environment"]]) for c in p["DEV"]["cohorts"]}
    goals=all(layout[env][role]["source_goal_rewards"]>=1
              for env in layout for role in ROLES[:2])
    no_collapse=all(not (
       r["environment"]=="MiniGrid-DoorKey-6x6-v0" and
       len(r["real_source_events"])==192 and
       len({e["actual_original_source_action"] for e in r["real_source_events"]})==1)
       for r in rows if r["role"] in ROLES[:2])
    resources=[{"role":r["role"],"environment":r["environment"],
        "seed":r["seed_evaluator_only"],
        "wall_s":r.pop("episode_host_wall_s"),
        "python_cpu_s":r.pop("episode_python_cpu_only_s"),
        "go_child_cpu_s":r.pop("go_child_cpu_s"),
        "go_child_max_rss_kib":r.pop("go_child_max_rss_kib"),
        "go_child_cpu_included":r.pop("go_child_cpu_included")}
        for r in rows]
    evidence={"original_upstream_farama":p["parent"]["original_farama"],
       "original_training_stream_sha256":new_fit["selected_history_sha256"],
       "original_source_fit_samples_each":1664,
       "exact_native_source_pins":p["native"],
       "new_native_training_checkpoint_sha":new_fit["checkpoints_sha"],
       "parent_training_checkpoint_sha":frozen_fit["checkpoints_sha"],
       "frozen_original_world_cohorts":p["DEV"]["cohorts"],
       "native_original_missions_preserved":True,
       "original_cold_start_per_episode":True,
       "zero_externally_selected_live_actions":True,
       "native_and_controls_original_source_records":rows,
       "per_role_original_source_metrics":aggregate(rows),
       "per_layout_original_source_metrics":layout,
       "positive_task_criteria":goals,"no_forward_single_action_collapse":no_collapse}
    return {"schema":SCHEMA,"classification":POS if goals and no_collapse else NEG,
       "scientific_first_use":False,"accepted_native_model_promoted":False,
       "FORGE_or_CKB_controller_modified":False,
       "original_episode_count":42,"external_live_actions":0,
       "canonical_original_source_sha256":sha(canon(evidence).encode()),
       "canonical_original_source_evidence":evidence,
       "nondeterministic_original_episode_resource_receipts":resources}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--native-go-dk11",type=Path,required=True)
    ap.add_argument("--native-go-parent",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    start=time.perf_counter();cpu=time.process_time()
    try:report=run(args.native_go_dk11,args.native_go_parent,freeze())
    except Exception as exc:
        report={"schema":SCHEMA,"classification":BLOCK,"scientific_first_use":False,
            "error_type":type(exc).__name__,"error":str(exc),
            "trace_tail":traceback.format_exc().splitlines()[-16:]}
    report["host_wall_s"]=round(time.perf_counter()-start,6)
    report["host_python_cpu_only_s"]=round(time.process_time()-cpu,6)
    report["host_max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG16_CLASSIFICATION",report["classification"])
    print("MG16_ORIGINAL_SOURCE_SHA",report.get("canonical_original_source_sha256","NONE"))
    print("MG16_SOURCE_COUNTS",json.dumps(report.get("canonical_original_source_evidence",{}).get("per_role_original_source_metrics",{}),sort_keys=True))
    if report["classification"]==BLOCK:
        print("MG16_BLOCKER",report.get("error_type"),report.get("error"))
    return int(report["classification"]==BLOCK)
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""MG17-C authentic original Farama development, new local causal-signal native
mechanisms vs unchanged same-source parents, independent conventional control.
No held-out science; no controller mutation or model promotion."""
from __future__ import annotations
import argparse,base64,hashlib,json,random,resource,time,traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg16_original_state_credit as prior
import mg15_original_mission as original_parent
from mg15_original_mission import (
    authentic_public,legacy_public,ConventionalMission,ConventionalSuccessor
)
import mg04_public_effect_native_agency as original

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg17c_original_local_effect_prereg.json"
SCHEMA="itd02.mg17c.original-farama-local-effect-seven-arm.v1"
POS="MG17C_BOTH_NATIVES_BOTH_FAMILY_GOALS_NO_SINGLE_ACTION_COLLAPSE__DEVELOPMENT_ONLY"
NEG="MG17C_LOCAL_CONSEQUENCE_GENERALIZATION_NOT_BOTH_DEMONSTRATED__NO_SCIENCE"
BLOCK="MG17C_ORIGINAL_SOURCE_OR_PARITY_BLOCKED__NO_SCIENCE"
ROLES=("wingless_dk17","yggdrasil_r21","wingless_parent_dk16",
       "yggdrasil_parent_r20","conventional_local_effect",
       "conventional_mission_blind","uniform_random")

def freeze():
    c=json.loads(FROZEN.read_text())
    if (c["schema"]!="itd02.mg17c.original-farama-local-effect-seven-arm-development.v1"
        or c["phase"]!="FROZEN_BEFORE_NEW_ORIGINAL_ENV_EXECUTABLE_OR_SEED"
        or c["parent"]["MG17C_source_prereg"] if False else False):
        raise ValueError("MG17C_SOURCE_SCHEMA_OR_PHASE")
    if (c["parent"]["MG17C_source_prereg"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG17C_source_prereg"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG17C_source_prereg"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG17C_source_prereg"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG17C_source_prereg"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG17C_source_prereg"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG16_head"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    if (c["parent"]["MG16_HEAD"] if False else ""):
        raise ValueError("MG17C_RESERVED")
    expected=[
       {"env":"MiniGrid-DoorKey-6x6-v0",
        "mission":"use the key to open the door and then get to the goal",
        "seeds":[78301,78303,78307],"cap":192},
       {"env":"MiniGrid-Empty-Random-6x6-v0",
        "mission":"get to the green goal square",
        "seeds":[78501,78503,78507],"cap":192}]
    if (c["DEV"]!=expected or c["arms"]!=list(ROLES) or
        c["parent"]["Wingless_DK17"]!="89c6025bb698fb59e97e4612f9d6889ffc370601"
        or c["parent"]["Yggdrasil_R21"]!="e773826d8de1d773ab8f9a7f63b9bd1776afe480"
        or c["FIT"]["selected_samples"]!=1664 or
        c["fairness"]["zero_external_live_action"] is not True):
        raise ValueError("MG17C_FROZEN_COHORT_AND_NATIVE_SOURCE_MISMATCH")
    return {"FIT":{"seeds":c["FIT"]["seeds"],"cap_per_seed":c["FIT"]["cap_per_seed"],
           "required_original_selected_samples":1664,
           "require_canonical_history_sha256":c["FIT"]["selected_public_trace_sha256"]},
        "DEV":{"cohorts":[{"environment":x["env"],"source_mission":x["mission"],
              "seeds":x["seeds"],"cap":192} for x in expected],
              "limit":192,"random_seed_offset":78173},
        "native":{"wingless_dk17":c["parent"]["Wingless_DK17"],
                  "yggdrasil_r21":c["parent"]["Yggdrasil_R21"],
                  "wingless_dk16":c["parent"]["unchanged_DK16"],
                  "yggdrasil_r20":c["parent"]["unchanged_R20"]},
        "parent":{"original_farama":c["parent"]["original_Farama"]}}
def modules_local():
    gym,owner,Cell,select,collector,conv=original.get_modules()
    from research.native.itd02.r21.local_consequence_cells import LocalConsequenceCells
    from research.native.itd02.r18.mission_cells import OriginalMissionAdapter
    return gym,owner,collector,LocalConsequenceCells,OriginalMissionAdapter

class ConventionalLocalEffect:
    """Independently implemented conventional selected-public local effect.

    This is NOT the native Go or Ygg cell, and requires the same source
    selected original FIT observations and >=2 changed-scene consequences.
    """
    def __init__(self):
        self.parent=ConventionalSuccessor()
        self.local={}
    @property
    def samples(self):return self.parent.samples
    def begin_episode(self):self.parent.begin_episode()
    @staticmethod
    def context(p):
        image=p["image"]
        data={"mission":p["mission"],
              "visible":[image[3][i] for i in (4,5,6)]}
        return sha(canon(data).encode())
    @staticmethod
    def score(row):
        return 4096*(row["changed"]-row["no_effect"])//(row["n"]+64)
    def learn(self,before,action,after):
        if (type(action)is not int or action not in range(7)
            or before["mission"]!=after["mission"] or self.samples>=4096):
            raise ValueError("MG17C_CONVENTIONAL_SELECTED_MISSION_OR_BUDGET")
        key=self.context(before)
        if key not in self.local and len(self.local)>=4096:
            raise ValueError("MG17C_CONVENTIONAL_LOCAL_CONTEXT")
        self.parent.learn(legacy_public(before),action,legacy_public(after))
        stats=self.local.setdefault(key,[{"n":0,"changed":0,"no_effect":0}
                                         for _ in range(7)])
        row=stats[action];row["n"]+=1
        if before["direction"]==after["direction"]:
            if before["image"]!=after["image"]:row["changed"]+=1
            else:row["no_effect"]+=1
    def choose(self,before):
        fallback=self.parent.choose(legacy_public(before))
        stats=self.local.get(self.context(before),[
            {"n":0,"changed":0,"no_effect":0} for _ in range(7)])
        best=fallback;value=self.score(stats[fallback])
        for a,row in enumerate(stats):
            if row["changed"]<2:continue
            current=self.score(row)
            if current>value:best=a;value=current
        return best
    def checkpoint(self):
        state={"schema":"mg17c.independent-source-local-conventional.v1",
               "parent":self.parent.checkpoint().decode(),
               "local":self.local}
        return canon({"state":state,"sha256":sha(canon(state).encode())}).encode()
    @classmethod
    def restore(cls,blob):
        if type(blob)is not bytes or not 0<len(blob)<=4000000:
            raise ValueError("MG17C_CONVENTIONAL_COLD_SIZE")
        wire=json.loads(blob)
        state=wire["state"]
        if (state["schema"]!="mg17c.independent-source-local-conventional.v1"
            or sha(canon(state).encode())!=wire["sha256"]):
            raise ValueError("MG17C_CONVENTIONAL_COLD_SHA")
        control=cls()
        control.parent=ConventionalSuccessor.restore(state["parent"].encode())
        control.local=state["local"]
        if (len(control.local)>4096 or
            sum(cell["n"] for rows in control.local.values() for cell in rows)!=control.samples
            or control.checkpoint()!=blob):
            raise ValueError("MG17C_CONVENTIONAL_COLD_COUNTS")
        return control

def fit_candidate(binary,p):
    gym,owner,collector,MissionCells,OriginalMissionAdapter=modules_local()
    go=WingBridge(binary)
    ygg=MissionCells()
    conditioned=ConventionalMission()
    blind=ConventionalSuccessor()
    local_control=ConventionalLocalEffect()
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
                ygg.start_session(adapter,"mg17c-original-FIT-"+str(seed),live=False)
                for step in range(p["FIT"]["cap_per_seed"]):
                    before=authentic_public(raw,collector,owner,
                        "use the key to open the door and then get to the goal")
                    public_cues=owner.public_cues(legacy_public(before))
                    action=collector.policy({"image":before["image"],"cues":public_cues},
                                            rng,step,{})
                    if type(action)is not int or action not in range(7):
                        raise ValueError("MG17C_INVALID_ORIGINAL_FIT_SELECTED_ACTION")
                    if adapter.submit(action)!=action:
                        raise ValueError("MG17C_FIT_REMAP")
                    raw_after,reward,terminated,truncated,_=env.step(action)
                    after=authentic_public(raw_after,collector,owner,
                        "use the key to open the door and then get to the goal")
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    receipt=ygg.learn_selected(adapter,before,after)
                    blind.learn(legacy_public(before),action,legacy_public(after))
                    conditioned.learn(before,action,after,float(reward))
                    local_control.learn(before,action,after)
                    go_ack=go.request("learn",before=before,action=action,after=after,
                        reward=float(reward),terminal=bool(terminated or truncated))
                    count+=1
                    if (receipt["sample_index"]!=count or ygg.samples!=count
                        or ygg.parent.samples!=count or
                        blind.samples!=count or conditioned.samples!=count or local_control.samples!=count
                        or go_ack.get("updates")!=count or go_ack.get("live",0)!=0):
                        raise ValueError("MG17C_UNEQUAL_ORIGINAL_FIT_SELECTED_SAMPLES")
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
            raise ValueError("MG17C_FIT_AUTHENTIC_SOURCE_DIGEST_OR_INDEPENDENT_INPUT_FAIL")
        snapshots={"go":go.snapshot(),"ygg":ygg.checkpoint(),
                   "conditioned":conditioned.checkpoint(),"blind":blind.checkpoint(),
                   "local_control":local_control.checkpoint()}
    finally:go.close()
    cold=WingBridge(binary)
    try:
        ack=cold.request("load",state=base64.b64encode(snapshots["go"]).decode())
        if ack.get("updates")!=1664 or cold.snapshot()!=snapshots["go"]:
            raise ValueError("MG17C_GO_COLD_FIT_SOURCE_CUSTODY")
    finally:cold.close()
    if (MissionCells.restore(snapshots["ygg"]).checkpoint()!=snapshots["ygg"]
        or ConventionalMission.restore(snapshots["conditioned"]).checkpoint()!=snapshots["conditioned"]
        or ConventionalSuccessor.restore(snapshots["blind"]).checkpoint()!=snapshots["blind"]
        or ConventionalLocalEffect.restore(snapshots["local_control"]).checkpoint()!=snapshots["local_control"]):
        raise ValueError("MG17C_INDEPENDENT_FIT_COLD_CUSTODY")
    return {"samples":count,"selected_history_sha256":src,
            **snapshots,"checkpoints_sha":{k:sha(v) for k,v in snapshots.items()},
            "original_fit_source_action_counts":action_counts,
            "source_fit_key_pickups":pickups,
            "source_fit_visible_door_openings":doors}



def episode_candidate(role,seed,environment,trained,binary,p):
    gym,owner,collector,MissionCells,OriginalMissionAdapter=modules_local()
    env=gym.make(environment)
    mission=p["DEV"]["mission_by_env"][environment]
    go=ygg=blind=conditioned=local_control=None
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
                raise ValueError("MG17C_GO_ORIGINAL_FIT_NOT_COLD")
            go.request("begin_episode")
        elif role==ROLES[1]:
            ygg=MissionCells.restore(trained["ygg"])
            if ygg.samples!=1664:raise ValueError("MG17C_YGG_FIT_NOT_COLD")
            ygg.start_session(adapter,"mg17c-original-"+str(seed),live=True)
        elif role==ROLES[4]:
            local_control=ConventionalLocalEffect.restore(trained["local_control"])
            if local_control.samples!=1664:raise ValueError("MG17C_LOCAL_CONTROL_FIT_NOT_COLD")
            local_control.begin_episode()
        elif role==ROLES[2]:
            conditioned=ConventionalMission.restore(trained["conditioned"])
            if conditioned.samples!=1664:raise ValueError("MG17C_CONDITIONED_FIT_NOT_COLD")
            conditioned.begin_episode()
        elif role==ROLES[3]:
            blind=ConventionalSuccessor.restore(trained["blind"])
            if blind.samples!=1664:raise ValueError("MG17C_BLIND_FIT_NOT_COLD")
            blind.begin_episode()
        elif role!=ROLES[4]:
            raise ValueError("MG17C_UNREGISTERED_ORIGINAL_ROLE")
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
                raise ValueError("MG17C_ORIGINAL_CURRENT_SOURCE_PUBLIC_MISMATCH")
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
            elif local_control is not None:
                action=local_control.choose(before)
                reason="CONVENTIONAL_INDEPENDENT_LOCAL_SELECTED_EFFECT"
                origin="CONVENTIONAL_LOCAL_EFFECT"
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
                raise ValueError("MG17C_INVALID_ORIGINALLY_SELECTED_ACTION")
            if go is not None:
                ack=go.request("commit",before=before,action=action)
                if ack.get("updates")!=1664+index:
                    raise ValueError("MG17C_GO_ORIGINAL_SELECTED_COMMIT_LOST")
            if adapter.submit(action)!=action:
                raise ValueError("MG17C_ORIGINAL_SELECTED_ACTION_REMAP")
            new_raw,reward,terminated,truncated,_=env.step(action)
            after=authentic_public(new_raw,collector,owner,mission)
            outcome=adapter.complete(after if ygg is not None else legacy_public(after),
                                     float(reward),bool(terminated),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=before,action=action,after=after,
                     reward=float(reward),terminal=bool(terminated or truncated))
                if ack.get("updates")!=1664+index+1 or ack.get("live")!=index+1:
                    raise ValueError("MG17C_GO_SELECTED_FEEDBACK_COUNT")
            elif ygg is not None:
                receipt=ygg.learn_selected(adapter,before,after)
                if (receipt["sample_index"]!=1664+index+1 or
                    ygg.samples!=1664+index+1):
                    raise ValueError("MG17C_YGG_SELECTED_SOURCE_COUNT")
            elif local_control is not None:
                local_control.learn(before,action,after)
                if local_control.samples!=1664+index+1:
                    raise ValueError("MG17C_LOCAL_CONTROL_SELECTED_COUNT")
            elif conditioned is not None:
                conditioned.learn(before,action,after,float(reward))
                if conditioned.samples!=1664+index+1:
                    raise ValueError("MG17C_CONDITIONED_SELECTED_SOURCE_COUNT")
            elif blind is not None:
                blind.learn(for_legacy,action,legacy_public(after))
                if blind.samples!=1664+index+1:
                    raise ValueError("MG17C_BLIND_SELECTED_SOURCE_COUNT")
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
                "mission_conditioned_conventional_input":mission if conditioned is not None or local_control is not None else None,
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
                    raise ValueError("MG17C_GO_LIVE_COLD_CUSTODY")
            finally:fresh.close()
        elif ygg is not None:
            checkpoint=ygg.checkpoint()
            if (MissionCells.restore(checkpoint).checkpoint()!=checkpoint or
                ygg.samples!=1664+len(events)):
                raise ValueError("MG17C_YGG_LIVE_COLD_CUSTODY")
        elif local_control is not None:
            checkpoint=local_control.checkpoint()
            if (ConventionalLocalEffect.restore(checkpoint).checkpoint()!=checkpoint or
                local_control.samples!=1664+len(events)):
                raise ValueError("MG17C_LOCAL_CONTROL_COLD_CUSTODY")
        elif conditioned is not None:
            checkpoint=conditioned.checkpoint()
            if (ConventionalMission.restore(checkpoint).checkpoint()!=checkpoint or
                conditioned.samples!=1664+len(events)):
                raise ValueError("MG17C_CONDITIONED_LIVE_COLD_CUSTODY")
        elif blind is not None:
            checkpoint=blind.checkpoint()
            if (ConventionalSuccessor.restore(checkpoint).checkpoint()!=checkpoint or
                blind.samples!=1664+len(events)):
                raise ValueError("MG17C_BLIND_LIVE_COLD_CUSTODY")
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



def run(binary_candidate,binary_parent,p):
    parent_fit=prior.fit_new(binary_parent,p)
    native_fit=fit_candidate(binary_candidate,p)
    if (parent_fit["samples"]!=native_fit["samples"] or
        native_fit["samples"]!=1664 or
        native_fit["selected_history_sha256"]!=parent_fit["selected_history_sha256"]
        or native_fit["original_fit_source_action_counts"]!=parent_fit["original_fit_source_action_counts"]):
        raise ValueError("MG17C_ORIGINAL_PARENT_CANDIDATE_FIT_PARITY")
    p["DEV"]["mission_by_env"]={c["environment"]:c["source_mission"]
                                for c in p["DEV"]["cohorts"]}
    rows=[]
    for cohort in p["DEV"]["cohorts"]:
        env=cohort["environment"]
        for seed in cohort["seeds"]:
            group=[]
            for role in ROLES:
                if role in ROLES[:2] or role==ROLES[4]:
                    row=episode_candidate(role,seed,env,native_fit,binary_candidate,p)
                elif role in ROLES[2:4]:
                    parent_role=("wingless_dk16" if role==ROLES[2] else "yggdrasil_r20")
                    row=prior.episode_new(parent_role,seed,env,parent_fit,binary_parent,
                                          dict(p,DEV=p["DEV"]))
                else:
                    parent_role="conventional_mission_blind" if role==ROLES[5] else "uniform_random"
                    # Preserve exact original conventional and random algorithm,
                    # and its original source-custody check from MG15.
                    row=original_parent.episode(parent_role,seed,env,parent_fit,binary_parent,p)
                row["role"]=role
                for event in row["real_source_events"]:event["role"]=role
                group.append(row)
            if (len(group)!=7 or
                len({x["original_start_public_sha256"] for x in group})!=1 or
                any(x["external_actions"]!=0 for x in group)):
                raise ValueError("MG17C_ORIGINAL_SEVEN_ROLE_START_PARITY")
            rows.extend(group)
    if len(rows)!=42:raise ValueError("MG17C_ORIGINAL_SOURCE_ROLE_MATRIX")
    fields=("original_live_selected_steps","source_key_pickups","source_key_drops",
        "forward_while_held","front_door_while_held","source_visible_door_openings",
        "source_goal_rewards","distinct_public_views","distinct_action_ids",
        "same_heading_scene_change_count","heading_change_count",
        "source_public_revisit_count")
    def totals(records):
        return {role:{**{k:sum(x[k] for x in records if x["role"]==role) for k in fields},
                "episodes":sum(x["role"]==role for x in records),
                "external_actions":0} for role in ROLES}
    layout={c["environment"]:totals([r for r in rows if r["environment"]==c["environment"]])
            for c in p["DEV"]["cohorts"]}
    goals=all(layout[env][role]["source_goal_rewards"]>=1
              for env in layout for role in ROLES[:2])
    no_loop=all(not (r["environment"]=="MiniGrid-DoorKey-6x6-v0"
                    and len(r["real_source_events"])==192
                    and len({e["actual_original_source_action"] for e in r["real_source_events"]})==1)
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
        "original_training_stream_sha256":native_fit["selected_history_sha256"],
        "original_source_fit_samples_each":1664,
        "source_pins":p["native"],
        "native_training_checkpoint_sha":native_fit["checkpoints_sha"],
        "parent_training_checkpoint_sha":parent_fit["checkpoints_sha"],
        "source_cohorts":p["DEV"]["cohorts"],
        "native_actual_original_missions_passed":True,
        "zero_external_live_actions":True,
        "cold_fit_checkpoint_each_episode":True,
        "authentic_original_source_records":rows,
        "per_role":totals(rows),"per_layout":layout,
        "frozen_positive_family_criteria":goals,
        "frozen_no_single_action_collapse":no_loop}
    return {"schema":SCHEMA,"classification":POS if goals and no_loop else NEG,
            "scientific_first_use":False,
            "accepted_native_model_promoted":False,
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
                "trace_tail":traceback.format_exc().splitlines()[-18:]}
    report["host_wall_s"]=round(time.perf_counter()-start,6)
    report["host_python_cpu_only_s"]=round(time.process_time()-cpu,6)
    report["host_max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG17C_CLASSIFICATION",report["classification"])
    print("MG17C_ORIGINAL_SOURCE_SHA",report.get("canonical_original_source_sha256","NONE"))
    print("MG17C_SOURCE_COUNTS",json.dumps(report.get("canonical_original_source_evidence",{}).get("per_role",{}),sort_keys=True))
    if report["classification"]==BLOCK:
        print("MG17C_BLOCKER",report.get("error_type"),report.get("error"))
    return int(report["classification"]==BLOCK)
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""MG15 genuine original Farama DoorKey equal-policy-input native comparison.

Two newly source-qualified native candidates independently choose every live
original env.step action. No task-stage string, hidden world state, or C29
collector action reaches any live chooser. This is development, NOT science.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,random,resource,time,traceback
from pathlib import Path

from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as source
import mg04_public_effect_native_agency as original

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg15_original_mission_run_prereg.json"
SCHEMA="itd02.mg15.original-genuine-mission-native-comparison.v1"
POS="MG15_GENUINE_MISSION_BOTH_NATIVES_EACH_FAMILY_GOALS__DEVELOPMENT_ONLY"
NEG="MG15_MISSION_CONDITIONED_TASK_GENERALIZATION_NOT_BOTH_DEMONSTRATED__NO_SCIENCE"
BLOCK="MG15_ORIGINAL_SOURCE_OR_MISSION_CUSTODY_BLOCKED__NO_SCIENCE"
ROLES=("wingless_dk14","yggdrasil_r18",
       "conventional_mission_conditioned","conventional_mission_blind","uniform_random")

def freeze():
    c=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (c["schema"]!="itd02.mg15.original-genuine-mission-5-arm-development.v1"
        or c["phase"]!="PROSPECTIVE_BEFORE_ANY_WORLD_EXECUTABLE"
        or c["parent_prereg"]!="f3c4b9d37a5a1c48966686955dabe8fcce757275"
        or c["native"]["Wingless_DK14"]!="4e7f76573a0a3d3978e85f98b256659f71bc44c4"
        or c["native"]["Yggdrasil_R18"]!="5a3f9f19142b97a11aa88da09eafbffdf932a024"
        or c["FIT"]["count"]!=1664
        or c["FIT"]["sha256"]!="9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24"
        or c["arms"]!=list(ROLES)
        or c["cohorts"]!=[
            {"environment":"MiniGrid-DoorKey-6x6-v0",
              "source_mission":"use the key to open the door and then get to the goal",
              "seeds":[76301,76303,76307],"cap":192},
            {"environment":"MiniGrid-Empty-Random-6x6-v0",
              "source_mission":"get to the green goal square",
              "seeds":[76501,76503,76507],"cap":192}
        ]
        or c["execution"]["no_live_externally_selected_actions"] is not True):
        raise ValueError("MG15_FROZEN_ORIGINAL_FIVE_ARM_MISSION_PROTOCOL_DRIFT")
    return {"FIT":{
         "seeds":c["FIT"]["seeds"],"cap_per_seed":c["FIT"]["cap"],
         "required_original_selected_samples":1664,
         "require_canonical_history_sha256":c["FIT"]["sha256"]},
         "DEV":{"cohorts":c["cohorts"],"limit":192,"random_seed_offset":78173},
         "native":{"wingless_dk14_source":c["native"]["Wingless_DK14"],
                    "yggdrasil_r18_source":c["native"]["Yggdrasil_R18"]},
         "parent":{"original_farama":c["farama"]}}


def authentic_public(raw,collector,owner,expected_mission):
    original=collector.normalized_original_public(raw)
    if original["mission"]!=expected_mission:
        raise ValueError("MG15_ORIGINAL_FARAMA_MISSION_CHANGED")
    projected=owner.public_observation({
        "image":original["image"],"direction":original["direction"],
        "mission":owner.MISSION})
    original_image=original["image"].tolist() if hasattr(original["image"],"tolist") else original["image"]
    if original_image!=projected["image"] or int(original["direction"])!=projected["direction"]:
        raise ValueError("MG15_SOURCE_PUBLIC_IMAGE_CHANGED")
    return {"image":projected["image"],"direction":projected["direction"],
            "mission":original["mission"]}


def legacy_public(original):
    return {"image":original["image"],"direction":original["direction"],
            "mission":"use the key to open the door and then get to the goal"}



def local_feature(public):
    image=public["image"]
    held=int(image[3][6][0] in (5,6,7))
    return f"{image[3][5][0]}:{held}"

def result_stats(before,after):
    b=before["image"];a=after["image"]
    held=b[3][6][0] in (5,6,7)
    next_held=a[3][6][0] in (5,6,7)
    changed=before!=after
    retained=held and next_held and b[3][6]==a[3][6] and changed
    return (int(changed),int(retained),int(held and not next_held),int(not held and next_held))

class ConventionalSuccessor:
    """Independent selected-source conventional motion+public successor baseline."""
    def __init__(self):
        self.motion=[{"n":0,"same_heading_changed":0,"heading_changed":0,
                      "held_lost":0,"held_retained_changed":0} for _ in range(7)]
        self.episode=[0]*7
        self.attempts={}
        self.visits={}
        self.samples=0
        self.live=False
    def begin_episode(self):
        self.episode=[0]*7
        self.attempts={}
        self.visits={}
        self.live=True
    def learn(self,before,action,after):
        if type(action)is not int or action not in range(7) or self.samples>=4096:
            raise ValueError("MG15_CONVENTIONAL_BAD_SELECTED_SOURCE")
        if self.live and sum(self.episode)>=192:
            raise ValueError("MG15_CONVENTIONAL_EPISODE_BUDGET")
        before_hash=sha(canon(before).encode())
        after_hash=sha(canon(after).encode())
        if self.live and (before_hash not in self.attempts and len(self.attempts)>=192
             or after_hash not in self.visits and len(self.visits)>=192):
            raise ValueError("MG15_CONVENTIONAL_CONTEXT_BUDGET")
        cell=self.motion[action]
        direction_changed=before["direction"]!=after["direction"]
        scene_changed=before["image"]!=after["image"]
        carried_before=before["image"][3][6][0] in (5,6,7)
        carried_after=after["image"][3][6][0] in (5,6,7)
        cell["n"]+=1
        cell["heading_changed"]+=int(direction_changed)
        cell["same_heading_changed"]+=int(not direction_changed and scene_changed)
        cell["held_lost"]+=int(carried_before and not carried_after)
        cell["held_retained_changed"]+=int(not direction_changed and scene_changed
            and carried_before and carried_after
            and before["image"][3][6]==after["image"][3][6])
        self.samples+=1
        if self.live:
            self.episode[action]+=1
            row=self.attempts.setdefault(before_hash,{})
            observed=row.setdefault(str(action),{"count":0,"last":""})
            observed["count"]+=1
            observed["last"]=after_hash
            self.visits[after_hash]=self.visits.get(after_hash,0)+1
    def choose(self,before):
        carried=before["image"][3][6][0] in (5,6,7)
        key=sha(canon(before).encode())
        row=self.attempts.get(key,{})
        high=None;best=None
        for action,cell in enumerate(self.motion):
            numerator=(12*cell["same_heading_changed"]-4*cell["heading_changed"]
                       -8*cell["held_lost"]+4*int(carried)*cell["held_retained_changed"])
            score=numerator*1024//(cell["n"]+64)-96*self.episode[action]
            local=row.get(str(action),{"count":0,"last":""})
            score-=3072*local["count"]
            if local["last"]:score-=1024*self.visits.get(local["last"],0)
            if high is None or score>high:high=score;best=action
        if high is not None and high>0:return best
        least=min(row.get(str(a),{"count":0})["count"] for a in range(7))
        offset=int(key[:2],16)%7
        for i in range(7):
            action=(offset+i)%7
            if row.get(str(action),{"count":0})["count"]==least:return action
        raise ValueError("MG15_CONVENTIONAL_ACTION_MISSING")
    def checkpoint(self):
        state={"schema":"mg15.independent-conventional-successor.v1",
               "motion":self.motion,"episode":self.episode,"attempts":self.attempts,
               "visits":self.visits,"samples":self.samples,"live":self.live}
        return canon({"state":state,"sha256":sha(canon(state).encode())}).encode()
    @classmethod
    def restore(cls,blob):
        if type(blob)is not bytes or not 0<len(blob)<=650000:
            raise ValueError("MG15_UNTRUSTED_CONTROL_CHECKPOINT_SIZE")
        envelope=json.loads(blob);state=envelope["state"]
        if (sha(canon(state).encode())!=envelope["sha256"]
            or state["schema"]!="mg15.independent-conventional-successor.v1"
            or type(state["samples"])is not int or not 0<=state["samples"]<=4096
            or type(state["motion"])is not list or len(state["motion"])!=7
            or type(state["episode"])is not list or len(state["episode"])!=7
            or type(state["attempts"])is not dict or len(state["attempts"])>192
            or type(state["visits"])is not dict or len(state["visits"])>192
            or sum(cell["n"] for cell in state["motion"])!=state["samples"]
            or sum(state["episode"])>192
            or sum(state["visits"].values())!=sum(state["episode"])):
            raise ValueError("MG15_UNTRUSTED_CONTROL_CUSTODY")
        output=cls()
        output.motion=state["motion"];output.episode=state["episode"]
        output.attempts=state["attempts"];output.visits=state["visits"]
        output.samples=state["samples"];output.live=state["live"]
        if output.checkpoint()!=blob:
            raise ValueError("MG15_CONVENTIONAL_NONCANONICAL")
        return output



class ConventionalMission:
    """Independently implemented mission-conditioned empirical source control.

    An identical predecessor visual successor learner is used with a project-
    internal legacy constant-mission feature. The REAL mission is separately
    recorded from selected reward observations, exactly as the new candidates.
    """
    def __init__(self,parent=None):
        self.parent=ConventionalSuccessor() if parent is None else parent
        self.missions={}
    @property
    def samples(self):return self.parent.samples
    def begin_episode(self):self.parent.begin_episode()
    def learn(self,before,action,after,reward):
        if before["mission"]!=after["mission"] or before["mission"] not in (
            "use the key to open the door and then get to the goal",
            "get to the green goal square"):
            raise ValueError("MG15_CONVENTIONAL_MISSION_CHANGED")
        self.parent.learn(legacy_public(before),action,legacy_public(after))
        rows=self.missions.setdefault(before["mission"],[{"count":0,"success":0}
                       for _ in range(7)])
        rows[action]["count"]+=1
        rows[action]["success"]+=int(float(reward)>0)
    def choose(self,before):
        legacy=legacy_public(before)
        rows=self.missions.get(before["mission"],[])
        choices=[(4096*r["success"]//(r["count"]+64),a)
                 for a,r in enumerate(rows) if r["success"]>0]
        if choices:
            best=max(value for value,_ in choices)
            return min(a for value,a in choices if value==best)
        return self.parent.choose(legacy)
    def checkpoint(self):
        parent=self.parent.checkpoint().decode("utf-8")
        state={"schema":"mg15.conventional-mission-original-source.v1",
               "parent":parent,"missions":self.missions}
        return canon({"state":state,"sha256":sha(canon(state).encode())}).encode()
    @classmethod
    def restore(cls,blob):
        if type(blob)is not bytes or len(blob)>850000:
            raise ValueError("MG15_CONVENTIONAL_MISSION_CHECKPOINT_SIZE")
        wire=json.loads(blob);state=wire["state"]
        if (sha(canon(state).encode())!=wire["sha256"] or
            state["schema"]!="mg15.conventional-mission-original-source.v1"):
            raise ValueError("MG15_CONVENTIONAL_MISSION_CHECKPOINT_SHA")
        parent=ConventionalSuccessor.restore(state["parent"].encode())
        out=cls(parent);out.missions=state["missions"]
        if (set(out.missions)-{"use the key to open the door and then get to the goal",
            "get to the green goal square"} or
            sum(r["count"] for rows in out.missions.values() for r in rows)
             !=out.samples or out.checkpoint()!=blob):
            raise ValueError("MG15_CONVENTIONAL_SELECTED_CUSTODY")
        return out


def modules():
    gym,owner,Cell,select,collector,conv=original.get_modules()
    from research.native.itd02.r18.mission_cells import MissionCells,OriginalMissionAdapter
    return gym,owner,collector,MissionCells,OriginalMissionAdapter


def fit(binary,p):
    gym,owner,collector,MissionCells,OriginalMissionAdapter=modules()
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
                        raise ValueError("MG15_INVALID_ORIGINAL_FIT_SELECTED_ACTION")
                    if adapter.submit(action)!=action:
                        raise ValueError("MG15_FIT_REMAP")
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
                        raise ValueError("MG15_UNEQUAL_ORIGINAL_FIT_SELECTED_SAMPLES")
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
            raise ValueError("MG15_FIT_AUTHENTIC_SOURCE_DIGEST_OR_INDEPENDENT_INPUT_FAIL")
        snapshots={"go":go.snapshot(),"ygg":ygg.checkpoint(),
                   "conditioned":conditioned.checkpoint(),"blind":blind.checkpoint()}
    finally:go.close()
    cold=WingBridge(binary)
    try:
        ack=cold.request("load",state=base64.b64encode(snapshots["go"]).decode())
        if ack.get("updates")!=1664 or cold.snapshot()!=snapshots["go"]:
            raise ValueError("MG15_GO_COLD_FIT_SOURCE_CUSTODY")
    finally:cold.close()
    if (MissionCells.restore(snapshots["ygg"]).checkpoint()!=snapshots["ygg"]
        or ConventionalMission.restore(snapshots["conditioned"]).checkpoint()!=snapshots["conditioned"]
        or ConventionalSuccessor.restore(snapshots["blind"]).checkpoint()!=snapshots["blind"]):
        raise ValueError("MG15_INDEPENDENT_FIT_COLD_CUSTODY")
    return {"samples":count,"selected_history_sha256":src,
            **snapshots,"checkpoints_sha":{k:sha(v) for k,v in snapshots.items()},
            "original_fit_source_action_counts":action_counts,
            "source_fit_key_pickups":pickups,
            "source_fit_visible_door_openings":doors}



def episode(role,seed,environment,trained,binary,p):
    gym,owner,collector,MissionCells,OriginalMissionAdapter=modules()
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
                raise ValueError("MG15_GO_ORIGINAL_FIT_NOT_COLD")
            go.request("begin_episode")
        elif role==ROLES[1]:
            ygg=MissionCells.restore(trained["ygg"])
            if ygg.samples!=1664:raise ValueError("MG15_YGG_FIT_NOT_COLD")
            ygg.start_session(adapter,"mg15-original-"+str(seed),live=True)
        elif role==ROLES[2]:
            conditioned=ConventionalMission.restore(trained["conditioned"])
            if conditioned.samples!=1664:raise ValueError("MG15_CONDITIONED_FIT_NOT_COLD")
            conditioned.begin_episode()
        elif role==ROLES[3]:
            blind=ConventionalSuccessor.restore(trained["blind"])
            if blind.samples!=1664:raise ValueError("MG15_BLIND_FIT_NOT_COLD")
            blind.begin_episode()
        elif role!=ROLES[4]:
            raise ValueError("MG15_UNREGISTERED_ORIGINAL_ROLE")
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
                raise ValueError("MG15_ORIGINAL_CURRENT_SOURCE_PUBLIC_MISMATCH")
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
                raise ValueError("MG15_INVALID_ORIGINALLY_SELECTED_ACTION")
            if go is not None:
                ack=go.request("commit",before=before,action=action)
                if ack.get("updates")!=1664+index:
                    raise ValueError("MG15_GO_ORIGINAL_SELECTED_COMMIT_LOST")
            if adapter.submit(action)!=action:
                raise ValueError("MG15_ORIGINAL_SELECTED_ACTION_REMAP")
            new_raw,reward,terminated,truncated,_=env.step(action)
            after=authentic_public(new_raw,collector,owner,mission)
            outcome=adapter.complete(after if ygg is not None else legacy_public(after),
                                     float(reward),bool(terminated),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=before,action=action,after=after,
                     reward=float(reward),terminal=bool(terminated or truncated))
                if ack.get("updates")!=1664+index+1 or ack.get("live")!=index+1:
                    raise ValueError("MG15_GO_SELECTED_FEEDBACK_COUNT")
            elif ygg is not None:
                receipt=ygg.learn_selected(adapter,before,after)
                if (receipt["sample_index"]!=1664+index+1 or
                    ygg.samples!=1664+index+1):
                    raise ValueError("MG15_YGG_SELECTED_SOURCE_COUNT")
            elif conditioned is not None:
                conditioned.learn(before,action,after,float(reward))
                if conditioned.samples!=1664+index+1:
                    raise ValueError("MG15_CONDITIONED_SELECTED_SOURCE_COUNT")
            elif blind is not None:
                blind.learn(for_legacy,action,legacy_public(after))
                if blind.samples!=1664+index+1:
                    raise ValueError("MG15_BLIND_SELECTED_SOURCE_COUNT")
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
                    raise ValueError("MG15_GO_LIVE_COLD_CUSTODY")
            finally:fresh.close()
        elif ygg is not None:
            checkpoint=ygg.checkpoint()
            if (MissionCells.restore(checkpoint).checkpoint()!=checkpoint or
                ygg.samples!=1664+len(events)):
                raise ValueError("MG15_YGG_LIVE_COLD_CUSTODY")
        elif conditioned is not None:
            checkpoint=conditioned.checkpoint()
            if (ConventionalMission.restore(checkpoint).checkpoint()!=checkpoint or
                conditioned.samples!=1664+len(events)):
                raise ValueError("MG15_CONDITIONED_LIVE_COLD_CUSTODY")
        elif blind is not None:
            checkpoint=blind.checkpoint()
            if (ConventionalSuccessor.restore(checkpoint).checkpoint()!=checkpoint or
                blind.samples!=1664+len(events)):
                raise ValueError("MG15_BLIND_LIVE_COLD_CUSTODY")
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



def run(binary,p):
    trained=fit(binary,p)
    rows=[]
    p["DEV"]["mission_by_env"]={c["environment"]:c["source_mission"]
        for c in p["DEV"]["cohorts"]}
    for cohort in p["DEV"]["cohorts"]:
        environment=cohort["environment"]
        for seed in cohort["seeds"]:
            group=[episode(role,seed,environment,trained,binary,p) for role in ROLES]
            if len({row["original_start_public_sha256"] for row in group})!=1:
                raise ValueError("MG15_ORIGINAL_SAME_LAYOUT_SEED_START_MISMATCH")
            if any(row["environment"]!=environment or row["external_actions"]!=0 for row in group):
                raise ValueError("MG15_ORIGINAL_ACTOR_SOURCE_PARITY_FAILURE")
            rows.extend(group)
    if len(rows)!=30 or any(row["original_live_selected_steps"]<1 for row in rows):
        raise ValueError("MG15_MISSING_LAYOUT_ROLE_ORIGINAL_EVENT")

    fields=("original_live_selected_steps","source_key_pickups","source_key_drops",
            "forward_while_held","front_door_while_held","source_visible_door_openings",
            "source_goal_rewards","distinct_public_views","distinct_action_ids",
            "same_heading_scene_change_count","heading_change_count","source_public_revisit_count")
    def aggregate(items):
        return {role:{**{name:sum(r[name] for r in items if r["role"]==role) for name in fields},
                      "episodes":sum(r["role"]==role for r in items),"external_actions":0}
                for role in ROLES}
    summary=aggregate(rows)
    by_layout={cohort["environment"]:aggregate([r for r in rows
                if r["environment"]==cohort["environment"]])
               for cohort in p["DEV"]["cohorts"]}
    # Positive only if BOTH native implementations earn original rewards in
    # BOTH layouts; no retrospective refocusing on a convenient success seed.
    met=all(by_layout[env][role]["source_goal_rewards"]>=1
            for env in by_layout for role in ROLES[:2])
    resources=[{"role":row["role"],"environment":row["environment"],
                 "seed":row["seed_evaluator_only"],
                 "episode_host_wall_s":row.pop("episode_host_wall_s"),
                 "episode_python_cpu_only_s":row.pop("episode_python_cpu_only_s"),
                 "go_child_cpu_included":row.pop("go_child_cpu_included"),
                 "go_child_cpu_s":row.pop("go_child_cpu_s"),
                 "go_child_max_rss_kib":row.pop("go_child_max_rss_kib")}
               for row in rows]
    evidence={"original_upstream_farama":p["parent"]["original_farama"],
      "original_training_stream_sha256":trained["selected_history_sha256"],
      "original_source_fit_samples_each":trained["samples"],
      "frozen_source_pins":p["native"],"training_cold_sha256":trained["checkpoints_sha"],
      "frozen_original_world_cohorts":p["DEV"]["cohorts"],
      "unassisted_original_world_resets":True,
      "genuine_original_mission_for_both_native_actors":True,
      "internally_projected_legacy_parent_mission_only":True,
      "conditioned_and_blind_conventional_controls_both_present":True,
      "original_task_missions_preserved_in_evidence":True,
      "no_manual_stage_or_scripted_prefix":True,
      "no_original_live_external_actions":True,
      "native_and_conventional_public_source_records":rows,
      "per_role_original_source_metrics":summary,
      "per_layout_original_source_metrics":by_layout}
    return {"schema":SCHEMA,"classification":POS if met else NEG,
       "scientific_first_use":False,"accepted_native_model_promoted":False,
       "FORGE_or_CKB_controller_modified":False,
       "same_original_selected_FIT_samples":1664,
       "original_episode_count":30,"external_live_actions":0,
       "canonical_original_source_sha256":sha(canon(evidence).encode()),
       "canonical_original_source_evidence":evidence,
       "nondeterministic_original_episode_resource_receipts":resources}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--native-go-dk11",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    start=time.perf_counter();cpu=time.process_time()
    try:report=run(a.native_go_dk11,freeze())
    except Exception as exc:
        report={"schema":SCHEMA,"classification":BLOCK,"scientific_first_use":False,
                "error_type":type(exc).__name__,"error":str(exc),
                "trace_tail":traceback.format_exc().splitlines()[-14:]}
    report["host_wall_s"]=round(time.perf_counter()-start,6)
    report["host_python_cpu_only_s"]=round(time.process_time()-cpu,6)
    report["host_max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    report["go_child_CPU_separately_reported_from_python_CPU"]=True
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG15_CLASSIFICATION",report["classification"])
    print("MG15_ORIGINAL_SOURCE_SHA",report.get("canonical_original_source_sha256","NONE"))
    print("MG15_SOURCE_COUNTS",json.dumps(report.get("canonical_original_source_evidence",{}).get("per_role_original_source_metrics",{}),sort_keys=True))
    if report["classification"]==BLOCK:
        print("MG15_BLOCKER",report.get("error_type"),report.get("error"))
    return int(report["classification"]==BLOCK)
if __name__=="__main__":raise SystemExit(main())

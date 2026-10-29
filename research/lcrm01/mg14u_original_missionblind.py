#!/usr/bin/env python3
"""MG14U genuine original Farama DoorKey equal-policy-input native comparison.

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
FROZEN=HERE/"mg14u_unfamiliar_family_prereg.json"
SCHEMA="itd02.mg14u.authentic-original-unfamiliar-missionblind.v1"
POS="MG14U_BOTH_NATIVES_GOAL_REWARDS_IN_BOTH_FAMILIES__DEVELOPMENT_ONLY"
NEG="MG14U_UNFAMILIAR_TASK_TRANSFER_NOT_BOTH_ESTABLISHED__DEVELOPMENT_ONLY"
BLOCK="MG14U_ORIGINAL_SOURCE_OR_MISSION_ABLATION_BLOCKED__NO_SCIENCE"
ROLES=("wingless_dk13","yggdrasil_r17",
       "conventional_public_successor","random")

def freeze():
    contract=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (contract["schema"]!="itd02.mg14u.authentic-unfamiliar-task-missionblind-vision.v1"
        or contract["phase"]!="PROSPECTIVE_BEFORE_EXECUTABLE_OR_ANY_UNFAMILIAR_ENV_STEP"
        or contract["parents"]["MG13T_head"]!="573e796c088d1b00c4281b79f5347975e7fd0b96"
        or contract["parents"]["wingless_dk13"]!="2992a25e3fe05783bfa80ecf70d737bb2a21e281"
        or contract["parents"]["yggdrasil_r17"]!="770244b04d011466458b2335d3951daf7653dc8f"
        or contract["fit"]["total_actual_source_samples"]!=1664
        or contract["arms"]!=list(ROLES)
        or contract["cohorts"]!=[
            {"environment":"MiniGrid-DoorKey-6x6-v0",
             "task_family":"trained-DoorKey-new-seeds-development",
             "source_mission":"use the key to open the door and then get to the goal",
             "seeds":[75301,75303,75307],"cap":192},
            {"environment":"MiniGrid-Empty-Random-6x6-v0",
             "task_family":"genuinely-new-goal-only-task-development",
             "source_mission":"get to the green goal square",
             "seeds":[75501,75503,75507],"cap":192}
        ]
        or contract["mission_ablation"]["original_mission_never_available_to_action_chooser"] is not True
        or contract["constraints"]["no_external_live_actions"] is not True):
        raise ValueError("MG14U_PROSPECTIVE_MISSIONBLIND_PROTOCOL_MISMATCH")
    return {"FIT":{
         "seeds":contract["fit"]["seeds"],"cap_per_seed":contract["fit"]["cap"],
         "required_original_selected_samples":1664,
         "require_canonical_history_sha256":contract["fit"]["exact_selected_trace_sha256"]},
         "DEV":{"cohorts":contract["cohorts"],"limit":192,"random_seed_offset":78173},
         "native":{"wingless_dk13_source":contract["parents"]["wingless_dk13"],
                   "yggdrasil_r17_source":contract["parents"]["yggdrasil_r17"]},
         "parent":{"original_farama":contract["parents"]["Farama"]}}


def original_and_masked_public(raw, collector, owner, expected_mission):
    """Strip mission from every ACTOR; retain genuine original mission in evidence.

    The unchanged R10 and Go DK13 source interfaces require their DoorKey
    constant mission. A fixed, environment-independent placeholder is used
    ONLY as transport. Nothing task-specific is presented to action choice.
    This is an explicit mission-blind ablation, not language transfer.
    """
    normalized=collector.normalized_original_public(raw)
    if (type(normalized["mission"]) is not str or
        normalized["mission"]!=expected_mission):
        raise ValueError("MG14U_ORIGINAL_FARAMA_MISSION_CHANGED")
    projected=owner.public_observation({
        "image":normalized["image"],"direction":normalized["direction"],
        "mission":owner.MISSION})
    source_public={"image":projected["image"],
        "direction":projected["direction"],"mission":normalized["mission"]}
    if any(source_public[k]!=projected[k] for k in ("image","direction")):
        raise ValueError("MG14U_SOURCE_PUBLIC_PROJECTION_CHANGED_SENSORY_DATA")
    return source_public,projected



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
            raise ValueError("MG14U_CONVENTIONAL_BAD_SELECTED_SOURCE")
        if self.live and sum(self.episode)>=192:
            raise ValueError("MG14U_CONVENTIONAL_EPISODE_BUDGET")
        before_hash=sha(canon(before).encode())
        after_hash=sha(canon(after).encode())
        if self.live and (before_hash not in self.attempts and len(self.attempts)>=192
             or after_hash not in self.visits and len(self.visits)>=192):
            raise ValueError("MG14U_CONVENTIONAL_CONTEXT_BUDGET")
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
        raise ValueError("MG14U_CONVENTIONAL_ACTION_MISSING")
    def checkpoint(self):
        state={"schema":"mg14u.independent-conventional-successor.v1",
               "motion":self.motion,"episode":self.episode,"attempts":self.attempts,
               "visits":self.visits,"samples":self.samples,"live":self.live}
        return canon({"state":state,"sha256":sha(canon(state).encode())}).encode()
    @classmethod
    def restore(cls,blob):
        if type(blob)is not bytes or not 0<len(blob)<=650000:
            raise ValueError("MG14U_UNTRUSTED_CONTROL_CHECKPOINT_SIZE")
        envelope=json.loads(blob);state=envelope["state"]
        if (sha(canon(state).encode())!=envelope["sha256"]
            or state["schema"]!="mg14u.independent-conventional-successor.v1"
            or type(state["samples"])is not int or not 0<=state["samples"]<=4096
            or type(state["motion"])is not list or len(state["motion"])!=7
            or type(state["episode"])is not list or len(state["episode"])!=7
            or type(state["attempts"])is not dict or len(state["attempts"])>192
            or type(state["visits"])is not dict or len(state["visits"])>192
            or sum(cell["n"] for cell in state["motion"])!=state["samples"]
            or sum(state["episode"])>192
            or sum(state["visits"].values())!=sum(state["episode"])):
            raise ValueError("MG14U_UNTRUSTED_CONTROL_CUSTODY")
        output=cls()
        output.motion=state["motion"];output.episode=state["episode"]
        output.attempts=state["attempts"];output.visits=state["visits"]
        output.samples=state["samples"];output.live=state["live"]
        if output.checkpoint()!=blob:
            raise ValueError("MG14U_CONVENTIONAL_NONCANONICAL")
        return output



def modules():
    gym,owner,Cell,select,collector,conv=original.get_modules()
    from research.native.itd02.r17.successor_cells import SuccessorCells
    return gym,owner,collector,SuccessorCells


def fit(binary,p):
    gym,owner,collector,SuccessorCells=modules()
    go=WingBridge(binary)
    ygg=SuccessorCells()
    control=ConventionalSuccessor()
    origin=hashlib.sha256()
    count=0;action_counts={str(i):0 for i in range(7)}
    key_pickups=door_opens=0
    try:
        for index,seed in enumerate(p["FIT"]["seeds"]):
            env=gym.make("MiniGrid-DoorKey-8x8-v0")
            adapter=owner.DoorKeyPublicAdapter()
            rng=random.Random(93617+7919*index)
            try:
                raw,_=env.reset(seed=seed)
                adapter.reset_public(collector.normalized_original_public(raw))
                ygg.start_session(adapter,"mg14u-original-fit-"+str(seed),live=False)
                for step in range(p["FIT"]["cap_per_seed"]):
                    before=source.normalize(collector,owner,raw)
                    public_cues=owner.public_cues(before)
                    chosen=collector.policy({"image":before["image"],"cues":public_cues},
                                            rng,step,{})
                    if type(chosen)is not int or chosen not in range(7):
                        raise ValueError("MG14U_FIT_ACTION_UNTRUSTED")
                    if adapter.submit(chosen)!=chosen:
                        raise ValueError("MG14U_FIT_ACTION_REMAP")
                    after_raw,reward,terminated,truncated,_=env.step(chosen)
                    after=source.normalize(collector,owner,after_raw)
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    receipt=ygg.learn_selected(adapter,before,after)
                    control.learn(before,chosen,after)
                    ack=go.request("learn",before=before,action=chosen,after=after,
                                   reward=float(reward),terminal=bool(terminated or truncated))
                    count+=1
                    if (receipt["sample_index"]!=count or ygg.samples!=count or
                        ygg.parent.local.samples!=count or control.samples!=count or
                        ack.get("updates")!=count or ack.get("live",0)!=0):
                        raise ValueError("MG14U_UNEQUAL_ORIGINAL_SOURCE_FIT")
                    origin.update((canon({"before":before,"action":chosen,"after":after,
                        "reward":float(reward),"terminal":bool(terminated or truncated)})+"\n").encode())
                    action_counts[str(chosen)]+=1
                    key_pickups+=int(event["visible_key_pickup"])
                    door_opens+=int(event["visible_door_opened"])
                    raw=after_raw
                    if terminated or truncated:break
            finally:env.close()
        src_sha=origin.hexdigest()
        if (count!=1664 or src_sha!=p["FIT"]["require_canonical_history_sha256"] or
            not all(action_counts.values()) or key_pickups==0 or door_opens==0):
            raise ValueError("MG14U_UNMATCHED_ORIGINAL_1664_FIT_SOURCE")
        go_checkpoint=go.snapshot()
        yg_checkpoint=ygg.checkpoint()
        conventional_checkpoint=control.checkpoint()
    finally:go.close()
    # Cold independent restores of all source-trained learners.
    cold=WingBridge(binary)
    try:
        ack=cold.request("load",state=base64.b64encode(go_checkpoint).decode())
        if ack.get("updates")!=1664 or cold.snapshot()!=go_checkpoint:
            raise ValueError("MG14U_GO_FIT_COLD_CUSTODY")
    finally:cold.close()
    if (SuccessorCells.restore(yg_checkpoint).checkpoint()!=yg_checkpoint or
        ConventionalSuccessor.restore(conventional_checkpoint).checkpoint()!=conventional_checkpoint):
        raise ValueError("MG14U_YGG_AND_CONVENTIONAL_COLD_CUSTODY")
    return {"samples":count,"selected_history_sha256":src_sha,
            "go":go_checkpoint,"ygg":yg_checkpoint,"conventional":conventional_checkpoint,
            "original_fit_source_action_counts":action_counts,"source_fit_key_pickups":key_pickups,
            "source_fit_visible_door_openings":door_opens,
            "checkpoints_sha":{"go":sha(go_checkpoint),"ygg":sha(yg_checkpoint),
                               "conventional":sha(conventional_checkpoint)}}


def episode(role,seed,environment,trained,binary,p):
    gym,owner,collector,SuccessorCells=modules()
    env=gym.make(environment)
    adapter=owner.DoorKeyPublicAdapter()
    go=None;ygg=None;control=None
    rng=random.Random(p["DEV"]["random_seed_offset"]+seed)
    try:
        raw,_=env.reset(seed=seed)
        source_before,before=original_and_masked_public(raw,collector,owner,
            p["DEV"]["mission_by_env"][environment])
        start_sha=owner.digest(source_before)
        adapter.reset_public(before)
        if role==ROLES[0]:
            go=WingBridge(binary)
            ack=go.request("load",state=base64.b64encode(trained["go"]).decode())
            if ack.get("updates")!=trained["samples"] or go.snapshot()!=trained["go"]:
                raise ValueError("MG14U_GO_SOURCE_FIT_NOT_COLD")
            go.request("begin_episode")
        elif role==ROLES[1]:
            ygg=SuccessorCells.restore(trained["ygg"])
            if ygg.samples!=1664:raise ValueError("MG14U_YGG_SOURCE_FIT_NOT_COLD")
            ygg.start_session(adapter,f"mg14u-original-{seed}",live=True)
        elif role==ROLES[2]:
            control=ConventionalSuccessor.restore(trained["conventional"])
            if control.samples!=1664:raise ValueError("MG14U_CONVENTIONAL_FIT_NOT_COLD")
            control.begin_episode()
        elif role!=ROLES[3]:
            raise ValueError("MG14U_UNREGISTERED_ORIGINAL_WORLD_ARM")
        events=[]
        pickups=drops=forward_held=front_held=doors=goals=0
        seen=set()
        time_start=time.perf_counter()
        cpu_start=time.process_time()
        child_before=resource.getrusage(resource.RUSAGE_CHILDREN)
        for index in range(p["DEV"]["limit"]):
            true_before,public=original_and_masked_public(raw,collector,owner,
                p["DEV"]["mission_by_env"][environment])
            if public!=adapter.current:raise ValueError("MG14U_UNORIGINAL_PUBLIC_STATE")
            held=public["image"][3][6][0] in (5,6,7)
            if go is not None:
                proposal=go.request("choose",before=public)
                action=proposal.get("action");reason=proposal.get("status")
                provenance="NATIVE_GO_DK13_RAW_PUBLIC_ONLY"
            elif ygg is not None:
                proposal=ygg.choose(public)
                action=proposal["action"];reason=proposal["status"]
                provenance="NATIVE_YGG_R17_RAW_PUBLIC_ONLY"
            elif control is not None:
                action=control.choose(public)
                reason="CONVENTIONAL_EQUIVALENT_EMPIRICAL_PUBLIC"
                provenance="CONVENTIONAL_EQUIVALENT_EMPIRICAL_PUBLIC"
            else:
                action=rng.randrange(7)
                reason="CONVENTIONAL_UNIFORM_RANDOM"
                provenance="CONVENTIONAL_UNIFORM_RANDOM"
            if type(action)is not int or action not in range(7):
                raise ValueError("MG14U_NO_VALID_SELF_SELECTED_ACTION")
            if go is not None:
                ack=go.request("commit",before=public,action=action)
                if ack.get("updates")!=1664+index:
                    raise ValueError("MG14U_GO_UNCOMMITTED_SELECTED")
            if adapter.submit(action)!=action:
                raise ValueError("MG14U_SELECTED_SOURCE_ACTION_REMAP")
            new_raw,reward,terminated,truncated,_=env.step(action)
            true_after,after=original_and_masked_public(new_raw,collector,owner,
                p["DEV"]["mission_by_env"][environment])
            public_event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=public,action=action,after=after,
                               reward=float(reward),terminal=bool(terminated or truncated))
                if (ack.get("updates")!=1664+index+1 or ack.get("live")!=index+1):
                    raise ValueError("MG14U_GO_SELECTED_UPDATE_LOST")
            elif ygg is not None:
                receipt=ygg.learn_selected(adapter,public,after)
                if (receipt["sample_index"]!=1664+index+1 or ygg.samples!=1664+index+1):
                    raise ValueError("MG14U_YGG_SELECTED_UPDATE_LOST")
            elif control is not None:
                control.learn(public,action,after)
                if control.samples!=1664+index+1:
                    raise ValueError("MG14U_CONVENTIONAL_SELECTED_UPDATE_LOST")
            next_held=after["image"][3][6][0] in (5,6,7)
            pickup=not held and next_held
            drop=held and not next_held
            front=held and public["image"][3][5][0]==4
            door=bool(public_event["visible_door_opened"])
            pickups+=int(pickup);drops+=int(drop)
            forward_held+=int(held and action==2)
            front_held+=int(front);doors+=int(door)
            goals+=int(float(reward)>0)
            before_sha=owner.digest(true_before)
            repeated=before_sha in seen;seen.add(before_sha)
            events.append({"step":index+1,"role":role,"native_or_control_origin":provenance,
               "selected_reason":reason,"actual_original_source_action":action,
               "public_before":true_before,"public_after":true_after,
               "policy_before_sha256":owner.digest(public),
               "policy_after_sha256":owner.digest(after),
               "mission_masked_for_every_trained_actor":True,
               "original_public_before_sha256":before_sha,
               "original_public_after_sha256":owner.digest(true_after),
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
                if (ack.get("updates")!=1664+len(events) or
                    ack.get("live")!=len(events) or fresh.snapshot()!=checkpoint):
                    raise ValueError("MG14U_GO_COLD_LIVE_CHECKPOINT")
            finally:fresh.close()
        elif ygg is not None:
            checkpoint=ygg.checkpoint()
            if (SuccessorCells.restore(checkpoint).checkpoint()!=checkpoint or
                ygg.samples!=1664+len(events)):
                raise ValueError("MG14U_YGG_COLD_LIVE_CHECKPOINT")
        elif control is not None:
            checkpoint=control.checkpoint()
            if (ConventionalSuccessor.restore(checkpoint).checkpoint()!=checkpoint or
                control.samples!=1664+len(events)):
                raise ValueError("MG14U_CONVENTIONAL_COLD_LIVE_CHECKPOINT")
        else:
            checkpoint=canon({"schema":"mg14u.separate-random-no-learn.v1",
                 "seed":seed,"selected":len(events)}).encode()
        return {"role":role,"environment":environment,"seed_evaluator_only":seed,
            "actual_source_mission":p["DEV"]["mission_by_env"][environment],
            "mission_blind_ablation":True,
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
            "episode_host_wall_s":round(time.perf_counter()-time_start,6),
            "episode_python_cpu_only_s":round(time.process_time()-cpu_start,6),
            "go_child_cpu_included":True,
            "go_child_cpu_s":round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+
                resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime-
                child_before.ru_utime-child_before.ru_stime,6),
            "go_child_max_rss_kib":resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
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
                raise ValueError("MG14U_ORIGINAL_SAME_LAYOUT_SEED_START_MISMATCH")
            if any(row["environment"]!=environment or row["external_actions"]!=0 for row in group):
                raise ValueError("MG14U_ORIGINAL_ACTOR_SOURCE_PARITY_FAILURE")
            rows.extend(group)
    if len(rows)!=24 or any(row["original_live_selected_steps"]<1 for row in rows):
        raise ValueError("MG14U_MISSING_LAYOUT_ROLE_ORIGINAL_EVENT")

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
      "mission_blind_public_projection_for_all_trained_arms":True,
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
       "original_episode_count":24,"external_live_actions":0,
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
    print("MG14U_CLASSIFICATION",report["classification"])
    print("MG14U_ORIGINAL_SOURCE_SHA",report.get("canonical_original_source_sha256","NONE"))
    print("MG14U_SOURCE_COUNTS",json.dumps(report.get("canonical_original_source_evidence",{}).get("per_role_original_source_metrics",{}),sort_keys=True))
    if report["classification"]==BLOCK:
        print("MG14U_BLOCKER",report.get("error_type"),report.get("error"))
    return int(report["classification"]==BLOCK)
if __name__=="__main__":raise SystemExit(main())

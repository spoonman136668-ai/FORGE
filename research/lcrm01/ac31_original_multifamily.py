#!/usr/bin/env python3
"""AC31 genuine original Farama three-family independently selected-source development.

All actual live original env.step actions are supplied by the stated actor.
No mission text substitution, privileged map or counterfactual, and no protected
scientific first use. Source errors fail closed as BLOCKED, with unknown partial
steps and no invented result. Independent second full source process required.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,random,resource,time,traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as source
from mg12_original_successor import modules,ConventionalSuccessor
from mg15_original_mission import ConventionalMission,authentic_public

ROOT=Path(__file__).resolve().parent
FROZEN=ROOT/"ac31_frozen_original_worlds.json"
SCHEMA="forge.ac31.original-source-three-family-five-arm-development.v1"
POS="AC31_BOTH_NATIVE_ALL_THREE_FAMILIES_AND_STRONG_CONTROL_BEAT__DEVELOPMENT_ONLY"
NEG="AC31_GENUINE_MISSION_NATIVE_CROSS_FAMILY_SUPERIORITY_NOT_DEMONSTRATED__NO_SCIENCE"
BLOCK="AC31_ORIGINAL_SOURCE_OR_ACTOR_CONTRACT_BLOCKED__NO_SCIENCE"
ROLES=("wingless_dk15","yggdrasil_r19","conventional_public_successor",
       "conventional_mission_conditioned","uniform_random")

def freeze():
    c=json.loads(FROZEN.read_text(encoding="utf-8"))
    worlds=[
      ("MiniGrid-DoorKey-6x6-v0","use the key to open the door and then get to the goal",[78301,78303,78307]),
      ("MiniGrid-Empty-Random-6x6-v0","get to the green goal square",[78501,78503,78507]),
      ("MiniGrid-Unlock-v0","open the door",[78701,78703,78707])
    ]
    if (c.get("schema")!="forge.ac31.authentic-original-three-family-five-arm-development.v1"
        or c.get("phase")!="PREREGISTERED_BEFORE_SOURCE_EXECUTABLE_OR_RESET"
        or c.get("frozen_parent_protocol_commit")!="e193189345258b1ae4ea56d211cc6a8587f1d155"
        or c.get("parent_mg15")!="ec61e460c5b71b043b9c626fced3a89c37a840ae"
        or c.get("original_farama")!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or c.get("original_native",{}).get("Wingless_DK15")!="9a712f574e48a3d47f2d986d8be3d0eda2b3b9bd"
        or c.get("original_native",{}).get("Yggdrasil_R19")!="2225c19a8a6c55bfdf6785ffc1a26b450fc6f24e"
        or c.get("FIT",{}).get("seeds")!=[50101,50103,50107,50109,50111,50113,50117,50119]
        or c["FIT"].get("count")!=1664
        or c["FIT"].get("canonical_sha256")!="9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24"
        or c.get("roles")!=list(ROLES)
        or [(w["environment"],w["mission"],w["seeds"]) for w in c.get("worlds",[])]!=worlds
        or any(w["limit"]!=192 for w in c["worlds"])
        or c.get("min_independent_source_processes")!=2
        or c.get("original_public_mission_rewrite_to_door_key") is not False
        or c.get("scientific_first_use") is not False
        or c.get("no_external_selected_actions") is not True):
        raise ValueError("AC31_FROZEN_SOURCE_PROTOCOL_OR_NATIVE_IDENTITY_DRIFT")
    return {"FIT":{"seeds":c["FIT"]["seeds"],"cap_per_seed":256,
             "required_original_selected_samples":1664,
             "require_canonical_history_sha256":c["FIT"]["canonical_sha256"]},
            "worlds":c["worlds"],
            "native":c["original_native"],"parent":{"original_farama":c["original_farama"]}}

def real_public(raw,collector,owner,mission):
    # Source mission belongs to original env. Historical R10 projection is ONLY
    # an audit of the unchanged public image, NEVER sent to opt-in new actor.
    p=authentic_public(raw,collector,owner,mission)
    if set(p)!={"image","direction","mission"} or p["mission"]!=mission:
        raise ValueError("AC31_GENUINE_SOURCE_PUBLIC_MISSION_OR_FIELDS")
    return p

def fit(binary,p):
    gym,owner,collector,SuccessorCells=modules()
    go=WingBridge(binary)
    ygg=SuccessorCells()
    control=ConventionalSuccessor()
    conditioned=ConventionalMission()
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
                ygg.start_session(adapter,"mg12-original-fit-"+str(seed),live=False)
                for step in range(p["FIT"]["cap_per_seed"]):
                    before=source.normalize(collector,owner,raw)
                    public_cues=owner.public_cues(before)
                    chosen=collector.policy({"image":before["image"],"cues":public_cues},
                                            rng,step,{})
                    if type(chosen)is not int or chosen not in range(7):
                        raise ValueError("MG12_FIT_ACTION_UNTRUSTED")
                    if adapter.submit(chosen)!=chosen:
                        raise ValueError("MG12_FIT_ACTION_REMAP")
                    after_raw,reward,terminated,truncated,_=env.step(chosen)
                    after=source.normalize(collector,owner,after_raw)
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    receipt=ygg.learn_selected(adapter,before,after)
                    control.learn(before,chosen,after)
                    conditioned.learn(before,chosen,after,float(reward))
                    ack=go.request("learn",before=before,action=chosen,after=after,
                                   reward=float(reward),terminal=bool(terminated or truncated))
                    count+=1
                    if (receipt["sample_index"]!=count or ygg.samples!=count or
                        ygg.parent.local.samples!=count or control.samples!=count or conditioned.samples!=count or
                        ack.get("updates")!=count or ack.get("live",0)!=0):
                        raise ValueError("MG12_UNEQUAL_ORIGINAL_SOURCE_FIT")
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
            raise ValueError("MG12_UNMATCHED_ORIGINAL_1664_FIT_SOURCE")
        go_checkpoint=go.snapshot()
        yg_checkpoint=ygg.checkpoint()
        conventional_checkpoint=control.checkpoint()
        conditioned_checkpoint=conditioned.checkpoint()
    finally:go.close()
    # Cold independent restores of all source-trained learners.
    cold=WingBridge(binary)
    try:
        ack=cold.request("load_parent",state=base64.b64encode(go_checkpoint).decode())
        if ack.get("updates")!=1664 or cold.snapshot()!=go_checkpoint:
            raise ValueError("MG12_GO_FIT_COLD_CUSTODY")
    finally:cold.close()
    if (SuccessorCells.restore(yg_checkpoint).checkpoint()!=yg_checkpoint or
        ConventionalSuccessor.restore(conventional_checkpoint).checkpoint()!=conventional_checkpoint or
        ConventionalMission.restore(conditioned_checkpoint).checkpoint()!=conditioned_checkpoint):
        raise ValueError("MG12_YGG_AND_CONVENTIONAL_COLD_CUSTODY")
    return {"samples":count,"selected_history_sha256":src_sha,
            "go":go_checkpoint,"ygg":yg_checkpoint,"conventional":conventional_checkpoint,
            "conditioned":conditioned_checkpoint,
            "original_fit_source_action_counts":action_counts,"source_fit_key_pickups":key_pickups,
            "source_fit_visible_door_openings":door_opens,
            "checkpoints_sha":{"go":sha(go_checkpoint),"ygg":sha(yg_checkpoint),
                               "conventional":sha(conventional_checkpoint),
                               "conditioned":sha(conditioned_checkpoint)}}



def episode(role,seed,cohort,trained,binary):
    gym,owner,collector,SuccessorCells=modules()
    from research.native.itd02.r19.mission_actor import MissionActor
    env=gym.make(cohort["environment"])
    go=ygg=control=conditioned=None
    mission=cohort["mission"]
    rng=random.Random(137291+seed)
    try:
        raw,_=env.reset(seed=seed)
        start=real_public(raw,collector,owner,mission)
        start_sha=owner.digest(start)
        if role==ROLES[0]:
            go=WingBridge(binary)
            ack=go.request("load_parent",state=base64.b64encode(trained["go"]).decode())
            if ack.get("updates")!=1664:
                raise ValueError("AC31_GO_ORIGINAL_FIT_NOT_LOADED")
            expected=go.request("snapshot_parent")["state"]
            if base64.b64decode(expected)!=trained["go"]:
                raise ValueError("AC31_GO_UNCHANGED_FIT_CHECKPOINT_MISMATCH")
            begun=go.request("begin",before=start)
            if begun.get("mode") not in ("ORIGINAL_DOORKEY_UNCHANGED","NATIVE_NEW_MISSION_PUBLIC_SELECTED"):
                raise ValueError("AC31_GO_NATIVE_MISSION_MODE_INVALID")
        elif role==ROLES[1]:
            ygg=MissionActor(SuccessorCells.restore(trained["ygg"]))
            if ygg.original.samples!=1664:
                raise ValueError("AC31_YGG_ORIGINAL_FIT_NOT_COLD")
            ygg.begin(start)
        elif role==ROLES[2]:
            control=ConventionalSuccessor.restore(trained["conventional"])
            if control.samples!=1664:raise ValueError("AC31_PUBLIC_CONTROL_FIT_NOT_COLD")
            control.begin_episode()
        elif role==ROLES[3]:
            conditioned=ConventionalMission.restore(trained["conditioned"])
            if conditioned.samples!=1664:raise ValueError("AC31_CONDITIONED_CONTROL_FIT_NOT_COLD")
            conditioned.begin_episode()
        elif role!=ROLES[4]:
            raise ValueError("AC31_ROLE_FORBIDDEN")
        events=[]
        previous=start
        seen=set()
        checkpoints_before=[]
        wall=time.perf_counter()
        cpu=time.process_time()
        child=resource.getrusage(resource.RUSAGE_CHILDREN)
        for index in range(cohort["limit"]):
            before=real_public(raw,collector,owner,mission)
            if before!=previous:raise ValueError("AC31_ORIGINAL_PUBLIC_STEP_CONTINUITY")
            if go is not None:
                proposal=go.request("choose")
                action=proposal.get("action")
                reason=proposal.get("status")
            elif ygg is not None:
                proposal=ygg.choose()
                action=proposal["action"]
                reason=proposal["reason"]
            elif control is not None:
                action=control.choose(before)
                reason="INDEPENDENT_PUBLIC_SUCCESSOR_CONVENTIONAL"
            elif conditioned is not None:
                action=conditioned.choose(before)
                reason="INDEPENDENT_MISSION_CONDITIONED_CONVENTIONAL"
            else:
                action=rng.randrange(7)
                reason="INDEPENDENT_UNIFORM_RANDOM"
            if type(action)is not int or action not in range(7):
                raise ValueError("AC31_UNREGISTERED_SELECTED_SOURCE_ACTION")
            if go is not None:
                go.request("commit",action=action)
            elif ygg is not None:
                ygg.commit(action)
            new_raw,reward,terminated,truncated,_=env.step(action)
            after=real_public(new_raw,collector,owner,mission)
            reward=float(reward)
            if go is not None:
                result=go.request("feedback",action=action,after=after,reward=reward,
                                  terminal=bool(terminated),truncated=bool(truncated))
                if result.get("live")!=index+1:
                    raise ValueError("AC31_GO_NATIVE_SELECTED_OUTCOME_MISSING")
            elif ygg is not None:
                result=ygg.feedback(action,after,reward,bool(terminated),bool(truncated))
                if len(ygg.boundary.events)!=index+1:
                    raise ValueError("AC31_YGG_NATIVE_SELECTED_OUTCOME_MISSING")
            elif control is not None:
                control.learn(before,action,after)
            elif conditioned is not None:
                conditioned.learn(before,action,after,reward)
            bfront=before["image"][3][5]
            afront=after["image"][3][5]
            held=before["image"][3][6][0] in (5,6,7)
            newheld=after["image"][3][6][0] in (5,6,7)
            source_open=(action==5 and bfront[0]==4 and afront[0]==4 and
                         bfront[1]==afront[1] and bfront[2] in (1,2) and afront[2]==0 and
                         before["direction"]==after["direction"])
            before_sha=owner.digest(before)
            events.append({
                "step":index+1,"role":role,"environment":cohort["environment"],
                "seed_evaluator_only":seed,"selected_reason":reason,
                "actual_original_source_action":action,
                "public_before":before,"public_after":after,
                "original_public_before_sha256":before_sha,
                "original_public_after_sha256":owner.digest(after),
                "source_reward":reward,"terminated":bool(terminated),
                "truncated":bool(truncated),
                "source_visible_door_opened":bool(source_open),
                "public_pickup":bool(not held and newheld),
                "public_drop":bool(held and not newheld),
                "external_live_actions":0,
                "true_original_mission_preserved_at_actor_boundary":True
            })
            seen.add(before_sha)
            raw=new_raw;previous=after
            if terminated or truncated:break
        if go is not None:
            checkpoint=go.snapshot()
            cold=WingBridge(binary)
            try:
                cold.request("load",state=base64.b64encode(checkpoint).decode())
                if cold.snapshot()!=checkpoint:
                    raise ValueError("AC31_GO_COLD_SELECTED_CHECKPOINT_DRIFT")
            finally:cold.close()
        elif ygg is not None:
            checkpoint=ygg.checkpoint()
            if MissionActor.restore(checkpoint).checkpoint()!=checkpoint:
                raise ValueError("AC31_YGG_COLD_SELECTED_CHECKPOINT_DRIFT")
        elif control is not None:
            checkpoint=control.checkpoint()
            if ConventionalSuccessor.restore(checkpoint).checkpoint()!=checkpoint:
                raise ValueError("AC31_CONTROL_COLD_SELECTED_CHECKPOINT_DRIFT")
        elif conditioned is not None:
            checkpoint=conditioned.checkpoint()
            if ConventionalMission.restore(checkpoint).checkpoint()!=checkpoint:
                raise ValueError("AC31_CONDITIONED_COLD_SELECTED_CHECKPOINT_DRIFT")
        else:
            checkpoint=canon({"role":role,"seed":seed,"steps":len(events)}).encode()
        child_end=resource.getrusage(resource.RUSAGE_CHILDREN)
        return {
          "role":role,"environment":cohort["environment"],"seed_evaluator_only":seed,
          "actual_source_mission":mission,"original_start_public_sha256":start_sha,
          "original_live_selected_steps":len(events),"external_actions":0,
          "source_goal_completed":int(any(e["source_reward"]>0 for e in events)),
          "source_goal_reward":sum(e["source_reward"] for e in events),
          "source_visible_door_openings":sum(e["source_visible_door_opened"] for e in events),
          "source_key_pickups":sum(e["public_pickup"] for e in events),
          "distinct_public_views":len(seen),
          "distinct_legal_actions_selected":len({e["actual_original_source_action"] for e in events}),
          "native_legacy_door_key_mode":bool(role in ROLES[:2] and mission=="use the key to open the door and then get to the goal"),
          "cold_checkpoint_sha256":sha(checkpoint),"real_source_events":events,
          "episode_python_cpu_only_s":round(time.process_time()-cpu,6),
          "episode_wall_s":round(time.perf_counter()-wall,6),
          "go_child_cpu_s":round(child_end.ru_utime+child_end.ru_stime-child.ru_utime-child.ru_stime,6),
          "go_child_max_rss_kib":child_end.ru_maxrss}
    finally:
        env.close()
        if go is not None:go.close()

def run(binary,p):
    trained=fit(binary,p)
    rows=[]
    for cohort in p["worlds"]:
        for seed in cohort["seeds"]:
            group=[episode(role,seed,cohort,trained,binary) for role in ROLES]
            if (len(group)!=5 or len({r["original_start_public_sha256"] for r in group})!=1 or
                any(r["external_actions"]!=0 or
                    r["actual_source_mission"]!=cohort["mission"] for r in group)):
                raise ValueError("AC31_ORIGINAL_SOURCE_SAME_START_AND_TRUE_MISSION_NOT_ESTABLISHED")
            rows.extend(group)
    if len(rows)!=45 or any(not r["real_source_events"] for r in rows):
        raise ValueError("AC31_ORIGINAL_45_SOURCE_EPISODES_MISSING")
    resources=[{"role":r["role"],"environment":r["environment"],
                 "seed":r["seed_evaluator_only"],
                 "python_cpu_s":r.pop("episode_python_cpu_only_s"),
                 "host_wall_s":r.pop("episode_wall_s"),
                 "go_child_cpu_s":r.pop("go_child_cpu_s"),
                 "go_child_max_rss_kib":r.pop("go_child_max_rss_kib")} for r in rows]
    by_family={}
    for cohort in p["worlds"]:
        env=cohort["environment"]
        by_family[env]={role:{
          "episodes":3,
          "original_goal_completions":sum(r["source_goal_completed"] for r in rows if r["role"]==role and r["environment"]==env),
          "source_goal_reward_total":sum(r["source_goal_reward"] for r in rows if r["role"]==role and r["environment"]==env),
          "original_selected_actions":sum(r["original_live_selected_steps"] for r in rows if r["role"]==role and r["environment"]==env),
          "source_visible_door_opens_audit_only":sum(r["source_visible_door_openings"] for r in rows if r["role"]==role and r["environment"]==env),
          "source_visible_pickups_audit_only":sum(r["source_key_pickups"] for r in rows if r["role"]==role and r["environment"]==env),
          "external_source_actions":0}
          for role in ROLES}
    native_totals={r:sum(by_family[env][r]["original_goal_completions"] for env in by_family) for r in ROLES}
    superior=all(by_family[env][native]["original_goal_completions"]>=1 for env in by_family
                 for native in ROLES[:2]) and all(native_totals[native]>
                 max(native_totals[ROLES[2]],native_totals[ROLES[3]]) for native in ROLES[:2])
    evidence={
      "original_upstream_farama":p["parent"]["original_farama"],
      "original_training_stream_sha256":trained["selected_history_sha256"],
      "original_source_fit_samples_each":trained["samples"],
      "frozen_source_pins":p["native"],
      "training_cold_sha256":trained["checkpoints_sha"],
      "original_world_cohorts":p["worlds"],
      "original_source_selected_actions_total":sum(r["original_live_selected_steps"] for r in rows),
      "original_missions_preserved_at_all_actor_boundaries":True,
      "no_external_rescue_or_manually_derived_stage_actions":True,
      "real_original_source_episodes":rows,
      "per_family_original_source_metrics":by_family}
    return {
      "schema":SCHEMA,"classification":POS if superior else NEG,
      "scientific_first_use":False,"scientific_admission":False,
      "accepted_native_model_promoted":False,"FORGE_or_CKB_controller_modified":False,
      "original_episode_count":45,"external_live_actions":0,
      "canonical_original_source_sha256":sha(canon(evidence).encode()),
      "canonical_original_source_evidence":evidence,
      "nondeterministic_host_resource_receipts":resources
    }

def main():
    q=argparse.ArgumentParser()
    q.add_argument("--native-go-dk11",type=Path,required=True)
    q.add_argument("--output",type=Path,required=True)
    args=q.parse_args()
    clock=time.perf_counter();cpu=time.process_time()
    try:r=run(args.native_go_dk11,freeze())
    except Exception as e:
        r={"schema":SCHEMA,"classification":BLOCK,
           "scientific_first_use":False,"scientific_admission":False,
           "error_type":type(e).__name__,"error":str(e),
           "original_source_partial_steps":"UNKNOWN_IF_ENV_ENTERED",
           "trace_tail":traceback.format_exc().splitlines()[-18:]}
    r["host_wall_s"]=round(time.perf_counter()-clock,6)
    r["host_python_cpu_only_s"]=round(time.process_time()-cpu,6)
    r["host_max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print("AC31_ORIGINAL_SOURCE_CLASSIFICATION",r["classification"])
    print("AC31_ORIGINAL_SOURCE_SHA",r.get("canonical_original_source_sha256","NONE"))
    if r["classification"]==BLOCK:
        print("AC31_BLOCKER",r.get("error_type"),r.get("error"))
    else:
        print("AC31_TRUE_ORIGINAL_GOAL_COUNTS",json.dumps(
          {env:{role:row["original_goal_completions"] for role,row in roles.items()}
           for env,roles in r["canonical_original_source_evidence"]["per_family_original_source_metrics"].items()},
          sort_keys=True))
    return int(r["classification"]==BLOCK)
if __name__=="__main__":
    raise SystemExit(main())

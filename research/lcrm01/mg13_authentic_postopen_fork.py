#!/usr/bin/env python3
"""MG13 controlled source-authentic open-door fork, NOT unassisted task learning.

Evaluator privately reproduces previously recorded original MG11 actor-selected
actions and verifies *every* public before/action/after/reward/terminal receipt.
No replay prefix or seed/goal/pose/route is supplied to native learners.
Their separate selected action streams BEGIN after the verified opening.
The pre-established door opening is an experimental precondition, NOT an action
the tested actor learned to perform or a held-out world.
"""
import argparse,base64,hashlib,json,random,resource,time,traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as source
import mg10_stage_free_original_doorkey as mg10
import mg11_authentic_selected_novelty as prior
from mg11_authentic_selected_novelty import modules,IndependentNovelty
from mg12_conventional_two_step import PublicTwoStep,independent_fit

SCHEMA="itd02.mg13.authenticated-original-open-door-public-fork.v1"
BLOCKED="MG13_AUTHENTIC_ORIGINAL_SOURCE_FORK_INTEGRITY_BLOCKED__NO_SCIENCE"
NEGATIVE="MG13_POSTOPEN_NATIVE_GOAL_NOT_ESTABLISHED__NO_SCIENCE"
POSITIVE="MG13_BOTH_NATIVE_POSTOPEN_GOAL_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=("wingless_go_dk12","wingless_go_dk11","yggdrasil_r16",
       "yggdrasil_r15","conventional_public_novelty",
       "conventional_two_step_public_model","conventional_seeded_random","frozen_ygg_r16")
NATIVE=("wingless_go_dk12","yggdrasil_r16")
PREREG=Path(__file__).with_name("mg13_postopen_source_prereg.json")

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    x=p["protocol"];s=p["original_source"]
    if (p.get("schema")!="itd02.mg13.original-minigrid-postopen-source-fork.v1"
        or p["parent"]["sha"]!="0ec12ea47f4ca7db279b3d50fb18ad8ec3735b11"
        or s["farama_commit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or s["unchanged_MG11_evaluator_blob"]!="89f68a4f97232cd63cdbb2675e1deb53d75abfcb"
        or s["unchanged_MG12_classical_blob"]!="6b5e89c69700a5e4c730e415567ea8d4419c0cc8"
        or len(p["boundaries"])!=3 or
        [b["id"] for b in p["boundaries"]]!=["71303_go116","71303_ygg37","71307_ygg118"]
        or x["actual_original_live_actor_selected_actions_per_episode"]!=16
        or x["native_original_FIT_selected_public_count"]!=1664
        or x["original_action_ids"]!=list(range(7))
        or x["actor_roles"]!=list(ROLES)
        or x["learner_receives_replay_action_prefix"] is not False
        or x["learner_receives_global_map_or_absolute_pose"] is not False
        or p["outcomes"]["blocked"]!=BLOCKED
        or p["outcomes"]["negative"]!=NEGATIVE
        or p["outcomes"]["bounded"]!=POSITIVE):
        raise ValueError("MG13_FROZEN_ORIGINAL_SOURCE_FORK_PREREG_CHANGED")
    for b in p["boundaries"]:
        if (len(b["replay_selected_actions"])!=b["original_open_ordinal"]
            or b["replay_selected_actions"][-1]!="5"
            or any(v not in "0123456" for v in b["replay_selected_actions"])
            or len(b["exact_prefix_trace_sha256"])!=64):
            raise ValueError("MG13_SOURCE_REPLAY_STEPS_NOT_PREREGISTERED")
    return p

def replay_verified(env,boundary,owner,collector):
    raw,_=env.reset(seed=boundary["seed"])
    collected=[]
    last=None
    for ordinal,raw_action in enumerate(boundary["replay_selected_actions"],1):
        before=source.normalize(collector,owner,raw)
        chosen=int(raw_action)
        nxt,reward,terminated,truncated,_=env.step(chosen)
        after=source.normalize(collector,owner,nxt)
        collected.append([ordinal,chosen,owner.digest(before),owner.digest(after),
                          float(reward),bool(terminated),bool(truncated)])
        last=(before,after,chosen,float(reward),bool(terminated or truncated))
        raw=nxt
        if terminated or truncated:
            raise ValueError("MG13_ORIGINAL_REPLAY_ENDED_BEFORE_VERIFIED_DOOR_OPEN")
    transcript=sha(canon(collected).encode())
    if transcript!=boundary["exact_prefix_trace_sha256"]:
        raise ValueError("MG13_REPLAY_ACTUAL_FARAMA_DIFFERS_FROM_ORIGINAL_MG11_TRACE")
    before,after,action,reward,terminal=last
    front=before["image"][3][5];front_after=after["image"][3][5]
    if (action!=5 or terminal or
        front[0]!=4 or front_after[0]!=4 or
        front[2]==0 or front_after[2]!=0 or
        owner.digest(after)!=boundary["original_open_public_after_sha256"]):
        raise ValueError("MG13_SOURCE_DOOR_OPENING_NOT_AUTHENTIC")
    return raw,{"prefix_sha":transcript,"last_open_public_after_sha":owner.digest(after),
                "evaluator_controlled_replay_actions":len(collected)}

def episode(role,boundary,fit,new_go,old_go,p):
    seed=boundary['seed']
    gym,owner,collector,conv,R16,R15=modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    go=None;y=None;ordinary=None;control=None;episode_memory=None;two=None
    rng=random.Random(97011+seed)
    try:
        raw,replay_receipt=replay_verified(env,boundary,owner,collector)
        first=source.normalize(collector,owner,raw)
        first_sha=owner.digest(first)
        adapter.reset_public(first)
        if role in ("wingless_go_dk12","wingless_go_dk11"):
            go=WingBridge(new_go if role=="wingless_go_dk12" else old_go)
            raw_checkpoint=fit["go12" if role=="wingless_go_dk12" else "go11"]
            ack=go.request("load",state=base64.b64encode(raw_checkpoint).decode())
            if ack.get("updates")!=1664 or ack.get("live",0)!=0:
                raise ValueError("MG11_COLD_GO_FIT_MISMATCH")
            go.request("begin_episode")
        elif role in ("yggdrasil_r16","yggdrasil_r15","frozen_ygg_r16"):
            y=R16.restore(fit["y16"]) if role!="yggdrasil_r15" else R15.restore(fit["y15"])
            y.start_session(adapter,"mg13-independent-public-fork-"+role,live=True)
            frozen=y.checkpoint()
        elif role=="conventional_two_step_public_model":
            two=PublicTwoStep.restore(fit['two_step'])
            two.begin_episode()
        else:
            ordinary=mg10.Conventional.restore(fit["conventional"])
            control=conv.Control.restore(fit["c30"])
            episode_memory=IndependentNovelty()
        seen_actions=set()
        events=[]
        for i in range(p["max_original_steps"]):
            before=source.normalize(collector,owner,raw)
            if before!=adapter.current:raise ValueError("MG11_NOT_ACTUAL_PUBLIC_SOURCE")
            if go is not None:
                proposal=go.request("choose",before=before)  # NO stage objective
                act=proposal.get("action");reason=proposal.get("status")
            elif y is not None:
                proposal=y.choose(before)
                act=proposal["action"];reason=proposal["status"]
            elif role=="conventional_public_novelty":
                act=episode_memory.choose(before);reason="CONVENTIONAL_OWN_PUBLIC_NOVELTY"
            elif role=="conventional_two_step_public_model":
                act=two.choose(before);reason="CONVENTIONAL_INDEPENDENT_PUBLIC_TWO_STEP"
            else:
                act=rng.randrange(7);reason="CONVENTIONAL_UNIFORM_SEEDED_RANDOM"
            if type(act)is not int or act not in range(7):
                raise ValueError("MG11_ACTION_NOT_FROM_ACTOR")
            if go is not None:
                ack=go.request("commit",before=before,action=act)
                if ack.get("updates")!=1664+i:
                    raise ValueError("MG11_GO_PENDING_SOURCE_NOT_COMMITTED")
            if adapter.submit(act)!=act:raise ValueError("MG11_SOURCE_ACTION_REMAP")
            nxt,reward,terminated,truncated,_=env.step(act)
            after=source.normalize(collector,owner,nxt)
            event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=before,action=act,
                     after=after,reward=float(reward),terminal=bool(terminated or truncated))
                if ack.get("updates")!=1664+i+1 or ack.get("live")!=i+1:
                    raise ValueError("MG11_GO_ORIGINAL_SOURCE_CREDIT_LOST")
            elif role in ("yggdrasil_r16","yggdrasil_r15"):
                receipt=y.learn_selected(adapter,before,after)
                if y.samples!=1664+i+1 or receipt["sample_index"]!=1664+i+1:
                    raise ValueError("MG11_YGG_ORIGINAL_SOURCE_CREDIT_LOST")
            elif role=="frozen_ygg_r16":
                if y.checkpoint()!=frozen or y.samples!=1664:
                    raise ValueError("MG11_FROZEN_NATIVE_LEARNED")
            elif role=="conventional_public_novelty":
                ordinary.observe(before,act,after)
                episode_memory.observe(before,act,after)
                control.learn(event)
                if ordinary.count!=1664+i+1 or control.samples!=1664+i+1:
                    raise ValueError("MG11_CONVENTIONAL_NOT_MATCHED_REAL_FEEDBACK")
            elif role=="conventional_two_step_public_model":
                two.observe(before,act,after)
                if two.count!=1664+i+1:
                    raise ValueError("MG13_CLASSICAL_OWN_SELECTED_PUBLIC_CREDIT")
            else:
                if ordinary.count!=1664 or control.samples!=1664:
                    raise ValueError("MG11_RANDOM_CONTROL_STORED_LEARNED_DATA")
            held=before["image"][3][6][0] in (5,6,7)
            held_after=after["image"][3][6][0] in (5,6,7)
            front=before["image"][3][5];front_after=after["image"][3][5]
            door=(front[0]==4 and front_after[0]==4 and front[2]!=front_after[2])
            seen_actions.add(act)
            events.append({"index":i+1,"public_before":before,"action":act,
                "policy_origin":reason,"public_after":after,"original_reward":float(reward),
                "terminated":bool(terminated),"truncated":bool(truncated),
                "public_held_gain":bool(not held and held_after),
                "public_held_loss":bool(held and not held_after),
                "public_key_front_door":bool(held and front[0]==4),
                "public_actual_door_change":bool(door),"external_action_count":0,
                "before_sha":owner.digest(before),"after_sha":owner.digest(after)})
            raw=nxt
            if terminated or truncated:break
        if go is not None:
            cp=go.snapshot();cold=WingBridge(new_go if role=="wingless_go_dk12" else old_go)
            try:
                a=cold.request("load",state=base64.b64encode(cp).decode())
                if (a.get("updates")!=1664+len(events) or a.get("live")!=len(events)
                    or cold.snapshot()!=cp):raise ValueError("MG11_GO_REAL_SOURCE_COLD_FAILED")
            finally:cold.close()
        elif y is not None:
            cp=y.checkpoint()
            rest=(R15 if role=="yggdrasil_r15" else R16).restore(cp)
            expected=1664+(0 if role=="frozen_ygg_r16" else len(events))
            if rest.samples!=expected or rest.checkpoint()!=cp:
                raise ValueError("MG11_YGG_REAL_SOURCE_COLD_FAILED")
            if role=="frozen_ygg_r16" and cp!=frozen:
                raise ValueError("MG11_FROZEN_SOURCE_WAS_CHANGED")
        elif role=="conventional_two_step_public_model":
            cp=two.checkpoint()
            if PublicTwoStep.restore(cp).checkpoint()!=cp:
                raise ValueError("MG13_TWO_STEP_COLD_SELECTED_SOURCE_LOSS")
        else:
            cp=ordinary.checkpoint()
            if mg10.Conventional.restore(cp).checkpoint()!=cp:
                raise ValueError("MG11_CONVENTIONAL_COLD_FAILED")
            if role=="conventional_public_novelty" and episode_memory.steps!=len(events):
                raise ValueError("MG11_NO_INDEPENDENT_SOURCE_EPISODE_CREDIT")
        return {"role":role,"evaluator_seed_only":seed,
             "source_replay_boundary_id":boundary['id'],
             "source_replay_prefix_length":len(boundary['replay_selected_actions']),
             "source_replay_prefix_sha":replay_receipt['prefix_sha'],
             "original_public_start_sha":first_sha,
             "real_original_source_actions":len(events),
             "distinct_original_selected_actions":len(seen_actions),
             "external_actions":0,
             "original_key_acquisitions":sum(x["public_held_gain"] for x in events),
             "original_key_losses":sum(x["public_held_loss"] for x in events),
             "original_key_front_door":sum(x["public_key_front_door"] for x in events),
             "actual_original_door_changes":sum(x["public_actual_door_change"] for x in events),
             "original_goal_rewards":sum(x["original_reward"]>0 for x in events),
             "original_cold_checkpoint_sha256":sha(cp),
             "all_original_public_selected_events":events}
    finally:
        env.close()
        if go is not None:go.close()


def run(go12,go11,p):
    fit_options={"source_FIT_seeds":p["protocol"]["native_FIT_seeds"]}
    trained=prior.train(go12,fit_options)
    control_fit=independent_fit({"original_FIT_seeds":p["protocol"]["native_FIT_seeds"]},
                                trained["source_history_sha256"])
    trained["two_step"]=control_fit["checkpoint"]
    evidence_rows=[]
    for b in p["boundaries"]:
        batch=[episode(role,b,trained,go12,go11,
            {"max_original_steps":p["protocol"]["actual_original_live_actor_selected_actions_per_episode"]})
               for role in ROLES]
        if (len(batch)!=8 or len({x["original_public_start_sha"] for x in batch})!=1
            or batch[0]["original_public_start_sha"]!=b["original_open_public_after_sha256"]
            or len({x["source_replay_prefix_sha"] for x in batch})!=1):
            raise ValueError("MG13_ORIGINAL_SOURCE_START_NOT_EQUIVALENT")
        evidence_rows.extend(batch)
    if len(evidence_rows)!=24:
        raise ValueError("MG13_SOURCE_FORK_COVERS_FEWER_THAN_EIGHT_ROLES")
    summaries={}
    for role in ROLES:
        matching=[x for x in evidence_rows if x["role"]==role]
        summaries[role]={
            "authenticated_postopen_forks":len(matching),
            "real_independently_selected_actions":sum(x["real_original_source_actions"] for x in matching),
            "minimum_selected_action_diversity_per_fork":min(x["distinct_original_selected_actions"] for x in matching),
            "original_positive_goal_rewards":sum(x["original_goal_rewards"] for x in matching),
            "original_actual_door_state_changes":sum(x["actual_original_door_changes"] for x in matching),
            "key_public_front_door_frames":sum(x["original_key_front_door"] for x in matching),
            "first_forward_action_ordinals":[next((i for i,e in
                enumerate(x["all_original_public_selected_events"],1) if e["action"]==2),None)
                for x in matching],
            "original_source_replay_actions_evaluator_only":
                sum(x["source_replay_prefix_length"] for x in matching)}
    positive=all(summaries[r]["original_positive_goal_rewards"]>=1 for r in NATIVE)
    evidence={"schema":SCHEMA,
        "source_original_farama":p["original_source"]["farama_commit"],
        "source_original_MG11_artifact":p["original_source"]["mg11_full_source_artifact"],
        "original_known_development_boundaries":p["boundaries"],
        "source_FIT_selected_history_sha":trained["source_history_sha256"],
        "independent_two_step_same_source_FIT_sha":control_fit["source_selected_sha"],
        "native_original_cold_FIT_checkpoints":trained["original_fit_checkpoints"],
        "independent_two_step_cold_FIT_sha":sha(control_fit["checkpoint"]),
        "true_original_source_fork_and_actor_events":evidence_rows,
        "per_role_public_fork_metrics":summaries,
        "no_replay_prefix_given_to_actors":True,
        "live_original_external_navigator_actions":0,
        "replay_before_measurement_is_evaluator_controlled":True,
        "no_native_model_changed":True}
    return {"schema":SCHEMA,"classification":POSITIVE if positive else NEGATIVE,
        "scientific_first_use":False,"native_model_promoted":False,
        "accepted_checkpoint_changed":False,"controller_changed":False,
        "authenticated_source_forks":3,"independent_live_episodes":24,
        "matched_original_source_FIT_count":1664,
        "live_external_actions":0,
        "canonical_source_digest":sha(canon(evidence).encode()),
        "canonical_original_source_evidence":evidence}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk12",type=Path,required=True)
    parser.add_argument("--wingless-dk11",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();t=time.perf_counter();cpu=time.process_time()
    try:result=run(args.wingless_dk12,args.wingless_dk11,freeze())
    except Exception as exc:
        result={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
            "error_type":type(exc).__name__,"error":str(exc),
            "trace_tail":traceback.format_exc().splitlines()[-18:]}
    result["host_wall_seconds"]=round(time.perf_counter()-t,6)
    result["host_cpu_seconds"]=round(time.process_time()-cpu,6)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG13_CLASSIFICATION",result["classification"])
    print("MG13_SOURCE_DIGEST",result.get("canonical_source_digest","NONE"))
    print("MG13_RESULTS",json.dumps(result.get("canonical_original_source_evidence",{}).get(
        "per_role_public_fork_metrics",{}),sort_keys=True))
    if result["classification"]==BLOCKED:print("MG13_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0
if __name__=="__main__":raise SystemExit(main())

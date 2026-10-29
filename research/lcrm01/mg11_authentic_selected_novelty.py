#!/usr/bin/env python3
"""MG11 prospective original Farama DoorKey selected-public action novelty.

Real original env.step only, no manually supplied stage, private pose, map,
future reward or C29 external action during live episodes. Frozen native source.
"""
import argparse,base64,hashlib,json,random,resource,time,traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as source
import mg04_public_effect_native_agency as original
import mg10_stage_free_original_doorkey as mg10

SCHEMA="itd02.mg11.authentic-public-selected-action-novelty.v1"
BLOCKED="MG11_SOURCE_OR_NOVELTY_CUSTODY_BLOCKED__NO_SCIENCE"
NEGATIVE="MG11_NATIVE_NOVELTY_TASK_GAIN_NOT_ESTABLISHED__NO_SCIENCE"
POSITIVE="MG11_BOTH_NATIVE_SOURCE_GOAL_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=("wingless_go_dk12","wingless_go_dk11","yggdrasil_r16",
       "yggdrasil_r15","conventional_public_novelty",
       "conventional_seeded_random","frozen_ygg_r16")
PRE=Path(__file__).with_name("mg11_public_selected_novelty_prereg.json")
NATIVE=("wingless_go_dk12","yggdrasil_r16")

def freeze():
    p=json.loads(PRE.read_text())
    if (p.get("schema")!="itd02.mg11.original-public-selected-novelty.v1"
       or p.get("parent_sha")!="e187b5e137490f94300f1bdc1982fd599731fbdd"
       or p["source_FIT_count"]!=1664
       or p["development_seeds"]!=[71301,71303,71307]
       or p["max_original_steps"]!=192 or p["actual_external_live_actions"]!=0
       or p["roles"]!=list(ROLES)
       or p["new_go"]=="PIN_AFTER_QUAL" or p["new_ygg"]=="PIN_AFTER_QUAL"
       or p["classification"]["blocked"]!=BLOCKED
       or p["classification"]["negative"]!=NEGATIVE
       or p["classification"]["positive"]!=POSITIVE):
        raise ValueError("MG11_SOURCE_PRE_REGISTERED_RULE_DRIFT")
    return p

def modules():
    gym,owner,_,_,collector,conv=original.get_modules()
    from research.native.itd02.r16.selected_novelty import NativeNovelty
    from research.native.itd02.r15.continuity_cells import NativeContinuity
    return gym,owner,collector,conv,NativeNovelty,NativeContinuity

class IndependentNovelty:
    """Independently authored equal-public classical selected episode control."""
    def __init__(self):
        self.count={};self.novel={};self.loops={};self.next={}
        self.seen={};self.steps=0
    def _key(self,p):
        if set(p)!={"image","direction","mission"}:
            raise ValueError("MG11_CONVENTIONAL_PRIVATE_OBSERVATION")
        return sha(canon(p).encode())
    def choose(self,b):
        state=self._key(b);row=self.count.get(state,{})
        shift=int(state[:2],16)%7
        for i in range(7):
            action=(shift+i)%7
            if row.get(str(action),0)==0:return action
        scores={}
        for a in range(7):
            action=str(a);dest=self.next.get(state,{}).get(action)
            scores[a]=(4*self.novel.get(state,{}).get(action,0)
                       -3*row[action]-2*self.loops.get(state,{}).get(action,0)
                       -min(2,self.seen.get(dest,0)) if dest is not None else -3*row[action])
        best=max(scores.values())
        for i in range(7):
            action=(shift+i)%7
            if scores[action]==best:return action
        raise ValueError("MG11_CLASSICAL_NO_PUBLIC_SOURCE_ACTION")
    def observe(self,b,a,after):
        if self.steps>=192 or type(a)is not int or a not in range(7):
            raise ValueError("MG11_BAD_ORIGINAL_SELECTED_CONVENTIONAL")
        before=self._key(b);next_state=self._key(after);action=str(a)
        row=self.count.setdefault(before,{})
        row[action]=row.get(action,0)+1
        if self.seen.get(next_state,0)==0:
            novelty=self.novel.setdefault(before,{})
            novelty[action]=novelty.get(action,0)+1
        if before==next_state:
            loops=self.loops.setdefault(before,{})
            loops[action]=loops.get(action,0)+1
        self.next.setdefault(before,{})[action]=next_state
        self.seen[next_state]=self.seen.get(next_state,0)+1
        self.steps+=1
    def snapshot(self):
        return canon({"count":self.count,"novel":self.novel,"loops":self.loops,
                      "next":self.next,"seen":self.seen,"steps":self.steps}).encode()

def train(go_new,p):
    gym,owner,collector,conv,R16,R15=modules()
    wing=WingBridge(go_new)
    ygg=R16()
    ordinary=mg10.Conventional()
    control=conv.Control()
    count=0;d=hashlib.sha256();action_counts={str(a):0 for a in range(7)}
    try:
        for index,seed in enumerate(p["source_FIT_seeds"]):
            env=gym.make("MiniGrid-DoorKey-8x8-v0")
            adapter=owner.DoorKeyPublicAdapter()
            rng=random.Random(93617+7919*index)
            try:
                raw,_=env.reset(seed=seed)
                adapter.reset_public(collector.normalized_original_public(raw))
                ygg.start_session(adapter,"mg11-auth-original-FIT-"+str(seed),live=False)
                for step in range(256):
                    before=source.normalize(collector,owner,raw)
                    action=collector.policy(
                        {"image":before["image"],"cues":owner.public_cues(before)},
                        rng,step,{})
                    if type(action)is not int or action not in range(7):
                        raise ValueError("MG11_ORIGINAL_FIT_FAKE_SOURCE_ACTION")
                    if adapter.submit(action)!=action:
                        raise ValueError("MG11_ACTUAL_FIT_SELECTED_REMAP")
                    nxt,reward,terminated,truncated,_=env.step(action)
                    after=source.normalize(collector,owner,nxt)
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    ygg.learn_selected(adapter,before,after)
                    ordinary.observe(before,action,after)
                    control.learn(event)
                    ack=wing.request("learn",before=before,action=action,
                       after=after,reward=float(reward),terminal=bool(terminated or truncated))
                    count+=1;action_counts[str(action)]+=1
                    if (ack.get("updates")!=count or ygg.samples!=count or
                        ordinary.count!=count or control.samples!=count):
                        raise ValueError("MG11_SOURCE_SELECTED_COUNT_NOT_EQUAL")
                    d.update((canon({"before":before,"action":action,"after":after,
                        "reward":float(reward),"terminal":bool(terminated or truncated)})+"\n").encode())
                    raw=nxt
                    if terminated or truncated:break
            finally:env.close()
        if count!=1664 or any(n==0 for n in action_counts.values()):
            raise ValueError("MG11_INSUFFICIENT_FIXED_PUBLIC_FIT")
        go12=wing.snapshot()
        y16=ygg.checkpoint()
        conventional=ordinary.checkpoint()
        c30=control.checkpoint()
    finally:wing.close()
    # Extract unchanged original parent checkpoint from an authenticated
    # newly qualified opt-in native wrapper. Original selected FIT is identical.
    inner_go=base64.b64decode(json.loads(go12)["state"]["inner"],validate=True)
    inner_y=json.loads(y16)["state"]["inner"].encode("utf-8")
    test_go=WingBridge(go_new)
    try:
        ack=test_go.request("load",state=base64.b64encode(go12).decode())
        if ack.get("updates")!=1664 or test_go.snapshot()!=go12:
            raise ValueError("MG11_GO_SOURCE_CHECKPOINT_DRIFT")
    finally:test_go.close()
    if (R16.restore(y16).checkpoint()!=y16 or R15.restore(inner_y).checkpoint()!=inner_y
        or mg10.Conventional.restore(conventional).checkpoint()!=conventional
        or conv.Control.restore(c30).checkpoint()!=c30):
        raise ValueError("MG11_SOURCE_COLD_RESTORE_NOT_EQUAL")
    return {"go12":go12,"go11":inner_go,"y16":y16,"y15":inner_y,
      "conventional":conventional,"c30":c30,"samples":count,
      "source_history_sha256":d.hexdigest(),"source_action_counts":action_counts,
      "original_fit_checkpoints":{"go12":sha(go12),"go11":sha(inner_go),
       "y16":sha(y16),"y15":sha(inner_y),"conventional":sha(conventional)}}

def episode(role,seed,fit,new_go,old_go,p):
    gym,owner,collector,conv,R16,R15=modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    go=None;y=None;ordinary=None;control=None;episode_memory=None
    rng=random.Random(97011+seed)
    try:
        raw,_=env.reset(seed=seed)
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
            y.start_session(adapter,"mg11-original-"+role+"-"+str(seed),live=True)
            frozen=y.checkpoint()
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
        else:
            cp=ordinary.checkpoint()
            if mg10.Conventional.restore(cp).checkpoint()!=cp:
                raise ValueError("MG11_CONVENTIONAL_COLD_FAILED")
            if role=="conventional_public_novelty" and episode_memory.steps!=len(events):
                raise ValueError("MG11_NO_INDEPENDENT_SOURCE_EPISODE_CREDIT")
        return {"role":role,"evaluator_seed_only":seed,
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

def run(new_go,old_go,p):
    fitted=train(new_go,p);records=[]
    for seed in p["development_seeds"]:
        group=[episode(role,seed,fitted,new_go,old_go,p) for role in ROLES]
        if len({r["original_public_start_sha"] for r in group})!=1:
            raise ValueError("MG11_ORIGINAL_PUBLIC_START_NOT_MATCHED")
        records.extend(group)
    if len(records)!=21 or any(r["real_original_source_actions"]<1 for r in records):
        raise ValueError("MG11_INCOMPLETE_ORIGINAL_ENV_EXPERIMENT")
    summary={}
    for role in ROLES:
        arr=[r for r in records if r["role"]==role]
        summary[role]={"episodes":3,
          "true_original_selected_actions":sum(r["real_original_source_actions"] for r in arr),
          "min_distinct_actions_per_episode":min(r["distinct_original_selected_actions"] for r in arr),
          "key_gains":sum(r["original_key_acquisitions"] for r in arr),
          "key_losses":sum(r["original_key_losses"] for r in arr),
          "key_front_door":sum(r["original_key_front_door"] for r in arr),
          "real_door_changes":sum(r["actual_original_door_changes"] for r in arr),
          "original_goal_rewards":sum(r["original_goal_rewards"] for r in arr),
          "external_actions":0}
    positive=all(summary[n]["original_goal_rewards"]>=1 and
          summary[n]["min_distinct_actions_per_episode"]>=3 for n in NATIVE)
    evidence={"schema":SCHEMA,"original_farama":p["source_farama"],
       "model_source_pins":{"new_go":p["new_go"],"new_ygg":p["new_ygg"]},
       "same_original_public_FIT_source_sha":fitted["source_history_sha256"],
       "same_FIT_selected_counts":fitted["source_action_counts"],
       "source_fit_checkpoint_sha":fitted["original_fit_checkpoints"],
       "original_public_selected_records":records,
       "per_role_original_results":summary,
       "no_manual_stage_or_external_route":True,"external_actions":0}
    return {"schema":SCHEMA,"classification":POSITIVE if positive else NEGATIVE,
      "scientific_first_use":False,"native_model_promoted":False,
      "FORGE_controller_changed":False,"accepted_original_source_changed":False,
      "source_FIT_original_count":1664,"actual_source_episodes":21,"external_live_actions":0,
      "canonical_original_selected_sha":sha(canon(evidence).encode()),
      "original_public_source_evidence":evidence}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk12",type=Path,required=True)
    parser.add_argument("--wingless-dk11",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    options=parser.parse_args()
    t=time.perf_counter();c=time.process_time()
    try:result=run(options.wingless_dk12,options.wingless_dk11,freeze())
    except Exception as e:
        result={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
          "error_type":type(e).__name__,"error":str(e),
          "trace_tail":traceback.format_exc().splitlines()[-14:]}
    result["host_wall_s"]=round(time.perf_counter()-t,6)
    result["host_cpu_s"]=round(time.process_time()-c,6)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    options.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG11_CLASSIFICATION",result["classification"])
    print("MG11_SOURCE_SHA",result.get("canonical_original_selected_sha","NONE"))
    print("MG11_RESULTS",json.dumps(result.get("original_public_source_evidence",{}).get("per_role_original_results",{}),sort_keys=True))
    if result["classification"]==BLOCKED:
        print("MG11_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0
if __name__=="__main__":raise SystemExit(main())

#!/usr/bin/env python3
"""MG07: real original Farama DoorKey temporal readouts with no live assistance.

Independent native Go DK10 over original DK9/DK8, native Yggdrasil R14 over
unchanged R13/R11, both native predecessors, and a separately implemented
conventional C30 public temporal control. The original models are NOT edited.
"""
import argparse
import base64
import hashlib
import json
import resource
import time
import traceback
from pathlib import Path

from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as source
import mg04_public_effect_native_agency as original
import mg06_original_doorkey_exploration as previous

FROZEN=Path(__file__).with_name("mg07_public_temporal_credit_prereg.json")
SCHEMA="itd02.mg07.original-doorkey-temporal-native-selected-source.v1"
BLOCKED="MG07_SOURCE_OR_FAIR_NATIVE_TEMPORAL_CUSTODY_BLOCKED__NO_SCIENCE"
NEGATIVE="MG07_TEMPORAL_SOURCE_PUBLIC_MEMORY_NOT_GOAL_SOLVING__NO_SCIENCE"
POSITIVE="MG07_BOUNDED_PUBLIC_TEMPORAL_GOAL_ACTION_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=("wingless_go_dk10","wingless_go_dk9","yggdrasil_r14",
       "yggdrasil_r13","conventional_public_temporal")

def freeze():
    data=json.loads(FROZEN.read_text(encoding="utf-8"))
    pins=data["future_native_new_source_commit"]
    if (data["schema"]!="itd02.mg07.authentic-original-doorkey-public-temporal-memory.v1"
        or data["source_parent_head"]!="3ff11059a64041e8cfc1dce2d34c43a046a0f64d"
        or data["identical_fit_count"]!=1664
        or data["new_development_seeds"]!=[67301,67303,67307]
        or data["live_action_cap"]!=192 or data["zero_external"] is not True
        or data["roles"]!=list(ROLES)
        or data["public"]!=["image","direction","mission"]
        or data["source_action_ids"]!=list(range(7))
        or data["negative"]!=NEGATIVE or data["blocked"]!=BLOCKED
        or pins["wingless_go_dk10_head"]!="e8f6cf7bce6bf7580de9bb7ab861530d7fd1e220"
        or pins["yggdrasil_r14_head"]!="c09b674d7045daca98b7881fda2fe54120c8fdd6"):
        raise ValueError("MG07_ORIGINAL_SOURCE_AND_PREREG_DRIFT")
    return data

class ConventionalTemporal:
    """Independently authored public-only conventional episodic count/edge table."""
    def __init__(self):
        self.visits={}
        self.edges={}
        self.seen={}
        self.steps=0
    def choose(self,control,conv,public):
        base=previous.conventional_min(control,conv,public)
        key=sha(canon(public).encode())
        row=self.visits.get(key,[0]*7)
        successors=self.edges.get(key,{})
        scores=[]
        for action in range(7):
            score=4*int(action==base)-3*row[action]
            successor=successors.get(str(action))
            if successor is not None:
                score-=2*int(successor==key)
                score-=min(2,self.seen.get(successor,0))
            scores.append(score)
        high=max(scores)
        start=int(key[:2],16)%7
        for offset in range(7):
            a=(start+offset)%7
            if scores[a]==high:return a
        raise ValueError("MG07_CONVENTIONAL_UNREACHABLE")
    def observe(self,before,action,after):
        if type(action)is not int or action not in range(7) or self.steps>=192:
            raise ValueError("MG07_CONVENTIONAL_INVALID_SELECTED")
        source_hash=sha(canon(before).encode())
        next_hash=sha(canon(after).encode())
        counts=self.visits.get(source_hash,[0]*7)[:]
        counts[action]+=1
        edges=dict(self.edges.get(source_hash,{}))
        edges[str(action)]=next_hash
        self.visits[source_hash]=counts
        self.edges[source_hash]=edges
        self.seen[next_hash]=self.seen.get(next_hash,0)+1
        self.steps+=1
    def checkpoint(self):
        return canon({"schema":"mg07.independent.conventional-temporal.v1",
                     "visits":self.visits,"edges":self.edges,
                     "seen":self.seen,"steps":self.steps})

def modules():
    gym,owner,Cell,collector,conv,r13=previous.source_modules()
    from research.native.itd02.r14.temporal_cells import TemporalCells
    return gym,owner,Cell,collector,conv,r13,TemporalCells

def fit(binary_new,binary_old,p):
    # Reuse exact original MG04 source FIT; Go DK10 wraps the original DK9/DK8
    # learner, and its inner snapshot is the original DK9 native checkpoint.
    result=original.fit(binary_new,{"FIT":{"seeds":p["source_fit_seeds"],"cap":256}})
    if result["samples"]!=1664:raise ValueError("MG07_ORIGINAL_SELECTED_FIT_COUNT")
    envelope=json.loads(result["native_go"])
    if (type(envelope)is not dict or
        envelope.get("state",{}).get("schema")!="wingless.itd02.dk10.source-public-temporal-loop-memory.v1"):
        raise ValueError("MG07_NOT_ORIGINAL_NATIVE_DK10_WRAPPER")
    inner=base64.b64decode(envelope["state"]["inner"],validate=True)
    original_go=WingBridge(binary_old)
    try:
        restore=original_go.request("load",state=base64.b64encode(inner).decode("ascii"))
        if restore.get("updates",0)!=1664 or original_go.snapshot()!=inner:
            raise ValueError("MG07_GO_DK9_ORIGINAL_FIT_CUSTODY")
    finally:original_go.close()
    return dict(result,parent_go=inner,parent_go_sha=sha(inner))

def episode(role,seed,trained,binary_new,binary_old,p):
    gym,owner,Cell,collector,conv,r13,TemporalCells=modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    wing=None
    native=None
    control=None
    ring=None
    try:
        raw,_=env.reset(seed=seed)
        first=source.normalize(collector,owner,raw)
        first_hash=owner.digest(first)
        adapter.reset_public(first)
        if role in ("wingless_go_dk10","wingless_go_dk9"):
            wing=WingBridge(binary_new if role=="wingless_go_dk10" else binary_old)
            cp=trained["native_go"] if role=="wingless_go_dk10" else trained["parent_go"]
            result=wing.request("load",state=base64.b64encode(cp).decode("ascii"))
            if result.get("updates",0)!=trained["samples"] or result.get("live",0)!=0:
                raise ValueError("MG07_ORIGINAL_GO_FIT_NOT_RESTORED")
            wing.request("begin_episode")
        elif role in ("yggdrasil_r14","yggdrasil_r13"):
            native=Cell.restore(trained["native_ygg"])
            native.start_session(adapter,"mg07-"+role+"-"+str(seed))
            if role=="yggdrasil_r14":ring=TemporalCells()
        elif role=="conventional_public_temporal":
            control=conv.Control.restore(trained["conventional"])
            ring=ConventionalTemporal()
        else:raise ValueError("MG07_UNKNOWN_ORIGINAL_ACTOR_ROLE")
        observed=[]
        goal_reward=carry_effects=door_effects=0
        carry_seen=door_after_carry=False
        for step in range(p["live_action_cap"]):
            before=source.normalize(collector,owner,raw)
            if before!=adapter.current:
                raise ValueError("MG07_NOT_REAL_SOURCE_OBSERVATION")
            if wing is not None:
                proposal=wing.request("choose",before=before,objective=original.objective(owner,before))
                action=proposal.get("action")
                provenance=proposal.get("status")
            elif role=="yggdrasil_r14":
                proposal=ring.decide(native,before)
                action=proposal["action"]
                provenance=proposal["status"]
            elif native is not None:
                proposal=r13(native,before)
                action=proposal["action"]
                provenance=proposal["status"]
            else:
                action=ring.choose(control,conv,before)
                provenance="CONVENTIONAL_PUBLIC_TEMPORAL_SOURCE_ONLY"
            if type(action)is not int or action not in range(7):
                raise ValueError("MG07_MISSING_GENUINELY_NATIVE_ACTION")
            if wing is not None:
                acknowledgement=wing.request("commit",before=before,action=action)
                if acknowledgement.get("updates",0)!=trained["samples"]+step:
                    raise ValueError("MG07_GO_ACTUAL_SELECTED_SOURCE_CUSTODY")
            if adapter.submit(action)!=action:
                raise ValueError("MG07_REAL_ORIGINAL_ACTION_REMAP")
            # Only one selected real original upstream action; never call
            # external collector/route planner or obtain nonselected rewards.
            raw_after,reward,terminated,truncated,_=env.step(action)
            after=source.normalize(collector,owner,raw_after)
            event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if wing is not None:
                ack=wing.request("feedback",before=before,action=action,after=after,
                    reward=float(reward),terminal=bool(terminated or truncated))
                if (ack.get("updates",0)!=trained["samples"]+step+1 or
                    ack.get("live",0)!=step+1):
                    raise ValueError("MG07_GO_FEEDBACK_DID_NOT_UPDATE_ONCE")
            elif native is not None:
                receipt=native.learn_selected(adapter)
                if receipt["sample_index"]!=trained["samples"]+step+1:
                    raise ValueError("MG07_YGG_ORIGINAL_SELECTED_FEEDBACK_MISSING")
                if ring is not None:ring.learn_selected(before,action,after,event)
            else:
                control.learn(event)
                if control.samples!=trained["samples"]+step+1:
                    raise ValueError("MG07_CONVENTIONAL_FEEDBACK_MISSING")
                ring.observe(before,action,after)
            carry=event["carried_before"]!=event["carried_after"]
            front0=event["front_before"]
            front1=event["front_after"]
            door=front0[0]==4 and front1[0]==4 and front0[2]!=front1[2]
            if carry:carry_seen=True
            if door and carry_seen:door_after_carry=True
            carry_effects+=int(carry)
            door_effects+=int(door)
            goal_reward+=int(float(reward)>0)
            observed.append({
                "ordinal":step+1,"original_public_before":before,
                "original_public_after":after,"original_selected_action":action,
                "action_origin":provenance,
                "original_reward":float(reward),
                "carrying_changed":bool(carry),"visible_door_changed":bool(door),
                "terminated":bool(terminated),"truncated":bool(truncated),
                "actual_public_before_sha256":owner.digest(before),
                "actual_public_after_sha256":owner.digest(after),
                "external_selected_actions":0})
            raw=raw_after
            if terminated or truncated:break
        if wing is not None:
            cp=wing.snapshot()
            cold=WingBridge(binary_new if role=="wingless_go_dk10" else binary_old)
            try:
                ack=cold.request("load",state=base64.b64encode(cp).decode("ascii"))
                if (ack.get("updates",0)!=trained["samples"]+len(observed)
                    or ack.get("live",0)!=len(observed) or cold.snapshot()!=cp):
                    raise ValueError("MG07_GO_COLD_SOURCE_MEM_LOSS")
            finally:cold.close()
            ring_sha=sha(cp) if role=="wingless_go_dk10" else "ORIGINAL_DK9_NO_TEMPORAL"
        elif native is not None:
            cp=native.checkpoint()
            restored=Cell.restore(cp)
            if (restored.samples!=trained["samples"]+len(observed)
                or restored.checkpoint()!=cp):
                raise ValueError("MG07_R11_COLD_NATIVE_MEMORY_LOSS")
            if ring is not None:
                recorded=ring.checkpoint()
                if (ring.steps!=len(observed)
                    or TemporalCells.restore(recorded).checkpoint()!=recorded):
                    raise ValueError("MG07_R14_TEMPORAL_COLD_SOURCE_LOSS")
                ring_sha=sha(recorded)
            else:ring_sha="ORIGINAL_R13_NO_TEMPORAL"
        else:
            cp=control.checkpoint()
            restored=conv.Control.restore(cp)
            if restored.samples!=trained["samples"]+len(observed) or restored.checkpoint()!=cp:
                raise ValueError("MG07_CONVENTIONAL_COLD_SOURCE_LOSS")
            if ring.steps!=len(observed):
                raise ValueError("MG07_CONVENTIONAL_TEMPORAL_SOURCE_LOSS")
            ring_sha=sha(ring.checkpoint())
        return {"role":role,"evaluator_seed_only":seed,
            "original_public_start_sha256":first_hash,
            "original_real_selected_steps":len(observed),
            "external_actions":0,
            "observed_public_carrying_changes":carry_effects,
            "observed_public_door_changes":door_effects,
            "original_goal_rewards":goal_reward,
            "observed_ordered_key_door_goal":bool(carry_seen and door_after_carry and goal_reward),
            "original_learner_checkpoint_sha256":sha(cp),
            "selected_public_temporal_checkpoint_sha256":ring_sha,
            "all_original_public_selected_action_consequences":observed}
    finally:
        env.close()
        if wing is not None:wing.close()

def run(new_go,old_go,p):
    trained=fit(new_go,old_go,p)
    rows=[]
    for seed in p["new_development_seeds"]:
        each=[episode(role,seed,trained,new_go,old_go,p) for role in ROLES]
        if len({x["original_public_start_sha256"] for x in each})!=1:
            raise ValueError("MG07_UNEQUAL_ORIGINAL_DOORKEY_PUBLIC_START")
        rows.extend(each)
    if len(rows)!=15 or any(e["original_real_selected_steps"]==0 for e in rows):
        raise ValueError("MG07_SOURCE_WORLD_MISSING_PUBLIC_ACTOR")
    summary={}
    for role in ROLES:
        chosen=[x for x in rows if x["role"]==role]
        summary[role]={"episodes":3,
          "actual_original_native_actions":sum(x["original_real_selected_steps"] for x in chosen),
          "external_actions":0,
          "carrying_changes":sum(x["observed_public_carrying_changes"] for x in chosen),
          "door_visible_changes":sum(x["observed_public_door_changes"] for x in chosen),
          "original_goal_rewards":sum(x["original_goal_rewards"] for x in chosen),
          "ordered_key_door_goal":sum(x["observed_ordered_key_door_goal"] for x in chosen)}
    success=all(summary[role]["original_goal_rewards"]>=1
                for role in ("wingless_go_dk10","yggdrasil_r14"))
    classification=POSITIVE if success else NEGATIVE
    evidence={"schema":SCHEMA,
        "upstream_farama":"7f5853792ea7f04f75614661006d87fcf949f26d",
        "unchanged_original_source_fit_sha":trained["source_history_sha256"],
        "same_source_fit_per_native_and_conventional":trained["samples"],
        "source_original_fit_checkpoint_sha":trained["checkpoint_sha256"],
        "original_go_dk9_inner_source_checkpoint_sha":trained["parent_go_sha"],
        "native_new_source_pins":p["future_native_new_source_commit"],
        "original_source_15_native_and_conventional_episode_records":rows,
        "per_role_source_metrics":summary,
        "original_wingless_r8_untouched":True,
        "original_ygg_r10_r11_r12_untouched":True,
        "no_external_navigation":True}
    return {"schema":SCHEMA,"classification":classification,
        "scientific_first_use":False,"native_model_promoted":False,
        "controller_modified":False,"original_accepted_sources_unchanged":True,
        "external_live_actions":0,"original_authentic_episode_count":15,
        "identical_original_source_fit_per_actor":1664,
        "canonical_full_original_source_trace_sha256":sha(canon(evidence).encode()),
        "canonical_full_original_source_evidence":evidence}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk10",type=Path,required=True)
    parser.add_argument("--wingless-dk9",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    t=time.perf_counter();cpu=time.process_time()
    try: result=run(args.wingless_dk10,args.wingless_dk9,freeze())
    except Exception as exc:
        result={"schema":SCHEMA,"classification":BLOCKED,
           "scientific_first_use":False,
           "error_type":type(exc).__name__,"error":str(exc),
           "trace_tail":traceback.format_exc().splitlines()[-14:]}
    result["host_wall_seconds"]=round(time.perf_counter()-t,6)
    result["host_cpu_seconds"]=round(time.process_time()-cpu,6)
    result["host_max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("MG07_CLASSIFICATION",result["classification"])
    print("MG07_ORIGINAL_SOURCE_SHA",result.get("canonical_full_original_source_trace_sha256","NONE"))
    print("MG07_SOURCE_SUMMARY",json.dumps(result.get("canonical_full_original_source_evidence",{}).get("per_role_source_metrics",{}),sort_keys=True))
    if result["classification"]==BLOCKED:
        print("MG07_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0
if __name__=="__main__":raise SystemExit(main())

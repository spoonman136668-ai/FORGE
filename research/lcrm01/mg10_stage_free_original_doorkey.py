#!/usr/bin/env python3
"""MG10: genuine Farama DoorKey independent raw-public native continuity.

No model is given manually annotated stage, hidden grid, route, chosen reward
oracle, other actor's memory or original world seed. Go DK11 and Ygg R15
are separate, independently source-qualified original native architectures.
"""
import argparse
import base64
import hashlib
import json
import random
import resource
import time
import traceback
from pathlib import Path

from k4r_minigrid_source import canon,sha
from k4u_native_minigrid import WingBridge
import mg03_equal_public_doorkey_live as old
import mg04_public_effect_native_agency as source

SCHEMA="itd02.mg10.original-stage-free-native-object-continuity.v1"
BLOCKED="MG10_AUTHENTIC_SOURCE_OR_EQUAL_PUBLIC_CONTINUITY_BLOCKED__NO_SCIENCE"
NEGATIVE="MG10_STAGE_FREE_NATIVE_FULL_TASK_NOT_ESTABLISHED__NO_SCIENCE"
POSITIVE="MG10_STAGE_FREE_BOTH_NATIVE_TASK_GOAL_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=("wingless_go_dk11","yggdrasil_r15","conventional_public_object_continuity",
       "conventional_seeded_random","frozen_ygg_r15_no_live_learning")
PREREG=Path(__file__).with_name("mg10_stage_free_object_continuity_prereg.json")

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    x=p["protocol"];y=p["source"]
    if (p["schema"]!="itd02.mg10.original-doorkey-stage-free-continuity.v1"
        or p["parent"]["head"]!="12d34b631b8c5b865d61d8327695c55f72030109"
        or y["go_dk11_head"]!="e75cc1ac6d302f4926df9fd28f3aab02eded1de3"
        or y["go_dk11_ipc_head"]!="5b5cda4346e278f46874d2f9264b22a5cf5a01ba"
        or y["ygg_r15_head"]!="630dde83f45d845488d59a36136d6c026e10880b"
        or x["new_world_seeds"]!=[70301,70303,70307]
        or x["cap_original_actions"]!=192 or x["source_FIT_count"]!=1664
        or x["public_input"]!=["image","direction","mission"] or x["actions"]!=list(range(7))
        or x["roles"]!=list(ROLES) or x["external_live_actions"]!=0
        or p["classification"]["negative"]!=NEGATIVE
        or p["classification"]["blocked"]!=BLOCKED
        or p["classification"]["positive"]!=POSITIVE):
        raise ValueError("MG10_SOURCE_PREREG_OR_SCIENCE_AUTHORITY_CHANGED")
    return p

def native_modules():
    gym,owner,_,_,collector,conv=source.get_modules()
    from research.native.itd02.r15.continuity_cells import NativeContinuity
    return gym,owner,collector,conv,NativeContinuity

def held(p):
    return p["image"][3][6][0] in (5,6,7)

def context(p):
    return str(p["image"][3][5][0])+":"+str(int(held(p)))

class Conventional:
    """Standalone conventional empirical event counts, not either native memory."""
    def __init__(self):
        self.memory={}
        self.count=0

    def observe(self,b,a,after):
        if (type(a)is not int or not 0<=a<=6 or self.count>=4096
            or set(b)!={"image","direction","mission"}
            or set(after)!={"image","direction","mission"}):
            raise ValueError("MG10_CONVENTIONAL_SPOOFED_SELECTED_EVENT")
        ctx=context(b)
        row=self.memory.setdefault(ctx,{})
        s=row.setdefault(str(a),{"count":0,"changed":0,"retained_changed":0,
                                "lost":0,"gained":0})
        was=held(b);now=held(after)
        changed=b!=after
        s["count"]+=1
        s["changed"]+=int(changed)
        s["retained_changed"]+=int(changed and was and now
                                  and b["image"][3][6]==after["image"][3][6])
        s["lost"]+=int(was and not now)
        s["gained"]+=int(not was and now)
        self.count+=1

    def choose(self,b):
        ctx=context(b)
        row=self.memory.get(ctx,{})
        best=None;high=0
        for a in range(7):
            s=row.get(str(a))
            if not s:continue
            numerator=(6*s["retained_changed"]+2*s["changed"]-8*s["lost"]
                       if held(b) else 6*s["gained"]+2*s["changed"])
            score=(numerator*1024)//s["count"]
            if score>high:best=a;high=score
        if best is not None:return best,"CONVENTIONAL_LEARNED_PUBLIC_CONTINUITY"
        counts=[row.get(str(i),{}).get("count",0) for i in range(7)]
        low=min(counts)
        start=int(sha(canon(b).encode())[:2],16)%7
        for n in range(7):
            a=(start+n)%7
            if counts[a]==low:return a,"CONVENTIONAL_UNKNOWN_PUBLIC_ACTION"
        raise ValueError("MG10_CONVENTIONAL_UNKNOWN_ACTION")

    def checkpoint(self):
        return canon({"schema":"mg10.conventional.public.v1",
          "memory":self.memory,"count":self.count}).encode()

    @classmethod
    def restore(cls,data):
        raw=json.loads(data)
        if raw.get("schema")!="mg10.conventional.public.v1" or set(raw)!={"schema","memory","count"}:
            raise ValueError("MG10_CONVENTIONAL_COLD_SOURCE")
        o=cls();o.memory=raw["memory"];o.count=raw["count"]
        if o.checkpoint()!=data or sum(v["count"] for row in o.memory.values()
             for v in row.values())!=o.count:
            raise ValueError("MG10_CONVENTIONAL_BAD_COLD_EVENT_COUNTERS")
        return o

def train(go_binary,p):
    gym,owner,collector,conv,Native=native_modules()
    go=WingBridge(go_binary)
    native=Native()
    baseline=conv.Control()
    independent=Conventional()
    digest=hashlib.sha256()
    count=0
    action_counts={str(a):0 for a in range(7)}
    try:
        for idx,seed in enumerate(p["protocol"]["source_FIT_seeds"]):
            env=gym.make("MiniGrid-DoorKey-8x8-v0")
            adapter=owner.DoorKeyPublicAdapter()
            rng=random.Random(93617+7919*idx)
            try:
                raw,_=env.reset(seed=seed)
                adapter.reset_public(collector.normalized_original_public(raw))
                native.start_session(adapter,"mg10-original-fit-"+str(seed),live=False)
                for step in range(256):
                    before=old.normalize(collector,owner,raw)
                    action=collector.policy(
                        {"image":before["image"],"cues":owner.public_cues(before)},
                        rng,step,{})
                    if type(action)is not int or action not in range(7):
                        raise ValueError("MG10_BAD_ORIGINAL_SELECTED_FIT_ACTION")
                    if adapter.submit(action)!=action:
                        raise ValueError("MG10_ORIGINAL_ACTION_REMAP_IN_FIT")
                    next_raw,reward,terminal,truncated,_=env.step(action)
                    after=old.normalize(collector,owner,next_raw)
                    event=adapter.complete(after,float(reward),bool(terminal),bool(truncated))
                    native.learn_selected(adapter,before,after)
                    baseline.learn(event)
                    independent.observe(before,action,after)
                    reply=go.request("learn",before=before,action=action,after=after,
                                     reward=float(reward),terminal=bool(terminal or truncated))
                    count+=1
                    if (reply.get("updates")!=count or native.samples!=count
                        or baseline.samples!=count or independent.count!=count):
                        raise ValueError("MG10_DIFFERENT_AUTHENTIC_SELECTED_SOURCE_COUNTS")
                    action_counts[str(action)]+=1
                    digest.update((canon({"before":before,"action":action,"after":after,
                        "reward":float(reward),"terminal":bool(terminal or truncated)})+"\n").encode())
                    raw=next_raw
                    if terminal or truncated:break
            finally:env.close()
        if count!=1664 or any(v==0 for v in action_counts.values()):
            raise ValueError("MG10_INSUFFICIENT_ORIGINAL_SOURCE_FIT")
        gc=go.snapshot();yc=native.checkpoint();bc=baseline.checkpoint();cc=independent.checkpoint()
    finally:go.close()
    cold=WingBridge(go_binary)
    try:
        reply=cold.request("load",state=base64.b64encode(gc).decode())
        if reply.get("updates")!=count or cold.snapshot()!=gc:
            raise ValueError("MG10_GO_COLD_FIT_NOT_IDENTICAL")
    finally:cold.close()
    if (Native.restore(yc).checkpoint()!=yc or conv.Control.restore(bc).checkpoint()!=bc
        or Conventional.restore(cc).checkpoint()!=cc):
        raise ValueError("MG10_NOT_IDENTICAL_ORIGINAL_COLD_FIT")
    return {"source_fit_sha256":digest.hexdigest(),"samples":count,
      "source_fit_action_counts":action_counts,
      "go":gc,"ygg":yc,"baseline":bc,"conventional":cc,
      "checkpoint_sha256":{"go":sha(gc),"ygg":sha(yc),
                             "baseline":sha(bc),"conventional":sha(cc)}}

def episode(role,seed,fit,go_binary,p):
    gym,owner,collector,conv,Native=native_modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    go=None;native=None;control=None;con=None
    rng=random.Random(97011+seed)
    try:
        raw,_=env.reset(seed=seed)
        first=old.normalize(collector,owner,raw)
        first_sha=owner.digest(first)
        adapter.reset_public(first)
        if role=="wingless_go_dk11":
            go=WingBridge(go_binary)
            ack=go.request("load",state=base64.b64encode(fit["go"]).decode())
            if ack.get("updates")!=fit["samples"] or ack.get("live",0)!=0:
                raise ValueError("MG10_GO_ORIGINAL_FIT_COLD_RESTORE_FAILED")
            go.request("begin_episode")
        elif role in ("yggdrasil_r15","frozen_ygg_r15_no_live_learning"):
            native=Native.restore(fit["ygg"])
            native.start_session(adapter,"mg10-"+role+"-"+str(seed),live=True)
            frozen=native.checkpoint()
            if native.samples!=fit["samples"]:raise ValueError("MG10_YGG_COLD_SOURCE_NOT_MATCHED")
        elif role in ("conventional_public_object_continuity","conventional_seeded_random"):
            control=conv.Control.restore(fit["baseline"])
            con=Conventional.restore(fit["conventional"])
        else:raise ValueError("MG10_ROLE_NOT_PREREGISTERED")

        rows=[]
        for i in range(p["protocol"]["cap_original_actions"]):
            before=old.normalize(collector,owner,raw)
            if before!=adapter.current:raise ValueError("MG10_NOT_REAL_PUBLIC_ORIGINAL_STATE")
            if go is not None:
                reply=go.request("choose",before=before) # NO stage input
                chosen=reply.get("action");mode=reply.get("status")
            elif native is not None:
                reply=native.choose(before)
                chosen=reply["action"];mode=reply["status"]
            elif role=="conventional_public_object_continuity":
                chosen,mode=con.choose(before)
            else:
                chosen=rng.randrange(7);mode="CONVENTIONAL_UNIFORM_RANDOM"
            if type(chosen)is not int or chosen not in range(7):
                raise ValueError("MG10_UNFAIR_OR_NONNATIVE_ACTION_SELECTED")
            if go is not None:
                ack=go.request("commit",before=before,action=chosen)
                if ack.get("updates")!=fit["samples"]+i:
                    raise ValueError("MG10_GO_PENDING_SELECTED_SOURCE_NOT_COMMITTED")
            if adapter.submit(chosen)!=chosen:
                raise ValueError("MG10_REAL_ORIGINAL_ENV_ACTION_REMAP")
            after_raw,reward,terminal,truncated,_=env.step(chosen)
            after=old.normalize(collector,owner,after_raw)
            event=adapter.complete(after,float(reward),bool(terminal),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=before,action=chosen,after=after,
                       reward=float(reward),terminal=bool(terminal or truncated))
                if (ack.get("updates")!=fit["samples"]+i+1 or ack.get("live")!=i+1):
                    raise ValueError("MG10_GO_TRUE_SELECTED_PUBLIC_CREDIT_MISSING")
            elif role=="yggdrasil_r15":
                receipt=native.learn_selected(adapter,before,after)
                if native.samples!=fit["samples"]+i+1 or receipt["sample_index"]!=fit["samples"]+i+1:
                    raise ValueError("MG10_YGG_TRUE_SELECTED_PUBLIC_CREDIT_MISSING")
            elif role=="frozen_ygg_r15_no_live_learning":
                if native.checkpoint()!=frozen or native.samples!=fit["samples"]:
                    raise ValueError("MG10_FROZEN_NATIVE_MEMORY_CHANGED")
            elif role=="conventional_public_object_continuity":
                control.learn(event);con.observe(before,chosen,after)
                if control.samples!=fit["samples"]+i+1 or con.count!=fit["samples"]+i+1:
                    raise ValueError("MG10_CONVENTIONAL_SELECTED_CREDIT_DROPPED")
            else:
                if control.samples!=fit["samples"] or con.count!=fit["samples"]:
                    raise ValueError("MG10_RANDOM_SHADOW_LEARNED")
            carrying=before["image"][3][6][0] in (5,6,7)
            carry_after=after["image"][3][6][0] in (5,6,7)
            bfront=before["image"][3][5];afront=after["image"][3][5]
            door_change=(bfront[0]==4 and afront[0]==4 and bfront[2]!=afront[2])
            rows.append({"ordinal":i+1,"public_before":before,"selected_real_action":chosen,
               "selected_action_origin":mode,"public_after":after,"original_reward":float(reward),
               "terminal":bool(terminal),"truncated":bool(truncated),
               "key_held_before":bool(carrying),"key_held_after":bool(carry_after),
               "public_held_loss":bool(carrying and not carry_after),
               "public_held_gain":bool(not carrying and carry_after),
               "public_key_front_door":bool(carrying and bfront[0]==4),
               "public_door_state_change":bool(door_change),
               "external_selected_action_count":0,
               "original_public_before_sha":owner.digest(before),
               "original_public_after_sha":owner.digest(after)})
            raw=after_raw
            if terminal or truncated:break

        if go is not None:
            cp=go.snapshot()
            cold=WingBridge(go_binary)
            try:
                ack=cold.request("load",state=base64.b64encode(cp).decode())
                if (ack.get("updates")!=fit["samples"]+len(rows)
                    or ack.get("live")!=len(rows) or cold.snapshot()!=cp):
                    raise ValueError("MG10_GO_NATIVE_COLD_CHECKPOINT_BAD")
            finally:cold.close()
        elif native is not None:
            cp=native.checkpoint()
            restored=Native.restore(cp)
            expected=fit["samples"]+(len(rows) if role=="yggdrasil_r15" else 0)
            if restored.checkpoint()!=cp or restored.samples!=expected:
                raise ValueError("MG10_YGG_NATIVE_COLD_CHECKPOINT_BAD")
            if role=="frozen_ygg_r15_no_live_learning" and cp!=frozen:
                raise ValueError("MG10_R15_NOLEARNING_CHECKPOINT_CHANGED")
        else:
            cp=con.checkpoint()
            if Conventional.restore(cp).checkpoint()!=cp:
                raise ValueError("MG10_CONVENTIONAL_COLD_CHECKPOINT_BAD")
            expected=fit["samples"]+(len(rows) if role=="conventional_public_object_continuity" else 0)
            if con.count!=expected:raise ValueError("MG10_CONVENTIONAL_EVENT_NOT_PRESERVED")

        return {"role":role,"seed_evaluator_only":seed,"original_public_start_sha":first_sha,
             "true_original_live_steps":len(rows),"external_actions":0,
             "key_acquisition_events":sum(x["public_held_gain"] for x in rows),
             "key_loss_events":sum(x["public_held_loss"] for x in rows),
             "key_front_door_frames":sum(x["public_key_front_door"] for x in rows),
             "real_door_state_changes":sum(x["public_door_state_change"] for x in rows),
             "true_original_goal_rewards":sum(x["original_reward"]>0 for x in rows),
             "original_native_checkpoint_sha256":sha(cp),
             "true_original_public_selected_events":rows}
    finally:
        env.close()
        if go is not None:go.close()

def run(binary,p):
    fitted=train(binary,p)
    records=[]
    for seed in p["protocol"]["new_world_seeds"]:
        all_for_seed=[episode(role,seed,fitted,binary,p) for role in ROLES]
        if len({x["original_public_start_sha"] for x in all_for_seed})!=1:
            raise ValueError("MG10_ORIGINAL_REAL_RESET_PUBLIC_NOT_EQUAL")
        records.extend(all_for_seed)
    if len(records)!=15 or any(x["true_original_live_steps"]<1 for x in records):
        raise ValueError("MG10_MISSING_NEW_ORIGINAL_SOURCE_EXPOSURE")
    summary={}
    for role in ROLES:
        arms=[x for x in records if x["role"]==role]
        summary[role]={"episodes":3,
            "true_original_selected_actions":sum(x["true_original_live_steps"] for x in arms),
            "external_actions":0,
            "public_key_acquisitions":sum(x["key_acquisition_events"] for x in arms),
            "public_key_losses":sum(x["key_loss_events"] for x in arms),
            "key_and_front_door_frames":sum(x["key_front_door_frames"] for x in arms),
            "real_door_state_changes":sum(x["real_door_state_changes"] for x in arms),
            "real_original_goal_rewards":sum(x["true_original_goal_rewards"] for x in arms)}
    both=all(summary[role]["real_original_goal_rewards"]>=1
              for role in ("wingless_go_dk11","yggdrasil_r15"))
    classification=POSITIVE if both else NEGATIVE
    evidence={"schema":SCHEMA,"original_farama":p["source"]["farama"],
        "qualified_native_source_heads":p["source"],
        "identical_original_FIT_selected_sha":fitted["source_fit_sha256"],
        "selected_source_fit_action_counts":fitted["source_fit_action_counts"],
        "same_original_selected_FIT_for_each_learned_actor":1664,
        "private_independent_cold_source_fit_checkpoint_sha":fitted["checkpoint_sha256"],
        "all_source_selected_public_events":records,
        "original_source_per_role_metrics":summary,
        "all_eligible_actors_use_raw_original_public_only":True,
        "no_manual_stage_or_hidden_answer":True,
        "external_live_actions":0}
    return {"schema":SCHEMA,"classification":classification,
       "scientific_first_use":False,"accepted_native_model_changed":False,
       "FORGE_controller_changed":False,"original_Wingless_R8_or_Ygg_R10_R12_changed":False,
       "same_original_FIT_selected_per_actor":1664,"original_source_episodes":15,
       "external_selected_original_live_actions":0,
       "canonical_original_selected_public_sha":sha(canon(evidence).encode()),
       "canonical_original_public_evidence":evidence}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wingless-dk11",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    start=time.perf_counter();cpu=time.process_time()
    try:result=run(a.wingless_dk11,freeze())
    except Exception as e:
        result={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
          "error_type":type(e).__name__,"error":str(e),
          "trace_tail":traceback.format_exc().splitlines()[-15:]}
    result["host_wall_seconds"]=round(time.perf_counter()-start,5)
    result["host_cpu_seconds"]=round(time.process_time()-cpu,5)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("MG10_CLASSIFICATION",result["classification"])
    print("MG10_SOURCE_SHA",result.get("canonical_original_selected_public_sha","NONE"))
    print("MG10_RESULTS",json.dumps(result.get("canonical_original_public_evidence",{}).get("original_source_per_role_metrics",{}),sort_keys=True))
    if result["classification"]==BLOCKED:
        print("MG10_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0
if __name__=="__main__":raise SystemExit(main())

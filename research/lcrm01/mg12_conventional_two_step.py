"""MG12 independent stronger conventional public two-step action-consequence baseline.

Trained separately on exactly the same 1,664 actual original selected FIT
samples. Does not read other agents' memory, private world state or routes.
"""
from __future__ import annotations
import hashlib
import json
import random
from k4r_minigrid_source import canon,sha
import mg11_authentic_selected_novelty as old
import mg03_equal_public_doorkey_live as original

SCHEMA="itd02.mg12.independent-two-step-public-transition-control.v1"

class PublicTwoStep:
    def __init__(self):
        self.edges={}
        self.episode={}
        self.seen={}
        self.count=0
    def _state(self,p):
        if type(p)is not dict or set(p)!={"image","direction","mission"}:
            raise ValueError("MG12_NONPUBLIC_CONVENTIONAL_STATE")
        return sha(canon(p).encode())
    def begin_episode(self):
        self.episode={}
    def choose(self,before):
        key=self._state(before)
        first=int(key[:2],16)%7
        candidates={}
        row=self.edges.get(key,{})
        for action in range(7):
            item=row.get(str(action))
            attempts=self.episode.get(key,{}).get(str(action),0)
            if item is None:
                score=1-3*attempts
            else:
                nxt=item["successor"]
                image_change=int(item["after_image"]!=before["image"])
                nextrow=self.edges.get(nxt,{})
                twohop=any(v["after_image"]!=item["after_image"] for v in nextrow.values())
                score=(5*image_change+2*int(item["novel"]>0)
                       -3*attempts-5*int(item["self_loop"]>0)+2*int(twohop))
            candidates[action]=score
        high=max(candidates.values())
        for offset in range(7):
            action=(first+offset)%7
            if candidates[action]==high:return action
        raise ValueError("MG12_CLASSICAL_NO_PUBLIC_ACTION")
    def observe(self,before,action,after):
        if (type(action)is not int or action not in range(7)
            or self.count>=4096):
            raise ValueError("MG12_CLASSICAL_SELECTED_CAP")
        key=self._state(before);nxt=self._state(after);a=str(action)
        record=self.edges.setdefault(key,{})
        item=record.get(a,{"count":0,"novel":0,"self_loop":0,
                            "successor":nxt,"after_image":after["image"]})
        item["count"]+=1
        if nxt not in self.seen:item["novel"]+=1
        if nxt==key:item["self_loop"]+=1
        item["successor"]=nxt
        item["after_image"]=after["image"]
        record[a]=item
        self.seen[nxt]=self.seen.get(nxt,0)+1
        e=self.episode.setdefault(key,{})
        e[a]=e.get(a,0)+1
        self.count+=1
    def checkpoint(self):
        if (self.count>4096 or sum(v["count"] for row in self.edges.values()
            for v in row.values())!=self.count
            or sum(self.seen.values())!=self.count):
            raise ValueError("MG12_CLASSICAL_INVALID_SELECTED_COUNTS")
        return canon({"schema":SCHEMA,"edges":self.edges,"episode":self.episode,
                      "seen":self.seen,"count":self.count}).encode()
    @classmethod
    def restore(cls,blob):
        if type(blob)is not bytes or len(blob)>2000000:
            raise ValueError("MG12_CLASSICAL_UNTRUSTED_CHECKPOINT_SIZE")
        body=json.loads(blob)
        if set(body)!={"schema","edges","episode","seen","count"} or body["schema"]!=SCHEMA:
            raise ValueError("MG12_CLASSICAL_UNTRUSTED_CHECKPOINT")
        out=cls()
        for k in ("edges","episode","seen","count"):setattr(out,k,body[k])
        if out.checkpoint()!=blob:raise ValueError("MG12_CLASSICAL_NONCANONICAL_SOURCE")
        return out

def independent_fit(p, expected_sha):
    gym,owner,collector,_,_,_=old.modules()
    model=PublicTwoStep()
    digest=hashlib.sha256()
    action_counts={str(a):0 for a in range(7)}
    for index,seed in enumerate(p["original_FIT_seeds"]):
        env=gym.make("MiniGrid-DoorKey-8x8-v0")
        adapter=owner.DoorKeyPublicAdapter()
        rng=random.Random(93617+7919*index)
        try:
            raw,_=env.reset(seed=seed)
            adapter.reset_public(collector.normalized_original_public(raw))
            for step in range(256):
                before=original.normalize(collector,owner,raw)
                chosen=collector.policy(
                    {"image":before["image"],"cues":owner.public_cues(before)},
                    rng,step,{})
                if type(chosen)is not int or chosen not in range(7):
                    raise ValueError("MG12_CLASSICAL_NOT_ORIGINAL_PUBLIC_FIT")
                if adapter.submit(chosen)!=chosen:
                    raise ValueError("MG12_CLASSICAL_SOURCE_REMAP")
                after_raw,reward,term,trunc,_=env.step(chosen)
                after=original.normalize(collector,owner,after_raw)
                adapter.complete(after,float(reward),bool(term),bool(trunc))
                model.observe(before,chosen,after)
                action_counts[str(chosen)]+=1
                digest.update((canon({"before":before,"action":chosen,"after":after,
                    "reward":float(reward),"terminal":bool(term or trunc)})+"\n").encode())
                raw=after_raw
                if term or trunc:break
        finally:env.close()
    if model.count!=1664 or digest.hexdigest()!=expected_sha:
        raise ValueError("MG12_CONVENTIONAL_FIT_NOT_MATCHED_1664_ORIGINAL_SELECTED")
    cp=model.checkpoint()
    if PublicTwoStep.restore(cp).checkpoint()!=cp:
        raise ValueError("MG12_CLASSICAL_FIT_COLD_MISMATCH")
    return {"checkpoint":cp,"source_selected_sha":digest.hexdigest(),
            "action_counts":action_counts}

def independent_episode(seed,blob):
    gym,owner,collector,_,_,_=old.modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    model=PublicTwoStep.restore(blob)
    model.begin_episode()
    try:
        raw,_=env.reset(seed=seed)
        start=original.normalize(collector,owner,raw)
        adapter.reset_public(start)
        steps=[]
        for i in range(192):
            before=original.normalize(collector,owner,raw)
            if adapter.current!=before:raise ValueError("MG12_SOURCE_PUBLIC_CONTEXT_NOT_EQUAL")
            chosen=model.choose(before)
            if adapter.submit(chosen)!=chosen:raise ValueError("MG12_SOURCE_SELECTED_ACTION_REMAP")
            after_raw,reward,term,trunc,_=env.step(chosen)
            after=original.normalize(collector,owner,after_raw)
            adapter.complete(after,float(reward),bool(term),bool(trunc))
            model.observe(before,chosen,after)
            held=before["image"][3][6][0] in (5,6,7)
            heldafter=after["image"][3][6][0] in (5,6,7)
            bfront=before["image"][3][5];afront=after["image"][3][5]
            door=(bfront[0]==4 and afront[0]==4 and bfront[2]!=afront[2])
            steps.append({"index":i+1,"public_before":before,"action":chosen,
                "policy_origin":"CLASSICAL_SOURCE_TWO_STEP_PUBLIC",
                "public_after":after,"original_reward":float(reward),
                "terminated":bool(term),"truncated":bool(trunc),
                "public_held_gain":bool(not held and heldafter),
                "public_held_loss":bool(held and not heldafter),
                "public_key_front_door":bool(held and bfront[0]==4),
                "public_actual_door_change":bool(door),
                "external_action_count":0,
                "before_sha":owner.digest(before),"after_sha":owner.digest(after)})
            raw=after_raw
            if term or trunc:break
        cp=model.checkpoint()
        if (model.count!=1664+len(steps) or
            PublicTwoStep.restore(cp).checkpoint()!=cp):
            raise ValueError("MG12_INDEPENDENT_CONVENTIONAL_LIVE_COLD_NOT_ACCOUNTED")
        return {"role":"conventional_two_step_public_model","evaluator_seed_only":seed,
            "original_public_start_sha":owner.digest(start),
            "real_original_source_actions":len(steps),
            "distinct_original_selected_actions":len(set(x["action"] for x in steps)),
            "external_actions":0,
            "original_key_acquisitions":sum(x["public_held_gain"] for x in steps),
            "original_key_losses":sum(x["public_held_loss"] for x in steps),
            "original_key_front_door":sum(x["public_key_front_door"] for x in steps),
            "actual_original_door_changes":sum(x["public_actual_door_change"] for x in steps),
            "original_goal_rewards":sum(x["original_reward"]>0 for x in steps),
            "original_cold_checkpoint_sha256":sha(cp),
            "all_original_public_selected_events":steps}
    finally:env.close()

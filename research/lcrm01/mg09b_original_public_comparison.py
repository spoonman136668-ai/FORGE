#!/usr/bin/env python3
"""MG09B genuine original Farama DoorKey equal-policy-input native comparison.

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
FROZEN=HERE/"mg09b_raw_public_original_prereg.json"
SCHEMA="itd02.mg09b.authentic-equal-raw-public-native.v1"
POS="MG09B_BOTH_NATIVE_ORIGINAL_GOAL_REWARDS__ENGINEERING_ONLY"
NEG="MG09B_NOT_BOTH_NATIVE_GOAL_SOLVING__NO_SCIENCE"
BLOCK="MG09B_AUTHENTIC_SOURCE_OR_PARITY_BLOCKED__NO_SCIENCE"
ROLES=("wingless_dk11_native","yggdrasil_r15_native",
       "conventional_matched_held_object_empirical","conventional_seeded_uniform_random")

def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (p["schema"]!="itd02.mg09b.original-equal-policy-facing-public-comparison.v1"
        or p["phase"]!="PREREG_BEFORE_CODE_OR_NEW_DOORKEY_EPISODES"
        or p["parent"]["head"]!="58a5b03050857fa45828773b0001a39a932da7db"
        or p["native"]["wingless_exact_head"]!="e75cc1ac6d302f4926df9fd28f3aab02eded1de3"
        or p["native"]["ygg_exact_head"]!="630dde83f45d845488d59a36136d6c026e10880b"
        or p["DEV"]["roles"]!=list(ROLES)
        or p["DEV"]["seeds"]!=[70301,70303,70307]
        or p["DEV"]["limit"]!=192
        or p["FIT"]["required_original_selected_samples"]!=1664
        or p["DEV"]["external_live_collector_actions"]!=0):
        raise ValueError("MG09B_FROZEN_ORIGINAL_WORLD_CONTRACT_DRIFT")
    return p

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

class ConventionalEmpirical:
    """Independent conventional lookup control with identical outcome feature and FIT."""
    def __init__(self):
        self.cells={};self.samples=0
    def learn(self,before,action,after):
        if type(action)is not int or action not in range(7) or self.samples>=4096:
            raise ValueError("MG09B_CONVENTIONAL_SOURCE_INVALID")
        key=local_feature(before)
        if key not in self.cells and len(self.cells)>=128:
            raise ValueError("MG09B_CONVENTIONAL_CONTEXT_BOUND")
        rows=self.cells.setdefault(key,{})
        stat=rows.setdefault(str(action),[0,0,0,0,0])
        stat[0]+=1
        for index,value in enumerate(result_stats(before,after),start=1):
            stat[index]+=value
        self.samples+=1
    def choose(self,before):
        key=local_feature(before);bins=self.cells.get(key,{})
        held=before["image"][3][6][0] in (5,6,7)
        best=None;highest=0
        for action in range(7):
            stat=bins.get(str(action))
            if not stat:continue
            n,changed,retained,lost,gained=stat
            score=(6*retained+2*changed-8*lost if held else 6*gained+2*changed)
            normalized=score*1024//n
            if normalized>highest:highest=normalized;best=action
        if best is not None:return best
        counts=[bins.get(str(a),[0])[0] for a in range(7)]
        minimum=min(counts)
        start=int(sha(canon(before).encode())[:2],16)%7
        for i in range(7):
            a=(start+i)%7
            if counts[a]==minimum:return a
        raise ValueError("MG09B_CONVENTIONAL_UNREACHABLE")
    def checkpoint(self):
        wire={"schema":"mg09b.conventional-same-feature-empirical.v1","cells":self.cells,
              "samples":self.samples}
        digest=sha(canon(wire).encode())
        return (canon({"data":wire,"sha256":digest})).encode()
    @classmethod
    def restore(cls,blob):
        envelope=json.loads(blob)
        data=envelope["data"]
        if (sha(canon(data).encode())!=envelope["sha256"]
            or data["schema"]!="mg09b.conventional-same-feature-empirical.v1"):
            raise ValueError("MG09B_CONVENTIONAL_CHECKPOINT_TAMPER")
        actor=cls()
        actor.cells=data["cells"];actor.samples=data["samples"]
        if actor.checkpoint()!=blob:raise ValueError("MG09B_CONVENTIONAL_NONCANONICAL")
        return actor


def modules():
    gym,owner,Cell,select,collector,conv=original.get_modules()
    from research.native.itd02.r15.continuity_cells import NativeContinuity
    return gym,owner,collector,NativeContinuity


def fit(binary,p):
    gym,owner,collector,NativeContinuity=modules()
    go=WingBridge(binary)
    ygg=NativeContinuity()
    control=ConventionalEmpirical()
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
                ygg.start_session(adapter,"mg09b-original-fit-"+str(seed),live=False)
                for step in range(p["FIT"]["cap_per_seed"]):
                    before=source.normalize(collector,owner,raw)
                    public_cues=owner.public_cues(before)
                    chosen=collector.policy({"image":before["image"],"cues":public_cues},
                                            rng,step,{})
                    if type(chosen)is not int or chosen not in range(7):
                        raise ValueError("MG09B_FIT_ACTION_UNTRUSTED")
                    if adapter.submit(chosen)!=chosen:
                        raise ValueError("MG09B_FIT_ACTION_REMAP")
                    after_raw,reward,terminated,truncated,_=env.step(chosen)
                    after=source.normalize(collector,owner,after_raw)
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    receipt=ygg.learn_selected(adapter,before,after)
                    control.learn(before,chosen,after)
                    ack=go.request("learn",before=before,action=chosen,after=after,
                                   reward=float(reward),terminal=bool(terminated or truncated))
                    count+=1
                    if (receipt["sample_index"]!=count or ygg.samples!=count or
                        ygg.local.samples!=count or control.samples!=count or
                        ack.get("updates")!=count or ack.get("live",0)!=0):
                        raise ValueError("MG09B_UNEQUAL_ORIGINAL_SOURCE_FIT")
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
            raise ValueError("MG09B_UNMATCHED_ORIGINAL_1664_FIT_SOURCE")
        go_checkpoint=go.snapshot()
        yg_checkpoint=ygg.checkpoint()
        conventional_checkpoint=control.checkpoint()
    finally:go.close()
    # Cold independent restores of all source-trained learners.
    cold=WingBridge(binary)
    try:
        ack=cold.request("load",state=base64.b64encode(go_checkpoint).decode())
        if ack.get("updates")!=1664 or cold.snapshot()!=go_checkpoint:
            raise ValueError("MG09B_GO_FIT_COLD_CUSTODY")
    finally:cold.close()
    if (NativeContinuity.restore(yg_checkpoint).checkpoint()!=yg_checkpoint or
        ConventionalEmpirical.restore(conventional_checkpoint).checkpoint()!=conventional_checkpoint):
        raise ValueError("MG09B_YGG_AND_CONVENTIONAL_COLD_CUSTODY")
    return {"samples":count,"selected_history_sha256":src_sha,
            "go":go_checkpoint,"ygg":yg_checkpoint,"conventional":conventional_checkpoint,
            "original_fit_source_action_counts":action_counts,"source_fit_key_pickups":key_pickups,
            "source_fit_visible_door_openings":door_opens,
            "checkpoints_sha":{"go":sha(go_checkpoint),"ygg":sha(yg_checkpoint),
                               "conventional":sha(conventional_checkpoint)}}


def episode(role,seed,trained,binary,p):
    gym,owner,collector,NativeContinuity=modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    go=None;ygg=None;control=None
    rng=random.Random(p["DEV"]["random_seed_offset"]+seed)
    try:
        raw,_=env.reset(seed=seed)
        before=source.normalize(collector,owner,raw)
        start_sha=owner.digest(before)
        adapter.reset_public(before)
        if role==ROLES[0]:
            go=WingBridge(binary)
            ack=go.request("load",state=base64.b64encode(trained["go"]).decode())
            if ack.get("updates")!=trained["samples"] or go.snapshot()!=trained["go"]:
                raise ValueError("MG09B_GO_SOURCE_FIT_NOT_COLD")
            go.request("begin_episode")
        elif role==ROLES[1]:
            ygg=NativeContinuity.restore(trained["ygg"])
            if ygg.samples!=1664:raise ValueError("MG09B_YGG_SOURCE_FIT_NOT_COLD")
            ygg.start_session(adapter,f"mg09b-original-{seed}",live=True)
        elif role==ROLES[2]:
            control=ConventionalEmpirical.restore(trained["conventional"])
            if control.samples!=1664:raise ValueError("MG09B_CONVENTIONAL_FIT_NOT_COLD")
        elif role!=ROLES[3]:
            raise ValueError("MG09B_UNREGISTERED_ORIGINAL_WORLD_ARM")
        events=[]
        pickups=drops=forward_held=front_held=doors=goals=0
        seen=set()
        time_start=time.perf_counter()
        cpu_start=time.process_time()
        for index in range(p["DEV"]["limit"]):
            public=source.normalize(collector,owner,raw)
            if public!=adapter.current:raise ValueError("MG09B_UNORIGINAL_PUBLIC_STATE")
            held=public["image"][3][6][0] in (5,6,7)
            if go is not None:
                proposal=go.request("choose",before=public)
                action=proposal.get("action");reason=proposal.get("status")
                provenance="NATIVE_GO_DK11_RAW_PUBLIC_ONLY"
            elif ygg is not None:
                proposal=ygg.choose(public)
                action=proposal["action"];reason=proposal["status"]
                provenance="NATIVE_YGG_R15_RAW_PUBLIC_ONLY"
            elif control is not None:
                action=control.choose(public)
                reason="CONVENTIONAL_EQUIVALENT_EMPIRICAL_PUBLIC"
                provenance="CONVENTIONAL_EQUIVALENT_EMPIRICAL_PUBLIC"
            else:
                action=rng.randrange(7)
                reason="CONVENTIONAL_UNIFORM_RANDOM"
                provenance="CONVENTIONAL_UNIFORM_RANDOM"
            if type(action)is not int or action not in range(7):
                raise ValueError("MG09B_NO_VALID_SELF_SELECTED_ACTION")
            if go is not None:
                ack=go.request("commit",before=public,action=action)
                if ack.get("updates")!=1664+index:
                    raise ValueError("MG09B_GO_UNCOMMITTED_SELECTED")
            if adapter.submit(action)!=action:
                raise ValueError("MG09B_SELECTED_SOURCE_ACTION_REMAP")
            new_raw,reward,terminated,truncated,_=env.step(action)
            after=source.normalize(collector,owner,new_raw)
            public_event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if go is not None:
                ack=go.request("feedback",before=public,action=action,after=after,
                               reward=float(reward),terminal=bool(terminated or truncated))
                if (ack.get("updates")!=1664+index+1 or ack.get("live")!=index+1):
                    raise ValueError("MG09B_GO_SELECTED_UPDATE_LOST")
            elif ygg is not None:
                receipt=ygg.learn_selected(adapter,public,after)
                if (receipt["sample_index"]!=1664+index+1 or ygg.samples!=1664+index+1):
                    raise ValueError("MG09B_YGG_SELECTED_UPDATE_LOST")
            elif control is not None:
                control.learn(public,action,after)
                if control.samples!=1664+index+1:
                    raise ValueError("MG09B_CONVENTIONAL_SELECTED_UPDATE_LOST")
            next_held=after["image"][3][6][0] in (5,6,7)
            pickup=not held and next_held
            drop=held and not next_held
            front=held and public["image"][3][5][0]==4
            door=bool(public_event["visible_door_opened"])
            pickups+=int(pickup);drops+=int(drop)
            forward_held+=int(held and action==2)
            front_held+=int(front);doors+=int(door)
            goals+=int(float(reward)>0)
            before_sha=owner.digest(public)
            repeated=before_sha in seen;seen.add(before_sha)
            events.append({"step":index+1,"role":role,"native_or_control_origin":provenance,
               "selected_reason":reason,"actual_original_source_action":action,
               "public_before":public,"public_after":after,
               "original_public_before_sha256":before_sha,
               "original_public_after_sha256":owner.digest(after),
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
                    raise ValueError("MG09B_GO_COLD_LIVE_CHECKPOINT")
            finally:fresh.close()
        elif ygg is not None:
            checkpoint=ygg.checkpoint()
            if (NativeContinuity.restore(checkpoint).checkpoint()!=checkpoint or
                ygg.samples!=1664+len(events)):
                raise ValueError("MG09B_YGG_COLD_LIVE_CHECKPOINT")
        elif control is not None:
            checkpoint=control.checkpoint()
            if (ConventionalEmpirical.restore(checkpoint).checkpoint()!=checkpoint or
                control.samples!=1664+len(events)):
                raise ValueError("MG09B_CONVENTIONAL_COLD_LIVE_CHECKPOINT")
        else:
            checkpoint=canon({"schema":"mg09b.separate-random-no-learn.v1",
                 "seed":seed,"selected":len(events)}).encode()
        return {"role":role,"seed_evaluator_only":seed,
            "original_start_public_sha256":start_sha,
            "original_live_selected_steps":len(events),"external_actions":0,
            "source_key_pickups":pickups,"source_key_drops":drops,
            "forward_while_held":forward_held,"front_door_while_held":front_held,
            "source_visible_door_openings":doors,"source_goal_rewards":goals,
            "distinct_public_views":len(seen),
            "episode_host_wall_s":round(time.perf_counter()-time_start,6),
            "episode_python_cpu_only_s":round(time.process_time()-cpu_start,6),
            "go_child_cpu_included":False,
            "cold_checkpoint_sha256":sha(checkpoint),"real_source_events":events}
    finally:
        env.close()
        if go is not None:go.close()


def run(binary,p):
    trained=fit(binary,p)
    rows=[]
    for seed in p["DEV"]["seeds"]:
        group=[episode(role,seed,trained,binary,p) for role in ROLES]
        if len({row["original_start_public_sha256"] for row in group})!=1:
            raise ValueError("MG09B_UNEQUAL_ORIGINAL_WORLD_START")
        rows.extend(group)
    if len(rows)!=12 or any(r["original_live_selected_steps"]<1 for r in rows):
        raise ValueError("MG09B_MISSING_ACTOR_ORIGINAL_SOURCE")
    summary={}
    fields=("original_live_selected_steps","source_key_pickups","source_key_drops",
            "forward_while_held","front_door_while_held","source_visible_door_openings",
            "source_goal_rewards","distinct_public_views")
    for role in ROLES:
        arms=[r for r in rows if r["role"]==role]
        summary[role]={name:sum(r[name] for r in arms) for name in fields}
        summary[role]["episodes"]=len(arms)
        summary[role]["external_actions"]=0
    # Resource observations vary across fresh OS processes and must not be
    # hashed as though they were deterministic original selected-source events.
    # Keep complete per-episode CPU/wall receipts outside the canonical trace.
    resources=[{"role":row["role"],"seed":row["seed_evaluator_only"],
                "episode_host_wall_s":row.pop("episode_host_wall_s"),
                "episode_python_cpu_only_s":row.pop("episode_python_cpu_only_s"),
                "go_child_cpu_included":row.pop("go_child_cpu_included")}
               for row in rows]
    met=all(summary[role]["source_goal_rewards"]>=1 for role in ROLES[:2])
    evidence={"original_upstream_farama":p["parent"]["original_farama"],
      "original_training_stream_sha256":trained["selected_history_sha256"],
      "original_source_fit_samples_each":trained["samples"],
      "frozen_source_pins":p["native"],"training_cold_sha256":trained["checkpoints_sha"],
      "frozen_original_world_seeds":p["DEV"]["seeds"],
      "no_manually_derived_stage_input_to_any_policy":True,
      "no_original_live_external_actions":True,
      "native_and_conventional_public_source_records":rows,
      "per_role_original_source_metrics":summary}
    return {"schema":SCHEMA,"classification":POS if met else NEG,
       "scientific_first_use":False,"accepted_native_model_promoted":False,
       "FORGE_or_CKB_controller_modified":False,"same_original_selected_FIT_samples":1664,
       "original_episode_count":12,"external_live_actions":0,
       "canonical_original_source_sha256":sha(canon(evidence).encode()),
       "canonical_original_source_evidence":evidence,\n       "nondeterministic_original_episode_resource_receipts":resources}


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
    report["go_child_CPU_excluded_from_python_CPU_measure"]=True
    a.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG09B_CLASSIFICATION",report["classification"])
    print("MG09B_ORIGINAL_SOURCE_SHA",report.get("canonical_original_source_sha256","NONE"))
    print("MG09B_SOURCE_COUNTS",json.dumps(report.get("canonical_original_source_evidence",{}).get("per_role_original_source_metrics",{}),sort_keys=True))
    if report["classification"]==BLOCK:
        print("MG09B_BLOCKER",report.get("error_type"),report.get("error"))
    return int(report["classification"]==BLOCK)
if __name__=="__main__":raise SystemExit(main())

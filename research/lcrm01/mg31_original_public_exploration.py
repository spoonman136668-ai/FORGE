#!/usr/bin/env python3
"""MG31 prospective original-world development data sufficiency, no MG28 rollout.

Previously qualified unchanged MG19 native actors plus two independent generic
source-public exploration controls and an unassisted original 7-action random.
Only source-selected env.step feedback; 12 newly exposed original DEV seeds.
"""
from __future__ import annotations
import argparse,base64,collections,hashlib,json,random,re,subprocess,time,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg31_original_public_exploration_prereg.json"
PARENT="0b207f714b8945354fd65b533caabb1b217ae055"
FREEZE="55a7244a43df5f16d8ca6e469d74276c91c4492c"
UPSTREAM="7f5853792ea7f04f75614661006d87fcf949f26d"
ROLES=("wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
       "generic_full_public_novelty_explorer","strong_action_only_ucb_explorer",
       "seeded_uniform_random")
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
SEEDS=((959101,959103,959107),(959201,959203,959207),
       (959301,959303,959307),(959401,959403,959407))
MISSION=re.compile(r"^pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)$")
COLOR={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}
OBJECT={"key":5,"ball":6,"box":7}

def encode(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
def digest(x):
    return hashlib.sha256(encode(x)).hexdigest()
def git(*args):
    return subprocess.run(["git",*args],capture_output=True,text=True,check=False,cwd=HERE.parents[1])
def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    d=p["design"]
    if (p.get("schema")!="itd02.mg31.genuine-original-public-exploration-opportunity-development.v1" or
        p.get("phase")!="FROZEN_BEFORE_FIRST_NEW_ORIGINAL_WORLD_ACTION_OR_EVALUATOR_CODE" or
        p["parent"]["forge_mg30"]!=PARENT or p["parent"]["upstream_farama"]!=UPSTREAM or
        tuple(d["families"])!=FAMILIES or tuple(tuple(x) for x in d["original_source_dev_seeds"])!=SEEDS or
        tuple(d["arms"])!=ROLES or d["max_selected_actions_per_actor_episode"]!=192 or
        d["zero_fit_for_all"] is not True or d["full_original_source_reproduction"]!=2 or
        not all(p["prohibitions"].values())):
        raise ValueError("MG31_ORIGINAL_WORLD_PREREG_DRIFT")
    selected=[x for group in SEEDS for x in group]
    if len(selected)!=12 or len(set(selected))!=12 or set(selected)&set(p["historical_known_exposed"]):
        raise ValueError("MG31_REUSED_ORIGINAL_SOURCE_SEED")
    if git("merge-base","--is-ancestor",PARENT,"HEAD").returncode:
        raise ValueError("MG31_NOT_ON_QUALIFIED_MG30_SOURCE_PARENT")
    if git("merge-base","--is-ancestor",FREEZE,"HEAD").returncode:
        raise ValueError("MG31_PREREG_NOT_FROZEN_BEFORE_EXECUTABLE")
    # Scoped source-custody check of everything reachable from the MG30 parent.
    # Do not pretend this queries disconnected private or parallel branches.
    for seed in selected:
        prior=git("grep","-n","-w",str(seed),PARENT,"--","research/lcrm01","docs/research")
        if prior.returncode==0:
            raise ValueError("MG31_ORIGINAL_SEED_PRIOR_SOURCE_EXPOSED:"+str(seed))
        if prior.returncode not in (1,):
            raise ValueError("MG31_PRIOR_SOURCE_SEED_CUSTODY_UNAVAILABLE")
    return p

class Explorer:
    """Independently programmed model-free source-selected state novelty and action-only controls."""
    def __init__(self,mode,counts=None,views=None,total=0):
        if mode not in ("full","action"):
            raise ValueError("MG31_EXPLORER_MODE")
        self.mode=mode
        self.counts={} if counts is None else counts
        self.views={} if views is None else views
        self.total=total
    def choose(self,public):
        state=digest(public)
        chosen=None;top=None
        tie=int(state[:2],16)%7 if self.mode=="full" else self.total%7
        row=self.counts.get(state if self.mode=="full" else "ALL",{})
        for i in range(7):
            a=(tie+i)%7
            cell=row.get(str(a),{"selected":0,"changed":0,"novel":0})
            # Frozen deterministic bounded, generic action-to-public effect acquisition.
            signal=cell["novel"] if self.mode=="full" else cell["changed"]
            points=(500*signal)//(cell["selected"]+2)+300//(cell["selected"]+1)
            if top is None or points>top:
                top=points;chosen=a
        return chosen
    def observe(self,before,action,after,reward,terminated):
        if type(action) is not int or action not in range(7):
            raise ValueError("MG31_NOT_ORIGINAL_SELECTED_ACTION")
        src=digest(before);successor=digest(after)
        key=src if self.mode=="full" else "ALL"
        row=self.counts.setdefault(key,{})
        cell=row.setdefault(str(action),{"selected":0,"changed":0,"novel":0})
        cell["selected"]+=1
        cell["changed"]+=int(src!=successor)
        cell["novel"]+=int(successor not in self.views)
        self.views[successor]=self.views.get(successor,0)+1
        self.total+=1
    def checkpoint(self):
        return encode({"schema":"mg31.source-generic-exploration.v1","mode":self.mode,
            "counts":self.counts,"views":self.views,"total":self.total})
    @classmethod
    def restore(cls,blob):
        wire=json.loads(blob)
        if set(wire)!={"schema","mode","counts","views","total"} or wire["schema"]!="mg31.source-generic-exploration.v1":
            raise ValueError("MG31_COLD_EXPLORER_SCHEMA")
        a=cls(wire["mode"],wire["counts"],wire["views"],wire["total"])
        if a.checkpoint()!=blob or a.total!=sum(c["selected"] for row in a.counts.values() for c in row.values()):
            raise ValueError("MG31_COLD_SELECTED_GENERIC_STATE_BAD")
        return a

def selected_effect(e):
    before=e["before"];after=e["after"];action=e["action"]
    p=before["image"][3][5];q=after["image"][3][5]
    heading=before["direction"]==after["direction"]
    target=MISSION.fullmatch(before["mission"])
    picked=(heading and action==3 and p[0] in (5,6,7) and q[0]==1)
    target_pickup=bool(picked and target and
        p[0]==OBJECT[target.group(2)] and p[1]==COLOR[target.group(1)])
    opening=bool(heading and action==5 and p[0]==q[0]==4 and
        p[1]==q[1] and p[2]==2 and q[2]==0)
    return {"visible_public_pickup":int(picked),
            "exact_mission_target_public_disappearance":int(target_pickup),
            "real_public_locked_door_open":int(opening),
            "original_positive_terminal_goal":int(e["reward"]>0 and e["terminated"])}

def explore_episode(gym,source_entry,family,seed,mode,prior,cap,public,digest_original):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=source_entry or env.action_space.n!=7:
            raise ValueError("MG31_FARAMA_REGISTRY_7_ACTION_MISMATCH")
        raw,_=env.reset(seed=seed)
        first=public(raw);starting=digest_original(first)
        actor=Explorer(mode) if prior is None else Explorer.restore(prior)
        if actor.mode!=mode:
            raise ValueError("MG31_EXPLORER_WRONG_COLD_MODE")
        begin=actor.total
        mission=first["mission"]
        events=[]
        for step in range(1,cap+1):
            b=public(raw)
            if b["mission"]!=mission:raise ValueError("MG31_SOURCE_MISSION_CHANGED")
            a=actor.choose(b)
            if type(a)is not int or a not in range(7):
                raise ValueError("MG31_INVALID_EXPLORATION_SOURCE_ACTION")
            raw2,reward,term,trunc,_=env.step(a)
            next_frame=public(raw2)
            if next_frame["mission"]!=mission or type(term)is not bool or type(trunc)is not bool:
                raise ValueError("MG31_INVALID_SOURCE_MISSION_OR_TERMINAL")
            actor.observe(b,a,next_frame,float(reward),term)
            events.append({"index":step,"before":b,"action":a,"after":next_frame,
                "mission":mission,"policy_status":"MG31_GENERIC_SELECTED_"+mode,
                "reward":float(reward),"terminated":term,"truncated":trunc,
                "before_sha256":digest_original(b),"after_sha256":digest_original(next_frame),
                "external_actions":0})
            raw=raw2
            if term or trunc:break
        state=actor.checkpoint()
        if Explorer.restore(state).checkpoint()!=state or actor.total!=begin+len(events):
            raise ValueError("MG31_SELECTED_EXPLORATION_COLD_MEMORY_LOSS")
        row={"family":family,"seed_dev_exposed":seed,
             "role":"generic_full_public_novelty_explorer" if mode=="full" else "strong_action_only_ucb_explorer",
             "public_start_sha256":starting,"original_public_mission":mission,
             "original_source_actions":len(events),"prior_selected_source_samples":begin,
             "selected_source_samples_after":actor.total,
             "original_terminal_goal_rewards":sum(int(e["reward"]>0 and e["terminated"]) for e in events),
             "observed_public_changes":sum(e["before_sha256"]!=e["after_sha256"] for e in events),
             "unique_public_views":len({e["before_sha256"] for e in events}),
             "distinct_actions":len({e["action"] for e in events}),
             "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
             "source_events_sha256":digest_original(events),"source_events":events}
        return row,state
    finally:
        env.close()

def execute(source_root,go_binary,p):
    import gymnasium as gym
    import minigrid
    from mg17_original_family_source_qual import frozen as upstream_frozen,attest_source,public,digest as og_digest
    from mg21_original_development import one_episode,ROLES as old_roles
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG31_NOT_PINNED_ORIGINAL_UPSTREAM_RUNTIME")
    source=upstream_frozen()
    attest_source(source_root,source)
    entry={x["id"]:x["entry_point"] for x in source["families"]}
    results=[]
    for family,seeds in zip(FAMILIES,SEEDS):
        inherited={role:None for role in ROLES}
        for seed in seeds:
            by_seed=[]
            for role in ROLES:
                if role in ROLES[0:2]:
                    old=old_roles[0] if role==ROLES[0] else old_roles[1]
                    row,metrics,new_state=one_episode(family,seed,old,192,inherited[role],go_binary,entry[family])
                    row["role"]=role
                elif role==ROLES[4]:
                    row,metrics,new_state=one_episode(family,seed,old_roles[3],192,None,go_binary,entry[family])
                    row["role"]=role
                else:
                    mode="full" if role==ROLES[2] else "action"
                    row,new_state=explore_episode(gym,entry[family],family,seed,mode,inherited[role],192,public,og_digest)
                if role!=ROLES[4]:
                    inherited[role]=new_state
                by_seed.append(row);results.append(row)
            if len({e["public_start_sha256"] for e in by_seed})!=1:
                raise ValueError("MG31_UNEQUAL_ORIGINAL_SEED_RESET")
    if len(results)!=60 or not all(1<=r["original_source_actions"]<=192 for r in results):
        raise ValueError("MG31_MISSING_REAL_ORIGINAL_SOURCE_EPISODES")
    metrics={}
    for family in FAMILIES:
        metrics[family]={}
        for role in ROLES:
            matching=[r for r in results if r["family"]==family and r["role"]==role]
            if len(matching)!=3:
                raise ValueError("MG31_INCOMPLETE_THREE_SEED_MATRIX")
            if role!=ROLES[4] and (matching[0]["prior_selected_source_samples"]!=0 or
                matching[1]["prior_selected_source_samples"]!=matching[0]["selected_source_samples_after"] or
                matching[2]["prior_selected_source_samples"]!=matching[1]["selected_source_samples_after"]):
                raise ValueError("MG31_NO_PERSISTENT_COLD_SOURCE_HISTORY")
            tallies=collections.Counter()
            for r in matching:
                for e in r["source_events"]:
                    tallies.update(selected_effect(e))
            metrics[family][role]={**{key:tallies[key] for key in ("visible_public_pickup",\n                "exact_mission_target_public_disappearance","real_public_locked_door_open",\n                "original_positive_terminal_goal")},"episodes":3,
                "original_selected_actions":sum(z["original_source_actions"] for z in matching),
                "distinct_positive_seed_episodes":sum(r["original_terminal_goal_rewards"]>0 for r in matching)}
    threshold=p["prereg_sufficiency"]
    sufficient=True
    for family in FAMILIES[1:]:
        aggregate=collections.Counter()
        for role in ROLES:
            aggregate.update({k:v for k,v in metrics[family][role].items() if k in
              ("exact_mission_target_public_disappearance","real_public_locked_door_open",
               "distinct_positive_seed_episodes")})
        if (aggregate["exact_mission_target_public_disappearance"] <
             threshold["each_unfamiliar_family_true_visible_target_pickup_effects_at_least"] or
            aggregate["real_public_locked_door_open"] <
             threshold["each_unfamiliar_family_real_locked_door_openings_at_least"] or
            aggregate["distinct_positive_seed_episodes"] <
             threshold["each_unfamiliar_family_independent_positive_goal_episodes_at_least"]):
            sufficient=False
        # Source acquisition only: require the generic non-scripted explorer
        # to outperform the strong action-only competitor on actual relevant effects.
        a=metrics[family][ROLES[2]];b=metrics[family][ROLES[3]]
        if (a["exact_mission_target_public_disappearance"] +
             a["real_public_locked_door_open"] <=
            b["exact_mission_target_public_disappearance"] +
             b["real_public_locked_door_open"]):
            sufficient=False
    result={"schema":"itd02.mg31.original-world-opportunity-development-source.v1",
        "classification":p["prereg_sufficiency"]["if_pass"] if sufficient else p["prereg_sufficiency"]["if_failure"],
        "source_upstream_farama":UPSTREAM,
        "original_60_episodes":results,
        "original_selected_action_count":sum(r["original_source_actions"] for r in results),
        "per_family_per_arm":metrics,"zero_external_actions":True,"scientific_first_use":False,
        "mg28_live_native_rollout_permitted":False,
        "controller_or_accepted_models_modified":False,
        "exposed_original_dev_seeds":list(map(list,SEEDS)),
        "same_three_original_seeds_per_arm":True}
    return {"schema":result["schema"],"source":result,"canonical_source_sha256":digest(result)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--native-go",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--compare",nargs=2,type=Path)
    opt=parser.parse_args()
    p=freeze()
    if opt.preflight:
        a=Explorer("full");b=Explorer("action")
        mission="pick up the red box"
        src={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
             "direction":0,"mission":mission}
        next_frame=dict(src,direction=1)
        for actor in (a,b):
            for _ in range(7):
                selected=actor.choose(src)
                actor.observe(src,selected,next_frame,0,False)
            if Explorer.restore(actor.checkpoint()).checkpoint()!=actor.checkpoint():
                raise ValueError("MG31_SOURCE_ONLY_COLD_EXPLORATION_FAILURE")
        print("MG31_FROZEN_SOURCE_LINEAGE_AND_NON_SCRIPTED_EXPLORER_PREFLIGHT_PASS")
        return
    if opt.compare:
        a,b=[json.loads(x.read_text()) for x in opt.compare]
        if (a.get("source")!=b.get("source") or
            a.get("canonical_source_sha256")!=b.get("canonical_source_sha256") or
            a.get("canonical_source_sha256")!=digest(a["source"]) or
            len(a["source"]["original_60_episodes"])!=60 or
            a["source"]["scientific_first_use"] is not False or
            a["source"]["zero_external_actions"] is not True):
            raise ValueError("MG31_INDEPENDENT_SOURCE_PROCESSES_OR_CUSTODY_MISMATCH")
        print("MG31_TWO_ORIGINAL_FARAMA_SOURCE_PROCESSES_PASS",a["canonical_source_sha256"])
        print("MG31_DEVELOPMENT_SOURCE_OPPORTUNITY_METRICS",json.dumps(a["source"]["per_family_per_arm"],sort_keys=True))
        return
    if not all((opt.source_root,opt.native_go,opt.output)):
        parser.error("require --source-root --native-go --output or --compare")
    started=time.perf_counter()
    try:
        result=execute(opt.source_root,opt.native_go,p)
    except Exception as exc:
        result={"schema":"itd02.mg31.original-world-opportunity-development-source.v1",
            "classification":"MG31_AUTHENTIC_ORIGINAL_SOURCE_BLOCKED_NO_SCIENCE",
            "error_type":type(exc).__name__,"error":str(exc),
            "trace_tail":traceback.format_exc().splitlines()[-12:]}
    result["host_wall_time_outside_canonical_source_seconds"]=round(time.perf_counter()-started,6)
    opt.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("MG31_ORIGINAL_WORLD_CLASSIFICATION",result["classification"])
    if "BLOCKED" in result["classification"]:
        raise ValueError(result["error"])
    print("MG31_ORIGINAL_WORLD_SOURCE_SHA",result["canonical_source_sha256"])
if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""MG42 authentic original DEV: public selected-effect anti-repickup cooldown.

A frozen engineered public-only policy. It does not claim learned action
semantics, native intelligence improvement or scientific first-use.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,subprocess,time,traceback,inspect
from pathlib import Path
from mg40_action_precondition_dev import (
 FAMILIES,UPSTREAM,digest,event_metric,mg33_episode,mg34_episode,
 corrected_class,control_episode,original_mg38_episode,ablated_episode,
 evidence_episode,EvidenceNavigation,NavigationAwareModel)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg42_progress_cooldown_original_prereg.json"
PARENT="404b9c7d4df594c186df7d758b71f5f676e67c92"
FREEZE="4aaf7a622cf925e325e2695386aca01bc4a0e450"
ROLES=(
 "wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
 "mg33_public_history_frontier_unchanged","mg34_graph_lookahead_unchanged",
 "mg33c_actiononly_ucb_exact_source","mg33c_actiononly_round_robin_exact_source",
 "mg38_generic_affordance_prior_enabled_exact_source",
 "mg39b_generic_affordance_prior_removed",
 "mg40_precondition_memory_enabled","mg40_precondition_memory_ablated",
 "mg42_progress_cooldown_enabled","seeded_uniform_random")
SEEDS=((1021101,1021103,1021107),(1021201,1021203,1021207),
       (1021301,1021303,1021307),(1021401,1021403,1021407))

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)
def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    c=p["cohort"];m=p["mechanism"]
    if (p["schema"]!="itd02.mg42.original-public-effect-cycle-cooldown-dev.v1"
        or p["phase"]!="PROSPECTIVE_FROZEN_BEFORE_MG42_EXECUTABLE_AND_ANY_NEW_ORIGINAL_ACTIONS"
        or p["base"]["mg41_head"]!=PARENT
        or p["pins"]["farama"]!=UPSTREAM
        or tuple(c["families"])!=FAMILIES or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["dev_seed_rows"]))!=SEEDS
        or c["original_actor_episodes"]!=144
        or c["source_actions_max_per_episode"]!=192
        or c["full_independent_reproductions"]!=2
        or m["cooldown_after_confirmed_drop_selected_steps"]!=16
        or not all(p["isolation"].values())):
        raise ValueError("MG42_FROZEN_SOURCE_PROTOCOL_DRIFT")
    seeds=[s for row in SEEDS for s in row]
    if len(seeds)!=12 or len(set(seeds))!=12:
        raise ValueError("MG42_DUPLICATED_FRESH_SOURCE_SEED")
    for parent in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",parent,"HEAD").returncode!=0:
            raise ValueError("MG42_SOURCE_FREEZE_NOT_ANCESTOR")
    for seed in seeds:
        old=git("grep","-n","-w",str(seed),PARENT,"--","research/lcrm01","docs/research")
        if old.returncode==0:
            raise ValueError("MG42_PRIOR_EXPOSED_SEED_REUSE")
        if old.returncode!=1:
            raise ValueError("MG42_CANNOT_PROVE_PARENT_SEED_LINEAGE")
    return p

class CooldownNavigation(EvidenceNavigation):
    """Original MG40 source-selected empirical state plus bounded effect veto."""
    SCHEMA="mg42.public-selected-effect-16-step-cooldown.v1"
    def __init__(self,*args,cooldown=0,**kwargs):
        super().__init__(*args,**kwargs)
        if type(cooldown) is not int or not 0<=cooldown<=16:
            raise ValueError("MG42_INVALID_COOLDOWN_STATE")
        self.cooldown=cooldown

    def begin_episode(self):
        super().begin_episode()
        self.cooldown=0

    def choose(self,public):
        selected=super().choose(public)
        if (self.cooldown>0 and selected==3 and
                public["image"][3][5][0] in (5,6,7)):
            selected=0 if self.global_actions[0]["n"]<=self.global_actions[1]["n"] else 1
            if self.pending is None:
                raise ValueError("MG42_MISSING_OWN_SELECTED_PENDING_ACTION")
            self.pending=(self.pending[0],selected)
        return selected

    def observe_selected(self,before,action,after,reward,terminated):
        front=before["image"][3][5]
        later=after["image"][3][5]
        observed_drop=(action==4 and front[0]==1 and later[0] in (5,6,7)
                       and before["direction"]==after["direction"])
        super().observe_selected(before,action,after,reward,terminated)
        self.cooldown=max(0,self.cooldown-1)
        if observed_drop:self.cooldown=16

    def checkpoint(self):
        original=json.loads(EvidenceNavigation.checkpoint(self))
        original["schema"]=EvidenceNavigation.SCHEMA
        return json.dumps({"schema":self.SCHEMA,"base":original,"cooldown":self.cooldown},
                 sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8")
    @classmethod
    def restore(cls,raw):
        d=json.loads(raw)
        if (set(d)!={"schema","base","cooldown"} or d["schema"]!=cls.SCHEMA
            or type(d["cooldown"]) is not int or not 0<=d["cooldown"]<=16):
            raise ValueError("MG42_INVALID_COOLDOWN_COLD_SCHEMA")
        old=EvidenceNavigation.restore(json.dumps(d["base"],sort_keys=True,
            separators=(",",":"),ensure_ascii=True).encode("utf8"))
        if not old.evidence_enabled:
            raise ValueError("MG42_COOLDOWN_DISABLED_OCCUPANCY_PROXY")
        model=cls(cooldown=d["cooldown"])
        model.__dict__.update(old.__dict__)
        if model.checkpoint()!=raw:
            raise ValueError("MG42_COLD_SELECTED_EVIDENCE_CHECKPOINT_DRIFT")
        return model

def cooldown_episode(gym,entry,family,seed,prior,cap,public,original_digest):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG42_INVALID_ORIGINAL_ENVIRONMENT")
        raw,_=env.reset(seed=seed)
        first=public(raw);mission=first["mission"]
        model=CooldownNavigation() if prior is None else CooldownNavigation.restore(prior)
        model.begin_episode()
        start_n=model.total;events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG42_PUBLIC_MISSION_DRIFT")
            action=model.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG42_ORIGINAL_SELECTED_SOURCE_FEEDBACK_INVALID")
            model.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG42_PUBLIC_EFFECT_PROGRESS_COOLDOWN"})
            raw=raw2
            if term or trunc:break
        state=model.checkpoint()
        if (CooldownNavigation.restore(state).checkpoint()!=state
            or model.total!=start_n+len(events)):
            raise ValueError("MG42_COLD_PUBLIC_SOURCE_HISTORY_LOSS")
        return ({"family":family,"role":ROLES[10],"seed_dev_exposed":seed,
                 "public_start_sha256":original_digest(first),
                 "original_public_mission":mission,
                 "original_source_actions":len(events),
                 "prior_selected_source_samples":start_n,
                 "selected_source_samples_after":model.total,
                 "original_terminal_goal_rewards":
                    sum(int(e["reward"]>0 and e["terminated"]) for e in events),
                 "observed_public_changes":
                    sum(e["before_sha256"]!=e["after_sha256"] for e in events),
                 "unique_public_views":len({e["before_sha256"] for e in events}),
                 "distinct_actions":len({e["action"] for e in events}),
                 "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
                 "observed_public_proxy_pickups":model.observed_pickups,
                 "observed_public_proxy_drops":model.observed_drops,
                 "source_events_sha256":original_digest(events),
                 "source_events":events},state)
    finally:env.close()

def source_only_preflight():
    p=frozen()
    # The inherited MG40 model is imported from pinned immutable parent source.
    a={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
       "direction":0,"mission":"pick up the red box"}
    b={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
       "direction":0,"mission":"pick up the red box"}
    a["image"][3][5]=[7,0,0]
    c=CooldownNavigation()
    c.pending=(digest(a),3)
    c.observe_selected(a,3,b,0.0,False)
    if not c.occupied_proxy:
        raise ValueError("MG42_MISSING_PUBLIC_PICKUP_EVIDENCE")
    c.pending=(digest(b),4)
    c.observe_selected(b,4,a,0.0,False)
    if c.cooldown!=16 or c.occupied_proxy:
        raise ValueError("MG42_MISSING_PUBLIC_DROP_COOLDOWN")
    raw=c.checkpoint()
    if CooldownNavigation.restore(raw).checkpoint()!=raw:
        raise ValueError("MG42_COLD_CHECKPOINT_INEXACT")
    old=EvidenceNavigation()
    old.pending=(digest(a),3)
    old.observe_selected(a,3,b,0.0,False)
    old.pending=(digest(b),4)
    old.observe_selected(b,4,a,0.0,False)
    selected=c.choose(a);baseline=old.choose(a)
    if baseline==3 and selected==3:
        raise ValueError("MG42_PICKUP_COOLDOWN_VETO_NOT_APPLIED")
    if selected not in range(7):
        raise ValueError("MG42_INVALID_SELECTED_ACTION")
    c.observe_selected(a,selected,a,0.0,False)
    if c.cooldown!=15:raise ValueError("MG42_COOLDOWN_NOT_ADVANCED")
    c.begin_episode()
    if c.cooldown!=0 or c.total!=3:
        raise ValueError("MG42_COLD_HISTORY_OR_EPISODE_RESET_DRIFT")
    print("MG42_FROZEN_SELECTED_PUBLIC_EFFECT_COOLDOWN_PREFLIGHT_PASS_NO_SCIENCE")
    return p

def summarize(rows):
    totals={}
    for family in FAMILIES:
        totals[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG40_INCOMPLETE_TRIPLE_COLD_ORIGINAL_SOURCE")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG40_COLD_SOURCE_MEMORY_NOT_RETAINED")
            action_hist=[0]*7
            seen=collections.Counter()
            goal_episodes=0
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG40_ORIGINAL_EVENT_SOURCE_HASH_CHANGED")
                goal_episodes+=int(ep["original_terminal_goal_rewards"]>0)
                for e in ep["source_events"]:
                    z=event_metric(e)
                    seen.update(z)
                    act=e["action"]
                    action_hist[act]+=1
                    f=e["before"]["image"][3][5]
                    aft=e["after"]["image"][3][5]
                    if act==4:
                        seen["selected_drops"]+=1
                        if f[0]==1:
                            seen["selected_drops_empty_front"]+=1
                            if aft[0] in (5,6,7) and e["before"]["direction"]==e["after"]["direction"]:
                                seen["actual_public_drop_effects"]+=1
                    if act==3 and f[0] in (5,6,7) and aft[0]==1 and e["before"]["direction"]==e["after"]["direction"]:
                        seen["actual_public_generic_pickup_effects"]+=1
            if sum(action_hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG40_ORIGINAL_SOURCE_ACTION_DENOMINATOR_MISMATCH")
            totals[family][role]={
                "episodes":3,"actions":sum(action_hist),
                "action_histogram":action_hist,
                "positive_goal_episodes":goal_episodes,
                "target_front":seen["target_front_frames"],
                "target_pick_attempt":seen["target_front_selected_pickup_attempts"],
                "target_pick_effect":seen["target_front_selected_effects"],
                "target_visible":seen["target_any_visible_frames"],
                "door_open":seen["locked_door_openings"],
                "selected_drops":seen["selected_drops"],
                "selected_drops_empty_front":seen["selected_drops_empty_front"],
                "actual_public_drop_effects":seen["actual_public_drop_effects"],
                "actual_public_generic_pickup_effects":seen["actual_public_generic_pickup_effects"]}
    return totals

def execute(root,native_go,control_root,p):
    import gymnasium as gym
    import minigrid
    from mg17_original_family_source_qual import (
        frozen as original_frozen,attest_source,public,digest as original_digest)
    from mg21_original_development import one_episode,ROLES as native_roles
    if not Path(minigrid.__file__).resolve().is_relative_to(root.resolve()):
        raise ValueError("MG40_FARAMA_SOURCE_NOT_FROM_PINNED_ROOT")
    upstream=original_frozen()
    attest_source(root,upstream)
    registry={f["id"]:f["entry_point"] for f in upstream["families"]}
    exact_control=corrected_class(control_root)
    result=[]
    for family,seeds in zip(FAMILIES,SEEDS):
        memory={role:None for role in ROLES}
        for seed in seeds:
            starts=[]
            for role in ROLES:
                if role in (ROLES[0],ROLES[1],ROLES[-1]):
                    actual=(native_roles[0] if role==ROLES[0]
                            else native_roles[1] if role==ROLES[1] else native_roles[3])
                    ep,_,state=one_episode(family,seed,actual,192,
                                           memory[role],native_go,registry[family])
                elif role==ROLES[2]:
                    ep,state=mg33_episode(gym,registry[family],family,seed,
                                         memory[role],192,public,original_digest)
                elif role==ROLES[3]:
                    ep,state=mg34_episode(gym,registry[family],family,seed,
                                         memory[role],192,public,original_digest)
                elif role in (ROLES[4],ROLES[5]):
                    mode="ucb" if role==ROLES[4] else "round_robin"
                    ep,state=control_episode(gym,registry[family],family,seed,
                                              mode,memory[role],192,public,
                                              original_digest,exact_control)
                elif role==ROLES[6]:
                    ep,state=original_mg38_episode(gym,registry[family],family,
                                                   seed,memory[role],192,
                                                   public,original_digest)
                elif role==ROLES[7]:
                    ep,state=ablated_episode(gym,registry[family],family,seed,
                                             memory[role],192,public,original_digest)
                elif role in (ROLES[8],ROLES[9]):
                    ep,state=evidence_episode(gym,registry[family],family,
                                              seed,memory[role],192,public,
                                              original_digest,role==ROLES[8])
                elif role==ROLES[10]:
                    ep,state=cooldown_episode(gym,registry[family],family,
                                               seed,memory[role],192,public,
                                               original_digest)
                else:
                    raise ValueError("MG40_UNAUTHORIZED_ORIGINAL_ROLE")
                ep["role"]=role
                starts.append(ep["public_start_sha256"])
                if role!=ROLES[-1]:
                    memory[role]=state
                result.append(ep)
            if len(set(starts))!=1:
                raise ValueError("MG40_NOT_MATCHED_ORIGINAL_SEED_RESET")
    if len(result)!=144 or any(not (1<=x["original_source_actions"]<=192)
                                for x in result):
        raise ValueError("MG40_INCOMPLETE_132_EPISODES")
    table=summarize(result)
    unfamiliar=FAMILIES[1:]
    roles=(ROLES[10],ROLES[8],ROLES[9],ROLES[6],ROLES[7])
    effects={role:sum(table[f][role]["target_pick_effect"] for f in unfamiliar)
             for role in roles}
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in unfamiliar)
           for role in roles}
    drops={role:sum(table[f][role]["actual_public_drop_effects"] for f in unfamiliar)
           for role in roles}
    from mg41_mg40_public_effect_cycles import reversible_pairs
    pairs={role:sum(
        reversible_pairs(ep["source_events"])["reversible_pickup_then_drop_within_4"]
        for ep in result if ep["role"]==role and ep["family"] in unfamiliar)
        for role in roles}
    candidate=ROLES[10]
    positive_families=sum(table[f][candidate]["positive_goal_episodes"]>0
                          for f in unfamiliar)
    difficult=any(table[f][candidate]["positive_goal_episodes"]>0
                  for f in FAMILIES[1:3])
    success=(pairs[candidate]<pairs[ROLES[8]]
             and effects[candidate]>=1 and positive_families>=2 and difficult
             and all(goals[candidate]>goals[r] for r in roles[1:]))
    label=p["frozen_dev_acceptance"]
    source={"schema":"itd02.mg42.original-public-selected-progress-cooldown.dev.v1",
        "classification":label["pass"] if success else label["fail"],
        "original_144_episodes":result,"original_selected_action_count":
            sum(x["original_source_actions"] for x in result),
        "per_family_per_role":table,
        "paired_evidence_on_off_and_cooldown":{
            "target_effects":effects,"positive_goals":goals,
            "public_drop_effects":drops,"short_reversible_effect_pairs":pairs,
            "candidate_positive_unfamiliar_families":positive_families,
            "candidate_positive_unlock_or_blocked":difficult,
            "filter_supported":success},
        "source_parent":PARENT,"farama_source":UPSTREAM,
        "exposed_dev_seeds":[list(x) for x in SEEDS],
        "scientific_first_use":False,"zero_external_actions":True,
        "native_models_or_controllers_modified":False,
        "mg28_native_rollout_permitted":False,
        "native_resource_parity_qualified":False,
        "hand_engineered_public_effect_detectors":True}
    return {"schema":source["schema"],"source":source,
            "canonical_source_sha256":digest(source)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--native-go",type=Path)
    ap.add_argument("--control-root",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--compare",nargs=2,type=Path)
    a=ap.parse_args()
    p=frozen()
    if a.preflight:
        source_only_preflight()
        return
    if a.compare:
        first,second=[json.loads(x.read_text(encoding="utf8")) for x in a.compare]
        if (first.get("source")!=second.get("source")
            or first.get("canonical_source_sha256")!=second.get("canonical_source_sha256")
            or first.get("canonical_source_sha256")!=digest(first["source"])
            or len(first["source"]["original_144_episodes"])!=144
            or first["source"]["scientific_first_use"] is not False
            or first["source"]["zero_external_actions"] is not True):
            raise ValueError("MG42_TWO_ORIGINAL_PROCESSES_NOT_MATCHED")
        print("MG42_TWO_INDEPENDENT_ORIGINAL_SOURCE_PROCESSES_IDENTICAL",first["canonical_source_sha256"])
        print("MG42_FROZEN_DEV_CLASSIFICATION",first["source"]["classification"])
        print("MG42_PAIRED_EVIDENCE_AND_COOLDOWN",
              json.dumps(first["source"]["paired_evidence_on_off_and_cooldown"],sort_keys=True))
        return
    if any(x is None for x in (a.source_root,a.native_go,a.control_root,a.output)):
        ap.error("require --source-root --native-go --control-root --output")
    started=time.perf_counter()
    try:result=execute(a.source_root,a.native_go,a.control_root,p)
    except Exception as err:
        result={"schema":"itd02.mg42.original-public-selected-progress-cooldown.dev.v1",
                "classification":"MG42_ORIGINAL_SOURCE_BLOCKED_NO_SCIENCE",
                "error_type":type(err).__name__,"error":str(err),
                "trace_tail":traceback.format_exc().splitlines()[-15:]}
    result["host_wall_time_outside_canonical_source_seconds"]=round(time.perf_counter()-started,6)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf8")
    status=result.get("classification",result.get("source",{}).get("classification","MG42_MISSING_CLASSIFICATION"))
    print("MG42_ORIGINAL_SOURCE_CLASSIFICATION",status)
    if "BLOCKED" in status:raise ValueError(result.get("error","MG42_UNQUALIFIED_SOURCE_BLOCKER"))
    print("MG42_ORIGINAL_SOURCE_SHA256",result["canonical_source_sha256"])
if __name__=="__main__":main()

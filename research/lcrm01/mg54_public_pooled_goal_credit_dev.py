#!/usr/bin/env python3
"""MG54: original Farama mission-conditioned public pooled credit DEV, no native promotion.

Original native and conventional actors imported from pinned previously qualified source.
Farama original source and previously qualified source-selected actors only.
Public state abstractions and goal weights engineered, not scientific first-use.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,subprocess,time,traceback
from pathlib import Path

from mg39b_original_affordance_ablation import (
    UPSTREAM,digest,event_metric,mg33_episode,mg34_episode,corrected_class,
    control_episode,original_mg38_episode,ablated_episode)
from mg40_action_precondition_dev import evidence_episode
from mg42_observed_reversal_guard import reversal_episode
from mg43_public_target_action_value import action_value_episode
from mg47_door_action_effect_memory_dev import (
    DoorMemoryNavigation as OriginalDoorMemory,
    door_episode as original_door_episode,
    preflight as original_door_preflight)
from mg43_public_target_action_value import public_exact_target_front
from mg37_mg36_navigation_audit import MISSION,TYPES,COLORS
from mg50_public_predictive_transition_dev import predictive_episode as original_mg50_episode
from mg52_goal_relevant_eligibility_dev import (goal_episode as original_mg52_episode,
    observed_goal_signal as original_goal_signal, preflight as original_mg52_preflight)
from mg44_public_precondition_release import (
    PublicSlotRelease,public_release_episode,synthetic_source_preflight
    as original_mg44_preflight)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg54_public_pooled_goal_credit_prereg.json"
PARENT="c75c98685a74769fb5933df7d894dc6aa6363edc"
FREEZE="f34ce003b5ec8a6e5f91b2f6dcee5fec25dffbf9"
POLICY_BLOB="2f93b9b5227d97d318cf5c05544f85c303496da7"
REGISTER_BLOB="41b4a731255d19bdf61072b7100e752a759a3ae4"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0",
          "MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
ENTRIES=("minigrid.envs:KeyCorridorEnv","minigrid.envs:KeyCorridorEnv",
         "minigrid.envs:ObstructedMaze_1Dlhb")
SEEDS=((1051101,1051103,1051107),(1051201,1051203,1051207),
       (1051301,1051303,1051307))
ROLES=("wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
 "mg33_public_history_frontier_unchanged","mg34_graph_lookahead_unchanged",
 "mg33c_actiononly_ucb_exact_source","mg33c_actiononly_round_robin_exact_source",
 "mg38_generic_affordance_prior_enabled_exact_source",
 "mg39b_generic_affordance_prior_removed",
 "mg40_precondition_memory_enabled_unchanged",
 "mg40_precondition_memory_ablated_unchanged",
 "mg42_observed_reversal_guard_unchanged",
 "mg43_engineered_target_matcher_plus_learned_action_value_unchanged",
 "mg43_engineered_target_matcher_no_action_value_ablation_unchanged",
 "mg44_public_precondition_release_enabled_UNMODIFIED",
 "mg44_public_precondition_release_disabled_UNMODIFIED",
 "mg47_door_action_effect_memory_enabled_unchanged",
 "mg47_door_action_effect_memory_disabled_unchanged",
 "mg50_empirical_public_transition_uncertainty_enabled_UNMODIFIED",
 "mg50_empirical_public_transition_uncertainty_disabled_UNMODIFIED",
 "mg52_original_goal_relevant_eligibility_enabled_UNMODIFIED",
 "mg52_original_goal_relevant_eligibility_disabled_UNMODIFIED",
 "mg54_public_context_pooled_goal_credit_enabled",
 "mg54_public_context_pooled_goal_credit_disabled",
 "seeded_uniform_random")
SEEDS=((1101101,1101103,1101107),(1101201,1101203,1101207),
       (1101301,1101303,1101307))

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    c=p["cohort"];m=p["mechanism"];v=m["coefficients"]
    if (p["schema"]!="itd02.mg54.original-public-mission-coarse-context-transfer-eligibility.dev.v1"
        or p["phase"]!="FROZEN_PROSPECTIVE_BEFORE_MG54_EXECUTABLE_AND_ALL_NEW_ORIGINAL_WORLD_ACTIONS"
        or p["parent"]["mg53_exact_head"]!=PARENT
        or p["source"]["farama_original"]!=UPSTREAM
        or p["source"]["farama_registration_blob"]!=REGISTER_BLOB
        or tuple((e["id"],e["entry"]) for e in c["families"])!=tuple(zip(FAMILIES,ENTRIES))
        or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["new_dev_seeds"]))!=SEEDS
        or c["expected_episodes"]!=216
        or c["cap_own_selected_actions_per_episode"]!=192
        or c["independent_complete_source_processes"]!=2
        or v!={"max_keys":2048,"trace_window":8,"discount_ratio":"1/2",
               "min_selected_samples":2,"value_margin":"1/8",
               "weights":{"new_target_visible":2,"real_locked_door_opening":3,
                          "exact_target_pickup_effect":6,
                          "original_terminal_positive_goal":10},
               "candidate_actions":[0,1,2]}
        or not all(p["prohibitions"].values())):
        raise ValueError("MG54_FROZEN_PROSPECTIVE_ORIGINAL_SOURCE_DEV_PROTOCOL_DRIFT")
    flat=[q for subset in SEEDS for q in subset]
    if len(flat)!=9 or len(set(flat))!=9:
        raise ValueError("MG54_NEW_DEV_SEED_DUPLICATED")
    for parent in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",parent,"HEAD").returncode:
            raise ValueError("MG54_FREEZE_NOT_ANCESTOR_OF_NEW_EXECUTABLE")
    for seed in flat:
        scan=git("grep","-n","-w",str(seed),PARENT,"--",
                 "research/lcrm01","docs/research")
        if scan.returncode==0:raise ValueError("MG54_SOURCE_DEV_SEED_ALREADY_EXPOSED")
        if scan.returncode!=1:raise ValueError("MG54_PRIOR_SOURCE_SEED_SEARCH_UNAVAILABLE")
    blob=git("hash-object","research/lcrm01/mg44_public_precondition_release.py")
    if blob.returncode or blob.stdout.strip()!=POLICY_BLOB:
        raise ValueError("MG54_UNCHANGED_MG44_POLICY_SOURCE_BLOB_MISMATCH")
    return p

def source_target_visible(public):
    m=MISSION.fullmatch(public["mission"])
    if not m:return False
    col,kind=m.groups()
    return any(c[0]==TYPES[kind] and c[1]==COLORS[col]
               for row in public["image"] for c in row)

def pooled_context(public):
    # Engineered public-only similarity: no heading, physical coordinate,
    # persistent object identity, inventory, answer oracle or hidden map.
    front=public["image"][3][5]
    kind=front[0]
    state=front[2] if kind==4 else -1
    return json.dumps([public["mission"],kind,state,int(source_target_visible(public))],
                      sort_keys=True,separators=(",",":"),ensure_ascii=True)

class PooledGoalCredit(OriginalDoorMemory):
    SCHEMA="mg54.original-source-public-coarse-mission-credit-v1"

    def __init__(self,steering_enabled=True):
        super().__init__(True)
        self.steering_enabled=steering_enabled
        self.pooled={}
        self.recent=[]
        self.pooled_opportunities=0
        self.pooled_overrides=0
        self.pooled_signal_events=0
        self.pooled_credit_assignments=0

    def begin_episode(self):
        super().begin_episode()
        self.recent=[]

    def choose(self,public):
        original=super().choose(public)
        if (not self.steering_enabled or self.phase!="seek"
            or original not in (0,1,2)
            or public_exact_target_front(public) is not None
            or self.pooled_signal_events<1):
            return original
        context=pooled_context(public)
        front=public["image"][3][5][0]
        options=(0,1,2) if front not in (2,4,5,6,7) else (0,1)
        def entry(a):
            return self.pooled.get(context+"|"+str(a),[0,0.0])
        supported=[a for a in options if entry(a)[0]>=2]
        if not supported:return original
        def value(a):
            n,credit=entry(a)
            return credit/(n+2)
        best=max(supported,key=lambda a:(value(a),a==original,-a))
        self.pooled_opportunities+=1
        if best!=original and value(best)>=value(original)+0.125:
            if self.pending!=(digest(public),original):
                raise ValueError("MG54_ORIGINAL_PARENT_SELECTION_NOT_SOURCE_CONFIRMED")
            self.pending=(digest(public),best)
            self.pooled_overrides+=1
            return best
        return original

    def observe_selected(self,before,action,after,reward,terminated):
        if self.pending!=(digest(before),action):
            raise ValueError("MG54_NOT_OWN_SELECTED_ORIGINAL_WORLD_ACTION")
        key=pooled_context(before)+"|"+str(action)
        if key in self.pooled or len(self.pooled)<2048:
            c=self.pooled.setdefault(key,[0,0.0])
            c[0]+=1
            self.recent.append(key)
        else:
            self.recent.append("")
        self.recent=self.recent[-8:]
        effect=original_goal_signal(before,action,after,reward,terminated)
        if effect:
            self.pooled_signal_events+=1
            for depth,key in enumerate(reversed(self.recent)):
                if key and key in self.pooled:
                    self.pooled[key][1]+=effect*(0.5**depth)
                    self.pooled_credit_assignments+=1
        super().observe_selected(before,action,after,reward,terminated)

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG54_PENDING_UNEXECUTED_SOURCE_SELECTION")
        parent=json.loads(OriginalDoorMemory.checkpoint(self))
        parent["schema"]=OriginalDoorMemory.SCHEMA
        parent["base"]["schema"]=PublicSlotRelease.SCHEMA
        return json.dumps({
            "schema":self.SCHEMA,"parent":parent,
            "steering_enabled":self.steering_enabled,
            "pooled":self.pooled,"recent":self.recent,
            "pooled_opportunities":self.pooled_opportunities,
            "pooled_overrides":self.pooled_overrides,
            "pooled_signal_events":self.pooled_signal_events,
            "pooled_credit_assignments":self.pooled_credit_assignments},
            sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8")

    @classmethod
    def restore(cls,raw):
        x=json.loads(raw)
        expected={"schema","parent","steering_enabled","pooled","recent",
            "pooled_opportunities","pooled_overrides",
            "pooled_signal_events","pooled_credit_assignments"}
        if (set(x)!=expected or x["schema"]!=cls.SCHEMA
            or type(x["steering_enabled"]) is not bool
            or type(x["pooled"]) is not dict or len(x["pooled"])>2048
            or type(x["recent"]) is not list or len(x["recent"])>8
            or any(type(k) is not str for k in x["recent"])
            or any(type(z) is not list or len(z)!=2
                   or type(z[0]) is not int or z[0]<1
                   or type(z[1]) not in (float,int)
                   or z[1]<0 or not math.isfinite(z[1])
                   for z in x["pooled"].values())
            or any(type(x[k]) is not int or x[k]<0
                   for k in ("pooled_opportunities","pooled_overrides",
                             "pooled_signal_events","pooled_credit_assignments"))
            or x["pooled_overrides"]>x["pooled_opportunities"]):
            raise ValueError("MG54_SOURCE_ORIGINAL_POOLED_COLD_MEMORY_INVALID")
        parent=OriginalDoorMemory.restore(json.dumps(x["parent"],
            sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8"))
        actor=cls(x["steering_enabled"])
        actor.__dict__.update(parent.__dict__)
        for k in ("pooled","recent","pooled_opportunities","pooled_overrides",
                  "pooled_signal_events","pooled_credit_assignments"):
            setattr(actor,k,x[k])
        actor.steering_enabled=x["steering_enabled"]
        if actor.checkpoint()!=raw:
            raise ValueError("MG54_SOURCE_COLD_POOLED_MEMORY_NOT_IDENTICAL")
        return actor

def preflight():
    p=frozen()
    original_mg52_preflight()
    observed={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
              "direction":0,"mission":"pick up the red box"}
    next_view=json.loads(json.dumps(observed))
    next_view["image"][3][4]=[7,0,0]
    if original_goal_signal(observed,0,next_view,0.0,False)!=2:
        raise ValueError("MG54_UNCHANGED_ORIGINAL_MG54_GOAL_EVENT_DETECTOR_DRIFT")
    if pooled_context(observed)!=pooled_context(
          {**observed,"direction":1}):
        raise ValueError("MG54_SOURCE_PUBLIC_HEADING_POOLING_NOT_AS_FROZEN")
    for enabled in (True,False):
        actor=PooledGoalCredit(enabled)
        before=actor.choose(observed)
        actor.observe_selected(observed,before,next_view,0.0,False)
        if (actor.pooled_signal_events!=1 or actor.pooled_credit_assignments!=1
            or sum(v[1] for v in actor.pooled.values())!=2):
            raise ValueError("MG54_ORIGINAL_GOAL_EVENT_NOT_ASSIGNED_TO_OWN_SELECTION")
        saved=actor.checkpoint()
        if PooledGoalCredit.restore(saved).checkpoint()!=saved:
            raise ValueError("MG54_ORIGINAL_PUBLIC_POOLED_COLD_ACTOR_NOT_RESTORED")
        actor.begin_episode()
        if (actor.recent or actor.pooled_signal_events!=1
            or not actor.pooled):
            raise ValueError("MG54_OWN_SELECTED_ACROSS_EPISODE_MEMORY_NOT_RETAINED")
        actor.pending=None
    print("MG54_CROSS_OS_PUBLIC_POOLED_GOAL_CREDIT_AND_ABLATION_SOURCE_ONLY_PASS")
    return p

def pooled_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if (gym.spec(family).entry_point!=entry
            or getattr(env.action_space,"n",None)!=7):
            raise ValueError("MG54_NOT_AUTHENTIC_ORIGINAL_FARAMA_SOURCE")
        raw,_=env.reset(seed=seed)
        first=public(raw);mission=first["mission"]
        actor=PooledGoalCredit(enabled) if prior is None else PooledGoalCredit.restore(prior)
        if actor.steering_enabled is not enabled:
            raise ValueError("MG54_SOURCE_ORIGINAL_ABLATION_NOT_IDENTICAL")
        actor.begin_episode()
        n0=actor.total
        o0=actor.pooled_overrides
        v0=actor.pooled_opportunities
        t0=actor.pooled_signal_events
        c0=actor.pooled_credit_assignments
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG54_ORIGINAL_SOURCE_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG54_AUTHENTIC_SOURCE_FEEDBACK_INVALID")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({
                "index":n,"before":before,"after":after,"action":action,
                "mission":mission,"reward":float(reward),"terminated":term,
                "truncated":trunc,"before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG54_OWN_SELECTED_POOLED_GOAL_ON" if enabled
                                else "MG54_OWN_SELECTED_POOLED_GOAL_OFF"})
            raw=raw2
            if term or trunc:break
        ck=actor.checkpoint()
        if (PooledGoalCredit.restore(ck).checkpoint()!=ck
            or actor.total!=n0+len(events)):
            raise ValueError("MG54_UNCHANGED_ORIGINAL_WORLD_COLD_CHECKPOINT_FAILED")
        return ({"family":family,"role":ROLES[21] if enabled else ROLES[22],
            "seed_dev_exposed":seed,"public_start_sha256":original_digest(first),
            "original_public_mission":mission,
            "original_source_actions":len(events),
            "prior_selected_source_samples":n0,
            "selected_source_samples_after":actor.total,
            "original_terminal_goal_rewards":
                sum(int(e["reward"]>0 and e["terminated"]) for e in events),
            "observed_public_changes":
                sum(e["before_sha256"]!=e["after_sha256"] for e in events),
            "unique_public_views":len({e["before_sha256"] for e in events}),
            "distinct_actions":len({e["action"] for e in events}),
            "checkpoint_sha256":hashlib.sha256(ck).hexdigest(),
            "source_events_sha256":original_digest(events),
            "source_pooled_goal_overrides":actor.pooled_overrides-o0,
            "source_pooled_goal_opportunities":actor.pooled_opportunities-v0,
            "source_pooled_goal_events":actor.pooled_signal_events-t0,
            "source_pooled_credit_assignments":actor.pooled_credit_assignments-c0,
            "source_pooled_context_action_count":len(actor.pooled),
            "source_events":events},ck)
    finally:env.close()

def metrics(rows):
    result={}
    for family in FAMILIES:
        result[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG54_SOURCE_ROLE_NOT_3_NEW_TRANSFER_EPISODES")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG54_WITHIN_FAMILY_SOURCE_MEMORY_NOT_RETAINED")
            counts=collections.Counter()
            hist=[0]*7
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG54_ORIGINAL_EPISODE_EVENT_HASH_FAILED")
                for i,e in enumerate(ep["source_events"],1):
                    if (e["index"]!=i or e["external_actions"]!=0
                        or digest(e["before"])!=e["before_sha256"]
                        or digest(e["after"])!=e["after_sha256"]):
                        raise ValueError("MG54_ORIGINAL_SOURCE_EVENT_NOT_AUTHENTIC")
                    v=event_metric(e)
                    counts.update(v)
                    hist[e["action"]]+=1
            if sum(hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG54_SELECTED_ACTION_COUNT_MISMATCH")
            result[family][role]={
                "episodes":3,
                "actions":sum(hist),
                "action_histogram":hist,
                "positive_goal_episodes":sum(
                    int(x["original_terminal_goal_rewards"]>0) for x in group),
                "target_visible_frames":counts["target_any_visible_frames"],
                "target_front_frames":counts["target_front_frames"],
                "selected_target_pickup_attempts":counts["target_front_selected_pickup_attempts"],
                "actual_selected_target_pickup_effects":counts["target_front_selected_effects"],
                "real_door_openings":counts["locked_door_openings"],
                "release_public_triggers":sum(
                    x.get("release_triggers",0) for x in group),
                "release_public_effects":sum(
                    x.get("release_actual_public_effects",0) for x in group)}
    return result

def run_original(source_root,native_go,control_root,p):
    import gymnasium as gym
    import minigrid
    import resource
    from mg17_original_family_source_qual import (
        frozen as original_frozen,attest_source,public,digest as original_digest)
    from mg21_original_development import one_episode,ROLES as native_roles
    preflight()
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG54_NOT_PINNED_FARAMA_IMPORT")
    orig=original_frozen()
    attest_source(source_root,orig)
    if subprocess.run(["git","-C",str(source_root),"hash-object",
                       "minigrid/__init__.py"],capture_output=True,text=True,
                       check=True).stdout.strip()!=REGISTER_BLOB:
        raise ValueError("MG54_ORIGINAL_REGISTRATION_SOURCE_CHANGED")
    entrypoints={}
    for name,expected in zip(FAMILIES,ENTRIES):
        spec=gym.spec(name)
        if spec.entry_point!=expected:
            raise ValueError("MG54_NEW_FAMILY_REGISTRY_NOT_ORIGINAL_SOURCE:"+name)
        # No reset/step until all source/registries verified.
        entrypoints[name]=expected
    exact_control=corrected_class(control_root)
    rows=[]
    costs=[]
    for family,seeds in zip(FAMILIES,SEEDS):
        memory={role:None for role in ROLES}
        for seed in seeds:
            start_hashes=[]
            for role in ROLES:
                wall0=time.perf_counter()
                cpu0=time.process_time()
                child0=resource.getrusage(resource.RUSAGE_CHILDREN)
                if role in (ROLES[0],ROLES[1],ROLES[-1]):
                    native=(native_roles[0] if role==ROLES[0] else
                            native_roles[1] if role==ROLES[1] else native_roles[3])
                    ep,_,state=one_episode(
                        family,seed,native,192,memory[role],
                        native_go,entrypoints[family])
                elif role==ROLES[2]:
                    ep,state=mg33_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role==ROLES[3]:
                    ep,state=mg34_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role in (ROLES[4],ROLES[5]):
                    mode="ucb" if role==ROLES[4] else "round_robin"
                    ep,state=control_episode(
                        gym,entrypoints[family],family,seed,mode,memory[role],
                        192,public,original_digest,exact_control)
                elif role==ROLES[6]:
                    ep,state=original_mg38_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role==ROLES[7]:
                    ep,state=ablated_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role in (ROLES[8],ROLES[9]):
                    ep,state=evidence_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[8])
                elif role==ROLES[10]:
                    ep,state=reversal_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role in (ROLES[11],ROLES[12]):
                    ep,state=action_value_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[11])
                elif role in (ROLES[13],ROLES[14]):
                    ep,state=public_release_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[13])
                elif role in (ROLES[15],ROLES[16]):
                    ep,state=original_door_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[15])
                elif role in (ROLES[17],ROLES[18]):
                    ep,state=original_mg50_episode(
                        gym,entrypoints[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[17])
                elif role in (ROLES[19],ROLES[20]):
                    ep,state=original_mg52_episode(
                        gym,entrypoints[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[19])
                elif role in (ROLES[21],ROLES[22]):
                    ep,state=pooled_episode(
                        gym,entrypoints[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[21])
                else:
                    raise ValueError("MG54_UNKNOWN_FROZEN_ORIGINAL_SOURCE_ACTOR")
                child1=resource.getrusage(resource.RUSAGE_CHILDREN)
                costs.append({"family":family,"role":role,"seed":seed,
                    "source_selected_actions":ep["original_source_actions"],
                    "outer_wall_seconds":round(time.perf_counter()-wall0,6),
                    "python_process_cpu_seconds":round(time.process_time()-cpu0,6),
                    "children_cpu_seconds_estimate":round(
                        child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime,6),
                    "note":"Linux outer process plus child deltas, not full per-native parity"})
                ep["role"]=role
                start_hashes.append(ep["public_start_sha256"])
                if role!=ROLES[-1]:
                    memory[role]=state
                rows.append(ep)
            if len(set(start_hashes))!=1:
                raise ValueError("MG54_SOURCE_RESET_SEED_NOT_EQUAL_ACROSS_ROLES")
    if len(rows)!=216 or any(not 1<=x["original_source_actions"]<=192 for x in rows):
        raise ValueError("MG54_NEW_FAMILY_ORIGINAL_SOURCE_EPISODES_MISSING")
    table=metrics(rows)
    candidate=ROLES[21]
    controls=(ROLES[22],ROLES[19],ROLES[20],ROLES[15],
              ROLES[13],ROLES[17],ROLES[18],ROLES[3])
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in FAMILIES)
           for role in (candidate,*controls)}
    corridor_visible=any(table[f][candidate]["target_visible_frames"]>0
                         for f in FAMILIES[:2])
    corridor_positive=any(table[f][candidate]["positive_goal_episodes"]>0
                          for f in FAMILIES[:2])
    maze_positive=table[FAMILIES[-1]][candidate]["positive_goal_episodes"]>0
    target_effects=sum(table[f][candidate]["actual_selected_target_pickup_effects"]
                       for f in FAMILIES)
    genuine_overrides=sum(ep.get("source_pooled_goal_overrides",0)
                         for ep in rows if ep["role"]==candidate)
    source_goal_events=sum(ep.get("source_pooled_goal_events",0)
                          for ep in rows if ep["role"]==candidate)
    passed=(genuine_overrides>=1 and corridor_visible and corridor_positive
            and maze_positive and all(goals[candidate]>goals[r] for r in controls))
    outcome=p["frozen_dev_filter"]["pass"] if passed else p["frozen_dev_filter"]["fail"]
    source={
        "schema":"itd02.mg54.original-source-public-pooled-goal-eligibility.dev.v1",
        "classification":outcome,
        "family_source_registration_blob_sha1":REGISTER_BLOB,
        "unchanged_mg44_source_blob_sha1":POLICY_BLOB,
        "original_216_episodes":rows,
        "original_selected_action_count":sum(x["original_source_actions"] for x in rows),
        "per_family_per_role":table,
        "pooled_goal_credit_filter":{
            "candidate":candidate,"goals":goals,
            "corridor_exact_target_visible":corridor_visible,
            "corridor_original_positive_goal":corridor_positive,
            "obstructedmaze_original_positive_goal":maze_positive,
            "candidate_actual_mission_target_effects":target_effects,
            "candidate_source_pooled_credit_overrides":genuine_overrides,
            "candidate_original_goal_relevance_events":source_goal_events,
            "supported":passed},
        "exposed_transfer_DEV_seeds":[list(x) for x in SEEDS],
        "source_original_Farama":UPSTREAM,
        "scientific_first_use":False,
        "independent_sealed_scientific_witness":False,
        "zero_external_actions":True,
        "native_models_or_controllers_modified":False,
        "native_full_compute_energy_parity_qualified":False,
        "mg28_native_rollout_permitted":False}
    receipt={"schema":source["schema"],"source":source,
             "canonical_source_sha256":digest(source)}
    resources={"schema":"itd02.mg54.auxiliary-host-episode-resources.v1",
               "note":"Host wall+Python process/child CPU deltas, no native CPU/RSS/energy parity claim",
               "original_source_sha256":receipt["canonical_source_sha256"],
               "records":costs}
    return receipt,resources

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--native-go",type=Path)
    ap.add_argument("--control-root",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--resources",type=Path)
    ap.add_argument("--compare",nargs=2,type=Path)
    a=ap.parse_args()
    p=frozen()
    if a.preflight:
        preflight()
        return
    if a.compare:
        first,second=[json.loads(x.read_text(encoding="utf8")) for x in a.compare]
        if (first.get("source")!=second.get("source")
            or first.get("canonical_source_sha256")!=second.get("canonical_source_sha256")
            or first.get("canonical_source_sha256")!=digest(first["source"])
            or first["source"].get("classification") not in
                 (p["frozen_dev_filter"]["pass"],p["frozen_dev_filter"]["fail"])
            or len(first["source"]["original_216_episodes"])!=216
            or first["source"]["scientific_first_use"] is not False
            or first["source"]["zero_external_actions"] is not True):
            raise ValueError("MG54_INDEPENDENT_ORIGINAL_PROCESSES_DIVERGED")
        print("MG54_TWO_AUTHENTIC_ORIGINAL_DOOR_MEMORY_PROCESSES_IDENTICAL",
              first["canonical_source_sha256"])
        print("MG54_FROZEN_DEVELOPMENT_CLASSIFICATION",
              first["source"]["classification"])
        print("MG54_ORIGINAL_PER_FAMILY_GOALS",json.dumps(
              {k:{role:z["positive_goal_episodes"] for role,z in v.items()
                  if role in (ROLES[0],ROLES[1],ROLES[13],ROLES[14])}
               for k,v in first["source"]["per_family_per_role"].items()},sort_keys=True))
        print("MG54_DOOR_MEMORY_FILTER",json.dumps(
              first["source"]["pooled_goal_credit_filter"],sort_keys=True))
        return
    if any(x is None for x in (a.source_root,a.native_go,a.control_root,
                               a.output,a.resources)):
        ap.error("--source-root --native-go --control-root --output --resources required")
    started=time.perf_counter()
    try:
        receipt,resources=run_original(
            a.source_root,a.native_go,a.control_root,p)
    except Exception as e:
        receipt={"schema":"itd02.mg47.door-memory-original-source-blocked.v1",
                 "classification":p["frozen_dev_filter"]["source_block"],
                 "error_type":type(e).__name__,"error":str(e),
                 "trace_tail":traceback.format_exc().splitlines()[-16:]}
        resources={"schema":"itd02.mg47.resources-blocked.v1","records":[]}
    receipt["host_wall_seconds_outside_canonical_source"]=round(
        time.perf_counter()-started,6)
    a.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",
                        encoding="utf8")
    a.resources.write_text(json.dumps(resources,indent=2,sort_keys=True)+"\n",
                           encoding="utf8")
    cls=receipt.get("source",{}).get("classification",
                                   receipt.get("classification","MG54_BLOCKED"))
    print("MG54_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(receipt.get("error","MG54_UNKNOWN_SOURCE_BLOCKER"))
    print("MG54_ORIGINAL_SOURCE_SHA256",receipt["canonical_source_sha256"])
if __name__=="__main__":
    main()

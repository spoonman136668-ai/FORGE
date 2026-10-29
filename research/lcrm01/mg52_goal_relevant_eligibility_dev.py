#!/usr/bin/env python3
"""MG45: unchanged MG44 original-source family transfer, never native promotion.

No candidate code copied, extended, tuned or monkeypatched. Public-domain
Farama original source and previously qualified source-selected actors only.
Fresh DEV transfer, NOT independently sealed heldout scientific acceptance.
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
from mg44_public_precondition_release import (
    PublicSlotRelease,public_release_episode,synthetic_source_preflight
    as original_mg44_preflight)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg52_goal_relevant_eligibility_prereg.json"
PARENT="a058d8f59555c2bac0121613dc14b5bd758ddf1f"
FREEZE="9d4833933165ef4204f2054a7e6e8bd0762880e8"
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
 "mg52_original_goal_relevant_eligibility_enabled",
 "mg52_original_goal_relevant_eligibility_disabled",
 "seeded_uniform_random")
SEEDS=((1081101,1081103,1081107),(1081201,1081203,1081207),
       (1081301,1081303,1081307))

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    c=p["cohort"];m=p["mechanism"];v=m["coefficients"]
    if (p["schema"]!="itd02.mg52.original-source-public-goal-effect-eligibility-memory.dev.v1"
        or p["phase"]!="PROSPECTIVE_PROTOCOL_FROZEN_BEFORE_EXECUTABLE_AND_ANY_NEW_ORIGINAL_WORLD_ACTION"
        or p["parent"]["mg51_head"]!=PARENT or p["source"]["original_farama"]!=UPSTREAM
        or p["source"]["farama_registry_blob"]!=REGISTER_BLOB
        or tuple((f["id"],f["entry"]) for f in c["families"])!=tuple(zip(FAMILIES,ENTRIES))
        or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["fresh_dev_seeds"]))!=SEEDS
        or c["episodes"]!=198 or c["original_actions_cap_each"]!=192
        or c["independent_full_source_processes"]!=2
        or v!={"trace_window":8,"discount_ratio":"1/2",
               "context_action_cap":2048,"minimum_context_action_samples":2,
               "minimum_mean_credit_advantage":"1/2",
               "credit_first_new_target_visible":2,
               "credit_true_locked_door_opening":3,
               "credit_selected_target_pickup_effect":6,
               "credit_positive_terminal_goal":10,
               "steering_actions":[0,1,2]}
        or not all(p["prohibitions"].values())):
        raise ValueError("MG52_FROZEN_PROSPECTIVE_PUBLIC_GOAL_VALUE_PROTOCOL_DRIFT")
    flat=[v for z in SEEDS for v in z]
    if len(flat)!=9 or len(set(flat))!=9:
        raise ValueError("MG52_ORIGINAL_DEV_SEEDS_NOT_DISJOINT")
    for revision in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",revision,"HEAD").returncode:
            raise ValueError("MG52_NO_EVIDENCE_OF_FREEZE_BEFORE_EXECUTABLE")
    for seed in flat:
        z=git("grep","-n","-w",str(seed),PARENT,"--",
              "research/lcrm01","docs/research")
        if z.returncode==0:raise ValueError("MG52_NEW_ORIGINAL_DEV_SEED_ALREADY_EXPOSED")
        if z.returncode!=1:raise ValueError("MG52_ORIGINAL_SEED_CUSTODY_SCAN_FAILED")
    blob=git("hash-object","research/lcrm01/mg44_public_precondition_release.py")
    if blob.returncode or blob.stdout.strip()!=POLICY_BLOB:
        raise ValueError("MG52_UNCHANGED_ORIGINAL_RELEASE_POLICY_NOT_SOURCE_IDENTICAL")
    return p

def target_visible(public):
    m=MISSION.fullmatch(public["mission"])
    if not m:return False
    col,obj=m.groups()
    return any(px[0]==TYPES[obj] and px[1]==COLORS[col]
               for row in public["image"] for px in row)

def compact_context(public):
    front=public["image"][3][5]
    mission=public["mission"]
    # Disclosed engineered public features, no source hidden state or x/y.
    return json.dumps([mission,front[0],front[1],front[2],
        public["direction"],int(target_visible(public))],
        separators=(",",":"),ensure_ascii=True)

def observed_goal_signal(before,action,after,reward,terminated):
    score=0
    if not target_visible(before) and target_visible(after):score+=2
    f=before["image"][3][5];a=after["image"][3][5]
    if (action==5 and f[0]==4 and f[2]==2 and a[0]==4
        and a[1]==f[1] and a[2]==0
        and before["direction"]==after["direction"]):
        score+=3
    if (action==3 and public_exact_target_front(before) is not None
        and a[0]==1 and before["direction"]==after["direction"]):
        score+=6
    if reward>0 and terminated:score+=10
    return score

class GoalRelevantEligibility(OriginalDoorMemory):
    SCHEMA="mg52.original-source-public-goal-effect-eligibility-v1"
    def __init__(self,eligibility_enabled=True):
        super().__init__(True)
        self.eligibility_enabled=eligibility_enabled
        self.memory={}
        self.recent=[]
        self.value_overrides=0
        self.value_opportunities=0
        self.source_goal_signals=0
        self.credit_assignments=0

    def begin_episode(self):
        super().begin_episode()
        self.recent=[]

    def choose(self,public):
        proposed=super().choose(public)
        if (not self.eligibility_enabled or self.phase!="seek"
            or proposed not in (0,1,2)
            or public_exact_target_front(public) is not None):
            return proposed
        context=compact_context(public)
        choices=(0,1,2) if public["image"][3][5][0] not in (2,4,5,6,7) else (0,1)
        def pair(a):
            return self.memory.get(context+"|"+str(a),[0,0.0])
        def value(a):
            n,credits=pair(a)
            return credits/(n+2)
        options=[a for a in choices if pair(a)[0]>=2]
        if not options:return proposed
        best=max(options,key=lambda a:(value(a),a==proposed,-a))
        self.value_opportunities+=1
        if best!=proposed and value(best)>=value(proposed)+0.5:
            if self.pending!=(digest(public),proposed):
                raise ValueError("MG52_ORIGINAL_SELECTED_PARENT_PENDING_MISSING")
            self.pending=(digest(public),best)
            self.value_overrides+=1
            return best
        return proposed

    def observe_selected(self,before,action,after,reward,terminated):
        if self.pending!=(digest(before),action):
            raise ValueError("MG52_NOT_OWN_SELECTED_FARAMA_FEEDBACK")
        key=compact_context(before)+"|"+str(action)
        if key in self.memory or len(self.memory)<2048:
            entry=self.memory.setdefault(key,[0,0.0])
            entry[0]+=1
            self.recent.append(key)
        else:
            self.recent.append("")
        self.recent=self.recent[-8:]
        score=observed_goal_signal(before,action,after,reward,terminated)
        if score:
            self.source_goal_signals+=1
            for depth,past in enumerate(reversed(self.recent)):
                if past and past in self.memory:
                    self.memory[past][1]+=score*(0.5**depth)
                    self.credit_assignments+=1
        super().observe_selected(before,action,after,reward,terminated)

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG52_UNEXECUTED_SOURCE_SELECTION_CANNOT_CHECKPOINT")
        original=json.loads(OriginalDoorMemory.checkpoint(self))
        original["schema"]=OriginalDoorMemory.SCHEMA
        original["base"]["schema"]=PublicSlotRelease.SCHEMA
        return json.dumps({"schema":self.SCHEMA,"original":original,
          "eligibility_enabled":self.eligibility_enabled,
          "memory":self.memory,"recent":self.recent,
          "value_overrides":self.value_overrides,
          "value_opportunities":self.value_opportunities,
          "source_goal_signals":self.source_goal_signals,
          "credit_assignments":self.credit_assignments},
          sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8")

    @classmethod
    def restore(cls,raw):
        q=json.loads(raw)
        required={"schema","original","eligibility_enabled","memory",
                  "recent","value_overrides","value_opportunities",
                  "source_goal_signals","credit_assignments"}
        if (set(q)!=required or q["schema"]!=cls.SCHEMA
            or type(q["eligibility_enabled"]) is not bool
            or type(q["memory"]) is not dict or len(q["memory"])>2048
            or type(q["recent"]) is not list or len(q["recent"])>8
            or any(type(k) is not str for k in q["recent"])
            or any(type(value) is not list or len(value)!=2
                   or type(value[0]) is not int or value[0]<1
                   or type(value[1]) not in (float,int)
                   or not math.isfinite(value[1]) or value[1]<0
                   for value in q["memory"].values())
            or any(type(q[k]) is not int or q[k]<0 for k in
                   ("value_overrides","value_opportunities",
                    "source_goal_signals","credit_assignments"))
            or q["value_overrides"]>q["value_opportunities"]):
            raise ValueError("MG52_ORIGINAL_GOAL_MEMORY_COLD_STATE_INVALID")
        original=OriginalDoorMemory.restore(json.dumps(
            q["original"],sort_keys=True,separators=(",",":"),
            ensure_ascii=True).encode("utf8"))
        out=cls(q["eligibility_enabled"])
        out.__dict__.update(original.__dict__)
        for k in ("memory","recent","value_overrides","value_opportunities",
                  "source_goal_signals","credit_assignments"):
            setattr(out,k,q[k])
        out.eligibility_enabled=q["eligibility_enabled"]
        if out.checkpoint()!=raw:
            raise ValueError("MG52_ORIGINAL_GOAL_MEMORY_COLD_STATE_NOT_IDENTICAL")
        return out

def preflight():
    p=frozen()
    original_door_preflight()
    observed={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
              "direction":0,"mission":"pick up the red box"}
    next_observation=json.loads(json.dumps(observed))
    next_observation["image"][3][4]=[7,0,0]
    if observed_goal_signal(observed,0,next_observation,0.0,False)!=2:
        raise ValueError("MG52_SOURCE_ONLY_PUBLIC_TARGET_OBSERVATION_CREDIT_FAIL")
    for enabled in (True,False):
        actor=GoalRelevantEligibility(enabled)
        selected=actor.choose(observed)
        actor.observe_selected(observed,selected,next_observation,0.0,False)
        if (actor.source_goal_signals!=1 or actor.credit_assignments!=1
            or sum(v[0] for v in actor.memory.values())!=1
            or sum(v[1] for v in actor.memory.values())!=2):
            raise ValueError("MG52_OWN_SELECTED_GOAL_RELEVANCE_CREDIT_NOT_RETAINED")
        state=actor.checkpoint()
        if GoalRelevantEligibility.restore(state).checkpoint()!=state:
            raise ValueError("MG52_COLD_SELECTED_SOURCE_GOAL_CREDIT_DIVERGED")
        actor.begin_episode()
        if actor.recent or actor.source_goal_signals!=1 or not actor.memory:
            raise ValueError("MG52_INDEPENDENT_EPISODE_MEMORY_RESET_INCORRECT")
        action=actor.choose(observed)
        if action not in range(7):
            raise ValueError("MG52_UNQUALIFIED_SELECTED_ACTION")
        actor.pending=None
    print("MG52_CROSS_OS_GOAL_RELEVANT_CREDIT_ON_OFF_COLD_SOURCE_PREFLIGHT_PASS")
    return p

def goal_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG52_NOT_PINNED_FARAMA_ORIGINAL_WORLD")
        raw,_=env.reset(seed=seed)
        first=public(raw);mission=first["mission"]
        actor=GoalRelevantEligibility(enabled) if prior is None else GoalRelevantEligibility.restore(prior)
        if actor.eligibility_enabled is not enabled:
            raise ValueError("MG52_SOURCE_ELIGIBILITY_ARM_CHANGED")
        actor.begin_episode()
        n0=actor.total;o0=actor.value_overrides
        q0=actor.value_opportunities;c0=actor.source_goal_signals
        a0=actor.credit_assignments
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:raise ValueError("MG52_ORIGINAL_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG52_ORIGINAL_SOURCE_FEEDBACK_INVALID")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG52_GOAL_ELIGIBILITY_ON" if enabled
                                else "MG52_GOAL_ELIGIBILITY_OFF"})
            raw=raw2
            if term or trunc:break
        state=actor.checkpoint()
        if (GoalRelevantEligibility.restore(state).checkpoint()!=state
            or actor.total!=n0+len(events)):
            raise ValueError("MG52_ORIGINAL_GOAL_ELIGIBILITY_SOURCE_COLD_RESTORE_FAIL")
        return ({"family":family,
          "role":ROLES[19] if enabled else ROLES[20],
          "seed_dev_exposed":seed,
          "public_start_sha256":original_digest(first),
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
          "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
          "source_events_sha256":original_digest(events),
          "source_goal_eligibility_overrides":actor.value_overrides-o0,
          "source_goal_value_opportunities":actor.value_opportunities-q0,
          "source_goal_relevance_events":actor.source_goal_signals-c0,
          "source_goal_credit_assignments":actor.credit_assignments-a0,
          "source_context_action_values":len(actor.memory),
          "source_events":events},state)
    finally:env.close()

def metrics(rows):
    result={}
    for family in FAMILIES:
        result[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG52_SOURCE_ROLE_NOT_3_NEW_TRANSFER_EPISODES")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG52_WITHIN_FAMILY_SOURCE_MEMORY_NOT_RETAINED")
            counts=collections.Counter()
            hist=[0]*7
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG52_ORIGINAL_EPISODE_EVENT_HASH_FAILED")
                for i,e in enumerate(ep["source_events"],1):
                    if (e["index"]!=i or e["external_actions"]!=0
                        or digest(e["before"])!=e["before_sha256"]
                        or digest(e["after"])!=e["after_sha256"]):
                        raise ValueError("MG52_ORIGINAL_SOURCE_EVENT_NOT_AUTHENTIC")
                    v=event_metric(e)
                    counts.update(v)
                    hist[e["action"]]+=1
            if sum(hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG52_SELECTED_ACTION_COUNT_MISMATCH")
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
        raise ValueError("MG52_NOT_PINNED_FARAMA_IMPORT")
    orig=original_frozen()
    attest_source(source_root,orig)
    if subprocess.run(["git","-C",str(source_root),"hash-object",
                       "minigrid/__init__.py"],capture_output=True,text=True,
                       check=True).stdout.strip()!=REGISTER_BLOB:
        raise ValueError("MG52_ORIGINAL_REGISTRATION_SOURCE_CHANGED")
    entrypoints={}
    for name,expected in zip(FAMILIES,ENTRIES):
        spec=gym.spec(name)
        if spec.entry_point!=expected:
            raise ValueError("MG52_NEW_FAMILY_REGISTRY_NOT_ORIGINAL_SOURCE:"+name)
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
                    ep,state=goal_episode(
                        gym,entrypoints[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[19])
                else:
                    raise ValueError("MG52_UNKNOWN_FROZEN_ORIGINAL_SOURCE_ACTOR")
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
                raise ValueError("MG52_SOURCE_RESET_SEED_NOT_EQUAL_ACROSS_ROLES")
    if len(rows)!=198 or any(not 1<=x["original_source_actions"]<=192 for x in rows):
        raise ValueError("MG52_NEW_FAMILY_ORIGINAL_SOURCE_EPISODES_MISSING")
    table=metrics(rows)
    candidate=ROLES[19]
    controls=(ROLES[20],ROLES[15],ROLES[13],ROLES[17],ROLES[18],ROLES[3])
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in FAMILIES)
           for role in (candidate,*controls)}
    corridor_visible=any(table[f][candidate]["target_visible_frames"]>0
                         for f in FAMILIES[:2])
    corridor_positive=any(table[f][candidate]["positive_goal_episodes"]>0
                          for f in FAMILIES[:2])
    maze_positive=table[FAMILIES[-1]][candidate]["positive_goal_episodes"]>0
    target_effects=sum(table[f][candidate]["actual_selected_target_pickup_effects"]
                       for f in FAMILIES)
    genuine_overrides=sum(ep.get("source_goal_eligibility_overrides",0)
                         for ep in rows if ep["role"]==candidate)
    source_relevance_events=sum(ep.get("source_goal_relevance_events",0)
                               for ep in rows if ep["role"]==candidate)
    passed=(genuine_overrides>=1 and corridor_visible and corridor_positive
            and maze_positive and all(goals[candidate]>goals[r] for r in controls))
    outcome=p["frozen_dev_filter"]["pass"] if passed else p["frozen_dev_filter"]["fail"]
    source={
        "schema":"itd02.mg52.original-source-goal-consequence-eligibility.dev.v1",
        "classification":outcome,
        "family_source_registration_blob_sha1":REGISTER_BLOB,
        "unchanged_mg44_source_blob_sha1":POLICY_BLOB,
        "original_198_episodes":rows,
        "original_selected_action_count":sum(x["original_source_actions"] for x in rows),
        "per_family_per_role":table,
        "goal_relevant_eligibility_filter":{
            "candidate":candidate,"goals":goals,
            "corridor_exact_target_visible":corridor_visible,
            "corridor_original_positive_goal":corridor_positive,
            "obstructedmaze_original_positive_goal":maze_positive,
            "candidate_actual_mission_target_effects":target_effects,
            "candidate_source_goal_eligibility_overrides":genuine_overrides,
            "candidate_original_goal_relevance_events":source_relevance_events,
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
    resources={"schema":"itd02.mg52.auxiliary-host-episode-resources.v1",
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
            or len(first["source"]["original_198_episodes"])!=198
            or first["source"]["scientific_first_use"] is not False
            or first["source"]["zero_external_actions"] is not True):
            raise ValueError("MG52_INDEPENDENT_ORIGINAL_PROCESSES_DIVERGED")
        print("MG52_TWO_AUTHENTIC_ORIGINAL_DOOR_MEMORY_PROCESSES_IDENTICAL",
              first["canonical_source_sha256"])
        print("MG52_FROZEN_DEVELOPMENT_CLASSIFICATION",
              first["source"]["classification"])
        print("MG52_ORIGINAL_PER_FAMILY_GOALS",json.dumps(
              {k:{role:z["positive_goal_episodes"] for role,z in v.items()
                  if role in (ROLES[0],ROLES[1],ROLES[13],ROLES[14])}
               for k,v in first["source"]["per_family_per_role"].items()},sort_keys=True))
        print("MG52_DOOR_MEMORY_FILTER",json.dumps(
              first["source"]["goal_relevant_eligibility_filter"],sort_keys=True))
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
                                   receipt.get("classification","MG52_BLOCKED"))
    print("MG52_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(receipt.get("error","MG52_UNKNOWN_SOURCE_BLOCKER"))
    print("MG52_ORIGINAL_SOURCE_SHA256",receipt["canonical_source_sha256"])
if __name__=="__main__":
    main()

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
from mg44_public_precondition_release import (
    PublicSlotRelease,public_release_episode,synthetic_source_preflight
    as original_mg44_preflight)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg50_public_predictive_transition_prereg.json"
PARENT="7bc5310a9a6116d1009d5f45ce65d12699c2ea86"
FREEZE="44f6cb211aea829297c86bd58166f9c6a28f855f"
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
 "mg50_empirical_public_transition_uncertainty_enabled",
 "mg50_empirical_public_transition_uncertainty_disabled",
 "seeded_uniform_random")
SEEDS=((1071101,1071103,1071107),(1071201,1071203,1071207),
       (1071301,1071303,1071307))

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    c=p["cohort"];m=p["mechanism"];x=m["coefficients"]
    if (p["schema"]!="itd02.mg50.original-public-selected-predictive-transition-uncertainty.dev.v1"
        or p["phase"]!="PROSPECTIVE_FROZEN_BEFORE_MG50_EXECUTABLE_AND_ALL_NEW_FARAMA_ACTIONS"
        or p["parent"]["mg49_head"]!=PARENT
        or p["source"]["farama"]!=UPSTREAM
        or p["source"]["registration_blob_sha1"]!=REGISTER_BLOB
        or tuple((q["id"],q["entry"]) for q in c["families"])!=tuple(zip(FAMILIES,ENTRIES))
        or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["fresh_dev_seeds"]))!=SEEDS
        or c["expected_episodes"]!=180 or c["cap"]!=192
        or c["independent_full_source_processes"]!=2
        or x!={"min_prior_same_context_transitions":2,
                "minimum_improvement_fraction":"1/4",
                "laplace_pseudocount_success":1,"laplace_pseudocount_total":2,
                "learned_context_action_cap":2048,"steering_actions":[0,1,2]}
        or not all(p["prohibitions"].values())):
        raise ValueError("MG50_FROZEN_ORIGINAL_SOURCE_PREDICTIVE_PROTOCOL_DRIFT")
    seeds=[v for x in SEEDS for v in x]
    if len(seeds)!=9 or len(set(seeds))!=9:
        raise ValueError("MG50_DUPLICATE_SOURCE_DEV_COHORT")
    for commit in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",commit,"HEAD").returncode:
            raise ValueError("MG50_PROTOCOL_FREEZE_NOT_ANCESTOR")
    for seed in seeds:
        q=git("grep","-n","-w",str(seed),PARENT,"--","research/lcrm01","docs/research")
        if q.returncode==0:raise ValueError("MG50_PRIOR_DEV_SEED_EXPOSURE")
        if q.returncode!=1:raise ValueError("MG50_PRIOR_SOURCE_CUSTODY_UNAVAILABLE")
    policy=git("hash-object","research/lcrm01/mg44_public_precondition_release.py")
    if policy.returncode or policy.stdout.strip()!=POLICY_BLOB:
        raise ValueError("MG50_ORIGINAL_MG44_UNCHANGED_POLICY_DRIFT")
    return p

class PublicTransitionPredictor(OriginalDoorMemory):
    SCHEMA="mg50.original-public-selected-transition-change-predictor.v1"

    def __init__(self,prediction_enabled=True):
        super().__init__(True)
        self.prediction_enabled=prediction_enabled
        self.trials={}
        self.prediction_overrides=0
        self.prediction_opportunities=0
        self.learned_contexts=0

    def choose(self,public):
        original=super().choose(public)
        if (not self.prediction_enabled or self.phase!="seek"
            or public_exact_target_front(public) is not None
            or original not in (0,1,2)):
            return original
        context=digest(public)
        trials={a:self.trials.get(context+":"+str(a),[0,0])
                for a in (0,1,2)}
        sampled=sum(v[0] for v in trials.values())
        if sampled<2:
            return original
        front=public["image"][3][5]
        # This is engineered policy prior based on the public source cell,
        # not a learned proof of motion or physical traversability.
        available=(0,1,2) if front[0] not in (2,4,5,6,7) else (0,1)
        def estimate(a):
            n,changed=trials[a]
            return (changed+1)/(n+2)
        best=max(available,key=lambda a:(estimate(a),a==original,-a))
        self.prediction_opportunities+=1
        if (best!=original and estimate(best)>estimate(original)+0.25):
            if self.pending!=(context,original):
                raise ValueError("MG50_INVALID_PARENT_SELECTED_ACTION")
            self.pending=(context,best)
            self.prediction_overrides+=1
            return best
        return original

    def observe_selected(self,before,action,after,reward,terminated):
        if self.pending!=(digest(before),action):
            raise ValueError("MG50_NOT_OWN_SELECTED_SOURCE_ACTION")
        key=digest(before)+":"+str(action)
        if key in self.trials or len(self.trials)<2048:
            c=self.trials.setdefault(key,[0,0])
            c[0]+=1
            c[1]+=int(digest(before)!=digest(after))
        super().observe_selected(before,action,after,reward,terminated)

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG50_UNEXECUTED_SOURCE_SELECTION")
        parent=json.loads(OriginalDoorMemory.checkpoint(self))
        parent["schema"]=OriginalDoorMemory.SCHEMA
        parent["base"]["schema"]=PublicSlotRelease.SCHEMA
        return json.dumps({"schema":self.SCHEMA,"parent":parent,
            "prediction_enabled":self.prediction_enabled,
            "trials":self.trials,
            "prediction_overrides":self.prediction_overrides,
            "prediction_opportunities":self.prediction_opportunities},
            sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8")

    @classmethod
    def restore(cls,raw):
        x=json.loads(raw)
        if (set(x)!={"schema","parent","prediction_enabled","trials",
                     "prediction_overrides","prediction_opportunities"}
            or x["schema"]!=cls.SCHEMA or type(x["prediction_enabled"]) is not bool
            or len(x["trials"])>2048
            or any(not isinstance(v,list) or len(v)!=2 or
                   any(type(n) is not int for n in v) or not 0<=v[1]<=v[0]
                   for v in x["trials"].values())
            or type(x["prediction_overrides"]) is not int
            or type(x["prediction_opportunities"]) is not int
            or not 0<=x["prediction_overrides"]<=x["prediction_opportunities"]):
            raise ValueError("MG50_COLD_SOURCE_PREDICTION_MODEL_INVALID")
        parent=OriginalDoorMemory.restore(json.dumps(
            x["parent"],sort_keys=True,separators=(",",":"),
            ensure_ascii=True).encode("utf8"))
        actor=cls(x["prediction_enabled"])
        actor.__dict__.update(parent.__dict__)
        actor.prediction_enabled=x["prediction_enabled"]
        actor.trials=x["trials"]
        actor.prediction_overrides=x["prediction_overrides"]
        actor.prediction_opportunities=x["prediction_opportunities"]
        if actor.checkpoint()!=raw:
            raise ValueError("MG50_ORIGINAL_SELECTED_COLD_MODEL_DIVERGED")
        return actor

def preflight():
    p=frozen()
    original_door_preflight()
    public={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
            "direction":0,"mission":"pick up the blue box"}
    next_observation=json.loads(json.dumps(public))
    next_observation["image"][3][4]=[5,0,0]
    for enable in (True,False):
        learner=PublicTransitionPredictor(enable)
        for i in range(2):
            chosen=learner.choose(public)
            learner.observe_selected(public,chosen,next_observation,0.0,False)
        if sum(x[0] for x in learner.trials.values())!=2:
            raise ValueError("MG50_OWN_SELECTED_CONTEXT_TRAINING_MISSING")
        raw=learner.checkpoint()
        if PublicTransitionPredictor.restore(raw).checkpoint()!=raw:
            raise ValueError("MG50_COLD_SOURCE_CONTEXT_MEMORY_NOT_PRESERVED")
        learner.begin_episode()
        if sum(x[0] for x in learner.trials.values())!=2:
            raise ValueError("MG50_SOURCE_FAMILY_PREDICTOR_NOT_RETAINED")
        action=learner.choose(public)
        if action not in range(7):
            raise ValueError("MG50_ACTION_OUT_OF_ORIGINAL_7_ACTION_SPACE")
        learner.pending=None
    print("MG50_SOURCE_ONLY_OWN_SELECTED_TRANSITION_VALUE_COLD_ABLATION_PASS")
    return p

def predictive_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG50_NOT_PINNED_ORIGINAL_FARAMA_WORLD")
        raw,_=env.reset(seed=seed);first=public(raw);mission=first["mission"]
        actor=PublicTransitionPredictor(enabled) if prior is None else PublicTransitionPredictor.restore(prior)
        if actor.prediction_enabled is not enabled:
            raise ValueError("MG50_FROZEN_ABLATION_ROLE_CHANGED")
        actor.begin_episode()
        n0=actor.total;o0=actor.prediction_overrides;q0=actor.prediction_opportunities
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:raise ValueError("MG50_PUBLIC_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action);after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG50_INVALID_ORIGINAL_SOURCE_SELECTED_FEEDBACK")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG50_SOURCE_PUBLIC_PREDICTIVE_ON" if enabled
                                else "MG50_SOURCE_PUBLIC_PREDICTIVE_OFF"})
            raw=raw2
            if term or trunc:break
        ck=actor.checkpoint()
        if (PublicTransitionPredictor.restore(ck).checkpoint()!=ck
            or actor.total!=n0+len(events)):
            raise ValueError("MG50_ORIGINAL_COLD_SELECTED_SOURCE_MODEL_MISSING")
        return ({"family":family,"role":ROLES[17] if enabled else ROLES[18],
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
            "checkpoint_sha256":hashlib.sha256(ck).hexdigest(),
            "source_events_sha256":original_digest(events),
            "source_prediction_overrides":actor.prediction_overrides-o0,
            "source_predictive_opportunities":actor.prediction_opportunities-q0,
            "source_predictive_contexts":len(actor.trials),
            "source_events":events},ck)
    finally:env.close()

def metrics(rows):
    result={}
    for family in FAMILIES:
        result[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG50_SOURCE_ROLE_NOT_3_NEW_TRANSFER_EPISODES")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG50_WITHIN_FAMILY_SOURCE_MEMORY_NOT_RETAINED")
            counts=collections.Counter()
            hist=[0]*7
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG50_ORIGINAL_EPISODE_EVENT_HASH_FAILED")
                for i,e in enumerate(ep["source_events"],1):
                    if (e["index"]!=i or e["external_actions"]!=0
                        or digest(e["before"])!=e["before_sha256"]
                        or digest(e["after"])!=e["after_sha256"]):
                        raise ValueError("MG50_ORIGINAL_SOURCE_EVENT_NOT_AUTHENTIC")
                    v=event_metric(e)
                    counts.update(v)
                    hist[e["action"]]+=1
            if sum(hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG50_SELECTED_ACTION_COUNT_MISMATCH")
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
        raise ValueError("MG50_NOT_PINNED_FARAMA_IMPORT")
    orig=original_frozen()
    attest_source(source_root,orig)
    if subprocess.run(["git","-C",str(source_root),"hash-object",
                       "minigrid/__init__.py"],capture_output=True,text=True,
                       check=True).stdout.strip()!=REGISTER_BLOB:
        raise ValueError("MG50_ORIGINAL_REGISTRATION_SOURCE_CHANGED")
    entrypoints={}
    for name,expected in zip(FAMILIES,ENTRIES):
        spec=gym.spec(name)
        if spec.entry_point!=expected:
            raise ValueError("MG50_NEW_FAMILY_REGISTRY_NOT_ORIGINAL_SOURCE:"+name)
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
                    ep,state=predictive_episode(
                        gym,entrypoints[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[17])
                else:
                    raise ValueError("MG50_UNKNOWN_FROZEN_ORIGINAL_SOURCE_ACTOR")
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
                raise ValueError("MG50_SOURCE_RESET_SEED_NOT_EQUAL_ACROSS_ROLES")
    if len(rows)!=180 or any(not 1<=x["original_source_actions"]<=192 for x in rows):
        raise ValueError("MG50_NEW_FAMILY_ORIGINAL_SOURCE_EPISODES_MISSING")
    table=metrics(rows)
    candidate=ROLES[17]
    controls=(ROLES[18],ROLES[15],ROLES[13],ROLES[3])
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in FAMILIES)
           for role in (candidate,*controls)}
    target_effects=sum(table[f][candidate]["actual_selected_target_pickup_effects"]
                       for f in FAMILIES)
    corridor_positive=any(table[f][candidate]["positive_goal_episodes"]>0
                          for f in FAMILIES[:2])
    maze_positive=table[FAMILIES[-1]][candidate]["positive_goal_episodes"]>0
    corridor_visible=any(table[f][candidate]["target_visible_frames"]>0
                         for f in FAMILIES[:2])
    changed_decisions=sum(x.get("source_prediction_overrides",0) for x in rows
                          if x["role"]==candidate)
    passed=(changed_decisions>=1 and corridor_visible and corridor_positive
            and maze_positive and all(goals[candidate]>goals[role] for role in controls))
    outcome=p["frozen_dev_filter"]["pass"] if passed else p["frozen_dev_filter"]["fail"]
    source={
        "schema":"itd02.mg50.original-source-public-predictive-uncertainty.dev.v1",
        "classification":outcome,
        "family_source_registration_blob_sha1":REGISTER_BLOB,
        "unchanged_mg44_source_blob_sha1":POLICY_BLOB,
        "original_180_episodes":rows,
        "original_selected_action_count":sum(x["original_source_actions"] for x in rows),
        "per_family_per_role":table,
        "predictive_transition_filter":{
            "candidate":candidate,"goals":goals,
            "corridor_exact_target_visible":corridor_visible,
            "corridor_original_positive_goal":corridor_positive,
            "obstructedmaze_original_positive_goal":maze_positive,
            "candidate_actual_mission_target_effects":target_effects,
            "candidate_source_prediction_overrides":changed_decisions,
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
    resources={"schema":"itd02.mg50.auxiliary-host-episode-resources.v1",
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
            or len(first["source"]["original_180_episodes"])!=180
            or first["source"]["scientific_first_use"] is not False
            or first["source"]["zero_external_actions"] is not True):
            raise ValueError("MG50_INDEPENDENT_ORIGINAL_PROCESSES_DIVERGED")
        print("MG50_TWO_AUTHENTIC_ORIGINAL_DOOR_MEMORY_PROCESSES_IDENTICAL",
              first["canonical_source_sha256"])
        print("MG50_FROZEN_DEVELOPMENT_CLASSIFICATION",
              first["source"]["classification"])
        print("MG50_ORIGINAL_PER_FAMILY_GOALS",json.dumps(
              {k:{role:z["positive_goal_episodes"] for role,z in v.items()
                  if role in (ROLES[0],ROLES[1],ROLES[13],ROLES[14])}
               for k,v in first["source"]["per_family_per_role"].items()},sort_keys=True))
        print("MG50_DOOR_MEMORY_FILTER",json.dumps(
              first["source"]["predictive_transition_filter"],sort_keys=True))
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
                                   receipt.get("classification","MG50_BLOCKED"))
    print("MG50_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(receipt.get("error","MG50_UNKNOWN_SOURCE_BLOCKER"))
    print("MG50_ORIGINAL_SOURCE_SHA256",receipt["canonical_source_sha256"])
if __name__=="__main__":
    main()

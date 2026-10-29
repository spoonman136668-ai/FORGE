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
from mg44_public_precondition_release import (
    PublicSlotRelease,public_release_episode,synthetic_source_preflight
    as original_mg44_preflight)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg47_door_action_effect_memory_prereg.json"
PARENT="53d15bff28fc230dcb46ac0c8d9c75a334c43a33"
FREEZE="62eafedcb252624f9762f255edbe8325c3c5e969"
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
 "mg33_public_history_frontier_unchanged",
 "mg34_graph_lookahead_unchanged",
 "mg33c_actiononly_ucb_exact_source",
 "mg33c_actiononly_round_robin_exact_source",
 "mg38_generic_affordance_prior_enabled_exact_source",
 "mg39b_generic_affordance_prior_removed",
 "mg40_precondition_memory_enabled_unchanged",
 "mg40_precondition_memory_ablated_unchanged",
 "mg42_observed_reversal_guard_unchanged",
 "mg43_engineered_target_matcher_plus_learned_action_value_unchanged",
 "mg43_engineered_target_matcher_no_action_value_ablation_unchanged",
 "mg44_public_precondition_release_enabled_UNMODIFIED",
 "mg44_public_precondition_release_disabled_UNMODIFIED",
 "mg47_door_action_effect_memory_enabled",
 "mg47_door_action_effect_memory_disabled",
 "seeded_uniform_random")

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    c=p["cohort"]; f=c["families"]
    if (p["schema"]!="itd02.mg47.public-selected-action-conditioned-door-transition-memory.original-dev.v1"
        or p["phase"]!="PROSPECTIVE_FROZEN_BEFORE_MG47_EXECUTABLE_AND_ANY_NEW_ORIGINAL_ACTION"
        or p["parent"]["mg46_head"]!=PARENT
        or p["source_pins"]["farama"]!=UPSTREAM
        or p["source_pins"]["minigrid_registry_blob"]!=REGISTER_BLOB
        or tuple((q["id"],q["entry"]) for q in f)!=tuple(zip(FAMILIES,ENTRIES))
        or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["dev_seed_rows"]))!=SEEDS
        or c["actor_episodes"]!=162
        or c["source_selected_action_cap"]!=192
        or c["independent_original_processes"]!=2
        or not all(p["safety"].values())):
        raise ValueError("MG47_FROZEN_SOURCE_PROTOCOL_DRIFT")
    flat=[v for seeds in SEEDS for v in seeds]
    if len(flat)!=9 or len(set(flat))!=9:
        raise ValueError("MG47_DUPLICATED_ORIGINAL_DEV_COHORT")
    for h in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",h,"HEAD").returncode:
            raise ValueError("MG47_FROZEN_COMMIT_MISSING")
    for seed in flat:
        q=git("grep","-n","-w",str(seed),PARENT,"--",
              "research/lcrm01","docs/research")
        if q.returncode==0:raise ValueError("MG47_SEED_ALREADY_EXPOSED")
        if q.returncode!=1:raise ValueError("MG47_SOURCE_ANCESTRY_SCAN_FAIL")
    original_policy_blob=git("hash-object","research/lcrm01/mg44_public_precondition_release.py")
    if original_policy_blob.returncode or original_policy_blob.stdout.strip()!=POLICY_BLOB:
        raise ValueError("MG47_ORIGINAL_MG44_SOURCE_CHANGED")
    return p

def preflight():
    p=frozen()
    original_mg44_preflight()
    if PublicSlotRelease.__module__!="mg44_public_precondition_release":
        raise ValueError("MG47_MG44_CLASS_ORIGINAL_IMPORT_MISSING")
    a={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
       "direction":0,"mission":"pick up the blue ball"}
    door_closed=json.loads(json.dumps(a))
    door_open=json.loads(json.dumps(a))
    door_closed["image"][3][5]=[4,0,1]
    door_open["image"][3][5]=[4,0,0]
    on=DoorMemoryNavigation(True);off=DoorMemoryNavigation(False)
    for obj in (on,off):
        obj.pending=(digest(door_closed),5)
        obj.observe_selected(door_closed,5,door_open,0.0,False)
        obj.pending=(digest(door_open),5)
        obj.observe_selected(door_open,5,door_closed,0.0,False)
        if obj.door_open_observed!=1 or obj.door_close_observed!=1:
            raise ValueError("MG47_ORIGINAL_SELECTED_DOOR_EFFECT_NOT_LEARNED")
        ck=obj.checkpoint()
        if DoorMemoryNavigation.restore(ck).checkpoint()!=ck:
            raise ValueError("MG47_COLD_DOOR_MEMORY_NOT_RESTORED")
        obj.begin_episode()
        if obj.door_open_observed!=1 or obj.door_close_observed!=1:
            raise ValueError("MG47_WITHIN_FAMILY_MEMORY_LOST")
    for obj in (on,off):
        # Source-only synthetic exact choice check: one action selected using
        # original inherited source policy, no Farama reset/step.
        selected=obj.choose(door_open)
        if selected not in range(7):
            raise ValueError("MG47_SYNTHETIC_SELECTED_ACTION_INVALID")
        obj.observe_selected(door_open,selected,door_open,0.0,False)
    print("MG47_PUBLIC_SELECTED_DOOR_CONSEQUENCE_ON_OFF_PREFLIGHT_PASS_NO_SCIENCE")
    return p


class DoorMemoryNavigation(PublicSlotRelease):
    """Engineered door outcome feature + actual own-selected evidence counters.

    No private map, pose, carrying or access to original env hidden fields.
    """
    SCHEMA="mg47.original-public-door-selected-effect-memory.v1"
    def __init__(self,evidence_enabled=True):
        super().__init__(release_enabled=True)
        self.evidence_enabled=evidence_enabled
        self.door_open_observed=0
        self.door_close_observed=0
        self.door_memory_vetoes=0

    def choose(self,public):
        selected=super().choose(public)
        front=public["image"][3][5]
        if (self.evidence_enabled and self.phase=="seek" and selected==5
            and front[0]==4 and front[2]==0
            and self.door_open_observed>0 and self.door_close_observed>0):
            if self.pending != (digest(public),5):
                raise ValueError("MG47_SOURCE_SELECTED_PENDING_CHANGED")
            self.pending=(digest(public),2)
            self.door_memory_vetoes+=1
            return 2
        return selected

    def observe_selected(self,before,action,after,reward,terminated):
        front=before["image"][3][5]
        later=after["image"][3][5]
        if (action==5 and before["direction"]==after["direction"]
            and front[0]==4 and later[0]==4):
            if front[2]==1 and later[2]==0:
                self.door_open_observed+=1
            elif front[2]==0 and later[2]==1:
                self.door_close_observed+=1
        super().observe_selected(before,action,after,reward,terminated)

    def checkpoint(self):
        base=json.loads(PublicSlotRelease.checkpoint(self))
        return json.dumps({"schema":self.SCHEMA,"base":base,
            "evidence_enabled":self.evidence_enabled,
            "door_open_observed":self.door_open_observed,
            "door_close_observed":self.door_close_observed,
            "door_memory_vetoes":self.door_memory_vetoes},
            sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8")

    @classmethod
    def restore(cls,raw):
        d=json.loads(raw)
        if (set(d)!={"schema","base","evidence_enabled","door_open_observed",
                     "door_close_observed","door_memory_vetoes"}
            or d["schema"]!=cls.SCHEMA
            or type(d["evidence_enabled"]) is not bool
            or any(type(d[k]) is not int or d[k]<0 for k in
                   ("door_open_observed","door_close_observed","door_memory_vetoes"))):
            raise ValueError("MG47_COLD_DOOR_SOURCE_STATE_INVALID")
        old=PublicSlotRelease.restore(json.dumps(d["base"],sort_keys=True,
            separators=(",",":"),ensure_ascii=True).encode("utf8"))
        if not old.release_enabled:
            raise ValueError("MG47_SOURCE_RELEASE_ROUTINE_UNEXPECTED_DISABLED")
        out=cls(d["evidence_enabled"])
        out.__dict__.update(old.__dict__)
        for k in ("door_open_observed","door_close_observed","door_memory_vetoes"):
            setattr(out,k,d[k])
        if out.checkpoint()!=raw:
            raise ValueError("MG47_COLD_DOOR_SOURCE_RESTORE_MISMATCH")
        return out

def door_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG47_ORIGINAL_FARAMA_SOURCE_UNMATCHED")
        raw,_=env.reset(seed=seed)
        first=public(raw);mission=first["mission"]
        actor=DoorMemoryNavigation(enabled) if prior is None else DoorMemoryNavigation.restore(prior)
        if actor.evidence_enabled is not enabled:
            raise ValueError("MG47_CROSS_ABLATION_STATE")
        actor.begin_episode()
        before_n=actor.total
        triggers_before=actor.release_triggers
        releases_before=actor.confirmed_releases
        retries_before=actor.retried_public_targets
        vetoes_before=actor.door_memory_vetoes
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG47_ORIGINAL_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG47_ORIGINAL_SELECTED_FEEDBACK_INVALID")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG47_SELECTED_DOOR_MEMORY_ON" if enabled
                                else "MG47_SELECTED_DOOR_MEMORY_ABLATION"})
            raw=raw2
            if term or trunc:break
        ck=actor.checkpoint()
        if (DoorMemoryNavigation.restore(ck).checkpoint()!=ck
            or actor.total!=before_n+len(events)):
            raise ValueError("MG47_ORIGINAL_COLD_MEMORY_NOT_RETAINED")
        return ({"family":family,
                 "role":ROLES[15] if enabled else ROLES[16],
                 "seed_dev_exposed":seed,
                 "public_start_sha256":original_digest(first),
                 "original_public_mission":mission,
                 "original_source_actions":len(events),
                 "prior_selected_source_samples":before_n,
                 "selected_source_samples_after":actor.total,
                 "original_terminal_goal_rewards":
                    sum(int(e["reward"]>0 and e["terminated"]) for e in events),
                 "observed_public_changes":
                    sum(e["before_sha256"]!=e["after_sha256"] for e in events),
                 "unique_public_views":len({e["before_sha256"] for e in events}),
                 "distinct_actions":len({e["action"] for e in events}),
                 "checkpoint_sha256":hashlib.sha256(ck).hexdigest(),
                 "source_events_sha256":original_digest(events),
                 "release_triggers":actor.release_triggers-triggers_before,
                 "release_actual_public_effects":actor.confirmed_releases-releases_before,
                 "release_retry_target_attempts":actor.retried_public_targets-retries_before,
                 "source_door_open_observed":actor.door_open_observed,
                 "source_door_close_observed":actor.door_close_observed,
                 "source_memory_vetoes":actor.door_memory_vetoes-vetoes_before,
                 "source_events":events},ck)
    finally:env.close()

def metrics(rows):
    result={}
    for family in FAMILIES:
        result[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG45_SOURCE_ROLE_NOT_3_NEW_TRANSFER_EPISODES")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG45_WITHIN_FAMILY_SOURCE_MEMORY_NOT_RETAINED")
            counts=collections.Counter()
            hist=[0]*7
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG45_ORIGINAL_EPISODE_EVENT_HASH_FAILED")
                for i,e in enumerate(ep["source_events"],1):
                    if (e["index"]!=i or e["external_actions"]!=0
                        or digest(e["before"])!=e["before_sha256"]
                        or digest(e["after"])!=e["after_sha256"]):
                        raise ValueError("MG45_ORIGINAL_SOURCE_EVENT_NOT_AUTHENTIC")
                    v=event_metric(e)
                    counts.update(v)
                    hist[e["action"]]+=1
            if sum(hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG45_SELECTED_ACTION_COUNT_MISMATCH")
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
        raise ValueError("MG45_NOT_PINNED_FARAMA_IMPORT")
    orig=original_frozen()
    attest_source(source_root,orig)
    if subprocess.run(["git","-C",str(source_root),"hash-object",
                       "minigrid/__init__.py"],capture_output=True,text=True,
                       check=True).stdout.strip()!=REGISTER_BLOB:
        raise ValueError("MG45_ORIGINAL_REGISTRATION_SOURCE_CHANGED")
    entrypoints={}
    for name,expected in zip(FAMILIES,ENTRIES):
        spec=gym.spec(name)
        if spec.entry_point!=expected:
            raise ValueError("MG45_NEW_FAMILY_REGISTRY_NOT_ORIGINAL_SOURCE:"+name)
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
                    ep,state=door_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[15])
                else:
                    raise ValueError("MG47_UNKNOWN_FROZEN_ORIGINAL_SOURCE_ACTOR")
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
                raise ValueError("MG45_SOURCE_RESET_SEED_NOT_EQUAL_ACROSS_ROLES")
    if len(rows)!=162 or any(not 1<=x["original_source_actions"]<=192 for x in rows):
        raise ValueError("MG45_NEW_FAMILY_ORIGINAL_SOURCE_EPISODES_MISSING")
    table=metrics(rows)
    candidate=ROLES[15]
    controls=(ROLES[16],ROLES[13],ROLES[14],ROLES[3])
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in FAMILIES)
           for role in (candidate,*controls)}
    target_effects=sum(table[f][candidate]["actual_selected_target_pickup_effects"]
                       for f in FAMILIES)
    corridor_positive=sum(table[f][candidate]["positive_goal_episodes"]>0
                          for f in FAMILIES[:2])>=1
    maze_positive=table[FAMILIES[-1]][candidate]["positive_goal_episodes"]>=1
    corridor_visible=sum(table[f][candidate]["target_visible_frames"] for f in FAMILIES[:2])>=1
    passed=(corridor_visible and corridor_positive and maze_positive
            and all(goals[candidate]>goals[role] for role in controls))
    outcome=p["frozen_dev_filter"]["pass"] if passed else p["frozen_dev_filter"]["fail"]
    source={
        "schema":"itd02.mg47.original-source-door-selected-effect-memory.dev.v1",
        "classification":outcome,
        "family_source_registration_blob_sha1":REGISTER_BLOB,
        "unchanged_mg44_source_blob_sha1":POLICY_BLOB,
        "original_162_episodes":rows,
        "original_selected_action_count":sum(x["original_source_actions"] for x in rows),
        "per_family_per_role":table,
        "door_memory_filter":{
            "candidate":candidate,"goals":goals,
            "corridor_exact_target_visible":corridor_visible,
            "corridor_original_positive_goal":corridor_positive,
            "obstructedmaze_original_positive_goal":maze_positive,
            "candidate_actual_mission_target_effects":target_effects,
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
    resources={"schema":"itd02.mg47.auxiliary-host-episode-resources.v1",
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
            or len(first["source"]["original_162_episodes"])!=162
            or first["source"]["scientific_first_use"] is not False
            or first["source"]["zero_external_actions"] is not True):
            raise ValueError("MG47_INDEPENDENT_ORIGINAL_PROCESSES_DIVERGED")
        print("MG47_TWO_AUTHENTIC_ORIGINAL_DOOR_MEMORY_PROCESSES_IDENTICAL",
              first["canonical_source_sha256"])
        print("MG47_FROZEN_DEVELOPMENT_CLASSIFICATION",
              first["source"]["classification"])
        print("MG47_ORIGINAL_PER_FAMILY_GOALS",json.dumps(
              {k:{role:z["positive_goal_episodes"] for role,z in v.items()
                  if role in (ROLES[0],ROLES[1],ROLES[13],ROLES[14])}
               for k,v in first["source"]["per_family_per_role"].items()},sort_keys=True))
        print("MG47_DOOR_MEMORY_FILTER",json.dumps(
              first["source"]["door_memory_filter"],sort_keys=True))
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
                                   receipt.get("classification","MG47_BLOCKED"))
    print("MG47_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(receipt.get("error","MG45_UNKNOWN_SOURCE_BLOCKER"))
    print("MG47_ORIGINAL_SOURCE_SHA256",receipt["canonical_source_sha256"])
if __name__=="__main__":
    main()

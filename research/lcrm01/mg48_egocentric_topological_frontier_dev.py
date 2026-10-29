#!/usr/bin/env python3
"""MG48: engineered egocentric observable alignment and uncertain topological frontier DEV.

All original MG48/MG44 selected-source actors imported unchanged. Public-domain
Farama original source and previously qualified source-selected actors only.
Fresh DEV navigation comparison, NOT independently sealed heldout scientific acceptance.
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
    door_episode as original_mg47_door_episode,
    DoorMemoryNavigation, preflight as original_mg47_preflight)
from mg44_public_precondition_release import (
    PublicSlotRelease,public_release_episode,synthetic_source_preflight
    as original_mg44_preflight)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg48_egocentric_topological_frontier_prereg.json"
PARENT="25bed29fc76e6046bc9e71f34ad47b1b38fd7263"
FREEZE="80b1843717b63b3cefbeccaaeab65ed5f4174e68"
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
 "mg48_door_action_effect_memory_enabled_unchanged",
 "mg48_door_action_effect_memory_disabled_unchanged",
 "mg48_empirical_egocentric_topological_frontier_enabled",
 "mg48_empirical_egocentric_topological_frontier_disabled",
 "seeded_uniform_random")
SEEDS=((1061101,1061103,1061107),(1061201,1061203,1061207),
       (1061301,1061303,1061307))

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    c=p["cohort"];m=p["mechanism"]
    if (p["schema"]!="itd02.mg48.public-egocentric-action-conditioned-topology-frontier.original-dev.v1"
        or p["phase"]!="FROZEN_PROSPECTIVE_BEFORE_MG48_EXECUTABLE_OR_FIRST_NEW_ORIGINAL_ACTION"
        or p["parent"]["mg48_sha"]!=PARENT
        or p["sources"]["farama_original"]!=UPSTREAM
        or p["sources"]["farama_registry_sha1"]!=REGISTER_BLOB
        or tuple((q["id"],q["entry"]) for q in c["families"])!=tuple(zip(FAMILIES,ENTRIES))
        or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["fresh_dev_seeds"]))!=SEEDS
        or c["actor_episodes"]!=180
        or c["cap_original_selected_actions"]!=192
        or c["independent_source_processes"]!=2
        or m["parameters"]!={"min_overlap_matches":8,"min_relative_support":3,
                             "max_projected_cells":4096,"local_visit_bonus":1,
                             "turn_tiebreak":"left","action_forward":2,
                             "action_left":0,"action_right":1}
        or not all(p["prohibitions"].values())):
        raise ValueError("MG48_FROZEN_ORIGINAL_SOURCE_TOPOLOGY_PROTOCOL_DRIFT")
    flat=[v for group in SEEDS for v in group]
    if len(flat)!=9 or len(set(flat))!=9:
        raise ValueError("MG48_FROZEN_DEV_SEED_DUPLICATE")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG48_FREEZE_NOT_BEFORE_EXECUTABLE")
    for seed in flat:
        q=git("grep","-n","-w",str(seed),PARENT,"--","research/lcrm01","docs/research")
        if q.returncode==0:raise ValueError("MG48_PRIOR_EXPOSED_FARAMA_DEV_SEED")
        if q.returncode!=1:raise ValueError("MG48_PRIOR_SOURCE_SCAN_UNAVAILABLE")
    source=git("hash-object","research/lcrm01/mg44_public_precondition_release.py")
    if source.returncode or source.stdout.strip()!=POLICY_BLOB:
        raise ValueError("MG48_UNCHANGED_MG44_POLICY_BLOB_DRIFT")
    return p

DIRECTIONS=((1,0),(0,1),(-1,0),(0,-1))
RIGHTS=((0,1),(-1,0),(0,-1),(1,0))

def projected(public,x,y):
    """Engineered public-only egocentric projection; not actual source pose."""
    d=public["direction"]
    if type(d) is not int or d not in range(4):
        raise ValueError("MG48_INVALID_ORIGINAL_PUBLIC_HEADING")
    fx,fy=DIRECTIONS[d];rx,ry=RIGHTS[d]
    image=public["image"]
    result={}
    for i in range(7):
        for j in range(7):
            cell=image[i][j]
            if cell[0]==0:continue
            pos=(x+(6-j)*fx+(i-3)*rx,y+(6-j)*fy+(i-3)*ry)
            result[str(pos[0])+","+str(pos[1])]=cell
    return result

def align(source,new,hypothesis_x,hypothesis_y):
    direction=source["direction"]
    if new["direction"]!=direction:return (0,0)
    fx,fy=DIRECTIONS[direction]
    base=projected(source,hypothesis_x,hypothesis_y)
    fixed=projected(new,hypothesis_x,hypothesis_y)
    shifted=projected(new,hypothesis_x+fx,hypothesis_y+fy)
    def match(other):
        return sum(base[k][0]==v[0] and base[k][2]==v[2]
                   for k,v in other.items() if k in base)
    return match(fixed),match(shifted)

class ObservableFrontier(DoorMemoryNavigation):
    """Uncertain, hand-engineered public projection and empirical frontier.

    No private true x/y/map/inventory. Source-selected forward alignment alone
    updates an *estimated* pose. Unchanged MG48 selected action model remains
    the parent; geometry and selection rule are explicit engineered priors.
    """
    SCHEMA="mg48.uncertain-source-public-egocentric-topological-frontier.v1"

    def __init__(self,topology_enabled=True):
        super().__init__(True)
        self.topology_enabled=topology_enabled
        self.hyp_x=0
        self.hyp_y=0
        self.map_cells={}
        self.node_visits={}
        self.grounded_forward_total=0
        self.grounded_forward_episode=0
        self.ambiguous_forward=0
        self.topology_overrides=0
        self.failed_locked_toggles={}
        self.navigation_proposals=0

    def begin_episode(self):
        super().begin_episode()
        self.hyp_x=0
        self.hyp_y=0
        self.grounded_forward_episode=0
        self.failed_locked_toggles={}
        key="0,0"
        self.node_visits[key]=self.node_visits.get(key,0)+1

    def register_view(self,public):
        for pos,cell in projected(public,self.hyp_x,self.hyp_y).items():
            if pos in self.map_cells or len(self.map_cells)<4096:
                self.map_cells[pos]=cell

    def choose(self,public):
        # Source original MG48 always owns the normal policy proposal.
        original=super().choose(public)
        self.register_view(public)
        if (not self.topology_enabled or self.phase!="seek"
            or self.grounded_forward_episode<=0):
            return original
        # Never override publicly visible original mission target interaction.
        from mg43_public_target_action_value import public_exact_target_front
        if public_exact_target_front(public) is not None:
            return original
        d=public["direction"]
        front=public["image"][3][5]
        fv=front[0] in (1,3,8) or (front[0]==4 and front[2]==0)
        if front[0]==4 and front[2]==2 and original==5:
            # This source-public locked-door state has repeatedly yielded no
            # observed opening on own attempts: avoid cycling an action5.
            key=str(self.hyp_x)+","+str(self.hyp_y)+","+str(d)
            if self.failed_locked_toggles.get(key,0)<2:
                return original
        dirs=((d+3)%4,(d+1)%4,d)
        def visit(heading):
            fx,fy=DIRECTIONS[heading]
            nx=self.hyp_x+fx;ny=self.hyp_y+fy
            cell=self.map_cells.get(str(nx)+","+str(ny))
            if cell is not None and (cell[0]==2 or
                (cell[0]==4 and cell[2] in (1,2))):
                return 1000000
            return self.node_visits.get(str(nx)+","+str(ny),0)
        left,right,ahead=(visit(q) for q in dirs)
        # Grounded first-order frontier action only: no hidden map planning.
        if fv and ahead<=min(left,right)+1:
            chosen=2
        elif left<=right:
            chosen=0
        else:
            chosen=1
        self.navigation_proposals+=1
        if chosen!=original:
            if self.pending!=(digest(public),original):
                raise ValueError("MG48_SOURCE_SELECTED_PENDING_NOT_VERIFIED")
            self.pending=(digest(public),chosen)
            self.topology_overrides+=1
        return chosen

    def observe_selected(self,before,action,after,reward,terminated):
        if self.pending!=(digest(before),action):
            raise ValueError("MG48_OFFPOLICY_SOURCE_FEEDBACK")
        stationary,moved=align(before,after,self.hyp_x,self.hyp_y)
        if action==5 and before["image"][3][5][0]==4 and before["image"][3][5][2]==2:
            # No private key/carrying inferred from failed public state.
            k=str(self.hyp_x)+","+str(self.hyp_y)+","+str(before["direction"])
            if (after["image"][3][5][0]==4 and after["image"][3][5][2]==2):
                self.failed_locked_toggles[k]=self.failed_locked_toggles.get(k,0)+1
        super().observe_selected(before,action,after,reward,terminated)
        if action==2:
            if moved>=8 and moved>=stationary+3:
                fx,fy=DIRECTIONS[before["direction"]]
                self.hyp_x+=fx;self.hyp_y+=fy
                self.grounded_forward_total+=1
                self.grounded_forward_episode+=1
                key=str(self.hyp_x)+","+str(self.hyp_y)
                self.node_visits[key]=self.node_visits.get(key,0)+1
            else:
                self.ambiguous_forward+=1
        self.register_view(after)

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG48_PENDING_SOURCE_ACTION_CANNOT_COLD_RESTORE")
        parent=json.loads(DoorMemoryNavigation.checkpoint(self))
        parent["schema"]=DoorMemoryNavigation.SCHEMA
        return json.dumps({
            "schema":self.SCHEMA,"parent":parent,
            "topology_enabled":self.topology_enabled,
            "hyp_x":self.hyp_x,"hyp_y":self.hyp_y,
            "map_cells":self.map_cells,"node_visits":self.node_visits,
            "grounded_forward_total":self.grounded_forward_total,
            "grounded_forward_episode":self.grounded_forward_episode,
            "ambiguous_forward":self.ambiguous_forward,
            "topology_overrides":self.topology_overrides,
            "failed_locked_toggles":self.failed_locked_toggles,
            "navigation_proposals":self.navigation_proposals},
            sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf8")

    @classmethod
    def restore(cls,raw):
        data=json.loads(raw)
        keys={"schema","parent","topology_enabled","hyp_x","hyp_y",
              "map_cells","node_visits","grounded_forward_total",
              "grounded_forward_episode","ambiguous_forward",
              "topology_overrides","failed_locked_toggles","navigation_proposals"}
        if (set(data)!=keys or data["schema"]!=cls.SCHEMA
            or type(data["topology_enabled"]) is not bool
            or any(type(data[k]) is not int for k in
                   ("hyp_x","hyp_y","grounded_forward_total",
                    "grounded_forward_episode","ambiguous_forward",
                    "topology_overrides","navigation_proposals"))
            or min(data["grounded_forward_total"],data["grounded_forward_episode"],
                   data["ambiguous_forward"],data["topology_overrides"])<0
            or len(data["map_cells"])>4096
            or any(type(v) is not int or v<0 for v in data["node_visits"].values())
            or any(type(v) is not int or v<0 for v in data["failed_locked_toggles"].values())):
            raise ValueError("MG48_INVALID_PUBLIC_UNCERTAIN_TOPOLOGY_COLD_STATE")
        parent=DoorMemoryNavigation.restore(json.dumps(
            data["parent"],sort_keys=True,separators=(",",":"),
            ensure_ascii=True).encode("utf8"))
        out=cls(data["topology_enabled"])
        out.__dict__.update(parent.__dict__)
        for k in keys-{"schema","parent","topology_enabled"}:
            setattr(out,k,data[k])
        out.topology_enabled=data["topology_enabled"]
        if out.checkpoint()!=raw:
            raise ValueError("MG48_SOURCE_COLD_STATE_NOT_IDENTICAL")
        return out

def preflight():
    p=frozen()
    original_mg48_preflight()
    # Public pose translation fixture: the same original observed object cells
    # under real movement are *more consistent* under a translated hypothesis.
    image=[[[2,0,(x+y)%3] for y in range(7)] for x in range(7)]
    before={"image":image,"direction":0,"mission":"pick up the blue ball"}
    moved={"image":[[[0,0,0] if y==0 else list(image[x][y-1])
                       for y in range(7)] for x in range(7)],
           "direction":0,"mission":"pick up the blue ball"}
    a,b=align(before,moved,0,0)
    if b<8 or b<a+3:
        raise ValueError("MG48_SOURCE_ONLY_EMPIRICAL_TRANSLATION_NOT_DETECTED")
    for enabled in (True,False):
        actor=ObservableFrontier(enabled)
        actor.pending=(digest(before),2)
        actor.observe_selected(before,2,moved,0.0,False)
        if (actor.grounded_forward_episode!=1 or actor.hyp_x!=1
            or actor.hyp_y!=0):
            raise ValueError("MG48_ORIGINAL_PUBLIC_SELECTED_FORWARD_NOT_GROUNDED")
        cold=actor.checkpoint()
        if ObservableFrontier.restore(cold).checkpoint()!=cold:
            raise ValueError("MG48_SOURCE_ONLY_COLD_MAP_LOST")
        actor.begin_episode()
        if actor.grounded_forward_episode!=0 or actor.grounded_forward_total!=1:
            raise ValueError("MG48_SOURCE_SELECTED_FAMILY_MEMORY_RESET_WRONG")
        choice=actor.choose(before)
        if choice not in range(7):
            raise ValueError("MG48_BAD_7_ACTION_SOURCE_POLICY")
        actor.pending=None
    print("MG48_ORIGINAL_CROSS_OS_PUBLIC_ONLY_PROJECTION_ALIGN_FRONTIER_PASS")
    return p

def topological_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG48_NOT_PINNED_ORIGINAL_FARAMA_SOURCE")
        raw,_=env.reset(seed=seed)
        first=public(raw);mission=first["mission"]
        actor=ObservableFrontier(enabled) if prior is None else ObservableFrontier.restore(prior)
        if actor.topology_enabled is not enabled:
            raise ValueError("MG48_CROSS_ARM_TOPOLOGY_ABLATION_CHANGED")
        actor.begin_episode()
        n0=actor.total
        grounded0=actor.grounded_forward_total
        ambiguous0=actor.ambiguous_forward
        override0=actor.topology_overrides
        trigger0=actor.release_triggers
        release0=actor.confirmed_releases
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:raise ValueError("MG48_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG48_INVALID_ORIGINAL_SELECTED_SOURCE_FEEDBACK")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG48_PUBLIC_UNCERTAIN_TOPOLOGY_ON" if enabled
                                else "MG48_PUBLIC_TOPOLOGY_ABLATION_OFF"})
            raw=raw2
            if term or trunc:break
        state=actor.checkpoint()
        if (ObservableFrontier.restore(state).checkpoint()!=state
            or actor.total!=n0+len(events)):
            raise ValueError("MG48_ORIGINAL_PUBLIC_TOPOLOGY_COLD_RESTORE_FAIL")
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
                 "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
                 "source_events_sha256":original_digest(events),
                 "source_grounded_forward_alignments":actor.grounded_forward_total-grounded0,
                 "source_ambiguous_forward":actor.ambiguous_forward-ambiguous0,
                 "source_frontier_overrides":actor.topology_overrides-override0,
                 "source_public_hypothesized_cells_count":len(actor.map_cells),
                 "source_release_triggers":actor.release_triggers-trigger0,
                 "source_release_actual_effects":actor.confirmed_releases-release0,
                 "source_events":events},state)
    finally:env.close()

def metrics(rows):
    result={}
    for family in FAMILIES:
        result[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG48_SOURCE_ROLE_NOT_3_NEW_TRANSFER_EPISODES")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG48_WITHIN_FAMILY_SOURCE_MEMORY_NOT_RETAINED")
            counts=collections.Counter()
            hist=[0]*7
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG48_ORIGINAL_EPISODE_EVENT_HASH_FAILED")
                for i,e in enumerate(ep["source_events"],1):
                    if (e["index"]!=i or e["external_actions"]!=0
                        or digest(e["before"])!=e["before_sha256"]
                        or digest(e["after"])!=e["after_sha256"]):
                        raise ValueError("MG48_ORIGINAL_SOURCE_EVENT_NOT_AUTHENTIC")
                    v=event_metric(e)
                    counts.update(v)
                    hist[e["action"]]+=1
            if sum(hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG48_SELECTED_ACTION_COUNT_MISMATCH")
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
        raise ValueError("MG48_NOT_PINNED_FARAMA_IMPORT")
    orig=original_frozen()
    attest_source(source_root,orig)
    if subprocess.run(["git","-C",str(source_root),"hash-object",
                       "minigrid/__init__.py"],capture_output=True,text=True,
                       check=True).stdout.strip()!=REGISTER_BLOB:
        raise ValueError("MG48_ORIGINAL_REGISTRATION_SOURCE_CHANGED")
    entrypoints={}
    for name,expected in zip(FAMILIES,ENTRIES):
        spec=gym.spec(name)
        if spec.entry_point!=expected:
            raise ValueError("MG48_NEW_FAMILY_REGISTRY_NOT_ORIGINAL_SOURCE:"+name)
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
                    ep,state=original_mg48_door_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[15])
                elif role in (ROLES[17],ROLES[18]):
                    ep,state=topological_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[17])
                else:
                    raise ValueError("MG48_UNKNOWN_FROZEN_ORIGINAL_SOURCE_ACTOR")
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
                raise ValueError("MG48_SOURCE_RESET_SEED_NOT_EQUAL_ACROSS_ROLES")
    if len(rows)!=180 or any(not 1<=x["original_source_actions"]<=192 for x in rows):
        raise ValueError("MG48_NEW_FAMILY_ORIGINAL_SOURCE_EPISODES_MISSING")
    table=metrics(rows)
    candidate=ROLES[17]
    controls=(ROLES[18],ROLES[15],ROLES[13],ROLES[3])
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in FAMILIES)
           for role in (candidate,*controls)}
    corridor_visible=sum(table[f][candidate]["target_visible_frames"]
                         for f in FAMILIES[:2])>=1
    corridor_positive=any(table[f][candidate]["positive_goal_episodes"]>0
                          for f in FAMILIES[:2])
    maze_positive=table[FAMILIES[-1]][candidate]["positive_goal_episodes"]>0
    grounded_corridor=sum(row.get("source_grounded_forward_alignments",0)
             for row in rows if row["family"] in FAMILIES[:2]
             and row["role"]==candidate)
    original_target_effects=sum(
        table[f][candidate]["actual_selected_target_pickup_effects"]
        for f in FAMILIES)
    passed=(grounded_corridor>=1 and corridor_visible and corridor_positive
            and maze_positive and all(goals[candidate]>goals[role] for role in controls))
    outcome=p["frozen_dev_filter"]["pass"] if passed else p["frozen_dev_filter"]["fail"]
    source={
        "schema":"itd02.mg48.original-source-public-uncertain-topology.dev.v1",
        "classification":outcome,
        "family_source_registration_blob_sha1":REGISTER_BLOB,
        "unchanged_mg44_source_blob_sha1":POLICY_BLOB,
        "original_180_episodes":rows,
        "original_selected_action_count":sum(x["original_source_actions"] for x in rows),
        "per_family_per_role":table,
        "topological_frontier_filter":{
            "candidate":candidate,"goals":goals,
            "corridor_exact_target_visible":corridor_visible,
            "corridor_original_positive_goal":corridor_positive,
            "obstructedmaze_original_positive_goal":maze_positive,
            "candidate_actual_mission_target_effects":original_target_effects,
            "grounded_corridor_forward_alignment":grounded_corridor,
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
    resources={"schema":"itd02.mg48.auxiliary-host-episode-resources.v1",
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
            raise ValueError("MG48_INDEPENDENT_ORIGINAL_PROCESSES_DIVERGED")
        print("MG48_TWO_AUTHENTIC_ORIGINAL_DOOR_MEMORY_PROCESSES_IDENTICAL",
              first["canonical_source_sha256"])
        print("MG48_FROZEN_DEVELOPMENT_CLASSIFICATION",
              first["source"]["classification"])
        print("MG48_ORIGINAL_PER_FAMILY_GOALS",json.dumps(
              {k:{role:z["positive_goal_episodes"] for role,z in v.items()
                  if role in (ROLES[0],ROLES[1],ROLES[13],ROLES[14])}
               for k,v in first["source"]["per_family_per_role"].items()},sort_keys=True))
        print("MG48_DOOR_MEMORY_FILTER",json.dumps(
              first["source"]["topological_frontier_filter"],sort_keys=True))
        return
    if any(x is None for x in (a.source_root,a.native_go,a.control_root,
                               a.output,a.resources)):
        ap.error("--source-root --native-go --control-root --output --resources required")
    started=time.perf_counter()
    try:
        receipt,resources=run_original(
            a.source_root,a.native_go,a.control_root,p)
    except Exception as e:
        receipt={"schema":"itd02.mg48.door-memory-original-source-blocked.v1",
                 "classification":p["frozen_dev_filter"]["source_block"],
                 "error_type":type(e).__name__,"error":str(e),
                 "trace_tail":traceback.format_exc().splitlines()[-16:]}
        resources={"schema":"itd02.mg48.resources-blocked.v1","records":[]}
    receipt["host_wall_seconds_outside_canonical_source"]=round(
        time.perf_counter()-started,6)
    a.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",
                        encoding="utf8")
    a.resources.write_text(json.dumps(resources,indent=2,sort_keys=True)+"\n",
                           encoding="utf8")
    cls=receipt.get("source",{}).get("classification",
                                   receipt.get("classification","MG48_BLOCKED"))
    print("MG48_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(receipt.get("error","MG48_UNKNOWN_SOURCE_BLOCKER"))
    print("MG48_ORIGINAL_SOURCE_SHA256",receipt["canonical_source_sha256"])
if __name__=="__main__":
    main()

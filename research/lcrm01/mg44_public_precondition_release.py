#!/usr/bin/env python3
"""MG43 prospective original public selected-action prerequisite evidence ablation.

MG43 uses a hand-engineered selected-action PUBLIC effect detector and a
memory-based policy score condition. It is not proof of native model improvement,
automatic discovery of object semantics, or held-out scientific transfer.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, re, subprocess, time, traceback
from pathlib import Path
from mg40_action_precondition_dev import evidence_episode as original_mg40_evidence_episode
from mg42_observed_reversal_guard import reversal_episode as original_mg42_reversal_episode, ReversalGuardNavigation as OriginalMG42
from mg39b_original_affordance_ablation import (
    FAMILIES, UPSTREAM, digest, event_metric, mg33_episode, mg34_episode,
    corrected_class, control_episode, original_mg38_episode, ablated_episode,
    NavigationAwareModel, source_only as mg39b_source_only)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg44_public_precondition_release_prereg.json"
PARENT="495ea7e5be473121d84c4a7928a64032234ccb07"
FREEZE="3cc294880ee3a0f4df8cb984d20cb37a16f94d5"
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
 "mg44_public_precondition_release_enabled","mg44_public_precondition_release_disabled",
 "seeded_uniform_random")
SEEDS=((1031101,1031103,1031107),(1031201,1031203,1031207),
       (1031301,1031303,1031307),(1031401,1031403,1031407))

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    c=p["cohort"];m=p["mechanism"];pa=m["parameters"]
    if (p["schema"]!="itd02.mg44.own-observed-object-slot-release-before-public-target.dev.v1"
        or p["phase"]!="FROZEN_BEFORE_EXECUTABLE_AND_ANY_NEW_ORIGINAL_FARAMA_ACTION"
        or p["parent"]["mg43_head"]!=PARENT
        or p["source"]["farama_original"]!=UPSTREAM
        or tuple(c["families"])!=FAMILIES
        or tuple(c["roles"])!=ROLES
        or tuple(map(tuple,c["fresh_development_seeds"]))!=SEEDS
        or c["episodes"]!=192 or c["original_actions_cap_each"]!=192
        or c["independent_complete_processes"]!=2
        or pa!={"turn_action_left":0,"turn_action_right":1,
                "original_action_pickup":3,"original_action_drop":4,
                "max_find_empty_turns":4,"max_return_turns":4,
                "max_source_steps_per_episode":192}
        or not all(p["prohibitions"].values())):
        raise ValueError("MG44_FROZEN_SOURCE_COHORT_OR_PUBLIC_RELEASE_CONTRACT_CHANGED")
    seeds=[x for grp in SEEDS for x in grp]
    if len(seeds)!=12 or len(set(seeds))!=12:
        raise ValueError("MG44_FRESH_DEV_SOURCE_ID_DUPLICATE")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG44_PREREG_NOT_BEFORE_EXECUTABLE")
    for seed in seeds:
        old=git("grep","-n","-w",str(seed),PARENT,"--","research/lcrm01","docs/research")
        if old.returncode==0:raise ValueError("MG44_PARENT_SOURCE_SEED_ALREADY_EXPOSED")
        if old.returncode!=1:raise ValueError("MG44_PARENT_SOURCE_SCAN_UNAVAILABLE")
    return p


class EvidenceNavigation(NavigationAwareModel):
    """Exact original MG38 scorer plus frozen public-evidence addends.

    'occupied_proxy' is never read from environment inventory. It is only
    an episode-local inference from one's own publicly observed action effects.
    """
    SCHEMA="mg43.public-effect-proxy-navigation.v1"

    def __init__(self,edges=None,visits=None,global_actions=None,total=0,
                 turn_chain=0,last_forward_nochange=False,occupied_proxy=False,
                 evidence_enabled=True,observed_pickups=0,observed_drops=0):
        super().__init__(edges,visits,global_actions,total,turn_chain,
                         last_forward_nochange)
        self.occupied_proxy=occupied_proxy
        self.evidence_enabled=evidence_enabled
        self.observed_pickups=observed_pickups
        self.observed_drops=observed_drops

    def begin_episode(self):
        super().begin_episode()
        self.occupied_proxy=False

    def choose(self, public):
        if self.pending is not None:
            raise ValueError("MG38_DOUBLE_CHOICE_BEFORE_ORIGINAL_FEEDBACK")
        key = digest(public)
        first = int(key[:2], 16) % 7
        front = public["image"][3][5]
        row = self.edges.get(key, {})
        chosen = None
        best = None
        for offset in range(7):
            action = (first + offset) % 7
            cell = row.get(str(action))
            local_count = cell["n"] if cell else 0
            g = self.global_actions[action]
            g_count = g["n"]
            effect = (g["changed"] + 0.5) / (g_count + 1)
            novel = (g["novel"] + 0.5) / (g_count + 1)
            goal = (g["goals"] + 0.25) / (g_count + 1)
            if action == 2:
                # Forward public change is *not* assumed to prove locomotion.
                local_nochange = (0 if cell is None else
                                  (cell["n"] - cell["changed"]) / cell["n"])
                score = (2.3 + 1.7 / (1 + local_count)
                         + 1.0 * novel - 2.0 * local_nochange)
            elif action in (0, 1):
                # Rotations NEVER get credit for changing egocentric public SHA.
                # Rotation is still eligible after unsuccessful own forward.
                score = (0.4 + 0.4 / (1 + local_count)
                         + 2.5 * int(self.last_forward_nochange)
                         - 1.25 * self.turn_chain)
                if self.turn_chain >= 2:
                    score -= 8.0
            else:
                score = (0.6 + 1.7 / (1 + local_count) + 2.0 * goal
                         + 0.7 * effect - 0.1 * local_count)
                # Public object classes only; NOT a mission-target matcher.
                if action == 3 and front[0] in (5,6,7):
                    score += 2.2
                elif action == 5 and front[0] == 4:
                    score += 2.2
            # MG43 prospective public-action-effect proxy: bounded engineered
            # score adjustments. Not a learned semantic/action-rule discovery.
            if self.evidence_enabled and self.occupied_proxy:
                if action == 4 and front[0] == 1:
                    score += 8.0
                if action == 3 and front[0] in (5, 6, 7):
                    score -= 8.0
            # Keep reward tied only to selected empirical source consequences.
            if cell is not None:
                score += 2.0 * cell["goals"] / (1 + cell["n"])
            if best is None or score > best:
                best = score
                chosen = action
        self.pending = (key, chosen)
        return chosen

    def observe_selected(self,before,action,after,reward,terminated):
        # Validation and empirical transition update first; no offpolicy data.
        super().observe_selected(before,action,after,reward,terminated)
        front=before["image"][3][5]
        later=after["image"][3][5]
        same_heading=before["direction"]==after["direction"]
        if (action==3 and same_heading and front[0] in (5,6,7)
            and later[0]==1):
            self.occupied_proxy=True
            self.observed_pickups+=1
        elif (action==4 and same_heading and front[0]==1
              and later[0] in (5,6,7)):
            self.occupied_proxy=False
            self.observed_drops+=1

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG43_PENDING_SELECTED_ACTION_NOT_CHECKPOINTABLE")
        obj={"schema":self.SCHEMA,"edges":self.edges,"visits":self.visits,
          "global_actions":self.global_actions,"total":self.total,
          "turn_chain":self.turn_chain,
          "last_forward_nochange":self.last_forward_nochange,
          "occupied_proxy":self.occupied_proxy,
          "evidence_enabled":self.evidence_enabled,
          "observed_pickups":self.observed_pickups,
          "observed_drops":self.observed_drops}
        return json.dumps(obj,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True).encode("utf-8")

    @classmethod
    def restore(cls,raw):
        d=json.loads(raw)
        expected={"schema","edges","visits","global_actions","total",
          "turn_chain","last_forward_nochange","occupied_proxy",
          "evidence_enabled","observed_pickups","observed_drops"}
        if (set(d)!=expected or d["schema"]!=cls.SCHEMA
            or any(type(d[x]) is not bool for x in
                   ("occupied_proxy","evidence_enabled","last_forward_nochange"))
            or any(type(d[x]) is not int or d[x]<0 for x in
                   ("total","turn_chain","observed_pickups","observed_drops"))):
            raise ValueError("MG43_INVALID_COLD_EVIDENCE_SCHEMA")
        model=cls(d["edges"],d["visits"],d["global_actions"],d["total"],
                  d["turn_chain"],d["last_forward_nochange"],d["occupied_proxy"],
                  d["evidence_enabled"],d["observed_pickups"],d["observed_drops"])
        if (raw!=model.checkpoint() or len(model.global_actions)!=7
            or model.total!=sum(z["n"] for z in model.global_actions)
            or model.total!=sum(c["n"] for r in model.edges.values()
                                for c in r.values())
            or any(c["n"]!=sum(c["next"].values()) for r in model.edges.values()
                   for c in r.values())
            or model.observed_pickups>model.total
            or model.observed_drops>model.total):
            raise ValueError("MG43_COLD_SELECTED_ACTION_EVIDENCE_DIVERGED")
        return model

class ReversalGuardNavigation(EvidenceNavigation):
    SCHEMA="mg43.observed-public-effect-reversal-guard.v1"

    def __init__(self,edges=None,visits=None,global_actions=None,total=0,
                 turn_chain=0,last_forward_nochange=False,occupied_proxy=False,
                 evidence_enabled=True,observed_pickups=0,observed_drops=0,
                 reversal_evidence_count=0,last_pickup_total=-1):
        super().__init__(edges,visits,global_actions,total,turn_chain,
                         last_forward_nochange,occupied_proxy,evidence_enabled,
                         observed_pickups,observed_drops)
        self.reversal_evidence_count=reversal_evidence_count
        self.last_pickup_total=last_pickup_total

    def begin_episode(self):
        super().begin_episode()
        self.last_pickup_total=-1

    def choose(self, public):
        if self.pending is not None:
            raise ValueError("MG38_DOUBLE_CHOICE_BEFORE_ORIGINAL_FEEDBACK")
        key = digest(public)
        first = int(key[:2], 16) % 7
        front = public["image"][3][5]
        row = self.edges.get(key, {})
        chosen = None
        best = None
        for offset in range(7):
            action = (first + offset) % 7
            cell = row.get(str(action))
            local_count = cell["n"] if cell else 0
            g = self.global_actions[action]
            g_count = g["n"]
            effect = (g["changed"] + 0.5) / (g_count + 1)
            novel = (g["novel"] + 0.5) / (g_count + 1)
            goal = (g["goals"] + 0.25) / (g_count + 1)
            if action == 2:
                # Forward public change is *not* assumed to prove locomotion.
                local_nochange = (0 if cell is None else
                                  (cell["n"] - cell["changed"]) / cell["n"])
                score = (2.3 + 1.7 / (1 + local_count)
                         + 1.0 * novel - 2.0 * local_nochange)
            elif action in (0, 1):
                # Rotations NEVER get credit for changing egocentric public SHA.
                # Rotation is still eligible after unsuccessful own forward.
                score = (0.4 + 0.4 / (1 + local_count)
                         + 2.5 * int(self.last_forward_nochange)
                         - 1.25 * self.turn_chain)
                if self.turn_chain >= 2:
                    score -= 8.0
            else:
                score = (0.6 + 1.7 / (1 + local_count) + 2.0 * goal
                         + 0.7 * effect - 0.1 * local_count)
                # Public object classes only; NOT a mission-target matcher.
                if action == 3 and front[0] in (5,6,7):
                    score += 2.2
                elif action == 5 and front[0] == 4:
                    score += 2.2
            # MG40 prospective public-action-effect proxy: bounded engineered
            # score adjustments. Not a learned semantic/action-rule discovery.
            if self.evidence_enabled and self.occupied_proxy:
                if action == 4 and front[0] == 1:
                    score += 8.0
                if action == 3 and front[0] in (5, 6, 7):
                    score -= 8.0
            # Keep reward tied only to selected empirical source consequences.
            if cell is not None:
                score += 2.0 * cell["goals"] / (1 + cell["n"])
            # MG42: only observed own pickup->drop reversals trigger a
            # bounded local anti-reversal penalty. No hidden inventory or
            # mission-target identity is used by this action scorer.
            if (action == 4 and self.occupied_proxy
                and self.reversal_evidence_count > 0
                and self.last_pickup_total >= 0
                and self.total - self.last_pickup_total <= 8):
                score -= 12.0
            if best is None or score > best:
                best = score
                chosen = action
        self.pending = (key, chosen)
        return chosen

    def observe_selected(self,before,action,after,reward,terminated):
        before_pickups=self.observed_pickups
        before_drops=self.observed_drops
        # Exact MG40 selected public-effect model validates the source
        # action and updates all empirical transition/reward observations.
        super().observe_selected(before,action,after,reward,terminated)
        if self.observed_pickups>before_pickups:
            self.last_pickup_total=self.total
        if self.observed_drops>before_drops:
            if (self.last_pickup_total>=0 and
                1 <= self.total-self.last_pickup_total <= 4):
                self.reversal_evidence_count+=1
            self.last_pickup_total=-1

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG43_PENDING_SOURCE_SELECTED_ACTION")
        x={"schema":self.SCHEMA,"edges":self.edges,"visits":self.visits,
           "global_actions":self.global_actions,"total":self.total,
           "turn_chain":self.turn_chain,"last_forward_nochange":self.last_forward_nochange,
           "occupied_proxy":self.occupied_proxy,"evidence_enabled":self.evidence_enabled,
           "observed_pickups":self.observed_pickups,"observed_drops":self.observed_drops,
           "reversal_evidence_count":self.reversal_evidence_count,
           "last_pickup_total":self.last_pickup_total}
        return json.dumps(x,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True).encode("utf-8")

    @classmethod
    def restore(cls,raw):
        x=json.loads(raw)
        expected={"schema","edges","visits","global_actions","total","turn_chain",
                  "last_forward_nochange","occupied_proxy","evidence_enabled",
                  "observed_pickups","observed_drops","reversal_evidence_count",
                  "last_pickup_total"}
        if (set(x)!=expected or x["schema"]!=cls.SCHEMA
            or any(type(x[k]) is not bool for k in
               ("last_forward_nochange","occupied_proxy","evidence_enabled"))
            or any(type(x[k]) is not int for k in
               ("total","turn_chain","observed_pickups","observed_drops",
                "reversal_evidence_count","last_pickup_total"))
            or min(x["total"],x["turn_chain"],x["observed_pickups"],
                   x["observed_drops"],x["reversal_evidence_count"])<0
            or x["last_pickup_total"]<-1):
            raise ValueError("MG43_INVALID_PUBLIC_REVERSAL_COLD_SOURCE")
        z=cls(x["edges"],x["visits"],x["global_actions"],x["total"],
              x["turn_chain"],x["last_forward_nochange"],x["occupied_proxy"],
              x["evidence_enabled"],x["observed_pickups"],x["observed_drops"],
              x["reversal_evidence_count"],x["last_pickup_total"])
        if (z.checkpoint()!=raw or z.total!=sum(q["n"] for q in z.global_actions)
            or z.total!=sum(a["n"] for row in z.edges.values() for a in row.values())
            or any(a["n"]!=sum(a["next"].values())
                   for row in z.edges.values() for a in row.values())
            or z.last_pickup_total>z.total):
            raise ValueError("MG43_COLD_RETAINED_EFFECT_HISTORY_NOT_VERIFIED")
        return z

def reversal_episode(gym,entry,family,seed,prior,cap,public,original_digest):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG43_NOT_PINNED_ORIGINAL_FARAMA_WORLD")
        raw,_=env.reset(seed=seed)
        first=public(raw);mission=first["mission"]
        actor=(ReversalGuardNavigation() if prior is None
               else ReversalGuardNavigation.restore(prior))
        actor.begin_episode()
        start_n=actor.total;events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG43_ORIGINAL_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG43_INVALID_ORIGINAL_SOURCE_FEEDBACK")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG43_OBSERVED_SOURCE_REVERSAL_GUARD"})
            raw=raw2
            if term or trunc:break
        state=actor.checkpoint()
        if (ReversalGuardNavigation.restore(state).checkpoint()!=state
            or actor.total!=start_n+len(events)):
            raise ValueError("MG43_COLD_SOURCE_MEMORY_LOST")
        return ({"family":family,"role":ROLES[10],
                 "seed_dev_exposed":seed,
                 "public_start_sha256":original_digest(first),
                 "original_public_mission":mission,
                 "original_source_actions":len(events),
                 "prior_selected_source_samples":start_n,
                 "selected_source_samples_after":actor.total,
                 "original_terminal_goal_rewards":
                     sum(int(e["reward"]>0 and e["terminated"]) for e in events),
                 "observed_public_changes":
                     sum(e["before_sha256"]!=e["after_sha256"] for e in events),
                 "unique_public_views":len({e["before_sha256"] for e in events}),
                 "distinct_actions":len({e["action"] for e in events}),
                 "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
                 "observed_public_proxy_pickups":actor.observed_pickups,
                 "observed_public_proxy_drops":actor.observed_drops,
                 "observed_source_reversals":actor.reversal_evidence_count,
                 "source_events_sha256":original_digest(events),
                 "source_events":events},state)
    finally:
        env.close()

TARGET_TYPE={"key":5,"ball":6,"box":7}
TARGET_COLOR={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}

def public_exact_target_front(public):
    """Engineered, not learned: parse literal public pickup mission and front."""
    mission=public.get("mission")
    if type(mission) is not str:
        return None
    match=re.fullmatch(
        r"pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)",
        mission)
    if match is None:
        return None
    color,obj=match.groups()
    front=public["image"][3][5]
    return (str(TARGET_TYPE[obj])+":"+str(TARGET_COLOR[color])
            if front[0]==TARGET_TYPE[obj] and front[1]==TARGET_COLOR[color]
            else None)


class TargetActionValueNavigation(ReversalGuardNavigation):
    SCHEMA="mg43.original-selected-target-action-value-engineered-matcher.v1"

    def __init__(self,edges=None,visits=None,global_actions=None,total=0,
                 turn_chain=0,last_forward_nochange=False,occupied_proxy=False,
                 evidence_enabled=True,observed_pickups=0,observed_drops=0,
                 reversal_evidence_count=0,last_pickup_total=-1,
                 action_value_enabled=True,target_trials=None):
        super().__init__(edges,visits,global_actions,total,turn_chain,
                         last_forward_nochange,occupied_proxy,evidence_enabled,
                         observed_pickups,observed_drops,reversal_evidence_count,
                         last_pickup_total)
        self.action_value_enabled=action_value_enabled
        self.target_trials={} if target_trials is None else target_trials

    def choose(self, public):
        if self.pending is not None:
            raise ValueError("MG38_DOUBLE_CHOICE_BEFORE_ORIGINAL_FEEDBACK")
        key = digest(public)
        engineered_target = public_exact_target_front(public)
        first = int(key[:2], 16) % 7
        front = public["image"][3][5]
        row = self.edges.get(key, {})
        chosen = None
        best = None
        for offset in range(7):
            action = (first + offset) % 7
            cell = row.get(str(action))
            local_count = cell["n"] if cell else 0
            g = self.global_actions[action]
            g_count = g["n"]
            effect = (g["changed"] + 0.5) / (g_count + 1)
            novel = (g["novel"] + 0.5) / (g_count + 1)
            goal = (g["goals"] + 0.25) / (g_count + 1)
            if action == 2:
                # Forward public change is *not* assumed to prove locomotion.
                local_nochange = (0 if cell is None else
                                  (cell["n"] - cell["changed"]) / cell["n"])
                score = (2.3 + 1.7 / (1 + local_count)
                         + 1.0 * novel - 2.0 * local_nochange)
            elif action in (0, 1):
                # Rotations NEVER get credit for changing egocentric public SHA.
                # Rotation is still eligible after unsuccessful own forward.
                score = (0.4 + 0.4 / (1 + local_count)
                         + 2.5 * int(self.last_forward_nochange)
                         - 1.25 * self.turn_chain)
                if self.turn_chain >= 2:
                    score -= 8.0
            else:
                score = (0.6 + 1.7 / (1 + local_count) + 2.0 * goal
                         + 0.7 * effect - 0.1 * local_count)
                # Public object classes only; NOT a mission-target matcher.
                if action == 3 and front[0] in (5,6,7):
                    score += 2.2
                elif action == 5 and front[0] == 4:
                    score += 2.2
            # MG40 prospective public-action-effect proxy: bounded engineered
            # score adjustments. Not a learned semantic/action-rule discovery.
            if self.evidence_enabled and self.occupied_proxy:
                if action == 4 and front[0] == 1:
                    score += 8.0
                if action == 3 and front[0] in (5, 6, 7):
                    score -= 8.0
            # Keep reward tied only to selected empirical source consequences.
            if cell is not None:
                score += 2.0 * cell["goals"] / (1 + cell["n"])
            # MG42: only observed own pickup->drop reversals trigger a
            # bounded local anti-reversal penalty. No hidden inventory or
            # mission-target identity is used by this action scorer.
            if (action == 4 and self.occupied_proxy
                and self.reversal_evidence_count > 0
                and self.last_pickup_total >= 0
                and self.total - self.last_pickup_total <= 8):
                score -= 12.0
            # MG43: explicit, disclosed mission->public-front matcher prior.
            # Empirical correction uses only this agent's own selected effects.
            if action == 3 and engineered_target is not None:
                score += 4.0
                if self.action_value_enabled:
                    q=self.target_trials.get(engineered_target,{"attempts":0,"successes":0})
                    score += (3.0*(q["successes"]+1)/(q["attempts"]+2)
                              - 6.0*(q["attempts"]-q["successes"])/(q["attempts"]+2))
            if best is None or score > best:
                best = score
                chosen = action
        self.pending = (key, chosen)
        return chosen

    def observe_selected(self,before,action,after,reward,terminated):
        if self.pending!=(digest(before),action):
            raise ValueError("MG43_REJECT_OFFPOLICY_TARGET_EFFECT")
        key=public_exact_target_front(before) if action==3 else None
        success=(key is not None and before["direction"]==after["direction"]
                 and after["image"][3][5][0]==1)
        # Validates actual source-selected feedback and updates unchanged
        # MG42 empirical model, public occupancy proxy and reversal evidence.
        super().observe_selected(before,action,after,reward,terminated)
        if key is not None:
            c=self.target_trials.setdefault(key,{"attempts":0,"successes":0})
            c["attempts"]+=1
            c["successes"]+=int(success)

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG43_UNEXECUTED_ACTION_CANNOT_BE_SAVED")
        d={"schema":self.SCHEMA,"edges":self.edges,"visits":self.visits,
           "global_actions":self.global_actions,"total":self.total,
           "turn_chain":self.turn_chain,"last_forward_nochange":self.last_forward_nochange,
           "occupied_proxy":self.occupied_proxy,"evidence_enabled":self.evidence_enabled,
           "observed_pickups":self.observed_pickups,"observed_drops":self.observed_drops,
           "reversal_evidence_count":self.reversal_evidence_count,
           "last_pickup_total":self.last_pickup_total,
           "action_value_enabled":self.action_value_enabled,
           "target_trials":self.target_trials}
        return json.dumps(d,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True).encode("utf-8")

    @classmethod
    def restore(cls,raw):
        d=json.loads(raw)
        required={"schema","edges","visits","global_actions","total","turn_chain",
                  "last_forward_nochange","occupied_proxy","evidence_enabled",
                  "observed_pickups","observed_drops","reversal_evidence_count",
                  "last_pickup_total","action_value_enabled","target_trials"}
        if (set(d)!=required or d["schema"]!=cls.SCHEMA
            or any(type(d[k]) is not bool for k in
                   ("last_forward_nochange","occupied_proxy","evidence_enabled",
                    "action_value_enabled"))
            or any(type(d[k]) is not int for k in
                   ("total","turn_chain","observed_pickups","observed_drops",
                    "reversal_evidence_count","last_pickup_total"))
            or any(set(c)!={"attempts","successes"} or type(c["attempts"]) is not int
                   or type(c["successes"]) is not int
                   or not 0<=c["successes"]<=c["attempts"]
                   for c in d["target_trials"].values())):
            raise ValueError("MG43_INVALID_COLD_PUBLIC_ACTION_VALUE_SCHEMA")
        actor=cls(d["edges"],d["visits"],d["global_actions"],d["total"],
                  d["turn_chain"],d["last_forward_nochange"],d["occupied_proxy"],
                  d["evidence_enabled"],d["observed_pickups"],d["observed_drops"],
                  d["reversal_evidence_count"],d["last_pickup_total"],
                  d["action_value_enabled"],d["target_trials"])
        if (raw!=actor.checkpoint()
            or actor.total!=sum(x["n"] for x in actor.global_actions)
            or actor.total!=sum(x["n"] for row in actor.edges.values() for x in row.values())
            or any(c["n"]!=sum(c["next"].values())
                   for row in actor.edges.values() for c in row.values())
            or sum(v["attempts"] for v in actor.target_trials.values())>actor.total):
            raise ValueError("MG43_COLD_EMPIRICAL_SELECTED_TARGET_HISTORY_DIVERGED")
        return actor

class PublicSlotRelease(TargetActionValueNavigation):
    SCHEMA="mg44.public-effect-proxy-engineered-slot-release.v1"

    def __init__(self,release_enabled=True):
        super().__init__(action_value_enabled=True)
        self.release_enabled=release_enabled
        self.phase="seek"
        self.heading_origin=-1
        self.find_turns=0
        self.return_turns=0
        self.release_confirmed=False
        self.attempted_public_target_contexts=set()
        self.release_triggers=0
        self.confirmed_releases=0
        self.retried_public_targets=0

    def begin_episode(self):
        super().begin_episode()
        self.phase="seek"
        self.heading_origin=-1
        self.find_turns=0
        self.return_turns=0
        self.release_confirmed=False
        self.attempted_public_target_contexts=set()

    def _forced(self,public,action):
        if self.pending is not None:
            raise ValueError("MG44_SELECTED_ACTION_PENDING")
        self.pending=(digest(public),action)
        return action

    def choose(self,public):
        if self.pending is not None:
            raise ValueError("MG44_DUPLICATE_SOURCE_CHOICE")
        if not self.release_enabled:
            return super().choose(public)
        exact=public_exact_target_front(public)
        if (self.phase=="seek" and self.occupied_proxy
            and exact is not None and
            digest(public) not in self.attempted_public_target_contexts):
            self.phase="find_empty"
            self.heading_origin=public["direction"]
            self.find_turns=1
            self.release_confirmed=False
            self.release_triggers+=1
            self.attempted_public_target_contexts.add(digest(public))
            return self._forced(public,0)
        if self.phase=="find_empty":
            if self.occupied_proxy and public["image"][3][5][0]==1:
                return self._forced(public,4)
            if self.find_turns<4:
                self.find_turns+=1
                return self._forced(public,0)
            self.phase="recover"
            self.release_confirmed=False
            self.return_turns=0
        if self.phase=="recover":
            if public["direction"]!=self.heading_origin and self.return_turns<4:
                self.return_turns+=1
                return self._forced(public,1)
            was_released=self.release_confirmed
            self.phase="retry" if was_released else "seek"
        if self.phase=="retry":
            self.phase="seek"
            if exact is not None and not self.occupied_proxy:
                self.retried_public_targets+=1
                return self._forced(public,3)
        return super().choose(public)

    def observe_selected(self,before,action,after,reward,terminated):
        bf=before["image"][3][5]
        af=after["image"][3][5]
        released=(action==4 and self.phase=="find_empty"
                  and bf[0]==1 and af[0] in (5,6,7)
                  and before["direction"]==after["direction"])
        super().observe_selected(before,action,after,reward,terminated)
        if action==4 and self.phase=="find_empty":
            self.phase="recover"
            self.release_confirmed=released
            self.return_turns=0
            if released:self.confirmed_releases+=1

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG44_PENDING_SOURCE_ACTION_CANNOT_CHECKPOINT")
        d=json.loads(super().checkpoint())
        d["schema"]=self.SCHEMA
        d.update({"release_enabled":self.release_enabled,
                  "phase":self.phase,
                  "heading_origin":self.heading_origin,
                  "find_turns":self.find_turns,"return_turns":self.return_turns,
                  "release_confirmed":self.release_confirmed,
                  "attempted_public_target_contexts":sorted(self.attempted_public_target_contexts),
                  "release_triggers":self.release_triggers,
                  "confirmed_releases":self.confirmed_releases,
                  "retried_public_targets":self.retried_public_targets})
        return json.dumps(d,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True).encode("utf-8")

    @classmethod
    def restore(cls,raw):
        d=json.loads(raw)
        extra=("release_enabled","phase","heading_origin","find_turns",
               "return_turns","release_confirmed","attempted_public_target_contexts",
               "release_triggers","confirmed_releases","retried_public_targets")
        if (d.get("schema")!=cls.SCHEMA
            or not all(k in d for k in extra)
            or d["phase"] not in ("seek","find_empty","recover","retry")
            or type(d["release_enabled"]) is not bool
            or type(d["release_confirmed"]) is not bool
            or any(type(d[k]) is not int or d[k]<0 for k in
                   ("find_turns","return_turns","release_triggers",
                    "confirmed_releases","retried_public_targets"))
            or type(d["heading_origin"]) is not int
            or d["heading_origin"] not in (-1,0,1,2,3)
            or type(d["attempted_public_target_contexts"]) is not list
            or d["attempted_public_target_contexts"]!=sorted(
                set(d["attempted_public_target_contexts"]))):
            raise ValueError("MG44_COLD_SOURCE_RELEASE_FSM_INVALID")
        base_data={k:v for k,v in d.items() if k not in extra}
        base_data["schema"]=TargetActionValueNavigation.SCHEMA
        base=TargetActionValueNavigation.restore(json.dumps(
            base_data,sort_keys=True,separators=(",",":"),
            ensure_ascii=True).encode("utf-8"))
        out=cls.__new__(cls)
        out.__dict__.update(base.__dict__)
        for k in extra:
            setattr(out,k,set(d[k]) if k=="attempted_public_target_contexts"
                    else d[k])
        if out.checkpoint()!=raw:
            raise ValueError("MG44_COLD_PUBLIC_SELECTED_FSM_CHECKPOINT_DIVERGED")
        return out


def public_release_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG44_WRONG_ORIGINAL_FARAMA_SOURCE")
        raw,_=env.reset(seed=seed)
        first=public(raw)
        mission=first["mission"]
        actor=(PublicSlotRelease(release_enabled=enabled) if prior is None
               else PublicSlotRelease.restore(prior))
        if actor.release_enabled is not enabled:
            raise ValueError("MG44_COLD_RELEASE_ABLATION_ROLE_CHANGE")
        actor.begin_episode()
        prior_n=actor.total
        triggers_before=actor.release_triggers
        releases_before=actor.confirmed_releases
        retries_before=actor.retried_public_targets
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG44_ORIGINAL_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG44_ORIGINAL_SOURCE_SELECTED_FEEDBACK_INVALID")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),
                "external_actions":0,
                "policy_status":"MG44_PUBLIC_RELEASE_ON" if enabled
                                else "MG44_IDENTICAL_RELEASE_DISABLED"})
            raw=raw2
            if term or trunc:break
        raw_ck=actor.checkpoint()
        if (PublicSlotRelease.restore(raw_ck).checkpoint()!=raw_ck
            or actor.total!=prior_n+len(events)):
            raise ValueError("MG44_ORIGINAL_PUBLIC_SOURCE_COLD_FSM_NOT_RETAINED")
        return ({"family":family,
                 "role":ROLES[13] if enabled else ROLES[14],
                 "seed_dev_exposed":seed,
                 "public_start_sha256":original_digest(first),
                 "original_public_mission":mission,
                 "original_source_actions":len(events),
                 "prior_selected_source_samples":prior_n,
                 "selected_source_samples_after":actor.total,
                 "original_terminal_goal_rewards":
                     sum(int(e["reward"]>0 and e["terminated"]) for e in events),
                 "observed_public_changes":
                     sum(e["before_sha256"]!=e["after_sha256"] for e in events),
                 "unique_public_views":len({e["before_sha256"] for e in events}),
                 "distinct_actions":len({e["action"] for e in events}),
                 "checkpoint_sha256":hashlib.sha256(raw_ck).hexdigest(),
                 "source_events_sha256":original_digest(events),
                 "release_triggers":actor.release_triggers-triggers_before,
                 "release_actual_public_effects":actor.confirmed_releases-releases_before,
                 "release_retry_target_attempts":actor.retried_public_targets-retries_before,
                 "source_events":events},raw_ck)
    finally:
        env.close()

def action_value_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG43_NOT_PINNED_ORIGINAL_SOURCE_ENV")
        raw,_=env.reset(seed=seed)
        first=public(raw)
        mission=first["mission"]
        actor=(TargetActionValueNavigation(action_value_enabled=enabled)
               if prior is None else TargetActionValueNavigation.restore(prior))
        if actor.action_value_enabled is not enabled:
            raise ValueError("MG43_COLD_ACTION_VALUE_ABLATION_ROLE_CHANGED")
        actor.begin_episode()
        n0=actor.total
        trials_before=sum(v["attempts"] for v in actor.target_trials.values())
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG43_REAL_SOURCE_MISSION_CHANGED")
            action=actor.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG43_REAL_ORIGINAL_SOURCE_FEEDBACK_INVALID")
            actor.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG43_PUBLIC_TARGET_LEARNED_VALUE_ON" if enabled
                                else "MG43_PUBLIC_TARGET_VALUE_DISABLED"})
            raw=raw2
            if term or trunc:break
        memory=actor.checkpoint()
        if (TargetActionValueNavigation.restore(memory).checkpoint()!=memory
            or actor.total!=n0+len(events)):
            raise ValueError("MG43_REAL_COLD_SELECTED_HISTORY_MISSING")
        return ({"family":family,"role":ROLES[11] if enabled else ROLES[12],
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
                 "checkpoint_sha256":hashlib.sha256(memory).hexdigest(),
                 "source_events_sha256":original_digest(events),
                 "selected_engineered_target_trials":sum(v["attempts"] for v in actor.target_trials.values())-trials_before,
                 "source_events":events},memory)
    finally:
        env.close()

def evidence_episode(gym,entry,family,seed,prior,cap,public,original_digest,enabled):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG43_INVALID_ORIGINAL_ENVIRONMENT")
        raw,_=env.reset(seed=seed)
        first=public(raw)
        mission=first["mission"]
        model=(EvidenceNavigation(evidence_enabled=enabled)
               if prior is None else EvidenceNavigation.restore(prior))
        if model.evidence_enabled is not enabled:
            raise ValueError("MG43_EVIDENCE_ABLATION_STATE_DRIFT")
        model.begin_episode()
        start_n=model.total
        events=[]
        for n in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=mission:
                raise ValueError("MG43_PUBLIC_MISSION_DRIFT")
            action=model.choose(before)
            raw2,reward,term,trunc,_=env.step(action)
            after=public(raw2)
            if (after["mission"]!=mission or type(term) is not bool
                or type(trunc) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG43_ORIGINAL_SELECTED_SOURCE_FEEDBACK_INVALID")
            model.observe_selected(before,action,after,float(reward),term)
            events.append({"index":n,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":term,"truncated":trunc,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG43_PUBLIC_EFFECT_EVIDENCE_ON" if enabled
                                else "MG43_PUBLIC_EFFECT_EVIDENCE_ABLATION"})
            raw=raw2
            if term or trunc:
                break
        state=model.checkpoint()
        if (EvidenceNavigation.restore(state).checkpoint()!=state
            or model.total!=start_n+len(events)):
            raise ValueError("MG43_COLD_PUBLIC_SOURCE_HISTORY_LOSS")
        return ({"family":family,"role":ROLES[8] if enabled else ROLES[9],
                 "seed_dev_exposed":seed,"public_start_sha256":original_digest(first),
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
    finally:
        env.close()

def synthetic_source_preflight():
    import inspect
    p=frozen()
    from mg43_public_target_action_value import (
        TargetActionValueNavigation as OriginalMG43,
        public_exact_target_front as OriginalMatcher)
    if (inspect.getsource(TargetActionValueNavigation.choose)
        !=inspect.getsource(OriginalMG43.choose)
        or inspect.getsource(public_exact_target_front)
        !=inspect.getsource(OriginalMatcher)):
        raise ValueError("MG44_ORIGINAL_MG43_TARGET_VALUE_POLICY_CHANGED")
    initial={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
             "direction":0,"mission":"pick up the red box"}
    initial["image"][3][5]=[7,0,0]
    cleared=json.loads(json.dumps(initial))
    cleared["image"][3][5]=[1,0,0]
    # Test own public-effects-only release trigger; no original env object.
    a=PublicSlotRelease(release_enabled=True)
    a.pending=(digest(initial),3)
    a.observe_selected(initial,3,cleared,0.0,False)
    if not a.occupied_proxy:
        raise ValueError("MG44_SELECTED_PUBLIC_OCCUPIED_PROXY_NOT_SUPPORTED")
    act=a.choose(initial)
    if act!=0 or a.phase!="find_empty" or a.heading_origin!=0:
        raise ValueError("MG44_EXACT_PUBLIC_TARGET_OCCUPIED_TRIGGER_FAILED")
    left=json.loads(json.dumps(cleared));left["direction"]=3
    a.observe_selected(initial,act,left,0.0,False)
    drop_action=a.choose(left)
    if drop_action!=4:
        raise ValueError("MG44_NOT_RELEASE_AT_PUBLIC_EMPTY_FRONT")
    after_drop=json.loads(json.dumps(left))
    after_drop["image"][3][5]=[7,0,0]
    a.observe_selected(left,4,after_drop,0.0,False)
    if a.occupied_proxy or a.confirmed_releases!=1:
        raise ValueError("MG44_PUBLIC_SOURCE_RELEASE_EFFECT_NOT_DETECTED")
    returned=a.choose(after_drop)
    if returned!=1:
        raise ValueError("MG44_NOT_RECOVERING_PUBLIC_ORIGINAL_HEADING")
    after_turn=json.loads(json.dumps(initial))
    a.observe_selected(after_drop,returned,after_turn,0.0,False)
    pick=a.choose(after_turn)
    if pick!=3 or a.retried_public_targets!=1:
        raise ValueError("MG44_CANNOT_RETRY_EXACT_PUBLIC_TARGET_AFTER_RELEASE")
    a.observe_selected(after_turn,3,cleared,1.0,True)
    saved=a.checkpoint()
    if PublicSlotRelease.restore(saved).checkpoint()!=saved:
        raise ValueError("MG44_PUBLIC_EFFECT_FSM_COLD_RESTORE_FAILED")
    a.begin_episode()
    if a.phase!="seek" or a.release_triggers!=1 or a.confirmed_releases!=1:
        raise ValueError("MG44_EPISODE_RESET_DROPPED_RETAINED_SELECTED_HISTORY")
    off=PublicSlotRelease(release_enabled=False)
    old=OriginalMG43()
    disabled_choice=off.choose(initial)
    original_choice=old.choose(initial)
    if disabled_choice!=original_choice:
        raise ValueError("MG44_RELEASE_OFF_NOT_IDENTICAL_MG43_SOURCE_POLICY")
    off.pending=None
    old.pending=None
    print("MG44_CROSS_OS_FROZEN_ORIGINAL_POLICY_IDENTITY_AND_PUBLIC_RELEASE_PREFLIGHT_PASS")
    return p

def summarize(rows):
    totals={}
    for family in FAMILIES:
        totals[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG43_INCOMPLETE_TRIPLE_COLD_ORIGINAL_SOURCE")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG43_COLD_SOURCE_MEMORY_NOT_RETAINED")
            action_hist=[0]*7
            seen=collections.Counter()
            goal_episodes=0
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG43_ORIGINAL_EVENT_SOURCE_HASH_CHANGED")
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
                raise ValueError("MG43_ORIGINAL_SOURCE_ACTION_DENOMINATOR_MISMATCH")
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
        raise ValueError("MG43_FARAMA_SOURCE_NOT_FROM_PINNED_ROOT")
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
                    ep,state=original_mg40_evidence_episode(gym,registry[family],family,
                                              seed,memory[role],192,public,
                                              original_digest,role==ROLES[8])
                elif role==ROLES[10]:
                    ep,state=original_mg42_reversal_episode(
                        gym,registry[family],family,seed,memory[role],192,
                        public,original_digest)
                elif role in (ROLES[11],ROLES[12]):
                    ep,state=action_value_episode(
                        gym,registry[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[11])
                elif role in (ROLES[13],ROLES[14]):
                    ep,state=public_release_episode(
                        gym,registry[family],family,seed,memory[role],192,
                        public,original_digest,role==ROLES[13])
                else:
                    raise ValueError("MG43_UNAUTHORIZED_ORIGINAL_ROLE")
                ep["role"]=role
                starts.append(ep["public_start_sha256"])
                if role!=ROLES[-1]:
                    memory[role]=state
                result.append(ep)
            if len(set(starts))!=1:
                raise ValueError("MG43_NOT_MATCHED_ORIGINAL_SEED_RESET")
    if len(result)!=192 or any(not (1<=x["original_source_actions"]<=192)
                                for x in result):
        raise ValueError("MG44_INCOMPLETE_192_EPISODES")
    table=summarize(result)
    unfamiliar=FAMILIES[1:]
    candidate=ROLES[13]
    controls=(ROLES[14],ROLES[11],ROLES[12],ROLES[10],ROLES[8],ROLES[9],
              ROLES[6],ROLES[7],ROLES[4],ROLES[5])
    roles=(candidate,*controls)
    effects={role:sum(table[f][role]["target_pick_effect"] for f in unfamiliar)
             for role in roles}
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in unfamiliar)
           for role in roles}
    genuine_releases={role:sum(ep.get("release_actual_public_effects",0)
                           for ep in result if ep["role"]==role and
                           ep["family"] in unfamiliar)
                      for role in (candidate,ROLES[14])}
    release_triggers=sum(ep.get("release_triggers",0) for ep in result
                          if ep["role"]==candidate and ep["family"] in unfamiliar)
    retry_counts=sum(ep.get("release_retry_target_attempts",0) for ep in result
                      if ep["role"]==candidate and ep["family"] in unfamiliar)
    positive_families=sum(table[f][candidate]["positive_goal_episodes"]>0
                          for f in unfamiliar)
    difficult=any(table[f][candidate]["positive_goal_episodes"]>0
                  for f in FAMILIES[1:3])
    supported=(genuine_releases[candidate]>=1 and effects[candidate]>=1
               and positive_families>=2 and difficult
               and all(goals[candidate]>goals[role] for role in controls))
    label=p["frozen_dev_filter"]
    source={"schema":"itd02.mg44.original-public-effect-release-before-target.dev-source.v1",
        "classification":label["pass"] if supported else label["fail"],
        "original_192_episodes":result,"original_selected_action_count":
            sum(x["original_source_actions"] for x in result),
        "per_family_per_role":table,
        "paired_release_enabled_disabled_controls":{
            "target_effects":effects,"positive_goals":goals,
            "release_triggers_at_public_target":release_triggers,
            "actual_original_public_release_effects":genuine_releases,
            "target_retries_after_release":retry_counts,
            "candidate_positive_unfamiliar_families":positive_families,
            "candidate_positive_target_effects":effects[candidate],
            "candidate_positive_unlock_or_blocked":difficult,
            "filter_supported":supported},
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
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--native-go",type=Path)
    parser.add_argument("--control-root",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--compare",nargs=2,type=Path)
    args=parser.parse_args()
    p=frozen()
    if args.preflight:
        synthetic_source_preflight()
        return
    if args.compare:
        a,b=[json.loads(x.read_text(encoding="utf8")) for x in args.compare]
        if (a.get("source")!=b.get("source")
            or a.get("canonical_source_sha256")!=b.get("canonical_source_sha256")
            or a.get("canonical_source_sha256")!=digest(a["source"])
            or len(a["source"]["original_192_episodes"])!=192
            or a["source"]["scientific_first_use"] is not False
            or a["source"]["zero_external_actions"] is not True):
            raise ValueError("MG43_TWO_ORIGINAL_PROCESSES_NOT_MATCHED")
        print("MG43_TWO_INDEPENDENT_ORIGINAL_SOURCE_PROCESSES_IDENTICAL",
              a["canonical_source_sha256"])
        print("MG43_FROZEN_DEV_CLASSIFICATION",a["source"]["classification"])
        print("MG43_PAIRED_EVIDENCE_ON_OFF",json.dumps(
              a["source"]["paired_release_enabled_disabled_controls"],sort_keys=True))
        return
    if any(x is None for x in (args.source_root,args.native_go,args.control_root,args.output)):
        parser.error("require --source-root, --native-go, --control-root, --output")
    start=time.perf_counter()
    try:
        r=execute(args.source_root,args.native_go,args.control_root,p)
    except Exception as e:
        r={"schema":"itd02.mg44.original-public-effect-release-before-target.dev-source.v1",
           "classification":"MG43_ORIGINAL_SOURCE_BLOCKED_NO_SCIENCE",
           "error_type":type(e).__name__,"error":str(e),
           "trace_tail":traceback.format_exc().splitlines()[-15:]}
    r["host_wall_time_outside_canonical_source_seconds"]=round(time.perf_counter()-start,6)
    args.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf8")
    cls=r.get("classification",r.get("source",{}).get(
        "classification","MG43_MISSING_ORIGINAL_CLASSIFICATION"))
    print("MG43_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(r.get("error","MG43_UNKNOWN_ORIGINAL_SOURCE_BLOCKER"))
    print("MG43_ORIGINAL_SOURCE_SHA256",r["canonical_source_sha256"])

if __name__=="__main__":
    main()

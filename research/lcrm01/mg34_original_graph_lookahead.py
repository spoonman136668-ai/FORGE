#!/usr/bin/env python3
"""MG34 fresh exposed DEV original MiniGrid public-history graph frontier.

Independent exploratory data-acquisition policy, NOT a native model replacement,
sealed test, science claim, or production rollout. Unchanged MG19 sources only.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,random,subprocess,time,traceback
from pathlib import Path
from mg31_original_public_exploration import (
    FAMILIES,UPSTREAM,explore_episode,selected_effect,digest,encode
)
from mg32_original_public_coverage import classify_event
from mg33_original_frontier_dev import Frontier as OldFrontier, frontier_episode as old_frontier_episode, context

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg34_original_graph_lookahead_prereg.json"
PARENT="d5837d6601701d439ace812010126bb04f012d5e"
FREEZE="964555b2605b45a88d3b902490ba40b82132baa8"
ROLES=("wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
       "public_graph_lookahead_candidate","mg33_public_history_frontier_unchanged",
       "generic_full_public_novelty_explorer","strong_action_only_ucb_explorer",
       "seeded_uniform_random")
SEEDS=((983101,983103,983107),(983201,983203,983207),
       (983301,983303,983307),(983401,983403,983407))


def git(*args):
    return subprocess.run(["git",*args],capture_output=True,text=True,
                          check=False,cwd=HERE.parents[1])


def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    d=p["design"]; f=d["frozen_policy_coefficients"]
    if (p.get("schema")!="itd02.mg34.original-public-graph-lookahead-fresh-development.v1"
        or p.get("phase")!="PROSPECTIVE_PREREG_FROZEN_BEFORE_EXECUTABLE_AND_NEW_ORIGINAL_ACTIONS"
        or p["parent"]["forge_mg33"]!=PARENT
        or p["source_pins"]["farama"]!=UPSTREAM
        or tuple(d["families"])!=FAMILIES
        or tuple(d["roles"])!=ROLES
        or tuple(tuple(s) for s in d["original_source_dev_seeds"])!=SEEDS
        or d["action_budget_each_episode"]!=192
        or d["source_process_reproductions"]!=2
        or d["zero_fit"] is not True
        or (f["depth_cap"],f["untried_bonus"],f["untried_repetition_penalty"],
            f["frontier_node_bonus"],f["reverse_visit_bonus"],
            f["path_depth_penalty"],f["edge_uncertainty_bonus"],
            f["self_loop_penalty"])!=(3,360,3,210,140,25,60,160)
        or not all(p["prohibitions"].values())):
        raise ValueError("MG34_FROZEN_DESIGN_DRIFT")
    known=set(d["known_exposed_seeds"])
    selected=[s for group in SEEDS for s in group]
    if len(selected)!=12 or len(set(selected))!=12 or known.intersection(selected):
        raise ValueError("MG34_PRIOR_SEED_COLLISION")
    if git("merge-base","--is-ancestor",PARENT,"HEAD").returncode:
        raise ValueError("MG34_WRONG_PARENT")
    if git("merge-base","--is-ancestor",FREEZE,"HEAD").returncode:
        raise ValueError("MG34_NOT_FROZEN_BEFORE_EXECUTABLE")
    for seed in selected:
        prior=git("grep","-n","-w",str(seed),PARENT,"--","research/lcrm01","docs/research")
        if prior.returncode==0:
            raise ValueError("MG34_PRIOR_EXPOSED_SOURCE:"+str(seed))
        if prior.returncode!=1:
            raise ValueError("MG34_PRIOR_SOURCE_CUSTODY_UNAVAILABLE")
    return p


class Lookahead(OldFrontier):
    """Bounded search on own *observed* original-public context/action graph.

    All edges come from actual previously selected actions. Never infers global
    location, inspects private MiniGrid state or programs a door/key action.
    """
    def choose(self,frame):
        state=context(frame)
        start=int(state[:2],16)%7
        row=self.edges.get(state,{})
        # Probe unattempted public-context actions before following old edges.
        for offset in range(7):
            action=(start+offset)%7
            if str(action) not in row:
                return action
        # Bounded breadth-first search over only genuinely observed successor
        # edges to source-public contexts with as-yet untried local actions.
        queue=collections.deque([(state,0,None)])
        seen={state}
        winner=None
        while queue:
            current,depth,first=queue.popleft()
            if depth>=3:
                continue
            edges=self.edges.get(current,{})
            for action in range(7):
                cell=edges.get(str(action))
                if not cell:
                    continue
                for successor in sorted(cell["next"]):
                    if successor in seen:
                        continue
                    seen.add(successor)
                    new_first=action if first is None else first
                    d=depth+1
                    frontier=len(self.edges.get(successor,{}))<7
                    score=(210*int(frontier)+140//(1+self.visits.get(successor,0))
                           +60//(1+cell["n"])-25*d
                           -160*int(successor==current))
                    if frontier:
                        candidate=(score,-d,-((new_first-start)%7),-new_first)
                        if winner is None or candidate>winner[0]:
                            winner=(candidate,new_first)
                    if d<3:
                        queue.append((successor,d,new_first))
        if winner:
            return winner[1]
        # All nearby actions are known: revisit the least saturated empirical
        # outgoing edge; discount measured no-effect transitions.
        best=None;chosen=None
        for offset in range(7):
            action=(start+offset)%7
            cell=row[str(action)]
            destinations=cell["next"]
            minvis=min((self.visits.get(k,0) for k in destinations),default=0)
            n=cell["n"]
            score=(140//(1+minvis)+60//(1+n)
                   -160*cell["stall"]//(n+1)-3*n)
            if best is None or score>best:
                best=score;chosen=action
        return chosen

    def checkpoint(self):
        return encode({"schema":"mg34.public-history-observed-graph-lookahead.v1",
                       "edges":self.edges,"visits":self.visits,"total":self.total})

    @classmethod
    def restore(cls,raw):
        d=json.loads(raw)
        if set(d)!={"schema","edges","visits","total"} or d["schema"]!="mg34.public-history-observed-graph-lookahead.v1":
            raise ValueError("MG34_COLD_SCHEMA")
        obj=cls(d["edges"],d["visits"],d["total"])
        if obj.checkpoint()!=raw or obj.total!=sum(
            cell["n"] for row in obj.edges.values() for cell in row.values()):
            raise ValueError("MG34_COLD_GRAPH_STATE_LOSS")
        return obj


def frontier_episode(gym,entry,family,seed,prior,cap,public,og_digest):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG34_WRONG_UPSTREAM_SEVEN_ACTION_ENV")
        raw,_=env.reset(seed=seed)
        first=public(raw);initial=og_digest(first);mission=first["mission"]
        learner=Lookahead() if prior is None else Lookahead.restore(prior)
        beginning=learner.total
        events=[]
        for step in range(1,cap+1):
            b=public(raw)
            if b["mission"]!=mission:
                raise ValueError("MG34_SOURCE_MISSION_DRIFT")
            a=learner.choose(b)
            assert type(a) is int and 0<=a<7
            raw2,reward,term,trunc,_=env.step(a)
            after=public(raw2)
            if after["mission"]!=mission or type(term) is not bool or type(trunc) is not bool or not math.isfinite(float(reward)):
                raise ValueError("MG34_SOURCE_ACTION_FEEDBACK_INVALID")
            learner.observe(b,a,after,float(reward),term)
            events.append({"index":step,"before":b,"action":a,"after":after,
                "mission":mission,"policy_status":"MG34_PUBLIC_HISTORY_GRAPH_SELECTED",
                "reward":float(reward),"terminated":term,"truncated":trunc,
                "before_sha256":og_digest(b),"after_sha256":og_digest(after),
                "external_actions":0})
            raw=raw2
            if term or trunc:break
        state=learner.checkpoint()
        if Lookahead.restore(state).checkpoint()!=state or learner.total!=beginning+len(events):
            raise ValueError("MG34_COLD_SELECTED_MEMORY_FAILED")
        row={"family":family,"seed_dev_exposed":seed,"role":ROLES[2],
             "public_start_sha256":initial,"original_public_mission":mission,
             "original_source_actions":len(events),"prior_selected_source_samples":beginning,
             "selected_source_samples_after":learner.total,
             "original_terminal_goal_rewards":sum(int(e["reward"]>0 and e["terminated"]) for e in events),
             "observed_public_changes":sum(e["before_sha256"]!=e["after_sha256"] for e in events),
             "unique_public_views":len({e["before_sha256"] for e in events}),
             "distinct_actions":len({e["action"] for e in events}),
             "checkpoint_sha256":hashlib.sha256(state).hexdigest(),
             "source_events_sha256":og_digest(events),"source_events":events}
        return row,state
    finally:
        env.close()


def metrics_for(results):
    matrix={}
    for family in FAMILIES:
        matrix[family]={}
        for role in ROLES:
            group=[r for r in results if r["family"]==family and r["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (0,None):
                raise ValueError("MG34_MISSING_ROLE_EPISODES_OR_NOT_COLD_STARTED")
            if role!=ROLES[-1]:
                for previous,current in zip(group,group[1:]):
                    if previous["selected_source_samples_after"]!=current["prior_selected_source_samples"]:
                        raise ValueError("MG34_NOT_COLD_RETAINED_BETWEEN_SEEDS")
            tally=collections.Counter()
            for r in group:
                for e in r["source_events"]:
                    tally.update(classify_event(e))
                    tally.update(selected_effect(e))
            matrix[family][role]={k:tally[k] for k in
               ("actions","target_front","target_pick_attempt","target_disappearance",
                "door_front","door_toggle_attempt","door_open","positive_goal",
                "no_public_change","exact_mission_target_public_disappearance",
                "real_public_locked_door_open","original_positive_terminal_goal")}
            matrix[family][role]["episodes"]=3
            matrix[family][role]["positive_goal_episodes"]=sum(r["original_terminal_goal_rewards"]>0 for r in group)
    return matrix


def execute(root,go,p):
    import gymnasium as gym
    import minigrid
    from mg17_original_family_source_qual import frozen as upstream_frozen,attest_source,public,digest as original_digest
    from mg21_original_development import one_episode,ROLES as old_roles
    if not Path(minigrid.__file__).resolve().is_relative_to(root.resolve()):
        raise ValueError("MG34_NOT_ORIGINAL_PINNED_UPSTREAM")
    source=upstream_frozen()
    attest_source(root,source)
    registry={v["id"]:v["entry_point"] for v in source["families"]}
    results=[]
    for family,seeds in zip(FAMILIES,SEEDS):
        old_states={role:None for role in ROLES}
        for seed in seeds:
            rows=[]
            for role in ROLES:
                if role in ROLES[:2] or role==ROLES[-1]:
                    native_role=(old_roles[0] if role==ROLES[0] else
                                 old_roles[1] if role==ROLES[1] else old_roles[3])
                    row,_,state=one_episode(family,seed,native_role,192,
                                             old_states[role],go,registry[family])
                    row["role"]=role
                elif role==ROLES[2]:
                    row,state=frontier_episode(gym,registry[family],family,seed,
                                               old_states[role],192,public,original_digest)
                elif role==ROLES[3]:
                    row,state=old_frontier_episode(gym,registry[family],family,seed,
                                                   old_states[role],192,public,original_digest)
                    row["role"]=role
                else:
                    mode="full" if role==ROLES[4] else "action"
                    row,state=explore_episode(gym,registry[family],family,seed,mode,
                                              old_states[role],192,public,original_digest)
                if role!=ROLES[-1]:
                    old_states[role]=state
                rows.append(row);results.append(row)
            if len({r["public_start_sha256"] for r in rows})!=1:
                raise ValueError("MG34_UNEQUAL_ORIGINAL_START")
    if len(results)!=84 or not all(1<=r["original_source_actions"]<=192 for r in results):
        raise ValueError("MG34_INCOMPLETE_ORIGINAL_WORLD_MATRIX")
    metrics=metrics_for(results)
    # Distinct full before-action original public observation contexts are
    # repeat-resistant; they are NOT evidence of unique world coordinates.
    for family in FAMILIES:
        for role in ROLES:
            group=(r for r in results if r["family"]==family and r["role"]==role)
            target_contexts=set()
            locked_contexts=set()
            for row in group:
                for event in row["source_events"]:
                    from_public=classify_event(event)
                    if from_public["target_front"]:
                        target_contexts.add(event["before_sha256"])
                    if from_public["door_front"]:
                        locked_contexts.add(event["before_sha256"])
            metrics[family][role]["distinct_target_front_contexts"]=len(target_contexts)
            metrics[family][role]["distinct_locked_door_front_contexts"]=len(locked_contexts)
    unfamiliar=FAMILIES[1:]
    candidate=ROLES[2]
    controls=ROLES[3:6]
    distinct_candidate=sum(metrics[f][candidate]["distinct_target_front_contexts"] for f in unfamiliar)
    distinct_controls={role:sum(metrics[f][role]["distinct_target_front_contexts"] for f in unfamiliar)
                       for role in controls}
    candidate_goals=sum(metrics[f][candidate]["positive_goal_episodes"] for f in unfamiliar)
    control_goals={role:sum(metrics[f][role]["positive_goal_episodes"] for f in unfamiliar)
                   for role in controls}
    candidate_effects=sum(metrics[f][candidate]["target_disappearance"] for f in unfamiliar)
    candidate_goal_families=sum(metrics[f][candidate]["positive_goal_episodes"]>0 for f in unfamiliar)
    supported=(distinct_candidate>max(distinct_controls.values())
               and all(candidate_goals>=v+1 for v in control_goals.values())
               and candidate_effects>=1 and candidate_goal_families>=2)
    classification=p["development_success_filter"]["pass_classification" if supported else "fail_classification"]
    result={"schema":"itd02.mg34.original-public-graph-lookahead-dev-source.v1",
        "classification":classification,
        "original_farama_source":UPSTREAM,"source_parent":PARENT,
        "exposed_dev_seeds":[list(x) for x in SEEDS],
        "original_84_episodes":results,"per_family_per_role":metrics,
        "original_selected_action_count":sum(r["original_source_actions"] for r in results),
        "lookahead_development_filter":{"distinct_target_contexts_candidate":distinct_candidate,
            "distinct_target_contexts_controls":distinct_controls,
            "positive_goals_candidate":candidate_goals,
            "positive_goals_controls":control_goals,
            "target_effects_candidate":candidate_effects,
            "goal_positive_unfamiliar_family_count":candidate_goal_families,
            "filter_supported":supported},
        "zero_external_actions":True,"scientific_first_use":False,
        "mg28_live_native_rollout_permitted":False,
        "accepted_models_or_controllers_modified":False,
        "native_resource_parity_qualified":False}
    return {"schema":result["schema"],"source":result,
            "canonical_source_sha256":digest(result)}


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
        source={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
                "direction":0,"mission":"pick up the red box"}
        nxt={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
             "direction":1,"mission":"pick up the red box"}
        actor=Lookahead()
        for _ in range(14):
            a=actor.choose(source); actor.observe(source,a,nxt,0.0,False)
        raw=actor.checkpoint()
        assert Lookahead.restore(raw).checkpoint()==raw and actor.total==14
        assert opt.source_root is None and opt.native_go is None and opt.output is None
        print("MG34_FROZEN_FRESH_SOURCE_AND_GRAPH_LOOKAHEAD_COLD_PREFLIGHT_PASS")
        return
    if opt.compare:
        a,b=[json.loads(Path(x).read_text()) for x in opt.compare]
        if (a.get("source")!=b.get("source") or
            a.get("canonical_source_sha256")!=b.get("canonical_source_sha256") or
            a.get("canonical_source_sha256")!=digest(a["source"]) or
            len(a["source"]["original_84_episodes"])!=84 or
            a["source"]["scientific_first_use"] is not False or
            a["source"]["zero_external_actions"] is not True):
            raise ValueError("MG34_TWO_AUTHENTIC_ORIGINAL_PROCESSES_DIFFER")
        print("MG34_INDEPENDENT_SOURCE_PROCESSES_PASS",a["canonical_source_sha256"])
        print("MG34_FROZEN_DEVELOPMENT_CLASSIFICATION",a["source"]["classification"])
        print("MG34_FRONTIER_EXPOSURE_AND_GOAL_METRICS",
              json.dumps(a["source"]["lookahead_development_filter"],sort_keys=True))
        return
    if not all((opt.source_root,opt.native_go,opt.output)):
        parser.error("require --source-root --native-go --output or --compare")
    started=time.perf_counter()
    try:
        envelope=execute(opt.source_root,opt.native_go,p)
    except Exception as exc:
        envelope={"schema":"itd02.mg34.original-public-history-frontier-dev-source.v1",
            "classification":"MG34_ORIGINAL_SOURCE_BLOCKED_NO_SCIENCE",
            "error_type":type(exc).__name__,"error":str(exc),
            "trace_tail":traceback.format_exc().splitlines()[-12:]}
    envelope["host_wall_time_outside_canonical_source_seconds"]=round(time.perf_counter()-started,6)
    opt.output.write_text(json.dumps(envelope,sort_keys=True,indent=2)+"\n")
    classification=envelope.get("classification",
                envelope.get("source",{}).get("classification","MG34_MISSING_CLASSIFICATION_BLOCKED"))
    print("MG34_ORIGINAL_SOURCE_CLASSIFICATION",classification)
    if "BLOCKED" in classification:
        raise ValueError(envelope.get("error","MG34_SOURCE_EXECUTION_FAILED"))
    print("MG34_ORIGINAL_SOURCE_SHA256",envelope["canonical_source_sha256"])


if __name__=="__main__":
    main()

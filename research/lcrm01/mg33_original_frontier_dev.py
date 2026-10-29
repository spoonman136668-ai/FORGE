#!/usr/bin/env python3
"""MG33 fresh exposed DEV original MiniGrid public-history graph frontier.

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

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg33_original_frontier_dev_prereg.json"
PARENT="4ba7933b988860ac7f7dd53ec5506f80d0a43db1"
FREEZE="61488cfe6cf68f0a601f42afc078c16a6476affc"
ROLES=("wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
       "public_history_graph_frontier","generic_full_public_novelty_explorer",
       "strong_action_only_ucb_explorer","seeded_uniform_random")
SEEDS=((973101,973103,973107),(973201,973203,973207),
       (973301,973303,973307),(973401,973403,973407))


def git(*args):
    return subprocess.run(["git",*args],capture_output=True,text=True,
                          check=False,cwd=HERE.parents[1])


def freeze():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    d=p["design"]; f=d["frozen_frontier_scoring"]
    if (p.get("schema")!="itd02.mg33.original-public-history-frontier-acquisition-development.v1"
        or p.get("phase")!="FROZEN_BEFORE_IMPLEMENTATION_AND_BEFORE_NEW_ORIGINAL_WORLD_ACTION"
        or p["parent"]["forge_mg32"]!=PARENT
        or p["authentic_source"]["farama_commit"]!=UPSTREAM
        or tuple(d["families"])!=FAMILIES
        or tuple(d["roles"])!=ROLES
        or tuple(tuple(s) for s in d["original_source_dev_seeds"])!=SEEDS
        or d["max_selected_actions_per_actor_episode"]!=192
        or d["independent_process_reproductions"]!=2
        or d["zero_fit_all"] is not True
        or (f["untried_action_bonus"],f["successor_inverse_visit_weight"],
            f["transition_change_weight"],f["global_successor_novelty_weight"],
            f["local_attempt_inverse_weight"],f["no_public_change_penalty_weight"],
            f["selected_attempt_penalty"])!=(360,220,180,180,180,230,4)
        or not all(p["prohibitions"].values())):
        raise ValueError("MG33_FROZEN_DESIGN_DRIFT")
    known=set(d["historical_exposed_seeds"])
    selected=[s for group in SEEDS for s in group]
    if len(selected)!=12 or len(set(selected))!=12 or (known&set(selected)):
        raise ValueError("MG33_HISTORICAL_SEED_COLLISION")
    if git("merge-base","--is-ancestor",PARENT,"HEAD").returncode:
        raise ValueError("MG33_WRONG_PARENT")
    if git("merge-base","--is-ancestor",FREEZE,"HEAD").returncode:
        raise ValueError("MG33_SOURCE_PREREG_NOT_FROZEN_BEFORE_EXECUTABLE")
    for s in selected:
        prior=git("grep","-n","-w",str(s),PARENT,"--","research/lcrm01","docs/research")
        if prior.returncode==0:
            raise ValueError("MG33_EXPOSED_IN_PARENT:"+str(s))
        if prior.returncode!=1:
            raise ValueError("MG33_SEED_PRIOR_SOURCE_VERIFICATION_UNAVAILABLE")
    return p


def context(frame):
    # Public pixels/heading only. No exact world coordinates or private object refs.
    return digest({"image":frame["image"],"direction":frame["direction"]})


class Frontier:
    """Source-selected public context/action/observed-successor graph.

    Distinct from MG31 exact-state UCB: global successor visitation, graph-edge
    statistics, cold cross-episode storage and no-effect discount are included.
    No action-specific target/door/key script or map oracle.
    """
    def __init__(self,edges=None,visits=None,total=0):
        self.edges={} if edges is None else edges
        self.visits={} if visits is None else visits
        self.total=total

    def choose(self,frame):
        key=context(frame)
        ties=int(key[:2],16)%7
        row=self.edges.get(key,{})
        best=None; selected=None
        for i in range(7):
            a=(ties+i)%7
            cell=row.get(str(a),{"n":0,"change":0,"novel":0,
                                 "stall":0,"next":{}})
            n=cell["n"]
            if cell["next"]:
                successor=sorted(cell["next"],key=lambda k:(-cell["next"][k],k))[0]
                successor_visits=self.visits.get(successor,0)
            else:
                successor_visits=0
            score=(360*int(n==0)+220//(1+successor_visits)
                   +180*(cell["change"]+1)//(n+2)
                   +180*(cell["novel"]+1)//(n+2)
                   +180//(n+1)-230*cell["stall"]//(n+1)-4*n)
            if best is None or score>best:
                best=score;selected=a
        return selected

    def observe(self,before,action,after,reward,terminated):
        if type(action) is not int or action not in range(7):
            raise ValueError("MG33_NON_SOURCE_SELECTED_ACTION")
        src=context(before);dst=context(after)
        new=dst not in self.visits
        b=digest(before);a=digest(after)
        cell=self.edges.setdefault(src,{}).setdefault(
            str(action),{"n":0,"change":0,"novel":0,"stall":0,"next":{}})
        cell["n"]+=1
        cell["change"]+=int(a!=b)
        cell["novel"]+=int(new)
        cell["stall"]+=int(a==b)
        cell["next"][dst]=cell["next"].get(dst,0)+1
        self.visits[src]=self.visits.get(src,0)+1
        self.visits[dst]=self.visits.get(dst,0)+1
        self.total+=1

    def checkpoint(self):
        return encode({"schema":"mg33.source-public-history-graph-frontier.v1",
                       "edges":self.edges,"visits":self.visits,"total":self.total})

    @classmethod
    def restore(cls,raw):
        data=json.loads(raw)
        if set(data)!={"schema","edges","visits","total"} or data["schema"]!="mg33.source-public-history-graph-frontier.v1":
            raise ValueError("MG33_FRONTIER_COLD_SCHEMA")
        a=cls(data["edges"],data["visits"],data["total"])
        if a.checkpoint()!=raw or a.total!=sum(
            cell["n"] for row in a.edges.values() for cell in row.values()):
            raise ValueError("MG33_FRONTIER_COLD_STATE_LOSS")
        return a


def frontier_episode(gym,entry,family,seed,prior,cap,public,og_digest):
    env=gym.make(family)
    try:
        if gym.spec(family).entry_point!=entry or getattr(env.action_space,"n",None)!=7:
            raise ValueError("MG33_WRONG_UPSTREAM_SEVEN_ACTION_ENV")
        raw,_=env.reset(seed=seed)
        first=public(raw);initial=og_digest(first);mission=first["mission"]
        learner=Frontier() if prior is None else Frontier.restore(prior)
        beginning=learner.total
        events=[]
        for step in range(1,cap+1):
            b=public(raw)
            if b["mission"]!=mission:
                raise ValueError("MG33_SOURCE_MISSION_DRIFT")
            a=learner.choose(b)
            assert type(a) is int and 0<=a<7
            raw2,reward,term,trunc,_=env.step(a)
            after=public(raw2)
            if after["mission"]!=mission or type(term) is not bool or type(trunc) is not bool or not math.isfinite(float(reward)):
                raise ValueError("MG33_SOURCE_ACTION_FEEDBACK_INVALID")
            learner.observe(b,a,after,float(reward),term)
            events.append({"index":step,"before":b,"action":a,"after":after,
                "mission":mission,"policy_status":"MG33_PUBLIC_HISTORY_GRAPH_SELECTED",
                "reward":float(reward),"terminated":term,"truncated":trunc,
                "before_sha256":og_digest(b),"after_sha256":og_digest(after),
                "external_actions":0})
            raw=raw2
            if term or trunc:break
        state=learner.checkpoint()
        if Frontier.restore(state).checkpoint()!=state or learner.total!=beginning+len(events):
            raise ValueError("MG33_COLD_SELECTED_MEMORY_FAILED")
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
                raise ValueError("MG33_MISSING_ROLE_EPISODES_OR_NOT_COLD_STARTED")
            if role!=ROLES[-1]:
                for previous,current in zip(group,group[1:]):
                    if previous["selected_source_samples_after"]!=current["prior_selected_source_samples"]:
                        raise ValueError("MG33_NOT_COLD_RETAINED_BETWEEN_SEEDS")
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
        raise ValueError("MG33_NOT_ORIGINAL_PINNED_UPSTREAM")
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
                else:
                    mode="full" if role==ROLES[3] else "action"
                    row,state=explore_episode(gym,registry[family],family,seed,mode,
                                              old_states[role],192,public,original_digest)
                if role!=ROLES[-1]:
                    old_states[role]=state
                rows.append(row);results.append(row)
            if len({r["public_start_sha256"] for r in rows})!=1:
                raise ValueError("MG33_UNEQUAL_ORIGINAL_START")
    if len(results)!=72 or not all(1<=r["original_source_actions"]<=192 for r in results):
        raise ValueError("MG33_INCOMPLETE_ORIGINAL_WORLD_MATRIX")
    metrics=metrics_for(results)
    gate=p["development_filter"]["pass_requires"]
    frontier=ROLES[2]
    pickup_families=FAMILIES[1:]
    found_pickup=sum(metrics[f][frontier]["target_disappearance"] for f in pickup_families)
    positive=sum(metrics[f][frontier]["positive_goal_episodes"] for f in pickup_families)
    frontier_exposure=sum(metrics[f][frontier]["target_front"]+
                          metrics[f][frontier]["door_front"] for f in pickup_families)
    controls=[sum(metrics[f][role]["target_front"]+
                  metrics[f][role]["door_front"] for f in pickup_families)
              for role in (ROLES[3],ROLES[4])]
    supported=(frontier_exposure>max(controls) and found_pickup>=1 and positive>=1)
    classification=p["development_filter"]["classification_if_met" if supported else "classification_if_failed"]
    result={"schema":"itd02.mg33.original-public-history-frontier-dev-source.v1",
        "classification":classification,
        "original_farama_source":UPSTREAM,"source_parent":PARENT,
        "exposed_dev_seeds":[list(x) for x in SEEDS],
        "original_72_episodes":results,"per_family_per_role":metrics,
        "original_selected_action_count":sum(r["original_source_actions"] for r in results),
        "frontier_development_filter":{"frontier_exposure":frontier_exposure,
            "matched_generic_and_action_only_exposures":controls,
            "frontier_exact_target_effects":found_pickup,"frontier_goals":positive,
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
        actor=Frontier()
        for _ in range(14):
            a=actor.choose(source); actor.observe(source,a,nxt,0.0,False)
        raw=actor.checkpoint()
        assert Frontier.restore(raw).checkpoint()==raw and actor.total==14
        assert opt.source_root is None and opt.native_go is None and opt.output is None
        print("MG33_FROZEN_FRESH_ORIGINAL_SOURCE_AND_PUBLIC_HISTORY_COLD_PREFLIGHT_PASS")
        return
    if opt.compare:
        a,b=[json.loads(Path(x).read_text()) for x in opt.compare]
        if (a.get("source")!=b.get("source") or
            a.get("canonical_source_sha256")!=b.get("canonical_source_sha256") or
            a.get("canonical_source_sha256")!=digest(a["source"]) or
            len(a["source"]["original_72_episodes"])!=72 or
            a["source"]["scientific_first_use"] is not False or
            a["source"]["zero_external_actions"] is not True):
            raise ValueError("MG33_TWO_AUTHENTIC_ORIGINAL_PROCESSES_DIFFER")
        print("MG33_INDEPENDENT_SOURCE_PROCESSES_PASS",a["canonical_source_sha256"])
        print("MG33_FROZEN_DEVELOPMENT_CLASSIFICATION",a["source"]["classification"])
        print("MG33_FRONTIER_EXPOSURE_AND_GOAL_METRICS",
              json.dumps(a["source"]["frontier_development_filter"],sort_keys=True))
        return
    if not all((opt.source_root,opt.native_go,opt.output)):
        parser.error("require --source-root --native-go --output or --compare")
    started=time.perf_counter()
    try:
        envelope=execute(opt.source_root,opt.native_go,p)
    except Exception as exc:
        envelope={"schema":"itd02.mg33.original-public-history-frontier-dev-source.v1",
            "classification":"MG33_ORIGINAL_SOURCE_BLOCKED_NO_SCIENCE",
            "error_type":type(exc).__name__,"error":str(exc),
            "trace_tail":traceback.format_exc().splitlines()[-12:]}
    envelope["host_wall_time_outside_canonical_source_seconds"]=round(time.perf_counter()-started,6)
    opt.output.write_text(json.dumps(envelope,sort_keys=True,indent=2)+"\n")
    classification=envelope.get("classification",
                envelope.get("source",{}).get("classification","MG33_MISSING_CLASSIFICATION_BLOCKED"))
    print("MG33_ORIGINAL_SOURCE_CLASSIFICATION",classification)
    if "BLOCKED" in classification:
        raise ValueError(envelope.get("error","MG33_SOURCE_EXECUTION_FAILED"))
    print("MG33_ORIGINAL_SOURCE_SHA256",envelope["canonical_source_sha256"])


if __name__=="__main__":
    main()

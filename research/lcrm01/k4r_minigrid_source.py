#!/usr/bin/env python3
"""K4R — Farama MiniGrid source qualification on two independent task families.

All state is from FullyObsWrapper's PUBLIC image observation. Fit a shared
turn/forward transition model and a conventional tabular Q baseline from
identical real FIT transitions. No native cognition or protected first use.
"""
from collections import Counter, deque
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import traceback

FROZEN=Path(__file__).with_name("k4r_frozen_independent_minigrid.json")
SCHEMA="mass.lcrm01.k4r.original-independent-interactive-world-source.v1"
FAMILIES=("empty","fourrooms")
POLICIES=("learned_model_bfs","public_bfs_expert","tabular_q",
          "uniform_random","fixed_forward")
# Published MiniGrid direction convention is an untrained oracle upper bound.
EXPERT_MOVES=((1,0),(0,1),(-1,0),(0,-1))


def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)


def sha(x):
    return hashlib.sha256(x).hexdigest()


def frozen():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if p.get("schema")!="mass.lcrm01.k4r.frozen-independent-interactive-benchmark-source-v1":
        raise ValueError("K4R_FROZEN_PROTOCOL_DRIFT")
    s=p["worlds"]["source_seeds"]
    if (s!={"FIT":"1100..1123 inclusive (24 episodes per family)",
             "CHECK":"2100..2103 inclusive (4 episodes per family)",
             "DEV":"3100..3107 inclusive (8 episodes per family)"}
        or p["independent_source"]["commit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or p["worlds"]["legal_actions"]!=[0,1,2]):
        raise ValueError("K4R_FROZEN_SOURCE_SEEDS_DRIFT")
    return p


def seeds(phase):
    return {"FIT":range(1100,1124),"CHECK":range(2100,2104),
            "DEV":range(3100,3108)}[phase]


def make_env(family):
    from minigrid.envs.empty import EmptyEnv
    from minigrid.envs.fourrooms import FourRoomsEnv
    from minigrid.wrappers import FullyObsWrapper
    if family=="empty":
        e=EmptyEnv(size=8,agent_start_pos=None,max_steps=96)
    elif family=="fourrooms":
        e=FourRoomsEnv(agent_pos=None,goal_pos=None,max_steps=192)
    else:
        raise ValueError("UNQUALIFIED_FAMILY")
    return FullyObsWrapper(e)


def public(obs,prior_goal=None):
    import numpy as np
    from minigrid.core.constants import OBJECT_TO_IDX
    image=np.asarray(obs["image"],dtype=np.uint8)
    if image.ndim!=3 or image.shape[2]!=3:
        raise ValueError("PUBLIC_IMAGE_NOT_ORIGINAL_FULL_GRID")
    pos=np.argwhere(image[:,:,0]==OBJECT_TO_IDX["agent"])
    goals=np.argwhere(image[:,:,0]==OBJECT_TO_IDX["goal"])
    if len(pos)!=1 or (prior_goal is None and len(goals)!=1):
        raise ValueError("PUBLIC_GRID_AGENT_OR_GOAL_NOT_UNIQUE")
    x,y=map(int,pos[0])
    direction=int(image[x,y,2])
    if direction not in range(4):
        raise ValueError("PUBLIC_AGENT_DIRECTION_NOT_FOUR")
    goal=tuple(map(int,goals[0])) if len(goals)==1 else prior_goal
    if goal is None:
        raise ValueError("PUBLIC_GOAL_NOT_OBSERVABLE")
    walls=frozenset(map(tuple,np.argwhere(image[:,:,0]==OBJECT_TO_IDX["wall"]).tolist()))
    return {"x":x,"y":y,"dir":direction,"goal":goal,"walls":walls,
            "shape":tuple(map(int,image.shape[:2])),
            "grid_sha256":sha(image.tobytes())}


def front_blocked(st,moves=EXPERT_MOVES):
    dx,dy=moves[st["dir"]]
    tx,ty=st["x"]+dx,st["y"]+dy
    return tx<0 or ty<0 or tx>=st["shape"][0] or ty>=st["shape"][1] or (tx,ty) in st["walls"]


def state_key(family,st):
    gx,gy=st["goal"]
    dx,dy=gx-st["x"],gy-st["y"]
    dist=abs(dx)+abs(dy)
    return ":".join(map(str,(family,(dx>0)-(dx<0),(dy>0)-(dy<0),
             min(3,dist//4),st["dir"],int(front_blocked(st)))))


def recorded_fit_transition(st,action,nxt,reward,family,seed,terminated):
    return {"family":family,"world_seed":seed,
      "action":action,"pos":[st["x"],st["y"]],"dir":st["dir"],
      "next_pos":[nxt["x"],nxt["y"]],"next_dir":nxt["dir"],
      "public_front_blocked":front_blocked(st),
      "start_key":state_key(family,st),"next_key":state_key(family,nxt),
      "reward":float(reward),"terminated":bool(terminated)}


def train_fit(p):
    import random
    experiences=[]
    initial=[]
    total_cpu=time.process_time()
    for fi,family in enumerate(FAMILIES):
        for seed in seeds("FIT"):
            e=make_env(family)
            rng=random.Random(810000+1000*fi+seed)
            try:
                obs,info=e.reset(seed=seed)
                st=public(obs)
                initial.append({"family":family,"seed":seed,
                    "public_start_sha256":st["grid_sha256"],
                    "public_goal":list(st["goal"])})
                for _ in range(96 if family=="empty" else 192):
                    a=rng.randrange(3)
                    next_obs,reward,terminated,truncated,_=e.step(a)
                    nxt=public(next_obs,st["goal"])
                    experiences.append(recorded_fit_transition(
                        st,a,nxt,reward,family,seed,terminated or truncated))
                    st=nxt
                    if terminated or truncated:break
            finally:
                e.close()
    return experiences,initial,time.process_time()-total_cpu


def empirical_model(rows):
    # Learned shared motion semantics, NOT hard-coded MiniGrid movement directions.
    turns={a:Counter() for a in (0,1)}
    free={d:Counter() for d in range(4)}
    blocked=Counter()
    for r in rows:
        a=r["action"];direct=r["dir"]
        dp=(r["next_pos"][0]-r["pos"][0],r["next_pos"][1]-r["pos"][1])
        if a in (0,1):
            turns[a][(r["next_dir"]-direct)%4]+=1
        elif a==2:
            if r["public_front_blocked"]:
                blocked[dp]+=1
            else:
                free[direct][dp]+=1
        else:raise ValueError("FIT_SOURCE_NONLEGAL_ACTION")
    missing=any(not turns[a] for a in (0,1)) or any(not free[d] for d in range(4)) or not blocked
    if missing:
        return None,{"FIT_motion_support_complete":False,
            "observed_turns":{str(a):sum(turns[a].values()) for a in turns},
            "free_forward_by_direction":{str(d):sum(free[d].values()) for d in free},
            "blocked_forward_samples":sum(blocked.values())}
    modal=lambda c:max(c,key=lambda x:(c[x],str(x)))
    model={"turns":{str(a):int(modal(turns[a])) for a in turns},
           "moves":{str(d):list(modal(free[d])) for d in free},
           "blocked_forward":list(modal(blocked)),
           "source_transition_count":len(rows)}
    guard=(model["turns"]=={"0":3,"1":1}
        and tuple(model["blocked_forward"])==(0,0)
        and all(tuple(model["moves"][str(d)])==EXPERT_MOVES[d] for d in range(4)))
    return model,{"FIT_motion_support_complete":True,
        "matches_public_documented_semantics":guard,
        "observed_turns":{str(a):sum(turns[a].values()) for a in turns},
        "free_forward_by_direction":{str(d):sum(free[d].values()) for d in free},
        "blocked_forward_samples":sum(blocked.values())}


def learn_q(rows):
    table={}
    alpha=.25;gamma=.95
    for rec in rows:
        key=rec["start_key"];a=rec["action"];nextkey=rec["next_key"]
        vals=table.setdefault(key,[0.,0.,0.])
        continuation=0. if rec["terminated"] else max(table.get(nextkey,[0.,0.,0.]))
        vals[a]=float(vals[a]+alpha*(rec["reward"]+gamma*continuation-vals[a]))
    return table


def fitted(rows,initial):
    model,counts=empirical_model(rows)
    diverse={family:len({r["public_start_sha256"] for r in initial
          if r["family"]==family}) for family in FAMILIES}
    gate=(model is not None and counts["matches_public_documented_semantics"]
          and all(diverse[f]>=16 for f in FAMILIES))
    return {"dynamics":model,"q_table":learn_q(rows),
            "FIT_support":counts,"FIT_distinct_public_starts":diverse,
            "FIT_source_eligible":bool(gate)}


def motion(st,action,model):
    # Inputs only public walls/current agent state and FIT learned dynamics.
    x,y,d=st
    if action in (0,1):
        turn=int(model["turns"][str(action)])
        return x,y,(d+turn)%4
    dx,dy=model["moves"][str(d)]
    px,py=x+dx,y+dy
    if px<0 or py<0 or px>=model["shape"][0] or py>=model["shape"][1] or (px,py) in model["walls"]:
        return x,y,d
    return px,py,d


def bfs(st,learned):
    model=(
        {"turns":learned["turns"],"moves":learned["moves"]}
        if learned is not None else
        {"turns":{"0":3,"1":1},
         "moves":{str(d):list(EXPERT_MOVES[d]) for d in range(4)}})
    model["walls"]=st["walls"];model["shape"]=st["shape"]
    start=(st["x"],st["y"],st["dir"])
    if (start[0],start[1])==st["goal"]:
        return 2
    queue=deque([start])
    seen={start};first={}
    while queue:
        node=queue.popleft()
        for a in (2,0,1):
            nxt=motion(node,a,model)
            if nxt==node or nxt in seen:continue
            first[nxt]=a if node==start else first[node]
            if (nxt[0],nxt[1])==st["goal"]:
                return first[nxt]
            seen.add(nxt);queue.append(nxt)
    return 2  # Explicit solver failure will be observable in success score.


def act(family,st,method,model,seed,step):
    if method=="learned_model_bfs":return bfs(st,model["dynamics"])
    if method=="public_bfs_expert":return bfs(st,None)
    if method=="tabular_q":
        values=model["q_table"].get(state_key(family,st),[0.,0.,0.])
        return max((0,1,2),key=lambda a:(values[a],-a))
    if method=="fixed_forward":return 2
    if method=="uniform_random":
        import random
        # Stateless repeatable source of random actions, never uncontrolled RNG.
        return random.Random(912000+seed*100+step+FAMILIES.index(family)*17000).randrange(3)
    raise ValueError("INVALID_POLICY")


def episode(family,seed,method,model):
    start_cpu=time.process_time()
    e=make_env(family)
    outcomes=[]
    try:
        obs,info=e.reset(seed=seed)
        st=public(obs)
        original_sha=st["grid_sha256"];goal=list(st["goal"])
        first_action=None;success=False;total=0.
        for t in range(96 if family=="empty" else 192):
            a=act(family,st,method,model,seed,t)
            if first_action is None:first_action=a
            obs_next,reward,term,trunc,_=e.step(a)
            nxt=public(obs_next,st["goal"])
            outcomes.append((st["x"],st["y"],st["dir"],a,nxt["x"],nxt["y"],nxt["dir"],float(reward)))
            total+=float(reward)
            st=nxt
            if term or trunc:
                success=bool(term and total>0.)
                break
        return {"family":family,"seed":seed,"policy":method,
            "initial_public_sha256":original_sha,
            "public_goal":goal,
            "first_action":first_action,"success":success,
            "reward":float(total),"steps":len(outcomes),
            "action_consequence_trace_sha256":sha(canon(outcomes).encode()),
            "eval_cpu_seconds":time.process_time()-start_cpu}
    finally:e.close()


def phase(p,part,model):
    results=[]
    for family in FAMILIES:
        for seed in seeds(part):
            for method in POLICIES:
                results.append(episode(family,seed,method,model))
    return results


def evidence(p,dev):
    detail={}
    passed=True
    for family in FAMILIES:
        methods={name:[r for r in dev if r["family"]==family and r["policy"]==name]
                 for name in POLICIES}
        if any(len(v)!=8 for v in methods.values()):
            raise ValueError("DEV_EVALUATION_MISSING_CONTROL")
        firsts={a["first_action"] for a in methods["public_bfs_expert"]}
        rates={name:sum(r["success"] for r in records)/8 for name,records in methods.items()}
        means={name:sum(r["reward"] for r in records)/8 for name,records in methods.items()}
        gates={"optimal_first_actions_diverse":len(firsts)>=2,
          "learned_success_at_least_6_of_8":rates["learned_model_bfs"]>=.75,
          "learned_over_random_plus_0_40":rates["learned_model_bfs"]-rates["uniform_random"]>=.40,
          "learned_mean_reward_at_least_75pct_expert":means["learned_model_bfs"]>=.75*means["public_bfs_expert"]}
        detail[family]={"success_rate":rates,"mean_real_reward":means,
           "expert_first_action_ids":sorted(firsts),"qualification":gates}
        passed=passed and all(gates.values())
    return {"result":"INDEPENDENT_INTERACTIVE_SOURCE_QUALIFIED" if passed
         else "INDEPENDENT_SOURCE_NOT_QUALIFIED",
       "families":detail,"original_scientific_acceptance":False,
       "native_mechanism_tested":False,"unfamiliar_cognition_proven":False}


def execute(p):
    initial_wall=time.perf_counter();initial_cpu=time.process_time()
    records,initial,fit_cpu=train_fit(p)
    model=fitted(records,initial)
    base={"schema":SCHEMA,"gate":"LCRM01-K4R",
      "source_commit":p["independent_source"]["commit"],
      "protocol_sha256":sha(FROZEN.read_bytes()),
      "FIT_experience_count":len(records),
      "FIT_source_episodes":len(initial),
      "FIT_original_start_records":initial,
      "FIT_source_transitions":records,
      "FIT_support":model["FIT_support"],
      "FIT_distinct_starts":model["FIT_distinct_public_starts"],
      "CHECK_episode_evaluations":0,"DEV_episode_evaluations":0,
      "original_K4Q_no_go_preserved":True,
      "scientific_first_use":False,"scientific_accepted":False}
    if not model["FIT_source_eligible"]:
        base.update({"result":"FIT_PUBLIC_MOTION_SOURCE_INSUFFICIENT_HOLDOUT_UNCONSUMED",
          "resource":{"FIT_cpu_seconds":fit_cpu,"whole_cpu_seconds":time.process_time()-initial_cpu,
                      "wall_seconds":time.perf_counter()-initial_wall,
                      "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
        return base
    state=json.loads(canon(model))
    if state!=model:
        raise ValueError("FIT_MODEL_JSON_ROUNDTRIP_FAILED")
    base["FIT_learned_motion"]=model["dynamics"]
    base["fitted_checkpoint_sha256"]=sha(canon(model).encode())
    base["fitted_checkpoint_bytes"]=len(canon(model).encode())
    # No heldout source was read when FIT model and checkpoint became fixed.
    check=phase(p,"CHECK",state)
    dev=phase(p,"DEV",state)
    decision=evidence(p,dev)
    base.update({"result":"COMPLETE_INDEPENDENT_PUBLIC_BENCHMARK",
      "CHECK_episode_evaluations":len(check),
      "DEV_episode_evaluations":len(dev),
      "CHECK_original_results":check,"DEV_original_results":dev,
      "source_qualification":decision,
      "resource":{"FIT_cpu_seconds":fit_cpu,
          "whole_cpu_seconds":time.process_time()-initial_cpu,
          "wall_seconds":time.perf_counter()-initial_wall,
          "peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}})
    return base


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output",required=True,type=Path)
    x=a.parse_args()
    if x.output.exists() or not x.output.parent.is_dir():
        raise RuntimeError("K4R_ORIGINAL_SOURCE_OUTPUT_NOT_FRESH")
    try:result=execute(frozen())
    except Exception as ex:
        result={"schema":SCHEMA,"gate":"LCRM01-K4R",
            "result":"INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED",
            "error_type":type(ex).__name__,"error":str(ex),
            "traceback_tail":traceback.format_exc().splitlines()[-15:],
            "original_K4Q_no_go_preserved":True,
            "scientific_first_use":False,"scientific_accepted":False}
    x.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("K4R_ORIGINAL_SOURCE_OUTCOME="+result["result"])
    if "source_qualification" in result:
        print("K4R_BENCHMARK_VERDICT="+result["source_qualification"]["result"])
        print("K4R_FAMILY_SCORES="+canon(result["source_qualification"]["families"]))
    if "FIT_support" in result:
        print("K4R_EMPIRICAL_SOURCE_SUPPORT="+canon(result["FIT_support"]))
    return 1 if result["result"]=="INFRASTRUCTURE_OR_SOURCE_NOT_QUALIFIED" else 0


if __name__=="__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""K4Z: original source-own Ygg R2 vs R3 online episodic causal navigation.

Long-term R2 local cell policy trained exclusively on FIT. During heldout,
R3 can remember its OWN public action consequences (no reward-policy update).
A conventional online planner receives the same causal observations, while
expert/learned-dynamics full-public-map planners are separate upper controls.
"""
from __future__ import annotations
import argparse,heapq,hashlib,json,math,os,resource,subprocess,sys,time,traceback
from pathlib import Path
import k4x_curriculum_intervention as k4x
from k4r_minigrid_source import FAMILIES, make_env,public,act,fitted,sha,canon
from k4u_native_minigrid import native_from_public,public_grid

PIN=Path(__file__).with_name("k4z_frozen_episodic_nav.json")
SCHEMA="mass.lcrm01.k4z.original-online-causal-navigation-v1"
METHODS=("ygg_R2_static","ygg_R3_episodic","online_optimistic_planner",
         "tabular_q_fit","learned_dynamics_bfs_fit","public_bfs_upper","uniform_random")
SEEDS={"FIT":tuple(range(17400,17424)),"CHECK":tuple(range(18400,18404)),
       "DEV":tuple(range(19400,19408))}
LIMITS={"empty":96,"fourrooms":192}
NATIVE_R3_BLOB="5348238f4ec2183bea29262659883391b5f429fd"

def frozen():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k4z.frozen-episodic-navigation-transfer.v1"
     or p["parent_K4Y"]!="b01627841e6014750b3f03bcd58873d08375f93d"
     or p["worlds"]["FIT"]!=[17400,17423]
     or p["worlds"]["DEV"]!=[19400,19407]
     or p["frozen_source"]["ygg_R2_blob"]!="f7e47dfef309e1c0bcc871d518154fd950b3eca0"):
  raise ValueError("K4Z_FROZEN_SOURCE_OR_FIRST_USE_COHORT_DRIFT")
 return p

def into(st,cls):
 v=st if set(st)=={"X","Y","GoalX","GoalY","Direction","FrontBlocked"} else public_grid(st)
 return cls(v["X"],v["Y"],v["GoalX"],v["GoalY"],v["Direction"],v["FrontBlocked"])

def fit_source():
 k4x.FIT_SEEDS=SEEDS["FIT"]
 events,records,starts,audit,wall=k4x.fit_stream("public_bfs_demonstration_equal_budget")
 control=fitted(records,starts)
 fitok=(len(events)==12000 and control["FIT_source_eligible"]
    and all(audit[f]["public_steps"]==6000 for f in FAMILIES)
    and all({e["action"] for e in events if e["family"]==f}=={0,1,2} for f in FAMILIES))
 return events,starts,audit,wall,control if fitok else None

class OnlinePlanner:
 """Independent conventional optimistic pose planner with online edge counts."""
 def __init__(self,model):
  self.model={int(d):tuple(v) for d,v in model.items()}
  self.reset(8,8)
 def reset(self,w,h):
  self.w=w;self.h=h;self.blocked=set();self.free=set()
  self.visits={}
 def choose(self,g):
  start=(g.x,g.y,g.direction);goal=(g.goal_x,g.goal_y)
  q=[(0.,0.,0,start,-1)];best={start:0.};i=0
  while q:
   _,cost,_,(x,y,d),first=heapq.heappop(q)
   if cost>best[(x,y,d)]+1e-8:continue
   if (x,y)==goal:return first if first>=0 else 2
   for a in (2,0,1):
    if a==0:n=(x,y,(d-1)%4);weight=.35
    elif a==1:n=(x,y,(d+1)%4);weight=.35
    else:
     if (x,y,d) in self.blocked:continue
     dx,dy=self.model[d];nx,ny=x+dx,y+dy
     if not(0<=nx<self.w and 0<=ny<self.h):continue
     n=(nx,ny,d)
     weight=1. if (x,y,d) in self.free else 1.35
     weight+=.04*min(10,self.visits.get(n,0))
    v=cost+weight
    if v+1e-9<best.get(n,float("inf")):
     best[n]=v;i+=1
     heapq.heappush(q,(v+abs(n[0]-goal[0])+abs(n[1]-goal[1]),v,i,n,a if first<0 else first))
  return 2
 def observe(self,before,a,after):
  if a==2:
   edge=(before.x,before.y,before.direction)
   if (before.x,before.y)==(after.x,after.y):
    self.blocked.add(edge)
   else:self.free.add(edge);self.blocked.discard(edge)
  key=(after.x,after.y,after.direction)
  self.visits[key]=self.visits.get(key,0)+1

def train(events):
 from research.native.itd02.r2.affordance_cells import AffordanceColony,PublicGrid
 from research.native.itd02.r3.navigator import Navigator
 r2=AffordanceColony();r3=Navigator()
 start=time.perf_counter();last_done=True;last_family=None
 for i,e in enumerate(events):
  family=e["family"]
  if last_done or family!=last_family:
   r3.reset_episode(8 if family=="empty" else 19,8 if family=="empty" else 19)
  b=into(e["before"],PublicGrid);n=into(e["after"],PublicGrid)
  r2.observe(b,e["action"],n,e["reward"],e["terminal"])
  r3.observe(b,e["action"],n,e["reward"],e["terminal"],True)
  last_done=e["terminal"];last_family=family
 elapsed=time.perf_counter()-start
 original_r2=r2.save();original_r3=r3.snapshot()
 r2=AffordanceColony.restore(original_r2)
 r3=Navigator.restore(original_r3)
 if r2.core.feedback_updates!=len(events) or r3.core.core.feedback_updates!=len(events):
  raise ValueError("K4Z_NONMATCHED_NATIVE_FIT_EXPOSURE")
 for d in range(4):
  if r3._motor(d) is None:
   raise ValueError("K4Z_PUBLIC_TRANSITION_MOTOR_INFORMATION_INSUFFICIENT")
 script="""import json,sys
from research.native.itd02.r2.affordance_cells import AffordanceColony
from research.native.itd02.r3.navigator import Navigator
b=AffordanceColony.restore(bytes.fromhex(sys.argv[1]))
c=Navigator.restore(bytes.fromhex(sys.argv[2]))
print(json.dumps({"r2":b.core.feedback_updates,"r3":c.core.core.feedback_updates,
"motor":[c._motor(i) for i in range(4)]}))
"""
 z=subprocess.run([sys.executable,"-B","-c",script,original_r2.hex(),original_r3.hex()],
    capture_output=True,text=True,timeout=45)
 if z.returncode or json.loads(z.stdout).get("motor")!=[[1,0],[0,1],[-1,0],[0,-1]]:
  raise ValueError("K4Z_FRESH_OS_CHECKPOINT_OR_CAUSAL_MOVEMENT_FAILED:"+z.stderr[-1000:])
 return r2,r3,{"authentic_native_FIT_events_each":len(events),
    "native_FIT_shared_wall_seconds":elapsed,
    "native_R2_checkpoint_bytes":len(original_r2),
    "native_R3_checkpoint_bytes":len(original_r3),
    "native_R2_checkpoint_sha256":sha(original_r2),
    "native_R3_checkpoint_sha256":sha(original_r3),
    "true_independent_OS_cold_restore":True,
    "source_causal_deltas":[r3._motor(d) for d in range(4)]}

def eval_one(family,seed,method,r2,r3,fitmodel):
 from research.native.itd02.r2.affordance_cells import PublicGrid
 w=8 if family=="empty" else 19
 r3.reset_episode(w,w)
 planner=OnlinePlanner(fitmodel["dynamics"]["moves"])
 planner.reset(w,w)
 env=make_env(family)
 trace=[];succ=False;real_reward=0.;t0=time.perf_counter()
 try:
  obs,_=env.reset(seed=seed)
  st=public(obs)
  for t in range(LIMITS[family]):
   state=into(st,PublicGrid)
   if method=="ygg_R2_static":a=r2.choose(state)
   elif method=="ygg_R3_episodic":a=r3.choose(state)
   elif method=="online_optimistic_planner":a=planner.choose(state)
   else:
    controls={"tabular_q_fit":"tabular_q","learned_dynamics_bfs_fit":"learned_model_bfs",
              "public_bfs_upper":"public_bfs_expert","uniform_random":"uniform_random"}
    a=act(family,st,controls[method],fitmodel,seed,t)
   if type(a)is not int or a not in (0,1,2):raise ValueError("K4Z_INVALID_TRUE_NAVIGATION_ACTION")
   before=[st["x"],st["y"],st["dir"],int(public_grid(st)["FrontBlocked"])]
   next_obs,reward,term,trunc,_=env.step(a)
   nxt=public(next_obs,st["goal"])
   after=[nxt["x"],nxt["y"],nxt["dir"],int(public_grid(nxt)["FrontBlocked"])]
   actual=float(reward)
   if not math.isfinite(actual):raise ValueError("K4Z_NONFINITE_ORIGINAL_REWARD")
   if method=="ygg_R3_episodic":
    r3.observe(state,a,into(nxt,PublicGrid),actual,bool(term or trunc),False)
   elif method=="online_optimistic_planner":
    planner.observe(state,a,into(nxt,PublicGrid))
   trace.append({"t":t,"a":a,"b":before,"n":after,"reward":actual,
        "terminal":bool(term),"truncated":bool(trunc)})
   st=nxt;real_reward+=actual
   if term or trunc:
    succ=bool(term and real_reward>0);break
  return {"family":family,"seed":seed,"method":method,
    "real_success":succ,"real_reward":real_reward,
    "complete_public_action_trace":trace,
    "steps":len(trace),"trace_sha256":sha(canon(trace).encode()),
    "native_or_control_episode_wall_seconds":time.perf_counter()-t0}
 finally:env.close()

def qualify(dev):
 report={};tests={}
 for family in FAMILIES:
  methods={m:[r for r in dev if r["family"]==family and r["method"]==m] for m in METHODS}
  if any(len(v)!=8 for v in methods.values()):raise ValueError("K4Z_MISSING_TRUE_HELDOUT")
  report[family]={}
  for m,v in methods.items():
   report[family][m]={"actual_goals":sum(z["real_success"] for z in v),
    "real_mean_reward":sum(z["real_reward"] for z in v)/8,
    "actual_steps":sum(z["steps"] for z in v),
    "observed_blocked_forward_steps":sum(
      step["a"]==2 and step["b"][3] for z in v for step in z["complete_public_action_trace"])}
 four=report["fourrooms"]
 empt=report["empty"]
 tests={"R3_fourrooms_at_least_four_real_goals":four["ygg_R3_episodic"]["actual_goals"]>=4,
   "R3_at_least_three_extra_fourrooms_goals":four["ygg_R3_episodic"]["actual_goals"]-four["ygg_R2_static"]["actual_goals"]>=3,
   "R3_fourrooms_at_least_75pct_planner_real_reward":four["ygg_R3_episodic"]["real_mean_reward"]>=.75*four["learned_dynamics_bfs_fit"]["real_mean_reward"],
   "R3_empty_no_gt_two_win_regression":empt["ygg_R3_episodic"]["actual_goals"]>=empt["ygg_R2_static"]["actual_goals"]-2,
   "original_conventional_planner_qualified":all(report[f]["learned_dynamics_bfs_fit"]["actual_goals"]>=6 for f in FAMILIES)}
 return {"result":"BOUNDED_NATIVE_EPISODIC_NAVIGATION_SOURCE_GAIN" if all(tests.values())
     else "NO_QUALIFIED_NATIVE_EPISODIC_PLANNING_TRANSFER",
     "original_DEVELOPMENT_family_results":report,"frozen_scientific_tests":tests,
     "native_novelty_or_pareto_claim":False,"scientific_first_use":False,"scientific_accepted":False}

def experiment():
 fit,starts,audit,source_wall,control=fit_source()
 result={"schema":SCHEMA,"gate":"LCRM01-K4Z",
    "FIT_public_episodes":len(starts),"FIT_original_experience_count":len(fit),
    "FIT_real_source":fit,"FIT_family_evidence":audit,
    "FIT_shared_world_generation_wall_seconds":source_wall,
    "source_model_FIT_eligible":control is not None,
    "CHECK_real_episodes":0,"DEV_real_episodes":0,
    "prior_K4Y_scientific_NO_GO_preserved":True,
    "scientific_first_use":False,"scientific_accepted":False}
 if control is None:
  result["result"]="FIT_SOURCE_UNQUALIFIED_NO_HELDOUT_EXPOSURE"
  return result
 r2,r3,info=train(fit)
 result["native_checkpoint_custody"]=info
 result["conventional_FIT_model_sha256"]=sha(canon(control).encode())
 # No native long-term policy updates on either heldout cohort.
 result["CHECK_original_traces"]=[eval_one(f,s,m,r2,r3,control) for f in FAMILIES
       for s in SEEDS["CHECK"] for m in METHODS]
 result["DEV_original_traces"]=[eval_one(f,s,m,r2,r3,control) for f in FAMILIES
       for s in SEEDS["DEV"] for m in METHODS]
 result["CHECK_real_episodes"]=len(result["CHECK_original_traces"])
 result["DEV_real_episodes"]=len(result["DEV_original_traces"])
 result["study_result"]=qualify(result["DEV_original_traces"])
 result["result"]="COMPLETE_AUTHENTIC_PROSPECTIVE_EPISODIC_NAVIGATION"
 return result

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",required=True,type=Path)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():
  raise RuntimeError("K4Z_ORIGINAL_RECEIPT_NOT_FRESH")
 c=time.process_time();w=time.perf_counter()
 try:
  proto=frozen()
  out=experiment()
  out["original_minigrid_source"]=proto["frozen_source"]["minigrid"]
  out["protocol_sha256"]=sha(PIN.read_bytes())
  out["native_source_original_R3_git_blob"]=NATIVE_R3_BLOB
 except Exception as e:
  out={"schema":SCHEMA,"gate":"LCRM01-K4Z","result":"SOURCE_OR_ENGINEERING_BLOCKED",
       "error":str(e),"type":type(e).__name__,
       "traceback_tail":traceback.format_exc().splitlines()[-14:],
       "scientific_first_use":False,"scientific_accepted":False}
 out["resources"]={"Python_CPU_seconds":time.process_time()-c,
   "wall_seconds":time.perf_counter()-w,
   "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 a.output.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K4Z_RESULT="+out["result"])
 if "study_result" in out:
  print("K4Z_ORIGINAL_NAVIGATION="+out["study_result"]["result"])
  print("K4Z_NEW_DEV="+canon(out["study_result"]["original_DEVELOPMENT_family_results"]))
 print("K4Z_REAL_FIT_EXPERIENCES="+str(out.get("FIT_original_experience_count",0)))
 return int(out["result"]=="SOURCE_OR_ENGINEERING_BLOCKED")
if __name__=="__main__":sys.exit(main())

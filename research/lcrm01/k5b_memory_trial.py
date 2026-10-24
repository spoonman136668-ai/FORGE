#!/usr/bin/env python3
"""K5B ORIGINAL MiniGrid MemoryEnv delayed cue, with genuine physical rewards.

Not autonomous navigation. Shared scripted public-map motor controller is held
identical across actual source-native and conventional late-choice policies.
The native/cognitive question is remembered cue + FIT reward association.
"""
import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time
import traceback
import numpy as np

PIN=Path(__file__).with_name("k5b_frozen_memory_task.json")
SCHEMA="mass.lcrm01.k5b.original-memory-delayed-cue-v1"
SIZE=(11,13)
PHASES={"FIT":range(26000,26064),"CHECK":range(27000,27008),"DEV":range(28000,28016)}
METHODS=("ygg_native_R4","native_without_cue_memory",
 "conventional_one_bit_reward_lookup","memoryless_top_choice","source_rule_upper_bound")
DIRECTIONS=((1,0),(0,1),(-1,0),(0,-1))
CODE_TO_TOKEN={5:"key",6:"ball"}  # authenticated against original MiniGrid OBJECT_TO_IDX
R4_BLOB="bb8747e225335affe0e23f57e3c5d692a25bf473"


def canonical(x):
 return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(x):
 return hashlib.sha256(x).hexdigest()

def frozen():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k5b.frozen-new-memory-task-matched-controls-v1"
     or p["parent_K5A_head"]!="f60b384416a473a0fff424d20d2efa29bf8d8dbf"
     or p["original_MemoryEnv"]["blob"]!="660b0a1b769948034c87bb421759c2b9a4f24548"
     or p["stream"]["FIT"]!=[26000,26063] or p["stream"]["DEV"]!=[28000,28015]
     or p["methods"]!=list(METHODS)):
  raise ValueError("K5B_PROTOCOL_DRIFT")
 from minigrid.core.constants import OBJECT_TO_IDX
 if {k:OBJECT_TO_IDX[k] for k in ("key","ball")}!={"key":5,"ball":6}:
  raise ValueError("K5B_ORIGINAL_OBJECT_CODEC_CHANGED")
 return p


def make_env(size):
 from minigrid.envs.memory import MemoryEnv
 from minigrid.wrappers import FullyObsWrapper
 if size not in SIZE:raise ValueError("K5B_UNREGISTERED_SIZE")
 return FullyObsWrapper(MemoryEnv(size=size,random_length=False,max_steps=250))


def read_cue_and_candidates(obs,size):
 image=np.asarray(obs["image"])
 if image.shape!=(size,size,3):raise ValueError("K5B_WRONG_PUBLIC_IMAGE")
 from minigrid.core.constants import OBJECT_TO_IDX
 mid=size//2; bx=size-2
 cue=int(image[1,mid-1,0])
 top=int(image[bx,mid-2,0])
 bot=int(image[bx,mid+2,0])
 if cue not in CODE_TO_TOKEN or {top,bot}!={5,6}:
  raise ValueError("K5B_ORIGINAL_CUE_OR_BRANCH_ENCODING_CHANGED")
 return CODE_TO_TOKEN[cue],CODE_TO_TOKEN[top],CODE_TO_TOKEN[bot]


def agent_state(image):
 from minigrid.core.constants import OBJECT_TO_IDX
 pts=np.argwhere(image[:,:,0]==OBJECT_TO_IDX["agent"])
 if len(pts)!=1:raise ValueError("K5B_PUBLIC_AGENT_NOT_VISIBLE")
 x,y=map(int,pts[0]);d=int(image[x,y,2])
 if d not in range(4):raise ValueError("K5B_BAD_PUBLIC_HEADING")
 return x,y,d


def navigate_plan(image,target):
 from minigrid.core.constants import OBJECT_TO_IDX
 start=agent_state(image)
 width,height=image.shape[:2]
 allowed={OBJECT_TO_IDX["empty"],OBJECT_TO_IDX["agent"]}
 blocked={OBJECT_TO_IDX["wall"],OBJECT_TO_IDX["key"],OBJECT_TO_IDX["ball"]}
 if image[target[0],target[1],0] not in allowed:
  raise ValueError("K5B_REAL_TERMINAL_CELL_NOT_FLOOR")
 q=deque([start]);previous={start:(None,None)}
 while q:
  x,y,d=q.popleft()
  if (x,y)==target:
   actions=[];z=(x,y,d)
   while previous[z][0] is not None:
    zprev,a=previous[z];actions.append(a);z=zprev
   return list(reversed(actions))
  for a in (0,1,2):
   if a==0:n=(x,y,(d-1)%4)
   elif a==1:n=(x,y,(d+1)%4)
   else:
    dx,dy=DIRECTIONS[d];nx,ny=x+dx,y+dy
    if not (0<=nx<width and 0<=ny<height):continue
    if int(image[nx,ny,0]) not in allowed:continue
    n=(nx,ny,d)
   if n not in previous:
    previous[n]=((x,y,d),a);q.append(n)
 raise ValueError("K5B_UNREACHABLE_PUBLIC_BRANCH")


def traverse(env,obs,destination,trace):
 cur=obs
 for a in navigate_plan(np.asarray(cur["image"]),destination):
  before=np.asarray(cur["image"]);b=agent_state(before)
  nxt,reward,terminal,truncated,_=env.step(a)
  after=agent_state(np.asarray(nxt["image"]))
  trace.append({"action":a,"before":b,"after":after,
    "reward":float(reward),"terminated":bool(terminal),"truncated":bool(truncated)})
  cur=nxt
  if terminal or truncated:return cur,float(reward),bool(terminal),bool(truncated)
 return cur,0.,False,False


def episode(size,seed,chosen_fn,fit_choice=None,method=None):
 env=make_env(size);t0=time.perf_counter();trace=[]
 try:
  obs,_=env.reset(seed=seed)
  cue,top,bottom=read_cue_and_candidates(obs,size)
  reset_hash=digest(np.asarray(obs["image"]).tobytes())
  if chosen_fn is not None:chosen_fn("begin",cue,top,bottom)
  mid=size//2;bx=size-2
  # Nonselective public actor first travels to a common decision junction.
  obs,rr,done,trunc=traverse(env,obs,(size-4,mid),trace)
  if done or trunc:raise ValueError("K5B_CUE_PHASE_PREMATURE_PHYSICAL_TERMINAL")
  cue2,top2,bottom2=read_cue_and_candidates(obs,size)
  if (cue2,top2,bottom2)!=(cue,top,bottom):
   raise ValueError("K5B_PUBLIC_CUE_SOURCE_CHANGED_DURING_DELAY")
  if fit_choice is not None:choice=fit_choice
  else:choice=chosen_fn("choose",None,top,bottom)
  if type(choice)is not int or choice not in (0,1):
   raise ValueError("K5B_INVALID_LEARNED_LATE_CHOICE")
  target=(bx,mid-1) if choice==0 else (bx,mid+1)
  obs,reward,term,trunc=traverse(env,obs,target,trace)
  # Genuine original MemoryEnv success/failed goal choice MUST TERMINATE.
  if not term or trunc or not trace:
   raise ValueError("K5B_REAL_MEMORY_REWARD_NOT_TERMINAL")
  if type(reward)is not float or not math.isfinite(reward) or not (0<=reward<=1):
   raise ValueError("K5B_INVALID_GENUINE_MEMORY_REWARD")
  if tuple(agent_state(np.asarray(obs["image"]))[:2])!=target:
   raise ValueError("K5B_ORIGINAL_CHOSEN_BRANCH_NOT_REACHED")
  return {"size":size,"seed":seed,"policy":method or "FIT_random",
   "cue_token":cue if fit_choice is not None else None,
   "public_initial_sha256":reset_hash,
   "phase2_options":[top,bottom],"selected_arm":choice,
   "selected_candidate":top if choice==0 else bottom,
   "real_goal_success":reward>0,"original_terminal_reward":reward,
   "actual_public_action_trace":trace,"physical_step_count":len(trace),
   "trace_sha256":digest(canonical(trace).encode()),
   "whole_episode_wall_seconds":time.perf_counter()-t0}
 finally:env.close()


class ConventionalMemory:
 def __init__(self):
  self.table={"match":[0,0],"different":[0,0]}
  self.cue=None
 def begin(self,c):self.cue=c
 def learn(self,choice_type,reward):
  key="match" if choice_type==self.cue else "different"
  self.table[key][0 if reward>0 else 1]+=1
  self.cue=None
 def choose(self,top,bottom):
  def score(c):
   key="match" if c==self.cue else "different"
   yes,no=self.table[key];return (yes+1)/(yes+no+2)
  return int(score(bottom)>score(top))


def trial():
 from research.native.itd02.r4.cue_cells import CueCells
 native=CueCells();classic=ConventionalMemory()
 fits=[];support={}
 for size in SIZE:
  pos=neg=0;choices=set();cues=set()
  for seed in PHASES["FIT"]:
   choice=random.Random(1417000+size*100000+seed*11).randrange(2)
   data=episode(size,seed,None,fit_choice=choice)
   cue=data["cue_token"];selected=data["selected_candidate"]
   native.begin(cue);native.observe(selected,data["original_terminal_reward"],True)
   classic.begin(cue);classic.learn(selected,data["original_terminal_reward"])
   pos+=int(data["real_goal_success"]);neg+=int(not data["real_goal_success"])
   choices.add(choice);cues.add(cue)
   fits.append(data)
  support[str(size)]={"actual_positive_goals":pos,"actual_negative_goals":neg,
    "actual_start_cues":sorted(cues),"actual_selected_arms":sorted(choices)}
 if any(x["actual_positive_goals"]<16 or x["actual_negative_goals"]<16 or
    x["actual_start_cues"]!=["ball","key"] or x["actual_selected_arms"]!=[0,1]
    for x in support.values()):
  return {"schema":SCHEMA,"result":"K5B_FIT_INFORMATION_INSUFFICIENT_HOLDOUT_NOT_CONSUMED",
    "FIT":fits,"FIT_support":support,"CHECK_real_episodes":0,"DEV_real_episodes":0,
    "scientific_first_use":False,"scientific_accepted":False}
 checkpoint=native.snapshot()
 # Source state must be authentically restored in a completely new Python OS
 # process before any heldout original environment is consumed.
 cold="""import json,sys
from research.native.itd02.r4.cue_cells import CueCells
x=CueCells.restore(sys.stdin.buffer.read())
print(json.dumps({"count":x.outcomes,"cue":x.cue,"counts":x.counts}))
"""
 z=subprocess.run([sys.executable,"-B","-c",cold],input=checkpoint,capture_output=True,timeout=30)
 if z.returncode:raise ValueError("K5B_NATIVE_COLD_CHECKPOINT_FAILED:"+z.stderr.decode()[-600:])
 signed=json.loads(z.stdout)
 if signed!={"count":128,"cue":None,"counts":native.counts}:
  raise ValueError("K5B_NATIVE_PERSISTENT_LEARNING_COLD_DRIFT")
 native=CueCells.restore(checkpoint)

 def play(method,phase):
  def cb(op,cue,top,bottom):
   if op=="begin":
    if method=="ygg_native_R4":native.begin(cue)
    elif method=="native_without_cue_memory":native.begin("key")
    elif method=="conventional_one_bit_reward_lookup":classic.begin(cue)
    return None
   if method in ("ygg_native_R4","native_without_cue_memory"):
    return native.choose(top,bottom)
   if method=="conventional_one_bit_reward_lookup":return classic.choose(top,bottom)
   if method=="memoryless_top_choice":return 0
   if method=="source_rule_upper_bound":return int(bottom==cue_holder[0])
   raise ValueError("K5B_NONFROZEN_EVAL_METHOD")
  # For the upper bound we need an explicit per-episode cue value that is
  # supplied identically in the first phase, never a hidden label.
  cue_holder=[None]
  def closure(op,cue,top,bottom):
   if op=="begin":cue_holder[0]=cue
   return cb(op,cue,top,bottom)
  return [episode(size,seed,closure,method=method) for size in SIZE for seed in PHASES[phase]]
 check=[v for name in METHODS for v in play(name,"CHECK")]
 dev=[v for name in METHODS for v in play(name,"DEV")]
 return {"schema":SCHEMA,"result":"COMPLETE_ORIGINAL_DELAYED_CUE_MEMORY_EXPERIMENT",
  "FIT":fits,"FIT_support":support,
  "source_native_checkpoint_sha256":digest(checkpoint),
  "source_native_checkpoint_bytes":len(checkpoint),
  "native_original_cold_OS_restore":True,
  "fitted_conventional_table":classic.table,
  "CHECK_real_episodes":len(check),"DEV_real_episodes":len(dev),
  "CHECK_full_actual_action_traces":check,"DEV_full_actual_action_traces":dev,
  "scientific":judge(dev),"scientific_first_use":False,"scientific_accepted":False}


def judge(dev):
 totals={}
 for size in SIZE:
  totals[str(size)]={}
  for m in METHODS:
   x=[z for z in dev if z["size"]==size and z["policy"]==m]
   if len(x)!=16 or sorted(z["seed"] for z in x)!=list(PHASES["DEV"]):
    raise ValueError("K5B_FROZEN_METHOD_WORLD_PARITY")
   totals[str(size)][m]={"actual_genuine_goals":sum(z["real_goal_success"] for z in x),
     "mean_real_reward":sum(z["original_terminal_reward"] for z in x)/16,
     "total_physical_steps":sum(z["physical_step_count"] for z in x)}
 checks={}
 for size in SIZE:
  r=totals[str(size)]
  checks[str(size)+"_12_native_goals"]=r["ygg_native_R4"]["actual_genuine_goals"]>=12
  checks[str(size)+"_4_extra_over_cue_ablation"]=(
   r["ygg_native_R4"]["actual_genuine_goals"]-
   r["native_without_cue_memory"]["actual_genuine_goals"]>=4)
  checks[str(size)+"_within_1_of_conventional"]=(
   r["ygg_native_R4"]["actual_genuine_goals"]>=
   r["conventional_one_bit_reward_lookup"]["actual_genuine_goals"]-1)
 native_positive=all(checks.values())
 native_advantage=all(
    totals[str(s)]["ygg_native_R4"]["actual_genuine_goals"]>
    totals[str(s)]["conventional_one_bit_reward_lookup"]["actual_genuine_goals"]
    for s in SIZE)
 return {"result":"BOUNDED_NATIVE_DELAYED_CUE_RETENTION" if native_positive
         else "NO_QUALIFIED_DELAYED_CUE_NATIVE_MEMORY",
  "families":totals,"frozen_primary_tests":checks,
  "native_superior_to_conventional":native_advantage,
  "autonomous_navigation_not_tested":True,
  "architecture_novelty_established":False,"scientific_first_use":False,"scientific_accepted":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 args=parser.parse_args()
 if args.output.exists() or not args.output.parent.is_dir():
  raise RuntimeError("K5B_NONFRESH_REPORT_PATH")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  p=frozen()
  result=trial()
  result["protocol_sha256"]=digest(PIN.read_bytes())
  result["original_native_R4_git_blob"]=R4_BLOB
  result["original_MemoryEnv_git_blob"]=p["original_MemoryEnv"]["blob"]
  result["prior_K5A_no_novelty_preserved"]=True
 except Exception as ex:
  result={"schema":SCHEMA,"result":"K5B_ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED",
   "error_type":type(ex).__name__,"error":str(ex),
   "traceback_tail":traceback.format_exc().splitlines()[-12:],
   "scientific_first_use":False,"scientific_accepted":False}
 result["resources"]={"Python_CPU_seconds":time.process_time()-cpu,
    "wall_seconds":time.perf_counter()-wall,
    "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("K5B_ORIGINAL_TASK="+result["result"])
 if "scientific" in result:
  print("K5B_SCIENTIFIC="+result["scientific"]["result"])
  print("K5B_DEV_GOALS="+canonical(result["scientific"]["families"]))
 if "FIT_support" in result:print("K5B_SOURCE_FIT="+canonical(result["FIT_support"]))
 return int(result["result"]=="K5B_ORIGINAL_SOURCE_OR_INFRASTRUCTURE_BLOCKED")
if __name__=="__main__":raise SystemExit(main())

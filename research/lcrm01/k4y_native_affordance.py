#!/usr/bin/env python3
"""K4Y: prospective original causal-affordance R2 versus identical-source R1.

Four native policies from their independently content-addressed source repos.
Never re-use K4X FIT/DEV worlds. Preserve FULL actual per-step heldout behavior.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
import k4x_curriculum_intervention as k4x
from k4u_native_minigrid import WingBridge,public_grid,native_from_public
from k4r_minigrid_source import FAMILIES,make_env,public,act,fitted,sha,canon

FROZEN=Path(__file__).with_name("k4y_frozen_learned_affordance.json")
SCHEMA="mass.lcrm01.k4y.original-public-native-affordance-evaluation.v1"
METHODS=("wingless_r1","wingless_r2","yggdrasil_r1","yggdrasil_r2",
         "fit_tabular_q","fit_dynamics_bfs","public_bfs_expert","uniform_random","fixed_forward")
MAP={"fit_tabular_q":"tabular_q","fit_dynamics_bfs":"learned_model_bfs"}
SEEDS={"FIT":tuple(range(11400,11424)),"CHECK":tuple(range(12400,12404)),
       "DEV":tuple(range(13400,13408))}
STEPS={"empty":96,"fourrooms":192}

def contract():
 p=json.loads(FROZEN.read_text())
 d=p["design"]
 if (p.get("schema")!="mass.lcrm01.k4y.frozen-learned-affordance-intervention-v1"
   or d["FIT_seed_start"]!=11400 or d["FIT_seed_end"]!=11423
   or d["CHECK_seed_start"]!=12400 or d["CHECK_seed_end"]!=12403
   or d["DEV_seed_start"]!=13400 or d["DEV_seed_end"]!=13407
   or d["legal_actions"]!=[0,1,2]
   or p["source"]["wingless_R2"]["blob"]!="e1564172079359ca4c450dcc87487a4733210584"
   or p["source"]["yggdrasil_R2"]["blob"]!="f7e47dfef309e1c0bcc871d518154fd950b3eca0"):
  raise ValueError("K4Y_PREREG_COHORT_OR_SOURCE_DRIFT")
 return p

def to_r1(s,native):
 return native.PublicGrid(s["X"],s["Y"],s["GoalX"],s["GoalY"],
                         s["Direction"],s["FrontBlocked"])

def to_r2(s,r2):
 return r2.PublicGrid(s["X"],s["Y"],s["GoalX"],s["GoalY"],
                      s["Direction"],s["FrontBlocked"])

def fit():
 k4x.FIT_SEEDS=SEEDS["FIT"]
 data,records,starts,audit,wall=k4x.fit_stream("public_bfs_demonstration_equal_budget")
 control=fitted(records,starts)
 if (len(data)!=12000 or not control["FIT_source_eligible"]
     or any(audit[f]["public_steps"]!=6000 for f in FAMILIES)
     or any(all(r["action"]!=a for r in data if r["family"]==f)
            for a in (0,1,2) for f in FAMILIES)):
  return data,starts,audit,wall,None
 return data,starts,audit,wall,control

def cold_python_save_verify(original,r2,stream):
 smoke="""import json,sys
from native_policy import GridColony,PublicGrid
from research.native.itd02.r2.affordance_cells import AffordanceColony,PublicGrid as R2Grid
a=GridColony.restore(bytes.fromhex(sys.argv[1]))
b=AffordanceColony.restore(bytes.fromhex(sys.argv[2]))
g=PublicGrid(3,4,6,7,0,True)
q=R2Grid(3,4,6,7,0,True)
print(json.dumps({"r1":a.choose(g),"r2":b.choose(q),
"r1_count":a.feedback_updates,"r2_count":b.core.feedback_updates}))
"""
 v=subprocess.run([sys.executable,"-B","-c",smoke,original.save().hex(),r2.save().hex()],
   text=True,capture_output=True,timeout=45)
 if v.returncode:
  raise ValueError("K4Y_YGG_COLD_OS_RESTORE_FAILED:"+v.stderr[-1000:])
 a=json.loads(v.stdout)
 if (a!={"r1":original.choose(to_r1({"X":3,"Y":4,"GoalX":6,"GoalY":7,"Direction":0,"FrontBlocked":True},
                                    sys.modules["native_policy"])),
         "r2":r2.choose(to_r2({"X":3,"Y":4,"GoalX":6,"GoalY":7,"Direction":0,"FrontBlocked":True},
                             sys.modules["research.native.itd02.r2.affordance_cells"])),
         "r1_count":len(stream),"r2_count":len(stream)}):
  raise ValueError("K4Y_YGG_COLD_OS_STATE_DRIFT")
 return True

def train(data,bin_r1,bin_r2):
 import native_policy as y1
 from research.native.itd02.r2 import affordance_cells as y2
 w1=WingBridge(bin_r1);w2=WingBridge(bin_r2)
 c1=y1.GridColony();c2=y2.AffordanceColony()
 start=time.perf_counter();cpu=time.process_time()
 try:
  for x in data:
   a=x["action"];before=x["before"];after=x["after"];r=x["reward"];done=x["terminal"]
   w1.learn(before,a,after,r,done)
   w2.learn(before,a,after,r,done)
   c1.observe(to_r1(before,y1),a,to_r1(after,y1),r,done)
   c2.observe(to_r2(before,y2),a,to_r2(after,y2),r,done)
  s1=w1.snapshot();s2=w2.snapshot()
  yraw1=c1.save();yraw2=c2.save()
  wall=time.perf_counter()-start;pcpu=time.process_time()-cpu
 finally:w1.close();w2.close()
 w1=WingBridge(bin_r1);w2=WingBridge(bin_r2)
 try:w1.restore(s1);w2.restore(s2)
 except Exception:w1.close();w2.close();raise
 restored_y1=y1.GridColony.restore(yraw1)
 restored_y2=y2.AffordanceColony.restore(yraw2)
 cold_python_save_verify(restored_y1,restored_y2,data)
 for x in data[:16]:
  if w1.choose(x["before"]) not in (0,1,2) or w2.choose(x["before"]) not in (0,1,2):
   raise ValueError("K4Y_NATIVE_POLICY_FAILED_AFTER_COLD_RESTART")
 return {"wingless_r1":w1,"wingless_r2":w2,
         "yggdrasil_r1":restored_y1,"yggdrasil_r2":restored_y2},y1,y2,{
         "native_FIT_update_events_per_method":len(data),
         "true_native_cold_restart":True,
         "shared_NATIVE_fit_wall_seconds":wall,
         "shared_Python_fit_CPU_seconds_excluding_Go":pcpu,
         "original_native_checkpoints_bytes":{"wingless_r1":len(s1),"wingless_r2":len(s2),
                "yggdrasil_r1":len(yraw1),"yggdrasil_r2":len(yraw2)},
         "original_native_checkpoint_sha256":{"wingless_r1":sha(s1),"wingless_r2":sha(s2),
                "yggdrasil_r1":sha(yraw1),"yggdrasil_r2":sha(yraw2)}}

def real_episode(family,seed,method,learners,y1,y2,control):
 e=make_env(family)
 rows=[];success=False;total=0.;start_wall=time.perf_counter();start_cpu=time.process_time()
 try:
  obs,_=e.reset(seed=seed)
  st=public(obs);initial=st["grid_sha256"]
  for tick in range(STEPS[family]):
   if method in ("wingless_r1","wingless_r2"):
    action=learners[method].choose(public_grid(st))
   elif method=="yggdrasil_r1":
    action=learners[method].choose(native_from_public(y1,st))
   elif method=="yggdrasil_r2":
    action=learners[method].choose(native_from_public(y2,st))
   else:action=act(family,st,MAP.get(method,method),control,seed,tick)
   if type(action)is not int or action not in (0,1,2):
    raise ValueError("K4Y_UNLAWFUL_NATIVE_NAVIGATION")
   source=public_grid(st)
   before=[st["x"],st["y"],st["dir"],st["goal"][0],st["goal"][1],int(source["FrontBlocked"])]
   nxtobs,reward,terminated,truncated,_=e.step(action)
   nxt=public(nxtobs,st["goal"])
   result=[nxt["x"],nxt["y"],nxt["dir"],nxt["goal"][0],nxt["goal"][1],
           int(public_grid(nxt)["FrontBlocked"])]
   if not math.isfinite(float(reward)):raise ValueError("K4Y_NONFINITE_ACTUAL_REWARD")
   rows.append({"t":tick,"a":action,"before":before,"after":result,
          "reward":float(reward),"terminated":bool(terminated),"truncated":bool(truncated)})
   total+=float(reward);st=nxt
   if terminated or truncated:
    success=bool(terminated and total>0.);break
  return {"family":family,"seed":seed,"method":method,
    "source_first_reset_sha256":initial,"success":success,
    "real_total_reward":total,"actual_public_step_trace":rows,
    "trace_sha256":sha(canon(rows).encode()),
    "episode_CPU_python_seconds":time.process_time()-start_cpu,
    "episode_wall_seconds":time.perf_counter()-start_wall}
 finally:e.close()

def evaluation(part,learners,y1,y2,control):
 return [real_episode(f,seed,m,learners,y1,y2,control)
         for f in FAMILIES for seed in SEEDS[part] for m in METHODS]

def report(dev):
 results={};checks={}
 for family in FAMILIES:
  methods={m:[z for z in dev if z["family"]==family and z["method"]==m] for m in METHODS}
  if any(len(x)!=8 for x in methods.values()):
   raise ValueError("K4Y_MISSING_GENUINE_MATCHED_DEV_WORLDS")
  item={}
  for method,episodes in methods.items():
   steps=[x for ep in episodes for x in ep["actual_public_step_trace"]]
   all_forward=sum(x["a"]==2 for x in steps)
   blocked_forward=sum(x["a"]==2 and x["before"][5]==1 for x in steps)
   item[method]={"successes":sum(x["success"] for x in episodes),
     "mean_real_reward":sum(x["real_total_reward"] for x in episodes)/8,
     "actual_total_steps":len(steps),"blocked_forward_steps":blocked_forward,
     "blocked_forward_per_100_steps":100*blocked_forward/len(steps),
     "blocked_fraction_of_forward":blocked_forward/max(1,all_forward),
     "first_actions":sorted({x["actual_public_step_trace"][0]["a"] for x in episodes})}
  results[family]=item
 for owner in ("wingless","yggdrasil"):
  gate={}
  for family in FAMILIES:
   a=results[family][owner+"_r1"];b=results[family][owner+"_r2"]
   gate[family+"_blocked_attempts_reduced_ge_30pct"]=(
       b["blocked_forward_per_100_steps"]<=.7*a["blocked_forward_per_100_steps"])
   gate[family+"_four_goals"]=b["successes"]>=4
   gate[family+"_at_least_75pct_planner_reward"]=(
       b["mean_real_reward"]>=.75*results[family]["fit_dynamics_bfs"]["mean_real_reward"])
  improvements=sum(results[f][owner+"_r2"]["successes"]-results[f][owner+"_r1"]["successes"]
                   for f in FAMILIES)
  gate["two_extra_goal_completions"]=improvements>=2
  checks[owner]={"criteria":gate,"genuine_goal_completion_delta":improvements,
    "all_primary_criteria":all(gate.values())}
 qualified=all(z["all_primary_criteria"] for z in checks.values()) and all(
     results[f]["fit_dynamics_bfs"]["successes"]>=6 for f in FAMILIES)
 return {"result":"BOTH_NATIVE_AFFORDANCES_GAIN_REAL_UNFAMILIAR_TRANSFER" if qualified
         else "NO_QUALIFIED_LEARNED_AFFORDANCE_NAVIGATION_TRANSFER",
       "results":results,"frozen_candidate_gates":checks,
       "all_native_cognition_criteria":qualified,
       "scientific_accepted":False,"scientific_first_use":False}

def experiment(bin_r1,bin_r2):
 start_wall=time.perf_counter();start_cpu=time.process_time()
 train_stream,starts,audit,source_wall,control=fit()
 base={"schema":SCHEMA,"gate":"LCRM01-K4Y",
    "FIT_episodes":len(starts),"FIT_public_experience_count":len(fit),
    "FIT_original_public_experiences":fit,"FIT_source_balance":audit,
    "shared_FIT_source_wall_seconds":source_wall,
    "FIT_conventional_source_eligible":control is not None,
    "CHECK_episodes":0,"DEV_episodes":0,
    "K4X_original_scientific_NO_GO_preserved":True,
    "scientific_first_use":False,"scientific_accepted":False}
 if control is None:
  base["result"]="FIT_SOURCE_NOT_QUALIFIED_HELDOUT_UNCONSUMED"
  return base
 base["FIT_conventional_sha256"]=sha(canon(control).encode())
 learners,y1,y2,info=train(train_stream,bin_r1,bin_r2)
 try:
  base["native_FIT_custody"]=info
  check=evaluation("CHECK",learners,y1,y2,control)
  dev=evaluation("DEV",learners,y1,y2,control)
  judgement=report(dev)
  base.update({"result":"COMPLETE_PROSPECTIVE_NATIVE_AFFORDANCE_EVALUATION",
   "CHECK_episodes":len(check),"DEV_episodes":len(dev),
   "CHECK_original_public_traces":check,"DEV_original_public_traces":dev,
   "source_science":judgement})
 finally:
  learners["wingless_r1"].close();learners["wingless_r2"].close()
 return base

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--wingless-r1",type=Path,required=True)
 a.add_argument("--wingless-r2",type=Path,required=True)
 a.add_argument("--yggdrasil-source",type=Path,required=True)
 a.add_argument("--output",type=Path,required=True)
 x=a.parse_args()
 if x.output.exists() or not x.output.parent.is_dir():
  raise RuntimeError("K4Y_NONFRESH_ORIGINAL_EVIDENCE_FILE")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  p=contract()
  sys.path.insert(0,str(x.yggdrasil_source.resolve()))
  q=experiment(x.wingless_r1,x.wingless_r2)
  q["protocol_sha256"]=sha(FROZEN.read_bytes())
  q["source_minigrid_commit"]=p["source"]["minigrid"]["commit"]
  q["original_native_heads"]={s:p["source"][s]["head"] for s in
       ("wingless_R1","wingless_R2","yggdrasil_R1","yggdrasil_R2")}
 except Exception as e:
  q={"schema":SCHEMA,"gate":"LCRM01-K4Y",
    "result":"SOURCE_OR_INFRASTRUCTURE_BLOCKED","error":str(e),
    "error_type":type(e).__name__,
    "traceback_tail":traceback.format_exc().splitlines()[-14:],
    "scientific_first_use":False,"scientific_accepted":False}
 q["resources"]={"process_python_CPU_seconds_excludes_Go":time.process_time()-cpu,
    "whole_wall_seconds":time.perf_counter()-wall,
    "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 x.output.write_text(json.dumps(q,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("K4Y_ORIGINAL_RESULT="+q["result"])
 if "source_science" in q:
  print("K4Y_NAVIGATION_SCIENCE="+q["source_science"]["result"])
  print("K4Y_DEV_MEASURED="+canon(q["source_science"]["results"]))
 print("K4Y_FIT_REAL_EVENTS="+str(q.get("FIT_public_experience_count",0)))
 return 1 if q["result"]=="SOURCE_OR_INFRASTRUCTURE_BLOCKED" else 0
if __name__=="__main__":
 sys.exit(main())

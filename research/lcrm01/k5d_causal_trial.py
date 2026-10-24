#!/usr/bin/env python3
"""K5D prospective public causal composition with true source interventions.

Native R6 source lives in Yggdrasil, controlled baselines live here. Neither
sees the simulator's latent permutation/mask, only same public 7-probe corpus
per intervention per world. New worlds receive the same declared calibration
budget (not zero-shot causal-rule discovery); heldout chains are prospective.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import resource
import subprocess
import sys
import time
import traceback
from k5d_causal_world import CausalSixBitWorld,INPUTS,OPS

PIN=Path(__file__).with_name("k5d_frozen_composition.json")
SCHEMA="mass.lcrm01.k5d.true-public-causal-composition-v1"
METHODS=("ygg_R6_native_composition","ygg_R6_no_composition","ygg_R6_no_world_memory",
 "conventional_GF2_solver","conventional_single_step_1NN","fixed_identity")
PHASE_WORLDS={"FIT":(401,402,403,404),"CHECK":(801,802),"DEV":(901,902,903,904)}
NATIVE_BLOB="K5D_R6_NATIVE_BLOB_PENDING"

def canonical(a):
 return json.dumps(a,sort_keys=True,separators=(",",":"),allow_nan=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()

def frozen():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k5d.frozen-public-causal-composition-v1"
  or p["parent_K5C_head"]!="15e18aef3a271c675dd7007fbdb8d869bfc682da"
  or p["cohorts"]["FIT_worlds"]!=list(PHASE_WORLDS["FIT"])
  or p["cohorts"]["CHECK_worlds"]!=list(PHASE_WORLDS["CHECK"])
  or p["cohorts"]["DEV_worlds"]!=list(PHASE_WORLDS["DEV"])
  or p["cohorts"]["public_calibration"]!=list(INPUTS)
  or p["methods"]!=list(METHODS)):
  raise ValueError("K5D_FROZEN_SOURCE_DRIFT")
 return p

def world_name(seed):
 return "world-"+str(seed)

class GF2Conventional:
 """Independent conventional exact fitted affine system ID on GF(2)."""
 def __init__(self):
  self.lookup={}
  self.events=0
 def learn(self,w,a,b,after):
  if b not in INPUTS or a not in OPS or not 0<=after<64:
   raise ValueError("K5D_CONVENTIONAL_UNLAWFUL_SOURCE")
  d=self.lookup.setdefault(w,{}).setdefault(a,{})
  if b in d:raise ValueError("K5D_CONVENTIONAL_DUPLICATE_FIT")
  d[b]=after;self.events+=1
 def step(self,w,a,x):
  row=self.lookup[w][a]
  if set(row)!=set(INPUTS):raise ValueError("K5D_CONVENTIONAL_PUBLIC_INFO_INCOMPLETE")
  zero=row[0]
  # Matrix columns for linear component are constructed independently,
  # never from native R6 model internals.
  columns=[row[1<<i]^zero for i in range(6)]
  state=zero
  for i in range(6):
   if x>>i&1:state^=columns[i]
  return state
 def predict(self,w,x,actions):
  for a in actions:x=self.step(w,a,x)
  return x
 def size(self):
  return len(canonical(self.lookup).encode())

class SingleStepNearest:
 def __init__(self):
  self.rows={};self.events=0
 def learn(self,w,a,b,result):
  self.rows.setdefault(w,{}).setdefault(a,[]).append((b,result))
  self.events+=1
 def predict(self,w,x,actions):
  for a in actions:
   observations=self.rows[w][a]
   before,after=min(observations,key=lambda z:((z[0]^x).bit_count(),z[0]))
   x=after
  return x
 def size(self):return len(canonical(self.rows).encode())

def calibrate(seed,native,conventional,nearest):
 w=world_name(seed)
 env=CausalSixBitWorld(seed)
 corpus=[]
 for x in INPUTS:
  for a in OPS:
   env.reset(x)
   before,action,after=env.step(a)
   if before!=x or action!=a:
    raise ValueError("K5D_SIMULATOR_CANNOT_REPORT_PUBLIC_ACTION")
   corpus.append({"world":w,"input":before,"op":a,"real_output":after})
   native.learn(w,a,before,after)
   conventional.learn(w,a,before,after)
   nearest.learn(w,a,before,after)
 if len(corpus)!=21 or {z["input"] for z in corpus}!=set(INPUTS):
  raise ValueError("K5D_PUBLIC_COUNTERFACTUAL_SUPPORT_MISSING")
 return corpus

def sequences(seed,phase):
 plan=[]
 for i in range(16 if phase=="DEV" else 8):
  rng=random.Random(770001+seed*10007+i*97+(0 if phase=="DEV" else 551100))
  states=[s for s in range(64) if 2<=s.bit_count()<=4 and s not in INPUTS]
  initial=states[rng.randrange(len(states))]
  n=3 if i%2==0 else 5
  actions=[rng.randrange(3) for _ in range(n)]
  if len(set(actions))<2:actions[-1]=(actions[-1]+1)%3
  plan.append((initial,actions))
 return plan

def evaluate(phase,models,source_native):
 native,conventional,nearest=models
 worlds=PHASE_WORLDS[phase];last=world_name(worlds[-1])
 rows=[];by_model={m:{"wall_seconds":0.,"queries":0} for m in METHODS}
 for seed in worlds:
  world=CausalSixBitWorld(seed);w=world_name(seed)
  for i,(state,actions) in enumerate(sequences(seed,phase)):
   predictions={}
   for method in METHODS:
    start=time.perf_counter()
    if method=="ygg_R6_native_composition":forecast=native.predict(w,state,actions)
    elif method=="ygg_R6_no_composition":forecast=native.predict(w,state,[actions[-1]])
    elif method=="ygg_R6_no_world_memory":forecast=native.predict(last,state,actions)
    elif method=="conventional_GF2_solver":forecast=conventional.predict(w,state,actions)
    elif method=="conventional_single_step_1NN":forecast=nearest.predict(w,state,actions)
    else:forecast=state
    cost=time.perf_counter()-start
    by_model[method]["wall_seconds"]+=cost
    by_model[method]["queries"]+=1
    if type(forecast)is not int or not 0<=forecast<64:
     raise ValueError("K5D_UNLAWFUL_MODEL_OUTPUT")
    predictions[method]=forecast
   # Forecasts are determined BEFORE any true composed DEV outcomes.
   observed=[];world.reset(state)
   for a in actions:
    before,act,next_state=world.step(a)
    observed.append({"before":before,"action":act,"actual_after":next_state})
   terminal=world.current()
   rows.append({"phase":phase,"seed":seed,"world":w,"trajectory_id":i,
    "public_start":state,"new_action_sequence":actions,
    "original_actual_action_trace":observed,
    "actual_terminal":terminal,
    "pre_committed_predictions":predictions,
    "is_correct":{k:v==terminal for k,v in predictions.items()},
    "full_source_trace_sha256":sha(canonical(observed).encode())})
 return rows,by_model

def science(dev,costs,sizes):
 if len(dev)!=64:raise ValueError("K5D_INCOMPLETE_PUBLIC_HELDOUT")
 outcomes={}
 for method in METHODS:
  by_world={}
  for seed in PHASE_WORLDS["DEV"]:
   group=[r for r in dev if r["seed"]==seed]
   if len(group)!=16:raise ValueError("K5D_NOT_ALL_SEE_UNFAMILIAR_WORLD")
   by_world[str(seed)]=sum(r["is_correct"][method] for r in group)
  outcomes[method]={"total_exact":sum(by_world.values()),"per_unseen_world":by_world,
    "measured_prediction_wall_seconds":costs[method]["wall_seconds"],
    "approx_fitted_checkpoint_bytes":sizes[method]}
 candidate=outcomes["ygg_R6_native_composition"]
 gf2=outcomes["conventional_GF2_solver"]
 gates={"native_at_least_60_of_64":candidate["total_exact"]>=60,
  "native_minimum_10_per_new_world":all(n>=10 for n in candidate["per_unseen_world"].values()),
  "gain_at_least_24_over_no_composition":candidate["total_exact"]-outcomes["ygg_R6_no_composition"]["total_exact"]>=24,
  "equally_informed_GF2_reference_qualified":gf2["total_exact"]>=60}
 bounded=all(gates.values())
 # Cost and bytes are reported as supporting measurements; a quality tie is
 # explicitly a scientific NO-GO on stronger native superiority.
 novel=(candidate["total_exact"]>=gf2["total_exact"]+2
        and candidate["measured_prediction_wall_seconds"]<=gf2["measured_prediction_wall_seconds"]
        and candidate["approx_fitted_checkpoint_bytes"]<=gf2["approx_fitted_checkpoint_bytes"])
 return {"result":"BOUNDED_PUBLIC_CAUSAL_COMPOSITION_LEARNED" if bounded
         else "NO_QUALIFIED_CAUSAL_COMPOSITION_LEARNING",
   "methods":outcomes,"frozen_tests":gates,
   "native_novelty_established":novel,
   "native_is_independently_superior_to_conventional_GF2":novel,
   "synthetic_authored_micro_world_not_original_external_benchmark":True,
   "unfamiliar_worlds_received_same_public_calibration":True,
   "scientific_first_use":False,"scientific_accepted":False}

def run_study():
 from research.native.itd02.r6.composer import LocalCausalComposer
 native=LocalCausalComposer();gf2=GF2Conventional();nn=SingleStepNearest()
 original={};train_time=time.perf_counter()
 for phase in ("FIT","CHECK"):
  original[phase]=[]
  # Multiple rules stored concurrently, with interleaved interventions.
  for seed in PHASE_WORLDS[phase]:
   original[phase]+=calibrate(seed,native,gf2,nn)
 fit_elapsed=time.perf_counter()-train_time
 raw=native.snapshot()
 child="""import json,sys
from research.native.itd02.r6.composer import LocalCausalComposer
o=LocalCausalComposer.restore(sys.stdin.buffer.read())
print(json.dumps({"updates":o.observations,"w401":o.predict("world-401",29,[0,1,2])}))
"""
 p=subprocess.run([sys.executable,"-B","-c",child],input=raw,capture_output=True,timeout=30)
 if p.returncode or json.loads(p.stdout).get("updates")!=126:
  raise ValueError("K5D_COLD_OS_INTERVENTION_MEMORY_DRIFT:"+p.stderr.decode()[-300:])
 native=LocalCausalComposer.restore(raw)
 check,checkcost=evaluate("CHECK",(native,gf2,nn),None)
 # DEV receives only its predeclared public basis calibration, not completed
 # novel sequences or target outputs, before any prospective predictions.
 original["DEV"]=[]
 for seed in PHASE_WORLDS["DEV"]:
  original["DEV"]+=calibrate(seed,native,gf2,nn)
 full_model=native.snapshot()
 native=LocalCausalComposer.restore(full_model)
 dev,devcost=evaluate("DEV",(native,gf2,nn),None)
 sizes={
   "ygg_R6_native_composition":len(full_model),
   "ygg_R6_no_composition":len(full_model),
   "ygg_R6_no_world_memory":len(full_model),
   "conventional_GF2_solver":gf2.size(),
   "conventional_single_step_1NN":nn.size(),
   "fixed_identity":0}
 out={"schema":SCHEMA,"gate":"LCRM01-K5D",
   "result":"COMPLETE_CONSTRUCTED_PUBLIC_CAUSAL_EXPERIMENT",
   "original_public_calibration":original,
   "calibration_source_events":sum(len(v) for v in original.values()),
   "source_native_checkpoint_sha256":sha(full_model),
   "source_native_checkpoint_bytes":len(full_model),
   "source_native_cold_OS_restore":True,
   "native_original_source_FIT_observations":native.observations,
   "source_shared_FIT_wall_seconds":fit_elapsed,
   "CHECK_original_public_traces":check,"DEV_original_public_traces":dev,
   "CHECK_actual_composed_episodes":len(check),
   "DEV_actual_composed_episodes":len(dev),
   "scientific":science(dev,devcost,sizes),
   "scientific_first_use":False,"scientific_accepted":False}
 return out

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",type=Path,required=True)
 args=parser.parse_args()
 if args.output.exists() or not args.output.parent.is_dir():
  raise RuntimeError("K5D_ORIGINAL_RECEIPT_NOT_FRESH")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  p=frozen()
  r=run_study()
  r["frozen_protocol_sha256"]=sha(PIN.read_bytes())
  r["native_R6_original_git_blob"]=NATIVE_BLOB
 except Exception as e:
  r={"schema":SCHEMA,"gate":"LCRM01-K5D","result":"ORIGINAL_SCIENCE_ENGINEERING_BLOCKED",
     "error":str(e),"exception":type(e).__name__,
     "traceback_tail":traceback.format_exc().splitlines()[-13:],
     "scientific_first_use":False,"scientific_accepted":False}
 r["resources"]={"whole_Python_CPU_seconds":time.process_time()-cpu,
   "whole_wall_seconds":time.perf_counter()-wall,
   "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 args.output.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("K5D_ORIGINAL_RESULT="+r["result"])
 if "scientific" in r:
  print("K5D_SCIENCE="+r["scientific"]["result"])
  print("K5D_ACTUAL_COMPOSITION="+canonical(r["scientific"]["methods"]))
 print("K5D_PUBLIC_INTERVENTIONS="+str(r.get("calibration_source_events",0)))
 return int(r["result"]=="ORIGINAL_SCIENCE_ENGINEERING_BLOCKED")
if __name__=="__main__":raise SystemExit(main())

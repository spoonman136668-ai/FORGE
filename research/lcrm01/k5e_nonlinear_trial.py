#!/usr/bin/env python3
"""K5E true non-affine public causal effects, truly interleaved source exposure.

Every original source observation is a REAL executed causal action from an
opaque authored world. Native R7 and independently fitted conventional
models receive identical records, including each new world's calibration.
Original heldout composed outcomes are executed only after all predictions.
"""
import argparse
import hashlib
import itertools
import json
import random
import resource
import subprocess
import sys
import time
import traceback
from pathlib import Path
from k5e_nonlinear_world import NonlinearParentWorld

PIN=Path(__file__).with_name("k5e_frozen_nonlinear.json")
SCHEMA="mass.lcrm01.k5e.original-interleaved-nonlinear-causality-v1"
COHORTS={"FIT":(111,112,113,114),"CHECK":(211,212),"DEV":(311,312,313,314)}
METHODS=("ygg_R7_causal_parent_model","native_R7_no_composition",
         "native_R7_no_world_identity","conventional_exhaustive_triple",
         "conventional_greedy_depth3","conventional_fullstate_1NN","conventional_affine_GF2")
TRIPLES=tuple(itertools.combinations(range(8),3))
SOURCE_BLOB="204ecd993b954b23e66d6d1e8b3568e7c93183c5"
WORLD_BLOB="a43643ee6435f15e42cc671f54a6e401f7188a98"

def canonical(o):return json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False)
def sha(s):return hashlib.sha256(s).hexdigest()

def freeze():
 p=json.loads(PIN.read_text())
 if (p.get("schema")!="mass.lcrm01.k5e.frozen-nonlinear-interleaved-v1"
  or p["parent_K5D"]!="7ce3c69ae8a8445256413318294e273f7dbf4d8a"
  or p["cohorts"]["DEV_worlds"]!=list(COHORTS["DEV"])
  or p["cohorts"]["FIT_worlds"]!=list(COHORTS["FIT"])
  or p["cohorts"]["CHECK_worlds"]!=list(COHORTS["CHECK"])
  or p["methods"]!=list(METHODS)):
  raise ValueError("K5E_FROZEN_PRIMARY_OR_SOURCE_DRIFT")
 return p

def triple_bin(x,p):
 return ((x>>p[0])&1)|(((x>>p[1])&1)<<1)|(((x>>p[2])&1)<<2)

class IndependentExhaustiveTriple:
 """Independently written full 3-parent conventional model; strong novelty veto."""
 def __init__(self):self.rows={};self.models={};self.events=0
 def observe(self,world,action,before,after):
  self.rows.setdefault(world,{}).setdefault(action,[]).append((before,after))
  self.events+=1
 def fit(self):
  for world,acts in self.rows.items():
   learned={}
   for action,source in acts.items():
    if len(source)!=192 or len({x for x,y in source})!=192:
     raise ValueError("K5E_CONVENTIONAL_SOURCE_NOT_IDENTIFIABLE")
    functions=[]
    for bit in range(8):
     best=(float("inf"),None,None)
     for p in TRIPLES:
      # A different implementation from source-native: encode (input/output)
      # joint bins and minimize empirical classification disagreement.
      samples=[[] for _ in range(8)]
      for x,y in source:samples[triple_bin(x,p)].append((y>>bit)&1)
      table=[int(sum(q)*2>=len(q)) if q else 0 for q in samples]
      wrong=sum(sum(z!=table[i] for z in vals) for i,vals in enumerate(samples))
      if wrong<best[0]:best=(wrong,p,table)
     functions.append([list(best[1]),best[2]])
    learned[action]=functions
   self.models[world]=learned
  self.rows={}
 def predict(self,world,state,actions):
  for action in actions:
   result=0
   for bit,(parents,values) in enumerate(self.models[world][action]):
    result|=values[triple_bin(state,parents)]<<bit
   state=result
  return state
 def size(self):return len(canonical(self.models).encode())

class GreedyDepth3Tree:
 """Conventional greedy decision tree, no structural 3-parent oracle."""
 def __init__(self):self.rows={};self.models={};self.events=0
 def observe(self,w,a,x,y):self.rows.setdefault(w,{}).setdefault(a,[]).append((x,y));self.events+=1
 def tree(self,source,bit,depth,used=()):
  ones=sum((y>>bit)&1 for _,y in source)
  if depth==0 or ones==0 or ones==len(source) or not source:return ["leaf",int(2*ones>=len(source))]
  best=None
  for feature in range(8):
   if feature in used:continue
   left=[p for p in source if not ((p[0]>>feature)&1)]
   right=[p for p in source if (p[0]>>feature)&1]
   if not left or not right:continue
   def impurity(rows):
    n=len(rows);n1=sum((y>>bit)&1 for _,y in rows)
    return 2*n1*(n-n1)/n
   cost=impurity(left)+impurity(right)
   if best is None or cost<best[0]:best=(cost,feature,left,right)
  if best is None:return ["leaf",int(2*ones>=len(source))]
  return ["split",best[1],self.tree(best[2],bit,depth-1,used+(best[1],)),
          self.tree(best[3],bit,depth-1,used+(best[1],))]
 def fit(self):
  for w,arms in self.rows.items():
   self.models[w]={}
   for a,rows in arms.items():
    if len(rows)!=192:raise ValueError("K5E_TREE_MISSING_PUBLIC_SOURCE")
    self.models[w][a]=[self.tree(rows,bit,3) for bit in range(8)]
  self.rows={}
 def single(self,w,a,state):
  final=0
  for bit,node in enumerate(self.models[w][a]):
   while node[0]=="split":node=node[2] if not(state>>node[1]&1) else node[3]
   final|=node[1]<<bit
  return final
 def predict(self,w,state,actions):
  for action in actions:state=self.single(w,action,state)
  return state
 def size(self):return len(canonical(self.models).encode())

class FullState1NN:
 def __init__(self):self.rows={};self.events=0
 def observe(self,w,a,x,y):self.rows.setdefault(w,{}).setdefault(a,[]).append((x,y));self.events+=1
 def fit(self):pass
 def predict(self,w,state,actions):
  for action in actions:
   x,y=min(self.rows[w][action],key=lambda r:((r[0]^state).bit_count(),r[0]))
   state=y
  return state
 def size(self):return len(canonical(self.rows).encode())

class AffineGF2:
 """Conventional affine approximation learned by GF2 elimination from same rows."""
 def __init__(self):self.rows={};self.coefficients={};self.events=0
 def observe(self,w,a,x,y):self.rows.setdefault(w,{}).setdefault(a,[]).append((x,y));self.events+=1
 def fit(self):
  for w,acts in self.rows.items():
   self.coefficients[w]={}
   for a,source in acts.items():
    rows=[]
    for x,y in source:rows.append((1|(x<<1),y))
    pivots={}
    for xs,ys in rows:
     for bit in reversed(range(9)):
      if xs>>bit&1:
       if bit in pivots:
        xx,yy=pivots[bit];xs^=xx;ys^=yy
       else:pivots[bit]=(xs,ys);break
    masks=[0]*9
    # Reduce selected independent rows into a plausible GF2 affine estimate;
    # inconsistent nonlinear rows cannot be satisfied by any affine model.
    coeff=[0]*9
    for bit in range(9):
     if bit in pivots:
      xs,ys=pivots[bit]
      for j in range(bit):
       if xs>>j&1:ys^=coeff[j]
      coeff[bit]=ys
    self.coefficients[w][a]=coeff
  self.rows={}
 def predict(self,w,x,actions):
  for a in actions:
   coeff=self.coefficients[w][a];n=coeff[0]
   for bit in range(8):
    if x>>bit&1:n^=coeff[bit+1]
   x=n
  return x
 def size(self):return len(canonical(self.coefficients).encode())

def original_source(native,conventional,tree,nn,affine):
 worlds=tuple(seed for phase in ("FIT","CHECK","DEV") for seed in COHORTS[phase])
 public={seed:[random.Random(9417000+seed*1009+a*43).sample(range(256),192)
               for a in range(3)] for seed in worlds}
 simulators={seed:NonlinearParentWorld(seed) for seed in worlds}
 original=[]
 for i in range(192):
  for seed in worlds:
   w="w"+str(seed)
   for a in range(3):
    x=public[seed][a][i]
    sim=simulators[seed];sim.reset(x)
    before,act,after=sim.step(a)
    if before!=x or act!=a:raise ValueError("K5E_FALSE_SIMULATOR_INTERVENTION")
    original.append({"source_index":i,"world":seed,"action":a,
                     "public_before":before,"observed_real_after":after})
    for method in (native,conventional,tree,nn,affine):method.observe(w,a,before,after)
 if len(original)!=5760:raise ValueError("K5E_INTERLEAVED_SOURCE_LENGTH_DRIFT")
 for seed in worlds:
  for a in range(3):
   src=[q["public_before"] for q in original if q["world"]==seed and q["action"]==a]
   if len(src)!=192 or len(set(src))!=192:
    raise ValueError("K5E_NOT_DISTINCT_PUBLIC_INTERVENTIONS")
 if any(original[i+30]["source_index"]!=original[i]["source_index"]+1
        for i in range(0,5700,30)):
  raise ValueError("K5E_SOURCE_NOT_INTERLEAVED")
 return original

def novel_sequences(seed,phase):
 q=[]
 for i in range(16 if phase=="DEV" else 8):
  r=random.Random(seed*100003+850000+i*97)
  start=r.randrange(256)
  n=3 if i%2==0 else 5
  actions=[r.randrange(3) for _ in range(n)]
  if len(set(actions))<2:actions[-1]=(actions[-1]+1)%3
  q.append((start,actions))
 return q

def actual_evaluation(phase,models,last):
 native,conv,tree,nn,affine=models
 methodsizes={
 "ygg_R7_causal_parent_model":len(native.checkpoint()),
 "native_R7_no_composition":len(native.checkpoint()),
 "native_R7_no_world_identity":len(native.checkpoint()),
 "conventional_exhaustive_triple":conv.size(),
 "conventional_greedy_depth3":tree.size(),
 "conventional_fullstate_1NN":nn.size(),
 "conventional_affine_GF2":affine.size()}
 elapsed={m:0. for m in METHODS};observed=[]
 for seed in COHORTS[phase]:
  sim=NonlinearParentWorld(seed);w="w"+str(seed)
  for trial,(start,actions) in enumerate(novel_sequences(seed,phase)):
   preds={}
   for method in METHODS:
    t=time.perf_counter()
    if method=="ygg_R7_causal_parent_model":v=native.predict(w,start,actions)
    elif method=="native_R7_no_composition":v=native.predict(w,start,[actions[-1]])
    elif method=="native_R7_no_world_identity":v=native.predict(last,start,actions)
    elif method=="conventional_exhaustive_triple":v=conv.predict(w,start,actions)
    elif method=="conventional_greedy_depth3":v=tree.predict(w,start,actions)
    elif method=="conventional_fullstate_1NN":v=nn.predict(w,start,actions)
    else:v=affine.predict(w,start,actions)
    elapsed[method]+=time.perf_counter()-t
    if type(v)is not int or not 0<=v<256:
     raise ValueError("K5E_ILLEGAL_PUBLIC_PREDICTION")
    preds[method]=v
   real=[];sim.reset(start)
   for a in actions:
    before,action,after=sim.step(a)
    real.append({"before":before,"action":action,"actual_after":after})
   outcome=sim.current()
   observed.append({"phase":phase,"seed":seed,"trial":trial,"public_initial":start,
     "action_sequence":actions,"predicted_before_execution":preds,
     "real_action_consequence_trace":real,
     "real_final_state":outcome,
     "exact":{m:p==outcome for m,p in preds.items()},
     "trace_sha256":sha(canonical(real).encode())})
 return observed,elapsed,methodsizes

def verdict(rows,elapsed,sizes):
 by={}
 for m in METHODS:
  worlds={}
  for seed in COHORTS["DEV"]:
   q=[row for row in rows if row["seed"]==seed]
   if len(q)!=16:raise ValueError("K5E_MISSING_ORIGINAL_NEW_WORLD")
   worlds[str(seed)]=sum(row["exact"][m] for row in q)
  by[m]={"correct":sum(worlds.values()),"per_world":worlds,
         "inference_wall_seconds":elapsed[m],"checkpoint_bytes":sizes[m]}
 p=by["ygg_R7_causal_parent_model"];c=by["conventional_exhaustive_triple"]
 gates={"native_60_of_64":p["correct"]>=60,
   "every_new_world_12_of_16":all(v>=12 for v in p["per_world"].values()),
   "at_least_24_gains_over_no_comp":p["correct"]-by["native_R7_no_composition"]["correct"]>=24,
   "strong_conventional_identification":c["correct"]>=60}
 novel=(p["correct"]>=c["correct"]+2 and
        p["checkpoint_bytes"]<=c["checkpoint_bytes"] and
        p["inference_wall_seconds"]<=c["inference_wall_seconds"])
 return {"result":"BOUNDED_LEARNED_NONLINEAR_CAUSAL_COMPOSITION" if all(gates.values())
    else "NO_QUALIFIED_NONLINEAR_CAUSAL_TRANSFER",
    "methods":by,"frozen_primary":gates,"native_architecture_superiority":novel,
    "constructed_micro_world_not_external":True,
    "public_calibration_at_new_worlds":True,
    "original_source_genuinely_interleaved":True,
    "scientific_first_use":False,"scientific_accepted":False}

def study():
 from research.native.itd02.r7.learner import NonlinearLocalLearner
 models=(NonlinearLocalLearner(),IndependentExhaustiveTriple(),GreedyDepth3Tree(),
         FullState1NN(),AffineGF2())
 t=time.perf_counter();source=original_source(*models)
 source_wall=time.perf_counter()-t
 fitcost={}
 for name,model in zip(("native_R7","strong_exhaustive_triple","greedy_tree","fullstate_1nn","affine_GF2"),models):
  started=time.perf_counter();model.fit();fitcost[name]=time.perf_counter()-started
 raw=models[0].checkpoint()
 child="""import json,sys
from research.native.itd02.r7.learner import NonlinearLocalLearner
n=NonlinearLocalLearner.restore(sys.stdin.buffer.read())
print(json.dumps({"events":n.events,"worlds":len(n.models),"check":n.predict("w111",97,[0,1,2])}))
"""
 z=subprocess.run([sys.executable,"-B","-c",child],input=raw,capture_output=True,timeout=30)
 if z.returncode or json.loads(z.stdout).get("events")!=5760:
  raise ValueError("K5E_SOURCE_NATIVE_COLD_RESTART_FAILED:"+z.stderr.decode()[-300:])
 native=NonlinearLocalLearner.restore(raw)
 models=(native,)+models[1:]
 check,checkcost,_=actual_evaluation("CHECK",models,"w"+str(COHORTS["DEV"][-1]))
 dev,devcost,sizes=actual_evaluation("DEV",models,"w"+str(COHORTS["DEV"][-1]))
 return {"schema":SCHEMA,"result":"COMPLETE_ORIGINAL_NONLINEAR_INTERLEAVED_STUDY",
   "source_interleaved_public_actions":source,
   "source_intervention_count":len(source),"original_native_source_cold_OS":True,
   "source_owned_native_checkpoint_sha256":sha(raw),
   "source_owned_native_checkpoint_bytes":len(raw),
   "FIT_shared_source_wall_seconds":source_wall,"per_model_fitting_wall_seconds":fitcost,
   "CHECK_original_action_traces":check,"DEV_original_action_traces":dev,
   "CHECK_composed_episodes":len(check),"DEV_composed_episodes":len(dev),
   "scientific":verdict(dev,devcost,sizes),
   "scientific_first_use":False,"scientific_accepted":False}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",required=True,type=Path)
 a=p.parse_args()
 if a.output.exists() or not a.output.parent.is_dir():raise RuntimeError("K5E_OUTPUT_NOT_FRESH")
 cpu=time.process_time();wall=time.perf_counter()
 try:
  frozen()
  result=study()
  result["frozen_protocol_sha256"]=sha(PIN.read_bytes())
  result["source_native_R7_git_blob"]=SOURCE_BLOB
  result["original_micro_world_git_blob"]=WORLD_BLOB
 except Exception as e:
  result={"schema":SCHEMA,"result":"SOURCE_OR_EXPERIMENT_ENGINEERING_BLOCKED",
    "exception":type(e).__name__,"error":str(e),
    "traceback_tail":traceback.format_exc().splitlines()[-14:],
    "scientific_first_use":False,"scientific_accepted":False}
 result["resources"]={"process_Python_CPU_seconds":time.process_time()-cpu,
   "process_wall_seconds":time.perf_counter()-wall,
   "peak_Python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024}
 a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("K5E_ORIGINAL_RESULT="+result["result"])
 if "scientific" in result:
  print("K5E_SCIENTIFIC="+result["scientific"]["result"])
  print("K5E_METHODS="+canonical(result["scientific"]["methods"]))
 print("K5E_REAL_SOURCE="+str(result.get("source_intervention_count",0)))
 return int(result["result"]=="SOURCE_OR_EXPERIMENT_ENGINEERING_BLOCKED")
if __name__=="__main__":raise SystemExit(main())

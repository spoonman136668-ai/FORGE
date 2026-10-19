"""T10 Mass: eight-byte learned cross-task nonlinear causal map.

All tasks are arbitrary nibble permutations with an independently hidden
shared ancestor. OPEN carries an independent one-swap change; 8 PUBLIC
first-round nibble witness requests are paid and identically available to
controls. No operator-family tags, private ancestor, or hidden labels enter
training. Source-neutral only; no signed scientific first use.
"""
import random,json,time,tracemalloc,importlib.util,sys
from pathlib import Path
D=Path(__file__).parent;TRAIN=range(-24015,-23999);OPEN=range(-24107,-24099)
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def ancestor():
 return random.Random(129337).sample(range(16),16)
def source(seed,m):
 assert seed in TRAIN or seed in OPEN
 rng=random.Random(12237+abs(seed)*60733)
 p=ancestor();a,b=rng.sample(range(16),2);p[a],p[b]=p[b],p[a]
 packed=m.pack(p)
 xs=rng.sample(range(65536),64)
 clean=[m.forward(x,packed) for x in xs]
 noise=set(rng.sample(range(48),6))
 public=[(x,y^(1 if j in noise else 0))
        for j,(x,y) in enumerate(zip(xs[:48],clean[:48]))]
 sampled=rng.sample(range(16),8)
 public_witness=tuple((i,p[i]) for i in sampled) # public first-round requests
 private=tuple(zip(xs[48:],clean[48:]))
 return (tuple(public[:40]),tuple(public[40:]),public_witness,private)
def prior_fit(rows,m):
 # Learn full bijection via repeated PUBLIC intermediate value evidence
 # across independent TRAIN tasks; only the 8B permutation persists.
 votes=[[0]*16 for _ in range(16)]
 for fit,check,witness,private in rows:
  for x,y in witness:votes[x][y]+=1
 pairs=sorted(((votes[i][j],i,j) for i in range(16) for j in range(16)),reverse=True)
 perm=[None]*16;chosen=set()
 for count,i,j in pairs:
  if perm[i] is None and j not in chosen:
   perm[i]=j;chosen.add(j)
 assert sorted(perm)==list(range(16))
 return m.pack(perm),{"public_votes":sum(map(sum,votes)),"TRAIN_tasks":len(rows),
                       "shared_parameter_bytes":8}
def infer_from_public(m,prior,witness,mode):
 if mode=="identity":state=list(range(16))
 else:state=list(m.unpack(prior))
 # Fix publicly witnessed entries, then assign remaining by prior preference.
 forced={x:y for x,y in witness}
 assert len(forced)==len(witness) and len(set(forced.values()))==len(forced)
 used=set(forced.values());result=[None]*16
 for x,y in forced.items():result[x]=y
 for x in range(16):
  if result[x] is None and state[x] not in used:
   result[x]=state[x];used.add(state[x])
 unused=[y for y in range(16) if y not in used]
 for x in range(16):
  if result[x] is None:result[x]=unused.pop(0)
 assert sorted(result)==list(range(16))
 return m.pack(result)
def measure(f):
 tracemalloc.start();t=time.process_time_ns();v=f()
 r={"cpu_ns":time.process_time_ns()-t,
    "Python_peak_bytes":tracemalloc.get_traced_memory()[1]}
 tracemalloc.stop();return v,r
def score(m,model,hold):
 return sum(m.forward(x,model)==y for x,y in hold)
def main():
 frozen=json.loads((D/"20261019-mass-t10-preregister.json").read_text())
 assert frozen["parent_head"]=="26a1a81d8ca2f84e995ce28fc59db7de4a6a63f2" and not frozen["authority"]["protected_original_first_use"]
 m=load(D/"20261018-mass-t3-learned-sbox.py","mass_t10_sbox")
 trainrows=[source(seed,m) for seed in TRAIN]
 openrows=[source(seed,m) for seed in OPEN]
 (prior,meta),tcost=measure(lambda:prior_fit(trainrows,m))
 assert len(prior)==8 and meta["public_votes"]==128
 outputs=[]
 for fit,check,public_witness,hold in openrows:
  (learned,lc)=measure(lambda:infer_from_public(m,prior,public_witness,"learned"))
  (identity,ic)=measure(lambda:infer_from_public(m,prior,public_witness,"identity"))
  (full,bc)=measure(lambda:infer_from_public(m,prior,public_witness,"full_prior"))
  ((local,info),fc)=measure(lambda:m.fit_public(fit,check))
  outputs.append({"learned_correct":score(m,learned,hold),
   "identity_correct":score(m,identity,hold),
   "strongest_same_prior_public_control_correct":score(m,full,hold),
   "T3_public_fit_correct":score(m,local,hold),
   "public_causal_queries":len(public_witness),
   "candidate_fit_cost":lc,"same_prior_control_cost":bc,
   "identity_cost":ic,"T3_public_fit_cost":fc})
 tot=lambda k:sum(x[k] for x in outputs)
 result={"schema":"mass.t10.learned-8byte-causal-map.v1",
  "TRAIN_tasks":len(trainrows),"OPEN_tasks":len(openrows),
  "public_intermediate_witnesses_per_OPEN_task":8,
  "source_public_fit_each":40,"public_check_each":8,
  "separately_unseen_final_outputs":len(outputs)*16,
  "model_shared_bijection_bytes":8,
  "TRAIN_sourceblind_public_votes":meta["public_votes"],
  "TRAIN_model_differs_from_identity":prior!=m.pack(list(range(16))),
  "learned_exact_outputs":tot("learned_correct"),
  "identity_exact_outputs":tot("identity_correct"),
  "strongest_same_train_and_public_control_exact":tot("strongest_same_prior_public_control_correct"),
  "unchanged_T3_public_only_fit_exact":tot("T3_public_fit_correct"),
  "TRAIN_CPU_peak":tcost,
  "OPEN_candidate_CPU_ns":sum(x["candidate_fit_cost"]["cpu_ns"] for x in outputs),
  "OPEN_control_CPU_ns":sum(x["same_prior_control_cost"]["cpu_ns"] for x in outputs),
  "learned_peak_including_training":max(tcost["Python_peak_bytes"],
    max(x["candidate_fit_cost"]["Python_peak_bytes"] for x in outputs)),
  "strongest_control_fit_peak":max(x["same_prior_control_cost"]["Python_peak_bytes"] for x in outputs),
  "full_public_witness_service_cost_accounted":False,
  "full_resource_parity":False,"new_operator_family_replication":False,
  "novel_arbitrary_permutation_transfer_conclusion":"source shares hidden ancestor and a one-swap shift; in-family latent relation only",
  "protected_ORIGINAL_MNS_used":0,"science_accepted":False,
  "cases":outputs}
 print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()

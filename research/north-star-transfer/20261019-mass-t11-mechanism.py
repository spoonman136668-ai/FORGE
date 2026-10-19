"""T11 Mass: incomplete PUBLIC first-round evidence vs a learned 8B prior.

Independent random 16! Sboxes per task; four first-round 16-bit
public witnesses disclose only the nibble transitions they touch. PRIVATE
held final outputs never feed fitting. Coverage and number of compatible
public table completions are audited. TRAIN prior is public-only, not a
source-specific label. No protected/consumed experimental source.
"""
from __future__ import annotations
import random,json,sys,math,importlib.util,time,tracemalloc
from pathlib import Path
D=Path(__file__).parent;TRAIN=range(-28015,-27999);OPEN=range(-28107,-28099)
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s)
 sys.modules[n]=m;s.loader.exec_module(m);return m
def measured(fn):
 tracemalloc.start();t=time.process_time_ns()
 val=fn();rec={"cpu_ns":time.process_time_ns()-t,
   "Python_peak_bytes":tracemalloc.get_traced_memory()[1]}
 tracemalloc.stop();return val,rec
def source(seed,m):
 assert seed in TRAIN or seed in OPEN
 rng=random.Random(280029+abs(seed)*35113)
 p=rng.sample(range(16),16)
 truth=m.pack(p);inputs=rng.sample(range(65536),64)
 outputs=[m.forward(x,truth) for x in inputs]
 corrupt=set(rng.sample(range(48),6))
 public=[(x,outputs[j]^(1 if j in corrupt else 0))
         for j,x in enumerate(inputs[:48])]
 first_round=tuple((x,m.apply_sbox(x,p)) for x in inputs[:4])
 held=tuple(zip(inputs[48:],outputs[48:]))
 assert len(first_round)==4 and len(held)==16
 return tuple(public[:40]),tuple(public[40:]),first_round,held
def count_covered(witness):
 pairs={}
 for x,y in witness:
  for shift in (0,4,8,12):
   a,b=(x>>shift)&15,(y>>shift)&15
   assert a not in pairs or pairs[a]==b
   pairs[a]=b
 assert len(set(pairs.values()))==len(pairs)
 return len(pairs),math.factorial(16-len(pairs))
def main():
 f=json.loads((D/"20261019-mass-t11-freeze.json").read_text())
 assert f["schema"]=="northstar.t11.mass.preregister.v1" and f["parent_exact_head"]=="cea317225f4985fd4d29ec221fe7296fdc8a3092"
 t10=load(D/"20261019-mass-t10-shared-map.py","mass_t11_frozen_t10")
 m=load(D/"20261018-mass-t3-learned-sbox.py","mass_t11_native_sbox")
 trainrows=[source(seed,m) for seed in TRAIN]
 openrows=[source(seed,m) for seed in OPEN]
 (prior,fit),traincost=measured(lambda:t10.prior_fit(trainrows,m))
 assert len(prior)==8 and prior!=m.pack(list(range(16)))
 rows=[]
 for FIT,CHECK,first_round,held in openrows:
  coverage,completions=count_covered(first_round)
  candidate,cc=measured(lambda:t10.infer_from_public(m,prior,first_round,"learned"))
  identity,ic=measured(lambda:t10.infer_from_public(m,prior,first_round,"identity"))
  same_prior,pc=measured(lambda:t10.infer_from_public(m,prior,first_round,"full_prior"))
  (original,ocdiag),oc=measured(lambda:m.fit_public(FIT,CHECK))
  score=lambda model:sum(m.forward(x,model)==y for x,y in held)
  rows.append({"distinct_public_nibble_entries":coverage,
   "remaining_consistent_bijection_completions":completions,
   "learned_exact":score(candidate),"identity_exact":score(identity),
   "strongest_same_prior_exact":score(same_prior),"T3_public_only_exact":score(original),
   "candidate_CPU_peak":cc,"control_CPU_peak":pc,
   "identity_CPU_peak":ic,"T3_CPU_peak":oc,
   "first_round_public_observations":len(first_round),
   "public_final_FIT":len(FIT),"public_final_CHECK":len(CHECK),
   "private_final_held":len(held)})
 totals=lambda k:sum(x[k] for x in rows)
 out={"schema":"mass.t11.incomplete-public-causal-evidence.v1",
  "TRAIN_tasks":len(trainrows),"OPEN_tasks":len(openrows),
  "public_first_round_witnesses_per_OPEN":4,
  "mean_distinct_nibble_mappings":totals("distinct_public_nibble_entries")/len(rows),
  "lowest_remaining_permutation_completions":min(x["remaining_consistent_bijection_completions"] for x in rows),
  "highest_remaining_permutation_completions":max(x["remaining_consistent_bijection_completions"] for x in rows),
  "learned_exact_unseen":totals("learned_exact"),
  "identity_exact_unseen":totals("identity_exact"),
  "strongest_same_prior_exact_unseen":totals("strongest_same_prior_exact"),
  "T3_public_only_exact_unseen":totals("T3_public_only_exact"),
  "unseen_outputs":len(rows)*16,"learned_parameter_bytes":8,
  "public_TRAIN_nibble_vote_count":fit["public_votes"],
  "TRAIN_CPU_peak":traincost,
  "candidate_fit_CPU_ns":sum(r["candidate_CPU_peak"]["cpu_ns"] for r in rows),
  "same_prior_control_fit_CPU_ns":sum(r["control_CPU_peak"]["cpu_ns"] for r in rows),
  "candidate_peak_including_TRAIN":max(traincost["Python_peak_bytes"],
                       max(r["candidate_CPU_peak"]["Python_peak_bytes"] for r in rows)),
  "same_information_control_fit_peak":max(r["control_CPU_peak"]["Python_peak_bytes"] for r in rows),
  "complete_public_observation_acquisition_cost_measured":False,
  "final_40_8_noisy_outputs_exploited_by_prior_candidate":False,
  "science_accepted":False,"consumed_MNS_or_T10_original_source_replayed":False,
  "rows":rows}
 assert out["unseen_outputs"]==128 and all(r["remaining_consistent_bijection_completions"]>=1 for r in rows)
 print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

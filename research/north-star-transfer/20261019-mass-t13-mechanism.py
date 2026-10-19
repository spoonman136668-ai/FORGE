"""T13 Mass: sparse TRAIN-shared latent nonlinear state under noisy public FIT.

Sixteen TRAIN + eight OPEN Sboxes share UNKNOWN seeded random permutation
ancestor, and each source independently changes two disjoint nibble swaps.
This is IN-FAMILY latent transfer, never a genuinely novel operator family.
The model fits a TRAIN-only eight-byte prior from TWO public round-one
witnesses per task, then a fixed eight swap public FIT refinement.
Untrained identity and strongest equally trained empirical prior see
identical FIT/CHK/witnesses and source-blind budget.
"""
from __future__ import annotations
import random,math,itertools,json,sys,importlib.util,time,tracemalloc
from pathlib import Path
D=Path(__file__).parent
TRAIN=range(-36015,-35999);OPEN=range(-36107,-36099)
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s)
 sys.modules[n]=m;s.loader.exec_module(m);return m
def measured(fn):
 tracemalloc.start();t=time.process_time_ns();v=fn()
 r={"cpu_ns":time.process_time_ns()-t,
 "Python_peak_bytes":tracemalloc.get_traced_memory()[1]}
 tracemalloc.stop();return v,r
def born(seed,m):
 assert seed in TRAIN or seed in OPEN
 rng=random.Random(65187+abs(seed)*17371)
 p=random.Random(88123029).sample(range(16),16)
 idx=rng.sample(range(16),4)
 p[idx[0]],p[idx[1]]=p[idx[1]],p[idx[0]]
 p[idx[2]],p[idx[3]]=p[idx[3]],p[idx[2]]
 model=m.pack(p)
 xs=rng.sample(range(65536),36)
 truth=[m.forward(x,model) for x in xs]
 bad=set(rng.sample(range(20),2))
 obs=tuple((x,truth[i]^(1 if i in bad else 0))
           for i,x in enumerate(xs[:20]))
 witness=tuple((x,m.apply_sbox(x,p)) for x in xs[:2])
 hold=tuple(zip(xs[20:],truth[20:]))
 assert len(obs)==20 and len(witness)==2 and len(hold)==16
 return obs[:16],obs[16:],witness,hold
def forced_from_public(witness):
 result={}
 for x,y in witness:
  for bits in (0,4,8,12):
   a,b=(x>>bits)&15,(y>>bits)&15
   assert a not in result or result[a]==b
   result[a]=b
 assert len(set(result.values()))==len(result)
 return result
def refine(m,t10,prior,FIT,CHECK,witness,kind):
 assert len(FIT)==16 and len(CHECK)==4 and len(witness)==2
 required=forced_from_public(witness)
 before=t10.infer_from_public(m,prior,witness,kind)
 p=list(m.unpack(before))
 free=[i for i in range(16) if i not in required]
 options=list(itertools.combinations(free,2))
 assert len(options)>=8
 error=lambda v:sum((m.forward(x,m.pack(v))^y).bit_count()
                       for x,y in FIT)
 current_error=error(p);proposals=0;improvements=0
 for step in range(8):
  i,j=options[(step*7)%len(options)]
  alt=p[:];alt[i],alt[j]=alt[j],alt[i]
  loss=error(alt);proposals+=1
  if loss<current_error:
   p=alt;current_error=loss;improvements+=1
 for x,y in required:assert p[x]==y
 check=sum((m.forward(x,m.pack(p))^y).bit_count() for x,y in CHECK)
 return m.pack(p),{"FIT_bit_errors":current_error,
  "CHECK_bit_errors":check,"sourceblind_fixed_proposals":proposals,
  "improving_swaps":improvements,"distinct_public_nibbles":len(required),
  "held_source_truth_used_for_fit":False}
def main():
 f=json.loads((D/"20261019-mass-t13-freeze.json").read_text())
 assert f["schema"]=="northstar.t13.mass.preimplementation-freeze.v1"
 assert f["science_head_parent"]=="470340b70bcb5a2ef911a22fcaad063194af1eaa"
 assert not f["safety"]["protected_science_first_use"]
 t10=load(D/"20261019-mass-t10-shared-map.py","mass_t13_t10")
 m=load(D/"20261018-mass-t3-learned-sbox.py","mass_t13_native")
 rows=[born(s,m) for s in TRAIN];tests=[born(s,m) for s in OPEN]
 (prior,fit),tcost=measured(lambda:t10.prior_fit(rows,m))
 identity=m.pack(tuple(range(16)))
 records=[]
 for FIT,CHECK,witness,hold in tests:
  (candidate,info),ccost=measured(lambda:refine(m,t10,prior,FIT,CHECK,witness,"learned"))
  (no_prior,zinfo),zcost=measured(lambda:refine(m,t10,identity,FIT,CHECK,witness,"identity"))
  (empirical,einfo),ecost=measured(lambda:refine(m,t10,prior,FIT,CHECK,witness,"full_prior"))
  def score(model):return sum(m.forward(x,model)==y for x,y in hold)
  records.append({"learned_exact":score(candidate),
   "untrained_identity_exact":score(no_prior),
   "same_TRAIN_empirical_prior_control_exact":score(empirical),
   "public_witness_coverage":info["distinct_public_nibbles"],
   "learner_accepted_swaps":info["improving_swaps"],
   "control_accepted_swaps":zinfo["improving_swaps"],
   "learned_model_cost":ccost,"identity_control_cost":zcost,
   "empirical_control_cost":ecost,
   "sourceblind_FIT":len(FIT),"sourceblind_CHECK":len(CHECK),
   "evaluator_only_private":len(hold)})
 tot=lambda k:sum(z[k] for z in records)
 out={"schema":"mass.t13.shared-latent-public-two-witness-learning.v1",
  "TRAIN_source_neutral":len(rows),"OPEN_source_neutral":len(tests),
  "source_relation":"independent two disjoint swaps from unknown shared latent permutation; not OOD",
  "public_witnesses_per_task":2,"public_noisy_FIT":16,
  "public_CHECK":4,"corrupted_public_y_per_task":2,
  "private_unseen_outputs":tot("evaluator_only_private"),
  "model_bytes":8,"TRAIN_public_vote_count":fit["public_votes"],
  "learned_correct":tot("learned_exact"),
  "same_information_untrained_correct":tot("untrained_identity_exact"),
  "same_information_empirical_TRAIN_prior_control_correct":tot("same_TRAIN_empirical_prior_control_exact"),
  "learned_equals_same_TRAIN_control_by_design":tot("learned_exact")==tot("same_TRAIN_empirical_prior_control_exact"),
  "sourceblind_proposals_per_task":8,
  "TRAIN_CPU_peak":tcost,
  "learned_model_CPU_ns":sum(z["learned_model_cost"]["cpu_ns"] for z in records),
  "untrained_model_CPU_ns":sum(z["identity_control_cost"]["cpu_ns"] for z in records),
  "learned_full_peak_including_training":max(tcost["Python_peak_bytes"],
      *(z["learned_model_cost"]["Python_peak_bytes"] for z in records)),
  "untrained_fit_peak":max(z["identity_control_cost"]["Python_peak_bytes"] for z in records),
  "remote_public_service_complete_cost":False,
  "full_resource_parity":False,
  "private_or_consumed_original_sources_born":0,
  "scientific_transfer_accepted":False,
  "cases":records}
 print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

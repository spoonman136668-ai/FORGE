"""T12 Mass: JOINT public causal witnesses plus noisy final FIT.

An independent eight-byte public TRAIN prior is completed using exactly
four PUBLIC first-round witnesses; 32 predetermined swap proposals between
unwitnessed nibble rows use the SAME 40 public noisy final outputs to refine
the model. Identity-init control has identical four witnesses, 32 swaps,
and 40 FIT observations. Final 8 CHECK and 16 private unseen outputs are
not training signals. First-use and prior registered sources untouched.
"""
from __future__ import annotations
import types,json,sys,importlib.util,time,tracemalloc,itertools
from pathlib import Path
D=Path(__file__).parent;TRAIN=range(-32015,-31999);OPEN=range(-32107,-32099)
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def measured(f):
 tracemalloc.start();t=time.process_time_ns()
 out=f();c={"cpu_ns":time.process_time_ns()-t,
             "Python_peak_bytes":tracemalloc.get_traced_memory()[1]}
 tracemalloc.stop();return out,c
def public_nibble_pairs(witness):
 known={}
 for x,y in witness:
  for off in (0,4,8,12):
   a,b=(x>>off)&15,(y>>off)&15
   assert a not in known or known[a]==b
   known[a]=b
 assert len(set(known.values()))==len(known)
 return known
def fit(m,t10,prior,FIT,CHECK,witness,mode):
 assert len(FIT)==40 and len(CHECK)==8 and len(witness)==4
 forced=public_nibble_pairs(witness)
 init=t10.infer_from_public(m,prior,witness,mode)
 p=list(m.unpack(init))
 available=[i for i in range(16) if i not in forced]
 candidates=list(itertools.combinations(available,2))
 assert candidates
 def public_error(model):
  return sum((m.forward(x,model)^y).bit_count() for x,y in FIT)
 best=public_error(m.pack(p));work=40;improve=0
 # The proposal schedule is fixed by unobserved public input indices,
 # not by private target, graph source tags, or observed outcomes.
 for step in range(32):
  a,b=candidates[step%len(candidates)]
  candidate=p[:];candidate[a],candidate[b]=candidate[b],candidate[a]
  packed=m.pack(candidate);error=public_error(packed);work+=40
  if error<best:best=error;p=candidate;improve+=1
 packed=m.pack(p)
 chk=sum((m.forward(x,packed)^y).bit_count() for x,y in CHECK)
 work+=8
 assert all(p[x]==y for x,y in forced.items())
 return packed,{"TRAIN_held_private_used":False,"sourceblind_FIT_forward_work":work,
     "number_fixed_proposals":32,"public_final_FIT_bit_errors":best,
     "public_CHECK_bit_errors":chk,"public_witness_distinct_entries":len(forced),
     "accepted_local_swaps":improve}
def main():
 frozen=json.loads((D/"20261019-mass-t12-freeze.json").read_text())
 assert frozen["schema"]=="northstar.t12.mass.frozen-preimplementation.v1" and frozen["parent_exact_head"]=="be3d9064f9a244dbff11997700797a86e4e0f015"
 t11=load(D/"20261019-mass-t11-mechanism.py","mass_t12_sourcebase")
 t10=load(D/"20261019-mass-t10-shared-map.py","mass_t12_t10")
 m=load(D/"20261018-mass-t3-learned-sbox.py","mass_t12_sbox")
 source=types.FunctionType(t11.source.__code__,dict(t11.source.__globals__,TRAIN=TRAIN,OPEN=OPEN),t11.source.__name__,t11.source.__defaults__)
 training=[source(i,m) for i in TRAIN];opens=[source(i,m) for i in OPEN]
 (prior,traininfo),tcost=measured(lambda:t10.prior_fit(training,m))
 identity=m.pack(tuple(range(16)))
 rows=[]
 for seed,(FIT,CHECK,witness,hidden) in zip(OPEN,opens):
  (learned,ldiag),lc=measured(lambda:fit(m,t10,prior,FIT,CHECK,witness,"learned"))
  (zero,zdiag),zc=measured(lambda:fit(m,t10,identity,FIT,CHECK,witness,"identity"))
  static,sc=measured(lambda:t10.infer_from_public(m,prior,witness,"learned"))
  (general,gdiag),gc=measured(lambda:m.fit_public(FIT,CHECK))
  score=lambda q:sum(m.forward(x,q)==y for x,y in hidden)
  rows.append({"source_id":seed,"learned_correct":score(learned),
    "zero_prior_equal_work_correct":score(zero),
    "unadapted_same_prior_correct":score(static),
    "T3_general_public_correct":score(general),
    "candidate_accepted_swaps":ldiag["accepted_local_swaps"],
    "sourceblind_forward_work":ldiag["sourceblind_FIT_forward_work"],
    "candidate_FIT_errors":ldiag["public_final_FIT_bit_errors"],
    "candidate_CHECK_errors":ldiag["public_CHECK_bit_errors"],
    "distinct_public_nibble_entries":ldiag["public_witness_distinct_entries"],
    "candidate_CPU_peak":lc,"identity_CPU_peak":zc,"general_T3_CPU_peak":gc})
 tot=lambda k:sum(x[k] for x in rows)
 out={"schema":"mass.t12.joint-partial-causal-witness-and-public-final-FIT.v1",
  "TRAIN_tasks":len(training),"OPEN_tasks":len(opens),
  "public_first_round_witnesses_per_OPEN":4,
  "public_final_FIT_per_OPEN":40,"public_final_CHECK_per_OPEN":8,
  "evaluator_only_unseen_outputs":len(opens)*16,
  "sourceblind_learned_8B_prior_differs_from_identity":prior!=identity,
  "candidate_exact_unseen":tot("learned_correct"),
  "equal_32proposal_untrained_exact":tot("zero_prior_equal_work_correct"),
  "unchanged_T11_prior_only_exact":tot("unadapted_same_prior_correct"),
  "original_T3_40FIT8CHECK_exact":tot("T3_general_public_correct"),
  "FIT_noisy_final_outcomes_actually_used_for_model_selection":True,
  "fixed_candidate_proposals_per_task":32,
  "TRAIN_CPU_peak":tcost,
  "candidate_model_CPU_total_ns":sum(r["candidate_CPU_peak"]["cpu_ns"] for r in rows),
  "identity_model_CPU_total_ns":sum(r["identity_CPU_peak"]["cpu_ns"] for r in rows),
  "candidate_peak_including_training":max(tcost["Python_peak_bytes"],
               *(r["candidate_CPU_peak"]["Python_peak_bytes"] for r in rows)),
  "matched_identity_peak_bytes":max(r["identity_CPU_peak"]["Python_peak_bytes"] for r in rows),
  "full_input_service_cost_qualified":False,
  "complete_resource_nonincrease":False,
  "protected_or_consumed_original_MNS_used":False,
  "science_accepted":False,"cases":rows}
 print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

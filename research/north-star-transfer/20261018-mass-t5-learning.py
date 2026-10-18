"""T5 Mass: public-only persistent cross-task nonlinear representation.

Eight independent TRAIN sources share a latent 4bit permutation with an
independent per-task swap. The shared latent is source-only; candidate learns
an 8-byte common prior from pooled public pairs. On disjoint OPEN sources
both prior-initialized and identity-initialized learners get identical 40/8
public responses with exactly six fixed corruptions. True outputs for 16
disjoint inputs are evaluator-only. No MNS registered data are consumed.
"""
from __future__ import annotations
import importlib.util,sys,json,random,time,tracemalloc
from pathlib import Path
HERE=Path(__file__).resolve().parent
FROZEN=HERE/"20261018-mass-t5-frozen.json"
T3=HERE/"20261018-mass-t3-learned-sbox.py"
TRAIN=range(-10407,-10399)
OPEN=range(-10503,-10499)
def need(ok,n):
    if not ok:raise ValueError("MASS_T5_"+n)
def load(path,name):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp)
    sys.modules[sp.name]=m;sp.loader.exec_module(m)
    return m
def born(i,m):
    need(i in TRAIN or i in OPEN,"PROTECTED_SOURCE_NEVER_CONSTRUCT")
    hidden_rng=random.Random(8031741)
    latent=hidden_rng.sample(range(16),16)    # never returned to learner
    rng=random.Random(77953+(-i)*32573)
    p=latent[:]
    a,b=rng.sample(range(16),2)
    p[a],p[b]=p[b],p[a]
    truth=m.pack(p)
    inputs=rng.sample(range(65536),64)
    outputs=[m.forward(x,truth) for x in inputs]
    noise=frozenset(rng.sample(range(48),6))
    pub=[(x,outputs[j]^(1 if j in noise else 0))
         for j,x in enumerate(inputs[:48])]
    private=tuple(zip(inputs[48:],outputs[48:]))
    need(len(noise)==6 and len(pub)==48 and len(private)==16,"FROZEN_PUBLIC_BUDGET")
    return (pub[:40],pub[40:],private)
def fit(m,FIT,CHECK,initial):
    need(len(FIT)==40 and len(CHECK)==8,"SAME_48")
    p=list(m.unpack(initial))
    score,total=m.score(FIT,p)
    tries=0
    for _ in range(2):
        for a in range(15):
            for b in range(a+1,16):
                alt=p[:];alt[a],alt[b]=alt[b],alt[a]
                err,ops=m.score(FIT,alt)
                total+=ops;tries+=1
                if err<score:score=err;p=alt
    chk,ops=m.score(CHECK,p);total+=ops
    return m.pack(p),{"FIT_bit_errors":score,"CHECK_bit_errors":chk,
                      "sourceblind_public_forward_evaluations":total,
                      "pair_swap_candidates":tries}
def learn_meta(m,sources):
    # Pool the shared public evidence. No true Sbox, hidden latent, task
    # name or protected evaluator label enters the 8-byte optimizer.
    rows=[]
    for source in sources:
        rows+=source[0]
    need(len(rows)==320,"FIXED_TRAIN_RESPONSES_8x40")
    baseline=m.pack(tuple(range(16)))
    p=list(m.unpack(baseline))
    best,total=m.score(rows,p)
    for _ in range(2):
        for a in range(15):
            for b in range(a+1,16):
                alt=p[:];alt[a],alt[b]=alt[b],alt[a]
                v,work=m.score(rows,alt);total+=work
                if v<best:best=v;p=alt
    return m.pack(p),{"TRAIN_only_public_pooled_responses":len(rows),
         "FIT_bit_errors":best,"total_forward_evaluations":total,
         "shared_persistent_parameter_bytes":8,
         "source_hidden_permutation_used":False}
def measured(fn):
    tracemalloc.start();t=time.process_time_ns()
    value=fn()
    result={"cpu_ns":time.process_time_ns()-t,
            "python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    tracemalloc.stop()
    return value,result
def evaluate(m,model,private):
    return (sum(m.forward(x,model)==y for x,y in private),
            sum((m.forward(x,model)^y).bit_count() for x,y in private))
def main():
    f=json.loads(FROZEN.read_text())
    need(f["schema"]=="research.northstar.t5.persistent-cross-task-sbox.v1"
       and f["parent_t4_head"]=="f8fb6055776065ff18e5f35828aa6ceaa3046477"
       and not f["authority"]["protected_original_first_use"],"FROZEN_SOURCE")
    m=load(T3,"mass_t5_model")
    TRAIN_rows=[born(i,m) for i in TRAIN]
    OPEN_rows=[born(i,m) for i in OPEN]
    (meta,meta_receipt),meta_cost=measured(lambda:learn_meta(m,TRAIN_rows))
    identity=m.pack(tuple(range(16)))
    cases=[];trained_scores=[];zero_scores=[]
    for FIT,CHECK,private in OPEN_rows:
        (trained,treceipt),tcost=measured(lambda:fit(m,FIT,CHECK,meta))
        (from_zero,zreceipt),zcost=measured(lambda:fit(m,FIT,CHECK,identity))
        (learned_outcome),licost=measured(lambda:evaluate(m,trained,private))
        (zero_outcome),zicost=measured(lambda:evaluate(m,from_zero,private))
        (metabare),mcost=measured(lambda:evaluate(m,meta,private))
        cases.append({"learned_correct":learned_outcome[0],
                     "zero_fit_correct":zero_outcome[0],
                     "meta_only_correct":metabare[0],
                     "learned_bit_errors":learned_outcome[1],
                     "zero_bit_errors":zero_outcome[1],
                     "meta_only_bit_errors":metabare[1],
                     "meta_fitted_model_differs":trained!=from_zero,
                     "learned_fit_cpu_ns":tcost["cpu_ns"],
                     "zero_fit_cpu_ns":zcost["cpu_ns"],
                     "learned_eval_cpu_ns":licost["cpu_ns"],
                     "zero_eval_cpu_ns":zicost["cpu_ns"],
                     "trained_fit_peak_bytes":tcost["python_peak_bytes"],
                     "baseline_fit_peak_bytes":zcost["python_peak_bytes"],
                     "unchanged_public_pairs":48,
                     "independent_unseen_input_evaluations":16})
    total=lambda key:sum(x[key] for x in cases)
    out={"schema":"mass.t5.persistent-cross-task-learning.v1",
      "source_only_train_tasks":len(TRAIN_rows),"source_only_open_tasks":len(OPEN_rows),
      "original_registered_MNS_used":0,"TRAIN_meta_prior_bytes":len(meta),
      "meta_differs_from_untrained_identity":meta!=identity,
      "training_fit_public_samples":meta_receipt["TRAIN_only_public_pooled_responses"],
      "training_sourceblind_forward_evaluations":meta_receipt["total_forward_evaluations"],
      "amortized_training_CPU_ns_per_OPEN_task":meta_cost["cpu_ns"]/len(OPEN_rows),
      "train_peak_bytes":meta_cost["python_peak_bytes"],
      "train_total_CPU_ns":meta_cost["cpu_ns"],
      "OPEN_exact_new":total("learned_correct"),"OPEN_exact_zero":total("zero_fit_correct"),
      "OPEN_exact_meta_no_adapt":total("meta_only_correct"),
      "OPEN_bit_errors_new":total("learned_bit_errors"),
      "OPEN_bit_errors_zero":total("zero_bit_errors"),
      "OPEN_bit_errors_meta_no_adapt":total("meta_only_bit_errors"),
      "OPEN_prior_affects_fitted_model_count":sum(c["meta_fitted_model_differs"] for c in cases),
      "OPEN_total_new_fit_CPU_ns":total("learned_fit_cpu_ns"),
      "OPEN_total_zero_fit_CPU_ns":total("zero_fit_cpu_ns"),
      "TRAIN_amortized_plus_OPEN_new_CPU_ns":
             meta_cost["cpu_ns"]/len(OPEN_rows)+total("learned_fit_cpu_ns")+
                         total("learned_eval_cpu_ns"),
      "OPEN_zero_control_CPU_ns":total("zero_fit_cpu_ns")+total("zero_eval_cpu_ns"),
      "full_cpu_parity_with_zero_control":False,
      "complete_AZ_graph_and_peak_parity_qualified":False,
      "strict_protected_transfer_accepted":False,"science_first_use":False,
      "cases":cases}
    need(out["OPEN_prior_affects_fitted_model_count"]>=0
         and len(cases)==4 and out["original_registered_MNS_used"]==0,
         "NO_ORACLE_OR_COHORT_LEAK")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

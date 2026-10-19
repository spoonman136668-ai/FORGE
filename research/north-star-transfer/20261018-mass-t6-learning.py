"""T6 Mass: public-only structural cross-task affine nibble representation.

Fresh source family is independently frozen: each task's unknown bijective
nibble substitution is p[n]=(a*n+b)%16 with same hidden a and new b.
This is a restricted family; never present it as arbitrary permutation
learning or genuine transfer to a new operator grammar. The learner must
infer a from TRAIN PUBLIC (x,y) only, then b from OPEN FIT PUBLIC.
All controls see exactly the same 40 FIT +8 CHECK noisy outputs.
"""
from __future__ import annotations
import importlib.util,json,random,time,tracemalloc,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
FREEZE=HERE/"20261018-mass-t6-freeze.json"
T3=HERE/"20261018-mass-t3-learned-sbox.py"
T5=HERE/"20261018-mass-t5-learning.py"
TRAIN=range(-10607,-10599)
OPEN=range(-10703,-10699)
ODD=(1,3,5,7,9,11,13,15)
def need(x,key):
    if not x:raise ValueError("MASS_T6_"+key)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
def perm(a,b):
    need(a in ODD and 0<=b<16,"GENERIC_AFFINE_NIBBLE_BIJECTION")
    return tuple((a*x+b)%16 for x in range(16))
def born(seed,m):
    need(seed in TRAIN or seed in OPEN,"REGISTERED_SOURCE_PROHIBITED")
    # Private source a is NEVER supplied to model; only public pairs.
    a=ODD[random.Random(907311).randrange(len(ODD))]
    rng=random.Random(171191+abs(seed)*8191)
    b=rng.randrange(16)
    model=m.pack(perm(a,b))
    xs=rng.sample(range(65536),64)
    clean=[m.forward(x,model) for x in xs]
    noise=frozenset(rng.sample(range(48),6))
    public=tuple((x,clean[i]^(1 if i in noise else 0)) for i,x in enumerate(xs[:48]))
    hidden=tuple(zip(xs[48:],clean[48:]))
    need(len(public)==48 and len(hidden)==16 and len(noise)==6,"FROZEN_48_6_16")
    return public[:40],public[40:],hidden
def fit_a_b(m,rows,known_a=None):
    need(len(rows) in (40,320),"MATCHED_PUBLIC_INPUT_BOUND")
    slopes=ODD if known_a is None else (known_a,)
    winner=None;work=0;tested=0
    for a in slopes:
        for b in range(16):
            model=m.pack(perm(a,b))
            v=0
            for x,y in rows:
                v+=(m.forward(x,model)^y).bit_count()
                work+=1
            candidate=(v,a,b)
            tested+=1
            if winner is None or candidate<winner:
                winner=candidate
    errors,a,b=winner
    return m.pack(perm(a,b)),{"public_fit_bit_errors":errors,"a_selected":a,
               "complete_nibble_candidate_models":tested,
               "model_forward_evaluations":work}
def learn_shared_a(m,TRAIN_rows):
    """For each a, infer nuisance b from each TRAIN source FIT only."""
    need(len(TRAIN_rows)==8,"EIGHT_SOURCE_TRAIN_TASKS")
    best=None;works=0
    for a in ODD:
        agg=0
        for FIT,CHECK,hidden in TRAIN_rows:
            _,receipt=fit_a_b(m,FIT,known_a=a)
            works+=receipt["model_forward_evaluations"]
            agg+=receipt["public_fit_bit_errors"]
        if best is None or (agg,a)<best:best=(agg,a)
    return best[1],{"TRAIN_public_fit_total_bit_errors":best[0],
                    "TRAIN_public_forward_evaluations":works,
                    "shared_slope_parameter_bits":3,
                    "protected_true_slope_given_to_learner":False}
def measure(f):
    tracemalloc.start();t=time.process_time_ns();v=f()
    cost={"cpu_ns":time.process_time_ns()-t,
          "python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    tracemalloc.stop();return v,cost
def eval_exact(m,model,hidden):
    return sum(m.forward(x,model)==y for x,y in hidden)
def main():
    frozen=json.loads(FREEZE.read_text())
    need(frozen["schema"]=="research.northstar.t6.frozen.v1"
         and frozen["parent_exact_head"]=="d486ef9e9f1442317be31e3ce69e9a217cb501f6"
         and not frozen["protected_source_first_use"],"FREEZE_BEFORE_SOURCE")
    m=load(T3,"mass_t6_model");t5=load(T5,"mass_t6_t5")
    train=[born(i,m) for i in TRAIN];tests=[born(i,m) for i in OPEN]
    (shared,trainreceipt),traincost=measure(lambda:learn_shared_a(m,train))
    outputs=[]
    for FIT,CHECK,hidden in tests:
        (candidate,learndata),c=measure(lambda:fit_a_b(m,FIT,known_a=shared))
        (full,fulldata),b=measure(lambda:fit_a_b(m,FIT))
        (old,olddata),oldcost=measure(lambda:t5.fit(m,FIT,CHECK,m.pack(tuple(range(16)))))
        outputs.append({"learned_exact_unobserved":eval_exact(m,candidate,hidden),
            "sourceblind_full_structural_exact":eval_exact(m,full,hidden),
            "T5_general_sbox_exact":eval_exact(m,old,hidden),
            "candidate_cpu_ns":c["cpu_ns"],"full_sourceblind_control_cpu_ns":b["cpu_ns"],
            "T5_general_sbox_cpu_ns":oldcost["cpu_ns"],
            "candidate_peak_bytes":c["python_peak_bytes"],
            "full_sourceblind_peak_bytes":b["python_peak_bytes"],
            "T5_sbox_peak_bytes":oldcost["python_peak_bytes"],
            "candidate_models_examined":learndata["complete_nibble_candidate_models"],
            "full_control_models_examined":fulldata["complete_nibble_candidate_models"],
            "public_fit_40_check_8":True,"independent_evaluation_inputs":16})
    total=lambda key:sum(x[key] for x in outputs)
    n=len(outputs)
    out={"schema":"mass.t6.shared-public-composition-disjoint-task-parameter.v1",
       "TRAIN_tasks":len(train),"OPEN_tasks":n,"registered_MNS_sources_born":0,
       "fresh_per_task_affine_nibble_offset":True,
       "shared_slope_learned_from_public_train_only":shared,
       "slope_parameter_bits":3,"task_offset_parameter_bits":4,
       "training_total_public_evaluations":trainreceipt["TRAIN_public_forward_evaluations"],
       "learned_exact_unobserved":total("learned_exact_unobserved"),
       "strongest_exact_public_structural_control_correct":total("sourceblind_full_structural_exact"),
       "general_unconstrained_T5_control_correct":total("T5_general_sbox_exact"),
       "independent_unobserved_outputs":16*n,
       "candidate_total_with_training_amortized_CPU_ns":total("candidate_cpu_ns")+traincost["cpu_ns"]/n,
       "full_public_structural_control_CPU_ns":total("full_sourceblind_control_cpu_ns"),
       "candidate_training_cost":traincost,
       "candidate_peak_including_training":max(traincost["python_peak_bytes"],
                                      *(x["candidate_peak_bytes"] for x in outputs)),
       "control_peak":max(x["full_sourceblind_peak_bytes"] for x in outputs),
       "strict_resource_parity":False,"full_AZ_end_to_end_resource_parity":False,
       "new_unseen_operator_family_transfer_claim":False,
       "source_of_truth_used_for_model_fitting":False,
       "protected_scientific_first_use":False,"science_accepted":False,
       "cases":outputs}
    need(n==4 and out["registered_MNS_sources_born"]==0,"SOURCE_BOUNDS")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

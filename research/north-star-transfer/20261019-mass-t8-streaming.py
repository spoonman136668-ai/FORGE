"""T8 Mass sourceblind streaming sufficient-statistic audit.

Train shared 3-bit nibble slope from the SAME frozen T6 public TRAIN
observations, one task at a time with 8 scalar accumulators. No pool of
320 rows or private true slope, no recreation of consumed T7 A/B cohort.
Source-neutral -19000 XOR-masked fixture tests expression / CPU / peak
against exact all-2048-model public structural search on SAME 40 FIT.
No novel transfer or full budget acceptance from one fixture.
"""
from __future__ import annotations
import importlib.util,random,json,sys,time,tracemalloc
from pathlib import Path
HERE=Path(__file__).resolve().parent
FREEZE=HERE/"20261019-mass-t8-source-freeze.json"
T6=HERE/"20261018-mass-t6-learning.py"
T7=HERE/"20261018-mass-t7-independent.py"
def need(ok,label):
    if not ok:raise ValueError("MASS_T8_"+label)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m;spec.loader.exec_module(m)
    return m
def measure(fn):
    tracemalloc.start();before=time.process_time_ns()
    out=fn()
    cpu=time.process_time_ns()-before
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return out,{"cpu_ns":cpu,"peak_Python_bytes":peak}
def streaming_public_prior(t6,m):
    scores=[0]*8;ops=0
    n=0
    # Exact same T6 eight TRAIN source IDs. The only retained cross-task
    # information is eight scalar scores, not the FIT/CHECK tuples.
    for seed in t6.TRAIN:
        FIT,CHECK,_source_only_evaluator_discarded=t6.born(seed,m)
        need(len(FIT)==40 and len(CHECK)==8,"T6_ORIGINAL_TRAIN_PUBLIC_SPLIT")
        for j,a in enumerate(t6.ODD):
            best=None
            for b in range(16):
                p=m.pack(t6.perm(a,b))
                error=0
                for x,y in FIT:
                    error+=(m.forward(x,p)^y).bit_count()
                    ops+=1
                best=error if best is None else min(best,error)
            scores[j]+=best
        # FIT, CHECK and evaluator-only true outputs are NOT retained.
        n+=1
    need(n==8 and ops==40960,"FROZEN_TRAIN_OPERATION_LEDGER")
    slope_index=min(range(8),key=lambda j:(scores[j],j))
    return t6.ODD[slope_index],{
      "train_task_count":n,"sourceblind_slope_scores":tuple(scores),
      "scoring_forward_evaluations":ops,
      "retained_shared_slope_bits":3,
      "pooled_public_training_rows_retained":0,
      "source_truth_passed_to_learner":False}
def new_fixture(t6,m):
    rng=random.Random(19000+809027)
    slope=t6.ODD[rng.randrange(8)]
    b=rng.randrange(16);mask=rng.randrange(1,16)
    p=m.pack(tuple((((slope*i+b)%16)^mask) for i in range(16)))
    xs=rng.sample(range(65536),64)
    truth=[m.forward(x,p) for x in xs]
    noise=frozenset(rng.sample(range(48),6))
    rows=tuple((x,truth[j]^(1 if j in noise else 0))
               for j,x in enumerate(xs[:48]))
    hold=tuple(zip(xs[48:],truth[48:]))
    need(len(rows)==48 and len(hold)==16,"SOURCE_NEUTRAL_48_PLUS_16")
    return rows[:40],rows[40:],hold
def main():
    f=json.loads(FREEZE.read_text())
    need(f["schema"]=="northstar.t8.qualified-causal-transfer-source.v1"
         and f["parent_exact_head"]=="fddd175423c4042f351c82f201f32f013d176e96"
         and not f["authorization"]["prospective_source_first_use"],
         "PREIMPLEMENTATION_FROZEN")
    t6=load(T6,"mass_t8_frozen_t6")
    t7=load(T7,"mass_t8_frozen_t7")
    m=load(t6.T3,"mass_t8_frozen_sbox")
    (shared,train),traincost=measure(lambda:streaming_public_prior(t6,m))
    (FIT,CHECK,HIDDEN),sourcecost=measure(lambda:new_fixture(t6,m))
    (learned,learnproof),learncost=measure(lambda:t7.solve(m,t6,FIT,shared))
    (strongest,fullproof),fullcost=measure(lambda:t7.solve(m,t6,FIT))
    exact=lambda p:sum(m.forward(x,p)==y for x,y in HIDDEN)
    out={"schema":"mass.t8.streaming-public-sufficient-statistic.v1",
      "T6_frozen_public_TRAIN_reused":True,"TRAIN_recorded_tasks":train["train_task_count"],
      "TRAIN_accumulator_count":8,
      "TRAIN_public_evaluations":train["scoring_forward_evaluations"],
      "TRAIN_truth_used":train["source_truth_passed_to_learner"],
      "TRAIN_shared_slope":shared,
      "T7_A_or_B_original_recreated":False,
      "new_source_neutral_fixture_only":True,
      "public_FIT":len(FIT),"public_CHECK":len(CHECK),
      "source_truth_only_postprediction":True,
      "unobserved_evaluation_inputs":len(HIDDEN),
      "learned_exact_unobserved":exact(learned),
      "strongest_exact_public_control_unobserved":exact(strongest),
      "model_parameters_bits":3+4+4,
      "source_io_cost":sourcecost,
      "TRAIN_full_CPU_peak":traincost,
      "candidate_fit_CPU_peak":learncost,
      "sourceblind_full_control_fit_CPU_peak":fullcost,
      "candidate_fit_proposals":learnproof["parameter_candidates"],
      "full_public_model_count":fullproof["parameter_candidates"],
      "train_amortized_candidate_CPU_ns_over_16_tasks":
            learncost["cpu_ns"]+traincost["cpu_ns"]/16,
      "full_control_CPU_ns":fullcost["cpu_ns"],
      "candidate_complete_peak_including_training":
            max(traincost["peak_Python_bytes"],learncost["peak_Python_bytes"]),
      "strongest_control_peak":fullcost["peak_Python_bytes"],
      "complete_memory_parity":
            max(traincost["peak_Python_bytes"],learncost["peak_Python_bytes"])
                   <=fullcost["peak_Python_bytes"],
      "strictly_better_accuracy_than_strongest_control":
           exact(learned)>exact(strongest),
      "protected_prospective_first_use":False,
      "scientific_transfer_accepted":False,
      "optimizer_promotion":False}
    need(out["TRAIN_recorded_tasks"]==8 and out["T7_A_or_B_original_recreated"] is False,
         "FIRST_USE_SAFEGUARD")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

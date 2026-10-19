"""T9 Mass: shared public learned slope across THREE genuinely distinct
operator-program grammars, under identical sourceblind public FIT evidence.

New source-neutral synthetic tasks only. Parameter programs:
 A odd affine mod16
 B affine then XOR
 C affine then XOR then nibble rotate1
Each model is an 8-byte full Sbox encoding with native T3 3-round
16-bit composition. True grammar, a, b, mask and hidden output are
source-only evaluator data and not passed to the learner.
"""
from __future__ import annotations
import random,json,sys,importlib.util,time,tracemalloc
from pathlib import Path
HERE=Path(__file__).resolve().parent
FREEZE=HERE/"20261019-mass-t9-source-freeze.json"
T6=HERE/"20261018-mass-t6-learning.py"
T8=HERE/"20261019-mass-t8-streaming.py"
SEEDS=range(-21011,-20999)
PROGRAMS=("affine","masked","rotmask")
def need(ok,label):
    if not ok:raise ValueError("MASS_T9_"+label)
def load(path,name):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sys.modules[name]=m
    sp.loader.exec_module(m);return m
def permutation(a,b,mask,program):
    need(a in (1,3,5,7,9,11,13,15)
          and 0<=b<16 and 0<=mask<16 and program in PROGRAMS,"LEGAL_PROGRAM")
    if program=="affine":need(mask==0,"AFFINE_HAS_NO_XOR")
    else:need(mask>0,"NONLINEAR_XOR_REQUIRED")
    out=[]
    for i in range(16):
        v=(a*i+b)&15
        if program!="affine":v^=mask
        if program=="rotmask":v=((v<<1)|(v>>3))&15
        out.append(v)
    need(sorted(out)==list(range(16)),"TRUE_BIJECTION")
    return tuple(out)
def born(seed,m):
    need(seed in SEEDS,"NEVER_TOUCH_REGISTERED_PROSPECTIVE")
    rng=random.Random(919231+abs(seed)*93251)
    kind=PROGRAMS[abs(seed)%3]
    # Shared slope follows independent ORIGINAL frozen T6 TRAIN-only
    # distribution, not any new hidden source label supplied to solver.
    a=(1,3,5,7,9,11,13,15)[random.Random(907311).randrange(8)]
    b=rng.randrange(16)
    mask=0 if kind=="affine" else rng.randrange(1,16)
    p=m.pack(permutation(a,b,mask,kind))
    xs=rng.sample(range(65536),64)
    outputs=[m.forward(x,p) for x in xs]
    noise=frozenset(rng.sample(range(48),6))
    public=tuple((x,outputs[j]^(1 if j in noise else 0))
                 for j,x in enumerate(xs[:48]))
    private=tuple(zip(xs[48:],outputs[48:]))
    need(len(public)==48 and len(private)==16 and len(noise)==6,
         "48_6_16_PUBLIC_PROTOCOL")
    return (public[:40],public[40:],private)
def search(m,rows,prior_slope=None):
    need(len(rows)==40,"PUBLIC_40_ONLY")
    slopes=(1,3,5,7,9,11,13,15) if prior_slope is None else (prior_slope,)
    best=None;seen=0;work=0
    for a in slopes:
        for b in range(16):
            for program in PROGRAMS:
                masks=(0,) if program=="affine" else range(1,16)
                for mask in masks:
                    packed=m.pack(permutation(a,b,mask,program))
                    err=0
                    for x,y in rows:
                        err+=(m.forward(x,packed)^y).bit_count()
                        work+=1
                    # Deterministic tie break by sourceblind program ID.
                    cmp=(err,PROGRAMS.index(program),a,b,mask)
                    if best is None or cmp<best[0]:best=(cmp,packed)
                    seen+=1
    need(best is not None,"NONEMPTY_PROGRAM_ENUMERATION")
    return best[1],{"candidate_models_tested":seen,
         "public_forward_evaluations":work,
         "best_FIT_bit_errors":best[0][0],
         "program_selected_without_source_tag":PROGRAMS[best[0][1]]}
def measure(fn):
    tracemalloc.start();start=time.process_time_ns()
    value=fn();r={"cpu_ns":time.process_time_ns()-start,
                  "Python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    tracemalloc.stop();return value,r
def main():
    freeze=json.loads(FREEZE.read_text())
    need(freeze["schema"]=="northstar.t9.causal-sufficiency.preimplementation.v1"
         and freeze["parent_exact_head"]=="9ee8061221307dcd136dfe4731233db61efa8350"
         and freeze["authority"]["T7_consumed_original_replay"] is False,
         "PREIMPLEMENTATION_FROZEN")
    t6=load(T6,"mass_t9_original_t6")
    t8=load(T8,"mass_t9_original_t8")
    m=load(t6.T3,"mass_t9_native_sbox")
    (learned_slope,train_receipt),training_cost=measure(lambda:
        t8.streaming_public_prior(t6,m))
    results=[]
    for seed in SEEDS:
        FIT,CHECK,private=born(seed,m)
        (candidate,candidate_diag),ccost=measure(lambda:search(m,FIT,learned_slope))
        (full,full_diag),fcost=measure(lambda:search(m,FIT))
        correct=lambda p:sum(m.forward(x,p)==y for x,y in private)
        results.append({"source_id":seed,
           "candidate_exact":correct(candidate),
           "strongest_structural_exact":correct(full),
           "candidate_program":candidate_diag["program_selected_without_source_tag"],
           "control_program":full_diag["program_selected_without_source_tag"],
           "candidate_models":candidate_diag["candidate_models_tested"],
           "control_models":full_diag["candidate_models_tested"],
           "candidate_fit_cpu_peak":ccost,
           "control_fit_cpu_peak":fcost,
           "public_fit_rows":len(FIT),"public_check_rows":len(CHECK),
           "hidden_evaluator_rows":len(private)})
    sums=lambda key:sum(r[key] for r in results)
    candcpu=sums("candidate_fit_cpu_peak") if False else sum(
         r["candidate_fit_cpu_peak"]["cpu_ns"] for r in results)
    ctrlcpu=sum(r["control_fit_cpu_peak"]["cpu_ns"] for r in results)
    result={"schema":"mass.t9.multifamily-public-composition-source-neutral.v1",
       "source_neutral_cases":len(results),
       "new_program_families":PROGRAMS,
       "learned_slope_from_original_public_TRAIN_only":learned_slope,
       "TRAIN_statistic_count":8,
       "TRAIN_fit_evaluations":train_receipt["scoring_forward_evaluations"],
       "learned_correct_unobserved":sums("candidate_exact"),
       "strongest_structural_control_correct_unobserved":sums("strongest_structural_exact"),
       "unobserved_inputs":len(results)*16,
       "TRAIN_CPU_peak":training_cost,
       "candidate_fit_total_cpu_ns":candcpu,
       "strongest_fit_total_cpu_ns":ctrlcpu,
       "candidate_train_amortized_CPU_ns":candcpu+training_cost["cpu_ns"]/len(results),
       "candidate_full_peak_including_training":
            max(training_cost["Python_peak_bytes"],max(
                r["candidate_fit_cpu_peak"]["Python_peak_bytes"] for r in results)),
       "strongest_structural_fit_peak_bytes":max(
                r["control_fit_cpu_peak"]["Python_peak_bytes"] for r in results),
       "complete_resource_parity_demonstrated":False,
       "source_generation_cost_separately_metered":False,
       "T7_or_original_MNS_consumed_sources_reused":False,
       "prospective_scientific_first_use":False,
       "independently_replicated_transfer":False,
       "scientific_acceptance":False,
       "rows":results}
    need(result["unobserved_inputs"]==192,"ORIGINAL_PUBLIC_EVIDENCE_BOUND")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()

"""T7 Mass: new task-specific XOR-masked affine nibble composition.

Independent source births under a preregistered third operator family.
The unchanged T6 TRAIN-only public data learn shared slope a; neither
generator hidden slope, offset, XOR mask nor private outputs enter fitting.
Original source-negative trial A; B is held unless A strictly qualifies.
"""
from __future__ import annotations
import random,json,time,tracemalloc,importlib.util,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
FROZEN=HERE/"20261018-mass-t7-preregister.json"
T6=HERE/"20261018-mass-t6-learning.py"
T5=HERE/"20261018-mass-t5-learning.py"
A=range(-17107,-17099)
B=range(-17207,-17199)
FIXTURE=-17000
def need(ok,tag):
    if not ok:raise ValueError("MASS_T7_"+tag)
def load(p,n):
    sp=importlib.util.spec_from_file_location(n,p)
    m=importlib.util.module_from_spec(sp)
    sys.modules[n]=m;sp.loader.exec_module(m);return m
def born(seed,m,t6,mode="prospective"):
    if mode=="fixture":need(seed==FIXTURE,"ONLY_SOURCE_FIXTURE")
    else:need(seed in A or seed in B,"SOURCE_BIRTH_IDENTITY")
    # The shared a originates at TRAIN-only T6 source birth; never visible
    # to learner in T7. The independent T7 relation adds unknown XOR mask.
    a=t6.ODD[random.Random(907311).randrange(8)]
    rng=(random.Random((abs(seed)*2654435761)^119982)
         if seed in B else random.Random(187713+abs(seed)*70841))
    b=rng.randrange(16);xor=rng.randrange(1,16)
    p=tuple((((a*i+b)%16)^xor) for i in range(16))
    need(sorted(p)==list(range(16)),"TRUE_NEW_COMPOSITE_BIJECTION")
    truth=m.pack(p)
    xs=rng.sample(range(65536),64)
    clean=[m.forward(x,truth) for x in xs]
    noise=frozenset(rng.sample(range(48),6))
    public=tuple((x,clean[j]^(1 if j in noise else 0))
                 for j,x in enumerate(xs[:48]))
    return public[:40],public[40:],tuple(zip(xs[48:],clean[48:]))
def masked_perm(t6,a,b,mask):
    return tuple((((a*x+b)%16)^mask) for x in range(16))
def solve(m,t6,public,a_known=None):
    need(len(public)==40,"FROZEN_EQUAL_PUBLIC_40")
    best=None;work=0;count=0
    slopes=t6.ODD if a_known is None else (a_known,)
    for a in slopes:
        for b in range(16):
            for mask in range(1,16):
                candidate=m.pack(masked_perm(t6,a,b,mask))
                err=0
                for x,y in public:
                    err+=(m.forward(x,candidate)^y).bit_count()
                    work+=1
                v=(err,a,b,mask)
                if best is None or v<best[0]:best=(v,candidate)
                count+=1
    return best[1],{"model_evaluations":work,"parameter_candidates":count,
                   "sourceblind_public_only":True}
def measure(fn):
    tracemalloc.start();t=time.process_time_ns()
    res=fn();receipt={"CPU_ns":time.process_time_ns()-t,
                     "Python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    tracemalloc.stop();return res,receipt
def preflight():
    p=json.loads(FROZEN.read_text())
    need(p["schema"]=="northstar.t7.mass.preimplementation-prospective.v1"
         and p["source_parent_head"]=="6f775e8fdbf5d58856674df7d920f1592af58ca0",
         "SOURCE_PREIMPLEMENTATION")
    t6=load(T6,"mass_t7_sourceonly_T6")
    m=load(t6.T3,"mass_t7_sourceonly_SBOX")
    FIT,CHECK,HIDDEN=born(FIXTURE,m,t6,mode="fixture")
    need(len(FIT)==40 and len(CHECK)==8 and len(HIDDEN)==16 and
         all(len(row)==2 for row in FIT+CHECK+HIDDEN),
         "NEW_FAMILY_SOURCE_40_8_16")
    for wrong in (-17100,-17200,-10600,902000):
        try:born(wrong,m,t6,mode="fixture")
        except ValueError:pass
        else:raise AssertionError("original first-use source built in preflight")
    return {"schema":"mass.t7.new-nonlinear-sourceonly.v1",
       "new_operator_family":"affine_nibble_then_nonlinear_xor_mask",
       "prospective_and_replica_sources_born":0,
       "MNS_original_protected_sources_used":0,
       "source_only_fixture_pass":True}
def case(m,t6,t5,shared,seed):
    FIT,CHECK,hidden=born(seed,m,t6)
    (candidate,cm),cc=measure(lambda:solve(m,t6,FIT,shared))
    (full,bm),bc=measure(lambda:solve(m,t6,FIT))
    (old,om),oc=measure(lambda:t5.fit(m,FIT,CHECK,
                              m.pack(tuple(range(16)))))
    def score(model):
        return sum(m.forward(x,model)==y for x,y in hidden)
    return {"source_id":seed,"learned_exact":score(candidate),
        "exact_same_information_structural_control":score(full),
        "T5_general_Sbox_control_exact":score(old),
        "learned_fitted_parameter_count":cm["parameter_candidates"],
        "full_public_exact_candidate_count":bm["parameter_candidates"],
        "learned_CPU_ns":cc["CPU_ns"],
        "full_sourceblind_CPU_ns":bc["CPU_ns"],
        "learned_peak_bytes":cc["Python_peak_bytes"],
        "full_sourceblind_peak_bytes":bc["Python_peak_bytes"],
        "public_observations":48,"private_inputs_not_public":16}
def cohort(m,t6,t5,shared,ids,train):
    out=[case(m,t6,t5,shared,i) for i in ids]
    n=len(out)
    total=lambda key:sum(x[key] for x in out)
    train_cpu=train["CPU_ns"]/16
    candidate_peak=max(train["Python_peak_bytes"],
                       max(x["learned_peak_bytes"] for x in out))
    control_peak=max(x["full_sourceblind_peak_bytes"] for x in out)
    return {"source_cases":n,
        "learned_exact_unobserved":total("learned_exact"),
        "full_sourceblind_control_exact":total("exact_same_information_structural_control"),
        "T5_general_Sbox_exact":total("T5_general_Sbox_control_exact"),
        "total_unobserved":n*16,
        "learned_FIT_cpu_ns":total("learned_CPU_ns"),
        "exact_control_FIT_cpu_ns":total("full_sourceblind_CPU_ns"),
        "learned_with_amortized_TRAIN_CPU_ns":total("learned_CPU_ns")+train_cpu,
        "candidate_peak_including_TRAIN":candidate_peak,
        "control_peak_without_training":control_peak,
        "full_cpu_nonincrease":total("learned_CPU_ns")+train_cpu<=total("full_sourceblind_CPU_ns"),
        "full_peak_nonincrease":candidate_peak<=control_peak,
        "strictly_beats_exact_public_control":
                total("learned_exact")>total("exact_same_information_structural_control")}
def original():
    preflight()
    t6=load(T6,"mass_t7_original_T6")
    t5=load(T5,"mass_t7_original_T5")
    m=load(t6.T3,"mass_t7_original_sbox")
    # Reuse original immutable public T6 TRAIN ONLY, no T6 OPEN reuse.
    training=[t6.born(i,m) for i in t6.TRAIN]
    (shared,_),traincost=measure(lambda:t6.learn_shared_a(m,training))
    first=cohort(m,t6,t5,shared,A,traincost)
    eligible=(first["strictly_beats_exact_public_control"]
              and first["full_cpu_nonincrease"] and first["full_peak_nonincrease"]
              and first["learned_exact_unobserved"]>0)
    replica=cohort(m,t6,t5,shared,B,traincost) if eligible else None
    return {"schema":"mass.t7.first-novel-operation-public-transfer.v1",
        "original_T6_TRAIN_only_public_prior_reused":True,
        "shared_slope_inferred_from_public_TRAIN":shared,
        "T7_TRAIN_cost":traincost,
        "A":first,"A_eligible":eligible,
        "B_independent_replica":replica,
        "B_created":replica is not None,
        "A_original_source_cases_born":len(A),
        "B_source_cases_born":len(B) if replica else 0,
        "original_MNS_protected_source_used":0,
        "AZ_full_resource_comparison_qualified":False,
        "scientific_transfer_accepted":False,
        "optimizer_promoted":False}
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=("preflight","original"),default="preflight")
    a=p.parse_args()
    print(json.dumps(preflight() if a.mode=="preflight" else original(),sort_keys=True))

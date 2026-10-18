"""Mass T2 independent compositional relation source — nonconsuming.

Actual new TRAIN grammar covers affine mod65536 and separately randomized
two-shear mappings. Unseen third family is fixed algebraically but its
reserved source identities cannot be constructed in T2, nor are the old
F124 source cases reused or compared to a fabricated OOD result.
"""
from __future__ import annotations
import json,math,random
from pathlib import Path
HERE=Path(__file__).resolve().parent
FREEZE=HERE/"20261018-mass-t2-source-freeze.json"
FIXTURES=(-930,-931)
RESERVED=[range(900000,900192),range(901000,901064),
          range(902000,902128),range(903000,903128)]
def need(ok,name):
    if not ok:raise ValueError("MASS_T2_"+name)
def rol8(x,n):return ((x<<n)|(x>>(8-n)))&255
def shearf(x,p,q):
    return (rol8(x,1)&p)^((rol8(x,3)&rol8(x,5))&q)
def trained_relation(x,kind,params):
    need(0<=x<65536,"SOURCE_BITS")
    if kind=="affine":
        a,b=params
        return (a*x+b)&65535
    need(kind=="2-shear" and len(params)==4,"TWO_DISTINCT_TRAIN_GRAMMARS")
    a=x&255;b=x>>8
    p,q,r,s=params
    b^=shearf(a,p,q)
    a^=shearf(b,r,s)
    return a|(b<<8)
def fixture(seed):
    need(seed in FIXTURES,"REGISTERED_TRAIN_VALIDATION_UNSEEN_AND_REPLICA_FORBIDDEN")
    rng=random.Random(seed*7321+9083)
    kind="affine" if seed==-930 else "2-shear"
    params=((2*rng.randrange(32768)+1,rng.randrange(65536))
             if kind=="affine" else tuple(rng.randrange(256) for _ in range(4)))
    sampled=rng.sample(range(65536),48)
    answers=[trained_relation(x,kind,params) for x in sampled]
    # 6 public corruption positions fixed by source seed, never model-fitted.
    corrupt=tuple(sorted(rng.sample(range(48),6)))
    pub=[{"input_bits":x,"output_bits":((answers[i]^1) if i in corrupt else answers[i])}
         for i,x in enumerate(sampled)]
    public={"observations":pub,"FIT":pub[:40],"CHECK":pub[40:],
             "source_identity_exposed_to_model":False}
    private={"source_kind_evaluator_only":kind,
             "source_params_evaluator_only":params,
             "noise_positions_evaluator_only":corrupt,
             "clean_outputs_evaluator_only":answers}
    need(len(pub)==48 and len(corrupt)==6
         and len(set(sampled))==48,"SOURCE_BORN_48_RESPONSES_SIX_ERRORS")
    return public,private
def unseen_family_entropy_lower_bound_bits():
    # All independent 4-bit substitution permutations comprise 16! LUTs;
    # 4B task model cannot encode arbitrary third-family lookup (without
    # extra task state). This is an information capacity warning, not a
    # proof that a distributed learned program cannot generalize.
    return math.log2(math.factorial(16))
def attest():
    d=json.loads(FREEZE.read_text())
    need(d["schema"]=="northstar.t2.mass.unseen-nonlinear-family-source.v1"
         and d["registered_cohorts_not_constructed"] is True
         and d["source_anchor_head"]=="3e480de74aac83f36c922b88cc393549a231316d",
         "FROZEN_NEW_SOURCE")
    for ids in RESERVED:
        need(not set(FIXTURES).intersection(ids),"RESERVED_COHORT_DISJOINT")
        try:fixture(ids.start)
        except ValueError:pass
        else:raise AssertionError("scientific identity must not be born")
    a,pa=fixture(-930);b,pb=fixture(-931)
    need(pa["source_kind_evaluator_only"]!=pb["source_kind_evaluator_only"],
         "TWO_INDEPENDENT_KINDS")
    need(unseen_family_entropy_lower_bound_bits()>32,
         "UNKNOWN_NONCOMMUTING_FAMILY_INEXPRESSIBLE_32BIT_LOOKUP")
    return {"schema":"mass.t2.source-only-readiness.v1",
       "synthetic_source_kinds":2,"new_family_not_from_old_F124_hard_negative_source":True,
       "original_public_observations_per_case":48,
       "new_unseen_source_constructed":0,
       "SBOX_permutation_min_description_bits":unseen_family_entropy_lower_bound_bits(),
       "current_learned_task_params_bits":32,
       "complete_resource_parity":False,
       "scientific_transfer_ready":False}
if __name__=="__main__":print(json.dumps(attest(),sort_keys=True))

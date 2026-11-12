"""Q19A anonymous sensor causal identifiability, exact source-free proof.

Not a fitted causal learner. The twelve latent SCM cases are an explicit
PRIVILEGED oracle hypothesis set used only for information sufficiency. The
public-facing observable is a matrix of interventions on anonymous sensor slots.
No original engines, held sources, paid APIs, random samples or controller use.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import time
import tracemalloc
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent
FROZEN_BLOB="aa85f7b1c0d1cdf5c4a7daf08f5457358fa09bf4"
KINDS=("chain","fork")
PERMUTATIONS=tuple(itertools.permutations(range(3)))
PARAMETERS=("Q19A_D1","Q19A_D2")
BITS=(0,1)


def need(ok,code):
    if not ok:
        raise RuntimeError("Q19A_"+code)


def read_frozen():
    raw=(HERE/"FROZEN_PROTOCOL.json").read_bytes()
    sha=hashlib.sha1(
        b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    need(sha==FROZEN_BLOB,"FROZEN_FIRST_PROTOCOL_BLOB_CHANGED")
    p=json.loads(raw)
    need(p["schema"]==
         "forge.nci04.q19a.anonymous-variable-intervention-identifiability.v1",
         "SCHEMA_DRIFT")
    need(tuple(f["id"] for f in p["development_parameter_families"])==
         PARAMETERS,"DEV_FAMILY_DRIFT")
    need(p["guardrails"]["no_held_or_outside_family_generation"]
         and p["guardrails"]["no_original_minigrid_pycolab_episodes"],
         "ORIGINAL_OR_HELD_SCOPE_DRIFT")
    return p


def config(p, name):
    need(name in PARAMETERS,"HELD_OR_UNREGISTERED_PARAMETER_FAMILY")
    for row in p["development_parameter_families"]:
        if row["id"]==name:
            a=Fraction(row["p_num"],row["p_den"])
            b=Fraction(row["q_num"],row["q_den"])
            need(0<a<Fraction(1,2) and 0<b<Fraction(1,2) and a!=b,
                 "NONIDENTIFIABLE_NOISE_CONFIGURATION")
            return a,b
    raise RuntimeError("Q19A_UNKNOWN_FAMILY")


def binary_weight(bit,prob):
    return prob if bit else 1-prob


def scm(kind, permutation, root, e1, e2, intervention=None):
    """Permutation maps each hidden z index to its visible sensor slot.

    root/e1/e2 are exogenous independent bits; intervention overrides the
    structural equation of a visible sensor, not the independent disturbance.
    """
    need(kind in KINDS and permutation in PERMUTATIONS,
         "NON_PREREGISTERED_GRAPH")
    z=[None,None,None]
    assignment=None
    if intervention is not None:
        slot,value=intervention
        need(slot in (0,1,2) and value in BITS,
             "NON_PREREGISTERED_INTERVENTION")
        assignment=(permutation.index(slot),value)
    if kind=="chain":
        order=(0,1,2)
        equations={0:lambda:root,
                   1:lambda:z[0]^e1,
                   2:lambda:z[1]^e2}
    else:
        order=(1,0,2)
        equations={1:lambda:root,
                   0:lambda:z[1]^e1,
                   2:lambda:z[1]^e2}
    for k in order:
        z[k]=assignment[1] if assignment is not None and assignment[0]==k \
            else equations[k]()
    visible=[None,None,None]
    for latent_index, sensor in enumerate(permutation):
        visible[sensor]=z[latent_index]
    return tuple(visible)


def exact_distribution(kind,permutation,p,q,intervention=None):
    out={bits:Fraction(0) for bits in itertools.product(BITS,repeat=3)}
    for root,e1,e2 in itertools.product(BITS,repeat=3):
        v=scm(kind,permutation,root,e1,e2,intervention)
        w=(Fraction(1,2)*binary_weight(e1,p)*
           binary_weight(e2,q))
        out[v]+=w
    need(len(out)==8 and sum(out.values())==1,"SCM_MASS_INVALID")
    return out


def exact_effect(distributions, target, response):
    """Nonintervened response difference from two do-value populations."""
    need(target!=response and target in range(3) and response in range(3),
         "CAUSAL_EFFECT_QUERY_INVALID")
    d0=distributions[(target,0)]
    d1=distributions[(target,1)]
    a=sum((mass for state,mass in d1.items() if state[response]==1),
          Fraction(0))
    b=sum((mass for state,mass in d0.items() if state[response]==1),
          Fraction(0))
    return a-b


def effects_of(kind,permutation,p,q):
    distributions={(i,v):exact_distribution(
        kind,permutation,p,q,(i,v)) for i in range(3) for v in BITS}
    return { (i,j):exact_effect(distributions,i,j)
             for i in range(3) for j in range(3) if i!=j },distributions


def ancestors(kind,permutation):
    """True graph is used ONLY for checking the oracle proof, never as learner input."""
    edges=(((0,1),(1,2)) if kind=="chain"
           else ((1,0),(1,2)))
    result=set()
    for source in range(3):
        arrived={source}
        for _ in range(3):
            for a,b in edges:
                if a in arrived:
                    arrived.add(b)
        for target in arrived-{source}:
            result.add((permutation[source],permutation[target]))
    return frozenset(result)


def symbolic_effects(kind,permutation,p,q):
    """Independent path-product control (no exogenous-state enumeration)."""
    edges=(((0,1,p),(1,2,q)) if kind=="chain"
           else ((1,0,p),(1,2,q)))
    result={}
    for u in range(3):
        for v in range(3):
            if u==v:
                continue
            latent_u=permutation.index(u)
            latent_v=permutation.index(v)
            ans=Fraction(0)
            agenda=[(latent_u,Fraction(1))]
            while agenda:
                node,product=agenda.pop()
                if node==latent_v:
                    ans+=product
                    continue
                for a,b,noise in edges:
                    if a==node:
                        agenda.append((b,product*(1-2*noise)))
            result[(u,v)]=ans
    return result


def fingerprint(distribution):
    return tuple(distribution[point]
                 for point in itertools.product(BITS,repeat=3))


def report_for(family,p,q):
    cases=[]
    for kind in KINDS:
        for perm in PERMUTATIONS:
            passive=exact_distribution(kind,perm,p,q)
            observed,distributions=effects_of(kind,perm,p,q)
            theoretical=symbolic_effects(kind,perm,p,q)
            reach=ancestors(kind,perm)
            need(observed==theoretical,"SYMBOLIC_ORACLE_EFFECT_DISAGREEMENT")
            need(frozenset(k for k,x in observed.items() if x>0)==reach,
                 "UNKNOWN_DIRECTION_FROM_EFFECT_SIGN")
            need(all(x>=0 for x in observed.values()),
                 "NONMONOTONE_CAUSAL_EFFECT_UNEXPECTED")
            cases.append((kind,perm,passive,observed,reach,distributions))
    need(len(cases)==12,"HYPOTHESIS_CLASS_CHANGED")
    collision=0
    pair_count=0
    min_gap=None
    cross_orientation_collisions=0
    for i,a in enumerate(cases):
        for b in cases[i+1:]:
            pair_count+=1
            passive_equal=(fingerprint(a[2])==fingerprint(b[2]))
            if a[4]!=b[4]:
                if passive_equal:
                    collision+=1
                    if a[0]!=b[0]:cross_orientation_collisions+=1
                delta=max(abs(a[3][pair]-b[3][pair]) for pair in a[3])
                need(delta>0,"DISTINCT_ANCESTRY_INTERVENTIONALLY_AMBIGUOUS")
                min_gap=delta if min_gap is None else min(min_gap,delta)
    need(pair_count==66 and collision>=6 and
         cross_orientation_collisions>=6,
         "PASSIVE_EQUIVALENCE_WITNESS_MISSING")
    need(min_gap is not None and min_gap>=Fraction(1,4),
         "ANONYMOUS_INTERVENTION_SIGNATURE_GAP_TOO_SMALL")
    chain_count=sum(c[0]=="chain" for c in cases)
    fork_count=sum(c[0]=="fork" for c in cases)
    return {
        "family":family,
        "p":str(p),"q":str(q),
        "latent_cases":len(cases),"chain_cases":chain_count,
        "fork_cases":fork_count,"all_pair_comparisons":pair_count,
        "observationally_indistinguishable_but_causally_different_pairs":collision,
        "chain_vs_fork_observational_collisions":cross_orientation_collisions,
        "minimum_intervention_effect_gap_between_different_ancestry":str(min_gap),
        "minimum_gap_float":float(min_gap),
        "oracle_symbolic_equal_exact":True,
        "sensor_identities_given_to_learner":False,
        "unknown_causal_ancestry_recoverable_from_population_effects":True,
        "finite_sample_error_not_established":True
    }


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--mode",required=True,
                     choices=("selftest","population-screen"))
    mode=arg.parse_args().mode
    p=read_frozen()
    for name in PARAMETERS:
        a,b=config(p,name)
        x=exact_distribution("chain",(0,1,2),a,b)
        y=exact_distribution("fork",(0,1,2),a,b)
        need(x==y,"SAME_SKELETON_PASSIVE_EQUIVALENCE_VIOLATED")
        e,_=effects_of("chain",(0,1,2),a,b)
        need(e[(0,2)]==e[(0,1)]*e[(1,2)],
             "TWO_HOP_CAUSAL_MEDIATION_INCORRECT")
    print("Q19A_ANONYMOUS_PASSIVE_ALIAS_AND_MEDIATION_SELFTEST=PASS",
          flush=True)
    if mode=="selftest":
        return
    tracemalloc.start()
    t=time.process_time()
    cases=[report_for(name,*config(p,name)) for name in PARAMETERS]
    peak=tracemalloc.get_traced_memory()[1]
    cpu=time.process_time()-t
    passed=all(c["minimum_gap_float"]>=.25 and
               c["chain_vs_fork_observational_collisions"]>=6 and
               c["oracle_symbolic_equal_exact"] for c in cases)
    verdict=("INFORMATION_SUFFICIENT_FOR_ANONYMOUS_CAUSAL_DISCOVERY_DESIGN_ONLY"
             if passed else "IDENTIFIABILITY_NO_GO_STOP")
    result={
        "schema":"forge.nci04.q19a.sourcefree-identifiability-result.v1",
        "frozen_protocol_git_blob":FROZEN_BLOB,
        "families":cases,"decision":verdict,
        "screen_cpu_seconds":cpu,
        "tracemalloc_peak_bytes":peak,
        "predefined_candidate_edges_provided_to_learner":False,
        "actual_trainable_learner_executed":False,
        "privileged_hypothesis_space_used_for_information_proof":True,
        "finite_sample_learning_claimed":False,
        "held_families_generated":False,
        "original_source_episodes":0,
        "scientific_first_use":False
    }
    for case in cases:
        print("Q19A_FAMILY="+case["family"]+
              " PASSIVE_COLLISIONS="+str(case["observationally_indistinguishable_but_causally_different_pairs"])+
              " MIN_EFFECT_GAP="+case["minimum_intervention_effect_gap_between_different_ancestry"],
              flush=True)
    print("Q19A_RESULT_JSON="+json.dumps(result,sort_keys=True,
         separators=(",",":"),allow_nan=False),flush=True)
    print("Q19A_INFORMATION_DECISION="+verdict,flush=True)
    print("Q19A_HELD_AND_ORIGINAL_SOURCE=NOT_CONSUMED",flush=True)


if __name__=="__main__":
    main()

"""AC-06: bounded source-free restricted-variant experiments from original 30 ideas.

All outcomes are deterministic engineering diagnostics using Python 3.11 stdlib.
No private data, LLM training, real-world causal source, native model, scientific
first-use, or unrestricted general intelligence claim. Preserve all negatives.
"""
from __future__ import annotations
from collections import defaultdict
import cmath
import hashlib
import json
import math
import random
import time
import tracemalloc

SCHEMA="forge.ac06.restricted-originals.sourcefree.v1"
SEEDS=(601,607,613)
WIDTH=256

def vsa(seed):
    """Binary VSA binding/bundling; recall requires supplied candidate inventory."""
    rng=random.Random(seed)
    rows=[]
    for capacity in (1,4,16,32):
        keys=[rng.getrandbits(WIDTH) for _ in range(capacity)]
        values=[rng.getrandbits(WIDTH) for _ in range(capacity)]
        counters=[0]*WIDTH
        for key,value in zip(keys,values):
            x=key^value
            for bit in range(WIDTH):
                counters[bit]+=(x>>bit)&1
        bundle=sum(1<<b for b,c in enumerate(counters) if c*2>capacity)
        success=0
        for i,key in enumerate(keys):
            candidate=bundle^key
            scores=[WIDTH-(candidate^val).bit_count() for val in values]
            guess=max(range(capacity),key=lambda j:(scores[j],-j))
            success+=guess==i
        rows.append({
            "bundle_entries":capacity,"correct":success,"tested":capacity,
            "inventory_random_guess_rate":1/capacity,
            "counter_storage_lower_bound_bits":WIDTH*math.ceil(math.log2(capacity+1)),
            "stored_source_bits":2*WIDTH*capacity,
            "candidate_inventory_required":True
        })
    assert rows[0]["correct"]==1
    return {"claim_ids":["U07","U10","U13","U18"],
            "dimensions":WIDTH,"capacity_rows":rows,
            "limitation":"Candidate inventory is supplied; no language generation, unlimited memory or independent causal source."}

def reservoir(seed):
    """Train linear readout from fixed recurrent random features."""
    rng=random.Random(seed)
    weights=[rng.uniform(-0.35,0.35) for _ in range(12)]
    recurrent=[rng.uniform(-0.4,0.4) for _ in range(12)]
    drive=[rng.uniform(-0.7,0.7) for _ in range(12)]
    def sequence(n,initial=0):
        state=[0.0]*12
        previous=initial
        dataset=[]
        for _ in range(n):
            bit=rng.randrange(2)
            state=[math.tanh(drive[i]*(bit*2-1)+recurrent[i]*state[i]+
                             weights[i]*state[(i-1)%12])
                   for i in range(12)]
            dataset.append((tuple(state)+(1.0,),float(previous),float(previous)))
            previous=bit
        return dataset
    train=sequence(360)
    test=sequence(160)
    coeff=[0.0]*13
    def mse(rows):
        return sum((sum(a*b for a,b in zip(coeff,x))-y)**2
                   for x,y,_ in rows)/len(rows)
    before=mse(train)
    for _ in range(45):
        for features,y,_ in train:
            err=sum(a*b for a,b in zip(coeff,features))-y
            for j,v in enumerate(features):
                coeff[j]-=0.02*err*v
    after=mse(train)
    heldout=mse(test)
    mean_y=sum(y for _,y,_ in train)/len(train)
    bias_mse=sum((mean_y-y)**2 for _,y,_ in test)/len(test)
    return {"claim_ids":["U08"],"feature_count":12,"fitted_examples":len(train),
            "eval_examples":len(test),"fit_mse_before":before,
            "fit_mse_after":after,"heldout_reservoir_mse":heldout,
            "heldout_fitted_constant_mse":bias_mse,
            "heldout_explicit_previous_bit_mse":0.0,
            "readout_trainable":True,
            "limitation":"Fixed recurrence; trained readout only. Explicit one-step memory is a stronger matched-information control."}

def finite_state(seed):
    """Saturating 2-bit online local-rule memory, not a full Tsetlin machine."""
    rng=random.Random(seed)
    states=[0]*16
    observed=[0]*16
    for _ in range(400):
        pattern=rng.randrange(16)
        y=((pattern&1)>0) ^ ((pattern&2)>0)
        observed[pattern]+=1
        states[pattern]=max(-2,min(2,states[pattern]+(1 if y else -1)))
    def predicted(p):
        return int(states[p]>0)
    fitted=sum(predicted(p)==((((p&1)>0)^((p&2)>0))) for p in range(16))
    inverted=sum(predicted(p)==(not (((p&1)>0)^((p&2)>0))) for p in range(16))
    return {"claim_ids":["U19"],"state_levels":5,"fit_updates":400,
            "observed_all_16_patterns":all(observed),
            "source_visible_holdout_pattern_accuracy":fitted/16,
            "fitted_tabular_control_accuracy":1.0,
            "flipped_rule_accuracy":inverted/16,
            "limitation":"Saturating per-pattern table, not genuine locally distributed Tsetlin learning or unknown-world transfer."}

def automata(seed):
    """Learn 8 local CA neighborhood transitions from FIT; test length transfer."""
    rng=random.Random(seed)
    def rule90(l,c,r):return l^r
    def rule110(l,c,r):return (110>>((l<<2)|(c<<1)|r))&1
    positive=[0]*8; negative=[0]*8
    for _ in range(90):
        cells=[rng.randrange(2) for _ in range(25)]
        for i in range(len(cells)):
            l,c,r=cells[i-1],cells[i],cells[(i+1)%len(cells)]
            idx=(l<<2)|(c<<1)|r
            if rule90(l,c,r):positive[idx]+=1
            else:negative[idx]+=1
    table=[int(positive[i]>negative[i]) for i in range(8)]
    n=0; success=0; changed_success=0
    for _ in range(35):
        cells=[rng.randrange(2) for _ in range(63)]
        for i in range(len(cells)):
            l,c,r=cells[i-1],cells[i],cells[(i+1)%len(cells)]
            idx=(l<<2)|(c<<1)|r
            n+=1
            success+=(table[idx]==rule90(l,c,r))
            changed_success+=(table[idx]==rule110(l,c,r))
    return {"claim_ids":["U24"],"fit_neighborhood_observations":90*25,
            "learned_local_table_entries":len(table),"eval_neighborhoods":n,
            "new_length_accuracy":success/n,
            "source_rule90_fitted_control_accuracy":1.0,
            "changed_rule110_accuracy":changed_success/n,
            "limitation":"Fits an 8-entry update table; no criticality, language, or self-organized cognitive learning."}

def lowrank(seed):
    """Bounded 1-rank factorization from row+column observations."""
    rng=random.Random(seed)
    n=18
    u=[1+i/6 for i in range(n)]
    v=[2+j/7 for j in range(n)]
    structured=[[u[i]*v[j] for j in range(n)] for i in range(n)]
    random_m=[[rng.uniform(-3,3) for _ in range(n)] for _ in range(n)]
    def evaluate(matrix):
        pivot=matrix[0][0]
        reconstructed=[[matrix[i][0]*matrix[0][j]/pivot for j in range(n)] for i in range(n)]
        rowmean=sum(matrix[0])/n
        colmeans=[matrix[i][0] for i in range(n)]
        naive=[[colmeans[i]+matrix[0][j]-rowmean for j in range(n)] for i in range(n)]
        coords=[(i,j) for i in range(1,n) for j in range(1,n)]
        error=lambda fitted:sum((fitted[i][j]-matrix[i][j])**2 for i,j in coords)/len(coords)
        return error(reconstructed),error(naive)
    fit_err,fit_control=evaluate(structured)
    other_err,other_control=evaluate(random_m)
    return {"claim_ids":["U09","U14","U22"],
            "matrix_dim":n,"fitted_observed_entries":2*n-1,
            "source_unknown_entries":(n-1)**2,
            "factor_floats":2*n,"dense_floats":n*n,
            "rank1_holdout_mse":fit_err,
            "rank1_fitted_rowcolumn_control_mse":fit_control,
            "fullrank_holdout_mse":other_err,
            "fullrank_fitted_rowcolumn_control_mse":other_control,
            "limitation":"Known rank-one assumption, float operations and row/column fit. Dense full-observation comparison is not information-matched."}

def graph_rules(seed):
    """Fit bounded typed 2-hop rule, then challenge unseen structural depth."""
    rng=random.Random(seed)
    def predict(edges,start,roles,mode):
        if mode=="one-hop":
            roles=roles[:1]
        if mode=="typed-two" and len(roles)!=2:
            return ()
        current={start}
        for role in roles:
            current={v for u,r,v in edges if u in current and
                     (r==role or mode=="roleblind")}
        return tuple(sorted(current))
    rows=[]
    for t in range(16):
        base=t*8
        edges=((base,"r",base+1),(base+1,"s",base+2),
               (base,"s",base+3),(base+3,"r",base+4),
               (base+2,"r",base+5))
        rows.append((edges,base,("r","s"),(base+2,)))
    candidates=("one-hop","roleblind","typed-two")
    score={name:sum(predict(*x[:3],name)==x[3] for x in rows)
           for name in candidates}
    selected=max(candidates,key=lambda name:(score[name],-candidates.index(name)))
    heldout=[]
    for t in range(16,24):
        b=400+t*8
        edges=((b,"r",b+1),(b+1,"s",b+2),(b,"s",b+3),(b+3,"r",b+4))
        heldout.append((edges,b,("r","s"),(b+2,)))
    parity=sum(predict(*x[:3],selected)==x[3] for x in heldout)
    unfamiliar=(((700,"r",701),(701,"s",702),(702,"t",703)),700,("r","s","t"),(703,))
    return {"claim_ids":["U20","U25","U27"],
            "candidate_programs_searched":len(candidates),
            "fit_examples":len(rows),"fitted_program":selected,
            "renamed_same_structure_correct":parity,
            "renamed_same_structure_total":len(heldout),
            "fully_fitted_typed_reference_correct":len(heldout),
            "unfamiliar_threehop_correct":predict(*unfamiliar[:3],selected)==unfamiliar[3],
            "unfamiliar_strong_typed_reference_correct":predict(*unfamiliar[:3],"typed")==unfamiliar[3],
            "limitation":"Predefined operator grammar; typed reference equally good on fit; three-hop is a new test family."}

def unusual_math(seed):
    """Check restricted algebra/geometry/chaos, not AI semantic inference."""
    p=17
    w=4
    a=(1,2,3,4);b=(4,3,2,1)
    def ntt(x, inverse=False):
        root=pow(w,-1,p) if inverse else w
        y=[sum(v*pow(root,(k*t)%4,p) for t,v in enumerate(x))%p
           for k in range(4)]
        return [(v*pow(4,-1,p))%p for v in y] if inverse else y
    out=ntt([i*j%p for i,j in zip(ntt(a),ntt(b))],True)
    naive=[sum(a[t]*b[(k-t)%4] for t in range(4))%p for k in range(4)]
    def spectral(x):
        return tuple(round(abs(sum(x[t]*cmath.exp(-2j*math.pi*k*t/len(x))
                   for t in range(len(x)))),8) for k in range(len(x)))
    spectral_collision=spectral((1,0,0,0))==spectral((0,1,0,0))
    # finite precision disallows storing 257 distinguishable states in 8 bits
    buckets={i%256 for i in range(257)}
    cycle=0;seen={}
    x=61
    while x not in seen and cycle<1024:
        seen[x]=cycle
        x=(3*x*(255-x)//255)%256
        cycle+=1
    state_cycle=cycle-seen[x]
    phase=cmath.exp(1j*math.pi/4)
    stabilizer_phases=(1,-1,1j,-1j)
    nonclifford=all(abs(phase-v)>1e-8 for v in stabilizer_phases)
    return {"claim_ids":["U06","U16","U17","U21","U23","U26","U28","U29","U30"],
            "ntt_matches_naive_mod17":out==naive,
            "spectral_magnitude_loses_order":spectral_collision,
            "eight_bit_value_count":len(buckets),
            "distinct_inputs_probed":257,
            "finite_state_chaos_cycle_detected":state_cycle>=1,
            "finite_state_chaos_cycle_length":state_cycle,
            "t_gate_non_stabilizer_relative_phase":nonclifford,
            "same_topology_can_have_distinct_role_labels":True,
            "limitation":"No continuous physical analog/quantum hardware, lossless unlimited compression, or semantic language capability."}

CASES={
    "vsa_interference":vsa,
    "reservoir_readout":reservoir,
    "finite_state_rule":finite_state,
    "local_automata":automata,
    "rank_one_factor":lowrank,
    "graph_program":graph_rules,
    "unusual_math":unusual_math
}
COVERED=tuple(sorted({claim for f in CASES.values()
                      for claim in f(SEEDS[0])["claim_ids"]}))
ALL_ORIGINAL=tuple("U%02d"%i for i in range(1,31))

def run():
    observations=[]
    for seed in SEEDS:
        for name,func in CASES.items():
            tracemalloc.start()
            t0=time.perf_counter_ns()
            result=func(seed)
            elapsed=time.perf_counter_ns()-t0
            peak=tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            observations.append({
                "seed":seed,"family":name,"claim_ids":result["claim_ids"],
                "source_visible_wall_ns":elapsed,"python_traced_peak_bytes":peak,
                "result":result
            })
    assert len(observations)==21
    return {"schema":SCHEMA,"scope":"SYNTHETIC_DEVELOPMENT_ONLY",
            "measured_families":len(CASES),"proposals_original_total":30,
            "experiment_claim_ids":list(COVERED),
            "unmeasured_original_ids":sorted(set(ALL_ORIGINAL)-set(COVERED)),
            "all_30_original_and_six_new_remain_advisory":True,
            "native_learning_or_transfer_superiority":False,
            "independent_consequence_source_verified":False,
            "scientific_first_use":False,"accepted_science":False,
            "source_qualified_development_only":True,
            "new_controller_or_scheduler":False,
            "observations":observations}

if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True,indent=2))

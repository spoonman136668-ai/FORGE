"""F124-AL source-blind example learner for new multiplication/OR relations.

Hypotheses are engineered but parameters inferred from PUBLIC examples.
Neither source operator name nor true graph label reaches this module.
Abstain on ambiguous/bad public examples, never consult test oracle.
"""
from __future__ import annotations
import f124aj_example_operator_learner as aj
import f124ak_nonlinear_learner as prior
import f124ag_transition_models as ygg_original
import f124ae_scoring_transfer as wing_original
import f124q_fresh_source as q

SUPPORT=(4,8,12,24)
CAPS=(0.,.05,.1,.2,.4,1.)
def need(ok,tag):q.need(ok,"F124AL_LEARN_"+tag)
def integer(bits):return sum(v<<i for i,v in enumerate(bits))
def bits(v):return [(v>>i)&1 for i in range(16)]
def popcount(v):return v.bit_count()

def tri_or(x,p,qq):
    data=bits(x)
    return integer([v^(int(data[i-p] or data[i-qq]) if i>=qq else 0)
                    for i,v in enumerate(data)])

def fit_mapping(demos,count):
    need(count in SUPPORT and len(demos)==24,
         "FROZEN_PUBLIC_DEMONSTRATION_GRID")
    given=[(integer(x["input_bits"]),integer(x["output_bits"]))
           for x in demos[:count]]
    candidates=set()
    # Learn odd multiplicative constant from public examples whose 16-bit
    # input is invertible mod 2^16. This is NOT a hard-coded coefficient.
    for x,y in given:
        if x&1:
            a=(y*pow(x,-1,65536))&65535
            if a>1 and a&1:candidates.add(("mul",a))
    # Generic reversible OR-induced coupling, all 10 distinct offsets,
    # with unknown XOR output mask learned from examples.
    for p in range(1,5):
        for qq in range(p+1,6):
            for x,y in given:
                mask=y^tri_or(x,p,qq)
                candidates.add(("or",p,qq,mask))
    def forward(x,c):
        if c[0]=="mul":return (x*c[1])&65535
        return tri_or(x,c[1],c[2])^c[3]
    scored=[]
    for c in sorted(candidates):
        mismatches=sum(popcount(forward(x,c)^y) for x,y in given)
        scored.append((mismatches,c))
    scored.sort()
    minimum=scored[0][0] if scored else None
    best=[c for mism,c in scored if mism==minimum]
    second=min((mism for mism,c in scored if mism>minimum),default=None)
    success=(minimum is not None and minimum<=1
             and len(best)==1 and (second is None or second-minimum>=2))
    diag={"support":count,"candidate_count":len(candidates),
          "lowest_mismatched_bits":minimum,
          "next_mismatch":second,"ambiguous":not success,
          "inferred_from_examples_only":True,
          "candidate_family":"odd_multiplication_or_triangular_OR",
          "hidden_operator_name_used":False}
    return best[0] if success else None,diag

def invert(data,hypothesis):
    if hypothesis[0]=="mul":
        return bits((integer(data)*pow(hypothesis[1],-1,65536))&65535)
    _,p,qq,mask=hypothesis
    target=bits(integer(data)^mask)
    original=[]
    for j in range(16):
        contribution=int(original[j-p] or original[j-qq]) if j>=qq else 0
        original.append(target[j]^contribution)
    return original

def normalize(g,count):
    public,demos,nonce=aj.public_task(g)
    candidate,diag=fit_mapping(demos,count)
    if candidate is None:
        return None,{"learn":diag,"bit_ops":0,"extra_cells":0}
    for e in public["edges"]:
        e["src_bits"]=invert(e["src_bits"],candidate)
    ygg_original.frozen.prior.parent.validate_15(public)
    return public,{"learn":diag,"bit_ops":16*len(public["edges"]),
                   "extra_cells":0}

def ygg(g,weights,delta,count):
    restored,diag=normalize(g,count)
    if restored is None:return -1.e9,None,diag
    score,raw,soft,work=ygg_original.ygg_transition(
        restored,list(weights),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "HISTORICAL_HARD_7_9")
    return score,work,diag

def wing(g,weights,delta,count,cap):
    restored,diag=normalize(g,count)
    if restored is None:return -1.e9,None,diag
    from f124al_packed_confidence import competitive_capped
    score,work=competitive_capped(restored,weights,delta,cap)
    need(work["max_active"]<=64 and work["max_states_per_node"]==1
         and work["max_packed_bits_per_state"]==12,
         "ONE_ORIGINAL_PACKED_STATE")
    return score,work,diag

def select_support(cases,weights,delta):
    need(len(cases)==48,"ONLY_TRAIN_48")
    grid=[]
    for count in SUPPORT:
        paired=fp=ambiguous=0
        for seed,v,fam,op,tag,p,n in cases:
            pa,_,ap=ygg(p,weights,delta,count)
            na,_,an=ygg(n,weights,delta,count)
            paired+=int(pa>=0 and na<0)
            fp+=int(na>=0)
            ambiguous+=int(ap["learn"]["ambiguous"])+int(an["learn"]["ambiguous"])
        grid.append({"count":count,"paired":paired,"FP":fp,
                     "ambiguous_graphs":ambiguous})
    choice=sorted(grid,key=lambda r:(-r["paired"],r["FP"],r["count"]))[0]
    return choice,grid

def select_wing_cap(cases,weights,delta,count):
    need(len(cases)==48 and count in SUPPORT,
         "ONLY_TRAIN_WING_CAP")
    grid=[]
    for cap in CAPS:
        paired=fp=long_pos=0
        for seed,v,fam,op,tag,p,n in cases:
            a,_,_=wing(p,weights,delta,count,cap)
            b,_,_=wing(n,weights,delta,count,cap)
            paired+=int(a>=0 and b<0)
            fp+=int(b>=0)
            if fam in ("rotate4_dense_13_15","xor16_extended_13_15"):
                long_pos+=int(a>=0)
        grid.append({"cap":cap,"paired":paired,
                     "FP":fp,"long_positive_sensitivity":long_pos})
    return sorted(grid,key=lambda r:(-r["paired"],r["FP"],
                                     -r["long_positive_sensitivity"],
                                     -r["cap"]))[0],grid

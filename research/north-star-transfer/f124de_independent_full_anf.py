"""F124-DE independently implemented fully trained cross-bit ANF competitor.

Same full degree<=4 polynomial on eight raw input bits, all TEN possible
public input-register pairs, same FIT rows, same minimum coefficient/degree
selection and same 256-point compiled runtime, but independent elimination
and source parsing. Not a weak pre-bitwise control. No source or candidate
imports and no arithmetic operator templates.
"""
from __future__ import annotations
from itertools import combinations

NAMES=("alpha","beta","gamma")
MONO=[sum(1<<j for j in c) for level in range(5) for c in combinations(range(8),level)]
COLS=len(MONO)
assert COLS==163
PAIR_POSITIONS=tuple(combinations(range(5),2))

def need(ok,why):
    if not ok:raise RuntimeError("F124DE_PEER_"+why)

def fit_rows(fit):
    need(type(fit) is list and len(fit)==24,"PEER_FIT_ALL_24")
    observations=[]
    for ep in fit:
        need(type(ep) is dict and set(ep)=={"initial","events"}
             and set(ep["initial"])==set(NAMES)
             and len(ep["events"])==8,"PEER_PUBLIC_EP")
        state={name:list(x) for name,x in ep["initial"].items()}
        need(all(len(v)==2 and all(type(x) is int and 0<=x<16 for x in v)
                 for v in state.values()),"PEER_PUBLIC_NIBBLE")
        for event in ep["events"]:
            need(set(event)=={"target","source","event","observed"}
                 and event["target"] in NAMES and event["source"] in NAMES
                 and event["target"]!=event["source"]
                 and all(type(event[k]) is int and 0<=event[k]<16
                     for k in ("event","observed")),"PEER_PUBLIC_EVENT")
            own=state[event["target"]];foreign=state[event["source"]]
            observations.append((own[0],own[1],foreign[0],foreign[1],
                                 event["event"],event["observed"]))
            state[event["target"]]=[event["observed"],own[0]]
    need(len(observations)==192,"PEER_FULL_FIT_192")
    return observations

def encoded_anf(pair8):
    # Independent 163-term degree ordered complete feature vector.
    answer=0
    for i,term in enumerate(MONO):
        if pair8&term==term:answer|=1<<i
    return answer

def solve(labels,bit):
    # Row-reduced elimination on already source-neutral polynomial design.
    # Same lexicographic sparse-free-variable convention as candidate.
    equations=[z|(((y>>bit)&1)<<COLS) for z,y in labels]
    pivot=[]
    top=0
    for col in range(COLS):
        found=next((r for r in range(top,len(equations)) if equations[r]>>col&1),None)
        if found is None:continue
        equations[top],equations[found]=equations[found],equations[top]
        for row in range(len(equations)):
            if row!=top and (equations[row]>>col)&1:
                equations[row]^=equations[top]
        pivot.append(col);top+=1
        if top==len(equations):break
    lowbits=(1<<COLS)-1
    if any((r&lowbits)==0 and (r>>COLS)&1 for r in equations):
        return None,len(pivot)
    theta=0
    for i in reversed(range(len(pivot))):
        col=pivot[i];row=equations[i]
        if ((row>>COLS)&1)^((row&theta).bit_count()&1):
            theta|=1<<col
    return theta,len(pivot)

# Independently generated 256-element all-assignment vector columns. Strong
# peer also benefits from optimized full-table compilation, not per-bit
# recursive eval at scoring time.
COL_FLAGS=tuple(sum(1<<i for i in range(256) if i&term==term) for term in MONO)
def compile_bitplane(coeff):
    result=0
    for k in range(COLS):
        if coeff>>k&1:result^=COL_FLAGS[k]
    return result

def compute(model,x):
    col_a,col_b=model["columns"]
    pos=x[col_a]+16*x[col_b]
    result=0
    for k,mask in enumerate(model["truth_bitplanes"]):
        result|=((mask>>pos)&1)<<k
    return result

def train(fit):
    examples=fit_rows(fit)
    best=None
    for cols in PAIR_POSITIONS:
        design=[(encoded_anf(row[cols[0]]+(row[cols[1]]<<4)),row[5])
                for row in examples]
        answers=[];ranks=[]
        for out in range(4):
            answer,rank=solve(design,out)
            if answer is None:break
            answers.append(answer);ranks.append(rank)
        if len(answers)<4:continue
        score=(sum(x.bit_count() for x in answers),
               sum(sum(term.bit_count() for i,term in enumerate(MONO) if x>>i&1)
                   for x in answers),cols)
        if best is None or score<best[0]:
            best=(score,tuple(answers),tuple(cols),ranks)
    if best is None:
        return None,{"natural_FIT":False,"FIT_rows":192,
                     "source_neutral_polynomial_terms":163,
                     "all_ten_pair_wirings_searched":True}
    complexity,coef,cols,ranks=best
    model={"columns":cols,"truth_bitplanes":tuple(compile_bitplane(x) for x in coef),
           "learned_coefficients":coef}
    errors=sum((compute(model,row)^row[5]).bit_count() for row in examples)
    need(errors==0,"PEER_NO_SOURCE_OPERATOR_FIT_EXACTNESS")
    unique=len({row[cols[0]]+(row[cols[1]]<<4) for row in examples})
    return model,{"natural_FIT":True,"FIT_rows":192,"FIT_bit_errors":0,
      "full_equal_163_monomial_vocabulary":True,
      "all_ten_pair_wirings_searched":True,
      "selected_raw_register_slots":list(cols),
      "unique_pair_inputs":unique,"unobserved_unrestricted_truth_entries":256-unique,
      "learned_monomial_count":complexity[0],
      "learned_degree_weight":complexity[1],
      "fit_pivot_ranks":ranks,"complete_native_256_pair_lookup_compilation":True}

def rollout(model,ep):
    need(model is not None,"PEER_NATURAL_FIT_REQUIRED")
    register={name:list(v) for name,v in ep["initial"].items()}
    output=[]
    for e in ep["events"]:
        target=e["target"];src=e["source"]
        a=register[target];b=register[src]
        y=compute(model,(a[0],a[1],b[0],b[1],e["event"]))
        output.append(y)
        register[target]=[y,a[0]]
    return output

def score(model,ep):
    predicted=rollout(model,ep);labels=[v["observed"] for v in ep["events"]]
    return {"exact":predicted==labels,"bit_errors":sum((a^b).bit_count() for a,b in zip(predicted,labels)),
            "native_events":len(predicted)}

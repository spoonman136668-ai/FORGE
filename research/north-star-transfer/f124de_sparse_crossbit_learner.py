"""F124-DE source-neutral sparse cross-bit causal polynomial induction.

Given only 24 public FIT eight-step trajectories, infer WHICH 2 out of 5
nibble input registers caused the response and four output-bit polynomials
of degree <=4 over all 8 raw bits. No ADD/rotate/carry/source law template,
no meta class label, no source generator import. Fit via incremental packed
GF2 constraint echelon; select least coefficients to avoid overfit across
equally consistent candidate register pairs. Compile into compact full
256-nibble-pair table by SIMD-style integer bit-parallel monomial masks.
"""
from __future__ import annotations
import hashlib
import itertools
import json
ROLES=("alpha","beta","gamma")
MONOMIALS=tuple(sum(1<<k for k in pair)
                for n in range(5) for pair in itertools.combinations(range(8),n))
WIDTH=len(MONOMIALS)
assert WIDTH==163
PAIR_CANDIDATES=tuple(itertools.combinations(range(5),2))
def need(ok,reason):
    if not ok:raise RuntimeError("F124DE_POLYNOMIAL_"+reason)
def training_rows(episodes):
    need(type(episodes) is list and len(episodes)==24,
         "COMPLETE_24_FIT_EPISODES")
    data=[]
    for ep in episodes:
        need(type(ep) is dict and set(ep)=={"initial","events"} and
             type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES)
             and type(ep["events"]) is list and len(ep["events"])==8,
             "COMPLETE_EIGHT_EVENT_INPUT")
        state={name:list(pair) for name,pair in ep["initial"].items()}
        need(all(type(pair) is list and len(pair)==2 and all(
            type(x) is int and 0<=x<16 for x in pair)
            for pair in state.values()),"ALL_INITIAL_NIBBLES")
        for event in ep["events"]:
            need(type(event) is dict and set(event)=={"target","source","event","observed"}
                 and event["target"] in ROLES and event["source"] in ROLES
                 and event["target"]!=event["source"] and
                 all(type(event[k]) is int and 0<=event[k]<16
                     for k in ("event","observed")),"ALL_PUBLIC_INPUT_LABELS")
            own=state[event["target"]];src=state[event["source"]]
            data.append(((own[0],own[1],src[0],src[1],event["event"]),event["observed"]))
            state[event["target"]]=[event["observed"],own[0]]
    need(len(data)==192,"COMPLETE_FIT_192_EVENT_SUPERVISION")
    return data
def features(value):
    # Sparse bounded feature bits, degree ordered. Power to all 163
    # coefficients learned, not a provided arithmetic operator formula.
    return sum((1<<k) for k,term in enumerate(MONOMIALS) if (value&term)==term)
def eliminate(equations,output_bit):
    # One-pass echelon for 192 packed binary equations; each row carries
    # 163 unknown monomial coefficients and one output parity constraint.
    pivot={}
    lower=(1<<WIDTH)-1
    for x,truth in equations:
        row=x|(((truth>>output_bit)&1)<<WIDTH)
        while row&lower:
            low=row&-row
            i=low.bit_length()-1
            if i in pivot:row^=pivot[i]
            else:
                pivot[i]=row
                break
        else:
            if row>>WIDTH&1:return None,len(pivot)
    theta=0
    for i in sorted(pivot,reverse=True):
        row=pivot[i]
        value=((row>>WIDTH)&1)^((row&theta).bit_count()&1)
        if value:theta|=1<<i
    return theta,len(pivot)
def eval_coeff(mask,inputbits):
    return (mask&features(inputbits)).bit_count()&1

# Bit-parallel exhaustive compilation once during FIT. Each bit of a
# 256-bit machine-int contains one nibble-pair assignment's feature.
PARALLEL_TERM_COLUMNS=tuple(sum(1<<v for v in range(256) if (v&term)==term)
                            for term in MONOMIALS)
def compile_lut(weights):
    # Four masked output bitplanes, assembled as a tuple of four 256-bit
    # ints. No CPU-intensive recursive Boolean program during inference.
    planes=[]
    for mask in weights:
        values=0
        while mask:
            low=mask&-mask
            values^=PARALLEL_TERM_COLUMNS[low.bit_length()-1]
            mask^=low
        planes.append(values)
    return tuple(planes)
def predict_raw(model,raw):
    a,b=model["wiring"]
    index=raw[a]|(raw[b]<<4)
    return sum(((plane>>index)&1)<<k for k,plane in enumerate(model["planes"]))
def fit(FIT):
    rows=training_rows(FIT)
    best=None
    observations=[]
    for pair in PAIR_CANDIDATES:
        binary=[(features(inputs[pair[0]]|(inputs[pair[1]]<<4)),y)
                for inputs,y in rows]
        unique=len({inputs[pair[0]]|(inputs[pair[1]]<<4) for inputs,_ in rows})
        matches=[]
        ranks=[]
        for bit in range(4):
            coeff,rank=eliminate(binary,bit)
            if coeff is None:break
            matches.append(coeff);ranks.append(rank)
        if len(matches)==4:
            # Complexity = total learned polynomial monomials, then the
            # degree-weighted total, then canonical wiring as final tie.
            score=(sum(c.bit_count() for c in matches),
                   sum(sum(MONOMIALS[k].bit_count()
                      for k in range(WIDTH) if c>>k&1) for c in matches),pair)
            observations.append({"pair":list(pair),"seen_public_pair_rows":unique,
                                 "FIT_pivot_ranks":ranks,
                                 "learned_monomials":score[0]})
            if best is None or score<best[0]:
                best=(score,tuple(matches),pair,unique)
    if best is None:return None,{"natural_FIT":False,"FIT_rows":len(rows),
                "generic_degree4_two_nibble_basis":WIDTH,
                "source_class_unknown":True,
                "all_10_input_wirings_tested":True}
    score,coef,pair,uniq=best
    model={"wiring":pair,"planes":compile_lut(coef),
           "fitted_coefficients":coef,"unique_training_pairs":uniq}
    error=sum((predict_raw(model,raw)^value).bit_count() for raw,value in rows)
    need(error==0,"ALL_SUPERVISED_CROSSBIT_LABELS_NOT_EXACT")
    return model,{"natural_FIT":True,"FIT_rows":192,"FIT_bit_errors":0,
          "input_nibble_registers_fit_from_public_data":list(pair),
          "unique_raw_2_nibble_training_combinations":uniq,
          "unseen_unrestricted_truth_cells_at_least":256-uniq,
          "learned_coefficients_nonzero":score[0],
          "generic_inductive_bias":"all 163 degree<=4 monomials of 8 raw Boolean variables",
          "feature_vector_input_arity":8,
          "all_10_input_wirings_tested":True,
          "full_256_case_LUT_compiled_from_FIT_coefficients":True,
          "fully_fit_candidate_pairs":observations}
def rollout(model,ep):
    need(model is not None and "planes" in model,"MODEL_MUST_FIT_NATURALLY")
    register={r:list(value) for r,value in ep["initial"].items()}
    out=[]
    for e in ep["events"]:
        own=register[e["target"]];src=register[e["source"]]
        y=predict_raw(model,(own[0],own[1],src[0],src[1],e["event"]))
        out.append(y)
        register[e["target"]]=[y,own[0]]
    return out
def score(model,ep):
    pred=rollout(model,ep);expected=[e["observed"] for e in ep["events"]]
    return {"exact":pred==expected,"bit_errors":sum((a^b).bit_count()
       for a,b in zip(pred,expected)),"native_events":len(pred)}
def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

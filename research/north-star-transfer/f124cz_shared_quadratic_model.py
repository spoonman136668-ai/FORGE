"""F124-CZ learned role-shared quadratic source-neutral causal transition.

An overcomplete, disclosed hypothesis class of 20 raw inputs + intercept +
all 190 order-two cross-bit interactions is fitted on 24 FIT episodes only.
The source is independent. Model does NOT know actual hidden quadratic
terms or whether the source world obeys quadratic assumptions. Canonical
Gaussian elimination privileges cross-role interactions, then remaining
quadratic terms. Both shared nonlinear models see the same 211 terms.

Important: exact FIT interpolation on unsupported carry worlds is NOT
evidence of generalization; only natural CHECK and heldout can admit.
"""
from __future__ import annotations
import hashlib
import json

ROLES=("alpha","beta","gamma")
WIDTH=211

def need(ok,reason):
    if not ok:raise ValueError("F124CZ_SHARED_"+reason)

def pair_order():
    blocks=((range(4),range(8,12)),(range(4,8),range(8,12)),
            (range(4),range(12,16)),(range(16,20),range(8,12)))
    first=[]
    for aa,bb in blocks:
        for a in aa:
            for b in bb:first.append(tuple(sorted((a,b))))
    canonical=[(a,b) for a in range(20) for b in range(a+1,20)]
    pairs=list(dict.fromkeys(first+[p for p in canonical if p not in first]))
    need(len(pairs)==190,"FULL_BASIS_ALL_190_PAIRWISE_INTERACTIONS")
    return pairs

PAIRS=pair_order()

def validate(ep):
    need(type(ep) is dict and set(ep)=={"initial","events"} and
       type(ep["initial"]) is dict and set(ep["initial"])==set(ROLES),
       "PUBLIC_EPISODE_SHAPE")
    need(all(type(v) is list and len(v)==2 and
       all(type(n) is int and 0<=n<16 for n in v)
       for v in ep["initial"].values()),"ALL_ROLE_INITIALS")
    need(type(ep["events"]) is list and len(ep["events"])==8 and
       all(type(t) is dict and set(t)=={"target","source","event","observed"} and
       t["target"] in ROLES and t["source"] in ROLES and
       t["target"]!=t["source"] and type(t["event"]) is int and
       0<=t["event"]<16 and type(t["observed"]) is int and
       0<=t["observed"]<16 for t in ep["events"]),"EIGHT_FULL_CAUSAL_TRANSITIONS")

def features(tc,tl,sc,sl,event):
    values=(tc,tl,sc,sl,event)
    need(all(type(x) is int and 0<=x<16 for x in values),"NIBBLE_STATES")
    bits=sum(v<<(4*i) for i,v in enumerate(values))
    row=(1<<20)|bits
    for index,(a,b) in enumerate(PAIRS):
        if ((bits>>a)&1) and ((bits>>b)&1):
            row|=1<<(21+index)
    return row

def samples(fit):
    need(type(fit) is list and len(fit)==24,
         "ALL_FROZEN_24_FIT_EPISODES_REQUIRED")
    pairs=[]
    for ep in fit:
        validate(ep)
        memory={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            t=e["target"];source=e["source"]
            tc,tl=memory[t];sc,sl=memory[source]
            pairs.append((features(tc,tl,sc,sl,e["event"]),e["observed"]))
            memory[t]=[e["observed"],tc]
    return pairs

def solve_equations(records,bit):
    # Gauss-Jordan on 211 columns, 192 supervised FIT rows; zero
    # unconstrained coefficients. Never selects a model using CHECK.
    rows=[x|(((y>>bit)&1)<<WIDTH) for x,y in records]
    pivots=[];top=0
    for col in range(WIDTH):
        k=next((k for k in range(top,len(rows)) if rows[k]>>col&1),None)
        if k is None:continue
        rows[top],rows[k]=rows[k],rows[top]
        for j in range(len(rows)):
            if j!=top and (rows[j]>>col)&1:rows[j]^=rows[top]
        pivots.append(col);top+=1
        if top==len(rows):break
    if any((r&((1<<WIDTH)-1))==0 and r>>WIDTH&1 for r in rows):
        return None,top
    theta=0
    for i in reversed(range(len(pivots))):
        col=pivots[i]
        if ((rows[i]>>WIDTH)&1)^((rows[i]&theta).bit_count()&1):
            theta|=1<<col
    return theta,top

def fit(fit):
    records=samples(fit)
    weights=[];ranks=[]
    for output_bit in range(4):
        w,k=solve_equations(records,output_bit)
        if w is None:
            return None,{"FIT_consistent":False,"natural_model_fitted":False,
                  "sourcefree_known_degree2_basis":True}
        weights.append(w);ranks.append(k)
    train_errors=sum((predict_from_features(x,weights)^y).bit_count()
                     for x,y in records)
    need(train_errors==0,"FIT_SOURCEFREE_211_MONOMIAL_TRAINING")
    return {"weights":weights},{
      "FIT_consistent":True,"FIT_rows":len(records),"FIT_bit_errors":train_errors,
      "natural_model_fitted":True,"full_public_basis_size":WIDTH,
      "all_cross_entity_second_order_monomials_provided":True,
      "GF2_pivot_ranks":ranks,
      "source_law_unknown_to_learner":True,
      "model_frozen_after_FIT":True}

def predict_from_features(row,masks):
    return sum(((row & mask).bit_count()&1)<<i for i,mask in enumerate(masks))

def predict(model,ep):
    validate(ep)
    need(model is not None and set(model)=={"weights"},"FITTED_MODEL")
    memory={name:list(v) for name,v in ep["initial"].items()}
    outputs=[]
    for e in ep["events"]:
        t=e["target"];s=e["source"]
        tc,tl=memory[t];sc,sl=memory[s]
        n=predict_from_features(features(tc,tl,sc,sl,e["event"]),model["weights"])
        outputs.append(n)
        memory[t]=[n,tc]
    return outputs

def score(model,ep):
    pred=predict(model,ep)
    true=[e["observed"] for e in ep["events"]]
    return {"correct":pred==true,"bit_errors":sum((a^b).bit_count()
                for a,b in zip(pred,true)),"native_event_calls":8}

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,
                        separators=(",",":")).encode()).hexdigest()

if __name__=="__main__":
    raise SystemExit("OUTOFCLASS_SHARED_MODEL_ONLY_NO_SOURCE_BIRTH")

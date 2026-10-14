"""R36 source-balanced, fixed-budget Wingless training candidates.

This is train-only development logic. Scientific-original eligibility requires
a separate source-fidelity audit, independent development review, and sealed
first-use authorization. Do not treat passing unit tests as eligibility.
"""
import hashlib
import json
import math
from wingless_learned import projection, risk_consumer

METHODS=("W36-C1","W36-C2","W36-C3","W36-C4")
DIM=16
EPOCHS=32
SOURCES=3
ROWS_PER_SOURCE=576

def _check(training):
    if len(training)!=SOURCES:
        raise ValueError("R36_SOURCE_COUNT")
    for group in training:
        if len(group)!=ROWS_PER_SOURCE:
            raise ValueError("R36_EXAMPLE_COUNT")
        for feature,label in group:
            if len(feature)!=DIM or label not in (-1,1):
                raise ValueError("R36_FEATURE_OR_LABEL")
            if any(type(x) not in (int,float) or not math.isfinite(x) for x in feature):
                raise ValueError("R36_NONFINITE")

def _gradient(rows,w):
    result=[0.0]*DIM
    for x,y in rows:
        if y*sum(a*b for a,b in zip(w,x))<=0:
            for i in range(DIM):
                result[i]+=y*x[i]/len(rows)
    return result

def _conflict_project(gradients):
    # Deterministic pairwise projection of conflicting source gradients.
    projected=[list(row) for row in gradients]
    for i in range(SOURCES):
        for j in range(SOURCES):
            if i==j:continue
            inner=sum(a*b for a,b in zip(projected[i],gradients[j]))
            if inner<0:
                norm=sum(b*b for b in gradients[j])
                if norm>0:
                    projected[i]=[a-inner*b/norm for a,b in zip(projected[i],gradients[j])]
    return [sum(g[i] for g in projected)/SOURCES for i in range(DIM)]

def train(method,training):
    if method not in METHODS:
        raise ValueError("R36_UNKNOWN_METHOD")
    _check(training)
    if method=="W36-C1":
        w,metadata=projection(training,EPOCHS)
    elif method=="W36-C3":
        w,metadata=risk_consumer(training,_gradient,EPOCHS)
    else:
        w=[0.0]*DIM
        metadata={}
        for _ in range(EPOCHS):
            if method=="W36-C2":
                step=_conflict_project([_gradient(group,w) for group in training])
            else:
                # Fixed 96-slot episodic memory: highest-loss 32 examples per
                # source, recomputed on each development-only training epoch.
                remembered=[]
                for group in training:
                    ranked=sorted(enumerate(group),
                        key=lambda e:(e[1][1]*sum(a*b for a,b in zip(w,e[1][0])),e[0]))
                    remembered.append(tuple(item for _index,item in ranked[:32]))
                step=[sum(_gradient(remembered[s],w)[i] for s in range(SOURCES))/SOURCES
                      for i in range(DIM)]
            w=[w[i]+0.1*step[i] for i in range(DIM)]
            if any(not math.isfinite(a) for a in w):
                raise ValueError("R36_MODEL_NONFINITE")
        if method=="W36-C4":
            metadata={"memory_slots_per_source":32,"source_count":3}
        else:
            metadata={"conflict_projection":"deterministic_pairwise_orthogonal"}
    if len(w)!=DIM or any(not math.isfinite(x) for x in w):
        raise ValueError("R36_MODEL_SHAPE")
    canonical=json.dumps(w,separators=(",",":"),allow_nan=False).encode()
    return {"method":method,"weights":tuple(w),"epochs":EPOCHS,
            "source_training_counts":(ROWS_PER_SOURCE,)*SOURCES,
            "weights_sha256":hashlib.sha256(canonical).hexdigest(),
            "mechanism":metadata}

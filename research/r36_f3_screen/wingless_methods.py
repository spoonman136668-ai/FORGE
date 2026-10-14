"""R36 bounded Wingless train-only candidate learners.

Development primitive only: caller supplies already separated training observations.
No sealed seed reader, dispatch, hidden tuning, or scientific-result claim.
"""
import hashlib
import json
import math

METHODS = ("W36-C1", "W36-C2", "W36-C3", "W36-C4")
DIM = 16
EPOCHS = 32
SOURCES = 3
ROWS_PER_SOURCE = 576

def _check(training):
    if len(training) != SOURCES:
        raise ValueError("R36_SOURCE_COUNT")
    for group in training:
        if len(group) != ROWS_PER_SOURCE:
            raise ValueError("R36_EXAMPLE_COUNT")
        for feature, label in group:
            if len(feature) != DIM or label not in (-1, 1):
                raise ValueError("R36_FEATURE_OR_LABEL")
            if any(type(v) not in (float, int) or not math.isfinite(v) for v in feature):
                raise ValueError("R36_NONFINITE")

def _gradient(rows, weights):
    g = [0.] * DIM
    for feature, label in rows:
        margin = label * sum(w*x for w,x in zip(weights, feature))
        if margin <= 0:
            for i in range(DIM):
                g[i] += label * feature[i] / len(rows)
    return g

def train(method, training):
    """A deterministic bounded 32-epoch 16-weight learner; not a science result."""
    if method not in METHODS:
        raise ValueError("R36_UNKNOWN_METHOD")
    _check(training)
    w = [0.] * DIM
    # Training-only source means and bounded per-source memory.
    means = [[sum(feature[i] for feature, _label in group)/ROWS_PER_SOURCE for i in range(DIM)]
             for group in training]
    for epoch in range(EPOCHS):
        gradients = [_gradient(group,w) for group in training]
        if method == "W36-C1":
            # Soft source-invariance pressure, 16-weight frozen-capacity proxy.
            shared = [sum(g[i] for g in gradients)/SOURCES for i in range(DIM)]
            source_spread = [max(m[i] for m in means)-min(m[i] for m in means) for i in range(DIM)]
            step = [shared[i]/(1+source_spread[i]) for i in range(DIM)]
        elif method == "W36-C2":
            # Conflicting source gradients are projected to zero.
            step = [sum(g[i] for g in gradients)/SOURCES if
                    min(g[i] for g in gradients)*max(g[i] for g in gradients)>=0
                    else 0. for i in range(DIM)]
        elif method == "W36-C3":
            # Two-state bounded risk gate: select harder vs pooled sources.
            losses = [sum(max(0.,1-y*sum(a*b for a,b in zip(w,x))) for x,y in group)/ROWS_PER_SOURCE
                      for group in training]
            hardest = max(range(SOURCES), key=lambda j:(losses[j],-j))
            step = gradients[hardest] if epoch%2 else [sum(g[i] for g in gradients)/SOURCES for i in range(DIM)]
        else:
            # Select the hardest 32 training examples per source deterministically.
            remembered = []
            for group in training:
                scored = sorted(enumerate(group),
                    key=lambda item: (item[1][1] * sum(a*b for a,b in zip(w,item[1][0])), item[0]))
                remembered.append(tuple(row for _index,row in scored[:32]))
            step = [sum(_gradient(remembered[j],w)[i] for j in range(SOURCES))/SOURCES for i in range(DIM)]
        w = [w[i]+0.1*step[i] for i in range(DIM)]
        if any(not math.isfinite(v) for v in w):
            raise ValueError("R36_MODEL_NONFINITE")
    canonical = json.dumps(w,separators=(",",":"),allow_nan=False).encode()
    return {"method":method,"weights":tuple(w),"epochs":EPOCHS,
            "source_training_counts":(ROWS_PER_SOURCE,)*SOURCES,
            "weights_sha256":hashlib.sha256(canonical).hexdigest()}

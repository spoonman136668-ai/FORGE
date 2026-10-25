#!/usr/bin/env python3
"""F124CN source-blind train-only learning: public 40 FIT, 8 CHECK, unseen inputs.

No source-law, source generator, original worlds, family labels, graph/oracle or
private parameters are imported here. Two distinct fitted staged programs:
candidate histogram/residual objective vs independent exact-symbol control.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import sys
import time

SCHEMA = "f124cn.learned-public-staged-v1"
MAGIC = b"F124CN01"
ARMS = ("stage", "conventional_exact", "nearest1", "nearest5", "constant")

def require(ok,reason):
    if not ok:
        raise ValueError("F124CN_DENIED_"+reason)

def nibs(x):
    require(type(x) is int and 0<=x<65536,"PUBLIC_INPUT_UINT16")
    return tuple((x>>(4*j))&15 for j in range(4))

def selector(x,phase):
    a,b,c,context=nibs(x)
    return (b if (context&1)^phase else a),c,context

def forward(x, state):
    phase,alpha,beta,bias=state
    selected,c,context=selector(x,phase)
    return (selected+alpha*c+beta*context+bias)&15

def train_stage(fit):
    """Distinct compositional candidate: infer bias from public residual histogram."""
    best=None
    ties=0
    for phase in (0,1):
        for alpha in range(16):
            for beta in range(16):
                hist=[0]*16
                for x,y in fit:
                    selected,c,context=selector(x,phase)
                    hist[(y-selected-alpha*c-beta*context)&15]+=1
                total=max(hist)
                error=len(fit)-total
                for bias,n in enumerate(hist):
                    if n!=total:
                        continue
                    word=(phase,alpha,beta,bias)
                    if best is None or error<best[0]:
                        best=(error,word)
                        ties=0
                    elif error==best[0]:
                        ties+=1
    return best[1],best[0],ties

def train_exact(fit):
    """Strong separately implemented conventional full-class exact-symbol search."""
    best_error=len(fit)+1
    winner=None
    ties=0
    # Independent direct enumeration of all 8192 possible 13-bit states.
    for p in range(2):
        for a in range(16):
            for b in range(16):
                for bias in range(16):
                    candidate=(p,a,b,bias)
                    errors=0
                    for x,y in fit:
                        if forward(x,candidate)!=y:
                            errors+=1
                            if errors>best_error:
                                break
                    if errors<best_error:
                        best_error=errors
                        winner=candidate
                        ties=0
                    elif errors==best_error:
                        ties+=1
    return winner,best_error,ties

def encode(state):
    require(state is not None and len(state)==4,"NO_SNAPSHOT_STATE")
    p,a,b,bias=state
    require(p in (0,1) and all(type(v) is int and 0<=v<16
            for v in (a,b,bias)),"BAD_MODEL_STATE")
    raw=MAGIC+bytes((p,a,b,bias))
    return raw+hashlib.sha256(raw).digest()

def restore(snapshot):
    require(type(snapshot) is bytes and len(snapshot)==len(MAGIC)+4+32
            and snapshot[:len(MAGIC)]==MAGIC
            and hashlib.sha256(snapshot[:-32]).digest()==snapshot[-32:],
            "SHA256_RESTART_INTEGRITY")
    state=tuple(snapshot[len(MAGIC):-32])
    encode(state)
    return state

def validate(fit,check,dev):
    require(type(fit) is list and len(fit)==40
            and type(check) is list and len(check)==8
            and type(dev) is list and len(dev)==64,"EXACT_PUBLIC_DATA_SPLITS")
    pairs=fit+check
    require(all(type(p) is list and len(p)==2
                and type(p[1]) is int and 0<=p[1]<16
                and type(p[0]) is int and 0<=p[0]<65536
                for p in pairs),"PUBLIC_TWO_COLUMN")
    require(all(type(x) is int and 0<=x<65536 for x in dev),
            "PUBLIC_UNSEEN_INPUTS_ONLY")
    require(len(set(p[0] for p in pairs)|set(dev))==112,
            "DISJOINT_PUBLIC_INPUT_IDENTITIES")

def cyclic_distance(x,y):
    a,b=nibs(x),nibs(y)
    return sum(min(abs(m-n),16-abs(m-n)) for m,n in zip(a,b))

def predict_nearest(fit,x,k):
    pairs=sorted(((cyclic_distance(x,xi),xi,y) for xi,y in fit))
    neighbors=pairs[:k]
    counts=[0]*16
    for _,_,y in neighbors:
        counts[y]+=1
    return min(range(16),key=lambda j:(-counts[j],j))

def get_snapshots(arm,fit,check,dev):
    require(arm in ARMS,"KNOWN_ARM")
    if arm in ("stage","conventional_exact"):
        state,errors,ties=(train_stage(fit) if arm=="stage" else train_exact(fit))
        check_errors=sum(forward(x,state)!=y for x,y in check)
        eligible=errors==0 and ties==0 and check_errors==0
        # Freeze the fully trained selection even on negative and abstain.
        checkpoint=encode(state)
        predicted=([forward(x,state) for x in dev] if eligible
                   else [None]*len(dev))
        train_info={"fit_symbol_errors":errors,"fit_best_ties":ties,
                    "check_errors_veto_only":check_errors,
                    "eligible":eligible,
                    "trained_param_bits":13}
    elif arm=="constant":
        counts=[0]*16
        for _,y in fit:
            counts[y]+=1
        modal=min(range(16),key=lambda y:(-counts[y],y))
        checkpoint=bytes((modal,))
        predicted=[modal]*len(dev)
        train_info={"fit_symbol_errors":sum(y!=modal for _,y in fit),
                    "fit_best_ties":0,"check_errors_veto_only":None,
                    "eligible":True,"trained_param_bits":4}
    else:
        k=1 if arm=="nearest1" else 5
        checkpoint=json.dumps(fit,sort_keys=True,separators=(",",":")).encode()
        predicted=[predict_nearest(fit,x,k) for x in dev]
        train_info={"fit_symbol_errors":0,"fit_best_ties":0,
                    "check_errors_veto_only":None,"eligible":True,
                    "trained_param_bits":None}
    return checkpoint,predicted,train_info

def usage():
    try:
        import resource
        q=resource.getrusage(resource.RUSAGE_SELF)
        return int(q.ru_maxrss*(1024 if sys.platform.startswith("linux") else 1))
    except ImportError:
        return None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--restore",action="store_true")
    args=p.parse_args()
    require(args.arm is not None,"ARM_SPECIFIED")
    q=json.load(sys.stdin)
    if args.restore:
        require(args.arm in ("stage","conventional_exact"),"RESTART_ONLY_FITTED_STAGED")
        state=restore(base64.b64decode(q["checkpoint"],validate=True))
        predictions=[forward(x,state) for x in q["dev"]]
        if not q["was_eligible"]:
            predictions=[None]*len(predictions)
        answer={"predictions":predictions,"cold_restarted":True}
    else:
        fit,check,dev=q["FIT"],q["CHECK"],q["dev"]
        validate(fit,check,dev)
        checkpoint,predictions,train_info=get_snapshots(args.arm,fit,check,dev)
        answer={"arm":args.arm,"predictions":predictions,
                "training":train_info,
                "checkpoint_b64":base64.b64encode(checkpoint).decode(),
                "checkpoint_bytes":len(checkpoint),
                "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
                "cold_restarted":False}
    answer["complete_child_cpu_ns"]=time.process_time_ns()
    answer["peak_process_RSS_bytes"]=usage()
    print(json.dumps(answer,sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    main()

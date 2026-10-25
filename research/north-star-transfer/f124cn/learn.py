"""F124CN source-public FIT-only four-parent compositional feasibility; NOT a native model.
Grammar source-law-informed and outcome-specific. Never imports original source/param.
"""
import hashlib, json
from itertools import combinations
ODD=tuple(range(1,16,2)); COEFF=(0,)+ODD
SCHEMA="forge.itd02.f124cn.development_composition.v1"

def guard(ok,reason):
    if not ok: raise ValueError("F124CN_"+reason)
def nibbles(x):
    guard(type(x) is int and 0<=x<65536,"PUBLIC_X")
    return tuple((x>>(4*i))&15 for i in range(4))
def rows(fit):
    guard(type(fit) in (tuple,list) and len(fit)==40,"FIT_COUNT")
    guard(all(type(x) in (tuple,list) and len(x)==2 and
              type(x[0]) is int and 0<=x[0]<65536 and
              type(x[1]) is int and 0<=x[1]<65536 for x in fit),"FIT_SHAPE")
    guard(len(set(x for x,y in fit))==40,"FIT_DUPLICATE")
    return tuple((nibbles(x),y&15) for x,y in fit)
def predict(model,x):
    gate,cw,tw,bias=model
    a,b,c,t=nibbles(x)
    return ((b if (t^gate)&1 else a)+cw*c+tw*t+bias)&15
def train(fit):
    obs=rows(fit);best=None;scans=0
    # Learn (parity swap, two interaction gains, residual bias) from FIT only.
    for gate in (0,1):
        for cw in ODD:
            for tw in ODD:
                counts=[0]*16
                for (a,b,c,t),y in obs:
                    counts[(y-(b if (t^gate)&1 else a)-cw*c-tw*t)&15]+=1
                    scans+=1
                bias=min(range(16),key=lambda k:(-counts[k],k))
                candidate=(40-counts[bias],gate,cw,tw,bias)
                if best is None or candidate<best:best=candidate
    return tuple(best[1:]),{"fit_errors":best[0],"row_scans":scans}
def conventional_four_parent(fit):
    """INDEPENDENT strong matched-grammar conventional exhaustive FIT search."""
    obs=rows(fit);best=None;scans=0
    for gate in (0,1):
        for cw in ODD:
            for tw in ODD:
                for bias in range(16):
                    error=0
                    for (a,b,c,t),y in obs:
                        estimate=((a if (t&1)==(gate&1) else b)
                                  +(c*cw)+(t*tw)+bias)&15
                        error+=(estimate!=y)
                        scans+=1
                    p=(error,gate,cw,tw,bias)
                    if best is None or p<best:best=p
    return tuple(best[1:]),{"fit_errors":best[0],"row_scans":scans}
def conventional_two_parent(fit):
    """Genuinely FIT-trained best modular sum over any 2 public input nibbles."""
    obs=rows(fit);best=None;scans=0
    for i,j in combinations(range(4),2):
        for gi in COEFF:
            for gj in COEFF:
                hist=[0]*16
                for x,y in obs:
                    hist[(y-gi*x[i]-gj*x[j])&15]+=1;scans+=1
                bias=min(range(16),key=lambda k:(-hist[k],k))
                p=(40-hist[bias],i,j,gi,gj,bias)
                if best is None or p<best:best=p
    return tuple(best[1:]),{"fit_errors":best[0],"row_scans":scans}
def predict_two(model,x):
    i,j,gi,gj,b=model;v=nibbles(x)
    return (gi*v[i]+gj*v[j]+b)&15
def constant(fit):
    counts=[0]*16
    for _,y in rows(fit):counts[y]+=1
    return min(range(16),key=lambda k:(-counts[k],k))
def ablation(fit):
    obs=rows(fit);best=None
    for cw in ODD:
        hist=[0]*16
        for (a,b,c,t),y in obs:hist[(y-a-cw*c)&15]+=1
        bias=min(range(16),key=lambda k:(-hist[k],k))
        p=(40-hist[bias],cw,bias)
        if best is None or p<best:best=p
    return tuple(best[1:])
def predict_ablation(model,x):
    a,b,c,t=nibbles(x)
    return (a+model[0]*c+model[1])&15
def canonical(o):
    return json.dumps(o,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def snapshot(model):
    guard(type(model) is tuple and len(model)==4,"MODEL_LENGTH")
    gate,cw,tw,bias=model
    guard(type(gate) is int and gate in (0,1)
          and type(cw) is int and cw in ODD
          and type(tw) is int and tw in ODD
          and type(bias) is int and 0<=bias<16,"MODEL_DOMAIN")
    body={"schema":SCHEMA,"model":list(model),"source_executed":False,"science_accepted":False}
    return canonical({"body":body,"sha256":hashlib.sha256(canonical(body)).hexdigest()})
def restore(raw):
    guard(type(raw) is bytes and 0<len(raw)<2048,"CHECKPOINT_BYTES")
    def unique(pairs):
        o={}
        for k,v in pairs:
            guard(k not in o,"DUPLICATE_KEY")
            o[k]=v
        return o
    try: env=json.loads(raw.decode("ascii"),object_pairs_hook=unique)
    except (UnicodeError,ValueError,TypeError) as ex:
        raise ValueError("F124CN_INVALID_JSON") from ex
    guard(type(env) is dict and set(env)=={"body","sha256"} and raw==canonical(env),
          "NONCANONICAL_CHECKPOINT")
    body=env["body"]
    guard(type(body) is dict and set(body)=={"schema","model","source_executed","science_accepted"}
          and body["schema"]==SCHEMA
          and body["source_executed"] is False
          and body["science_accepted"] is False,"CHECKPOINT_AUTHORITY")
    guard(env["sha256"]==hashlib.sha256(canonical(body)).hexdigest(),"CHECKPOINT_HASH")
    model=body["model"]
    guard(type(model) is list and len(model)==4 and
          all(type(z) is int for z in model),"CHECKPOINT_MODEL")
    snapshot(tuple(model))
    return tuple(model)

"""F124-AE: frozen AD anchor transfer and unchanged one-state scorer.

The only change to original predictors for 13-15 hop observations is the
source-blind structural admissibility validator in cloned function globals.
Weights, sorting, inference and 7+9 / 1-state capacity unchanged. Scorer
reference path and labels cannot be accessed by these functions.
"""
from __future__ import annotations
import math,types
from types import SimpleNamespace
import f124ae_frozen_source as s
import f124ab_soft_hamming_pareto as ab
import f124aa_packed_transfer as aa
import f124z_sparse_continuity as z
import f124q_independent_binding as q

def frozen_ab_soft(g,base,delta):
    proxy=SimpleNamespace(parent=SimpleNamespace(validate_extended=s.validate_15),
                          need=s.need)
    env=dict(ab.soft_continuity.__globals__)
    env["fresh"]=proxy
    fn=types.FunctionType(ab.soft_continuity.__code__,env,
                          ab.soft_continuity.__name__,
                          ab.soft_continuity.__defaults__)
    return fn(g,list(base),list(delta),.25)

def frozen_t(g,base,delta):
    env=dict(q.yggdrasil_lookahead.__globals__)
    env["source"]=SimpleNamespace(validate_public=s.validate_15)
    fn=types.FunctionType(q.yggdrasil_lookahead.__code__,env,
                          q.yggdrasil_lookahead.__name__,
                          q.yggdrasil_lookahead.__defaults__)
    return fn(g,list(base),list(delta))

def frozen_z(g,base,delta):
    env=dict(z.continuity_head.__globals__)
    env["source"]=SimpleNamespace(validate_public=s.validate_15)
    fn=types.FunctionType(z.continuity_head.__code__,env,
                          z.continuity_head.__name__,
                          z.continuity_head.__defaults__)
    raw,ratio,work=fn(g,list(base),list(delta))
    return z.corrected_logit(raw,ratio,.5),raw,ratio,work

def frozen_packed(g,base,delta):
    env=dict(aa.packed_one_state.__globals__)
    env["experiment"]=SimpleNamespace(validate_extended=s.validate_15,need=s.need)
    fn=types.FunctionType(aa.packed_one_state.__code__,env,
                          aa.packed_one_state.__name__,
                          aa.packed_one_state.__defaults__)
    return fn(g,list(base),list(delta))

def frozen_three(g,base,delta):
    env=dict(ab.packed_frontier.__globals__)
    env["fresh"]=SimpleNamespace(parent=SimpleNamespace(
                         validate_extended=s.validate_15),need=s.need)
    fn=types.FunctionType(ab.packed_frontier.__code__,env,
                          ab.packed_frontier.__name__,
                          ab.packed_frontier.__defaults__)
    return fn(g,list(base),list(delta),3)

def anchored_score(g,base,delta,anchor=10):
    s.need(anchor in (10,16),"UNCHANGED_AD_READOUT")
    raw,ratio,work=frozen_ab_soft(g,base,delta)
    depth=len(g["roles"])
    best=(raw/4.+base[6])*(depth-1)
    result=ab.logit(raw,ratio,.25) if anchor==16 else (
          4.*(best/min(depth-1,anchor)-base[6])-.25*(1.-ratio))
    s.need(math.isfinite(result),"LONG_CHAIN_SCORE_FINITE")
    return result,raw,ratio,work

def wing_threshold(g,base,delta,bias):
    s.need(bias in s.BIAS,"FROZEN_FIT_BIAS")
    raw,work=frozen_packed(g,base,delta)
    # No changed states, weights, or work counters.
    result=raw if bias==0 else raw+bias
    s.need(math.isfinite(result),"FINITE_PACKED_LOGIT")
    return result,raw,work

def fit_threshold(cases,base,delta):
    s.need(len(cases)==48,"COMPLETE_NEW_FIT_ONLY")
    logits=[(frozen_packed(p,base,delta)[0],
             frozen_packed(n,base,delta)[0])
            for _,_,_,p,n in cases]
    grid=[{"bias":b,"paired":sum(p+b>=0 and n+b<0 for p,n in logits)}
          for b in s.BIAS]
    selected=sorted(grid,key=lambda x:(-x["paired"],abs(x["bias"]),x["bias"]))[0]
    return selected,grid

"""F124-CM equally informed independent nonlinear recurrent comparator.

Own 25-column learned quadratic family; identical 40 FIT/8 CHECK,
100 coefficient bits plus eight online history bits, no candidate import.
Comparable CPU/RSS and native work are NOT established until independently
observed on unseen original cases. Engineering candidate only.
"""
from __future__ import annotations
import hashlib
import json
from typing import NamedTuple

FIT_COUNT=40
CHECK_COUNT=8
FEATURE_BITS=25
COEFFICIENT_BITS=100
HISTORY_BITS=8

class State(NamedTuple):
    current: int
    lagged: int

class Model(NamedTuple):
    weights: tuple[int,int,int,int]

def req(ok, reason):
    if not ok:raise ValueError('F124CM_CONTROL_'+reason)

def nib(v):return type(v) is int and 0<=v<16

def basis(event,current,lagged):
    req(all(nib(v) for v in (event,current,lagged)),'STATE_WIDTH')
    e=[(event>>i)&1 for i in range(4)]
    s=[(current>>i)&1 for i in range(4)]
    h=[(lagged>>i)&1 for i in range(4)]
    bits=[1]+e+s+h
    bits += [e[i]&s[(i+1)%4] for i in range(4)]
    bits += [e[i]&h[(i+2)%4] for i in range(4)]
    bits += [s[i]&h[(i+3)%4] for i in range(4)]
    req(len(bits)==FEATURE_BITS,'BASIS_25')
    return sum(v<<i for i,v in enumerate(bits))

def step(model,event,state):
    req(isinstance(model,Model) and len(model.weights)==4 and all(type(v) is int and 0<=v<1<<FEATURE_BITS for v in model.weights),'PARAMETERS')
    req(isinstance(state,State) and all(nib(v) for v in state),'HISTORY')
    x=basis(event,*state)
    return State(sum(((v&x).bit_count()%2)<<i for i,v in enumerate(model.weights)),state.current)

def train(fit,check):
    req(type(fit) in (list,tuple) and len(fit)==FIT_COUNT and type(check) in (list,tuple) and len(check)==CHECK_COUNT,'COUNTS')
    rows=list(fit)+list(check)
    req(all(type(r) in (list,tuple) and len(r)==4 and all(nib(v) for v in r) for r in rows),'TRANSITIONS')
    req(len({tuple(r[:3]) for r in rows})==48,'UNIQUE_INPUTS')
    # Independently implemented GF(2) elimination on a rotated nonlinear basis.
    pivots={}
    contradictory=False
    for e,s,h,target in fit:
        lhs=basis(e,s,h)
        rhs=target
        while lhs:
            p=lhs.bit_length()-1
            if p in pivots:
                row,out=pivots[p]
                lhs^=row;rhs^=out
            else:
                pivots[p]=(lhs,rhs)
                break
        if lhs==0 and rhs:
            contradictory=True
    rank=len(pivots)
    coeff=[0]*4
    if not contradictory and rank==FEATURE_BITS:
        for bit in sorted(pivots):
            x,y=pivots[bit]
            for o in range(4):
                out=((y>>o)&1)^((coeff[o]&(x^(1<<bit))).bit_count()%2)
                coeff[o]|=out<<bit
    candidate=Model(tuple(coeff)) if rank==FEATURE_BITS and not contradictory else None
    fit_errors=sum(step(candidate,r[0],State(r[1],r[2])).current!=r[3] for r in fit) if candidate else None
    check_errors=sum(step(candidate,r[0],State(r[1],r[2])).current!=r[3] for r in check) if candidate else None
    admitted=candidate is not None and fit_errors==0 and check_errors==0
    return (candidate if admitted else None),{
      'schema':'mass.f124cm.independently-trained-relational-control.v1',
      'FIT_sha256':hashlib.sha256(json.dumps(fit,separators=(',',':')).encode()).hexdigest(),
      'FIT_only_training':True,'CHECK_veto_only':True,
      'FIT_rows':40,'CHECK_rows':8,'rank':rank,'contradictory_FIT':contradictory,
      'FIT_errors':fit_errors,'CHECK_errors':check_errors,
      'coefficient_bits':COEFFICIENT_BITS,'history_bits':HISTORY_BITS,
      'trained_nonlinear_recurrence':True,'candidate_training_imported':False,
      'original_E2F2_source_reused':False,'protected_source_used':False,
      'science_accepted':False,'admitted_public_only':admitted,
    }

if __name__=='__main__':
    raise SystemExit('CONTROL_ENGINEERING_ONLY')

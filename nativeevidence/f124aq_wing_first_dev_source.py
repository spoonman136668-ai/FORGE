"""F124-AQ source-only Wingless DEV adapter; NEVER imported by candidates.

Separate first-use module prevents the TRAIN source API from generating DEV.
Only the exact frozen Wingless cohort is constructible. Yggdrasil remains
inaccessible after its prospective TRAIN negative.
"""
from __future__ import annotations
import types
from collections import Counter
import f124aq_train_source as frozen
import f124ao_frozen_source as parent

def build(seed,vector):
    frozen.need(type(seed) is int and
                seed in frozen.COHORTS["Wingless"]["DEV"] and
                tuple(vector) in frozen.VECTORS,
                "FIRST_DEV_WINGLESS_ONLY_NEW_COHORT")
    env=dict(parent.build.__globals__)
    env.update(COHORTS=frozen.COHORTS,OPERATORS=frozen.OPERATORS,
               relation=frozen.relation,plain=frozen.plain)
    fn=types.FunctionType(parent.build.__code__,env,
                          parent.build.__name__,parent.build.__defaults__)
    family,operator,nonce,p,n,selected=fn(
        "Wingless",seed,vector,"DEV")
    frozen.need(p["demos"]==n["demos"] and
        sum(frozen.relation(d["input_bits"],operator)!=d["output_bits"]
            for d in p["demos"])==3,
        "SYMMETRIC_NEW_SOURCE_ONLY_DEV")
    return family,operator,nonce,p,n,selected

def pairs():
    frozen.frozen()
    rows=[]
    for vec in frozen.VECTORS:
        for seed in frozen.COHORTS["Wingless"]["DEV"]:
            fam,op,nonce,p,n,chosen=build(seed,vec)
            rows.append((chosen,tuple(vec),fam,op,nonce,p,n))
    frozen.need(len(rows)==48 and
        Counter(x[2] for x in rows)==Counter({fam:12 for fam in frozen.FAMILIES}),
        "DEV_FOUR_FAMILIES_ONCE")
    return rows

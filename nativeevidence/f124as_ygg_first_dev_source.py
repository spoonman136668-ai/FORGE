"""Separate prospective F124-AS Yggdrasil DEV first-use source ONLY.

Ygg first-use is initiated solely by the admitted workflow. Wingless DEV has
NO construction path here. No source-only operator identity reaches models.
"""
from __future__ import annotations
from collections import Counter
import types
import f124as_train_source as frozen
import f124ao_frozen_source as birth

def need(ok,label):frozen.need(ok,"YGG_FIRST_USE_"+label)

def build(seed,vector):
    need(type(seed) is int and
         seed in frozen.COHORTS["Yggdrasil"]["DEV"] and
         tuple(vector) in frozen.VECTORS,
         "ONLY_PRECOMMITTED_YGG_DEV")
    env=dict(birth.build.__globals__)
    env.update(COHORTS=frozen.COHORTS,OPERATORS=frozen.OPERATORS,
               relation=frozen.relation,plain=frozen.plain)
    fn=types.FunctionType(birth.build.__code__,env,
                          birth.build.__name__,birth.build.__defaults__)
    family,op,nonce,p,n,selected=fn("Yggdrasil",seed,vector,"DEV")
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(frozen.relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,
         "PAIRED_PUBLIC_NOISE_BOUND")
    return family,op,nonce,p,n,selected

def pairs():
    frozen.frozen()
    rows=[]
    for vec in frozen.VECTORS:
        for seed in frozen.COHORTS["Yggdrasil"]["DEV"]:
            family,op,nonce,p,n,selected=build(seed,vec)
            rows.append((selected,tuple(vec),family,op,nonce,p,n))
    need(len(rows)==48 and
         Counter(x[2] for x in rows)==
         Counter({family:12 for family in frozen.FAMILIES}),
         "FROZEN_FIRST_DEV_COMPLETE_DENOMINATOR")
    return rows

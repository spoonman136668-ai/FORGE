"""F124-AH distinct public causal semantics, prospectively frozen.

The parent AG generator and admissibility rules run before either label's
symmetric public-rule transformation. An unchanged key-matching model will
not see the model-free evaluator's inverse transform. The true rule is
disclosed in all public role strings, not in a hidden oracle or label.
"""
from __future__ import annotations
from collections import Counter
import copy,json,types
from pathlib import Path
import f124ag_frozen_source as parent
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ah-frozen-alternate-causal-rules.json"
FREEZE_BLOB="3076167057b20eac050b9b0514665614381a6d06"
PARENT_BLOB="60d0c0e58c55054ef50ea78b439afdddc8e43ada"
COHORTS={"Wingless":{"FIT":range(2080000,2080024),"DEV":range(2080100,2080124)},
         "Yggdrasil":{"FIT":range(2090000,2090024),"DEV":range(2090100,2090124)}}
VECTORS=parent.VECTORS
FAMILIES=("xor16_permuted","rotate4_dense_13_15",
          "xor16_extended_13_15","rotate4_tolerant")
OLD_FAMILIES=parent.FAMILIES
RULES=("xor16","rotate4")

def need(ok,label):
    q.need(ok,"F124AH_"+label)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(parent.__file__)==PARENT_BLOB,
         "FREEZE_OR_AUTHENTIC_AG_SOURCE_IDENTITY")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]==
         "forge.research.f124ah.frozen-alternate-public-relation-and-packed-survival.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]==
             "8a5687eba4a35aa46528b61f1050306ee628b4fe"
         and p["sources"]["families"]==list(FAMILIES)
         and p["sources"]["Wingless"]==
             {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
         and p["sources"]["Yggdrasil"]==
             {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
         and p["Yggdrasil"]["confirmation"] is False,
         "FROZEN_SOURCE_PROTOCOL")
    need(all(v is False for v in p["authority"].values())
         and p["Wingless"]["memory"]["maximum_nodes"]==64,
         "NO_UNAUTHORIZED_SCIENTIFIC_ACTIVATION")
    return p

def transform(bits,rule,inverse=False):
    need(type(bits) is list and len(bits)==16
         and all(type(x) is int and x in (0,1) for x in bits),
         "PUBLIC_16_BIT_SOURCE")
    if rule=="xor16":return [1-x for x in bits]
    need(rule=="rotate4","PUBLIC_RELATION_DEFINED")
    return bits[-4:]+bits[:-4] if inverse else bits[4:]+bits[:4]

def rule_for(family):
    need(family in FAMILIES,"FROZEN_RULE_FAMILY")
    return "xor16" if family.startswith("xor16") else "rotate4"

def restore(g,family):
    """Evaluator only: undo the public-role and public-source translation."""
    rule=rule_for(family);prefix="rel_"+rule+":"
    out=copy.deepcopy(g)
    def untag(token):
        need(token.startswith(prefix),"DECLARED_PUBLIC_CAUSAL_RULE_MISSING")
        return token[len(prefix):]
    out["roles"]=[untag(r) for r in out["roles"]]
    for e in out["edges"]:
        e["role"]=untag(e["role"])
        e["src_bits"]=transform(e["src_bits"],rule,inverse=True)
    return out

def routes(g,family):
    """Evaluator-only new rule; never imported in model inference."""
    original=restore(g,family)
    return parent.prior.parent.routes15(
       original,relaxed=family=="rotate4_tolerant")

def build(lane,requested,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(requested) is int and requested in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,
         "INDEPENDENT_PUBLIC_COHORT")
    env=dict(parent.build.__globals__)
    env["COHORTS"]=COHORTS
    original=types.FunctionType(parent.build.__code__,env,
                                 parent.build.__name__,parent.build.__defaults__)
    old_fam,p,n,selected_seed=original(lane,requested,vector,phase)
    index=(requested-COHORTS[lane][phase].start)%4
    family=FAMILIES[index]
    rule=rule_for(family)
    need(old_fam==OLD_FAMILIES[index],"ORIGINAL_PARENT_SOURCE_FAMILY")
    prefix="rel_"+rule+":"
    for g in (p,n):
        g["roles"]=[prefix+r for r in g["roles"]]
        for e in g["edges"]:
            e["role"]=prefix+e["role"]
            e["src_bits"]=transform(e["src_bits"],rule)
    need(routes(p,family)==1 and routes(n,family)==0,
         "CHANGED_PUBLIC_RELATION_ORIGINAL_REFERENCE")
    need(parent.prior.parent.routes15(p,relaxed=True)==0
         and parent.prior.parent.routes15(n,relaxed=True)==0,
         "NO_OLD_EXACT_OR_ONE_BIT_SHORTCUT")
    need(parent.prior.parent.routes15(p,role_only=True)==
         parent.prior.parent.routes15(n,role_only=True),
         "SAME_ROLE_ONLY_NEGATIVE_CONTROL")
    need(all(p[k]==n[k] for k in ("start","target","roles")),
         "NO_PUBLIC_QUERY_LEAK")
    def inventory(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[field]) for e in g["edges"]
                        for field in ("src_bits","dst_bits")))
    need(inventory(p)==inventory(n),"PAIRED_PUBLIC_INVENTORY_MATCH")
    return family,p,n,selected_seed

def pairs(lane,phase):
    out=[]
    for vec in VECTORS:
        for seed in COHORTS[lane][phase]:
            fam,p,n,selected=build(lane,seed,vec,phase)
            out.append((selected,tuple(vec),fam,p,n))
    need(len(out)==48 and all(sum(x[2]==f for x in out)==12
                              for f in FAMILIES)
         and (phase!="FIT" or
              all(c[0]<COHORTS[lane]["DEV"].start for c in out)),
         "DISJOINT_BALANCED_PUBLIC_LABEL_SOURCE")
    return out

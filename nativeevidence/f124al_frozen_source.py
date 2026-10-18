"""F124-AL new source-only out-of-class nonlinear rules with noisy demos.

Original F124-AK birth + first-admitted original causal pair unchanged.
The new public graph is a prospective transformation plus independent
paired support examples. True operator and inverse unavailable to model.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import copy,json,random,types
import f124ak_frozen_source as prior
import f124w_hop_trace_indexed as git
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124al-frozen-noisy-relations-and-packed-fp.json"
FREEZE_BLOB="952b2dea33837c3176112861ecf612c9f488dc35"
PRIOR_SOURCE_BLOB="b7bafd3a5cb9b7247cfe2713bb601aceb259f891"
COHORTS={"Wingless":{"TRAIN":range(2480000,2480024),"DEV":range(2480100,2480124)},
         "Yggdrasil":{"TRAIN":range(2490000,2490024),"DEV":range(2490100,2490124)}}
FAMILIES=prior.FAMILIES
VECTORS=prior.VECTORS
OPERATORS={"TRAIN":("mul_0003","tri_or_1_2","mul_0005","tri_or_1_3"),
           "DEV":("tri_or_2_4","mul_0007","tri_or_1_4","mul_000B")}
SUPPORT=(4,8,12,24)
CAP=(0.,.05,.1,.2,.4,1.)

def need(ok,label):q.need(ok,"F124AL_"+label)
def frozen():
    prior.frozen()
    need(git.blob(FREEZE)==FREEZE_BLOB and
         git.blob(prior.__file__)==PRIOR_SOURCE_BLOB,
         "FROZEN_NEW_SCIENTIFIC_IDENTITY")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124al.frozen-noisy-outofclass-relations-and-packed-fp.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_exact_head"]=="d0d4d4d0ebc3cf4d5ad645bf8cb267fb2c3c7d21"
         and p["sources"]["Wingless"]==
             {x:[v.start,v.stop-1] for x,v in COHORTS["Wingless"].items()}
         and p["sources"]["Yggdrasil"]==
             {x:[v.start,v.stop-1] for x,v in COHORTS["Yggdrasil"].items()}
         and p["sources"]["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and p["sources"]["DEV_operators"]==list(OPERATORS["DEV"])
         and p["Yggdrasil"]["grid_support"]==list(SUPPORT)
         and p["Wingless"]["grid_cap"]==list(CAP)
         and all(v is False for v in p["authority"].values()),
         "SOURCE_FREEZE_PRE_IMPLEMENTATION")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "NEW_UNSEEN_SEMANTIC_FAMILIES")
    return p

def bits(k):return [(k>>i)&1 for i in range(16)]
def integer(v):return sum(b<<i for i,b in enumerate(v))
def relation(data,operator,inverse=False):
    need(operator in OPERATORS["TRAIN"]+OPERATORS["DEV"],
         "DECLARED_ONLY_IN_SOURCE_OPERATOR")
    if operator.startswith("mul_"):
        a=int(operator[4:],16)
        need(a%2==1 and 1<a<65536,"ODD_INVERTIBLE_MULTIPLIER")
        return bits((integer(data)*(pow(a,-1,65536) if inverse else a))&65535)
    _,_,p,qq=operator.split("_")
    p,qq=int(p),int(qq)
    need(1<=p<qq<=5,"REVERSIBLE_TRIANGULAR_OR")
    if not inverse:
        return [bit^(int(data[i-p] or data[i-qq]) if i>=qq else 0)
                for i,bit in enumerate(data)]
    recovered=[]
    for i,bit in enumerate(data):
        term=int(recovered[i-p] or recovered[i-qq]) if i>=qq else 0
        recovered.append(bit^term)
    return recovered

def plain(g,operator,tag):
    marker="rel_task_"+tag+":"
    out=copy.deepcopy(g);out.pop("demos")
    need(all(x.startswith(marker) for x in out["roles"]) and
         all(e["role"].startswith(marker) for e in out["edges"]),
         "SAME_OPAQUE_PUBLIC_RULE")
    out["roles"]=[x[len(marker):] for x in out["roles"]]
    for e in out["edges"]:
        e["role"]=e["role"][len(marker):]
        e["src_bits"]=relation(e["src_bits"],operator,inverse=True)
    return out

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("TRAIN","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,"NEW_SOURCE_ONLY")
    env=dict(prior.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,relation=relation,plain=plain)
    original=types.FunctionType(prior.build.__code__,env,
                                prior.build.__name__,prior.build.__defaults__)
    family,op,tag,pos,neg,selected=original(lane,seed,vector,phase)
    need(family==FAMILIES[(seed-COHORTS[lane][phase].start)%4],
         "ORIGINAL_CAUSAL_STRUCTURE_COHORT")
    # Independent support corruption is EXACTLY symmetric across paired
    # classes. First vector is ambiguous (duplicate first demo) and noisy
    # (single output-bit flip in the fourth demo); second vector is clean.
    if tuple(vector)==tuple(VECTORS[0]):
        for g in (pos,neg):
            g["demos"][1]=copy.deepcopy(g["demos"][0])
            g["demos"][3]["output_bits"][5]^=1
    need(pos["demos"]==neg["demos"] and len(pos["demos"])==24,
         "CLASS_INDEPENDENT_PUBLIC_NOISE")
    relaxed=family=="rotate4_tolerant"
    need(prior.parent.original.parent.prior.parent.routes15(
           plain(pos,op,tag),relaxed=relaxed)==1 and
         prior.parent.original.parent.prior.parent.routes15(
           plain(neg,op,tag),relaxed=relaxed)==0,
         "NO_NEW_SOURCE_LABEL_DRIFT")
    need(prior.parent.original.parent.prior.parent.routes15(
           {k:pos[k] for k in ("start","target","roles","edges")},
           relaxed=True)==0,"OLD_RAW_EQUALITY_SHORTCUT_ABSENT")
    def census(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[f]) for e in g["edges"]
                        for f in ("src_bits","dst_bits")))
    need(census(pos)==census(neg) and
         all(pos[k]==neg[k] for k in ("start","target","roles","demos")),
         "NEGATIVE_TOPOLOGY_AND_TOKEN_PARITY")
    return family,op,tag,pos,neg,selected

def pairs(lane,phase):
    out=[]
    for vector in VECTORS:
        for seed in COHORTS[lane][phase]:
            fam,op,tag,p,n,s=build(lane,seed,vector,phase)
            out.append((s,tuple(vector),fam,op,tag,p,n))
    need(len(out)==48 and
         all(sum(c[2]==family for c in out)==12 for family in FAMILIES)
         and (phase!="TRAIN" or
              all(x[0]<COHORTS[lane]["DEV"].start for x in out)),
         "INDEPENDENT_FRESH_COHORT_COUNT")
    return out

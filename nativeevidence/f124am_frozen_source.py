"""F124-AM prospectively frozen new dense-affine and Feistel sources.

Only evaluator/source code imports this module. Models receive opaque task
nonces and independent noisy public input/output examples, not truth names.
Birth of each graph uses unchanged historical AL first-admitted pair logic,
rebound only to new cohorts/operators via a source-only wrapper.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import copy,hashlib,json,types
import f124al_frozen_source as old
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124am-frozen-affine-feistel-noisy.json"
FREEZE_BLOB="64481a7c1077e8ae8aafee723ca63d3f33f298a1"
PARENT_SOURCE_BLOB="092d3990254acd258af76e627190e62357689a40"
COHORTS={"Wingless":{"TRAIN":range(2580000,2580024),"DEV":range(2580100,2580124)},
         "Yggdrasil":{"TRAIN":range(2590000,2590024),"DEV":range(2590100,2590124)}}
FAMILIES=old.FAMILIES
VECTORS=old.VECTORS
OPERATORS={"TRAIN":("affine_AX17","feistel_K13","affine_AX29","feistel_K27"),
           "DEV":("affine_AX47","feistel_K31","affine_AX59","feistel_K43")}
SUPPORT=(17,20,24)
GAMMAS=(0.,.1,.25,.5,1.)
MASK=65535

def need(value,key):q.need(value,"F124AM_"+key)

def frozen():
    old.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(old.__file__)==PARENT_SOURCE_BLOB,
         "AUTHENTIC_PREIMPLEMENTATION_SOURCE_IDENTITY")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124am.frozen-affine-feistel-corruption-and-one-packed-competition.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_head"]=="efe2b9f26a79e5cf2872c40f14fadedb3dfd8427"
         and p["sources"]["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and p["sources"]["DEV_operators"]==list(OPERATORS["DEV"])
         and p["Yggdrasil"]["support_grid"]==list(SUPPORT)
         and p["Wingless"]["gamma_grid"]==list(GAMMAS)
         and p["sources"]["Wingless"]==
             {t:[r.start,r.stop-1] for t,r in COHORTS["Wingless"].items()}
         and p["sources"]["Yggdrasil"]==
             {t:[r.start,r.stop-1] for t,r in COHORTS["Yggdrasil"].items()}
         and all(v is False for v in p["authority"].values()),
         "FROZEN_COUPLING_AND_FIRST_USE")
    return p

def to_int(v):return sum(x<<i for i,x in enumerate(v))
def to_bits(v):return [(v>>i)&1 for i in range(16)]

def mix(v,d,shift):
    if d=="l":return (v ^ ((v<<shift)&MASK))&MASK
    return (v ^ (v>>shift))&MASK

def unmix(v,d,shift):
    s=shift
    while s<16:
        v=mix(v,d,s)
        s*=2
    return v

def affine_params(operator):
    h=hashlib.sha256(("F124AM/affine/"+operator).encode()).digest()
    shifts=(3+h[0]%4,3+h[1]%4,5+h[2]%4,2+h[3]%4)
    actions=(("l",shifts[0]),("r",shifts[1]),
             ("l",shifts[2]),("r",shifts[3]))
    offset=int.from_bytes(h[4:6],"little")
    return actions,offset

def feistel_f(value,key,round_no):
    k=(key+round_no*29)&255
    return ((value*k)^((value<<3)&255)^(value>>2)^((value*value)&255)^k)&255

def relation(inp,operator,inverse=False):
    need(operator in OPERATORS["TRAIN"]+OPERATORS["DEV"],
         "SOURCE_ONLY_OPERATOR_CATALOG")
    v=to_int(inp)
    if operator.startswith("affine_"):
        actions,offset=affine_params(operator)
        if inverse:
            v^=offset
            for direction,shift in reversed(actions):v=unmix(v,direction,shift)
        else:
            for direction,shift in actions:v=mix(v,direction,shift)
            v^=offset
    else:
        need(operator.startswith("feistel_"),"SPECIFIED_FEISTEL_OR_AFFINE")
        key=hashlib.sha256(("F124AM/feistel/"+operator).encode()).digest()[0]|1
        left,right=(v>>8)&255,v&255
        if inverse:
            for i in (1,0):
                left,right=(right^feistel_f(left,key,i)),left
        else:
            for i in (0,1):
                left,right=right,left^feistel_f(right,key,i)
        v=((left&255)<<8)|(right&255)
    return to_bits(v&MASK)

def plain(g,operator,nonce):
    marker="rel_task_"+nonce+":"
    copied=copy.deepcopy(g);copied.pop("demos")
    need(all(role.startswith(marker) for role in copied["roles"]) and
         all(e["role"].startswith(marker) for e in copied["edges"]),
         "PUBLIC_SOURCE_LABEL_FREE")
    copied["roles"]=[x[len(marker):] for x in copied["roles"]]
    for e in copied["edges"]:
        e["role"]=e["role"][len(marker):]
        e["src_bits"]=relation(e["src_bits"],operator,True)
    return copied

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("TRAIN","DEV") and
         type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,
         "FRESH_SOURCE_DISJOINT")
    env=dict(old.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(old.build.__code__,env,
                          old.build.__name__,old.build.__defaults__)
    family,operator,nonce,p,n,selected=fn(lane,seed,vector,phase)
    # AL original first-vector demo3 already contains one corrupt output
    # and demo1 is duplicate of demo0. Add one more first-vector corruption;
    # clean second vector receives two corruption sites. Thus ALL cases
    # have exactly two one-bit corruptions, matched between labels.
    if tuple(vector)==tuple(VECTORS[0]):
        for graph in (p,n):
            graph["demos"][2]=copy.deepcopy(graph["demos"][0])
    else:
        for graph in (p,n):
            graph["demos"][3]["output_bits"][5]^=1
    for graph in (p,n):
        graph["demos"][7]["output_bits"][9]^=1
    need(p["demos"]==n["demos"],"PAIRED_CORRUPTION_SYMMETRIC")
    count_corrupted=sum(relation(d["input_bits"],operator)!=d["output_bits"]
                        for d in p["demos"])
    need(count_corrupted==2,"EXACT_TWO_PUBLIC_CORRUPTED_DEMONSTRATIONS")
    relaxed=family=="rotate4_tolerant"
    oracle=old.prior.parent.original.parent.prior.parent.routes15
    need(oracle(plain(p,operator,nonce),relaxed=relaxed)==1 and
         oracle(plain(n,operator,nonce),relaxed=relaxed)==0,
         "EVALUATOR_TRUE_REFERENCE_UNCHANGED")
    raw={k:p[k] for k in ("start","target","roles","edges")}
    need(oracle(raw,relaxed=True)==0,
         "NO_OLD_RAW_EQUALITY_SHORTCUT")
    def signature(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(signature(p)==signature(n) and
         all(p[k]==n[k] for k in ("start","target","roles","demos")),
         "PAIRED_LABEL_BLIND_SOURCE_INVENTORY")
    return family,operator,nonce,p,n,selected

def pairs(lane,phase):
    res=[]
    for vec in VECTORS:
        for seed in COHORTS[lane][phase]:
            family,operator,nonce,p,n,chosen=build(lane,seed,vec,phase)
            res.append((chosen,tuple(vec),family,operator,nonce,p,n))
    need(len(res)==48 and
         all(sum(x[2]==fam for x in res)==12 for fam in FAMILIES)
         and (phase!="TRAIN" or
              all(x[0]<COHORTS[lane]["DEV"].start for x in res)),
         "FROZEN_NEW_FAMILY_DENOMINATORS")
    return res

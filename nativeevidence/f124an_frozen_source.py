"""F124-AN immutable new-source adapter, source oracle NEVER model input."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import copy,json,types
import f124am_frozen_source as am
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124an-frozen-robust-affine-wing-isolation.json"
FREEZE_BLOB="d3ad91612d2aefc4be13f94515badb6d2b4347cb"
PARENT_SOURCE_BLOB="c75fd5ec5a60618a1ea9abb85c60a3666514ab85"
COHORTS={"Wingless":{"TRAIN":range(2680000,2680024),"DEV":range(2680100,2680124)},
         "Yggdrasil":{"TRAIN":range(2690000,2690024),"DEV":range(2690100,2690124)}}
OPERATORS={"TRAIN":("affine_AX61","feistel_K53","affine_AX73","feistel_K67"),
           "DEV":("affine_AX83","feistel_K79","affine_AX97","feistel_K89")}
FAMILIES=am.FAMILIES
VECTORS=am.VECTORS
def need(value,tag):q.need(value,"F124AN_"+tag)
def frozen():
    am.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(am.__file__)==PARENT_SOURCE_BLOB,
         "IMMUTABLE_PREIMPLEMENTATION_FINGERPRINT")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]==
        "forge.research.f124an.frozen-noisy-operator-confidence-and-one-packed-isolation.v1"
        and p["status"]=="PREIMPLEMENTATION_FROZEN"
        and p["lineage"]["parent_head"]=="c0926513bfa06b2348043bfc8b78116f10445fc7"
        and p["source"]["TRAIN_operators"]==list(OPERATORS["TRAIN"])
        and p["source"]["DEV_operators"]==list(OPERATORS["DEV"])
        and p["source"]["Wingless"]==
            {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
        and p["source"]["Yggdrasil"]==
            {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
        and p["source"]["corrupted_output_bits_per_task"]==3
        and all(v is False for v in p["authority"].values()),
        "SOURCE_BIRTH_DISJOINT_NO_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"]),
         "UNSEEN_OPERATOR_SEED")
    return p

# Clone ORIGINAL unchanged relation/restore bytecode with just the
# PROSPECTIVELY FROZEN catalogue rebound in source-only globals.
RENV=dict(am.relation.__globals__,OPERATORS=OPERATORS)
RELATION=types.FunctionType(am.relation.__code__,RENV,
                           am.relation.__name__,am.relation.__defaults__)
PENV=dict(am.plain.__globals__,relation=RELATION)
PLAIN=types.FunctionType(am.plain.__code__,PENV,
                         am.plain.__name__,am.plain.__defaults__)

def relation(bits,op,inverse=False):
    return RELATION(bits,op,inverse)

def plain(g,op,nonce):
    return PLAIN(g,op,nonce)

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("TRAIN","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,
         "PROSPECTIVE_NEW_COHORT")
    env=dict(am.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(am.build.__code__,env,
                          am.build.__name__,am.build.__defaults__)
    family,op,nonce,p,n,chosen=fn(lane,seed,vector,phase)
    # AM source has exactly two corrupted demonstration outputs.
    # Independently add THIRD bit flip at held-out demonstration #12;
    # on first vector also duplicate an extra example pair.
    for g in (p,n):
        g["demos"][12]["output_bits"][11]^=1
        if tuple(vector)==tuple(VECTORS[0]):
            g["demos"][10]=copy.deepcopy(g["demos"][0])
    need(p["demos"]==n["demos"] and len(p["demos"])==24,
         "SAME_DEMONSTRATIONS_BOTH_LABELS")
    corrupted=sum(relation(d["input_bits"],op)!=d["output_bits"]
                  for d in p["demos"])
    need(corrupted==3,"EXACTLY_THREE_INDEPENDENT_PUBLIC_CORRUPTIONS")
    oracle=am.old.prior.parent.original.parent.prior.parent.routes15
    relaxed=family=="rotate4_tolerant"
    need(oracle(plain(p,op,nonce),relaxed=relaxed)==1
         and oracle(plain(n,op,nonce),relaxed=relaxed)==0,
         "INVERSE_RULE_ORACLE_ONLY_NEW_SOURCE")
    raw={k:p[k] for k in ("start","target","roles","edges")}
    need(oracle(raw,relaxed=True)==0,
         "ORIGINAL_LITERAL_KEY_SHORTCUT_ELIMINATED")
    def census(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(census(p)==census(n) and
         all(p[k]==n[k] for k in ("start","target","roles","demos")),
         "NO_PAIR_LABEL_LEAKAGE")
    return family,op,nonce,p,n,chosen

def pairs(lane,phase):
    rows=[]
    for vec in VECTORS:
        for seed in COHORTS[lane][phase]:
            family,op,nonce,p,n,selected=build(lane,seed,vec,phase)
            rows.append((selected,tuple(vec),family,op,nonce,p,n))
    need(len(rows)==48 and
         all(sum(row[2]==family for row in rows)==12
             for family in FAMILIES)
         and (phase!="TRAIN" or
              all(row[0]<COHORTS[lane]["DEV"].start for row in rows)),
         "PROSPECTIVE_SOURCE_DENOMINATOR")
    return rows

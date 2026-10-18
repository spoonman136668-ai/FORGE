"""F124-AO independently frozen 40-public-support source, source oracle only.

Use original F124-AN first-admitted paired graph source code unchanged except
new seed/operator namespaces. Append 16 new independent clean public supports
to 24 original examples with three corrupted outputs. Do not give relation
names, hidden class, graph keys or oracle to prediction modules.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import copy,hashlib,json,random,types
import f124an_frozen_source as prior
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ao-frozen-redundant-public-and-sequential-packed.json"
FREEZE_BLOB="9f2f938a492eb7a24c8f119d2ed35ec11d46f433"
PARENT_SOURCE_BLOB="0bdb7579050f90c078a5c05acc7faf77d2f9c5d4"
COHORTS={"Wingless":{"TRAIN":range(2780000,2780024),"DEV":range(2780100,2780124)},
         "Yggdrasil":{"TRAIN":range(2790000,2790024),"DEV":range(2790100,2790124)}}
OPERATORS={"TRAIN":("affine_AX101","feistel_K103","affine_AX107","feistel_K109"),
           "DEV":("affine_AX113","feistel_K127","affine_AX131","feistel_K137")}
FAMILIES=prior.FAMILIES
VECTORS=prior.VECTORS
CHECKSUMS=((1,3,4,2),(2,4,1,3),(4,2,3,1),(3,4,2,1))
TRIALS=(64,256,1024)
MARGINS=(1,3)

def need(val,key):q.need(val,"F124AO_"+key)
def frozen():
    prior.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(prior.__file__)==PARENT_SOURCE_BLOB,
         "SOURCE_PREIMPLEMENTATION_IDENTITY")
    f=json.loads(FREEZE.read_text(encoding="utf8"))
    need(f["schema"]==
        "forge.research.f124ao.frozen-redundant-public-operator-and-sequential-packed-consensus.v1"
        and f["status"]=="PREIMPLEMENTATION_FROZEN"
        and f["original"]["head"]=="ca46eba41179a1c6d9cd0bfa74119782c6d11d88"
        and f["birth"]["TRAIN_operators"]==list(OPERATORS["TRAIN"])
        and f["birth"]["DEV_operators"]==list(OPERATORS["DEV"])
        and f["birth"]["public_examples"]==40
        and f["birth"]["bad_public_output_bits"]==3
        and f["Yggdrasil"]["grid"]["trials"]==list(TRIALS)
        and f["Yggdrasil"]["grid"]["margin"]==list(MARGINS)
        and f["Wingless"]["checksum_grid"]==[list(x) for x in CHECKSUMS]
        and all(x is False for x in f["authority"].values())
        and f["birth"]["Wingless"]==
            {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
        and f["birth"]["Yggdrasil"]==
            {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()},
        "SOURCES_GRIDS_AND_AUTHORITY_FROZEN")
    return f

RENV=dict(prior.am.relation.__globals__,OPERATORS=OPERATORS)
R=types.FunctionType(prior.am.relation.__code__,RENV,
                     prior.am.relation.__name__,prior.am.relation.__defaults__)
PENV=dict(prior.am.plain.__globals__,relation=R)
P=types.FunctionType(prior.am.plain.__code__,PENV,
                     prior.am.plain.__name__,prior.am.plain.__defaults__)
def relation(bits,op,inverse=False):return R(bits,op,inverse)
def plain(g,op,nonce):return P(g,op,nonce)

def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("TRAIN","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS,"FRESH_DISJOINT_SOURCE")
    env=dict(prior.build.__globals__)
    env.update(COHORTS=COHORTS,OPERATORS=OPERATORS,
               relation=relation,plain=plain)
    fn=types.FunctionType(prior.build.__code__,env,
                          prior.build.__name__,prior.build.__defaults__)
    fam,op,nonce,pos,neg,birth=fn(lane,seed,vector,phase)
    before=copy.deepcopy(pos["demos"])
    need(before==neg["demos"] and len(before)==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in before)==3,
         "ORIGINAL_THREE_CORRUPT_SUPPORT_CUSTODY")
    rng=random.Random("F124AO/new_public_support/"+lane+"/"+phase+
                      "/"+str(seed)+"/"+str(tuple(vector))+"/"+fam)
    extra=[]
    for i in range(16):
        x=rng.getrandbits(16)
        inp=[(x>>j)&1 for j in range(16)]
        extra.append({"input_bits":inp,"output_bits":relation(inp,op)})
    for g in (pos,neg):
        g["demos"].extend(copy.deepcopy(extra))
    need(len(pos["demos"])==40 and pos["demos"]==neg["demos"]
         and pos["demos"][:24]==before
         and all(relation(d["input_bits"],op)==d["output_bits"]
                 for d in pos["demos"][24:]),
         "SUPPORT_REDUNDANCY_WITHOUT_LABEL_LEAK")
    oracle=prior.am.old.prior.parent.original.parent.prior.parent.routes15
    relaxed=fam=="rotate4_tolerant"
    need(oracle(plain(pos,op,nonce),relaxed=relaxed)==1
         and oracle(plain(neg,op,nonce),relaxed=relaxed)==0,
         "SOURCE_TRUE_CAUSAL_POSITIVE_NEGATIVE")
    need(oracle({k:pos[k] for k in ("start","target","roles","edges")},
                relaxed=True)==0,"NO_LUCKY_LITERAL_RULE")
    def census(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[f]) for e in g["edges"]
                        for f in ("src_bits","dst_bits")))
    need(census(pos)==census(neg)
         and all(pos[k]==neg[k]
                 for k in ("start","target","roles","demos")),
         "PAIR_UNBLINDED_SOURCE_FAIL")
    return fam,op,nonce,pos,neg,birth

def pairs(lane,phase):
    rows=[]
    for vec in VECTORS:
        for seed in COHORTS[lane][phase]:
            fam,op,nonce,p,n,birth=build(lane,seed,vec,phase)
            rows.append((birth,tuple(vec),fam,op,nonce,p,n))
    need(len(rows)==48
         and all(sum(row[2]==f for row in rows)==12 for f in FAMILIES)
         and (phase!="TRAIN" or
              all(row[0]<COHORTS[lane]["DEV"].start for row in rows)),
         "NEW_SOURCE_FOUR_FAMILIES_AND_TRAIN_DEV")
    return rows

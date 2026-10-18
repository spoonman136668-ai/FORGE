"""F124-BF independent source-only four first-hit hard negatives per graph.

The original private oracle is used ONLY to label source challenges, not to
select candidate algorithms, fit models or expose oracle feedback to them.
"""
from __future__ import annotations
import copy,json,types
from pathlib import Path
from collections import Counter
import f124be_source_only as parent
import f124ao_frozen_source as birth
import f124bc_hard_negative_source as bc
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124bf-frozen-contextual-counterfactual.json"
FREEZE_BLOB="09dda1c17b340326baa05ded6fb097ea06c5e0af"
FREEZE_COMMIT="36e6802e6fd7a97d228bb3613fe24b4c46e019c6"
PARENT="ae512d1471f1f92375652a2e628774afa200b487"
PARENT_SOURCE_BLOB="c5280505df158e26d4e674fd4ea1383dc3cedb51"
COHORTS={"Yggdrasil":{"TRAIN":range(5400000,5400024),
                       "DEV":range(5400100,5400124)}}
OPERATORS={"TRAIN":("affine_AX701","feistel_K701","affine_AX709","feistel_K709"),
           "DEV":("affine_AX719","feistel_K719","affine_AX727","feistel_K727")}
VECTORS=parent.VECTORS
FAMILIES=parent.FAMILIES
ORACLE=bc.TRUE_ORACLE

def need(ok,tag):parent.need(ok,"BF_"+tag)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB and
         witness.blob(parent.__file__)==PARENT_SOURCE_BLOB,
         "IMMUTABLE_SOURCE_AND_PARENT")
    d=json.loads(FREEZE.read_text(encoding="utf8"))
    s=d["sources"];h=d["hard_panel"]
    need(d["schema"]=="forge.research.f124bf.frozen-causal-counterfactual-margin.v1"
         and d["state"]=="PREIMPLEMENTATION_IMMUTABLE"
         and d["lineage"]["parent_head"]==PARENT
         and s["FIT"]==[5400000,5400011]
         and s["SCREEN"]==[5400012,5400023]
         and s["protected_DEV"]==[5400100,5400123]
         and s["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and s["DEV_operators"]==list(OPERATORS["DEV"])
         and h["panel_size"]==4 and h["max_oracle_probes_per_task"]==1024
         and d["public"]["per_task_responses"]==48
         and len(d["policies"])==6
         and all(x is False for x in d["safety"].values()),
         "FROZEN_ADMISSION_OR_IDENTITY_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(
             COHORTS["Yggdrasil"]["DEV"]), "TRAIN_AND_DEV_DISJOINT")
    return d

ENV=dict(birth.RELATION.__globals__,OPERATORS=OPERATORS)
REL=types.FunctionType(birth.RELATION.__code__,ENV,birth.RELATION.__name__,birth.RELATION.__defaults__)
PENV=dict(birth.PLAIN.__globals__,relation=REL)
PLAIN=types.FunctionType(birth.PLAIN.__code__,PENV,birth.PLAIN.__name__,birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return REL(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def four_hard(p,n,op,nonce,fam):
    relaxed=fam=="rotate4_tolerant"
    need(ORACLE(plain(p,op,nonce),relaxed=relaxed)==1
         and ORACLE(plain(n,op,nonce),relaxed=relaxed)==0,
         "ORIGINAL_ORACLE_TRUE_POS_AND_NEG")
    probes=0;hard=[];edits=[]
    for i in range(min(32,len(p["edges"]))):
        for field in ("src_bits","dst_bits"):
            for bit in range(16):
                if len(hard)==4:break
                probes+=1
                g=copy.deepcopy(p)
                g["edges"][i][field][bit]^=1
                if ORACLE(plain(g,op,nonce),relaxed=relaxed)==0:
                    need(g["demos"]==p["demos"]
                         and g["roles"]==p["roles"]
                         and g["start"]==p["start"] and g["target"]==p["target"],
                         "PUBLIC_SOURCE_TOPOLOGY_DRIFT")
                    hard.append(g);edits.append({"edge":i,"field":field,"bit":bit})
            if len(hard)==4:break
        if len(hard)==4:break
    need(probes<=1024 and len(hard)<=4,"FROZEN_ORACLE_SOURCE_BUDGET")
    return hard,{"true_hard":len(hard),"oracle_probes":probes+2,
                 "edits":edits,"oracle_model_feedback":False,
                 "model_based_source_selection":False,
                 "source_fallbacks":4-len(hard)}

def build(seed,vec):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"NO_DEV_SOURCE_BIRTH")
    env=dict(birth.build.__globals__,COHORTS=COHORTS,OPERATORS=OPERATORS,
             relation=relation,plain=plain)
    fn=types.FunctionType(birth.build.__code__,env,birth.build.__name__,birth.build.__defaults__)
    fam,op,nonce,p,n,_=fn("Yggdrasil",seed,vec,"TRAIN")
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,
         "UNCHANGED_24_PUBLIC_AND_THREE_NOISE")
    hard,meta=four_hard(p,n,op,nonce,fam)
    return fam,op,nonce,p,n,hard,meta

def public48(seed,vec,op,query,demos):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS and op in OPERATORS["TRAIN"]
         and query in ("balanced_basis48","random48"),
         "ONLY_SOURCE_NEW_PUBLIC_QUERIES")
    env=dict(parent.public48.__globals__,COHORTS=COHORTS,
             OPERATORS=OPERATORS,relation=relation)
    fn=types.FunctionType(parent.public48.__code__,env,parent.public48.__name__,parent.public48.__defaults__)
    result=fn(seed,vec,op,query,demos)
    need(len(result)==48
         and sum(relation(row["input_bits"],op)!=row["output_bits"] for row in result)==6,
         "MATCHED_PUBLIC_48_SIX_ERRORS")
    return result

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"NO_PROTECTED_DEV")
    seeds=range(5400000,5400012) if stage=="FIT" else range(5400012,5400024)
    out=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n,hard,meta=build(seed,vec)
            out.append((seed,tuple(vec),fam,op,nonce,p,n,hard,meta))
    need(len(out)==24 and
         Counter(x[2] for x in out)==Counter({f:6 for f in FAMILIES}),
         "EQUAL_24_PAIRED_FOUR_HARD_PANEL")
    return out

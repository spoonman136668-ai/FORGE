"""F124-BC source-only one-bit negative near-miss challenge.

Preregistered model-blind source birth: take a true positive from the original
source graph, change ONE bit in at most 32 original edges, and use evaluator
routes15 ONLY to confirm a label-negative result. Candidate enumeration is
lexicographic, stopping at FIRST negative. Model scores NEVER choose sources.
If no one-bit oracle-negative found under the frozen 1024-probe limit, retain
unchanged original negative and clearly mark fallback as NOT a hard negative.
"""
from __future__ import annotations
import copy,json,types
from pathlib import Path
from collections import Counter
import f124bb_train_source as parent
import f124ao_frozen_source as source_birth
import f124am_frozen_source as am
import f124w_hop_trace_indexed as witness

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124bc-frozen-hard-negative-falsification.json"
FREEZE_BLOB="834945168ad01172dcd63b9e6440cfcc482cc0b1"
FIRST_COMMIT="0fd49102ab8d7aca68adeac089d88194670b816e"
PARENT="6d4bed6013d956c06da9bd3762775433701c90f4"
PARENT_SOURCE_BLOB="1547633c2cea224643e43d08bffeb04ed4e56f7d"
COHORTS={"Yggdrasil":{"TRAIN":range(5100000,5100024),
                       "DEV":range(5100100,5100124)}}
OPERATORS={"TRAIN":("affine_AX541","feistel_K541","affine_AX547","feistel_K547"),
           "DEV":("affine_AX557","feistel_K557","affine_AX563","feistel_K563")}
VECTORS=parent.VECTORS
FAMILIES=parent.FAMILIES
TRUE_ORACLE=am.old.prior.parent.original.parent.prior.parent.routes15
def need(ok,key):parent.need(ok,"BC_"+key)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(parent.__file__)==PARENT_SOURCE_BLOB,
         "IMMUTABLE_SOURCE_PARENT")
    d=json.loads(FREEZE.read_text(encoding="utf-8"))
    c=d["cohort"]
    h=d["challenge"]
    need(d["schema"]=="forge.research.f124bc.frozen-hard-negative-falsification.v1"
         and d["status"]=="PREIMPLEMENTATION_FROZEN"
         and d["lineage"]["source_parent_exact"]==PARENT
         and c["TRAIN"]==[5100000,5100023]
         and c["FIT"]==[5100000,5100011]
         and c["held_SCREEN"]==[5100012,5100023]
         and c["reserved_DEV"]==[5100100,5100123]
         and c["TRAIN_operators"]==list(OPERATORS["TRAIN"])
         and c["DEV_operators"]==list(OPERATORS["DEV"])
         and h["source_probe_max"]==1024 and h["source_edges_max"]==32
         and h["hard_negative_near_miss_bit_edits"]==1
         and h["fields"]==["src_bits","dst_bits"]
         and h["reported_coverage_requirements"]["minimum_hard_negatives_on_FIT"]==18
         and len(d["arms"])==4 and d["public"]["total_responses_per_task"]==48
         and all(v is False for v in d["governance"].values()),
         "FROZEN_SOURCE_BIRTH_OR_PROTOCOL_DRIFT")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["DEV"])
         and set(COHORTS["Yggdrasil"]["TRAIN"]).isdisjoint(COHORTS["Yggdrasil"]["DEV"]),
         "TRAIN_DEV_DISJOINT")
    return d

REN=dict(source_birth.RELATION.__globals__,OPERATORS=OPERATORS)
REL=types.FunctionType(source_birth.RELATION.__code__,REN,
                       source_birth.RELATION.__name__,source_birth.RELATION.__defaults__)
PEN=dict(source_birth.PLAIN.__globals__,relation=REL)
PLAIN=types.FunctionType(source_birth.PLAIN.__code__,PEN,
                         source_birth.PLAIN.__name__,source_birth.PLAIN.__defaults__)
def relation(bits,op,inverse=False):return REL(bits,op,inverse)
def plain(graph,op,nonce):return PLAIN(graph,op,nonce)

def model_blind_one_bit_near_miss(pos,original_negative,op,nonce,family):
    """Independent source oracle, fixed FIRST negative; no model access."""
    relaxed=family=="rotate4_tolerant"
    need(TRUE_ORACLE(plain(pos,op,nonce),relaxed=relaxed)==1
         and TRUE_ORACLE(plain(original_negative,op,nonce),relaxed=relaxed)==0,
         "ORIGINAL_SOURCE_LABELS")
    count=0
    for i in range(min(32,len(pos["edges"]))):
        for field in ("src_bits","dst_bits"):
            for j in range(16):
                count+=1
                candidate=copy.deepcopy(pos)
                candidate["edges"][i][field][j]^=1
                if TRUE_ORACLE(plain(candidate,op,nonce),relaxed=relaxed)==0:
                    need(candidate["demos"]==pos["demos"]
                         and candidate["roles"]==pos["roles"]
                         and candidate["start"]==pos["start"]
                         and candidate["target"]==pos["target"],
                         "NO_PUBLIC_TASK_OR_TOPOLOGY_DRIFT")
                    return candidate,{"hard":True,"source_oracle_probes":count,
                        "edit_edge_index":i,"edit_field":field,"edit_bit":j,
                        "edit_hamming_bits":1,"label_oracle_only":True,
                        "selection_used_model_predictions":False}
    return copy.deepcopy(original_negative),{
        "hard":False,"source_oracle_probes":count,"edit_edge_index":None,
        "edit_field":None,"edit_bit":None,"edit_hamming_bits":None,
        "label_oracle_only":True,"selection_used_model_predictions":False}

def build(seed,vec):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS,"ONLY_TRAIN_OR_HOLD_SCREEN")
    env=dict(source_birth.build.__globals__,COHORTS=COHORTS,
             OPERATORS=OPERATORS,relation=relation,plain=plain)
    fn=types.FunctionType(source_birth.build.__code__,env,
                          source_birth.build.__name__,source_birth.build.__defaults__)
    family,op,nonce,p,n,_=fn("Yggdrasil",seed,vec,"TRAIN")
    need(p["demos"]==n["demos"] and len(p["demos"])==24
         and sum(relation(d["input_bits"],op)!=d["output_bits"]
                 for d in p["demos"])==3,"ORIGINAL_PUBLIC_SUPPORT_INTACT")
    challenge,meta=model_blind_one_bit_near_miss(p,n,op,nonce,family)
    need(challenge["demos"]==p["demos"]==n["demos"]
         and TRUE_ORACLE(plain(challenge,op,nonce),
            relaxed=family=="rotate4_tolerant")==0,
         "CONFIRMED_SOURCE_TRUE_NEGATIVE")
    return family,op,nonce,p,n,challenge,meta

def public48(seed,vec,op,condition,demos):
    need(type(seed) is int and seed in COHORTS["Yggdrasil"]["TRAIN"]
         and tuple(vec) in VECTORS and op in OPERATORS["TRAIN"]
         and condition in ("balanced_basis48","random48"),
         "NO_PROTECTED_PUBLIC_RESPONSES")
    # Rebind original public response query function through the prior wrapper.
    env=dict(parent.parent.old.original.original.old.active_public_demos.__globals__,
             COHORTS=COHORTS,OPERATORS=OPERATORS,relation=relation)
    fn=types.FunctionType(parent.parent.old.original.original.old.active_public_demos.__code__,env,
                          parent.parent.old.original.original.old.active_public_demos.__name__,
                          parent.parent.old.original.original.old.active_public_demos.__defaults__)
    rows=fn(seed,vec,op,condition,demos)
    need(len(rows)==48
         and sum(relation(d["input_bits"],op)!=d["output_bits"] for d in rows)==6,
         "EXACT_48_PUBLIC_AND_SIX_ERRORS")
    return rows

def rows(stage):
    frozen()
    need(stage in ("FIT","SCREEN"),"TRAIN_SPLITS_ONLY")
    seeds=(range(5100000,5100012) if stage=="FIT" else range(5100012,5100024))
    out=[]
    for vec in VECTORS:
        for seed in seeds:
            fam,op,nonce,p,n,h,meta=build(seed,vec)
            out.append((seed,tuple(vec),fam,op,nonce,p,n,h,meta))
    need(len(out)==24 and
         Counter(x[2] for x in out)==Counter({f:6 for f in FAMILIES}),
         "COMPLETE_INDEPENDENT_24_PAIRED")
    return out

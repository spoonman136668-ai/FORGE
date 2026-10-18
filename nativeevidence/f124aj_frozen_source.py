"""F124-AJ independent operator teaching examples, not named rule tokens.

Generator-only map family is used solely to birth paired source graphs,
make support examples, and authenticate labels after model prediction.
The learner MUST NOT import this module or consult family names.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,random,types,copy
from pathlib import Path
import f124ah_frozen_source as original
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124aj-frozen-incontext-operator-learning.json"
FREEZE_BLOB="c6f370fe58c3a4aec38ddc45bfad2d65f6b7f17f"
PARENT_SOURCE_BLOB="ebc4c043704ac5066bea5ca5194ca65fa344f3de"
COHORTS={"Wingless":{"TRAIN":range(2280000,2280024),"HOLDOUT":range(2280100,2280124)},
         "Yggdrasil":{"TRAIN":range(2290000,2290024),"HOLDOUT":range(2290100,2290124)}}
FAMILIES=original.FAMILIES
VECTORS=original.VECTORS
OPERATOR_NAMES={"TRAIN":("xor_mask_FFFF","rotl_4","xor_mask_0F0F","rotl_8"),
                "HOLDOUT":("bit_reverse","bit_pair_swap",
                           "permutation_rotate3_xor_A55A","reverse_xor_1357")}
DEMO_COUNTS=(8,12,16,24)

def need(ok,label):q.need(ok,"F124AJ_"+label)

def frozen():
    original.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(original.__file__)==PARENT_SOURCE_BLOB,
         "FREEZE_OR_ORIGINAL_GENERATOR")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124aj.frozen-incontext-operator-induction.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_head"]=="7415fff61943dabc34d72decabd15f8c962848bb"
         and p["source"]["train_semantic_families"]==list(OPERATOR_NAMES["TRAIN"])
         and p["source"]["holdout_semantic_families"]==list(OPERATOR_NAMES["HOLDOUT"])
         and p["source"]["Wingless"]==
             {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
             {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
         and p["source"]["demonstrations_per_task"]==24
         and p["Yggdrasil"]["train_hyperparameter_grid_demo_count"]==list(DEMO_COUNTS)
         and all(v is False for v in p["authority"].values())
         and set(OPERATOR_NAMES["TRAIN"]).isdisjoint(OPERATOR_NAMES["HOLDOUT"]),
         "PROSPECTIVE_TRAIN_HOLDOUT_AND_CAPACITY")
    return p

def truth_mapping(operator):
    """Source/evaluator only: explicit invertible 16-bit map generator."""
    need(operator in OPERATOR_NAMES["TRAIN"]+OPERATOR_NAMES["HOLDOUT"],
         "PRESPECIFIED_OPERATOR")
    if operator.startswith("xor_mask_"):
        perm=tuple(range(16))
        mask=int(operator[len("xor_mask_"):],16)
    elif operator.startswith("rotl_"):
        n=int(operator[5:])
        perm=tuple((i+n)%16 for i in range(16))
        mask=0
    elif operator=="bit_reverse":
        perm=tuple(15-i for i in range(16));mask=0
    elif operator=="bit_pair_swap":
        perm=tuple(i^1 for i in range(16));mask=0
    elif operator=="permutation_rotate3_xor_A55A":
        perm=tuple((i+3)%16 for i in range(16));mask=0xA55A
    else:
        need(operator=="reverse_xor_1357","CORRECT_HELDOUT_FAMILY")
        perm=tuple(15-i for i in range(16));mask=0x1357
    need(sorted(perm)==list(range(16)),"BIJECTIVE_BIT_COORDINATES")
    return perm,mask

def apply(bits,operator):
    need(type(bits) is list and len(bits)==16
         and all(type(v) is int and v in (0,1) for v in bits),
         "PUBLIC_DEMONSTRATION_16BIT")
    perm,mask=truth_mapping(operator)
    return [bits[perm[i]]^((mask>>i)&1) for i in range(16)]

def invert(bits,operator):
    perm,mask=truth_mapping(operator)
    result=[0]*16
    for j in range(16):result[perm[j]]=bits[j]^((mask>>j)&1)
    return result

def plain_for_oracle(g,operator,tag):
    need(type(g) is dict and "demos" in g,"PUBLIC_GRAPH_AND_EXAMPLES")
    restored=copy.deepcopy(g)
    restored.pop("demos")
    pre="rel_task_"+tag+":"
    need(all(x.startswith(pre) for x in restored["roles"]) and
         all(x["role"].startswith(pre) for x in restored["edges"]),
         "OPAQUE_PUBLIC_TASK_ID")
    restored["roles"]=[x[len(pre):] for x in restored["roles"]]
    for e in restored["edges"]:
        e["role"]=e["role"][len(pre):]
        e["src_bits"]=invert(e["src_bits"],operator)
    return restored

def build(lane,requested,vector,period):
    need(lane in COHORTS and period in ("TRAIN","HOLDOUT")
         and type(requested) is int and requested in COHORTS[lane][period]
         and tuple(vector) in VECTORS,
         "INDEPENDENT_OPERATOR_TASK")
    adapted={ln:{"FIT":v["TRAIN"],"DEV":v["HOLDOUT"]}
             for ln,v in COHORTS.items()}
    env=dict(original.build.__globals__)
    env["COHORTS"]=adapted
    make=types.FunctionType(original.build.__code__,env,
                            original.build.__name__,original.build.__defaults__)
    old_family,pos,neg,chosen=make(
        lane,requested,vector,"FIT" if period=="TRAIN" else "DEV")
    index=(requested-COHORTS[lane][period].start)%4
    need(old_family==FAMILIES[index],"ORIGINAL_FAMILY_UNTOUCHED")
    op=OPERATOR_NAMES[period][index]
    pos=original.restore(pos,old_family)
    neg=original.restore(neg,old_family)
    tag=hashlib.sha256(("F124AJ/opaque/"+lane+"/"+period+"/"+str(chosen)+
        "/"+str(tuple(vector))+"/"+old_family).encode()).hexdigest()[:12]
    rng=random.Random("F124AJ/demo/"+lane+"/"+period+"/"+str(chosen)+
                      "/"+str(tuple(vector))+"/"+old_family)
    demos=[]
    for i in range(24):
        raw=rng.getrandbits(16)
        inp=[(raw>>j)&1 for j in range(16)]
        demos.append({"input_bits":inp,"output_bits":apply(inp,op)})
    marker="rel_task_"+tag+":"
    for graph in (pos,neg):
        graph["roles"]=[marker+r for r in graph["roles"]]
        for e in graph["edges"]:
            e["role"]=marker+e["role"]
            e["src_bits"]=apply(e["src_bits"],op)
        graph["demos"]=copy.deepcopy(demos)
    # These source-only checks are NEVER exposed to a scorer.
    a=plain_for_oracle(pos,op,tag)
    b=plain_for_oracle(neg,op,tag)
    relaxed=old_family=="rotate4_tolerant"
    need(original.parent.prior.parent.routes15(a,relaxed=relaxed)==1
         and original.parent.prior.parent.routes15(b,relaxed=relaxed)==0,
         "NEW_RELATION_SOURCE_ONLY_ADMISSION")
    def public_graph(g):
        return {k:copy.deepcopy(v) for k,v in g.items() if k!="demos"}
    aa=public_graph(pos);bb=public_graph(neg)
    need(original.parent.prior.parent.routes15(
          aa,relaxed=True)==0
         and original.parent.prior.parent.routes15(
          bb,relaxed=True)==0,
         "ORIGINAL_EQUALITY_SHORTCUT_ELIMINATED")
    def census(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(census(pos)==census(neg)
         and all(pos[k]==neg[k] for k in ("start","target","roles","demos")),
         "SAME_LABEL_BLIND_TOPOLOGY_TOKENS_AND_SUPPORT")
    return old_family,op,tag,pos,neg,chosen

def pairs(lane,period):
    result=[]
    for vector in VECTORS:
        for seed in COHORTS[lane][period]:
            fam,op,tag,p,n,chosen=build(lane,seed,vector,period)
            result.append((chosen,tuple(vector),fam,op,tag,p,n))
    need(len(result)==48
         and all(sum(x[2]==family for x in result)==12 for family in FAMILIES)
         and (period!="TRAIN" or
              all(x[0]<COHORTS[lane]["HOLDOUT"].start for x in result)),
         "SOURCE_FAMILY_AND_TRAIN_HOLDOUT_SEPARATION")
    return result

"""F124-AK source-only nonlinear/carry relation birth; no model import.

A real new source generator is first-admitted with unchanged AJ bytecode
and only new COHORTS. Strip prior AJ relation, apply new bijective
triangular-AND or modular-addition source relation, with independently
generated 24 public examples. True rule never appears in graph roles.
"""
from __future__ import annotations
import hashlib,random,json,copy,types
from pathlib import Path
from collections import Counter
import f124aj_frozen_source as parent
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ak-frozen-nonlinear-transfer.json"
FREEZE_BLOB="c052cabc1e1ad5b762337ea31f606883fb6cb234"
PARENT_BLOB="9516beb4d32acb22d1a8ad8ae102a31602568311"
COHORTS={"Wingless":{"TRAIN":range(2380000,2380024),"HOLDOUT":range(2380100,2380124)},
         "Yggdrasil":{"TRAIN":range(2390000,2390024),"HOLDOUT":range(2390100,2390124)}}
FAMILIES=parent.FAMILIES
VECTORS=parent.VECTORS
OPERATORS={"TRAIN":("add_00B3","tri_and_1_2","add_012F","tri_and_1_3"),
           "HOLDOUT":("tri_and_2_4","add_003D","tri_and_1_4","add_0179")}
SUPPORT=(4,6,8,12,24)
BETA=(0.,.1,.25,.5,1.)

def need(ok,label):q.need(ok,"F124AK_"+label)

def frozen():
    parent.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(parent.__file__)==PARENT_BLOB,
         "AUTHENTIC_FREEZE_AND_SOURCE")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]==
         "forge.research.f124ak.frozen-nonlinear-operator-induction-and-packed-evidence.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["parent_head"]=="262a21a646047fea6695a32cf3cca5c8aadb0734"
         and p["sources"]["Wingless"]==
              {k:[v.start,v.stop-1] for k,v in COHORTS["Wingless"].items()}
         and p["sources"]["Yggdrasil"]==
              {k:[v.start,v.stop-1] for k,v in COHORTS["Yggdrasil"].items()}
         and p["sources"]["TRAIN_relations"]==list(OPERATORS["TRAIN"])
         and p["sources"]["HOLDOUT_relations"]==list(OPERATORS["HOLDOUT"])
         and p["Yggdrasil"]["support_grid"]==list(SUPPORT)
         and p["Wingless"]["beta_grid"]==list(BETA)
         and all(v is False for v in p["authority"].values()),
         "NEW_SOURCE_AND_FIT_RULE")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["HOLDOUT"]),
         "HOLDOUT_OPERATOR_IDENTITY")
    return p

def integer(bits):return sum(x<<j for j,x in enumerate(bits))
def bits(value):return [(value>>i)&1 for i in range(16)]

def relation(bits_in,operator,inverse=False):
    need(operator in OPERATORS["TRAIN"]+OPERATORS["HOLDOUT"],
         "PROSPECTIVE_RULE_IN_SOURCE_ONLY")
    if operator.startswith("add_"):
        n=int(operator[4:],16)
        return bits((integer(bits_in)+(-n if inverse else n))&65535)
    _,_,pp,qq=operator.split("_")
    p,q=int(pp),int(qq)
    need(1<=p<q<=5,"FROZEN_TRIANGULAR_RULE")
    if inverse:
        recovered=[]
        for j in range(16):
            t=(recovered[j-p]&recovered[j-q]) if j>=q else 0
            recovered.append(bits_in[j]^t)
        return recovered
    return [v^((bits_in[j-p]&bits_in[j-q]) if j>=q else 0)
            for j,v in enumerate(bits_in)]

def plain(g,operator,tag):
    need(type(g) is dict and "demos" in g,"OPAQUE_SOURCE_TASK")
    marker="rel_task_"+tag+":"
    out=copy.deepcopy(g);out.pop("demos")
    need(all(role.startswith(marker) for role in out["roles"]),
         "SOURCE_PUBLIC_TASK_ROLES")
    out["roles"]=[role[len(marker):] for role in out["roles"]]
    for e in out["edges"]:
        need(e["role"].startswith(marker),"SOURCE_EDGE_TASK_ROLES")
        e["role"]=e["role"][len(marker):]
        e["src_bits"]=relation(e["src_bits"],operator,True)
    return out

def build(lane,requested,vec,phase):
    need(lane in COHORTS and phase in ("TRAIN","HOLDOUT")
         and requested in COHORTS[lane][phase] and tuple(vec) in VECTORS,
         "INDEPENDENT_NEW_LANE_COHORT")
    env=dict(parent.build.__globals__)
    env["COHORTS"]=COHORTS
    birth=types.FunctionType(parent.build.__code__,env,
                             parent.build.__name__,parent.build.__defaults__)
    family,old_op,old_tag,p,n,selected=birth(lane,requested,vec,phase)
    index=(requested-COHORTS[lane][phase].start)%4
    need(family==FAMILIES[index],"SOURCE_FAMILY_NOT_CHANGED")
    p=parent.plain_for_oracle(p,old_op,old_tag)
    n=parent.plain_for_oracle(n,old_op,old_tag)
    op=OPERATORS[phase][index]
    tag=hashlib.sha256(("F124AK/"+lane+"/"+phase+"/"+str(selected)+
          "/"+str(tuple(vec))+"/"+family).encode()).hexdigest()[:12]
    rng=random.Random("F124AK/support/"+lane+"/"+phase+"/"+str(selected)+
                      "/"+str(tuple(vec))+"/"+family)
    demos=[]
    for j in range(24):
        raw=bits(rng.getrandbits(16))
        demos.append({"input_bits":raw,"output_bits":relation(raw,op)})
    marker="rel_task_"+tag+":"
    for graph in (p,n):
        graph["roles"]=[marker+r for r in graph["roles"]]
        for e in graph["edges"]:
            e["role"]=marker+e["role"]
            e["src_bits"]=relation(e["src_bits"],op)
        graph["demos"]=copy.deepcopy(demos)
    relaxed=family=="rotate4_tolerant"
    need(parent.original.parent.prior.parent.routes15(
         plain(p,op,tag),relaxed=relaxed)==1 and
         parent.original.parent.prior.parent.routes15(
         plain(n,op,tag),relaxed=relaxed)==0,
         "NEW_NONLINEAR_RULE_CAUSAL_ADMISSION")
    normp={k:p[k] for k in ("start","target","roles","edges")}
    normn={k:n[k] for k in ("start","target","roles","edges")}
    need(parent.original.parent.prior.parent.routes15(normp,relaxed=True)==0
         and parent.original.parent.prior.parent.routes15(normn,relaxed=True)==0,
         "OLD_RAW_EQUALITY_SHORTCUT_REJECTED")
    def census(g):
        return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                Counter(tuple(e[k]) for e in g["edges"]
                        for k in ("src_bits","dst_bits")))
    need(census(p)==census(n) and
         all(p[k]==n[k] for k in ("start","target","roles","demos")),
         "SAME_PUBLIC_PAIRED_GRAPH_AND_SUPPORT")
    return family,op,tag,p,n,selected

def pairs(lane,phase):
    result=[]
    for vec in VECTORS:
        for seed in COHORTS[lane][phase]:
            family,operator,tag,p,n,chosen=build(lane,seed,vec,phase)
            result.append((chosen,tuple(vec),family,operator,tag,p,n))
    need(len(result)==48 and
         all(sum(row[2]==family for row in result)==12
             for family in FAMILIES)
         and (phase!="TRAIN" or
              all(row[0]<COHORTS[lane]["HOLDOUT"].start for row in result)),
         "NEW_TRAIN_HOLDOUT_SOURCE_IDENTITY")
    return result

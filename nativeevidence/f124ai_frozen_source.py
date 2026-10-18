"""F124-AI novel rule-family source with disjoint TRAIN / HOLDOUT.

Production model code never imports this module's reference inversion. The
new public rule is stated explicitly as rel_xor_XXXX: or rel_rotl_N: on each
query role and edge role. TRAIN uses two XOR masks/two rotation parameters.
HOLDOUT contains four unseen parameter values, zero overlap.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import copy,json,types
import f124ah_frozen_source as ah
import f124w_hop_trace_indexed as witness
import f124q_fresh_source as q

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ai-frozen-compositional-public-rule.json"
FREEZE_BLOB="5f1a0acf498b6bfec4414ccafc2efebfd581e512"
PARENT_BLOB="ebc4c043704ac5066bea5ca5194ca65fa344f3de"
COHORTS={"Wingless":{"TRAIN":range(2180000,2180024),"HOLDOUT":range(2180100,2180124)},
         "Yggdrasil":{"TRAIN":range(2190000,2190024),"HOLDOUT":range(2190100,2190124)}}
FAMILIES=ah.FAMILIES
VECTORS=ah.VECTORS
OPERATORS={"TRAIN":("xor_FFFF","rotl_4","xor_0F0F","rotl_8"),
           "HOLDOUT":("xor_55AA","rotl_12","xor_A55A","rotl_3")}
ETAS=(0.,.025,.05,.1,.2,.4)

def need(value,label):q.need(value,"F124AI_"+label)

def frozen():
    ah.frozen()
    need(witness.blob(FREEZE)==FREEZE_BLOB
         and witness.blob(ah.__file__)==PARENT_BLOB,
         "FROZEN_AUTHENTIC_SOURCE_AND_PLAN")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124ai.frozen-public-rule-compositional-transfer.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["exact_parent"]==
             "d56e95cb2383891250aad685bdb0842a141e4d30"
         and p["source"]["TRAIN_operator_values"]==list(OPERATORS["TRAIN"])
         and p["source"]["HOLDOUT_operator_values"]==list(OPERATORS["HOLDOUT"])
         and p["source"]["Wingless"]==
             {k:[r.start,r.stop-1] for k,r in COHORTS["Wingless"].items()}
         and p["source"]["Yggdrasil"]==
             {k:[r.start,r.stop-1] for k,r in COHORTS["Yggdrasil"].items()}
         and p["Yggdrasil"]["eta_grid"]==list(ETAS)
         and all(value is False for value in p["authority"].values()),
         "TRAIN_UNSEEN_OPERATOR_OR_AUTHORITY")
    need(set(OPERATORS["TRAIN"]).isdisjoint(OPERATORS["HOLDOUT"]),
         "RELATION_FAMILY_HELD_OUT")
    return p

def rule_transform(bits,operator,inverse=False):
    need(type(bits) is list and len(bits)==16 and
         all(type(x) is int and x in (0,1) for x in bits),
         "PUBLIC_RAW_BITS")
    if operator.startswith("xor_"):
        mask=int(operator[4:],16)
        need(0<mask<65536,"FROZEN_XOR_MASK")
        return [v^((mask>>i)&1) for i,v in enumerate(bits)]
    need(operator.startswith("rotl_"),"FROZEN_ROTATION_OPERATOR")
    amount=int(operator[5:])
    need(0<amount<16,"PUBLIC_ROTATION_PARAMETER")
    if inverse:return bits[-amount:]+bits[:-amount]
    return bits[amount:]+bits[:amount]

def prefix(operator):return "rel_"+operator+":"

def restore_public(g,operator):
    """ONLY in source/evaluator, never in model scoring."""
    marker=prefix(operator)
    transformed=copy.deepcopy(g)
    need(all(r.startswith(marker) for r in transformed["roles"]) and
         all(e["role"].startswith(marker) for e in transformed["edges"]),
         "HONEST_PUBLIC_DECLARED_RULE")
    transformed["roles"]=[r[len(marker):] for r in transformed["roles"]]
    for e in transformed["edges"]:
        e["role"]=e["role"][len(marker):]
        e["src_bits"]=rule_transform(e["src_bits"],operator,inverse=True)
    return transformed

def oracle(g,operator,family):
    return ah.parent.prior.parent.routes15(
        restore_public(g,operator),
        relaxed=family=="rotate4_tolerant")

def build(lane,requested,vector,period):
    need(lane in COHORTS and period in ("TRAIN","HOLDOUT")
         and type(requested) is int
         and requested in COHORTS[lane][period]
         and tuple(vector) in VECTORS,
         "FRESH_INDEPENDENT_REQUEST")
    phase="FIT" if period=="TRAIN" else "DEV"
    # Source generator code itself unchanged, with only new cohort bindings.
    env=dict(ah.build.__globals__)
    adapted={"Wingless":{"FIT":COHORTS["Wingless"]["TRAIN"],
                        "DEV":COHORTS["Wingless"]["HOLDOUT"]},
             "Yggdrasil":{"FIT":COHORTS["Yggdrasil"]["TRAIN"],
                         "DEV":COHORTS["Yggdrasil"]["HOLDOUT"]}}
    env["COHORTS"]=adapted
    fn=types.FunctionType(ah.build.__code__,env,ah.build.__name__,ah.build.__defaults__)
    old_family,p,n,admitted=fn(lane,requested,vector,phase)
    index=(requested-COHORTS[lane][period].start)%4
    need(old_family==FAMILIES[index],"UNCHANGED_AH_STRUCTURE_FAMILY")
    origp=ah.restore(p,old_family)
    orign=ah.restore(n,old_family)
    operator=OPERATORS[period][index]
    marker=prefix(operator)
    for graph in (origp,orign):
        graph["roles"]=[marker+r for r in graph["roles"]]
        for e in graph["edges"]:
            e["role"]=marker+e["role"]
            e["src_bits"]=rule_transform(e["src_bits"],operator)
    need(oracle(origp,operator,old_family)==1 and
         oracle(orign,operator,old_family)==0,
         "SOURCE_NEW_RELATION_ORACLE_ONLY")
    need(ah.parent.prior.parent.routes15(origp,relaxed=True)==0 and
         ah.parent.prior.parent.routes15(orign,relaxed=True)==0,
         "OLD_EQUALITY_SHORTCUT_REJECTED")
    def inv(graph):
        return (Counter((e["from"],e["to"],e["role"]) for e in graph["edges"]),
                Counter(tuple(e[k]) for e in graph["edges"]
                        for k in ("src_bits","dst_bits")))
    need(inv(origp)==inv(orign) and
         all(origp[k]==orign[k] for k in ("start","target","roles")),
         "PAIRED_QUERY_TOPOLOGY_AND_TOKEN_MATCH")
    return old_family,operator,origp,orign,admitted

def pairs(lane,period):
    out=[]
    for vector in VECTORS:
        for seed in COHORTS[lane][period]:
            family,operator,p,n,chosen=build(lane,seed,vector,period)
            out.append((chosen,tuple(vector),family,operator,p,n))
    need(len(out)==48 and
         all(sum(x[2]==family for x in out)==12 for family in FAMILIES)
         and (period!="TRAIN" or
              all(x[0]<COHORTS[lane]["HOLDOUT"].start for x in out)),
         "FRESH_FAMILY_AND_PHASE_DENOMINATOR")
    return out

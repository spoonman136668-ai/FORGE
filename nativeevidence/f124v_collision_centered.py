"""F124-V preregistered equal-cardinality compression & centered causal cell values.

No FIT tuning or parameter reuse from DEV. Original F124-O/T/U weights and
negative verdicts are immutable. Only public graph fields enter prediction.
"""
from __future__ import annotations
from collections import defaultdict
import json
import math
from pathlib import Path
import types

import f124u_interventions as parent
import f124q_fresh_source as source
import f124q_independent_binding as q
import f124o_native_learners as original

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124v-frozen-collision-centered-cell.json"
FREEZE_BLOB="a88353bfd2090a3869aa4e125f92605c3a5626f7"
PARENT_SOURCE_BLOB="4fb51d3981ebc7c4b468faff866351f39e135510"
ORIGINAL_Q_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
COHORTS={
 "Wingless":{"FIT":range(880000,880024),"DEV":range(880100,880124)},
 "Yggdrasil":{"FIT":range(890000,890024),"DEV":range(890100,890124)}
}
VECTORS=parent.VECTORS


def need(ok,label):
    source.need(ok,"F124V_"+label)


def git_blob(path):
    return source.git_blob(Path(path).read_bytes().replace(b"\r\n",b"\n"))


def frozen():
    parent.frozen()
    need(git_blob(FREEZE)==FREEZE_BLOB,"FROZEN_PREIMPLEMENTATION_IDENTITY")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124v.frozen-collision-and-centered-cell.v1"
         and p["state"]=="PREIMPLEMENTATION_FROZEN"
         and p["lineage"]["qualified_parent"]=="6ba96aaaeff083a5e2f54020c70d2a717e431a10"
         and p["lineage"]["parent_u_source_blob"]==PARENT_SOURCE_BLOB
         and p["hypotheses"]["Yggdrasil"]["fixed_mechanism"].find("0.15")>=0
         and p["source"]["cohorts"]==
             {lane:{phase:[r.start,r.stop-1] for phase,r in sub.items()}
              for lane,sub in COHORTS.items()}
         and all(v is False for v in p["safety"].values())
         and git_blob(parent.__file__)==PARENT_SOURCE_BLOB
         and git_blob(q.__file__)==ORIGINAL_Q_BLOB,
         "FROZEN_SOURCE_OR_SAFETY_DRIFT")
    return p


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and tuple(vector) in VECTORS
         and seed not in parent.COHORTS[lane]["FIT"]
         and seed not in parent.COHORTS[lane]["DEV"]
         and seed not in source.COHORTS[lane]["FIT"]
         and seed not in source.COHORTS[lane]["DEV"]
         and seed not in source.FORBIDDEN[lane],
         "NONRESERVED_NEVER_REUSED_PUBLIC_SOURCE")
    env=dict(parent.build.__globals__)
    env["COHORTS"]=COHORTS
    clone=types.FunctionType(parent.build.__code__,env,
                             parent.build.__name__,parent.build.__defaults__)
    pos,neg=clone(lane,seed,vector,phase)
    need(source.paired_admit(pos,neg),"ORIGINAL_PUBLIC_CAUSAL_ADMISSION")
    return pos,neg


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"KNOWN_PHASE_AND_LANE")
    return [(seed,tuple(v),*build(lane,seed,v,phase))
            for v in VECTORS for seed in COHORTS[lane][phase]]


def nibble_code(bits):
    need(type(bits) is list and len(bits)==4 and
         all(type(b) is int and b in (0,1) for b in bits),
         "NIBBLE_RAW_BITS")
    return (bits[0]+2*bits[1]+3*bits[2]+4*bits[3])%5


def wingless_collision_reassignment(graph,base,delta):
    """Still only 4 scalar channels, each restricted to the original 5 bins.

    Original popcount compression loses nibble identities with equal bit count;
    this nonlearned signed checksum changes collisions but adds no category
    levels or state slots. Entire original 3/node engine, priority and head
    are unchanged.
    """
    source.validate_public(graph)
    weights=q.wingless_anchored_weights(list(base),list(delta))
    edges=original.sorted_edges(graph)
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "evictions":0,"state_limit":3,"compression_levels":5,
          "compression_channels":4}
    def encode(bits):
        work["raw_bit_ops"]+=16
        return tuple(weights[j]*(nibble_code(bits[4*j:4*j+4])-2)/2
                     for j in range(4))
    def affinity(left,right):
        work["raw_bit_ops"]+=4
        return 1.-sum(abs(a-b) for a,b in zip(left,right))/8.
    states={graph["start"]:[(0.,None)]}
    for k,role in enumerate(graph["roles"]):
        nextrole=graph["roles"][k+1] if k+1<len(graph["roles"]) else None
        following=defaultdict(list)
        for node in sorted(states):
            allowed=[e for e in edges if e["from"]==node and e["role"]==role]
            for score,carried in states[node]:
                work["public_edge_scans"]+=len(edges)
                for edge in allowed:
                    src=encode(edge["src_bits"])
                    dst=encode(edge["dst_bits"])
                    match=1. if carried is None else affinity(carried,src)
                    value=score+weights[4]*(match-.6)
                    if nextrole is None:
                        look=0.
                    else:
                        possible=[p for p in edges if
                                  p["from"]==edge["to"] and p["role"]==nextrole]
                        look=max((affinity(dst,encode(p["src_bits"]))
                                  for p in possible),default=0.)
                    priority=value+weights[5]*(look-.6)
                    following[edge["to"]].append((priority,value,dst))
        states={}
        for node,rows in following.items():
            rows.sort(key=lambda x:(-x[0],-x[1],x[2]))
            work["evictions"]+=max(0,len(rows)-3)
            states[node]=[(value,vec) for _,value,vec in rows[:3]]
        work["max_active"]=max(work["max_active"],
                               sum(len(v) for v in states.values()))
        need(work["max_active"]<=192 and
             all(len(v)<=3 for v in states.values()),"FIXED_WINGLESS_STATE_CAPACITY")
    finals=[s for s,_ in states.get(graph["target"],[])]
    best=max(finals,default=-2.*len(graph["roles"]))
    logit=4.*(best/max(1,len(graph["roles"])-1)-weights[6])
    need(math.isfinite(logit),"FINITE_COMPRESSED_OUTPUT")
    return logit,work


def yggdrasil_centered_evidence(graph,base,delta):
    """Candidate-relative, depth-normalized causal-key updates.

    Unlike U, same-hop candidate centered evidence has zero group mean.
    Frozen .15 coefficient and +/- .1 bound apply to each hop's score update.
    No extra cell, learned weight, privileged route or inference oracle.
    """
    source.validate_public(graph)
    need(len(base)==7 and len(delta)==2 and
         all(math.isfinite(float(x)) for x in (*base,*delta)),
         "FROZEN_PARAMETER_SHAPE")
    edges=original.sorted_edges(graph)
    active=[(graph["start"],None,0.)]
    retained=[]
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,"prospective_key_comparisons":0,
          "centered_arithmetic":0,
          "active_cell_limit":7,"retained_cell_limit":9}
    def comp(left,right):
        if left is None:return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            left[4*j:4*j+4],right[4*j:4*j+4]))/4.
            for j in range(4))/4.
    depth=len(graph["roles"])
    for k,role in enumerate(graph["roles"]):
        nextrole=graph["roles"][k+1] if k+1<depth else None
        pre=[]
        for node,carried,score in active+retained:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:continue
                similarity=comp(carried,edge["src_bits"])
                value=score+base[4]*(similarity-.35)
                competition=base[5]*(similarity-.5)
                if nextrole is None:
                    look=0.
                else:
                    options=[e for e in edges if e["from"]==edge["to"]
                             and e["role"]==nextrole]
                    work["public_edge_scans"]+=len(edges)
                    look=max((comp(tuple(edge["dst_bits"]),item["src_bits"])
                              for item in options),default=0.)
                    work["prospective_key_comparisons"]+=len(options)
                pre.append((value,competition,look,edge["to"],tuple(edge["dst_bits"])))
        mean=sum(row[2] for row in pre)/len(pre) if pre else 0.
        candidates=[]
        for value,competition,look,node,key in pre:
            raw=.15*(delta[0]+delta[1])*(look-mean)/depth
            increment=max(-.1,min(.1,raw))
            work["centered_arithmetic"]+=4
            new_value=value+increment
            cell=(node,key,new_value)
            candidates.append((new_value+competition+delta[0]*(look-.5),
                               new_value-competition+delta[1]*(look-.5),cell))
        candidates.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[x[2] for x in candidates[:7]]
        selected={id(x) for x in candidates[:7]}
        extras=[x for x in candidates if id(x) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[x[2] for x in extras[:9]]
        work["evictions"]+=max(0,len(candidates)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"EXACT_SEVEN_ACTIVE_NINE_RETAINED")
    values=[s for node,_,s in active+retained if node==graph["target"]]
    best=max(values,default=-2.*depth)
    logit=4.*(best/max(1,depth)-base[6])
    need(math.isfinite(logit),"FINITE_CENTRED_LOGIT")
    return logit,work

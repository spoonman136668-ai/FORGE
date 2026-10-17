"""F124-P frozen one-change mechanisms. F124-O original source is never modified.

Wingless: 3-slot latent diversity selection, public observations only.
Yggdrasil: 7 active unique-destination priority, 9 retained as before.
Frozen ablations use the unchanged F124-O functions where possible.
"""
from __future__ import annotations
from collections import defaultdict
import math

import f124o_native_learners as original
import f124n_novel_structure_source as source


def need(ok, code):
    source.need(ok, "F124P_" + code)


def wingless_diverse(g, w):
    """Original Wingless equations plus ONE bounded selection innovation."""
    source.validate_public(g)
    need(len(w)==7 and all(type(v) in (int,float) and math.isfinite(v) for v in w),
         "WINGLESS_WEIGHTS")
    edges=original.sorted_edges(g)
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "evictions":0,"state_limit":3,"diversity_comparisons":0}
    def enc(bits):
        work["raw_bit_ops"]+=16
        return tuple(w[j]*(sum(2*b-1 for b in bits[j*4:j*4+4])/4.)
                     for j in range(4))
    def affine(a,b):
        work["raw_bit_ops"]+=4
        return 1.-sum(abs(x-y) for x,y in zip(a,b))/8.
    states={g["start"]:[(0.,None)]}
    for step,role in enumerate(g["roles"]):
        nextrole=g["roles"][step+1] if step+1<len(g["roles"]) else None
        new=defaultdict(list)
        for node in sorted(states):
            allowed=[e for e in edges if e["from"]==node and e["role"]==role]
            for score,carried in states[node]:
                work["public_edge_scans"]+=len(edges)
                for edge in allowed:
                    src=enc(edge["src_bits"])
                    dst=enc(edge["dst_bits"])
                    compat=1. if carried is None else affine(carried,src)
                    value=score+w[4]*(compat-.6)
                    if nextrole is None:
                        look=0.
                    else:
                        queries=[q for q in edges if q["from"]==edge["to"] and
                                 q["role"]==nextrole]
                        look=max((affine(dst,enc(q["src_bits"])) for q in queries),
                                 default=0.)
                    priority=value+w[5]*(look-.6)
                    new[edge["to"]].append((priority,value,dst))
        states={}
        for node,candidates in new.items():
            candidates.sort(key=lambda x:(-x[0],-x[1],x[2]))
            selected=[]
            deferred=[]
            for item in candidates:
                if len(selected)>=3:
                    deferred.append(item)
                    continue
                distinct=True
                for prior in selected:
                    work["diversity_comparisons"]+=4
                    if sum((a-b)**2 for a,b in zip(item[2],prior[2]))<.25**2:
                        distinct=False
                        break
                if distinct:
                    selected.append(item)
                else:
                    deferred.append(item)
            # Prefer diversity but never silently reduce capacity below original.
            for item in deferred:
                if len(selected)>=3:
                    break
                selected.append(item)
            work["evictions"]+=max(0,len(candidates)-len(selected))
            states[node]=[(value,key) for _,value,key in selected]
        work["max_active"]=max(work["max_active"],sum(len(x) for x in states.values()))
        need(work["max_active"]<=192,"WINGLESS_STATE_BUDGET")
    terminal=[score for score,_ in states.get(g["target"],[])]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-w[6])
    need(math.isfinite(logit),"WINGLESS_FINITE")
    return logit,work


def yggdrasil_cell_variant(g,w,*,disable_retained=False,diverse_active=False):
    """Original 7+9 budget with optional retained ablation OR node diversity."""
    source.validate_public(g)
    need(len(w)==7 and all(type(v) in (int,float) and math.isfinite(v) for v in w)
         and not (disable_retained and diverse_active),"YGGDRASIL_VARIANT_SHAPE")
    edges=original.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    work={"public_edge_scans":0,"raw_bit_ops":0,"max_active":1,
          "max_retained":0,"evictions":0,
          "active_cell_limit":7,"retained_cell_limit":9,
          "diversity_comparisons":0}
    def compatibility(carried,src):
        if carried is None:
            return 1.
        work["raw_bit_ops"]+=16
        return sum(w[j]*sum(int(a==b) for a,b in zip(
                carried[j*4:j*4+4],src[j*4:j*4+4]))/4. for j in range(4))/4.
    for role in g["roles"]:
        candidate=[]
        for node,carried,score in active+([] if disable_retained else retained):
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                similarity=compatibility(carried,edge["src_bits"])
                value=score+w[4]*(similarity-.35)
                competition=w[5]*(similarity-.5)
                cell=(edge["to"],tuple(edge["dst_bits"]),value)
                candidate.append((value+competition,value-competition,cell))
        candidate.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        chosen=candidate[:7]
        if diverse_active:
            chosen=[]
            used_nodes=set()
            for row in candidate:
                work["diversity_comparisons"]+=1
                dest=row[2][0]
                if dest not in used_nodes and len(chosen)<7:
                    chosen.append(row)
                    used_nodes.add(dest)
            for row in candidate:
                if len(chosen)>=7:
                    break
                if not any(row is chosen_row for chosen_row in chosen):
                    chosen.append(row)
        active=[row[2] for row in chosen]
        selected={id(row) for row in chosen}
        extras=[row for row in candidate if id(row) not in selected]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[row[2] for row in extras[:9]]
        work["evictions"]+=max(0,len(candidate)-16)
        work["max_active"]=max(work["max_active"],len(active))
        work["max_retained"]=max(work["max_retained"],len(retained))
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"YGGDRASIL_CELL_BUDGET")
    terminal=[score for node,_,score in active+retained if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    logit=4.*(best/max(1,len(g["roles"])-1)-w[6])
    need(math.isfinite(logit),"YGGDRASIL_FINITE")
    return logit,work


def variant_forward(lane,arm,g,w):
    """One frozen architectural delta or specified ablation; no training."""
    need(lane in ("Wingless","Yggdrasil"),"UNKNOWN_LANE")
    need(arm in ("original","ablate_compression","ablate_secondary",
                 "candidate"),"UNKNOWN_ARM")
    original_weights=list(w)
    need(len(original_weights)==7,"MISSING_ORIGINAL_WEIGHTS")
    if arm=="original":
        return original.forward(lane,g,original_weights)
    if arm=="ablate_compression":
        original_weights[:4]=[1.,1.,1.,1.]
        return original.forward(lane,g,original_weights)
    if arm=="ablate_secondary":
        if lane=="Wingless":
            original_weights[5]=0.
            return original.wingless_forward(g,original_weights)
        return yggdrasil_cell_variant(g,original_weights,disable_retained=True)
    if lane=="Wingless":
        return wingless_diverse(g,original_weights)
    return yggdrasil_cell_variant(g,original_weights,diverse_active=True)

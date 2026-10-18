"""F124-AI compositional public-rule interpreter for bounded original models.

This is an EXPLICIT ENGINEERED rule grammar, NOT a learned representation.
Learnable component is only Yggdrasil scalar eta, selected on source-frozen
TRAIN alone. Operator arguments are parsed compositionally from PUBLIC roles.
No oracle, graph labels, source-family key or held-out special cases.
"""
from __future__ import annotations
import copy,math,re
import f124ag_transition_models as ag
import f124ae_scoring_transfer as old
import f124q_fresh_source as q

PREFIX=re.compile(r"^rel_(xor_([0-9A-F]{4})|rotl_([1-9]|1[0-5])):")
ETAS=(0.,.025,.05,.1,.2,.4)

def need(ok,label):q.need(ok,"F124AI_MODEL_"+label)

def public_operator(role):
    need(type(role) is str,"DECLARED_ROLE_STRING_ONLY")
    m=PREFIX.match(role)
    need(m is not None,"PUBLIC_OPERATOR_MISSING")
    name=m.group(1)
    tail=role[m.end():]
    need(bool(tail),"PUBLIC_ROLE_IDENTIFIER_MISSING")
    if m.group(2) is not None:
        mask=int(m.group(2),16)
        need(0<mask<65536,"NONTRIVIAL_PUBLIC_MASK")
        return ("xor",mask,tail,m.group())
    amount=int(m.group(3))
    need(0<amount<16,"PUBLIC_ROTATION_IN_RANGE")
    return ("rotl",amount,tail,m.group())

def normalize_public_graph(graph):
    """One role-declared reversible operator, no label or target path."""
    need(type(graph) is dict and set(graph)=={"start","target","roles","edges"},
         "PUBLIC_GRAPH_FIELDS")
    roles=graph["roles"]
    need(type(roles) is list and len(roles) in range(7,16),
         "PUBLIC_ROLE_DEPTH")
    parsed=[public_operator(role) for role in roles]
    kind,parameter=parsed[0][:2]
    need(all((k,p)==(kind,parameter) for k,p,*_ in parsed),
         "RULE_UNIFORMLY_PUBLIC")
    result={"start":graph["start"],"target":graph["target"],
            "roles":[x[2] for x in parsed],"edges":[]}
    bit_ops=0
    for e in graph["edges"]:
        k,p,plain,_=public_operator(e["role"])
        need((k,p)==(kind,parameter),"EDGE_ROLE_RULE_AGREEMENT")
        bits=e["src_bits"]
        need(type(bits) is list and len(bits)==16
             and all(type(b) is int and b in (0,1) for b in bits),
             "SOURCE_PUBLIC_16BITS_ONLY")
        if kind=="xor":
            normalized=[bit^((parameter>>i)&1) for i,bit in enumerate(bits)]
            bit_ops+=16
        else:
            normalized=bits[-parameter:]+bits[:-parameter]
            bit_ops+=16
        result["edges"].append({"from":e["from"],"to":e["to"],
                                "role":plain,"src_bits":normalized,
                                "dst_bits":list(e["dst_bits"])})
    # Original graph valid under original structural validator;
    # this is SOURCE-BLIND validation, not causal admission.
    ag.frozen.prior.parent.validate_15(result)
    return result,{"public_rule_family":kind,
                   "public_parameter":parameter,
                   "normalized_edges":len(result["edges"]),
                   "additional_raw_bit_ops":bit_ops,
                   "extra_retained_cells":0,
                   "operator_was_explicit_in_roles":True}

def ygg(graph,base,delta,eta):
    need(eta in ETAS,"TRAIN_ONLY_ETA_GRID")
    normalized,pre=normalize_public_graph(graph)
    score,raw,ratio,work=ag.ygg_transition(
        normalized,list(base),list(delta),eta)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_SEVEN_PLUS_NINE")
    return score,raw,ratio,work,pre

def wing(graph,base,delta):
    normalized,pre=normalize_public_graph(graph)
    score,work=old.frozen_packed(normalized,list(base),list(delta))
    need(work["max_states_per_node"]==1 and work["max_active"]<=64
         and work["max_packed_bits_per_state"]==12,
         "ORIGINAL_SINGLE_PACKED_12BIT_STATE")
    return score,work,pre

def train_eta(cases,base,delta):
    need(len(cases)==48,"COMPLETE_NEW_TRAIN_COHORT")
    grid=[]
    for eta in ETAS:
        paired=0
        for seed,vector,family,operator,pos,neg in cases:
            positive=ygg(pos,base,delta,eta)[0]
            negative=ygg(neg,base,delta,eta)[0]
            paired+=int(positive>=0 and negative<0)
        grid.append({"eta":eta,"paired":paired})
    chosen=sorted(grid,key=lambda x:(-x["paired"],x["eta"]))[0]
    return chosen,grid

def old_ygg(graph,base,delta):
    score,raw,ratio,work=ag.ygg_transition(
        graph,list(base),list(delta),.1)
    return score,work

def old_wing(graph,base,delta):
    return old.frozen_packed(graph,list(base),list(delta))

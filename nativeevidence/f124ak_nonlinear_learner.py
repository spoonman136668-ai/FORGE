"""F124-AK example-conditioned inference of NON-permutation relations.

Source-blind in-task hypothesis selection: test generic modular-addition and
triangular two-input AND-XOR families against public unlabeled examples.
Learn unknown addition constant or triangular offsets and optional output
flip mask by measured agreement. Neither names nor source oracle imported.
TRAIN learns demonstration count, not operator labels. Holds old 7+9.
"""
from __future__ import annotations
import f124aj_example_operator_learner as aj
import f124ag_transition_models as ag
import f124ae_scoring_transfer as old
import f124q_fresh_source as q

SUPPORT=(4,6,8,12,24)
BETAS=(0.,.1,.25,.5,1.)

def need(ok,tag):q.need(ok,"F124AK_LEARN_"+tag)
def bits(x):return [(x>>i)&1 for i in range(16)]
def integer(x):return sum(bit<<i for i,bit in enumerate(x))

def triangular(bits_in,p,qq):
    return [v ^ (int(bits_in[i-p] and bits_in[i-qq]) if i>=qq else 0)
            for i,v in enumerate(bits_in)]

def induced_hypotheses(demos,count):
    """Find exact function from support, without source/evaluator import."""
    need(count in SUPPORT and len(demos)==24,"FROZEN_PUBLIC_SUPPORT_SIZE")
    selected=demos[:count]
    examples=[(integer(row["input_bits"]),integer(row["output_bits"]))
              for row in selected]
    hypotheses=[]
    if examples:
        add=(examples[0][1]-examples[0][0])&65535
        if all(((x+add)&65535)==y for x,y in examples):
            hypotheses.append(("add",add))
        for p in range(1,5):
            for qq in range(p+1,6):
                x0=bits(examples[0][0])
                y0=bits(examples[0][1])
                out=triangular(x0,p,qq)
                mask=integer([y0[i]^out[i] for i in range(16)])
                if all((integer(triangular(bits(x),p,qq))^mask)==y
                       for x,y in examples):
                    hypotheses.append(("tri",p,qq,mask))
    return (hypotheses[0] if len(hypotheses)==1 else None),{
        "demos":count,"hypotheses_consistent":len(hypotheses),
        "unique":len(hypotheses)==1,
        "candidate_families_tested":11,
        "hypothesis_class":"modular_add_or_triangular_AND_plus_mask",
        "hidden_operator_name_accessed":False}

def inverse_public_key(out_bits,hypothesis):
    if hypothesis[0]=="add":
        return bits((integer(out_bits)-hypothesis[1])&65535)
    _,p,qq,mask=hypothesis
    target=bits(integer(out_bits)^mask)
    recovered=[]
    for i in range(16):
        t=int(recovered[i-p] and recovered[i-qq]) if i>=qq else 0
        recovered.append(target[i]^t)
    return recovered

def normalize(graph,amount):
    base,demos,nonce=aj.public_task(graph)
    model,learn=induced_hypotheses(demos,amount)
    if model is None:return None,{"learn":learn,"bit_ops":0,"extra_retained_cells":0}
    for e in base["edges"]:
        e["src_bits"]=inverse_public_key(e["src_bits"],model)
    ag.frozen.prior.parent.validate_15(base)
    return base,{"learn":learn,
                 "bit_ops":len(base["edges"])*16,
                 "extra_retained_cells":0}

def ygg(graph,base,delta,amount):
    restored,meta=normalize(graph,amount)
    if restored is None:return -1.e9,None,meta
    score,raw,ratio,work=ag.ygg_transition(
        restored,list(base),list(delta),.1)
    need(work["max_active"]<=7 and work["max_retained"]<=9,
         "ORIGINAL_7_ACTIVE_9_RETAINED")
    return score,work,meta

def wing(graph,base,delta,amount,beta):
    restored,meta=normalize(graph,amount)
    if restored is None:return -1.e9,None,meta
    from f124ak_one_packed_contrast import wing_competitive
    score,work=wing_competitive(restored,list(base),list(delta),beta)
    need(work["max_states_per_node"]==1 and
         work["max_packed_bits_per_state"]==12 and
         work["max_active"]<=64,
         "ORIGINAL_ONE_12BIT_PACKED_SLOT")
    return score,work,meta

def fit_support(cases,base,delta):
    need(len(cases)==48,"TRAIN_ONLY_48_PAIRS")
    grid=[]
    for count in SUPPORT:
        correct=0;ambiguous=0
        for seed,vector,fam,op,tag,p,n in cases:
            a,wa,ma=ygg(p,base,delta,count)
            b,wb,mb=ygg(n,base,delta,count)
            correct+=int(a>=0 and b<0)
            ambiguous+=int(not ma["learn"]["unique"])+int(not mb["learn"]["unique"])
        grid.append({"count":count,"correct":correct,"ambiguous_graphs":ambiguous})
    chosen=sorted(grid,key=lambda row:(-row["correct"],row["count"]))[0]
    return chosen,grid

def fit_wing_beta(cases,base,delta,amount):
    need(len(cases)==48 and amount in SUPPORT,"TRAIN_ONLY_BETA")
    grid=[]
    for beta in BETAS:
        correct=0
        for seed,vec,fam,op,tag,p,n in cases:
            a,_,_=wing(p,base,delta,amount,beta)
            b,_,_=wing(n,base,delta,amount,beta)
            correct+=int(a>=0 and b<0)
        grid.append({"beta":beta,"correct":correct})
    chosen=sorted(grid,key=lambda row:(-row["correct"],row["beta"]))[0]
    return chosen,grid

"""F124-H trainable depth-invariant signed evidence and competition, TRAIN only.

A retains per-record individual carried raw keys and computes learned *mean*
signed compatibility over compared steps, not path mass. B adds learnable
contrast against other publicly eligible same-role outgoing edge matches.
Top-three prospective-query retention is deterministic and nondifferentiable.
No full path enumeration, truth flag, precomputed equality or label at inference.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from pathlib import Path

import f124h_source as source
import f124c_node_state_models as ad

SLOTS=3
PARAM_A=20
PARAM_B=21
EPOCHS=100
AUTO_BLOB="76653b7877cbdc092f12a96e4140a38b381bbddf"

def need(value,code):
    source.require(value,"MODEL_"+code)

def frozen():
    source.frozen()
    raw=Path(ad.__file__).read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(raw)==AUTO_BLOB,"AUTODIFF_IDENTITY")
    return True

def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def initial(arm):
    need(arm in ("A","B"),"UNKNOWN_ARM")
    rng=random.Random(124080)
    # Raw 16-bit compatibility is learned componentwise, never a feature supplied
    # by the environment. Null offset, output gain/bias and rival coefficient.
    weights=[rng.uniform(.4,.85) for _ in range(16)]
    weights.extend([-.02,.10,6.0,.06])
    if arm=="B":weights.append(.25)
    need(len(weights)==(PARAM_A if arm=="A" else PARAM_B),"PARAMETER_BUDGET")
    return weights

def _ekey(e):
    return (e["from"],e["to"],e["role"],tuple(e["src_bits"]),tuple(e["dst_bits"]))

def _sig(x):
    return ad.sig(x)

def _log(x):
    need(x.v>0,"LOG_DOMAIN")
    return ad.tape.node(math.log(x.v),((x,1./x.v),))

def _exp(x):
    value=math.exp(max(-35.,min(35.,x.v)))
    return ad.tape.node(value,((x,value),))

def logmeanexp(values):
    need(len(values)>0,"EMPTY_RIVAL_EVIDENCE")
    detached=max(x.v for x in values)
    total=sum((_exp(x-detached) for x in values),ad.tape.node(0.))
    return _log(total/len(values))+detached

def forward(graph,weights,arm,train_seed=None,query_priority=True):
    """Return (p, logit, gradients-or-None, work) on *public graph* only."""
    source.validate(graph)
    need(arm in ("A","B") and type(weights) is list
         and len(weights)==(PARAM_A if arm=="A" else PARAM_B)
         and all(type(x) in (int,float) and math.isfinite(x) for x in weights)
         and type(query_priority) is bool,"PARAMETER_OR_PUBLIC_INPUT")
    ad.tape=ad.Tape()
    tape=ad.tape
    w=[tape.node(x) for x in weights]
    edges=sorted(graph["edges"],key=_ekey)
    lookup={}
    for role in graph["roles"]:
        for e in edges:
            if e["role"]==role:
                lookup.setdefault((e["from"],role),[]).append(tuple(e["src_bits"]))
    counters={"public_edge_scans":0,"raw_bit_multiply_adds":0,
              "exp_evaluations":0,"sigmoids":0,
              "peak_key_records":0,"max_messages_per_hop":0,
              "evicted_records":0,"readout_compared_hops":0,
              "terminal_records":0,"depth":len(graph["roles"])}
    def agreement(key,other):
        z=w[16]
        for i,(a,b) in enumerate(zip(key,other)):
            z=z+w[i]*(((2*a-1)*(2*b-1))/16.)
            counters["raw_bit_multiply_adds"]+=1
        return z
    # Each record is (sum of learned signed evidence, raw carried key, count).
    # It is not a mean of incompatible states and is not an oracle-verified path.
    states={graph["start"]:[(tape.node(0.),None,0)]}
    for step,role in enumerate(graph["roles"]):
        incoming={}
        nmessage=0
        for node in sorted(states):
            allowed=[e for e in edges if e["from"]==node and e["role"]==role]
            for prior,key,count in states[node]:
                counters["public_edge_scans"]+=len(edges)
                if not allowed:continue
                logits=([agreement(key,tuple(e["src_bits"])) for e in allowed]
                        if key is not None else None)
                for idx,e in enumerate(allowed):
                    if key is None:
                        newevidence=prior
                        newcount=count
                    else:
                        link=logits[idx]
                        delta=link-w[17]
                        if arm=="B" and len(allowed)>1:
                            rivals=[x for j,x in enumerate(logits) if j!=idx]
                            delta=delta+w[20]*(link-logmeanexp(rivals))
                            counters["exp_evaluations"]+=len(rivals)
                        newevidence=prior+delta
                        newcount=count+1
                    nextkey=tuple(e["dst_bits"])
                    incoming.setdefault(e["to"],[]).append(
                        (newevidence,nextkey,newcount,_ekey(e)))
                    nmessage+=1
                    need(nmessage<=128,"MESSAGE_BUDGET")
        states={}
        following=graph["roles"][step+1] if step+1<len(graph["roles"]) else None
        for node in sorted(incoming):
            candidates=[]
            for evidence,key,count,identity in incoming[node]:
                queries=lookup.get((node,following),[]) if following else []
                q=(max(agreement(key,x).v for x in queries)
                   if query_priority and queries else 0.)
                # TRAIN-proof route oracle and valid causal witness never enter
                # either priority or readout. Source-stable tie-break.
                candidates.append(((-q,-evidence.v,identity,key),
                                   evidence,key,count))
            candidates.sort(key=lambda x:x[0])
            counters["evicted_records"]+=max(0,len(candidates)-SLOTS)
            states[node]=[(ev,key,n) for _,ev,key,n in candidates[:SLOTS]]
        counters["peak_key_records"]=max(counters["peak_key_records"],
                                         sum(len(v) for v in states.values()))
        counters["max_messages_per_hop"]=max(counters["max_messages_per_hop"],
                                              nmessage)
        need(counters["peak_key_records"]<=128,"MEMORY_BUDGET")
    terminal=states.get(graph["target"],[])
    counters["terminal_records"]=len(terminal)
    if terminal:
        # Hard best public evidence record; gradients flow through the chosen
        # record, not through candidate membership. No depth sum in head.
        ranked=sorted(terminal,key=lambda x:-x[0].v/max(1,x[2]))
        evidence,key,n=ranked[0]
        counters["readout_compared_hops"]=n
        perhop=evidence/max(1,n)
    else:
        perhop=tape.node(-1.)
    logit=w[18]*(perhop-w[19])
    p=_sig(logit).v
    counters["sigmoids"]+=1
    need(math.isfinite(p) and 0.<=p<=1.,"NONFINITE_PREDICTION")
    grad=None
    if train_seed is not None:
        need(type(train_seed) in (int,float) and math.isfinite(train_seed),
             "INVALID_BACKWARD_SEED")
        tape.back(logit,train_seed)
        grad=[x.grad for x in w]
        need(all(math.isfinite(x) for x in grad),"NONFINITE_GRADIENT")
    counters["terminal_mean_signed_evidence"]=round(perhop.v,10)
    return p,logit.v,grad,counters

def train(lane,vectors,arm):
    frozen()
    need(lane in source.TRAIN and arm in ("A","B") and
         type(vectors) is list and len(vectors)==2 and vectors[0]!=vectors[1]
         and all(type(v) is list and len(v)==3 and
                 all(type(x) is int and 0<=x<=3 for x in v) for v in vectors),
         "TRAIN_ONLY_SOURCE")
    pairs=[source.build(seed,v,lane,"TRAIN") for v in vectors
           for seed in source.TRAIN[lane]]
    need(len(pairs)==48,"TRAIN_COHORT")
    weights=initial(arm);prior=list(weights)
    for epoch in range(EPOCHS):
        grads=[0.]*len(weights)
        for j in range(4):
            pos,neg=pairs[(epoch*4+j)%48]
            pp,lp,_,_=forward(pos,weights,arm)
            pn,ln,_,_=forward(neg,weights,arm)
            rank=1./(1.+math.exp(max(-40.,min(40.,lp-ln))))
            _,_,gp,_=forward(pos,weights,arm,.5*(pp-1.)-.5*rank)
            _,_,gn,_=forward(neg,weights,arm,.5*pn+.5*rank)
            for k in range(len(grads)):grads[k]+=gp[k]+gn[k]
        for k,g in enumerate(grads):
            weights[k]=max(-6.,min(6.,weights[k]-.20*max(-1.5,min(1.5,g/8.))))
    update=math.sqrt(sum((a-b)**2 for a,b in zip(weights,prior)))
    need(update>1e-6 and all(math.isfinite(x) for x in weights),
         "NO_GENUINE_LEARNING")
    bydepth={str(d):{"pairs":0,"paired":0,"ranked":0,
                     "positive_logit_mean":0.,"negative_logit_mean":0.}
             for d in (4,5)}
    paired=tp=tn=ranked=0
    counts={"public_edge_scans":0,"raw_bit_multiply_adds":0,"exp_evaluations":0}
    for pos,neg in pairs:
        pp,lp,_,cost=forward(pos,weights,arm)
        pn,ln,_,_=forward(neg,weights,arm)
        ok=(pp>=.5 and pn<.5)
        paired+=int(ok);tp+=int(pp>=.5);tn+=int(pn<.5);ranked+=int(lp>ln)
        depth=bydepth[str(len(pos["roles"]))]
        depth["pairs"]+=1;depth["paired"]+=int(ok);depth["ranked"]+=int(lp>ln)
        depth["positive_logit_mean"]+=lp;depth["negative_logit_mean"]+=ln
        for k in counts:counts[k]+=cost[k]
    for x in bydepth.values():
        need(x["pairs"]==24,"DEPTH_BALANCE")
        x["positive_logit_mean"]=round(x["positive_logit_mean"]/24,8)
        x["negative_logit_mean"]=round(x["negative_logit_mean"]/24,8)
    return {"lane":lane,"arm":arm,"phase":"TRAIN_ONLY","epochs":EPOCHS,
            "pairs":48,"trainable_parameters":len(weights),
            "update_l2":round(update,9),"weight_sha256":sha(weights),
            "weights":weights,"positive_correct":tp,"negative_correct":tn,
            "paired_correct":paired,"positive_rank_higher":ranked,
            "depth":bydepth,"resource_counts":counts,
            "source_vectors_sha256":sha(vectors),
            "confirmation_generated":0,"scientific_first_use":False,
            "scientific_acceptances":0,"optimizer_promotions":0}

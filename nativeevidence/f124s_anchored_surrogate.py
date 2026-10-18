"""F124-S independently frozen, fresh cohort FIT-only research.

Reuses the original F124-Q generator *bytecode* with disjoint public seed
ranges. Wingless retains uniform-anchored model. Yggdrasil trains Q's same
two inference-time ranking coefficients via a smooth *training-only* path
mass surrogate. No new inference cells, oracle at inference or DEV training.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import random
import types

import f124q_fresh_source as qsource
import f124q_independent_binding as qmodel
import f124o_native_learners as original

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124s-fresh-surrogate-freeze.json"
FREEZE_BLOB="b7807e9eb5a67cafa96c40a8577e7bbed250bc22"
QSOURCE_BLOB="63a8657a948500d3d178aea2c6cdf14880faf431"
QMODEL_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
SCHEMA="forge.research.f124s.fresh-anchored-and-smooth-causal-mass.v1"
COHORTS={
    "Wingless":{"FIT":range(580000,580024),"DEV":range(580100,580124)},
    "Yggdrasil":{"FIT":range(590000,590024),"DEV":range(590100,590124)}
}
VECTORS=qsource.VECTORS


def need(ok,code):
    qsource.need(ok,"F124S_"+code)


def git_blob(file):
    raw=Path(file).read_bytes().replace(b"\r\n",b"\n")
    return qsource.git_blob(raw)


def frozen():
    need(git_blob(FREEZE)==FREEZE_BLOB,"FROZEN_PROTOCOL_DRIFT")
    spec=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(spec["schema"]=="forge.research.f124s.frozen-fresh-compute-census-and-surrogate.v1"
         and spec["state"]=="PREIMPLEMENTATION_FROZEN"
         and spec["parent"]["qualified_qg_head"]==
           "df8ca4cd696734c5e520a7595e749ac6c19ced22"
         and spec["parent"]["f124q_source_git_blob"]==QSOURCE_BLOB
         and spec["parent"]["f124q_model_git_blob"]==QMODEL_BLOB
         and spec["training"]["steps"]==72
         and spec["training"]["epochs"]==12
         and spec["training"]["batch_pairs"]==8
         and spec["training"]["learning_rate"]==0.04
         and spec["training"]["perturbation"]==0.08
         and spec["source"]["FIT"]==
             {k:[v["FIT"].start,v["FIT"].stop-1] for k,v in COHORTS.items()}
         and spec["source"]["DEV"]==
             {k:[v["DEV"].start,v["DEV"].stop-1] for k,v in COHORTS.items()}
         and all(x is False for x in spec["authority"].values())
         and git_blob(qsource.__file__)==QSOURCE_BLOB
         and git_blob(qmodel.__file__)==QMODEL_BLOB,
         "ORIGINAL_BYTECODE_OR_FROZEN_SOURCE_DRIFT")
    qsource.frozen()
    return spec


def build(lane,seed,vector,phase):
    """Rebind ONLY source cohort; graph builder code, salt and admission stay
    original F124-Q bytecode. No reserved or prior cohorts can enter.
    """
    need(lane in COHORTS and phase in ("FIT","DEV")
         and type(seed) is int and seed in COHORTS[lane][phase]
         and seed not in qsource.FORBIDDEN[lane]
         and seed not in qsource.COHORTS[lane]["FIT"]
         and seed not in qsource.COHORTS[lane]["DEV"]
         and tuple(vector) in VECTORS,
         "SEED_OR_PHASE_NOT_FRESH")
    environment=dict(qsource.build.__globals__)
    environment["COHORTS"]=COHORTS
    clone=types.FunctionType(qsource.build.__code__,environment,
                             qsource.build.__name__,
                             qsource.build.__defaults__)
    positive,negative=clone(lane,seed,vector,phase)
    need(qsource.paired_admit(positive,negative),"PAIRED_CAUSAL_PUBLIC_ADMISSION")
    return positive,negative


def pairs(lane,phase):
    need(lane in COHORTS and phase in ("FIT","DEV"),"BAD_COHORT")
    return [(build(lane,seed,vector,phase))
            for vector in VECTORS
            for seed in COHORTS[lane][phase]]


def softplus(x):
    return max(x,0.0)+math.log1p(math.exp(-abs(x)))


def logsumexp(v):
    if not v:
        return -35.0
    biggest=max(v)
    return biggest+math.log(sum(math.exp(x-biggest) for x in v))


def smooth_yggdrasil(graph,base,delta):
    """Training-only soft public-key path mass, no selected oracle path.

    Path energies use the same existing F124-O raw-bit compatibility and
    F124-Q public lookahead cues. Learns *Q inference* deltas; hard 7+9
    inference function is NOT changed. Public target is not the truth label.
    """
    qsource.validate_public(graph)
    need(len(base)==7 and len(delta)==2
         and all(math.isfinite(v) for v in (*base,*delta)),
         "SURROGATE_PARAMS")
    edges=original.sorted_edges(graph)
    count={"public_edge_scans":0,"raw_bit_ops":0,"path_states":1,
           "prospective_key_comparisons":0}
    def sim(left,right):
        if left is None:
            return 1.0
        count["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(a==b) for a,b in zip(
            left[4*j:4*j+4],right[4*j:4*j+4]))/4.0
            for j in range(4))/4.0
    paths=[(graph["start"],None,0.0)]
    for i,role in enumerate(graph["roles"]):
        nextrole=graph["roles"][i+1] if i+1<len(graph["roles"]) else None
        next_paths=[]
        for node,key,mass in paths:
            count["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                compat=sim(key,edge["src_bits"])
                possible=[]
                if nextrole is not None:
                    count["public_edge_scans"]+=len(edges)
                    possible=[e for e in edges if
                              e["from"]==edge["to"] and e["role"]==nextrole]
                prospective=(max((sim(edge["dst_bits"],p["src_bits"])
                                  for p in possible),default=0.0)
                             if nextrole is not None else 0.0)
                count["prospective_key_comparisons"]+=len(possible)
                base_score=base[4]*(compat-.35)+base[5]*(compat-.5)
                new_score=(base_score+delta[0]*(prospective-.5)+
                           delta[1]*(prospective-.5)*(1.0-compat))
                next_paths.append((edge["to"],edge["dst_bits"],mass+new_score))
                need(len(next_paths)<=256,"SOFT_PATH_LIMIT")
        paths=next_paths
        count["path_states"]=max(count["path_states"],len(paths))
    target=[energy for node,_,energy in paths if node==graph["target"]]
    logits=logsumexp(target)-logsumexp([p[2] for p in paths])
    need(math.isfinite(logits),"SOFT_READOUT_NONFINITE")
    return 4.0*logits+3.0,count


def fit_loss(lane,batch,base,delta):
    total=0.0
    counters={"public_edge_scans":0,"raw_bit_ops":0,
              "prospective_key_comparisons":0}
    for pos,neg in batch:
        if lane=="Wingless":
            a,wa=qmodel.forward(lane,pos,list(base),delta)
            b,wb=qmodel.forward(lane,neg,list(base),delta)
        else:
            a,wa=smooth_yggdrasil(pos,base,delta)
            b,wb=smooth_yggdrasil(neg,base,delta)
        for work in (wa,wb):
            for k in counters:
                counters[k]+=work.get(k,0)
        total+=softplus(-a)+softplus(b)+.15*softplus(b-a)
    return total/len(batch),counters


def train(lane,base):
    """Same frozen 72-step SPSA settings, fresh FIT only.

    All public operation costs include both plus/minus gradient evaluations,
    not just best final model. Failed update is retained fail-closed.
    """
    frozen()
    need(lane in COHORTS and len(base)==7,"KNOWN_BASE")
    training_pairs=pairs(lane,"FIT")
    need(len(training_pairs)==48,"FIT_DENOMINATOR")
    d=[0.]* (4 if lane=="Wingless" else 2)
    rng=random.Random(int.from_bytes(hashlib.sha256(
        ("F124S/FIT/SPSA/v1/"+lane).encode()).digest()[:12],"big"))
    initial,_=fit_loss(lane,training_pairs,base,d)
    costs={"public_edge_scans":0,"raw_bit_ops":0,
           "prospective_key_comparisons":0}
    nonzero=0
    step=0
    for epoch in range(12):
        order=list(range(48));rng.shuffle(order)
        for k in range(0,48,8):
            batch=[training_pairs[j] for j in order[k:k+8]]
            signs=[1 if rng.getrandbits(1) else -1 for _ in d]
            hi=[max(-3.,min(3.,v+.08*sgn)) for v,sgn in zip(d,signs)]
            lo=[max(-3.,min(3.,v-.08*sgn)) for v,sgn in zip(d,signs)]
            plus,cp=fit_loss(lane,batch,base,hi)
            minus,cm=fit_loss(lane,batch,base,lo)
            for work in (cp,cm):
                for field in costs:
                    costs[field]+=work[field]
            difference=plus-minus
            nonzero+=int(abs(difference)>1e-12)
            derivative=difference/.16
            rate=.04/(1+.01*step)
            d=[max(-3.,min(3.,v-rate*derivative*sgn))
               for v,sgn in zip(d,signs)]
            step+=1
    update=math.sqrt(sum(v*v for v in d))
    final,_=fit_loss(lane,training_pairs,base,d)
    return {"lane":lane,"delta":d,"delta_sha256":qmodel.digest(d),
            "fit_pairs":48,"epochs":12,"steps":step,
            "nonzero_gradient_steps":nonzero,
            "update_l2":round(update,12),
            "initial_fit_loss":round(initial,10),
            "final_fit_loss":round(final,10),
            "cost_of_gradient_evaluations":costs,
            "DEV_generated_during_fit":False,"protected_read":False,
            "genuine_fit_update":update>1e-9}

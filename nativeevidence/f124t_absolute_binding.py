"""F124-T new preregistered absolute causal-key evidence FIT-only hypothesis.

F124-S's normalized terminal path fraction was constant for these graphs:
every complete role-consistent path terminates at the public query target.
That frozen failure is untouched. New absolute evidence is independently
preregistered: logsumexp(target route mass) - log(number of role routes).
Inference continues to use EXACT original F124-Q 7+9 hard cell model.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import types

import f124s_anchored_surrogate as predecessor
import f124q_fresh_source as qsource
import f124q_independent_binding as qmodel
import f124o_native_learners as original

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124t-absolute-mass-freeze.json"
FREEZE_BLOB="60b985282d581d51cb9b121333fb40f1024f2310"
S_SOURCE_BLOB="0ac891b4ccff616c4d2a689f856487c3c4c574ee"
Q_INFER_BLOB="ebad38ff22ef6b151fd5ff7f25da41a20d9fcf65"
COHORTS={
    "Wingless":{"FIT":range(680000,680024),"DEV":range(680100,680124)},
    "Yggdrasil":{"FIT":range(690000,690024),"DEV":range(690100,690124)}
}
VECTORS=predecessor.VECTORS


def need(cond,label):
    qsource.need(cond,"F124T_"+label)


def git_blob(file):
    return qsource.git_blob(Path(file).read_bytes().replace(b"\r\n",b"\n"))


def frozen():
    predecessor.frozen()
    need(git_blob(FREEZE)==FREEZE_BLOB,"PREIMPLEMENTATION_BLOB")
    p=json.loads(FREEZE.read_text(encoding="utf-8"))
    need(p["schema"]=="forge.research.f124t.frozen-absolute-causal-mass-replacement.v1"
         and p["lineage"]["failed_f124s_head"]==
             "ca0326d5b957647d7131dc1f043c2d9765d466e4"
         and p["lineage"]["failed_f124s_DEV_built"] is False
         and p["lineage"]["f124s_frozen_source_blob"]==S_SOURCE_BLOB
         and p["lineage"]["f124q_inference_blob"]==Q_INFER_BLOB
         and p["source"]["FIT"]==
             {lane:[a["FIT"].start,a["FIT"].stop-1] for lane,a in COHORTS.items()}
         and p["source"]["DEV"]==
             {lane:[a["DEV"].start,a["DEV"].stop-1] for lane,a in COHORTS.items()}
         and p["training"]["no_restart_or_retune_on_failure"]
         and p["resource"]["max_active_ygg"]==7
         and p["resource"]["max_retained_ygg"]==9
         and all(v is False for v in p["authority"].values())
         and git_blob(predecessor.__file__)==S_SOURCE_BLOB
         and git_blob(qmodel.__file__)==Q_INFER_BLOB,
         "PREDECLARED_ARCHITECTURE_OR_SOURCE_DRIFT")
    return p


def build(lane,seed,vector,phase):
    need(lane in COHORTS and phase in ("FIT","DEV")
         and seed in COHORTS[lane][phase]
         and seed not in predecessor.COHORTS[lane]["FIT"]
         and seed not in predecessor.COHORTS[lane]["DEV"]
         and seed not in qsource.COHORTS[lane]["FIT"]
         and seed not in qsource.COHORTS[lane]["DEV"],
         "FRESH_SOURCE_IDENTITY")
    glob=dict(predecessor.build.__globals__)
    glob["COHORTS"]=COHORTS
    fn=types.FunctionType(predecessor.build.__code__,glob,
                          predecessor.build.__name__,
                          predecessor.build.__defaults__)
    return fn(lane,seed,vector,phase)


def pairs(lane,phase):
    return [build(lane,seed,vector,phase)
            for vector in VECTORS
            for seed in COHORTS[lane][phase]]


def logsumexp(v):
    if not v:
        return -35.
    p=max(v)
    return p+math.log(sum(math.exp(a-p) for a in v))


def absolute_yggdrasil(graph,base,delta):
    """No oracle, no exact route, no hidden path. FIT loss only.

    All public role-matched path hypotheses are retained up to the frozen
    256 TRAIN-only budget. This is NEVER the inference graph consumer, which
    remains the original hard 7+9 forward from F124-Q.
    """
    qsource.validate_public(graph)
    need(len(base)==7 and len(delta)==2
         and all(math.isfinite(x) for x in (*base,*delta)),
         "SMOOTH_SURROGATE_PARAMETER")
    edges=original.sorted_edges(graph)
    work={"public_edge_scans":0,"raw_bit_ops":0,"path_states":1,
          "prospective_key_comparisons":0}
    def compat(a,b):
        if a is None:
            return 1.
        work["raw_bit_ops"]+=16
        return sum(base[j]*sum(int(x==y) for x,y in zip(
            a[j*4:j*4+4],b[j*4:j*4+4]))/4. for j in range(4))/4.
    paths=[(graph["start"],None,0.)]
    for step,role in enumerate(graph["roles"]):
        nextrole=(graph["roles"][step+1]
                  if step+1<len(graph["roles"]) else None)
        remaining=[]
        for node,key,mass in paths:
            work["public_edge_scans"]+=len(edges)
            for edge in edges:
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                sim=compat(key,edge["src_bits"])
                possible=[]
                if nextrole is not None:
                    work["public_edge_scans"]+=len(edges)
                    possible=[p for p in edges if p["from"]==edge["to"]
                              and p["role"]==nextrole]
                look=(max((compat(edge["dst_bits"],p["src_bits"])
                           for p in possible),default=0.0)
                      if nextrole is not None else 0.0)
                work["prospective_key_comparisons"]+=len(possible)
                evidence=base[4]*(sim-.35)+base[5]*(sim-.5)
                evidence+=delta[0]*(look-.5)
                evidence+=delta[1]*(look-.5)*(1.-sim)
                remaining.append((edge["to"],edge["dst_bits"],mass+evidence))
                need(len(remaining)<=256,"FROZEN_SOFT_PATH_BUDGET")
        paths=remaining
        work["path_states"]=max(work["path_states"],len(paths))
    targets=[mass for node,_,mass in paths if node==graph["target"]]
    # DIFFERENT from F124-S: fixed-size public graph nuisance baseline;
    # do not normalize by label-blind denominator weighted by same parameters.
    # The terminal target is a public query node, not an oracle path.
    absolute=(logsumexp(targets)-math.log(max(1,len(paths))))
    output=4.*absolute+3.
    need(math.isfinite(output),"NONFINITE_ABSOLUTE_EVIDENCE")
    return output,work


def fit_loss(lane,batch,base,delta):
    if lane=="Wingless":
        return predecessor.fit_loss(lane,batch,base,delta)
    need(lane=="Yggdrasil","LANE")
    total=0.
    counters={"public_edge_scans":0,"raw_bit_ops":0,
              "prospective_key_comparisons":0}
    for pos,neg in batch:
        a,aw=absolute_yggdrasil(pos,base,delta)
        b,bw=absolute_yggdrasil(neg,base,delta)
        for work in (aw,bw):
            for key in counters:
                counters[key]+=work.get(key,0)
        total+=predecessor.softplus(-a)+predecessor.softplus(b)
        total+=.15*predecessor.softplus(b-a)
    return total/len(batch),counters


def train(lane,base):
    """Reuse F124-S exact 12x6 optimizer BYTECODE with only fresh cohorts and
    separately frozen FIT loss; no rewriting training machinery.
    """
    frozen()
    glob=dict(predecessor.train.__globals__)
    glob.update({"COHORTS":COHORTS,"pairs":pairs,"fit_loss":fit_loss,
                 "frozen":frozen})
    fn=types.FunctionType(predecessor.train.__code__,glob,
                          predecessor.train.__name__,
                          predecessor.train.__defaults__)
    return fn(lane,base)

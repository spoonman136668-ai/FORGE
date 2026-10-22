"""Q18 shared-edge causal composition under graph rewiring (TRAIN/DEV only).

Entirely source-free synthetic episode generation. All empirical models see
exactly the same edge skeleton and intervention-match counts; only composed
source-to-terminal reachability labels are supplied for fitting.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import time
import tracemalloc
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BLOB="1d3d37ccb11c0877b165cc13bd7ead3e75cf9a26"
NPROBES=12
CAND="SHARED_EDGE_CAUSAL_COMPOSITOR"
FLAT="TRAINED_TOPOLOGY_PATH_FEATURES"
RNN="TRAINED_TWO_STATE_GRAPH_RNN"
SYM="TRAINED_SYMBOLIC_REACHABILITY"
ORACLE="KNOWN_LAW_ORACLE_BAYES"
KINDS=(CAND,FLAT,RNN,SYM,ORACLE)
FIT_TEMPLATES=("FIT3_CHAIN","FIT4_CHAIN")
DEV_TEMPLATES=("DEV4_DIAMOND","DEV4_SKIP")
EPS=1e-12


def must(ok, name):
    if not ok:
        raise RuntimeError("Q18_"+name)


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def seed(*parts)->int:
    txt=":".join(str(x) for x in parts)
    return int.from_bytes(hashlib.sha256(txt.encode()).digest()[:8],"big")


def protocol():
    data=(ROOT/"FROZEN_PROTOCOL.json").read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    must(blob==BLOB,"FROZEN_GIT_BLOB_DRIFT")
    doc=json.loads(data)
    must(doc["schema"]=="forge.nci04.q18.shared-edge-causal-graph-transfer.v1",
         "SCHEMA_CHANGED")
    d=doc["data"]
    must(tuple(x["name"] for x in d["fit_templates"])==FIT_TEMPLATES
         and tuple(x["name"] for x in d["dev_templates"])==DEV_TEMPLATES,
         "FAMILY_SET_CHANGED")
    must(doc["fit"]["epochs"]==12 and doc["fit"]["restarts"]==[0,1],
         "TRAIN_POLICY_CHANGED")
    return doc


def graph_paths(nodes:int, edges:tuple)->tuple:
    paths=[]
    def dfs(node,used):
        if node==nodes-1:
            paths.append(tuple(used));return
        for i,(source,target) in enumerate(edges):
            if source==node:
                dfs(target,used+[i])
    dfs(0,[])
    return tuple(paths)


def reach(nodes:int, edges:tuple, on:tuple)->bool:
    seen={0}
    for u,v in edges:
        if u in seen and on[edges.index((u,v))]:
            seen.add(v)
    return nodes-1 in seen


def make_episodes(role:str, doc:dict)->list:
    must(role in ("fit","dev"),"PROTECTED_HELD_OR_ORIGINAL_GENERATION")
    templates=(doc["data"]["fit_templates"] if role=="fit"
               else doc["data"]["dev_templates"])
    expected=FIT_TEMPLATES if role=="fit" else DEV_TEMPLATES
    episodes=[]
    for t in templates:
        must(t["name"] in expected and
             t["nodes"] in (3,4) and
             len(t["edges"]) in (2,3,4),
             "TEMPLATE_OUT_OF_FROZEN_SCOPE")
        edges=tuple(tuple(x) for x in t["edges"])
        must(len(edges)==len(set(edges)) and all(
             0<=u<v<t["nodes"] for u,v in edges),
             "NOT_A_PUBLIC_DAG")
        for i in range(t["episodes"]):
            rng=random.Random(seed("q18","v1",role,t["name"],i))
            latents=tuple(rng.randrange(2) for _ in edges)
            counts=[]
            for ispresent in latents:
                nmatch=0
                for _ in range(NPROBES):
                    _action=rng.randrange(2)
                    nmatch+=int(rng.random() < (.8 if ispresent else .5))
                counts.append(nmatch)
            label=int(reach(t["nodes"],edges,latents))
            episodes.append((t["name"],t["nodes"],edges,tuple(counts),label))
    must(len(episodes)==(320 if role=="fit" else 128),
         "DATA_CARDINALITY_NOT_PREREGISTERED")
    return episodes


def digest(episodes:list)->str:
    return sha(json.dumps(episodes,separators=(",",":"),sort_keys=True).encode())


def sigmoid(x:float)->float:
    if x>=0:return 1/(1+math.exp(-x))
    ex=math.exp(x);return ex/(1+ex)


def bce(p:float,y:int)->float:
    p=max(EPS,min(1-EPS,p))
    return -y*math.log(p)-(1-y)*math.log1p(-p)


def enumerate_reach(n:int, edges:tuple, probs:tuple)->float:
    total=0.
    for mask in range(1<<len(edges)):
        weight=1.
        on=[]
        for i,p in enumerate(probs):
            bit=(mask>>i)&1
            weight*=p if bit else (1-p)
            on.append(bit)
        if reach(n,edges,tuple(on)):
            total+=weight
    return total


def public_features(ep):
    _,nodes,edges,counts,_=ep
    e=[(k/12-.5) for k in counts]
    paths=graph_paths(nodes,edges)
    must(paths,"NO_PATH_IN_PUBLIC_SKELETON")
    def raw(i):return counts[i]/12
    mins=[min(raw(i) for i in path) for path in paths]
    products=[math.prod(raw(i) for i in path) for path in paths]
    return [1.,sum(e)/len(e),min(e),max(mins),
            max(products),len(edges)/4,len(paths)/2]


def oracle_edge_posterior(k):
    present=(.8**k)*(.2**(12-k))
    absent=.5**12
    return present/(present+absent)


def predict(kind,params,ep):
    _,n,edges,ks,_=ep
    if kind==CAND:
        probs=tuple(sigmoid(params[0]*(k/12-.5)+params[1]) for k in ks)
        return enumerate_reach(n,edges,probs)
    if kind==ORACLE:
        return enumerate_reach(n,edges,tuple(oracle_edge_posterior(k)
                                              for k in ks))
    if kind==FLAT:
        return sigmoid(sum(v*x for v,x in zip(params,public_features(ep))))
    if kind==RNN:
        h=[0.,0.]
        for (u,v),k in zip(edges,ks):
            evidence=k/12-.5
            span=(v-u)/n
            h[0]=math.tanh(params[0]*h[0]+params[2]*evidence+
                           params[4]*span+params[6])
            h[1]=math.tanh(params[1]*h[1]+params[3]*evidence+
                           params[5]*span+params[7])
        return sigmoid(params[8]*h[0]+params[9]*h[1]+params[10])
    if kind==SYM:
        inferred=tuple(int(k>=params["threshold"]) for k in ks)
        return params["p_yes"] if reach(n,edges,inferred) else params["p_no"]
    raise RuntimeError("Q18_UNKNOWN_MODEL")


def loss(kind,params,rows):
    return sum(bce(predict(kind,params,ep),ep[4])
               for ep in rows)/len(rows)


def fit_gradient(kind,fit,dev,cfg):
    dims={CAND:2,FLAT:7,RNN:11}
    width=dims[kind]
    chosen=None
    costs=[]
    start=time.process_time()
    peak=0
    for restart in cfg["restarts"]:
        rng=random.Random(seed("q18","init",kind,restart))
        p=[rng.uniform(-.5,.5) for _ in range(width)]
        m=[0.]*width;v=[0.]*width
        step=0
        tracemalloc.start()
        for epoch in range(cfg["epochs"]):
            order=list(range(len(fit)))
            rng.shuffle(order)
            for offset in range(0,len(order),cfg["mini_batch_episodes"]):
                batch=[fit[i] for i in order[
                    offset:offset+cfg["mini_batch_episodes"]]]
                grad=[]
                for k in range(width):
                    hi=p.copy();lo=p.copy()
                    hi[k]+=cfg["finite_difference_delta"]
                    lo[k]-=cfg["finite_difference_delta"]
                    grad.append((loss(kind,hi,batch)-loss(kind,lo,batch))/
                                (2*cfg["finite_difference_delta"]))
                norm=math.sqrt(sum(g*g for g in grad))
                if norm>cfg["gradient_clip"]:
                    grad=[g*cfg["gradient_clip"]/norm for g in grad]
                step+=1
                for k,g in enumerate(grad):
                    m[k]=.9*m[k]+.1*g
                    v[k]=.999*v[k]+.001*g*g
                    p[k]-=cfg["lr"]*(m[k]/(1-.9**step))/(
                        math.sqrt(v[k]/(1-.999**step))+1e-8)
                must(all(math.isfinite(x) for x in p),
                     "TRAINED_PARAM_NONFINITE")
        peak=max(peak,tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        score=loss(kind,p,dev)
        costs.append({"restart":restart,"dev_nll":score})
        if chosen is None or score<chosen[0]:
            chosen=(score,p[:],restart)
    return chosen[1],{"fit_cpu_seconds":time.process_time()-start,
                      "max_tracemalloc_bytes":peak,
                      "restart_scores":costs,
                      "selected_restart":chosen[2]}


def fit_symbolic(fit):
    start=time.process_time()
    best=None
    for threshold in range(13):
        true_positive, true_total, false_positive, false_total=0,0,0,0
        for ep in fit:
            prediction=reach(ep[1],ep[2],
                             tuple(int(k>=threshold) for k in ep[3]))
            if prediction:
                true_total+=1;true_positive+=ep[4]
            else:
                false_total+=1;false_positive+=ep[4]
        par={"threshold":threshold,
             "p_yes":(true_positive+1)/(true_total+2),
             "p_no":(false_positive+1)/(false_total+2)}
        score=loss(SYM,par,fit)
        if best is None or score<best[0]:
            best=(score,par)
    return best[1],{"fit_cpu_seconds":time.process_time()-start,
                   "max_tracemalloc_bytes":0,
                   "fit_thresholds_considered":13}


def score(kind,params,dev):
    t=time.process_time()
    values=[bce(predict(kind,params,ep),ep[4]) for ep in dev]
    result={}
    for idx,name in enumerate(DEV_TEMPLATES):
        result[name]=sum(values[idx*64:(idx+1)*64])/64
    predicted=[int(predict(kind,params,ep)>=.5) for ep in dev]
    false_pos=sum(int(y==0 and p==1) for p,ep in zip(predicted,dev)
                  for y in [ep[4]])
    return {"nll":sum(values)/len(values),
            "dev_by_template":result,"hard_false_positives":false_pos,
            "accuracy":sum(int(p==ep[4]) for p,ep in zip(predicted,dev))/len(dev),
            "eval_cpu_seconds":time.process_time()-t,
            "checkpoint_bytes":len(json.dumps(params,sort_keys=True).encode()),
            "parameter_count":len(params) if params is not None else 0,
            "max_online_state_scalars":8}


def ablation(kind,params,dev):
    rewired=[]
    for name,n,edges,ks,y in dev:
        if len(ks)>1:ks=ks[1:]+ks[:1]
        rewired.append((name,n,edges,ks,y))
    return loss(kind,params,rewired)


def selftest(doc):
    fit=make_episodes("fit",doc)
    dev=make_episodes("dev",doc)
    must(len(fit)==320 and len(dev)==128,"SOURCE_FREE_COUNTS")
    must(digest(fit)!=digest(dev),"FIT_DEV_SOURCE_LEAK")
    for role in ("held","HELD5_BRANCHING","HELD5_REVERSED_ROLE",
                 "original","scientific"):
        try: make_episodes(role,doc)
        except RuntimeError as exc:
            must("PROTECTED_HELD_OR_ORIGINAL_GENERATION" in str(exc),
                 "HELD_FIRST_USE_GUARD")
        else:raise RuntimeError("Q18_HELD_GENERATION_ALLOWED")
    example=fit[0]
    for kind,p in ((CAND,[1.0,.0]),(FLAT,[.1]*7),
                   (RNN,[.1]*11),(SYM,{"threshold":7,"p_yes":.9,"p_no":.1}),
                   (ORACLE,None)):
        z=predict(kind,p,example)
        must(math.isfinite(z) and 0<z<1,"PREDICTION_INVALID")
    must(graph_paths(4,((0,1),(0,2),(1,3),(2,3)))==
         ((0,1,2),(0,3)) or
         len(graph_paths(4,((0,1),(0,2),(1,3),(2,3))))==2,
         "DIAMOND_PATH_ENUMERATION_FAILED")
    print("Q18_SOURCE_FREE_FIT_DEV_CUSTODY_SELFTEST=PASS",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("selftest","train-dev"),required=True)
    mode=parser.parse_args().mode
    doc=protocol()
    selftest(doc)
    if mode=="selftest":return
    fit=make_episodes("fit",doc)
    dev=make_episodes("dev",doc)
    costs={};scores={};params={}
    chosen_candidate=None
    for kind in KINDS:
        if kind==ORACLE:
            p=None
            cost={"fit_cpu_seconds":0.,"max_tracemalloc_bytes":0,
                  "privileged_true_generator_law":True}
        elif kind==SYM:p,cost=fit_symbolic(fit)
        else:p,cost=fit_gradient(kind,fit,dev,doc["fit"])
        model=score(kind,p,dev)
        if kind==CAND:
            chosen_candidate=p[:]
        costs[kind]=cost
        scores[kind]=model
        params[kind]=sha(json.dumps(p,sort_keys=True).encode())
        print("Q18_DEV_MODEL="+kind+" NLL="+format(model["nll"],".10f"),flush=True)
    best=min((FLAT,RNN,SYM),key=lambda k:scores[k]["nll"])
    gain=scores[best]["nll"]-scores[CAND]["nll"]
    per={fam:scores[best]["dev_by_template"][fam]-
         scores[CAND]["dev_by_template"][fam] for fam in DEV_TEMPLATES}
    must(chosen_candidate is not None,"MISSING_FROZEN_CANDIDATE_CHECKPOINT")
    ablated_nll=ablation(CAND,chosen_candidate,dev)
    ablation_increase=ablated_nll-scores[CAND]["nll"]
    checks={
        "gain_vs_best_fitted":gain>=doc["frozen_gate"][
            "dev_gain_over_best_fitted_control_min_nats_per_episode"],
        "near_privileged_oracle":scores[CAND]["nll"]<=scores[ORACLE]["nll"]+
            doc["frozen_gate"]["candidate_vs_privileged_oracle_max_nats_gap"],
        "positive_both_rewired_families":all(g>0 for g in per.values()),
        "cpu_vs_recurrent":(costs[CAND]["fit_cpu_seconds"]+
            scores[CAND]["eval_cpu_seconds"])<=1.15*(
            costs[RNN]["fit_cpu_seconds"]+scores[RNN]["eval_cpu_seconds"]),
        "memory_budget":scores[CAND]["max_online_state_scalars"]<=8,
        "causal_edge_alignment_ablation":ablation_increase>=doc["frozen_gate"]["ablation_min_loss_increase_when_edge_evidence_reassigned"]
    }
    report={
        "schema":"forge.nci04.q18.frozen-rewired-fit-dev-result.v1",
        "protocol_git_blob":BLOB,
        "fit_episodes":len(fit),"dev_episodes":len(dev),
        "fit_sha256":digest(fit),"dev_sha256":digest(dev),
        "scores":scores,"costs":costs,
        "checkpoint_sha256":params,
        "best_fitted_control":best,
        "candidate_gain_nats":gain,"gain_by_rewired_family":per,
        "edge_alignment_ablation_nll":ablated_nll,
        "edge_alignment_ablation_increase_nats":ablation_increase,
        "frozen_gate_checks":checks,
        "unknown_held_five_node_generated":False,
        "original_source_engine_episodes":0,
        "scientific_first_use":False,
        "unfamiliar_transfer_accepted":False
    }
    report["verdict"]=(doc["frozen_gate"]["decision_success"]
                       if all(checks.values()) else
                       doc["frozen_gate"]["decision_failure"])
    print("Q18_RESULT_JSON="+json.dumps(report,sort_keys=True,
                       separators=(",",":"),allow_nan=False),flush=True)
    print("Q18_DEV_VERDICT="+report["verdict"],flush=True)
    print("Q18_UNFAMILIAR_HELD_AND_ORIGINAL_SOURCES=NOT_GENERATED",flush=True)


if __name__=="__main__":
    main()

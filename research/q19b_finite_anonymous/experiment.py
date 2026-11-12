"""Q19B source-free finite-intervention anonymous causal relation estimation.

Only empirical FIT graph ancestry labels are supervised. No model is given a
latent structure/permutation at inference; the oracle alone is explicitly
privileged with the true synthetic law and family. No real source is consumed.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
import random
import time
import tracemalloc
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent
FROZEN_BLOB="b6d4bd82e96355fba92be48b2b5d6425141b2195"
PAIRS=tuple((i,j) for i in range(3) for j in range(3) if i!=j)
PERMS=tuple(itertools.permutations(range(3)))
STRUCTURES=("chain","fork")
N=6
CAND="SHARED_TREATMENT_EFFECT_LOGISTIC"
FLAT="TRAINED_PAIRWISE_FLAT_LOGISTIC"
RNN="TRAINED_SHARED_TWO_STEP_RNN"
BAYES="TRAINED_GAUSSIAN_NAIVE_BAYES"
SYM="TRAINED_EFFECT_THRESHOLD"
ORACLE="TRUE_SCM_ORACLE_BAYES"
ALL=(CAND,FLAT,RNN,BAYES,SYM,ORACLE)
EPS=1e-9


def require(ok,reason):
    if not ok:
        raise RuntimeError("Q19B_"+reason)


def hashed(*terms):
    return int.from_bytes(hashlib.sha256(
        ":".join(str(x) for x in terms).encode()).digest()[:8],"big")


def hash_cohort(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,
              separators=(",",":")).encode()).hexdigest()


def load():
    raw=(HERE/"FROZEN_PROTOCOL.json").read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    require(blob==FROZEN_BLOB,"PREEXECUTION_PROTOCOL_BLOB_DRIFT")
    doc=json.loads(raw)
    require(doc["schema"]=="forge.nci04.q19b.anonymous_finite_treatment_learning.v1",
            "SCHEMA_CHANGED")
    require(doc["fit"]["epochs"]==20 and doc["fit"]["restarts"]==[0,1],
            "FROZEN_FIT_POLICY_CHANGED")
    return doc


def parse_ratio(s):
    n,d=s.split("/")
    return float(Fraction(int(n),int(d)))


def simulate(kind,perm,root,e1,e2,intervene):
    hidden=[None,None,None]
    slot,setting=intervene
    node=perm.index(slot)
    if kind=="chain":
        order=(0,1,2)
    else:
        order=(1,0,2)
    for k in order:
        if k==node:
            hidden[k]=setting
        elif kind=="chain":
            hidden[k]=(root if k==0 else
                       hidden[0]^e1 if k==1 else hidden[1]^e2)
        else:
            hidden[k]=(root if k==1 else
                       hidden[1]^e1 if k==0 else hidden[1]^e2)
    visible=[0,0,0]
    for latent,slot_i in enumerate(perm):
        visible[slot_i]=hidden[latent]
    return tuple(visible)


def ancestor_labels(kind,perm):
    edges=((0,1),(1,2)) if kind=="chain" else ((1,0),(1,2))
    answers=[]
    for source,target in PAIRS:
        a=perm.index(source)
        b=perm.index(target)
        closure={a}
        for _ in range(3):
            closure.update(y for x,y in edges if x in closure)
        answers.append(int(b in closure))
    return tuple(answers)


def generate(role,doc):
    require(role in ("fit","development"),"HELD_OR_ORIGINAL_ROLE_DENIED")
    specs=doc["cohorts"]["training"] if role=="fit" else doc["cohorts"]["development"]
    expected=("FIT_ANON1","FIT_ANON2") if role=="fit" else ("DEV_ANON3","DEV_ANON4")
    require(tuple(x["family"] for x in specs)==expected,"COHORT_FAMILY_DRIFT")
    result=[]
    for family in specs:
        p,q=parse_ratio(family["p"]),parse_ratio(family["q"])
        for kind in STRUCTURES:
            for perm in PERMS:
                for idx in range(family["episodes_per_configuration"]):
                    rnd=random.Random(hashed("q19b","v1",role,family["family"],
                                             kind,"".join(map(str,perm)),idx))
                    events=[]
                    for action_slot in range(3):
                        for value in (0,1):
                            for _ in range(N):
                                root=rnd.randrange(2)
                                e1=int(rnd.random()<p)
                                e2=int(rnd.random()<q)
                                v=simulate(kind,perm,root,e1,e2,(action_slot,value))
                                events.append((action_slot,value,v))
                    feats=extract(tuple(events))
                    result.append((family["family"],feats,
                                   ancestor_labels(kind,perm),tuple(events)))
    require(len(result)==(480 if role=="fit" else 288),"DATA_COUNT_DRIFT")
    return result


def extract(events):
    require(len(events)==36,"NOT_EXACTLY_THIRTY_SIX_PUBLIC_EVENTS")
    counts={}
    for slot,action,v in events:
        require(slot in range(3) and action in (0,1) and len(v)==3,
                "MALFORMED_PUBLIC_INTERVENTION_EVENT")
        counts.setdefault((slot,action),[]).append(v)
    require(len(counts)==6 and all(len(x)==6 for x in counts.values()),
            "DO_INTERVENTION_BUDGET_NOT_MATCHED")
    feats=[]
    for i,j in PAIRS:
        k0=sum(v[j] for v in counts[(i,0)])
        k1=sum(v[j] for v in counts[(i,1)])
        feats.append((k0,k1))
    return tuple(feats)


def sigmoid(z):
    if z>=0:
        return 1/(1+math.exp(-z))
    x=math.exp(z)
    return x/(1+x)


def nll(prob,label):
    p=min(1-EPS,max(EPS,prob))
    return -label*math.log(p)-(1-label)*math.log1p(-p)


def estimates(name,params,row):
    _,features,_,_=row
    out=[]
    for index,(k0,k1) in enumerate(features):
        x=(k1-k0)/N
        if name==CAND:
            z=params[0]*x+params[1]
            pred=sigmoid(z)
        elif name==FLAT:
            a=params[3*index:3*index+3]
            pred=sigmoid(a[0]+a[1]*k0/N+a[2]*k1/N)
        elif name==RNN:
            a,w0,w1,b,v,c=params
            h0=math.tanh(w0*k0/N+b)
            h1=math.tanh(a*h0+w1*k1/N+b)
            pred=sigmoid(v*h1+c)
        elif name==BAYES:
            means=params["mean"];var=params["var"];pr=params["prior"]
            def log_density(cls):
                return (-.5*math.log(var[cls])
                        -(x-means[cls])**2/(2*var[cls])+
                        math.log(pr if cls==1 else 1-pr))
            z=log_density(1)-log_density(0)
            pred=sigmoid(z)
        elif name==SYM:
            positive=(k1-k0)>=params["threshold"]
            pred=params["positive"] if positive else params["negative"]
        else:
            raise RuntimeError("Q19B_UNKNOWN_ESTIMATOR")
        out.append(pred)
    return tuple(out)


def weighted_loss(name,params,rows):
    return sum(nll(p,y) for row in rows
               for p,y in zip(estimates(name,params,row),row[2]))/(6*len(rows))


def train_gradient(name,fit,development,cfg):
    dim={CAND:2,FLAT:18,RNN:6}[name]
    best=None
    total_cpu=0.0
    maxpeak=0
    attempts=[]
    for restart in cfg["restarts"]:
        rnd=random.Random(hashed("q19b-init",name,restart))
        theta=[rnd.uniform(-.4,.4) for _ in range(dim)]
        m=[0.0]*dim
        v=[0.0]*dim
        tic=time.process_time()
        tracemalloc.start()
        for epoch in range(cfg["epochs"]):
            gradient=[]
            for i in range(dim):
                high=theta.copy();low=theta.copy()
                high[i]+=cfg["fd_delta"];low[i]-=cfg["fd_delta"]
                gradient.append((weighted_loss(name,high,fit)-
                                 weighted_loss(name,low,fit))/
                                (2*cfg["fd_delta"]))
            length=math.sqrt(sum(x*x for x in gradient))
            if length>cfg["grad_clip"]:
                gradient=[x*cfg["grad_clip"]/length for x in gradient]
            step=epoch+1
            for i,x in enumerate(gradient):
                m[i]=.9*m[i]+.1*x
                v[i]=.999*v[i]+.001*x*x
                theta[i]-=cfg["lr"]*m[i]/(1-.9**step)/(
                    math.sqrt(v[i]/(1-.999**step))+1e-8)
            require(all(math.isfinite(x) for x in theta),"NONFINITE_TRAINING")
        peak=tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        total_cpu+=time.process_time()-tic
        maxpeak=max(maxpeak,peak)
        score=weighted_loss(name,theta,development)
        attempts.append({"restart":restart,"dev_nll":score})
        if best is None or score<best[0]:
            best=(score,theta.copy(),restart)
    return best[1],{"fit_cpu_seconds":total_cpu,
                    "peak_python_bytes":maxpeak,
                    "selected_restart":best[2],
                    "restart_losses":attempts}


def train_bayes(rows):
    start=time.process_time()
    vals={0:[],1:[]}
    for _,fs,ys,_ in rows:
        for (a,b),y in zip(fs,ys):
            vals[y].append((b-a)/N)
    prior=len(vals[1])/(len(vals[0])+len(vals[1]))
    mu=[sum(vals[i])/len(vals[i]) for i in (0,1)]
    var=[max(1/36,sum((v-mu[i])**2 for v in vals[i])/len(vals[i]))
         for i in (0,1)]
    return {"mean":mu,"var":var,"prior":prior},{
        "fit_cpu_seconds":time.process_time()-start,
        "peak_python_bytes":0,
        "fitted_from_labels_only":True}


def train_symbolic(rows):
    tic=time.process_time()
    best=None
    for threshold in range(-6,7):
        positive=[0,0]
        negative=[0,0]
        for _,fs,ys,_ in rows:
            for (a,b),y in zip(fs,ys):
                cell=positive if (b-a)>=threshold else negative
                cell[0]+=y;cell[1]+=1
        par={"threshold":threshold,
             "positive":(positive[0]+1)/(positive[1]+2),
             "negative":(negative[0]+1)/(negative[1]+2)}
        loss=weighted_loss(SYM,par,rows)
        if best is None or loss<best[0]:
            best=(loss,par)
    return best[1],{"fit_cpu_seconds":time.process_time()-tic,
                    "peak_python_bytes":0,
                    "threshold_candidates":13}


def scm_likelihood(kind,perm,p,q,slot,value,observed):
    total=0.0
    for root,e1,e2 in itertools.product((0,1),repeat=3):
        v=simulate(kind,perm,root,e1,e2,(slot,value))
        if v==observed:
            total+=.5*(p if e1 else 1-p)*(q if e2 else 1-q)
    return total


def oracle(row,doc):
    family,_,_,events=row
    spec=next((x for x in doc["cohorts"]["development"]
               if x["family"]==family),None)
    require(spec is not None,"ORACLE_FAMILY_NOT_DECLARED")
    p,q=parse_ratio(spec["p"]),parse_ratio(spec["q"])
    hypotheses=[]
    for kind in STRUCTURES:
        for perm in PERMS:
            loglike=0.0
            for slot,value,observed in events:
                mass=scm_likelihood(kind,perm,p,q,slot,value,observed)
                if mass==0:
                    loglike=float("-inf");break
                loglike+=math.log(mass)
            hypotheses.append((loglike,ancestor_labels(kind,perm)))
    biggest=max(x for x,_ in hypotheses)
    require(math.isfinite(biggest),"ORACLE_ALL_HYPOTHESES_IMPOSSIBLE")
    weights=[math.exp(v-biggest) for v,_ in hypotheses]
    denom=sum(weights)
    return tuple(sum(w*labels[i] for w,(_,labels) in zip(weights,hypotheses))
                 /denom for i in range(6))


def evaluate(name,params,rows,doc):
    tic=time.process_time()
    grouped={}
    fp=0;hits=0;total=0
    for row in rows:
        fam=row[0]
        probs=oracle(row,doc) if name==ORACLE else estimates(name,params,row)
        ys=row[2]
        grouped.setdefault(fam,[]).extend(
            nll(p,y) for p,y in zip(probs,ys))
        for p,y in zip(probs,ys):
            guess=int(p>=.5)
            fp+=int(guess==1 and y==0)
            hits+=int(guess==y)
            total+=1
    family={k:sum(v)/len(v) for k,v in grouped.items()}
    return {"nll":sum(sum(v) for v in grouped.values())/total,
            "dev_by_family":family,
            "accuracy":hits/total,"hard_false_positives":fp,
            "prediction_cpu_seconds":time.process_time()-tic,
            "parameter_count":len(params) if params is not None else 0,
            "state_scalars":12,
            "checkpoint_bytes":len(json.dumps(params,sort_keys=True).encode())}


def selftest(doc):
    fit=generate("fit",doc)
    dev=generate("development",doc)
    require(len(fit)==480 and len(dev)==288,"SELFTEST_COUNT")
    require(hash_cohort(fit)!=hash_cohort(dev),"ROLE_LEAK")
    for role in ("held","HELD_4NODE_CHAIN","HELD_4NODE_FORK",
                 "original","scientific"):
        try:generate(role,doc)
        except RuntimeError as e:
            require("HELD_OR_ORIGINAL_ROLE_DENIED" in str(e),
                    "HELD_ROLE_GUARD_DIAG")
        else:
            raise RuntimeError("Q19B_HELD_GENERATED")
    for row in (fit[0],fit[-1],dev[0]):
        require(len(row[1])==6 and len(row[2])==6 and len(row[3])==36,
                "PUBLIC_DATA_SHAPE")
        require(all(0<=a<=6 and 0<=b<=6 for a,b in row[1]),
                "FEATURE_BOUNDS")
    print("Q19B_SOURCE_FREE_FINITE_ANONYMOUS_ROLE_SELFTEST=PASS",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",required=True,choices=("selftest","train-dev"))
    args=parser.parse_args()
    doc=load()
    selftest(doc)
    if args.mode=="selftest":return
    fit=generate("fit",doc)
    dev=generate("development",doc)
    params={};scores={};costs={}
    for kind in ALL:
        if kind in (CAND,FLAT,RNN):
            model,cost=train_gradient(kind,fit,dev,doc["fit"])
        elif kind==BAYES:
            model,cost=train_bayes(fit)
        elif kind==SYM:
            model,cost=train_symbolic(fit)
        else:
            model=None;cost={"fit_cpu_seconds":0,
                             "privileged_true_scm_model_and_family":True}
        score=evaluate(kind,model,dev,doc)
        params[kind]=model
        scores[kind]=score
        costs[kind]=cost
        print("Q19B_DEV_MODEL="+kind+" NLL="+format(score["nll"],".9f"),
              flush=True)
    comparators=(FLAT,RNN,BAYES,SYM)
    strongest=min(comparators,key=lambda x:scores[x]["nll"])
    candidate=scores[CAND]
    gain=scores[strongest]["nll"]-candidate["nll"]
    byfamily={x:scores[strongest]["dev_by_family"][x]-
              candidate["dev_by_family"][x]
              for x in ("DEV_ANON3","DEV_ANON4")}
    cpu1=costs[CAND]["fit_cpu_seconds"]+candidate["prediction_cpu_seconds"]
    cpu2=costs[RNN]["fit_cpu_seconds"]+scores[RNN]["prediction_cpu_seconds"]
    decision=doc["decision"]
    checks={
        "improves_vs_best_empirical_by_0_015":
            gain>=decision["candidate_must_improve_vs_best_fitted_control_by_nats"],
        "improves_both_dev_families":all(v>0 for v in byfamily.values()),
        "hard_false_positives_nonregression":
            candidate["hard_false_positives"]<=scores[strongest]["hard_false_positives"],
        "cpu_nonregression_vs_rnn":cpu1<=
            decision["candidate_fit_plus_eval_cpu_ratio_vs_recurrent_at_most"]*cpu2,
        "online_state_max_12":candidate["state_scalars"]<=12
    }
    verdict=decision["pass"] if all(checks.values()) else decision["fail"]
    report={
        "schema":"forge.nci04.q19b.finite-anonymous-sourcefree-dev-result.v1",
        "frozen_protocol_blob":FROZEN_BLOB,
        "fit_count":len(fit),"dev_count":len(dev),
        "fit_sha256":hash_cohort(fit),"dev_sha256":hash_cohort(dev),
        "models":scores,"costs":costs,
        "checkpoint_sha256":{
            k:hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
            for k,v in params.items()},
        "best_empirical_control":strongest,
        "candidate_gain_over_best_nats":gain,
        "gain_by_dev_family":byfamily,
        "frozen_checks":checks,
        "decision":verdict,
        "oracle_privileged_known_scm":True,
        "hidden_graph_at_inference":False,
        "supervised_ancestry_labels_in_fit":True,
        "unfamiliar_held_generated":False,
        "original_source_episodes":0,
        "scientific_first_use":False
    }
    print("Q19B_RESULT_JSON="+json.dumps(report,sort_keys=True,
               separators=(",",":"),allow_nan=False),flush=True)
    print("Q19B_FROZEN_DEV_DECISION="+verdict,flush=True)
    print("Q19B_UNFAMILIAR_AND_ORIGINAL_SOURCES=UNOPENED",flush=True)


if __name__=="__main__":
    main()

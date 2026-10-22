"""Q16 frozen source-free, locally gated predictive memory TRAIN/DEV only.

No external datasets, original engines, CKB state, protected original seeds,
G/H held cohorts, network calls, worker dispatch, or paid APIs.
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

HERE = Path(__file__).resolve().parent
PIN = "f47e7a35093833f7b1692a39176aa2eb5093907b"
FAMILIES = ("E_regime", "F_burst")
KINDS = ("SURPRISE_RELIABILITY_WRITE", "TRAINED_TANH_RNN",
         "TRAINED_CUE_BAYES", "TRAINED_DECAYED_CUE_COUNT",
         "TRAINED_CURRENT_CUE")
FREE = 1e-9


def fail_unless(ok, code):
    if not ok:
        raise ValueError("Q16_" + code)


def sha(x):
    return hashlib.sha256(x).hexdigest()


def load():
    data=(HERE / "FROZEN_PROTOCOL.json").read_bytes()
    git=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    fail_unless(git == PIN, "PREREG_BLOB_DRIFT")
    p=json.loads(data)
    fail_unless(p["schema"]=="forge.nci04.q16.gated-predictive-write.v1",
                "PROTOCOL_DRIFT")
    fail_unless(tuple(f["name"] for f in p["generator"]["family_algorithms"])
                == FAMILIES, "FAMILIES_DRIFT")
    fail_unless(p["optimizer"]["epochs"]==18
                and p["optimizer"]["restarts"]==[0,1], "TRAINING_DRIFT")
    return p


def make_seed(*terms):
    key=":".join(str(s) for s in terms)
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],"big")


def data_for(role, family):
    fail_unless(role in ("train","dev") and
                family["name"] in FAMILIES, "ORIGINAL_OR_HELD_FORBIDDEN")
    count=family["train_episodes"] if role=="train" else family["validation_episodes"]
    out=[]
    for index in range(count):
        r=random.Random(make_seed("q16","v1",role,family["name"],index))
        z=r.randrange(2)
        reliable=r.randrange(2)==1
        countdown=0
        xs=[]; cs=[]; labels=[]
        for t in range(family["steps"]):
            if t>0 and r.random()<(.08 if family["name"]=="E_regime" else .13):
                z^=1
            if family["name"]=="E_regime":
                if t>0 and r.random()<.11:
                    reliable=not reliable
                cue=reliable if r.random()>=.09 else not reliable
                mismatch=.06 if reliable else .42
            else:
                if countdown==0 and r.random()<.23:
                    countdown=r.randint(2,5)
                reliable=countdown==0
                cue=reliable
                if countdown:
                    countdown-=1
                mismatch=.14 if reliable else .41
            xbit=z if r.random()>=mismatch else 1-z
            xs.append(2*xbit-1)
            cs.append(1 if cue else -1)
            labels.append(z)
        out.append((family["name"],tuple(xs),tuple(cs),tuple(labels)))
    return out


def digest(dataset):
    return sha(json.dumps(dataset,separators=(",",":")).encode())


def sigmoid(x):
    if x>=0:
        return 1/(1+math.exp(-x))
    y=math.exp(x)
    return y/(1+y)


def bce(logit,y):
    return max(0.0,logit)+math.log1p(math.exp(-abs(logit)))-y*logit


def features(kind, params, ep, bayes=None):
    _, xs, cs, _=ep
    logits=[]
    h=0.0
    for x,c in zip(xs,cs):
        if kind=="SURPRISE_RELIABILITY_WRITE":
            gate=sigmoid(params[0]+params[1]*c+
                         params[2]*abs(x-h))
            h=h*(1-gate)+gate*x
            logit=params[3]*h+params[4]
        elif kind=="TRAINED_TANH_RNN":
            h=math.tanh(params[0]*h+params[1]*x+
                        params[2]*c+params[3])
            logit=params[4]*h+params[5]
        elif kind=="TRAINED_CUE_BAYES":
            hazard=bayes["hazard"]
            prior=h*(1-hazard)+(1-h)*hazard if logits else .5
            noise=bayes["noise_positive"] if c==1 else bayes["noise_negative"]
            p1=(1-noise) if x==1 else noise
            p0=noise if x==1 else (1-noise)
            h=prior*p1/(prior*p1+(1-prior)*p0)
            h=max(FREE,min(1-FREE,h))
            logit=math.log(h/(1-h))
        elif kind=="TRAINED_DECAYED_CUE_COUNT":
            h=.8*h+x
            logit=params[0]*h+params[1]*c*x+params[2]
        elif kind=="TRAINED_CURRENT_CUE":
            logit=params[0]*x+params[1]*c*x+params[2]
        else:
            raise ValueError("Q16_UNKNOWN_MODEL")
        logits.append(logit)
    return logits


def loss(kind,params,episode,bayes=None):
    logits=features(kind,params,episode,bayes)
    return sum(bce(v,y) for v,y in zip(logits,episode[3]))/len(logits)


def evaluate(kind,params,episodes,bayes=None):
    group={k:[] for k in FAMILIES}
    for ep in episodes:
        group[ep[0]].append(loss(kind,params,ep,bayes))
    fail_unless(all(group.values()),"EMPTY_FAMILY")
    avg={k:sum(v)/len(v) for k,v in group.items()}
    return {"by_family":avg,"mean":sum(avg.values())/len(avg)}


def fit_bayes(train):
    mismatch={1:0,-1:0}; counts={1:0,-1:0}
    flips=0; transitions=0
    start=time.process_time()
    for _,xs,cs,ys in train:
        for x,c,y in zip(xs,cs,ys):
            counts[c]+=1
            mismatch[c]+=int((x==1)!=(y==1))
        flips+=sum(a!=b for a,b in zip(ys,ys[1:]))
        transitions+=len(ys)-1
    fail_unless(all(counts.values()),"TRAIN_MISSING_CUE")
    def clamp(x):
        return max(.0001,min(.4999,x))
    params={"hazard":clamp(flips/transitions),
            "noise_positive":clamp(mismatch[1]/counts[1]),
            "noise_negative":clamp(mismatch[-1]/counts[-1])}
    return params,{"train_cpu_seconds":time.process_time()-start,
                   "python_peak_bytes":0,"epochs":1,"restarts":1}


def fit(kind,train,dev,config):
    widths={
      "SURPRISE_RELIABILITY_WRITE":5,
      "TRAINED_TANH_RNN":6,
      "TRAINED_DECAYED_CUE_COUNT":3,
      "TRAINED_CURRENT_CUE":3,
    }
    width=widths[kind]
    best=None
    attempts=[]
    totalcpu=0.
    peak=0
    for restart in config["restarts"]:
        r=random.Random(make_seed("q16","init",kind,restart))
        par=[r.uniform(-.35,.35) for _ in range(width)]
        # Symmetric low-norm parameter starts; no generator or DEV or model oracle.
        m=[0.]*width
        v=[0.]*width
        it=0
        start=time.process_time()
        tracemalloc.start()
        for epoch in range(config["epochs"]):
            indices=list(range(len(train)))
            r.shuffle(indices)
            for begin in range(0,len(indices),config["train_minibatch_episodes"]):
                batch=[train[i] for i in indices[
                    begin:begin+config["train_minibatch_episodes"]]]
                grad=[]
                for i in range(width):
                    plus=par.copy(); minus=par.copy()
                    plus[i]+=config["fd_delta"]
                    minus[i]-=config["fd_delta"]
                    lp=sum(loss(kind,plus,ep) for ep in batch)/len(batch)
                    lm=sum(loss(kind,minus,ep) for ep in batch)/len(batch)
                    grad.append((lp-lm)/(2*config["fd_delta"]))
                norm=math.sqrt(sum(x*x for x in grad))
                if norm>config["grad_clip"]:
                    grad=[x*config["grad_clip"]/norm for x in grad]
                it+=1
                for i,g in enumerate(grad):
                    m[i]=.9*m[i]+.1*g
                    v[i]=.999*v[i]+.001*g*g
                    par[i]-=config["lr"]*(m[i]/(1-.9**it))/(
                        math.sqrt(v[i]/(1-.999**it))+1e-8)
                fail_unless(all(math.isfinite(x) for x in par),
                            "NONFINITE_OPTIMIZATION")
        thispeak=tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        totalcpu+=time.process_time()-start
        peak=max(peak,thispeak)
        score=evaluate(kind,par,dev)
        attempts.append({"restart":restart,"dev_nll":score["mean"]})
        if best is None or score["mean"]<best["score"]["mean"]:
            best={"params":par[:],"score":score,"restart":restart}
    return best["params"],best["score"],{
        "train_cpu_seconds":totalcpu,
        "python_peak_bytes":peak,
        "selected_restart":best["restart"],
        "restarts":attempts,
        "epochs":config["epochs"]}


def selftest():
    p=load()
    q=p["generator"]
    fail_unless(all(f["name"] in FAMILIES for f in q["family_algorithms"]),
                "BAD_SOURCE_FAMILIES")
    fail_unless(make_seed("q16","v1","train","E_regime",0)!=
                make_seed("q16","v1","dev","E_regime",0),
                "COHORT_SEED_COLLISION")
    for f in q["family_algorithms"]:
        if f["name"]=="E_regime":
            ep=data_for("train",f)
            fail_unless(len(ep)==48 and len(ep[0][1])==16,
                        "E_DATA_SHAPE")
        else:
            ep=data_for("dev",f)
            fail_unless(len(ep)==24 and len(ep[0][1])==20,
                        "F_DATA_SHAPE")
    for bad in ("G_reversed","H_delayed"):
        try:
            data_for("train",{"name":bad,"steps":16,
                       "train_episodes":1,"validation_episodes":1})
        except ValueError as exc:
            fail_unless("ORIGINAL_OR_HELD_FORBIDDEN" in str(exc),
                        "FUTURE_FIRST_USE_NOT_PROTECTED")
        else:
            raise RuntimeError("Q16_HELD_GENERATED")
    test=("E_regime",(1,-1),(1,-1),(1,0))
    for k,par in [
        ("SURPRISE_RELIABILITY_WRITE",[.2,.3,.4,.5,.1]),
        ("TRAINED_TANH_RNN",[.2,.3,.4,.5,.6,.1]),
        ("TRAINED_CUE_BAYES",[]),
        ("TRAINED_DECAYED_CUE_COUNT",[.2,.3,.1]),
        ("TRAINED_CURRENT_CUE",[.2,.3,.1])
    ]:
        score=loss(k,par,test,{"hazard":.1,"noise_positive":.1,
                                "noise_negative":.4})
        fail_unless(math.isfinite(score),"LOSS_NAN")
    print("Q16_SELFTEST_SOURCE_FREE_ROLE_AND_MODEL=PASS")


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--mode",required=True,choices=("selftest","train-dev"))
    mode=arg.parse_args().mode
    p=load()
    selftest()
    if mode=="selftest":
        return
    spec=p["generator"]["family_algorithms"]
    train=[x for f in spec for x in data_for("train",f)]
    dev=[x for f in spec for x in data_for("dev",f)]
    fail_unless(len(train)==96 and len(dev)==48,"DATASET_CARDINALITY")
    results={}
    costs={}
    snapshots={}
    for kind in KINDS:
        if kind=="TRAINED_CUE_BAYES":
            par,cost=fit_bayes(train)
            score=evaluate(kind,[],dev,par)
        else:
            par,score,cost=fit(kind,train,dev,p["optimizer"])
        start=time.process_time()
        repeat=evaluate(kind,par if isinstance(par,list) else [],
                        dev,par if kind=="TRAINED_CUE_BAYES" else None)
        cost["dev_inference_cpu_seconds"]=time.process_time()-start
        fail_unless(abs(repeat["mean"]-score["mean"])<=1e-12,
                    "DUPLICATE_SCORING_DRIFT")
        state=0 if kind=="TRAINED_CURRENT_CUE" else 1
        score["state_scalars"]=state
        score["trainable_params"]=len(par) if isinstance(par,list) else len(par)
        score["checkpoint_bytes"]=len(json.dumps(par,sort_keys=True).encode())
        results[kind]=score
        costs[kind]=cost
        snapshots[kind]=sha(json.dumps(par,sort_keys=True).encode())
        print("Q16_DEV_MODEL="+kind+" NLL="+format(score["mean"],".9f"),
              flush=True)
    candidate="SURPRISE_RELIABILITY_WRITE"
    others=[k for k in KINDS if k!=candidate]
    champion=min(others,key=lambda k:results[k]["mean"])
    delta=results[champion]["mean"]-results[candidate]["mean"]
    family={f:results[champion]["by_family"][f]-
            results[candidate]["by_family"][f] for f in FAMILIES}
    cpu1=sum(costs[candidate][k] for k in
             ("train_cpu_seconds","dev_inference_cpu_seconds"))
    cpu2=sum(costs["TRAINED_TANH_RNN"][k] for k in
             ("train_cpu_seconds","dev_inference_cpu_seconds"))
    gate=p["decision"]
    checks={
        "gain_over_best_conventional":delta>=gate[
            "candidate_must_gain_nats_vs_best_conventional"],
        "positive_both_independent_dev_families":all(z>0 for z in family.values()),
        "matched_online_state":results[candidate]["state_scalars"]<=
            results["TRAINED_TANH_RNN"]["state_scalars"],
        "cpu_leq_1_10_times_rnn":cpu1<=gate[
            "candidate_train_infer_cpu_leq_rnn_ratio"]*cpu2,
    }
    verdict=gate["advance_if_all"] if all(checks.values()) else gate["otherwise"]
    payload={
        "schema":"forge.nci04.q16.train-dev-result.v1",
        "frozen_protocol_blob":PIN,
        "train_count":len(train),"dev_count":len(dev),
        "train_sha256":digest(train),"dev_sha256":digest(dev),
        "models":results,"costs":costs,
        "checkpoint_sha256":snapshots,
        "best_control":champion,
        "candidate_gain_nats":delta,
        "candidate_gain_by_family":family,
        "frozen_gate_checks":checks,
        "verdict":verdict,
        "held_G_H_generated":False,
        "original_source_episodes":0,
        "scientific_first_use":False,
    }
    print("Q16_RESULT_JSON="+json.dumps(payload,sort_keys=True,
                                separators=(",",":"),allow_nan=False),flush=True)
    print("Q16_DEV_VERDICT="+verdict,flush=True)
    print("Q16_UNFAMILIAR_G_H=NOT_GENERATED",flush=True)
    print("Q16_ORIGINAL_CKB_MINIGRID_PYCOLAB=UNTOUCHED",flush=True)


if __name__=="__main__":
    main()

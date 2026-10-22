"""Q17B — supervised causal-edge composition from source-free interventions.

Synthetic FIT and development only. Model inference sees 32 public events,
never latent edge identities, source family, truth label or generator seed.
No original-engine import, protected scientific source or outside services.
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

BASE = Path(__file__).resolve().parent
PROTO_BLOB = "7b09596afb9a3e2859f2de20e470c91416d94578"
N = 16
KINDS = ("LEARNED_FACTORIZED_CAUSAL_EDGES","TRAINED_FLAT_INTERACTION",
         "TRAINED_TWO_STATE_TANH_RNN","TRAINED_SYMBOLIC_TWO_THRESHOLD_AND",
         "ORACLE_BAYES_TWO_EDGE_POSTERIOR")
EPS=1e-12


def must(ok, name):
    if not ok:
        raise RuntimeError("Q17B_" + name)


def sha(s):
    return hashlib.sha256(s).hexdigest()


def frozen():
    data=(BASE/"FROZEN_PROTOCOL.json").read_bytes()
    blob=hashlib.sha1(
        b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()
    must(blob==PROTO_BLOB,"FROZEN_PRE_EXECUTION_BLOB_DRIFT")
    doc=json.loads(data)
    must(doc["schema"]=="forge.nci04.q17b.learned_twoedge_composition.v1",
         "FROZEN_SCHEMA_DRIFT")
    must(doc["training"]["epochs"]==24 and
         doc["training"]["restarts"]==[0,1],"TRAINING_POLICY_DRIFT")
    must(doc["cohorts"]["fit"]["total_episodes"]==256 and
         doc["cohorts"]["development"]["total_episodes"]==64,
         "COHORT_COUNTS_DRIFT")
    return doc


def seeded(*parts):
    key=":".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8],"big")


def episodes(role,doc):
    must(role in ("fit","development"),"HELD_OR_REAL_SOURCE_UNAUTHORIZED")
    count=doc["cohorts"][role]["episodes_per_structure"]
    must((role=="fit" and count==64) or
         (role=="development" and count==16),"COHORT_SIZE_UNFROZEN")
    result=[]
    for index_structure in range(4):
        truth=(index_structure>>1)&1 and index_structure&1
        for episode_index in range(count):
            rng=random.Random(seeded("q17b-v1",role,index_structure,
                                     episode_index))
            events=[]
            for edge in (0,1):
                present=(index_structure>>(1-edge))&1
                for _ in range(N):
                    action=rng.randrange(2)
                    match=int(rng.random() <
                              (0.8 if present else 0.5))
                    outcome=action if match else 1-action
                    events.append((edge,action,outcome))
            result.append((tuple(events),int(truth)))
    must(len(result)==count*4,"EPISODE_COUNT_INVALID")
    return result


def cohort_sha(rows):
    return sha(json.dumps(rows,separators=(",",":"),sort_keys=True).encode())


def sigmoid(v):
    if v>=0:
        return 1/(1+math.exp(-v))
    t=math.exp(v)
    return t/(1+t)


def counts(events):
    count=[0,0]
    for edge, action, outcome in events:
        must(edge in (0,1) and action in (0,1) and outcome in (0,1),
             "UNAUTHENTICATED_EVENT")
        count[edge]+=int(action==outcome)
    must(len(events)==32,"INTERVENTION_BUDGET_INVALID")
    return count


def probability(kind,params,events):
    if kind=="LEARNED_FACTORIZED_CAUSAL_EDGES":
        k1,k2=counts(events)
        x1=(2*k1-N)/N
        x2=(2*k2-N)/N
        return sigmoid(params[0]*x1+params[1])*sigmoid(
            params[2]*x2+params[3])
    if kind=="TRAINED_FLAT_INTERACTION":
        k1,k2=counts(events)
        a=(2*k1-N)/N
        b=(2*k2-N)/N
        return sigmoid(params[0]+params[1]*a+params[2]*b+
                       params[3]*a*b)
    if kind=="TRAINED_TWO_STATE_TANH_RNN":
        h=[0.0,0.0]
        for edge,action,outcome in events:
            success=(2*int(action==outcome)-1)
            # Shared decay a, independent public-edge weights and biases.
            h[edge]=math.tanh(params[0]*h[edge]+
                              params[1+edge]*success+
                              params[3+edge])
        return sigmoid(params[5]*h[0]+params[6]*h[1]+
                       params[7]*h[0]*h[1]+params[8])
    if kind=="ORACLE_BAYES_TWO_EDGE_POSTERIOR":
        k1,k2=counts(events)
        def edge_p(k):
            likelihood_present=(.8**k)*(.2**(N-k))
            likelihood_absent=.5**N
            return likelihood_present/(likelihood_present+likelihood_absent)
        return edge_p(k1)*edge_p(k2)
    if kind=="TRAINED_SYMBOLIC_TWO_THRESHOLD_AND":
        k1,k2=counts(events)
        positive=(k1>=params["threshold_a"] and
                  k2>=params["threshold_b"])
        return params["p_true"] if positive else params["p_false"]
    raise RuntimeError("Q17B_UNKNOWN_MODEL")


def bce(p,y):
    p=max(EPS,min(1-EPS,p))
    return -y*math.log(p)-(1-y)*math.log1p(-p)


def average_loss(kind,params,data):
    return sum(bce(probability(kind,params,ep),y)
               for ep,y in data)/len(data)


def train_gradient(kind,fit,dev,policy):
    dims={"LEARNED_FACTORIZED_CAUSAL_EDGES":4,
          "TRAINED_FLAT_INTERACTION":4,
          "TRAINED_TWO_STATE_TANH_RNN":9}
    d=dims[kind]
    best=None
    records=[]
    total_cpu=0.
    peak=0
    for restart in policy["restarts"]:
        rnd=random.Random(seeded("q17b-init",kind,restart))
        par=[rnd.uniform(-.4,.4) for _ in range(d)]
        mom=[0.]*d; var=[0.]*d
        tic=time.process_time()
        tracemalloc.start()
        iteration=0
        for _ in range(policy["epochs"]):
            order=list(range(len(fit)))
            rnd.shuffle(order)
            for offset in range(0,len(order),policy["batch_episodes"]):
                batch=[fit[i] for i in order[
                    offset:offset+policy["batch_episodes"]]]
                grad=[]
                for i in range(d):
                    p1=par.copy(); p2=par.copy()
                    p1[i]+=policy["finite_difference_epsilon"]
                    p2[i]-=policy["finite_difference_epsilon"]
                    grad.append((average_loss(kind,p1,batch)-
                                 average_loss(kind,p2,batch))/
                                (2*policy["finite_difference_epsilon"]))
                norm=math.sqrt(sum(x*x for x in grad))
                if norm>policy["clip_grad_norm"]:
                    grad=[x*policy["clip_grad_norm"]/norm for x in grad]
                iteration+=1
                for i,g in enumerate(grad):
                    mom[i]=.9*mom[i]+.1*g
                    var[i]=.999*var[i]+.001*g*g
                    par[i]-=policy["adam_lr"] * (
                        mom[i]/(1-.9**iteration))/(
                        math.sqrt(var[i]/(1-.999**iteration))+1e-8)
                must(all(math.isfinite(x) for x in par),"NONFINITE_FIT")
        _,thispeak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        total_cpu+=time.process_time()-tic
        peak=max(peak,thispeak)
        score=average_loss(kind,par,dev)
        records.append({"restart":restart,"dev_loss":score})
        if best is None or score<best[0]:
            best=(score,par[:],restart)
    return best[1],{"fit_cpu_seconds":total_cpu,"python_peak_bytes":peak,
                    "selected_restart":best[2],"restarts":records,
                    "epochs":policy["epochs"]}


def train_symbolic(fit):
    tic=time.process_time()
    best=None
    # All 17^2 public integer-count policies; FIT-only calibration.
    scored=[(counts(ep),y) for ep,y in fit]
    for t_a in range(N+1):
        for t_b in range(N+1):
            a1,a0,b1,b0=0,0,0,0
            for (ka,kb),y in scored:
                flag=(ka>=t_a and kb>=t_b)
                if flag:
                    a1+=y; b1+=1
                else:
                    a0+=y; b0+=1
            p1=(a1+1)/(b1+2); p0=(a0+1)/(b0+2)
            params={"threshold_a":t_a,"threshold_b":t_b,
                    "p_true":p1,"p_false":p0}
            score=average_loss("TRAINED_SYMBOLIC_TWO_THRESHOLD_AND",
                               params,fit)
            if best is None or score<best[0]:
                best=(score,params)
    return best[1],{"fit_cpu_seconds":time.process_time()-tic,
                    "python_peak_bytes":0,"grid_candidates":(N+1)**2}


def eval_report(kind,params,dev):
    tic=time.process_time()
    vals=[bce(probability(kind,params,ev),y) for ev,y in dev]
    cpu=time.process_time()-tic
    by_structure={}
    for index in range(4):
        offset=index*16
        by_structure[str(index)]=sum(vals[offset:offset+16])/16
    predictions=[probability(kind,params,ev)>=.5 for ev,_ in dev]
    correct=sum(int(pred==bool(y)) for pred,(_,y) in zip(predictions,dev))
    hard_false_positive=sum(int(pred and not y)
                            for pred,(_,y) in zip(predictions,dev))
    return {"nll":sum(vals)/len(vals),"accuracy":correct/len(vals),
            "hard_false_positives":hard_false_positive,
            "nll_by_structure":by_structure,
            "inference_cpu_seconds":cpu,
            "checkpoint_bytes":len(json.dumps(params,sort_keys=True).encode())}


def selftest(doc):
    f=episodes("fit",doc); d=episodes("development",doc)
    must(len(f)==256 and len(d)==64,"SELFTEST_COUNTS")
    must(cohort_sha(f)!=cohort_sha(d),"FIT_DEV_DATA_IDENTITY_COLLISION")
    for index in range(4):
        must(sum(y for _,y in f[index*64:(index+1)*64])==
             (64 if index==3 else 0),"COMPOSITION_LABEL_INVALID")
    for kind,params in [
        ("LEARNED_FACTORIZED_CAUSAL_EDGES",[1.,0.,1.,0.]),
        ("TRAINED_FLAT_INTERACTION",[0.,1.,1.,1.]),
        ("TRAINED_TWO_STATE_TANH_RNN",[.2,.3,.3,0.,0.,1.,1.,.5,0.]),
        ("TRAINED_SYMBOLIC_TWO_THRESHOLD_AND",
         {"threshold_a":10,"threshold_b":10,"p_true":.9,"p_false":.1}),
        ("ORACLE_BAYES_TWO_EDGE_POSTERIOR",None),
    ]:
        p=probability(kind,params,f[0][0])
        must(0<p<1 and math.isfinite(p),"MODEL_FINITENESS")
    try:
        episodes("held",doc)
    except RuntimeError as error:
        must("HELD_OR_REAL_SOURCE_UNAUTHORIZED" in str(error),
             "HELD_BLOCK_FAILED")
    else:
        raise RuntimeError("Q17B_HELD_DATA_GENERATED")
    print("Q17B_FROZEN_SOURCEFREE_AND_HELD_BLOCK_SELFTEST=PASS")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("selftest","train-dev"),
                        required=True)
    mode=parser.parse_args().mode
    doc=frozen()
    selftest(doc)
    if mode=="selftest":
        return
    fit=episodes("fit",doc)
    dev=episodes("development",doc)
    result={}
    costs={}
    checkpoint={}
    for kind in KINDS:
        if kind=="ORACLE_BAYES_TWO_EDGE_POSTERIOR":
            params=None
            cost={"fit_cpu_seconds":0.0,
                  "python_peak_bytes":0,
                  "privileged_generator_parameter_access":True}
        elif kind=="TRAINED_SYMBOLIC_TWO_THRESHOLD_AND":
            params,cost=train_symbolic(fit)
        else:
            params,cost=train_gradient(kind,fit,dev,doc["training"])
        score=eval_report(kind,params,dev)
        score["online_state_scalars"]=2
        score["parameter_count"]=len(params) if params is not None else 0
        result[kind]=score
        costs[kind]=cost
        checkpoint[kind]=sha(json.dumps(params,sort_keys=True).encode())
        print("Q17B_DEV_MODEL="+kind+
              " NLL="+format(score["nll"],".9f"),flush=True)
    candidate=result[KINDS[0]]
    checks={
      "near_privileged_bayes":candidate["nll"] <=
          result["ORACLE_BAYES_TWO_EDGE_POSTERIOR"]["nll"]+.015,
      "gain_over_flat":candidate["nll"] <=
          result["TRAINED_FLAT_INTERACTION"]["nll"]-.010,
      "gain_over_rnn":candidate["nll"] <=
          result["TRAINED_TWO_STATE_TANH_RNN"]["nll"]-.010,
      "gain_over_symbolic":candidate["nll"] <=
          result["TRAINED_SYMBOLIC_TWO_THRESHOLD_AND"]["nll"]-.010,
      "cpu_leq_rnn_1_10":(costs[KINDS[0]]["fit_cpu_seconds"]+
          candidate["inference_cpu_seconds"])<=1.10*(
          costs["TRAINED_TWO_STATE_TANH_RNN"]["fit_cpu_seconds"]+
          result["TRAINED_TWO_STATE_TANH_RNN"]["inference_cpu_seconds"]),
      "two_scalar_state":candidate["online_state_scalars"]<=2
    }
    verdict=("DEV_ONLY_COMPOSITION_REPRESENTATION_CANDIDATE_NOT_TRANSFER"
             if all(checks.values()) else
             "DEV_NO_GO_RETAIN_NEGATIVE_NO_HELD")
    report={
       "schema":"forge.nci04.q17b.sourcefree-fit-dev-result.v1",
       "frozen_protocol_git_blob":PROTO_BLOB,
       "fit_count":len(fit),"dev_count":len(dev),
       "fit_sha256":cohort_sha(fit),"dev_sha256":cohort_sha(dev),
       "model_scores":result,"training_costs":costs,
       "checkpoint_sha256":checkpoint,
       "gate_checks":checks,"verdict":verdict,
       "original_scientific_source_episodes":0,
       "hidden_edge_labels_available_at_inference":False,
       "oracle_has_privileged_known_law":True,
       "unfamiliar_held_generated":False,
       "scientific_first_use":False
    }
    print("Q17B_RESULT_JSON="+json.dumps(
        report,sort_keys=True,separators=(",",":"),allow_nan=False),
        flush=True)
    print("Q17B_DEV_VERDICT="+verdict,flush=True)
    print("Q17B_HELD_ORIGINAL_AND_CKB=NOT_TOUCHED",flush=True)


if __name__=="__main__":
    main()

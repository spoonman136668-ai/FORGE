"""Q20: unlabeled online next-observation learning from public interventions.

No latent z, responsive sensor slot, world graph or outcome target is used for
any empirical FIT. The privileged oracle consumes secret metadata in its own
evaluation path only. Original scientific sources / protected held are absent.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random, time, tracemalloc
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BLOB="b517e5fc03680bdd04ec357e6d84ebdf3cb3b4c8"
CAND="EXCHANGEABLE_ACTION_PREDICTIVE_STATE"
RNN="TRAINED_TWO_CELL_ACTION_RNN"
FLAT="TRAINED_ACTION_FLAT_LOGISTIC"
SYM="TRAINED_ACTION_BIGRAM"
HMM="TRAINED_UNSUPERVISED_TWO_STATE_HMM"
ORACLE="TRUE_LAW_ORACLE_FILTER"
NAMES=(CAND,RNN,FLAT,SYM,HMM,ORACLE)
ROLES=("fit","dev")
EPS=1e-9

def need(ok,message):
    if not ok:raise RuntimeError("Q20_"+message)

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()

def initial_seed(*parts):
    return int.from_bytes(hashlib.sha256(":".join(
        str(z) for z in parts).encode()).digest()[:8],"big")

def protocol():
    raw=(ROOT/"FROZEN_PROTOCOL.json").read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    need(blob==BLOB,"FROZEN_PREEXECUTION_PROTOCOL_DRIFT")
    d=json.loads(raw)
    need(d["schema"]=="forge.nci04.q20.unlabeled_action_predictive_state.v1",
         "SCHEMA_IDENTITY_DRIFT")
    need(d["training"]["epochs"]==14 and d["training"]["restarts"]==[0,1],
         "MODEL_TRAINING_POLICY_CHANGED")
    need(d["training"]["hmm_em_epochs"]==12
         and d["training"]["hmm_restarts"]==[0,1,2],
         "EM_POLICY_CHANGED")
    return d

def fraction(value):
    n,den=value.split("/")
    return int(n)/int(den)

def generate(role,doc):
    need(role in ROLES,"UNKNOWN_OR_HELD_ROLE_FORBIDDEN")
    families=doc["synthetic_source"]["cohorts_fit"] if role=="fit" else (
        doc["synthetic_source"]["cohorts_dev"])
    allowed=("FIT_L1","FIT_L2") if role=="fit" else ("DEV_L3","DEV_L4")
    need(tuple(f["name"] for f in families)==allowed,
         "FROZEN_FAMILY_ID_CHANGED")
    public=[]
    secrets=[]
    for family in families:
        noise=fraction(family["noise"])
        flip0=fraction(family["flip0"])
        flip1=fraction(family["flip1"])
        for index in range(family["episodes"]):
            rng=random.Random(initial_seed("q20","v1",role,family["name"],index))
            responsive=rng.randrange(2)
            latent=rng.randrange(2)
            observations=[]
            actions=[]
            for t in range(13):
                responsive_value=latent^int(rng.random()<noise)
                decoy=rng.randrange(2)
                observation=(responsive_value,decoy) if responsive==0 else (
                    decoy,responsive_value)
                observations.append(observation)
                if t<12:
                    action=rng.randrange(2)
                    actions.append(action)
                    latent^=int(rng.random()<(flip1 if action else flip0))
            public.append((family["name"],tuple(observations),tuple(actions)))
            secrets.append((responsive,noise,flip0,flip1))
    need(len(public)==(192 if role=="fit" else 64),"DATASET_COUNT_CHANGED")
    return public,secrets

def sigmoid(z):
    if z>=0:return 1/(1+math.exp(-z))
    x=math.exp(z)
    return x/(1+x)

def bitloss(p,y):
    p=min(1-EPS,max(EPS,p))
    return -y*math.log(p)-(1-y)*math.log1p(-p)

def sym_id(x):
    return (x[0]<<1)|x[1]

def model_predictions(kind,params,row):
    _,obs,actions=row
    out=[]
    h=[0.,0.]
    if kind==HMM:
        prior=params["prior"]
        em=params["emission"]
        transition=params["transition"]
        first=sym_id(obs[0])
        alpha=[prior[0]*em[0][first],prior[1]*em[1][first]]
        norm=sum(alpha)
        alpha=[x/norm for x in alpha]
    for t,action in enumerate(actions):
        sx=[2*obs[t][0]-1,2*obs[t][1]-1]
        sa=2*action-1
        if kind==CAND:
            old=h[:]
            for i in (0,1):
                h[i]=math.tanh(params[0]*old[i]+params[1]*old[1-i]+
                    params[2]*sx[i]+params[3]*sx[1-i]+
                    params[4]*sa+params[5]*sa*old[i]+params[6])
            pred=(sigmoid(params[7]*h[0]+params[8]),
                  sigmoid(params[7]*h[1]+params[8]))
        elif kind==RNN:
            old=h[:]
            h[0]=math.tanh(params[0]*old[0]+params[1]*old[1]+
                  params[4]*sx[0]+params[5]*sx[1]+params[8]*sa+params[10])
            h[1]=math.tanh(params[2]*old[0]+params[3]*old[1]+
                  params[6]*sx[0]+params[7]*sx[1]+params[9]*sa+params[11])
            pred=(sigmoid(params[12]*h[0]+params[13]),
                  sigmoid(params[14]*h[1]+params[15]))
        elif kind==FLAT:
            f=(1.,sx[0],sx[1],sa,sx[0]*sa,sx[1]*sa)
            pred=tuple(sigmoid(sum(a*b for a,b in zip(
                params[6*i:6*i+6],f))) for i in (0,1))
        elif kind==SYM:
            next_probs=params[action][sym_id(obs[t])]
            pred=(next_probs[2]+next_probs[3],
                  next_probs[1]+next_probs[3])
        elif kind==HMM:
            pr=[sum(alpha[i]*transition[action][i][j] for i in (0,1))
                for j in (0,1)]
            probs=[sum(pr[j]*em[j][k] for j in (0,1))
                   for k in range(4)]
            pred=(probs[2]+probs[3],probs[1]+probs[3])
            now=sym_id(obs[t+1])
            alpha=[pr[j]*em[j][now] for j in (0,1)]
            norm=sum(alpha)
            need(norm>0,"HMM_PREDICTION_NORMALIZER_ZERO")
            alpha=[x/norm for x in alpha]
        else:
            raise RuntimeError("Q20_UNKNOWN_EMPIRICAL_MODEL")
        out.append(pred)
    return out

def empirical_loss(kind,params,episodes):
    total=0.
    for row in episodes:
        forecasts=model_predictions(kind,params,row)
        for t,ps in enumerate(forecasts):
            for j in (0,1):
                total+=bitloss(ps[j],row[1][t+1][j])
    return total/(24*len(episodes))

def train_gradient(kind,fit,dev,config):
    width={CAND:9,RNN:16,FLAT:12}[kind]
    best=None
    logs=[]
    total_cpu=0.
    peak=0
    for restart in config["restarts"]:
        rng=random.Random(initial_seed("q20-init",kind,restart))
        p=[rng.uniform(-.3,.3) for _ in range(width)]
        m=[0.]*width;v=[0.]*width
        begin=time.process_time()
        tracemalloc.start()
        for iteration in range(1,config["epochs"]+1):
            gradient=[]
            for i in range(width):
                hi=p.copy();lo=p.copy()
                hi[i]+=config["grad_delta"]
                lo[i]-=config["grad_delta"]
                gradient.append((empirical_loss(kind,hi,fit)-
                      empirical_loss(kind,lo,fit))/(2*config["grad_delta"]))
            norm=math.sqrt(sum(x*x for x in gradient))
            if norm>config["clip_norm"]:
                gradient=[x*config["clip_norm"]/norm for x in gradient]
            for i,g in enumerate(gradient):
                m[i]=.9*m[i]+.1*g
                v[i]=.999*v[i]+.001*g*g
                p[i]-=config["lr"]*(m[i]/(1-.9**iteration))/(
                    math.sqrt(v[i]/(1-.999**iteration))+1e-8)
            need(all(math.isfinite(x) for x in p),"NONFINITE_TRAINED_WEIGHT")
        peak=max(peak,tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        total_cpu+=time.process_time()-begin
        val=empirical_loss(kind,p,dev)
        logs.append({"restart":restart,"dev_nll":val})
        if best is None or val<best[0]:
            best=(val,p[:],restart)
    return best[1],{"train_cpu_seconds":total_cpu,
                    "python_tracemalloc_peak_bytes":peak,
                    "restarts":logs,"selected_restart":best[2]}

def train_symbolic(fit):
    start=time.process_time()
    # Dirichlet(1/2) for all action/current joint sensor state to next state
    tables=[[[.5]*4 for _ in range(4)] for _ in range(2)]
    for _,obs,actions in fit:
        for t,a in enumerate(actions):
            tables[a][sym_id(obs[t])][sym_id(obs[t+1])]+=1
    out=[[tuple(x/sum(row) for x in row) for row in block]
         for block in tables]
    return out,{"train_cpu_seconds":time.process_time()-start,
                "python_tracemalloc_peak_bytes":0,
                "calibrated_action_state_contexts":8}

def hmm_init(restart):
    r=random.Random(initial_seed("q20-hmm-init",restart))
    p=r.uniform(.35,.65)
    a=[]
    for _action in (0,1):
        aa=[]
        for _state in (0,1):
            x=r.uniform(.25,.75)
            aa.append([x,1-x])
        a.append(aa)
    e=[]
    for _ in (0,1):
        x=[r.uniform(.2,1.0) for k in range(4)]
        e.append([z/sum(x) for z in x])
    return {"prior":[p,1-p],"transition":a,"emission":e}

def forward_backward(model,obs,actions):
    symbols=[sym_id(v) for v in obs]
    transition=model["transition"]; emission=model["emission"]
    alpha=[];scales=[]
    first=[model["prior"][j]*emission[j][symbols[0]] for j in (0,1)]
    sc=sum(first);need(sc>0,"HMM_FORWARD_ZERO")
    alpha.append([v/sc for v in first]);scales.append(sc)
    for t,a in enumerate(actions):
        nxt=[sum(alpha[t][i]*transition[a][i][j] for i in (0,1))*
             emission[j][symbols[t+1]] for j in (0,1)]
        sc=sum(nxt);need(sc>0,"HMM_FORWARD_NORM_ZERO")
        alpha.append([v/sc for v in nxt]);scales.append(sc)
    beta=[[1.,1.] for _ in range(len(obs))]
    for t in range(len(actions)-1,-1,-1):
        a=actions[t]
        beta[t]=[sum(transition[a][i][j]*
                     emission[j][symbols[t+1]]*beta[t+1][j]
                     for j in (0,1))/scales[t+1] for i in (0,1)]
    gamma=[]
    for t in range(len(obs)):
        g=[alpha[t][j]*beta[t][j] for j in (0,1)]
        denom=sum(g)
        gamma.append([x/denom for x in g])
    return gamma,alpha,beta,scales,symbols

def hmm_em_step(model,episodes,smooth):
    pi=[smooth,smooth]
    counts=[[[smooth]*2 for _ in range(2)] for _ in range(2)]
    emis=[[smooth]*4 for _ in range(2)]
    trans=model["transition"]
    emission=model["emission"]
    for _,obs,actions in episodes:
        gam,alph,bet,scales,syms=forward_backward(model,obs,actions)
        for j in (0,1):
            pi[j]+=gam[0][j]
        for t,symbol in enumerate(syms):
            for j in (0,1):
                emis[j][symbol]+=gam[t][j]
        for t,action in enumerate(actions):
            vals=[[alph[t][i]*trans[action][i][j]*
                   emission[j][syms[t+1]]*bet[t+1][j]
                   for j in (0,1)] for i in (0,1)]
            den=sum(sum(row) for row in vals)
            for i in (0,1):
                for j in (0,1):
                    counts[action][i][j]+=vals[i][j]/den
    def normalized(xs):
        total=sum(xs)
        return [z/total for z in xs]
    return {"prior":normalized(pi),
            "transition":[[normalized(row) for row in block] for block in counts],
            "emission":[normalized(row) for row in emis]}

def fit_hmm(fit,dev,config):
    start=time.process_time()
    peak=0
    attempts=[]
    best=None
    tracemalloc.start()
    for restart in config["hmm_restarts"]:
        model=hmm_init(restart)
        for _ in range(config["hmm_em_epochs"]):
            model=hmm_em_step(model,fit,
                  config["hmm_emission_and_transition_pseudocount"])
        val=empirical_loss(HMM,model,dev)
        attempts.append({"restart":restart,"dev_nll":val})
        if best is None or val<best[0]:
            best=(val,model,restart)
    peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return best[1],{"train_cpu_seconds":time.process_time()-start,
                    "python_tracemalloc_peak_bytes":peak,
                    "restarts":attempts,"selected_restart":best[2]}

def privileged_oracle_forecasts(row,secret):
    """True world and sensor slot ONLY for labeled privileged upper-bound."""
    _,obs,actions=row
    responsive,noise,f0,f1=secret
    state=.5
    def observed_update(prior,x):
        likely=1-noise if x==1 else noise
        unlikely=noise if x==1 else 1-noise
        return prior*likely/(prior*likely+(1-prior)*unlikely)
    state=observed_update(.5,obs[0][responsive])
    out=[]
    for t,a in enumerate(actions):
        flip=f1 if a else f0
        prior=state*(1-flip)+(1-state)*flip
        next_prob=noise+(1-2*noise)*prior
        vals=[.5,.5];vals[responsive]=next_prob
        out.append(tuple(vals))
        state=observed_update(prior,obs[t+1][responsive])
    return out

def evaluate(kind,params,dev,priv=None):
    start=time.process_time()
    grouped={}
    false=0;right=0;total=0
    for idx,row in enumerate(dev):
        ps=(privileged_oracle_forecasts(row,priv[idx]) if kind==ORACLE
            else model_predictions(kind,params,row))
        fam=row[0]
        for t,pair in enumerate(ps):
            for j in (0,1):
                p=pair[j];y=row[1][t+1][j]
                grouped.setdefault(fam,[]).append(bitloss(p,y))
                guess=int(p>=.5)
                false+=int(guess==1 and y==0)
                right+=int(guess==y)
                total+=1
    byfam={k:sum(v)/len(v) for k,v in grouped.items()}
    return {"nll":sum(map(sum,grouped.values()))/total,
            "by_family":byfam,"accuracy":right/total,
            "hard_false_positives":false,
            "inference_cpu_seconds":time.process_time()-start,
            "trained_parameters":0 if params is None else (
                len(params) if isinstance(params,list) else 16),
            "online_state_scalars":(0 if kind in (FLAT,SYM) else 2),
            "checkpoint_bytes":len(json.dumps(params,sort_keys=True).encode())}

def selftest(doc):
    fit,secrets=generate("fit",doc)
    dev,secret_dev=generate("dev",doc)
    need(len(fit)==192 and len(dev)==64,"ROLE_COUNTS")
    need(digest(fit)!=digest(dev),"ROLE_COLLISION")
    need(len(secrets)==len(fit) and len(secret_dev)==len(dev),"SECRET_SCOPE")
    for role in ("held","HELD_NEW_SENSOR_FAMILY",
                 "HELD_LONG_HORIZON_TRANSFER","original","scientific"):
        try:generate(role,doc)
        except RuntimeError as err:
            need("UNKNOWN_OR_HELD_ROLE_FORBIDDEN" in str(err),"GUARD_FAILED")
        else:
            raise RuntimeError("Q20_HELD_FIRST_USE_INVALID")
    sample=fit[0]
    need(len(sample)==3 and len(sample[1])==13 and
         len(sample[2])==12,"NOISE_FAMILY_EXPOSED_TO_MODEL")
    for kind,params in ((CAND,[.1]*9),(RNN,[.1]*16),
                        (FLAT,[.1]*12),
                        (SYM,[[[.25]*4 for _ in range(4)] for _ in range(2)]),
                        (HMM,hmm_init(0))):
        forecasts=model_predictions(kind,params,sample)
        need(len(forecasts)==12 and all(
             len(pair)==2 and all(math.isfinite(x) and 0<x<1 for x in pair)
             for pair in forecasts),"EMPIRICAL_FORECAST_NONFINITE")
    need(len(privileged_oracle_forecasts(dev[0],secret_dev[0]))==12,
         "PRIVILEGED_ORACLE_SHAPE")
    print("Q20_UNLABELED_ROLES_HMM_AND_ALL_CONTROLS_SELFTEST=PASS",flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("selftest","train-dev"),required=True)
    mode=parser.parse_args().mode
    d=protocol()
    selftest(d)
    if mode=="selftest":return
    fit,_fit_priv=generate("fit",d)
    dev,dev_priv=generate("dev",d)
    results={};costs={};pins={}
    for name in NAMES:
        if name in (CAND,RNN,FLAT):
            params,cost=train_gradient(name,fit,dev,d["training"])
        elif name==HMM:
            params,cost=fit_hmm(fit,dev,d["training"])
        elif name==SYM:
            params,cost=train_symbolic(fit)
        else:
            params=None;cost={"train_cpu_seconds":0,
                              "privileged_true_world_state_access":True}
        score=evaluate(name,params,dev,dev_priv if name==ORACLE else None)
        results[name]=score
        costs[name]=cost
        pins[name]=hashlib.sha256(json.dumps(
            params,sort_keys=True).encode()).hexdigest()
        print("Q20_DEV_MODEL="+name+" NLL="+format(score["nll"],".9f"),
              flush=True)
    empirical=(RNN,FLAT,SYM,HMM)
    winner=min(empirical,key=lambda z:results[z]["nll"])
    improvement=results[winner]["nll"]-results[CAND]["nll"]
    byfam={f:results[winner]["by_family"][f]-
           results[CAND]["by_family"][f] for f in ("DEV_L3","DEV_L4")}
    decision=d["frozen_decision"]
    candidate_cpu=costs[CAND]["train_cpu_seconds"]+results[CAND]["inference_cpu_seconds"]
    rnn_cpu=costs[RNN]["train_cpu_seconds"]+results[RNN]["inference_cpu_seconds"]
    gate={
        "gain_vs_best_fitted_0_015":
            improvement>=decision["candidate_gain_vs_best_fitted_control_nats_min"],
        "positive_each_dev_family":all(x>0 for x in byfam.values()),
        "cpu_leq_rnn_1_10":candidate_cpu<=rnn_cpu*
            decision["candidate_cpu_fit_plus_eval_leq_rnn_ratio"],
        "two_state_scalars":results[CAND]["online_state_scalars"]<=2
    }
    verdict=decision["advance"] if all(gate.values()) else decision["fail"]
    report={
        "schema":"forge.nci04.q20.unlabeled-nextobs-result.v1",
        "protocol_git_blob":BLOB,"fit_episodes":len(fit),"dev_episodes":len(dev),
        "fit_sha256":digest(fit),"dev_sha256":digest(dev),
        "models":results,"costs":costs,
        "model_checkpoint_sha256":pins,
        "best_equally_trained_control":winner,
        "gain_over_best_fitted_nats_per_bit":improvement,
        "gain_by_dev_family":byfam,
        "frozen_gate":gate,
        "verdict":verdict,
        "supervised_hidden_labels_used":False,
        "only_public_future_observation_labels_used":True,
        "trained_hmm_is_unsupervised":True,
        "oracle_has_privileged_world_identifiers":True,
        "unfamiliar_held_family_generated":False,
        "original_scientific_source_episodes":0,
        "protected_first_use":False
    }
    print("Q20_RESULT_JSON="+json.dumps(report,sort_keys=True,
                              separators=(",",":"),allow_nan=False),flush=True)
    print("Q20_FROZEN_DEV_DECISION="+verdict,flush=True)
    print("Q20_UNFAMILIAR_HELD_AND_ORIGINAL=UNTOUCHED",flush=True)

if __name__=="__main__":
    main()

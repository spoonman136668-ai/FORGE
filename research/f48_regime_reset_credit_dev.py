#!/usr/bin/env python3
"""F48: synthetic-only, non-token delayed action credit with stable/working memory.

Source-owned action-consequence environment is not independent science or
Gymnasium. Evaluator-private hidden modes/noise never flow into policy methods.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

EFFECTS = ((1,2),(1,4),(2,4),(2,1),(4,2),(4,1))
FIT = (4104,4105,4106,4107,4110,4111,4112,4113)
TRANSFER = (4300,4301,4306,4307,4312,4313,4318,4319,
            4324,4325,4330,4331,4336,4337,4342,4343,
            4348,4349,4354,4355,4360,4361,4366,4367)
RETENTION = (4500,4501,4502,4503,4506,4507,4508,4509,
             4512,4513,4514,4515)
FORBIDDEN = (59,83)
ACTIONS = (0,1,2)
DURATION = 8
ARMS = ("stable-working-reset","fixed-hazard-bayes","markov-switch-bayes",
        "recent3-bayes","no-feedback","trained-empirical",
        "candidate-wrong-credit","candidate-no-stable","candidate-no-reset")
CONTROLS = ARMS[1:6]
NEGATIVES = ARMS[6:]
BEHAVIOR = (0,2,1,0,1,2,0,1)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def lcg(x):
    return (1664525*(int(x)&0xffffffff)+1013904223)&0xffffffff


def hamming(a,b):
    return (a ^ b).bit_count()


def task(seed,episode):
    if type(seed) is not int or type(episode) is not int or not 0<=episode<12:
        raise ValueError("F48_UNAUTHORIZED_TASK")
    state=(seed*3+episode*5+1)%8
    goal=state^(1+((seed+episode*7)%7))
    if state==goal or not (0<=goal<=7):
        raise ValueError("F48_BAD_GOAL")
    return state,goal


def exogenous(seed,episode,t):
    x=(seed*2654435761 ^ (episode+23)*2246822519
       ^ (t+31)*3266489917 ^ 0xF4801020)&0xffffffff
    x=lcg(x)
    noise=(1,2,4)[(lcg(x)>>9)%3] if x%5==0 else 0
    x=lcg(lcg(x))
    witness_flip=(x%5==0)
    return noise,witness_flip


class World:
    def __init__(self,seed,episode,*,switching=False):
        if type(seed) is not int or seed in FORBIDDEN or seed not in (*FIT,*TRANSFER,*RETENTION):
            raise ValueError("F48_FORBIDDEN_OR_UNAUTHORIZED_WORLD")
        self._seed=seed
        self._episode=episode
        self._mode0=seed%6
        self._switch=bool(switching)
        self.state,self.goal=task(seed,episode)
        self.pending=2
        self.t=0
        self.done=False

    def step(self,requested):
        if self.done or type(requested) is not int or requested not in ACTIONS:
            raise ValueError("F48_INVALID_REAL_STEP")
        mode=((self._mode0+3)%6 if self._switch and self.t in (3,4,5)
              else self._mode0)
        queued=self.pending
        effect=EFFECTS[mode][queued] if queued!=2 else 0
        noise,flip=exogenous(self._seed,self._episode,self.t)
        self.state^=effect^noise
        witness=(int(mode>=3)^int(flip)) if queued==2 else -1
        self.pending=requested
        self.t+=1
        self.done=(self.t==DURATION)
        reward=-1+(10 if self.state==self.goal else -2*hamming(self.state,self.goal)) if self.done else -1
        return self.state,witness,reward,self.done


def likelihood(mode,credited_action,effect,witness,*,sensor_applied):
    if mode not in range(6) or credited_action not in ACTIONS:
        raise ValueError("F48_BAD_HYPOTHESIS_OR_ACTION")
    expected=EFFECTS[mode][credited_action] if credited_action!=2 else 0
    residual=effect^expected
    value=0.8 if residual==0 else ((0.2/3) if residual in (1,2,4) else 0.0)
    if sensor_applied:
        if witness not in (0,1):
            raise ValueError("F48_MISSING_PUBLIC_SENSOR")
        value*=0.8 if witness==int(mode>=3) else 0.2
    elif witness!=-1:
        raise ValueError("F48_PHANTOM_PUBLIC_SENSOR")
    return value


def normalize(values):
    denom=sum(values)
    if denom<=0 or not math.isfinite(denom):
        raise ValueError("F48_IMPOSSIBLE_SOURCE_OBSERVATION")
    return [v/denom for v in values]


def fit_data():
    worlds=[]
    coverage=[0,0,0]
    for seed in FIT:
        episodes=[]
        for ep in range(12):
            world=World(seed,ep,switching=False)
            transcript=[]
            for action in BEHAVIOR:
                before,pending=world.state,world.pending
                after,witness,reward,terminal=world.step(action)
                transcript.append([before,pending,action,after,witness,reward,terminal])
                coverage[action]+=1
            episodes.append(transcript)
        worlds.append(episodes)
    if (len(worlds)!=8 or sum(len(e) for w in worlds for e in w)!=768
            or coverage!=[288,288,192]):
        raise ValueError("F48_FIT_ONLY_TRANSCRIPT_OR_ACTION_DRIFT")
    return worlds,coverage


def fit_shared(worlds):
    if len(worlds)!=8 or any(len(x)!=12 for x in worlds):
        raise ValueError("F48_INVALID_TRAINING_ONLY_WORLDS")
    counts=[1.0]*6
    empirical=[{j:0 for j in range(8)} for _ in ACTIONS]
    n=0
    for world in worlds:
        posterior=[1/6]*6
        for episode in world:
            for before,pending,requested,after,witness,reward,done in episode:
                L=[likelihood(m,pending,before^after,witness,sensor_applied=pending==2)
                   for m in range(6)]
                posterior=normalize([posterior[m]*L[m] for m in range(6)])
                empirical[pending][before^after]+=1
                n+=1
        counts=[x+p for x,p in zip(counts,posterior)]
    if n!=768:
        raise ValueError("F48_FIT_ONLY_N_DRIFT")
    prior=normalize(counts)
    if any(x<=0 for x in prior):
        raise ValueError("F48_FIT_UNSEEN_SUPPORT_ZERO")
    effects=[min(range(8),key=lambda e:(-empirical[a][e],e)) for a in ACTIONS]
    return {"prior":prior,"empirical":effects,"training_transitions":n,
            "training_worlds":len(worlds)}


def planner(s,goal,pending,probs):
    if not 0<=s<8 or not 0<=goal<8 or pending not in ACTIONS:
        raise ValueError("F48_INVALID_PUBLIC_STATE_FOR_PLAN")
    def score(action):
        return sum(p*(2*int((s^(EFFECTS[m][pending] if pending!=2 else 0)
                          ^(EFFECTS[m][action] if action!=2 else 0))==goal)
                       -hamming(s^(EFFECTS[m][pending] if pending!=2 else 0)
                                    ^(EFFECTS[m][action] if action!=2 else 0),goal))
                   for m,p in enumerate(probs))
    return max(ACTIONS,key=lambda a:(score(a),-a))


class Policy:
    def __init__(self,kind,fit):
        if kind not in ARMS:
            raise ValueError("F48_UNKNOWN_POLICY")
        self.kind=kind
        self.prior=list(fit["prior"])
        self.working=list(self.prior)
        self.stable=list(self.prior)
        self.empirical=list(fit["empirical"])
        self.history=[]
        self.streak=0
        self.resets=0
        self.stable_updates=0
        self.abstains=0
        self.decision_ns=0
        self.observations=0

    def decide(self,state,goal,pending,t):
        begin=time.perf_counter_ns()
        if t not in range(DURATION):
            raise ValueError("F48_INVALID_PUBLIC_CLOCK")
        if self.kind=="trained-empirical":
            first=self.empirical[pending]
            chosen=max(ACTIONS,key=lambda a:(-hamming(state^first^self.empirical[a],goal),-a))
        else:
            chosen=planner(state,goal,pending,self.working)
        self.decision_ns+=time.perf_counter_ns()-begin
        return int(chosen)

    def observe(self,before,pending,requested,after,witness):
        self.observations+=1
        if self.kind in ("no-feedback","trained-empirical"):
            return
        credited=requested if self.kind=="candidate-wrong-credit" else pending
        effect=before^after
        L=[likelihood(m,credited,effect,witness,sensor_applied=pending==2)
           for m in range(6)]
        if self.kind=="recent3-bayes":
            self.history=(self.history+[[pending,effect,witness]])[-3:]
            # Equivalent to the predeclared last-three likelihood product
            # over FIT prior. Abstain to fitted prior on an impossible
            # joint sequence rather than fabricate a source consequence.
            weights=list(self.prior)
            for cmd,obs,signal in self.history:
                ls=[likelihood(m,cmd,obs,signal,sensor_applied=cmd==2)
                    for m in range(6)]
                weights=[w*ls[m] for m,w in enumerate(weights)]
            if sum(weights)<=0:
                self.working=list(self.prior)
                self.abstains+=1
            else:
                self.working=normalize(weights)
            return
        if self.kind=="fixed-hazard-bayes":
            base=[.92*self.working[m]+.08*self.prior[m] for m in range(6)]
        elif self.kind=="markov-switch-bayes":
            base=[.88*self.working[m]+.12*(1-self.working[m])/5 for m in range(6)]
        else:
            is_surprising=(pending!=2 and sum(p*l for p,l in zip(self.working,L))<.12)
            if is_surprising and self.kind!="candidate-no-reset":
                self.resets+=1
                if self.kind=="candidate-no-stable":
                    self.working=list(self.prior)
                else:
                    self.working=[.5*s+.5*f for s,f in zip(self.stable,self.prior)]
                self.streak=0
            elif pending!=2 and not is_surprising:
                self.streak+=1
            else:
                self.streak=0
            base=[.98*self.working[m]+.02*self.prior[m] for m in range(6)]
        weighted=[base[m]*L[m] for m in range(6)]
        if sum(weighted)<=0 and self.kind=="candidate-wrong-credit":
            self.abstains+=1
            return
        self.working=normalize(weighted)
        if self.kind in ("stable-working-reset","candidate-no-reset") and self.streak>=2:
            self.stable=normalize([.9*s+.1*w for s,w in zip(self.stable,self.working)])
            self.stable_updates+=1

    def snapshot(self):
        return {"kind":self.kind,"posterior":self.working,"stable":self.stable,
                "resets":self.resets,"stable_updates":self.stable_updates,
                "observations":self.observations,"abstains":self.abstains,
                "streak":self.streak}


def episode(seed,ep,kind,fit):
    if type(seed) is not int or seed not in (*TRANSFER,*RETENTION):
        raise ValueError("F48_UNAUTHORIZED_EVALUATION_OR_FIRST_USE")
    world=World(seed,ep,switching=seed in TRANSFER)
    learner=Policy(kind,fit)
    goal=world.goal
    trace=[]
    for t in range(DURATION):
        before,pending=world.state,world.pending
        action=learner.decide(before,goal,pending,t)
        after,witness,reward,done=world.step(action)
        learner.observe(before,pending,action,after,witness)
        trace.append([before,pending,action,after,witness,reward,done])
    if not world.done or len(trace)!=DURATION:
        raise ValueError("F48_REAL_ACTION_BUDGET_NOT_MET")
    return {"success":world.state==goal,"return":sum(t[5] for t in trace),
            "terminal_distance":hamming(world.state,goal),"trace":trace,
            "snapshot":learner.snapshot(),"resets":learner.resets,
            "stable_updates":learner.stable_updates,
            "decision_ns":learner.decision_ns}


def assess(fit,training_hash,coverage):
    if fit["training_transitions"]!=768 or fit["training_worlds"]!=8:
        raise ValueError("F48_TRAINING_ONLY_CUSTODY_DRIFT")
    if coverage!=[288,288,192] or len(fit["prior"])!=6 or len(fit["empirical"])!=3:
        raise ValueError("F48_MODEL_OR_COVERAGE_DRIFT")
    seeds=(*FIT,*TRANSFER,*RETENTION)
    if len(set(seeds))!=44 or set(seeds)&set(FORBIDDEN):
        raise ValueError("F48_FIT_DEV_OR_FIRST_USE_COLLISION")
    if any(s%6 not in (4,5) for s in TRANSFER):
        raise ValueError("F48_TRANSFER_HIDDEN_MODE_LEAK")
    if any(s%6 not in (0,1,2,3) for s in (*FIT,*RETENTION)):
        raise ValueError("F48_FIT_RETENTION_MODE_LEAK")
    frozen=canonical(fit)
    model=json.loads(frozen)
    if canonical(model)!=frozen:
        raise ValueError("F48_COLD_MODEL_RESTORE_DRIFT")
    report={"schema":"forge.eureka.f48.delayed-credit-regime-reset-synthetic-dev.v1",
            "synthetic_only":True,"original_external_environment":False,
            "first_use_consumed":False,"scientific_accepted":False,
            "owner_eligible":False,"general_rsi_proven":False,
            "matched_whole_process_compute_proven":False,
            "fit_sha256":training_hash,"model_sha256":digest(fit),
            "train_transitions":768,"train_action_counts":coverage,
            "fit_prior":fit["prior"],"fit_empirical":fit["empirical"],
            "fit_seeds":FIT,"transfer_seeds":TRANSFER,"retention_seeds":RETENTION,
            "arms":{}}
    for kind in ARMS:
        worlds=[]
        for seed in (*TRANSFER,*RETENTION):
            eps=[]
            for ep in range(4):
                a=episode(seed,ep,kind,fit)
                b=episode(seed,ep,kind,model)
                if (canonical(a["trace"])!=canonical(b["trace"])
                    or canonical(a["snapshot"])!=canonical(b["snapshot"])
                    or a["return"]!=b["return"] or a["success"]!=b["success"]):
                    raise ValueError("F48_REAL_SYNTHETIC_COLD_WARM_PARITY_FAIL")
                eps.append({"episode":ep,"success":a["success"],"return":a["return"],
                            "steps":len(a["trace"]),
                            "reset_events":a["resets"],"stable_updates":a["stable_updates"],
                            "trace_sha256":digest(a["trace"]),
                            "policy_sha256":digest(a["snapshot"]),
                            "decision_ns":a["decision_ns"],"cold_matches":True})
            worlds.append({"seed":seed,"episodes":eps,
                           "success_count":sum(e["success"] for e in eps),
                           "mean_return":sum(e["return"] for e in eps)/4,
                           "reset_events":sum(e["reset_events"] for e in eps),
                           "stable_updates":sum(e["stable_updates"] for e in eps)})
        transfer=worlds[:24]; retention=worlds[24:]
        cost=sum(ep["decision_ns"] for w in transfer for ep in w["episodes"])
        count=sum(ep["steps"] for w in transfer for ep in w["episodes"])
        if cost<=0 or count<=0:
            raise ValueError("F48_UNMEASURED_DECISION_COST")
        report["arms"][kind]={
            "worlds":worlds,
            "transfer_success":sum(w["success_count"] for w in transfer)/96,
            "retention_success":sum(w["success_count"] for w in retention)/48,
            "transfer_return":sum(w["mean_return"] for w in transfer)/24,
            "decision_ns_per_action":cost/count,
            "reset_worlds":sum(w["reset_events"]>0 for w in transfer),
            "stable_update_worlds":sum(w["stable_updates"]>0 for w in transfer)}
    strongest=max(CONTROLS,key=lambda k:report["arms"][k]["transfer_success"])
    cand=report["arms"]["stable-working-reset"]
    best=report["arms"][strongest]
    report["strongest_conventional"]=strongest
    report["success_gain"]=cand["transfer_success"]-best["transfer_success"]
    report["return_gain"]=cand["transfer_return"]-best["transfer_return"]
    report["paired_world_wins"]=sum(a["success_count"]>b["success_count"]
                                     for a,b in zip(cand["worlds"][:24],best["worlds"][:24]))
    report["best_retention"]=max(report["arms"][x]["retention_success"] for x in CONTROLS)
    report["retention_margin"]=cand["retention_success"]-report["best_retention"]
    report["cost_ratio"]=cand["decision_ns_per_action"]/best["decision_ns_per_action"]
    report["frozen_conditions_met"]=bool(
        report["success_gain"]>=.10 and report["return_gain"]>=.75
        and report["paired_world_wins"]>=16
        and all(cand["transfer_success"]>=report["arms"][k]["transfer_success"]+.10
                for k in NEGATIVES)
        and report["retention_margin"]>=-.05
        and cand["reset_worlds"]>=8 and cand["stable_update_worlds"]>=8
        and report["cost_ratio"]<=2
        and all(len(a["worlds"])==36
                and all(len(w["episodes"])==4
                        and all(e["steps"]==DURATION and e["cold_matches"]
                                for e in w["episodes"])
                        for w in a["worlds"]) for a in report["arms"].values()))
    report["classification"]=("F48_DEV_SIGNAL_UNVERIFIED" if report["frozen_conditions_met"]
                              else "F48_DEV_NO_GO")
    report["report_sha256"]=digest(report)
    return report


def main(args=None):
    args=sys.argv[1:] if args is None else args
    if len(args)!=1:
        raise ValueError("F48_USAGE: python research/f48_regime_reset_credit_dev.py /tmp/report.json")
    dest=Path(args[0]).resolve()
    fit_worlds,coverage=fit_data()
    fit=fit_shared(fit_worlds)
    report=assess(fit,digest(fit_worlds),coverage)
    report["report_sha256"]=digest({k:v for k,v in report.items() if k!="report_sha256"})
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(canonical(report)+b"\n")
    print("F48_DELAYED_CREDIT_SYNTHETIC_DEV="+report["classification"]
          +" sha256="+report["report_sha256"])
    print("F48_FIT_TRAINING="+str(report["train_transitions"])
          +" hash="+report["fit_sha256"])
    print("F48_STRONGEST="+report["strongest_conventional"]
          +" success_gain="+str(report["success_gain"])
          +" paired_world_wins="+str(report["paired_world_wins"])
          +" return_gain="+str(report["return_gain"])
          +" resets="+str(report["arms"]["stable-working-reset"]["reset_worlds"])
          +" stable_worlds="+str(report["arms"]["stable-working-reset"]["stable_update_worlds"])
          +" cost_ratio="+str(report["cost_ratio"]))
    return report


if __name__=="__main__":
    main()

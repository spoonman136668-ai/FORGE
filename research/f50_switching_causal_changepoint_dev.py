#!/usr/bin/env python3
"""F50: prospective fresh cohorts and switch-capable conventional controls.

Only source-owned synthetic physics. Never a FORGE owner action, science first-use,
independent external environment, live intelligence or deployment signal.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time

EFFECTS = ((1,2),(1,4),(2,4),(2,1),(4,2),(4,1))
ACTIONS = (0,1,2)
FIT = (6204,6205,6206,6207,6216,6217,6218,6219)
TRANSFER = (6400,6401,6406,6407,6412,6413,6418,6419,6424,6425,6430,6431,
            6436,6437,6442,6443,6448,6449,6454,6455,6460,6461,6466,6467)
RETENTION = (6600,6601,6602,6603,6612,6613,6614,6615,6624,6625,6626,6627)
FORBIDDEN = (59,83)
BEHAVIOR = (0,2,1,0,1,2,0,1,0,2,1,0)
DURATION = 12
ARMS = ("corroborated-change","fixed-hazard-bayes","switching-hmm-bayes",
        "recent3-switch-bayes","no-feedback","trained-empirical",
        "single-surprise-reset","candidate-no-reset","candidate-wrong-credit")
CONVENTIONAL = ARMS[1:6]
ABLATIONS = ARMS[6:]
CANDIDATE = ARMS[0]
CUTOFF = 0.12
LOG_BF = math.log(8)


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


def lcg(x):
    return (1664525*(int(x)&0xffffffff)+1013904223)&0xffffffff


def hamming(a,b):
    return (a ^ b).bit_count()


def task(seed,episode):
    if type(seed) is not int or type(episode) is not int or not 0 <= episode < 12:
        raise ValueError("F50_INVALID_TASK")
    state=(seed*7+episode*3+5)%8
    goal=state^(1+((seed+episode*7)%7))
    if not (0<=goal<8) or state==goal:
        raise ValueError("F50_GOAL_INVALID")
    return state,goal


def exogenous(seed,episode,t):
    x=(seed*2654435761 ^ (episode+9)*2246822519
       ^ (t+5)*3266489917 ^ 0xF500E119)&0xffffffff
    x=lcg(x)
    noise=(1,2,4)[(lcg(x)>>11)%3] if x%5==0 else 0
    x=lcg(lcg(x))
    flip=x%5==0
    return noise,flip


class World:
    """Evaluator-private mode, switch, and exogenous state; never policy inputs."""
    def __init__(self,seed,episode,*,switching=False):
        if type(seed) is not int or seed in FORBIDDEN or seed not in (*FIT,*TRANSFER,*RETENTION):
            raise ValueError("F50_UNAUTHORIZED_SOURCE_OR_PROTECTED_SEED")
        self.seed=seed
        self.episode=episode
        self._mode=seed%6
        self._switching=bool(switching)
        self.state,self.goal=task(seed,episode)
        self.pending=2
        self.steps=0
        self.done=False

    def step(self,requested):
        if self.done or type(requested) is not int or requested not in ACTIONS:
            raise ValueError("F50_INVALID_OR_EXTRA_PHYSICAL_ACTION")
        t=self.steps
        actual_mode=((self._mode+3)%6 if self._switching and t in (5,6,7,8)
                     else self._mode)
        pending=self.pending
        true_effect=EFFECTS[actual_mode][pending] if pending!=2 else 0
        noise,flip=exogenous(self.seed,self.episode,t)
        self.state^=true_effect^noise
        witness=(int(actual_mode>=3)^int(flip)) if pending==2 else -1
        self.pending=requested
        self.steps+=1
        self.done=self.steps==DURATION
        reward=-1 if not self.done else -1 + (
            10 if self.state==self.goal else -2*hamming(self.state,self.goal))
        return self.state,witness,reward,self.done


def likelihood(mode,credited_action,observed_effect,witness,*,sensor_applied):
    if mode not in range(6) or credited_action not in ACTIONS:
        raise ValueError("F50_INVALID_CAUSAL_HYPOTHESIS_OR_ACTION")
    effect=EFFECTS[mode][credited_action] if credited_action!=2 else 0
    disturbance=observed_effect^effect
    val=.8 if disturbance==0 else ((.2/3) if disturbance in (1,2,4) else 0.)
    if sensor_applied:
        if witness not in (0,1):
            raise ValueError("F50_SENSOR_WITNESS_MISSING")
        val*=.8 if witness==int(mode>=3) else .2
    elif witness!=-1:
        raise ValueError("F50_UNREQUESTED_SENSOR_WITNESS")
    return val


def normalize(weights):
    total=sum(weights)
    if total<=0 or not math.isfinite(total):
        raise ValueError("F50_IMPOSSIBLE_CAUSAL_OBSERVATION")
    return [float(p/total) for p in weights]


def collect_fit():
    corpus=[]
    counts=[0,0,0]
    for seed in FIT:
        worlds=[]
        for episode in range(12):
            env=World(seed,episode,switching=False)
            records=[]
            for action in BEHAVIOR:
                before,queued=env.state,env.pending
                after,witness,reward,done=env.step(action)
                records.append([before,queued,action,after,witness,reward,done])
                counts[action]+=1
            if len(records)!=DURATION or not env.done:
                raise ValueError("F50_FIT_PHYSICAL_ACTION_MISSING")
            worlds.append(records)
        corpus.append(worlds)
    if len(corpus)!=8 or sum(len(e) for w in corpus for e in w)!=1152:
        raise ValueError("F50_FIT_TRANSCRIPT_INCOMPLETE")
    if counts!=[480,384,288]:
        raise ValueError("F50_FIT_ACTION_COVERAGE_CHANGED")
    return corpus,counts


def fit_model(corpus):
    if len(corpus)!=8 or any(len(w)!=12 for w in corpus):
        raise ValueError("F50_TRAIN_COHORT_CHANGED")
    prior_counts=[1.]*6
    effect_counts=[{e:0 for e in range(8)} for _ in ACTIONS]
    transitions=0
    for world in corpus:
        posterior=[1/6]*6
        for episode in world:
            for before,pending,requested,after,witness,reward,done in episode:
                probs=[likelihood(m,pending,before^after,witness,sensor_applied=pending==2)
                       for m in range(6)]
                posterior=normalize([posterior[m]*probs[m] for m in range(6)])
                effect_counts[pending][before^after]+=1
                transitions+=1
        prior_counts=[x+p for x,p in zip(prior_counts,posterior)]
    if transitions!=1152:
        raise ValueError("F50_FIT_RECORD_COUNT_DRIFT")
    prior=normalize(prior_counts)
    empirical=[min(range(8),key=lambda e:(-effect_counts[a][e],e)) for a in ACTIONS]
    if any(x<=0 for x in prior):
        raise ValueError("F50_UNSEEN_HYPOTHESIS_LOST")
    return {"prior":prior,"empirical":empirical,
            "training_transitions":transitions,"fit_worlds":8}


def plan(state,goal,pending,probs):
    def score(action):
        total=0.
        for m,p in enumerate(probs):
            first=EFFECTS[m][pending] if pending!=2 else 0
            second=EFFECTS[m][action] if action!=2 else 0
            nxt=state^first^second
            total+=p*(2*int(nxt==goal)-hamming(nxt,goal))
        return total
    return max(ACTIONS,key=lambda a:(score(a),-a))


class Policy:
    def __init__(self,kind,fit):
        if kind not in ARMS:
            raise ValueError("F50_UNKNOWN_POLICY_ARM")
        self.kind=kind
        self.fit_prior=list(fit["prior"])
        self.working=list(self.fit_prior)
        self.stable=list(self.fit_prior)
        self.empirical=list(fit["empirical"])
        self.last3=[]
        self.history=[]
        self.consecutive_positive=0
        self.resets=0
        self.stable_updates=0
        self.abstains=0
        self.observations=0
        self.decision_ns=0

    def decide(self,state,goal,pending,t):
        before=time.perf_counter_ns()
        if (state not in range(8) or goal not in range(8)
            or pending not in ACTIONS or t not in range(DURATION)):
            raise ValueError("F50_INVALID_PUBLIC_POLICY_INPUT")
        if self.kind=="trained-empirical":
            first=self.empirical[pending]
            action=max(ACTIONS,key=lambda a:(-hamming(state^first^self.empirical[a],goal),-a))
        else:
            action=plan(state,goal,pending,self.working)
        self.decision_ns+=time.perf_counter_ns()-before
        return int(action)

    def observe(self,old,pending,requested,nxt,witness):
        self.observations+=1
        if self.kind in ("trained-empirical","no-feedback"):
            return
        credited=requested if self.kind=="candidate-wrong-credit" else pending
        L=[likelihood(m,credited,old^nxt,witness,sensor_applied=pending==2)
           for m in range(6)]
        if self.kind=="recent3-switch-bayes":
            # Strong switching-capable 3-observation control: restart from the
            # common FIT prior and permit latent transitions between *each*
            # actually observed public consequence. No true mode/switch access.
            self.history=(self.history+[[pending,old^nxt,witness]])[-3:]
            weights=list(self.fit_prior)
            for cmd,observed,sig in self.history:
                weights=[.88*w+.12*(1-w)/5 for w in weights]
                l=[likelihood(m,cmd,observed,sig,sensor_applied=cmd==2)
                   for m in range(6)]
                weights=normalize([weights[m]*l[m] for m in range(6)])
            self.working=weights
            return
        if self.kind=="fixed-hazard-bayes":
            base=[.92*w+.08*p for w,p in zip(self.working,self.fit_prior)]
        elif self.kind=="switching-hmm-bayes":
            base=[.88*w+.12*(1-w)/5 for w in self.working]
        elif self.kind=="single-surprise-reset":
            q=sum(w*l for w,l in zip(self.working,L))
            if pending!=2 and q<CUTOFF:
                self.working=list(self.fit_prior)
                self.resets+=1
            base=[.98*w+.02*p for w,p in zip(self.working,self.fit_prior)]
        else:
            # Corroborated change-point and its two mechanistic ablations:
            # Evidence is from ACTUALLY observed, non-sensor public consequences.
            if pending==2:
                self.last3=[]
                self.consecutive_positive=0
            else:
                s=sum(w*l for w,l in zip(self.stable,L))
                a=sum(p*l for p,l in zip(self.fit_prior,L))
                ratio=math.log(max(a,1e-12))-math.log(max(s,1e-12))
                self.last3=(self.last3+[ratio])[-3:]
                self.consecutive_positive=(self.consecutive_positive+1 if ratio>.5 else 0)
                should_reset=(len(self.last3)>=3 and self.consecutive_positive>=2
                              and sum(self.last3)>LOG_BF)
                if should_reset and self.kind!="candidate-no-reset":
                    self.working=list(self.fit_prior)
                    self.last3=[]
                    self.consecutive_positive=0
                    self.resets+=1
            base=[.98*w+.02*p for w,p in zip(self.working,self.fit_prior)]
        weighted=[base[m]*L[m] for m in range(6)]
        if sum(weighted)<=0 and self.kind=="candidate-wrong-credit":
            self.abstains+=1
            return
        self.working=normalize(weighted)
        if self.kind in ("corroborated-change","candidate-no-reset","candidate-wrong-credit"):
            if len(self.last3)==3 and all(x<=.5 for x in self.last3):
                self.stable=normalize([.97*s+.03*w for s,w in zip(self.stable,self.working)])
                self.stable_updates+=1

    def snapshot(self):
        return {"kind":self.kind,"working":self.working,"stable":self.stable,
                "resets":self.resets,"stable_updates":self.stable_updates,
                "abstains":self.abstains,"observations":self.observations,
                "last3":self.last3,"consecutive_positive":self.consecutive_positive,
                "history":self.history}


def fit_replay(corpus,fit):
    """Off-policy stationary FIT transcript replay; NO new source physical steps."""
    counts={"candidate_resets":0,"single_surprise_resets":0,
            "candidate_stable_updates":0,"episodes":0,"records":0}
    for world in corpus:
        for records in world:
            c=Policy(CANDIDATE,fit)
            b=Policy("single-surprise-reset",fit)
            for record in records:
                before,pending,requested,nxt,witness,_reward,_done=record
                c.observe(before,pending,requested,nxt,witness)
                b.observe(before,pending,requested,nxt,witness)
                counts["records"]+=1
            if c.observations!=DURATION or b.observations!=DURATION:
                raise ValueError("F50_FIT_REPLAY_TRUNCATED")
            counts["candidate_resets"]+=c.resets
            counts["single_surprise_resets"]+=b.resets
            counts["candidate_stable_updates"]+=c.stable_updates
            counts["episodes"]+=1
    if counts["episodes"]!=96 or counts["records"]!=1152:
        raise ValueError("F50_FIT_ONLY_REPLAY_INCOMPLETE")
    return counts


def episode(seed,ep,kind,fit):
    if type(seed) is not int or seed in FORBIDDEN or seed not in (*TRANSFER,*RETENTION):
        raise ValueError("F50_UNAUTHORIZED_DEV_OR_PROTECTED_FIRST_USE")
    world=World(seed,ep,switching=seed in TRANSFER)
    p=Policy(kind,fit)
    trace=[]
    for t in range(DURATION):
        old,pending=world.state,world.pending
        chosen=p.decide(old,world.goal,pending,t)
        nxt,wit,rwd,done=world.step(chosen)
        p.observe(old,pending,chosen,nxt,wit)
        trace.append([old,pending,chosen,nxt,wit,rwd,done])
    if len(trace)!=DURATION or not world.done:
        raise ValueError("F50_REAL_PHYSICAL_ACTION_BUDGET_DRIFT")
    return {"success":world.state==world.goal,
            "return":sum(row[5] for row in trace),
            "steps":len(trace),"resets":p.resets,
            "stable_updates":p.stable_updates,"trace":trace,
            "snapshot":p.snapshot(),"decision_ns":p.decision_ns}


def assess(fit,training_sha,coverage,fit_counts,*,started=None,trained_at=None):
    if (fit["training_transitions"]!=1152 or fit["fit_worlds"]!=8
        or coverage!=[480,384,288] or fit_counts["records"]!=1152
        or fit_counts["episodes"]!=96):
        raise ValueError("F50_FROZEN_FIT_CUSTODY_DRIFT")
    seeds=(*FIT,*TRANSFER,*RETENTION)
    if len(set(seeds))!=44 or set(seeds)&set(FORBIDDEN):
        raise ValueError("F50_FIT_DEV_FIRST_USE_OVERLAP")
    if any(s%6 not in (4,5) for s in TRANSFER):
        raise ValueError("F50_UNKNOWN_TRANSFER_MODE_COHORT_DRIFT")
    if any(s%6 not in (0,1,2,3) for s in (*FIT,*RETENTION)):
        raise ValueError("F50_FAMILIAR_COHORT_DRIFT")
    frozen=canonical(fit)
    model=json.loads(frozen)
    if canonical(model)!=frozen:
        raise ValueError("F50_COLD_RESTORE_MODEL_DRIFT")
    report={
        "schema":"forge.eureka.f50.noise-aware-corroborated-change-synthetic-dev.v1",
        "synthetic_only":True,"external_original_physics":False,
        "scientific_accepted":False,"first_use_consumed":False,
        "owner_eligible":False,"general_rsi_proven":False,
        "matched_whole_process_compute_proven":False,
        "training_sha256":training_sha,"fit_model_sha256":digest(fit),
        "training_transitions":1152,"fit_action_counts":coverage,
        "fit_only_stationary_replay":fit_counts,
        "fit_prior":fit["prior"],"fit_empirical":fit["empirical"],
        "train_seeds":FIT,"transfer_seeds":TRANSFER,
        "retention_seeds":RETENTION,"arms":{},
    }
    for kind in ARMS:
        worlds=[]
        for seed in (*TRANSFER,*RETENTION):
            eps=[]
            for ep in range(4):
                warm=episode(seed,ep,kind,fit)
                cold=episode(seed,ep,kind,model)
                if (canonical(warm["trace"])!=canonical(cold["trace"])
                    or canonical(warm["snapshot"])!=canonical(cold["snapshot"])
                    or warm["success"]!=cold["success"]
                    or warm["return"]!=cold["return"]):
                    raise ValueError("F50_INDEPENDENT_COLD_WARM_REAL_TRACE_DRIFT")
                eps.append({
                    "episode":ep,"success":warm["success"],"return":warm["return"],
                    "steps":warm["steps"],"resets":warm["resets"],
                    "stable_updates":warm["stable_updates"],
                    "trace_sha256":digest(warm["trace"]),
                    "policy_snapshot_sha256":digest(warm["snapshot"]),
                    "decision_ns":warm["decision_ns"],"cold_matches":True,
                })
            worlds.append({
                "seed":seed,"episodes":eps,
                "goal_successes":sum(x["success"] for x in eps),
                "mean_return":sum(x["return"] for x in eps)/4,
                "reset_count":sum(x["resets"] for x in eps),
                "stable_update_count":sum(x["stable_updates"] for x in eps),
            })
        transfer=worlds[:24]; retention=worlds[24:]
        clocks=sum(x["decision_ns"] for w in transfer for x in w["episodes"])
        steps=sum(x["steps"] for w in transfer for x in w["episodes"])
        if clocks<=0 or steps<=0:
            raise ValueError("F50_UNMEASURED_REAL_DECISION_COST")
        report["arms"][kind]={
            "worlds":worlds,
            "transfer_success":sum(w["goal_successes"] for w in transfer)/96,
            "retention_success":sum(w["goal_successes"] for w in retention)/48,
            "transfer_return":sum(w["mean_return"] for w in transfer)/24,
            "reset_worlds":sum(w["reset_count"]>0 for w in transfer),
            "stable_update_worlds":sum(w["stable_update_count"]>0 for w in transfer),
            "decision_ns_per_step":clocks/steps,
        }
    strongest=max(CONVENTIONAL,key=lambda k:report["arms"][k]["transfer_success"])
    ca=report["arms"][CANDIDATE]; base=report["arms"][strongest]
    report["strongest_conventional"]=strongest
    report["success_gain"]=ca["transfer_success"]-base["transfer_success"]
    report["return_gain"]=ca["transfer_return"]-base["transfer_return"]
    report["paired_world_success_wins"]=sum(
        w["goal_successes"]>b["goal_successes"]
        for w,b in zip(ca["worlds"][:24],base["worlds"][:24]))
    report["best_conventional_retention"]=max(
        report["arms"][k]["retention_success"] for k in CONVENTIONAL)
    report["retention_margin"]=ca["retention_success"]-report["best_conventional_retention"]
    report["cost_ratio"]=ca["decision_ns_per_step"]/base["decision_ns_per_step"]
    n=fit_counts["single_surprise_resets"]
    report["stationary_false_alarm_ratio"]=(
        fit_counts["candidate_resets"]/n if n else None)
    report["frozen_conditions_met"]=bool(
        report["success_gain"]>=.10
        and report["return_gain"]>=.75
        and report["paired_world_success_wins"]>=16
        and all(ca["transfer_success"]>=report["arms"][k]["transfer_success"]+.10
                for k in ("candidate-no-reset","candidate-wrong-credit"))
        and ca["transfer_success"]>=report["arms"]["single-surprise-reset"]["transfer_success"]+.05
        and report["retention_margin"]>=-.05
        and ca["reset_worlds"]>=8 and ca["stable_update_worlds"]>=8
        and n>=1 and fit_counts["candidate_resets"]<=n/2
        and report["cost_ratio"]<=2
        and all(len(a["worlds"])==36 and all(len(w["episodes"])==4
                and all(ep["steps"]==DURATION and ep["cold_matches"]
                        for ep in w["episodes"]) for w in a["worlds"])
                for a in report["arms"].values())
    )
    report["classification"]=(
        "F50_DEV_SIGNAL_UNVERIFIED" if report["frozen_conditions_met"]
        else "F50_DEV_NO_GO")
    report["report_sha256"]=digest(report)
    return report


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    if len(argv)!=1:
        raise ValueError("F50_USAGE: python source.py /tmp/f50-report.json")
    start=time.perf_counter()
    corpus,coverage=collect_fit()
    fit=fit_model(corpus)
    fit_counts=fit_replay(corpus,fit)
    trained_at=time.perf_counter()
    report=assess(fit,digest(corpus),coverage,fit_counts)
    evaluated_at=time.perf_counter()
    report["training_fit_replay_seconds"]=trained_at-start
    report["full_scored_evaluation_seconds"]=evaluated_at-trained_at
    report["whole_process_seconds"]=evaluated_at-start
    report["report_sha256"]=digest({k:v for k,v in report.items() if k!="report_sha256"})
    out=Path(argv[0]).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(canonical(report)+b"\n")
    print("F50_CORROBORATED_CHANGE_SYNTHETIC_DEV="+report["classification"]
          +" sha256="+report["report_sha256"])
    print("F50_TRAINING_TRANSITIONS="+str(report["training_transitions"])
          +" sha256="+report["training_sha256"])
    print("F50_STATIONARY_CANDIDATE_FALSE_RESETS="+
          str(fit_counts["candidate_resets"])+" SINGLE_RESET="+
          str(fit_counts["single_surprise_resets"]))
    print("F50_STRONGEST="+report["strongest_conventional"]+
          " success_gain="+str(report["success_gain"])+
          " wins="+str(report["paired_world_success_wins"])+
          " return_gain="+str(report["return_gain"])+
          " reset_worlds="+str(ca_reset_worlds(report))+
          " decision_ratio="+str(report["cost_ratio"]))
    return report


def ca_reset_worlds(report):
    return report["arms"][CANDIDATE]["reset_worlds"]


if __name__=="__main__":
    main()

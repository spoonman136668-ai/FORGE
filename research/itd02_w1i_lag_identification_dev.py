#!/usr/bin/env python3
"""W1I: causal-delay identifiability via genuine selected *synthetic* actions.

DEV only. No protected original world, FSA, file/queue/worker execution by
models. Exact source-first protocol 39cd0c72daf1d1853c83ea7791eb2c913630c665.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

SCHEMA = "forge.eureka.itd02.w1i.identifiable-intervention-dev.v1"
PROTOCOL_COMMIT = "39cd0c72daf1d1853c83ea7791eb2c913630c665"
FAMILIES = {
    "lag-cycle": (0, 1, 2, 0),
    "lag-return": (1, 2, 1, 0),
    "lag-stationary": (2, 2, 2, 2),
    "lag-distractor": (0, 2, 1, 2),
}
SEEDS = (94011, 94017, 94021, 94033)
ARMS = ("pulse-causal", "bayes-active", "bayes-greedy", "recent16",
        "eligibility", "no-feedback", "random")
CONVENTIONAL = ("bayes-active", "bayes-greedy", "recent16", "eligibility")
FIT_STEPS = 96
SCORED_STEPS = 160
OMEGA = 2.0 * math.pi / 7.0
HAZARD = .04
SURPRISE_HAZARD = .40
SIGMA = .25
PROBE_BONUS = .35
PROBE_COST = .10
SURPRISE_THRESHOLD = .70
MAX_CHECKPOINT_BYTES = 16384
GENESIS = "0" * 64
FROZEN_STEPS = len(FAMILIES) * len(SEEDS) * len(ARMS) * SCORED_STEPS


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(value):
    return digest_bytes(canonical(value))


def sign(x):
    return 1. if x >= 0. else -1.


def _finite(x):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError("W1I_NONFINITE_INPUT")
    return float(x)


def public_goal(obs, lag=0):
    if type(obs) not in (list, tuple) or len(obs) != 2:
        raise ValueError("W1I_PUBLIC_VECTOR_INVALID")
    sine, cosine = map(_finite, obs)
    if abs(sine)>1.01 or abs(cosine)>1.01:
        raise ValueError("W1I_PUBLIC_RANGE_INVALID")
    if type(lag) is not int or not 0 <= lag <= 2:
        raise ValueError("W1I_LAG_OUT_OF_SCOPE")
    angle = math.atan2(sine, cosine)
    return sign(math.sin(angle + lag * OMEGA))


class World:
    """Source owns phase, action history, noise and physical momentum."""
    def __init__(self, family, seed, fit):
        if family not in FAMILIES or type(seed) is not int or type(fit) is not bool:
            raise ValueError("W1I_SOURCE_IDENTITY_INVALID")
        self.family = family
        self.seed = seed
        self.fit = fit
        self.horizon = FIT_STEPS if fit else SCORED_STEPS
        salt = list(FAMILIES).index(family) * 13007 + (611 if fit else 2773)
        self.rng = random.Random(seed * 101 + salt)
        self.offset = self.rng.uniform(-.5, .5)
        self.actions = [0, 0]
        self.momentum = 0.
        self.t = 0

    def public(self):
        theta = OMEGA * self.t + self.offset
        return [math.sin(theta), math.cos(theta)]

    def _lag(self):
        return ((0,1,2)[min(self.t // 32, 2)] if self.fit
                else FAMILIES[self.family][min(self.t // 40, 3)])

    def step(self, action):
        if type(action) is not int or action not in (0, 1) or self.t >= self.horizon:
            raise ValueError("W1I_ACTION_OR_BUDGET_INVALID")
        obs = self.public()
        lag = self._lag()
        chosen = [action, self.actions[-1], self.actions[-2]][lag]
        noise = self.rng.uniform(-.05, .05)
        nuisance = (.04 * obs[1] if self.family == "lag-distractor" else 0.)
        observed = sign(obs[0]) * chosen - PROBE_COST * action + nuisance + noise
        self.momentum = max(-1., min(1., .7*self.momentum+.3*(2.*action-1.)))
        self.actions.append(action)
        self.actions = self.actions[-2:]
        self.t += 1
        if not math.isfinite(observed) or abs(observed) > 2.:
            raise ValueError("W1I_BAD_SOURCE_FEEDBACK")
        return obs, float(observed), self.public(), self.t == self.horizon


def check_fit_actions(rows):
    """Reject periodic a_t = a_(t-2) and singular lag regressor design."""
    if len(rows) != FIT_STEPS:
        raise ValueError("W1I_FIT_LENGTH_MISMATCH")
    actions = [0, 0] + [row[1] for row in rows]
    comparisons = sum(actions[t+2] != actions[t] for t in range(2, FIT_STEPS))
    x = [[float(actions[t+2-d]) for d in range(3)]
         for t in range(2, FIT_STEPS)]
    gram = [[sum(row[i]*row[j] for row in x) for j in range(3)]
            for i in range(3)]
    a,b,c=gram[0]
    d,e,f=gram[1]
    g,h,i=gram[2]
    determinant=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
    if comparisons < 24 or determinant < 1.:
        raise ValueError("W1I_CAUSAL_LAGS_NOT_IDENTIFIABLE_FROM_FIT")
    return {"separated_lag0_lag2": comparisons, "lag_design_determinant": determinant}


def collect_fit(family, seed):
    w = World(family, seed, True)
    independent = random.Random(seed * 211 + list(FAMILIES).index(family) * 733 + 1901)
    rows = []
    for _ in range(FIT_STEPS):
        a = independent.randrange(2)
        obs, reward, new, final = w.step(a)
        rows.append((obs, a, reward))
    if not final or len(rows) != FIT_STEPS:
        raise ValueError("W1I_FIT_NOT_COMPLETE")
    coverage = check_fit_actions(rows)
    return rows, coverage


class LagBelief:
    """All causally relevant inputs come from selected-action feedback only.

    A minor hazard-adaptive three-lag Bayesian model. No latent-phase oracle.
    """
    def __init__(self, kind):
        if kind not in ("pulse-causal","bayes-active","bayes-greedy"):
            raise ValueError("W1I_UNDECLARED_BAYESIAN")
        self.kind=kind
        self.posterior=[1./3.]*3
        self.history=[0,0]
        self.completed=0
        self.streak=0
        self.head=GENESIS

    def choose(self, obs):
        premium=(PROBE_BONUS * (1.-max(self.posterior))
                 if self.kind != "bayes-greedy" else 0.)
        value=(sum(self.posterior[d]*public_goal(obs,d) for d in range(3))
               - PROBE_COST + premium)
        return int(value > 0.)

    def update(self, obs, action, consequence):
        if type(action) is not int or action not in (0,1):
            raise ValueError("W1I_BAYES_BAD_ACTION")
        reward=_finite(consequence)
        acts=[action,self.history[-1],self.history[-2]]
        expected=[sign(obs[0])*acts[d]-PROBE_COST*action for d in range(3)]
        prior_mean=sum(self.posterior[d]*expected[d] for d in range(3))
        # Contemporaneous source nuisance is not a hidden known family label;
        # bounded public cos disturbance is deliberately an unmodeled error.
        hazard=(SURPRISE_HAZARD if self.kind=="pulse-causal" and self.streak>=2
                else HAZARD)
        prior=[(1.-hazard)*p + (hazard/2.)*(1.-p) for p in self.posterior]
        prob=[prior[d]*math.exp(-.5*((reward-expected[d])/SIGMA)**2)
              for d in range(3)]
        total=sum(prob)
        if total<=1e-250:
            raise ValueError("W1I_BAYES_POSTERIOR_UNIDENTIFIABLE")
        self.posterior=[p/total for p in prob]
        if self.kind=="pulse-causal":
            self.streak = min(self.streak+1,2) if abs(reward-prior_mean)>=SURPRISE_THRESHOLD else 0
        record={"seq":self.completed,"obs":list(obs),"action":action,
                "consequence":reward,"prev":self.head}
        self.head=sha(record)
        self.history=[self.history[-1],action]
        self.completed+=1

    def reset_episode_history(self):
        self.history=[0,0]
        self.streak=0

    def state(self):
        return {"kind":self.kind,"posterior":self.posterior,
                "history":self.history,"completed":self.completed,
                "streak":self.streak,"head":self.head}

    def checkpoint(self):
        packet={"schema":SCHEMA,"model":self.state(),
                "scientific_accepted":False,"can_dispatch_original":False}
        raw=canonical(packet)
        if len(raw)>MAX_CHECKPOINT_BYTES:raise ValueError("W1I_COLD_TOO_LARGE")
        return raw,digest_bytes(raw)

    @classmethod
    def restore(cls,raw,expected_sha,minimum_completed):
        if (type(raw) is not bytes or len(raw)>MAX_CHECKPOINT_BYTES or
            type(expected_sha) is not str or digest_bytes(raw)!=expected_sha or
            type(minimum_completed) is not int or minimum_completed<0):
            raise ValueError("W1I_COLD_EXTERNAL_CUSTODY_INVALID")
        def unique(pairs):
            obj={}
            for key,value in pairs:
                if key in obj:raise ValueError("W1I_COLD_DUPLICATE_JSON_KEY")
                obj[key]=value
            return obj
        try:
            body=json.loads(raw,object_pairs_hook=unique,
                            parse_constant=lambda _:(_ for _ in ()).throw(
                                ValueError("W1I_COLD_NONFINITE_JSON")))
        except (UnicodeError,ValueError) as exc:
            raise ValueError("W1I_COLD_MALFORMED") from exc
        if (type(body) is not dict or set(body)!={"schema","model","scientific_accepted","can_dispatch_original"} or
            body["schema"]!=SCHEMA or body["scientific_accepted"] is not False or
            body["can_dispatch_original"] is not False or canonical(body)!=raw):
            raise ValueError("W1I_COLD_PROTOCOL_DRIFT")
        state=body["model"]
        if (type(state) is not dict or
            set(state)!={"kind","posterior","history","completed","streak","head"}):
            raise ValueError("W1I_COLD_MODEL_INVALID")
        out=cls(state["kind"])
        probs=state["posterior"]
        if (type(probs) is not list or len(probs)!=3 or
            any(type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 for p in probs) or
            abs(sum(probs)-1.)>1e-10 or
            type(state["history"]) is not list or len(state["history"])!=2 or
            any(type(a) is not int or a not in (0,1) for a in state["history"]) or
            type(state["completed"]) is not int or state["completed"] < minimum_completed or
            type(state["streak"]) is not int or state["streak"] not in (0,1,2) or
            type(state["head"]) is not str or len(state["head"])!=64 or
            any(c not in "0123456789abcdef" for c in state["head"])):
            raise ValueError("W1I_COLD_HISTORY_INVALID")
        out.posterior=list(probs)
        out.history=list(state["history"])
        out.completed=state["completed"]
        out.streak=state["streak"]
        out.head=state["head"]
        return out


class Recent16:
    def __init__(self):
        self.hist=[0,0];self.rows=[];self.completed=0
    def _posterior(self):
        evidence=[0.,0.,0.]
        for obs,acts,action,reward in self.rows[-16:]:
            for d in range(3):
                expect=sign(obs[0])*acts[d]-PROBE_COST*action
                evidence[d] -= .5*((reward-expect)/SIGMA)**2
        mx=max(evidence)
        weights=[math.exp(x-mx) for x in evidence]
        return [x/sum(weights) for x in weights]
    def choose(self,obs):
        p=self._posterior()
        return int(sum(p[d]*public_goal(obs,d) for d in range(3))-PROBE_COST>0.)
    def update(self,obs,action,consequence):
        self.rows.append((list(obs),[action,self.hist[-1],self.hist[-2]],
                          action,_finite(consequence)))
        self.rows=self.rows[-16:]
        self.hist=[self.hist[-1],action]
        self.completed+=1
    def reset_episode_history(self):
        self.hist=[0,0]
    def state(self):
        return {"rows":self.rows,"history":self.hist,"completed":self.completed}


class Eligibility:
    """Conventional fixed temporal eligibility weights, same observed feedback."""
    def __init__(self):
        self.hist=[0,0];self.values=[0.,0.,0.];self.count=0
    def choose(self,obs):
        weights=[1.,.7,.49]
        totals=[self.values[i]*weights[i] for i in range(3)]
        norm=sum(abs(x) for x in totals)
        prob=([abs(x)/norm for x in totals] if norm > 1e-12 else [1./3.]*3)
        return int(sum(prob[d]*public_goal(obs,d) for d in range(3))-PROBE_COST>0.)
    def update(self,obs,action,consequence):
        past=[action,self.hist[-1],self.hist[-2]]
        adjusted=_finite(consequence)+PROBE_COST*action
        for d in range(3):
            self.values[d]+=(sign(obs[0])*past[d]-0.5)*adjusted
        self.hist=[self.hist[-1],action]
        self.count+=1
    def reset_episode_history(self):
        self.hist=[0,0]
    def state(self):
        return {"history":self.hist,"values":self.values,"observations":self.count}


class NoFeedback:
    def choose(self,obs): return int(public_goal(obs,0)>0)
    def update(self,obs,action,consequence): pass
    def reset_episode_history(self): pass
    def state(self): return {"kind":"no-feedback"}


class RandomPolicy:
    def __init__(self,seed):
        self.rng=random.Random(seed*227+19)
    def choose(self,obs):return self.rng.randrange(2)
    def update(self,obs,action,consequence):pass
    def reset_episode_history(self):pass
    def state(self):return {"kind":"random","rng":str(self.rng.getstate())}


def policy(name,seed):
    if name in ("pulse-causal","bayes-active","bayes-greedy"):
        return LagBelief(name)
    if name=="recent16":return Recent16()
    if name=="eligibility":return Eligibility()
    if name=="no-feedback":return NoFeedback()
    if name=="random":return RandomPolicy(seed)
    raise ValueError("W1I_UNKNOWN_POLICY")


def rollout(family,seed,name,fit_rows,*,cold):
    learner=policy(name,seed)
    start_wall=time.perf_counter();start_cpu=time.process_time()
    for obs,action,reward in fit_rows:learner.update(obs,action,reward)
    learner.reset_episode_history()
    world=World(family,seed,False)
    trace=[];pulses=0;correct_lag=0;possibilities=0;positive=0
    total_return=0.;direct_cold=0
    history=[0,0]
    for step in range(SCORED_STEPS):
        obs=world.public()
        choice=learner.choose(obs)
        if type(choice) is not int or choice not in (0,1):
            raise ValueError("W1I_OUT_OF_CONTRACT_POLICY_ACTION")
        if step>=2 and choice!=history[-2]:possibilities+=1
        real_lag=world._lag()  # evaluator-only, never passed to learner
        before,reward,after,terminal=world.step(choice)
        learner.update(before,choice,reward)
        pulses+=choice;positive+=int(reward>0.)
        total_return+=reward
        if isinstance(learner,LagBelief):
            correct_lag+=int(max(range(3),key=lambda d:learner.posterior[d])==real_lag)
        trace.append([before,choice,reward,after,terminal])
        history=[history[-1],choice]
        if name=="pulse-causal" and cold and step==79:
            raw,digest=learner.checkpoint()
            learner=LagBelief.restore(raw,digest,minimum_completed=FIT_STEPS+80)
            direct_cold+=1
    if not terminal or len(trace)!=SCORED_STEPS:
        raise ValueError("W1I_WORLD_TRUNCATED")
    return {"return":total_return,"pulses":pulses,"positive_steps":positive,
            "lag_identification_correct":correct_lag if isinstance(learner,LagBelief) else None,
            "identifiable_decisions":possibilities,
            "trace_sha256":sha(trace),"model_sha256":sha(learner.state()),
            "cold_continuations":direct_cold,
            "source_steps":len(trace),
            "cpu_seconds":time.process_time()-start_cpu,
            "wall_seconds":time.perf_counter()-start_wall}


def score():
    results=[];warm_count=0;cold_count=0;fit_total=0
    for family in FAMILIES:
        for seed in SEEDS:
            fit,identifiability=collect_fit(family,seed)
            fit_total+=len(fit)
            arms={}
            for name in ARMS:
                warm=rollout(family,seed,name,fit,cold=False)
                cold=rollout(family,seed,name,fit,cold=True)
                warm_count+=warm["source_steps"];cold_count+=cold["source_steps"]
                for field in ("return","pulses","positive_steps","lag_identification_correct",
                              "identifiable_decisions","trace_sha256","model_sha256","source_steps"):
                    if warm[field]!=cold[field]:
                        raise ValueError("W1I_ORIGINAL_COLD_REPLAY_MISMATCH_"+field)
                if name=="pulse-causal" and cold["cold_continuations"]!=1:
                    raise ValueError("W1I_NO_ACTUAL_COLD_MODEL_CONTINUATION")
                arms[name]=warm
            results.append({"family":family,"seed":seed,"fit_sha256":sha(fit),
                            "fit_identifiability":identifiability,"arms":arms})
    if fit_total!=16*FIT_STEPS or warm_count!=FROZEN_STEPS or cold_count!=FROZEN_STEPS:
        raise ValueError("W1I_FROZEN_INTERVENTION_BUDGET_INCOMPLETE")
    totals={name:sum(e["arms"][name]["return"] for e in results) for name in ARMS}
    winner=max(CONVENTIONAL,key=lambda n:(totals[n],-CONVENTIONAL.index(n)))
    gains=totals["pulse-causal"]-totals[winner]
    paired=sum(e["arms"]["pulse-causal"]["return"] > e["arms"][winner]["return"]
               for e in results)
    family_means={fam:{name:sum(e["arms"][name]["return"] for e in results
                                 if e["family"]==fam)/len(SEEDS)
                       for name in ARMS} for fam in FAMILIES}
    nondegraded=all(family_means[f]["pulse-causal"]>=family_means[f][winner]
                    for f in FAMILIES)
    differing=sum(e["arms"]["pulse-causal"]["trace_sha256"]!=
                  e["arms"]["bayes-greedy"]["trace_sha256"] for e in results)
    valid_positive=(gains>=.05*abs(totals[winner]) and paired>=12 and nondegraded and
                    totals["pulse-causal"]>totals["bayes-greedy"] and
                    totals["pulse-causal"]>totals["eligibility"] and differing>=8)
    outcome={
        "schema":SCHEMA,"protocol_commit":PROTOCOL_COMMIT,
        "status":"ITD02_W1I_DEV_SIGNAL_UNVERIFIED" if valid_positive else "ITD02_W1I_DEV_NO_GO",
        "source":"synthetic-public-selected-action-lag-worlds",
        "worlds":results,"families":list(FAMILIES),"seeds":list(SEEDS),"arms":list(ARMS),
        "strongest_conventional":winner,"total_returns":totals,
        "candidate_gain":gains,"candidate_minimum_gain":.05*abs(totals[winner]),
        "candidate_paired_world_wins":paired,"per_family_mean_return":family_means,
        "per_family_nondegraded":nondegraded,"candidate_vs_greedy_distinct_worlds":differing,
        "fit_source_steps":fit_total,"warm_scored_world_steps":warm_count,
        "cold_replay_world_steps":cold_count,
        "original_scientific_first_use":False,"scientific_accepted":False,
        "F57_reserved_seed_uses":0,"autonomous_owner_execution":False
    }
    outcome["report_sha256"]=sha(outcome)
    return outcome


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:raise ValueError("W1I_OUTPUT_PATH_REQUIRED")
    result=score()
    destination=Path(args[0])
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(canonical(result)+b"\n")
    print("W1I_RESULT="+result["status"])
    print("W1I_SUMMARY="+json.dumps({
        "candidate_return":result["total_returns"]["pulse-causal"],
        "strongest":result["strongest_conventional"],
        "strongest_return":result["total_returns"][result["strongest_conventional"]],
        "returns":result["total_returns"],
        "paired_wins":result["candidate_paired_world_wins"],
        "gain":result["candidate_gain"],
        "min_gain":result["candidate_minimum_gain"],
        "family_means":result["per_family_mean_return"],
        "distinct_greedy_worlds":result["candidate_vs_greedy_distinct_worlds"],
        "warm_steps":result["warm_scored_world_steps"],
        "cold_steps":result["cold_replay_world_steps"],
        "report_sha256":result["report_sha256"]},sort_keys=True))
    return result


if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""F45 DEV original-physics two-hypothesis causal action-sequence tournament.

All true physical consequences are from source-pinned original MountainCar.
The external action reversal is evaluator-only; no first-use or owner admission.
"""
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import f41_original_mountaincar_dev as f41
import f42_original_actuator_reversal_dev as f42
import f43_train_calibrated_contradiction_dev as f43

SOURCE = f41.SOURCE
TRAIN_SHA256 = f43.TRAIN_SHA256
FAULT_WORLDS = {
    1801: ((24, 70), (112, 154)),
    1811: ((35, 82), (121, 166)),
    1823: ((61, 120), (154, 191)),
    1831: ((72, 126), (151, 190)),
    1847: ((27, 148),),
    1853: ((45, 160),),
    1867: ((22, 56), (90, 126), (150, 186)),
    1879: ((18, 62), (88, 118), (149, 181)),
}
RETENTION_WORLDS = (1891, 1901, 1913, 1931)
FORBIDDEN = (59, 83)
TOURNAMENT = (
    "hypothesis-tournament", "tournament-no-info",
    "tournament-static-belief", "tournament-wrong-credit",
)
CONVENTIONAL = (
    "bayes-no-probe", "rolling8-no-probe",
    "rolling8-probe", "bayes-probe",
    "fixed-mpc", "velocity-rule",
)
INCUMBENT = "calibrated-contradiction"
KINDS = (*TOURNAMENT, *CONVENTIONAL, INCUMBENT)
SEQUENCES = f41.SEQUENCES


def canonical(x):
    return f41.canonical(x)


def digest(x):
    return f41.digest(x)


def frozen_fit(gym):
    fit = f43.source_fit(gym)
    if (fit["training_sha256"] != TRAIN_SHA256 or fit["training_episodes"] != 96
        or fit["training_transitions"] != 18138
        or fit["training_action_counts"] != [7107, 3011, 8020]
        or fit["calibration_n"] < 1000):
        raise ValueError("F45_SOURCE_FIT_PROVENANCE_DRIFT")
    return fit


def hypothesis_returns(state, dynamics):
    """Return two arrays over the SAME 81 requested-action sequences."""
    state = f41.public_obs(state)
    results = []
    for reversed_channel in (False, True):
        simulated = np.repeat(np.asarray(state,dtype=float)[None,:], len(SEQUENCES), axis=0)
        scores = np.zeros(len(SEQUENCES), dtype=float)
        for t in range(4):
            requested = SEQUENCES[:,t]
            physical = 2 - requested if reversed_channel else requested
            simulated = f41.predict(simulated, physical, dynamics)
            scores += (.92**t)*(-simulated[:,0] - 10*np.abs(simulated[:,1]))
        results.append(scores)
    return results


def information_bonus(state, dynamics, p):
    """Training-model-derived first-action information value only. No physical probe."""
    public = f41.public_obs(state)
    actions = SEQUENCES[:,0]
    normal = f41.predict(np.repeat(np.asarray(public)[None,:],len(actions),axis=0),
                         actions, dynamics)
    rev = f41.predict(np.repeat(np.asarray(public)[None,:],len(actions),axis=0),
                      2-actions, dynamics)
    separation = np.abs(normal[:,1]-rev[:,1])/.0025
    return 0.04*(4*p*(1-p))*np.minimum(1.0,separation)**2


class Tournament:
    def __init__(self, kind, dynamics):
        if kind not in TOURNAMENT:
            raise ValueError("F45_UNKNOWN_TOURNAMENT_ARM")
        self.kind = kind
        self.model = dynamics
        self.posterior = 0.02
        self.flips = 0
        self.probes = 0
        self.informative = 0
        self.decision_ns = 0
        self.posterior_changes = 0

    def decide(self, state, t):
        start = time.perf_counter_ns()
        normal, reversed_mode = hypothesis_returns(state, self.model)
        p = self.posterior
        scores = (1-p)*normal + p*reversed_mode
        if self.kind != "tournament-no-info":
            scores = scores + information_bonus(state, self.model, p)
        action = int(SEQUENCES[int(np.argmax(scores)),0])
        self.decision_ns += time.perf_counter_ns()-start
        return action

    def observe(self, previous, requested, observed):
        start = time.perf_counter_ns()
        l = f42.reversal_evidence(previous, requested, observed, self.model)
        if l:
            self.informative += 1
            if self.kind != "tournament-static-belief":
                if self.kind == "tournament-wrong-credit":
                    l = -l
                prior = 0.03 + 0.94 * self.posterior
                odds = (prior/(1-prior))*math.exp(l)
                updated = odds/(1+odds)
                if not math.isfinite(updated):
                    raise ValueError("F45_NONFINITE_HYPOTHESIS_POSTERIOR")
                if updated != self.posterior:
                    self.posterior_changes += 1
                if (self.posterior < .5) != (updated < .5):
                    self.flips += 1
                self.posterior = updated
        self.decision_ns += time.perf_counter_ns()-start


def policy_for(kind, dynamics, tau):
    if kind in TOURNAMENT:
        return Tournament(kind, dynamics)
    if kind in CONVENTIONAL or kind == INCUMBENT:
        return f43.policy_for(kind, dynamics, tau)
    raise ValueError("F45_UNREGISTERED_POLICY")


def episode(gym, seed, kind, model, tau):
    if type(seed) is not int or seed in FORBIDDEN or seed not in (*FAULT_WORLDS, *RETENTION_WORLDS):
        raise ValueError("F45_PROTECTED_OR_UNAUTHORIZED_DEV_SEED")
    if kind not in KINDS:
        raise ValueError("F45_UNREGISTERED_POLICY")
    policy = policy_for(kind, model, tau)
    windows = FAULT_WORLDS.get(seed, ())
    env = gym.make("MountainCar-v0", render_mode=None)
    try:
        if env.action_space.n != 3:
            raise ValueError("F45_ORIGINAL_ACTION_SPACE_DRIFT")
        observation, _ignored = env.reset(seed=seed)
        state = f41.public_obs(observation)
        initial = state[:]
        trace = []
        effective_faults = 0
        for t in range(200):
            requested = policy.decide(state, t)
            physical = f42.effective_action(requested, t, windows)
            next_obs, reward, terminated, truncated, _ignored = env.step(physical)
            nxt = f41.public_obs(next_obs)
            reward = float(reward)
            if not math.isfinite(reward) or type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError("F45_INVALID_ORIGINAL_PUBLIC_REWARD")
            policy.observe(state, requested, nxt)  # Never give actual action or fault phase to policy.
            if requested != physical:
                effective_faults += 1
            trace.append({"requested":requested,"physical":physical,"next":nxt,
                          "reward":reward,"terminated":terminated,"truncated":truncated})
            state = nxt
            if terminated or truncated:
                break
        if not trace:
            raise ValueError("F45_EMPTY_ORIGINAL_EPISODE")
        return {
            "initial": initial, "trace": trace,
            "return": sum(x["reward"] for x in trace),
            "steps": len(trace), "probes": policy.probes,
            "flips": policy.flips, "informative":policy.informative,
            "decision_ns":policy.decision_ns,
            "posterior":float(getattr(policy,"posterior",0.0)),
            "posterior_changes":int(getattr(policy,"posterior_changes",0)),
            "faulted_actions":effective_faults,
            "terminated":trace[-1]["terminated"],
            "truncated":trace[-1]["truncated"],
        }
    finally:
        env.close()


def assess(gym, fit, source):
    if (fit["training_sha256"] != TRAIN_SHA256
        or fit["training_episodes"] != 96 or fit["training_transitions"] != 18138
        or fit["training_action_counts"] != [7107,3011,8020]
        or fit["calibration_n"] < 1000):
        raise ValueError("F45_FROZEN_SOURCE_FIT_NOT_QUALIFIED")
    model_bytes = canonical(fit["dynamics"])
    cold_model = json.loads(model_bytes)
    if canonical(cold_model) != model_bytes:
        raise ValueError("F45_COLD_CHECKPOINT_CORRUPTED")
    model_sha = digest(fit["dynamics"])
    report = {
        "schema":"forge.eureka.f45.causal-hypothesis-tournament-dev.v1",
        "source":source,
        "original_physics_with_external_actuator_fault":True,
        "unmodified_original_gymnasium_task":False,
        "development_only":True,
        "scientific_accepted":False,
        "first_use_consumed":False,
        "owner_eligible":False,
        "matched_whole_process_compute_proven":False,
        "training_sha256":fit["training_sha256"],
        "train_episodes":fit["training_episodes"],
        "train_transitions":fit["training_transitions"],
        "train_action_counts":fit["training_action_counts"],
        "source_fit_sha256":fit["source_fit_sha256"],
        "model_sha256":model_sha,
        "faulted_eval_seeds":tuple(FAULT_WORLDS),
        "retention_eval_seeds":RETENTION_WORLDS,
        "arms":{},
    }
    for kind in KINDS:
        worlds=[]
        for seed in (*FAULT_WORLDS,*RETENTION_WORLDS):
            cold = episode(gym,seed,kind,cold_model,fit["tau"])
            warm = episode(gym,seed,kind,fit["dynamics"],fit["tau"])
            if (canonical(cold["trace"])!=canonical(warm["trace"])
                or cold["initial"]!=warm["initial"]
                or cold["flips"]!=warm["flips"]
                or cold["probes"]!=warm["probes"]
                or cold["posterior"]!=warm["posterior"]):
                raise ValueError("F45_COLD_WARM_REAL_TRACE_DRIFT")
            trace=cold["trace"]
            worlds.append({
                "seed":seed,"return":cold["return"],"steps":cold["steps"],
                "terminated":cold["terminated"],"truncated":cold["truncated"],
                "flips":cold["flips"],"probes":cold["probes"],
                "informative":cold["informative"],
                "decision_ns":cold["decision_ns"],
                "posterior":cold["posterior"],
                "posterior_changes":cold["posterior_changes"],
                "faulted_actions":cold["faulted_actions"],
                "requested_sha256":digest([x["requested"] for x in trace]),
                "physical_sha256":digest([x["physical"] for x in trace]),
                "observation_sha256":digest([cold["initial"],[x["next"] for x in trace]]),
                "reward_sha256":digest([x["reward"] for x in trace]),
                "trace_sha256":digest([cold["initial"],trace]),
                "cold_matches":True,
            })
        fault=worlds[:8];clean=worlds[8:]
        decision_ns=sum(x["decision_ns"] for x in fault)
        steps=sum(x["steps"] for x in fault)
        if decision_ns<=0 or steps<=0:
            raise ValueError("F45_MISSING_DECISION_COST")
        report["arms"][kind]={
            "worlds":worlds,
            "fault_mean_return":sum(x["return"] for x in fault)/8,
            "retention_mean_return":sum(x["return"] for x in clean)/4,
            "fault_decision_ns_per_step":decision_ns/steps,
            "fault_total_steps":steps,
        }
    strongest=max(CONVENTIONAL,key=lambda k:report["arms"][k]["fault_mean_return"])
    c=report["arms"]["hypothesis-tournament"];b=report["arms"][strongest]
    best_ret=max(report["arms"][k]["retention_mean_return"] for k in CONVENTIONAL)
    report["strongest_conventional"]=strongest
    report["candidate_mean_gain"]=c["fault_mean_return"]-b["fault_mean_return"]
    report["candidate_mean_gain_over_incumbent"]=(
        c["fault_mean_return"]-report["arms"][INCUMBENT]["fault_mean_return"])
    report["candidate_seed_wins_ge10"]=sum(
        x["return"]>=y["return"]+10 for x,y in zip(c["worlds"][:8],b["worlds"][:8]))
    report["retention_margin"]=c["retention_mean_return"]-best_ret
    report["candidate_decision_ns_ratio_to_strongest"]=(
        c["fault_decision_ns_per_step"]/b["fault_decision_ns_per_step"])
    report["frozen_conditions_met"]=bool(
        report["candidate_mean_gain"]>=15
        and report["candidate_mean_gain_over_incumbent"]>=15
        and report["candidate_seed_wins_ge10"]>=6
        and all(c["fault_mean_return"]>=report["arms"][k]["fault_mean_return"]+15
                for k in ("tournament-static-belief","tournament-wrong-credit"))
        and c["fault_mean_return"]>=report["arms"]["tournament-no-info"]["fault_mean_return"]+5
        and report["retention_margin"]>=-5
        and all(w["probes"]==0 for w in c["worlds"])
        and all(len(a["worlds"])==12 and
                all(w["cold_matches"] and w["probes"]<=16 for w in a["worlds"])
                for a in report["arms"].values())
        and report["candidate_decision_ns_ratio_to_strongest"]<=3
    )
    if digest(fit["dynamics"])!=model_sha:
        raise ValueError("F45_MUTATED_FROZEN_TRAINED_DYNAMICS")
    report["classification"]="F45_ORIGINAL_RUNTIME_UNVERIFIED"
    report["report_sha256"]=digest(report)
    return report


def original_gym(root):
    return f41.original_gym(root)


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    if len(argv)!=2:
        raise ValueError("F45_USAGE: script.py /original/Gymnasium /tmp/report.json")
    root=Path(argv[0]).resolve(strict=True)
    dest=Path(argv[1]).resolve()
    if dest.is_relative_to(root):
        raise ValueError("F45_REPORT_INSIDE_PINNED_GYMNASIUM_REFUSED")
    try:
        gym,git=original_gym(root)
    except (ImportError,FileNotFoundError) as e:
        raise RuntimeError("F45_ORIGINAL_RUNTIME_BLOCKED") from e
    start=time.perf_counter()
    fit=frozen_fit(gym)
    trained=time.perf_counter()
    report=assess(gym,fit,SOURCE)
    evaluated=time.perf_counter()
    original_gym(root)
    if git(root,"status","--porcelain=v1","--untracked-files=all","--ignored=matching"):
        raise ValueError("F45_ORIGINAL_SOURCE_CHANGED")
    if report["classification"]!="F45_ORIGINAL_RUNTIME_UNVERIFIED":
        raise ValueError("F45_FAKE_ORIGINAL_LABEL_REFUSED")
    report["training_and_fit_seconds"]=trained-start
    report["original_evaluation_seconds"]=evaluated-trained
    report["classification"]=(
        "F45_DEV_SIGNAL_UNVERIFIED" if report["frozen_conditions_met"]
        else "F45_DEV_NO_GO")
    report["report_sha256"]=digest({k:v for k,v in report.items() if k!="report_sha256"})
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(canonical(report)+b"\n")
    print("F45_ORIGINAL_CAUSAL_TOURNAMENT_DEV="+report["classification"]+
          " report_sha256="+report["report_sha256"])
    print("F45_COMMON_TRAINING_SHA256="+report["training_sha256"]+
          " transitions="+str(report["train_transitions"]))
    print("F45_STRONGEST="+strongest_display(report)+
          " candidate_gain="+str(report["candidate_mean_gain"])+
          " wins_ge10="+str(report["candidate_seed_wins_ge10"])+
          " decision_ratio="+str(report["candidate_decision_ns_ratio_to_strongest"]))
    return report


def strongest_display(report):
    return report["strongest_conventional"]


if __name__=="__main__":
    main()

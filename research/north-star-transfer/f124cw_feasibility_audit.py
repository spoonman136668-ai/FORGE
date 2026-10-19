"""F124-CW source-free exact identifiability + sequence-learning headroom.

Neither the source law nor records from F124-CU, F124-CR or older scientific
first-use cohorts are read/imported. Mechanistic synthetic *engineering*
diagnostics only; no prospective scientific source IDs or private oracles.
Design frozen before source fixture at 69d7ac22c8e869075e60df6c36562e152ec4a19b.

Two synthetic grammar families each contain exactly 256 causal functions.
Finite version-space enumeration tests information sufficiency *conditional
on that grammar*. A separate frozen 45-epoch BPTT vs 135-epoch stress probe
tests optimization headroom but cannot prove representational impossibility.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124ct_sequence_protocol as public
import f124ct_attentive_causal_memory as attentive
import f124ct_gated_sequence_control as gated

REGIMES=("dense","sparse")
SEEDS=(0,1,2,3)
BUDGETS=(2,4,8,12,24)
ROLES=("alpha","beta","gamma")
HYPOTHESES=tuple((a,b) for a in range(16) for b in range(16))
TRIALS=24
CHECK=8
TEST=8

def require(ok,reason):
    if not ok:raise ValueError("F124CW_"+reason)

def rotate(x):
    return ((x<<1)|(x>>3))&15

def rare(target,source,event):
    return bool(target=="alpha" and source=="gamma" and event==0)

def grammar(regime,target,source,event,target_cur,target_lag,source_cur,source_lag,keys):
    """Unconsumed, small explicit toy grammar; not actual prior source laws."""
    require(regime in REGIMES and len(keys)==2 and
            all(type(x) is int and 0<=x<16 for x in
            (event,target_cur,target_lag,source_cur,source_lag,*keys)),
            "SOURCEFREE_GRAMMAR_INPUT")
    nonlinear=((3*source_cur + target_lag + event)&15)^rotate(target_cur)
    if regime=="dense":
        k=keys[1] if (event&1) else keys[0]
    else:
        k=keys[1] if rare(target,source,event) else keys[0]
    return nonlinear^k

def episode(rng,regime,keys):
    initial={name:[rng.randrange(16),rng.randrange(16)] for name in ROLES}
    actual=copy.deepcopy(initial)
    events=[]
    for _ in range(public.STEPS_PER_EPISODE):
        target=rng.choice(ROLES)
        source=rng.choice(tuple(k for k in ROLES if k!=target))
        e=rng.randrange(16)
        t,l=actual[target];s,h=actual[source]
        y=grammar(regime,target,source,e,t,l,s,h,keys)
        events.append({"target":target,"source":source,"event":e,"observed":y})
        actual[target]=[y,t]
    return {"initial":initial,"events":events}

def fixture(regime,seed):
    require(regime in REGIMES and type(seed) is int and seed in SEEDS,
            "FROZEN_MECHANISM_SEED")
    rng=random.Random(1249100+seed*791+REGIMES.index(regime)*17161)
    keys=(rng.randrange(16),rng.randrange(16))
    train=[episode(rng,regime,keys) for _ in range(TRIALS)]
    veto=[episode(rng,regime,keys) for _ in range(CHECK)]
    holdout=[episode(rng,regime,keys) for _ in range(TEST)]
    public.validate(train,TRIALS)
    public.validate(veto,CHECK)
    public.validate(holdout,TEST)
    return keys,train,veto,holdout

def replay(ep,regime,keys):
    state={r:list(pair) for r,pair in ep["initial"].items()}
    outputs=[]
    for row in ep["events"]:
        t=row["target"];source=row["source"];e=row["event"]
        old=state[t]
        sc,sl=state[source]
        value=grammar(regime,t,source,e,old[0],old[1],sc,sl,keys)
        outputs.append(value)
        state[t]=[value,old[0]]
    return outputs

def compatible(ep,regime,keys):
    expected=[x["observed"] for x in ep["events"]]
    return replay(ep,regime,keys)==expected

def version_space(fit,regime):
    return [h for h in HYPOTHESES
            if all(compatible(ep,regime,h) for ep in fit)]

def heldout_disagreement(survivors,heldout,regime):
    # Fraction of ordered heldout events with more than one possible
    # prediction under grammar-consistent hypotheses, fully autoregressive.
    guesses=[[replay(ep,regime,keys) for ep in heldout] for keys in survivors]
    event_positions=0
    divergent=0
    for i in range(len(heldout)):
        for t in range(public.STEPS_PER_EPISODE):
            possible={run[i][t] for run in guesses}
            event_positions+=1
            divergent+=len(possible)>1
    return divergent,event_positions

def evidence(regime,seed,budget):
    keys,fit,check,heldout=fixture(regime,seed)
    surviving=version_space(fit[:budget],regime)
    require(keys in surviving and len(surviving)>=1,"TRUE_CAUSAL_LAW_DROPPED")
    disagreement,total=heldout_disagreement(surviving,heldout,regime)
    witnessed=sum(rare(step["target"],step["source"],step["event"])
                  for ep in fit[:budget] for step in ep["events"])
    successes=sum(all(compatible(ep,regime,guess) for ep in heldout)
                  for guess in surviving)
    # An exact solution exists for this *given* synthetic grammar, regardless
    # of any learner's expressivity or optimizer.
    return {"regime":regime,"seed":seed,"FIT_episode_budget":budget,
      "observed_supervised_events":budget*public.STEPS_PER_EPISODE,
      "known_grammar_hypotheses":len(HYPOTHESES),
      "consistent_hypotheses_after_sequential_FIT":len(surviving),
      "exactly_identified_under_known_grammar":len(surviving)==1,
      "rare_intervention_observations":witnessed,
      "indeterminate_heldout_event_positions":disagreement,
      "heldout_event_positions":total,
      "hypotheses_matching_all_eight_heldout_episodes":successes,
      "source_unknown_to_model":True,
      "synthetic_engineering_only":True,
      "consumed_scientific_source_used":False}

def neural_diagnostic(regime,epochs):
    require(regime in REGIMES and epochs in (45,135),
            "PRESPECIFIED_OPTIMIZATION_STRESS")
    keys,fit,check,heldout=fixture(regime,0)
    out=[]
    for arm,mod in (("attentive",attentive),("gated",gated)):
        old=public.EPOCHS
        try:
            public.EPOCHS=epochs
            begin=time.process_time_ns()
            model,receipt=mod.train(fit,check)
            cpu=time.process_time_ns()-begin
        finally:
            public.EPOCHS=old
        accepted=bool(receipt["natural_model_admission"])
        # For mechanism diagnosis ONLY, score unadmitted provisional network
        # by *identical frozen training* on the full FIT, not by privately
        # peeking at sources. Failing CHECK cannot magically be reported as a
        # legitimate admitted model. If unadmitted, do not force native work.
        if accepted:
            exact=sum(mod.predict_sequence(model,ep)==
                  [row["observed"] for row in ep["events"]] for ep in heldout)
            trained_exact=sum(mod.predict_sequence(model,ep)==
                  [row["observed"] for row in ep["events"]] for ep in fit)
        else:
            exact=None;trained_exact=None
        out.append({
          "regime":regime,"arm":arm,"full_sequence_training_epochs":epochs,
          "FIT_episode_count":len(fit),"CHECK_veto_only_episodes":len(check),
          "full_BPTT":True,
          "FIT_start_bce":receipt["initial_FIT_bit_cross_entropy"],
          "FIT_end_bce":receipt["final_FIT_bit_cross_entropy"],
          "relative_FIT_loss_reduction":receipt["FIT_relative_loss_reduction"],
          "FIT_bit_errors":receipt["FIT_bit_errors"],
          "CHECK_veto_bit_errors":receipt["CHECK_bit_errors"],
          "natural_admission":accepted,
          "admitted_heldout_full_episodes_exact_of_eight":exact,
          "admitted_fit_full_episodes_exact_of_24":trained_exact,
          "complete_training_OS_CPU_ns":cpu,
          "full_process_peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
          "used_consumed_science":False,
          "sourcefree_mechanism_only":True,
          "higher_epochs_are_diagnostic_not_scientific_retuning":epochs>45
        })
    return out

def interpret(info,learners):
    last=[x for x in info if x["FIT_episode_budget"]==24]
    by_regime={}
    for regime in REGIMES:
        v=[x for x in last if x["regime"]==regime]
        model=[x for x in learners if x["regime"]==regime]
        identifiable=sum(x["exactly_identified_under_known_grammar"] for x in v)
        by_regime[regime]={
          "known_grammar_fully_identified_seeds_of_four":identifiable,
          "known_grammar_unidentifiable_seeds":len(v)-identifiable,
          "survivor_counts_at_24":[x["consistent_hypotheses_after_sequential_FIT"] for x in v],
          "rare_intervention_counts_at_24":[x["rare_intervention_observations"] for x in v],
          "frozen_45_epoch_attentive_admitted":next(x["natural_admission"]
                         for x in model if x["arm"]=="attentive" and x["full_sequence_training_epochs"]==45),
          "frozen_45_epoch_gated_admitted":next(x["natural_admission"]
                         for x in model if x["arm"]=="gated" and x["full_sequence_training_epochs"]==45),
          "conclusion":"Identification is ONLY relative to a privileged known synthetic grammar. Neural models trained from episodes have no access to that grammar; a negative neural result cannot alone distinguish optimizer from representational capacity."
        }
    return {
      "schema":"mass.f124cw.engineering-feasibility-interpretation.v1",
      "full_FIT_episodes":TRIALS,"CHECK_veto_only":CHECK,
      "sequential_event_observations":TRIALS*public.STEPS_PER_EPISODE,
      "mechanism_only":True,
      "regime_results":by_regime,
      "scientific_transfer_proven":False,
      "complete_CPU_RSS_nonregression_proven":False,
      "prospective_firstuse_cases_consumed":0,
      "learning_information_identified_for_real_unknown_causal_source":False,
      "authoritative_limit":"No result with toy privileged grammar can prove actual unknown-family causal identifiability, model representation sufficiency or optimization failure; original L/M negatives are not retested.",
      "next_scientific_admission":"Only if a new, independently source-neutral feasibility threshold validates natural sequence-trained role binding and adequate intervention coverage; no source birth in this gate."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    require(not args.out.exists(),"DO_NOT_OVERWRITE_EVIDENCE")
    all_info=[evidence(regime,seed,budget) for regime in REGIMES
             for seed in SEEDS for budget in BUDGETS]
    all_neural=[row for regime in REGIMES for epochs in (45,135)
                for row in neural_diagnostic(regime,epochs)]
    report={
      "schema":"mass.f124cw.original-sourcefree-feasibility-engineering.v1",
      "preregistered_seed_count":len(SEEDS),"preregistered_budget_count":len(BUDGETS),
      "all_40_exact_version_space_diagnostics":all_info,
      "all_8_sourcefree_full_sequence_training_diagnostics":all_neural,
      "interpretation":interpret(all_info,all_neural),
      "source_origin":"SYNTHETIC_PUBLIC_ENGINEERING_NOT_ACTUAL_SCIENTIFIC_SOURCE",
      "private_prior_sources_imported":False,
      "protected_source_opened":False,"scientific_acceptance":False}
    args.out.mkdir(parents=True)
    (args.out/"feasibility-full.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("F124CW_ORIGINAL_ENGINEERING_STUDY=COMPLETE")
    print("F124CW_PREBIRTH_VERSION_SPACE_CHECKS=40")
    print("F124CW_SOURCEFREE_NEURAL_TRAININGS=8")
    for regime,x in report["interpretation"]["regime_results"].items():
        print("F124CW_"+regime.upper()+"_IDENTIFIED_AT_24="+str(x["known_grammar_fully_identified_seeds_of_four"])+"/4")
        print("F124CW_"+regime.upper()+"_VERSION_COUNTS="+json.dumps(x["survivor_counts_at_24"]))
        print("F124CW_"+regime.upper()+"_NATURAL_ADMISSION_45="+json.dumps(
              {"attentive":x["frozen_45_epoch_attentive_admitted"],
               "gated":x["frozen_45_epoch_gated_admitted"]}))
    print("F124CW_NEW_SCIENTIFIC_SOURCES_CONSUMED=0")
    print("F124CW_SCIENTIFIC_ACCEPTANCE=FALSE")

if __name__=="__main__":main()

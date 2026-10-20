"""F124-DG fixed source-free budgeted causal query experiment.

All three FIT solvers share the exact 24 FIT and eight CHECK episodes,
the same public meta training frequencies, and the identical 0/16/48
source-free extra-intervention query allowance. Source/oracle responses
are explicitly metered and never accessible from fit model modules.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124dg_new_sourcefree_oracle as world
import f124dg_meta_rank_learner as learned
import f124dg_independent_active_control as peer

ARMS=("meta_rank","independent_meta_rank","lex_exact_rank")
BUDGETS=(0,16,48)

def require(ok,reason):
    if not ok:raise RuntimeError("F124DG_TRIAL_"+reason)

def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def sourcefree_case(family,seed,arm,budget):
    require(family in world.FAMILIES and seed in world.SEEDS and
            arm in ARMS and budget in BUDGETS,"PREREGISTERED_ARM_SOURCE_AND_BUDGET_ONLY")
    public=world.born(family,seed)
    fit,check,hold=(public[k] for k in ("FIT","CHECK","HELDOUT"))
    for ep in fit+check+hold:learned.check_ep(ep)
    meta=world.public_meta_pair_frequencies()
    chosen=[]
    def oracle(pair):
        require(len(chosen)<budget and pair not in chosen and type(pair) is int
                and 0<=pair<256,"ADDITIONAL_INFORMATION_EXACT_BUDGET")
        chosen.append(pair)
        return world.response(family,seed,pair)
    if arm=="meta_rank":
        model,receipt=learned.learn(fit,budget,oracle,meta)
        scored=learned.score
        trajectory=learned.trajectory
    else:
        model,receipt=peer.fit(fit,budget,oracle,meta,lex_only=(arm=="lex_exact_rank"))
        scored=peer.score
        trajectory=peer.trajectory
    require(len(chosen)==budget,"FROZEN_0_16_48_EXTRA_ORACLE_RESPONSES")
    original=learned.supervised_rows(fit)
    observed=learned.basis([(x,0) for x,_ in original])
    unidentified=next((x for x in range(256) if learned.independent(observed,x)),None)
    null_witness=False
    if unidentified is not None:
        augmented=learned.basis([(x,0) for x,_ in original]+[(unidentified,1)])
        explicit_w=learned.solve(augmented)
        null_witness=bool(
            learned.reconstruct(explicit_w,unidentified)==1 and
            all(learned.reconstruct(explicit_w,x)==0 for x,_ in original))
        require(null_witness,"SOURCEFREE_EXPLICIT_FIT_NULLSPACE_WITNESS")
    checks=[scored(model,ep) for ep in check]
    natural=all(z["correct"] for z in checks)
    pos=[scored(model,ep) for ep in hold]
    neg=[scored(model,world.matched_negative(ep)) for ep in hold]
    require(all(z["native_events"]==8 for z in checks+pos+neg),
            "COMPLETE_AUTOREGRESSIVE_EVENTS")
    # A full posterior rank 163 is independent information sufficiency in
    # the KNOWN degree<=4 grammar only; it says nothing about arbitrary laws.
    return {
        "schema":"mass.f124dg.frozen-sourcefree-budgeted-active-causal-trial.v1",
        "family":family,"seed":seed,"arm":arm,"extra_oracle_budget":budget,
        "FIT_hash":sha(fit),"CHECK_hash":sha(check),"HELDOUT_hash":sha(hold),
        "same_public_meta_score_sha256":sha(meta),
        "FIT_episodes":24,"CHECK_veto_episodes":8,"HELDOUT_positive_episodes":8,
        "original_FIT_rank":len(observed),"full_hypothesis_dimension":163,
        "explicit_nonzero_nullspace_polynomial_on_unobserved_pair":null_witness,
        "unobserved_counterfactual_pair":unidentified,
        "new_oracle_queries_consumed":len(chosen),"queries_distinct":len(set(chosen))==len(chosen),
        "final_rank":receipt["final_rank"],
        "rank_gain_from_extra_information":receipt["final_rank"]-len(observed),
        "natural_CHECK_admission":natural,
        "CHECK_exact_episodes_of_8":sum(x["correct"] for x in checks),
        "diagnostic_HELDOUT_exact_positives_of_8":sum(x["correct"] for x in pos),
        "diagnostic_HELDOUT_hard_false_positive_of_8":sum(x["correct"] for x in neg),
        "diagnostic_HELDOUT_bit_errors":sum(x["bit_errors"] for x in pos),
        "admitted_HELDOUT_exact_positives":sum(x["correct"] for x in pos) if natural else None,
        "admitted_HELDOUT_hard_false_positive":sum(x["correct"] for x in neg) if natural else None,
        "fitting":receipt,"oracle_is_additional_information":True,
        "hypothesis_known_degree4_163":"same for all comparators",
        "sourcefree_hidden_coefficients_never_passed_to_models":True,
        "science_original_firstuse_consumed":False,
        "source_origin":"SYNTHETIC_INTERNAL_NOT_EXTERNAL_SCIENCE",
        "science_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",required=True,choices=world.FAMILIES)
    p.add_argument("--seed",required=True,type=int)
    p.add_argument("--arm",required=True,choices=ARMS)
    p.add_argument("--budget",required=True,type=int)
    v=p.parse_args()
    print(json.dumps(sourcefree_case(v.family,v.seed,v.arm,v.budget),sort_keys=True))

if __name__=="__main__":main()

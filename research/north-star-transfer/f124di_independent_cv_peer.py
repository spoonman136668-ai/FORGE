"""F124-DI independently implemented full CV structural prior competitor.

Same 24 public FIT episodes, first 20 training + 4 internal CV episodes,
10 source-neutral input pairs, 4 degree limits, full independently
optimized 163-feature exact GF2 fitting. NO candidate/source imports and
no oracle/heldout tuning. A valid strongest trained peer, not a dummy.
"""
from __future__ import annotations
import itertools
import f124de_independent_full_anf as peer

ROLES=("alpha","beta","gamma")
PAIRS=tuple(itertools.combinations(range(5),2))
DEGREES=(1,2,3,4)
TRUNCMASK={degree:sum(1<<i for i,mono in enumerate(peer.MONO)
                        if mono.bit_count()<=degree) for degree in DEGREES}

def need(ok,why):
    if not ok:raise RuntimeError("F124DI_EQUAL_PEER_"+why)

def fit_model(episodes,inputs,degree):
    # Separate source parser and elimination from the learned candidate.
    samples=[]
    for ep in episodes:
        need(set(ep)=={"initial","events"} and len(ep["events"])==8
             and set(ep["initial"])==set(ROLES),"PUBLIC_COMPLETE_TRAJECTORY")
        state={k:list(v) for k,v in ep["initial"].items()}
        for e in ep["events"]:
            a=state[e["target"]];b=state[e["source"]]
            samples.append((a[0],a[1],b[0],b[1],e["event"],e["observed"]))
            state[e["target"]]=[e["observed"],a[0]]
    eqs=[(peer.encoded_anf(x[inputs[0]]+(x[inputs[1]]<<4))&TRUNCMASK[degree],x[5])
         for x in samples]
    solved=[]
    for bit in range(4):
        answer,rank=peer.solve(eqs,bit)
        if answer is None:return None
        solved.append(answer)
    model={"columns":inputs,"truth_bitplanes":tuple(peer.compile_bitplane(q) for q in solved),
           "learned_coefficients":tuple(solved)}
    need(all(peer.compute(model,x)==x[5] for x in samples),"FIT_UNDERDETERMINED_SOLVER")
    return model

def fit(FIT):
    need(type(FIT) is list and len(FIT)==24,"SAME_ALL_TWENTY_FOUR_FIT")
    fitdata=FIT[:20];cv=FIT[20:]
    champion=None;tested=0
    # Same 40 structural options, full learned underdetermined polynomial
    # coefficients; selection uses FIT-local CV and never CHECK.
    for degree in DEGREES:
        for pair in PAIRS:
            model=fit_model(fitdata,pair,degree)
            if model is None:continue
            tested+=1
            scored=[peer.score(model,episode) for episode in cv]
            error=sum(z["bit_errors"] for z in scored)
            correct=sum(z["exact"] for z in scored)
            complexity=sum(q.bit_count() for q in model["learned_coefficients"])
            rank=(error,-correct,complexity,degree,pair)
            if champion is None or rank<champion[0]:
                champion=(rank,degree,pair,error,correct)
    if champion is None:
        return None,{"FIT_fitted":False,"candidate_structural_priors_tested":0}
    _,degree,pair,error,correct=champion
    model=fit_model(FIT,pair,degree)
    if model is None:return None,{"FIT_fitted":False,"structural_prior_not_refittable":True,
              "learned_degree":degree,"learned_pair":list(pair),
              "CV_bit_errors":error,"CV_exact_full_trajectories_of_4":correct,
              "trained_candidate_structures":tested}
    return model,{"FIT_fitted":True,"learned_degree":degree,
         "learned_pair":list(pair),"CV_bit_errors":error,
         "CV_exact_full_trajectories_of_4":correct,
         "trained_candidate_structures":tested,
         "full_independent_163_term_solver":True,
         "FIT_complete_event_rows":192,"new_oracle_answers":0,
         "used_CHECK_or_scientific_heldout_to_tune":False}

def score(model,episode):
    return peer.score(model,episode)

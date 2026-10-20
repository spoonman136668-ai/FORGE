"""F124-DI trained complexity prior using ONLY 24 available FIT trajectories.

No meta labels, new oracle queries or hidden source generator. It learns a
degree/wiring preference via held-out-FIT whole-sequence cross-validation:
first 20 FIT episodes for training, final 4 FIT episodes as CV, and refit
all 24 using ONLY the chosen structural degree/pair. This does not resolve
all information-theoretic nullspaces and cannot guarantee unseen accuracy.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import f124de_sparse_crossbit_learner as frozen

ROLES=("alpha","beta","gamma")
PAIRS=tuple(itertools.combinations(range(5),2))
DEGREES=(1,2,3,4)
MASKS={d:sum(1<<i for i,x in enumerate(frozen.MONOMIALS) if x.bit_count()<=d)
       for d in DEGREES}

def need(ok,why):
    if not ok:raise RuntimeError("F124DI_LEARNED_PRIOR_"+why)

def rows(episodes):
    res=[]
    for ep in episodes:
        need(set(ep)=={"initial","events"} and set(ep["initial"])==set(ROLES)
             and len(ep["events"])==8,"PUBLIC_FULL_TRAJECTORY")
        state={role:list(values) for role,values in ep["initial"].items()}
        for e in ep["events"]:
            need(set(e)=={"target","source","event","observed"}
                 and e["target"] in ROLES and e["source"] in ROLES
                 and e["target"]!=e["source"],"PUBLIC_CAUSAL_EVENT")
            own=state[e["target"]];other=state[e["source"]]
            res.append(((own[0],own[1],other[0],other[1],e["event"]),e["observed"]))
            state[e["target"]]=[e["observed"],own[0]]
    return res

def fit_pair(episodes,pair,degree):
    samples=rows(episodes)
    mask=MASKS[degree]
    training=[(frozen.features(x[pair[0]]|(x[pair[1]]<<4))&mask,y) for x,y in samples]
    coef=[]
    for bit in range(4):
        p,rank=frozen.eliminate(training,bit)
        if p is None:return None
        coef.append(p)
    model={"wiring":pair,"planes":frozen.compile_lut(tuple(coef)),
           "fitted_coefficients":tuple(coef)}
    need(all(frozen.predict_raw(model,x)==y for x,y in samples),
         "MODELED_TRAJECTORY_INTERPOLATION")
    return model

def learn(FIT):
    need(type(FIT) is list and len(FIT)==24,
         "EXACT_TWENTY_FOUR_NO_EXTRA_ORACLE_TRAINING_TRAJECTORIES")
    training,internal_validation=FIT[:20],FIT[20:]
    best=None;candidates=0
    for d in DEGREES:
        for p in PAIRS:
            model=fit_pair(training,p,d)
            if model is None:continue
            candidates+=1
            # INTERNAL FIT holdout is used only to learn an inductive
            # prior. Never touch CHECK or future heldout during selection.
            scores=[frozen.score(model,e) for e in internal_validation]
            errors=sum(x["bit_errors"] for x in scores)
            exact=sum(x["exact"] for x in scores)
            complexity=sum(x.bit_count() for x in model["fitted_coefficients"])
            cost=(errors,-exact,complexity,d,p)
            if best is None or cost<best[0]:
                best=(cost,d,p,errors,exact)
    if best is None:return None,{"FIT_fitted":False,"candidate_structural_priors_tested":0}
    _,degree,pair,errors,exact=best
    refit=fit_pair(FIT,pair,degree)
    if refit is None:
        return None,{"FIT_fitted":False,"structural_prior_not_refittable":True,
                     "learned_degree":degree,"learned_pair":list(pair),
                     "CV_bit_errors":errors,
                     "CV_exact_full_trajectories_of_4":exact,
                     "trained_candidate_structures":candidates}
    return refit,{"FIT_fitted":True,"learned_degree":degree,"learned_pair":list(pair),
          "source_neutral_degree_from_20_train_4_CV_only":True,
          "CV_bit_errors":errors,"CV_exact_full_trajectories_of_4":exact,
          "trained_candidate_structures":candidates,
          "FIT_complete_event_rows":192,
          "new_oracle_answers":0,
          "used_CHECK_or_scientific_heldout_to_tune":False}

def score(model,ep):
    return frozen.score(model,ep)

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()

"""F124-AY evaluator-only structural witness and model-only fitting diagnostics.

True inverse is used *only* inside witness(), never by probe(). Any nonzero
Boolean third derivative is a rigorous degree>2 impossibility certificate.
"""
from __future__ import annotations
import random
import f124ay_source_only as source
import f124ax_sparse_quadratic as quad
import f124am_example_affine_learner as bits

TRIALS=256
def need(ok,tag):source.need(ok,"DIAGNOSTIC_"+tag)

def asbits(n):return [(n>>i)&1 for i in range(16)]
def asint(v):return bits.integer(v)

def witness(operator):
    """Evaluator-only truthful black-box source operator; never model input."""
    cfg=source.frozen()["cohort"]["structural_witness"]
    need(operator in source.OPERATORS["TRAIN"],"EVALUATOR_TRAIN_OPERATOR_ONLY")
    def inverse(n):return asint(source.relation(asbits(n),operator,True))
    zero=inverse(0)
    single=[inverse(1<<i) for i in range(16)]
    interacting=[]
    for i in range(16):
        for j in range(i+1,16):
            derivative=zero^single[i]^single[j]^inverse((1<<i)|(1<<j))
            if derivative:interacting.append([i,j])
    nonzero_thirds=[]
    for triple in cfg["triple_bit_sets"]:
        for base in cfg["base_outputs"]:
            derivative=0
            for subset in range(8):
                x=base
                for index in range(3):
                    if subset&(1<<index):x^=1<<triple[index]
                derivative^=inverse(x)
            if derivative:nonzero_thirds.append({"bits":triple,"base":base,"difference":derivative})
    return {"operator_family":"affine" if operator.startswith("affine_") else "feistel",
            "distinct_nonzero_second_difference_pairs_at_zero":len(interacting),
            "first_interactions":interacting[:12],
            "nonzero_third_derivatives":len(nonzero_thirds),
            "first_third_witnesses":nonzero_thirds[:6],
            "proven_outside_degree2":bool(nonzero_thirds),
            "proven_outside_AX_2pair_class":bool(nonzero_thirds) or len(interacting)>2,
            "oracle_evaluator_only":True}

def probe(public,nonce):
    """Exact 256-trial AX sparse inverse search and ordered rejection census."""
    need(len(public) in (48,96),"48_OR_96_RESPONSES_ONLY")
    total=len(public)
    fit_n=40 if total==48 else 80
    check_n=total-fit_n
    samples=public[:fit_n]
    rng=random.Random("F124AX_SPARSE_Q_PUBLIC_ONLY:"+str(nonce)
                      if total==48 else "F124AY_DIAG_96:"+str(nonce))
    ranked=[]
    for _ in range(TRIALS):
        pairs=tuple(quad.PAIRS[k] for k in rng.sample(range(len(quad.PAIRS)),2))
        ids=rng.sample(range(fit_n),quad.FEATURES)
        coefficients=quad.solve([samples[i] for i in ids],pairs)
        if coefficients is None:continue
        wrong=sum((quad.transform(d["output_bits"],coefficients,pairs)^
                   asint(d["input_bits"])).bit_count() for d in samples)
        ranked.append((wrong,coefficients,pairs))
    ranked.sort(key=lambda t:(t[0],t[1],t[2]))
    best=ranked[0][0] if ranked else None
    checks=[]
    passing_fit=passing_check=passing_bijection=0
    if total==48:
        for wrong,coeff,pairs in ranked:
            if wrong>quad.BUDGET:break
            passing_fit+=1
            check=sum(16-(quad.transform(x["output_bits"],coeff,pairs)^
                         asint(x["input_bits"])).bit_count()
                      for x in public[fit_n:])
            checks.append(check)
            if check>=quad.CHECK_MIN:
                passing_check+=1
                if quad.bijective(coeff,pairs):passing_bijection+=1
    else:
        # 96 is diagnostic only: do not apply AX 48-sample threshold to a
        # different denominator. Report normalized fit and CHECK quality.
        if ranked:
            _,coeff,pairs=ranked[0]
            checks.append(sum(16-(quad.transform(x["output_bits"],coeff,pairs)^
                                  asint(x["input_bits"])).bit_count()
                              for x in public[fit_n:]))
    result={"public_responses":total,"fit_rows":fit_n,"check_rows":check_n,
            "attempts":TRIALS,"rank_valid_fits":len(ranked),
            "best_fit_wrong_bits":best,
            "best_fit_error_per_input_bit":None if best is None else best/(fit_n*16),
            "best_observed_public_CHECK_bits":max(checks) if checks else None,
            "best_observed_public_CHECK_accuracy":max(checks)/(check_n*16)
              if checks else None,
            "fit_budget_passing":passing_fit if total==48 else None,
            "CHECK_threshold_passing":passing_check if total==48 else None,
            "full_domain_bijection_passing":passing_bijection if total==48 else None,
            "first_hard_blocker":("NO_RANK" if not ranked else
                "FIT_RESIDUAL" if total==48 and passing_fit==0 else
                "CHECK" if total==48 and passing_check==0 else
                "BIJECTION" if total==48 and passing_bijection==0 else
                "ADMITTED" if total==48 else "96_DIAGNOSTIC_ONLY"),
            "oracle_or_operator_seen_by_model":False,
            "fits_are_sourceblind":True}
    if total==48:
        fitted,metadata=quad.fit(public,nonce)
        need((fitted is not None)==bool(passing_bijection),
             "EXACT_AX_ALGORITHM_REPLAY_NOT_CONSISTENT")
        result["original_AX_admitted"]=fitted is not None
        result["AX_max_extra_model_bits"]=metadata["transient_task_coefficient_bits"]
    else:
        result["original_AX_admitted"]=None
        result["AX_max_extra_model_bits"]=quad.FEATURES*16+2*8
    return result

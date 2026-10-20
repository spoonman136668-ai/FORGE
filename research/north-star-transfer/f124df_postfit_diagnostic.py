"""F124-DF source-free mathematical identifiability/selection diagnosis.

This is a post-learning forensic analyzer, NEVER imported by the frozen
F124-DE candidate or equally trained peer. All secrets are consulted only
AFTER model train+CHECK+heldout. No scientific source original touched.
"""
from __future__ import annotations
import itertools
import f124de_sparse_crossbit_learner as math

def require(ok,msg):
    if not ok:raise RuntimeError("F124DF_DIAG_"+msg)

def rref_feature_pivots(rows,pair):
    # 163 degree<=4 polynomial features per two-nibble causal input.
    basis={}
    for inputs,_ in rows:
        value=inputs[pair[0]]+(inputs[pair[1]]<<4)
        r=math.features(value)
        while r:
            low=r&-r;i=low.bit_length()-1
            if i in basis:r^=basis[i]
            else:
                basis[i]=r
                break
    return basis

def explicit_nullspace_witness(rows,pair):
    pivot=rref_feature_pivots(rows,pair)
    free=next((col for col in range(math.WIDTH) if col not in pivot),None)
    if free is None:
        return {"rank":len(pivot),"nullity":0,"witness_exists":False,
                "different_unobserved_input":None}
    null=1<<free
    for bit in sorted(pivot,reverse=True):
        if (pivot[bit]&null).bit_count()&1:null|=1<<bit
    for inputs,_ in rows:
        raw=inputs[pair[0]]+(inputs[pair[1]]<<4)
        require((null&math.features(raw)).bit_count()%2==0,
                "WITNESS_NOT_ZERO_ON_PUBLIC_FIT")
    example=next((x for x in range(256)
        if (null&math.features(x)).bit_count()%2==1),None)
    require(example is not None,"NONZERO_NULLPOLYNOMIAL_IDENTICALLY_ZERO")
    return {"rank":len(pivot),"nullity":math.WIDTH-len(pivot),
            "witness_exists":True,"nullspace_polynomial_bitmask_hex":hex(null),
            "different_unobserved_input":example,
            "unobserved_witness_proves_nonidentification":True}

def algebraic_normal_form_of_truth(oracular_pair_law):
    degrees=[];termcounts=[];tables=[]
    for bit in range(4):
        values=[(oracular_pair_law(pair&15,pair>>4)>>bit)&1
                for pair in range(256)]
        for axis in range(8):
            for index in range(256):
                if index>>axis&1:values[index]^=values[index^(1<<axis)]
        terms=[i for i,value in enumerate(values) if value]
        degree=max((i.bit_count() for i in terms),default=0)
        degrees.append(degree);termcounts.append(len(terms))
        tables.append(terms)
    return {"exact_unrestricted_256_pair_ANF_degrees":degrees,
            "max_true_algebraic_degree":max(degrees),
            "source_is_representable_with_degree4":all(x<=4 for x in degrees),
            "true_polynomial_monomial_count_each_output_bit":termcounts}

def diagnose_after_scoring(FIT,hidden_true_wires,oracle_law,
                           selected_wires,model_fitted,admitted):
    rows=math.training_rows(FIT)
    pair_results=[]
    for pair in itertools.combinations(range(5),2):
        feats=[(math.features(x[pair[0]]+(x[pair[1]]<<4)),target)
               for x,target in rows]
        rank=len(rref_feature_pivots(rows,pair))
        consistent=all(math.eliminate(feats,out)[0] is not None
                       for out in range(4))
        pair_results.append({"pair":list(pair),"rank":rank,
                             "FIT_consistent_all_four_bits":consistent})
    if len(hidden_true_wires)!=2:
        return {"post_model_source_wiring":list(hidden_true_wires),
                "outside_two_register_hypothesis":True,
                "model_fitted":model_fitted,"CHECK_admitted":admitted,
                "consistent_pair_count":sum(q["FIT_consistent_all_four_bits"] for q in pair_results),
                "all_ten_pair_FIT_feasibility":pair_results,
                "novel_cross_pair_oracle_degree":"OUTSIDE_TWO_REGISTER_DOMAIN"}
    true_pair=tuple(hidden_true_wires)
    witness=explicit_nullspace_witness(rows,true_pair)
    oracle=algebraic_normal_form_of_truth(oracle_law)
    consistent_true=next(q["FIT_consistent_all_four_bits"] for q in pair_results
                         if q["pair"]==list(true_pair))
    require(consistent_true==oracle["source_is_representable_with_degree4"],
            "INDEPENDENT_TRUE_ORACLE_AND_FIT_FEASIBILITY_CONFLICT")
    return {"post_model_source_wiring":list(true_pair),
            "post_model_selected_wiring":list(selected_wires) if selected_wires is not None else None,
            "selected_input_pair_matches_true_source":tuple(selected_wires)==true_pair if selected_wires is not None else None,
            "wrong_pair_selected":tuple(selected_wires)!=true_pair if selected_wires is not None else None,
            "true_pair_FIT_degree4_representable":consistent_true,
            "true_pair_FIT_indeterminacy":witness,
            "independent_sourcefree_256_input_oracle_degree_proof":oracle,
            "all_ten_pair_FIT_feasibility":pair_results,
            "consistent_pair_count":sum(q["FIT_consistent_all_four_bits"] for q in pair_results),
            "source_model_class_representable":oracle["source_is_representable_with_degree4"],
            "model_fitted":model_fitted,"CHECK_admitted":admitted,
            "FIT_complete_solver_failure_observed":not model_fitted and consistent_true,
            "FIT_numerical_optimizer_cannot_be_blamed_if_exact":bool(model_fitted and consistent_true),
            "unambiguous_unique_operator_from_24_FIT":not witness["witness_exists"]}

"""F124-CY one case/arm source-free complete-process causal comparison.

All three models receive the same public FIT/CHECK/heldout episodes. The
source generator supplies no hidden masks or source oracle to any learner.
Synthetic labels are not fed during CHECK/heldout forward recurrence.
No original scientific 924–937 sources or source families are imported.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124cy_sourcefree_fixture as fixture
import f124cy_shared_causal_composition as shared
import f124cy_independent_edge_control as edge
import f124ct_gated_sequence_control as gated
import f124ct_sequence_protocol as protocol

ARMS=("shared","edge_control","gated_recurrent")

def need(ok,msg):
    if not ok:raise ValueError("F124CY_TRIAL_"+msg)

def test(regime,seed,arm):
    need(regime in fixture.REGIMES and seed in (0,1,2,3) and arm in ARMS,
         "FROZEN_SOURCEFREE_ROSTER")
    d=fixture.born(regime,seed)
    fit,check,heldout=d["fit"],d["check"],d["heldout"]
    protocol.HIDDEN=8
    protocol.EPOCHS=45
    if arm=="shared":
        model,receipt=shared.fit(fit,regime)
        score=shared.score
    elif arm=="edge_control":
        model,receipt=edge.train(fit,regime)
        score=edge.score
    else:
        model,receipt=gated.train(fit,check)
        score=lambda model,ep:(
           lambda pred,gold:{
            "correct":pred==gold,
            "bit_errors":sum((x^y).bit_count() for x,y in zip(pred,gold)),
            "native_event_calls":len(pred)})(gated.predict_sequence(model,ep),
                                    [x["observed"] for x in ep["events"]])
    fitted=model is not None
    # CHECK never updates parameters. A complete natural CHECK PASS requires
    # all 8 fully-autoregressive positive trajectories to match, and
    # the recurrent peer has its own stronger default frozen CHECK veto.
    check_rows=[score(model,ep) for ep in check] if fitted else []
    check_pass=bool(fitted and all(v["correct"] for v in check_rows) and
                    (arm!="gated_recurrent" or receipt["natural_model_admission"]))
    positives=[score(model,ep) for ep in heldout] if fitted else []
    negatives=[score(model,fixture.matched_hard_negative(ep)) for ep in heldout] if fitted else []
    need(not fitted or all(v["native_event_calls"]==8 for v in
                 check_rows+positives+negatives),"COMPLETE_EIGHT_EVENT_AUTOREGRESSION")
    result={
      "schema":"mass.f124cy.sourcefree-compositional-role-comparison.v1",
      "regime":regime,"seed":seed,"arm":arm,
      "same_public_FIT_sha256":shared.digest(fit),
      "same_public_CHECK_sha256":shared.digest(check),
      "same_public_HELDOUT_sha256":shared.digest(heldout),
      "FIT_episodes":24,"CHECK_veto_only_episodes":8,"heldout_episodes":8,
      "shared_causal_role_information":True,
      "fitted_parameters_without_oracle":fitted,
      "natural_CHECK_trajectory_admission":check_pass,
      "natural_CHECK_full_trajectories_correct":sum(v["correct"] for v in check_rows),
      "diagnostic_heldout_positive_exact_of_8":sum(v["correct"] for v in positives),
      "diagnostic_heldout_hard_false_positives_of_8":sum(v["correct"] for v in negatives),
      "diagnostic_heldout_bit_errors":sum(v["bit_errors"] for v in positives),
      "admitted_heldout_correct_positives":sum(v["correct"] for v in positives) if check_pass else None,
      "admitted_hard_false_positives":sum(v["correct"] for v in negatives) if check_pass else None,
      "model_training_receipt":receipt,
      "full_rollout_no_early_exit":True,
      "original_source_ids_924_to_937_read":False,
      "synthetic_known_parity_basis_given_to_both_parity_arms":True,
      "privileged_hypothesis_class_declared":True,
      "prospective_scientific_case_consumed":False,
      "science_accepted":False}
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--regime",choices=fixture.REGIMES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    x=p.parse_args()
    print(json.dumps(test(x.regime,x.seed,x.arm),sort_keys=True))

if __name__=="__main__":
    main()

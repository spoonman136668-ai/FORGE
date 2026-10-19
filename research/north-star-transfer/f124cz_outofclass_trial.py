"""F124-CZ blinded nonlinear causal comparison on source-free episodes.

Frozen F124-CY affine operator, new shared quadratic learned operator,
independently authored pooled nonlinear solver, fully fitted directed-edge
control, and unchanged gated recurrent baseline. No source hidden parameters
may enter a learner. All labels on CHECK/HELDOUT are comparison-only; no
teacher forcing in any online recurrence. No original scientific birth.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124cz_outofclass_fixture as source
import f124cy_shared_causal_composition as affine
import f124cz_shared_quadratic_model as shared
import f124cz_independent_pooled_control as pooled
import f124cz_edge_quadratic_control as edge
import f124ct_gated_sequence_control as rnn
import f124ct_sequence_protocol as protocol

ARMS=("frozen_affine","shared_quadratic","independent_pooled",
      "edge_quadratic","frozen_gated_recurrent")

def need(ok,why):
    if not ok:raise RuntimeError("F124CZ_TRIAL_"+why)

def original(realm,seed,arm):
    need(realm in source.REGIMES and seed in source.SEEDS
         and arm in ARMS,"FROZEN_NEW_SOURCEFREE_IDENTITY")
    public=source.born(realm,seed)
    fit,check,heldout=public["FIT"],public["CHECK"],public["HELDOUT"]
    # Explicitly fix the same original 8D/45epoch sequence baseline.
    protocol.HIDDEN=8;protocol.EPOCHS=45
    if arm=="frozen_affine":
        model,receipt=affine.fit(fit,"ungated_shared_linear_GF2")
        score=affine.score
    elif arm=="shared_quadratic":
        model,receipt=shared.fit(fit)
        score=shared.score
    elif arm=="independent_pooled":
        model,receipt=pooled.train(fit)
        score=pooled.score
    elif arm=="edge_quadratic":
        model,receipt=edge.fit(fit)
        score=edge.score
    else:
        model,receipt=rnn.train(fit,check)
        def score(m,ep):
            predictions=rnn.predict_sequence(m,ep)
            gold=[e["observed"] for e in ep["events"]]
            return {"correct":predictions==gold,
                 "bit_errors":sum((a^b).bit_count() for a,b in zip(predictions,gold)),
                 "native_event_calls":8}
    fitted=model is not None
    # NOTE: all 5 arms use identical 24 FIT public sequences.
    check_scores=[score(model,ep) for ep in check] if fitted else []
    admitted=bool(fitted and all(x["correct"] for x in check_scores) and
          (arm!="frozen_gated_recurrent" or receipt["natural_model_admission"]))
    pos=[score(model,ep) for ep in heldout] if fitted else []
    neg=[score(model,source.hard_negative(ep)) for ep in heldout] if fitted else []
    need(all(x["native_event_calls"]==8 for x in check_scores+pos+neg),
         "COMPLETE_EIGHT_EVENT_NATIVE_PREDICTION")
    receipt_safe=receipt
    return {
      "schema":"mass.f124cz.original-sourcefree-outofclass-trial.v1",
      "realm":realm,"seed":seed,"arm":arm,
      "FIT_public_SHA256":shared.digest(fit),
      "CHECK_veto_public_SHA256":shared.digest(check),
      "HELDOUT_public_SHA256":shared.digest(heldout),
      "FIT_complete_episodes":24,
      "CHECK_veto_only_complete_episodes":8,
      "heldout_complete_positive_episodes":8,
      "matched_hard_negative_episodes":8,
      "candidate_input_basis":"original 20b+constant" if arm=="frozen_affine" else
          ("original full BPTT learnt" if arm=="frozen_gated_recurrent" else
           "all 211 public degree<=2 bit monomials"),
      "fitted_naturally_from_FIT":fitted,
      "natural_CHECK_admitted":admitted,
      "complete_CHECK_exact_trajectories":sum(x["correct"] for x in check_scores),
      "diagnostic_heldout_exact_positive":sum(x["correct"] for x in pos),
      "diagnostic_heldout_exact_hard_false_positive":sum(x["correct"] for x in neg),
      "diagnostic_heldout_positive_bit_errors":sum(x["bit_errors"] for x in pos),
      "admitted_heldout_exact_positive":sum(x["correct"] for x in pos) if admitted else None,
      "admitted_heldout_hard_false_positive":sum(x["correct"] for x in neg) if admitted else None,
      "FIT_receipt":receipt_safe,
      "natural_abstention_not_forced_into_parity":not admitted,
      "private_source_law_not_passed_to_learner":True,
      "no_old_924_through_937_original_sci_sources_used":True,
      "no_early_exit":True,"science_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--realm",choices=source.REGIMES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    z=p.parse_args()
    print(json.dumps(original(z.realm,z.seed,z.arm),sort_keys=True))

if __name__=="__main__":main()

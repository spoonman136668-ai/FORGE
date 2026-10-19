"""F124-DA original sourcefree learned-program causal trial.

Every arm gets the same complete 24 FIT, eight veto-only CHECK and eight
heldout sequences, including all role identities and event tokens. No
hidden generator program is passed to learner; CHECK never selects models.
Natural FIT and CHECK abstentions not replaced with fabricated workload.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124da_sourcefree_program_worlds as source
import f124da_shared_program_synthesis as candidate
import f124da_independent_program_control as strong
import f124da_edge_program_control as edge
import f124ct_gated_sequence_control as rnn
import f124ct_sequence_protocol as protocol

ARMS=("shared_program","independent_pooled","edge_program","frozen_gated_recurrent")

def need(ok,reason):
    if not ok:raise RuntimeError("F124DA_TRIAL_"+reason)

def run(family,seed,arm):
    need(family in source.FAMILIES and seed in source.SEEDS and arm in ARMS,
         "EXACT_SOURCEFREE_FAMILY_SEED_ARM")
    public=source.born(family,seed)
    fit,check,heldout=(public[k] for k in ("FIT","CHECK","HELDOUT"))
    protocol.HIDDEN=8;protocol.EPOCHS=45
    if arm=="shared_program":
        model,receipt=candidate.train(fit);score=candidate.score
    elif arm=="independent_pooled":
        model,receipt=strong.train(fit);score=strong.score
    elif arm=="edge_program":
        model,receipt=edge.train(fit);score=edge.score
    else:
        model,receipt=rnn.train(fit,check)
        def score(model,ep):
            pred=rnn.predict_sequence(model,ep)
            gold=[e["observed"] for e in ep["events"]]
            return {"correct":pred==gold,
                    "bit_errors":sum((a^b).bit_count() for a,b in zip(pred,gold)),
                    "native_event_calls":len(pred)}
    fitted=model is not None
    checked=[score(model,ep) for ep in check] if fitted else []
    admitted=bool(fitted and all(x["correct"] for x in checked) and
                  (arm!="frozen_gated_recurrent" or receipt["natural_model_admission"]))
    pos=[score(model,ep) for ep in heldout] if fitted else []
    neg=[score(model,source.matched_negative(ep)) for ep in heldout] if fitted else []
    need(all(x["native_event_calls"]==8 for x in checked+pos+neg),
         "NO_EARLY_EXIT_ACROSS_EIGHT_EVENT_NATIVE_SCORE")
    return {
       "schema":"mass.f124da.sourcefree-operator-program-trial.v1",
       "family":family,"seed":seed,"arm":arm,
       "FIT_SHA256":candidate.digest(fit),
       "CHECK_SHA256":candidate.digest(check),
       "HELDOUT_SHA256":candidate.digest(heldout),
       "FIT_episodes":24,"CHECK_veto_only_episodes":8,
       "HELDOUT_positive_episodes":8,"matched_hard_negative_episodes":8,
       "all_eight_autoregressive_steps_scored_if_fitted":True,
       "natural_fit_model_found":fitted,
       "natural_CHECK_8_of_8_admitted":admitted,
       "diagnostic_CHECK_exact":sum(x["correct"] for x in checked),
       "diagnostic_HELDOUT_exact_positives":sum(x["correct"] for x in pos),
       "diagnostic_HELDOUT_hard_false_positives":sum(x["correct"] for x in neg),
       "diagnostic_HELDOUT_positive_bit_errors":sum(x["bit_errors"] for x in pos),
       "admitted_HELDOUT_exact_positives":sum(x["correct"] for x in pos) if admitted else None,
       "admitted_HELDOUT_hard_false_positives":sum(x["correct"] for x in neg) if admitted else None,
       "FIT_training_receipt":receipt,
       "source_program_never_passed_to_model":True,
       "all_old_original_scientific_924_to_937_sources_untouched":True,
       "sourcefree_program_library_supplied_to_both_pooled_models":True,
       "scientific_firstuse_consumed":0,
       "protected_source_used":False,"scientific_acceptance":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",required=True,choices=source.FAMILIES)
    p.add_argument("--seed",required=True,type=int)
    p.add_argument("--arm",required=True,choices=ARMS)
    a=p.parse_args()
    print(json.dumps(run(a.family,a.seed,a.arm),sort_keys=True))

if __name__=="__main__":main()

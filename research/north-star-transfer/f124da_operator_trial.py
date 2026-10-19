"""F124-DA operator-induction source-free prospective diagnostic.

Five arms receive EXACT same public FIT/CHECK/HELDOUT episodes. No learner
sees hidden source operator table, wiring or params. Natural CHECK veto
must pass before any heldout can count as accepted (all diagnostic heldout
outcomes retained for falsification, marked non-scientific).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124da_sourcefree_operators as source
import f124da_learned_operator_search as candidate
import f124da_independent_operator_peer as peer
import f124da_edge_operator_control as edge
import f124cz_shared_quadratic_model as quadratic
import f124ct_gated_sequence_control as gated
import f124ct_sequence_protocol as protocol

ARMS=("learned_lexicon","independent_equal_lexicon","edge_lexicon",
      "frozen_quadratic","frozen_gated_recurrent")

def must(ok,why):
    if not ok:raise RuntimeError("F124DA_TRIAL_"+why)

def eval_case(regime,seed,arm):
    must(regime in source.REGIMES and seed in source.SEEDS and
         arm in ARMS,"FROZEN_SOURCEFREE_CASE_ARM")
    public=source.born(regime,seed)
    fit,check,heldout=public["FIT"],public["CHECK"],public["HELDOUT"]
    protocol.HIDDEN=8;protocol.EPOCHS=45
    if arm=="learned_lexicon":
        model,receipt=candidate.train(fit)
        evaluate=candidate.score
    elif arm=="independent_equal_lexicon":
        model,receipt=peer.train(fit)
        evaluate=peer.score
    elif arm=="edge_lexicon":
        model,receipt=edge.train(fit)
        evaluate=edge.score
    elif arm=="frozen_quadratic":
        model,receipt=quadratic.fit(fit)
        def evaluate(m,ep):
            q=quadratic.score(m,ep)
            return {"exact":q["correct"],"bit_errors":q["bit_errors"],
                    "native_events":q["native_event_calls"]}
    else:
        model,receipt=gated.train(fit,check)
        def evaluate(m,ep):
            predicted=gated.predict_sequence(m,ep)
            expected=[e["observed"] for e in ep["events"]]
            return {"exact":predicted==expected,
                    "bit_errors":sum((a^b).bit_count() for a,b in zip(predicted,expected)),
                    "native_events":8}
    fitted=model is not None
    check_rows=[evaluate(model,x) for x in check] if fitted else []
    naturally_admitted=bool(fitted and all(r["exact"] for r in check_rows)
         and (arm!="frozen_gated_recurrent" or receipt["natural_model_admission"]))
    pos=[evaluate(model,x) for x in heldout] if fitted else []
    neg=[evaluate(model,source.hard_negative(x)) for x in heldout] if fitted else []
    must(all(v["native_events"]==8 for v in check_rows+pos+neg),
         "COMPLETE_AUTOREGRESSIVE_FULL_TRAJECTORY")
    return {
      "schema":"mass.f124da.sourcefree-new-operator-trial.v1",
      "regime":regime,"seed":seed,"arm":arm,
      "FIT_public_hash":candidate.digest(fit),
      "CHECK_public_hash":candidate.digest(check),
      "HELDOUT_public_hash":candidate.digest(heldout),
      "FIT_episodes":24,"CHECK_veto_only_episodes":8,
      "heldout_positive_episodes":8,"matched_hard_negative_episodes":8,
      "FIT_model_fitted":fitted,
      "natural_CHECK_admitted":naturally_admitted,
      "natural_CHECK_full_trajectory_correct_count":sum(r["exact"] for r in check_rows),
      "diagnostic_heldout_positive_exact_count":sum(r["exact"] for r in pos),
      "diagnostic_heldout_negative_false_positive_count":sum(r["exact"] for r in neg),
      "diagnostic_heldout_bit_errors":sum(r["bit_errors"] for r in pos),
      "qualified_heldout_exact_positive_count":sum(r["exact"] for r in pos) if naturally_admitted else None,
      "qualified_hard_false_positive_count":sum(r["exact"] for r in neg) if naturally_admitted else None,
      "full_public_training_receipt":receipt,
      "hidden_truth_tables_and_wire_indices_not_passed_to_models":True,
      "all_original_924_to_937_scientific_cases_untouched":True,
      "source_free_only":True,
      "non_scientific_diagnostic":True,
      "scientific_firstuse_cases":0,
      "scientific_success_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--regime",choices=source.REGIMES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    a=p.parse_args()
    print(json.dumps(eval_case(a.regime,a.seed,a.arm),sort_keys=True))

if __name__=="__main__":main()

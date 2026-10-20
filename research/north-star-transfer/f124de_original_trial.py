"""F124-DE exactly paired new sourcefree cross-bit FIT/CHECK/HELDOUT trial.

The independent full-degree-four ANF peer receives identical 192 causal
FIT transitions and the same polynomial class as the proposed compressed
incremental solver. Frozen prior optimized bitwise ANF additionally has
fresh meta data and is *secondary* out-of-class capability reference.
Neither primary arm sees source labels, private wire assignments or oracle.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124de_sourceonly_crossbit as source
import f124de_sparse_crossbit_learner as candidate
import f124de_independent_full_anf as peer
import f124dd_independent_compact_anf as historical

ARMS=("sparse_crossbit_compact","independent_equal_degree4_ANF","prior_optimized_bitwise_ANF")
def need(ok,reason):
    if not ok:raise RuntimeError("F124DE_TRIAL_"+reason)
def evaluate(family,seed,arm):
    need(family in source.FAMILIES and seed in source.SEEDS and arm in ARMS,
         "EXACT_FROZEN_NEW_SYNTHETIC_ROSTER")
    public=source.born(family,seed)
    fit,check,heldout=(public[k] for k in ("FIT","CHECK","HELDOUT"))
    if arm=="sparse_crossbit_compact":
        model,receipt=candidate.fit(fit)
        score=candidate.score
    elif arm=="independent_equal_degree4_ANF":
        model,receipt=peer.train(fit)
        score=peer.score
    else:
        meta=source.meta_training()
        meta_model,meta_receipt=historical.train_meta(meta)
        model,receipt=historical.fit(meta_model,fit)
        score=historical.score
        receipt=dict(receipt);receipt["additional_secondary_meta"]=meta_receipt
    fitted=model is not None
    checks=[score(model,e) for e in check] if fitted else []
    admitted=bool(fitted and len(checks)==8 and all(x["exact"] for x in checks))
    positives=[score(model,e) for e in heldout] if fitted else []
    negatives=[score(model,source.negative(e)) for e in heldout] if fitted else []
    need(all(x["native_events"]==8 for x in checks+positives+negatives),
         "REAL_FULL_EIGHT_STEP_AUTOREGRESSIVE_SCORING")
    row_data=candidate.training_rows(fit)
    info=[len({x[i]|(x[j]<<4) for x,_ in row_data})
          for i in range(5) for j in range(i+1,5)]
    return {
      "schema":"mass.f124de.original-sourcefree-crossbit-trial.v1",
      "family":family,"seed":seed,"arm":arm,
      "meta_public_SHA256":candidate.digest(source.meta_training()),
      "FIT_public_SHA256":candidate.digest(fit),
      "CHECK_public_SHA256":candidate.digest(check),
      "heldout_public_SHA256":candidate.digest(heldout),
      "FIT_episodes":24,"CHECK_veto_only_episodes":8,
      "untouched_heldout_positive_episodes":8,"matched_crossrole_negatives":8,
      "events_per_episode":8,"source_private_formula_not_given_to_model":True,
      "FIT_possible_pair_unique_cell_min":min(info),
      "FIT_possible_pair_unique_cell_max":max(info),
      "maximum_known_unconstrained_truth_table_pairs":256-min(info),
      "unrestricted_256_entry_nibble_operator_not_identifiable_from_192_rows":True,
      "natural_FIT":fitted,
      "natural_CHECK_admission":admitted,
      "CHECK_correct_complete_episodes":sum(x["exact"] for x in checks),
      "diagnostic_heldout_positive_exact":sum(x["exact"] for x in positives) if fitted else None,
      "diagnostic_hard_false_positives":sum(x["exact"] for x in negatives) if fitted else None,
      "diagnostic_bit_errors":sum(x["bit_errors"] for x in positives) if fitted else None,
      "admitted_positive_exact":sum(x["exact"] for x in positives) if admitted else None,
      "admitted_hard_false_positives":sum(x["exact"] for x in negatives) if admitted else None,
      "FIT_receipt":receipt,
      "primary_pair_equal_frozen_training_information":arm!="prior_optimized_bitwise_ANF",
      "science_original_924_to_937_accessed":False,
      "prior_F124DD_81_to_84_used":False,
      "sourcefree_only":True,"new_scientific_firstuse_consumed":0,
      "independent_external_source_birth":False,"science_accepted":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=source.FAMILIES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    x=p.parse_args()
    print(json.dumps(evaluate(x.family,x.seed,x.arm),sort_keys=True))
if __name__=="__main__":main()

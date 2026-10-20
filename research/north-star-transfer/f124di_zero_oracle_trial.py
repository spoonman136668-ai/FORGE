"""F124-DI source-free DEVELOPMENT-only zero-extra-information CV comparison.

All three fully fitted arms see the exact same 24 FIT episodes.
Candidate and independently coded peer both train a degree/wiring
prior using first20 train and final4 FIT crossvalidation; an unchanged
full-degree4 reference uses all 24 but has no FIT-only CV prior.
CHECK/heldout never influence training, model choice, or program costs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124di_sourcefree_development as source
import f124di_cv_degree_prior as prior
import f124di_independent_cv_peer as equal
import f124de_sparse_crossbit_learner as old

ARMS=("learned_CV_causal_prior","independent_equal_CV_peer","frozen_degree4_reference")
def need(ok,why):
    if not ok:raise RuntimeError("F124DI_DEV_"+why)

def trial(family,seed,arm):
    need(family in source.FAMILIES and seed in source.SEEDS and arm in ARMS,
         "EXACT_FROZEN_DEVELOPMENT_CASE")
    public=source.development(family,seed)
    FIT,CHECK,HOLD=(public[x] for x in ("FIT","CHECK","HELDOUT"))
    if arm==ARMS[0]:
        model,rec=prior.learn(FIT);score=prior.score
    elif arm==ARMS[1]:
        model,rec=equal.fit(FIT);score=equal.score
    else:
        model,rec=old.fit(FIT);score=old.score
    fitted=model is not None
    chk=[score(model,x) for x in CHECK] if fitted else []
    admitted=bool(fitted and len(chk)==8 and all(q["exact"] for q in chk))
    pos=[score(model,x) for x in HOLD] if fitted else []
    neg=[score(model,source.matched_negative(x)) for x in HOLD] if fitted else []
    need(all(q["native_events"]==8 for q in chk+pos+neg),"ALL_EIGHT_CAUSAL_STEPS_REQUIRED")
    return {
      "schema":"mass.f124di.sourcefree-zero-oracle-development-trial.v1",
      "family":family,"seed":seed,"arm":arm,
      "FIT_public_sha256":prior.digest(FIT),
      "CHECK_public_sha256":prior.digest(CHECK),
      "HELDOUT_public_sha256":prior.digest(HOLD),
      "complete_FIT_episodes":24,"internal_FIT_train_episodes":20,
      "internal_FIT_validation_episodes":4,
      "full_CHECK_veto_only_episodes":8,
      "untouched_development_heldout_positive":8,
      "matched_hard_negatives":8,
      "new_oracle_queries_or_labels":0,
      "source_law_hidden_from_models":True,
      "CHECK_used_for_training":False,
      "natural_FIT":fitted,
      "natural_CHECK_admission":admitted,
      "CHECK_correct_full_trajectories":sum(x["exact"] for x in chk),
      "diagnostic_exact_heldout_positives":sum(x["exact"] for x in pos) if fitted else None,
      "diagnostic_hard_false_positives":sum(x["exact"] for x in neg) if fitted else None,
      "admitted_exact_heldout_positives":sum(x["exact"] for x in pos) if admitted else None,
      "admitted_hard_false_positives":sum(x["exact"] for x in neg) if admitted else None,
      "fitted_model_receipt":rec,
      "sourcefree_development_only":True,
      "original_scientific_firstuse":0,
      "consumed_scientific_sources_replayed":False,
      "prior_F124DG_DH_cases_replayed":False,
      "scientific_acceptance":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=source.FAMILIES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    z=p.parse_args()
    print(json.dumps(trial(z.family,z.seed,z.arm),sort_keys=True))
if __name__=="__main__":main()

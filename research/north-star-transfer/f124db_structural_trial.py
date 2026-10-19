"""F124-DB one source-free heldout task against two meta-trained peers.

Both source-neutral program learners meta-train on the same twelve public
tasks, then freeze their learned libraries. Four controls receive the
same heldout FIT/CHECK/heldout; only independent meta-peer is claimed to
have identical cross-task training and constructive search resources.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124db_sourcefree_meta_tasks as source
import f124db_learned_meta_constructor as candidate
import f124db_independent_meta_peer as peer
import f124cz_shared_quadratic_model as quad
import f124ct_gated_sequence_control as gated
import f124ct_sequence_protocol as prot

ARMS=("meta_constructor","equal_meta_peer","frozen_quadratic",
      "frozen_gated_recurrent")

def require(ok,reason):
    if not ok:raise RuntimeError("F124DB_TRIAL_"+reason)

def run(family,seed,arm):
    require(family in source.FAMILIES and seed in source.SEEDS and
            arm in ARMS,"ORIGINAL_FROZEN_COHORT_SCOPE")
    meta=source.meta_training()
    public=source.heldout(family,seed)
    fit,check,heldout=public["FIT"],public["CHECK"],public["HELDOUT"]
    prot.HIDDEN=8;prot.EPOCHS=45
    trained_from_meta=False
    meta_receipt=None
    if arm=="meta_constructor":
        meta_model,meta_receipt=candidate.learn_library(meta)
        model,receipt=candidate.fit_novel(meta_model,fit)
        score=candidate.score
        trained_from_meta=True
    elif arm=="equal_meta_peer":
        meta_model,meta_receipt=peer.train_meta(meta)
        model,receipt=peer.synth(meta_model,fit)
        score=peer.score
        trained_from_meta=True
    elif arm=="frozen_quadratic":
        model,receipt=quad.fit(fit)
        def score(model,ep):
            z=quad.score(model,ep)
            return {"exact":z["correct"],"bit_errors":z["bit_errors"],
                    "native_events":z["native_event_calls"]}
    else:
        model,receipt=gated.train(fit,check)
        def score(model,ep):
            predictions=gated.predict_sequence(model,ep)
            labels=[x["observed"] for x in ep["events"]]
            return {"exact":predictions==labels,
               "bit_errors":sum((a^b).bit_count() for a,b in zip(predictions,labels)),
               "native_events":8}
    fitted=model is not None
    check_scores=[score(model,ep) for ep in check] if fitted else []
    admitted=bool(fitted and all(z["exact"] for z in check_scores) and
                  (arm!="frozen_gated_recurrent" or receipt["natural_model_admission"]))
    positive=[score(model,ep) for ep in heldout] if fitted else []
    negatives=[score(model,source.hard_negative(ep)) for ep in heldout] if fitted else []
    require(all(x["native_events"]==8 for x in
               check_scores+positive+negatives),"NATIVE_FULL_EIGHT_STEP_TRAJECTORIES")
    return {
      "schema":"mass.f124db.original-sourcefree-compositional-construction-trial.v1",
      "family":family,"seed":seed,"arm":arm,
      "meta_task_public_sha256":candidate.digest(meta),
      "heldout_FIT_sha256":candidate.digest(fit),
      "heldout_CHECK_sha256":candidate.digest(check),
      "heldout_unseen_sha256":candidate.digest(heldout),
      "public_meta_tasks":12,"FIT_episodes":24,"CHECK_veto_episodes":8,
      "unseen_positive_episodes":8,"matched_hard_negative_episodes":8,
      "source_hidden_macro_and_tree_not_passed_to_learners":True,
      "naturally_fitted_FIT":fitted,
      "natural_CHECK_admission":admitted,
      "natural_CHECK_correct_episodes":sum(z["exact"] for z in check_scores),
      "diagnostic_heldout_exact_positives":sum(z["exact"] for z in positive) if fitted else None,
      "diagnostic_hard_false_positives":sum(z["exact"] for z in negatives) if fitted else None,
      "diagnostic_heldout_bit_errors":sum(z["bit_errors"] for z in positive) if fitted else None,
      "admitted_exact_heldout_positives":sum(z["exact"] for z in positive) if admitted else None,
      "admitted_hard_false_positives":sum(z["exact"] for z in negatives) if admitted else None,
      "cross_task_meta_trained":trained_from_meta,
      "full_public_training_receipt":receipt,
      "meta_training_receipt":meta_receipt,
      "no_prior_scientific_original_cases_read":True,
      "sourcefree_only":True,"scientific_firstuse_consumed":0,
      "scientific_acceptance":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--family",required=True,choices=source.FAMILIES)
    ap.add_argument("--seed",required=True,type=int)
    ap.add_argument("--arm",required=True,choices=ARMS)
    z=ap.parse_args()
    print(json.dumps(run(z.family,z.seed,z.arm),sort_keys=True))

if __name__=="__main__":main()

"""F124-DF fresh sourcefree postfit diagnosis, frozen F124-DE strong arms.

Both frozen learners see only identical public FIT. Source author wiring
and 256-input oracle are consulted *after* model train/CHECK/heldout;
not supplied to any model, select/training routine or CHECK policy.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124df_sourceonly_new_rotation as source
import f124df_postfit_diagnostic as forensic
import f124de_sparse_crossbit_learner as candidate
import f124de_independent_full_anf as peer

ARMS=("frozen_sparse_crossbit","frozen_equal_full_ANF")
def need(ok,why):
    if not ok:raise RuntimeError("F124DF_TRIAL_"+why)
def one(family,seed,arm):
    need(family in source.FAMILIES and seed in source.SEEDS and arm in ARMS,
         "FROZEN_UNFAMILIAR_SOURCEFREE_CONDITION")
    public=source.birth(family,seed)
    fit,check,heldout=(public[k] for k in ("FIT","CHECK","HELDOUT"))
    # First complete ALL frozen learning/evaluation with public-only
    # trajectories, absolutely no source wire/oracle argument.
    if arm==ARMS[0]:
        model,fit_receipt=candidate.fit(fit)
        score=candidate.score
        selected=model["wiring"] if model is not None else None
    else:
        model,fit_receipt=peer.train(fit)
        score=peer.score
        selected=model["columns"] if model is not None else None
    checkrows=[score(model,x) for x in check] if model is not None else []
    admitted=bool(model is not None and len(checkrows)==8 and
                  all(x["exact"] for x in checkrows))
    positives=[score(model,x) for x in heldout] if model is not None else []
    negatives=[score(model,source.hard_negative(x)) for x in heldout] if model is not None else []
    need(all(q["native_events"]==8 for q in checkrows+positives+negatives),
         "FULL_AUTOREGRESSIVE_EIGHT_STEPS_NOT_EVALUATED")
    # Audited AFTER scoring only: no model access to oracle or hidden
    # truth wiring; purely synthetic forensic classification.
    private=source.wiring(family,seed)
    if len(private)==2:
        def independent_source_oracle(a,b):
            raw=[0]*5
            raw[private[0]]=a;raw[private[1]]=b
            return source.private_operator(family,raw,private)
    else:
        independent_source_oracle=None
    diagnosis=forensic.diagnose_after_scoring(
        fit,private,independent_source_oracle,selected,model is not None,admitted)
    if model is not None:
        need(fit_receipt.get("FIT_bit_errors")==0,"FROZEN_MODEL_NOT_FULLY_FITTED")
    return {
      "schema":"mass.f124df.new-sourcefree-rotation-diagnostic.v1",
      "family":family,"seed":seed,"arm":arm,
      "FIT_source_sha256":candidate.digest(fit),
      "CHECK_source_sha256":candidate.digest(check),
      "HELDOUT_source_sha256":candidate.digest(heldout),
      "FIT_episodes":24,"CHECK_veto_episodes":8,
      "heldout_positives":8,"matched_hard_negatives":8,
      "original_competitors_unchanged":True,
      "source_wiring_disclosed_to_models":False,
      "private_oracle_used_only_after_complete_model_scoring":True,
      "natural_FIT":model is not None,
      "natural_CHECK_admission":admitted,
      "CHECK_full_episodes_exact":sum(x["exact"] for x in checkrows),
      "diagnostic_heldout_positive_exact":sum(x["exact"] for x in positives) if model is not None else None,
      "diagnostic_hard_false_positives":sum(x["exact"] for x in negatives) if model is not None else None,
      "CHECK_admitted_heldout_exact":sum(x["exact"] for x in positives) if admitted else None,
      "CHECK_admitted_hard_false_positives":sum(x["exact"] for x in negatives) if admitted else None,
      "FIT_receipt":fit_receipt,
      "post_learning_forensic_receipt":diagnosis,
      "previous_sourcefree_91_94_never_replayed":True,
      "consumed_sci_924_937_never_used":True,
      "sourcefree_synthetic_only":True,
      "scientific_firstuse_consumed":0,
      "scientific_acceptance":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=source.FAMILIES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    args=p.parse_args()
    print(json.dumps(one(args.family,args.seed,args.arm),sort_keys=True))
if __name__=="__main__":main()

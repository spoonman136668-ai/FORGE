"""F124-DD exact paired new-sourcefree causal compiler trial.

All arms receive same NEW public meta 12 tasks and 24 FIT / 8 CHECK
veto / 8 sourcefree heldout positives and 8 matched hard negatives.
Both main arms train independent meta-derived function bases and compile
compact 4-input or fewer Boolean programs; third arm is a full-source,
fully-FIT slow graph execution control to isolate runtime costs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124dd_sourceonly_new_structures as source
import f124dd_meta_compact_nand as candidate
import f124dd_independent_compact_anf as peer

ARMS=("compact_meta_NAND","independent_compact_meta_ANF","slow_meta_NAND_DAG")
def need(ok,why):
    if not ok:raise RuntimeError("F124DD_TRIAL_"+why)

def run(family,seed,arm):
    need(family in source.FAMILIES and seed in source.SEEDS and arm in ARMS,
         "EXACT_SOURCEFREE_CASE_AND_ARM")
    meta=source.meta_training()
    novel=source.heldout(family,seed)
    fit=novel["FIT"];check=novel["CHECK"];heldout=novel["HELDOUT"]
    if arm=="independent_compact_meta_ANF":
        m,meta_receipt=peer.train_meta(meta)
        model,fit_receipt=peer.fit(m,fit)
        score=peer.score
    else:
        m,meta_receipt=candidate.train_meta(meta)
        mode="compact" if arm=="compact_meta_NAND" else "graph"
        model,fit_receipt=candidate.train_new(m,fit,mode=mode)
        score=candidate.score
    fitted=model is not None
    check_rows=[score(model,x) for x in check] if fitted else []
    admitted=bool(fitted and all(x["exact"] for x in check_rows) and
                  len(check_rows)==8)
    pos=[score(model,x) for x in heldout] if fitted else []
    neg=[score(model,source.hard_negative(x)) for x in heldout] if fitted else []
    need(all(q["native_events"]==8 for q in check_rows+pos+neg),
         "COMPLETE_NATIVE_TRAJECTORY_NOT_ALL_EIGHT_EVENTS")
    return {
      "schema":"mass.f124dd.sourcefree-compact-operator-original-trial.v1",
      "family":family,"seed":seed,"arm":arm,
      "meta_task_public_sha256":candidate.digest(meta),
      "FIT_public_sha256":candidate.digest(fit),
      "CHECK_public_sha256":candidate.digest(check),
      "holdout_public_sha256":candidate.digest(heldout),
      "meta_public_task_count":12,"FIT_full_episodes":24,"CHECK_veto_episodes":8,
      "heldout_positive_episodes":8,"matched_negative_episodes":8,
      "source_law_hidden_from_all_arms":True,
      "meta_trained_from_same_public_data":True,
      "FIT_naturally_fitted":fitted,
      "CHECK_naturally_admitted":admitted,
      "CHECK_correct_full_trajectories":sum(q["exact"] for q in check_rows),
      "diagnostic_heldout_positive_exact":sum(q["exact"] for q in pos) if fitted else None,
      "diagnostic_hard_false_positives":sum(q["exact"] for q in neg) if fitted else None,
      "diagnostic_positive_bit_errors":sum(q["bit_errors"] for q in pos) if fitted else None,
      "CHECK_admitted_positive_exact":sum(q["exact"] for q in pos) if admitted else None,
      "CHECK_admitted_hard_false_positives":sum(q["exact"] for q in neg) if admitted else None,
      "meta_receipt":meta_receipt,"FIT_receipt":fit_receipt,
      "old_924_to_937_source_ids_used":False,
      "old_DC_sciencefree_holdouts_reused":False,
      "sourcefree_synthetic_only":True,"new_original_scientific_firstuse":0,
      "scientific_accepted":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=source.FAMILIES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    z=p.parse_args()
    print(json.dumps(run(z.family,z.seed,z.arm),sort_keys=True))
if __name__=="__main__":main()

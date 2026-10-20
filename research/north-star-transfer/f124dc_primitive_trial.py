"""F124-DC frozen source-free meta-learned primitive construction trial.

The heldout source-only generator supplies identical public episodes to
all arms. Candidate and independent peer each FIT learn their own gate
bases from 12 public meta tasks and train an unseen ternary operator
solely from 24 novel FIT episodes, with no primitive labels or oracle.
A four-input heldout family tests rejection beyond the 3-input grammar.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124dc_sourcefree_structures as source
import f124dc_learned_gate_compiler as candidate
import f124dc_independent_anf_meta_peer as peer
import f124da_learned_operator_search as old

ARMS=("meta_NAND_constructor","equally_meta_trained_ANF_peer",
      "same_compute_no_meta_gate_ablation","prior_F124DA_two_input_lexicon")

def need(ok,why):
    if not ok:raise RuntimeError("F124DC_TRIAL_"+why)

def run(family,seed,arm):
    need(family in source.FAMILIES and seed in source.SEEDS and arm in ARMS,
         "EXACT_PREDECLARED_CASE_ARM")
    meta=source.meta_training()
    tasks=source.heldout(family,seed)
    fit,check,heldout=tasks["FIT"],tasks["CHECK"],tasks["HELDOUT"]
    meta_receipt=None
    if arm=="meta_NAND_constructor":
        m,meta_receipt=candidate.learn_universal_gate(meta)
        model,fitreceipt=candidate.learn_new_primitive(m,fit)
        score=candidate.score
    elif arm=="equally_meta_trained_ANF_peer":
        m,meta_receipt=peer.train_meta(meta)
        model,fitreceipt=peer.train_novel(m,fit)
        score=peer.score
    elif arm=="same_compute_no_meta_gate_ablation":
        m,meta_receipt=candidate.learn_universal_gate(meta)
        # Same 12 training tasks and 24 novel FIT episodes, but the
        # previously learned universal gate cannot enter the compiler.
        without={"learned_gate_table":None,"meta_motifs":m["meta_motifs"]}
        model,fitreceipt=candidate.learn_new_primitive(without,fit)
        score=candidate.score
    else:
        model,fitreceipt=old.train(fit)
        def score(m,ep):
            v=old.score(m,ep) if hasattr(old,"score") else None
            if v is not None:return {"exact":v["exact"],"bit_errors":v["bit_errors"],
                "native_events":v.get("native_events",8)}
            predicted=old.rollout(m,ep) if hasattr(old,"rollout") else old.predict_sequence(m,ep)
            actual=[z["observed"] for z in ep["events"]]
            return {"exact":predicted==actual,"bit_errors":sum((x^y).bit_count()
                    for x,y in zip(predicted,actual)),"native_events":8}
    fitted=model is not None
    checkrows=[score(model,ep) for ep in check] if fitted else []
    admitted=bool(fitted and len(checkrows)==8 and all(q["exact"] for q in checkrows))
    positives=[score(model,ep) for ep in heldout] if fitted else []
    negatives=[score(model,source.hard_negative(ep)) for ep in heldout] if fitted else []
    need(all(q["native_events"]==8 for q in
              checkrows+positives+negatives),"WHOLE_EIGHT_EVENT_PREDICTIONS")
    return {
      "schema":"mass.f124dc.original-sourcefree-new-primitive-trial.v1",
      "family":family,"seed":seed,"arm":arm,
      "same_public_meta_SHA256":candidate.digest(meta),
      "same_public_FIT_SHA256":candidate.digest(fit),
      "same_public_CHECK_SHA256":candidate.digest(check),
      "same_public_unseen_SHA256":candidate.digest(heldout),
      "public_meta_tasks":12,"novel_FIT_episodes":24,
      "CHECK_veto_only_episodes":8,"heldout_positive_episodes":8,
      "matched_negative_episodes":8,"full_events_per_episode":8,
      "learned_gate_meta_trained":arm!="prior_F124DA_two_input_lexicon",
      "FIT_naturally_fitted":fitted,
      "CHECK_naturally_admitted":admitted,
      "CHECK_full_trajectories_correct":sum(z["exact"] for z in checkrows),
      "diagnostic_full_heldout_positive_exact":sum(z["exact"] for z in positives) if fitted else None,
      "diagnostic_full_hard_false_positives":sum(z["exact"] for z in negatives) if fitted else None,
      "diagnostic_bit_errors":sum(z["bit_errors"] for z in positives) if fitted else None,
      "CHECK_admitted_positive_exact":sum(z["exact"] for z in positives) if admitted else None,
      "CHECK_admitted_hard_false_positives":sum(z["exact"] for z in negatives) if admitted else None,
      "meta_receipt":meta_receipt,"FIT_receipt":fitreceipt,
      "original_sci_cases_924_to_937_used":False,
      "hidden_source_law_or_operator_label_given_to_model":False,
      "sourcefree_synthetic_only":True,"scientific_firstuse_consumed":0,
      "scientific_acceptance":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--family",choices=source.FAMILIES,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--arm",choices=ARMS,required=True)
    z=p.parse_args()
    print(json.dumps(run(z.family,z.seed,z.arm),sort_keys=True))

if __name__=="__main__":main()

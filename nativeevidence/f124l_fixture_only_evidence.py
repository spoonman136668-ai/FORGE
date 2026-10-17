"""F124-L original TRAIN weight custody and COMPLETE fixture-only 7-9-hop diagnostic.

Never reads or generates reserved F124-H/K confirmation data. No model
training, gradient updates, model selection, new threshold, or first-use.
Failures are counted against complete 48-pair denominators, not retried.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import f124l_validation_only_adapter as adapter
import f124k_extended_source as fixture

SCHEMA="forge.research.f124l.authentic-original-weight-fixture-only-7to9.v1"
def need(value,key):adapter.need(bool(value),"EVIDENCE_"+key)

def evaluate(receipt_raw):
    protocol=adapter.frozen()
    weights=adapter.authenticate_train_receipt(receipt_raw)
    source_vectors=protocol["mechanism"]["guarded_limits"]["vectors"]
    output=[]
    forward=adapter.original_arm_b_adapter()
    fixed=adapter.fixed_12of16_adapter()
    for lane in ("Wingless","Yggdrasil"):
        pair_count=pos_ok=neg_ok=paired=ranked=failures=0
        fixed_pairs=exact_pairs=0
        depth={str(i):{"pairs":0,"paired_correct":0,"model_failures":0,
                       "fixed_paired_correct":0,"exact_paired_correct":0}
               for i in (7,8,9)}
        error_types=Counter()
        receipt_pairs=[]
        for seed in fixture.FIXTURES[lane]:
            for v in source_vectors:
                samples,truth=adapter.evaluate_fixture(
                    lane,seed,v,weights[lane],forward,fixed)
                need(truth["positive_symbolic_routes"]==1 and
                     truth["negative_symbolic_routes"]==0,
                     "NONINDEPENDENT_SYMBOLIC_REFERENCE")
                pair_count+=1
                d=str(7+seed%3)
                record=depth[d];record["pairs"]+=1
                both=not any(s["failed"] for s in samples)
                failures+=sum(bool(s["failed"]) for s in samples)
                record["model_failures"]+=sum(bool(s["failed"]) for s in samples)
                for s in samples:
                    if s["failed"]:error_types[s.get("failure_code","unknown")]+=1
                a=bool(both and samples[0]["positive_prediction"])
                b=bool(both and not samples[1]["positive_prediction"])
                correct=int(a and b)
                pos_ok+=int(a);neg_ok+=int(b)
                paired+=correct;record["paired_correct"]+=correct
                ranked+=int(both and samples[0]["logit"]>samples[1]["logit"])
                # The fixed public 12/16 comparator is scored separately even
                # if the Arm B model failed on this particular pair.
                pos,neg=adapter.fixture_pair(lane,seed,v)
                fp,_=fixed(pos);fn,_=fixed(neg)
                f=int(fp and not fn)
                fixed_pairs+=f
                record["fixed_paired_correct"]+=f
                exact_pairs+=1
                record["exact_paired_correct"]+=1
                receipt_pairs.append(hashlib.sha256(adapter.canonical(
                    {"seed":seed,"vector":v,"model":samples,
                     "exact_truth":truth,"fixed_pair_correct":bool(f)}
                )).hexdigest())
        need(pair_count==48 and
             {k:v["pairs"] for k,v in depth.items()}==
             {"7":16,"8":16,"9":16} and exact_pairs==48,
             "DENOMINATOR_OR_DEPTH")
        output.append({
          "lane":lane,"source":"QUALIFICATION_FIXTURE_ONLY",
          "fixture_pairs":48,"positive_correct":pos_ok,
          "negative_correct":neg_ok,"paired_correct":paired,
          "positive_logit_greater":ranked,
          "original_arm_b_frozen_weight_sha256":adapter.original.sha(weights[lane]),
          "model_exception_case_count":failures,
          "exception_types":dict(sorted(error_types.items())),
          "fixed_12of16_paired_correct":fixed_pairs,
          "exact_symbolic_paired_correct":exact_pairs,
          "role_only_paired_correct":0,
          "depth":depth,
          "pair_evidence_sha256":hashlib.sha256(
              adapter.canonical(receipt_pairs)).hexdigest(),
          "no_model_retraining":True,"no_protected_source_generation":True
        })
    need([x["lane"] for x in output]==["Wingless","Yggdrasil"],"TWO_LANES")
    return {
      "schema":SCHEMA,
      "protocol_git_blob":adapter.FREEZE_BLOB,
      "f124k_fixture_git_blob":adapter.FIXTURE_SOURCE_BLOB,
      "original_model_git_blob":adapter.ORIGINAL_MODEL_BLOB,
      "original_source_git_blob":adapter.ORIGINAL_SOURCE_BLOB,
      "original_train_receipt_sha256":adapter.ORIGINAL_TRAIN_RECEIPT_SHA256,
      "phase":"NONRESERVED_QUALIFICATION_FIXTURE_ONLY",
      "original_model_forward_code_object_reused":True,
      "original_model_source_modified":False,
      "original_model_weights_updated":False,
      "arms_trained":0,"lanes":output,
      "protected_examples_generated":0,"protected_examples_scored":0,
      "independent_first_use_witness_verified":False,
      "independent_original_scientific_first_use":False,
      "scientific_acceptances":0,"optimizer_promotions":0,
      "accepted_ref_mutations":0,"Codex_calls":0,"paid_API_calls":0,
      "new_scheduler":False,"ckb_plane_contact":False
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--train-receipt",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    dest=Path(args.output)
    need(dest.parent.is_dir() and not dest.exists(),"OUTPUT_OVERWRITE")
    result=evaluate(Path(args.train_receipt).read_bytes())
    raw=adapter.canonical(result)
    dest.open("xb").write(raw)
    print("F124L_EVIDENCE_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in result["lanes"]:
        print("F124L_"+lane["lane"].upper()+
              "_ORIGINAL_ARM_B_FIXTURE="+str(lane["paired_correct"])+"/48")
        print("F124L_"+lane["lane"].upper()+
              "_FIXED_PUBLIC="+str(lane["fixed_12of16_paired_correct"])+"/48")
        print("F124L_"+lane["lane"].upper()+
              "_ORIGINAL_MODEL_ERRORS="+str(lane["model_exception_case_count"]))
    print("F124L_PROTECTED_FIRST_USE=false")
    print("F124L_SCIENTIFIC_ACCEPTANCE=false")

if __name__=="__main__":
    try:main()
    except (adapter.Quarantined,fixture.Invalid,KeyError,
            ValueError,TypeError,OSError) as e:
        print("F124L_EVIDENCE_QUARANTINED="+str(e),file=sys.stderr)
        raise SystemExit(1)

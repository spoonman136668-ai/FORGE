"""Bounded automatic negative-result successor, no scientific dispatch.

Interpret an independently replayed F10 failure without retroactively
retuning F10 against its previously inspected validation split. Propose
a different F11 information-value objective, with explicit custody
requirements for genuinely fresh evaluation. No controller or API.
"""
import argparse,hashlib,json
from pathlib import Path

NEGATIVE="Y-FORGE-F11-TASK-ALIGNED-OBSERVATION-VALUE-PROPOSAL"
REPLICATION="Y-FORGE-F11-OBSERVATION-VALUE-REPLICATION-PROPOSAL"

def need(x,why):
    if not x:raise ValueError("F10_SUCCESSOR_"+why)

def canonical(x):
    return (json.dumps(x,sort_keys=True,separators=(",",":"))+"\n").encode()

def prepare(result_bytes,witness_bytes):
    result=json.loads(result_bytes)
    witness=json.loads(witness_bytes)
    need(result.get("schema")=="forge.f10.automatic-public-information-value-engineering.v1"
         and result.get("status")=="F3_USED_ONLY_NO_SCIENTIFIC_AUTHORITY"
         and result.get("scientific_winner_selected") is False
         and result.get("scientific_dispatch_authorized") is False
         and all(result.get(k)==0 for k in ("new_cohort_uses","new_first_use_claims",
                                             "new_scientific_originals","paid_api_calls")),
         "PARENT_PROVENANCE")
    model=result.get("model",{})
    need(model.get("schema")=="forge.f10.frozen-public-value-estimator.v1"
         and model.get("train_seeds")==[67204,67205]
         and model.get("validation_seeds")==[67206,67207]
         and model.get("train_public_observations")==1152
         and model.get("scientific_dispatch_authorized") is False,
         "TRAIN_SOURCE")
    need(witness.get("schema")=="forge.f10.independent-learned-information-value-review.v1"
         and witness.get("status")=="F3_USED_SOURCE_REPLAY_QUALIFIED_NOT_SCIENCE"
         and witness.get("training_public_labels")==1152
         and witness.get("replayed_validation")==96
         and witness.get("validation_summary")==result.get("validation_summary")
         and witness.get("scientific_dispatch_authorized") is False
         and witness.get("new_first_use_claims")==0,"INDEPENDENT_REPLAY")
    controls=result.get("f9_used_validation_controls",{})
    need(controls.get("ALWAYS_SWAP",{}).get("mismatches")==66 and
         controls.get("START_GE7_EARLY",{}).get("mismatches")==66 and
         controls.get("ALWAYS_EARLY",{}).get("mismatches")==74,
         "EXACT_PARENT_CONTROLS")
    evidence=result["validation_summary"]
    total=evidence["pre"]+evidence["post"]
    need(evidence.get("cases")==96 and
         total==witness.get("f10_historical_mismatches") and
         witness.get("best_fixed_historical_mismatches")==66,
         "RECOMPUTED_HISTORICAL_METRIC")
    worse=total>=66
    chosen=NEGATIVE if worse else REPLICATION
    hypothesis=(
        "Learn task-aligned expected reduction in future physical-assignment error, "
        "not only the entropy of an immediate sensor anomaly. Calibrate sparse "
        "counterfactual coverage and require robust minimum source observability "
        "before prospective comparison, using fresh first-use-authorized cohorts."
        if worse else
        "Prospectively replicate the observed development advantage on independently "
        "released blinded cohorts and compare against frozen F9 controls."
    )
    return {
      "schema":"forge.f10.automatic-negative-to-f11-design.v1",
      "status":"ENGINEERING_SUCCESSOR_ONLY_FIRST_USE_BLOCKED",
      "parent_f10_sha256":hashlib.sha256(result_bytes).hexdigest(),
      "independent_f10_review_sha256":hashlib.sha256(witness_bytes).hexdigest(),
      "finding":"HISTORICAL_F10_UNCERTAINTY_VALUE_NOT_BETTER_THAN_FIXED" if worse else
                "HISTORICAL_F10_GAIN_REQUIRES_INDEPENDENT_REPLICATION",
      "selected_proposal_id":chosen,
      "hypothesis":hypothesis,
      "historical_f10_mismatches":total,
      "historical_best_fixed_mismatches":66,
      "original_f10_model_frozen_no_retuning":True,
      "proposed_F11_source_and_sealed_cohorts":"UNALLOCATED_CUSTODY_REQUIRED",
      "new_first_use_claims":0,"new_scientific_originals":0,
      "new_data_accesses":0,"paid_api_calls":0,
      "scientific_dispatch_authorized":False
    }

def main():
    p=argparse.ArgumentParser()
    for item in ("parent","witness","out"):p.add_argument("--"+item,required=True)
    a=p.parse_args()
    data=prepare(Path(a.parent).read_bytes(),Path(a.witness).read_bytes())
    with Path(a.out).open("xb") as out:out.write(canonical(data))
    print("F10_AUTONOMOUS_NEGATIVE_TO_F11_DESIGN=PASS")
    print("F11_PROPOSAL_ID="+data["selected_proposal_id"])
    print("F11_FIRST_USE_AND_ORIGINALS=ZERO")
if __name__=="__main__":main()

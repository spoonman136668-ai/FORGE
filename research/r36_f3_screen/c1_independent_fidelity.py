"""Independent R36/F3 C1 method-fidelity witness, DEVELOPMENT-ONLY.

The immutable YF3-C1 preregistration requires a learnable PERMUTATION of the
existing public read schedule. A permutation preserves the multiset of
physical read addresses; learning to sample NEW addresses is a different
hypothesis, even when it produces qualified development gains.

This witness cannot authorize a sealed original, select a scientific winner,
or reinterpret the frozen hypothesis. It only classifies evidence already
independently replayed against the pinned science source.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from run_wingless_development import audit_frozen

BASELINE = ((0, 1), (0, 1), (0, 1), (2, 4), (2, 4))
BASELINE_MULTISET = Counter(cell for pair in BASELINE for cell in pair)
C1_ID = "YF3-C1"
SOURCE = "5797a257a75fe139313e8486cd1a1ae79c44b148"


def _require(condition, reason):
    if not condition:
        raise ValueError("F3_C1_FIDELITY_" + reason)


def sensor_identity_delta(trace):
    """Returns new-address evidence; valid permutation must preserve multiplicity."""
    _require(type(trace) is list and len(trace) == 5, "TRACE_SHAPE")
    for pair in trace:
        _require(type(pair) is list and len(pair) == 2, "READ_LIMIT")
        _require(all(type(x) is int and 0 <= x < 16 for x in pair), "ADDRESS")
        _require(pair[0] != pair[1], "DUPLICATE")
    current = Counter(cell for pair in trace for cell in pair)
    _require(sum(current.values()) == 10, "READ_LIMIT")
    new_addresses = sorted(set(current) - set(BASELINE_MULTISET))
    return {
        "preserves_existing_address_multiset": current == BASELINE_MULTISET,
        "new_physical_addresses": new_addresses,
        "baseline_read_counts": dict(sorted(BASELINE_MULTISET.items())),
        "observed_read_counts": dict(sorted(current.items())),
    }


def review(record, independent_witness, dev_closeout, record_sha256, witness_sha256):
    frozen = audit_frozen()
    y = frozen["yggdrasil"]
    prereg = next(c for c in y["candidates"] if c["id"] == C1_ID)
    _require(prereg["method"] == "train_only_sentinel_read_order", "PREREG_METHOD_DRIFT")
    _require(prereg["mechanism"] == "Learnable permutation of the existing public read schedule; freeze before sealed evaluation", "PREREG_MECHANISM_DRIFT")
    _require(y["control"] == "Pinned Y070 dual-sentinel decoder-corrected policy, fixed public observation schedule", "CONTROL_IDENTITY")
    _require(y["method_source_commit"] == SOURCE, "SOURCE_IDENTITY")
    _require(record.get("schema") == "forge.f3.yggdrasil.policy-development.v1", "RECORD_SCHEMA")
    _require(record.get("source_commit") == SOURCE, "RECORD_SOURCE")
    _require(record.get("scientific_winners_selected") == 0 and record.get("sealed_first_uses_consumed") == 0, "ORIGINAL_AUTHORITY")
    _require(independent_witness.get("status") == "ALL_FOUR_DEVELOPMENT_SCORES_REPLAYED_SCIENCE_NOT_ADMITTED", "INDEPENDENT_REPLAY")
    _require(independent_witness.get("records_replayed") == 960 and independent_witness.get("scientific_winners_selected") == 0, "INDEPENDENT_WITNESS")
    _require(dev_closeout.get("status") == "DEVELOPMENT_REVIEW_PASS_SCIENCE_METHOD_FIDELITY_PENDING", "CLOSEOUT_STATE")
    _require(dev_closeout.get("record_sha256") == record_sha256 and dev_closeout.get("witness_sha256") == witness_sha256, "REVIEW_EVIDENCE_HASH")
    _require(dev_closeout.get("scientific_winner_selected") is False and dev_closeout.get("scientific_admission") is False, "REVIEW_AUTHORITY")
    _require(dev_closeout.get("provisional_leader_development_only") == C1_ID, "PROVISIONAL_ID")
    rows = record.get("records")
    _require(type(rows) is list and len(rows) == 960, "RECORD_COUNT")
    base = [x for x in rows if x.get("candidate") == "CONTROL"]
    c1 = [x for x in rows if x.get("candidate") == C1_ID]
    _require(len(base) == 192 and len(c1) == 192, "CASE_COUNTS")
    _require(all(x.get("public_addresses") == [list(v) for v in BASELINE] for x in base), "CONTROL_DRIFT")
    violations = 0
    changed_set = set()
    trace_cases = []
    for x in c1:
        _require(x.get("seed") in range(67204, 67208), "NONDEVELOPMENT_SEED")
        check = sensor_identity_delta(x.get("public_addresses"))
        if not check["preserves_existing_address_multiset"]:
            violations += 1
            changed_set.update(check["new_physical_addresses"])
            if len(trace_cases) < 3:
                trace_cases.append({"seed": x["seed"], "addresses": x["public_addresses"],
                                    "new_addresses": check["new_physical_addresses"]})
    _require(independent_witness.get("actual_sensor_intervention_trials", {}).get(C1_ID) == 192, "INSTRUMENTATION_ATTESTATION")
    return {
        "schema": "forge.r36-f3.c1-independent-method-fidelity.v1",
        "source_commit": SOURCE,
        "frozen_portfolio_blob": "4140cf897c05d27dd6dac01cea796f383fa2ef44",
        "frozen_c1_mechanism": prereg["mechanism"],
        "control_sensor_addresses": sorted(BASELINE_MULTISET),
        "validated_development_trials": len(c1),
        "nonpermutation_trials": violations,
        "new_physical_sensor_addresses": sorted(changed_set),
        "sampled_counterexamples": trace_cases,
        "status": ("REJECTED_NONPERMUTATION_SENSOR_CHANGE" if violations else
                   "PERMUTATION_NECESSARY_CONDITION_ONLY_FURTHER_REVIEW_REQUIRED"),
        "claim_limit": "Development gain is evidence for a different sensor-reallocation mechanism, not the frozen C1 permutation hypothesis.",
        "scientific_candidate_accepted": False,
        "scientific_winner_selected": False,
        "sealed_original_authorized": False,
        "new_original_executed": False,
        "first_use_claims_consumed": 0,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record", required=True)
    p.add_argument("--witness", required=True)
    p.add_argument("--dev-closeout", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    data = Path(a.record).read_bytes()
    witness = Path(a.witness).read_bytes()
    result = review(json.loads(data), json.loads(witness),
                    json.loads(Path(a.dev_closeout).read_bytes()),
                    hashlib.sha256(data).hexdigest(),
                    hashlib.sha256(witness).hexdigest())
    with Path(a.out).open("xb") as f:
        f.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode())
    print("F3_C1_INDEPENDENT_FIDELITY_STATUS=" + result["status"])
    print("F3_C1_NONPERMUTATION_TRIALS=" + str(result["nonpermutation_trials"]))
    print("F3_C1_NEW_SENSOR_ADDRESSES=" + ",".join(map(str, result["new_physical_sensor_addresses"])))
    print("F3_C1_SCIENTIFIC_ADMISSION=BLOCKED")


if __name__ == "__main__":
    main()

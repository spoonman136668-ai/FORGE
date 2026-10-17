"""F123 cross-OS TRAIN-only numerical equivalence and immutable receipt audit.

Exact OS-specific training SHA identities remain distinct. A qualified candidate
for future CONFIRM may reference the Ubuntu receipt *only* by its exact SHA.
No model weights are averaged, rounded for inference, or silently substituted.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

SCHEMA = "forge.autonomy.f123.train-only-controls-custody.v1"
TOLERANCE = 1e-12

class Invalid(ValueError):
    pass

def require(test, code):
    if not test:
        raise Invalid("F123_OS_PARITY_" + code)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                          separators=(",", ":")).encode()).hexdigest()

def read_receipt(directory):
    path = Path(directory) / "f123-train-weights.json"
    checksum = Path(directory) / "f123-train-weights.sha256"
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    require(checksum.read_text(encoding="utf-8").strip() ==
            sha + "  f123-train-weights.json", "RECEIPT_SHA_MISMATCH")
    result = json.loads(raw)
    require(result["schema"] == SCHEMA and
            result["cohorts"] == "TRAIN_ONLY" and
            result["confirmation_inputs_generated"] == 0 and
            result["scientific_first_use"] is False and
            result["scientific_acceptances"] == 0 and
            result["accepted_ref_mutations"] == 0 and
            result["optimizer_promotions"] == 0 and
            result["originals_dispatched"] == 0 and
            len(result["lanes"]) == 2, "UNQUALIFIED_TRAIN_RECEIPT")
    for lane in result["lanes"]:
        models = lane["train_frozen_weights"]
        require(lane["train_source_only_selection"] in ("A", "B") and
                set(models) == {"A", "B"} and
                set(lane["model_arms"]) == {"A", "B"} and
                lane["confirmation_inputs_generated"] == 0 and
                len(lane["train_f122_foundation_weights"]) == 17 and
                len(lane["train_query_only_weights"]) == 20,
                "INCOMPLETE_TRAINED_MODEL")
        for arm in ("A", "B"):
            expected = digest(models[arm])
            require(expected == lane["weights_sha256"][arm] ==
                    lane["model_arms"][arm]["weight_sha256"],
                    "MODEL_WEIGHT_SHA_INVALID")
        require(digest(models[lane["train_source_only_selection"]]) ==
                lane["selected_model_weights_sha256"] and
                digest(lane["train_query_only_weights"]) ==
                lane["query_only_weights_sha256"], "SELECTED_WEIGHT_SHA_INVALID")
    return result, sha

def compare(a, b):
    require(a["source_sha"] == b["source_sha"] and
            a["run_id"] == b["run_id"] and
            a["event"] == b["event"] and
            a["freeze_git_blob"] == b["freeze_git_blob"],
            "SOURCE_OR_PROTOCOL_IDENTITY_DRIFT")
    require([x["lane"] for x in a["lanes"]] ==
            [x["lane"] for x in b["lanes"]] ==
            ["Wingless", "Yggdrasil"], "LANE_ORDER_DRIFT")
    a, b = copy.deepcopy(a), copy.deepcopy(b)
    maxdiff = 0.
    for left, right in zip(a["lanes"], b["lanes"]):
        for field in ("train_frozen_weights",
                      "train_f122_foundation_weights",
                      "train_query_only_weights"):
            x, y = left[field], right[field]
            names = ("A", "B") if isinstance(x, dict) else (None,)
            for name in names:
                lv = x[name] if name else x
                rv = y[name] if name else y
                require(len(lv) == len(rv), "WEIGHT_VECTOR_SHAPE_DRIFT")
                for xv, yv in zip(lv, rv):
                    require(type(xv) is float and type(yv) is float and
                            math.isfinite(xv) and math.isfinite(yv),
                            "NONFINITE_OR_NONFLOAT_MODEL_WEIGHT")
                    delta = abs(xv - yv)
                    require(delta <= TOLERANCE and round(xv, 12) == round(yv, 12),
                            "WEIGHT_NUMERICAL_DRIFT")
                    maxdiff = max(maxdiff, delta)
            # Rounded values are used only for equivalence classification, not
            # for changing the scientific candidate's exact inference weights.
            for lane in (left, right):
                val = lane[field]
                lane[field] = ({k: [round(v, 12) for v in vector]
                                for k, vector in val.items()}
                               if isinstance(val, dict) else
                               [round(v, 12) for v in val])
        for lane in (left, right):
            lane.pop("weights_sha256")
            lane.pop("selected_model_weights_sha256")
            lane.pop("query_only_weights_sha256")
            for model in lane["model_arms"].values():
                model.pop("weight_sha256")
    require(a == b, "NONNUMERICAL_OR_TRAIN_SCORE_DRIFT")
    return maxdiff

def audit(ubuntu, windows):
    a, sha_a = read_receipt(ubuntu)
    b, sha_b = read_receipt(windows)
    diff = compare(a, b)
    return {"schema": "forge.autonomy.f123.cross-os-train-receipt-parity.v1",
            "source_sha": a["source_sha"], "run_id": a["run_id"],
            "f123_freeze_git_blob": a["freeze_git_blob"],
            "canonical_inference_os": "ubuntu-latest",
            "ubuntu_train_receipt_sha256": sha_a,
            "windows_train_receipt_sha256": sha_b,
            "cross_os_weight_max_absolute_difference": diff,
            "weight_numerical_tolerance": TOLERANCE,
            "exact_full_report_identity": sha_a == sha_b,
            "score_and_selection_exact_identity": True,
            "nonfloat_provenance_exact_identity": True,
            "confirmation_inputs_generated": 0,
            "scientific_first_use_authorized": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ubuntu", required=True)
    p.add_argument("--windows", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    dest = Path(args.output)
    require(dest.parent.is_dir() and not dest.exists(),
            "OUTPUT_REPLACEMENT")
    report = audit(args.ubuntu, args.windows)
    with dest.open("xb") as f:
        f.write((json.dumps(report, sort_keys=True, separators=(",", ":"))
                 + "\n").encode())

if __name__ == "__main__":
    try:
        main()
    except (Invalid, KeyError, ValueError, TypeError, OSError) as exc:
        print("F123_CROSS_OS_CUSTODY=QUARANTINED " + str(exc), file=sys.stderr)
        raise SystemExit(1)

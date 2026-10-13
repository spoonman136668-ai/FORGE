"""Fail-closed R28 -> R29 successor proposal; never dispatches an experiment."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

PARENT_RUN = "38484042414"
PARENT_ID = "W-FORGE-R28-SOURCE-ROBUST-OBJECTIVE-01"
PARENT_BLOB = "0f51aedd38a726347780990027129c6881736b5d"
EXPECTED_OUTCOME = "NO_CONFIRMED_MINIMAX_GAIN"
NEXT_ID = "W-FORGE-R29-SOURCE-ROBUST-SUCCESSOR-01"

def parse(data):
    if not 0 < len(data) < 25_000_000:
        raise ValueError("INPUT_SIZE_INVALID")
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("DUPLICATE_JSON_KEY")
            d[k] = v
        return d
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("INVALID_FLOAT")))

def build(manifest, original, review, claim, run):
    if run != PARENT_RUN:
        raise ValueError("PARENT_RUN_ID_DRIFT")
    m, r, c = parse(manifest), parse(original), parse(claim)
    if m.get("experiment_id") != PARENT_ID:
        raise ValueError("PARENT_MANIFEST_DRIFT")
    if c != {
        "schema": "forge.r28.remote-first-use-claim.v1",
        "experiment_id": PARENT_ID,
        "prereg_blob": PARENT_BLOB,
        "source_commit": "f7cc4da574f55b28b9cadf89bc0f3ea3b9af7381", 
        "first_use_consumed": True,
        "rerun_allowed": False,
    }:
        raise ValueError("FIRST_USE_CLAIM_DRIFT")
    if r.get("github_run_id") != PARENT_RUN:
        raise ValueError("ORIGINAL_RUN_DRIFT")
    reviewer_path = Path(__file__).resolve().parents[1] / "r28-wingless" / "review.py"
    spec = importlib.util.spec_from_file_location("r28_independent_review", reviewer_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    expected = mod.verify(manifest, original)
    if parse(review) != expected or expected.get("outcome") != EXPECTED_OUTCOME:
        raise ValueError("INDEPENDENT_OUTCOME_DRIFT")
    if expected.get("independently_validated") is not True or expected.get("original_replay_allowed") is not False:
        raise ValueError("INDEPENDENT_CUSTODY_INVALID")
    return {
        "schema": "forge.r29.verified-successor-proposal.v1",
        "lane": "Wingless",
        "experiment_id": NEXT_ID,
        "parent_experiment_id": PARENT_ID,
        "parent_run_id": int(PARENT_RUN),
        "parent_original_sha256": hashlib.sha256(original).hexdigest(),
        "parent_outcome": EXPECTED_OUTCOME,
        "parent_replay_allowed": False,
        "hypothesis": "Under an unchanged training and compute budget, a train-only smooth robust objective may improve sealed worst-source accuracy over the failed hard-minimax family-selection method.",
        "required_gates": [
            "Independent design review and new falsifiable frozen preregistration",
            "Disjoint development and sealed heldout identities",
            "Source-birth and bounded implementation/interface qualification",
            "One durable first-use claim preceding worker execution",
            "One required full regression and separate scientific review",
        ],
        "proposal_only": True,
        "new_original_dispatch_authorized": False,
        "new_scientific_originals_executed": 0,
        "fsa_deferred": True,
        "ckb_execution_authority_unchanged": True,
    }

def main():
    p = argparse.ArgumentParser()
    for key in ("manifest", "original", "review", "claim", "run", "output"):
        p.add_argument("--" + key, required=True)
    a = p.parse_args()
    result = build(*(Path(getattr(a, key)).read_bytes() for key in ("manifest", "original", "review", "claim")), a.run)
    Path(a.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("R29_VERIFIED_NEGATIVE_TO_SUCCESSOR_PROPOSAL=PASS")
    print("R29_SCIENTIFIC_DISPATCH_AUTHORIZED=FALSE")

if __name__ == "__main__":
    main()

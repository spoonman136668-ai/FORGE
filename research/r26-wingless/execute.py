"""R26 prospective Wingless scientific original on NEW frozen cohorts only.

Imports the exact W-R52 scientific evaluator from a separately SHA-pinned,
read-only Wingless checkout. Not permitted to run historical W-R52 cohorts.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys

PINNED_WINGLESS_SOURCE = "b1e4972f04142f1f35f76f9483b12491dec4846c"
PREREG_GIT_BLOB = "ba54fa51807e7135b598ac2cefbe09984f162da6"
EXPERIMENT = "W-FORGE-R26-OUT-OF-COHORT-REPLICATION-01"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wingless-root", required=True)
    parser.add_argument("--prereg", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    pre = pathlib.Path(args.prereg)
    root = pathlib.Path(args.wingless_root)
    output = pathlib.Path(args.output)
    if not (root.is_absolute() and pre.is_absolute() and output.is_absolute()):
        raise RuntimeError("R26_ABSOLUTE_SOURCE_PATHS_REQUIRED")
    manifest_bytes = pre.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(manifest_bytes)).encode() + b"\0" + manifest_bytes).hexdigest()
    if blob != PREREG_GIT_BLOB:
        raise RuntimeError("R26_PREREGISTRATION_DRIFT")
    m = json.loads(manifest_bytes)
    if (m.get("schema") != "forge.r26.wingless.prospective-replication.v1"
            or m.get("experiment_id") != EXPERIMENT
            or m.get("source_sha") != PINNED_WINGLESS_SOURCE
            or m.get("first_use", {}).get("no_replay_on_uncertainty") is not True
            or not args.run_id.isdecimal() or len(args.run_id)>25):
        raise RuntimeError("R26_INVALID_FROZEN_EXPERIMENT_IDENTITY")
    blocks = tuple(tuple(b) for b in m["development_blocks"])
    heldout = tuple(m["sealed_heldout_seeds"])
    assert len(blocks) == 3 and all(len(x) == 16 for x in blocks) and len(heldout) == 48
    assert len(set(sum((list(x) for x in blocks), [])) | set(heldout)) == 96
    assert set(heldout).isdisjoint(set(range(3520,3568)))
    assert all(set(b).isdisjoint(set(range(3424,3504))) for b in blocks)
    path = root / m["source_path"]
    spec = importlib.util.spec_from_file_location("w52_r26_exact_source", path)
    if not spec or not spec.loader:
        raise RuntimeError("R26_W52_PINNED_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.DEV_BLOCKS == blocks or module.HELDOUT == heldout:
        raise RuntimeError("R26_OLD_ORIGINAL_COLLISION")
    module.DEV_BLOCKS = blocks
    module.HELDOUT = heldout
    # Fresh training occurs before untouched sealed evaluation inside W-R52
    # run(), with frozen equal-example budget and fixed prespecified arms.
    original = module.run()
    if original["classification"] not in m["outcomes"]:
        raise RuntimeError("R26_UNEXPECTED_OUTCOME")
    if original["development_blocks"] != blocks or original["sealed_heldout_seeds"] != heldout:
        raise RuntimeError("R26_SOURCE_IGNORED_FROZEN_COHORT")
    result = {
        "schema": "forge.r26.wingless.original.v1",
        "experiment_id": EXPERIMENT,
        "method_source_sha": PINNED_WINGLESS_SOURCE,
        "manifest_git_blob": PREREG_GIT_BLOB,
        "github_run_id": args.run_id,
        "source_result": original,
        "science_production_accepted": False,
        "original_replay_authorized": False,
    }
    payload = (json.dumps(result, sort_keys=True, separators=(",",":"), allow_nan=False)+"\n").encode()
    with output.open("xb") as f:
        f.write(payload)
        f.flush()
        import os
        os.fsync(f.fileno())
    print("FORGE_R26_ORIGINAL_RECORDED_SHA256="+hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    main()

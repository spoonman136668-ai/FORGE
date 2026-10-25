#!/usr/bin/env python3
"""L9 neural TRAIN-only development fit using byte-identical frozen model suite.

No selector or audit reader. Inference/training checkpoint hashes and bytes retained
for independently sealed SELECT; no raw corpus or reference string in receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import l9_model_suite as model
from l9_train_select_candidate import load_train_select, EXPECTED_ROLE_SHA

VALID_ARMS = ("GRU_SEQ2SEQ", "SMALL_TRANSFORMER")
SEEDS = (1701, 1702)
EPOCHS = (4, 8, 12)
SUITE_BLOB = "710ce648a30ffc55647f689c5f4aa3ac13b07066"
SCHEMA = "forge.optimizer.language.l9.neural-train-only-development-v1"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def run(repo: Path, arm: str, seed: int, out: Path):
    if arm not in VALID_ARMS or seed not in SEEDS:
        raise ValueError("unfrozen model arm or seed")
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
    original = Path(__file__).resolve().parent
    source = original / "l9_model_suite.py"
    # The actual Git blob is independently pinned by the Actions workflow.
    assert source.exists()
    start = time.perf_counter()
    cpu_start = time.process_time()
    examples, _ = load_train_select(repo)
    train = [x for x in examples if x.role == "L9_TRAIN"]
    select_count = sum(x.role == "L9_SELECT" for x in examples)
    assert len(train) == 8480 and select_count == 2154
    assert not any(x.role == "L9_AUDIT_DEV" for x in examples)
    tensor_start = time.perf_counter()
    result = model.train_neural(arm, train, seed, device="cpu")
    train_wall = time.perf_counter() - tensor_start
    assert set(result["checkpoints"]) == set(EPOCHS)
    assert result["arm"] == arm and result["seed"] == seed
    entries = {}
    for epoch in EPOCHS:
        checkpoint = result["checkpoints"][epoch]
        raw = checkpoint["inference_state"]
        assert len(raw) == checkpoint["inference_bytes"]
        assert len(raw) <= model.INFERENCE_STATE_CEILING
        assert checkpoint["training_checkpoint_bytes"] <= model.TRAINING_CHECKPOINT_CEILING
        dest = out / f"{arm}-seed{seed}-epoch{epoch}-inference.pt"
        dest.write_bytes(raw)
        entries[str(epoch)] = {
            "inference_sha256": sha(raw),
            "inference_file": dest.name,
            "inference_bytes": len(raw),
            "training_checkpoint_bytes": checkpoint["training_checkpoint_bytes"],
        }
    import torch
    # Receipts contain only source identities, resource metrics, checkpoint IDs;
    # no WebNLG reference text, model example input, or official TEST material.
    receipt = {
        "schema": SCHEMA,
        "status": "NEURAL_TRAIN_COMPLETE_SELECT_NOT_RUN_DEVELOPMENT_ONLY",
        "source_release_sha": "a7ea49b5ffa5011edf81e8530c59b3552a965023",
        "role_identity_sha256": EXPECTED_ROLE_SHA,
        "model_suite_git_blob": SUITE_BLOB,
        "arm": arm,
        "seed": seed,
        "model_fit_role": "L9_TRAIN",
        "train_examples": len(train),
        "select_count_loaded_but_unseen_by_fit": select_count,
        "select_fidelity_scored": False,
        "audit_dev_reference_consumed": False,
        "official_test_consumed": False,
        "checkpoint_epochs": list(EPOCHS),
        "checkpoints": entries,
        "exclusions": result["exclusions"],
        "fit_wall_seconds": round(train_wall, 3),
        "end_to_end_wall_seconds": round(time.perf_counter() - start, 3),
        "end_to_end_cpu_seconds": round(time.process_time() - cpu_start, 3),
        "torch_version": torch.__version__,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "accelerator": "CPU_ONLY",
        "scientific_go": False,
    }
    raw = model.canonical_json_bytes(receipt)
    (out / "receipt.json").write_bytes(raw)
    print("L9_NEURAL_TRAIN_COMPLETE=TRUE", flush=True)
    print("L9_TRAIN_EXAMPLES=8480", flush=True)
    print("L9_SELECT_SCORED=FALSE", flush=True)
    print("L9_AUDIT_DEV_REFERENCE_CONSUMED=FALSE", flush=True)
    print("L9_OFFICIAL_TEST_CONSUMED=FALSE", flush=True)
    print("L9_NEURAL_TRAIN_RECEIPT_SHA256=" + sha(raw), flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--webnlg-repo",type=Path,required=True)
    parser.add_argument("--arm",choices=VALID_ARMS,required=True)
    parser.add_argument("--seed",type=int,choices=SEEDS,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    run(args.webnlg_repo,args.arm,args.seed,args.out)

if __name__ == "__main__":
    main()

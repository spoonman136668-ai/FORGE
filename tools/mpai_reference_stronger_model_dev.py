"""Stronger non-Qwen local-model development-only evidence use experiment.

Same four already exposed questions as previous 360M study. This is an
engineering diagnostic, never first-use holdout or scientific acceptance.
Original source and consumer behavior are unchanged. No external model API,
source mutation, continuous writer or controller. Trial content private.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import time
import urllib.request

from mpai_reference_model_dev import (
    QUESTIONS, RECORD, load, require, verify_pair
)

MODEL_URL = (
    "https://huggingface.co/bartowski/SmolLM2-1.7B-Instruct-GGUF/resolve/"
    "72da00985aa7cb57cd436a6172be99c3bd906d9c/"
    "SmolLM2-1.7B-Instruct-Q4_K_M.gguf?download=true"
)
MODEL_SHA256 = "77665ea4815999596525c636fbeb56ba8b080b46ae85efef4f0d986a139834d7"
MODEL_BYTES = 1055609824
N_CTX = 2048
MAX_COMPLETION_TOKENS = 24
ALLOWED = frozenset(("YES", "NO", "UNKNOWN"))


def download_verified(path: Path) -> None:
    require(not path.exists(), "MODEL_FILE_COLLISION")
    require(shutil.disk_usage(str(path.parent)).free > 2_100_000_000,
            "STRONGER_SCRATCH_SPACE")
    h = hashlib.sha256()
    total = 0
    started = time.monotonic()
    req = urllib.request.Request(
        MODEL_URL, headers={"User-Agent": "FORGE-MPAI-stronger-development/1"})
    with urllib.request.urlopen(req, timeout=50) as response, path.open("xb") as file:
        while True:
            blob = response.read(4 * 1024 * 1024)
            if not blob:
                break
            total += len(blob)
            require(total <= MODEL_BYTES and time.monotonic()-started < 650,
                    "STRONGER_MODEL_DOWNLOAD_BOUND")
            h.update(blob)
            file.write(blob)
    require(total == MODEL_BYTES and h.hexdigest() == MODEL_SHA256,
            "STRONGER_MODEL_SOURCE_DRIFT")
    with path.open("rb") as f:
        require(f.read(4) == b"GGUF", "STRONGER_MODEL_FORMAT")


def score(response: str) -> str:
    # Strict single-answer grammar handles output format in the model call.
    normalized = response.strip().upper()
    return normalized if normalized in ALLOWED else "UNSCORABLE"


def evaluate(args: argparse.Namespace) -> dict:
    root = args.scratch.resolve(strict=True)
    require(re.fullmatch(r"[a-f0-9]{40}", args.source) is not None,
            "SOURCE_ID_INVALID")
    model_path = root / "pinned-stronger-nonqwen.gguf"
    # Public model download ONLY, before reading any private material.
    download_verified(model_path)
    os.environ["HF_HUB_OFFLINE"] = "1"
    def block_network(*_args, **_kwargs):
        raise RuntimeError("MPAI_DEV_PRIVATE_EVIDENCE_NO_NETWORK")
    socket.socket = block_network
    baseline = load(args.baseline)
    candidate = load(args.candidate)
    pointer, full = verify_pair(baseline, candidate, args.source)
    from llama_cpp import Llama, LlamaGrammar
    grammar = LlamaGrammar.from_string(
        'root ::= "YES" | "NO" | "UNKNOWN"', verbose=False)
    model = Llama(model_path=str(model_path), n_ctx=N_CTX,
                  n_threads=4, n_batch=128, n_gpu_layers=0,
                  seed=137, verbose=False)
    rows = []
    t_start = time.monotonic()
    for i, (case_id, question, expected_full) in enumerate(QUESTIONS):
        arms = ("reference_only", "full_evidence")
        if i % 2:
            arms = tuple(reversed(arms))
        for arm in arms:
            material = pointer if arm == "reference_only" else full
            prompt = (
                "Answer based only on the supplied evidence. "
                "Use YES or NO only if the evidence explicitly establishes it; "
                "otherwise answer UNKNOWN. Exactly one word.\n"
                "Evidence:\n" + material + "\n"
                "Question: " + question + "\nAnswer:"
            )
            started = time.monotonic()
            completion = model.create_completion(
                prompt=prompt, temperature=0.0, top_p=1.0,
                max_tokens=MAX_COMPLETION_TOKENS, grammar=grammar)
            elapsed_ms = max(1, int(1000 * (time.monotonic()-started)))
            answer = completion["choices"][0]["text"]
            usage = completion["usage"]
            require(type(answer) is str
                    and 0 < int(usage["prompt_tokens"]) < N_CTX
                    and 0 <= int(usage["completion_tokens"]) <= MAX_COMPLETION_TOKENS,
                    "COMPLETION_CONTRACT")
            answer = score(answer)
            rows.append({
                "case_id": case_id, "arm": arm, "response": answer,
                "expected_full_evidence": expected_full,
                "expected_given_arm": "UNKNOWN"
                    if arm == "reference_only" else expected_full,
                "prompt_tokens": int(usage["prompt_tokens"]),
                "output_tokens": int(usage["completion_tokens"]),
                "inference_ms": elapsed_ms,
            })
    require(len(rows) == 8, "EXACT_EIGHT_MODEL_CALLS")
    stats = {}
    for arm in ("reference_only", "full_evidence"):
        selected = [r for r in rows if r["arm"] == arm]
        require(len(selected) == 4, "UNBALANCED_ARMS")
        stats[arm] = {
            "calls": 4,
            "full_truth_agreement": sum(
                r["response"] == r["expected_full_evidence"] for r in selected),
            "evidence_calibrated_agreement": sum(
                r["response"] == r["expected_given_arm"] for r in selected),
            "abstentions": sum(r["response"] == "UNKNOWN" for r in selected),
            "unscorable": sum(r["response"] == "UNSCORABLE" for r in selected),
            "prompt_tokens": sum(r["prompt_tokens"] for r in selected),
            "output_tokens": sum(r["output_tokens"] for r in selected),
            "inference_ms": sum(r["inference_ms"] for r in selected),
        }
    receipt = {
        "schema": "forge.mpai-reference-stronger-development.v1",
        "source_sha": args.source,
        "model": "SmolLM2-1.7B-Instruct-Q4_K_M",
        "model_sha256": MODEL_SHA256,
        "questions_exposed_in_prior_360m_study": True,
        "real_local_model_calls": 8,
        "same_model_and_questions_both_arms": True,
        "matched_information": False,
        "baseline_reference_only": True,
        "candidate_verified_full_evidence": True,
        "output_constrained_to_three_decisions": True,
        "independent_external_agent_authenticated": False,
        "first_use_holdout": False,
        "blinded_independent_grading": False,
        "scientific_acceptance": False,
        "production_memory_writes": 0,
        "elapsed_ms": int(1000*(time.monotonic()-t_start)),
        "stats": stats,
        "private_model_decisions": rows,
    }
    (root / "private-stronger-decisions.json").write_text(
        json.dumps(receipt, sort_keys=True), encoding="utf-8")
    print("MPAI_STRONG_MODEL_SHA256=PASS")
    print("MPAI_STRONG_ACTUAL_MODEL_CALLS=8")
    for name in ("reference_only", "full_evidence"):
        for key, value in stats[name].items():
            print("MPAI_STRONG_" + name.upper() + "_" + key.upper() + "=" + str(value))
    print("MPAI_STRONG_OLD_EXPOSED_QUESTIONS=TRUE")
    print("MPAI_STRONG_MATCHED_INFORMATION=FALSE")
    print("MPAI_STRONG_FIRST_USE=FALSE")
    print("MPAI_STRONG_SCIENTIFIC_ADMISSION=FALSE")
    print("MPAI_STRONG_PRODUCTION_WRITES=0")
    del model
    gc.collect()
    return receipt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    evaluate(ap.parse_args())


if __name__ == "__main__":
    main()

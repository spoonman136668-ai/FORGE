"""MP-AI10: source-pinned equal-information policy comparison, DEVELOPMENT ONLY.

A real non-Qwen 1.7B local model receives the identical full accepted record
on every arm and task. The only difference is instructions: direct answer
versus explicit verification/uncertainty reflection. Frozen novel development
questions are not a secret held-out benchmark or independently graded science.
No provider API, scheduler, controller, promotion, writer or production changes.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import time

from mpai_reference_stronger_model_dev import (
    MODEL_BYTES, MODEL_SHA256, MAX_COMPLETION_TOKENS, N_CTX,
    download_verified, score,
)
from mpai_reference_model_dev import (
    RECORD, QUESTIONS as PREVIOUS_QUESTIONS, load, require, verify_pair,
)

# New, distinct development questions; independent first use is NOT claimed.
# Frozen before running the first comparison (same old exposed source lesson).
TASKS = (
    ("new-tiered-input-upper", "Did tiered retrieval use under 2,000 input tokens?", "YES"),
    ("new-legacy-input-upper", "Did legacy retrieval use under 2,000 input tokens?", "NO"),
    ("new-context-40pct", "Was the reported context-byte reduction greater than 40 percent?", "YES"),
    ("new-time-30pct", "Was the measured generation-time reduction greater than 30 percent?", "NO"),
    ("new-call-count", "Were there more questions than genuine model calls?", "NO"),
    ("new-answer-pair-identity", "Were all eight answer pairs identical between arms?", "NO"),
    ("new-context-60pct", "Was the context-byte saving greater than 60 percent?", "NO"),
    ("new-both-over-half", "Were both input-token and context-byte savings greater than 50 percent?", "YES"),
    ("new-causal-mechanism", "Was a causal explanation for differences in answers established?", "UNKNOWN"),
    ("new-gpu-status", "Did the study also run on a dedicated graphics card?", "UNKNOWN"),
    ("new-milliseconds", "Did total measured generation time decrease by over 4,000 milliseconds?", "YES"),
    ("new-factual-success", "Were all eight candidate answers factually correct?", "UNKNOWN"),
)

assert len(TASKS) == 12
assert len({t[0] for t in TASKS}) == len(TASKS)
assert not ({t[0] for t in TASKS} & {t[0] for t in PREVIOUS_QUESTIONS})
assert all(t[2] in ("YES", "NO", "UNKNOWN") for t in TASKS)

# Neither arm gets extra content. These are technique instructions, not facts.
SYSTEM = {
    "direct": (
        "Based only on the evidence, answer the question directly. "
        "If the record does not establish the answer, answer UNKNOWN. "
        "Choose exactly YES, NO, or UNKNOWN."
    ),
    "reflect": (
        "Before deciding, check numerical thresholds and what the record "
        "does not establish. Do not confuse reported observations with proof. "
        "Choose exactly YES, NO, or UNKNOWN."
    ),
}
ARMS = ("direct", "reflect")


def verify_same_record(a: dict, b: dict, sha: str) -> str:
    # Real producer's default and resolved outputs must both bind the same
    # source SHA and same preview. The resolved full record is verified against
    # its original content SHA and provenance by verify_pair.
    _, full = verify_pair(a, b, sha)
    require(type(full) is str and len(full) < 2200 and
            "no independent factual accuracy grades" in full,
            "FULL_LESSON_UNVERIFIED")
    return full


def evaluate(args: argparse.Namespace) -> dict:
    root = args.scratch.resolve(strict=True)
    require(re.fullmatch(r"[a-f0-9]{40}", args.source) is not None, "SOURCE_FORMAT")
    model_path = root / "pinned-equal-info-smollm2-1p7b.gguf"
    # Download only pinned public weights BEFORE opening private-memory files.
    download_verified(model_path)
    os.environ["HF_HUB_OFFLINE"] = "1"
    def deny(*_args, **_kwargs):
        raise RuntimeError("MPAI10_NO_NETWORK_AFTER_PUBLIC_WEIGHTS")
    socket.socket = deny
    a = load(args.baseline)
    b = load(args.candidate)
    lesson = verify_same_record(a, b, args.source)
    full_hash = hashlib.sha256(lesson.encode("utf-8")).hexdigest()
    from llama_cpp import Llama, LlamaGrammar
    grammar = LlamaGrammar.from_string(
        'root ::= "YES" | "NO" | "UNKNOWN"', verbose=False)
    model = Llama(model_path=str(model_path), n_ctx=N_CTX, n_threads=4,
                  n_batch=128, n_gpu_layers=0, seed=137, verbose=False)
    rows = []
    start = time.monotonic()
    for i, (key, question, expected) in enumerate(TASKS):
        order = ARMS if i % 2 == 0 else tuple(reversed(ARMS))
        for arm in order:
            # Source information identity is exact, byte-for-byte.
            prompt = (SYSTEM[arm] + "\nEvidence:\n" + lesson
                      + "\nQuestion: " + question + "\nAnswer:")
            t = time.monotonic()
            response = model.create_completion(
                prompt=prompt, temperature=0.0, top_p=1.0,
                max_tokens=MAX_COMPLETION_TOKENS, grammar=grammar)
            ms = max(1, int((time.monotonic() - t) * 1000))
            raw = response["choices"][0]["text"]
            usage = response["usage"]
            require(type(raw) is str
                    and 0 < int(usage["prompt_tokens"]) < N_CTX
                    and 0 <= int(usage["completion_tokens"]) <= MAX_COMPLETION_TOKENS,
                    "MODEL_OUTPUT_INVALID")
            rows.append({
                "task_id": key, "arm": arm, "expected_development": expected,
                "decision": score(raw), "private_raw": raw[:1024],
                "lesson_sha256": full_hash,
                "prompt_tokens": int(usage["prompt_tokens"]),
                "completion_tokens": int(usage["completion_tokens"]),
                "inference_ms": ms,
            })
    require(len(rows) == len(TASKS) * 2, "MODEL_CALL_COUNT")
    stats = {}
    for arm in ARMS:
        selected = [x for x in rows if x["arm"] == arm]
        require(len(selected) == len(TASKS), "ARM_COUNT")
        stats[arm] = {
            "calls": len(selected),
            "correct_development_labels": sum(
                x["decision"] == x["expected_development"] for x in selected),
            "unscorable": sum(x["decision"] == "UNSCORABLE" for x in selected),
            "abstained": sum(x["decision"] == "UNKNOWN" for x in selected),
            "prompt_tokens": sum(x["prompt_tokens"] for x in selected),
            "completion_tokens": sum(x["completion_tokens"] for x in selected),
            "inference_ms": sum(x["inference_ms"] for x in selected),
        }
    require(len({r["lesson_sha256"] for r in rows}) == 1,
            "EQUAL_INFORMATION_DRIFT")
    receipt = {
        "schema": "forge.mpai10.equal-information-development.v1",
        "model_sha256": MODEL_SHA256,
        "source_sha": args.source,
        "lesson_id": RECORD,
        "full_lesson_sha256": full_hash,
        "same_full_evidence_both_arms": True,
        "same_local_model_both_arms": True,
        "same_questions_both_arms": True,
        "questions_new_relative_to_prior_four": True,
        "source_lesson_already_exposed": True,
        "development_only": True,
        "first_use_holdout": False,
        "independent_blinded_grading": False,
        "independent_external_agent_authenticated": False,
        "scientific_qualification": False,
        "production_writes": 0,
        "real_local_model_calls": len(rows),
        "wall_elapsed_ms": int(1000*(time.monotonic()-start)),
        "stats": stats,
        "private_trials": rows,
    }
    (root / "mpai10-private-decisions.json").write_text(
        json.dumps(receipt, sort_keys=True), encoding="utf-8")
    print("MPAI10_VERIFIED_MODEL=PASS")
    print("MPAI10_REAL_MODEL_CALLS=" + str(len(rows)))
    print("MPAI10_SAME_FACTS_BOTH_ARMS=TRUE")
    for arm in ARMS:
        for key, value in stats[arm].items():
            print("MPAI10_" + arm.upper() + "_" + key.upper() + "=" + str(value))
    print("MPAI10_PRIOR_FOUR_CASES_EXCLUDED=TRUE")
    print("MPAI10_SOURCE_LESSON_PREVIOUSLY_EXPOSED=TRUE")
    print("MPAI10_INDEPENDENT_REVIEW=FALSE")
    print("MPAI10_FIRST_USE_HOLDOUT=FALSE")
    print("MPAI10_SCIENTIFIC_QUALIFICATION=FALSE")
    print("MPAI10_PRODUCTION_WRITES=0")
    del model
    gc.collect()
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    evaluate(p.parse_args())

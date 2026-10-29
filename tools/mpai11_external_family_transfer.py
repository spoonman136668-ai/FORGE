"""MP-AI11: external author science-task transfer, source-verified DEVELOPMENT ONLY.

This module tests a general decision instruction against an independently
authored public question family on the same non-Qwen local model. Both arms
see precisely the same task options and the same pinned accepted lesson; only
their decision instructions differ. Externally published labels remain
outside model prompts. A publicly released benchmark is not a sealed holdout,
nor independent scientific witness or authenticated external agent.

No network access after public weights and public questions are verified;
private Mind-Palace records only opened after network denial.
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
import urllib.request

from mpai_reference_model_dev import load, require
from mpai_reference_equal_information_dev import (
    MODEL_SHA256, N_CTX, MAX_COMPLETION_TOKENS, ARMS, SYSTEM,
    verify_same_record,
)
from mpai_reference_stronger_model_dev import download_verified

MIRROR_REPO = "zhangSchnee/Arc-challenge"
MIRROR_COMMIT = "ae51da706ed693b99e7de41c418dad13845e3c09"
MIRROR_PATH = "ARC-V1-Feb2018-2/arc_corpus/Challenge_dir/dev.jsonl"
MIRROR_GIT_BLOB_SHA1 = "907d3294123dbe34929e1fb802c2504d698f7dbd"
MIRROR_URL = (
    "https://raw.githubusercontent.com/" + MIRROR_REPO + "/" +
    MIRROR_COMMIT + "/" + MIRROR_PATH
)
SEED = "MPAI11-AI2-ARC-TRANSFER-DEVELOPMENT-20261029-v1"
EXPECTED_LINES = 299
CASES = 24
LABELS = frozenset(("A", "B", "C", "D"))
ALL_DECISIONS = LABELS | {"UNKNOWN"}
MAX_DATA_BYTES = 600_000

# One fixed policy pair, frozen before external model outcomes.
POLICIES = {
    "direct": (
        "Answer the question using the evidence and the four choices. "
        "Select the best-supported letter A, B, C or D, or UNKNOWN if "
        "there is not enough information. Output one label."
    ),
    "reflect": (
        "Before choosing, verify what the supplied evidence establishes, "
        "distinguish supported inference from assumptions, and check uncertainty. "
        "Use the same supplied evidence only. "
        "Choose A, B, C or D, or UNKNOWN if evidence is insufficient. "
        "Output one label."
    ),
}
assert set(POLICIES) == set(ARMS)


def validate_public_blob(raw: bytes) -> tuple[list[dict], str]:
    require(type(raw) is bytes and len(raw) <= MAX_DATA_BYTES,
            "PUBLIC_DATA_BYTE_LIMIT")
    signature = b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    require(hashlib.sha1(signature).hexdigest() == MIRROR_GIT_BLOB_SHA1,
            "PUBLIC_GIT_BLOB_IDENTITY_DRIFT")
    sha256 = hashlib.sha256(raw).hexdigest()
    lines = raw.decode("utf-8").splitlines()
    require(len(lines) == EXPECTED_LINES, "PUBLIC_ROW_COUNT_DRIFT")
    rows = [json.loads(line) for line in lines]
    ids = [r.get("id") for r in rows]
    require(all(type(x) is str and x for x in ids)
            and len(set(ids)) == len(ids), "PUBLIC_QUESTION_IDENTITY_DRIFT")
    return rows, sha256


def freeze_public_cohort(rows: list[dict]) -> tuple[list[dict], dict[str, str], str]:
    """Freeze solely by immutable question IDs and text format, NOT answers."""
    eligible = []
    ids = set()
    for record in rows:
        key = record.get("id")
        question = record.get("question")
        if type(key) is not str or key in ids:
            raise RuntimeError("MPAI11_SOURCE_DUPLICATE_ID")
        ids.add(key)
        if type(question) is not dict:
            continue
        stem, options = question.get("stem"), question.get("choices")
        if (type(stem) is not str or not (20 <= len(stem) <= 650)
                or type(options) is not list or len(options) != 4):
            continue
        labels = [x.get("label") for x in options if type(x) is dict]
        texts = [x.get("text") for x in options if type(x) is dict]
        if (len(labels) != 4 or set(labels) != LABELS
                or len(set(labels)) != 4
                or not all(type(t) is str and 1 <= len(t) <= 260
                            for t in texts)):
            continue
        answer = record.get("answerKey")
        if answer not in LABELS:
            continue
        choices = sorted(((opt["label"], opt["text"])
                          for opt in options), key=lambda x: x[0])
        # Ignore untrusted third-party option enrichment fields (para etc.)
        # The original answerKey never enters the task-facing object.
        cleaned = {"id": key, "question": stem,
                   "choices": [{"label": k, "text": v} for k, v in choices]}
        selector = hashlib.sha256(
            (SEED + "|" + key).encode("utf-8")).hexdigest()
        eligible.append((selector, cleaned, answer))
    eligible.sort(key=lambda t: (t[0], t[1]["id"]))
    require(len(eligible) >= CASES, "PUBLIC_ELIGIBLE_COHORT_TOO_SMALL")
    selected = eligible[:CASES]
    tasks = [x[1] for x in selected]
    gold = {x[1]["id"]: x[2] for x in selected}
    require(len(tasks) == CASES and len(gold) == CASES,
            "FROZEN_COHORT_DUPLICATE")
    canonical = json.dumps(
        tasks, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return tasks, gold, digest


def fetch_public_questions() -> bytes:
    req = urllib.request.Request(
        MIRROR_URL, headers={"User-Agent": "MPAI11-external-public-dev/1"})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=45) as stream:
        raw = stream.read(MAX_DATA_BYTES + 1)
    require(time.monotonic() - start < 90, "PUBLIC_DOWNLOAD_TIME")
    require(len(raw) <= MAX_DATA_BYTES, "PUBLIC_DOWNLOAD_LIMIT")
    return raw


def prompt(task: dict, instruction: str, lesson: str) -> str:
    # These are identical across both arms except for the instruction.
    # Gold labels, answer key, and optional 'para' fields never enter.
    choices = "\n".join(
        opt["label"] + ": " + opt["text"] for opt in task["choices"])
    return (
        instruction + "\nEarlier advisory memory (same in both arms):\n" +
        lesson + "\nScience question:\n" + task["question"] +
        "\nChoices:\n" + choices + "\nAnswer:"
    )


def evaluate(args: argparse.Namespace) -> dict:
    root = args.scratch.resolve(strict=True)
    require(re.fullmatch("[a-f0-9]{40}", args.source) is not None,
            "SOURCE_PIN_INVALID")
    # Model and benchmark are immutable PUBLIC sources downloaded first.
    model_file = root / "verified-smollm2-1p7b.gguf"
    download_verified(model_file)
    public_raw = fetch_public_questions()
    source_rows, public_sha = validate_public_blob(public_raw)
    tasks, gold, cohort_sha = freeze_public_cohort(source_rows)
    del source_rows, public_raw
    os.environ["HF_HUB_OFFLINE"] = "1"
    def denied(*_a, **_kw):
        raise RuntimeError("MPAI11_NETWORK_DENIED_WITH_PRIVATE_CONTEXT")
    socket.socket = denied
    baseline = load(args.baseline)
    full = load(args.candidate)
    lesson = verify_same_record(baseline, full, args.source)
    lesson_sha = hashlib.sha256(lesson.encode("utf-8")).hexdigest()
    from llama_cpp import Llama, LlamaGrammar
    grammar = LlamaGrammar.from_string(
        'root ::= "A" | "B" | "C" | "D" | "UNKNOWN"', verbose=False)
    model = Llama(model_path=str(model_file), n_ctx=N_CTX, n_threads=4,
                  n_batch=128, n_gpu_layers=0, seed=137, verbose=False)
    rows = []
    start = time.monotonic()
    for i, task in enumerate(tasks):
        order = ARMS if i % 2 == 0 else tuple(reversed(ARMS))
        for arm in order:
            instruction = POLICIES[arm]
            question = prompt(task, instruction, lesson)
            started = time.monotonic()
            result = model.create_completion(
                prompt=question, temperature=0.0, top_p=1.0,
                grammar=grammar, max_tokens=MAX_COMPLETION_TOKENS)
            ms = max(1, int(1000*(time.monotonic()-started)))
            answer = result["choices"][0]["text"]
            usage = result["usage"]
            require(type(answer) is str and
                    0 < int(usage["prompt_tokens"]) < N_CTX
                    and 0 <= int(usage["completion_tokens"]) <= MAX_COMPLETION_TOKENS,
                    "COMPLETION_CONTRACT")
            decision = answer.strip().upper()
            if decision not in ALL_DECISIONS:
                decision = "UNSCORABLE"
            rows.append({
                "id": task["id"], "arm": arm, "decision": decision,
                "private_raw": answer[:500],
                "lesson_sha256": lesson_sha,
                "prompt_tokens": int(usage["prompt_tokens"]),
                "output_tokens": int(usage["completion_tokens"]),
                "inference_ms": ms,
            })
    require(len(rows) == CASES * 2, "MODEL_CALL_COUNT")
    # Gold is accessed only AFTER both arms have finished model inference.
    stats = {}
    paired = {t["id"]: {} for t in tasks}
    for item in rows:
        paired[item["id"]][item["arm"]] = item["decision"]
    require(all(set(x) == set(ARMS) for x in paired.values()), "PAIRS_INCOMPLETE")
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        stats[arm] = {
            "calls": len(selected),
            "correct_official_gold": sum(
                r["decision"] == gold[r["id"]] for r in selected),
            "wrong_labeled": sum(
                r["decision"] in LABELS and r["decision"] != gold[r["id"]]
                for r in selected),
            "unknown": sum(r["decision"] == "UNKNOWN" for r in selected),
            "unscorable": sum(r["decision"] == "UNSCORABLE" for r in selected),
            "prompt_tokens": sum(r["prompt_tokens"] for r in selected),
            "output_tokens": sum(r["output_tokens"] for r in selected),
            "inference_ms": sum(r["inference_ms"] for r in selected),
        }
    def right(id: str, arm: str) -> bool:
        return paired[id][arm] == gold[id]
    delta = {
        "reflect_wins_direct_wrong": sum(
            right(id, "reflect") and not right(id, "direct") for id in paired),
        "direct_wins_reflect_wrong": sum(
            right(id, "direct") and not right(id, "reflect") for id in paired),
        "both_correct": sum(
            right(id, "direct") and right(id, "reflect") for id in paired),
        "both_not_correct": sum(
            not right(id, "direct") and not right(id, "reflect") for id in paired),
    }
    require(sum(delta.values()) == CASES, "PAIRED_DENOMINATOR")
    require(len({x["lesson_sha256"] for x in rows}) == 1,
            "EVIDENCE_INFORMATION_MISMATCH")
    receipt = {
        "schema": "forge.mpai11.public-external-family-development.v1",
        "benchmark": "AI2-ARC-Challenge-Dev",
        "mirror": MIRROR_REPO + "@" + MIRROR_COMMIT,
        "mirror_git_blob_sha1": MIRROR_GIT_BLOB_SHA1,
        "public_source_sha256": public_sha,
        "cohort_sha256": cohort_sha,
        "model_sha256": MODEL_SHA256,
        "source_sha": args.source,
        "full_lesson_sha256": lesson_sha,
        "same_tasks_model_and_evidence_both_arms": True,
        "gold_never_in_model_prompts": True,
        "external_gold_from_public_dataset": True,
        "independent_blinded_review": False,
        "sealed_first_use": False,
        "public_benchmark_training_contamination_unknown": True,
        "externally_authenticated_agent_provider": False,
        "science_qualified": False,
        "production_writes": 0,
        "real_local_model_calls": len(rows),
        "elapsed_ms": int(1000*(time.monotonic()-start)),
        "stats": stats,
        "paired": delta,
        "private_decisions": rows,
    }
    (root / "mpai11-private-results.json").write_text(
        json.dumps(receipt, sort_keys=True), encoding="utf-8")
    print("MPAI11_PUBLIC_SOURCE_GIT_BLOB=PASS")
    print("MPAI11_PUBLIC_SOURCE_SHA256=" + public_sha)
    print("MPAI11_COHORT_SHA256=" + cohort_sha)
    print("MPAI11_MODEL_SHA256=PASS")
    print("MPAI11_ACTUAL_MODEL_CALLS=" + str(len(rows)))
    for arm in ARMS:
        for key, value in stats[arm].items():
            print("MPAI11_" + arm.upper() + "_" + key.upper() + "=" + str(value))
    for key, value in delta.items():
        print("MPAI11_PAIRED_" + key.upper() + "=" + str(value))
    print("MPAI11_EQUAL_TASKS_EVIDENCE_MODEL=TRUE")
    print("MPAI11_PUBLIC_NOT_SEALED=TRUE")
    print("MPAI11_INDEPENDENT_BLIND_REVIEW=FALSE")
    print("MPAI11_SCIENTIFIC_QUALIFICATION=FALSE")
    print("MPAI11_PRODUCTION_WRITES=0")
    del model
    gc.collect()
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    evaluate(parser.parse_args())

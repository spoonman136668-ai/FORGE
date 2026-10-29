"""Read-only development ablation on one source-pinned real Mind-Palace lesson.

Compares default reference-only and opt-in verified full evidence for the
same independently downloaded, SHA256-checked, non-Qwen local GGUF model.
No first-use holdout, independent grading, external agent identity, writes,
promotion, model improvement claim, or paid inference.
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

MODEL_URL = (
    "https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/resolve/"
    "ab928a97ee49f3a015f35194879f68211291d6ca/"
    "SmolLM2-360M-Instruct-Q4_K_M.gguf?download=true"
)
MODEL_BYTES = 270590880
MODEL_SHA256 = "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2"
RECORD = "lesson/mpai-hindsight-h2-development-context-efficiency-20261028"
QUESTIONS = (
    ("independent_accuracy", "Did the experiment prove independently graded factual accuracy improvement?", "NO"),
    ("input_tokens", "Did the development comparison reduce input token use by more than half?", "YES"),
    ("output_cap", "Did both arms hit the 96-token output cap on every case?", "YES"),
    ("first_use", "Was an authenticated first-use holdout established?", "NO"),
)
N_CTX = 2048
MAX_OUTPUT_TOKENS = 32


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError("MPAI_DEV_" + message)


def load(path: Path) -> dict:
    require(path.is_file(), "PRIVATE_INPUT_MISSING")
    doc = json.loads(path.read_text(encoding="utf-8"))
    require(doc.get("schema") == "forge.mpai05.readonly-consumer-result.v1",
            "PRIVATE_INPUT_SCHEMA")
    require(doc.get("receipt", {}).get("read_only") is True, "READ_ONLY_REQUIRED")
    return doc


def verify_pair(baseline: dict, candidate: dict, source_sha: str) -> tuple[str, str]:
    a, b = baseline["result"], candidate["result"]
    require(baseline["receipt"].get("reference_followup") == "disabled",
            "BASELINE_ROUTING")
    require(candidate["receipt"].get("reference_followup") == "enabled",
            "CANDIDATE_ROUTING")
    require(baseline["receipt"].get("resolved_reference_count") == 0,
            "BASELINE_UNCHANGED")
    require(candidate["receipt"].get("resolved_reference_count", 0) >= 1,
            "NO_RESOLVED_RECORD")
    require(a.get("source_sha") == source_sha and b.get("source_sha") == source_sha,
            "SOURCE_SHA_DRIFT")
    require(a.get("records_sha256") == b.get("records_sha256"),
            "MEMORY_DIGEST_DRIFT")
    require(a.get("scope") == b.get("scope") == ["Mind-Palace"],
            "PROJECT_SCOPE_DRIFT")
    a_pointer = [x for x in a["matches"] if x.get("id") == RECORD]
    b_pointer = [x for x in b["matches"] if x.get("id") == RECORD]
    full = [x for x in b["resolved_reference_records"] if x.get("id") == RECORD]
    require(len(a_pointer) == len(b_pointer) == len(full) == 1,
            "MATCH_IDENTITY_DRIFT")
    a_pointer, b_pointer, full = a_pointer[0], b_pointer[0], full[0]
    require(a_pointer == b_pointer and
            a_pointer.get("retrieval_preview_kind") == "reference_only" and
            a_pointer.get("full_record_required") is True,
            "REFERENCE_ONLY_BASELINE_MISSING")
    statement = full.get("statement")
    require(type(statement) is str and
            hashlib.sha256(statement.encode("utf-8")).hexdigest() ==
            a_pointer.get("source_statement_sha256"),
            "FULL_STATEMENT_HASH_DRIFT")
    require(full.get("source_refs") == a_pointer.get("source_refs")
            and full.get("project") == "Mind-Palace"
            and full.get("status") == "observed",
            "FULL_EVIDENCE_PROVENANCE_DRIFT")
    require("no independent factual accuracy grades" in statement
            and "no scientific improvement claim" in statement
            and "96-token output cap" in statement,
            "NEGATIVE_CAVEATS_MISSING")
    return a_pointer["statement"], statement


def download_verified(path: Path) -> None:
    require(not path.exists(), "MODEL_FILE_COLLISION")
    require(shutil.disk_usage(str(path.parent)).free > 900_000_000,
            "INSUFFICIENT_SCRATCH_SPACE")
    h = hashlib.sha256()
    size = 0
    start = time.monotonic()
    req = urllib.request.Request(
        MODEL_URL, headers={"User-Agent": "FORGE-MPAI-development-nonQwen/1"})
    with urllib.request.urlopen(req, timeout=45) as src, path.open("xb") as target:
        while True:
            block = src.read(4 * 1024 * 1024)
            if not block:
                break
            size += len(block)
            require(size <= MODEL_BYTES and time.monotonic()-start < 420,
                    "MODEL_DOWNLOAD_BOUND")
            h.update(block)
            target.write(block)
    require(size == MODEL_BYTES and h.hexdigest() == MODEL_SHA256,
            "MODEL_PIN_DRIFT")
    with path.open("rb") as f:
        require(f.read(4) == b"GGUF", "MODEL_FORMAT")


def decide(response: str) -> str:
    words = re.findall(r"\b(?:YES|NO|UNKNOWN)\b", response.upper())
    return words[0] if len(words) == 1 else "UNSCORABLE"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    args = ap.parse_args()
    root = args.scratch.resolve(strict=True)
    require(len(args.source) == 40 and
            re.fullmatch(r"[a-f0-9]{40}", args.source) is not None,
            "SOURCE_FORMAT")
    # Network is used only to download public, frozen GGUF weights; the
    # private input is first opened AFTER the network has been disabled.
    model_path = root / "pinned-public-smollm2.gguf"
    download_verified(model_path)
    os.environ["HF_HUB_OFFLINE"] = "1"
    def no_network(*_a, **_kw):
        raise RuntimeError("MPAI_DEV_NETWORK_FORBIDDEN")
    socket.socket = no_network

    baseline = load(args.baseline)
    candidate = load(args.candidate)
    pointer, full = verify_pair(baseline, candidate, args.source)
    from llama_cpp import Llama
    model = Llama(model_path=str(model_path), n_ctx=N_CTX, n_threads=4,
                  n_batch=128, n_gpu_layers=0, seed=137, verbose=False)
    rows = []
    start_all = time.monotonic()
    for idx, (case_id, question, expected) in enumerate(QUESTIONS):
        # Counterbalance order to avoid always warming one arm first.
        order = ("baseline", "candidate") if idx % 2 == 0 else ("candidate", "baseline")
        for arm in order:
            evidence = pointer if arm == "baseline" else full
            prompt = (
                "Use ONLY the evidence below; never guess. "
                "Answer exactly YES, NO, or UNKNOWN. If evidence is only a "
                "reference pointer, answer UNKNOWN. Do not invent facts.\n"
                "Evidence:\n" + evidence + "\nQuestion: " + question +
                "\nAnswer:"
            )
            started = time.monotonic()
            output = model.create_completion(
                prompt=prompt, temperature=0.0, top_p=1.0,
                max_tokens=MAX_OUTPUT_TOKENS
            )
            elapsed = int(1000 * (time.monotonic()-started))
            response = output["choices"][0]["text"]
            usage = output.get("usage", {})
            require(type(response) is str and
                    0 < int(usage.get("prompt_tokens", 0)) < N_CTX and
                    0 <= int(usage.get("completion_tokens", -1)) <= MAX_OUTPUT_TOKENS,
                    "MODEL_COMPLETION_INVALID")
            rows.append({
                "case_id": case_id,
                "arm": arm,
                "expected_from_full_source": expected,
                "decision": decide(response),
                "response_private": response[:2048],
                "prompt_tokens": usage["prompt_tokens"],
                "output_tokens": usage["completion_tokens"],
                "model_elapsed_ms": elapsed,
            })
    require(len(rows) == 2 * len(QUESTIONS), "MODEL_CALL_COUNT")
    stats = {}
    for arm in ("baseline", "candidate"):
        selected = [row for row in rows if row["arm"] == arm]
        stats[arm] = {
            "calls": len(selected),
            "exact_answer_agreement": sum(
                r["decision"] == r["expected_from_full_source"] for r in selected),
            "abstentions": sum(r["decision"] == "UNKNOWN" for r in selected),
            "unscorable": sum(r["decision"] == "UNSCORABLE" for r in selected),
            "prompt_tokens": sum(r["prompt_tokens"] for r in selected),
            "output_tokens": sum(r["output_tokens"] for r in selected),
            "inference_ms": sum(r["model_elapsed_ms"] for r in selected),
        }
    report = {
        "schema": "forge.mpai-reference-development-real-model.v1",
        "source_sha": args.source,
        "model_sha256": MODEL_SHA256,
        "model_identity": "SmolLM2-360M-Instruct-Q4_K_M",
        "development_only": True,
        "real_local_model_calls": len(rows),
        "matched_questions_same_model": True,
        "matched_information": False,
        "baseline_pointer_vs_candidate_complete_evidence": True,
        "independent_blind_grading": False,
        "authentic_external_agent": False,
        "heldout_first_use": False,
        "scientific_admission": False,
        "model_weight_or_production_memory_writes": 0,
        "elapsed_ms_total": int(1000*(time.monotonic()-start_all)),
        "stats": stats,
        "private_trials": rows,
    }
    (root / "private-model-decisions.json").write_text(
        json.dumps(report, sort_keys=True), encoding="utf-8")
    print("MPAI_DEV_VERIFIED_NON_QWEN_MODEL=PASS")
    print("MPAI_DEV_REAL_LOCAL_MODEL_CALLS=" + str(len(rows)))
    for arm in ("baseline", "candidate"):
        for key, value in stats[arm].items():
            print("MPAI_DEV_" + arm.upper() + "_" + key.upper() + "=" + str(value))
    print("MPAI_DEV_MATCHED_INFORMATION=FALSE")
    print("MPAI_DEV_BLIND_GRADE=FALSE")
    print("MPAI_DEV_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI_DEV_PRODUCTION_WRITES=0")
    del model
    gc.collect()


if __name__ == "__main__":
    main()

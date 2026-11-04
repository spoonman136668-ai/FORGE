"""MP-AI26: exact-source, DEVELOPMENT-ONLY per-trial receipt export.

No model invocation, network, production memory writes, or authentication.
An artifact proves GitHub published bytes, NOT independent provider/holdout custody.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from mpai26_new_family_transfer_development import (
    ARMS, MODEL_SHA, MODEL_REV, QUESTIONS, RECORDS_SHA, SOURCE_SHA, protocol_sha,
)

SCHEMA = "mind-palace.mpai26-development-trial-receipts.v1"
FIELDS = {"case", "family", "arm", "decision", "correct", "abstained",
          "unparseable", "prompt_tokens", "completion_tokens", "latency_ms",
          "context_chars", "context_sha256", "response_sha256"}
HEX40 = re.compile(r"[0-9a-f]{40}\\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\\Z")
ARMS_EXPECTED = tuple(ARMS)
CASES = {case_id: (index // 2, gold) for index, (case_id, _, _, gold) in enumerate(QUESTIONS)}


def require(ok, reason):
    if not ok:
        raise ValueError("MPAI26_RECEIPT_" + reason)


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def validate_private_trial(source):
    require(type(source) is dict and set(source) ==
            {"study", "protocol_sha", "source_sha", "model_sha", "trials"}, "INPUT_FIELDS")
    require(source["study"] == "development_only_nonindependent" and
            source["protocol_sha"] == protocol_sha() and
            source["source_sha"] == SOURCE_SHA and source["model_sha"] == MODEL_SHA,
            "FROZEN_SOURCE_DRIFT")
    rows = source["trials"]
    require(type(rows) is list and len(rows) == 24, "TRIAL_COUNT")
    seen = set()
    validated = []
    for row in rows:
        require(type(row) is dict and set(row) == FIELDS, "TRIAL_FIELDS")
        case, arm = row["case"], row["arm"]
        require(type(case) is str and case in CASES and type(arm) is str and
                arm in ARMS_EXPECTED and (case, arm) not in seen, "DUPLICATE_OR_UNKNOWN")
        seen.add((case, arm))
        family, gold = CASES[case]
        answer = row["decision"]
        require(type(row["family"]) is int and row["family"] == family and
                (answer is None or (type(answer) is str and
                 answer in ("YES", "NO", "UNKNOWN"))), "FAMILY_OR_DECISION")
        require(type(row["correct"]) is bool and row["correct"] == (answer == gold) and
                type(row["abstained"]) is bool and row["abstained"] == (answer == "UNKNOWN") and
                type(row["unparseable"]) is bool and row["unparseable"] == (answer is None),
                "OUTCOME_INCONSISTENT")
        require(all(type(row[k]) is int and row[k] >= 0 for k in
                    ("prompt_tokens", "completion_tokens", "latency_ms", "context_chars")),
                "RESOURCE_INVALID")
        require(0 < row["prompt_tokens"] <= 3000 and
                0 < row["completion_tokens"] <= 12 and
                row["latency_ms"] >= 1, "RESOURCE_LIMIT")
        require(all(type(row[k]) is str and HEX64.fullmatch(row[k]) for k in
                    ("context_sha256", "response_sha256")), "DIGEST_INVALID")
        if arm == "none":
            require(row["context_chars"] == 0 and row["context_sha256"] ==
                    hashlib.sha256(b"").hexdigest(), "NO_MEMORY_LEAK")
        validated.append(dict(row))
    require(seen == {(case, arm) for case in CASES for arm in ARMS_EXPECTED},
            "MISSING_TRIAL")
    return sorted(validated, key=lambda r: (r["case"], r["arm"]))


def export_receipt(source, *, run_id, run_attempt, job, forge_sha):
    require(type(run_id) is int and run_id > 0 and type(run_attempt) is int and
            run_attempt > 0 and type(job) is str and job == "original-windows" and
            type(forge_sha) is str and HEX40.fullmatch(forge_sha), "WORKFLOW_IDENTITY")
    rows = validate_private_trial(source)
    summaries = {}
    for arm in ARMS_EXPECTED:
        subset = [r for r in rows if r["arm"] == arm]
        summaries[arm] = {
            "calls": len(subset),
            "correct": sum(r["correct"] for r in subset),
            "abstentions": sum(r["abstained"] for r in subset),
            "unparseable": sum(r["unparseable"] for r in subset),
            "tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in subset),
            "wall_ms": sum(r["latency_ms"] for r in subset),
        }
    return {
        "schema": SCHEMA,
        "evidence_class": "EXPOSED_DEVELOPMENT_NOT_INDEPENDENTLY_AUTHENTICATED",
        "github_context_unverified": {
            "repository": "spoonman136668-ai/FORGE", "run_id": run_id,
            "run_attempt": run_attempt, "job": job, "forge_source_sha": forge_sha,
        },
        "frozen": {
            "protocol_sha256": protocol_sha(), "memory_commit": SOURCE_SHA,
            "records_sha256": RECORDS_SHA, "model_sha256": MODEL_SHA,
            "model_revision": MODEL_REV,
            "cohort": "exposed_development_only", "holdout_first_use": False,
        },
        "trial_count": len(rows), "trials": rows, "aggregate": summaries,
        "claims": {
            "actual_execution_authenticated_by_this_receipt": False,
            "independent_provider_custody": False,
            "independent_holdout_custody": False,
            "real_chatgpt_consumer_tested": False,
            "recursive_improvement_proven": False,
            "production_memory_writes": 0,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-trials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--forge-sha", required=True)
    args = parser.parse_args()
    input_path, output = args.private_trials.resolve(), args.output.resolve()
    require(input_path.is_file() and not input_path.is_symlink() and
            input_path.stat().st_size <= 65536, "INPUT_FILE")
    require(output != input_path and not output.exists() and
            output.parent.is_dir() and not output.parent.is_symlink(), "OUTPUT_BOUNDARY")
    original = json.loads(input_path.read_text(encoding="utf-8"))
    receipt = export_receipt(original, run_id=args.run_id,
                            run_attempt=args.run_attempt, job=args.job,
                            forge_sha=args.forge_sha)
    output.write_bytes(canonical(receipt) + b"\\n")
    print("MPAI26_TASK_RECEIPTS_EXPORTED=PASS count=24 custody=NOT_AUTHENTICATED")
    print("MPAI26_TASK_RECEIPT_SHA256=" +
          hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()

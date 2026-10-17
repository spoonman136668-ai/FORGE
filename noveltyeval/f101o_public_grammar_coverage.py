"""F101-O: immutable public MetaQA question-only, full-population parser coverage.

Reads no answer strings into Go and never asks the graph for target entities.
Public descriptive compatibility only. No scientific first-use or accuracy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

UPSTREAM_HEAD = "826ee617e4da5b087584b0e03c70fe76642c6188"
COHORTS = (
    (2, "metaqa/original/2-hop/qa_test.txt", "c60e27a75140cfc2792469181caca05b79b017ad", 14872),
    (3, "metaqa/original/3-hop/qa_test.txt", "09756f302c4100897c64144e7af8c73763cee4a2", 14274),
)
SCHEMA = "forge.optimizer.f101o.public-answer-blind-complete-question-coverage.v1"


class Denied(ValueError):
    pass


def require(predicate: bool, reason: str) -> None:
    if not predicate:
        raise Denied("F101O_FAIL_CLOSED_" + reason)


def immutable_git_bytes(root: pathlib.Path, relative: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), "show", "HEAD:" + relative],
                            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=30)
    require(result.returncode == 0, "PINNED_GIT_OBJECT_MISSING")
    return result.stdout


def git_blob_hash(raw: bytes) -> str:
    payload = b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    return hashlib.sha1(payload).hexdigest()


def question_only_bytes(raw: bytes, *, expected: int) -> bytes:
    # Invariant: no decoded, interpreted, transmitted or published answer bytes.
    rows = raw.splitlines()
    require(len(rows) == expected, "COMPLETE_COHORT_DENOMINATOR_DRIFT")
    questions: list[bytes] = []
    for row in rows:
        require(row.count(b"\t") == 1, "UNEXPECTED_QA_ROW_FIELDS")
        q, _, answer = row.partition(b"\t")
        require(len(q) > 0 and len(answer) > 0, "EMPTY_QUESTION_OR_ANSWER_FIELD")
        require(b"\n" not in q and b"\r" not in q, "QUESTION_NEWLINE")
        # Explicitly discard answer here. All downstream code receives only q.
        questions.append(q)
    return b"\n".join(questions) + b"\n"


def count_questions(question_only: bytes, hops: int, expected: int) -> dict:
    proc = subprocess.run(["go", "run", "./cmd/forge-f101o-grammar-count",
                           "--hops", str(hops)], input=question_only,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=False, timeout=160)
    require(proc.returncode == 0, "FROZEN_GRAMMAR_CLI_FAILURE")
    try:
        data = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Denied("F101O_INVALID_AGGREGATE_OUTPUT") from exc
    require(data["schema"] == "forge.optimizer.f101o.public-fixed-grammar-count.v1"
            and data["hops"] == hops and data["questions"] == expected,
            "PARSER_DENOMINATOR_DRIFT")
    require(data["matched"] + data["abstained"] == expected and
            sum(data["reasons"].values()) == data["abstained"],
            "PARSE_ACCOUNTING_MISMATCH")
    require(data["question_only_data_flow"] is True and data["answers_read"] == 0
            and data["model_calls"] == 0 and data["scientific_dispatch"] is False
            and data["accepted_ref_mutation"] is False,
            "FALSE_PARSER_AUTHORITY")
    return data


def audit(root: pathlib.Path) -> dict:
    git_head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=20)
    require(git_head.returncode == 0
            and git_head.stdout.decode("ascii").strip() == UPSTREAM_HEAD,
            "UPSTREAM_COMMIT_DRIFT")
    cohorts = []
    for hops, path, expected_blob, denominator in COHORTS:
        raw = immutable_git_bytes(root, path)
        require(len(raw) > 0 and len(raw) <= 7_000_000, "UNBOUNDED_QA_SOURCE")
        require(git_blob_hash(raw) == expected_blob, "UPSTREAM_SOURCE_GIT_BLOB_DRIFT")
        questions = question_only_bytes(raw, expected=denominator)
        result = count_questions(questions, hops, denominator)
        cohorts.append({
            "hops": hops,
            "original_rows": denominator,
            "git_blob": expected_blob,
            "original_bytes_sha256": hashlib.sha256(raw).hexdigest(),
            "aggregate": result,
        })
    require(sum(c["original_rows"] for c in cohorts) == 29146,
            "ALL_COHORTS_NOT_ACCOUNTED")
    return {
        "schema": SCHEMA,
        "status": "PUBLIC_FIXED_GRAMMAR_COVERAGE_ONLY",
        "source_repository": "tiantiangao7/kalm-qa",
        "source_commit": UPSTREAM_HEAD,
        "frozen_grammar_count": 8,
        "entire_public_qa_population": 29146,
        "cohorts": cohorts,
        "answer_values_supplied_to_parser": False,
        "answer_field_compared": False,
        "per_question_data_published": False,
        "actual_qa_accuracy_computed": False,
        "independent_blinded_scientific_firstuse": False,
        "scientific_acceptance": False,
        "dream_pareto_promotion": False,
        "thetaevolve_accepted_training": False,
        "science_dispatch_authorized": False,
        "accepted_ref_mutation": False,
        "codex_calls": 0,
        "paid_model_calls": 0,
        "cloudflare_writes": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    require(not args.output.exists(), "OUTPUT_OVERWRITE")
    result = audit(args.upstream)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("F101O_PUBLIC_QUESTIONS_ACCOUNTED=29146")
    print("F101O_AUTHENTIC_FIRST_USE_AND_QA_ACCURACY=ZERO")


if __name__ == "__main__":
    try:
        main()
    except (Denied, OSError, UnicodeError, subprocess.SubprocessError, KeyError) as exc:
        print("F101O_QUESTION_ONLY_COVERAGE_BLOCKED:", exc, file=sys.stderr)
        sys.exit(1)

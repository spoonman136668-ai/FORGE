"""F98-O: exact-public-Git-source audit for an existing external KGQA benchmark.

This is not a sealed holdout, an independently witnessed experiment, a learned
reasoning success, or an adaptation signal. No inference or candidate evaluation
is performed. Source is publicly observable MetaQA data mirrored by KALM-QA.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

SCHEMA = "forge.optimizer.f98o.external-preexisting-public-corpus-source-audit.v1"
UPSTREAM_REPO = "tiantiangao7/kalm-qa"
UPSTREAM_HEAD = "826ee617e4da5b087584b0e03c70fe76642c6188"
F95_BASE = "b61fa60084fc487b4d010b3662a2b85872488deb"
FILES = (
    ("kg", "metaqa/original/kb.txt",
     "a43fa7ca5e6894236556f2984764070c4ca5562b", 1),
    ("qa2", "metaqa/original/2-hop/qa_test.txt",
     "c60e27a75140cfc2792469181caca05b79b017ad", 14872),
    ("qa3", "metaqa/original/3-hop/qa_test.txt",
     "09756f302c4100897c64144e7af8c73763cee4a2", 14274),
)
SAFE = re.compile(r"^[a-z0-9_-]{1,48}$")


class Blocked(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Blocked("FORGE_F98O_UNQUALIFIED_PUBLIC_SOURCE_" + reason)


def git(root: pathlib.Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=False, timeout=20,
        env={"PATH": __import__("os").environ.get("PATH", ""),
             "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_OPTIONAL_LOCKS": "0"},
    )
    require(cp.returncode == 0, "GIT_OBJECT_UNAVAILABLE")
    return cp.stdout.strip()


def file_hash(path: pathlib.Path) -> tuple[bytes, str]:
    require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK")
    require(0 < path.stat().st_size <= 7_000_000, "FILE_UNBOUNDED")
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def lines(raw: bytes, label: str) -> list[str]:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeError as exc:
        raise Blocked("FORGE_F98O_UNQUALIFIED_PUBLIC_SOURCE_INVALID_UTF8") from exc
    parts = decoded.splitlines()
    require(parts and all(x and "\x00" not in x for x in parts),
            label + "_BLANK_OR_BINARY")
    return parts


def kb_counts(data: bytes) -> dict:
    items = lines(data, "KB")
    bad = 0
    safe = 0
    relations = set()
    for line in items:
        parts = line.split("|")
        require(len(parts) == 3 and all(parts), "INVALID_KB_TRIPLE")
        subject, relation, target = parts
        relations.add(relation)
        if all(SAFE.fullmatch(x) is not None for x in parts):
            safe += 1
        else:
            bad += 1
    return {"triples": len(items), "distinct_relation_labels": len(relations),
            "f95_identifier_compatible_triples": safe,
            "f95_identifier_incompatible_triples": bad,
            "entire_kb_fits_f95_128_edge_cap": len(items) <= 128,
            "all_entities_can_be_loaded_without_relabeling": bad == 0}


def qa_counts(data: bytes, minimum: int, label: str) -> dict:
    items = lines(data, label)
    require(len(items) == minimum, label + "_EXPECTED_DENOMINATOR_DRIFT")
    multiple = 0
    bracketed = 0
    for row in items:
        parts = row.split("\t")
        require(len(parts) == 2 and all(parts), label + "_MALFORMED_QA")
        question, answers = parts
        require(question.count("[") == 1 and question.count("]") == 1,
                label + "_TOPIC_ENTITY_UNMARKED")
        require(all(x for x in answers.split("|")), label + "_EMPTY_ANSWER")
        if "|" in answers:
            multiple += 1
        bracketed += 1
    return {"all_rows_preserved": True, "questions": len(items),
            "bracketed_topic_questions": bracketed,
            "multi_answer_questions": multiple,
            "explicit_role_sequences_supplied_for_f95": False}


def inspect(root: pathlib.Path, *,
            actual_git_head: str | None = None,
            raw_files: dict[str, bytes] | None = None,
            git_blobs: dict[str, str] | None = None) -> dict:
    # injected file/blob values are test-only: authenticated CI uses actual git.
    if actual_git_head is None:
        actual_git_head = git(root, "rev-parse", "HEAD")
    require(actual_git_head == UPSTREAM_HEAD, "SOURCE_COMMIT_DRIFT")
    if raw_files is None or git_blobs is None:
        require(raw_files is None and git_blobs is None,
                "UNPAIRED_TEST_FILE_PROVENANCE")
        files = {}
        blobs = {}
        for label, path, _, _ in FILES:
            source = root.joinpath(*path.split("/"))
            require(source.resolve().is_relative_to(root.resolve()),
                    "PATH_ESCAPES_SOURCE_TREE")
            files[label] = file_hash(source)[0]
            blobs[label] = git(root, "rev-parse", "HEAD:" + path)
    else:
        files, blobs = raw_files, git_blobs
    source_items = []
    for label, path, expected_blob, minimum in FILES:
        require(label in files and label in blobs and
                blobs[label] == expected_blob, label + "_GIT_BLOB_DRIFT")
        raw = files[label]
        require(isinstance(raw, bytes) and 0 < len(raw) <= 7_000_000,
                label + "_DATA_UNAVAILABLE")
        d = hashlib.sha256(raw).hexdigest()
        counts = kb_counts(raw) if label == "kg" else qa_counts(raw, minimum, label)
        source_items.append({
            "kind": label, "path": path, "source_git_blob_sha1": blobs[label],
            "source_bytes_sha256": d, "source_byte_count": len(raw),
            "population": counts,
        })
    kb = source_items[0]["population"]
    return {
        "schema": SCHEMA,
        "source_repository": UPSTREAM_REPO, "source_commit": UPSTREAM_HEAD,
        "source_is_separate_preexisting_public_repository": True,
        "source_origin_predates_f95_code": True,
        "full_public_source_file_count": 3,
        "source_files": source_items,
        "two_hop_denominator": source_items[1]["population"]["questions"],
        "three_hop_denominator": source_items[2]["population"]["questions"],
        "source_triple_denominator": kb["triples"],
        "f95_current_128_relation_limit_blocks_full_kb": not kb["entire_kb_fits_f95_128_edge_cap"],
        "f95_identifier_schema_requires_adapter": not kb["all_entities_can_be_loaded_without_relabeling"],
        "question_to_roles_frozen_adapter_exists": False,
        "all_external_test_items_runnable_without_label_based_selection": False,
        "f95_test_accuracy_computed": False,
        "independent_blinded_holdout_verified": False,
        "independent_pre_outcome_witness_verified": False,
        "authentic_scientific_original_firstuse": False,
        "causal_scientific_superiority_established": False,
        "dream_pareto_promotion_authorized": False,
        "thetaevolve_accepted_training_allowed": False,
        "science_dispatch_authorized": False,
        "accepted_ref_mutation": False,
        "model_calls": 0,
        "codex_calls": 0,
        "cloudflare_writes": 0,
        "status": "GENUINE_HISTORICAL_PUBLIC_SOURCE_AUTHENTICATED_NOT_AN_UNSEEN_ORIGINAL_OR_MODEL_RESULT",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "REFUSE_OVERWRITE")
    output = inspect(args.upstream)
    args.output.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("F98O_PUBLIC_DATA_SOURCE_AUTHENTIC=TRUE")
    print("F98O_EXPERIMENTAL_ORIGINALS_OR_THETA_UPDATES=ZERO")


if __name__ == "__main__":
    try:
        main()
    except (Blocked, OSError, subprocess.SubprocessError) as exc:
        print("F98O_READ_ONLY_SOURCE_QUALIFICATION_BLOCKED:", exc, file=sys.stderr)
        sys.exit(1)

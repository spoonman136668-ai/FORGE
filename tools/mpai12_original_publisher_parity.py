"""MP-AI12 source-custody audit: original AI2 ARC vs third-party mirror.

This is public publisher-source parity and grade-key verification of previously
CONSUMED MP-AI11 development cases. It is NOT independent reviewer custody,
not sealed first-use, not a new model trial and not scientific qualification.
No private Mind-Palace data or production system is opened or modified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.request
import zipfile

from mpai11_external_family_transfer import (
    MIRROR_GIT_BLOB_SHA1, MIRROR_URL, MIRROR_COMMIT, MIRROR_PATH,
    validate_public_blob, freeze_public_cohort, CASES,
)

PUBLISHER_URL = "https://s3-us-west-2.amazonaws.com/ai2-website/data/ARC-V1-Feb2018.zip"
PUBLISHER_ARCHIVE_BYTES = 680841265
PUBLISHER_ARCHIVE_SHA256 = (
    "6d2d5ab50b2ceec6ba5f79c921be77cf2de712ea25a2b3f4fff3acc101cecfa0"
)
PUBLISHER_SPLIT = "ARC-V1-Feb2018-2/ARC-Challenge/ARC-Challenge-Dev.jsonl"
EXPECTED_ROWS = 299
MAX_SOURCE_BYTES = 2_000_000
MAX_MIRROR_BYTES = 600_000
MAX_SECONDS = 600


def fail(code: str) -> None:
    raise RuntimeError("MPAI12_" + code)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def download_pinned_archive(destination: Path) -> None:
    if destination.exists():
        fail("ARCHIVE_COLLISION")
    if shutil.disk_usage(str(destination.parent)).free < 1_400_000_000:
        fail("DISK_BUDGET")
    h = hashlib.sha256()
    count = 0
    start = time.monotonic()
    req = urllib.request.Request(
        PUBLISHER_URL, headers={"User-Agent": "MPAI12-OriginalPublisherSourceAudit/1"})
    with urllib.request.urlopen(req, timeout=60) as src, destination.open("xb") as out:
        while True:
            chunk = src.read(4 * 1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > PUBLISHER_ARCHIVE_BYTES or time.monotonic()-start > MAX_SECONDS:
                fail("PUBLISHER_DOWNLOAD_BUDGET")
            h.update(chunk)
            out.write(chunk)
    if count != PUBLISHER_ARCHIVE_BYTES or h.hexdigest() != PUBLISHER_ARCHIVE_SHA256:
        fail("OFFICIAL_ARCHIVE_SHA_OR_LENGTH_MISMATCH")


def publisher_rows(archive: Path) -> tuple[list[dict], str]:
    with zipfile.ZipFile(archive) as zf:
        if zf.namelist().count(PUBLISHER_SPLIT) != 1:
            fail("PUBLISHER_SPLIT_IDENTITY_MISSING")
        entry = zf.getinfo(PUBLISHER_SPLIT)
        if not (100 < entry.file_size <= MAX_SOURCE_BYTES):
            fail("PUBLISHER_DECOMPRESS_SIZE")
        with zf.open(PUBLISHER_SPLIT) as data:
            raw = data.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        fail("PUBLISHER_RAW_TOO_LARGE")
    try:
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("MPAI12_PUBLISHER_SCHEMA_INVALID") from exc
    if len(rows) != EXPECTED_ROWS:
        fail("PUBLISHER_SPLIT_ROW_COUNT")
    return rows, digest(raw)


def mirror_rows() -> tuple[list[dict], str]:
    req = urllib.request.Request(
        MIRROR_URL, headers={"User-Agent": "MPAI12-MirrorOriginalParity/1"})
    with urllib.request.urlopen(req, timeout=45) as src:
        raw = src.read(MAX_MIRROR_BYTES + 1)
    if len(raw) > MAX_MIRROR_BYTES:
        fail("MIRROR_SIZE_LIMIT")
    # Git blob identity, raw SHA256 and 299-row contract from the earlier trial.
    return validate_public_blob(raw)


def canonical_core(row: dict) -> tuple:
    """Ignore only untrusted retrieval-enrichment fields (e.g. choice.para)."""
    if type(row) is not dict:
        fail("ROW_NOT_OBJECT")
    key, question, answer = row.get("id"), row.get("question"), row.get("answerKey")
    if (type(key) is not str or not key or type(question) is not dict
            or type(answer) is not str):
        fail("ROW_ID_QUESTION_GOLD_INVALID")
    stem, options = question.get("stem"), question.get("choices")
    if (type(stem) is not str or not stem or type(options) is not list
            or not (2 <= len(options) <= 6)):
        fail("ROW_STEM_OR_OPTIONS_INVALID")
    choices = []
    for item in options:
        if (type(item) is not dict or type(item.get("label")) is not str
                or type(item.get("text")) is not str
                or not item["label"] or not item["text"]):
            fail("ROW_OPTION_INVALID")
        choices.append((item["label"], item["text"]))
    if (len(set(k for k, _ in choices)) != len(choices)
            or answer not in {k for k, _ in choices}):
        fail("GOLD_NOT_IN_OPTIONS")
    return key, stem, tuple(sorted(choices)), answer


def to_index(rows: list[dict]) -> dict[str, tuple]:
    if len(rows) != EXPECTED_ROWS:
        fail("ROW_COUNT_INVALID")
    result = {}
    for row in rows:
        value = canonical_core(row)
        if value[0] in result:
            fail("DUPLICATE_ID")
        result[value[0]] = value
    return result


def audit(publisher: list[dict], mirror: list[dict]) -> dict:
    p, m = to_index(publisher), to_index(mirror)
    if p.keys() != m.keys():
        fail("QUESTION_ID_POPULATION_DRIFT")
    mismatches = [id for id in p if p[id] != m[id]]
    if mismatches:
        # Do not disclose the question IDs in a public workflow.
        fail("ORIGINAL_PUBLISHER_MIRROR_CONTENT_OR_GOLD_MISMATCH")
    chosen_m, gold_m, selected_hash_m = freeze_public_cohort(mirror)
    chosen_p, gold_p, selected_hash_p = freeze_public_cohort(publisher)
    if (chosen_m != chosen_p or gold_m != gold_p
            or selected_hash_m != selected_hash_p
            or len(chosen_p) != CASES):
        fail("CONSUMED_COHORT_OR_GOLD_DRIFT")
    return {
        "full_split_source_parity": True,
        "exact_question_answer_parity": True,
        "all_split_questions": len(p),
        "already_consumed_cohort": len(chosen_p),
        "selected_question_only_sha256": selected_hash_p,
        "selected_gold_key_agreement": len(gold_p),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    args = ap.parse_args()
    scratch = args.scratch.resolve(strict=True)
    archive = scratch / "publisher-pinned-arc.zip"
    download_pinned_archive(archive)
    publisher, pub_split_sha = publisher_rows(archive)
    mirror, mirror_sha = mirror_rows()
    results = audit(publisher, mirror)
    receipt = {
        "schema": "forge.mpai12.publisher-parity-readonly.v1",
        "original_publisher_archive_url": PUBLISHER_URL,
        "original_publisher_archive_sha256": PUBLISHER_ARCHIVE_SHA256,
        "original_publisher_archive_bytes": PUBLISHER_ARCHIVE_BYTES,
        "publisher_challenge_dev_sha256": pub_split_sha,
        "mirror_source_pin": MIRROR_COMMIT,
        "mirror_git_blob": MIRROR_GIT_BLOB_SHA1,
        "mirror_challenge_dev_sha256": mirror_sha,
        "publisher_parity": results,
        "public_previously_consumed_cohort": True,
        "third_party_sealed_holdout": False,
        "separate_independent_reviewer_authenticated": False,
        "new_model_calls": 0,
        "scientific_first_use": False,
        "scientific_qualification": False,
        "production_writes": 0,
    }
    (scratch / "mpai12-private-source-audit.json").write_text(
        json.dumps(receipt, sort_keys=True), encoding="utf-8")
    print("MPAI12_PUBLISHER_ZIP_SHA256=PASS")
    print("MPAI12_PUBLISHER_DEV_SHA256=" + pub_split_sha)
    print("MPAI12_MIRROR_DEV_SHA256=" + mirror_sha)
    print("MPAI12_ALL_SPLIT_RECORDS_MATCH=" + str(results["all_split_questions"]))
    print("MPAI12_CONSUMED_COHORT_GOLD_MATCH=" + str(results["selected_gold_key_agreement"]))
    print("MPAI12_SELECTED_COHORT_SHA256=" + results["selected_question_only_sha256"])
    print("MPAI12_AUTHENTIC_PRIMARY_SECONDARY_PARITY=PASS")
    print("MPAI12_INDEPENDENT_REVIEWER_AUTHENTICATED=FALSE")
    print("MPAI12_FIRST_USE=FALSE")
    print("MPAI12_SCIENTIFIC_QUALIFICATION=FALSE")
    print("MPAI12_PRODUCTION_WRITES=0")


if __name__ == "__main__":
    main()

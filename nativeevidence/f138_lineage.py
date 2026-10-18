"""F138: source-bound development ancestry evidence, not scientific authorization.

This report reflects the GitHub event and inputs observed by each independent
OS worker. It is content-addressed but not a cryptographic signature. External
provider run/artifact identities must be authenticated by a separate verifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

REPO = "spoonman136668-ai/FORGE"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
POSITIVE = re.compile(r"^[1-9][0-9]*$")
RECOVERIES = {
    "f136-completion",
    "f137-scheduled-recovery",
    "f137-windows-recovery",
}
EVENTS = {"schedule", "push", "pull_request", "workflow_dispatch"}


class LineageError(ValueError):
    pass


def check(condition: bool, code: str) -> None:
    if not condition:
        raise LineageError("F138_" + code)


def build(*, repository: str, ref: str, source_sha: str, run_id: str,
          run_attempt: str, event: str, origin: str,
          parent_run_id: str = "", parent_source_sha: str = "") -> dict:
    """Strictly validate fields, retaining explicit distinction from genuine cron."""
    check(repository == REPO, "FOREIGN_REPOSITORY")
    check(type(source_sha) is str and HEX40.fullmatch(source_sha) is not None,
          "SOURCE_INVALID")
    check(type(run_id) is str and POSITIVE.fullmatch(run_id) is not None,
          "RUN_ID_INVALID")
    check(type(run_attempt) is str and POSITIVE.fullmatch(run_attempt) is not None,
          "ATTEMPT_INVALID")
    check(event in EVENTS, "EVENT_INVALID")

    # PR checks use a synthetic merge ref; they cannot claim main continuity.
    check(ref == "refs/heads/main" if event != "pull_request"
          else ref.startswith("refs/pull/") and ref.endswith("/merge"),
          "EVENT_REF_MISMATCH")
    if event == "workflow_dispatch":
        check(origin in RECOVERIES | {"manual"}, "DISPATCH_ORIGIN_INVALID")
        if origin in RECOVERIES:
            check(type(parent_run_id) is str and
                  POSITIVE.fullmatch(parent_run_id) is not None,
                  "PARENT_ID_REQUIRED")
            check(parent_source_sha == source_sha, "PARENT_SOURCE_DRIFT")
        else:
            check(parent_run_id == "" and parent_source_sha == "",
                  "MANUAL_CANNOT_IMPERSONATE_PARENT")
    else:
        check(origin == event, "UNSCHEDULED_ORIGIN_SPOOF")
        check(parent_run_id == "" and parent_source_sha == "",
              "NONDISPATCH_PARENT_SPOOF")

    check(int(run_id) < 2**63 and int(run_attempt) < 2**31,
          "INTEGER_OVERFLOW")
    if parent_run_id:
        check(int(parent_run_id) < int(run_id), "PARENT_NOT_PRIOR")
    return {
        "schema": "forge.autonomy.f138.development-lineage.v1",
        "repository": REPO,
        "ref": ref,
        "source_sha": source_sha,
        "run_id": int(run_id),
        "run_attempt": int(run_attempt),
        "event": event,
        "origin": origin,
        "parent_run_id": int(parent_run_id) if parent_run_id else None,
        "parent_source_sha": parent_source_sha or None,
        "genuine_integrated_schedule": event == "schedule",
        "development_only": True,
        "scientific_first_use_authorized": False,
        "scientific_originals_dispatched": 0,
        "accepted_ref_mutations": 0,
        "optimizer_promotions": 0,
        "codex_calls": 0,
        "paid_model_calls": 0,
    }


def encode(document: dict) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")


def write_once(folder: Path, document: dict) -> str:
    """Write append-only SHA256 witness on each runner, never overwrite."""
    check(folder.is_dir(), "OUTPUT_DIRECTORY_MISSING")
    data = encode(document)
    digest = hashlib.sha256(data).hexdigest()
    target = folder / "f138-lineage.json"
    receipt = folder / "f138-lineage.sha256"
    check(not target.exists() and not receipt.exists(), "OUTPUT_EXISTS")
    with target.open("xb") as stream:
        stream.write(data)
    with receipt.open("xb") as stream:
        stream.write((digest + "  f138-lineage.json\n").encode("ascii"))
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    for arg in ("repository", "ref", "source-sha", "run-id", "run-attempt",
                "event", "origin", "parent-run-id", "parent-source-sha"):
        parser.add_argument("--" + arg, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(repository=args.repository, ref=args.ref,
                   source_sha=args.source_sha, run_id=args.run_id,
                   run_attempt=args.run_attempt, event=args.event,
                   origin=args.origin, parent_run_id=args.parent_run_id,
                   parent_source_sha=args.parent_source_sha)
    digest = write_once(args.output_dir, report)
    print("F138_SOURCE_LINEAGE_RECEIPT=PASS " + digest)
    print("F138_SCIENTIFIC_AUTHORITY=FALSE")


if __name__ == "__main__":
    try:
        main()
    except (LineageError, OSError) as exc:
        parser_error = str(exc)
        raise SystemExit("F138_FAIL_CLOSED " + parser_error) from exc

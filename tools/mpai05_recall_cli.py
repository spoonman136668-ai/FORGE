"""One-shot, private, read-only Mind-Palace query consumer.

This is not a controller, scheduler or memory writer. Invoke against a pinned
local Mind-Palace checkout. The source's own MemorySnapshot validates its
committed manifest and project scope. No query/record is logged publicly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from mpai05_retrieval_consumer import recall_with_normalizer

PIN = re.compile(r"[a-f0-9]{40}\Z")
MODES = ("off", "shadow", "eligible")
MAX_QUERY_BYTES = 4096
MAX_PRIVATE_RESULT_BYTES = 65536
MAX_REFERENCE_FOLLOWUPS = 5


def _top_digest(result: dict) -> str:
    ids = [m["id"] for m in result.get("matches", [])[:4]]
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()


def retrieve(snapshot, sha: str, query: str, *, mode: str = "off",
             projects: list[str] | None = None, profile: str = "continuation",
             resolve_reference_only: bool = False) -> tuple[dict, dict]:
    """Return private results and a non-content operational receipt.

    Shadow mode serves ORIGINAL results; candidate is sampled for telemetry only.
    Eligible mode serves normalized results for recognized templates only.
    """
    if not isinstance(sha, str) or PIN.fullmatch(sha) is None:
        raise ValueError("invalid source pin")
    if mode not in MODES:
        raise ValueError("unsupported mode")
    if not isinstance(query, str) or not query.strip() or len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        raise ValueError("query exceeds read contract")
    if projects != ["Mind-Palace"]:
        raise ValueError("scope must be Mind-Palace only")
    if profile not in ("status", "continuation", "architecture", "historical"):
        raise ValueError("invalid profile")
    began = time.perf_counter()
    if mode == "shadow":
        primary = recall_with_normalizer(snapshot, sha, query, projects, profile, enabled=False)
        observed = recall_with_normalizer(snapshot, sha, query, projects, profile, enabled=True)
        candidate = observed["result"]
        served = primary
    else:
        served = recall_with_normalizer(snapshot, sha, query, projects, profile,
                                        enabled=(mode == "eligible"))
        candidate = None
    result = served["result"]
    if result.get("source_sha") != sha or not isinstance(result.get("matches"), list):
        raise RuntimeError("retrieval identity invalid")
    if not all(m.get("source_refs") for m in result["matches"]):
        raise RuntimeError("source provenance missing")
    if candidate is not None and (candidate.get("source_sha") != sha
                                  or not isinstance(candidate.get("matches"), list)
                                  or not all(m.get("source_refs") for m in candidate["matches"])):
        raise RuntimeError("shadow source provenance missing")
    resolved_count = 0
    if resolve_reference_only:
        result, resolved_count = resolve_reference_records(
            snapshot, sha, projects, result)
    receipt = {
        "schema": "forge.mpai05.readonly-consumer-receipt.v1",
        "source_sha": sha,
        "mode": mode,
        "routing": served["routing"],
        "record_count": len(result["matches"]),
        "elapsed_ms": round((time.perf_counter() - began) * 1000, 3),
        "private_result_sha256": hashlib.sha256(
            json.dumps(result, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "shadow_record_count": len(candidate["matches"]) if candidate is not None else None,
        "shadow_changed_top4": _top_digest(result) != _top_digest(candidate)
        if candidate is not None else None,
        "read_only": True,
        "reference_followup": "enabled" if resolve_reference_only else "disabled",
        "resolved_reference_count": resolved_count,
    }
    return result, receipt



def resolve_reference_records(snapshot, source_sha: str, projects: list[str],
                              result: dict) -> tuple[dict, int]:
    """Opt-in, fail-closed source-only resolution; no model call or writer.

    The record stays inside the private result, not the ordinary bounded
    model-visible recall matches. A caller must use verified full evidence
    rather than the abbreviated reference pointer as an answer.
    """
    if type(result) is not dict or result.get("source_sha") != source_sha:
        raise RuntimeError("reference source identity invalid")
    if result.get("scope") != projects or projects != ["Mind-Palace"]:
        raise RuntimeError("reference scope invalid")
    matches = result.get("matches")
    if type(matches) is not list:
        raise RuntimeError("reference matches invalid")
    resolved = []
    ids = set()
    for pointer in matches:
        if type(pointer) is not dict:
            raise RuntimeError("reference item invalid")
        needs_full = pointer.get("full_record_required", False)
        if needs_full is not True:
            if pointer.get("retrieval_preview_kind") == "reference_only":
                raise RuntimeError("reference preview missing required flag")
            continue
        if pointer.get("retrieval_preview_kind") != "reference_only":
            raise RuntimeError("reference followup flag inconsistent")
        record_id = pointer.get("id")
        digest = pointer.get("source_statement_sha256")
        if (type(record_id) is not str or not record_id or len(record_id) > 256
                or type(digest) is not str or
                re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or record_id in ids):
            raise RuntimeError("reference identity invalid")
        ids.add(record_id)
        if len(ids) > MAX_REFERENCE_FOLLOWUPS:
            raise RuntimeError("reference count exceeds limit")
        opened = snapshot.get_record(source_sha, record_id, projects)
        if (type(opened) is not dict or opened.get("found") is not True
                or opened.get("source_sha") != source_sha
                or type(opened.get("record")) is not dict):
            raise RuntimeError("referenced full record unavailable")
        if ("records_sha256" in result and
                opened.get("records_sha256") != result["records_sha256"]):
            raise RuntimeError("reference snapshot digest drift")
        full = opened["record"]
        statement = full.get("statement")
        if (full.get("id") != record_id
                or full.get("project") != projects[0]
                or full.get("source_refs") != pointer.get("source_refs")
                or full.get("kind") != pointer.get("kind")
                or full.get("status") != pointer.get("status")
                or type(statement) is not str or not statement
                or hashlib.sha256(statement.encode("utf-8")).hexdigest() != digest):
            raise RuntimeError("reference full-record verification failed")
        resolved.append(full)
    output = dict(result)
    output["resolved_reference_records"] = resolved
    output["reference_resolution"] = "verified_full_records"
    return output, len(resolved)


def _write_private(path_text: str, root: Path, result: dict, receipt: dict) -> None:
    path = Path(path_text)
    if not path.is_absolute() or path.suffix.lower() != ".json" or not path.parent.is_dir():
        raise ValueError("private output must be an absolute new JSON file")
    resolved_parent = path.parent.resolve(strict=True)
    source_root = root.resolve(strict=True)
    working_root = Path.cwd().resolve(strict=True)
    if (resolved_parent == source_root or source_root in resolved_parent.parents
            or resolved_parent == working_root or working_root in resolved_parent.parents):
        raise ValueError("private output cannot be inside source or public workspace")
    document = json.dumps({"schema": "forge.mpai05.readonly-consumer-result.v1",
                           "receipt": receipt, "result": result},
                          sort_keys=True, ensure_ascii=False).encode("utf-8")
    if len(document) > MAX_PRIVATE_RESULT_BYTES:
        raise ValueError("result exceeds private output budget")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(document)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private one-shot pinned Mind-Palace recall")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--private-result", required=True)
    parser.add_argument("--profile", choices=("status", "continuation", "architecture",
                                             "historical"), default="continuation")
    parser.add_argument("--mode", choices=MODES, default="off",
                        help="off (default), shadow (serve original), eligible (opt-in)")
    parser.add_argument("--resolve-reference-only", action="store_true",
                        help="opt-in verified full-record followup in private output")
    args = parser.parse_args(argv)
    try:
        # Stdin pipes commonly append CRLF; remove only line terminators.
        query = sys.stdin.read(MAX_QUERY_BYTES + 1).rstrip("\r\n")
        root = Path(args.source_root).resolve(strict=True)
        sys.path.insert(0, str(root / "tools"))
        from mindpalace_readonly import MemorySnapshot
        snapshot = MemorySnapshot(root, args.source_sha, ["Mind-Palace"])
        result, receipt = retrieve(snapshot, args.source_sha, query,
                                   mode=args.mode, projects=["Mind-Palace"],
                                   profile=args.profile,
                                   resolve_reference_only=args.resolve_reference_only)
        _write_private(args.private_result, root, result, receipt)
    except Exception as exc:
        # Intentionally no exception message: it might include private inputs.
        print("MPAI05_READ_DENIED=" + type(exc).__name__, file=sys.stderr)
        return 1
    print("MPAI05_CONSUMER_EXECUTION=PASS")
    print("MPAI05_MODE=" + receipt["mode"])
    print("MPAI05_ROUTING=" + receipt["routing"])
    print("MPAI05_MATCH_COUNT=" + str(receipt["record_count"]))
    print("MPAI05_SOURCE_PIN=" + receipt["source_sha"])
    print("MPAI05_SHADOW_CHANGED_TOP4=" + str(receipt["shadow_changed_top4"]))
    print("MPAI05_PRIVATE_RESULT_ONLY=True")
    print("MPAI05_SCIENTIFIC_BENEFIT=NOT_EVALUATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

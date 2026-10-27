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


def _top_digest(result: dict) -> str:
    ids = [m["id"] for m in result.get("matches", [])[:4]]
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()


def retrieve(snapshot, sha: str, query: str, *, mode: str = "off",
             projects: list[str] | None = None, profile: str = "continuation") -> tuple[dict, dict]:
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
    }
    return result, receipt


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
    args = parser.parse_args(argv)
    try:
        query = sys.stdin.read(MAX_QUERY_BYTES + 1)
        root = Path(args.source_root).resolve(strict=True)
        sys.path.insert(0, str(root / "tools"))
        from mindpalace_readonly import MemorySnapshot
        snapshot = MemorySnapshot(root, args.source_sha, ["Mind-Palace"])
        result, receipt = retrieve(snapshot, args.source_sha, query,
                                   mode=args.mode, projects=["Mind-Palace"],
                                   profile=args.profile)
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

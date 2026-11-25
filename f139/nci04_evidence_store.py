"""Persistent Append-Only Cross-Run Research Evidence Store for FORGE F139 (Gate 19).

Stores cryptographically hash-chained research receipts (`ExperimentReceipt`,
`CampaignLedger`, `SelfImprovementBundle`, `CrossArchitectureEvidence`) in an
append-only JSONL ledger strictly separate from the signed controller
`state.sqlite`.

Hard boundaries:
- Never touches or mutates `state.sqlite` (fail-closed denies `.sqlite`/`.db` paths).
- Every appended record links to `prev_record_sha256` and seals `record_sha256`
  so tampering, deletion, or silent reordering is immediately detected.
- Retains 100% of verified and negative/failed runs for cumulative learning.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

from f139.nci04_native_contract import canonical, digest

STORE_SCHEMA = "forge.f139.research-evidence-store-record.v1"
GENESIS_HASH = "0" * 64
ALLOWED_RECORD_KINDS = frozenset({
    "experiment_receipt",
    "campaign_ledger",
    "self_improvement_bundle",
    "cross_architecture_evidence",
})


class EvidenceStoreDenied(ValueError):
    """Fail-closed denial for invalid store path, corrupt chain, or bad record."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise EvidenceStoreDenied("F139_EVIDENCE_STORE_" + reason)


def _validate_store_path(store_path: Path) -> Path:
    p = Path(store_path)
    suffix = p.suffix.lower()
    need(suffix not in (".sqlite", ".sqlite3", ".db"), "CONTROLLER_SQLITE_PATH_FORBIDDEN")
    need(p.name != "state.sqlite", "CONTROLLER_SQLITE_PATH_FORBIDDEN")
    need(not p.is_symlink(), "STORE_SYMLINK_FORBIDDEN")
    return p


def read_evidence_records(store_path: Path) -> list[dict]:
    """Read and cryptographically verify the entire append-only evidence chain."""
    p = _validate_store_path(store_path)
    if not p.exists():
        return []
    need(p.is_file(), "STORE_NOT_REGULAR_FILE")
    records: list[dict] = []
    expected_prev = GENESIS_HASH
    with p.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except ValueError as exc:
                raise EvidenceStoreDenied("F139_EVIDENCE_STORE_CORRUPT_JSON") from exc
            need(type(rec) is dict and rec.get("schema") == STORE_SCHEMA, "RECORD_SCHEMA_INVALID")
            need(rec.get("seq") == idx, "RECORD_SEQ_DRIFT")
            need(rec.get("prev_record_sha256") == expected_prev, "CHAIN_PREV_HASH_MISMATCH")
            sig = rec.get("record_sha256")
            unsigned = {k: v for k, v in rec.items() if k != "record_sha256"}
            need(digest(canonical(unsigned)) == sig, "RECORD_DIGEST_TAMPERED")
            expected_prev = sig
            records.append(rec)
    return records


def append_evidence_record(
    store_path: Path,
    *,
    kind: str,
    method_family: str,
    status: str,
    payload: dict,
    primary_metric: str | None = None,
    primary_value: float | None = None,
    higher_is_better: bool = True,
) -> dict:
    """Append a hash-chained research record to the persistent JSONL evidence store."""
    p = _validate_store_path(store_path)
    need(kind in ALLOWED_RECORD_KINDS, "UNKNOWN_RECORD_KIND")
    need(type(method_family) is str and 2 <= len(method_family) <= 64, "METHOD_FAMILY_INVALID")
    need(status in ("VERIFIED", "NEGATIVE", "QUALIFIED", "REJECTED"), "STATUS_INVALID")
    need(type(payload) is dict, "PAYLOAD_NOT_DICT")
    need(payload.get("paid_model_calls", 0) == 0, "PAID_MODEL_CALLS_FORBIDDEN")
    need(payload.get("auto_promote_checkpoint", False) is False, "AUTO_PROMOTE_FORBIDDEN")
    need(payload.get("scientific_first_use", False) is False, "SCIENTIFIC_FIRST_USE_UNQUALIFIED")

    existing = read_evidence_records(p)
    seq = len(existing) + 1
    prev_hash = existing[-1]["record_sha256"] if existing else GENESIS_HASH

    unsigned = {
        "schema": STORE_SCHEMA,
        "seq": seq,
        "prev_record_sha256": prev_hash,
        "recorded_at_unix": int(time.time()),
        "kind": kind,
        "method_family": method_family,
        "status": status,
        "primary_metric": primary_metric,
        "primary_value": primary_value,
        "higher_is_better": higher_is_better,
        "payload_sha256": digest(canonical(payload)),
        "payload": payload,
    }
    record = dict(unsigned, record_sha256=digest(canonical(unsigned)))

    p.parent.mkdir(parents=True, exist_ok=True)
    line = canonical(record).decode("utf-8") + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    return record


def summarize_evidence_store(store_path: Path) -> dict:
    """Compute cumulative per-family stats, best scores, and failure counts."""
    records = read_evidence_records(store_path)
    by_family: dict[str, dict] = {}
    for rec in records:
        fam = rec["method_family"]
        bucket = by_family.setdefault(fam, {
            "total": 0,
            "verified": 0,
            "negative": 0,
            "qualified": 0,
            "rejected": 0,
            "consecutive_failures": 0,
            "best_metric": None,
            "best_value": None,
            "best_seq": None,
        })
        bucket["total"] += 1
        st = rec["status"]
        if st == "VERIFIED":
            bucket["verified"] += 1
            bucket["consecutive_failures"] = 0
        elif st == "QUALIFIED":
            bucket["qualified"] += 1
            bucket["consecutive_failures"] = 0
        elif st == "NEGATIVE":
            bucket["negative"] += 1
            bucket["consecutive_failures"] += 1
        elif st == "REJECTED":
            bucket["rejected"] += 1
            bucket["consecutive_failures"] += 1

        val = rec.get("primary_value")
        if st in ("VERIFIED", "QUALIFIED") and type(val) in (int, float):
            cur = bucket["best_value"]
            better = (
                cur is None
                or (val > cur if rec.get("higher_is_better", True) else val < cur)
            )
            if better:
                bucket["best_value"] = float(val)
                bucket["best_metric"] = rec.get("primary_metric")
                bucket["best_seq"] = rec["seq"]

    summary = {
        "schema": "forge.f139.research-evidence-store-summary.v1",
        "chain_verified": True,
        "total_records": len(records),
        "head_record_sha256": records[-1]["record_sha256"] if records else GENESIS_HASH,
        "by_family": by_family,
    }
    summary["summary_sha256"] = digest(canonical(summary))
    return summary

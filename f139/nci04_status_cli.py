"""One-Command Read-Only Status & Scientific Scorecard CLI for FORGE F139 (Gate 19).

Inspects (strictly read-only, zero mutations):
  1. Local hardware capabilities (`detect_hardware_profile`),
  2. Optional controller `state.sqlite` (`mode=ro` + `PRAGMA query_only=ON`) and
     highest installed `v{N}` source-forward certificate version,
  3. Optional persistent research evidence store (`summarize_evidence_store`),
  4. Multi-lane scheduler recommendation (`select_next_lane`).

Usage:
  python -B -m f139.nci04_status_cli [--db PATH] [--store PATH] [--human]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from f139.nci04_evidence_store import summarize_evidence_store
from f139.nci04_fresh_owner_source_forward_chain import (
    CERT_NAME_RE,
)
from f139.nci04_hardware_trainer import detect_hardware_profile
from f139.nci04_multi_lane_scheduler import select_next_lane
from f139.nci04_native_contract import canonical, digest

STATUS_SCHEMA = "forge.f139.readonly-status-scorecard.v1"


def _inspect_controller_readonly(db_path: Path | None) -> dict:
    if db_path is None or not db_path.is_file():
        return {
            "present": False,
            "head_seq": None,
            "head_hash": None,
            "highest_cert_version": None,
        }
    uri = f"file:{db_path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        row = conn.execute("SELECT head_seq, head_hash FROM meta").fetchone()
    finally:
        conn.close()

    highest_ver = None
    for entry in db_path.parent.iterdir():
        m = CERT_NAME_RE.fullmatch(entry.name)
        if m:
            v = int(m.group(1))
            if highest_ver is None or v > highest_ver:
                highest_ver = v
    if highest_ver is None and (db_path.parent / "fresh-original-owner-source-forward.json").is_file():
        highest_ver = 1

    return {
        "present": True,
        "head_seq": int(row[0]) if row else None,
        "head_hash": str(row[1]) if row else None,
        "highest_cert_version": highest_ver,
    }


def collect_readonly_status(
    *,
    db_path: Path | None = None,
    evidence_store_path: Path | None = None,
) -> dict:
    """Collect a deterministic, read-only FORGE operational & scientific scorecard."""
    hw = detect_hardware_profile()
    ctrl = _inspect_controller_readonly(db_path)
    ev = (
        summarize_evidence_store(evidence_store_path)
        if evidence_store_path is not None
        else {"chain_verified": True, "total_records": 0, "by_family": {}}
    )
    sched = select_next_lane(evidence_store_path=evidence_store_path)

    report = {
        "schema": STATUS_SCHEMA,
        "readonly": True,
        "controller": ctrl,
        "hardware": {
            "platform": hw["platform"],
            "cpu_count": hw["cpu_count"],
            "torch_available": hw["torch_available"],
            "cuda_available": hw["cuda_available"],
            "recommended_backend": hw["recommended_backend"],
        },
        "evidence_store": {
            "chain_verified": ev["chain_verified"],
            "total_records": ev["total_records"],
            "by_family": ev["by_family"],
        },
        "next_recommended_lane": sched["selected_lane"],
        "eligible_lanes": sched["eligible_lanes"],
        "skipped_lanes": sched["skipped_lanes"],
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    report["status_sha256"] = digest(canonical(report))
    return report


def _format_human(report: dict) -> str:
    hw = report["hardware"]
    ctrl = report["controller"]
    ev = report["evidence_store"]
    lines = [
        f"FORGE Read-Only Status Scorecard ({report['status_sha256'][:12]})",
        f"  Hardware : {hw['platform']} | CPUs={hw['cpu_count']} | torch={hw['torch_available']} | cuda={hw['cuda_available']} | backend={hw['recommended_backend']}",
        f"  SQLite   : present={ctrl['present']} | head_seq={ctrl['head_seq']} | cert=v{ctrl['highest_cert_version']}",
        f"  Evidence : chain_ok={ev['chain_verified']} | records={ev['total_records']} | next_lane={report['next_recommended_lane']}",
    ]
    for fam, st in sorted(ev["by_family"].items()):
        lines.append(
            f"    - {fam:18s} total={st['total']} verified={st['verified']} neg={st['negative']} best={st['best_metric']}={st['best_value']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FORGE read-only status & scorecard CLI")
    parser.add_argument("--db", type=Path, default=None, help="Optional path to state.sqlite (read-only)")
    parser.add_argument("--store", type=Path, default=None, help="Optional path to research evidence JSONL")
    parser.add_argument("--human", action="store_true", help="Print human-readable summary")
    ns = parser.parse_args(argv)
    report = collect_readonly_status(db_path=ns.db, evidence_store_path=ns.store)
    if ns.human:
        print(_format_human(report))
    else:
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""F139-NCI04-A4 original-owner SQLite custody audit (read-only).

This deliberately does NOT start/stop/dispatch F139, admit a source transition,
modify the owner database, or declare naturally unattended development proven.
Original D2C/D2J custody and the sealed 23-event prefix are re-verified before
the two D2K issue-bound original attempts. A checked source-copy, exact local
receipt ZIP bytes, and independently pinned GitHub provider metadata must agree.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from f139 import audit_d2k_custody as historical
from f139.local_controller import (
    Database, GitHub, F139Error, hash_bytes, receipt_from_zip,
)

PREFIX_HEAD = "eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87"
SOURCE = "5a252f8dde245c67e9a5d9c9dfcd421fd18f5d91"
EXPECTED = {
    687: {
        "issue_id": 5951110847, "lane": "Wingless", "run_id": 39513293606,
        "ticket": "f139-d2k-i687-5a252f8dde24-5a2ecddb",
        "target_package": "./optimizerstages",
        "artifacts": {
            "ubuntu-latest": {
                "id": 12306985329, "size": 1313,
                "sha256": "ff7ffae1afb7adc23a4af3ad9d24f65fde7de7b51933ea8390a991d19f8bbbc8",
            },
            "windows-latest": {
                "id": 12306183513, "size": 1315,
                "sha256": "d9ca538ba8eb7a87bf84679437f6cb368e25709f7793aec7a577e9eee321deb2",
            },
        },
    },
    688: {
        "issue_id": 5951111288, "lane": "Yggdrasil", "run_id": 39513381790,
        "ticket": "f139-d2k-i688-5a252f8dde24-02ded761",
        "target_package": "./dreamrsi",
        "artifacts": {
            "ubuntu-latest": {
                "id": 12307445140, "size": 1299,
                "sha256": "802b9e4d97168336993bc1528334b0dcbe25f1adaa6a7a3dce6502f02a687a28",
            },
            "windows-latest": {
                "id": 12307195334, "size": 1303,
                "sha256": "05a272f0555bfb7240826e9f9b255eca5398574dda8201d16163fe9fe2555c06",
            },
        },
    },
}
ALLOWED_KINDS = (
    "DEVELOPMENT_WORK_ADMITTED",
    "TASK_INTAKE",
    "BEFORE_DISPATCH_INTENT",
    "DISPATCH_POST_RETURNED",
    "PROVIDER_VERIFIED_TERMINAL",
)


class A4CustodyBlocked(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise A4CustodyBlocked("F139_NCI04_A4_" + code)


def _provider_artifact_rows(provider_arts, oslabel):
    matches = [x for x in provider_arts
               if x.get("name") == "forge-f139-dev-receipt-" + oslabel]
    require(len(matches) == 1, "PROVIDER_RECEIPT_AMBIGUOUS")
    return matches[0]


def verify_one(*, owner_root, db: Database, provider: GitHub, spec: dict,
               admission: dict, events: list[dict]) -> dict:
    ticket = spec["ticket"]
    rows = [dict(r) for r in db.conn.execute(
        "SELECT * FROM tasks WHERE ticket=?", (ticket,))]
    require(len(rows) == 1, "ISSUE_TASK_NOT_UNIQUE")
    row = rows[0]
    require(row["stage"] == "VERIFIED" and row["source_sha"] == SOURCE
            and row["lane"] == spec["lane"] and row["run_id"] == spec["run_id"]
            and isinstance(row["evidence_sha"], str)
            and re.fullmatch(r"[a-f0-9]{64}", row["evidence_sha"]) is not None
            and isinstance(row["started_at"], str),
            "ISSUE_TASK_NOT_TERMINAL")
    fields = db.d2k_fields(ticket)
    issue_number = int(fields["issue_number"])
    require(issue_number in EXPECTED and EXPECTED[issue_number] == spec
            and int(fields["issue_id"]) == spec["issue_id"]
            and fields["target_package"] == spec["target_package"]
            and admission["ticket"] == ticket
            and admission["issue_number"] == issue_number
            and admission["issue_id"] == spec["issue_id"]
            and admission["source_sha"] == SOURCE
            and admission["lane"] == spec["lane"]
            and admission["kind"] == "go-package-test-diagnostic"
            and admission["target_package"] == spec["target_package"]
            and admission["body_sha256"] == fields["body_sha256"]
            and admission["manifest_sha256"] == row["manifest_sha"]
            and admission["scientific_first_use"] is False,
            "ISSUE_ADMISSION_DRIFT")

    # Authenticated issue-specific lifecycle must have one of each original
    # event, strictly ordered. A second claim/POST/terminal is a replay.
    lifecycle = [(x["seq"], x["kind"], json.loads(x["payload"]))
                 for x in events
                 if x["kind"] in ALLOWED_KINDS
                 and json.loads(x["payload"]).get("ticket") == ticket]
    require([k for _, k, _ in lifecycle] == list(ALLOWED_KINDS),
            "ISSUE_LIFECYCLE_OR_REPLAY")
    require(lifecycle[0][2]["manifest_sha256"] == row["manifest_sha"]
            and lifecycle[1][2]["manifest_sha"] == row["manifest_sha"]
            and lifecycle[2][2]["started_at"] == row["started_at"]
            and lifecycle[3][2]["ticket"] == ticket
            and lifecycle[4][2]["run_id"] == spec["run_id"]
            and lifecycle[4][2]["evidence_sha"] == row["evidence_sha"],
            "ISSUE_LIFECYCLE_BINDING_DRIFT")

    matched = provider.candidates(ticket, row["started_at"])
    require(isinstance(matched, dict) and matched.get("id") == spec["run_id"],
            "PROVIDER_ORIGINAL_ATTEMPT_DRIFT")
    rid, artifacts = provider.run_proof(matched, ticket, SOURCE, row["started_at"])
    require(rid == spec["run_id"], "PROVIDER_RUN_MISMATCH")
    evidence_path = owner_root / "evidence" / ticket / str(rid)
    require(evidence_path.is_dir() and not evidence_path.is_symlink()
            and not (owner_root / "evidence" / ticket).is_symlink(),
            "EVIDENCE_DIRECTORY_MISSING")
    require(isinstance(row["evidence_dir"], str)
            and Path(row["evidence_dir"]).resolve() == evidence_path.resolve()
            and {p.name for p in evidence_path.iterdir()} ==
                {"manifest.json", "ubuntu-latest.zip", "windows-latest.zip"},
            "EVIDENCE_DIRECTORY_DRIFT")
    manifest_path = evidence_path / "manifest.json"
    require(manifest_path.is_file() and not manifest_path.is_symlink()
            and manifest_path.stat().st_size <= 8192,
            "EVIDENCE_MANIFEST_UNTRUSTED")
    manifest_raw = manifest_path.read_bytes()
    require(hash_bytes(manifest_raw) == row["evidence_sha"],
            "EVIDENCE_MANIFEST_DIGEST_DRIFT")
    try:
        manifest = json.loads(manifest_raw)
    except ValueError as exc:
        raise A4CustodyBlocked("F139_NCI04_A4_MANIFEST_INVALID") from exc
    require(manifest.get("schema") == "forge.f139.windows-evidence-manifest.v1"
            and manifest.get("ticket") == ticket
            and manifest.get("run_id") == rid
            and manifest.get("scientific_originals") == 0
            and manifest.get("approved_science") is False,
            "EVIDENCE_MANIFEST_SOURCE_OR_AUTHORITY")
    fingerprints = {}
    for oslabel in ("ubuntu-latest", "windows-latest"):
        pinned = spec["artifacts"][oslabel]
        provider_artifact = _provider_artifact_rows(artifacts, oslabel)
        require(provider_artifact.get("id") == pinned["id"]
                and provider_artifact.get("size_in_bytes") == pinned["size"]
                and provider_artifact.get("digest") == "sha256:" + pinned["sha256"],
                "PROVIDER_ARTIFACT_DRIFT")
        path = evidence_path / (oslabel + ".zip")
        require(path.is_file() and not path.is_symlink()
                and path.stat().st_size == pinned["size"],
                "LOCAL_ARTIFACT_SIZE_DRIFT")
        raw = path.read_bytes()
        require(hash_bytes(raw) == pinned["sha256"]
                and manifest.get("sha256", {}).get(oslabel) == pinned["sha256"],
                "LOCAL_ARTIFACT_DIGEST_DRIFT")
        receipt = receipt_from_zip(
            raw, {"digest": provider_artifact["digest"],
                  "size_in_bytes": provider_artifact["size_in_bytes"]},
            row, rid, oslabel, db.meta()["epoch"], d2k_fields=fields)
        require(receipt["outcome"] == "PASS", "DIAGNOSTIC_FAILED_NOT_COMPLETED")
        fingerprints[oslabel] = pinned["sha256"]
    return {"issue_number": issue_number, "ticket": ticket, "run_id": rid,
            "source_sha": SOURCE, "stage": "VERIFIED",
            "local_provider_original_bytes": 2,
            "artifacts_sha256": fingerprints,
            "scientific_first_use": False}


def audit(db_path: Path, *, sealed_23_head: str,
          provider: GitHub | None = None) -> dict:
    require(isinstance(sealed_23_head, str)
            and re.fullmatch(r"[a-f0-9]{64}", sealed_23_head) is not None
            and sealed_23_head == PREFIX_HEAD,
            "INDEPENDENT_SEALED_PREFIX_REQUIRED")
    require(isinstance(db_path, Path), "DB_PATH_INVALID")
    owner_root = db_path.parent.resolve()
    api = provider or GitHub()
    # Exact protected-main identity is an observation, never permission to
    # transition SQLite or silently repin a historical task.
    require(api.protected_main() == SOURCE, "PROTECTED_MAIN_DRIFT")
    with tempfile.TemporaryDirectory(prefix="f139-a4-readonly-") as tmp:
        source_copy = historical.copied_snapshot(db_path, Path(tmp))
        db = Database(source_copy)  # writes, if any, affect TEMPORARY copy only
        try:
            meta = db.meta()
            require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
                    and meta["source_sha"] == SOURCE,
                    "OWNER_CONTROLLER_SOURCE_OR_LIFECYCLE_DRIFT")
            db.verify()
            events = [dict(x) for x in db.conn.execute(
                "SELECT * FROM events ORDER BY seq")]
            require(len(events) >= 33
                    and events[22]["sha"] == sealed_23_head,
                    "SEALED_PREFIX_OR_D2K_HISTORY_MISSING")
            original, _, _ = historical.verify_chain(events[:23],
                                                     sealed_23_head)
            historical_tasks = [dict(x) for x in db.conn.execute(
                "SELECT * FROM tasks ORDER BY ticket")
                if x["ticket"] in original]
            require(len(historical_tasks) == 4
                    and {x["ticket"] for x in historical_tasks} == set(original),
                    "FOUR_ORIGINAL_TASKS_NOT_PRESERVED")
            provider_history = historical.load_provider_anchor()
            for row in historical_tasks:
                require(row["run_id"] == original[row["ticket"]]["run_id"]
                        and row["evidence_sha"] == original[row["ticket"]]["evidence_sha"],
                        "HISTORICAL_EVENT_TASK_DRIFT")
                historical.verify_evidence(owner_root, row,
                                           meta["epoch"], provider_history)
            admissions = [json.loads(x["payload"]) for x in events
                          if x["kind"] == "DEVELOPMENT_WORK_ADMITTED"]
            matching = [x for x in admissions
                        if x.get("issue_number") in EXPECTED]
            require(len(matching) == 2
                    and {x["issue_number"] for x in matching} == set(EXPECTED),
                    "ISSUE_ADMISSION_MISSING_OR_DUPLICATE")
            reports = []
            for record in matching:
                reports.append(verify_one(owner_root=owner_root, db=db,
                               provider=api, spec=EXPECTED[record["issue_number"]],
                               admission=record, events=events))
            require(all(not json.loads(event["payload"]).get("scientific_first_use", False)
                        for event in events
                        if event["kind"] in ("DEVELOPMENT_WORK_ADMITTED",
                                            "SOURCE_TRANSITION_ADMITTED")),
                    "PROTECTED_FIRST_USE_FLAG")
            return {
                "schema": "forge.f139.nci04.original-native-controller-custody.v1",
                "disposition": "LOCAL_D2K_CUSTODY_VERIFIED_NOT_UNATTENDED_PROOF",
                "controller_source_sha": meta["source_sha"],
                "event_head_sha256": meta["head_hash"],
                "sealed_23_event_head_sha256": sealed_23_head,
                "events": len(events), "historical_task_count": 4,
                "historical_provider_artifact_count": 8,
                "d2k_provider_artifact_count": 4,
                "original_sqlite_mutations": 0,
                "controller_dispatches": 0, "controller_restarts": 0,
                "native_development_proven": False,
                "unattended_controller_origin_proven": False,
                "scientific_first_use": False, "issues": reports,
            }
        finally:
            db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="F139 original-owner read-only custody verifier")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--sealed-23-head", required=True)
    args = parser.parse_args()
    require(os.name == "nt", "OWNER_WINDOWS_REQUIRED")
    result = audit(args.db, sealed_23_head=args.sealed_23_head)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (A4CustodyBlocked, F139Error, historical.CustodyBlocked,
            sqlite3.DatabaseError, ValueError, OSError) as exc:
        raise SystemExit("F139_NCI04_A4_FAIL_CLOSED " + str(exc)) from exc

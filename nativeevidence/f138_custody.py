"""F138-C1: deterministic provenance reconstitution, not an authority grant.

This verifies that retained repository JSON encodes the *exact raw bytes* of
the F137 parent and dual-OS F138 lineage reports previously authenticated
from GitHub. A SHA256 match is integrity evidence, not an issuer signature.
It does not claim complete permanent provider-index retention.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reference/research-intake/f138-custody-20261018-1144.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
NONCE = re.compile(r"^[0-9a-f]{32}$")


class CustodyInvalid(ValueError):
    pass


def need(value, reason):
    if not value:
        raise CustodyInvalid("F138_CUSTODY_" + reason)


def encode(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("utf-8")


def sha(obj):
    return hashlib.sha256(encode(obj)).hexdigest()


def check(record):
    need(type(record) is dict
         and record.get("schema") ==
            "forge.autonomy.f138.durable-source-custody-intake.v1"
         and record.get("repository") == "spoonman136668-ai/FORGE",
         "SCHEMA_OR_REPO")
    source = record.get("source_main_sha")
    need(type(source) is str and HEX40.fullmatch(source),
         "SOURCE_MISSING")
    observation = record.get("source_custody_observation", {})
    need(type(observation) is dict
         and observation.get("github_run_id") == 39124429721
         and observation.get("github_artifact_id") == 12135755671
         and observation.get("qualified_readonly_pr") == 529
         and type(observation.get("qualified_verifier_head")) is str
         and HEX40.fullmatch(observation["qualified_verifier_head"]),
         "ORIGINAL_PROVIDER_IDENTITY")
    for key in ("github_artifact_zip_sha256",
                "provider_snapshot_json_sha256",
                "provider_decision_json_sha256"):
        need(type(observation.get(key)) is str
             and HEX64.fullmatch(observation[key]), "PROVIDER_DIGEST_UNPINNED")
    outcome = record.get("reported_disposition", {})
    need(type(outcome) is dict
         and outcome.get("windows_recovery_continuity_verified") is True
         and outcome.get("verified_unattended_runs") == 4
         and outcome.get("genuine_scheduled_count") == 0
         and outcome.get("full_f138_verdict") == "PENDING"
         and outcome.get("scientific_first_use_authorized") is False
         and outcome.get("accepted_ref_mutations") == 0,
         "FALSE_CONTINUITY_PROMOTION")
    scope = record.get("custody_scope", {})
    need(type(scope) is dict
         and scope.get("exact_controller_decision_bytes_reconstructable") is True
         and scope.get("exact_child_lineage_json_bytes_reconstructable") is True
         and scope.get("exact_dual_os_receipt_bytes_reconstructable") is True
         and scope.get("entire_provider_snapshot_bytes_embedded") is False
         and scope.get("original_zip_bytes_embedded") is False
         and scope.get("permanent_complete_custody_qualified") is False
         and scope.get("source_review_required") is True
         and scope.get("merge_separately_authorized") is False,
         "CUSTODY_OVERCLAIM")
    entries = record.get("original_source_records")
    need(type(entries) is list and len(entries) == 4, "RECORD_COUNT")
    controllers, children, nonces, begins = set(), set(), set(), []
    snapshots = []
    for row in entries:
        need(type(row) is dict and type(row.get("controller")) is dict
             and type(row.get("child")) is dict
             and type(row.get("original_sha256")) is dict,
             "RECORD_SHAPE")
        parent = row["controller"]
        child = row["child"]
        hashes = row["original_sha256"]
        cid, rid = parent.get("controller_run_id"), child.get("run_id")
        nonce = parent.get("wake_nonce")
        need(type(cid) is int and cid>0 and cid not in controllers
             and type(rid) is int and rid>cid and rid not in children
             and type(nonce) is str and NONCE.fullmatch(nonce)
             and nonce not in nonces, "REPLAY_OR_DUPLICATE")
        controllers.add(cid)
        children.add(rid)
        nonces.add(nonce)
        need(parent.get("schema") ==
                 "forge.autonomy.f137.windows-development-wake.v1"
             and child.get("schema") ==
                 "forge.autonomy.f138.development-lineage.v1"
             and parent.get("source_sha") == child.get("source_sha") == source
             and child.get("parent_source_sha") == source
             and child.get("parent_run_id") == cid
             and parent.get("dispatch") is True
             and parent.get("reasons") == []
             and parent.get("daily_cap") == 96
             and parent.get("frozen_f136_sha256") ==
                 "256051094a5581c8b010ad63ffd98c42d228e11ea8c89d0f4003a1d6f838c6d2"
             and parent.get("origin") == child.get("origin") ==
                 "f137-windows-recovery"
             and parent.get("genuine_schedule_claim") is False
             and child.get("genuine_integrated_schedule") is False
             and child.get("event") == "workflow_dispatch"
             and child.get("run_attempt") == 1
             and child.get("development_only") is True
             and child.get("ref") == "refs/heads/main"
             and child.get("repository") == "spoonman136668-ai/FORGE",
             "SOURCE_OR_PARENT_DRIFT")
        for boolkey in ("scientific_first_use_authorized",):
            need(parent.get(boolkey) is False and child.get(boolkey) is False,
                 "SCIENTIFIC_ADMISSION_FALSE")
        for key in ("science_originals", "accepted_ref_mutations",
                    "codex_calls", "paid_api_calls"):
            need(parent.get(key) == 0, "CONTROLLER_AUTHORITY_EXCEEDED")
        for key in ("scientific_originals_dispatched",
                    "accepted_ref_mutations", "optimizer_promotions",
                    "codex_calls", "paid_model_calls"):
            need(child.get(key) == 0, "CHILD_AUTHORITY_EXCEEDED")
        need(type(hashes.get("controller_json")) is str
             and sha(parent) == hashes["controller_json"]
             and type(hashes.get("child_lineage_json")) is str
             and sha(child) == hashes["child_lineage_json"],
             "EXACT_REPORT_BYTES_DIFFER")
        receipt = (sha(child) + "  f138-lineage.json\n").encode("ascii")
        receipt_sha = hashlib.sha256(receipt).hexdigest()
        need(receipt_sha == hashes.get("ubuntu_lineage_receipt") ==
             hashes.get("windows_lineage_receipt"),
             "CROSS_PLATFORM_RECEIPT_DRIFT")
        t = row.get("observed_child_created_at")
        e = row.get("observed_child_updated_at")
        need(type(t) is str and type(e) is str
             and t < e and t.endswith("Z") and e.endswith("Z"),
             "TIME_ORDER_INVALID")
        begins.append(t)
        snapshots.append({
            "controller_run_id": cid, "child_run_id": rid,
            "controller_sha256": sha(parent), "child_sha256": sha(child),
            "ubuntu_windows_receipt_sha256": receipt_sha,
            "created_at": t, "updated_at": e,
        })
    need(begins == sorted(begins) and len(set(begins)) == 4,
         "CHRONOLOGY_DRIFT")
    need((sum(x["controller"]["daily_starts"] for x in entries)
          == 6+7+8+9), "DAILY_BUDGET_HISTORY_DRIFT")
    return {
        "schema": "forge.autonomy.f138.reconstructed-source-custody.v1",
        "verdict": "PARTIAL_SOURCE_RECORD_CUSTODY_VERIFIED",
        "source_sha": source,
        "reconstructed_controller_decisions": len(snapshots),
        "reconstructed_cross_platform_lineages": len(snapshots) * 2,
        "source_records": snapshots,
        "complete_provider_snapshot_custody": False,
        "f138_full_continuity_accepted": False,
        "scientific_first_use_authorized": False,
        "accepted_ref_mutations": 0,
    }


def load(path=SOURCE):
    data = Path(path).read_bytes()
    need(0 < len(data) <= 100_000, "MANIFEST_SIZE")
    def no_dupes(rows):
        d = {}
        for k, v in rows:
            need(k not in d, "DUPLICATE_JSON_FIELD")
            d[k] = v
        return d
    return json.loads(data, object_pairs_hook=no_dupes)


if __name__ == "__main__":
    result = check(load())
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    print("F138_SOURCE_CUSTODY_C1=PASS")
    print("F138_COMPLETE_PERMANENT_CUSTODY=NOT_YET_PROVEN")

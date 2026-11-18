"""Read-only FORGE audit of real Yggdrasil CKAD25 GitHub campaign artifacts.

This does NOT dispatch FORGE jobs, authenticate arbitrary caller-supplied API
JSON, certify source scientific first-use, promote weights or replace F139.
The caller must obtain run/artifact metadata directly from a trusted GitHub
GET and exact archive bytes. Digest matches do not authenticate their origin
if supplied by an untrusted actor.
"""
from __future__ import annotations

from io import BytesIO
import json
import re
import zipfile

from f139.ckad_stage_custody import (
    CKAD25_DEV_SHA, CKAD25_DEV_TREE, canonical, digest,
)
from f139.ckad_native_stage_artifact import inspect_native_checkpoint
from f139.ckad_campaign_request import CampaignDenied, need

SOURCE_REPO = "spoonman136668-ai/Yggdrasil"
WORKFLOW_PATH = ".github/workflows/ckad25-development-campaign.yml"
RUN_NAME = "CKAD25 source-owned bounded development training proof"
BRANCH = "research/ckad-native-stage-dev-20261118"
CAMPAIGN = "ckad-two-stage-dev-20261118"
RESULT_SCHEMA = "yggdrasil.ckad.bounded-development-campaign.v1"
RECEIPT_SCHEMA = "yggdrasil.ckad.native-development-stage-receipt.v1"
FILES = frozenset((
    "campaign-result.json", "evaluation.json", "initial.native.json",
    "stage-01.native.json", "stage-02.native.json",
    "stage-01.packet.json", "stage-02.packet.json",
    "stage-01.receipt.json", "stage-02.receipt.json",
))
PLATFORMS = ("ubuntu-latest", "windows-2022")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_json(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 16 * 1024 * 1024,
         "CAMPAIGN_BYTES_REQUIRED")
    def unique(pairs):
        o = {}
        for k, v in pairs:
            need(k not in o, "DUPLICATE_JSON_KEY")
            o[k] = v
        return o
    try:
        obj = json.loads(raw.decode("ascii"), object_pairs_hook=unique,
                         parse_constant=lambda _: need(False, "NONFINITE_JSON"))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_JSON_INVALID") from exc
    need(canonical(obj) == raw, "NONCANONICAL_JSON")
    return obj


def _archive(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 2 * 1024 * 1024,
         "ARCHIVE_SIZE_BOUND")
    try:
        with zipfile.ZipFile(BytesIO(raw)) as z:
            items = z.infolist()
            names = [x.filename for x in items]
            need(len(items) == 9 and len(set(names)) == 9
                 and set(names) == FILES
                 and all(0 < x.file_size <= 16 * 1024 * 1024
                         and x.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                         and (x.external_attr >> 16) & 0o170000 != 0o120000
                         for x in items)
                 and sum(x.file_size for x in items) <= 1_000_000,
                 "UNTRUSTED_ARCHIVE_ENTRIES")
            return {name: z.read(name) for name in names}
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_ARCHIVE_INVALID") from exc


def _audit_archive(raw):
    f = _archive(raw)
    result = _canonical_json(f["campaign-result.json"])
    need(type(result) is dict
         and result.get("schema") == RESULT_SCHEMA
         and result.get("campaign_id") == CAMPAIGN
         and result.get("source_sha") == CKAD25_DEV_SHA
         and result.get("source_tree") == CKAD25_DEV_TREE
         and result.get("source_repo") == SOURCE_REPO
         and result.get("source_mode") == "previously-consumed-engineering-fixture-only"
         and result.get("stages_completed") == 2
         and result.get("evaluations_completed") == 1
         and result.get("observations") == 12
         and result.get("interventions") == 0
         and result.get("scientific_first_use") is False
         and result.get("scientific_pass") is False
         and result.get("forge_dispatch_authorized") is False
         and result.get("accepted_native") is False
         and type(result.get("receipts")) is list
         and len(result["receipts"]) == 2,
         "CAMPAIGN_SOURCE_OR_AUTHORITY_DRIFT")
    old = f["initial.native.json"]
    need(digest(old) == result["initial_checkpoint_sha256"],
         "INITIAL_CHECKPOINT_PIN")
    prev_receipt = None
    for index in (1, 2):
        name = "stage-0" + str(index)
        packet = f[name + ".packet.json"]
        rec = _canonical_json(f[name + ".receipt.json"])
        new = f[name + ".native.json"]
        need(type(rec) is dict and rec.get("schema") == RECEIPT_SCHEMA
             and rec.get("campaign_id") == CAMPAIGN
             and rec.get("stage_index") == index - 1
             and rec.get("source_commit") == CKAD25_DEV_SHA
             and rec.get("source_tree") == CKAD25_DEV_TREE
             and rec.get("input_checkpoint_sha256") == digest(old)
             and rec.get("output_checkpoint_sha256") == digest(new)
             and rec.get("packet_sha256") == digest(packet)
             and rec.get("parent_receipt_sha256") == prev_receipt
             and rec.get("native_cold_restore_verified") is True
             and rec.get("development_fixture_training_executed") is True
             and rec.get("scientific_first_use") is False
             and rec.get("forge_dispatch_authorized") is False
             and rec.get("scientific_pass") is False
             and rec.get("original_source_authenticated") is False
             and rec.get("model_promotion_authorized") is False,
             "TRAINING_STAGE_SOURCE_OR_CHAIN_DRIFT")
        packet_obj = _canonical_json(packet)
        need(packet_obj.get("source_mode") == "engineering_fixture_only"
             and packet_obj.get("source_kind") == "engineering_public_binary_consequence"
             and packet_obj.get("slot") == 0
             and type(packet_obj.get("rows")) is list
             and len(packet_obj["rows"]) == (8 if index == 1 else 4),
             "SOURCE_PACKETS_CHANGED")
        stable = dict(rec)
        stable.pop("wall_milliseconds", None)
        stable.pop("stable_receipt_sha256", None)
        pin = digest(canonical(stable))
        need(rec.get("stable_receipt_sha256") == pin
             and result["receipts"][index - 1] == pin,
             "NATIVE_STAGE_STABLE_RECEIPT")
        inspect_native_checkpoint(new)
        old, prev_receipt = new, pin
    inspect_native_checkpoint(f["initial.native.json"])
    evaluator = _canonical_json(f["evaluation.json"])
    metric = evaluator.get("metrics", {})
    need(digest(f["evaluation.json"]) == result["evaluation_sha256"]
         and evaluator.get("checkpoint_sha256") == digest(old)
         and evaluator.get("scientific_pass") is False
         and evaluator.get("independent_science") is False
         and metric.get("held") == result.get("held_total") == 4
         and type(metric.get("answered")) is int
         and 0 <= metric["answered"] <= 4
         and type(metric.get("correct")) is int
         and 0 <= metric["correct"] <= metric["answered"]
         and metric["answered"] == result["held_answered"]
         and metric["correct"] == result["held_correct"]
         and result["final_checkpoint_sha256"] == digest(old),
         "HELD_EVALUATION_NOT_BOUND")
    return {"result": result, "checkpoints": (
        f["initial.native.json"], f["stage-01.native.json"], old),
        "evaluation": f["evaluation.json"]}


def audit_github_development_campaign(run, artifacts, zip_by_platform):
    """Check a source-specific, read-only GitHub result and two raw ZIPs.

    Inputs must be retrieved from authenticated GitHub API transport first.
    This function has no network access and does not grant execution rights.
    """
    need(type(run) is dict and type(artifacts) is dict
         and type(zip_by_platform) is dict
         and set(zip_by_platform) == set(PLATFORMS),
         "GITHUB_INPUT_FIELDS")
    run_id = run.get("id")
    need(type(run_id) is int and run_id > 0
         and run.get("name") == RUN_NAME
         and run.get("path") == WORKFLOW_PATH
         and run.get("head_branch") == BRANCH
         and run.get("head_sha") == CKAD25_DEV_SHA
         and run.get("event") == "push"
         and run.get("status") == "completed"
         and run.get("conclusion") == "success"
         and run.get("run_attempt") == 1
         and isinstance(run.get("actor"), dict)
         and run["actor"].get("login") == "spoonman136668-ai",
         "GITHUB_SOURCE_OWNER_RUN_NOT_MATCHED")
    items = artifacts.get("artifacts")
    need(type(items) is list and len(items) == 2,
         "ARTIFACT_COUNT")
    by_name = {a.get("name"): a for a in items if type(a) is dict}
    need(len(by_name) == 2, "ARTIFACT_NAMES_DUPLICATE")
    records = []
    for platform in PLATFORMS:
        expected = "ckad25-development-training-" + platform
        a = by_name.get(expected)
        raw = zip_by_platform[platform]
        need(type(a) is dict and type(raw) is bytes
             and type(a.get("id")) is int and a["id"] > 0
             and a.get("digest") == "sha256:" + digest(raw)
             and a.get("expired") is False
             and a.get("size_in_bytes") == len(raw)
             and type(a.get("workflow_run")) is dict
             and a["workflow_run"].get("id") == run_id
             and a["workflow_run"].get("head_sha") == CKAD25_DEV_SHA,
             "GITHUB_ARTIFACT_DIGEST_OR_SOURCE_DRIFT")
        records.append(_audit_archive(raw))
    linux, windows = records
    need(linux["result"] == windows["result"]
         and linux["checkpoints"] == windows["checkpoints"]
         and linux["evaluation"] == windows["evaluation"],
         "CROSS_PLATFORM_LEARNED_STATE_DRIFT")
    return {"schema": "forge.ckad.cross-platform-development-archive-audit.v1",
            "run_id": run_id, "source_sha": CKAD25_DEV_SHA,
            "source_tree": CKAD25_DEV_TREE,
            "final_checkpoint_sha256": linux["result"]["final_checkpoint_sha256"],
            "initial_checkpoint_sha256": linux["result"]["initial_checkpoint_sha256"],
            "held_answered": linux["result"]["held_answered"],
            "held_correct": linux["result"]["held_correct"],
            "held_total": linux["result"]["held_total"],
            "training_stages_verified_from_bytes": 2,
            "platform_artifact_byte_digests_match_metadata": True,
            "cross_platform_checkpoint_bytes_equal": True,
            "scientific_pass": False,
            "source_owner_execution_authorized": False,
            "forge_dispatch_authorized": False,
            "model_promotion_authorized": False}

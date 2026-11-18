"""Read-only verification of source-owned, Git-committed CKAD25 checkpoints.

The caller MUST retrieve commit identity and bytes from authenticated GitHub
transport; this function cannot authenticate arbitrary caller-supplied claims.
Neither committed fixtures nor their checksums grant training or dispatch.
"""
from __future__ import annotations
import json
from f139.ckad_campaign_request import CampaignDenied, need
from f139.ckad_stage_custody import canonical, digest
from f139.ckad_native_stage_artifact import inspect_native_checkpoint

SCHEMA = "yggdrasil.ckad.persistent-development-evidence.v1"
SOURCE_REPO = "spoonman136668-ai/Yggdrasil"
SNAPSHOT_COMMIT = "224196b24878fbbbc8dbd2ca4e28afbde06b2d8b"
SNAPSHOT_TREE = "af4683869ce4ceba9e86a6a7fa1c43deae18280f"
ORIGINAL_SOURCE = "d743aafea7446d89a20d24fb3a7bdf5fa9c62c72"
ORIGINAL_TREE = "8e60e2ae76eab0e418a203755a6966a0f498eb82"
RUN_ID = 44331408493
FILES = frozenset((
    "initial.native.json", "stage-01.native.json", "stage-02.native.json",
    "stage-01.packet.json", "stage-02.packet.json",
    "stage-01.receipt.json", "stage-02.receipt.json",
    "evaluation.json", "campaign-result.json",
))
PATHS = frozenset(platform + "/" + name
                  for platform in ("linux", "windows") for name in FILES)
MANIFEST_FIELDS = frozenset((
    "schema", "original_source_sha", "original_source_tree", "github_run_id",
    "campaign_result_sha256", "final_checkpoint_sha256",
    "all_platform_files_sha256", "scientific_first_use", "scientific_pass",
    "accepted_native", "forge_dispatch_authorized",
))


def _json(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 16_777_216,
         "PERSISTED_BYTES_MISSING_OR_OVERSIZE")
    def unique(pairs):
        d = {}
        for k, v in pairs:
            need(k not in d, "PERSISTED_DUPLICATE_KEY")
            d[k] = v
        return d
    try:
        d = json.loads(raw.decode("ascii"), object_pairs_hook=unique,
                       parse_constant=lambda _: need(False, "PERSISTED_NONFINITE"))
    except (UnicodeError, ValueError, TypeError) as ex:
        raise CampaignDenied("FORGE_CKAD_PERSISTED_INVALID_JSON") from ex
    need(type(d) is dict and canonical(d) == raw, "PERSISTED_NONCANONICAL")
    return d


def audit_persisted_ckad25(manifest_raw, files, *, repository, commit, tree):
    """Validate committed exact-source checkpoint lineage; no writes or model calls.

    The returned digest is suitable for read-only development continuity,
    NOT execution, scientific first-use, live training admission, or promotion.
    """
    need(repository == SOURCE_REPO and commit == SNAPSHOT_COMMIT
         and tree == SNAPSHOT_TREE, "UNAUTHENTICATED_REPOSITORY_COMMIT")
    manifest = _json(manifest_raw)
    need(set(manifest) == MANIFEST_FIELDS and manifest["schema"] == SCHEMA
         and manifest["original_source_sha"] == ORIGINAL_SOURCE
         and manifest["original_source_tree"] == ORIGINAL_TREE
         and type(manifest["github_run_id"]) is int
         and manifest["github_run_id"] == RUN_ID
         and all(manifest[k] is False for k in
                 ("scientific_first_use", "scientific_pass", "accepted_native",
                  "forge_dispatch_authorized")),
         "PERSISTED_SOURCE_OR_AUTHORITY")
    need(type(files) is dict and set(files) == PATHS
         and type(manifest["all_platform_files_sha256"]) is dict
         and set(manifest["all_platform_files_sha256"]) == PATHS,
         "PERSISTED_INVENTORY_MISMATCH")
    for path in PATHS:
        raw = files[path]
        need(type(raw) is bytes and 0 < len(raw) <= 16_777_216
             and digest(raw) == manifest["all_platform_files_sha256"][path],
             "PERSISTED_FILE_HASH_MISMATCH")
    for path in FILES - {"stage-01.receipt.json", "stage-02.receipt.json"}:
        need(files["linux/"+path] == files["windows/"+path],
             "CROSS_PLATFORM_LEARNED_BYTES_DRIFT")
    result = _json(files["linux/campaign-result.json"])
    need(digest(files["linux/campaign-result.json"]) ==
         manifest["campaign_result_sha256"]
         and result.get("source_repo") == SOURCE_REPO
         and result.get("source_sha") == ORIGINAL_SOURCE
         and result.get("source_tree") == ORIGINAL_TREE
         and result.get("stages_completed") == 2
         and result.get("evaluations_completed") == 1
         and result.get("observations") == 12
         and result.get("interventions") == 0
         and result.get("held_total") == 4
         and result.get("held_answered") == 0
         and result.get("held_correct") == 0
         and result.get("scientific_pass") is False
         and result.get("forge_dispatch_authorized") is False
         and result.get("accepted_native") is False,
         "PERSISTED_CAMPAIGN_NOT_QUALIFIED")
    prior = files["linux/initial.native.json"]
    need(digest(prior) == result["initial_checkpoint_sha256"],
         "PERSISTED_INITIAL_CHECKPOINT")
    previous_stable = None
    for stage in (1, 2):
        prefix = "stage-0" + str(stage)
        nxt = files["linux/"+prefix+".native.json"]
        packet = files["linux/"+prefix+".packet.json"]
        for platform in ("linux", "windows"):
            receipt = _json(files[platform+"/"+prefix+".receipt.json"])
            need(receipt.get("source_commit") == ORIGINAL_SOURCE
                 and receipt.get("source_tree") == ORIGINAL_TREE
                 and receipt.get("stage_index") == stage-1
                 and receipt.get("input_checkpoint_sha256") == digest(prior)
                 and receipt.get("output_checkpoint_sha256") == digest(nxt)
                 and receipt.get("packet_sha256") == digest(packet)
                 and receipt.get("parent_receipt_sha256") == previous_stable
                 and receipt.get("native_cold_restore_verified") is True
                 and receipt.get("scientific_first_use") is False
                 and receipt.get("scientific_pass") is False
                 and receipt.get("forge_dispatch_authorized") is False,
                 "PERSISTED_STAGE_CHAIN_MISMATCH")
            stable = dict(receipt)
            stable.pop("wall_milliseconds", None)
            stable.pop("stable_receipt_sha256", None)
            need(digest(canonical(stable)) == receipt.get("stable_receipt_sha256")
                 and receipt.get("stable_receipt_sha256") == result["receipts"][stage-1],
                 "PERSISTED_RECEIPT_DIGEST_MISMATCH")
        inspect_native_checkpoint(nxt)
        previous_stable, prior = result["receipts"][stage-1], nxt
    inspect_native_checkpoint(files["linux/initial.native.json"])
    final = digest(prior)
    need(final == result["final_checkpoint_sha256"]
         and final == manifest["final_checkpoint_sha256"]
         and digest(files["linux/evaluation.json"]) == result["evaluation_sha256"],
         "PERSISTED_FINAL_OR_EVALUATION_DRIFT")
    evaluation = _json(files["linux/evaluation.json"])
    metric = evaluation.get("metrics", {})
    need(evaluation.get("checkpoint_sha256") == final
         and evaluation.get("scientific_pass") is False
         and evaluation.get("independent_science") is False
         and metric.get("held") == 4
         and metric.get("answered") == 0
         and metric.get("correct") == 0,
         "PERSISTED_SCIENCE_NEGATIVE_MUST_REMAIN")
    return {
        "schema": "forge.ckad.read-only-persisted-source-qualification.v1",
        "source_snapshot_commit": SNAPSHOT_COMMIT,
        "source_snapshot_tree": SNAPSHOT_TREE,
        "manifest_sha256": digest(manifest_raw),
        "source_owner_origin_sha": ORIGINAL_SOURCE,
        "final_checkpoint_sha256": final,
        "stages_verified_from_committed_files": 2,
        "platform_files_verified": 18,
        "cross_platform_checkpoint_bytes_equal": True,
        "scientific_pass": False, "held_answered": 0, "held_total": 4,
        "training_execution_authorized": False,
        "owner_permit_verified": False,
        "original_first_use_authorized": False,
        "forge_dispatch_authorized": False,
    }

"""Non-mutating V41 source-bound release-preflight evidence join.

This is NOT a production installer, signed release, owner task lease, source
transition permit, scientific first-use, or Hybrid admission. A V40 owner
must continue unchanged until a separately qualified deployment exists.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from f139.nci04_native_contract import canonical, digest
from f139 import nci04_v41_offline_cold_bundle as offline
from f139 import nci04_v41_owner_approval as approval
from f139 import nci04_v41_source_transition as source


SCHEMA = "forge.f139.v41.source-bound-release-preflight-dev.v1"
REPO = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
RUN_NAMES = frozenset((
    "FORGE public Linux and Windows qualification",
    "FORGE F73 protected-main cryptographic origin (no science permission)",
))


class V41ReleasePreflightDenied(ValueError):
    pass


def need(valid, code):
    if not valid:
        raise V41ReleasePreflightDenied("F139_V41_RELEASE_PREFLIGHT_" + code)


def _sha(value, width):
    return type(value) is str and (
        SHA40 if width == 40 else SHA64).fullmatch(value) is not None


def _get(get, path):
    need(callable(get) and type(path) is str
         and path.startswith("repos/" + REPO + "/"),
         "GET_SCOPE_DENIED")
    response = get(path)
    need(type(response) is dict, "GET_RESPONSE_INVALID")
    return response


def _remote_source(get, *, target, release_pr):
    """Read twice; never infer release identity from untrusted CI text."""
    prefix = "repos/" + REPO + "/"
    main = _get(get, prefix + "branches/main")
    release = _get(get, prefix + "branches/f139-owner-release-" + target)
    commit = _get(get, prefix + "git/commits/" + target)
    pr = _get(get, prefix + "pulls/" + str(release_pr))
    runs = _get(get, prefix + "actions/runs?head_sha=" + target
                + "&event=push&branch=main&per_page=30")

    need(main.get("protected") is True
         and main.get("commit", {}).get("sha") == target
         and release.get("name") == "f139-owner-release-" + target
         and release.get("protected") is True
         and release.get("commit", {}).get("sha") == target,
         "IMMUTABLE_RELEASE_REF_OR_MAIN_MISSING")
    need(commit.get("sha") == target
         and _sha(commit.get("tree", {}).get("sha"), 40),
         "TARGET_COMMIT_TREE_MISSING")
    need(pr.get("number") == release_pr
         and pr.get("merged") is True
         and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == target
         and pr.get("base", {}).get("ref") == "main"
         and pr.get("user", {}).get("login") == OWNER
         and pr.get("head", {}).get("sha")
         and _sha(pr["head"]["sha"], 40),
         "OWNER_MERGED_PR_IDENTITY_DRIFT")
    catalog = runs.get("workflow_runs")
    need(type(catalog) is list and len(catalog) <= 30,
         "EXACT_RUN_CATALOG_REQUIRED")
    selected = {}
    for name in RUN_NAMES:
        matching = [r for r in catalog
                    if type(r) is dict and r.get("name") == name
                    and r.get("head_sha") == target
                    and r.get("head_branch") == "main"
                    and r.get("event") == "push"]
        need(len(matching) == 1
             and type(matching[0].get("id")) is int
             and matching[0]["id"] > 0
             and matching[0].get("status") == "completed"
             and matching[0].get("conclusion") == "success"
             and matching[0].get("run_attempt") == 1
             and matching[0].get("actor", {}).get("login") == OWNER,
             "QUALIFIED_EXACT_SOURCE_FIRST_ATTEMPT_REQUIRED")
        selected[name] = matching[0]["id"]
    return {
        "source_sha": target,
        "tree_sha": commit["tree"]["sha"],
        "release_ref": release["name"],
        "owner_pr_number": release_pr,
        "qualified_runs": selected,
    }


def qualify_inert_release_preflight(
        get, bundle_root, *, target, release_pr,
        backup_run_id, sealed_manifest_sha256,
        original_head_seq, original_head_sha256,
        cold_receipt, pending_receipt, owner_comment_id):
    """Join independently sealed offline backup with authentic remote custody.

    This function only GETs repository evidence and reads an offline bundle.
    It does not edit a ref, emit a release permit or write original owner
    SQLite. The future original owner installer must independently require
    disabled owner task, SID, lease, source-bound executable and activation.
    """
    need(_sha(target, 40) and target != source.FROM_V40
         and type(release_pr) is int and release_pr > 0
         and type(backup_run_id) is int and backup_run_id > 0
         and type(owner_comment_id) is int and owner_comment_id > 0
         and type(original_head_seq) is int and original_head_seq > 0
         and _sha(original_head_sha256, 64)
         and _sha(sealed_manifest_sha256, 64),
         "EXACT_IDENTITY_INPUTS_REQUIRED")
    approval._receipts(cold_receipt, pending_receipt, target)
    need(cold_receipt["original_head_seq"] == original_head_seq
         and cold_receipt["original_head_sha256"] == original_head_sha256,
         "ORIGINAL_HEAD_MISMATCH")
    bundle_root = Path(bundle_root)
    need(bundle_root.is_absolute()
         and bundle_root.name == "f139-v41-before-" + str(backup_run_id),
         "CANONICAL_OFFLINE_BUNDLE_PATH_REQUIRED")
    restored = offline.verify_sealed_bundle_offline(
        bundle_root,
        expected_manifest_sha256=sealed_manifest_sha256,
        target=target, run_id=backup_run_id,
        expected_head_seq=original_head_seq,
        expected_head_sha256=original_head_sha256)
    need(type(restored) is dict
         and restored.get("independent_restore_verified") is True
         and restored.get("original_source_sha") == source.FROM_V40
         and restored.get("target_source_sha") == target
         and restored.get("original_head_seq") == original_head_seq
         and restored.get("original_head_sha256") == original_head_sha256
         and restored.get("manifest_sha256") == sealed_manifest_sha256
         and restored.get("release_qualified") is False
         and restored.get("source_transition_authorized") is False
         and restored.get("scientific_first_use") is False
         and restored.get("hybrid_admission") is False,
         "INDEPENDENT_RESTORE_RECEIPT_DRIFT")
    manifest_path = bundle_root / "manifest.sha256.json"
    manifest_bytes = manifest_path.read_bytes()
    need(digest(manifest_bytes) == sealed_manifest_sha256,
         "MANIFEST_CHANGED_AFTER_RESTORE")
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeError, ValueError) as exc:
        raise V41ReleasePreflightDenied(
            "F139_V41_RELEASE_PREFLIGHT_MANIFEST_UNREADABLE") from exc
    need(type(manifest) is dict and canonical(manifest) == manifest_bytes
         and manifest.get("schema") == offline.SCHEMA
         and manifest.get("run_id") == backup_run_id
         and manifest.get("original_source_sha") == source.FROM_V40
         and manifest.get("target_source_sha") == target
         and manifest.get("original_head_seq") == original_head_seq
         and manifest.get("original_head_sha256") == original_head_sha256
         and type(manifest.get("files_sha256")) is dict
         and manifest["files_sha256"].get("state.sqlite") ==
             cold_receipt["backup_sha256"]
         and manifest.get("logical_all_tables_sha256") ==
             cold_receipt["logical_all_tables_sha256"]
         and manifest.get("provider_archives_manifest_sha256") ==
             cold_receipt["provider_archives_manifest_sha256"]
         and manifest.get("generation_binary_manifest_sha256") ==
             cold_receipt["generation_binary_manifest_sha256"],
         "BACKUP_AND_COLD_RECEIPT_BINDING_DRIFT")

    first = _remote_source(get, target=target, release_pr=release_pr)
    intent = approval.verify_owner_comment(
        get, target=target, cold=cold_receipt,
        pending_receipt=pending_receipt, comment_id=owner_comment_id)
    need(type(intent) is dict
         and intent.get("schema") == approval.RECEIPT
         and intent.get("original_source_sha") == source.FROM_V40
         and intent.get("target_source_sha") == target
         and intent.get("owner_comment_id") == owner_comment_id
         and intent.get("owner_comment_identity_verified") is True
         and intent.get("pending_disposition_requested") == "EXPLICIT_ESCROW_ONCE"
         and intent.get("pending_disposition_implemented") is False
         and intent.get("original_owner_release_qualified") is False
         and intent.get("source_transition_authorized") is False
         and intent.get("reissue_authorized") is False
         and intent.get("scientific_first_use") is False
         and intent.get("hybrid_admission") is False
         and intent.get("owner_mutations") == 0
         and intent.get("new_dispatches") == 0,
         "OWNER_INTENT_NOT_A_RELEASE_PERMIT")
    second = _remote_source(get, target=target, release_pr=release_pr)
    need(first == second
         and digest(manifest_path.read_bytes()) == sealed_manifest_sha256,
         "REMOTE_OR_OFFLINE_CHANGED_DURING_READ")
    return {
        "schema": SCHEMA,
        "source_sha": target,
        "original_source_sha": source.FROM_V40,
        "source_tree_sha": first["tree_sha"],
        "release_ref": first["release_ref"],
        "release_pr_number": release_pr,
        "exact_first_attempt_ci_runs": first["qualified_runs"],
        "backup_run_id": backup_run_id,
        "sealed_manifest_sha256": sealed_manifest_sha256,
        "original_head_seq": original_head_seq,
        "original_head_sha256": original_head_sha256,
        "pending_1715_escrow_intent_verified": True,
        "owner_comment_id": owner_comment_id,
        "owner_comment_body_sha256": intent["owner_comment_body_sha256"],
        "independent_restore_verified": True,
        "candidate_inputs_readonly_qualified": True,
        "original_owner_installed": False,
        "source_transition_authorized": False,
        "release_qualified": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
        "owner_mutations": 0,
        "remote_writes": 0,
    }

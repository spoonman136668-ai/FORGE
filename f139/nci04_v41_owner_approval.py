"""Inert V41 original-owner approval/custody verifier.

A canonical GitHub OWNER comment is evidence of a proposed scoped decision,
not a task lease, signed release, first-use permission, or migration command.
This module only GETs/read-verifies. No CLI, writes, scheduler or dispatch.
"""
from __future__ import annotations

import json
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import decode_unique, BODY_KEYS, SCHEMA as ISSUE_SCHEMA, KIND as ISSUE_KIND, LABEL as ISSUE_LABEL
from f139 import nci04_v41_catalog_recovery_preflight as source
from f139 import nci04_v41_cold_copy_verifier as coldcopy
from f139 import nci04_v41_pending_custody as pending

REPO = "spoonman136668-ai/FORGE"
PREFIX = "F139-V41-OWNER-APPROVAL "
SCHEMA = "forge.f139.v41.owner-approval-intent.v1"
RECEIPT = "forge.f139.v41.owner-approval-readonly.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
COLD_KEYS = frozenset({
    "schema", "source_sha", "candidate_sha", "original_head_seq",
    "original_head_sha256", "backup_sha256",
    "verified_isolated_snapshot_sha256", "logical_all_tables_sha256",
    "provider_archives_manifest_sha256", "generation_binary_manifest_sha256",
    "preserved_verified_tasks", "preserved_quarantined_tasks",
    "original_owner_mutations", "source_transition_authorized",
    "new_dispatches", "scientific_first_use", "hybrid_admission",
})
FIELDS = frozenset({
    "schema", "owner_comment_id", "from_source_sha", "to_source_sha",
    "to_source_tree_sha", "original_head_seq", "original_head_sha256",
    "cold_backup_sha256", "logical_all_tables_sha256",
    "provider_archives_manifest_sha256", "generation_binary_manifest_sha256",
    "pending_issue_number", "pending_issue_id", "pending_ticket",
    "pending_semantic_identity_sha256", "pending_disposition",
    "pending_disposition_receipt_sha256", "qualification_run_id",
    "qualification_artifact_id", "qualification_artifact_sha256",
    "original_task_definition_sha256", "original_owner_sid_sha256",
    "owner_source_transition", "owner_policy_source_update",
    "pause_resume_existing_task", "create_immutable_release_ref",
    "scientific_first_use", "hybrid_admission", "new_controller",
    "new_scheduler", "new_queue", "paid_model_calls",
})
OWNER_ACTIONS = ("owner_source_transition", "owner_policy_source_update",
                 "pause_resume_existing_task", "create_immutable_release_ref")
DENIED_ACTIONS = ("scientific_first_use", "hybrid_admission",
                  "new_controller", "new_scheduler", "new_queue")


class V41ApprovalDenied(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise V41ApprovalDenied("F139_V41_APPROVAL_" + reason)


def _sha(value, width):
    return type(value) is str and (SHA40 if width == 40 else SHA64).fullmatch(value) is not None


def _receipts(cold, pending_receipt, target):
    """Check exact prior typed receipt identities; does not mint them."""
    need(type(cold) is dict and set(cold) == COLD_KEYS
         and cold["schema"] == "forge.f139.v41.original-owner-cold-copy-readonly.v1"
         and cold["source_sha"] == source.OWNER_SOURCE
         and cold["candidate_sha"] == target
         and _sha(target, 40)
         and type(cold["original_head_seq"]) is int
         and cold["original_head_seq"] >= source.OBSERVED_SEQ
         and all(_sha(cold[k], 64) for k in (
             "original_head_sha256", "backup_sha256",
             "verified_isolated_snapshot_sha256", "logical_all_tables_sha256",
             "provider_archives_manifest_sha256", "generation_binary_manifest_sha256"))
         and cold["backup_sha256"] == cold["verified_isolated_snapshot_sha256"]
         and type(cold["preserved_verified_tasks"]) is int
         and cold["preserved_verified_tasks"] >= 153
         and type(cold["preserved_quarantined_tasks"]) is int
         and cold["preserved_quarantined_tasks"] == 56
         and cold["original_owner_mutations"] == 0
         and cold["new_dispatches"] == 0
         and cold["source_transition_authorized"] is False
         and cold["scientific_first_use"] is False
         and cold["hybrid_admission"] is False, "COLD_CUSTODY_DRIFT")
    need(type(pending_receipt) is dict
         and set(pending_receipt) == pending.FROZEN_KEYS
         and pending_receipt["schema"] == pending.SCHEMA
         and pending_receipt["source_sha"] == source.OWNER_SOURCE
         and pending_receipt["original_head_seq"] == cold["original_head_seq"]
         and pending_receipt["original_head_sha256"] == cold["original_head_sha256"]
         and pending_receipt["issue_number"] == pending.PENDING_NUMBER
         and type(pending_receipt["issue_id"]) is int
         and pending_receipt["issue_id"] > 0
         and type(pending_receipt["ticket"]) is str
         and re.fullmatch("f139-nci04-i1715-" + source.OWNER_SOURCE[:12] + "-[a-f0-9]{8}", pending_receipt["ticket"]) is not None
         and all(_sha(pending_receipt[k], 64) for k in (
             "issue_body_sha256", "native_intent_sha256",
             "semantic_identity_sha256"))
         and all(_sha(pending_receipt[k], 40) for k in (
             "target_commit", "target_tree_sha"))
         and pending_receipt["disposition"] == "UNADMITTED_RETAINED_NO_DISPATCH"
         and pending_receipt["source_transition_authorized"] is False
         and pending_receipt["reissue_authorized"] is False
         and pending_receipt["new_dispatches"] == 0
         and pending_receipt["owner_mutations"] == 0
         and pending_receipt["scientific_first_use"] is False,
         "PENDING_1715_CUSTODY_DRIFT")


def _decode(body, comment_id, cold, pending_receipt, target, target_tree):
    need(type(body) is str and 0 < len(body) <= 6000
         and body.startswith(PREFIX), "CANONICAL_COMMENT_REQUIRED")
    try:
        doc = json.loads(body[len(PREFIX):])
    except (TypeError, ValueError, UnicodeError) as exc:
        raise V41ApprovalDenied("F139_V41_APPROVAL_JSON_INVALID") from exc
    need(type(doc) is dict and set(doc) == FIELDS
         and body == PREFIX + canonical(doc).decode("ascii"),
         "EXACT_FIELDS_OR_CANONICAL_BYTES")
    pairs = (
        ("owner_comment_id", comment_id),
        ("from_source_sha", source.OWNER_SOURCE),
        ("to_source_sha", target),
        ("to_source_tree_sha", target_tree),
        ("original_head_seq", cold["original_head_seq"]),
        ("original_head_sha256", cold["original_head_sha256"]),
        ("cold_backup_sha256", cold["backup_sha256"]),
        ("logical_all_tables_sha256", cold["logical_all_tables_sha256"]),
        ("provider_archives_manifest_sha256",
         cold["provider_archives_manifest_sha256"]),
        ("generation_binary_manifest_sha256",
         cold["generation_binary_manifest_sha256"]),
        ("pending_issue_number", pending_receipt["issue_number"]),
        ("pending_issue_id", pending_receipt["issue_id"]),
        ("pending_ticket", pending_receipt["ticket"]),
        ("pending_semantic_identity_sha256",
         pending_receipt["semantic_identity_sha256"]),
    )
    need(doc["schema"] == SCHEMA
         and all(type(doc[key]) is type(expected) and doc[key] == expected
                 for key, expected in pairs)
         and type(doc["qualification_run_id"]) is int
         and doc["qualification_run_id"] > 0
         and type(doc["qualification_artifact_id"]) is int
         and doc["qualification_artifact_id"] > 0
         and all(_sha(doc[k], 64) and doc[k] != "0" * 64 for k in (
             "pending_disposition_receipt_sha256",
             "qualification_artifact_sha256",
             "original_task_definition_sha256", "original_owner_sid_sha256"))
         and doc["pending_disposition"] in
             ("EXPLICIT_QUARANTINE_ONCE", "EXPLICIT_ESCROW_ONCE")
         and all(doc[k] is True for k in OWNER_ACTIONS)
         and all(doc[k] is False for k in DENIED_ACTIONS)
         and type(doc["paid_model_calls"]) is int
         and doc["paid_model_calls"] == 0, "SCOPE_SOURCE_OR_CUSTODY_DRIFT")
    return doc


def verify_owner_comment(get, *, target, cold, pending_receipt, comment_id):
    """Authenticate an owner-authored intent twice; never authorize a cutover.

    Only the original scoped owner, not CI or this function, can approve a
    later actual release. The supplied receipts must be produced by the
    exact original read-only verifiers under the genuine Windows owner mutex.
    """
    need(callable(get) and _sha(target, 40)
         and target != source.OWNER_SOURCE
         and type(comment_id) is int and comment_id > 0,
         "INPUT_OR_COMMENT_INVALID")
    _receipts(cold, pending_receipt, target)
    prefix = "repos/" + REPO + "/"
    def read(route):
        need(type(route) is str and route.startswith(prefix),
             "GET_SCOPE_DENIED")
        result = get(route)
        need(type(result) is dict, "GET_RESPONSE_INVALID")
        return result

    def evidence():
        main = read(prefix + "branches/main")
        policy = read(prefix + "issues/807")
        commit = read(prefix + "git/commits/" + target)
        comment = read(prefix + "issues/comments/" + str(comment_id))
        issue = read(prefix + "issues/" + str(pending.PENDING_NUMBER))
        need(main.get("protected") is True and
             main.get("commit", {}).get("sha") == target,
             "PROTECTED_MAIN_DRIFT")
        need(commit.get("sha") == target
             and _sha(commit.get("tree", {}).get("sha"), 40),
             "TARGET_COMMIT_OR_TREE_DRIFT")
        need(policy.get("state") == "open"
             and policy.get("number") == 807
             and policy.get("user", {}).get("login") == "spoonman136668-ai"
             and policy.get("author_association") == "OWNER",
             "ORIGINAL_POLICY_OWNER_DRIFT")
        try:
            pdoc = json.loads(policy.get("body"))
        except (TypeError, ValueError, UnicodeError) as exc:
            raise V41ApprovalDenied("F139_V41_APPROVAL_POLICY_JSON") from exc
        need(type(pdoc) is dict and pdoc.get("enabled") is True
             and pdoc.get("source_sha") == source.OWNER_SOURCE
             and pdoc.get("lanes") == ["Wingless", "Yggdrasil"]
             and pdoc.get("scientific_first_use") is False
             and pdoc.get("paid_model_calls") == 0,
             "ORIGINAL_V40_POLICY_DRIFT")
        need(comment.get("id") == comment_id
             and comment.get("issue_url") ==
                 "https://api.github.com/" + prefix + "issues/807"
             and comment.get("user", {}).get("login") ==
                 "spoonman136668-ai"
             and comment.get("author_association") == "OWNER",
             "OWNER_COMMENT_IDENTITY_DRIFT")
        need(issue.get("state") == "open" and not issue.get("pull_request")
             and issue.get("number") == pending.PENDING_NUMBER
             and issue.get("id") == pending_receipt["issue_id"]
             and issue.get("user", {}).get("login") == "spoonman136668-ai"
             and issue.get("author_association") == "OWNER"
             and isinstance(issue.get("labels"), list)
             and ISSUE_LABEL in [
                 label.get("name") for label in issue["labels"]
                 if isinstance(label, dict)],
             "PENDING_1715_REMOTE_IDENTITY_DRIFT")
        try:
            body = json.loads(issue.get("body"), object_pairs_hook=decode_unique)
        except (TypeError, ValueError, UnicodeError) as exc:
            raise V41ApprovalDenied("F139_V41_APPROVAL_PENDING_1715_JSON") from exc
        need(type(body) is dict and set(body) == BODY_KEYS
             and body.get("schema") == ISSUE_SCHEMA
             and body.get("kind") == ISSUE_KIND
             and body.get("source_sha") == source.OWNER_SOURCE
             and body.get("lane") == "Yggdrasil"
             and body.get("scientific_first_use") is False
             and body.get("paid_model_calls") == 0
             and digest(canonical(body)) == pending_receipt["issue_body_sha256"],
             "PENDING_1715_BODY_CHANGED")
        doc = _decode(comment.get("body"), comment_id, cold, pending_receipt,
                      target, commit["tree"]["sha"])
        return (main["commit"]["sha"], policy["body"], comment["body"],
                comment.get("updated_at"), commit["tree"]["sha"],
                digest(canonical(body)), issue.get("updated_at")), doc

    first, doc = evidence()
    second, again = evidence()
    need(first == second and doc == again,
         "CHANGED_DURING_DOUBLE_READ")
    return {
        "schema": RECEIPT,
        "original_source_sha": source.OWNER_SOURCE,
        "target_source_sha": target,
        "owner_comment_id": comment_id,
        "owner_comment_body_sha256": digest(first[2].encode("ascii")),
        "original_head_seq": cold["original_head_seq"],
        "original_head_sha256": cold["original_head_sha256"],
        "pending_issue_number": pending.PENDING_NUMBER,
        "pending_disposition_requested": doc["pending_disposition"],
        "pending_disposition_implemented": False,
        "original_owner_release_qualified": False,
        "owner_comment_identity_verified": True,
        "provider_reads_only": True,
        "remote_writes": 0,
        "owner_mutations": 0,
        "new_dispatches": 0,
        "source_transition_authorized": False,
        "reissue_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
    }


def inspect_locked_original(original, backup, get, api, *, target,
                            run_id, backup_sha256, owner_comment_id):
    """Only end-to-end entry: authenticate actual V40 under original mutex.

    No ability to issue an approval, create an escrow, rewrite #1715, install
    a source, touch the owner database, or dispatch a model. Synthetic tests
    of the pure comparison are not original-host acceptance evidence.
    """
    before = original.meta().copy()
    changes = original.conn.total_changes
    cold = coldcopy.verify_cold_copy(
        original, backup, get, target=target, run_id=run_id,
        expected_backup_sha256=backup_sha256)
    preserved = pending.inspect_never_admitted(original, api)
    receipt = verify_owner_comment(
        get, target=target, cold=cold, pending_receipt=preserved,
        comment_id=owner_comment_id)
    need(original.meta() == before and original.conn.total_changes == changes,
         "ORIGINAL_CHANGED_DURING_APPROVAL_READ")
    return receipt

"""Data-only native candidate proposal preparation for the existing F139 intake.

This code does not authenticate GitHub sources, create issues, label eligible
work, dispatch tasks, mutate Git refs, execute candidate bytes, or grant science.
The caller must independently fetch and authenticate target commit/tree and
file bytes, then an owner-authenticated issue must pass inspect_owner_issue.
"""
from __future__ import annotations

import base64

from f139.nci04_native_contract import (
    SCHEMA as INTENT_SCHEMA, REPOS, canonical, digest, parse_intent,
)
from f139.nci04_owner_issue import SCHEMA as ISSUE_SCHEMA, KIND


class ProposalPreparationError(ValueError):
    pass


def prepare_proposal(*, controller_source_sha: str, lane: str,
                     target_commit: str, target_tree_sha: str,
                     path: str, before: bytes, after: bytes,
                     dependency_sha256: str, qualification_harness_sha256: str,
                     training_config_sha256: str, suite_identity_sha256: str,
                     toolchain_identity: str) -> dict:
    """Return a bounded owner-review *proposal*, never an eligible work item.

    The hashes, commit/tree, and source file must be independently authenticated
    by the caller. This function only constructs and verifies canonical bytes;
    it intentionally has no filesystem, subprocess, network, or GitHub I/O.
    """
    if (not isinstance(lane, str) or lane not in REPOS
            or not isinstance(before, bytes) or not isinstance(after, bytes)):
        raise ProposalPreparationError("NATIVE_PROPOSAL_SOURCE_INPUT_INVALID")
    if not before or before == after:
        raise ProposalPreparationError("NATIVE_PROPOSAL_SOURCE_UNCHANGED")
    value = {
        "schema": INTENT_SCHEMA,
        "controller_source_sha": controller_source_sha,
        "lane": lane,
        "target_repository": REPOS[lane][0],
        "target_commit": target_commit,
        "target_tree_sha": target_tree_sha,
        "dependency_sha256": dependency_sha256,
        "qualification_harness_sha256": qualification_harness_sha256,
        "training_config_sha256": training_config_sha256,
        "toolchain_identity": toolchain_identity,
        "suite_identity_sha256": suite_identity_sha256,
        "path": path,
        "before_sha256": digest(before),
        "after_sha256": digest(after),
        "after_base64": base64.b64encode(after).decode("ascii"),
        "worker_mode": "isolated-candidate-only",
        "scientific_first_use": False,
        "paid_api_calls": 0,
        "accepted_ref_mutations": 0,
        "optimizer_policy_mutations": 0,
        "protected_holdouts_accessed": 0,
    }
    raw = canonical(value)
    # Reuse the existing immutable V1 contract, without widening executable
    # paths, allowed tasks, candidate sizes or source-provenance requirements.
    candidate = parse_intent(
        raw, protected_main=controller_source_sha,
        target_commit=target_commit, target_tree_sha=target_tree_sha)
    issue = {
        "schema": ISSUE_SCHEMA,
        "source_sha": controller_source_sha,
        "lane": lane,
        "kind": KIND,
        "intent_base64": base64.b64encode(raw).decode("ascii"),
        "scientific_first_use": False,
        "paid_model_calls": 0,
    }
    issue_bytes = canonical(issue)
    if len(raw) > 44000 or len(issue_bytes) > 60000:
        raise ProposalPreparationError("NATIVE_PROPOSAL_ISSUE_TOO_LARGE")
    # Return a draft payload *only*. Owner authentication, GitHub creation,
    # eligibility labelling, historical dedupe and admission remain external.
    return {
        "issue_body": issue_bytes.decode("ascii"),
        "issue_body_sha256": digest(issue_bytes),
        "intent_sha256": candidate.intent_sha256,
        "qualification_key": candidate.qualification_key,
        "target_commit": candidate.target_commit,
        "target_tree_sha": candidate.target_tree_sha,
        "source_sha": controller_source_sha,
        "owner_issue_required": True,
        "eligible": False,
        "dispatch_authorized": False,
        "scientific_first_use": False,
    }

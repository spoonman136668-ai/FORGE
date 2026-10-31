"""Reusable validation for F139 model-free research lineage envelopes.

This verifies canonical self-consistency and owner-session cross-links only.
It never authenticates the cited artifacts or grants execution/science authority.
"""
from __future__ import annotations
import re
from f139.nci04_native_contract import canonical, digest

SHA64 = re.compile(r"[a-f0-9]{64}\Z")
LINEAGE_SCHEMA = "forge.f139.model-free-research-lineage.v1"
LINEAGE_FIELDS = frozenset({
    "schema", "controller_source_sha", "target_commit", "target_tree_sha",
    "lane", "path", "before_sha256", "after_sha256",
    "frontier_candidate_identity", "owner_candidate_identity",
    "mechanism_sha256", "frozen_split_sha256", "dependency_sha256",
    "qualification_harness_sha256", "suite_identity_sha256",
    "training_config_sha256", "toolchain_identity",
    "frontier_history_sha256", "owner_history_sha256",
    "native_intent_sha256", "native_qualification_key",
    "model_response_sha256", "scientific_first_use",
})


class ResearchLineageDenied(ValueError):
    pass


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise ResearchLineageDenied("F139_RESEARCH_LINEAGE_" + reason)


def validate_research_lineage(*, record: dict, declared_sha256: str,
                              model_response_sha256: str,
                              native_intent_sha256: str,
                              native_qualification_key: str,
                              after_sha256: str,
                              frontier_candidate_identity: str,
                              owner_candidate_identity: str,
                              controller_source_sha: str,
                              target_commit: str, target_tree_sha: str,
                              mechanism_sha256: str, frozen_split_sha256: str,
                              owner_history_sha256: str, before_sha256: str,
                              dependency_sha256: str,
                              qualification_harness_sha256: str,
                              suite_identity_sha256: str,
                              training_config_sha256: str,
                              frontier_history_sha256: str) -> dict:
    """Check exact shape, canonical digest, and independently supplied links."""
    _need(type(record) is dict and set(record) == LINEAGE_FIELDS,
          "FIELDS_INVALID")
    _need(type(declared_sha256) is str and SHA64.fullmatch(declared_sha256)
          and digest(canonical(record)) == declared_sha256, "DIGEST_INVALID")
    _need(record["schema"] == LINEAGE_SCHEMA
          and record["lane"] == "Yggdrasil"
          and record["path"] == "yggdrasil/public_causal_cells.py"
          and record["toolchain_identity"] == "python3.11.11"
          and record["scientific_first_use"] is False, "POLICY_INVALID")
    for key in ("controller_source_sha", "target_commit", "target_tree_sha"):
        _need(type(record[key]) is str
              and re.fullmatch(r"[a-f0-9]{40}", record[key]) is not None,
              "GIT_IDENTITY_INVALID_" + key.upper())
    for key in (
        "before_sha256", "after_sha256", "frontier_candidate_identity",
        "owner_candidate_identity", "mechanism_sha256", "frozen_split_sha256",
        "dependency_sha256", "qualification_harness_sha256",
        "suite_identity_sha256", "training_config_sha256",
        "frontier_history_sha256", "owner_history_sha256",
        "native_intent_sha256", "native_qualification_key",
        "model_response_sha256",
    ):
        _need(type(record[key]) is str and SHA64.fullmatch(record[key]) is not None,
              "HASH_INVALID_" + key.upper())
    expected = {
        "model_response_sha256": model_response_sha256,
        "native_intent_sha256": native_intent_sha256,
        "native_qualification_key": native_qualification_key,
        "after_sha256": after_sha256,
        "frontier_candidate_identity": frontier_candidate_identity,
        "owner_candidate_identity": owner_candidate_identity,
        "controller_source_sha": controller_source_sha,
        "target_commit": target_commit,
        "target_tree_sha": target_tree_sha,
        "mechanism_sha256": mechanism_sha256,
        "frozen_split_sha256": frozen_split_sha256,
        "owner_history_sha256": owner_history_sha256,
        "before_sha256": before_sha256,
        "dependency_sha256": dependency_sha256,
        "qualification_harness_sha256": qualification_harness_sha256,
        "suite_identity_sha256": suite_identity_sha256,
        "training_config_sha256": training_config_sha256,
        "frontier_history_sha256": frontier_history_sha256,
    }
    _need(all(record[key] == value for key, value in expected.items()),
          "RESPONSE_LINK_MISMATCH")
    return {
        "record": dict(record), "canonical_bytes": canonical(record),
        "sha256": declared_sha256, "self_consistency_verified": True,
        "source_identity_authenticated": False,
        "frozen_science_authenticated": False,
        "owner_history_authenticated": False,
        "scientific_first_use": False, "publication_authorized": False,
        "dispatch_authorized": False,
    }

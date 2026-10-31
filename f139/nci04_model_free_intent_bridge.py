"""H69 inert model-free proposal -> original NCI-04 V1 intent conversion.

Only serializes a deterministic proposal for independent original-owner review.
The caller MUST independently authenticate the source/tree, complete ledger,
scientific frozen split and all later owner-issued authorizations. This module
has no Git, provider, secret, SQLite, worker, scheduling or signing operations.
"""
from __future__ import annotations

import base64
import hashlib

from f139.nci04_model_free_frontier import digest, verify_proposal
from f139.nci04_model_free_grammar import generate
from f139.nci04_native_contract import (
    SCHEMA as NATIVE_SCHEMA, NativeContractError, canonical, parse_intent,
)

SCHEMA = "forge.f139.model-free-unsigned-native-intent-bridge.v1"


class BridgeDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise BridgeDenied("F139_H69_" + reason)


def build_unsigned_native_intents(*, controller_source_sha: str,
                                  target_commit: str, target_tree_sha: str,
                                  frozen_source_sha256: str, original: bytes,
                                  metadata: dict, complete_history: list[dict]) -> dict:
    """Produce at most one typed *unsigned* native V1 intent per research lane.

    Source and history authentication are external prerequisites, NOT outcomes
    of this encoder. The finite original grammar currently covers Yggdrasil.
    Native qualification keys intentionally do NOT attest the frozen split,
    mechanism, experiment preregistration or signed original owner history.
    """
    generated = generate(
        controller_source_sha=controller_source_sha,
        target_commit=target_commit, target_tree_sha=target_tree_sha,
        frozen_source_sha256=frozen_source_sha256, original=original,
        metadata=metadata, complete_history=complete_history)
    selected = generated["selected"]
    sources = generated["source_by_candidate_id"]
    need(len(selected) <= 1 and set(sources) ==
         {row["candidate_identity"] for row in selected}, "SELECTION_SCOPE")
    intents = []
    for row in selected:
        source = sources[row["candidate_identity"]]
        need(type(source) is bytes and 0 < len(source) <= 32768
             and hashlib.sha256(source).hexdigest() == row["after_sha256"],
             "GENERATED_BYTES_DRIFT")
        proposal = {
            "lane": row["lane"], "controller_source_sha": controller_source_sha,
            "target_commit": target_commit, "target_tree_sha": target_tree_sha,
            "path": row["path"], "before_sha256": frozen_source_sha256,
            "after_sha256": row["after_sha256"],
            "mechanism_sha256": row["mechanism_sha256"],
            "toolchain_identity": "python3.11.11",
            "scientific_first_use": False,
            "protected_holdouts_accessed": 0, "paid_model_calls": 0,
            "accepted_ref_mutations": 0, "optimizer_policy_mutations": 0,
            **metadata,
        }
        need(verify_proposal(proposal, controller_source_sha)
             ["candidate_identity"] == row["candidate_identity"],
             "FRONTIER_IDENTITY_DRIFT")
        intent = {
            "schema": NATIVE_SCHEMA,
            "controller_source_sha": controller_source_sha,
            "lane": "Yggdrasil",
            "target_repository": "spoonman136668-ai/Yggdrasil",
            "target_commit": target_commit,
            "target_tree_sha": target_tree_sha,
            "dependency_sha256": metadata["dependency_sha256"],
            "qualification_harness_sha256": metadata["qualification_harness_sha256"],
            "training_config_sha256": metadata["training_config_sha256"],
            "toolchain_identity": proposal["toolchain_identity"],
            "suite_identity_sha256": metadata["suite_identity_sha256"],
            "path": row["path"],
            "before_sha256": frozen_source_sha256,
            "after_sha256": row["after_sha256"],
            "after_base64": base64.b64encode(source).decode("ascii"),
            "worker_mode": "isolated-candidate-only",
            "scientific_first_use": False,
            "paid_api_calls": 0, "accepted_ref_mutations": 0,
            "optimizer_policy_mutations": 0, "protected_holdouts_accessed": 0,
        }
        raw = canonical(intent)
        try:
            parsed = parse_intent(
                raw, protected_main=controller_source_sha,
                target_commit=target_commit,
                target_tree_sha=target_tree_sha)
        except NativeContractError as exc:
            raise BridgeDenied("F139_H69_NATIVE_CONTRACT_REJECTED") from exc
        need(parsed.after_bytes == source
             and parsed.after_sha256 == row["after_sha256"]
             and parsed.before_sha256 == frozen_source_sha256
             and parsed.lane == row["lane"] and parsed.path == row["path"],
             "NATIVE_ROUND_TRIP_DRIFT")
        intents.append({
            "lane": row["lane"],
            "candidate_identity": row["candidate_identity"],
            "mechanism_sha256": row["mechanism_sha256"],
            "frozen_split_sha256": metadata["frozen_split_sha256"],
            "unsigned_intent_bytes": raw,
            "intent_sha256": parsed.intent_sha256,
            "native_qualification_key": parsed.qualification_key,
            "after_sha256": row["after_sha256"],
        })
    return {
        "schema": SCHEMA,
        "controller_source_sha": controller_source_sha,
        "candidate_catalog_sha256": generated["candidate_catalog_sha256"],
        "history_sha256": generated["history_sha256"],
        "selected": intents,
        "abstentions": generated["abstentions"],
        "source_identity_authenticated": False,
        "complete_owner_history_authenticated": False,
        "original_owner_signed": False,
        "native_qualification_accepted": False,
        "frozen_science_authenticated": False,
        "scientific_first_use": False,
        "dispatch_authorized": False,
        "publication_authorized": False,
        "accepted_ref_mutations": 0,
        "paid_model_calls": 0,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
    }

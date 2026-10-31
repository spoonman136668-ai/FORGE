"""H72 inert model-free candidate -> existing original-owner model proposal format.

Shadow translation only. Neither an original-owner request/response session nor
original SQLite/provider identities are authenticated by this module. The
original SingleOwner publisher remains exclusively responsible for once-only
remote writes and upstream source/owner custody; this code NEVER calls it.
"""
from __future__ import annotations

import hashlib
import re

from f139.nci04_autonomy_feed import _semantic_identities, candidate_identity
from f139.nci04_model_free_intent_bridge import build_unsigned_native_intents
from f139.nci04_model_proposal import SCHEMA as MODEL_SCHEMA, validate
from f139.nci04_native_contract import canonical, digest, parse_intent

SCHEMA = "forge.f139.model-free-owner-response-shadow.v1"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
QUESTION = "Can opt-in posterior smoothing change observed public-cost choice?"
HYPOTHESIS = ("A finite public-observation prior may alter action preference; "
              "no scientific improvement or unfamiliar transfer is claimed.")
CONTROL = ("Preserve the native default and compare public-cost decisions "
           "against equally informed resource-matched conventional controls.")


class OwnerResponseShadowDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OwnerResponseShadowDenied("F139_H72_" + reason)



from f139.nci04_research_lineage import (
    LINEAGE_FIELDS, LINEAGE_SCHEMA, ResearchLineageDenied,
    validate_research_lineage as _validate_research_lineage,
)


def validate_research_lineage(**kwargs):
    """Preserve the original shadow error contract over the shared validator."""
    try:
        return _validate_research_lineage(**kwargs)
    except ResearchLineageDenied as exc:
        raise OwnerResponseShadowDenied(str(exc).replace(
            "F139_RESEARCH_LINEAGE_", "F139_H72_RESEARCH_LINEAGE_")) from exc



def encode_owner_response_shadow(*, controller_source_sha: str,
                                 target_commit: str, target_tree_sha: str,
                                 frozen_source_sha256: str, original: bytes,
                                 metadata: dict, complete_history: list[dict],
                                 owner_history_sha256: str,
                                 owner_consumed_candidates: set[str],
                                 owner_consumed_after_hashes: set[str]) -> dict:
    """Do not conflate frontier IDs with original owner candidate identities.

    The caller must separately authenticate complete owner history, source,
    frozen scientific controls, and consumption sets from the *same* original
    owner epoch. This produces unsigned data for a future genuine SingleOwner
    publication preflight. NEVER pass it directly to V3 worker dispatch.
    """
    need(type(owner_history_sha256) is str
         and SHA64.fullmatch(owner_history_sha256) is not None,
         "OWNER_HISTORY_DIGEST_MISSING")
    need(type(owner_consumed_candidates) is set
         and type(owner_consumed_after_hashes) is set
         and len(owner_consumed_candidates) <= 10000
         and len(owner_consumed_after_hashes) <= 10000
         and all(type(x) is str and SHA64.fullmatch(x) is not None for x in
                 (owner_consumed_candidates | owner_consumed_after_hashes)),
         "OWNER_CONSUMPTION_SET_INVALID")
    expected_metadata = _semantic_identities(
        controller_source_sha, "Yggdrasil", target_tree_sha,
        "yggdrasil/public_causal_cells.py")
    need(type(metadata) is dict
         and set(metadata) == set(expected_metadata) | {"frozen_split_sha256"}
         and all(metadata.get(key) == value
                 for key, value in expected_metadata.items())
         and type(metadata.get("frozen_split_sha256")) is str
         and SHA64.fullmatch(metadata["frozen_split_sha256"]) is not None,
         "OWNER_SEMANTIC_IDENTITIES_MISMATCH")
    result = build_unsigned_native_intents(
        controller_source_sha=controller_source_sha,
        target_commit=target_commit, target_tree_sha=target_tree_sha,
        frozen_source_sha256=frozen_source_sha256, original=original,
        metadata=metadata, complete_history=complete_history)
    need(len(result["selected"]) <= 1 and
         result["publication_authorized"] is False and
         result["dispatch_authorized"] is False, "BRIDGE_AUTHORITY_DRIFT")
    responses = []
    for item in result["selected"]:
        candidate = parse_intent(
            item["unsigned_intent_bytes"],
            protected_main=controller_source_sha,
            target_commit=target_commit, target_tree_sha=target_tree_sha)
        need(candidate.before_sha256 == frozen_source_sha256
             and hashlib.sha256(original).hexdigest() == frozen_source_sha256
             and candidate.after_sha256 == item["after_sha256"]
             and candidate.path == "yggdrasil/public_causal_cells.py"
             and candidate.lane == "Yggdrasil",
             "ORIGINAL_SOURCE_OR_LANE_DRIFT")
        legacy_id = candidate_identity(
            candidate.lane, target_commit, candidate.path, candidate.after_sha256)
        need(legacy_id not in owner_consumed_candidates
             and candidate.after_sha256 not in owner_consumed_after_hashes,
             "ORIGINAL_OWNER_CONSUMED_NO_REPLAY")
        response = {
            "schema": MODEL_SCHEMA, "lane": candidate.lane,
            "target_commit": target_commit, "path": candidate.path,
            "history_sha256": owner_history_sha256,
            "question": QUESTION, "hypothesis": HYPOTHESIS, "control": CONTROL,
            "candidate_source": candidate.after_bytes.decode("utf-8", "strict"),
        }
        raw = canonical(response)
        checked = validate(
            raw, lane=candidate.lane, target_commit=target_commit,
            path=candidate.path, before=original,
            before_sha256=frozen_source_sha256,
            history_sha256=owner_history_sha256,
            consumed_candidates=owner_consumed_candidates,
            consumed_after_hashes=owner_consumed_after_hashes)
        need(checked["record"]["candidate_identity"] == legacy_id
             and checked["record"]["after_sha256"] == candidate.after_sha256
             and checked["candidate_source"] == candidate.after_bytes
             and checked["record"]["scientific_first_use"] is False
             and checked["record"]["publication_authorized"] is False,
             "OWNER_MODEL_FORMAT_ROUND_TRIP_DRIFT")
        # Advisory content-addressed scientific lineage only. Native V1
        # qualification_key does not include mechanism, frozen split, or owner
        # history; these bytes do not grant scientific or owner authority.
        lineage = {
            "schema": "forge.f139.model-free-research-lineage.v1",
            "controller_source_sha": controller_source_sha,
            "target_commit": target_commit,
            "target_tree_sha": target_tree_sha,
            "lane": candidate.lane,
            "path": candidate.path,
            "before_sha256": frozen_source_sha256,
            "after_sha256": item["after_sha256"],
            "frontier_candidate_identity": item["candidate_identity"],
            "owner_candidate_identity": legacy_id,
            "mechanism_sha256": item["mechanism_sha256"],
            "frozen_split_sha256": item["frozen_split_sha256"],
            "dependency_sha256": metadata["dependency_sha256"],
            "qualification_harness_sha256": metadata["qualification_harness_sha256"],
            "suite_identity_sha256": metadata["suite_identity_sha256"],
            "training_config_sha256": metadata["training_config_sha256"],
            "toolchain_identity": "python3.11.11",
            "frontier_history_sha256": result["history_sha256"],
            "owner_history_sha256": owner_history_sha256,
            "native_intent_sha256": item["intent_sha256"],
            "native_qualification_key": item["native_qualification_key"],
            "model_response_sha256": digest(raw),
            "scientific_first_use": False,
        }
        responses.append({
            "research_lineage_record": lineage,
            "research_lineage_sha256": digest(canonical(lineage)),
            "research_lineage_authenticated": False,
            "native_v1_scientific_lineage_bound": False,
            "frontier_candidate_identity": item["candidate_identity"],
            "owner_candidate_identity": legacy_id,
            "mechanism_sha256": item["mechanism_sha256"],
            "frozen_split_sha256": item["frozen_split_sha256"],
            "owner_history_sha256": owner_history_sha256,
            "model_response_bytes": raw,
            "model_response_sha256": digest(raw),
            "native_intent_sha256": item["intent_sha256"],
            "native_qualification_key": item["native_qualification_key"],
            "after_sha256": item["after_sha256"],
        })
    return {
        "schema": SCHEMA,
        "controller_source_sha": controller_source_sha,
        "selected": responses,
        "abstentions": result["abstentions"],
        "frontier_history_sha256": result["history_sha256"],
        "owner_history_sha256": owner_history_sha256,
        "source_identity_authenticated": False,
        "complete_owner_history_authenticated": False,
        "owner_consumption_sets_authenticated": False,
        "original_single_owner_witnessed": False,
        "original_owner_signed": False,
        "original_owner_publication_performed": False,
        "owner_v3_dispatch_authorized": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
        "new_controller": False,
        "new_scheduler": False,
        "new_queue": False,
    }

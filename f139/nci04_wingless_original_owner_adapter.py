"""Read-only original-F139 format adapter for a Wingless native source candidate.

Data-only seam between the existing Wingless source generator and original
owner model-response validator. No GitHub writes, new queue, model calls,
dispatch, source promotion, or scientific first use.
This draft parent has NOT passed original Wingless Atlas source acceptance.
"""
from __future__ import annotations

import re

from f139.nci04_model_proposal import SCHEMA as RESPONSE_SCHEMA, validate
from f139.nci04_native_contract import canonical, digest
from f139.nci04_wingless_source_producer import (
    LANE, PARENT, PATH, _blob, propose,
)

FROZEN_PARENT_BLOB = "a33a6b7b901d424b4d40721d920d5fbf199e2f9b"
REQUEST_SCHEMA = "forge.f139.model-request.v1"
SESSION_SCHEMA = "forge.f139.owner-model-session.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class WinglessOwnerAdapterDenied(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise WinglessOwnerAdapterDenied("F139_WINGLESS_OWNER_ADAPTER_" + reason)


def prepare_original_response(*, prepared: dict, historical_model_after: set[str],
                              original_git_blob_sha: str) -> dict:
    """Compile source-bound original model data WITHOUT publishing a PR.

    An actual original-owner caller must first obtain prepared via the
    existing nci04_model_owner_bridge.owner_request under SingleOwner.
    This function alone never authenticates a running owner.
    """
    require(type(prepared) is dict and set(prepared) == {
        "request", "session", "before", "consumed_candidates",
        "consumed_after_hashes",
    }, "INPUT_FIELDS")
    request, session, before = (
        prepared["request"], prepared["session"], prepared["before"])
    require(type(request) is dict and type(session) is dict
            and type(before) is bytes
            and type(prepared["consumed_candidates"]) is set
            and type(prepared["consumed_after_hashes"]) is set
            and type(historical_model_after) is set
            and len(historical_model_after) <= 10000
            and all(type(x) is str and SHA64.fullmatch(x)
                    for x in (historical_model_after |
                              prepared["consumed_after_hashes"] |
                              prepared["consumed_candidates"])),
            "SOURCE_OR_HISTORY_TYPES")
    require(set(session) == {
        "schema", "owner_head_seq", "owner_head_sha256",
        "request_sha256", "source_sha", "lane", "target_commit",
        "target_tree_sha", "path", "before_sha256", "history_sha256",
        "scientific_first_use", "publication_authorized",
    } and session["schema"] == SESSION_SCHEMA
            and type(session["owner_head_seq"]) is int
            and session["owner_head_seq"] > 0
            and type(session["owner_head_sha256"]) is str
            and SHA64.fullmatch(session["owner_head_sha256"]) is not None
            and type(session["source_sha"]) is str
            and SHA40.fullmatch(session["source_sha"]) is not None
            and type(session["target_tree_sha"]) is str
            and SHA40.fullmatch(session["target_tree_sha"]) is not None
            and session["lane"] == LANE
            and session["target_commit"] == PARENT
            and session["path"] == PATH
            and session["scientific_first_use"] is False
            and session["publication_authorized"] is False,
            "ORIGINAL_SESSION_BOUNDARY")
    require(request.get("schema") == REQUEST_SCHEMA
            and request.get("lane") == LANE
            and request.get("target_commit") == PARENT
            and request.get("path") == PATH
            and request.get("controller_source_sha") == session["source_sha"]
            and request.get("target_tree_sha") == session["target_tree_sha"]
            and request.get("before_sha256") == session["before_sha256"]
            and request.get("history_sha256") == session["history_sha256"]
            and request.get("scientific_first_use") is False
            and request.get("model_execution_authorized") is False
            and request.get("publication_authorized") is False
            and type(request.get("source")) is str
            and request["source"] == before.decode("utf-8", "strict")
            and digest(before) == session["before_sha256"]
            and digest(canonical(request)) == session["request_sha256"],
            "REQUEST_SOURCE_OR_HISTORY_DRIFT")
    require(original_git_blob_sha == FROZEN_PARENT_BLOB
            and _blob(before) == FROZEN_PARENT_BLOB,
            "FROZEN_GIT_BLOB_DRIFT")
    all_consumed = prepared["consumed_after_hashes"] | historical_model_after
    proposal = propose(
        lane=LANE, path=PATH, parent_commit=PARENT,
        before_bytes=before, verified_git_blob_sha=original_git_blob_sha,
        pinned_before_sha256=session["before_sha256"],
        owner_history_sha256=session["history_sha256"],
        consumed_mechanisms=set(), consumed_source_sha256=all_consumed,
        scientific_first_use=False,
    )
    response = canonical({
        "schema": RESPONSE_SCHEMA,
        "lane": LANE, "target_commit": PARENT,
        "path": PATH, "history_sha256": session["history_sha256"],
        "question": "Does learned action disagreement justify public probing?",
        "hypothesis": proposal["record"]["hypothesis"],
        "control": proposal["record"]["needed_controls"],
        "candidate_source": proposal["source"].decode("utf-8", "strict"),
    })
    checked = validate(
        response, lane=LANE, target_commit=PARENT, path=PATH,
        before=before, before_sha256=session["before_sha256"],
        history_sha256=session["history_sha256"],
        consumed_candidates=prepared["consumed_candidates"],
        consumed_after_hashes=all_consumed)
    require(checked["record"]["candidate_identity"] ==
            proposal["candidate_identity"]
            and checked["record"]["after_sha256"] ==
            proposal["record"]["after_sha256"],
            "EXISTING_MODEL_VALIDATOR_DRIFT")
    return {
        "raw_response": response,
        "original_session": session,
        "candidate_identity": proposal["candidate_identity"],
        "source_after_sha256": proposal["record"]["after_sha256"],
        "original_owner_authenticated": False,
        "original_source_atlas_qualified": False,
        "publication_authorized": False,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "paid_api_calls": 0,
        "source_pr": 389,
    }

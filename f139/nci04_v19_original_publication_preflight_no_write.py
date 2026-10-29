"""V19 read-only original-owner model draft preflight; NEVER writes Git/SQLite.

Recheck a previously original-cold-validated candidate and its exact public
parent against the existing original publication policy, no-replay history,
single-file native V1 contract and bounded branch/PR uniqueness witnesses.
Output remains data-only, not permission to call an existing writer.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_autonomy_feed import (
    _semantic_identities, candidate_identity,
)
from f139.nci04_candidate_publisher import (
    _verified_original, _sha1_blob,
)
from f139.nci04_free_reasoner_provider import (
    verify_anonymous_public_source,
)
from f139.nci04_model_owner_publication import (
    BRANCH, _publication_history, _unique_branch,
)
from f139.nci04_native_contract import (
    REPOS, digest, parse_intent,
)
from f139.nci04_proposal_compiler import prepare_proposal
from f139.nci04_v19_original_proposal_validation_custody import (
    KIND as VALIDATION_KIND, SCHEMA as VALIDATION_SCHEMA,
)
from f139.nci04_v19_original_one_post_handoff import (
    KIND as HANDOFF_KIND, SCHEMA as HANDOFF_SCHEMA,
)
from f139.nci04_v19_research_renewal_shadow import (
    ShadowDenied, is_sha64,
)

SCHEMA = "forge.f139.v19.original-draft-publication-preflight.v1"


def deny(code: str) -> None:
    raise ShadowDenied("F139_V19_DRAFT_PREFLIGHT_" + code)


def preflight_original_v19_candidate_without_writing(
    db: Database, *, validation_seq: int, validation_sha256: str,
    candidate_source: bytes, public_packet: dict,
    original_get: Callable[[str], object],
    public_reader: Callable[[str], dict],
    owner_witness: Callable[[], bool],
) -> dict:
    """Compile immutable owner draft intent; no original or GitHub mutation.

    The original SHA-linked validated candidate must be the exact current
    ledger head. The authenticated original owner and its fixed policy stay
    the only eventual publication authority (in a separate release gate).
    """
    if (type(db) is not Database
            or type(validation_seq) is not int or validation_seq <= 0
            or not is_sha64(validation_sha256)
            or type(candidate_source) is not bytes
            or not 0 < len(candidate_source) <= 32768
            or type(public_packet) is not dict
            or not callable(original_get) or not callable(public_reader)
            or not callable(owner_witness) or owner_witness() is not True
            or not SingleOwner.held(db.filename.with_suffix(".lock"))):
        deny("ORIGINAL_INPUT_OWNER_MUTEX_OR_WITNESS")
    db.verify()
    meta = db.meta().copy()
    if (meta["head_seq"] != validation_seq
            or meta["head_hash"] != validation_sha256):
        deny("VALIDATION_ALREADY_CONSUMED_OR_HEAD_MOVED")
    if (meta["enabled"] != 1 or meta["legacy_suspended"] != 1
            or db.ready() is not None or db.actives()):
        deny("ORIGINAL_OWNER_DISABLED_OR_BUSY")
    row = db.conn.execute(
        "SELECT kind,payload,sha FROM events WHERE seq=?",
        (validation_seq,)).fetchone()
    if (row is None or row["kind"] != VALIDATION_KIND
            or row["sha"] != validation_sha256):
        deny("VALIDATION_EVENT_FORGED")
    validated = json.loads(row["payload"])
    if (validated.get("schema") != VALIDATION_SCHEMA
            or validated["owner_source_sha"] != meta["source_sha"]
            or digest(candidate_source) != validated["source_after_sha256"]
            or candidate_identity(validated["lane"], validated["target_commit"],
                                  validated["native_path"],
                                  digest(candidate_source))
               != validated["candidate_identity"]):
        deny("MODEL_CANDIDATE_BYTES_OR_SOURCE_DRIFT")
    predecessor = db.conn.execute(
        "SELECT kind,payload FROM events WHERE seq=?",
        (validated["send_seq"] - 1,)).fetchone()
    if predecessor is None or predecessor["kind"] != HANDOFF_KIND:
        deny("ORIGINAL_HANDOFF_MISSING")
    handoff = json.loads(predecessor["payload"])
    if handoff.get("schema") != HANDOFF_SCHEMA:
        deny("ORIGINAL_HANDOFF_SCHEMA")
    if (public_packet.get("lane") != validated["lane"]
            or public_packet.get("target_commit") != validated["target_commit"]
            or public_packet.get("path") != validated["native_path"]
            or public_packet.get("target_tree_sha") != handoff["public_tree_sha"]
            or public_packet.get("before_sha256") != validated["source_before_sha256"]
            or public_packet.get("history_sha256") != validated["history_sha256"]):
        deny("VALIDATED_PUBLIC_SOURCE_SCOPE_DRIFT")
    if verify_anonymous_public_source(public_packet, public_reader) is not True:
        deny("TARGET_PUBLIC_SOURCE_NOT_AUTHENTIC")
    # Full original protected source + enabled owner policy. The public
    # source authentication alone does not give a model publication rights.
    _verified_original(original_get, source_sha=meta["source_sha"])
    parent = validated["target_commit"]
    lane = validated["lane"]
    path = validated["native_path"]
    repository = REPOS[lane][0]
    before = public_packet["public_source"].encode("utf-8")
    if (digest(before) != validated["source_before_sha256"]
            or digest(candidate_source) == digest(before)):
        deny("BEFORE_SOURCE_HASH_OR_NOOP")
    semantics = _semantic_identities(
        meta["source_sha"], lane, public_packet["target_tree_sha"], path)
    compiled = prepare_proposal(
        controller_source_sha=meta["source_sha"], lane=lane,
        target_commit=parent,
        target_tree_sha=public_packet["target_tree_sha"],
        path=path, before=before, after=candidate_source, **semantics)
    intent = json.loads(compiled["issue_body"])["intent_base64"]
    import base64
    native = parse_intent(
        base64.b64decode(intent, validate=True),
        protected_main=meta["source_sha"], target_commit=parent,
        target_tree_sha=public_packet["target_tree_sha"])
    if (native.lane != lane or native.path != path
            or native.before_sha256 != validated["source_before_sha256"]
            or native.after_sha256 != validated["source_after_sha256"]):
        deny("NATIVE_CONTRACT_OR_SOURCE_DRIFT")
    branch = ("f139/auto-model-" + ("w" if lane == "Wingless" else "y") +
              "-" + validated["candidate_identity"][:20] + "-" + parent[:12])
    if BRANCH.fullmatch(branch) is None:
        deny("ORIGINAL_BRANCH_NOT_EXACT")
    _publication_history(db, validated["candidate_identity"],
                         validated["source_after_sha256"])
    _unique_branch(original_get, repository, branch)
    # No remote result may have changed the original source or the owner
    # during preflight. A future writer must re-prove this separately before
    # placing its original MODEL_DRAFT_ATTEMPTED event.
    db.verify()
    if (db.meta() != meta or owner_witness() is not True
            or not SingleOwner.held(db.filename.with_suffix(".lock"))):
        deny("ORIGINAL_OWNER_MOVED_AFTER_PUBLICATION_PREFLIGHT")
    return {
        "schema": SCHEMA,
        "disposition": "SOURCE_AND_ORIGINAL_PUBLICATION_PREFLIGHT_ONLY",
        "original_validation_seq": validation_seq,
        "original_validation_sha256": validation_sha256,
        "original_owner_source_sha": meta["source_sha"],
        "owner_event_head_sha256": meta["head_hash"],
        "lane": lane, "repository": repository, "branch": branch,
        "target_commit": parent, "target_tree_sha": public_packet["target_tree_sha"],
        "path": path, "source_before_blob_sha1": _sha1_blob(before),
        "source_after_blob_sha1": _sha1_blob(candidate_source),
        "source_after_sha256": digest(candidate_source),
        "candidate_identity": validated["candidate_identity"],
        "compiled_intent_sha256": compiled["intent_sha256"],
        "compiled_qualification_key": compiled["qualification_key"],
        "owner_issue_required": True, "draft_only": True,
        "publication_authorized": False, "original_write_calls": 0,
        "provider_requests": 0, "paid_model_calls": 0,
        "worker_dispatched": False, "scientific_first_use": False,
        "accepted_ref_mutations": 0,
    }

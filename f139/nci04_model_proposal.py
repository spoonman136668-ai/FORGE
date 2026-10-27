"""Validate an untrusted model proposal for the existing F139 native feeder.

This is a data-only boundary. It does not invoke a model, read the owner
ledger, authenticate GitHub, publish a PR, dispatch a worker, or authorize
scientific first-use. The original owner must supply authenticated source and
history and separately bind these bytes to its existing publication protocol.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from typing import Any

from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_native_contract import REPOS, canonical, digest
from f139 import nci04_research_steering as steering

SCHEMA = "forge.f139.model-proposal.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}\Z")
FIELDS = frozenset({"schema", "lane", "target_commit", "path",
                    "history_sha256", "question", "hypothesis",
                    "control", "candidate_source"})


class ProposalDenied(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ProposalDenied("F139_MODEL_PROPOSAL_" + reason)


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def build_request(get, *, lane: str, target_commit: str, path: str,
                  before: bytes, before_sha256: str, history_sha256: str,
                  history: list[dict]) -> dict:
    """Build an advisory model input from pinned steering and owner-supplied history.

    The caller still authenticates the Git source and owner ledger. No model is
    invoked here; the source, history and steering are untrusted prompt data.
    """
    need(callable(get) and type(lane) is str and lane in REPOS and isinstance(target_commit, str)
         and SHA40.fullmatch(target_commit) is not None
         and isinstance(path, str) and PATH.fullmatch(path) is not None
         and all(part not in ("", ".", "..") and not part.startswith(".")
                 for part in path.split("/"))
         and path.startswith(REPOS[lane][1]) and path.endswith(REPOS[lane][2])
         and type(before) is bytes and 0 < len(before) <= 32768
         and isinstance(before_sha256, str) and SHA64.fullmatch(before_sha256)
         and digest(before) == before_sha256
         and isinstance(history_sha256, str) and SHA64.fullmatch(history_sha256),
         "REQUEST_SOURCE_OR_HISTORY_INVALID")
    need(type(history) is list and len(history) <= 100, "REQUEST_HISTORY_INVALID")
    seen = set()
    for item in history:
        need(type(item) is dict and set(item) == {"candidate_identity", "outcome", "summary"}
             and isinstance(item["candidate_identity"], str)
             and SHA64.fullmatch(item["candidate_identity"])
             and item["candidate_identity"] not in seen
             and type(item["outcome"]) is str
             and item["outcome"] in {"VERIFIED", "QUARANTINED", "INDETERMINATE",
                                     "NEGATIVE", "MIXED", "INVALID", "LIMITATION"}
             and type(item["summary"]) is str and len(item["summary"]) <= 300
             and not any(ord(c) < 32 for c in item["summary"]),
             "REQUEST_HISTORY_INVALID")
        seen.add(item["candidate_identity"])
    try:
        original = before.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise ProposalDenied("F139_MODEL_PROPOSAL_REQUEST_SOURCE_INVALID") from exc
    cache = {}
    def cached(route):
        if route not in cache:
            cache[route] = get(route)
        return cache[route]
    guidance = steering.read_approved_steering(cached)
    documents = {path: steering._read_one(cached, path, blob)
                 for path, blob in steering.DOCUMENTS}
    return {"schema": "forge.f139.model-request.v1", "lane": lane,
            "target_commit": target_commit, "path": path,
            "before_sha256": before_sha256, "source": original,
            "history_sha256": history_sha256, "history": [dict(item) for item in history],
            "steering_source_commit": guidance["source_commit"],
            "steering_manifest_sha256": guidance["manifest_sha256"],
            "steering_documents": documents,
            "scientific_first_use": False, "model_execution_authorized": False,
            "publication_authorized": False}


def validate(raw: bytes, *, lane: str, target_commit: str, path: str,
             before: bytes, before_sha256: str, history_sha256: str,
             consumed_candidates: set[str], consumed_after_hashes: set[str]) -> dict:
    """Return bounded candidate data, not an authorization or a novelty claim.

    History, parent and original bytes must come from independently verified
    owner custody. Output cannot select a different file, parent or history.
    """
    need(type(lane) is str and lane in REPOS and isinstance(target_commit, str)
         and SHA40.fullmatch(target_commit) is not None
         and isinstance(path, str) and PATH.fullmatch(path) is not None
         and all(part not in ("", ".", "..") and not part.startswith(".")
                 for part in path.split("/"))
         and path.startswith(REPOS[lane][1]) and path.endswith(REPOS[lane][2]),
         "TARGET_INVALID")
    need(type(before) is bytes and 0 < len(before) <= 32768
         and isinstance(before_sha256, str) and SHA64.fullmatch(before_sha256)
         and hashlib.sha256(before).hexdigest() == before_sha256
         and isinstance(history_sha256, str) and SHA64.fullmatch(history_sha256)
         and type(consumed_candidates) is set and type(consumed_after_hashes) is set
         and len(consumed_candidates) <= 10000 and len(consumed_after_hashes) <= 10000
         and all(isinstance(x, str) and SHA64.fullmatch(x)
                 for x in consumed_candidates | consumed_after_hashes),
         "SOURCE_OR_HISTORY_INVALID")
    need(type(raw) is bytes and 0 < len(raw) <= 60000, "RESPONSE_SIZE_INVALID")
    try:
        doc = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             ProposalDenied("F139_MODEL_PROPOSAL_NONFINITE_JSON")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ProposalDenied("F139_MODEL_PROPOSAL_INVALID_JSON") from exc
    need(type(doc) is dict and set(doc) == FIELDS and doc["schema"] == SCHEMA,
         "RESPONSE_SCHEMA_INVALID")
    need(doc["lane"] == lane and doc["target_commit"] == target_commit
         and doc["path"] == path and doc["history_sha256"] == history_sha256,
         "RESPONSE_BINDING_DRIFT")
    for key in ("question", "hypothesis", "control"):
        value = doc[key]
        need(type(value) is str and 1 <= len(value.strip()) <= 600
             and not any(ord(ch) < 32 for ch in value), "RESEARCH_TEXT_INVALID")
    need(type(doc["candidate_source"]) is str, "SOURCE_INVALID")
    try:
        after = doc["candidate_source"].encode("utf-8", "strict")
        if lane == "Yggdrasil":
            ast.parse(doc["candidate_source"], filename=path)
    except (UnicodeError, SyntaxError, ValueError, RecursionError) as exc:
        raise ProposalDenied("F139_MODEL_PROPOSAL_SOURCE_INVALID") from exc
    need(0 < len(after) <= 32768 and after != before and b"\x00" not in after,
         "SOURCE_SIZE_OR_CHANGE_INVALID")
    after_sha = digest(after)
    identity = candidate_identity(lane, target_commit, path, after_sha)
    need(identity not in consumed_candidates and after_sha not in consumed_after_hashes,
         "PREVIOUSLY_CONSUMED_NO_REPLAY")
    record = {"schema": SCHEMA, "lane": lane, "target_commit": target_commit,
              "path": path, "history_sha256": history_sha256,
              "before_sha256": before_sha256, "after_sha256": after_sha,
              "candidate_identity": identity, "question": doc["question"].strip(),
              "hypothesis": doc["hypothesis"].strip(), "control": doc["control"].strip(),
              "scientific_first_use": False, "publication_authorized": False}
    return {"record": record, "record_sha256": digest(canonical(record)),
            "candidate_source": after}

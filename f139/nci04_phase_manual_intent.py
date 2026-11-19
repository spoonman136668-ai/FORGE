"""Inert, owner-source-bound manual phase intent from GitHub issue-comment data.

The caller must independently fetch this single comment and issue #807 through
an authenticated provider while holding the ORIGINAL F139 owner boundary. The
caller must derive installed source, protected main, epoch, and consumed IDs from
independently verified owner state. This helper cannot authenticate GitHub
transport or commit to original SQLite: it only rejects malformed/mismatched
intent and returns a non-authoritative candidate. DO NOT wire to dispatch.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re

from f139.nci04_phase_steering import LANES, MODES

OWNER = "spoonman136668-ai"
OWNER_ID = 253477821
POLICY_ISSUE = 807
ISSUE_URL = "https://api.github.com/repos/spoonman136668-ai/FORGE/issues/807"
SCHEMA = "forge.f139.phase-manual-intent.v1"
PREFIX = "F139-STEER-V1 "
FIELDS = frozenset({"schema", "owner_source_sha", "owner_epoch", "mode", "lane"})
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
MAX_BODY = 512
MAX_CONSUMED = 100000


class ManualPhaseDenied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ManualPhaseDenied("F139_PHASE_MANUAL_" + reason)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManualPhaseDenied("F139_PHASE_MANUAL_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _utc_stamp(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def inspect_comment(*, comment: dict, installed_source_sha: str,
                    protected_main_sha: str, owner_epoch: int,
                    consumed_comment_ids: frozenset[int]) -> dict:
    """Parse one read-only candidate; no authority, acceptance or state changes.

    Replayed comments cannot be accepted if `consumed_comment_ids` is derived
    from the original append-only ledger. That derivation and actual atomic
    consumption are *not implemented* by this source-only helper.
    """
    require(type(installed_source_sha) is str
            and SHA40.fullmatch(installed_source_sha) is not None
            and type(protected_main_sha) is str
            and protected_main_sha == installed_source_sha
            and type(owner_epoch) is int and 1 <= owner_epoch < 2**31,
            "OWNER_SOURCE_OR_EPOCH_DRIFT")
    require(type(consumed_comment_ids) is frozenset
            and len(consumed_comment_ids) <= MAX_CONSUMED
            and all(type(x) is int and x > 0 for x in consumed_comment_ids),
            "CONSUMED_CUSTODY_INVALID")
    require(type(comment) is dict
            and type(comment.get("id")) is int and comment["id"] > 0
            and comment["id"] not in consumed_comment_ids
            and comment.get("issue_url") == ISSUE_URL
            and type(comment.get("user")) is dict
            and comment["user"].get("login") == OWNER
            and comment["user"].get("id") == OWNER_ID
            and comment.get("author_association") == "OWNER",
            "ISSUE_OR_COMMENT_OWNER_UNQUALIFIED")
    created = comment.get("created_at")
    require(_utc_stamp(created) and comment.get("updated_at") == created,
            "EDITED_OR_MALFORMED_COMMENT")
    body = comment.get("body")
    require(type(body) is str and len(body) <= MAX_BODY
            and body.startswith(PREFIX) and "\x00" not in body,
            "BODY_NOT_EXACT_INTENT")
    try:
        raw_body = body.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise ManualPhaseDenied("F139_PHASE_MANUAL_BODY_UTF8_INVALID") from exc
    require(len(raw_body) <= MAX_BODY, "BODY_NOT_EXACT_INTENT")
    try:
        payload = json.loads(body[len(PREFIX):], object_pairs_hook=_unique_object)
    except (ValueError, TypeError) as exc:
        raise ManualPhaseDenied("F139_PHASE_MANUAL_INVALID_JSON") from exc
    require(type(payload) is dict and set(payload) == FIELDS
            and payload["schema"] == SCHEMA
            and payload["owner_source_sha"] == installed_source_sha
            and type(payload["owner_epoch"]) is int
            and payload["owner_epoch"] == owner_epoch
            and type(payload["mode"]) is str and payload["mode"] in MODES,
            "INTENT_SCOPE_OR_SOURCE_DRIFT")
    mode, lane = payload["mode"], payload["lane"]
    require(lane is None or (type(lane) is str and lane in LANES),
            "INTENT_LANE_INVALID")
    require(mode not in ("HOLD", "SELF_IMPROVE") or lane is None,
            "INTENT_LANE_SCOPE_DRIFT")
    return {
        "schema": SCHEMA, "comment_id": comment["id"],
        "owner_source_sha": installed_source_sha, "owner_epoch": owner_epoch,
        "mode": mode, "lane": lane, "comment_created_at": created,
        "body_sha256": hashlib.sha256(raw_body).hexdigest(),
        "advisory_only": True, "owner_admitted": False,
        "dispatch_authorized": False, "scientific_first_use": False,
        "self_source_mutation": False, "checkpoint_mutation": False,
        "deployment_authorized": False, "accepted_ref_mutation": False,
    }

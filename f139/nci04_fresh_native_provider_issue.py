"""Read-only provider revalidation for a future fresh F139 Yggdrasil issue.

Only a negative preflight. Even an entirely valid result MUST NOT be used to
admit a task, sign a workflow, move a Windows owner, or authorize science.
Caller must separately cold-verify the activated fresh SQLite, original task
release, original consumed-history archive, and one current original owner.
No provider POST, local write, new controller, scheduler or queue is present.
"""
from __future__ import annotations

import re
from typing import Callable

from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_fresh_native_activation import (
    ACTIVATION_SCHEMA,
)
from f139.nci04_fresh_remote_floor import SCHEMA as FLOOR_SCHEMA
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSIONS_SCHEMA
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED, RECEIPT_SCHEMA as YGG_SCHEMA,
    preflight_new_yggdrasil_development_issue,
)
from f139.nci04_v59_owner_forward_readiness import SOURCE, HEAD_SEQ, HEAD_SHA256

FORGE = "repos/spoonman136668-ai/FORGE"
YGG = "repos/spoonman136668-ai/Yggdrasil"
API = "https://api.github.com/" + FORGE
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SCHEMA = "forge.f139.fresh-provider-issue-preflight-only.v1"


class FreshProviderIssueDenied(ValueError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise FreshProviderIssueDenied("F139_FRESH_ISSUE_" + code)


def _protected(get: Callable, root: str, expected: str) -> None:
    branch = get(root + "/branches/main")
    need(type(branch) is dict
         and branch.get("name") == "main"
         and branch.get("protected") is True
         and type(branch.get("commit")) is dict
         and branch["commit"].get("sha") == expected,
         "PROTECTED_MAIN_MOVED")


def _provider_issue(get: Callable, number: int) -> dict:
    doc = get(FORGE + "/issues/" + str(number))
    need(type(doc) is dict
         and type(doc.get("number")) is int
         and doc["number"] == number
         and type(doc.get("id")) is int and doc["id"] > 0
         and doc.get("repository_url") == API
         and doc.get("url") == API + "/issues/" + str(number),
         "ISSUE_PROVIDER_IDENTITY_INVALID")
    return doc


def inspect_fresh_provider_issue(
    *, activation: dict, remote_floor: dict, consumed: dict,
    yggdrasil_boundary: dict, issue_number: int,
    get: Callable[[str], object],
) -> dict:
    """Re-read one post-cutover provider issue and both accepted main refs.

    The local activation record and supplied receipts must already have been
    cold verified, not merely sourced from arbitrary files. The remote cutover
    floor is immutable at handoff, but is NOT an admission authority. A second
    provider read detects edits to the issue during this inspection. The
    function deliberately has no database, HMAC, dispatch or write surface.
    """
    need(callable(get)
         and type(issue_number) is int and issue_number > 0
         and type(activation) is dict
         and type(remote_floor) is dict
         and type(consumed) is dict
         and type(yggdrasil_boundary) is dict,
         "INPUT_NOT_VERIFIED")
    source = activation.get("source_sha")
    floor = remote_floor.get("remote_cutover_issue_number_floor")
    need(activation.get("schema") == ACTIVATION_SCHEMA
         and type(source) is str and SHA40.fullmatch(source) is not None
         and source != SOURCE
         and activation.get("original_source_sha") == SOURCE
         and activation.get("original_head_seq") == HEAD_SEQ
         and activation.get("original_head_sha256") == HEAD_SHA256
         and activation.get("development_only") is True
         and activation.get("scientific_first_use") is False
         and type(activation.get("paid_model_calls")) is int
         and activation["paid_model_calls"] == 0
         and activation.get("worker_dispatch_authorized") is False
         and activation.get("model_continuation_authorized") is False,
         "FRESH_ACTIVATION_RECORD_INVALID")
    need(remote_floor.get("schema") == FLOOR_SCHEMA
         and remote_floor.get("target_forge_source_sha") == source
         and remote_floor.get("original_source_sha") == SOURCE
         and remote_floor.get("original_head_seq") == HEAD_SEQ
         and remote_floor.get("original_head_sha256") == HEAD_SHA256
         and remote_floor.get("remote_cutover_issue_provider_verified") is True
         and remote_floor.get("fresh_activation_authorized") is False
         and remote_floor.get("issue_admission_authorized") is False
         and remote_floor.get("worker_dispatch_authorized") is False
         and type(floor) is int and floor > 0
         and activation.get("remote_issue_number_floor") == floor
         and activation.get("remote_cutover_receipt_sha256")
             == digest(canonical(remote_floor))
         and consumed.get("schema") == EXCLUSIONS_SCHEMA
         and consumed.get("source_sha") == SOURCE
         and consumed.get("original_head_seq") == HEAD_SEQ
         and consumed.get("original_head_sha256") == HEAD_SHA256
         and consumed.get("previous_work_replay_authorized") is False
         and consumed.get("fresh_activation_authorized") is False
         and remote_floor.get("consumed_exclusions_sha256")
             == digest(canonical(consumed))
         and activation.get("consumed_exclusions_sha256")
             == digest(canonical(consumed))
         and yggdrasil_boundary.get("schema") == YGG_SCHEMA
         and yggdrasil_boundary.get("accepted_main_source_sha") == ACCEPTED
         and activation.get("yggdrasil_research_boundary_sha256")
             == digest(canonical(yggdrasil_boundary)),
         "CUTOVER_RECEIPT_OR_HISTORY_DRIFT")
    need(type(consumed.get("old_issue_numbers")) is list
         and all(type(n) is int and n > 0
                 for n in consumed["old_issue_numbers"])
         and floor >= max(consumed["old_issue_numbers"], default=0)
         and issue_number > floor,
         "OLD_OR_PRE_CUTOVER_ISSUE")

    _protected(get, FORGE, source)
    _protected(get, YGG, ACCEPTED)
    committed = get(YGG + "/git/commits/" + ACCEPTED)
    need(type(committed) is dict
         and committed.get("sha") == ACCEPTED
         and type(committed.get("tree")) is dict
         and type(committed["tree"].get("sha")) is str
         and SHA40.fullmatch(committed["tree"]["sha"]) is not None,
         "ACCEPTED_YGGDRASIL_TREE_UNVERIFIED")
    first = _provider_issue(get, issue_number)
    need(type(first.get("created_at")) is str
         and type(remote_floor.get("remote_cutover_issue_created_at")) is str
         and first["created_at"] >= remote_floor["remote_cutover_issue_created_at"],
         "ISSUE_CREATION_PRECEDES_CUTOVER")
    native = inspect_owner_issue(
        first, protected_main=source,
        authenticated_target_commit=ACCEPTED,
        authenticated_target_tree=committed["tree"]["sha"])
    proof = preflight_new_yggdrasil_development_issue(
        native, controller_source_sha=source, consumed_history=consumed,
        research_boundary=yggdrasil_boundary,
        authenticated_remote_issue_floor=floor)
    need(proof.get("worker_dispatch_authorized") is False
         and proof.get("owner_activation_authorized") is False,
         "RESEARCH_PREFLIGHT_ESCALATION")
    second = _provider_issue(get, issue_number)
    need(canonical(first) == canonical(second),
         "ISSUE_CHANGED_DURING_PROVIDER_READ")
    _protected(get, FORGE, source)
    _protected(get, YGG, ACCEPTED)
    return {
        "schema": SCHEMA,
        "source_sha": source,
        "issue_number": native.number,
        "issue_id": native.issue_id,
        "ticket": native.ticket,
        "issue_body_sha256": native.issue_body_sha256,
        "native_intent_sha256": native.native_intent_sha256,
        "accepted_yggdrasil_source_sha": ACCEPTED,
        "accepted_yggdrasil_tree_sha": committed["tree"]["sha"],
        "remote_cutover_issue_number_floor": floor,
        "issue_provider_readback_twice": True,
        "source_refs_rechecked": True,
        "old_work_rejected_by_frozen_exclusions": True,
        "issue_admission_authorized": False,
        "worker_dispatch_authorized": False,
        "owner_task_rebind_authorized": False,
        "scientific_first_use": False,
        "model_continuation_authorized": False,
    }

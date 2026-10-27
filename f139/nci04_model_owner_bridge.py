"""Owner-locked, read-only bridge from F139's original history to model proposal data.

The caller MUST be the existing Windows SingleOwner holder and provide its
independent running-owner witness. No model invocation, queue, GitHub write,
worker dispatch, new controller, scientific first-use or ledger mutation occurs.
The response must be rechecked against a FRESH original owner snapshot before
it can even become non-authorizing proposal compiler input.
"""
from __future__ import annotations

import re
from typing import Callable

from f139.local_controller import Database
from f139.nci04_autonomy_feed import (
    FORGE_REPO, POLICY_ISSUE, _decode_content, _semantic_identities,
    candidate_identity_from_intent_base64, inspect_policy,
)
from f139.nci04_model_proposal import build_request, validate
from f139.nci04_native_contract import REPOS, PATH, digest, canonical, model_source_path_allowed
from f139.nci04_owner_ledger import native_events, verify_native_activation
from f139.nci04_proposal_compiler import prepare_proposal

SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
STAGES = frozenset({"READY", "START_RISK", "WAIT_PROVIDER", "VERIFIED", "QUARANTINED"})
MAX_HISTORY = 100
MAX_CONSUMED = 10000


class OwnerModelDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise OwnerModelDenied("F139_OWNER_MODEL_" + reason)


def owner_history(db: Database) -> dict:
    """Retain ALL consumed identities and negatives from verified original SQLite.

    Only the bounded selection is sent to the advisor. The complete consumed
    hash sets stay on the owner side for no-replay admission. If negative
    history exceeds the model's capacity, fail closed rather than erase it.
    """
    need(type(db) is Database, "ORIGINAL_DATABASE_REQUIRED")
    db.verify()
    meta = db.meta()
    need(isinstance(meta["head_hash"], str)
         and SHA64.fullmatch(meta["head_hash"]) is not None
         and type(meta["head_seq"]) is int and meta["head_seq"] > 0,
         "ORIGINAL_EVENT_HEAD_INVALID")
    originals = native_events(db)
    need(len(originals) <= MAX_CONSUMED, "HISTORY_CAPACITY_EXCEEDED")
    histories, candidates, after_hashes, full = [], set(), set(), []
    for event in originals:
        ticket = event["ticket"]
        task = db.conn.execute(
            "SELECT stage,source_sha,run_id,evidence_sha,quarantine_reason "
            "FROM tasks WHERE ticket=?", (ticket,)).fetchone()
        need(task is not None and task["source_sha"] == event["source_sha"]
             and task["stage"] in STAGES, "ORIGINAL_TASK_DRIFT")
        stage = task["stage"]
        if stage == "VERIFIED":
            need(type(task["run_id"]) is int and task["run_id"] > 0
                 and isinstance(task["evidence_sha"], str)
                 and SHA64.fullmatch(task["evidence_sha"]) is not None,
                 "VERIFIED_RECEIPT_MISSING")
        if stage == "QUARANTINED":
            need(isinstance(task["quarantine_reason"], str)
                 and bool(task["quarantine_reason"]), "NEGATIVE_REASON_MISSING")
        candidate = candidate_identity_from_intent_base64(
            event["native_intent_base64"])
        after = event["after_sha256"]
        need(candidate not in candidates
             and isinstance(after, str) and SHA64.fullmatch(after) is not None,
             "REPEATED_OR_INVALID_CANDIDATE")
        candidates.add(candidate)
        after_hashes.add(after)
        outcome = stage if stage in {"VERIFIED", "QUARANTINED"} else "INDETERMINATE"
        row = {"candidate_identity": candidate, "outcome": outcome,
               "summary": "Original owner issue #" + str(event["issue_number"]) +
                          " stage " + stage}
        histories.append(row)
        full.append({"candidate_identity": candidate, "after_sha256": after,
                     "outcome": outcome, "ticket": ticket})
    mandatory = [i for i, item in enumerate(histories)
                 if item["outcome"] != "VERIFIED"]
    need(len(mandatory) <= MAX_HISTORY, "NEGATIVE_HISTORY_TOO_LARGE")
    optional = [i for i, item in enumerate(histories)
                if item["outcome"] == "VERIFIED"]
    chosen = set(mandatory + optional[-(MAX_HISTORY-len(mandatory)):]
                 if len(mandatory) < MAX_HISTORY else mandatory)
    selected = [row for i, row in enumerate(histories) if i in chosen]
    history_sha = digest(canonical({
        "schema": "forge.f139.owner-model-retained-history.v1",
        "head_seq": meta["head_seq"], "head_hash": meta["head_hash"],
        "all_original_native_outcomes": full,
    }))
    return {"head_seq": meta["head_seq"], "head_hash": meta["head_hash"],
            "history_sha256": history_sha, "history": selected,
            "consumed_candidates": candidates,
            "consumed_after_hashes": after_hashes}


def owner_request(db: Database, get: Callable, steering_get: Callable, *,
                  source_sha: str, lane: str, target_commit: str, path: str,
                  owner_witness: Callable[[], bool]) -> dict:
    """Prepare owner-grounded read-only model input, NOT a model call or permit."""
    need(type(db) is Database and callable(get) and callable(steering_get)
         and callable(owner_witness) and owner_witness() is True,
         "ORIGINAL_WINDOWS_OWNER_WITNESS_REQUIRED")
    history = owner_history(db)
    meta = db.meta()
    need(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and verify_native_activation(db) is True
         and db.ready() is None and not db.actives()
         and meta["source_sha"] == source_sha
         and isinstance(source_sha, str) and SHA40.fullmatch(source_sha) is not None,
         "ORIGINAL_OWNER_NOT_IDLE_OR_ACTIVATED")
    policy = get("repos/" + FORGE_REPO + "/issues/" + str(POLICY_ISSUE))
    need(inspect_policy(policy, source_sha)["enabled"] is True,
         "ORIGINAL_FEED_POLICY_DISABLED")
    need(type(lane) is str and lane in REPOS
         and isinstance(target_commit, str)
         and SHA40.fullmatch(target_commit) is not None
         and isinstance(path, str) and PATH.fullmatch(path) is not None
         and not path.startswith("/") and "\\" not in path
         and all(part not in ("", ".", "..") and not part.startswith(".")
                 for part in path.split("/"))
         and model_source_path_allowed(lane, path),
         "TARGET_SCOPE_INVALID")
    repository = REPOS[lane][0]
    commit = get("repos/" + repository + "/git/commits/" + target_commit)
    need(isinstance(commit, dict) and commit.get("sha") == target_commit
         and isinstance(commit.get("tree"), dict)
         and isinstance(commit["tree"].get("sha"), str)
         and SHA40.fullmatch(commit["tree"]["sha"]) is not None,
         "TARGET_COMMIT_NOT_AUTHENTICATED")
    doc = get("repos/" + repository + "/contents/" + path + "?ref=" + target_commit)
    before, _ = _decode_content(doc)
    before_sha = digest(before)
    target_tree = commit["tree"]["sha"]
    request = build_request(
        steering_get, controller_source_sha=source_sha,
        lane=lane, target_commit=target_commit, target_tree_sha=target_tree,
        path=path, before=before, before_sha256=before_sha,
        history_sha256=history["history_sha256"], history=history["history"])
    session = {
        "schema": "forge.f139.owner-model-session.v1",
        "owner_head_seq": history["head_seq"],
        "owner_head_sha256": history["head_hash"],
        "request_sha256": digest(canonical(request)),
        "source_sha": source_sha, "lane": lane,
        "target_commit": target_commit, "target_tree_sha": target_tree,
        "path": path, "before_sha256": before_sha,
        "history_sha256": history["history_sha256"],
        "scientific_first_use": False,
        "publication_authorized": False,
    }
    return {"request": request, "session": session,
            "consumed_candidates": history["consumed_candidates"],
            "consumed_after_hashes": history["consumed_after_hashes"],
            "before": before}


def owner_response(db: Database, get: Callable, steering_get: Callable, *,
                   session: dict, raw_response: bytes,
                   owner_witness: Callable[[], bool]) -> dict:
    """Re-read original custody + source after model execution, then compile data.

    A stale request, changed negative, modified steering blob or moved target
    makes the response unusable. This deliberately does NOT publish its result.
    """
    need(type(session) is dict
         and set(session) == {"schema", "owner_head_seq", "owner_head_sha256",
                             "request_sha256", "source_sha", "lane",
                             "target_commit", "target_tree_sha", "path",
                             "before_sha256", "history_sha256",
                             "scientific_first_use", "publication_authorized"}
         and session["schema"] == "forge.f139.owner-model-session.v1"
         and session["scientific_first_use"] is False
         and session["publication_authorized"] is False,
         "SESSION_INVALID")
    current = owner_request(
        db, get, steering_get, source_sha=session["source_sha"],
        lane=session["lane"], target_commit=session["target_commit"],
        path=session["path"], owner_witness=owner_witness)
    need(current["session"] == session, "SESSION_STALE_OR_UNAUTHENTICATED")
    request, before = current["request"], current["before"]
    candidate = validate(
        raw_response, lane=session["lane"],
        target_commit=session["target_commit"], path=session["path"],
        before=before, before_sha256=session["before_sha256"],
        history_sha256=session["history_sha256"],
        consumed_candidates=current["consumed_candidates"],
        consumed_after_hashes=current["consumed_after_hashes"])
    semantics = _semantic_identities(
        session["source_sha"], session["lane"],
        session["target_tree_sha"], session["path"])
    proposal = prepare_proposal(
        controller_source_sha=session["source_sha"],
        lane=session["lane"], target_commit=session["target_commit"],
        target_tree_sha=session["target_tree_sha"],
        path=session["path"], before=before,
        after=candidate["candidate_source"], **semantics)
    need(proposal["owner_issue_required"] is True
         and proposal["eligible"] is False
         and proposal["dispatch_authorized"] is False
         and proposal["scientific_first_use"] is False,
         "COMPILER_AUTHORITY_DRIFT")
    return {"record": candidate["record"], "proposal": proposal,
            "request_sha256": session["request_sha256"],
            "scientific_first_use": False, "worker_dispatched": False,
            "publication_authorized": False}

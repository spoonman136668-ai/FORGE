"""Single-original-owner, once-only model draft publication using F139's existing GitHub path.

No independent model call, scheduler, queue, controller, scientific first-use,
or direct worker dispatch. Caller must hold the original SingleOwner mutex and
supply its running Windows-owner witness. An original SHA-linked attempt is
written BEFORE the first remote mutation; ambiguous writes are never replayed.
"""
from __future__ import annotations

import base64
import json
import re
from typing import Callable

from f139.local_controller import Database
from f139.nci04_autonomy_feed import (
    _candidate_from_pr, _decode_content, candidate_identity)
from f139.nci04_candidate_publisher import _sha1_blob, _verified_original
from f139.nci04_model_owner_bridge import owner_response
from f139.nci04_native_contract import REPOS, canonical, digest, parse_intent

ATTEMPT = "MODEL_DRAFT_ATTEMPTED"
SUCCESS = "MODEL_DRAFT_AUTHENTICATED"
SCHEMA = "forge.f139.owner-model-draft-publication.v1"
BRANCH = re.compile(r"f139/auto-model-[wy]-[a-f0-9]{20}-[a-f0-9]{12}\Z")


class ModelDraftDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ModelDraftDenied("F139_MODEL_DRAFT_" + reason)


def _publication_history(db: Database, candidate_id: str,
                         after_sha256: str) -> None:
    """Fail closed on any unresolved prior original-owner model write."""
    attempts, successes = {}, {}
    for row in db.conn.execute(
            "SELECT kind,payload FROM events WHERE kind IN (?,?) ORDER BY seq",
            (ATTEMPT, SUCCESS)):
        item = json.loads(row["payload"])
        need(type(item) is dict and item.get("schema") == SCHEMA
             and isinstance(item.get("candidate_identity"), str)
             and re.fullmatch(r"[a-f0-9]{64}", item["candidate_identity"]) is not None
             and isinstance(item.get("source_after_sha256"), str)
             and re.fullmatch(r"[a-f0-9]{64}", item["source_after_sha256"]) is not None
             and item.get("scientific_first_use") is False,
             "HISTORICAL_EVENT_INVALID")
        key = item["candidate_identity"]
        if row["kind"] == ATTEMPT:
            need(set(item) == {"schema", "candidate_identity", "source_after_sha256",
                               "source_sha", "parent_commit", "branch",
                               "prior_event_head_sha256", "scientific_first_use",
                               "retry_allowed"}, "ATTEMPT_FIELDS_INVALID")
            need(key not in attempts and item["retry_allowed"] is False
                 and isinstance(item["branch"], str)
                 and BRANCH.fullmatch(item["branch"]) is not None,
                 "ATTEMPT_DUPLICATE_OR_DRIFT")
            attempts[key] = item
        else:
            need(set(item) == {"schema", "candidate_identity", "source_after_sha256",
                               "pr_number", "head_commit", "scientific_first_use",
                               "worker_dispatched"}, "SUCCESS_FIELDS_INVALID")
            need(key in attempts and key not in successes
                 and item["source_after_sha256"] ==
                 attempts[key]["source_after_sha256"]
                 and item["worker_dispatched"] is False
                 and type(item["pr_number"]) is int and item["pr_number"] > 0
                 and isinstance(item["head_commit"], str)
                 and re.fullmatch(r"[a-f0-9]{40}", item["head_commit"]) is not None,
                 "SUCCESS_ORPHAN_OR_DRIFT")
            successes[key] = item
    # A remote ref/PR may have been created even if POST's response was lost.
    need(set(attempts) == set(successes), "UNRESOLVED_REMOTE_WRITE_NO_RETRY")
    need(candidate_id not in attempts and
         after_sha256 not in {v["source_after_sha256"] for v in attempts.values()},
         "PREVIOUSLY_ATTEMPTED_NO_REPLAY")
    g3 = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind='G3_DRAFT_ATTEMPTED'").fetchone()[0]
    g3_success = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind='G3_DRAFT_AUTHENTICATED'").fetchone()[0]
    need(g3 == g3_success, "UNRESOLVED_G3_REMOTE_WRITE")


def _unique_branch(get: Callable, repository: str, branch: str) -> None:
    # Exactly the bounded original G2 history scan. No ref or PR writes here.
    refs = get(f"repos/{repository}/git/matching-refs/heads/{branch}")
    need(type(refs) is list and len(refs) == 0, "REF_ALREADY_EXISTS")
    first, seen, previous = None, set(), None
    for page in range(1, 13):
        rows = get(f"repos/{repository}/pulls?state=all&per_page=100&page={page}")
        need(type(rows) is list and len(rows) <= 100, "PR_HISTORY_INVALID")
        identities = []
        for item in rows:
            need(type(item) is dict and type(item.get("number")) is int
                 and item["number"] > 0
                 and isinstance(item.get("head"), dict)
                 and isinstance(item["head"].get("ref"), str)
                 and bool(item["head"]["ref"]), "PR_HISTORY_ITEM_INVALID")
            num, ref = item["number"], item["head"]["ref"]
            need(num not in seen and (previous is None or num < previous),
                 "PR_HISTORY_CHANGED")
            seen.add(num)
            previous = num
            need(ref != branch, "PR_ALREADY_PUBLISHED")
            identities.append((num, ref))
        if first is None:
            first = identities
        if len(rows) < 100:
            fresh = get(f"repos/{repository}/pulls?state=all&per_page=100&page=1")
            need(type(fresh) is list and len(fresh) == len(first)
                 and all(type(row) is dict
                         and type(row.get("number")) is int
                         and isinstance(row.get("head"), dict)
                         and (row["number"], row["head"].get("ref")) == pair
                         for row, pair in zip(fresh, first)),
                 "PR_HISTORY_MOVED")
            return
    need(False, "PR_HISTORY_UNBOUNDED")


def _preflight(db: Database, get: Callable, steering_get: Callable,
               session: dict, raw_response: bytes, owner_witness: Callable) -> dict:
    need(type(db) is Database and callable(get) and callable(steering_get)
         and callable(owner_witness) and owner_witness() is True,
         "ORIGINAL_OWNER_WITNESS_REQUIRED")
    # Both source and original ledger are re-read; this rejects stale requests.
    outcome = owner_response(
        db, get, steering_get, session=session, raw_response=raw_response,
        owner_witness=owner_witness)
    note = outcome["record"]
    proposal = outcome["proposal"]
    source_sha = session["source_sha"]
    _verified_original(get, source_sha=source_sha)
    repository = REPOS[session["lane"]][0]
    path = session["path"]
    parent = session["target_commit"]
    before_doc = get(f"repos/{repository}/contents/{path}?ref={parent}")
    before, before_blob = _decode_content(before_doc)
    need(digest(before) == session["before_sha256"],
         "SOURCE_CHANGED_BEFORE_PUBLICATION")
    payload = json.loads(proposal["issue_body"])
    raw = base64.b64decode(payload["intent_base64"], validate=True)
    candidate = parse_intent(raw, protected_main=source_sha,
                             target_commit=parent,
                             target_tree_sha=session["target_tree_sha"])
    need(candidate.lane == session["lane"] and candidate.path == path
         and candidate.before_sha256 == session["before_sha256"]
         and candidate.after_sha256 == note["after_sha256"]
         and candidate_identity(candidate.lane, parent, path,
                                candidate.after_sha256) == note["candidate_identity"],
         "COMPILED_PROPOSAL_DRIFT")
    branch = ("f139/auto-model-" +
              ("w" if session["lane"] == "Wingless" else "y") + "-" +
              note["candidate_identity"][:20] + "-" + parent[:12])
    need(BRANCH.fullmatch(branch) is not None, "BRANCH_SCOPE_INVALID")
    _publication_history(db, note["candidate_identity"], note["after_sha256"])
    _unique_branch(get, repository, branch)
    document = {
        "schema": "forge.f139.owner-model-draft-note.v1",
        "question": note["question"], "hypothesis": note["hypothesis"],
        "control": note["control"],
        "history_sha256": session["history_sha256"],
        "candidate_identity": note["candidate_identity"],
        "scientific_first_use": False,
        "dispatch_authorized": False,
        "independent_scientific_acceptance": False,
    }
    title = ("F139 autonomy DEV: bounded " + session["lane"] +
             " learning proposal " + note["candidate_identity"][:12])
    result = {
        "schema": SCHEMA, "repository": repository,
        "lane": session["lane"], "path": path,
        "branch": branch, "source_sha": source_sha,
        "parent_commit": parent, "parent_tree": session["target_tree_sha"],
        "before_blob": before_blob,
        "after_blob": _sha1_blob(candidate.after_bytes),
        "source_after_sha256": note["after_sha256"],
        "candidate_identity": note["candidate_identity"],
        "candidate_source": candidate.after_bytes,
        "owner_head_sha256": session["owner_head_sha256"],
        "owner_head_seq": session["owner_head_seq"],
        "request_sha256": session["request_sha256"],
        "title": title, "body": canonical(document).decode("ascii"),
        "scientific_first_use": False, "writes_authorized": False,
    }
    return result


def _write_draft(get: Callable, write: Callable, plan: dict) -> dict:
    repository, branch, path = plan["repository"], plan["branch"], plan["path"]
    ref = "refs/heads/" + branch
    created = write("POST", f"repos/{repository}/git/refs", {
        "ref": ref, "sha": plan["parent_commit"]})
    need(type(created) is dict and created.get("ref") == ref
         and isinstance(created.get("object"), dict)
         and created["object"].get("sha") == plan["parent_commit"],
         "REF_RESPONSE_AMBIGUOUS_NO_RETRY")
    changed = write("PUT", f"repos/{repository}/contents/{path}", {
        "message": "F139 MODEL DEV: owner-validated isolated source candidate",
        "content": base64.b64encode(plan["candidate_source"]).decode("ascii"),
        "sha": plan["before_blob"], "branch": branch})
    need(type(changed) is dict
         and isinstance(changed.get("content"), dict)
         and changed["content"].get("sha") == plan["after_blob"]
         and isinstance(changed.get("commit"), dict)
         and isinstance(changed["commit"].get("sha"), str)
         and re.fullmatch(r"[a-f0-9]{40}", changed["commit"]["sha"]) is not None,
         "COMMIT_RESPONSE_AMBIGUOUS_NO_RETRY")
    head = changed["commit"]["sha"]
    delta = get(f"repos/{repository}/compare/{plan['parent_commit']}...{head}")
    files = delta.get("files") if type(delta) is dict else None
    need(type(delta) is dict and delta.get("status") == "ahead"
         and delta.get("ahead_by") == 1 and delta.get("behind_by") == 0
         and delta.get("total_commits") == 1
         and type(files) is list and len(files) == 1
         and files[0].get("filename") == path
         and files[0].get("status") == "modified"
         and files[0].get("sha") == plan["after_blob"],
         "EXACT_ONE_FILE_COMMIT_REQUIRED")
    pr = write("POST", f"repos/{repository}/pulls", {
        "title": plan["title"], "head": branch, "base": "main",
        "draft": True, "body": plan["body"]})
    need(type(pr) is dict and type(pr.get("number")) is int
         and pr["number"] > 0, "PR_RESPONSE_AMBIGUOUS_NO_RETRY")
    observed = get(f"repos/{repository}/pulls/{pr['number']}")
    need(type(observed) is dict and observed.get("state") == "open"
         and observed.get("draft") is True
         and observed.get("title") == plan["title"]
         and observed.get("body") == plan["body"]
         and observed.get("head", {}).get("sha") == head
         and observed.get("head", {}).get("ref") == branch
         and observed.get("user", {}).get("login") == "spoonman136668-ai"
         and observed.get("author_association") == "OWNER",
         "OWNER_DRAFT_NOT_AUTHENTICATED")
    authenticated = _candidate_from_pr(
        get, lane=plan["lane"], pr=observed, source_sha=plan["source_sha"])
    need(authenticated["candidate_identity"] == plan["candidate_identity"],
         "FEEDER_CANDIDATE_DRIFT")
    return {"pr_number": pr["number"], "head_commit": head}


def publish_model_once(db: Database, get: Callable, steering_get: Callable,
                       write: Callable, *, session: dict, raw_response: bytes,
                       owner_witness: Callable[[], bool]) -> dict:
    """Original-owner-only once-only publication, no running model or dispatch.

    Caller owns the original Windows SingleOwner lock throughout this call.
    This function MUST NOT be invoked by generic workflow runners. It creates
    an original owner custody event before the first GitHub write, so any
    ambiguous network result remains frozen until explicit reconciliation.
    """
    need(type(db) is Database and callable(get) and callable(steering_get)
         and callable(write) and callable(owner_witness)
         and owner_witness() is True,
         "ORIGINAL_WINDOWS_OWNER_REQUIRED")
    plan = _preflight(db, get, steering_get, session, raw_response, owner_witness)
    # Re-read Git and owner history just before freezing the immutable attempt.
    fresh = _preflight(db, get, steering_get, session, raw_response, owner_witness)
    need(fresh == plan, "PLAN_MOVED_BEFORE_CUSTODY")
    with db.transaction():
        db.verify()
        need(db.meta()["head_hash"] == plan["owner_head_sha256"]
             and db.meta()["head_seq"] == plan["owner_head_seq"]
             and db.ready() is None and not db.actives(),
             "PREWRITE_ORIGINAL_LEDGER_MOVED")
        _publication_history(db, plan["candidate_identity"],
                             plan["source_after_sha256"])
        db.event(ATTEMPT, {
            "schema": SCHEMA, "candidate_identity": plan["candidate_identity"],
            "source_after_sha256": plan["source_after_sha256"],
            "source_sha": plan["source_sha"],
            "parent_commit": plan["parent_commit"],
            "branch": plan["branch"],
            "prior_event_head_sha256": plan["owner_head_sha256"],
            "scientific_first_use": False, "retry_allowed": False,
        })
        db.verify()
    try:
        result = _write_draft(get, write, plan)
    except Exception:
        # May have created ref, source commit or PR. NO retry/replay.
        return {"disposition": "MODEL_DRAFT_REMOTE_AMBIGUOUS_NO_RETRY",
                "scientific_first_use": False, "worker_dispatched": False}
    with db.transaction():
        db.verify()
        _publication_rows = [
            json.loads(row["payload"]) for row in db.conn.execute(
                "SELECT payload FROM events WHERE kind=? ORDER BY seq", (ATTEMPT,))]
        need(_publication_rows and
             _publication_rows[-1]["candidate_identity"] ==
             plan["candidate_identity"], "ORIGINAL_ATTEMPT_CUSTODY_MOVED")
        db.event(SUCCESS, {
            "schema": SCHEMA, "candidate_identity": plan["candidate_identity"],
            "source_after_sha256": plan["source_after_sha256"],
            "pr_number": result["pr_number"],
            "head_commit": result["head_commit"],
            "scientific_first_use": False, "worker_dispatched": False,
        })
        db.verify()
    return {"disposition": "MODEL_DRAFT_AUTHENTICATED",
            "pr_number": result["pr_number"],
            "head_commit": result["head_commit"],
            "scientific_first_use": False, "worker_dispatched": False}

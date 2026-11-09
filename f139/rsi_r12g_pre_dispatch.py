"""R12-G: original-owner lifetime-one PRE-dispatch envelope and cold audit.

The R12-B/C design needs a GitHub run/job ID BEFORE workflow_dispatch,
which is impossible. This v2 source-only path seals an original R11
reservation *before* GitHub creates those IDs. Subsequent run/job identity
is observed separately. No owner tick, dispatch, credential-free worker,
deployment, first-use or promotion is connected here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3

from f139.local_controller import canonical
from f139.rsi_r11_owner_once import (
    KIND as RESERVATION_KIND, _authentic_original_owner,
    _source_at_event, audit_owner_once,
)
from f139.rsi_r12_candidate_binding import (
    binding_from_reservation_event, bind_original_candidate,
    original_owner_database,
)
from f139.rsi_r12b_signed_job import (
    LANE, REPO, WORKFLOW, RUNNER_OSES, valid_binding,
    sha40, sha64,
)
from f139.rsi_r12c_original_spend import (
    KIND as LEGACY_POSTDISPATCH_KIND, owner_self_policy_allows,
)
from f139.rsi_r6_provider_readback import Readback

KIND = "RSI_SELF_ORIGINAL_PREISSUED"
SCHEMA = "forge.f139.rsi-r12g.pre-dispatch-original-once.v1"
BUNDLE_SCHEMA = "forge.f139.rsi-r12g.pre-dispatch-intent.v1"
DOMAIN = b"FORGE-F139-RSI-ORIGINAL-PREDISPATCH-V1\n"
WORKER_PREFIX = "rsi-self-qualification"
FIELDS = frozenset({
    "schema", "owner_source_sha", "reservation_seq",
    "reservation_event_sha256", "binding_sha256", "intent",
    "intent_sha256", "signature_sha256", "prior_event_head_sha256",
    "lifetime_issue_limit", "retry_allowed", "development_only",
    "worker_run_id_unassigned", "worker_job_id_unassigned",
    "worker_dispatched", "credential_free_worker_admitted",
    "scientific_first_use", "source_promoted", "autonomous_rsi_proven",
})


class PreDispatchDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise PreDispatchDenied("F139_RSI_R12G_" + code)


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def prepare(*, binding: dict, source_sha: str, source_tree_sha: str,
            runner_os: str) -> dict:
    """Draft ONLY; no run ID exists yet, no original-owner authorization."""
    need(valid_binding(binding) and sha40(source_sha)
         and sha40(source_tree_sha)
         and type(runner_os) is str and runner_os in RUNNER_OSES,
         "PRE_DISPATCH_INPUT_OR_BINDING_INVALID")
    body = {
        "schema": BUNDLE_SCHEMA,
        "repository": REPO,
        "workflow": WORKFLOW,
        "lane": LANE,
        "source_sha": source_sha,
        "source_tree_sha": source_tree_sha,
        "owner_source_sha": binding["owner_source_sha"],
        "reservation_seq": binding["reservation_seq"],
        "reservation_event_sha256": binding["reservation_event_sha256"],
        "binding_sha256": binding["candidate_binding_sha256"],
        "failed_head_sha": binding["failed_head_sha"],
        "failed_run_id": binding["failed_run_id"],
        "failed_job_id": binding["failed_job_id"],
        "target_path": binding["target_path"],
        "before_sha256": binding["before_sha256"],
        "candidate_sha256": binding["candidate_sha256"],
        "task_scope_sha256": binding["task_scope_sha256"],
        "runner_os": runner_os,
        "retry_allowed": False,
        "development_only": True,
        "credential_free_worker_admitted": False,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }
    # Exactly one original R11 reservation -> exactly one deterministic
    # ticket per protected target and runner. Never reuse across source drift.
    return {**body, "ticket": "f139-rsi-" + digest(body)[:32]}


def validate_bundle(bundle: dict, binding: dict) -> None:
    need(type(bundle) is dict, "PREDISPATCH_BUNDLE_TYPE")
    expected = prepare(
        binding=binding,
        source_sha=bundle.get("source_sha"),
        source_tree_sha=bundle.get("source_tree_sha"),
        runner_os=bundle.get("runner_os"))
    need(bundle == expected and not any(
        key in bundle for key in (
            "worker_run_id", "worker_job_id", "worker_run_attempt")),
        "UNASSIGNED_GITHUB_IDS_OR_FIELDS_DRIFT")


def sign(secret: str, bundle: dict) -> str:
    """Domain-separated HMAC primitive; a test key is NOT original custody."""
    need(type(secret) is str
         and 32 <= len(secret.encode("utf-8")) <= 4096,
         "ORIGINAL_SIGNING_KEY_BOUNDS")
    return hmac.new(secret.encode("utf-8"),
                    DOMAIN + canonical(bundle), hashlib.sha256).hexdigest()


def event_payload(*, bundle: dict, signature: str,
                  binding: dict, prior_head: str) -> dict:
    validate_bundle(bundle, binding)
    need(sha64(signature) and sha64(prior_head),
         "SIGNATURE_OR_HEAD_SHAPE_INVALID")
    return {
        "schema": SCHEMA,
        "owner_source_sha": binding["owner_source_sha"],
        "reservation_seq": binding["reservation_seq"],
        "reservation_event_sha256": binding["reservation_event_sha256"],
        "binding_sha256": binding["candidate_binding_sha256"],
        "intent": bundle,
        "intent_sha256": digest(bundle),
        "signature_sha256": hashlib.sha256(
            signature.encode("ascii")).hexdigest(),
        "prior_event_head_sha256": prior_head,
        "lifetime_issue_limit": 1,
        "retry_allowed": False,
        "development_only": True,
        "worker_run_id_unassigned": True,
        "worker_job_id_unassigned": True,
        "worker_dispatched": False,
        "credential_free_worker_admitted": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }


def validate_event(*, payload: dict, row, binding: dict,
                   source_at_event: str) -> None:
    need(type(payload) is dict and set(payload) == FIELDS
         and payload["schema"] == SCHEMA and valid_binding(binding)
         and payload["owner_source_sha"] ==
             binding["owner_source_sha"] == source_at_event
         and payload["reservation_seq"] == binding["reservation_seq"]
         and payload["reservation_event_sha256"] ==
             binding["reservation_event_sha256"]
         and payload["binding_sha256"] == binding["candidate_binding_sha256"]
         and payload["intent_sha256"] == digest(payload["intent"])
         and sha64(payload["signature_sha256"])
         and payload["prior_event_head_sha256"] == row["prior_sha"]
         and type(row["seq"]) is int
         and row["seq"] > binding["reservation_seq"]
         and type(payload["lifetime_issue_limit"]) is int
         and payload["lifetime_issue_limit"] == 1
         and payload["retry_allowed"] is False
         and payload["development_only"] is True
         and payload["worker_run_id_unassigned"] is True
         and payload["worker_job_id_unassigned"] is True
         and all(payload[k] is False for k in (
             "worker_dispatched", "credential_free_worker_admitted",
             "scientific_first_use", "source_promoted",
             "autonomous_rsi_proven")),
         "ORIGINAL_PREISSUE_EVENT_OR_HISTORY_DRIFT")
    validate_bundle(payload["intent"], binding)


def audit_preissued(db) -> tuple[dict, ...]:
    """Cold verify one pre-issue against original R11 historic event and source."""
    need(original_owner_database(db), "ORIGINAL_DATABASE_REQUIRED")
    issues = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (KIND,)))
    if not issues:
        return ()
    need(len(issues) == 1, "LIFETIME_PREISSUE_ALREADY_SPENT")
    legacy = db.conn.execute(
        "SELECT COUNT(*) FROM events WHERE kind=?",
        (LEGACY_POSTDISPATCH_KIND,)).fetchone()[0]
    need(legacy == 0, "LEGACY_POSTDISPATCH_DOUBLE_ISSUANCE_DENIED")
    reserved = audit_owner_once(db)
    originals = list(db.conn.execute(
        "SELECT seq,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (RESERVATION_KIND,)))
    need(len(reserved) == len(originals) == 1,
         "ONE_AUTHENTIC_ORIGINAL_RESERVATION_REQUIRED")
    binding = binding_from_reservation_event(
        reservation=reserved[0], row=originals[0],
        expected_owner_source_sha=reserved[0]["owner_source_sha"])
    rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha "
        "FROM events ORDER BY seq"))
    transitions = [json.loads(row["payload"]) for row in rows
                   if row["kind"] == "SOURCE_TRANSITION_ADMITTED"]
    initial = transitions[0]["from_source_sha"] if transitions else db.meta()["source_sha"]
    for row, source in _source_at_event(rows, initial):
        if row["kind"] != KIND:
            continue
        payload = json.loads(row["payload"])
        validate_event(payload=payload, row=row, binding=binding,
                       source_at_event=source)
        return (payload,)
    need(False, "ORIGINAL_PREISSUE_EVENT_MISSING")
    return ()


def original_preissue_once(*, db, provider, candidate: Readback,
                           signing_key: str, protected_main_sha: str,
                           protected_tree_sha: str,
                           runner_os: str) -> tuple[dict, str]:
    """Future original-owner-only atomic PRE-dispatch spend. NOT called today.

    This source-only function does NOT invoke a workflow. It can only be
    called by a separately qualified installed original Windows owner after
    an operator-authenticated source transition and three-lane policy.
    """
    from f139.local_controller import SingleOwner
    source = _authentic_original_owner(
        db, provider, allow_used_reservation=True)
    need(type(candidate) is Readback and type(signing_key) is str
         and type(runner_os) is str and runner_os in RUNNER_OSES,
         "ORIGINAL_CANDIDATE_OR_SIGNER_REQUIRED")
    secret = os.environ.get("F139_WORKER_HMAC_KEY", "")
    need(len(secret) >= 32
         and hmac.compare_digest(secret, signing_key),
         "ORIGINAL_SIGNER_CUSTODY_DRIFT")
    need(len(audit_owner_once(db)) == 1
         and not audit_preissued(db),
         "LIFETIME_ORIGINAL_RESERVATION_OR_PREISSUE_INVALID")
    prefix = "repos/" + REPO + "/"
    policy_issue = provider.get(prefix + "issues/807")
    need(type(policy_issue) is dict
         and policy_issue.get("number") == 807
         and policy_issue.get("state") == "open"
         and type(policy_issue.get("user")) is dict
         and policy_issue["user"].get("login") == "spoonman136668-ai"
         and policy_issue.get("author_association") == "OWNER"
         and "pull_request" not in policy_issue
         and type(policy_issue.get("body")) is str,
         "ORIGINAL_OPERATOR_POLICY_IDENTITY_DRIFT")
    try:
        policy = json.loads(policy_issue["body"])
    except (ValueError, TypeError) as exc:
        raise PreDispatchDenied(
            "F139_RSI_R12G_OPERATOR_POLICY_UNREADABLE") from exc
    need(owner_self_policy_allows(
        policy, original_source_sha=source),
        "FORGE_SELF_NOT_YET_ACTIVATED_IN_ORIGINAL_OWNER_POLICY")
    need(sha40(protected_main_sha) and sha40(protected_tree_sha)
         and provider.protected_main() == protected_main_sha,
         "PROTECTED_MAIN_SOURCE_DRIFT")
    commit = provider.get(prefix + "git/commits/" + protected_main_sha)
    need(type(commit) is dict
         and commit.get("sha") == protected_main_sha
         and type(commit.get("tree")) is dict
         and commit["tree"].get("sha") == protected_tree_sha,
         "PROTECTED_MAIN_TREE_DRIFT")
    binding = bind_original_candidate(
        db=db, candidate=candidate,
        expected_owner_source_sha=source)
    envelope = prepare(
        binding=binding, source_sha=protected_main_sha,
        source_tree_sha=protected_tree_sha, runner_os=runner_os)
    signature = sign(signing_key, envelope)
    previous = db.meta()
    doc = event_payload(
        bundle=envelope, signature=signature,
        binding=binding, prior_head=previous["head_hash"])
    with db.transaction():
        db.verify()
        now = db.meta()
        need(now["head_hash"] == previous["head_hash"]
             and now["source_sha"] == source
             and now["enabled"] == 1
             and now["legacy_suspended"] == 1
             and not db.actives() and db.ready() is None
             and SingleOwner.held(db.filename.with_suffix(".lock"))
             and not audit_preissued(db),
             "OWNER_HEAD_OR_LIFETIME_ISSUE_CHANGED")
        db.event(KIND, doc)
        db.verify()
    # A valid HMAC alone is not worker admission. No dispatch occurs.
    return envelope, signature


def observe_provider_job(*, bundle: dict, run: dict, job: dict) -> dict:
    """READ-ONLY provider-shape check AFTER GitHub creates run and job IDs.

    GitHub's run API does not expose workflow_dispatch inputs. The run name
    alone is NOT proof the worker verified a secret or admitted the original
    owner. A separate credentialed authorization job is still required.
    """
    need(type(bundle) is dict and type(run) is dict and type(job) is dict,
         "PROVIDER_OBSERVATION_TYPE_INVALID")
    ident, label = run.get("id"), job.get("id")
    need(type(ident) is int and ident > bundle["failed_run_id"]
         and type(label) is int and label > 0
         and run.get("event") == "workflow_dispatch"
         and run.get("run_attempt") == 1
         and run.get("head_sha") == bundle["source_sha"]
         and run.get("head_branch") == "main"
         and run.get("name") == "F139 " + bundle["ticket"]
         and run.get("path") == ".github/workflows/" + WORKFLOW
         and run.get("status") in ("queued", "in_progress")
         and run.get("conclusion") is None
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == "spoonman136668-ai"
         and type(run.get("repository")) is dict
         and run["repository"].get("full_name") == REPO
         and type(run.get("head_repository")) is dict
         and run["head_repository"].get("full_name") == REPO
         and job.get("id") == label
         and job.get("run_id") == ident
         and job.get("head_sha") == bundle["source_sha"]
         and job.get("name") == WORKER_PREFIX + " (" + bundle["runner_os"] + ")"
         and job.get("labels") == [bundle["runner_os"]]
         and job.get("status") in ("queued", "in_progress")
         and job.get("conclusion") is None,
         "GITHUB_JOB_ORIGIN_UNVERIFIED")
    return {
        "schema": "forge.f139.rsi-r12g.post-dispatch-observation.v1",
        "run_id": ident,
        "job_id": label,
        "ticket": bundle["ticket"],
        "source_sha": bundle["source_sha"],
        "source_tree_sha": bundle["source_tree_sha"],
        "provider_origin_shape_matched": True,
        "original_owner_preissue_verified": False,
        "credentialed_worker_signature_verified": False,
        "credential_free_worker_admitted": False,
        "worker_dispatched_by_this_function": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }

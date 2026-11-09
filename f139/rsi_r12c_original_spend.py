"""R12-C: original-owner single-use FORGE-self job issuance ledger.

This SOURCE-ONLY gate does not modify owner tick, job worker, workflow,
scheduler, first-use custody or accepted code. Only an authenticated
installed Windows original owner may commit the one issuance event. The
current workflow contains no credential-free FORGE-self qualification job,
so a real issuance is presently impossible and must fail closed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os

from f139.local_controller import Database, GitHub, SingleOwner, canonical
from f139.rsi_r11_owner_once import (
    KIND as RESERVATION_KIND, audit_owner_once,
    _authentic_original_owner, _source_at_event,
)
from f139.rsi_r12_candidate_binding import (
    bind_original_candidate, binding_from_reservation_event,
)
from f139.rsi_r12b_signed_job import (
    prepare, validate_intent, valid_binding, sha64, sha40,
    _development_signature, WORKFLOW, REPO, RUNNER_OSES,
)
from f139.rsi_r6_provider_readback import Readback

KIND = "RSI_SELF_ORIGINAL_ISSUED"
SCHEMA = "forge.f139.rsi-r12c.original-owner-lifetime-one-issuance.v1"
# Not present in current workflow. Never reinterpret its existing credentialed
# execute matrix (which shares F139_WORKER_HMAC_KEY) as credential-free work.
JOB_PREFIX = "rsi-self-qualification"
FIELDS = frozenset({
    "schema", "owner_source_sha", "reservation_seq",
    "reservation_event_sha256", "binding_sha256",
    "original_owner_ledger_head_sha256", "intent",
    "intent_sha256", "signature_sha256", "prior_event_head_sha256",
    "one_job_maximum", "retry_allowed", "development_only",
    "worker_admitted", "worker_dispatched",
    "credential_free_worker_admitted", "paid_model_calls",
    "scientific_first_use", "source_promoted", "autonomous_rsi_proven",
})


class OriginalIssueDenied(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise OriginalIssueDenied("F139_RSI_R12C_" + code)


def event_payload(*, binding: dict, intent: dict, signature: str,
                  prior_head: str) -> dict:
    """Create an inert event payload; a fixture cannot claim original custody."""
    need(valid_binding(binding) and sha64(prior_head)
         and sha64(signature), "SOURCE_OR_HMAC_SHAPE_INVALID")
    validate_intent(intent, binding)
    return {
        "schema": SCHEMA,
        "owner_source_sha": binding["owner_source_sha"],
        "reservation_seq": binding["reservation_seq"],
        "reservation_event_sha256": binding["reservation_event_sha256"],
        "binding_sha256": binding["candidate_binding_sha256"],
        "original_owner_ledger_head_sha256":
            binding["original_owner_ledger_head_sha256"],
        "intent": intent,
        "intent_sha256": hashlib.sha256(canonical(intent)).hexdigest(),
        "signature_sha256": hashlib.sha256(
            signature.encode("ascii")).hexdigest(),
        "prior_event_head_sha256": prior_head,
        "one_job_maximum": 1,
        "retry_allowed": False,
        "development_only": True,
        "worker_admitted": False,
        "worker_dispatched": False,
        "credential_free_worker_admitted": False,
        "paid_model_calls": 0,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }


def validate_event(*, payload: dict, event_row, binding: dict,
                   source_at_event: str) -> None:
    """Fail closed on any altered historical issuance; never grant execution."""
    need(type(payload) is dict and set(payload) == FIELDS
         and payload["schema"] == SCHEMA
         and valid_binding(binding)
         and payload["owner_source_sha"] ==
             binding["owner_source_sha"] == source_at_event
         and payload["reservation_seq"] == binding["reservation_seq"]
         and payload["reservation_event_sha256"] ==
             binding["reservation_event_sha256"]
         and payload["binding_sha256"] == binding["candidate_binding_sha256"]
         and payload["original_owner_ledger_head_sha256"] ==
             binding["original_owner_ledger_head_sha256"]
         and type(payload["one_job_maximum"]) is int
         and payload["one_job_maximum"] == 1
         and payload["retry_allowed"] is False
         and payload["development_only"] is True
         and payload["worker_admitted"] is False
         and payload["worker_dispatched"] is False
         and payload["credential_free_worker_admitted"] is False
         and type(payload["paid_model_calls"]) is int
         and payload["paid_model_calls"] == 0
         and payload["scientific_first_use"] is False
         and payload["source_promoted"] is False
         and payload["autonomous_rsi_proven"] is False
         and sha64(payload["signature_sha256"])
         and sha64(payload["intent_sha256"])
         and hashlib.sha256(canonical(payload["intent"])).hexdigest()
             == payload["intent_sha256"]
         and payload["prior_event_head_sha256"] == event_row["prior_sha"]
         and type(event_row["seq"]) is int
         and event_row["seq"] > binding["reservation_seq"],
         "ISSUANCE_FIELDS_OR_OWNER_AUTHORITY_INVALID")
    validate_intent(payload["intent"], binding)
    need(payload["intent"]["owner_source_sha"] == source_at_event,
         "ISSUER_SOURCE_DRIFT")


def audit_issuance(db: Database) -> tuple[dict, ...]:
    """Read-only cold audit of all original issuance events (lifetime <=1).

    DB.verify already checks SHA chain before invoking this auditor. No secret,
    network, worker, or original owner effect occurs here.
    """
    import sqlite3
    # The actual CLI runs as __main__ under python -m f139.local_controller.
    # Match the already qualified R11 original-ledger class split; a foreign
    # lookalike DB or connection type cannot claim owner authority.
    need(type(db).__name__ == "Database"
         and type(db).__module__ in (
             "f139.local_controller", "local_controller", "__main__")
         and type(getattr(db, "conn", None)) is sqlite3.Connection,
         "ORIGINAL_DATABASE_REQUIRED")
    issued = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events "
        "WHERE kind=? ORDER BY seq", (KIND,)))
    if not issued:
        return ()
    need(len(issued) == 1, "LIFETIME_ISSUANCE_EXHAUSTED")
    reservations = audit_owner_once(db)
    reserved_rows = list(db.conn.execute(
        "SELECT seq,payload,prior_sha,sha FROM events WHERE kind=? "
        "ORDER BY seq", (RESERVATION_KIND,)))
    need(len(reservations) == 1 and len(reserved_rows) == 1,
         "ORIGINAL_RESERVATION_MISSING")
    reserved = reservations[0]
    origin = reserved_rows[0]
    binding = binding_from_reservation_event(
        reservation=reserved, row=origin,
        expected_owner_source_sha=reserved["owner_source_sha"])
    need(valid_binding(binding), "ORIGINAL_BINDING_INVALID")
    all_rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    transitions = [json.loads(row["payload"]) for row in all_rows
                   if row["kind"] == "SOURCE_TRANSITION_ADMITTED"]
    initial = (transitions[0]["from_source_sha"] if transitions
               else db.meta()["source_sha"])
    for row, source_at_event in _source_at_event(all_rows, initial):
        if row["kind"] != KIND:
            continue
        doc = json.loads(row["payload"])
        validate_event(payload=doc, event_row=row, binding=binding,
                       source_at_event=source_at_event)
        return (doc,)
    need(False, "ISSUANCE_EVENT_UNREACHABLE")
    return ()


def owner_self_policy_allows(policy: dict, *, original_source_sha: str) -> bool:
    """Original source-bound operator policy, NOT inferred from an HMAC."""
    if type(policy) is not dict or not sha40(original_source_sha):
        return False
    lanes = policy.get("lanes")
    return (
        policy.get("schema") ==
        "forge.f139.native-autonomy-feed-owner-policy.v1"
        and policy.get("enabled") is True
        and policy.get("source_sha") == original_source_sha
        and type(lanes) is list and len(lanes) == len(set(lanes))
        and "FORGE-self" in lanes
        and all(type(lane) is str for lane in lanes)
        and type(policy.get("max_issue_creations_per_cycle")) is int
        and 0 <= policy["max_issue_creations_per_cycle"] <= 2
        and policy.get("new_controller") is False
        and policy.get("new_scheduler") is False
        and policy.get("new_queue") is False
        and policy.get("scientific_first_use") is False
        and type(policy.get("paid_model_calls")) is int
        and policy["paid_model_calls"] == 0
        and type(policy.get("accepted_ref_mutations")) is int
        and policy["accepted_ref_mutations"] == 0
    )


def issue_original_once(*, db: Database, provider: GitHub,
                        candidate: Readback, signing_key: str,
                        protected_main_sha: str, protected_main_tree_sha: str,
                        worker_run_id: int, worker_job_id: int,
                        runner_os: str) -> dict:
    """Original-owner-only single ledger append; NO dispatch, NO ticket output.

    A qualifying future credential-free job must already be externally
    authenticated. The current unmodified workflow cannot satisfy this.
    """
    source = _authentic_original_owner(
        db, provider, allow_used_reservation=True)
    need(type(candidate) is Readback and type(signing_key) is str
         and type(runner_os) is str and runner_os in RUNNER_OSES,
         "ORIGINAL_INPUTS_REQUIRED")
    original_key = os.environ.get("F139_WORKER_HMAC_KEY", "")
    need(len(original_key) >= 32
         and hmac.compare_digest(signing_key, original_key),
         "ORIGINAL_SIGNER_SECRET_NOT_VERIFIED")
    reserved = audit_owner_once(db)
    need(len(reserved) == 1 and reserved[0]["owner_source_sha"] == source,
         "ORIGINAL_RESERVATION_EPOCH_REQUIRED")
    need(not audit_issuance(db), "LIFETIME_ISSUANCE_ALREADY_SPENT")
    prefix = "repos/" + REPO + "/"
    policy_record = provider.get(prefix + "issues/807")
    need(type(policy_record) is dict
         and policy_record.get("number") == 807
         and policy_record.get("state") == "open"
         and type(policy_record.get("user")) is dict
         and policy_record["user"].get("login") == "spoonman136668-ai"
         and type(policy_record.get("body")) is str,
         "ORIGINAL_OWNER_POLICY_NOT_AUTHENTIC")
    try:
        owner_policy = json.loads(policy_record["body"])
    except (ValueError, TypeError) as exc:
        raise OriginalIssueDenied(
            "F139_RSI_R12C_ORIGINAL_OWNER_POLICY_UNREADABLE") from exc
    need(owner_self_policy_allows(
        owner_policy, original_source_sha=source),
        "FORGE_SELF_NOT_IN_ORIGINAL_OWNER_POLICY")
    binding = bind_original_candidate(
        db=db, candidate=candidate,
        expected_owner_source_sha=source)
    need(sha40(protected_main_sha) and sha40(protected_main_tree_sha)
         and provider.protected_main() == protected_main_sha,
         "PROTECTED_MAIN_DRIFT")
    commit = provider.get(prefix + "git/commits/" + protected_main_sha)
    need(type(commit) is dict and commit.get("sha") == protected_main_sha
         and type(commit.get("tree")) is dict
         and commit["tree"].get("sha") == protected_main_tree_sha,
         "PROTECTED_MAIN_TREE_DRIFT")
    intent = prepare(
        binding=binding, source_sha=protected_main_sha,
        source_tree_sha=protected_main_tree_sha,
        worker_run_id=worker_run_id,
        worker_job_id=worker_job_id, runner_os=runner_os)
    run = provider.get(prefix + "actions/runs/" + str(worker_run_id))
    job = provider.get(prefix + "actions/jobs/" + str(worker_job_id))
    need(type(run) is dict and type(job) is dict
         and run.get("id") == worker_run_id
         and run.get("run_attempt") == 1
         and run.get("event") == "workflow_dispatch"
         and run.get("head_sha") == protected_main_sha
         and run.get("head_branch") == "main"
         and run.get("path") == ".github/workflows/" + WORKFLOW
         and run.get("status") in ("queued", "in_progress")
         and run.get("conclusion") is None
         and type(run.get("repository")) is dict
         and run["repository"].get("full_name") == REPO
         and type(run.get("head_repository")) is dict
         and run["head_repository"].get("full_name") == REPO
         and type(run.get("actor")) is dict
         and run["actor"].get("login") == "spoonman136668-ai"
         and job.get("id") == worker_job_id
         and job.get("run_id") == worker_run_id
         and job.get("head_sha") == protected_main_sha
         and job.get("name") == JOB_PREFIX + " (" + runner_os + ")"
         and job.get("labels") == [runner_os]
         and job.get("status") in ("queued", "in_progress")
         and job.get("conclusion") is None,
         "ORIGINAL_PROVIDER_SELF_WORKER_NOT_QUALIFIED")
    # Do not return or log a usable ticket: a separately authorized
    # credential-free worker integration is still absent.
    signature = _development_signature(signing_key, intent)
    meta = db.meta()
    payload = event_payload(
        binding=binding, intent=intent, signature=signature,
        prior_head=meta["head_hash"])
    with db.transaction():
        db.verify()
        now = db.meta()
        need(now["head_hash"] == meta["head_hash"]
             and now["source_sha"] == source
             and now["enabled"] == 1 and now["legacy_suspended"] == 1
             and not db.actives() and db.ready() is None
             and not audit_issuance(db)
             and SingleOwner.held(db.filename.with_suffix(".lock")),
             "ORIGINAL_OWNER_CHANGED_OR_ISSUANCE_SPENT")
        db.event(KIND, payload)
        db.verify()
        result = {
            "schema": SCHEMA,
            "issuance_event_sha256": db.meta()["head_hash"],
            "binding_sha256": binding["candidate_binding_sha256"],
            "intent_sha256": payload["intent_sha256"],
            "one_original_issuance_spent": True,
            "credential_free_worker_admitted": False,
            "worker_dispatched": False,
            "scientific_first_use": False,
            "source_promoted": False,
            "autonomous_rsi_proven": False,
        }
    return result

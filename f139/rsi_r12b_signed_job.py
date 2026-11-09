"""R12-B: source-bound HMAC envelope for ONE future F139-self DEV job.

Pure credentialed verification, no live original-owner signature, dispatch,
worker admission, new lane, workflow, replay, or scientific authority.
Original-source one-shot spending and credential-free worker acceptance
must be independently qualified before this can be an executable ticket.
"""
from __future__ import annotations

import hashlib
import hmac

from f139.local_controller import Database, canonical
from f139.rsi_r12_candidate_binding import (
    SCHEMA as BINDING_SCHEMA, bind_original_candidate,
    original_owner_database,
)
from f139.rsi_r6_known_repair_cycle import HEAD, DIGEST, PATH
from f139.rsi_r6_provider_readback import Readback

SCHEMA = "forge.f139.rsi-r12b.one-job-signed-development-contract.v1"
AUTH_SCHEMA = "forge.f139.rsi-r12b.credentialed-validation-only.v1"
DOMAIN = b"FORGE-F139-RSI-R12B-DEV-V1\n"
REPO = "spoonman136668-ai/FORGE"
WORKFLOW = "forge-f139-development-worker.yml"
LANE = "FORGE-self"
RUNNER_OSES = frozenset(("ubuntu-latest", "windows-latest"))
MAX_RUN_ID = (1 << 63) - 1

BINDING_KEYS = frozenset({
    "schema", "owner_source_sha", "reservation_seq",
    "reservation_event_sha256", "original_owner_ledger_head_sha256",
    "failed_head_sha", "failed_run_id", "failed_job_id",
    "failed_log_sha256", "source_git_blob_sha", "target_path",
    "before_sha256", "candidate_sha256", "task_scope_sha256",
    "mechanism", "development_only", "original_owner_signed",
    "worker_admitted", "worker_dispatched", "original_regression_qualified",
    "scientific_first_use", "source_promoted", "autonomous_rsi_proven",
    "candidate_binding_sha256",
})

FIELDS = frozenset({
    "schema", "repository", "workflow", "lane", "event",
    "source_sha", "source_tree_sha", "owner_source_sha",
    "original_ledger_head_sha256", "reservation_event_sha256",
    "reservation_seq", "binding_sha256", "failed_head_sha",
    "failed_run_id", "failed_job_id", "failed_log_sha256",
    "source_git_blob_sha", "target_path", "before_sha256",
    "candidate_sha256", "task_scope_sha256", "worker_run_id",
    "worker_job_id", "worker_run_attempt", "runner_os",
    "development_only", "worker_admitted", "worker_dispatched",
    "scientific_first_use", "source_promoted", "autonomous_rsi_proven",
})


class SignedDevelopmentDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise SignedDevelopmentDenied("F139_RSI_R12B_" + reason)


def sha40(x) -> bool:
    return type(x) is str and HEAD.fullmatch(x) is not None


def sha64(x) -> bool:
    return type(x) is str and DIGEST.fullmatch(x) is not None


def valid_binding(binding: dict) -> bool:
    if type(binding) is not dict or set(binding) != BINDING_KEYS:
        return False
    try:
        body = {k: v for k, v in binding.items()
                if k != "candidate_binding_sha256"}
        return (
            binding["schema"] == BINDING_SCHEMA
            and sha40(binding["owner_source_sha"])
            and type(binding["reservation_seq"]) is int
            and binding["reservation_seq"] > 0
            and all(sha64(binding[k]) for k in (
                "reservation_event_sha256",
                "original_owner_ledger_head_sha256",
                "failed_log_sha256", "before_sha256",
                "candidate_sha256", "task_scope_sha256",
                "candidate_binding_sha256"))
            and sha40(binding["failed_head_sha"])
            and sha40(binding["source_git_blob_sha"])
            and type(binding["failed_run_id"]) is int
            and binding["failed_run_id"] > 0
            and type(binding["failed_job_id"]) is int
            and binding["failed_job_id"] > 0
            and type(binding["target_path"]) is str
            and PATH.fullmatch(binding["target_path"]) is not None
            and type(binding["mechanism"]) is str
            and 3 <= len(binding["mechanism"]) <= 60
            and binding["before_sha256"] != binding["candidate_sha256"]
            and binding["development_only"] is True
            and all(binding[k] is False for k in (
                "original_owner_signed", "worker_admitted",
                "worker_dispatched", "original_regression_qualified",
                "scientific_first_use", "source_promoted",
                "autonomous_rsi_proven"))
            and hashlib.sha256(canonical(body)).hexdigest()
            == binding["candidate_binding_sha256"]
        )
    except (KeyError, TypeError, ValueError):
        return False


def prepare(*, binding: dict, source_sha: str, source_tree_sha: str,
            worker_run_id: int, worker_job_id: int,
            runner_os: str) -> dict:
    """Draft only: a signed payload is NOT an original-owner spend/permit."""
    need(valid_binding(binding), "ORIGINAL_BINDING_INVALID")
    need(sha40(source_sha) and sha40(source_tree_sha)
         and type(worker_run_id) is int
         and binding["failed_run_id"] < worker_run_id <= MAX_RUN_ID
         and type(worker_job_id) is int
         and 0 < worker_job_id <= MAX_RUN_ID
         and type(runner_os) is str
         and runner_os in RUNNER_OSES,
         "WORKER_SOURCE_OR_RUN_INVALID")
    return {
        "schema": SCHEMA,
        "repository": REPO,
        "workflow": WORKFLOW,
        "lane": LANE,
        "event": "workflow_dispatch",
        "source_sha": source_sha,
        "source_tree_sha": source_tree_sha,
        "owner_source_sha": binding["owner_source_sha"],
        "original_ledger_head_sha256":
            binding["original_owner_ledger_head_sha256"],
        "reservation_event_sha256": binding["reservation_event_sha256"],
        "reservation_seq": binding["reservation_seq"],
        "binding_sha256": binding["candidate_binding_sha256"],
        "failed_head_sha": binding["failed_head_sha"],
        "failed_run_id": binding["failed_run_id"],
        "failed_job_id": binding["failed_job_id"],
        "failed_log_sha256": binding["failed_log_sha256"],
        "source_git_blob_sha": binding["source_git_blob_sha"],
        "target_path": binding["target_path"],
        "before_sha256": binding["before_sha256"],
        "candidate_sha256": binding["candidate_sha256"],
        "task_scope_sha256": binding["task_scope_sha256"],
        "worker_run_id": worker_run_id,
        "worker_job_id": worker_job_id,
        "worker_run_attempt": 1,
        "runner_os": runner_os,
        "development_only": True,
        "worker_admitted": False,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "source_promoted": False,
        "autonomous_rsi_proven": False,
    }


def validate_intent(intent: dict, binding: dict) -> None:
    need(type(intent) is dict and set(intent) == FIELDS
         and valid_binding(binding), "INTENT_OR_BINDING_SHAPE_INVALID")
    expected = prepare(
        binding=binding, source_sha=intent.get("source_sha"),
        source_tree_sha=intent.get("source_tree_sha"),
        worker_run_id=intent.get("worker_run_id"),
        worker_job_id=intent.get("worker_job_id"),
        runner_os=intent.get("runner_os"))
    need(intent == expected, "TICKET_FIELDS_OR_AUTHORITY_DRIFT")


def _development_signature(secret: str, intent: dict) -> str:
    """Cryptographic primitive only; not a live original-owner signer."""
    need(type(secret) is str and len(secret) >= 32
         and 32 <= len(secret.encode("utf-8")) <= 4096,
         "SIGNING_KEY_NOT_BOUNDED")
    return hmac.new(secret.encode("utf-8"),
                    DOMAIN + canonical(intent), hashlib.sha256).hexdigest()


def validate_credentialed(*, db: Database, candidate: Readback,
                          owner_source_sha: str, intent: dict,
                          signature: str, signing_key: str,
                          authenticated_main_sha: str,
                          authenticated_main_tree_sha: str,
                          authenticated_run_id: int,
                          authenticated_job_id: int,
                          authenticated_attempt: int,
                          authenticated_event: str,
                          authenticated_repository: str,
                          authenticated_workflow: str,
                          authenticated_runner_os: str) -> dict:
    """Credentialed validator only. No execution or signed owner authority.

    This must run independently of the credential-free worker, and it still
    cannot approve work until original lifetime-one issuance is journaled.
    """
    need(original_owner_database(db) and type(candidate) is Readback,
         "ORIGINAL_SOURCE_OBJECTS_REQUIRED")
    binding = bind_original_candidate(
        db=db, candidate=candidate,
        expected_owner_source_sha=owner_source_sha)
    validate_intent(intent, binding)
    need(sha40(authenticated_main_sha)
         and sha40(authenticated_main_tree_sha)
         and type(authenticated_run_id) is int
         and type(authenticated_job_id) is int
         and authenticated_attempt == 1
         and type(authenticated_attempt) is int
         and authenticated_main_sha == intent["source_sha"]
         and authenticated_main_tree_sha == intent["source_tree_sha"]
         and authenticated_run_id == intent["worker_run_id"]
         and authenticated_job_id == intent["worker_job_id"]
         and authenticated_repository == intent["repository"] == REPO
         and authenticated_workflow == intent["workflow"] == WORKFLOW
         and authenticated_event == intent["event"] == "workflow_dispatch"
         and authenticated_runner_os == intent["runner_os"]
         and authenticated_runner_os in RUNNER_OSES,
         "PROVIDER_WORKER_ORIGIN_DRIFT")
    need(sha64(signature)
         and hmac.compare_digest(
             _development_signature(signing_key, intent), signature),
         "TICKET_SIGNATURE_INVALID")
    body = canonical(intent)
    return {
        "schema": AUTH_SCHEMA,
        "intent_sha256": hashlib.sha256(body).hexdigest(),
        "signature_sha256": hashlib.sha256(signature.encode("ascii")).hexdigest(),
        "binding_sha256": binding["candidate_binding_sha256"],
        "cryptographic_validation_passed": True,
        "original_lifetime_spend_verified": False,
        "credential_free_worker_admitted": False,
        "worker_dispatched": False,
        "source_regression_qualified": False,
        "source_promoted": False,
        "scientific_first_use": False,
        "autonomous_rsi_proven": False,
    }

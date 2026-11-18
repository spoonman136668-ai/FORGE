"""Bounded, non-executing training requests for FORGE's original F139 owner.

The existing original owner may use these deterministic requests to seek a
separately authenticated CKAD stage authorization. Neither a campaign nor a
request authorizes dispatch, original-source exposure, model promotion, a new
scheduler, or first-use. Yggdrasil owns execution and scientific judgment.
"""
from __future__ import annotations

import re

from f139.ckad_stage_custody import (
    CustodyDenied, audit_chain, canonical, digest, plan_digest,
    seal_stage,
)

SCHEMA = "forge.ckad.specified-training-request.v1"
REQUEST_SCHEMA = "forge.ckad.original-owner-stage-proposal.v1"
OWNER_REPO = "spoonman136668-ai/FORGE"
OWNER_TASK = "FORGE-F139-UnifiedController"
SCIENCE_OWNER = "Yggdrasil/CKAD"
MODE = "previously-consumed-development-custody-only"
ID = re.compile(r"[a-z][a-z0-9-]{3,63}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "campaign_id", "lane", "science_owner", "owner_repo",
    "owner_task", "original_owner_source_sha", "mode", "plan",
    "max_total_observations", "max_total_interventions", "max_total_cpu_seconds",
    "max_stages", "scientific_first_use", "training_execution_authorized",
    "promotion_authorized", "paid_api_calls", "new_controller", "new_scheduler",
    "new_queue",
})


class CampaignDenied(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_" + code)


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def validate_campaign(campaign):
    """Freeze a request. Do not convert operator intent into execution rights."""
    need(type(campaign) is dict and set(campaign) == FIELDS,
         "EXACT_FIELDS")
    plan = campaign["plan"]
    try:
        pin = plan_digest(plan)
    except (CustodyDenied, KeyError, TypeError, ValueError) as exc:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_FROZEN_PLAN_INVALID") from exc
    need(campaign["schema"] == SCHEMA
         and type(campaign["campaign_id"]) is str
         and ID.fullmatch(campaign["campaign_id"]) is not None
         and campaign["lane"] == "Yggdrasil"
         and campaign["science_owner"] == SCIENCE_OWNER
         and campaign["owner_repo"] == OWNER_REPO
         and campaign["owner_task"] == OWNER_TASK
         and type(campaign["original_owner_source_sha"]) is str
         and SHA40.fullmatch(campaign["original_owner_source_sha"]) is not None
         and campaign["mode"] == MODE
         and campaign["scientific_first_use"] is False
         and campaign["training_execution_authorized"] is False
         and campaign["promotion_authorized"] is False
         and campaign["paid_api_calls"] == 0
         and type(campaign["paid_api_calls"]) is int
         and campaign["new_controller"] is False
         and campaign["new_scheduler"] is False
         and campaign["new_queue"] is False,
         "OWNER_OR_AUTHORITY_SCOPE")
    stages = plan["stages"]
    need(_int(campaign["max_stages"], 1, len(stages))
         and _int(campaign["max_total_observations"], 0, 1_200_000)
         and _int(campaign["max_total_interventions"], 0, 24_576)
         and _int(campaign["max_total_cpu_seconds"], 1, 43_200)
         and sum(x["max_observations"] for x in stages[:campaign["max_stages"]])
                <= campaign["max_total_observations"]
         and sum(x["max_interventions"] for x in stages[:campaign["max_stages"]])
                <= campaign["max_total_interventions"]
         and sum(x["max_cpu_seconds"] for x in stages[:campaign["max_stages"]])
                <= campaign["max_total_cpu_seconds"],
         "GLOBAL_BUDGET_INSUFFICIENT")
    phases = [s["phase"] for s in stages[:campaign["max_stages"]]]
    need("learn" in phases and "evaluate" in phases
         and phases.index("learn") < phases.index("evaluate"),
         "EVALUATION_MUST_FOLLOW_LEARNING_WITHIN_STAGE_CAP")
    raw = canonical(campaign)
    need(len(raw) <= 32768, "REQUEST_OVERSIZE")
    return {"campaign_sha256": digest(raw), "plan_sha256": pin}


def next_stage(campaign, receipts, *, independently_pinned_head=None):
    """Prepare the next inert CKAD stage proposal under verified lineage.

    An independently held head digest is mandatory after stage zero; callers
    may not treat the chain's self-reported last hash as independent custody.
    After the declared limit, no further stages are proposed.
    """
    pins = validate_campaign(campaign)
    need(type(receipts) is list, "RECEIPTS_REQUIRED")
    if receipts:
        need(type(independently_pinned_head) is str
             and SHA64.fullmatch(independently_pinned_head) is not None,
             "INDEPENDENT_HEAD_PIN_REQUIRED")
    else:
        need(independently_pinned_head is None, "UNEXPECTED_HEAD_PIN")
    try:
        audit = audit_chain(campaign["plan"], receipts,
                            expected_head_receipt_sha256=independently_pinned_head)
    except (CustodyDenied, TypeError, KeyError, ValueError) as exc:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_CHECKPOINT_OR_RECEIPT_DRIFT") from exc
    need(audit["completed_stages"] <= campaign["max_stages"],
         "STAGE_LIMIT_EXCEEDED")
    observations = sum(r["observations_reported"] for r in receipts)
    interventions = sum(r["interventions_reported"] for r in receipts)
    cpu_seconds = sum(r["cpu_seconds_reported"] for r in receipts)
    need(observations <= campaign["max_total_observations"]
         and interventions <= campaign["max_total_interventions"]
         and cpu_seconds <= campaign["max_total_cpu_seconds"],
         "OBSERVED_BUDGET_EXCEEDED")
    index = audit["completed_stages"]
    common = {
        "campaign_id": campaign["campaign_id"],
        "campaign_sha256": pins["campaign_sha256"],
        "plan_sha256": pins["plan_sha256"],
        "last_receipt_sha256": audit["last_receipt_sha256"],
        "checkpoint_sha256": audit["current_checkpoint_sha256"],
        "stages_completed": index,
        "scientific_pass": False,
        "training_execution_authorized": False,
        "dispatch_authorized": False,
        "promotion_authorized": False,
    }
    if index == campaign["max_stages"]:
        return dict(common, status="ALL_REQUESTED_STAGES_SEALED",
                    next_stage=None, next_request_sha256=None)
    s = campaign["plan"]["stages"][index]
    proposal = {
        "schema": REQUEST_SCHEMA, "campaign_id": campaign["campaign_id"],
        "campaign_sha256": pins["campaign_sha256"],
        "plan_sha256": pins["plan_sha256"],
        "owner_repo": OWNER_REPO, "owner_task": OWNER_TASK,
        "owner_source_sha": campaign["original_owner_source_sha"],
        "science_owner": SCIENCE_OWNER, "lane": "Yggdrasil",
        "target_source_sha": campaign["plan"]["candidate_sha"],
        "target_tree_sha": campaign["plan"]["candidate_tree"],
        "stage_index": index, "stage_id": s["id"], "phase": s["phase"],
        "native_component": s["component"],
        "prior_receipt_sha256": audit["last_receipt_sha256"],
        "input_checkpoint_sha256": audit["current_checkpoint_sha256"],
        "max_observations": s["max_observations"],
        "max_interventions": s["max_interventions"],
        "max_cpu_seconds": s["max_cpu_seconds"],
        "scientific_first_use": False, "dispatch_authorized": False,
        "training_execution_authorized": False,
    }
    return dict(common, status="CKAD_OWNER_STAGE_AUTHORIZATION_REQUIRED",
                next_stage=proposal, next_request_sha256=digest(canonical(proposal)))


def seal_owner_result(campaign, receipts, stage_proposal, *,
                      independently_pinned_head=None, checkpoint_input,
                      checkpoint_output, evidence_bytes, control_receipt_bytes,
                      evaluation_receipt_bytes, observations, interventions,
                      cpu_seconds):
    """Audit CKAD-supplied raw bytes without executing training in FORGE."""
    current = next_stage(campaign, receipts,
                         independently_pinned_head=independently_pinned_head)
    need(current["next_stage"] is not None
         and type(stage_proposal) is dict
         and stage_proposal == current["next_stage"],
         "STAGE_PROPOSAL_REPLAY_OR_TAMPER")
    try:
        sealed = seal_stage(campaign["plan"], receipts,
                            stage_index=stage_proposal["stage_index"],
                            checkpoint_input=checkpoint_input,
                            checkpoint_output=checkpoint_output,
                            evidence_bytes=evidence_bytes,
                            control_receipt_bytes=control_receipt_bytes,
                            evaluation_receipt_bytes=evaluation_receipt_bytes,
                            observations=observations,
                            interventions=interventions,
                            cpu_seconds=cpu_seconds)
    except (CustodyDenied, TypeError, KeyError, ValueError) as exc:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_STAGE_RESULT_INVALID") from exc
    return sealed

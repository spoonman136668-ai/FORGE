"""Source-pinned cross-repo CKAD development work-order adapter (non-dispatch).

Compiles one FORGE SingleOwner-owned *proposal* into the exact input format
of Yggdrasil's native CKAD development stage. It does not create an owner
permit, dispatch a GitHub workflow, call a trainer, or sign an authority claim.
"""
from __future__ import annotations

import re

from f139.ckad_campaign_request import (
    CampaignDenied, need, next_stage, validate_campaign,
)
from f139.ckad_stage_custody import (
    CKAD25_DEV_SHA, CKAD25_DEV_TREE, COMPONENTS, digest, canonical,
)

SCHEMA = "forge.ckad.yggdrasil-development-stage-adapter.v1"
TARGET_SCHEMA = "yggdrasil.ckad.native-development-stage.v1"
SOURCE_REPO = "spoonman136668-ai/Yggdrasil"
SOURCE_MODE = "previously-consumed-engineering-fixture-only"
TAG = re.compile(r"[a-z][a-z0-9-]{3,63}\Z")
PIN = re.compile(r"[0-9a-f]{64}\Z")


def compile_development_order(campaign, receipts, *,
                              source_ref_sha256, packet_sha256,
                              independently_pinned_head=None):
    """Return bounded inert Yggdrasil-shaped input for a *learn* stage.

    The source owner must separately prove the packet's previous-consumption
    custody, persist and verify state, and independently approve an execution
    route. Digest equality cannot authenticate evidence from a foreign job.
    """
    head = next_stage(campaign, receipts,
                      independently_pinned_head=independently_pinned_head)
    proposal = head["next_stage"]
    need(type(proposal) is dict, "STAGE_LIMIT_REACHED")
    stage = campaign["plan"]["stages"][proposal["stage_index"]]
    need(proposal["phase"] == "learn"
         and type(proposal["stage_id"]) is str
         and TAG.fullmatch(proposal["stage_id"]) is not None
         and stage["component"] in COMPONENTS
         and proposal["target_source_sha"] == CKAD25_DEV_SHA
         and proposal["target_tree_sha"] == CKAD25_DEV_TREE
         and type(source_ref_sha256) is str
         and PIN.fullmatch(source_ref_sha256) is not None
         and type(packet_sha256) is str
         and PIN.fullmatch(packet_sha256) is not None
         and 1 <= stage["max_observations"] <= 2048
         and stage["max_interventions"] == 0
         and 1 <= stage["max_cpu_seconds"] <= 120,
         "SOURCE_OWNER_LEARN_ONLY_OR_BUDGET")
    request = {
        "schema": TARGET_SCHEMA,
        "campaign_id": campaign["campaign_id"],
        "stage_index": proposal["stage_index"],
        "stage_id": proposal["stage_id"],
        "phase": "learn",
        "source_repo": SOURCE_REPO,
        "source_commit": proposal["target_source_sha"],
        "source_tree": proposal["target_tree_sha"],
        "native_component": stage["component"],
        "source_mode": SOURCE_MODE,
        "source_ref_sha256": source_ref_sha256,
        "input_checkpoint_sha256": proposal["input_checkpoint_sha256"],
        "packet_sha256": packet_sha256,
        "max_observations": stage["max_observations"],
        "max_wall_seconds": stage["max_cpu_seconds"],
        "scientific_first_use": False,
        "forge_dispatch_authorized": False,
        "promotion_authorized": False,
        "paid_api_calls": 0,
    }
    return {
        "schema": SCHEMA,
        "owner_source_sha": campaign["original_owner_source_sha"],
        "campaign_sha256": validate_campaign(campaign)["campaign_sha256"],
        "source_owned_request": request,
        "source_owned_request_sha256": digest(canonical(request)),
        "prior_receipt_sha256": head["last_receipt_sha256"],
        "source_owner_packet_authenticated": False,
        "source_owner_execution_authorized": False,
        "source_owner_run_authenticated": False,
        "dispatch_authorized": False,
        "training_execution_authorized": False,
        "scientific_first_use": False,
        "scientific_pass": False,
        "promotion_authorized": False,
    }

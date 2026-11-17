"""CKAD: read-only custody contract for cumulative tokenless Yggdrasil training.

FORGE may CHECK handoff integrity. Only CKAD/Yggdrasil may train or promote a
native model. No training, source actions, GitHub writes, agent dispatch, local
runner, controller, scheduler, model calls, scientific first-use or acceptance.
This does not authenticate untrusted external receipts or prove intelligence.
"""
from __future__ import annotations
import hashlib
import json
import re

SCHEMA = "forge.ckad.cumulative-dev-handoff.v1"
RECEIPT = "forge.ckad.cumulative-dev-stage-receipt.v1"
SOURCE_REPO = "spoonman136668-ai/Yggdrasil"
SOURCE_MAIN = "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9"
CKAD12_SHA = "5df8dbf506027b914f66e19441376d1347a3e09d"
CKAD12_TREE = "52e54277d155f8ab683ef34e02e4a0d599e54037"
COMPONENTS = frozenset((
    "yggdrasil.native_context_basis.NativeContextBasis",
    "yggdrasil.native_property_knowledge.NativePropertyKnowledge",
    "yggdrasil.native_intervention_repair.NativeInterventionRepair",
    "yggdrasil.native_degree_hypothesis.NativeDegreeHypothesis",
))
PHASES = frozenset(("observe", "learn", "consolidate", "evaluate", "repair"))
SHA = re.compile(r"[0-9a-f]{64}\Z")
TAG = re.compile(r"[a-z][a-z0-9_-]{1,47}\Z")
PLAN_FIELDS = frozenset((
    "schema", "source_repo", "accepted_main", "candidate_sha", "candidate_tree",
    "native_architecture", "source_mode", "initial_checkpoint_sha256",
    "frozen_prereg_sha256", "frozen_controls_sha256",
    "frozen_split_sha256", "seeds", "stages",
    "scientific_first_use", "training_execution_authorized",
))
STAGE_FIELDS = frozenset((
    "id", "phase", "component", "max_observations", "max_interventions",
    "max_cpu_seconds",
))
RECEIPT_FIELDS = frozenset((
    "schema", "plan_sha256", "stage_index", "stage_id", "phase",
    "source_commit", "source_tree", "component", "prior_receipt_sha256",
    "input_checkpoint_sha256", "output_checkpoint_sha256",
    "evidence_sha256", "control_receipt_sha256", "evaluation_receipt_sha256",
    "observations_reported", "interventions_reported", "cpu_seconds_reported",
    "checkpoint_changed", "scientific_pass", "training_executed_by_forge",
    "development_custody_only",
))
MAX_RAW = 4 * 1024 * 1024

class CustodyDenied(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise CustodyDenied("FORGE_CKAD_" + code)

def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def sha_ok(x):
    return type(x) is str and SHA.fullmatch(x) is not None

def bytes_ok(x):
    return type(x) is bytes and 1 <= len(x) <= MAX_RAW

def plan_digest(plan):
    """Freeze exact source identity, curriculum and scientific controls."""
    need(type(plan) is dict and set(plan) == PLAN_FIELDS, "PLAN_FIELDS")
    need(plan["schema"] == SCHEMA and plan["source_repo"] == SOURCE_REPO
         and plan["accepted_main"] == SOURCE_MAIN
         and plan["candidate_sha"] == CKAD12_SHA
         and plan["candidate_tree"] == CKAD12_TREE
         and plan["native_architecture"] == "yggdrasil-native-tokenless"
         and plan["source_mode"] == "previously-consumed-synthetic-only"
         and plan["scientific_first_use"] is False
         and plan["training_execution_authorized"] is False,
         "SOURCE_OR_AUTHORITY")
    need(all(sha_ok(plan[k]) for k in (
        "initial_checkpoint_sha256", "frozen_prereg_sha256",
        "frozen_controls_sha256", "frozen_split_sha256")),
        "FROZEN_EVIDENCE")
    seeds = plan["seeds"]
    need(type(seeds) is list and 1 <= len(seeds) <= 8
         and all(type(s) is int and 0 <= s < 2**32 for s in seeds)
         and len(set(seeds)) == len(seeds), "FROZEN_SEEDS")
    stages = plan["stages"]
    need(type(stages) is list and 2 <= len(stages) <= 12, "CURRICULUM_LENGTH")
    ids = []
    for stage in stages:
        need(type(stage) is dict and set(stage) == STAGE_FIELDS
             and type(stage["id"]) is str
             and TAG.fullmatch(stage["id"]) is not None
             and stage["phase"] in PHASES
             and stage["component"] in COMPONENTS
             and type(stage["max_observations"]) is int
             and 0 <= stage["max_observations"] <= 100_000
             and type(stage["max_interventions"]) is int
             and 0 <= stage["max_interventions"] <= 2048
             and type(stage["max_cpu_seconds"]) is int
             and 1 <= stage["max_cpu_seconds"] <= 3600,
             "STAGE_OR_BUDGET")
        ids.append(stage["id"])
    need(len(ids) == len(set(ids))
         and "learn" in [s["phase"] for s in stages]
         and "evaluate" in [s["phase"] for s in stages],
         "FROZEN_CURRICULUM")
    data = canonical(plan)
    need(len(data) <= 32_768, "PLAN_OVERSIZE")
    return digest(data)

def receipt_digest(receipt):
    need(type(receipt) is dict and set(receipt) == RECEIPT_FIELDS,
         "RECEIPT_FIELDS")
    return digest(canonical(receipt))

def audit_chain(plan, receipts, *, expected_head_receipt_sha256=None):
    """Audit the complete declared digest chain, not native learning quality.

    This check cannot prove a stored checkpoint exists without the checkpoint
    bytes. Each stage seal below separately checks the supplied raw bytes.
    """
    pin = plan_digest(plan)
    need(type(receipts) is list
         and len(receipts) <= len(plan["stages"]), "CHAIN_LENGTH")
    prior = None
    state = plan["initial_checkpoint_sha256"]
    for i, r in enumerate(receipts):
        need(type(r) is dict and set(r) == RECEIPT_FIELDS,
             "CHAIN_RECEIPT_FIELDS")
        s = plan["stages"][i]
        need(r["schema"] == RECEIPT
             and r["plan_sha256"] == pin
             and type(r["stage_index"]) is int and r["stage_index"] == i
             and r["stage_id"] == s["id"] and r["phase"] == s["phase"]
             and r["component"] == s["component"]
             and r["source_commit"] == CKAD12_SHA
             and r["source_tree"] == CKAD12_TREE
             and r["prior_receipt_sha256"] == prior
             and r["input_checkpoint_sha256"] == state
             and all(sha_ok(r[k]) for k in (
                 "input_checkpoint_sha256", "output_checkpoint_sha256",
                 "evidence_sha256", "control_receipt_sha256",
                 "evaluation_receipt_sha256"))
             and type(r["observations_reported"]) is int
             and 0 <= r["observations_reported"] <= s["max_observations"]
             and type(r["interventions_reported"]) is int
             and 0 <= r["interventions_reported"] <= s["max_interventions"]
             and type(r["cpu_seconds_reported"]) is int
             and 0 <= r["cpu_seconds_reported"] <= s["max_cpu_seconds"]
             and type(r["checkpoint_changed"]) is bool
             and r["checkpoint_changed"] ==
                 (r["input_checkpoint_sha256"] != r["output_checkpoint_sha256"])
             and r["scientific_pass"] is False
             and r["training_executed_by_forge"] is False
             and r["development_custody_only"] is True,
             "CHILD_SOURCE_OR_CUSTODY_DRIFT")
        prior = receipt_digest(r)
        state = r["output_checkpoint_sha256"]
    if expected_head_receipt_sha256 is not None:
        need(sha_ok(expected_head_receipt_sha256)
             and prior == expected_head_receipt_sha256,
             "EXTERNAL_RECEIPT_HEAD_DRIFT")
    return {"schema": "forge.ckad.cumulative-chain-audit.v1",
            "source_commit": CKAD12_SHA,
            "source_tree": CKAD12_TREE,
            "plan_sha256": pin,
            "completed_stages": len(receipts),
            "current_checkpoint_sha256": state,
            "last_receipt_sha256": prior,
            "scientific_pass": False,
            "execution_authorized": False}

def seal_stage(plan, prior_receipts, *, stage_index, checkpoint_input,
               checkpoint_output, evidence_bytes, control_receipt_bytes,
               evaluation_receipt_bytes, observations, interventions,
               cpu_seconds):
    """Generate advisory metadata from actual supplied byte digests only."""
    previous = audit_chain(plan, prior_receipts)
    need(type(stage_index) is int
         and stage_index == len(prior_receipts)
         and stage_index < len(plan["stages"]), "STAGE_ORDER_OR_REPLAY")
    need(all(bytes_ok(x) for x in (checkpoint_input, checkpoint_output,
                                  evidence_bytes, control_receipt_bytes,
                                  evaluation_receipt_bytes)), "MISSING_RAW_CUSTODY")
    need(digest(checkpoint_input) == previous["current_checkpoint_sha256"],
         "COLD_CHECKPOINT_CHAIN_DRIFT")
    s = plan["stages"][stage_index]
    doc = {
        "schema": RECEIPT, "plan_sha256": previous["plan_sha256"],
        "stage_index": stage_index, "stage_id": s["id"], "phase": s["phase"],
        "source_commit": CKAD12_SHA, "source_tree": CKAD12_TREE,
        "component": s["component"],
        "prior_receipt_sha256": previous["last_receipt_sha256"],
        "input_checkpoint_sha256": digest(checkpoint_input),
        "output_checkpoint_sha256": digest(checkpoint_output),
        "evidence_sha256": digest(evidence_bytes),
        "control_receipt_sha256": digest(control_receipt_bytes),
        "evaluation_receipt_sha256": digest(evaluation_receipt_bytes),
        "observations_reported": observations,
        "interventions_reported": interventions,
        "cpu_seconds_reported": cpu_seconds,
        "checkpoint_changed": checkpoint_input != checkpoint_output,
        "scientific_pass": False,
        "training_executed_by_forge": False,
        "development_custody_only": True,
    }
    audit_chain(plan, prior_receipts + [doc])
    return doc

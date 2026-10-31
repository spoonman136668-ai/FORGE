"""NR-M2I source-only decision evidence and fail-closed telemetry validator.

This module NEVER selects an action, evaluates an unselected transition,
runs a simulator, imports an active controller, or attests source ownership.
A witness is syntactic/source-public integrity evidence only. Only an
independently authorized original source owner can attest a parent proposal.
"""
import hashlib
import json
import math
import re

from nr_m2e_extended_public import full_public

SCHEMA = "forge.nr-m2i.selected-decision-witness.v1"
LEDGER_SCHEMA = "forge.nr-m2i.source-only-witness-ledger.v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
FIELDS = frozenset((
    "source_before_sha256", "source_policy_sha1", "parent_action",
    "selected_action", "allowed_actions", "context_digest",
    "selected_before_feedback_counts", "selected_before_goal_effect_mass",
    "explicit_exploration_budget_spent", "selected_action_reason",
    "event_sequence", "episode_id", "after_sha256", "real_reward",
    "terminated", "truncated",
))

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def source_public_digest(obj):
    return sha256(canonical(full_public(obj)))

def require_hex(s, pattern):
    if type(s) is not str or pattern.fullmatch(s) is None:
        raise ValueError("INVALID_SOURCE_IDENTITY")

def classify(e):
    """Classify actual selected evidence, NOT the claimed action intent."""
    if e["selected_action"] == e["parent_action"]:
        return "UNCHANGED_PARENT"
    selected = e["selected_action"]
    n = e["selected_before_feedback_counts"][selected]
    mass = e["selected_before_goal_effect_mass"][selected]
    if n == 0:
        return "UNTRIED_NO_GOAL_EVIDENCE"
    if mass == 0:
        return "TRIED_NO_GOAL_EVIDENCE"
    return "TRIED_WITH_ENGINEERED_GOAL_EVIDENCE"

class DecisionEvidenceLedger:
    def __init__(self):
        self.next_sequence = 1
        self.last_receipt_sha256 = None
        self.receipts = 0

    def record(self, event, before, after):
        if type(event) is not dict or set(event) != FIELDS:
            raise ValueError("INVALID_WITNESS_FIELDS")
        require_hex(event["source_policy_sha1"], HEX40)
        for name in ("source_before_sha256", "after_sha256", "context_digest"):
            require_hex(event[name], HEX64)
        if (event["source_before_sha256"] != source_public_digest(before) or
            event["after_sha256"] != source_public_digest(after)):
            raise ValueError("SOURCE_PUBLIC_DIGEST_MISMATCH")
        admitted_before = full_public(before)
        admitted_after = full_public(after)
        if admitted_before["mission"] != admitted_after["mission"]:
            raise ValueError("MISSION_CUSTODY_DRIFT")
        if (type(event["episode_id"]) is not str or
            not 1 <= len(event["episode_id"]) <= 128 or
            event["event_sequence"] != self.next_sequence or
            type(event["event_sequence"]) is not int):
            raise ValueError("MISSING_SOURCE_EPISODE_SEQUENCE")
        allowed = event["allowed_actions"]
        if (type(allowed) is not list or not allowed or
            any(type(a) is not int or not 0 <= a <= 6 for a in allowed) or
            allowed != sorted(set(allowed))):
            raise ValueError("INVALID_ORIGINAL_ACTION_RIGHTS")
        for k in ("parent_action", "selected_action"):
            if type(event[k]) is not int or event[k] not in allowed:
                raise ValueError("UNAUTHORIZED_ACTION_OR_UNKNOWN_PARENT")
        counts = event["selected_before_feedback_counts"]
        masses = event["selected_before_goal_effect_mass"]
        if (type(counts) is not list or len(counts) != 7 or
            type(masses) is not list or len(masses) != 7):
            raise ValueError("INVALID_PRESELECTION_HISTORY")
        for n, mass in zip(counts, masses):
            if type(n) is not int or n < 0:
                raise ValueError("INVALID_SOURCE_SELECTED_FEEDBACK_COUNT")
            if (type(mass) not in (int, float) or not math.isfinite(mass)
                or mass < 0 or (n == 0 and mass != 0)):
                raise ValueError("INVALID_SOURCE_GOAL_EVENT_CREDIT")
        spent = event["explicit_exploration_budget_spent"]
        if type(spent) is not int or spent < 0:
            raise ValueError("INVALID_EXPLORATION_ACCOUNTING")
        reason = event["selected_action_reason"]
        if reason not in ("PARENT", "GOAL_EVIDENCE", "EXPLICIT_EXPLORATION"):
            raise ValueError("UNKNOWN_INTENT_PROVENANCE")
        changed = event["selected_action"] != event["parent_action"]
        n = counts[event["selected_action"]]
        mass = masses[event["selected_action"]]
        if ((not changed and (reason != "PARENT" or spent != 0)) or
            (changed and reason == "PARENT") or
            (changed and reason == "EXPLICIT_EXPLORATION" and spent == 0) or
            (changed and reason == "GOAL_EVIDENCE" and (n == 0 or mass == 0))):
            raise ValueError("UNSUPPORTED_SELECTED_DECISION_INTENT")
        if (type(event["real_reward"]) not in (int, float) or
            not math.isfinite(event["real_reward"])):
            raise ValueError("INVALID_ORIGINAL_REWARD")
        if (type(event["terminated"]) is not bool or
            type(event["truncated"]) is not bool or
            (event["terminated"] and event["truncated"])):
            raise ValueError("INVALID_TERMINAL_CUSTODY")
        # Explicitly distinguish the selected action's prior engineered
        # public-effect credit from THIS returned original reward.
        evidence_class = classify(event)
        envelope = {
            "schema": SCHEMA,
            "decision": event,
            "previous_receipt_sha256": self.last_receipt_sha256,
            "evidence_class": evidence_class,
            "parent_source_attestation": "UNVERIFIED_BY_SOURCE_ONLY_MODULE",
            "source_original_world_execution": False,
            "authenticity_boundary": "EXTERNAL_OWNER_WITNESS_REQUIRED",
        }
        raw = canonical(envelope)
        digest = sha256(raw)
        self.next_sequence += 1
        self.receipts += 1
        self.last_receipt_sha256 = digest
        return raw, digest

    def checkpoint(self):
        return canonical({
            "schema": LEDGER_SCHEMA,
            "next_sequence": self.next_sequence,
            "last_receipt_sha256": self.last_receipt_sha256,
            "receipts": self.receipts,
        })

    @classmethod
    def restore(cls, raw, expected_sha256):
        require_hex(expected_sha256, HEX64)
        if type(raw) is not bytes or sha256(raw) != expected_sha256:
            raise ValueError("UNTRUSTED_WITNESS_CHECKPOINT")
        try:
            data = json.loads(raw)
            if (type(data) is not dict or
                set(data) != {"schema", "next_sequence",
                              "last_receipt_sha256", "receipts"} or
                data["schema"] != LEDGER_SCHEMA or
                type(data["next_sequence"]) is not int or
                type(data["receipts"]) is not int or
                data["next_sequence"] != data["receipts"] + 1 or
                not 0 <= data["receipts"] <= 1000000 or
                (data["last_receipt_sha256"] is None) != (data["receipts"] == 0)):
                raise ValueError("WITNESS_CHECKPOINT_SCHEMA")
            if data["last_receipt_sha256"] is not None:
                require_hex(data["last_receipt_sha256"], HEX64)
            model = cls()
            model.next_sequence = data["next_sequence"]
            model.receipts = data["receipts"]
            model.last_receipt_sha256 = data["last_receipt_sha256"]
            if model.checkpoint() != raw:
                raise ValueError("NONCANONICAL_WITNESS_CHECKPOINT")
            return model
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            raise ValueError("WITNESS_RESTORE_REJECTED") from exc

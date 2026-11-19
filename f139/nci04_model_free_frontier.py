"""Inert, exact-identity model-free native development candidate frontier.

This module only chooses among *externally source-authenticated* proposal
manifests. It never invents a code patch, attests to Git/ledger identity,
reads private data, executes a model, invokes an API or writes owner state.
Candidates are advisory, not authority to dispatch, publish or use science.
The original F139 owner/SQLite/worker is unaffected until separately qualified.
"""
from __future__ import annotations

import hashlib
import json
import re

from f139.nci04_native_contract import model_source_path_allowed

SCHEMA = "forge.f139.model-free-frontier.v1"
HASH40 = re.compile(r"[a-f0-9]{40}\Z")
HASH64 = re.compile(r"[a-f0-9]{64}\Z")
LANES = ("Wingless", "Yggdrasil")
MAX_CATALOG = 128
MAX_HISTORY = 10000
ENTRY = frozenset({
    "lane", "controller_source_sha", "target_commit", "target_tree_sha",
    "path", "before_sha256", "after_sha256", "mechanism_sha256",
    "dependency_sha256", "qualification_harness_sha256", "suite_identity_sha256",
    "training_config_sha256", "toolchain_identity", "frozen_split_sha256",
    "scientific_first_use", "protected_holdouts_accessed", "paid_model_calls",
    "accepted_ref_mutations", "optimizer_policy_mutations",
})
HISTORY = frozenset({
    "seq", "event_sha256", "controller_source_sha", "lane",
    "candidate_identity", "mechanism_sha256", "outcome", "evidence_sha256",
})
OUTCOMES = frozenset({
    "VERIFIED", "QUARANTINED", "NEGATIVE", "CONSUMED_INDETERMINATE",
    "START_RISK", "WAIT_PROVIDER",
})


class FrontierDenied(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise FrontierDenied("F139_FRONTIER_" + why)


def valid_hash(value: object, length: int) -> bool:
    pattern = HASH40 if length == 40 else HASH64
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def verify_proposal(row: object, source_sha: str) -> dict:
    """Check declared identities and authority fences; not Git attestations."""
    need(type(row) is dict and set(row) == ENTRY, "PROPOSAL_FIELDS_INVALID")
    need(type(row["lane"]) is str and row["lane"] in LANES
         and row["controller_source_sha"] == source_sha
         and valid_hash(row["target_commit"], 40)
         and valid_hash(row["target_tree_sha"], 40)
         and model_source_path_allowed(row["lane"], row["path"]),
         "PROPOSAL_TARGET_INVALID")
    for key in ("before_sha256", "after_sha256", "mechanism_sha256",
                "dependency_sha256", "qualification_harness_sha256",
                "suite_identity_sha256", "training_config_sha256",
                "frozen_split_sha256"):
        need(valid_hash(row[key], 64), "PROPOSAL_HASH_INVALID")
    need(row["after_sha256"] != row["before_sha256"], "NOOP_CANDIDATE")
    need(row["toolchain_identity"] == (
             "go1.25.0" if row["lane"] == "Wingless" else "python3.11.11"),
         "TOOLCHAIN_MISMATCH")
    need(row["scientific_first_use"] is False
         and all(type(row[key]) is int and row[key] == 0 for key in (
             "protected_holdouts_accessed", "paid_model_calls",
             "accepted_ref_mutations", "optimizer_policy_mutations")),
         "AUTHORITY_BOUNDARY_INVALID")
    return {"candidate_identity": digest(row), "proposal": row}


def choose_frontier(*, source_sha: str, catalog: list[dict],
                    history: list[dict]) -> dict:
    """Deterministically select at most one unconsumed proposal per lane.

    The caller must independently verify the catalog against exact Git blobs,
    source trees, dependency/harness/split pins, plus the *complete* authentic
    original owner event history (including negatives and ambiguous starts).
    The result is solely an inert plan. Missing history is not an admission.
    """
    need(valid_hash(source_sha, 40), "SOURCE_IDENTITY_INVALID")
    need(type(catalog) is list and 0 <= len(catalog) <= MAX_CATALOG
         and type(history) is list and 0 <= len(history) <= MAX_HISTORY,
         "UNBOUNDED_INPUT")
    consumed_ids, consumed_mechanisms, event_hashes = set(), set(), set()
    last_seq = 0
    result_counts = {lane: {o: 0 for o in sorted(OUTCOMES)} for lane in LANES}
    for item in history:
        need(type(item) is dict and set(item) == HISTORY,
             "HISTORY_FIELDS_INVALID")
        need(type(item["seq"]) is int and item["seq"] > last_seq
             and valid_hash(item["event_sha256"], 64)
             and item["event_sha256"] not in event_hashes
             and valid_hash(item["controller_source_sha"], 40)
             and type(item["lane"]) is str and item["lane"] in LANES
             and valid_hash(item["candidate_identity"], 64)
             and valid_hash(item["mechanism_sha256"], 64)
             and type(item["outcome"]) is str and item["outcome"] in OUTCOMES
             and valid_hash(item["evidence_sha256"], 64),
             "HISTORY_SOURCE_OR_ORDER_INVALID")
        need(item["candidate_identity"] not in consumed_ids
             and item["mechanism_sha256"] not in consumed_mechanisms,
             "HISTORY_REPLAY_OR_DUPLICATE")
        last_seq = item["seq"]
        event_hashes.add(item["event_sha256"])
        consumed_ids.add(item["candidate_identity"])
        consumed_mechanisms.add(item["mechanism_sha256"])
        result_counts[item["lane"]][item["outcome"]] += 1
    seen_ids, seen_mechanisms = set(), set()
    eligible = {lane: [] for lane in LANES}
    excluded = {lane: 0 for lane in LANES}
    for item in catalog:
        checked = verify_proposal(item, source_sha)
        cid, mech = checked["candidate_identity"], item["mechanism_sha256"]
        need(cid not in seen_ids and mech not in seen_mechanisms,
             "CATALOG_DUPLICATE")
        seen_ids.add(cid)
        seen_mechanisms.add(mech)
        lane = item["lane"]
        if cid in consumed_ids or mech in consumed_mechanisms:
            excluded[lane] += 1
        else:
            eligible[lane].append(checked)
    selected, abstentions = [], []
    for lane in LANES:
        candidates = eligible[lane]
        if not candidates:
            abstentions.append({"lane": lane, "reason": "NO_ELIGIBLE_CANDIDATE"})
            continue
        # No claimed scientific fitness: stable content-addressed order only.
        chosen = min(candidates, key=lambda x: x["candidate_identity"])
        p = chosen["proposal"]
        selected.append({
            "lane": lane, "candidate_identity": chosen["candidate_identity"],
            "mechanism_sha256": p["mechanism_sha256"],
            "target_commit": p["target_commit"],
            "target_tree_sha": p["target_tree_sha"],
            "path": p["path"], "after_sha256": p["after_sha256"],
            "reason": "DETERMINISTIC_UNCONSUMED_NOT_A_SCIENCE_RANK",
        })
    return {
        "schema": SCHEMA, "source_sha": source_sha,
        "catalog_sha256": digest(catalog), "history_sha256": digest(history),
        "selected": selected, "abstentions": abstentions,
        "consumed_history_count": len(history),
        "excluded_count_by_lane": excluded,
        "terminal_history_count_by_lane": result_counts,
        "publication_authorized": False, "dispatch_authorized": False,
        "scientific_first_use": False, "accepted_ref_mutations": 0,
        "paid_model_calls": 0, "new_controller": False,
        "source_generation_performed": False,
        "independent_source_authentication": "CALLER_REQUIRED",
        "new_scheduler": False, "new_queue": False,
    }

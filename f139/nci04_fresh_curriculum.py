"""Read-only, history-conditioned DEV candidate selector for the existing F139 owner.

This module is a *selection seam*, not a candidate author, custody verifier,
controller, queue, publisher, science evaluator or permission to execute.
The caller must first authenticate the original SQLite history with
read_lifecycle, authenticate each provider-backed proposal (including intent
bytes and source refs), and commit the publication attempt before any POST.
Do not feed untrusted issue text directly to this selector.
"""
from __future__ import annotations

import re

SCHEMA = "forge.f139.history-conditioned-dev-selector.v1"
PROPOSAL_SCHEMA = "forge.f139.qualified-dev-proposal.v1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
STAGES = frozenset({"READY", "START_RISK", "WAIT_PROVIDER", "NEGATIVE", "VERIFIED"})
HISTORY_FIELDS = frozenset({
    "after_sha256", "intent_sha256", "stage", "terminal_evidence_sha256",
})
PROPOSAL_FIELDS = frozenset({
    "schema", "source_sha", "target_tree_sha", "after_sha256",
    "intent_sha256", "mechanism_sha256", "qualification_sha256",
    "prerequisites", "exclusions", "cost_units", "development_only",
    "scientific_first_use", "paid_model_calls", "accepted_ref_mutations",
})


class CurriculumDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise CurriculumDenied("F139_CURRICULUM_" + reason)


def sha(value: object, width: int = 64) -> bool:
    return type(value) is str and bool((SHA40 if width == 40 else SHA64).fullmatch(value))


def hashes(value: object) -> bool:
    return (type(value) is list and len(value) <= 16
            and all(sha(v) for v in value)
            and len(value) == len(set(value)))


def select_next(*, history: list[dict], proposals: list[dict],
                source_sha: str, target_tree_sha: str,
                remaining_cost_units: int,
                spent_after_sha256: frozenset[str] = frozenset(),
                spent_intent_sha256: frozenset[str] = frozenset()) -> dict | None:
    """Select one unconsumed qualified DEV proposal; never create or post it.

    'VERIFIED' proves only a separately authenticated *development* terminal;
    it is deliberately not a scientific reward or model-quality metric.
    Other states consume identities, including uncertain outcomes. A verified
    prerequisite is required for dependent work; an excluded attempted
    identity blocks a candidate. No proposals means clean exhaustion.
    """
    need(sha(source_sha, 40) and sha(target_tree_sha, 40)
         and type(remaining_cost_units) is int
         and 0 <= remaining_cost_units <= 10000,
         "SOURCE_OR_BUDGET_INVALID")
    need(type(spent_after_sha256) is frozenset
         and type(spent_intent_sha256) is frozenset
         and len(spent_after_sha256) <= 10000
         and len(spent_intent_sha256) <= 10000
         and all(sha(v) for v in spent_after_sha256)
         and all(sha(v) for v in spent_intent_sha256),
         "SEALED_SPENT_IDENTITIES_INVALID")
    need(type(history) is list and 1 <= len(history) <= 4096
         and type(proposals) is list and len(proposals) <= 64,
         "BOUNDED_INPUT_INVALID")
    attempted: set[str] = set()
    seen_intents: set[str] = set()
    verified: set[str] = set()
    for row in history:
        need(type(row) is dict and set(row) == HISTORY_FIELDS
             and sha(row["after_sha256"]) and sha(row["intent_sha256"])
             and row["stage"] in STAGES
             and ((sha(row["terminal_evidence_sha256"]) and row["stage"] == "VERIFIED")
                  or (row["terminal_evidence_sha256"] is None
                      and row["stage"] != "VERIFIED")),
             "HISTORY_PROOF_SHAPE_INVALID")
        need(row["after_sha256"] not in attempted
             and row["intent_sha256"] not in seen_intents,
             "HISTORY_IDENTITY_REUSED")
        attempted.add(row["after_sha256"])
        seen_intents.add(row["intent_sha256"])
        if row["stage"] == "VERIFIED":
            verified.add(row["after_sha256"])

    # A prior CLAIM/POST of unknown outcome must never be bypassed by proposing
    # a different ticket. Only a separately audited terminal can clear this.
    need(history[-1]["stage"] == "VERIFIED", "LAST_TICKET_NOT_TERMINAL")
    seen_candidate_after: set[str] = set()
    seen_candidate_intents: set[str] = set()
    eligible: list[dict] = []
    for proposal in proposals:
        need(type(proposal) is dict and set(proposal) == PROPOSAL_FIELDS
             and proposal["schema"] == PROPOSAL_SCHEMA
             and proposal["source_sha"] == source_sha
             and proposal["target_tree_sha"] == target_tree_sha
             and all(sha(proposal[k]) for k in (
                 "after_sha256", "intent_sha256", "mechanism_sha256",
                 "qualification_sha256",
             ))
             and hashes(proposal["prerequisites"])
             and hashes(proposal["exclusions"])
             and type(proposal["cost_units"]) is int
             and 1 <= proposal["cost_units"] <= 1000
             and proposal["development_only"] is True
             and proposal["scientific_first_use"] is False
             and type(proposal["paid_model_calls"]) is int
             and proposal["paid_model_calls"] == 0
             and type(proposal["accepted_ref_mutations"]) is int
             and proposal["accepted_ref_mutations"] == 0,
             "UNQUALIFIED_OR_UNSAFE_PROPOSAL")
        after = proposal["after_sha256"]
        intent = proposal["intent_sha256"]
        need(after not in seen_candidate_after and intent not in seen_candidate_intents,
             "DUPLICATE_PROPOSAL_IDENTITY")
        seen_candidate_after.add(after)
        seen_candidate_intents.add(intent)
        need(not set(proposal["prerequisites"]).intersection(proposal["exclusions"]),
             "CONTRADICTORY_DEPENDENCIES")
        if (after in attempted or after in spent_after_sha256
                or intent in seen_intents or intent in spent_intent_sha256
                or proposal["cost_units"] > remaining_cost_units
                or not set(proposal["prerequisites"]).issubset(verified)
                or set(proposal["exclusions"]).intersection(attempted)):
            continue
        eligible.append(proposal)
    if not eligible:
        return None
    # Specific verified ancestry first; then least estimated work; stable tie.
    eligible.sort(key=lambda p: (-len(p["prerequisites"]), p["cost_units"],
                                 p["after_sha256"], p["intent_sha256"]))
    return dict(eligible[0])

"""NR-M2M: observation-only causal-prefix admissibility guard.

It processes only ORIGINAL ALREADY-SELECTED history through t-1, the exact
public observation at decision time t, and a caller-supplied proposal. It
cannot select a source action or infer unobserved counterfactual outcomes.
Retrospective MG56 DEV motifs are NOT calibration or model superiority.
"""
from __future__ import annotations

from nr_m2i_decision_evidence import canonical, sha256
from nr_m2j_source_cycles import (
    MAX_SELECTED, POLICIES, _frame, _is_original_event, public_digest
)

SCHEMA = "forge.nr-m2m.source-only-causal-prefix-proposal-advisory.v1"
STATUS = "EXPOSED_DEV_NO_SCIENTIFIC_FIRST_USE"
MOTIF_UNCALIBRATED = "DESCRIPTIVE_UNCALIBRATED_NO_COUNTERFACTUAL_REWARD"

def assess_prefix_proposal(selected_history, public_now, proposed_action):
    """Analyze a *proposed* action without selecting or vetoing it.

    selected_history strictly ends before proposal execution. Any source-owner
    authenticity must be separately attested by an original source custodian.
    """
    if (type(selected_history) is not list or
        len(selected_history) >= MAX_SELECTED or
        type(proposed_action) is not int or
        not 0 <= proposed_action <= 6):
        raise ValueError("M2M_ORIGINAL_SOURCE_PREFIX_OR_PROPOSAL_INVALID")
    current = _frame(public_now)
    current_sha = public_digest(current)
    last_sha, mission, policy = None, None, None
    for i, event in enumerate(selected_history, start=1):
        if i > 1 and (
            selected_history[i-2]["terminated"] or
            selected_history[i-2]["truncated"]
        ):
            raise ValueError("M2M_EVENT_AFTER_ORIGINAL_TERMINAL")
        if type(event) is not dict or type(event.get("policy_status")) is not str:
            raise ValueError("M2M_ORIGINAL_SOURCE_EVENT_SCHEMA_INVALID")
        _is_original_event(event, i, last_sha, mission, policy)
        if i == 1:
            mission, policy = event["mission"], event["policy_status"]
        last_sha = event["after_sha256"]
    if selected_history:
        tail = selected_history[-1]
        if tail["terminated"] or tail["truncated"]:
            raise ValueError("M2M_PROPOSAL_AFTER_ORIGINAL_TERMINAL")
        if current_sha != last_sha or current["mission"] != mission:
            raise ValueError("M2M_CURRENT_PUBLIC_SOURCE_NOT_CONTIGUOUS")
    history_actions = [e["action"] for e in selected_history]
    inverse_turn = (
        len(history_actions) >= 1 and
        history_actions[-1] in (0, 1) and
        proposed_action == 1 - history_actions[-1]
    )
    fourth_turn = (
        len(history_actions) >= 3 and
        proposed_action in (0, 1) and
        all(a == proposed_action for a in history_actions[-3:])
    )
    # Never embed the actual returned observation of the proposed action in
    # this decision-time receipt. No historical closed-cycle label imported.
    receipt = {
        "schema": SCHEMA,
        "status": STATUS,
        "source_owner_attestation": "NOT_ESTABLISHED_BY_SOURCE_ONLY_AUDIT",
        "prior_selected_action_count": len(history_actions),
        "current_original_public_sha256": current_sha,
        "proposed_action_only": proposed_action,
        "inverse_prior_selected_turn": inverse_turn,
        "fourth_consecutive_proposed_turn": fourth_turn,
        "observed_motif_calibration": MOTIF_UNCALIBRATED,
        "future_suffix_read": False,
        "future_result_predicted": False,
        "source_action_selected": False,
        "proposed_action_vetoed": False,
        "new_original_world_step": False,
        "scientific_gain_claimed": False,
    }
    receipt["decision_prefix_receipt_sha256"] = sha256(canonical({
        "selected_past_events": selected_history,
        "current_public_sha256": current_sha,
        "proposed_action": proposed_action,
        "advisory": receipt,
    }))
    return receipt

"""ITD-01 R6: strictly public, source-neutral causal event observation adapter.

This is an EXTERNAL IO CONTRACT, not a Wingless/Yggdrasil learner.
No hidden causal roles, original world source, private labels, source-family
metadata or simulated future observations enter this adapter.
"""
from __future__ import annotations
import hashlib
import json
import math
from public_dev import MAX_OBSERVATION, canonical, ContractViolation

NEUTRAL_SCHEMA = "itd01.observe-neutral.v1"
PUBLIC_SCHEMA = "itd01.observe.v1"
EVENT_SCHEMA = "itd01.public-event-neutral.v1"
EXPECTED_OBS = frozenset({
    "schema", "episode_id", "turn", "entities", "observations",
    "delayed_events", "public_goal", "interaction_budget_remaining"
})
ORIGINAL_EVENTS = {
    "relay_pulse": "observed-effect",
    "inflow_arrived": "observed-effect",
    "feed_pulse": "observed-effect",
    "dependence_pulse": "observed-effect",
    "relay_settled": "observed-confirmation",
    "resource_delivered": "observed-confirmation",
    "relay_stable": "observed-confirmation",
    "reservoir_balanced": "observed-confirmation",
    "goal_confirmed": "observed-confirmation",
    "ambient_drift": "incidental-observation",
}
VALID_EVENT_STATUS = frozenset({"partial", "ready", "settled", "confirmed", "idle"})
VALID_DIAGNOSTIC_SIGNAL = frozenset({"responsive", "idle"})


def _check(x, code):
    if not x:
        raise ContractViolation("ITD01_R6_" + code)


def _public_copy(value):
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ContractViolation("ITD01_R6_NOT_CANONICAL_PUBLIC_JSON") from None


def _validate_public_observation(obs):
    _check(type(obs) is dict and set(obs) == EXPECTED_OBS,
           "OBS_FIELDS_INVALID")
    _check(obs["schema"] == PUBLIC_SCHEMA, "OBS_SCHEMA_INVALID")
    _check(type(obs["episode_id"]) is str and obs["episode_id"].startswith("DEV-")
           and len(obs["episode_id"]) <= 64, "NON_DEV_EPISODE_BLOCKED")
    _check(type(obs["turn"]) is int and 0 <= obs["turn"] <= 41,
           "TURN_INVALID")
    _check(type(obs["interaction_budget_remaining"]) is int
           and obs["interaction_budget_remaining"] ==
           max(0, 40 - obs["turn"]), "BUDGET_INVALID")
    _check(type(obs["public_goal"]) is str and
           0 < len(obs["public_goal"]) <= 512, "PUBLIC_GOAL_INVALID")
    _check(type(obs["entities"]) is list and len(obs["entities"]) == 4,
           "PUBLIC_ENTITY_CATALOGUE_INVALID")
    names = []
    for entry in obs["entities"]:
        _check(type(entry) is dict and set(entry) == {"id", "legal_values"},
               "ENTITY_FIELDS_INVALID")
        _check(type(entry["id"]) is str and entry["id"].startswith("node")
               and len(entry["id"]) <= 24, "ENTITY_ID_INVALID")
        _check(type(entry["legal_values"]) is list
               and entry["legal_values"] in (["activate", "deactivate"], ["fill", "drain"]),
               "ENTITY_PUBLIC_ACTIONS_INVALID")
        names.append(entry["id"])
    _check(len(set(names)) == 4, "ENTITY_IDS_COLLIDE")
    _check(len({tuple(entry["legal_values"]) for entry in obs["entities"]}) == 1,
           "PUBLIC_ACTION_CATALOGUE_MISMATCH")
    _check(type(obs["delayed_events"]) is list and
           type(obs["observations"]) is list, "EVENT_COLLECTION_INVALID")
    _check(len(obs["delayed_events"]) <= 40 and len(obs["observations"]) <= 40,
           "EVENT_COLLECTION_TOO_LARGE")
    _check(len(canonical(obs)) <= MAX_OBSERVATION, "INPUT_OBSERVATION_TOO_LARGE")
    return names


def _normal_event(e, names):
    _check(type(e) is dict and set(e) == {"kind", "entity", "status"},
           "EVENT_FIELDS_INVALID")
    _check(type(e["kind"]) is str and e["kind"] in ORIGINAL_EVENTS,
           "UNKNOWN_OR_PROTECTED_EVENT_KIND")
    _check(type(e["entity"]) is str and e["entity"] in names,
           "EVENT_INVALID_PUBLIC_ENTITY")
    _check(type(e["status"]) is str and e["status"] in VALID_EVENT_STATUS,
           "EVENT_STATUS_INVALID")
    return {
        "schema": EVENT_SCHEMA,
        "type": ORIGINAL_EVENTS[e["kind"]],
        "entity": e["entity"],
        "observation": e["status"],
    }


def _normal_signal(s, names):
    _check(type(s) is dict, "PUBLIC_SIGNAL_INVALID")
    if set(s) == {"kind", "entity", "signal"}:
        _check(s["kind"] == "public_diagnostic", "UNKNOWN_PUBLIC_DIAGNOSTIC")
        _check(type(s["entity"]) is str and s["entity"] in names,
               "PUBLIC_SIGNAL_ENTITY_INVALID")
        _check(s["signal"] in VALID_DIAGNOSTIC_SIGNAL,
               "PUBLIC_DIAGNOSTIC_VALUE_INVALID")
        return {"type": "public-sensor", "entity": s["entity"],
                "observation": s["signal"]}
    if set(s) == {"kind", "status"} and s["kind"] == "invalid_action":
        _check(s["status"] == "rejected", "INVALID_ACTION_STATUS_INVALID")
        return {"type": "public-rejection", "observation": "rejected"}
    raise ContractViolation("ITD01_R6_UNKNOWN_OR_PRIVATE_SIGNAL")


def normalize_public_observation(raw: dict) -> dict:
    """One-way public DEV observation normalization. Fail closed."""
    raw = _public_copy(raw)
    names = _validate_public_observation(raw)
    normal = {
        "schema": NEUTRAL_SCHEMA,
        "episode_id": raw["episode_id"],
        "turn": raw["turn"],
        "entities": raw["entities"],
        "observations": [_normal_signal(s, names) for s in raw["observations"]],
        "events": [_normal_event(e, names) for e in raw["delayed_events"]],
        "public_goal": raw["public_goal"],
        "interaction_budget_remaining": raw["interaction_budget_remaining"],
    }
    _check(len(canonical(normal)) <= MAX_OBSERVATION, "NORMALIZED_OBSERVATION_TOO_LARGE")
    return normal


def public_observation_hash(normalized: dict) -> str:
    _check(type(normalized) is dict and normalized.get("schema") == NEUTRAL_SCHEMA,
           "NOT_NORMALIZED_PUBLIC_OBSERVATION")
    return hashlib.sha256(canonical(normalized)).hexdigest()


def public_transition_from_step(step_result: dict) -> dict:
    """All outputs remain public action/observed reward; no judge truth fields."""
    result = _public_copy(step_result)
    _check(type(result) is dict and
           set(result) == {"schema", "observation", "reward", "done"},
           "STEP_FIELDS_INVALID")
    _check(result["schema"] == "itd01.step.v1", "STEP_SCHEMA_INVALID")
    _check(type(result["reward"]) is int and result["reward"] in (0, 1),
           "STEP_PUBLIC_REWARD_INVALID")
    _check(type(result["done"]) is bool, "STEP_DONE_INVALID")
    return {
        "schema": "itd01.transition-neutral.v1",
        "observation": normalize_public_observation(result["observation"]),
        "reward": result["reward"],
        "done": result["done"],
    }


def is_executable_native_learner(candidate) -> bool:
    """API conformance only; NOT proof of a native architecture or learning."""
    if candidate is None:
        return False
    needed = ("reset_public", "step_public", "save_learned_state",
              "restore_learned_state", "learning_update_count")
    return all(callable(getattr(candidate, name, None)) for name in needed)

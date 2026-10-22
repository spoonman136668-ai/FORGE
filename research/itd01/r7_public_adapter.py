"""R7: strictly PUBLIC source-neutral causal event representation for R4 controls.

Human-designed abstraction used only at the external learner observation
boundary. It makes no claim of self-discovered ontology or independent science.
The raw public world response is never modified and no hidden role is supplied.
"""
from __future__ import annotations

import json
from public_dev import canonical
from r4_public_experience import PublicTranscript, get_action
from r5_causal_dev import R5CausalWorld
from r6_neutral_ontology import normalize_public_observation


def r4_compatible_public_observation(raw):
    neutral = normalize_public_observation(raw)
    original = json.loads(canonical(raw))
    events = []
    categories = {
        "observed-effect": "relay_pulse",
        "observed-confirmation": "relay_stable",
        "incidental-observation": "ambient_drift",
    }
    for event in neutral["events"]:
        kind = categories.get(event["type"])
        if kind is None:
            raise ValueError("ITD01_R7_UNKNOWN_NEUTRAL_EVENT")
        events.append({"kind": kind, "entity": event["entity"],
                       "status": event["observation"]})
    original["delayed_events"] = events
    return original


def r7_rollout_public_only(agent, family, seed, episode_id, mode="normal"):
    """The fitted agent only sees projected PUBLIC response dictionaries."""
    if mode not in ("normal","erase","blind_delayed"):
        raise ValueError("ITD01_R7_UNKNOWN_HISTORY_MODE")
    world = R5CausalWorld(family, episode_id, seed)
    original = json.loads(canonical(world.reset()))
    history = PublicTranscript(r4_compatible_public_observation(original))
    state = agent.init_state()
    illegal = False
    for _ in range(41):
        # Deep-clone transcript and its public events. An ablated policy never
        # receives the full history through a secondary object reference.
        from r5_history_boundary import isolated_public_view
        view = isolated_public_view(history, mode)
        if mode == "erase":
            state = agent.init_state()
        x = view.features()
        label, state = agent.choose(x, view, state)
        chosen = get_action(original, label)
        step = json.loads(canonical(world.step(chosen)))
        original = step["observation"]
        illegal |= any(e.get("kind") == "invalid_action"
                       for e in original.get("observations", []))
        history.ingest(chosen, r4_compatible_public_observation(original))
        if step["done"]:
            receipt=world.public_trace_receipt()
            if receipt["steps"]>41 or receipt["scientific_first_use"]:
                raise ValueError("ITD01_R7_PUBLIC_AUTHORITY_OR_BUDGET_DRIFT")
            return {"reward": int(step["reward"]), "steps": receipt["steps"],
                    "legal": not illegal,
                    "trace_sha256": receipt["trace_head_sha256"]}
    raise ValueError("ITD01_R7_PUBLIC_ACTION_CAP_BYPASS")

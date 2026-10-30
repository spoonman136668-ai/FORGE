"""NR-M2J: audit ONLY already-selected source-public action consequences.

A closed turn cycle is an observational pattern, never a model proposal or
unseen-action reward estimate. All input episodes remain EXPOSED DEV.
This source-only module cannot authenticate an original source owner or call
an environment, select actions, train a native model, or authorize first use.
"""
from __future__ import annotations

import json
import math
import re

from nr_m2i_decision_evidence import canonical, sha256

SCHEMA = "forge.nr-m2j.selected-original-public-information-yield.v1"
EXPOSED_ONLY = "READ_ONLY_EXPOSED_DEV_NOT_SCIENTIFIC_FIRST_USE"
MAX_SELECTED = 192
EVENT_KEYS = frozenset((
    "index", "before", "after", "action", "mission", "reward",
    "terminated", "truncated", "before_sha256", "after_sha256",
    "external_actions", "policy_status",
))
FRAME_KEYS = frozenset(("image", "direction", "mission"))
MISSION = re.compile(r"pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
POLICIES = frozenset((
    "MG56_OWN_SELECTED_NOVEL_GOAL_ON",
    "MG56_OWN_SELECTED_NOVEL_GOAL_OFF",
))

def _frame(frame):
    if type(frame) is not dict or set(frame) != FRAME_KEYS:
        raise ValueError("M2J_PUBLIC_ONLY_FRAME_REQUIRED")
    if (type(frame["direction"]) is not int or
        not 0 <= frame["direction"] <= 3 or
        type(frame["mission"]) is not str or
        MISSION.fullmatch(frame["mission"]) is None):
        raise ValueError("M2J_ORIGINAL_PUBLIC_MISSION_OR_HEADING_INVALID")
    rows = frame["image"]
    if type(rows) is not list or len(rows) != 7:
        raise ValueError("M2J_PUBLIC_IMAGE_SHAPE")
    for row in rows:
        if type(row) is not list or len(row) != 7:
            raise ValueError("M2J_PUBLIC_IMAGE_ROW")
        for pixel in row:
            if (type(pixel) is not list or len(pixel) != 3 or
                any(type(x) is not int or not 0 <= x <= 255 for x in pixel)):
                raise ValueError("M2J_PUBLIC_PIXEL_INVALID")
    return frame

def public_digest(frame):
    return sha256(canonical(_frame(frame)))

def symbolic_scene_key(frame):
    frame = _frame(frame)
    scene = sorted(tuple(cell) for row in frame["image"] for cell in row
                   if cell[0] not in (0, 1))
    # The original source uses this *exact canonical JSON representation*.
    return canonical([frame["mission"], scene]).decode("utf-8")

def _is_original_event(e, n, last_digest, mission, policy):
    if type(e) is not dict or set(e) != EVENT_KEYS:
        raise ValueError("M2J_MISSING_OR_EXTRA_SELECTED_EVENT")
    if type(e["index"]) is not int or e["index"] != n:
        raise ValueError("M2J_ORIGINAL_INDEX_NOT_SEQUENTIAL")
    if (type(e["action"]) is not int or not 0 <= e["action"] <= 6 or
        type(e["external_actions"]) is not int or e["external_actions"] != 0):
        raise ValueError("M2J_ORIGINAL_SELECTED_ACTION_INVALID")
    if e["policy_status"] not in POLICIES or (policy and e["policy_status"] != policy):
        raise ValueError("M2J_ORIGINAL_POLICY_ID_DRIFT")
    if (type(e["reward"]) not in (int, float) or
        not math.isfinite(e["reward"]) or
        type(e["terminated"]) is not bool or
        type(e["truncated"]) is not bool or
        (e["terminated"] and e["truncated"])):
        raise ValueError("M2J_ORIGINAL_REWARD_TERMINAL_INVALID")
    b, a = _frame(e["before"]), _frame(e["after"])
    if (type(e["mission"]) is not str or
        b["mission"] != a["mission"] or b["mission"] != e["mission"] or
        (mission is not None and e["mission"] != mission)):
        raise ValueError("M2J_ORIGINAL_PUBLIC_MISSION_CHANGED")
    if (type(e["before_sha256"]) is not str or
        type(e["after_sha256"]) is not str or
        HEX64.fullmatch(e["before_sha256"]) is None or
        HEX64.fullmatch(e["after_sha256"]) is None or
        public_digest(b) != e["before_sha256"] or
        public_digest(a) != e["after_sha256"]):
        raise ValueError("M2J_SELECTED_PUBLIC_SOURCE_SHA_DRIFT")
    if last_digest and e["before_sha256"] != last_digest:
        raise ValueError("M2J_SELECTED_ACTION_OBSERVATION_DISCONTINUITY")

def audit_exposed_episode(events, expected_source_events_sha256):
    """Validate and classify a whole selected original episode, never steps.

    expected_source_events_sha256 is externally supplied, *not* a signature.
    A forged owner claim cannot be redeemed by matching hashes.
    """
    if (type(expected_source_events_sha256) is not str or
        HEX64.fullmatch(expected_source_events_sha256) is None or
        type(events) is not list or not 1 <= len(events) <= MAX_SELECTED):
        raise ValueError("M2J_EPISODE_CUSTODY_MISSING")
    calculated_sha = sha256(canonical(events))
    if calculated_sha != expected_source_events_sha256:
        raise ValueError("M2J_ORIGINAL_EVENT_CHAIN_MISMATCH")
    prev = None
    mission = None
    policy = None
    public_seen = set()
    scene_seen = set()
    novel_exact, novel_scene = [], []
    goals = turns = forwards = 0
    for i, e in enumerate(events, start=1):
        if i > 1 and (events[i-2]["terminated"] or events[i-2]["truncated"]):
            raise ValueError("M2J_SELECTED_EVENT_AFTER_TERMINAL")
        _is_original_event(e, i, prev, mission, policy)
        if i == 1:
            mission = e["mission"]
            policy = e["policy_status"]
            public_seen.add(e["before_sha256"])
            scene_seen.add(symbolic_scene_key(e["before"]))
        after_hash = e["after_sha256"]
        after_scene = symbolic_scene_key(e["after"])
        novel_exact.append(after_hash not in public_seen)
        novel_scene.append(after_scene not in scene_seen)
        public_seen.add(after_hash)
        scene_seen.add(after_scene)
        prev = after_hash
        turns += int(e["action"] in (0, 1))
        forwards += int(e["action"] == 2)
        goals += int(e["reward"] > 0 and e["terminated"])
    cycles = []
    p = 0
    while p < len(events):
        first_action = events[p]["action"]
        kind = None
        n = 0
        if (p + 1 < len(events) and first_action in (0, 1) and
            events[p+1]["action"] == 1-first_action and
            events[p]["before_sha256"] == events[p+1]["after_sha256"]):
            kind, n = "TWO_STEP_OPPOSING_TURNS", 2
        elif (p + 3 < len(events) and first_action in (0, 1) and
              all(events[p+j]["action"] == first_action for j in (1, 2, 3)) and
              events[p]["before_sha256"] == events[p+3]["after_sha256"]):
            kind, n = "FOUR_STEP_SAME_DIRECTION_ROTATION", 4
        if n:
            # Novelty is evaluated strictly online at each true selected
            # after-observation, not from the future or across episodes.
            cycles.append({
                "start_selected_event": p+1,
                "length_selected_actions": n,
                "kind": kind,
                "any_new_exact_public_view": any(novel_exact[p:p+n]),
                "any_new_original_symbolic_scene": any(novel_scene[p:p+n]),
            })
            p += n  # disjoint by construction
        else:
            p += 1
    cycle_actions = sum(c["length_selected_actions"] for c in cycles)
    no_exact = sum(c["length_selected_actions"] for c in cycles
                   if not c["any_new_exact_public_view"])
    no_scene = sum(c["length_selected_actions"] for c in cycles
                   if not c["any_new_original_symbolic_scene"])
    if not 0 <= no_exact <= cycle_actions <= len(events) or not 0 <= no_scene <= cycle_actions:
        raise ValueError("M2J_CLOSED_CYCLE_NONOVERLAP_VIOLATED")
    return {
        "schema": SCHEMA, "source_status": EXPOSED_ONLY,
        "source_owner_attestation": "EXTERNAL_SOURCE_OWNER_REQUIRED",
        "source_episode_sha256": calculated_sha,
        "selected_original_actions": len(events),
        "source_selected_turn_actions": turns,
        "source_selected_forward_actions": forwards,
        "positive_original_terminal_goal_steps": goals,
        "two_step_cycles": sum(c["length_selected_actions"] == 2 for c in cycles),
        "four_step_cycles": sum(c["length_selected_actions"] == 4 for c in cycles),
        "closed_cycle_action_cost": cycle_actions,
        "closed_cycle_zero_new_exact_public_action_cost": no_exact,
        "closed_cycle_zero_new_symbolic_scene_action_cost": no_scene,
        "cycles": cycles,
        "new_action_selected": False,
        "original_environment_executed": False,
        "counterfactual_task_improvement_claimed": False,
    }

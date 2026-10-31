"""Source-only 7-action DoorKey public-observation boundary.

No use of env.grid, env.carrying, agent_pos or hidden door/key state.
Unchanged R7/R8/R9 remain three-action learners; this is *transport*, not
causal learning or permission to execute a protected physical episode.
"""
from __future__ import annotations

import hashlib
import json
import math

SCHEMA = "yggdrasil.itd02.r10.public-doorkey-seven-action.v1"
ACTION_NAMES = ("left", "right", "forward", "pickup", "drop", "toggle", "done")
MISSION = "use the key to open the door and then get to the goal"
VIEW_SIZE = 7
AGENT_CELL = (3, 6)
FRONT_CELL = (3, 5)
MAX_EPISODE_ACTIONS = 4096
MAX_LEDGER = 64
MAX_SNAPSHOT = 250000
UPSTREAM_MINIGRID_COMMIT = "7f5853792ea7f04f75614661006d87fcf949f26d"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _image_lists(image):
    if type(image).__module__ == "numpy" and type(image).__name__ == "ndarray":
        image = image.tolist()  # Only source-public ndarray to JSON-native copy.
    if type(image) not in (tuple, list) or len(image) != VIEW_SIZE:
        raise ValueError("R10_PUBLIC_IMAGE_SHAPE")
    validated = []
    for row in image:
        if type(row) not in (tuple, list) or len(row) != VIEW_SIZE:
            raise ValueError("R10_PUBLIC_IMAGE_ROW")
        new_row = []
        for pixel in row:
            if type(pixel) not in (tuple, list) or len(pixel) != 3:
                raise ValueError("R10_PUBLIC_IMAGE_PIXEL")
            if any(type(i) is not int for i in pixel):
                raise ValueError("R10_PUBLIC_IMAGE_TYPE")
            kind, color, state = pixel
            if not (0 <= kind <= 10 and 0 <= color <= 5 and 0 <= state <= 255):
                raise ValueError("R10_PUBLIC_IMAGE_RANGE")
            if kind == 4 and state not in (0, 1, 2):
                raise ValueError("R10_PUBLIC_DOOR_STATE")
            new_row.append([kind, color, state])
        validated.append(new_row)
    return validated


def public_observation(obs):
    """Accept ONLY the original image/direction/mission from gen_obs()."""
    if type(obs) is not dict or set(obs) != {"image", "direction", "mission"}:
        raise ValueError("R10_UNTRUSTED_OR_PRIVILEGED_OBSERVATION")
    direction, mission = obs["direction"], obs["mission"]
    if type(direction) is not int or direction not in (0, 1, 2, 3):
        raise ValueError("R10_PUBLIC_DIRECTION")
    if type(mission) is not str or mission != MISSION:
        raise ValueError("R10_PUBLIC_MISSION")
    return {"image": _image_lists(obs["image"]), "direction": direction, "mission": mission}


def public_cues(obs):
    frame = public_observation(obs)
    image = frame["image"]
    front = image[FRONT_CELL[0]][FRONT_CELL[1]]
    carried = image[AGENT_CELL[0]][AGENT_CELL[1]]
    # Object stored here by upstream gen_obs_grid IF AND ONLY IF carried.
    # Never read env.carrying, agent_pos, Grid or an evaluator-owned object.
    return {"front": front, "carried": carried if carried[0] in (5, 6, 7) else None,
            "direction": frame["direction"], "observation_sha256": digest(frame)}


class DoorKeyPublicAdapter:
    """Transactional source-public action→returned-outcome ledger, no policy oracle."""

    def __init__(self):
        self.initial = None
        self.current = None
        self.pending = None
        self.events = 0
        self.terminal = False
        self.ledger = []

    def reset_public(self, observation):
        frame = public_observation(observation)
        if self.pending is not None:
            raise ValueError("R10_RESET_WITH_UNRETURNED_ACTION")
        self.initial = frame
        self.current = frame
        self.pending = None
        self.events = 0
        self.terminal = False
        self.ledger = []

    def submit(self, action):
        if self.current is None or self.pending is not None or self.terminal:
            raise ValueError("R10_ACTION_ILLEGAL_PHASE")
        if type(action) is not int or not 0 <= action < len(ACTION_NAMES):
            raise ValueError("R10_UNSUPPORTED_OR_INVALID_ACTION")
        if self.events >= MAX_EPISODE_ACTIONS:
            raise ValueError("R10_SOURCE_ACTION_BUDGET_EXCEEDED")
        self.pending = action
        return action  # Exact upstream action identity, never cast through R7/R9.

    def complete(self, observation, reward, terminated, truncated):
        if self.pending is None or self.current is None or self.terminal:
            raise ValueError("R10_NO_OUTSTANDING_SOURCE_ACTION")
        # All validation before any mutable state is changed.
        next_frame = public_observation(observation)
        if type(reward) not in (int, float) or not math.isfinite(reward) or not -1 <= reward <= 1:
            raise ValueError("R10_SOURCE_REWARD_INVALID")
        if type(terminated) is not bool or type(truncated) is not bool:
            raise ValueError("R10_SOURCE_TERMINATION_INVALID")
        action = self.pending
        before = public_cues(self.current)
        after = public_cues(next_frame)
        previous_door = before["front"] if before["front"][0] == 4 else None
        current_door = after["front"] if after["front"][0] == 4 else None
        # These are observations, NOT inferred privileged causal truths.
        visible_door_opened = (action == 5 and previous_door is not None and
                               current_door is not None and previous_door[1] == current_door[1] and
                               previous_door[2] in (1, 2) and current_door[2] == 0 and
                               before["direction"] == after["direction"])
        visible_pickup = (action == 3 and before["carried"] is None and
                          after["carried"] is not None)
        event = {"ordinal": self.events + 1, "action": action, "action_name": ACTION_NAMES[action],
                 "before_public_sha256": before["observation_sha256"],
                 "after_public_sha256": after["observation_sha256"],
                 "front_before": before["front"], "front_after": after["front"],
                 "carried_before": before["carried"], "carried_after": after["carried"],
                 "heading_before": before["direction"], "heading_after": after["direction"],
                 "visible_key_pickup": visible_pickup, "visible_door_opened": visible_door_opened,
                 "pose_delta": None,  # Absolute pose NOT present in original public gen_obs.
                 "reward": float(reward), "terminated": terminated, "truncated": truncated}
        self.current = next_frame
        self.pending = None
        self.events += 1
        self.terminal = terminated or truncated
        self.ledger = (self.ledger + [event])[-MAX_LEDGER:]
        return event

    def checkpoint(self):
        state = {"schema": SCHEMA, "upstream": UPSTREAM_MINIGRID_COMMIT,
                 "initial": self.initial, "current": self.current, "pending": self.pending,
                 "events": self.events, "terminal": self.terminal, "ledger": self.ledger}
        raw = canonical(state)
        if len(raw) > MAX_SNAPSHOT:
            raise ValueError("R10_CHECKPOINT_TOO_LARGE")
        return canonical({"state": state, "sha256": hashlib.sha256(raw).hexdigest()})

    @classmethod
    def restore(cls, blob):
        try:
            if type(blob) is not bytes or not 0 < len(blob) <= MAX_SNAPSHOT:
                raise ValueError("R10_RESTORE_BYTES_INVALID")
            obj = json.loads(blob)
            if type(obj) is not dict or set(obj) != {"state", "sha256"}:
                raise ValueError("R10_RESTORE_ENVELOPE")
            state = obj["state"]
            if type(state) is not dict or hashlib.sha256(canonical(state)).hexdigest() != obj["sha256"]:
                raise ValueError("R10_CHECKPOINT_SHA_INVALID")
            if (set(state) != {"schema", "upstream", "initial", "current", "pending", "events", "terminal", "ledger"} or
                state["schema"] != SCHEMA or state["upstream"] != UPSTREAM_MINIGRID_COMMIT or
                type(state["events"]) is not int or not 0 <= state["events"] <= MAX_EPISODE_ACTIONS or
                type(state["terminal"]) is not bool or
                (state["pending"] is not None and (type(state["pending"]) is not int or not 0 <= state["pending"] <= 6)) or
                (state["terminal"] and state["pending"] is not None) or
                type(state["ledger"]) is not list or len(state["ledger"]) > MAX_LEDGER or
                len(state["ledger"]) > state["events"]):
                raise ValueError("R10_RESTORE_SCHEMA_INVALID")
            if (state["initial"] is None) != (state["current"] is None):
                raise ValueError("R10_RESTORE_EPISODE_INVALID")
            if state["initial"] is None and (state["pending"] is not None or state["events"] or state["terminal"] or state["ledger"]):
                raise ValueError("R10_RESTORE_UNINITIALIZED_INVALID")
            if state["initial"] is not None:
                if public_observation(state["initial"]) != state["initial"] or public_observation(state["current"]) != state["current"]:
                    raise ValueError("R10_RESTORE_PUBLIC_IMAGE_DRIFT")
            for index, entry in enumerate(state["ledger"]):
                if (type(entry) is not dict or type(entry.get("ordinal")) is not int or
                    entry["ordinal"] != state["events"] - len(state["ledger"]) + index + 1 or
                    type(entry.get("action")) is not int or not 0 <= entry["action"] <= 6 or
                    entry.get("action_name") != ACTION_NAMES[entry["action"]] or
                    type(entry.get("reward")) is not float or not math.isfinite(entry["reward"]) or
                    not -1 <= entry["reward"] <= 1 or
                    type(entry.get("terminated")) is not bool or type(entry.get("truncated")) is not bool or
                    type(entry.get("visible_key_pickup")) is not bool or type(entry.get("visible_door_opened")) is not bool or
                    entry.get("pose_delta") is not None):
                    raise ValueError("R10_RESTORE_LEDGER_INVALID")
                for field in ("before_public_sha256", "after_public_sha256"):
                    h = entry.get(field)
                    if type(h) is not str or len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h):
                        raise ValueError("R10_RESTORE_SOURCE_DIGEST_INVALID")
                if index and state["ledger"][index - 1]["after_public_sha256"] != entry["before_public_sha256"]:
                    raise ValueError("R10_RESTORE_EVENT_CHAIN_INVALID")
            if state["ledger"] and state["ledger"][-1]["after_public_sha256"] != digest(state["current"]):
                raise ValueError("R10_RESTORE_LAST_OBSERVATION_MISMATCH")
            if state["ledger"] and state["terminal"] != (state["ledger"][-1]["terminated"] or state["ledger"][-1]["truncated"]):
                raise ValueError("R10_RESTORE_TERMINAL_MISMATCH")
            out = cls()
            for k in ("initial", "current", "pending", "events", "terminal", "ledger"):
                setattr(out, k, state[k])
            return out
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
            raise ValueError("R10_UNTRUSTED_CHECKPOINT") from exc

#!/usr/bin/env python3
"""E-D116: source-informed, observation-only matched Memory junction probe.

ENGINEERING / EXPOSED SEEDS ONLY. An engineered register is not learned memory.
No environment internals, hidden maps, scientific first-use or holdout access.
"""
from __future__ import annotations

import hashlib
import json

import gymnasium as gym
import minigrid
from minigrid.core.constants import OBJECT_TO_IDX

ENV = "MiniGrid-MemoryS13Random-v0"
SEEDS = (84000, 84001, 84002, 84003)  # already exposed smoke seeds
EXPECTED_VERSION = "3.2.0"
KEY = OBJECT_TO_IDX["key"]
BALL = OBJECT_TO_IDX["ball"]
WALL = OBJECT_TO_IDX["wall"]
OBJECTS = {KEY, BALL}
LIMIT = 128


def branch(cue, north, south, remember):
    """The sole policy difference is whether the observed west cue survives."""
    if north not in OBJECTS or south not in OBJECTS or north == south:
        return None
    if remember:
        if cue not in OBJECTS:
            return None
        return "north" if cue == north else "south" if cue == south else None
    return "north"  # fixed, cue-erased control; no privileged information


def episode(seed, remember):
    env = gym.make(ENV, render_mode=None)
    actions = []
    events = []
    done = truncated = False
    reward = 0.0
    obs, info = env.reset(seed=seed)
    assert isinstance(info, dict)
    assert int(obs["direction"]) == 0, "source-informed start orientation drift"
    status = "ABSTAIN_UNCLASSIFIED"
    cue = north = south = None
    prechoice = None
    selected = None

    def take(action):
        nonlocal obs, reward, done, truncated
        assert not (done or truncated), "action after terminal"
        assert len(actions) < LIMIT, "engineering action budget"
        obs, reward, done, truncated, info = env.step(action)
        assert isinstance(info, dict)
        actions.append(int(action))
        events.append([int(action),
                       hashlib.sha256(obs["image"].tobytes()).hexdigest(),
                       int(obs["direction"]), float(reward),
                       bool(done), bool(truncated)])

    def front():
        return int(obs["image"][3, 5, 0])

    def two_ahead():
        return int(obs["image"][3, 4, 0])

    def digest(rows):
        return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    try:
        if minigrid.__version__ != EXPECTED_VERSION:
            raise AssertionError("MiniGrid version drift")
        assert obs["image"].shape == (7, 7, 3)

        # West-wall localization from reset/step observations. The authentic
        # upstream geometry has a start-room object one cell north of the
        # westernmost traversable centerline cell. No env.unwrapped access.
        take(0)
        take(0)
        while not (done or truncated) and front() != WALL and len(actions) < LIMIT - 20:
            take(2)
        if done or truncated or front() != WALL:
            status = "ABSTAIN_WEST_WALL"
        else:
            take(1)  # west -> north; inspect the immediate source-informed landmark
            cue = front()
            if cue not in OBJECTS:
                status = "ABSTAIN_WEST_CUE_NOT_VISIBLE"
            else:
                take(1)  # north -> east; navigate common centerline to eastern wall
                while not (done or truncated) and front() != WALL and len(actions) < LIMIT - 10:
                    take(2)
                if done or truncated or front() != WALL:
                    status = "ABSTAIN_EAST_WALL"
                else:
                    take(0)  # east -> north; view object two cells ahead
                    north = two_ahead()
                    take(1)
                    take(1)  # north -> east -> south
                    south = two_ahead()
                    prechoice = digest(events)
                    selected = branch(cue, north, south, remember)
                    if selected is None:
                        status = "ABSTAIN_BRANCH_UNOBSERVABLE"
                    else:
                        if selected == "north":
                            take(1)
                            take(1)  # south -> west -> north
                        take(2)  # enter matching/nonmatching target-side cell
                        status = "TERMINATED" if done and not truncated else "ABSTAIN_NO_TERMINAL"
        return {
            "seed": seed,
            "remember": bool(remember),
            "status": status,
            "west_cue": cue,
            "north_object": north,
            "south_object": south,
            "selected": selected,
            "prechoice_sha256": prechoice,
            "reward": float(reward),
            "terminated": bool(done),
            "truncated": bool(truncated),
            "actions": len(actions),
            "trace_sha256": digest(events),
        }
    finally:
        env.close()


def main():
    # A deliberate non-learning causal intervention at the choice boundary.
    assert branch(KEY, KEY, BALL, True) == "north"
    assert branch(KEY, BALL, KEY, True) == "south"
    assert branch(KEY, BALL, KEY, False) == "north"
    assert branch(None, KEY, BALL, True) is None
    assert branch(KEY, BALL, BALL, True) is None

    rows = []
    for seed in SEEDS:
        erased = episode(seed, False)
        retained = episode(seed, True)
        assert erased == episode(seed, False), "non-deterministic erased replay"
        assert retained == episode(seed, True), "non-deterministic retained replay"
        assert erased["prechoice_sha256"] == retained["prechoice_sha256"], (
            "not an identical predecision observation/action history", seed
        )
        rows.append({
            "seed": seed,
            "erased": erased,
            "retained": retained,
            "reward_delta": retained["reward"] - erased["reward"],
        })
    print(json.dumps({
        "status": "PASS_ENGINEERING_MEMORY_CAUSAL_JUNCTION_PROBE",
        "scope": "EXPOSED_SEEDS_ONLY",
        "environment": ENV,
        "source_version": minigrid.__version__,
        "warning": "ENGINEERED_SOURCE_GEOMETRY_NOT_LEARNING_NOT_INDEPENDENT_CUE_AUTHENTICATION_NOT_SCIENCE",
        "rows": rows,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

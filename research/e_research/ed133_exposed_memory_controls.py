#!/usr/bin/env python3
"""E-D133: strong fixed-direction and wrong-cue controls, EXPOSED seeds only.

This is a follow-up engineering falsification study, not scientific first-use,
native learning, new prospective split, unfamiliar-family transfer, or holdout.
Reuses the E-D116 observation-only navigator and its default behavior unchanged.
"""
from __future__ import annotations

import json
import math

import minigrid
from ed116_memory_causal_junction import (
    ENV, SEEDS, LIMIT, EXPECTED_VERSION, OBJECTS, episode,
)

ARMS = (
    ("fixed_north", {"remember": False}),
    ("fixed_south", {"remember": False, "erased_choice": "south"}),
    ("retained_cue", {"remember": True}),
    ("inverted_cue", {"remember": True, "corrupt_cue": True}),
)


def trial(seed):
    arms = {}
    for label, kwargs in ARMS:
        first = episode(seed, **kwargs)
        repeated = episode(seed, **kwargs)
        assert first == repeated, (seed, label, "NON_DETERMINISTIC")
        arms[label] = first

    expected_prefix = arms["retained_cue"]["prechoice_sha256"]
    assert expected_prefix is not None, (seed, "MISSING_CHOICE")
    assert all(v["prechoice_sha256"] == expected_prefix for v in arms.values()), (
        seed, "MISMATCHED_PRECHOICE_HISTORY"
    )
    west = arms["retained_cue"]["west_cue"]
    north = arms["retained_cue"]["north_object"]
    south = arms["retained_cue"]["south_object"]
    assert west in OBJECTS and north in OBJECTS and south in OBJECTS and north != south, (
        seed, "UNOBSERVED_OR_AMBIGUOUS_CUE"
    )
    assert all(
        a["west_cue"] == west
        and a["north_object"] == north
        and a["south_object"] == south
        and a["status"] == "TERMINATED"
        and a["terminated"] is True
        and a["truncated"] is False
        and 0 < a["actions"] <= LIMIT
        and math.isfinite(a["reward"])
        for a in arms.values()
    ), (seed, "INVALID_TERMINAL_CONTROL_PAIR")

    assert arms["fixed_north"]["selected"] == "north"
    assert arms["fixed_south"]["selected"] == "south"
    assert arms["retained_cue"]["selected"] in ("north", "south")
    assert arms["inverted_cue"]["selected"] != arms["retained_cue"]["selected"]

    return {
        "seed": seed,
        "common_prechoice_sha256": expected_prefix,
        "source_informed_visible_west_cue": west,
        "visible_north_object": north,
        "visible_south_object": south,
        "arms": {
            name: {
                "choice": a["selected"],
                "reward": a["reward"],
                "actions": a["actions"],
                "trace_sha256": a["trace_sha256"],
            } for name, a in arms.items()
        },
        "retained_minus_fixed_north": arms["retained_cue"]["reward"] - arms["fixed_north"]["reward"],
        "retained_minus_fixed_south": arms["retained_cue"]["reward"] - arms["fixed_south"]["reward"],
        "retained_minus_wrong_cue": arms["retained_cue"]["reward"] - arms["inverted_cue"]["reward"],
    }


def main():
    assert minigrid.__version__ == EXPECTED_VERSION, "UPSTREAM_RUNTIME_VERSION_DRIFT"
    assert SEEDS == (84000, 84001, 84002, 84003), "EXPOSED_SEED_SCOPE_DRIFT"
    rows = [trial(seed) for seed in SEEDS]
    n = len(rows)
    assert n == len(SEEDS)
    summary = {
        name: {
            "mean_reward": sum(r["arms"][name]["reward"] for r in rows) / n,
            "positive_reward_episodes": sum(r["arms"][name]["reward"] > 0 for r in rows),
            "mean_actions": sum(r["arms"][name]["actions"] for r in rows) / n,
        } for name, _ in ARMS
    }
    print(json.dumps({
        "status": "PASS_EXPOSED_MEMORY_CONTROL_STRESS_ENGINEERING_ONLY",
        "source_version": minigrid.__version__,
        "environment": ENV,
        "scope": "FOUR_ALREADY_EXPOSED_SEEDS_NO_PROSPECTIVE_OR_HOLDOUT",
        "not_native_learning": True,
        "not_scientific_first_use": True,
        "source_geometry_informed_navigation": True,
        "matched_terminal_episode_count": n,
        "summary": summary,
        "rows": rows,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

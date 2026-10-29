#!/usr/bin/env python3
"""MG17: authentic, quarantined MiniGrid family source smoke (NOT model evaluation).

Runs original upstream reset/step with deterministic non-learning smoke actions.
The selected-action native adapter remains unchanged. These source-smoke events
may NEVER be used for FIT, DEV, sealed evaluation or scientific acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import operator
import random
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
PREREG = HERE / "mg17_original_family_source_prereg.json"
EXPECTED_UPSTREAM = "7f5853792ea7f04f75614661006d87fcf949f26d"
EXPECTED_IDS = (
    ("MiniGrid-DoorKey-6x6-v0", "minigrid.envs:DoorKeyEnv"),
    ("MiniGrid-UnlockPickup-v0", "minigrid.envs:UnlockPickupEnv"),
    ("MiniGrid-BlockedUnlockPickup-v0", "minigrid.envs:BlockedUnlockPickupEnv"),
    ("MiniGrid-KeyCorridorS3R1-v0", "minigrid.envs:KeyCorridorEnv"),
)
SOURCE_ONLY = "PROSPECTIVE_SOURCE_QUALIFICATION_ONLY_NO_FIT_DEV_SEALED_OR_SCIENCE"


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()


def run_git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   text=True, stderr=subprocess.PIPE).strip()


def frozen():
    data = json.loads(PREREG.read_text(encoding="utf-8"))
    source = data["source"]
    qual = data["qualification"]
    if (data["schema"] != "itd02.mg17.original-minigrid-source-family-smoke.v1"
        or data["phase"] != SOURCE_ONLY
        or source["repo"] != "Farama-Foundation/Minigrid"
        or source["commit"] != EXPECTED_UPSTREAM
        or [(x["id"], x["entry_point"]) for x in data["families"]] != list(EXPECTED_IDS)
        or qual["replay_seeds"] != [917001, 917003]
        or qual["max_actions_per_seed"] != 12
        or qual["source_action_count"] != 7
        or qual["public_fields"] != ["image", "direction", "mission"]
        or qual["smoke_seeds_disqualified_from_fit_dev_sealed"] is not True
        or qual["source_authentic_no_reward_shaping"] is not True
        or not all(data["boundaries"].values())):
        raise ValueError("MG17_SOURCE_ONLY_PREREG_DRIFT")
    return data


def attest_source(root, data):
    if run_git(root, "rev-parse", "HEAD") != EXPECTED_UPSTREAM:
        raise ValueError("MG17_WRONG_ORIGINAL_FARAMA_COMMIT")
    for path, expected in sorted(data["source"]["git_blob_sha1"].items()):
        actual = run_git(root, "hash-object", path)
        if actual != expected:
            raise ValueError("MG17_ORIGINAL_SOURCE_BLOB_DRIFT:" + path)


def public(obs):
    if not isinstance(obs, dict) or not all(k in obs for k in
                                             ("image", "direction", "mission")):
        raise ValueError("MG17_MISSING_ORIGINAL_PUBLIC_FIELD")
    img = obs["image"]
    if hasattr(img, "tolist"):
        img = img.tolist()
    if (not isinstance(img, list) or len(img) != 7 or
        any(not isinstance(row, list) or len(row) != 7 for row in img) or
        any(not isinstance(cell, list) or len(cell) != 3 or
            any(type(v) is not int or v < 0 or v > 255 for v in cell)
            for row in img for cell in row)):
        raise ValueError("MG17_NOT_ORIGINAL_7X7X3_PUBLIC_IMAGE")
    try:
        direction = operator.index(obs["direction"])  # preserves source numpy integer
    except TypeError as e:
        raise ValueError("MG17_NONINTEGRAL_ORIGINAL_PUBLIC_DIRECTION") from e
    if direction not in range(4):
        raise ValueError("MG17_INVALID_ORIGINAL_PUBLIC_DIRECTION")
    mission = obs["mission"]
    if type(mission) is not str or not mission.strip():
        raise ValueError("MG17_MISSING_ORIGINAL_PUBLIC_MISSION")
    return {"image": img, "direction": direction, "mission": mission}


def smoke(root, data):
    import gymnasium as gym
    import minigrid
    if not Path(minigrid.__file__).resolve().is_relative_to(root.resolve()):
        raise ValueError("MG17_IMPORT_NOT_PINNED_UPSTREAM_CHECKOUT")
    results = []
    for family in data["families"]:
        name = family["id"]
        spec = gym.spec(name)
        if spec.entry_point != family["entry_point"]:
            raise ValueError("MG17_GYM_REGISTRY_OR_ENTRYPOINT_DRIFT:" + name)
        env = gym.make(name)
        try:
            if getattr(env.action_space, "n", None) != 7:
                raise ValueError("MG17_NONORIGINAL_ACTION_SCHEMA:" + name)
            for seed in data["qualification"]["replay_seeds"]:
                raw, _info = env.reset(seed=seed)
                first = public(raw)
                prior = first
                rng = random.Random(f"mg17-source-smoke:{name}:{seed}")
                events = []
                for sequence in range(1, 1 + data["qualification"]["max_actions_per_seed"]):
                    chosen = rng.randrange(7)  # explicitly non-learning, quarantined
                    next_raw, reward, terminated, truncated, _info = env.step(chosen)
                    after = public(next_raw)
                    if after["mission"] != first["mission"]:
                        raise ValueError("MG17_SOURCE_MISSION_CHANGED")
                    value = float(reward)
                    if not math.isfinite(value):
                        raise ValueError("MG17_NONFINITE_SOURCE_REWARD")
                    if type(terminated) is not bool or type(truncated) is not bool:
                        raise ValueError("MG17_INVALID_ORIGINAL_TERMINATION")
                    events.append({
                        "index": sequence,
                        "before": prior,
                        "source_action": chosen,
                        "after": after,
                        "original_reward": value,
                        "terminated": terminated,
                        "truncated": truncated,
                        "before_sha256": digest(prior),
                        "after_sha256": digest(after),
                        "policy": "QUARANTINED_SOURCE_SMOKE_RANDOM_NOT_AGENT",
                    })
                    prior = after
                    if terminated or truncated:
                        break
                results.append({"environment": name, "smoke_seed_not_eligible": seed,
                                "original_mission": first["mission"],
                                "original_selected_source_events": events,
                                "trace_sha256": digest(events)})
        finally:
            env.close()
    envelope = {
        "schema": "itd02.mg17.original-source-qualification-replay.v1",
        "source_commit": EXPECTED_UPSTREAM,
        "source_blobs": data["source"]["git_blob_sha1"],
        "scope": "ENGINEERING_SOURCE_SMOKE_NO_NATIVE_TRAINING_NO_SCIENCE",
        "records": results,
    }
    envelope["canonical_trace_sha256"] = digest(results)
    return envelope


def compare(a, b):
    first = json.loads(Path(a).read_text(encoding="utf-8"))
    second = json.loads(Path(b).read_text(encoding="utf-8"))
    if (first != second or first.get("schema") !=
        "itd02.mg17.original-source-qualification-replay.v1"
        or first.get("source_commit") != EXPECTED_UPSTREAM
        or first.get("scope") != "ENGINEERING_SOURCE_SMOKE_NO_NATIVE_TRAINING_NO_SCIENCE"
        or len(first.get("records", [])) != 8
        or first["canonical_trace_sha256"] != digest(first["records"])
        or any(record["trace_sha256"] != digest(record["original_selected_source_events"])
               for record in first["records"])):
        raise ValueError("MG17_INDEPENDENT_ORIGINAL_SOURCE_REPLAY_MISMATCH")
    return first["canonical_trace_sha256"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, metavar=("REPLAY_A", "REPLAY_B"))
    args = parser.parse_args()
    if args.compare:
        print("MG17_INDEPENDENT_SOURCE_REPLAY_PASS_NO_SCIENCE " +
              compare(*args.compare))
        return
    if args.source_root is None or args.output is None:
        parser.error("require --source-root and --output, or --compare")
    prereg = frozen()
    attest_source(args.source_root.resolve(), prereg)
    report = smoke(args.source_root.resolve(), prereg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("MG17_SOURCE_SMOKE_NOT_SCIENCE " + report["canonical_trace_sha256"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MG32: read-only retrospective audit of already-exposed MG31 original public source.

Never starts MiniGrid, executes env.step, modifies native actors, selects a model,
or claims scientific first use. Original MG31 source bytes are the source of truth.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE = HERE / "mg32_original_public_coverage_prereg.json"
MISSION = re.compile(r"^pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)$")
COLORS = {"red": 0, "green": 1, "blue": 2, "purple": 3, "yellow": 4, "grey": 5}
OBJECTS = {"key": 5, "ball": 6, "box": 7}
KEYS = ("actions", "target_front", "target_pick_attempt", "target_disappearance",
        "door_front", "door_toggle_attempt", "door_open", "positive_goal",
        "no_public_change", "any_key_front", "unique_public_views")


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(obj):
    return hashlib.sha256(encode(obj)).hexdigest()


def frozen():
    p = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert p["schema"] == "itd02.mg32.exposed-original-public-opportunity-retrospective-audit.v1"
    assert p["scope"] == "RETROSPECTIVE_EXPOSED_DEVELOPMENT_ONLY_NO_NEW_WORLD_ACTIONS_NO_FIRST_USE"
    assert p["parent"]["mg31_run_id"] == 40916681528
    assert p["cohort"]["episodes"] == 60
    assert p["cohort"]["original_actions"] == 11511
    assert p["output"]["classification"] == "MG32_RETROSPECTIVE_EXPOSURE_ACTION_DECOMPOSITION_ONLY_NO_SCIENCE"
    assert all(p["prohibitions"].values())
    return p


def classify_event(e):
    before = e["before"]
    after = e["after"]
    front = before["image"][3][5]
    afterfront = after["image"][3][5]
    action = e["action"]
    assert type(action) is int and 0 <= action <= 6
    assert e["external_actions"] == 0
    assert digest(before) == e["before_sha256"]
    assert digest(after) == e["after_sha256"]
    mission = MISSION.fullmatch(before["mission"])
    exact_target = bool(mission and front[0] == OBJECTS[mission.group(2)]
                        and front[1] == COLORS[mission.group(1)])
    locked_door = front[0] == 4 and front[2] == 2
    same_heading = before["direction"] == after["direction"]
    return {
        "actions": 1,
        "target_front": int(exact_target),
        "target_pick_attempt": int(exact_target and action == 3),
        "target_disappearance": int(exact_target and action == 3
                                    and afterfront[0] == 1 and same_heading),
        "door_front": int(locked_door),
        "door_toggle_attempt": int(locked_door and action == 5),
        "door_open": int(locked_door and action == 5 and same_heading
                         and afterfront[0] == 4 and afterfront[1] == front[1]
                         and afterfront[2] == 0),
        "positive_goal": int(e["reward"] > 0 and e["terminated"] is True),
        "no_public_change": int(e["before_sha256"] == e["after_sha256"]),
        "any_key_front": int(front[0] == 5)
    }


def audit_source(source, p):
    c = p["cohort"]
    assert source["classification"] == p["parent"]["mg31_scientific_classification"]
    assert source["scientific_first_use"] is False
    assert source["mg28_live_native_rollout_permitted"] is False
    assert source["controller_or_accepted_models_modified"] is False
    assert source["zero_external_actions"] is True
    assert source["same_three_original_seeds_per_arm"] is True
    assert source["original_selected_action_count"] == c["original_actions"]
    assert source["exposed_original_dev_seeds"] == c["seeds"]
    episodes = source["original_60_episodes"]
    assert len(episodes) == c["episodes"]
    expected = {(family, role, seed)
                for family, seeds in zip(c["families"], c["seeds"])
                for role in c["roles"] for seed in seeds}
    found = set()
    aggregate = collections.defaultdict(collections.Counter)
    opportunities = collections.defaultdict(lambda: [0, 0, 0])
    per_episode = []
    for row in episodes:
        key = (row["family"], row["role"], row["seed_dev_exposed"])
        assert key in expected and key not in found
        found.add(key)
        events = row["source_events"]
        assert digest(events) == row["source_events_sha256"]
        assert len(events) == row["original_source_actions"]
        assert len(events) <= 192
        count = collections.Counter()
        views = set()
        front_seen = set()
        for idx, event in enumerate(events, 1):
            assert event["index"] == idx
            assert event["mission"] == row["original_public_mission"]
            assert event["before"]["mission"] == event["after"]["mission"] == event["mission"]
            count.update(classify_event(event))
            views.add(event["before_sha256"])
            if event["before"]["image"][3][5][0] == 4:
                front_seen.add(idx)
        count["unique_public_views"] = len(views)
        assert count["actions"] == row["original_source_actions"]
        assert count["positive_goal"] == row["original_terminal_goal_rewards"]
        assert count["unique_public_views"] == row["unique_public_views"]
        assert count["no_public_change"] + row["observed_public_changes"] == count["actions"]
        aggregate[key[:2]].update(count)
        opportunities[key[:2]][0] += int(count["target_front"] > 0)
        opportunities[key[:2]][1] += int(count["door_front"] > 0)
        opportunities[key[:2]][2] += int(count["positive_goal"] > 0)
        per_episode.append({"family": key[0], "role": key[1], "seed": key[2],
                            **{k: count[k] for k in KEYS}})
    assert found == expected
    assert sum(x["actions"] for x in aggregate.values()) == c["original_actions"]
    # Frozen original classifier crosscheck: do not reclassify an existing MG31 negative.
    for (family, role), count in aggregate.items():
        earlier = source["per_family_per_arm"][family][role]
        assert count["target_disappearance"] == earlier["exact_mission_target_public_disappearance"]
        assert count["door_open"] == earlier["real_public_locked_door_open"]
        assert count["positive_goal"] == earlier["original_positive_terminal_goal"]
        assert count["actions"] == earlier["original_selected_actions"]
    rows = []
    for (family, role), count in sorted(aggregate.items()):
        rows.append({"family": family, "role": role,
                     **{k: count[k] for k in KEYS},
                     "target_front_episodes": opportunities[(family, role)][0],
                     "door_front_episodes": opportunities[(family, role)][1],
                     "positive_goal_episodes": opportunities[(family, role)][2]})
    return {"classification": p["output"]["classification"],
            "source_classification_unchanged": source["classification"],
            "source_sha256": p["parent"]["mg31_identical_process_source_sha256"],
            "total_episodes": len(episodes),
            "total_actual_selected_actions": c["original_actions"],
            "unfamiliar_family_target_front_zero_both_pickup_tasks":
                all(r["target_front"] == 0 for r in rows
                    if r["family"] in c["families"][1:3]),
            "retrospective_only": True, "scientific_first_use": False,
            "mg28_live_native_rollout_permitted": False,
            "per_family_per_role": rows,
            "per_episode": sorted(per_episode, key=lambda r:(r["family"], r["role"], r["seed"]))}


def run(artifact, output):
    p = frozen()
    expected_zip = p["parent"]["mg31_artifact_zip_sha256"]
    sha = hashlib.sha256()
    with artifact.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(block)
    assert sha.hexdigest() == expected_zip, "MG32_ORIGINAL_ARTIFACT_CUSTODY_MISMATCH"
    with zipfile.ZipFile(artifact) as z:
        assert set(z.namelist()) == {"first.json", "second.json", "first.log", "second.log", "comparison.log"}
        sources = []
        reports = []
        for name in ("first.json", "second.json"):
            with z.open(name) as f:
                envelope = json.load(f)
            assert envelope["canonical_source_sha256"] == p["parent"]["mg31_identical_process_source_sha256"]
            assert digest(envelope["source"]) == envelope["canonical_source_sha256"]
            sources.append(envelope["source"])
            reports.append(audit_source(envelope["source"], p))
        assert sources[0] == sources[1], "MG32_TWO_ORIGINAL_PROCESSES_DIVERGE"
        assert reports[0] == reports[1], "MG32_DIAGNOSTIC_NOT_REPRODUCIBLE"
        assert p["parent"]["mg31_identical_process_source_sha256"] in z.read("comparison.log").decode("utf-8")
    report = reports[0]
    report["source_artifact_sha256"] = expected_zip
    report["audit_report_sha256"] = digest(reports[0])
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(report["classification"])
    print("MG32_PINNED_TWO_PROCESS_SOURCE_AND_AUDIT_PASS", report["audit_report_sha256"])
    for row in report["per_family_per_role"]:
        print("MG32_OPPORTUNITY", row["family"], row["role"], "target_front",
              row["target_front"], "pick_attempt", row["target_pick_attempt"],
              "door_front", row["door_front"], "toggle_attempt", row["door_toggle_attempt"],
              "goal", row["positive_goal"])


def preflight():
    p = frozen()
    example = {"before": {"mission": "pick up the red box", "direction": 0,
                          "image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)]},
               "after": {"mission": "pick up the red box", "direction": 0,
                         "image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)]},
               "action": 3, "reward": 1.0, "terminated": True, "external_actions": 0}
    example["before"]["image"][3][5] = [7, 0, 0]
    example["before_sha256"] = digest(example["before"])
    example["after_sha256"] = digest(example["after"])
    row = classify_event(example)
    assert (row["target_front"], row["target_pick_attempt"],
            row["target_disappearance"], row["positive_goal"]) == (1, 1, 1, 1)
    assert p["parent"]["forge_source_head"] == "70fb89763d8331c23e2ab5f3845c475e31c25711"
    print("MG32_FROZEN_RETROSPECTIVE_ONLY_SOURCE_PREFLIGHT_PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--artifact", type=Path)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if a.preflight:
        preflight()
    else:
        if a.artifact is None or a.output is None:
            ap.error("require --artifact and --output")
        run(a.artifact, a.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""NR-M1N: read-only historical native-action support audit, no env reset/step.

Original external artifact: FORGE Actions run 40980730264, artifact #12945140842.
Pinned archive SHA-256: 25575d33723017be52ed57f014c6cea8baaa34bb9bc1616ad876f372d66b2a2c.
Requires a copy of that immutable artifact, not fresh source-world execution.
"""
import argparse
import collections
import hashlib
import json
import math
import zipfile

EXPECTED_ZIP = "25575d33723017be52ed57f014c6cea8baaa34bb9bc1616ad876f372d66b2a2c"
EXPECTED_SOURCE = "69dbc08751f65013874eec1c1e32c108fb51fb356820474b1702bf08bae6e019"
NATIVE_ROLES = {"wingless_mg19_unchanged", "yggdrasil_mg19_unchanged"}
MIN_OBSERVATIONS = 3
IMPROVEMENT_MARGIN = 0.1

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")

def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()

def context(public):
    # Mirrors exact source-public key fields from:
    # Wingless MG37 source_bridge.go / Yggdrasil MG23 observed_key.
    front = public["image"][3][5]
    return (public["mission"], public["direction"],
            front[0], front[1], front[2])

def eligible_for_any_parent(table):
    # Upper bound: checks all 7 possible parents because an actual MG28
    # parent proposal is NOT present in these older original MG19 trajectories.
    for parent in range(7):
        n0, reward0 = table[parent]
        if n0 < MIN_OBSERVATIONS:
            continue
        base = reward0 / n0
        for alternative in range(7):
            n, reward = table[alternative]
            if alternative == parent or n < MIN_OBSERVATIONS:
                continue
            mean = reward / n
            if mean > 0 and mean > base + IMPROVEMENT_MARGIN:
                return True
    return False

def audit(receipt):
    source = receipt["source"]
    assert receipt["canonical_source_sha256"] == EXPECTED_SOURCE
    assert digest(source) == EXPECTED_SOURCE, "SOURCE_CANONICAL_SHA_MISMATCH"
    assert source["schema"].startswith("itd02.mg56.")
    assert source["scientific_first_use"] is False
    assert source["zero_external_actions"] is True
    episodes = source["original_234_episodes"]
    assert len(episodes) == 234
    result = []
    for role in sorted(NATIVE_ROLES):
        by_family = collections.defaultdict(list)
        for ep in episodes:
            if ep["role"] == role:
                by_family[ep["family"]].append(ep)
        assert len(by_family) == 3
        for family, series in sorted(by_family.items()):
            assert len(series) == 3
            series.sort(key=lambda ep: ep["seed_dev_exposed"])
            counts = collections.defaultdict(lambda: [[0, 0.0] for _ in range(7)])
            tally = collections.Counter()
            goals = []
            for ep in series:
                events = ep["source_events"]
                assert ep["original_source_actions"] == len(events)
                assert ep["source_events_sha256"] == digest(events)
                for index, event in enumerate(events, 1):
                    assert event["index"] == index
                    assert event["external_actions"] == 0
                    assert event["mission"] == ep["original_public_mission"]
                    assert event["before"]["mission"] == event["after"]["mission"] == event["mission"]
                    assert event["action"] in range(7)
                    reward = event["reward"]
                    assert isinstance(reward, (int, float)) and math.isfinite(reward)
                    assert -1 <= reward <= 1
                    assert event["before_sha256"] == digest(event["before"])
                    assert event["after_sha256"] == digest(event["after"])
                    key = context(event["before"])
                    table = counts[key]
                    # The evaluation happens strictly BEFORE selected feedback.
                    tally["predecision_upperbound_eligible"] += int(eligible_for_any_parent(table))
                    tally["predecision_positive_context"] += int(any(n > 0 and s > 0 for n, s in table))
                    tally["events"] += 1
                    tally["events_positive"] += int(reward > 0)
                    tally["events_negative"] += int(reward < 0)
                    tally["events_zero"] += int(reward == 0)
                    tally["positive_nonterminal"] += int(reward > 0 and not (event["terminated"] or event["truncated"]))
                    tally["positive_terminal"] += int(reward > 0 and event["terminated"])
                    if reward > 0:
                        goals.append({"seed": ep["seed_dev_exposed"], "step": index,
                                      "action": event["action"], "reward": reward,
                                      "terminated": event["terminated"], "context": list(key)})
                    table[event["action"]][0] += 1
                    table[event["action"]][1] += reward
                tally["episodes"] += 1
            tally["distinct_contexts"] = len(counts)
            tally["final_supported_contexts"] = sum(eligible_for_any_parent(t) for t in counts.values())
            tally["final_any_positive_contexts"] = sum(any(s > 0 for n, s in t) for t in counts.values())
            result.append({"role": role, "family": family,
                           "seeds": [e["seed_dev_exposed"] for e in series],
                           **tally, "goal_events": goals})
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    assert sha_file(args.artifact) == EXPECTED_ZIP, "ARCHIVE_SHA_MISMATCH"
    with zipfile.ZipFile(args.artifact) as archive:
        assert {"first.json", "second.json", "comparison.log"}.issubset(archive.namelist())
        try:
            import orjson
            loads = orjson.loads
        except ImportError:
            loads = json.loads
        first = loads(archive.read("first.json"))
        rows = audit(first)
        del first
        second = loads(archive.read("second.json"))
        assert audit(second) == rows, "INDEPENDENT_PROCESS_DIVERGENCE"
    output = {
        "schema": "nr-m1n-original-selected-native-context-support-v1",
        "classification": "READ_ONLY_RETROSPECTIVE_PROXY_NOT_NATIVE_MG37_ORIGINAL_SCIENCE",
        "artifact_id": 12945140842, "zip_sha256": EXPECTED_ZIP,
        "source_canonical_sha256": EXPECTED_SOURCE,
        "contexts": "original public mission,direction,front pixel triple",
        "guard": "parent and alternative both >=3 selected same-context observations; alternative positive mean > parent+0.1",
        "roles": "original unchanged MG19 source actions, NOT an MG28/MG37 replay",
        "two_original_processes_match_native_context_counts": True,
        "both_full_canonical_source_sha256_recomputed": True,
        "native_episode_sha256_recomputed": True,
        "limitations": [
            "native MG28 action proposals were NOT observed; all-parent eligible is an upper bound",
            "source selected trajectories cannot represent outcomes of unchosen counterfactual actions",
            "per-role/family independent cold memory: no pooling across roles or families",
            "only exposed DEV evidence; no fresh original source run or scientific first-use"
        ],
        "rows": rows
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)
        f.write("\n")
    for r in rows:
        print(r["role"], r["family"], r["events"],
              r["events_positive"], r["predecision_upperbound_eligible"])

if __name__ == "__main__":
    main()

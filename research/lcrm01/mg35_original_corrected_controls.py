#!/usr/bin/env python3
"""MG35 source-pinned nondegenerate action-only comparison in authentic MiniGrid DEV.

The original qualified MG33-C ActionOnly class is imported from a *separate
exact-SHA checkout*, not reimplemented or edited. DEV only; no native rollout.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib, json, math, subprocess, sys, time, traceback
from pathlib import Path
from mg31_original_public_exploration import FAMILIES, UPSTREAM, explore_episode, digest
from mg32_original_public_coverage import classify_event
from mg33_original_frontier_dev import frontier_episode as mg33_frontier_episode
from mg34_original_graph_lookahead import frontier_episode as mg34_lookahead_episode

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "mg35_original_corrected_controls_prereg.json"
PARENT = "aa03bd3da4faa3a95dbab3e900fd82b00cda2072"
FREEZE = "f50287e1059f58af6c3911c9d52dbb2927ff0763"
CORRECTED = "f6a0363fd0c0c1ae0f312a4de9062b9395e70aac"
BLOB = "082ef861258476703a0590a4092add1ce0ab57c5"
ROLES = (
    "wingless_mg19_unchanged", "yggdrasil_mg19_unchanged",
    "mg33_public_history_frontier_unchanged",
    "mg34_graph_lookahead_unchanged",
    "mg31_generic_public_novelty_unchanged",
    "mg33c_actiononly_ucb_exact_source",
    "mg33c_actiononly_round_robin_exact_source",
    "seeded_uniform_random")
SEEDS = ((993101, 993103, 993107), (993201, 993203, 993207),
         (993301, 993303, 993307), (993401, 993403, 993407))


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE.parents[1],
                          capture_output=True, text=True, check=False)


def frozen():
    p = json.loads(FROZEN.read_text(encoding="utf-8"))
    d = p["design"]
    if (p.get("schema") != "itd02.mg35.authentic-original-nondegenerate-action-only-comparison.dev.v1"
        or p["phase"] != "PROSPECTIVE_PREREG_BEFORE_IMPLEMENTATION_AND_NEW_WORLD_ACTION"
        or p["parent"]["mg34_head"] != PARENT
        or p["source_pins"]["original_farama"] != UPSTREAM
        or p["corrected_control"]["qualified_source_commit"] != CORRECTED
        or p["corrected_control"]["source_git_blob_sha1"] != BLOB
        or tuple(d["families"]) != FAMILIES
        or tuple(d["roles"]) != ROLES
        or tuple(map(tuple, d["seeds"])) != SEEDS
        or d["episodes_total"] != 96
        or d["max_source_actions_per_episode"] != 192
        or d["independent_real_source_processes"] != 2
        or d["no_training_fit"] is not True
        or not all(p["prohibitions"].values())):
        raise ValueError("MG35_FROZEN_PROTOCOL_DRIFT")
    seeds = [s for cohort in SEEDS for s in cohort]
    if len(seeds) != 12 or len(set(seeds)) != 12 or set(seeds) & set(d["historically_known_exposed_seeds"]):
        raise ValueError("MG35_NONFRESH_KNOWN_DEV_ID")
    for sha in (PARENT, FREEZE):
        if git("merge-base", "--is-ancestor", sha, "HEAD").returncode != 0:
            raise ValueError("MG35_NOT_FROZEN_ON_PARENT_BEFORE_NEW_WORLD")
    for seed in seeds:
        proc = git("grep", "-n", "-w", str(seed), PARENT, "--", "research/lcrm01", "docs/research")
        if proc.returncode == 0:
            raise ValueError("MG35_PRIOR_PARENT_DEV_SEED_EXPOSED:" + str(seed))
        if proc.returncode != 1:
            raise ValueError("MG35_PRIOR_SEED_CUSTODY_UNAVAILABLE")
    return p


def corrected_class(control_root):
    root = control_root.resolve()
    source = root / "research/lcrm01/mg33c_actiononly_control.py"
    if not source.is_file():
        raise ValueError("MG35_MISSING_ORIGINAL_MG33C_SOURCE")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    blob = subprocess.run(["git", "-C", str(root), "hash-object",
                           "research/lcrm01/mg33c_actiononly_control.py"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != CORRECTED or blob != BLOB:
        raise ValueError("MG35_MG33C_SOURCE_IDENTITY_DRIFT")
    # Qualified code imported verbatim and no source checkout modified.
    sys.path.insert(0, str(source.parent))
    module = importlib.import_module("mg33c_actiononly_control")
    return module.ActionOnly


def control_episode(gym, entry, family, seed, mode, checkpoint, cap, public, original_digest, control):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space, "n", None) != 7:
            raise ValueError("MG35_WRONG_ORIGINAL_ENV")
        raw, _ = env.reset(seed=seed)
        first = public(raw)
        mission = first["mission"]
        initial = original_digest(first)
        actor = control(mode) if checkpoint is None else control.restore(checkpoint)
        if actor.mode != mode:
            raise ValueError("MG35_WRONG_RESTORED_MODE")
        start_count = actor.total
        events = []
        for n in range(1, cap + 1):
            before = public(raw)
            if before["mission"] != mission:
                raise ValueError("MG35_MISSION_CHANGED")
            action = actor.choose()  # Proven action-only: no scene passed to selector.
            raw2, reward, term, trunc, _ = env.step(action)
            after = public(raw2)
            if (after["mission"] != mission or type(term) is not bool or type(trunc) is not bool
                or not math.isfinite(float(reward))):
                raise ValueError("MG35_INVALID_SOURCE_FEEDBACK")
            bsha = original_digest(before); asha = original_digest(after)
            actor.observe_selected(action, bsha, asha, float(reward), term)
            events.append({"index": n, "before": before, "action": action,
                           "after": after, "mission": mission,
                           "policy_status": "MG35_UNCHANGED_MG33C_" + mode,
                           "reward": float(reward), "terminated": term, "truncated": trunc,
                           "before_sha256": bsha, "after_sha256": asha,
                           "external_actions": 0})
            raw = raw2
            if term or trunc:
                break
        state = actor.checkpoint()
        restored = control.restore(state)
        if restored.checkpoint() != state or restored.total != start_count + len(events):
            raise ValueError("MG35_MG33C_COLD_SOURCE_STATE_LOSS")
        if len(events) == cap and len({e["action"] for e in events}) < 4:
            raise ValueError("MG35_CORRECTED_CONTROL_DEGENERATE_IN_REAL_WORLD")
        return ({
            "family": family, "seed_dev_exposed": seed,
            "role": "mg33c_actiononly_ucb_exact_source" if mode == "ucb" else
                    "mg33c_actiononly_round_robin_exact_source",
            "public_start_sha256": initial, "original_public_mission": mission,
            "original_source_actions": len(events),
            "prior_selected_source_samples": start_count,
            "selected_source_samples_after": actor.total,
            "original_terminal_goal_rewards":
                sum(int(e["reward"] > 0 and e["terminated"]) for e in events),
            "observed_public_changes":
                sum(e["before_sha256"] != e["after_sha256"] for e in events),
            "unique_public_views": len({e["before_sha256"] for e in events}),
            "distinct_actions": len({e["action"] for e in events}),
            "checkpoint_sha256": hashlib.sha256(state).hexdigest(),
            "source_events_sha256": original_digest(events), "source_events": events
        }, state)
    finally:
        env.close()


def summarize(rows):
    totals = {}
    for family in FAMILIES:
        totals[family] = {}
        for role in ROLES:
            group = [r for r in rows if r["family"] == family and r["role"] == role]
            if len(group) != 3 or group[0]["prior_selected_source_samples"] not in (0, None):
                raise ValueError("MG35_MISSING_THREE_COLD_SOURCE_SEEDS")
            if role != ROLES[-1]:
                for a, b in zip(group, group[1:]):
                    if a["selected_source_samples_after"] != b["prior_selected_source_samples"]:
                        raise ValueError("MG35_ROLE_MEMORY_NOT_CONTINUOUS")
            counts = collections.Counter()
            target_contexts = set()
            door_contexts = set()
            action_hist = [0] * 7
            positive = 0
            for r in group:
                if original_digest_events(r) is False:
                    raise ValueError("MG35_SOURCE_EVENT_DIGEST_DRIFT")
                positive += int(r["original_terminal_goal_rewards"] > 0)
                for e in r["source_events"]:
                    x = classify_event(e)
                    counts.update(x)
                    action_hist[e["action"]] += 1
                    if x["target_front"]:
                        target_contexts.add(e["before_sha256"])
                    if x["door_front"]:
                        door_contexts.add(e["before_sha256"])
            if sum(action_hist) != sum(r["original_source_actions"] for r in group):
                raise ValueError("MG35_SELECTED_ACTION_COUNT_MISMATCH")
            totals[family][role] = {
                **{k: counts[k] for k in
                   ("actions", "target_front", "target_pick_attempt", "target_disappearance",
                    "door_front", "door_toggle_attempt", "door_open", "positive_goal",
                    "no_public_change")},
                "unique_target_public_contexts": len(target_contexts),
                "unique_locked_door_public_contexts": len(door_contexts),
                "positive_goal_episodes": positive,
                "action_histogram": action_hist, "episodes": len(group)}
    return totals


def original_digest_events(r):
    from mg17_original_family_source_qual import digest as original_digest
    return original_digest(r["source_events"]) == r["source_events_sha256"]


def execute(root, native_go, control_root, p):
    import gymnasium as gym
    import minigrid
    from mg17_original_family_source_qual import (
        frozen as upstream_frozen, attest_source, public, digest as original_digest)
    from mg21_original_development import one_episode, ROLES as native_roles
    control = corrected_class(control_root)
    if not Path(minigrid.__file__).resolve().is_relative_to(root.resolve()):
        raise ValueError("MG35_NOT_PINNED_ORIGINAL_MINIGRID_SOURCE")
    source = upstream_frozen()
    attest_source(root, source)
    registry = {f["id"]: f["entry_point"] for f in source["families"]}
    results = []
    for family, seeds in zip(FAMILIES, SEEDS):
        carried = {role: None for role in ROLES}
        for seed in seeds:
            same_seed_rows = []
            for role in ROLES:
                if role in ROLES[:2] or role == ROLES[-1]:
                    actual = native_roles[0] if role == ROLES[0] else (
                        native_roles[1] if role == ROLES[1] else native_roles[3])
                    row, _, state = one_episode(
                        family, seed, actual, 192, carried[role], native_go, registry[family])
                elif role == ROLES[2]:
                    row, state = mg33_frontier_episode(
                        gym, registry[family], family, seed, carried[role], 192, public, original_digest)
                elif role == ROLES[3]:
                    row, state = mg34_lookahead_episode(
                        gym, registry[family], family, seed, carried[role], 192, public, original_digest)
                elif role == ROLES[4]:
                    row, state = explore_episode(
                        gym, registry[family], family, seed, "full", carried[role], 192, public, original_digest)
                elif role in (ROLES[5], ROLES[6]):
                    mode = "ucb" if role == ROLES[5] else "round_robin"
                    row, state = control_episode(
                        gym, registry[family], family, seed, mode, carried[role], 192, public,
                        original_digest, control)
                else:
                    raise ValueError("MG35_INVALID_ROLE")
                row["role"] = role
                if role != ROLES[-1]:
                    carried[role] = state
                results.append(row)
                same_seed_rows.append(row)
            if len({r["public_start_sha256"] for r in same_seed_rows}) != 1:
                raise ValueError("MG35_UNEQUAL_SOURCE_START")
    if len(results) != 96 or any(not (1 <= r["original_source_actions"] <= 192) for r in results):
        raise ValueError("MG35_MISSING_REAL_SOURCE_EPISODES")
    table = summarize(results)
    unfamiliar = FAMILIES[1:]
    candidate = ROLES[2]
    controls = ROLES[5:7]
    positive = {role: sum(table[f][role]["positive_goal_episodes"] for f in unfamiliar)
                for role in (candidate, *controls)}
    effects = {role: sum(table[f][role]["target_disappearance"] for f in unfamiliar)
               for role in (candidate, *controls)}
    candidate_families = sum(table[f][candidate]["positive_goal_episodes"] > 0 for f in unfamiliar)
    supported = (candidate_families >= 2 and effects[candidate] >= 1
                 and all(positive[candidate] > positive[r] and effects[candidate] > effects[r]
                         for r in controls))
    labels = p["primary_dev_filter"]
    classification = labels["pass_label"] if supported else labels["fail_label"]
    source = {
        "schema": "itd02.mg35.authentic-original-nondegenerate-action-only-comparison-source.v1",
        "classification": classification,
        "source_parent": PARENT,
        "farama_source": UPSTREAM,
        "qualified_actiononly_source": CORRECTED,
        "qualified_actiononly_blob_sha1": BLOB,
        "original_96_episodes": results,
        "original_selected_action_count": sum(r["original_source_actions"] for r in results),
        "per_family_per_role": table,
        "candidate_vs_nondegenerate_controls": {
            "positive_goal_episodes": positive,
            "exact_target_effects": effects,
            "candidate_positive_unfamiliar_families": candidate_families,
            "filter_supported": supported},
        "exposed_dev_seeds": [list(s) for s in SEEDS],
        "zero_external_actions": True,
        "scientific_first_use": False, "native_resource_parity_qualified": False,
        "mg28_native_rollout_permitted": False,
        "native_models_or_controllers_modified": False}
    return {"schema": source["schema"], "source": source,
            "canonical_source_sha256": digest(source)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--source-root", type=Path)
    ap.add_argument("--native-go", type=Path)
    ap.add_argument("--control-root", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--compare", nargs=2, type=Path)
    opt = ap.parse_args()
    p = frozen()
    if opt.preflight:
        if tuple(p["primary_dev_filter"]["matched_non_degenerate_controls"]) != ROLES[5:7]:
            raise ValueError("MG35_BAD_FROZEN_STRONG_CONTROLS")
        if p["primary_dev_filter"]["candidate"] != ROLES[2]:
            raise ValueError("MG35_BAD_FROZEN_CANDIDATE")
        print("MG35_FROZEN_SOURCE_AND_CORRECTED_CONTROL_IMPORT_BOUNDARY_PREFLIGHT_PASS")
        return
    if opt.compare:
        a, b = [json.loads(x.read_text(encoding="utf-8")) for x in opt.compare]
        if (a.get("source") != b.get("source")
            or a.get("canonical_source_sha256") != b.get("canonical_source_sha256")
            or a.get("canonical_source_sha256") != digest(a["source"])
            or len(a["source"]["original_96_episodes"]) != 96
            or a["source"]["zero_external_actions"] is not True
            or a["source"]["scientific_first_use"] is not False):
            raise ValueError("MG35_TWO_ORIGINAL_PROCESSES_NOT_MATCHED")
        print("MG35_TWO_ORIGINAL_SOURCE_PROCESSES_IDENTICAL", a["canonical_source_sha256"])
        print("MG35_FROZEN_DEV_CLASSIFICATION", a["source"]["classification"])
        print("MG35_CORRECTED_CONTROL_COMPARISON", json.dumps(
            a["source"]["candidate_vs_nondegenerate_controls"], sort_keys=True))
        return
    if any(x is None for x in (opt.source_root, opt.native_go, opt.control_root, opt.output)):
        ap.error("require --source-root --native-go --control-root --output")
    start = time.perf_counter()
    try:
        result = execute(opt.source_root, opt.native_go, opt.control_root, p)
    except Exception as e:
        result = {"schema": "itd02.mg35.authentic-original-nondegenerate-action-only-comparison-source.v1",
                  "classification": "MG35_ORIGINAL_WORLD_SOURCE_BLOCKED_NO_SCIENCE",
                  "error_type": type(e).__name__, "error": str(e),
                  "trace_tail": traceback.format_exc().splitlines()[-15:]}
    result["host_wall_time_outside_canonical_source_seconds"] = round(time.perf_counter() - start, 6)
    opt.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    cl = result.get("classification", result.get("source", {}).get(
        "classification", "MG35_MISSING_SOURCE_CLASSIFICATION_BLOCKED"))
    print("MG35_ORIGINAL_SOURCE_CLASSIFICATION", cl)
    if "BLOCKED" in cl:
        raise ValueError(result.get("error", "MG35_BLOCKED_SOURCE"))
    print("MG35_ORIGINAL_SOURCE_SHA256", result["canonical_source_sha256"])


if __name__ == "__main__":
    main()

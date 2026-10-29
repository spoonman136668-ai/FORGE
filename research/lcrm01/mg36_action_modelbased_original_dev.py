#!/usr/bin/env python3
"""MG36 source-pinned nondegenerate action-only comparison in authentic MiniGrid DEV.

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
FROZEN = HERE / "mg36_action_modelbased_original_dev_prereg.json"
PARENT = "bd20f50c9a478623b6af5ad1afb149becb75faf9"
FREEZE = "2ab16f3f089a9312a25a4776306f0176cc47ad78"
CORRECTED = "f6a0363fd0c0c1ae0f312a4de9062b9395e70aac"
BLOB = "082ef861258476703a0590a4092add1ce0ab57c5"
ROLES = (
    "wingless_mg19_unchanged", "yggdrasil_mg19_unchanged",
    "mg33_public_history_frontier_unchanged",
    "mg34_graph_lookahead_unchanged",
    "mg31_generic_public_novelty_unchanged",
    "mg33c_actiononly_ucb_exact_source",
    "mg33c_actiononly_round_robin_exact_source",
    "action_conditioned_public_model_based",
    "seeded_uniform_random")
SEEDS = ((997101, 997103, 997107), (997201, 997203, 997207),
         (997301, 997303, 997307), (997401, 997403, 997407))


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE.parents[1],
                          capture_output=True, text=True, check=False)


def frozen():
    p = json.loads(FROZEN.read_text(encoding="utf-8"))
    d = p["cohort"]
    model = p["conventional_model"]
    if (p.get("schema") != "itd02.mg36.public-action-conditioned-modelbased-conventional-dev.v1"
        or p["phase"] != "PROSPECTIVE_FREEZE_BEFORE_IMPLEMENTATION_AND_BEFORE_NEW_FARAMA_ACTION"
        or p["parent"]["mg35_head"] != PARENT
        or p["immutable_sources"]["farama"] != UPSTREAM
        or p["immutable_sources"]["mg33c_control"] != CORRECTED
        or p["immutable_sources"]["mg33c_blob_sha1"] != BLOB
        or tuple(d["families"]) != FAMILIES
        or tuple(d["roles"]) != ROLES
        or tuple(map(tuple, d["seeds"])) != SEEDS
        or d["expected_source_episodes"] != 108
        or d["source_actions_cap_per_episode"] != 192
        or d["independent_original_reproductions"] != 2
        or d["fit_enabled"] is not False
        or (model["lookahead_depth"], model["discount"],
            model["local_untried_bonus"], model["action_effect_bonus"],
            model["novel_state_bonus"], model["empirical_goal_bonus"],
            model["planning_frontier_bonus"], model["visit_penalty"]) !=
           (2, 0.70, 2.0, 0.75, 0.65, 2.0, 0.9, 0.02)
        or not all(p["prohibitions"].values())):
        raise ValueError("MG36_FROZEN_PROTOCOL_DRIFT")
    seeds = [s for cohort in SEEDS for s in cohort]
    if len(seeds) != 12 or len(set(seeds)) != 12 or set(seeds) & set(d["known_exposed_seeds"]):
        raise ValueError("MG36_NONFRESH_KNOWN_DEV_ID")
    for sha in (PARENT, FREEZE):
        if git("merge-base", "--is-ancestor", sha, "HEAD").returncode != 0:
            raise ValueError("MG36_NOT_FROZEN_ON_PARENT_BEFORE_NEW_WORLD")
    for seed in seeds:
        prior = git("grep", "-n", "-w", str(seed), PARENT, "--", "research/lcrm01", "docs/research")
        if prior.returncode == 0:
            raise ValueError("MG36_PRIOR_PARENT_DEV_SEED_EXPOSED:" + str(seed))
        if prior.returncode != 1:
            raise ValueError("MG36_PRIOR_SEED_CUSTODY_UNAVAILABLE")
    return p


def corrected_class(control_root):
    root = control_root.resolve()
    source = root / "research/lcrm01/mg33c_actiononly_control.py"
    if not source.is_file():
        raise ValueError("MG36_MISSING_ORIGINAL_MG33C_SOURCE")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    blob = subprocess.run(["git", "-C", str(root), "hash-object",
                           "research/lcrm01/mg33c_actiononly_control.py"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != CORRECTED or blob != BLOB:
        raise ValueError("MG36_MG33C_SOURCE_IDENTITY_DRIFT")
    # Qualified code imported verbatim and no source checkout modified.
    sys.path.insert(0, str(source.parent))
    module = importlib.import_module("mg33c_actiononly_control")
    return module.ActionOnly


def control_episode(gym, entry, family, seed, mode, checkpoint, cap, public, original_digest, control):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space, "n", None) != 7:
            raise ValueError("MG36_WRONG_ORIGINAL_ENV")
        raw, _ = env.reset(seed=seed)
        first = public(raw)
        mission = first["mission"]
        initial = original_digest(first)
        actor = control(mode) if checkpoint is None else control.restore(checkpoint)
        if actor.mode != mode:
            raise ValueError("MG36_WRONG_RESTORED_MODE")
        start_count = actor.total
        events = []
        for n in range(1, cap + 1):
            before = public(raw)
            if before["mission"] != mission:
                raise ValueError("MG36_MISSION_CHANGED")
            action = actor.choose()  # Proven action-only: no scene passed to selector.
            raw2, reward, term, trunc, _ = env.step(action)
            after = public(raw2)
            if (after["mission"] != mission or type(term) is not bool or type(trunc) is not bool
                or not math.isfinite(float(reward))):
                raise ValueError("MG36_INVALID_SOURCE_FEEDBACK")
            bsha = original_digest(before); asha = original_digest(after)
            actor.observe_selected(action, bsha, asha, float(reward), term)
            events.append({"index": n, "before": before, "action": action,
                           "after": after, "mission": mission,
                           "policy_status": "MG36_UNCHANGED_MG33C_" + mode,
                           "reward": float(reward), "terminated": term, "truncated": trunc,
                           "before_sha256": bsha, "after_sha256": asha,
                           "external_actions": 0})
            raw = raw2
            if term or trunc:
                break
        state = actor.checkpoint()
        restored = control.restore(state)
        if restored.checkpoint() != state or restored.total != start_count + len(events):
            raise ValueError("MG36_MG33C_COLD_SOURCE_STATE_LOSS")
        if len(events) == cap and len({e["action"] for e in events}) < 4:
            raise ValueError("MG36_CORRECTED_CONTROL_DEGENERATE_IN_REAL_WORLD")
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



class EmpiricalActionModel:
    """Conventional two-step empirical tabular transition model.

    Every model edge is learned from this actor's own selected real actions.
    Scores are action-conditioned uncertainty + observed transition/reward
    statistics; no hidden coordinates, scripted key-door sequence or oracle.
    """
    SCHEMA = "mg36.empirical-public-action-two-step-model.v1"

    def __init__(self, edges=None, visits=None, global_actions=None, total=0):
        self.edges = {} if edges is None else edges
        self.visits = {} if visits is None else visits
        self.global_actions = ([{"n": 0, "changed": 0, "novel": 0, "goals": 0}
                                for _ in range(7)] if global_actions is None else global_actions)
        self.total = total
        self.pending = None

    def value(self, key, depth):
        if depth <= 0:
            return 0.0
        row = self.edges.get(key, {})
        # Bound two-step model backup over empirical source-selected transitions.
        best = 0.0
        for action in range(7):
            cell = row.get(str(action))
            if not cell:
                best = max(best, 0.9)
                continue
            n = cell["n"]
            future = sum(
                freq * (0.9 * int(len(self.edges.get(dst, {})) < 7)
                        + 0.7 * self.value(dst, depth - 1))
                for dst, freq in cell["next"].items()) / n
            estimate = 2.0 * cell["goals"] / n + future
            best = max(best, estimate)
        return best

    def choose(self, public):
        if self.pending is not None:
            raise ValueError("MG36_DOUBLE_CHOOSE_WITHOUT_OWN_FEEDBACK")
        key = digest(public)
        tie = int(key[:2], 16) % 7
        row = self.edges.get(key, {})
        best = None
        chosen = None
        for offset in range(7):
            action = (tie + offset) % 7
            cell = row.get(str(action))
            global_row = self.global_actions[action]
            n = 0 if cell is None else cell["n"]
            g = global_row["n"]
            effect_prior = (global_row["changed"] + 0.5) / (g + 1)
            novelty_prior = (global_row["novel"] + 0.5) / (g + 1)
            goal_prior = (global_row["goals"] + 0.25) / (g + 1)
            score = (2.0 / (1 + n) + 0.75 * effect_prior +
                     0.65 * novelty_prior + 2.0 * goal_prior - 0.02 * n)
            if cell is not None:
                expected = sum(freq * (0.9 * int(len(self.edges.get(dst, {})) < 7)
                                        + 0.70 * self.value(dst, 1))
                               for dst, freq in cell["next"].items()) / n
                score += 0.70 * expected
                score += 2.0 * cell["goals"] / (n + 1)
            if best is None or score > best:
                best, chosen = score, action
        self.pending = (key, chosen)
        return chosen

    def observe_selected(self, before, action, after, reward, terminated):
        if (self.pending != (digest(before), action)
            or type(action) is not int or action not in range(7)
            or type(terminated) is not bool or
            type(reward) not in (int, float) or not math.isfinite(reward)
            or reward < 0):
            raise ValueError("MG36_NOT_OWN_SELECTED_VALID_SOURCE_FEEDBACK")
        before_key = digest(before); after_key = digest(after)
        novel = after_key not in self.visits
        changed = before_key != after_key
        goal = bool(reward > 0 and terminated)
        row = self.edges.setdefault(before_key, {})
        cell = row.setdefault(str(action), {"n": 0, "changed": 0, "novel": 0,
                                            "goals": 0, "next": {}})
        cell["n"] += 1
        cell["changed"] += int(changed)
        cell["novel"] += int(novel)
        cell["goals"] += int(goal)
        cell["next"][after_key] = cell["next"].get(after_key, 0) + 1
        global_row = self.global_actions[action]
        global_row["n"] += 1
        global_row["changed"] += int(changed)
        global_row["novel"] += int(novel)
        global_row["goals"] += int(goal)
        self.visits[before_key] = self.visits.get(before_key, 0) + 1
        self.visits[after_key] = self.visits.get(after_key, 0) + 1
        self.total += 1
        self.pending = None

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG36_CANNOT_CHECKPOINT_PENDING_ACTION")
        return json.dumps({"schema": self.SCHEMA, "edges": self.edges,
                           "visits": self.visits,
                           "global_actions": self.global_actions, "total": self.total},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

    @classmethod
    def restore(cls, raw):
        wire = json.loads(raw)
        if (set(wire) != {"schema", "edges", "visits", "global_actions", "total"}
            or wire["schema"] != cls.SCHEMA):
            raise ValueError("MG36_COLD_SCHEMA")
        a = cls(wire["edges"], wire["visits"], wire["global_actions"], wire["total"])
        if (raw != a.checkpoint() or len(a.global_actions) != 7
            or type(a.total) is not int or a.total < 0
            or a.total != sum(g["n"] for g in a.global_actions)
            or a.total != sum(c["n"] for r in a.edges.values() for c in r.values())
            or any(c["n"] != sum(c["next"].values())
                   for r in a.edges.values() for c in r.values())):
            raise ValueError("MG36_COLD_EMPIRICAL_MODEL_DIVERGED")
        return a


def model_episode(gym, entry, family, seed, prior, cap, public, original_digest):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space, "n", None) != 7:
            raise ValueError("MG36_NOT_SOURCE_ORIGINAL_SEVEN_ACTION")
        raw, _ = env.reset(seed=seed)
        first = public(raw)
        mission = first["mission"]
        start_hash = original_digest(first)
        actor = EmpiricalActionModel() if prior is None else EmpiricalActionModel.restore(prior)
        beginning = actor.total
        events = []
        for number in range(1, cap + 1):
            before = public(raw)
            if before["mission"] != mission:
                raise ValueError("MG36_PUBLIC_MISSION_CHANGED")
            action = actor.choose(before)
            raw2, reward, term, trunc, _ = env.step(action)
            after = public(raw2)
            if after["mission"] != mission or type(term) is not bool or type(trunc) is not bool:
                raise ValueError("MG36_INVALID_ORIGINAL_TERMINAL_OR_MISSION")
            actor.observe_selected(before, action, after, float(reward), term)
            events.append({
                "index": number, "before": before, "action": action, "after": after,
                "mission": mission, "policy_status": "MG36_EMPIRICAL_MODEL_BASED_SELECTED",
                "reward": float(reward), "terminated": term, "truncated": trunc,
                "before_sha256": original_digest(before),
                "after_sha256": original_digest(after), "external_actions": 0})
            raw = raw2
            if term or trunc:
                break
        checkpoint = actor.checkpoint()
        if (EmpiricalActionModel.restore(checkpoint).checkpoint() != checkpoint
            or actor.total != beginning + len(events)):
            raise ValueError("MG36_SELECTED_SOURCE_MEMORY_NOT_RESTORED")
        row = {
            "family": family, "seed_dev_exposed": seed, "role": ROLES[7],
            "public_start_sha256": start_hash, "original_public_mission": mission,
            "original_source_actions": len(events), "prior_selected_source_samples": beginning,
            "selected_source_samples_after": actor.total,
            "original_terminal_goal_rewards":
                sum(int(e["reward"] > 0 and e["terminated"]) for e in events),
            "observed_public_changes":
                sum(e["before_sha256"] != e["after_sha256"] for e in events),
            "unique_public_views": len({e["before_sha256"] for e in events}),
            "distinct_actions": len({e["action"] for e in events}),
            "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
            "source_events_sha256": original_digest(events),
            "source_events": events}
        return row, checkpoint
    finally:
        env.close()




def summarize(rows):
    totals = {}
    for family in FAMILIES:
        totals[family] = {}
        for role in ROLES:
            group = [r for r in rows if r["family"] == family and r["role"] == role]
            if len(group) != 3 or group[0]["prior_selected_source_samples"] not in (0, None):
                raise ValueError("MG36_MISSING_THREE_COLD_SOURCE_SEEDS")
            if role != ROLES[-1]:
                for a, b in zip(group, group[1:]):
                    if a["selected_source_samples_after"] != b["prior_selected_source_samples"]:
                        raise ValueError("MG36_ROLE_MEMORY_NOT_CONTINUOUS")
            counts = collections.Counter()
            target_contexts = set()
            door_contexts = set()
            action_hist = [0] * 7
            positive = 0
            for r in group:
                if original_digest_events(r) is False:
                    raise ValueError("MG36_SOURCE_EVENT_DIGEST_DRIFT")
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
                raise ValueError("MG36_SELECTED_ACTION_COUNT_MISMATCH")
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
        raise ValueError("MG36_NOT_PINNED_ORIGINAL_MINIGRID_SOURCE")
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
                elif role == ROLES[7]:
                    row, state = model_episode(
                        gym, registry[family], family, seed, carried[role], 192,
                        public, original_digest)
                else:
                    raise ValueError("MG36_INVALID_ROLE")
                row["role"] = role
                if role != ROLES[-1]:
                    carried[role] = state
                results.append(row)
                same_seed_rows.append(row)
            if len({r["public_start_sha256"] for r in same_seed_rows}) != 1:
                raise ValueError("MG36_UNEQUAL_SOURCE_START")
    if len(results) != 108 or any(not (1 <= r["original_source_actions"] <= 192) for r in results):
        raise ValueError("MG36_MISSING_REAL_SOURCE_EPISODES")
    table = summarize(results)
    unfamiliar = FAMILIES[1:]
    candidate = ROLES[7]
    controls = (ROLES[2], ROLES[3], ROLES[5], ROLES[6])
    positive = {role: sum(table[f][role]["positive_goal_episodes"] for f in unfamiliar)
                for role in (candidate, *controls)}
    effects = {role: sum(table[f][role]["target_disappearance"] for f in unfamiliar)
               for role in (candidate, *controls)}
    candidate_families = sum(table[f][candidate]["positive_goal_episodes"] > 0
                             for f in unfamiliar)
    pickup_specific = any(table[f][candidate]["positive_goal_episodes"] > 0
                          for f in FAMILIES[1:3])
    supported = (candidate_families >= 2 and pickup_specific
                 and effects[candidate] >= 1
                 and all(positive[candidate] > positive[r] for r in controls))
    labels = p["dev_acceptance"]
    classification = labels["pass"] if supported else labels["fail"]
    source = {
        "schema": "itd02.mg36.action-conditioned-public-modelbased-dev-source.v1",
        "classification": classification,
        "source_parent": PARENT,
        "farama_source": UPSTREAM,
        "qualified_actiononly_source": CORRECTED,
        "qualified_actiononly_blob_sha1": BLOB,
        "original_108_episodes": results,
        "original_selected_action_count": sum(r["original_source_actions"] for r in results),
        "per_family_per_role": table,
        "modelbased_vs_matched_controls": {
            "positive_goal_episodes": positive,
            "exact_target_effects": effects,
            "candidate_positive_unfamiliar_families": candidate_families,
            "candidate_positive_unlock_or_blocked": pickup_specific,
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
        if p["dev_acceptance"]["candidate"] != ROLES[7]:
            raise ValueError("MG36_FROZEN_CANDIDATE_MISMATCH")
        if tuple(p["dev_acceptance"]["comparison_roles"]) != (ROLES[2],ROLES[3],ROLES[5],ROLES[6]):
            raise ValueError("MG36_CONTROL_SET_DRIFT")
        before = {"image": [[[1,0,0] for _ in range(7)] for _ in range(7)],
                  "direction": 0, "mission": "pick up the red box"}
        after = dict(before, direction=1)
        agent = EmpiricalActionModel()
        chosen = []
        for n in range(28):
            action = agent.choose(before)
            if n == 0:
                try:
                    agent.observe_selected(before, (action + 1) % 7, after, 0.0, False)
                except ValueError:
                    pass
                else:
                    raise ValueError("MG36_OFF_POLICY_FEEDBACK_ACCEPTED")
            agent.observe_selected(before, action, after, 0.0, False)
            chosen.append(action)
        if len(set(chosen)) < 2:
            raise ValueError("MG36_SYNTHETIC_MODEL_ACTION_COLLAPSE")
        state = agent.checkpoint()
        if EmpiricalActionModel.restore(state).checkpoint() != state:
            raise ValueError("MG36_SYNTHETIC_COLD_MODEL_LOSS")
        print("MG36_FROZEN_ACTION_CONDITIONED_MODEL_SOURCE_ONLY_PREFLIGHT_PASS")
        return
    if opt.compare:
        a, b = [json.loads(x.read_text(encoding="utf-8")) for x in opt.compare]
        if (a.get("source") != b.get("source")
            or a.get("canonical_source_sha256") != b.get("canonical_source_sha256")
            or a.get("canonical_source_sha256") != digest(a["source"])
            or len(a["source"]["original_108_episodes"]) != 108
            or a["source"]["zero_external_actions"] is not True
            or a["source"]["scientific_first_use"] is not False):
            raise ValueError("MG36_TWO_ORIGINAL_PROCESSES_NOT_MATCHED")
        print("MG36_TWO_ORIGINAL_SOURCE_PROCESSES_IDENTICAL", a["canonical_source_sha256"])
        print("MG36_FROZEN_DEV_CLASSIFICATION", a["source"]["classification"])
        print("MG36_MODELBASED_VS_MATCHED_CONTROLS", json.dumps(
            a["source"]["modelbased_vs_matched_controls"], sort_keys=True))
        return
    if any(x is None for x in (opt.source_root, opt.native_go, opt.control_root, opt.output)):
        ap.error("require --source-root --native-go --control-root --output")
    start = time.perf_counter()
    try:
        result = execute(opt.source_root, opt.native_go, opt.control_root, p)
    except Exception as e:
        result = {"schema": "itd02.mg36.authentic-original-nondegenerate-action-only-comparison-source.v1",
                  "classification": "MG36_ORIGINAL_WORLD_SOURCE_BLOCKED_NO_SCIENCE",
                  "error_type": type(e).__name__, "error": str(e),
                  "trace_tail": traceback.format_exc().splitlines()[-15:]}
    result["host_wall_time_outside_canonical_source_seconds"] = round(time.perf_counter() - start, 6)
    opt.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    cl = result.get("classification", result.get("source", {}).get(
        "classification", "MG36_MISSING_SOURCE_CLASSIFICATION_BLOCKED"))
    print("MG36_ORIGINAL_SOURCE_CLASSIFICATION", cl)
    if "BLOCKED" in cl:
        raise ValueError(result.get("error", "MG36_BLOCKED_SOURCE"))
    print("MG36_ORIGINAL_SOURCE_SHA256", result["canonical_source_sha256"])


if __name__ == "__main__":
    main()

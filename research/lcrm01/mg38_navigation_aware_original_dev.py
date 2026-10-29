#!/usr/bin/env python3
"""MG38 source-pinned nondegenerate action-only comparison in authentic MiniGrid DEV.

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
FROZEN = HERE / "mg38_navigation_aware_original_dev_prereg.json"
PARENT = "26bc90e1ff7aa91da80ff734984d62ef766ff3cf"
FREEZE = "9738f89c489508d9e67f9f8c54ddfa5b86d77c79"
CORRECTED = "f6a0363fd0c0c1ae0f312a4de9062b9395e70aac"
BLOB = "082ef861258476703a0590a4092add1ce0ab57c5"
ROLES = (
    "wingless_mg19_unchanged", "yggdrasil_mg19_unchanged",
    "mg33_public_history_frontier_unchanged",
    "mg34_graph_lookahead_unchanged",
    "mg31_generic_public_novelty_unchanged",
    "mg33c_actiononly_ucb_exact_source",
    "mg33c_actiononly_round_robin_exact_source",
    "mg36_action_conditioned_public_model_based_unchanged",
    "navigation_aware_empirical_model_candidate",
    "seeded_uniform_random")
SEEDS = ((1003101,1003103,1003107),(1003201,1003203,1003207),
         (1003301,1003303,1003307),(1003401,1003403,1003407))


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE.parents[1],
                          capture_output=True, text=True, check=False)


def frozen():
    p = json.loads(FROZEN.read_text(encoding="utf-8"))
    d = p["cohort"]
    n = p["navigation_aware_control"]
    c = n["score_coefficients"]
    if (p.get("schema") != "itd02.mg38.original-public-navigation-aware-empirical-model-control.dev.v1"
        or p["phase"] != "PROSPECTIVE_FROZEN_BEFORE_EXECUTABLE_AND_BEFORE_ANY_ORIGINAL_WORLD_STEP"
        or p["parent"]["mg37_head"] != PARENT
        or p["source"]["farama"] != UPSTREAM
        or p["source"]["mg33c_exact_control"] != CORRECTED
        or p["source"]["mg33c_blob_sha1"] != BLOB
        or tuple(d["families"]) != FAMILIES
        or tuple(d["roles"]) != ROLES
        or tuple(map(tuple, d["seeds"])) != SEEDS
        or d["expected_episodes"] != 120
        or d["steps_cap_per_actor_episode"] != 192
        or d["independent_original_processes"] != 2
        or d["fit_enabled"] is not False
        or n["max_turn_chain"] != 2
        or tuple(c[k] for k in ("forward_base","forward_untried",
            "forward_change_prior","forward_local_nochange_penalty",
            "turn_base","turn_untried","turn_after_forward_nochange",
            "turn_per_consecutive_penalty","turn_long_chain_penalty",
            "other_base","other_untried","other_goal_prior",
            "other_global_change_prior","other_local_attempt_penalty",
            "generic_front_public_pickup_affordance",
            "generic_front_public_door_toggle_affordance")) !=
            (2.3,1.7,1.0,2.0,0.4,0.4,2.5,1.25,8.0,
             0.6,1.7,2.0,0.7,0.1,2.2,2.2)
        or not all(p["prohibitions"].values())):
        raise ValueError("MG38_FROZEN_PROTOCOL_DRIFT")
    seeds = [seed for group in SEEDS for seed in group]
    if len(seeds) != 12 or len(set(seeds)) != 12:
        raise ValueError("MG38_REPEATED_NEW_SOURCE_SEED")
    for sha in (PARENT, FREEZE):
        if git("merge-base", "--is-ancestor", sha, "HEAD").returncode != 0:
            raise ValueError("MG38_NOT_FROZEN_BEFORE_EXECUTABLE")
    for seed in seeds:
        prior = git("grep", "-n", "-w", str(seed), PARENT, "--", "research/lcrm01", "docs/research")
        if prior.returncode == 0:
            raise ValueError("MG38_ALREADY_EXPOSED_PAST_SOURCE_SEED:" + str(seed))
        if prior.returncode != 1:
            raise ValueError("MG38_PARENT_SOURCE_IDENTITY_UNAVAILABLE")
    return p


def corrected_class(control_root):
    root = control_root.resolve()
    source = root / "research/lcrm01/mg33c_actiononly_control.py"
    if not source.is_file():
        raise ValueError("MG38_MISSING_ORIGINAL_MG33C_SOURCE")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    blob = subprocess.run(["git", "-C", str(root), "hash-object",
                           "research/lcrm01/mg33c_actiononly_control.py"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != CORRECTED or blob != BLOB:
        raise ValueError("MG38_MG33C_SOURCE_IDENTITY_DRIFT")
    # Qualified code imported verbatim and no source checkout modified.
    sys.path.insert(0, str(source.parent))
    module = importlib.import_module("mg33c_actiononly_control")
    return module.ActionOnly


def control_episode(gym, entry, family, seed, mode, checkpoint, cap, public, original_digest, control):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space, "n", None) != 7:
            raise ValueError("MG38_WRONG_ORIGINAL_ENV")
        raw, _ = env.reset(seed=seed)
        first = public(raw)
        mission = first["mission"]
        initial = original_digest(first)
        actor = control(mode) if checkpoint is None else control.restore(checkpoint)
        if actor.mode != mode:
            raise ValueError("MG38_WRONG_RESTORED_MODE")
        start_count = actor.total
        events = []
        for n in range(1, cap + 1):
            before = public(raw)
            if before["mission"] != mission:
                raise ValueError("MG38_MISSION_CHANGED")
            action = actor.choose()  # Proven action-only: no scene passed to selector.
            raw2, reward, term, trunc, _ = env.step(action)
            after = public(raw2)
            if (after["mission"] != mission or type(term) is not bool or type(trunc) is not bool
                or not math.isfinite(float(reward))):
                raise ValueError("MG38_INVALID_SOURCE_FEEDBACK")
            bsha = original_digest(before); asha = original_digest(after)
            actor.observe_selected(action, bsha, asha, float(reward), term)
            events.append({"index": n, "before": before, "action": action,
                           "after": after, "mission": mission,
                           "policy_status": "MG38_UNCHANGED_MG33C_" + mode,
                           "reward": float(reward), "terminated": term, "truncated": trunc,
                           "before_sha256": bsha, "after_sha256": asha,
                           "external_actions": 0})
            raw = raw2
            if term or trunc:
                break
        state = actor.checkpoint()
        restored = control.restore(state)
        if restored.checkpoint() != state or restored.total != start_count + len(events):
            raise ValueError("MG38_MG33C_COLD_SOURCE_STATE_LOSS")
        if len(events) == cap and len({e["action"] for e in events}) < 4:
            raise ValueError("MG38_CORRECTED_CONTROL_DEGENERATE_IN_REAL_WORLD")
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
    SCHEMA = "mg38.empirical-public-action-two-step-model.v1"

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
            raise ValueError("MG38_DOUBLE_CHOOSE_WITHOUT_OWN_FEEDBACK")
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
            raise ValueError("MG38_NOT_OWN_SELECTED_VALID_SOURCE_FEEDBACK")
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
            raise ValueError("MG38_CANNOT_CHECKPOINT_PENDING_ACTION")
        return json.dumps({"schema": self.SCHEMA, "edges": self.edges,
                           "visits": self.visits,
                           "global_actions": self.global_actions, "total": self.total},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

    @classmethod
    def restore(cls, raw):
        wire = json.loads(raw)
        if (set(wire) != {"schema", "edges", "visits", "global_actions", "total"}
            or wire["schema"] != cls.SCHEMA):
            raise ValueError("MG38_COLD_SCHEMA")
        a = cls(wire["edges"], wire["visits"], wire["global_actions"], wire["total"])
        if (raw != a.checkpoint() or len(a.global_actions) != 7
            or type(a.total) is not int or a.total < 0
            or a.total != sum(g["n"] for g in a.global_actions)
            or a.total != sum(c["n"] for r in a.edges.values() for c in r.values())
            or any(c["n"] != sum(c["next"].values())
                   for r in a.edges.values() for c in r.values())):
            raise ValueError("MG38_COLD_EMPIRICAL_MODEL_DIVERGED")
        return a


def model_episode(gym, entry, family, seed, prior, cap, public, original_digest):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space, "n", None) != 7:
            raise ValueError("MG38_NOT_SOURCE_ORIGINAL_SEVEN_ACTION")
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
                raise ValueError("MG38_PUBLIC_MISSION_CHANGED")
            action = actor.choose(before)
            raw2, reward, term, trunc, _ = env.step(action)
            after = public(raw2)
            if after["mission"] != mission or type(term) is not bool or type(trunc) is not bool:
                raise ValueError("MG38_INVALID_ORIGINAL_TERMINAL_OR_MISSION")
            actor.observe_selected(before, action, after, float(reward), term)
            events.append({
                "index": number, "before": before, "action": action, "after": after,
                "mission": mission, "policy_status": "MG38_EMPIRICAL_MODEL_BASED_SELECTED",
                "reward": float(reward), "terminated": term, "truncated": trunc,
                "before_sha256": original_digest(before),
                "after_sha256": original_digest(after), "external_actions": 0})
            raw = raw2
            if term or trunc:
                break
        checkpoint = actor.checkpoint()
        if (EmpiricalActionModel.restore(checkpoint).checkpoint() != checkpoint
            or actor.total != beginning + len(events)):
            raise ValueError("MG38_SELECTED_SOURCE_MEMORY_NOT_RESTORED")
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





class NavigationAwareModel(EmpiricalActionModel):
    """Bounded conventional empirical model with rotation-neutral discovery.

    It can use generic public front-object affordance priors, but cannot
    match the mission target, read private world pose, or script a route.
    All observed edges and rewards are own selected original source outcomes.
    """
    SCHEMA = "mg38.navigation-aware-source-selected-public-model.v1"

    def __init__(self, edges=None, visits=None, global_actions=None, total=0,
                 turn_chain=0, last_forward_nochange=False):
        super().__init__(edges, visits, global_actions, total)
        self.turn_chain = turn_chain
        self.last_forward_nochange = last_forward_nochange

    def begin_episode(self):
        self.turn_chain = 0
        self.last_forward_nochange = False
        if self.pending is not None:
            raise ValueError("MG38_PENDING_SOURCE_ACTION_ACROSS_SEED")

    def choose(self, public):
        if self.pending is not None:
            raise ValueError("MG38_DOUBLE_CHOICE_BEFORE_ORIGINAL_FEEDBACK")
        key = digest(public)
        first = int(key[:2], 16) % 7
        front = public["image"][3][5]
        row = self.edges.get(key, {})
        chosen = None
        best = None
        for offset in range(7):
            action = (first + offset) % 7
            cell = row.get(str(action))
            local_count = cell["n"] if cell else 0
            g = self.global_actions[action]
            g_count = g["n"]
            effect = (g["changed"] + 0.5) / (g_count + 1)
            novel = (g["novel"] + 0.5) / (g_count + 1)
            goal = (g["goals"] + 0.25) / (g_count + 1)
            if action == 2:
                # Forward public change is *not* assumed to prove locomotion.
                local_nochange = (0 if cell is None else
                                  (cell["n"] - cell["changed"]) / cell["n"])
                score = (2.3 + 1.7 / (1 + local_count)
                         + 1.0 * novel - 2.0 * local_nochange)
            elif action in (0, 1):
                # Rotations NEVER get credit for changing egocentric public SHA.
                # Rotation is still eligible after unsuccessful own forward.
                score = (0.4 + 0.4 / (1 + local_count)
                         + 2.5 * int(self.last_forward_nochange)
                         - 1.25 * self.turn_chain)
                if self.turn_chain >= 2:
                    score -= 8.0
            else:
                score = (0.6 + 1.7 / (1 + local_count) + 2.0 * goal
                         + 0.7 * effect - 0.1 * local_count)
                # Public object classes only; NOT a mission-target matcher.
                if action == 3 and front[0] in (5,6,7):
                    score += 2.2
                elif action == 5 and front[0] == 4:
                    score += 2.2
            # Keep reward tied only to selected empirical source consequences.
            if cell is not None:
                score += 2.0 * cell["goals"] / (1 + cell["n"])
            if best is None or score > best:
                best = score
                chosen = action
        self.pending = (key, chosen)
        return chosen

    def observe_selected(self, before, action, after, reward, terminated):
        # Parent validates selected-only feedback, updates the empirical
        # source-transition graph and rejects invalid/off-policy feedback.
        super().observe_selected(before, action, after, reward, terminated)
        if action in (0, 1):
            self.turn_chain += 1
        else:
            self.turn_chain = 0
        self.last_forward_nochange = (
            action == 2 and digest(before) == digest(after))

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("MG38_PENDING_STATE_CANNOT_BE_CHECKPOINTED")
        body = {"schema": self.SCHEMA, "edges": self.edges,
                "visits": self.visits, "global_actions": self.global_actions,
                "total": self.total, "turn_chain": self.turn_chain,
                "last_forward_nochange": self.last_forward_nochange}
        return json.dumps(body,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True).encode("utf-8")

    @classmethod
    def restore(cls, raw):
        d = json.loads(raw)
        if (set(d) != {"schema","edges","visits","global_actions","total",
                       "turn_chain","last_forward_nochange"}
            or d["schema"] != cls.SCHEMA or type(d["turn_chain"]) is not int
            or d["turn_chain"] < 0
            or type(d["last_forward_nochange"]) is not bool):
            raise ValueError("MG38_INVALID_COLD_NAVIGATION_MODEL_SCHEMA")
        model = cls(d["edges"],d["visits"],d["global_actions"],d["total"],
                    d["turn_chain"],d["last_forward_nochange"])
        if (model.checkpoint() != raw or model.total < 0
            or model.total != sum(x["n"] for x in model.global_actions)
            or model.total != sum(cell["n"] for row in model.edges.values()
                                  for cell in row.values())
            or any(cell["n"] != sum(cell["next"].values())
                   for row in model.edges.values() for cell in row.values())):
            raise ValueError("MG38_EMPIRICAL_COLD_SOURCE_STATE_DIVERGED")
        return model


def navigation_episode(gym, entry, family, seed, prior, cap, public, original_digest):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space,"n",None) != 7:
            raise ValueError("MG38_WRONG_AUTHENTIC_FARAMA_WORLD")
        raw, _ = env.reset(seed=seed)
        first = public(raw)
        start = original_digest(first)
        mission = first["mission"]
        model = NavigationAwareModel() if prior is None else NavigationAwareModel.restore(prior)
        model.begin_episode()
        previous_samples = model.total
        events = []
        for index in range(1,cap+1):
            before = public(raw)
            if before["mission"] != mission:
                raise ValueError("MG38_ORIGINAL_MISSION_CHANGED_DURING_EPISODE")
            action = model.choose(before)
            raw2, reward, terminated, truncated, _ = env.step(action)
            after = public(raw2)
            if (after["mission"] != mission or type(terminated) is not bool
                or type(truncated) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG38_ORIGINAL_WORLD_SELECTED_FEEDBACK_INVALID")
            model.observe_selected(before,action,after,float(reward),terminated)
            events.append({"index":index,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":terminated,"truncated":truncated,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG38_ROTATION_NEUTRAL_EMPIRICAL_MODEL_SELECTED"})
            raw = raw2
            if terminated or truncated:
                break
        checkpoint = model.checkpoint()
        if (NavigationAwareModel.restore(checkpoint).checkpoint() != checkpoint
            or model.total != previous_samples + len(events)):
            raise ValueError("MG38_COLD_SOURCE_MODEL_OR_EPISODE_SAMPLES_LOST")
        return ({
            "family":family,"role":ROLES[8],"seed_dev_exposed":seed,
            "public_start_sha256":start,"original_public_mission":mission,
            "original_source_actions":len(events),
            "prior_selected_source_samples":previous_samples,
            "selected_source_samples_after":model.total,
            "original_terminal_goal_rewards":
                sum(int(e["reward"]>0 and e["terminated"]) for e in events),
            "observed_public_changes":
                sum(e["before_sha256"]!=e["after_sha256"] for e in events),
            "unique_public_views":len({e["before_sha256"] for e in events}),
            "distinct_actions":len({e["action"] for e in events}),
            "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
            "source_events_sha256":original_digest(events),
            "source_events":events
        }, checkpoint)
    finally:
        env.close()



def summarize(rows):
    totals = {}
    for family in FAMILIES:
        totals[family] = {}
        for role in ROLES:
            group = [r for r in rows if r["family"] == family and r["role"] == role]
            if len(group) != 3 or group[0]["prior_selected_source_samples"] not in (0, None):
                raise ValueError("MG38_MISSING_THREE_COLD_SOURCE_SEEDS")
            if role != ROLES[-1]:
                for a, b in zip(group, group[1:]):
                    if a["selected_source_samples_after"] != b["prior_selected_source_samples"]:
                        raise ValueError("MG38_ROLE_MEMORY_NOT_CONTINUOUS")
            counts = collections.Counter()
            target_contexts = set()
            door_contexts = set()
            action_hist = [0] * 7
            positive = 0
            for r in group:
                if original_digest_events(r) is False:
                    raise ValueError("MG38_SOURCE_EVENT_DIGEST_DRIFT")
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
                raise ValueError("MG38_SELECTED_ACTION_COUNT_MISMATCH")
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
        raise ValueError("MG38_NOT_PINNED_ORIGINAL_MINIGRID_SOURCE")
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
                elif role == ROLES[8]:
                    row, state = navigation_episode(
                        gym, registry[family], family, seed, carried[role], 192,
                        public, original_digest)
                else:
                    raise ValueError("MG38_INVALID_ROLE")
                row["role"] = role
                if role != ROLES[-1]:
                    carried[role] = state
                results.append(row)
                same_seed_rows.append(row)
            if len({r["public_start_sha256"] for r in same_seed_rows}) != 1:
                raise ValueError("MG38_UNEQUAL_SOURCE_START")
    if len(results) != 120 or any(not (1 <= r["original_source_actions"] <= 192) for r in results):
        raise ValueError("MG38_MISSING_REAL_SOURCE_EPISODES")
    table = summarize(results)
    unfamiliar = FAMILIES[1:]
    candidate = ROLES[8]
    controls = (ROLES[7],ROLES[2],ROLES[3],ROLES[5],ROLES[6])
    positive = {role: sum(table[f][role]["positive_goal_episodes"] for f in unfamiliar)
                for role in (candidate,*controls)}
    effects = {role: sum(table[f][role]["target_disappearance"] for f in unfamiliar)
               for role in (candidate,*controls)}
    successful_families = sum(table[f][candidate]["positive_goal_episodes"] > 0
                              for f in unfamiliar)
    successful_difficult = any(table[f][candidate]["positive_goal_episodes"] > 0
                               for f in FAMILIES[1:3])
    action_histogram = lambda role: [sum(table[f][role]["action_histogram"][i]
                                          for f in FAMILIES) for i in range(7)]
    ca = action_histogram(candidate)
    baseline = action_histogram(ROLES[7])
    candidate_turn_fraction = (ca[0]+ca[1])/sum(ca)
    baseline_turn_fraction = (baseline[0]+baseline[1])/sum(baseline)
    supported = (successful_families >= 2 and successful_difficult
                 and effects[candidate] >= 1
                 and all(positive[candidate] > positive[r] for r in controls)
                 and candidate_turn_fraction < baseline_turn_fraction)
    labels = p["dev_filter"]
    classification = labels["pass"] if supported else labels["fail"]
    source = {
        "schema": "itd02.mg38.navigation-aware-original-public-model-dev-source.v1",
        "classification": classification,
        "source_parent": PARENT,
        "farama_source": UPSTREAM,
        "qualified_actiononly_source": CORRECTED,
        "qualified_actiononly_blob_sha1": BLOB,
        "original_120_episodes": results,
        "original_selected_action_count": sum(r["original_source_actions"] for r in results),
        "per_family_per_role": table,
        "navigation_aware_vs_matched_controls": {
            "positive_goal_episodes": positive,
            "exact_target_effects": effects,
            "candidate_positive_unfamiliar_families": successful_families,
            "candidate_positive_unlock_or_blocked": successful_difficult,
            "candidate_turn_fraction": candidate_turn_fraction,
            "original_mg36_turn_fraction": baseline_turn_fraction,
            "candidate_action_histogram": ca,
            "original_mg36_action_histogram": baseline,
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
        if p["dev_filter"]["candidate"] != ROLES[8] or tuple(p["dev_filter"]["controls"]) != (ROLES[7],ROLES[2],ROLES[3],ROLES[5],ROLES[6]):
            raise ValueError("MG38_FROZEN_COMPARATOR_SET_DRIFT")
        before = {"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
                  "direction":0,"mission":"pick up the red box"}
        after = dict(before,direction=1)
        actor=NavigationAwareModel()
        selected=[]
        for k in range(42):
            action=actor.choose(before)
            if k==0:
                try:
                    actor.observe_selected(before,(action+1)%7,after,0.0,False)
                except ValueError:
                    pass
                else:
                    raise ValueError("MG38_OFFPOLICY_FEEDBACK_NOT_REJECTED")
            actor.observe_selected(before,action,
                                   before if action==2 else after,0.0,False)
            selected.append(action)
        if 2 not in selected or len(set(selected))<2:
            raise ValueError("MG38_SYNTHETIC_NO_FORWARD_OR_ACTION_DIVERSITY")
        raw=actor.checkpoint()
        twin=NavigationAwareModel.restore(raw)
        if twin.checkpoint()!=raw:
            raise ValueError("MG38_SYNTHETIC_MEMORY_ROUNDTRIP_BROKEN")
        twin.begin_episode()
        if twin.total!=42 or twin.turn_chain!=0 or twin.last_forward_nochange:
            raise ValueError("MG38_EPISODE_RESET_ERASES_LEARNED_MEMORY")
        print("MG38_FROZEN_ROTATION_NEUTRAL_EMPIRICAL_CONTROL_COLD_SOURCE_PREFLIGHT_PASS")
        return
    if opt.compare:
        a, b = [json.loads(x.read_text(encoding="utf-8")) for x in opt.compare]
        if (a.get("source") != b.get("source")
            or a.get("canonical_source_sha256") != b.get("canonical_source_sha256")
            or a.get("canonical_source_sha256") != digest(a["source"])
            or len(a["source"]["original_120_episodes"]) != 120
            or a["source"]["zero_external_actions"] is not True
            or a["source"]["scientific_first_use"] is not False):
            raise ValueError("MG38_TWO_ORIGINAL_PROCESSES_NOT_MATCHED")
        print("MG38_TWO_ORIGINAL_SOURCE_PROCESSES_IDENTICAL", a["canonical_source_sha256"])
        print("MG38_FROZEN_DEV_CLASSIFICATION", a["source"]["classification"])
        print("MG38_NAVIGATION_CONTROL_VS_MATCHED_ORIGINAL", json.dumps(
            a["source"]["navigation_aware_vs_matched_controls"], sort_keys=True))
        return
    if any(x is None for x in (opt.source_root, opt.native_go, opt.control_root, opt.output)):
        ap.error("require --source-root --native-go --control-root --output")
    start = time.perf_counter()
    try:
        result = execute(opt.source_root, opt.native_go, opt.control_root, p)
    except Exception as e:
        result = {"schema": "itd02.mg38.navigation-aware-original-public-model-dev-source.v1",
                  "classification": "MG38_ORIGINAL_WORLD_SOURCE_BLOCKED_NO_SCIENCE",
                  "error_type": type(e).__name__, "error": str(e),
                  "trace_tail": traceback.format_exc().splitlines()[-15:]}
    result["host_wall_time_outside_canonical_source_seconds"] = round(time.perf_counter() - start, 6)
    opt.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    cl = result.get("classification", result.get("source", {}).get(
        "classification", "MG38_MISSING_SOURCE_CLASSIFICATION_BLOCKED"))
    print("MG38_ORIGINAL_SOURCE_CLASSIFICATION", cl)
    if "BLOCKED" in cl:
        raise ValueError(result.get("error", "MG38_BLOCKED_SOURCE"))
    print("MG38_ORIGINAL_SOURCE_SHA256", result["canonical_source_sha256"])


if __name__ == "__main__":
    main()

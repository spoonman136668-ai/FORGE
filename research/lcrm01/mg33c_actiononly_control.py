#!/usr/bin/env python3
"""MG33-C: bounded task-agnostic action-only exploration control preflight.

Synthetic source-only qualification. Does NOT launch MiniGrid, enact a genuine
policy, assign counterfactual rewards, or claim native intelligence improvement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "mg33c_actiononly_control_prereg.json"
SCHEMA = "itd02.mg33c.actiononly-control-state.v1"
ACTIONS = tuple(range(7))

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")

def hash_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def frozen():
    p = json.loads(FROZEN.read_text(encoding="utf-8"))
    if (p.get("schema") != "itd02.mg33c.non-degenerate-action-only-control-preflight.v1"
            or p.get("phase") != "PROSPECTIVE_PREREG_BEFORE_EXECUTABLE"
            or p["parent"]["mg32_head"] != "4ba7933b988860ac7f7dd53ec5506f80d0a43db1"
            or p["synthetic_simulation"]["episodes"] != 3
            or p["synthetic_simulation"]["steps_each"] != 192
            or not all(p["isolation"].values())):
        raise ValueError("MG33C_FROZEN_PROTOCOL_CHANGED")
    return p

class ActionOnly:
    """Own selected action counts + public digest feedback only, no context identity."""
    def __init__(self, mode):
        if mode not in ("ucb", "round_robin"):
            raise ValueError("MG33C_INVALID_CONTROL_MODE")
        self.mode = mode
        self.total = 0
        self.counts = [0] * 7
        self.changes = [0] * 7
        self.goals = [0] * 7
        self.pending = None

    def choose(self):
        if self.pending is not None:
            raise ValueError("MG33C_DOUBLE_CHOICE_WITHOUT_FEEDBACK")
        if self.mode == "round_robin":
            action = self.total % 7
        else:
            floor = max(1, self.total // 14)
            deficit = [a for a in ACTIONS if self.counts[a] < floor]
            if deficit:
                action = min(deficit, key=lambda a: (self.counts[a], (a - self.total) % 7))
            else:
                def score(a):
                    n = self.counts[a]
                    fit = (self.changes[a] + 1) / (n + 2)
                    reward = (self.goals[a] + 1) / (n + 2)
                    optimism = math.sqrt(2 * math.log(self.total + 8) / (n + 1))
                    return fit + .25 * reward + optimism
                action = min(ACTIONS, key=lambda a: (-score(a), (a - self.total) % 7))
        self.pending = action
        return action

    def observe_selected(self, action, before_sha256, after_sha256, reward, terminated):
        if type(action) is not int or action not in ACTIONS or action != self.pending:
            raise ValueError("MG33C_NOT_OWN_SELECTED_ACTION_FEEDBACK")
        if (not isinstance(before_sha256, str) or not isinstance(after_sha256, str)
                or len(before_sha256) != 64 or len(after_sha256) != 64
                or any(c not in "0123456789abcdef" for c in before_sha256 + after_sha256)):
            raise ValueError("MG33C_INVALID_PUBLIC_DIGEST")
        if (type(reward) not in (int, float) or not math.isfinite(reward)
                or reward < 0 or type(terminated) is not bool):
            raise ValueError("MG33C_BAD_SELECTED_REWARD_OR_TERMINAL")
        self.counts[action] += 1
        self.changes[action] += int(before_sha256 != after_sha256)
        self.goals[action] += int(reward > 0 and terminated)
        self.total += 1
        self.pending = None

    def checkpoint(self):
        return canonical({"schema": SCHEMA, "mode": self.mode, "total": self.total,
                          "counts": self.counts, "changes": self.changes,
                          "goals": self.goals, "pending": self.pending})

    @classmethod
    def restore(cls, blob):
        w = json.loads(blob)
        if (set(w) != {"schema", "mode", "total", "counts", "changes", "goals", "pending"}
                or w["schema"] != SCHEMA):
            raise ValueError("MG33C_INVALID_CHECKPOINT_SCHEMA")
        a = cls(w["mode"])
        a.total = w["total"]
        a.counts = w["counts"]
        a.changes = w["changes"]
        a.goals = w["goals"]
        a.pending = w["pending"]
        if (type(a.total) is not int or a.total < 0 or
            any(type(z) is not int or z < 0 for xs in (a.counts, a.changes, a.goals) for z in xs)
            or any(len(xs) != 7 for xs in (a.counts, a.changes, a.goals))
            or a.total != sum(a.counts)
            or any(a.changes[i] > a.counts[i] or a.goals[i] > a.counts[i] for i in ACTIONS)
            or (a.pending is not None and (type(a.pending) is not int or a.pending not in ACTIONS))
            or blob != a.checkpoint()):
            raise ValueError("MG33C_CORRUPTED_COLD_SELECTED_STATE")
        return a

def simulate(mode, public_variant):
    actor = ActionOnly(mode)
    per_episode = []
    first = None
    for episode in range(3):
        chosen = []
        for step in range(192):
            before = hash_text(f"SYNTHETIC_ONLY::{episode}:{step}:before")
            a = actor.choose()
            if first is None:
                first = a
                try:
                    actor.observe_selected((a + 1) % 7, before, before, 0, False)
                except ValueError as exc:
                    assert str(exc) == "MG33C_NOT_OWN_SELECTED_ACTION_FEEDBACK"
                else:
                    raise AssertionError("MG33C_OFFPOLICY_FEEDBACK_ACCEPTED")
            changed = (episode + step + a * 3) % 5 in (0, 2, 4)
            after = hash_text(f"SYNTHETIC_ONLY::{episode}:{step}:after") if changed else before
            actor.observe_selected(a, before, after, 1.0 if a == 2 and step % 19 == 0 else 0.0,
                                   a == 2 and step % 19 == 0)
            chosen.append(a)
            if public_variant == "arbitrary-alternate-mission-and-image":
                assert a in ACTIONS  # No public context enters the selector API.
        counts = [chosen.count(a) for a in ACTIONS]
        assert len(set(chosen)) == 7
        assert min(counts) >= (27 if mode == "round_robin" else 8), counts
        assert counts[2] > 0 and counts[3] > 0 and counts[5] > 0
        state = actor.checkpoint()
        actor = ActionOnly.restore(state)
        assert actor.checkpoint() == state
        per_episode.append({"episode": episode, "counts": counts,
                            "trace_sha256": hashlib.sha256(bytes(chosen)).hexdigest(),
                            "state_sha256": hashlib.sha256(state).hexdigest()})
    return {"mode": mode, "episodes": per_episode,
            "full_selected_count": actor.total,
            "full_counts": actor.counts, "context_supplied_to_policy": False}

def legacy_negative():
    # Exact inherited MG31 source is unchanged. Its synthetic action-0 collapse
    # must be reproduced independently rather than invented in this control.
    from mg31_original_public_exploration import Explorer
    src = {"image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)],
           "direction": 0, "mission": "pick up the red box"}
    successor = dict(src, direction=1)
    actor = Explorer("action")
    trace = []
    for _ in range(192):
        choice = actor.choose(src)
        trace.append(choice)
        actor.observe(src, choice, successor, 0, False)
    if trace != [0] * 192:
        raise AssertionError("MG33C_LEGACY_NEGATIVE_NOT_REPRODUCED")
    return {"selected": len(trace), "unique_actions": len(set(trace)),
            "all_turn_left": all(x == 0 for x in trace)}

def run():
    p = frozen()
    a = {mode: simulate(mode, "standard") for mode in ("ucb", "round_robin")}
    b = {mode: simulate(mode, "arbitrary-alternate-mission-and-image")
         for mode in ("ucb", "round_robin")}
    if a != b:
        raise AssertionError("MG33C_CONTEXT_LEAK_OR_NONDETERMINISM")
    c = {mode: simulate(mode, "standard") for mode in ("ucb", "round_robin")}
    if a != c:
        raise AssertionError("MG33C_SECOND_INDEPENDENT_REPRODUCTION_MISMATCH")
    original = legacy_negative()
    model = ActionOnly("ucb")
    selected = model.choose()
    h = hash_text("synthetic")
    for arg in (-1, float("nan")):
        try:
            model.observe_selected(selected, h, h, arg, False)
        except ValueError as exc:
            assert str(exc) == "MG33C_BAD_SELECTED_REWARD_OR_TERMINAL"
        else:
            raise AssertionError("MG33C_NEGATIVE_OR_NAN_REWARD_ACCEPTED")
    model.observe_selected(selected, h, h, 0, False)
    try:
        model.observe_selected(selected, h, h, 0, False)
    except ValueError as exc:
        assert str(exc) == "MG33C_NOT_OWN_SELECTED_ACTION_FEEDBACK"
    else:
        raise AssertionError("MG33C_DOUBLE_FEEDBACK_ACCEPTED")
    return {"classification": p["classification_if_pass"],
            "original_world_steps": 0, "scientific_first_use": False,
            "native_model_modified": False, "legacy_synthetic_negative": original,
            "synthetic_controls": a, "reproduction_identical": True,
            "source_kind": "synthetic_control_preflight_only"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--report", type=Path)
    opt = ap.parse_args()
    report = run()
    digest = hashlib.sha256(canonical(report)).hexdigest()
    print(report["classification"])
    print("MG33C_SOURCE_ONLY_TEST_RECEIPT_SHA256", digest)
    if opt.report:
        opt.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()

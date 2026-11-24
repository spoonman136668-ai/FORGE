"""Deterministic synthetic engineering benchmark for two-tier evidence.

This benchmark is intentionally synthetic. It checks algorithmic properties on
paired, predeclared two-context stationary/reversal schedules. It is not a
Yggdrasil training run, authenticated corpus result, transfer study, or science
acceptance. All arms receive identical observations. No I/O or randomness.
"""
from __future__ import annotations

import hashlib
import json

from scripts.two_tier_evidence_memory import TwoTierEvidence

SCHEMA = "forge.research.two-tier-synthetic-benchmark.v1"
ARMS = ("lifetime-only", "recent-only", "two-tier", "no-memory")
STEPS = 48
REVERSAL_AT = 24
CONTEXTS = (0, 1)


def _hash(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")).hexdigest()


class _Arm:
    def __init__(self, mode):
        self.mode = mode
        self.memory = TwoTierEvidence()

    def choose(self, context):
        if self.mode == "no-memory":
            return 0
        if self.mode == "lifetime-only":
            result = self.memory.choose_lifetime(context, minimum_support=2)
        elif self.mode == "recent-only":
            result = self.memory._winner(
                self.memory.recent_counts(context, 0),
                self.memory.recent_counts(context, 1), 2)
        else:
            result = self.memory.choose(context, minimum_support=2)
        return 0 if result is None else result

    def observe_both_actions(self, context, expected_action):
        # Paired full-feedback design: every arm receives both revealed action
        # outcomes, independent of its choice, preventing information imbalance.
        for action in (0, 1):
            self.memory.observe(context, action, int(action == expected_action))


def run_benchmark():
    schedule = []
    for step in range(STEPS):
        # Context 0 reverses at step 24; context 1 remains stationary throughout.
        winner0 = 0 if step < REVERSAL_AT else 1
        winner1 = 1
        schedule.append({"step": step, "winner_by_context": [winner0, winner1]})
    schedule_sha = _hash(schedule)
    arms = {name: _Arm(name) for name in ARMS}
    history = {name: {context: [] for context in CONTEXTS} for name in ARMS}
    for step, row in enumerate(schedule):
        for name, arm in arms.items():
            for context, winner in enumerate(row["winner_by_context"]):
                choice = arm.choose(context)
                history[name][context].append(int(choice == winner))
                arm.observe_both_actions(context, winner)

    result = {"schema": SCHEMA, "classification": "SYNTHETIC_ENGINEERING_DIAGNOSTIC",
              "schedule_sha256": schedule_sha, "steps": STEPS,
              "reversal_at": REVERSAL_AT, "contexts": len(CONTEXTS),
              "paired_observation_policy": "both actions revealed equally to every arm",
              "arms": {}, "authenticated_source": False,
              "scientific_first_use": False, "scientific_gain_verified": False,
              "deployment_authorized": False, "paid_api_calls": 0, "model_calls": 0}
    for name, arm in arms.items():
        ctx0 = history[name][0]
        ctx1 = history[name][1]
        post = ctx0[REVERSAL_AT:]
        stable = ctx1
        first_correct = next((i for i, value in enumerate(post) if value), None)
        result["arms"][name] = {
            "context0_pre_reversal_accuracy": sum(ctx0[:REVERSAL_AT]) / REVERSAL_AT,
            "context0_post_reversal_accuracy": sum(post) / len(post),
            "context1_stationary_accuracy": sum(stable) / len(stable),
            "context0_adaptation_delay_steps": None if first_correct is None else first_correct,
            "lifetime_counts_context0_action0": list(arm.memory.lifetime_counts(0, 0)),
            "lifetime_counts_context0_action1": list(arm.memory.lifetime_counts(0, 1)),
            "learned_bytes": arm.memory.LEARNED_BYTES,
            "checkpoint_bytes": len(arm.memory.snapshot()),
        }
    return result


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), sort_keys=True, indent=2))

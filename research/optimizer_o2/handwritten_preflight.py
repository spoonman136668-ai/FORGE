"""Handwritten public-only O2 preflight. Scores are diagnostic, NEVER science GO."""
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from public_replay import POLICIES, PublicLearner, public_nll

# Thirty-two explicit two-field public observations. No source RNG or role birth.
TRAIN = (
    ("u", 1), ("v", 0), ("u", 1), ("v", 0),
    ("u", 1), ("v", 0), ("u", 1), ("v", 0),
    ("u", 1), ("v", 0), ("u", 1), ("v", 0),
    ("u", 0), ("v", 1), ("u", 0), ("v", 1),
    ("u", 0), ("v", 1), ("u", 0), ("v", 1),
    ("u", 1), ("v", 0), ("u", 1), ("v", 0),
)
PUBLIC_DEV = (
    ("u", 1), ("v", 0), ("u", 1), ("v", 0),
    ("u", 1), ("v", 0), ("u", 1), ("v", 0),
)


def preflight():
    receipts = {}
    for policy in POLICIES:
        learner = PublicLearner(policy)
        selected = []
        for k, (cue, outcome) in enumerate(TRAIN):
            learner.observe({"cue": cue, "outcome": outcome})
            if (k + 1) % 8 == 0 and policy != "FULL_HISTORY_COUNTS_DIAGNOSTIC":
                selected.append(learner.consolidate())
        original = learner.checkpoint()
        losses = [public_nll(y, learner.predict(cue)) for cue, y in PUBLIC_DEV]
        assert learner.checkpoint() == original, "DEV_EVALUATION_MUTATED_TRAINING"
        receipts[policy] = {
            "mean_handwritten_dev_nll": sum(losses) / len(losses),
            "state_bytes": len(original),
            "observations_shared": learner.observations,
            "consolidation_calls": learner.consolidations,
            "replay_updates": learner.replay_updates,
            "selected_public_sequence_indices": selected,
            "learned_state_checksum": json.loads(original)["sha256"],
        }
    return {
        "schema": "forge.optimizer.o2.handwritten-dev-preflight.v1",
        "source": "HANDWRITTEN_PUBLIC_ONLY",
        "experimental_roles_generated": 0,
        "protected_first_use": False,
        "scientific_decision": "NOT_EVALUATED",
        "fsa_grant": "NONE",
        "conventional_strong_controls_completed": False,
        "candidate_policy_hardcoded": True,
        "public_dev_evaluated_without_training": True,
        "arms": receipts,
    }


if __name__ == "__main__":
    print(json.dumps(preflight(), indent=2, sort_keys=True, allow_nan=False))

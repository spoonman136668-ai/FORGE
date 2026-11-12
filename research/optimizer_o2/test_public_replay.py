"""Strict engineering tests for source-only O2; no generator/role/hidden state."""
import hashlib
import json
import math
import unittest

from handwritten_preflight import PUBLIC_DEV, TRAIN, preflight
from public_replay import (
    BUFFER_CAP, MAX_EVENTS, POLICIES, PublicLearner,
    InvalidPublicExperience, canonical,
)


class TestPublicOnlyMechanismScreen(unittest.TestCase):
    def test_candidate_learns_persistent_predictive_values(self):
        m = PublicLearner("SURPRISE_REPLAY")
        before = m.predict("u")
        for _ in range(3):
            m.observe({"cue": "u", "outcome": 1})
        self.assertGreater(m.predict("u"), before)
        self.assertEqual(PublicLearner.restore(m.checkpoint()).checkpoint(),
                         m.checkpoint())

    def test_same_observations_and_replay_budget_all_policies(self):
        a = preflight()
        self.assertEqual(a["scientific_decision"], "NOT_EVALUATED")
        self.assertEqual(a["experimental_roles_generated"], 0)
        self.assertEqual(set(a["arms"]), set(POLICIES))
        for policy in POLICIES:
            receipt = a["arms"][policy]
            self.assertEqual(receipt["observations_shared"], len(TRAIN))
            self.assertTrue(math.isfinite(receipt["mean_handwritten_dev_nll"]))
            self.assertGreater(receipt["state_bytes"], 0)
            if policy == "FULL_HISTORY_COUNTS_DIAGNOSTIC":
                self.assertEqual(receipt["replay_updates"], 0)
            else:
                self.assertEqual(receipt["replay_updates"], 12)
                self.assertEqual(receipt["consolidation_calls"], 3)
        self.assertEqual(len(PUBLIC_DEV), 8)

    def test_deterministic_replay_same_source(self):
        self.assertEqual(preflight(), preflight())

    def test_surprise_retains_unexpected_public_case_when_fifo_evicts(self):
        a = PublicLearner("SURPRISE_REPLAY")
        b = PublicLearner("FIFO_REPLAY")
        experience = (("u", 1), ("u", 1)) + tuple(("u", 0) for _ in range(14))
        for cue, y in experience:
            item = {"cue": cue, "outcome": y}
            a.observe(item)
            b.observe(item)
        self.assertEqual(a.observations, b.observations)
        self.assertLessEqual(len(a.buffer), BUFFER_CAP)
        self.assertEqual(len(b.buffer), BUFFER_CAP)
        self.assertNotEqual([r["seq"] for r in a.buffer],
                            [r["seq"] for r in b.buffer])

    def test_invalid_public_or_privileged_fields_refused_without_mutation(self):
        m = PublicLearner("SURPRISE_REPLAY")
        snapshot = m.checkpoint()
        invalid = (
            {"cue": "u", "outcome": 1, "hidden_state": 1},
            {"cue": "u", "outcome": True},
            {"cue": "z", "outcome": 1},
            {"cue": "u", "outcome": float("nan")},
            {"cue": "u", "outcome": 1, "future": 1},
        )
        for example in invalid:
            with self.subTest(example=example), self.assertRaises(InvalidPublicExperience):
                m.observe(example)
            self.assertEqual(m.checkpoint(), snapshot)

    def test_capacity_and_replay_restart(self):
        m = PublicLearner("SURPRISE_REPLAY")
        for i in range(MAX_EVENTS):
            m.observe({"cue": "u", "outcome": i % 2})
        self.assertEqual(m.observations, 48)
        with self.assertRaises(InvalidPublicExperience):
            m.observe({"cue": "u", "outcome": 1})
        self.assertEqual(len(m.buffer), BUFFER_CAP)
        m.consolidate()
        recovered = PublicLearner.restore(m.checkpoint())
        self.assertEqual(recovered.predict("u"), m.predict("u"))
        self.assertEqual(recovered.checkpoint(), m.checkpoint())

    def test_recomputed_forged_budgets_fail_closed(self):
        model = PublicLearner("FIXED_RANDOM_REPLAY")
        for _ in range(3):
            model.observe({"cue": "u", "outcome": 1})
        obj = json.loads(model.checkpoint())
        obj["state"]["observations"] = 49
        obj["sha256"] = hashlib.sha256(canonical(obj["state"])).hexdigest()
        with self.assertRaises(InvalidPublicExperience):
            PublicLearner.restore(canonical(obj))

    def test_model_state_untouched_during_handwritten_dev(self):
        # Source-only checks are not scientific significance or independent transfer.
        for policy in POLICIES:
            model = PublicLearner(policy)
            for cue, y in TRAIN:
                model.observe({"cue": cue, "outcome": y})
            before = model.checkpoint()
            _ = [model.predict(cue) for cue, _ in PUBLIC_DEV]
            self.assertEqual(model.checkpoint(), before)


if __name__ == "__main__":
    unittest.main()

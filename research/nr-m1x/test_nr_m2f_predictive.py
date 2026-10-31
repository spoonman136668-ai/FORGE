"""NR-M2F bounded source-only development checks, no original world actions."""
import hashlib
import unittest
from nr_m2e_extended_public import full_public, GOAL_MISSION
from nr_m2f_predictive import SelectedPublicPredictor

def frame(direction=0, mission=GOAL_MISSION):
    return {"image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)],
            "direction": direction, "mission": mission}

class PredictiveSourceOnlyTest(unittest.TestCase):
    def test_original_actions_full_frame_noop_and_abstain(self):
        a = frame()
        b = frame(1)
        for action in range(7):
            p = SelectedPublicPredictor(full_public)
            self.assertFalse(p.predict(a, action)[1]["supported"])
            for _ in range(2):
                p.begin(a)
                p.select(a, action)
                p.feedback(a, action, b if action == 2 else a)
            predicted, support = p.predict(a, action)
            self.assertTrue(support["supported"])
            self.assertEqual(predicted, b if action == 2 else a)
            self.assertEqual(support["no_effect"], action != 2)
            self.assertEqual(p.forecast(a, [action])[0], predicted)
            with self.assertRaises(ValueError):
                p.select(a, 7)
            with self.assertRaises(ValueError):
                p.select(a, True)
            with self.assertRaises(ValueError):
                p.predict(dict(a, agent_pos=[1, 1]), action)

    def test_selected_custody_contradiction_and_cold_snapshot(self):
        a, b, c = frame(), frame(1), frame(2)
        p = SelectedPublicPredictor(full_public)
        p.begin(a)
        with self.assertRaises(ValueError):
            p.feedback(a, 2, b)
        p.select(a, 2)
        with self.assertRaises(ValueError):
            p.feedback(a, 1, b)
        with self.assertRaises(ValueError):
            p.checkpoint()
        p.feedback(a, 2, b)
        with self.assertRaises(ValueError):
            p.feedback(a, 2, b)
        p.begin(a); p.select(a, 2); p.feedback(a, 2, b)
        self.assertTrue(p.predict(a, 2)[1]["supported"])
        p.begin(a); p.select(a, 2); p.feedback(a, 2, c)
        predicted, evidence = p.predict(a, 2)
        self.assertIsNone(predicted)
        self.assertEqual(evidence["reason"], "CONTRADICTORY_SELECTED_EFFECTS")
        raw = p.checkpoint()
        restored = SelectedPublicPredictor.restore(full_public, raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(restored.checkpoint(), raw)
        with self.assertRaises(ValueError):
            SelectedPublicPredictor.restore(full_public, raw, "0"*64)

    def test_multi_step_and_no_unseen_oracle(self):
        a, b, c = frame(), frame(1), frame(2)
        p = SelectedPublicPredictor(full_public)
        for _ in range(2):
            p.begin(a); p.select(a, 2); p.feedback(a, 2, b)
            p.select(b, 3); p.feedback(b, 3, c)
        self.assertEqual(p.forecast(a, [2, 3])[0], c)
        self.assertFalse(p.forecast(a, [2, 5])[1]["supported"])
        with self.assertRaises(ValueError):
            p.forecast(a, [2]*6)

if __name__ == "__main__":
    unittest.main()

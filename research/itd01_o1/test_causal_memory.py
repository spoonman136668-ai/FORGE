"""O1 public-only handwritten diagnostic tests; NEVER Q21/ITD protected roles."""
import hashlib
import json
import unittest

from causal_memory import CausalMemory, Refused, canonical


class TestCausalMemory(unittest.TestCase):
    def make_memory(self, names=("a", "b", "c", "decoy")):
        a, b, c, d = names
        m = CausalMemory(names)
        z = {a: 0, b: 0, c: 0, d: 0}
        # Explicitly handwritten eight public paired interventions.
        for _ in range(2):
            m.observe(a, dict(z), {a: 1, b: 1, c: 0, d: 0})
            m.observe(b, dict(z), {a: 0, b: 1, c: 1, d: 0})
            m.observe(c, dict(z), {a: 0, b: 0, c: 1, d: 0})
            m.observe(d, dict(z), {a: 0, b: 0, c: 0, d: 1})
        return m

    def test_two_hop_diagnostic_vs_direct_only(self):
        m = self.make_memory()
        self.assertIsNone(m.direct_effect("a", "c"))
        self.assertEqual(m.compose("a", "c"),
                         {"path": ["a", "b", "c"], "sign": 1, "hops": 2})
        self.assertIsNone(m.compose("a", "decoy"))
        self.assertEqual(m.trials, 8)

    def test_renamed_entities_and_retained_state(self):
        m = self.make_memory(("r7", "x2", "w9", "q4"))
        self.assertEqual(m.compose("r7", "w9")["path"], ["r7", "x2", "w9"])
        self.assertIsNone(m.direct_effect("r7", "w9"))
        self.assertIsNone(CausalMemory(m.entities).compose("r7", "w9"))
        recovered = CausalMemory.restore(m.checkpoint())
        self.assertEqual(m.checkpoint(), recovered.checkpoint())
        self.assertEqual(recovered.compose("r7", "w9"), m.compose("r7", "w9"))

    def test_zero_contrast_rejects_observational_correlation(self):
        m = CausalMemory(("a", "b"))
        for _ in range(2):
            m.observe("a", {"a": 0, "b": 1}, {"a": 1, "b": 1})
        self.assertIsNone(m.direct_effect("a", "b"))
        self.assertIsNone(m.compose("a", "b"))

    def test_inconsistent_signed_effect_abstains(self):
        m = CausalMemory(("a", "b"))
        for _ in range(2):
            m.observe("a", {"a": 0, "b": 0}, {"a": 1, "b": 1})
        self.assertEqual(m.direct_effect("a", "b"), 1)
        m.observe("a", {"a": 0, "b": 1}, {"a": 1, "b": 0})
        self.assertIsNone(m.direct_effect("a", "b"))

    def test_input_borders_and_no_mutation_on_refusal(self):
        m = CausalMemory(("a", "b"))
        bad = [
            ("a", {"a": 0, "b": 0, "hidden": 1}, {"a": 1, "b": 1}),
            ("a", {"a": 0, "b": 0}, {"a": 1, "b": 1, "future": 0}),
            ("a", {"a": 0, "b": 0}, {"a": 0, "b": 1}),
            ("a", {"a": 0, "b": 0}, {"a": True, "b": 1}),
        ]
        for trial in bad:
            with self.subTest(trial=trial), self.assertRaises(Refused):
                m.observe(*trial)
        self.assertEqual(m.trials, 0)
        with self.assertRaises(Refused):
            m.compose("a", "b", 3)
        with self.assertRaises(Refused):
            m.compose("a", "other")

    def test_checkpoint_tamper_and_semantic_forgery_refused(self):
        m = self.make_memory()
        raw = json.loads(m.checkpoint())
        raw["state"]["trials"] = 9
        with self.assertRaises(Refused):
            CausalMemory.restore(canonical(raw))
        forged = json.loads(m.checkpoint())
        forged["state"]["counts"][0]["hist"] = [0, 0, 99]
        forged["sha256"] = hashlib.sha256(canonical(forged["state"])).hexdigest()
        with self.assertRaises(Refused):
            CausalMemory.restore(canonical(forged))

    def test_48_trial_budget_and_entity_identity(self):
        with self.assertRaises(Refused):
            CausalMemory(("a", "a"))
        m = CausalMemory(("a", "b"))
        for _ in range(48):
            m.observe("a", {"a": 0, "b": 0}, {"a": 1, "b": 1})
        self.assertEqual(m.trials, 48)
        with self.assertRaises(Refused):
            m.observe("a", {"a": 0, "b": 0}, {"a": 1, "b": 1})
        self.assertEqual(m.trials, 48)


if __name__ == "__main__":
    unittest.main()

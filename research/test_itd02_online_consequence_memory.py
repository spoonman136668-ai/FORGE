"""Numerical-only isolated ITD02 source tests, NOT original science."""
import ast
import hashlib
import inspect
import json
import math
import unittest

import itd02_online_consequence_memory as mod


def fixture(start=0, stop=120):
    """Only this test fixture contains the hidden action -> outcome map."""
    rows = []
    for k in range(start, stop):
        a = k % 3
        obs = (math.sin(k * 0.23) * 0.8, math.cos(k * 0.17) * 0.7)
        y = (-1. + a) * 2. + (a + 1) * obs[0] - (2 - a) * obs[1]
        rows.append((obs, a, y))
    return rows


def assess(model, samples):
    return sum((model.predict(obs, a) - y) ** 2
               for obs, a, y in samples) / len(samples)


class OnlineConsequenceMemoryTests(unittest.TestCase):
    def test_protocol_pinned_before_source(self):
        self.assertEqual(mod.PROTOCOL_COMMIT,
                         "38234f3158bc6dacfe2328ab0cdfb6d1fe1c5676")
        self.assertEqual(mod.PROTOCOL_BLOB,
                         "fc415a6b81b1b94be427366e2af35ca5ef162461")
        self.assertEqual(mod.RIDGE, 0.1)
        self.assertEqual(mod.SCHEMA,
                         "forge.eureka.itd02.online-consequence-memory.dev.v1")

    def test_measured_consequence_learnt_without_hidden_world_features(self):
        data = fixture()
        m = mod.OnlineConsequenceMemory()
        self.assertEqual(m.predict((0., 0.), 0), 0.)
        self.assertEqual(m.predict((0., 0.), 2), 0.)
        for i, (obs, a, y) in enumerate(data):
            m.observe(i, obs, a, y)
        self.assertEqual(m.completed, 120)
        self.assertEqual(m.counts, [40, 40, 40])
        self.assertLess(assess(m, fixture(120, 180)), 0.01)
        self.assertGreater(m.predict((0., 0.), 2),
                           m.predict((0., 0.), 1))

    def test_action_blind_and_rotated_credit_negative_and_full_fitted_control(self):
        data = fixture()
        m = mod.OnlineConsequenceMemory()
        blind = mod.OnlineConsequenceMemory()
        rotated = mod.OnlineConsequenceMemory()
        for i, (obs, a, y) in enumerate(data):
            m.observe(i, obs, a, y)
            blind.observe(i, obs, 0, y)
            rotated.observe(i, obs, (a + 1) % 3, y)
        heldout = fixture(120, 180)  # Never supplied to any fitted model.
        candidate = assess(m, heldout)
        blind_mse = sum((blind.predict(obs, 0) - y) ** 2
                        for obs, a, y in heldout) / len(heldout)
        rotated_mse = assess(rotated, heldout)
        self.assertLess(candidate, 0.01)
        self.assertGreater(blind_mse, 2 * candidate)
        self.assertGreater(rotated_mse, 2 * candidate)
        # Fully fitted conventional action-specific ridge sees identical
        # samples and closed-form normal equations; no superiority claimed.
        fitted = mod.OnlineConsequenceMemory()
        for i, (obs, a, y) in enumerate(data):
            fitted.observe(i, obs, a, y)
        self.assertAlmostEqual(assess(fitted, heldout), candidate, places=14)

    def test_proposal_is_read_only_and_exploration_is_value_of_information_proxy(self):
        m = mod.OnlineConsequenceMemory()
        for i in range(80):
            m.observe(i, (0., 0.), 0, 0.5)
        before = m.checkpoint()
        exploit = m.propose((0., 0.), exploration_weight=0.)
        explore = m.propose((0., 0.), exploration_weight=1.)
        self.assertEqual(exploit["action"], 0)
        self.assertEqual(explore["action"], 1)
        self.assertTrue(explore["information_seeking"])
        self.assertFalse(explore["can_dispatch_original"])
        self.assertEqual(m.checkpoint(), before)

    def test_cold_restoration_extends_exact_new_experience(self):
        data = fixture()
        m = mod.OnlineConsequenceMemory()
        for i, (obs, a, y) in enumerate(data[:65]):
            m.observe(i, obs, a, y)
        packed, sha = m.checkpoint()
        cold = mod.OnlineConsequenceMemory.restore(packed, sha, 65)
        self.assertEqual(cold.checkpoint(), (packed, sha))
        for i, (obs, a, y) in enumerate(data[65:], start=65):
            m.observe(i, obs, a, y)
            cold.observe(i, obs, a, y)
        self.assertEqual(m.checkpoint(), cold.checkpoint())
        self.assertEqual(m.propose((0.45, -0.32), 0.3),
                         cold.propose((0.45, -0.32), 0.3))
        self.assertNotEqual(m.checkpoint()[1], sha)

    def test_invalid_observation_and_replay_fail_without_mutation(self):
        m = mod.OnlineConsequenceMemory(max_events=2)
        before = m.checkpoint()
        bad = [(-1, (0., 0.), 0, 1.),
               (1, (0., 0.), 0, 1.),
               (0, (2., 0.), 0, 1.),
               (0, (0., 0.), True, 1.),
               (0, (0., 0.), 3, 1.),
               (0, (0., 0.), 0, float("nan")),
               (0, (0., 0.), 0, 101.),
               (0, (0.,), 0, 1.)]
        for seq, obs, a, reward in bad:
            with self.assertRaises(ValueError):
                m.observe(seq, obs, a, reward)
            self.assertEqual(m.checkpoint(), before)
        m.observe(0, (0., 0.), 2, -1.)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SKIPPED"):
            m.observe(0, (0., 0.), 2, -1.)
        m.observe(1, (0., 0.), 2, -1.)
        with self.assertRaisesRegex(ValueError, "BUDGET_EXCEEDED"):
            m.observe(2, (0., 0.), 2, -1.)

    def test_cold_snapshot_hash_and_external_minimum_rejects(self):
        m = mod.OnlineConsequenceMemory()
        m.observe(0, (0., 0.), 1, 0.2)
        raw, digest = m.checkpoint()
        with self.assertRaises(ValueError):
            mod.OnlineConsequenceMemory.restore(raw.replace(b"0.2", b"0.3"), digest)
        with self.assertRaisesRegex(ValueError, "HISTORY_INCONSISTENT"):
            mod.OnlineConsequenceMemory.restore(raw, digest, minimum_completed=2)
        with self.assertRaises(ValueError):
            mod.OnlineConsequenceMemory.restore(raw, "bad")
        # Recomputed external hash does not make semantically invalid memory valid.
        d = json.loads(raw)
        d["grams"][0][0][0] = -100.
        invalid = mod._canonical(d)
        with self.assertRaises(ValueError):
            mod.OnlineConsequenceMemory.restore(invalid,
                                                hashlib.sha256(invalid).hexdigest())

    def test_duplicate_json_and_invalid_history_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SNAPSHOT_JSON_KEY"):
            mod.OnlineConsequenceMemory.restore(
                b'{"x":1,"x":2}', hashlib.sha256(b'{"x":1,"x":2}').hexdigest())
        m = mod.OnlineConsequenceMemory()
        m.observe(0, (.3, -.2), 0, 1.)
        d = json.loads(m.checkpoint()[0]); d["counts"][0] += 1
        bad = mod._canonical(d)
        with self.assertRaisesRegex(ValueError, "COLD_HISTORY_INCONSISTENT"):
            mod.OnlineConsequenceMemory.restore(bad, hashlib.sha256(bad).hexdigest())

    def test_no_external_runtime_or_source_imports(self):
        source = inspect.getsource(mod)
        tree = ast.parse(source)
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.update(x.name for x in n.names)
            if isinstance(n, ast.ImportFrom):
                imports.add(n.module)
        self.assertEqual(imports, {"hashlib", "json", "math", "re"})
        self.assertFalse(any(x in source for x in
                             ("gymnasium", "subprocess", "requests", "F57_",
                              "os.system", "exec(", "eval(")))


if __name__ == "__main__":
    unittest.main()

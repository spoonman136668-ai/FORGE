"""W1L source-only structural smoke; NEVER consumes frozen 73xxx score seeds."""
import ast
import inspect
import math
import unittest

import itd02_w1l_closed_loop_dev as w


class W1LFocusedTests(unittest.TestCase):
    def test_protocol_and_frozen_controls(self):
        self.assertEqual(w.PROTOCOL_COMMIT, "7057eef8e47f984ab20bd65a01214c0b906bdd51")
        self.assertEqual(w.SEEDS, (73011, 73017, 73021, 73029))
        self.assertEqual(len(w.FAMILIES), 3)
        self.assertEqual(len(w.ARMS), 7)
        self.assertEqual(w.SCORED_STEPS, 128)
        self.assertEqual(w.FIT_STEPS, 64)
        self.assertEqual(w.CONVENTIONAL,
                         ("switch-bayes", "rolling8", "rolling16", "lagged-credit"))

    def test_action_actually_changes_numeric_source_state(self):
        x = w.NumericWorld("switch", 72001, fit=False)
        y = w.NumericWorld("switch", 72001, fit=False)
        obsx, rx, nextx, _ = x.step(0)
        obsy, ry, nexty, _ = y.step(1)
        self.assertEqual(obsx, obsy)
        self.assertNotEqual(nextx, nexty)
        self.assertGreater(rx, ry)
        self.assertNotEqual(x.public(), y.public())
        self.assertEqual(len(x.public()), 2)

    def test_unannounced_family_switches_and_lagged_effect(self):
        for name in w.FAMILIES:
            source = w.NumericWorld(name, 72003, fit=False)
            rewards = []
            for t in range(128):
                obs, reward, new, terminal = source.step(t % 2)
                self.assertEqual(len(obs), 2)
                self.assertEqual(len(new), 2)
                self.assertTrue(-2. <= reward <= 2.)
                self.assertEqual(terminal, t == 127)
                rewards.append(reward)
            self.assertEqual(source.t, 128)
            self.assertNotEqual(rewards[0], rewards[40])
            with self.assertRaises(ValueError):
                source.step(0)
        # Lagged worlds use previous actual action, not today's selected action.
        a = w.NumericWorld("lagged", 72003, fit=False)
        b = w.NumericWorld("lagged", 72003, fit=False)
        self.assertEqual(a.step(0)[1], b.step(1)[1])
        self.assertNotEqual(a.public(), b.public())

    def test_separate_familiar_fit_only_smoke_seed(self):
        rows = w.collect_fit("switch", 72001)
        self.assertEqual(len(rows), 64)
        self.assertEqual(rows, w.collect_fit("switch", 72001))
        self.assertEqual(sum(row[1] == 0 for row in rows), 32)
        self.assertTrue(rows[-1][-1])
        self.assertFalse(rows[0][-1])

    def test_all_policies_get_only_delivered_feedback(self):
        rows = w.collect_fit("third", 72001)
        states = []
        for name in w.ARMS:
            agent = w.new_policy(name, 72001)
            for obs, action, reward, _, _ in rows:
                agent.observe(obs, action, reward)
            if hasattr(agent, "episode_reset"):
                agent.episode_reset()
            state = w.NumericWorld("third", 72003, fit=False)
            for _ in range(5):
                obs = state.public()
                action = agent.choose(obs)
                self.assertIn(action, (0, 1))
                old, reward, _, _ = state.step(action)
                agent.observe(old, action, reward)
            self.assertEqual(len(agent.state()), 64)
            states.append(agent.state())
        self.assertEqual(len(states), 7)

    def test_candidate_mid_episode_cold_continuation_inert(self):
        agent = w.TwoBankPolicy()
        for t in range(20):
            agent.observe([0., 0.], t % 2, 1. if t % 2 == 0 else -1.)
        previous = agent.state()
        agent.cold()
        self.assertEqual(previous, agent.state())
        for t in range(20, 24):
            agent.observe([0., 0.], t % 2, -1. if t % 2 == 0 else 1.)
        self.assertNotEqual(previous, agent.state())
        self.assertIn(agent.choose([0., 0.]), (0, 1))

    def test_simulator_unauthorized_scope_guard(self):
        source = inspect.getsource(w)
        tree = ast.parse(source)
        banned = {"gymnasium", "requests", "subprocess", "socket", "cloudflare"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertFalse(banned & imported)
        self.assertNotIn("original_first_use_authorized = True", source)
        self.assertNotIn("scientific_accepted = True", source)
        self.assertEqual(w.SCHEMA, "forge.eureka.itd02.w1l.closed-loop-source-dev.v1")

    def test_bad_actions_and_budget_fail_closed(self):
        world = w.NumericWorld("switch", 72003, fit=True)
        for action in (False, True, -1, 2, 0.5):
            with self.assertRaises(ValueError):
                world.step(action)
        for i in range(64):
            world.step(i % 2)
        with self.assertRaises(ValueError):
            world.step(0)

    def test_unfrozen_training_fixture_is_not_score(self):
        # Deliberately NOT calling score() or rollout() on declared score seeds.
        self.assertNotIn(72001, w.SEEDS)
        self.assertNotIn(72003, w.SEEDS)
        self.assertEqual(len(set(w.SEEDS)), len(w.SEEDS))
        for kind in w.FAMILIES:
            self.assertTrue(math.isfinite(
                w.NumericWorld(kind, 72001, fit=True).public()[0]))


if __name__ == "__main__":
    unittest.main()

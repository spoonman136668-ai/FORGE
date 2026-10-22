"""R3 public DEV delayed-causality engineering controls, no protected first use."""
import hashlib
import inspect
import unittest

from public_dev import PUBLIC_FAMILIES, ContractViolation, action, canonical
from public_dev_r3 import (PublicCausalDevWorld, development_calibration,
                           fixed_public_control, public_episode_summary,
                           solve_from_public_only)


class R3CausalDEV(unittest.TestCase):
    def new(self, family=None, seed=11):
        return PublicCausalDevWorld(family or PUBLIC_FAMILIES[0],
                                    f"DEV-R3-TEST-{seed}", seed)

    def test_both_worlds_need_delayed_action_causation(self):
        for family in PUBLIC_FAMILIES:
            for seed in (11, 17, 31):
                world = self.new(family, seed)
                obs = world.reset()
                self.assertNotIn("_upstream", canonical(obs).decode())
                self.assertNotIn("_downstream", canonical(obs).decode())
                self.assertEqual(obs["interaction_budget_remaining"], 40)
                value = obs["entities"][0]["legal_values"][0]
                first = world.step(action("intervene", world._labels[world._upstream], value))
                self.assertFalse(first["observation"]["delayed_events"])
                self.assertFalse(first["done"])
                # The source event is delayed until two (A) or three (B) waits.
                lag = 2 if family == PUBLIC_FAMILIES[0] else 3
                for tick in range(1, lag + 1):
                    after = world.step(action("wait"))
                    events = after["observation"]["delayed_events"]
                    self.assertEqual(bool(events), tick == lag)
                self.assertEqual(events[0]["entity"], world._labels[world._downstream])

    def test_no_public_inspection_role_oracle(self):
        for family in PUBLIC_FAMILIES:
            world = self.new(family)
            obs = world.reset()
            for entity in obs["entities"]:
                signal = world.step(action("inspect", entity["id"]))
                self.assertEqual(signal["observation"]["observations"][0]["kind"],
                                 "public_diagnostic")
                self.assertNotIn("role", canonical(signal).decode())
                self.assertNotIn("required", canonical(signal).decode())

    def test_no_goal_by_activating_both_before_pulse(self):
        for family in PUBLIC_FAMILIES:
            world = self.new(family)
            obs = world.reset()
            yes = obs["entities"][0]["legal_values"][0]
            src, dst = world._upstream, world._downstream
            world.step(action("intervene", world._labels[src], yes))
            world.step(action("intervene", world._labels[dst], yes))
            for _ in range(4):
                world.step(action("wait"))
            self.assertEqual(world.step(action("commit"))["reward"], 0,
                             "Must perform downstream action AFTER public pulse")

    def test_no_goal_without_source_discovery(self):
        for family in PUBLIC_FAMILIES:
            for seed in (3, 4):
                world = self.new(family, seed)
                obs = world.reset()
                # Any wrong actuator can be turned on, but no causal pulse is generated.
                wrong = next(i for i in range(4) if i not in (world._upstream, world._downstream))
                world.step(action("intervene", world._labels[wrong],
                                  obs["entities"][0]["legal_values"][0]))
                for _ in range(3):
                    outcome = world.step(action("wait"))
                self.assertFalse(outcome["observation"]["delayed_events"])
                self.assertEqual(world.step(action("commit"))["reward"], 0)

    def test_public_exhaustive_explorer_solves_both(self):
        for family in PUBLIC_FAMILIES:
            wins = []
            for i in range(80):
                world = self.new(family, seed=9000 + i)
                result = solve_from_public_only(world)
                receipt = world.public_trace_receipt()
                self.assertFalse(receipt["scientific_first_use"])
                self.assertTrue(receipt["done"])
                self.assertLessEqual(receipt["steps"], 40)
                wins.append(result["reward"])
            self.assertGreaterEqual(sum(wins), 64, family)

    def test_fixed_two_action_shortcut_fails(self):
        for family in PUBLIC_FAMILIES:
            wins = []
            for seed in range(40):
                world = self.new(family, seed=5000 + seed)
                wins.append(fixed_public_control(world)["reward"])
            self.assertEqual(sum(wins), 0, "No direct fixed pair shortcut")

    def test_public_causal_oracle_does_not_introspect_private_roles(self):
        # Static source rule in addition to runtime public contract tests.
        text = inspect.getsource(solve_from_public_only)
        for private in ("._upstream", "._downstream", "._required",
                        "._states", "._pending", "._rng", "._lookup", "._family"):
            self.assertNotIn(private, text)
        self.assertIn('"delayed_events"', text)

    def test_determinism_and_public_trace_no_private_leak(self):
        for family in PUBLIC_FAMILIES:
            a = public_episode_summary(321, family, "public_oracle")
            b = public_episode_summary(321, family, "public_oracle")
            self.assertEqual(a, b)
            self.assertEqual(len(a["trace_sha256"]), 64)
            self.assertTrue(a["success"])
            self.assertLessEqual(a["steps"], 40)

    def test_calibration_is_developer_only_not_scientific(self):
        receipt = development_calibration(16, seed_start=73000)
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["source_birth_attested"])
        self.assertEqual(set(receipt["family_results"]), set(PUBLIC_FAMILIES))
        for families in receipt["family_results"].values():
            self.assertGreaterEqual(families["public_oracle"]["success_rate"], .8)
            self.assertEqual(families["fixed"]["success_rate"], 0.)

    def test_original_public_contract_invalid_actions_still_terminal(self):
        for family in PUBLIC_FAMILIES:
            world = self.new(family)
            world.reset()
            result = world.step({"schema": "itd01.act.v1", "verb": "read_hidden",
                                 "target": None, "value": None})
            self.assertTrue(result["done"])
            with self.assertRaises(ContractViolation):
                world.step(action("wait"))
            self.assertFalse(world.public_trace_receipt()["source_birth_attested"])

if __name__ == "__main__":
    unittest.main()

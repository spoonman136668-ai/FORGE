"""Adversarial qualification of the ITD-01 public-only DEV contract.

These tests do not train either cognitive architecture, calibrate accepted
held tasks or authorize any original scientific source reset.
"""
import hashlib
import unittest

from public_dev import (ACTION_SCHEMA, GENESIS, MAX_OBSERVATION,
                        OBS_SCHEMA, PUBLIC_FAMILIES, ContractViolation,
                        PublicDevWorld, action, canonical)


def public_probe_agent(world):
    """A deliberately public-only deterministic DEV heuristic, not a trained model."""
    obs = world.reset()
    votes = {}
    for entry in obs["entities"]:
        entity = entry["id"]
        votes[entity] = 0
        for _ in range(5):
            result = world.step(action("inspect", entity))
            votes[entity] += int(result["observation"]["observations"][0]["signal"]
                                 == "responsive")
    selected = sorted(votes, key=lambda entity: (-votes[entity], entity))[:2]
    value = "activate" if "activate" in obs["entities"][0]["legal_values"] else "fill"
    for entity in selected:
        world.step(action("intervene", entity, value))
    for _ in range(3):
        world.step(action("wait"))
    return world.step(action("commit"))


class PublicITD01Fixture(unittest.TestCase):
    def new(self, family=None, seed=17, episode="DEV-TEST"):
        return PublicDevWorld(family or PUBLIC_FAMILIES[0], episode, seed)

    def test_only_public_development_families_and_ids(self):
        for bad in ("H1_independent_fault_recovery",
                    "H2_independent_ecological_control", "SCIENTIFIC"):
            with self.assertRaises(ContractViolation):
                self.new(bad)
        for episode in ("HELD-1", "DEV-../evil", "DEV-", "DEV-ø"):
            with self.assertRaises(ContractViolation):
                self.new(episode=episode)
        for invalid in (-1, 2**31, True):
            with self.assertRaises(ContractViolation):
                self.new(seed=invalid)

    def test_public_observation_no_hidden_roles(self):
        for family in PUBLIC_FAMILIES:
            world = self.new(family)
            obs = world.reset()
            self.assertEqual(obs["schema"], OBS_SCHEMA)
            self.assertEqual(set(obs), {"schema", "episode_id", "turn", "entities",
                                        "observations", "delayed_events",
                                        "public_goal", "interaction_budget_remaining"})
            self.assertEqual(len(obs["entities"]), 4)
            self.assertLessEqual(len(canonical(obs)), MAX_OBSERVATION)
            for forbidden in ("_required", "_states", "hidden_state", "world_truth",
                              "answer", "source_birth_witness", "H1_", "H2_"):
                self.assertNotIn(forbidden, canonical(obs).decode())
            self.assertEqual(obs["interaction_budget_remaining"], 40)

    def test_reset_once_and_terminal_once(self):
        world = self.new()
        with self.assertRaisesRegex(ContractViolation, "RESET_REQUIRED"):
            world.step(action("wait"))
        world.reset()
        with self.assertRaisesRegex(ContractViolation, "RESET_ALREADY_USED"):
            world.reset()
        result = world.step(action("commit"))
        self.assertTrue(result["done"])
        self.assertEqual(result["reward"], 0)
        with self.assertRaisesRegex(ContractViolation, "ALREADY_TERMINAL"):
            world.step(action("commit"))
        self.assertFalse(world.public_trace_receipt()["scientific_first_use"])

    def test_invalid_action_is_terminal_without_second_attempt(self):
        bad_inputs = [
            {"schema": ACTION_SCHEMA, "verb": "shell", "target": None, "value": None},
            {"schema": ACTION_SCHEMA, "verb": "intervene", "target": "ghost", "value": "fill"},
            {"schema": ACTION_SCHEMA, "verb": "wait", "target": None, "value": None,
             "private_hint": True},
            {"schema": ACTION_SCHEMA, "verb": "commit", "target": "node0", "value": None},
            {"schema": ACTION_SCHEMA, "verb": "inspect", "target": "node0", "value": "secret"},
            {"schema": ACTION_SCHEMA, "verb": "wait", "target": None, "value": float("nan")},
            {"schema": ACTION_SCHEMA, "verb": "wait", "target": None, "value": {"untrusted": object()}},
        ]
        for family in PUBLIC_FAMILIES:
            for idx, bad in enumerate(bad_inputs):
                with self.subTest(family=family, idx=idx):
                    world = self.new(family)
                    world.reset()
                    result = world.step(bad)
                    self.assertTrue(result["done"])
                    self.assertEqual(result["reward"], 0)
                    self.assertEqual(result["observation"]["observations"][0]["kind"],
                                     "invalid_action")
                    with self.assertRaises(ContractViolation):
                        world.step(action("wait"))
                    self.assertEqual(world.public_trace_receipt()["steps"], 1)

    def test_delay_and_action_budget_never_reveals_private_state(self):
        for family in PUBLIC_FAMILIES:
            world = self.new(family)
            obs = world.reset()
            entity = obs["entities"][0]["id"]
            value = "activate" if family == PUBLIC_FAMILIES[0] else "fill"
            first = world.step(action("intervene", entity, value))
            self.assertFalse(first["observation"]["delayed_events"])
            second = world.step(action("wait"))
            self.assertFalse(second["observation"]["delayed_events"])
            third = world.step(action("wait"))
            if family == PUBLIC_FAMILIES[0]:
                self.assertTrue(third["observation"]["delayed_events"])
            else:
                self.assertFalse(third["observation"]["delayed_events"])
                fourth = world.step(action("wait"))
                self.assertTrue(fourth["observation"]["delayed_events"])
            self.assertLessEqual(world.public_trace_receipt()["steps"], 5)

    def test_strict_interaction_caps(self):
        world = self.new()
        world.reset()
        for _ in range(24):
            self.assertFalse(world.step(action("wait"))["done"])
        rejected = world.step(action("wait"))
        self.assertTrue(rejected["done"])
        self.assertEqual(rejected["reward"], 0)
        world = self.new()
        obs = world.reset()
        for _ in range(16):
            world.step(action("intervene", obs["entities"][0]["id"], "deactivate"))
        self.assertTrue(world.step(action("intervene", obs["entities"][0]["id"],
                                              "activate"))["done"])

    def test_deterministic_public_chain_and_integrity(self):
        a = self.new(PUBLIC_FAMILIES[1], episode="DEV-CHAIN")
        b = self.new(PUBLIC_FAMILIES[1], episode="DEV-CHAIN")
        self.assertEqual(a.reset(), b.reset())
        script = [action("inspect", "node0"), action("intervene", "node1", "fill"),
                  action("wait"), action("wait"), action("wait"), action("commit")]
        for planned in script:
            self.assertEqual(a.step(planned), b.step(planned))
        self.assertEqual(a.public_trace_receipt(), b.public_trace_receipt())
        head = GENESIS
        for record in a.public_trace_records():
            self.assertEqual(record["prior_sha256"], head)
            body = {key: record[key] for key in ("action", "result", "prior_sha256")}
            head = hashlib.sha256(canonical(body)).hexdigest()
            self.assertEqual(head, record["record_sha256"])
        self.assertEqual(head, a.public_trace_receipt()["trace_head_sha256"])
        self.assertFalse(a.public_trace_receipt()["source_birth_attested"])

    def test_both_dev_families_solvable_from_public_observations(self):
        # Engineering sanity, NOT a protected or statistically admitted calibration.
        for family in PUBLIC_FAMILIES:
            successful = 0
            for seed in range(40):
                result = public_probe_agent(self.new(family, seed=seed,
                                                       episode=f"DEV-CAL-{seed}"))
                successful += result["reward"]
            self.assertGreaterEqual(successful, 32, family)

    def test_no_live_authority_entrypoint(self):
        import public_dev as module
        for attr in ("run_original", "issue_reset", "dispatch", "resume_controller",
                     "read_held", "activate_science", "write_first_use"):
            self.assertFalse(hasattr(module, attr))


if __name__ == "__main__":
    unittest.main()

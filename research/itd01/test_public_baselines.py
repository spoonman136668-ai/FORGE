"""R2 baseline training is public-feedback-only and neither held nor privileged."""
import unittest

from public_dev import PUBLIC_FAMILIES, PublicDevWorld
from public_baselines import (ExplicitEpisodicAgent, PredictiveWorldModelAgent,
                              RecurrentRewardAgent, obtain_public_probes,
                              execute_public_candidate, model_identity,
                              model_state_bytes)
from run_public_baselines import gather, run, evaluate


class TrainedPublicControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training, cls.chain = gather(17, 18)

    def test_train_data_is_public_reward_only(self):
        self.assertEqual(len(self.training), 36)
        self.assertEqual(len(self.chain), 64)
        self.assertTrue(any(e["reward"] == 1 for e in self.training))
        self.assertTrue(any(e["reward"] == 0 for e in self.training))
        for ep in self.training:
            self.assertEqual(set(ep), {"probes", "pair", "reward"})
            self.assertEqual(len(ep["probes"]), 16)
            self.assertTrue(all(0 <= idx < 4 and val in (0.0, 1.0)
                                for idx, val in ep["probes"]))
            self.assertIn(ep["reward"], (0, 1))

    def test_seeds_reproduce_public_only_training_chain(self):
        episodes, chain = gather(17, 18)
        self.assertEqual(self.chain, chain)
        self.assertEqual(self.training, episodes)

    def test_recurrent_backprop_updates_are_real(self):
        model = RecurrentRewardAgent(17)
        old = model_identity(model)
        model.train(self.training)
        self.assertEqual(model.updates, len(self.training) * 3)
        self.assertNotEqual(old, model_identity(model))
        self.assertEqual(len(model.predict_all(self.training[0]["probes"])), 6)
        self.assertGreater(model_state_bytes(model), 200)
        self.assertLess(model_state_bytes(model), 65536)

    def test_world_model_trains_on_future_public_diagnostics(self):
        model = PredictiveWorldModelAgent()
        old = model_identity(model)
        model.train(self.training)
        self.assertGreater(model.updates, 0)
        self.assertNotEqual(old, model_identity(model))
        self.assertEqual(len(model.predict_all(self.training[0]["probes"])), 6)

    def test_memory_training_serializes_public_feedback_only(self):
        model = ExplicitEpisodicAgent(max_cases=25)
        model.train(self.training)
        self.assertEqual(model.updates, 36)
        self.assertEqual(len(model.cases), 25)
        self.assertTrue(all(set(x) == {"features", "pair", "reward"} for x in model.cases))
        self.assertEqual(len(model.predict_all(self.training[0]["probes"])), 6)

    def test_all_agents_execute_public_task_with_legal_verbs(self):
        for constructor in (lambda: RecurrentRewardAgent(17),
                            PredictiveWorldModelAgent, ExplicitEpisodicAgent):
            model = constructor()
            model.train(self.training)
            old = model_identity(model)
            result = evaluate(model, 3)
            self.assertEqual(set(result), set(PUBLIC_FAMILIES))
            for family in PUBLIC_FAMILIES:
                self.assertEqual(result[family]["tasks"], 3)
                self.assertTrue(0.0 <= result[family]["success_rate"] <= 1.0)
            self.assertEqual(model_identity(model), old)

    def test_no_evaluator_object_is_passed_into_agent(self):
        for family in PUBLIC_FAMILIES:
            world = PublicDevWorld(family, "DEV-R2-ISOLATION", 19)
            reset = world.reset()
            events, names = obtain_public_probes(reset, world.step)
            self.assertEqual(len(events), 16)
            self.assertTrue(all(type(x) is tuple for x in events))
            self.assertIn(execute_public_candidate(reset, world.step, names, 0), (0, 1))
            self.assertTrue(world.public_trace_receipt()["done"])
            self.assertFalse(world.public_trace_receipt()["source_birth_attested"])

    def test_bounded_smoke_receipt_keeps_science_blocked(self):
        receipt = run(8, 2, 17)
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["source_birth_attested"])
        self.assertFalse(receipt["original_held_families_used"])
        self.assertEqual(receipt["authority"], "NONE_DEV_ONLY")
        self.assertEqual(len(receipt["trained_agent_classes"]), 3)
        self.assertGreater(receipt["shared_process_total_cpu_seconds"], 0)
        for model in receipt["trained_agent_classes"]:
            self.assertGreater(model["training_updates"], 0)
            self.assertGreater(model["trained_serialized_bytes"], 0)


if __name__ == "__main__":
    unittest.main()

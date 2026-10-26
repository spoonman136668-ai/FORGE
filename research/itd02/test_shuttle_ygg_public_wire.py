"""Cross-repo original-source PUBLIC WIRE contract, no original episodes.

This is an authored wire-shape fixture, NOT Shuttle state dynamics or a
scientific observation. Both learners are the genuine pinned Yggdrasil source.
"""
import unittest

from shuttle_source_contract import PublicEventGuard
from yggdrasil.itd02_native_task_bridge_dev import NativeTaskRingBridgeDev


class ShuttleYggdrasilPublicSeamTests(unittest.TestCase):
    def test_selected_public_action_updates_both_original_native_models(self):
        owner = PublicEventGuard()
        learner = NativeTaskRingBridgeDev()
        original = learner.model_identities()
        owner.begin("LRV")
        learner.start_observation("LRV")
        chosen = "Backup"  # Explicit legal exploration selection, not an oracle.
        # Source-free public fixture only. Not an original Shuttle step.
        event = owner.accept(action=chosen, next_observation="MRV",
                             reward=10, terminal=True)
        self.assertEqual(set(event), {
            "observation", "action", "next_observation", "reward", "terminal"})
        learner.accept_public_transition(
            event["action"], event["next_observation"], event["reward"],
            terminal=event["terminal"])
        self.assertEqual(owner.transitions, 1)
        self.assertEqual(learner.transitions, 1)
        self.assertEqual(learner.native.core.events, 1)
        self.assertEqual(learner.memory.updates, 1)
        self.assertNotEqual(original["native"], learner.model_identities()["native"])
        self.assertNotEqual(original["memory"], learner.model_identities()["memory"])

    def test_invalid_hidden_payload_never_mutates_native_learners(self):
        owner = PublicEventGuard()
        learner = NativeTaskRingBridgeDev()
        owner.begin("MRV")
        learner.start_observation("MRV")
        before = learner.checkpoint()
        with self.assertRaises(TypeError):
            owner.accept(action="Backup", next_observation="Nothing",
                         reward=0, terminal=False, private_state=2)
        self.assertEqual(learner.checkpoint(), before)
        self.assertEqual(owner.transitions, 0)
        self.assertTrue(owner.pending)


if __name__ == "__main__":
    unittest.main()

"""R6: shared neutral public-only exploratory script, NOT native cognition."""
import inspect
import unittest
from public_dev import PUBLIC_FAMILIES
from public_dev_r3 import PublicCausalDevWorld
from r5_causal_dev import R5CausalWorld
from run_r6_neutral_qualification import (neutral_scripted_public_policy,
                                          run_one,evaluate)


class SharedNeutralPublicDEV(unittest.TestCase):
    def test_one_unmodified_public_policy_solves_four_world_combinations(self):
        for name,world in (("R3",PublicCausalDevWorld),
                           ("R5",R5CausalWorld)):
            for family in PUBLIC_FAMILIES:
                for seed in range(24):
                    result=run_one(world,family,710000+seed,
                                   f"DEV-R6-SOLV-{name}-{seed}")
                    self.assertEqual(result["reward"],1,(name,family,seed,result))
                    self.assertLessEqual(result["steps"],41)
                    self.assertGreater(result["neutral_events_count"]["observed-effect"],0)
                    self.assertGreater(result["neutral_events_count"]["observed-confirmation"],0)

    def test_generic_policy_never_uses_original_event_name_or_world_identity(self):
        src=inspect.getsource(neutral_scripted_public_policy)
        for banned in ("relay_pulse","feed_pulse","inflow_arrived",
                       "dependence_pulse","reservoir_balanced","goal_confirmed",
                       "PublicCausalDevWorld","R5CausalWorld","._source","._relay",
                       "._sink","_required","_family","source_birth"):
            self.assertNotIn(banned,src)

    def test_deterministic_neutral_trace_and_no_original_science(self):
        for world in (PublicCausalDevWorld,R5CausalWorld):
            for family in PUBLIC_FAMILIES:
                first=run_one(world,family,711983,"DEV-R6-REPLAY")
                second=run_one(world,family,711983,"DEV-R6-REPLAY")
                self.assertEqual(first,second)
                self.assertEqual(len(first["public_normalized_trace_sha256"]),64)
                self.assertNotEqual(first["public_normalized_trace_sha256"],
                                    first["public_original_trace_sha256"])

    def test_preheld_development_only_aggregate(self):
        groups=evaluate(3)
        self.assertEqual(len(groups),2)
        for group in groups.values():
            self.assertEqual(len(group),2)
            for fam in group.values():
                self.assertEqual(fam["tasks"],3)
                self.assertGreaterEqual(fam["goal_success"],.8)
                self.assertLessEqual(fam["max_actions"],41)


if __name__=="__main__":
    unittest.main()

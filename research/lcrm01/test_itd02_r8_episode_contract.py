"""Source-only validation of frozen R8 heldout episode requests."""
import unittest
from itd02_r8_episode_contract import validate_episode_request

class EpisodeContractTest(unittest.TestCase):
    def test_registered_check_and_dev(self):
        for seed in (82400,82407,83400,83407):
            for family in ("empty","fourrooms"):
                for method in ("wingless_r8_online_beliefs","wingless_r5_cost_frontier"):
                    row=validate_episode_request(family,seed,method)
                    self.assertEqual(row["seed"],seed)
                    self.assertEqual(row["method"],method)
    def test_reject_fit_and_historical(self):
        for seed in (81400,71400,72400,73400,82399,82408,83399,83408):
            with self.assertRaises(ValueError):
                validate_episode_request("empty",seed,"wingless_r8_online_beliefs")
    def test_reject_invalid_method_family_type(self):
        for family,seed,method in (
            ("unknown",82400,"wingless_r8_online_beliefs"),
            ("empty",82400,"unregistered"),
            ("empty",True,"wingless_r8_online_beliefs"),
        ):
            with self.assertRaises(ValueError):
                validate_episode_request(family,seed,method)

if __name__=="__main__":
    unittest.main()

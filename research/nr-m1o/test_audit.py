import unittest
from audit import key, native_choice

class NRNativeChangeSupportTests(unittest.TestCase):
    def test_original_nonreward_public_change_can_support_override(self):
        stats=[[0,0] for _ in range(7)]
        stats[0]=[3,0]
        stats[2]=[3,3]
        self.assertEqual(native_choice(stats,0),2)
        self.assertIsNone(native_choice(stats,2))

    def test_requires_at_least_three_real_source_events(self):
        stats=[[0,0] for _ in range(7)]
        stats[0]=[3,0]
        stats[2]=[2,2]
        self.assertIsNone(native_choice(stats,0))

    def test_early_turn_bias_is_not_goal_evidence(self):
        stats=[[0,0] for _ in range(7)]
        stats[0]=[3,3]
        self.assertEqual(native_choice(stats,2),0)

    def test_no_override_for_equal_observation_change_rates(self):
        stats=[[0,0] for _ in range(7)]
        stats[0]=[3,3]
        stats[1]=[3,3]
        self.assertIsNone(native_choice(stats,0))

    def test_only_original_public_mission_direction_front(self):
        p={"mission":"pick up the blue ball","direction":3,
           "image":[[[0,0,0] for _ in range(7)] for _ in range(7)]}
        p["image"][3][5]=[6,2,0]
        self.assertEqual(key(p),("pick up the blue ball",3,6,2,0))
        p["direction"]=4
        with self.assertRaises(ValueError):
            key(p)

if __name__=="__main__":
    unittest.main()

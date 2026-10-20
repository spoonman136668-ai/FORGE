"""Source-free K4D comparison and intervention target tests. No PyBullet import."""
import unittest
import numpy as np
from k4d_cross_intervention import PairFailure, compare_records, intervention_target


class TestK4DSourceFree(unittest.TestCase):
    def test_exact_equal(self):
        self.assertTrue(compare_records([{"a":1, "b":2}],[{"a":1,"b":2}],"control"))

    def test_detect_first_changed_step_and_field(self):
        with self.assertRaises(PairFailure) as caught:
            compare_records([{"r":1},{"r":2, "t":1}],
                            [{"r":1},{"r":3, "t":1}], "treated")
        self.assertEqual((caught.exception.phase,caught.exception.step,caught.exception.fields),
                         ("treated",1,["r"]))

    def test_lengths_fail_closed(self):
        with self.assertRaises(PairFailure):
            compare_records([{"a":1}],[],"missing")

    def test_exact_joint_assignment_within_limits(self):
        joints = np.zeros(9)
        low = np.full(9,-1.0)
        high = np.full(9,1.0)
        target=intervention_target(np,joints,np.stack([low,high]),.04)
        self.assertEqual(target[0],.04)
        self.assertTrue(np.array_equal(target[1:], joints[1:]))

    def test_distinct_velocity_intervention_target(self):
        joints = np.zeros(9)
        bounds = np.stack([np.full(9,-2.0),np.full(9,2.0)])
        target = intervention_target(np,joints,bounds,.1)
        self.assertEqual(float(target[0]),.1)
        self.assertTrue(np.array_equal(target[1:],joints[1:]))

    def test_clamped_at_joint_upper_limit(self):
        joints = np.zeros(9)
        joints[0] = .99
        bounds = np.stack([np.full(9,-1.0),np.full(9,1.0)])
        with self.assertRaises(PairFailure):
            intervention_target(np,joints,bounds,.04)


if __name__=="__main__":
    unittest.main()

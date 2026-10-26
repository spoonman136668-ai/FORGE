"""Fixture-only six-field adapter regression; no original MiniGrid reset."""
import unittest
from unittest.mock import patch
import itd02_r8_sixfield_adapter as subject
import k4t_f4_original_r5_cost as original

class SixfieldAdapterTest(unittest.TestCase):
    def test_heldout_delegation(self):
        expected={"method":"sixfield_fit_model_route","success":True}
        with patch.object(original,"sixfield_episode",return_value=expected) as call:
            row=subject.run_sixfield("fourrooms",83400,{"fitted":"fixture"})
        call.assert_called_once_with("fourrooms",83400,{"fitted":"fixture"})
        self.assertEqual(row["fit_provenance"],"original_F4_sixfield_policy_fresh_R8_FIT_required")
        self.assertFalse(row["scientific_accepted"])
    def test_fit_seed_rejected_before_episode(self):
        with patch.object(original,"sixfield_episode") as call:
            with self.assertRaises(ValueError):
                subject.run_sixfield("empty",81400,{"fitted":"fixture"})
            call.assert_not_called()
    def test_missing_fit_rejected(self):
        with self.assertRaises(ValueError):
            subject.run_sixfield("empty",83400,None)
    def test_method_drift_rejected(self):
        with patch.object(original,"sixfield_episode",return_value={"method":"other"}):
            with self.assertRaises(ValueError):
                subject.run_sixfield("empty",83400,{"fitted":"fixture"})

if __name__=="__main__":unittest.main()

"""Fixture tests for independently labeled conventional control execution."""
import unittest
from unittest.mock import patch
import itd02_r8_independent_control as subject

class IndependentControlTest(unittest.TestCase):
    def test_provenance_for_both_controls(self):
        for method in subject.MODELS:
            with self.subTest(method=method),patch.object(subject,"run_statistical_episode",return_value={"method":method,"scientific_accepted":True}) as run:
                result=subject.run_independent_control("empty",83400,method,lambda state:2)
                self.assertEqual(result["fallback_provenance"],"independent_conventional_not_native_r5")
                self.assertFalse(result["native_r5_matched"])
                self.assertFalse(result["scientific_accepted"])
                self.assertEqual(run.call_args.args[0:2],("empty",83400))
    def test_invalid_method_and_missing_base_fail_closed(self):
        with patch.object(subject,"run_statistical_episode") as run:
            with self.assertRaises(ValueError):
                subject.run_independent_control("empty",83400,"unknown",lambda state:2)
            with self.assertRaises(ValueError):
                subject.run_independent_control("empty",83400,"independent_conditional_beta",None)
            run.assert_not_called()

if __name__=="__main__":unittest.main()

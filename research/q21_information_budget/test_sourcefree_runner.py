"""Q21 full-pipeline entrypoint guards: all experiments remain unexecuted."""
import copy
import unittest
from unittest import mock
import sourcefree as src
import sourcefree_runner as run

class Q21RunnerSourceOnly(unittest.TestCase):
    def test_preflight_never_draws_development_episodes(self):
        with mock.patch.object(src,"generate",side_effect=AssertionError("EARLY_SOURCE")):
            result=run.preflight()
        self.assertEqual(result["development_generation"],"NOT_PERFORMED")
        self.assertEqual(result["fit_validation_dev"],"NOT_PERFORMED")

    def test_protocol_drift_blocks_before_experience(self):
        p=copy.deepcopy(src.protocol())
        p["intent"]="mutated scientific protocol"
        with mock.patch.object(src,"generate",side_effect=AssertionError("EARLY_SOURCE")):
            with self.assertRaisesRegex(ValueError,"FROZEN_PROTOCOL_DRIFT"):
                run.acquire_public_roles(src.FAMILIES[0],p)

    def test_protected_source_family_is_not_authorized(self):
        with mock.patch.object(src,"generate",side_effect=AssertionError("EARLY_SOURCE")):
            with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_FAMILY"):
                run.acquire_public_roles("HELD_NEW_SENSOR_FAMILY",src.protocol())

    def test_only_public_rows_exposed_and_generation_metered(self):
        def fake(role,family,index,doc):
            data=src.public_episode(family,[(index%2,0),(0,1),(1,1)],[1,0])
            return data,{"secret_sensor_slot":index%2}
        # Preserve frozen episode counts: patching ROLE_COUNTS itself would
        # correctly trip the protocol identity guard.
        with mock.patch.object(src,"generate",side_effect=fake) as invoked:
            result,receipt=run.acquire_public_roles(src.FAMILIES[0],src.protocol())
        self.assertEqual(invoked.call_count,sum(src.ROLE_COUNTS.values()))
        self.assertTrue(all(len(row)==3 for seq in result.values() for row in seq))
        self.assertGreater(receipt["payload"]["serialized_bytes"],0)
        self.assertGreater(receipt["process_peak_rss_bytes"],0)
        self.assertEqual(receipt["communication"]["wire_bytes"],0)

    def test_full_pipeline_drift_rejection_precedes_all_activity(self):
        p=copy.deepcopy(src.protocol())
        p["source_parent"]="forged"
        with mock.patch.object(src,"generate",side_effect=AssertionError("EARLY_SOURCE")):
            with self.assertRaisesRegex(ValueError,"FROZEN_PROTOCOL_DRIFT"):
                run.execute_development(p)

    def test_accounting_wraps_real_native_counter_operation(self):
        data,receipt=run.measured("fixture",lambda:{"observed":"handcrafted"})
        self.assertEqual(data["observed"],"handcrafted")
        self.assertGreaterEqual(receipt["process_cpu_seconds"],0)
        self.assertFalse("per_model" not in receipt["rss_scope"].lower())
        self.assertEqual(receipt["communication"]["adapter_bytes"],0)

    def test_no_development_cli(self):
        from pathlib import Path
        text=Path(run.__file__).read_text(encoding="utf-8")
        self.assertIn('choices=("preflight",)',text)
        self.assertNotIn('choices=("train-dev",)',text)

if __name__=="__main__":
    unittest.main()

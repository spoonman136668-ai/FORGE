"""Exact V17 owner result visibility regression; no work admission or model call."""
from __future__ import annotations

import inspect
import unittest

from f139.local_controller import (
    F139Error, preserve_verified_steering, run_once,
)


class VerifiedSteeringTerminalWitnessTests(unittest.TestCase):
    def test_no_feed_witness_remains_absent_without_mutating_report(self):
        report = {
            "disposition": "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY",
            "worker_dispatched": False,
            "scientific_first_use": False,
            "paid_model_calls": 0,
        }
        self.assertIs(preserve_verified_steering(report, None), report)
        self.assertNotIn("steering_selection", report)

    def test_spent_reasoner_preserves_real_authenticated_intake_selection(self):
        witness = {
            "status": "VERIFIED_ADVISORY_ONLY",
            "schema": "forge.f139.itd02-steering-consumption.v1",
            "selection_witness": {
                "schema": "forge.f139.itd02-selection-witness.v1",
                "eligible_authenticated_count": 0,
                "selected_authenticated_count": 0,
                "scientific_first_use": False,
                "dispatch_authorized": False,
            },
        }
        original = {
            "disposition": "FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY",
            "scientific_first_use": False,
            "worker_dispatched": False,
            "paid_model_calls": 0,
        }
        new = preserve_verified_steering(original, witness)
        self.assertEqual(new["steering_selection"], witness)
        self.assertEqual(
            {key: value for key, value in new.items()
             if key != "steering_selection"},
            original,
        )
        self.assertNotIn("steering_selection", original)
        self.assertEqual(new["disposition"], original["disposition"])
        self.assertFalse(new["scientific_first_use"])
        self.assertFalse(new["worker_dispatched"])
        self.assertEqual(new["paid_model_calls"], 0)
        self.assertIsNot(new, original)

    def test_bad_witness_or_report_fails_closed(self):
        with self.assertRaisesRegex(F139Error, "STEERING_WITNESS_INVALID"):
            preserve_verified_steering({"disposition": "read-only"}, "fabricated")
        with self.assertRaisesRegex(F139Error, "STEERING_REPORT_INVALID"):
            preserve_verified_steering("not a controller report", None)

    def test_real_owner_reasoner_return_preserves_selection_after_custody(self):
        source = inspect.getsource(run_once)
        self.assertIn("reasoner_report = run_original_free_reasoner_once(", source)
        self.assertIn(
            "return preserve_verified_steering(\n"
            "                    reasoner_report, steering_selection)", source)
        self.assertLess(source.index("eligible = api.native_eligible_issues("),
                        source.index("reasoner_report = run_original_free_reasoner_once("))
        self.assertLess(source.index("feed = feeder("),
                        source.index("return preserve_verified_steering("))
        self.assertIn("FREE_REASONER_GUARD_BLOCKED_FAIL_CLOSED", source)
        self.assertNotIn("scientific_first_use=True", source)


if __name__ == "__main__":
    unittest.main()

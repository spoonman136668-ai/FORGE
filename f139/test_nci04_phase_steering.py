"""Source-only negative and decision tests: never reads or mutates owner state."""
from __future__ import annotations

import unittest

from f139.nci04_phase_steering import PhaseSteeringDenied, preview


class PhaseSteeringPreviewTests(unittest.TestCase):
    def select(self, mode="AUTO", lane=None, research=(), training=(),
               admissions=(), outcomes=(), self_ready=False, phase_history=()):
        return preview(mode=mode, lane=lane, research_ready=research,
                       training_ready=training, admitted_lanes=admissions,
                       recent_training_outcomes=outcomes,
                       self_improvement_ready=self_ready,
                       admitted_phases=phase_history)

    def test_auto_prefers_ready_training(self):
        actual = self.select(research=("Yggdrasil",), training=("Yggdrasil",))
        self.assertEqual((actual["phase"], actual["selected_lane"]),
                         ("TRAIN", "Yggdrasil"))
        self.assertFalse(actual["dispatch_authorized"])
        self.assertFalse(actual["scientific_first_use"])

    def test_auto_no_training_readiness_falls_to_research(self):
        self.assertEqual(self.select(research=("Wingless",))["phase"], "RESEARCH")

    def test_auto_two_negative_training_results_route_to_research(self):
        outcome = (("Yggdrasil", "NO_GAIN"), ("Yggdrasil", "REGRESSED"))
        actual = self.select(research=("Yggdrasil",), training=("Yggdrasil",),
                             outcomes=outcome)
        self.assertEqual(actual["status"], "AUTO_TRAINING_STALLED_RESEARCH_FIRST")
        self.assertEqual(actual["phase"], "RESEARCH")

    def test_auto_one_negative_does_not_force_research(self):
        actual = self.select(research=("Yggdrasil",), training=("Yggdrasil",),
                             outcomes=(("Yggdrasil", "NO_GAIN"),))
        self.assertEqual(actual["phase"], "TRAIN")

    def test_auto_stalled_only_training_fails_closed(self):
        actual = self.select(training=("Wingless",),
                             outcomes=(("Wingless", "REGRESSED"),
                                       ("Wingless", "NO_GAIN")))
        self.assertEqual(actual["status"], "AUTO_TRAINING_STALLED_NO_RESEARCH")
        self.assertIsNone(actual["phase"])

    def test_manual_training_cannot_infer_readiness(self):
        actual = self.select(mode="TRAIN", research=("Wingless",))
        self.assertEqual(actual["status"], "MANUAL_NO_ELIGIBLE_TRAIN")
        self.assertIsNone(actual["selected_lane"])

    def test_manual_research_honors_explicit_lane(self):
        actual = self.select(mode="RESEARCH", lane="TTT-Hybrid",
                             research=("Wingless", "TTT-Hybrid"))
        self.assertEqual(actual["selected_lane"], "TTT-Hybrid")

    def test_explicit_lane_not_silently_switched(self):
        actual = self.select(mode="AUTO", lane="TTT-Hybrid",
                             research=("Wingless",), training=("Yggdrasil",))
        self.assertEqual(actual["status"], "AUTO_NO_ELIGIBLE_WORK")

    def test_fairness_from_verified_admissions(self):
        actual = self.select(research=("Wingless", "Yggdrasil"),
                             admissions=("Wingless",))
        self.assertEqual(actual["selected_lane"], "Yggdrasil")

    def test_hold_only_stops_future_admissions(self):
        actual = self.select(mode="HOLD", training=("Yggdrasil",))
        self.assertEqual(actual["status"], "HOLD_NEW_ADMISSIONS_ONLY")
        self.assertIsNone(actual["phase"])
        self.assertFalse(actual["dispatch_authorized"])

    def test_outcome_not_an_authority(self):
        actual = self.select(mode="TRAIN", training=("Yggdrasil",),
                             outcomes=(("Yggdrasil", "IMPROVED"),))
        for field in ("dispatch_authorized", "scientific_first_use",
                      "checkpoint_mutation", "accepted_ref_mutation", "new_controller"):
            self.assertIs(actual[field], False)

    def test_manual_forge_self_improvement_ready(self):
        actual = self.select(mode="SELF_IMPROVE", self_ready=True)
        self.assertEqual(actual["phase"], "SELF_IMPROVE")
        self.assertEqual(actual["selected_lane"], "FORGE-self")
        self.assertFalse(actual["self_source_mutation"])
        self.assertFalse(actual["rsi_proven"])
        self.assertFalse(actual["deployment_authorized"])

    def test_self_improvement_requires_existing_source_readiness(self):
        actual = self.select(mode="SELF_IMPROVE")
        self.assertIsNone(actual["phase"])
        self.assertEqual(actual["status"], "MANUAL_NO_ELIGIBLE_SELF_IMPROVE")

    def test_self_improvement_rejects_independent_lane_takeover(self):
        with self.assertRaises(PhaseSteeringDenied):
            self.select(mode="SELF_IMPROVE", lane="Wingless", self_ready=True)

    def test_auto_still_defaults_to_model_training(self):
        actual = self.select(research=("Yggdrasil",), training=("Yggdrasil",),
                             self_ready=True)
        self.assertEqual(actual["phase"], "TRAIN")

    def test_auto_rotates_to_self_improvement_after_other_phases(self):
        actual = self.select(research=("Wingless",), training=("Yggdrasil",),
                             self_ready=True,
                             phase_history=("TRAIN", "RESEARCH"))
        self.assertEqual(actual["phase"], "SELF_IMPROVE")
        self.assertEqual(actual["selected_lane"], "FORGE-self")

    def test_auto_rotates_back_to_native_research_after_self_improvement(self):
        actual = self.select(research=("Wingless",), training=("Yggdrasil",),
                             self_ready=True,
                             phase_history=("SELF_IMPROVE", "TRAIN"))
        self.assertEqual(actual["phase"], "RESEARCH")
        self.assertEqual(actual["selected_lane"], "Wingless")

    def test_lane_pinned_auto_does_not_take_forge_self_work(self):
        actual = self.select(lane="Wingless", self_ready=True)
        self.assertEqual(actual["status"], "AUTO_NO_ELIGIBLE_WORK")
        self.assertIsNone(actual["phase"])

    def test_self_improvement_alternative_to_stalled_training(self):
        actual = self.select(training=("Yggdrasil",), self_ready=True,
                             outcomes=(("Yggdrasil", "NO_GAIN"),
                                       ("Yggdrasil", "REGRESSED")))
        self.assertEqual(actual["phase"], "SELF_IMPROVE")

    def test_self_improvement_source_mutation_never_authorized_by_preview(self):
        actual = self.select(mode="SELF_IMPROVE", self_ready=True)
        for key in ("dispatch_authorized", "scientific_first_use",
                    "self_source_mutation", "checkpoint_mutation",
                    "rsi_proven", "deployment_authorized",
                    "accepted_ref_mutation", "new_controller"):
            self.assertIs(actual[key], False)

    def test_untrusted_data_rejected(self):
        cases = (
            dict(mode="train"), dict(mode="SCIENCE"), dict(lane="FORGE"),
            dict(research_ready=["Wingless"]),
            dict(research_ready=("Wingless", "Wingless")),
            dict(training_ready=("BadLane",)),
            dict(recent_training_outcomes=(("Yggdrasil", "PASS"),)),
            dict(recent_training_outcomes=(("Yggdrasil", "NO_GAIN", "X"),)),
            dict(admitted_lanes=("forged",)),
            dict(self_improvement_ready="yes"),
            dict(admitted_phases=("TRAIN", "FORGE-self")),
            dict(admitted_phases=["TRAIN"]),
        )
        defaults = {"mode": "AUTO", "lane": None,
                    "research_ready": (), "training_ready": ()}
        for patch in cases:
            with self.subTest(patch=patch):
                with self.assertRaises(PhaseSteeringDenied):
                    preview(**{**defaults, **patch})


if __name__ == "__main__":
    unittest.main()

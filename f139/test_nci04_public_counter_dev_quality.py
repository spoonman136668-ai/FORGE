"""Exact bounded synthetic quality and negative controls; no live FORGE owner."""
import unittest

from f139.nci04_public_counter_dev_quality import assess
from f139.nci04_prompt_program import public_success_count_order

# Original Yggdrasil source programs, Git blobs:
# #838 1c23c0712774a8225b595a0ae8ecac13fa1c8088
# #846 36255a29dfb01d533c8bc793c73a781040e98fa9
# #847 4a7ad54faee2393079c288c93b59ccd7548c823a
PROGRAMS = {
    "pr838": "rate mul add success success mul success total add add total zero add zero zero",
    "pr846": "rate add add failure success mul success total add add total zero add zero zero",
    "pr847": "rate mul add failure success mul success total add add total zero add zero zero",
}


class DevelopmentQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = assess(PROGRAMS)

    def test_real_candidates_falsify_improvement_against_competent_control(self):
        r = self.result
        self.assertEqual(r["fixed_scenarios"], 54)
        self.assertEqual(r["grid_decision_cases"], 4225)
        self.assertEqual(r["strongest_control"], "laplace")
        self.assertEqual(r["controls"]["laplace"]["decimal"], "0.050400401845")
        self.assertEqual(r["controls"]["empirical"]["decimal"], "0.053670957271")
        self.assertEqual(r["programs"]["pr846"]["mean_regret"]["decimal"], "0.079289483941")
        self.assertEqual(r["programs"]["pr847"]["mean_regret"]["decimal"], "0.104965204580")
        self.assertFalse(r["programs"]["pr847"]["beats_strongest_control_on_this_synthetic_dev_grid"])
        self.assertFalse(r["programs"]["pr846"]["beats_strongest_control_on_this_synthetic_dev_grid"])

    def test_existing_symbolic_duplicate_guard_reused(self):
        self.assertTrue(public_success_count_order(PROGRAMS["pr838"]))
        self.assertTrue(public_success_count_order(PROGRAMS["pr846"]))
        self.assertFalse(public_success_count_order(PROGRAMS["pr847"]))
        r = self.result["programs"]
        self.assertEqual(r["pr838"]["finite_public_grid_signature_sha256"],
                         r["pr846"]["finite_public_grid_signature_sha256"])
        self.assertNotEqual(r["pr847"]["finite_public_grid_signature_sha256"],
                            r["pr846"]["finite_public_grid_signature_sha256"])

    def test_no_authority_granted_by_valid_development_diagnostics(self):
        r = self.result
        for name in ("finite_grid_equality_is_global_equivalence_proof",
                     "independent_source_custody_proven", "scientific_first_use",
                     "scientific_accepted", "optimizer_training_authorized",
                     "dispatch_authorized", "owner_policy_modified"):
            self.assertIs(r[name], False, name)
        self.assertEqual(r["mode"], "SYNTHETIC_DEVELOPMENT_DIAGNOSTIC_ONLY")

    def test_exact_decision_cache_avoids_duplicate_regret_without_merging_sources(self):
        from f139 import nci04_public_counter_dev_quality as quality
        from unittest.mock import patch
        with patch.object(quality, "_loss", wraps=quality._loss) as run:
            result = quality.assess(PROGRAMS)
        # Two competent controls, two distinct candidate behaviors; not three
        # candidate evaluations. The two original different Git source hashes
        # and both diagnostic records stay separately visible.
        self.assertEqual(run.call_count, 4)
        self.assertEqual(result["distinct_fixed_dev_decision_behaviors"], 2)
        self.assertEqual(result["redundant_regret_evaluations_avoided"], 1)
        self.assertTrue(result["candidate_source_bytes_and_negative_results_preserved"])
        self.assertNotEqual(result["programs"]["pr838"]["program_sha256"],
                            result["programs"]["pr846"]["program_sha256"])
        self.assertEqual(result["programs"]["pr838"]["mean_regret"],
                         result["programs"]["pr846"]["mean_regret"])
        self.assertNotEqual(result["programs"]["pr847"]["mean_regret"],
                            result["programs"]["pr846"]["mean_regret"])

    def test_complete_fixed_dev_support_required_for_exact_caching(self):
        from f139 import nci04_public_counter_dev_quality as quality
        from unittest.mock import patch
        with patch.object(quality, "TRIAL_COUNTS", (12,)):
            with self.assertRaisesRegex(ValueError, "SIGNATURE_DOMAIN_TOO_SMALL"):
                quality.assess(PROGRAMS)

    def test_invalid_program_or_input_rejected(self):
        for bad in ({}, {"bad": 3}, {" ": PROGRAMS["pr847"]},
                    {"pr847": "rate wrong"}, {"pr847": ""},
                    {"pr847": PROGRAMS["pr847"], "pr846": None}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                assess(bad)

    def test_reproducible_without_outcome_or_clock_inputs(self):
        self.assertEqual(assess(dict(reversed(list(PROGRAMS.items()))))["programs"],
                         self.result["programs"])


class AdvisoryScreenTests(unittest.TestCase):
    def test_real_originals_rejected_without_treating_ci_as_reward(self):
        from f139.nci04_public_counter_dev_quality import screen_development_candidates
        result = screen_development_candidates(PROGRAMS)
        self.assertEqual(result["mode"], "NON_AUTHORIZING_SYNTHETIC_DEV_SELECTION")
        self.assertEqual(result["disposition"], "DEV_NO_GO")
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["best_observed_candidate_for_diagnostics"], "pr838")
        self.assertEqual(result["strongest_control"], "laplace")
        from fractions import Fraction
        self.assertLess(Fraction(result["absolute_regret_gain_exact"]), 0)
        self.assertEqual(Fraction(result["predeclared_absolute_regret_gain_floor_exact"]),
                         Fraction(1, 100))
        self.assertFalse(result["equal_evidence_and_complete_cost_independently_proven"])
        for key in ("scientific_first_use", "scientific_accepted",
                    "optimizer_training_authorized", "dispatch_authorized",
                    "accepted_ref_mutation_authorized"):
            self.assertIs(result[key], False)

    def test_dictionary_order_and_duplicate_names_do_not_change_no_go(self):
        from f139.nci04_public_counter_dev_quality import screen_development_candidates
        from fractions import Fraction
        report = screen_development_candidates(dict(reversed(list(PROGRAMS.items()))))
        self.assertEqual(report["disposition"], "DEV_NO_GO")
        self.assertIsNone(report["candidate"])
        self.assertEqual(report["best_observed_candidate_for_diagnostics"], "pr838")
        self.assertEqual(report["owner_selection_unchanged"], True)
        self.assertIs(type(Fraction(report["absolute_regret_gain_exact"])), Fraction)

    def test_promising_mock_is_only_advisory_not_permission(self):
        from f139 import nci04_public_counter_dev_quality as quality
        from unittest.mock import patch
        fake = {
            "strongest_control": "laplace",
            "controls": {"laplace": {"exact_fraction": "1/10"}},
            "programs": {"candidate_a": {"mean_regret": {"exact_fraction": "1/20"}}},
        }
        with patch.object(quality, "assess", return_value=fake):
            result = quality.screen_development_candidates({"candidate_a": PROGRAMS["pr847"]})
        self.assertEqual(result["candidate"], "candidate_a")
        self.assertEqual(result["disposition"],
                         "PROMISING_DEV_ONLY_REQUIRES_NEW_INDEPENDENT_EVIDENCE")
        self.assertFalse(result["optimizer_training_authorized"])
        self.assertFalse(result["scientific_accepted"])
        self.assertFalse(result["dispatch_authorized"])


if __name__ == "__main__":
    unittest.main()

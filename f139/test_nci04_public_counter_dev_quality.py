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



# NOV10_F139_COHORT: original publicly visible Yggdrasil PR file diffs.
# Source refs: github.com/spoonman136668-ai/Yggdrasil/pull/<PR>/files.
# Inert trusted arithmetic grammar only; never execute candidate Python.
# A finite public-grid equality is not a global equivalence certificate.
NOV10_F139_COHORT = {
    869: "max add two success mul success total",
    867: "max min two success mul success total",
    866: "add min two success mul success total",
    865: "mul min two success mul success total",
    864: "mul max two success mul success total",
    861: "add max two success mul success total",
    860: "add max two total mul success total",
    859: "mul max two total mul success total",
    858: "mul min two total mul success total",
    857: "add min two total mul success total",
    856: "add add two total mul success total",
    855: "mul add two total mul success total",
    854: "mul add one total mul success total",
    852: "add add one total mul success total",
    851: "add add failure total mul success total",
    850: "mul add failure total mul success total",
}


class November10OriginalCohortTests(unittest.TestCase):
    def test_public_proposals_preserve_negative_result_without_owner_authority(self):
        programs = {
            f"pr{number}": "rate " + numerator + " add add total zero add zero zero"
            for number, numerator in NOV10_F139_COHORT.items()
        }
        result = assess(programs)
        self.assertEqual(len(programs), 16)
        self.assertEqual(result["fixed_scenarios"], 54)
        self.assertEqual(result["grid_decision_cases"], 4225)
        self.assertEqual(result["strongest_control"], "laplace")
        self.assertEqual(result["controls"]["laplace"]["decimal"], "0.050400401845")
        self.assertEqual(result["distinct_fixed_dev_decision_behaviors"], 13)
        self.assertEqual(result["redundant_regret_evaluations_avoided"], 3)
        self.assertEqual(
            min(v["mean_regret"]["decimal"] for v in result["programs"].values()),
            "0.067387319411")
        self.assertEqual(result["programs"]["pr861"]["mean_regret"]["exact_fraction"],
                         "488406937/7247757312")
        self.assertEqual(result["programs"]["pr869"]["mean_regret"]["decimal"],
                         "0.074761040923")
        self.assertEqual(result["programs"]["pr856"]["mean_regret"],
                         result["programs"]["pr861"]["mean_regret"])
        self.assertEqual(
            result["programs"]["pr867"]["finite_public_grid_signature_sha256"],
            result["programs"]["pr865"]["finite_public_grid_signature_sha256"])
        for name, candidate in result["programs"].items():
            with self.subTest(name=name):
                self.assertFalse(candidate[
                    "beats_strongest_control_on_this_synthetic_dev_grid"])
        self.assertFalse(result["scientific_first_use"])
        self.assertFalse(result["scientific_accepted"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertFalse(result["owner_policy_modified"])


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

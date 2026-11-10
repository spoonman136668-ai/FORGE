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

    def test_invalid_program_or_input_rejected(self):
        for bad in ({}, {"bad": 3}, {" ": PROGRAMS["pr847"]},
                    {"pr847": "rate wrong"}, {"pr847": ""},
                    {"pr847": PROGRAMS["pr847"], "pr846": None}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                assess(bad)

    def test_reproducible_without_outcome_or_clock_inputs(self):
        self.assertEqual(assess(dict(reversed(list(PROGRAMS.items()))))["programs"],
                         self.result["programs"])


if __name__ == "__main__":
    unittest.main()

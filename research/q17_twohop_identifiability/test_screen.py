"""Adversarial exact tests for Q17 information sufficiency; no real episodes."""
from fractions import Fraction
from itertools import product
import pathlib
import unittest

import screen as q


class Q17IdentifiabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=q.read_protocol()
        cls.families=q.fixed_families(cls.protocol)

    def test_preexecuted_protocol_is_git_blob_pinned(self):
        self.assertEqual(q.FROZEN_BLOB,
                         "18fcff8607d93b9596cb22e5b190ac9fda8bd61f")
        self.assertEqual([k for k,_,_ in self.families],
                         ["C17_dev_a", "C17_dev_b"])
        self.assertEqual(self.protocol["evaluation"]
                         ["intervened_samples_per_family"],64)

    def test_complete_passive_population_equal_on_all_eight_events(self):
        for name,p,r in self.families:
            with self.subTest(name=name):
                a=q.passive_distribution("forward",p,r)
                b=q.passive_distribution("reverse",p,r)
                self.assertEqual(set(a),set(product((0,1),repeat=3)))
                self.assertEqual(a,b)
                self.assertEqual(sum(a.values()),1)
                self.assertEqual(min(a.values())>0,True)

    def test_intervention_is_terminal_outcome_not_unobserved_mediator(self):
        for _,p,r in self.families:
            for action in (0,1):
                self.assertEqual(q.intervention_symbolic("forward",action,p,r),
                                 q.intervention_closed_form("forward",p,r))
                self.assertEqual(q.intervention_symbolic("reverse",action,p,r),
                                 Fraction(1,2))

    def test_first_dev_family_twohop_effect_exact(self):
        _,p,r=self.families[0]
        self.assertEqual(q.intervention_closed_form("forward",p,r),
                         Fraction(37,50))
        self.assertEqual(q.intervention_closed_form("forward",p,r)-
                         q.intervention_closed_form("reverse",p,r),
                         Fraction(6,25))

    def test_second_dev_family_twohop_effect_exact(self):
        _,p,r=self.families[1]
        self.assertEqual(q.intervention_closed_form("forward",p,r),
                         Fraction(11,16))
        self.assertEqual(q.intervention_closed_form("forward",p,r)-
                         q.intervention_closed_form("reverse",p,r),
                         Fraction(3,16))

    def test_pure_passive_posterior_never_prefer_causal_direction(self):
        for _,p,r in self.families:
            lhs=q.passive_distribution("forward",p,r)
            rhs=q.passive_distribution("reverse",p,r)
            for event in lhs:
                # Equal structure priors imply posterior exactly 1/2.
                posterior=lhs[event]/(lhs[event]+rhs[event])
                self.assertEqual(posterior,Fraction(1,2))

    def test_exact_binomial_likelihood_mass_normalization(self):
        for n in (1,2,8,64):
            for prob in (Fraction(1,2),Fraction(37,50),Fraction(11,16)):
                self.assertEqual(sum(
                    (q.binomial_mass(n,k,prob) for k in range(n+1)),
                    Fraction(0)),1)

    def test_one_intervention_can_change_optimal_decision_risk(self):
        risk,info,strict=q.exact_equal_prior_bayes_error(
            1,Fraction(37,50),Fraction(1,2))
        self.assertEqual(risk,Fraction(19,50))
        self.assertGreater(info,0)
        self.assertEqual(strict,2)

    def test_exact_finite_interventions_are_information_sufficient(self):
        for _,p,r in self.families:
            risk,information,_=q.exact_equal_prior_bayes_error(
                64,q.intervention_closed_form("forward",p,r),Fraction(1,2))
            self.assertLessEqual(risk,Fraction(3,20))
            self.assertGreater(information,0)
            self.assertLess(information,1)

    def test_tampering_with_unknown_held_family_fails_closed(self):
        modified=dict(self.protocol)
        modified["development_families"]=[
            dict(self.protocol["development_families"][0]),
            {"id":"C17_hold_c","p_num":1,"p_den":3,
             "q_num":1,"q_den":9}]
        with self.assertRaisesRegex(ValueError,"HELD_FAMILY_FORBIDDEN"):
            q.fixed_families(modified)

    def test_class_bias_has_no_unjustified_passive_certification(self):
        # No single passive event distinguishes direction; in particular,
        # the highest likelihood ratio equals exactly one.
        for _,p,r in self.families:
            left=q.passive_distribution("forward",p,r)
            right=q.passive_distribution("reverse",p,r)
            self.assertTrue(all(left[k]/right[k]==1 for k in left))

    def test_model_comparators_have_matching_intervention_access(self):
        e=self.protocol["evaluation"]
        self.assertEqual(e["intervention_allocation"],
                         {"do_X_0":32,"do_X_1":32})
        self.assertTrue(e["matched_intervention_budget_for_each_control"])
        self.assertTrue(e["no_learned_capability_claim"])
        self.assertTrue(e["no_development_fit_or_optimizer_tuning"])

    def test_no_original_source_or_unfamiliar_generator(self):
        src=pathlib.Path(q.__file__).read_text(encoding="utf-8").lower()
        for forbidden in ("import minigrid", "import pycolab",
                          "from minigrid", "from pycolab",
                          "import requests", "import socket",
                          "import subprocess", "import urllib",
                          "import github", "import cloudflare"):
            self.assertNotIn(forbidden,src)
        self.assertFalse(self.protocol["custody"]["protected_scientific_first_use"])
        self.assertEqual(self.protocol["custody"]["original_source_engine_episodes"],0)

    def test_selftest_and_screen_do_not_claim_learning(self):
        q.selftest(self.protocol)
        result=q.screen(self.protocol)
        self.assertFalse(result["native_learned_cognitive_candidate_trained"])
        self.assertFalse(result["held_unfamiliar_cases_generated"])
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(len(result["cases"]),2)


if __name__=="__main__":
    unittest.main()

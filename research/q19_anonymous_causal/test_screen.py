"""Q19A adversarial anonymous causal-variable identifiability tests."""
from fractions import Fraction
from itertools import permutations,product
import pathlib
import unittest
import screen as q


class Q19AnonymousCausalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy=q.read_frozen()
        cls.families=[q.config(cls.policy,x) for x in q.PARAMETERS]

    def test_frozen_design_precedes_all_computation(self):
        self.assertEqual(q.FROZEN_BLOB,
                         "aa85f7b1c0d1cdf5c4a7daf08f5457358fa09bf4")
        self.assertEqual(len(q.PERMUTATIONS),6)
        self.assertEqual(q.KINDS,("chain","fork"))
        self.assertEqual(
            self.policy["scientific_decision"]["success"],
            "INFORMATION_SUFFICIENT_FOR_ANONYMOUS_CAUSAL_DISCOVERY_DESIGN_ONLY")

    def test_parameter_families_are_new_and_bounded(self):
        self.assertEqual(self.families,[(Fraction(1,6),Fraction(1,7)),
                                         (Fraction(2,9),Fraction(1,11))])

    def test_unregistered_or_held_families_never_evaluated(self):
        for name in ("Q19A_H1","Q19A_H2","Q17A_C17_hold_c",
                     "original","protected",""):
            with self.subTest(name=name):
                with self.assertRaisesRegex(RuntimeError,
                                            "HELD_OR_UNREGISTERED_PARAMETER_FAMILY"):
                    q.config(self.policy,name)

    def test_scm_passive_joint_mass_exact_all_eight_outputs(self):
        for p,r in self.families:
            for kind in q.KINDS:
                for perm in q.PERMUTATIONS:
                    with self.subTest(kind=kind,perm=perm,p=p):
                        distribution=q.exact_distribution(kind,perm,p,r)
                        self.assertEqual(len(distribution),8)
                        self.assertEqual(sum(distribution.values()),1)
                        self.assertTrue(all(x>0 for x in distribution.values()))

    def test_passive_chain_fork_alias_for_same_anonymous_permutation(self):
        for p,r in self.families:
            for perm in q.PERMUTATIONS:
                a=q.exact_distribution("chain",perm,p,r)
                b=q.exact_distribution("fork",perm,p,r)
                self.assertEqual(a,b)

    def test_public_interventions_do_not_change_assigned_slot(self):
        for kind in q.KINDS:
            for perm in q.PERMUTATIONS:
                for slot in range(3):
                    for value in (0,1):
                        a=q.scm(kind,perm,root=0,e1=1,e2=0,
                                intervention=(slot,value))
                        self.assertEqual(a[slot],value)

    def test_every_population_do_distribution_normalized(self):
        p,r=self.families[0]
        for kind in q.KINDS:
            for perm in q.PERMUTATIONS:
                effect,distributions=q.effects_of(kind,perm,p,r)
                self.assertEqual(len(distributions),6)
                self.assertEqual(len(effect),6)
                for dist in distributions.values():
                    self.assertEqual(sum(dist.values()),1)

    def test_unknown_sensor_ancestry_from_observed_effect_signs(self):
        for p,r in self.families:
            for kind in q.KINDS:
                for perm in q.PERMUTATIONS:
                    effect,_=q.effects_of(kind,perm,p,r)
                    detected={k for k,v in effect.items() if v>0}
                    self.assertEqual(detected,q.ancestors(kind,perm))

    def test_symbolic_path_control_matches_independent_scm_enumeration(self):
        for p,r in self.families:
            for kind in q.KINDS:
                for perm in q.PERMUTATIONS:
                    empirical,_=q.effects_of(kind,perm,p,r)
                    symbolic=q.symbolic_effects(kind,perm,p,r)
                    self.assertEqual(empirical,symbolic)

    def test_twohop_chain_mediated_causal_effect_multiplies(self):
        for p,r in self.families:
            effect,_=q.effects_of("chain",(0,1,2),p,r)
            self.assertEqual(effect[(0,2)],
                             (1-2*p)*(1-2*r))
            self.assertEqual(effect[(0,2)],
                             effect[(0,1)]*effect[(1,2)])

    def test_fork_has_no_terminal_child_to_child_effect(self):
        p,r=self.families[0]
        effect,_=q.effects_of("fork",(0,1,2),p,r)
        self.assertEqual(effect[(0,2)],0)
        self.assertEqual(effect[(2,0)],0)
        self.assertGreater(effect[(1,0)],0)
        self.assertGreater(effect[(1,2)],0)

    def test_interventional_population_identifiability_predefined_gate(self):
        for family,(p,r) in zip(q.PARAMETERS,self.families):
            result=q.report_for(family,p,r)
            self.assertEqual(result["latent_cases"],12)
            self.assertEqual(result["all_pair_comparisons"],66)
            self.assertGreaterEqual(result["chain_vs_fork_observational_collisions"],6)
            self.assertGreaterEqual(
                Fraction(result["minimum_intervention_effect_gap_between_different_ancestry"]),
                Fraction(1,4))
            self.assertTrue(result["oracle_symbolic_equal_exact"])

    def test_all_original_science_and_learned_claims_blocked(self):
        guards=self.policy["guardrails"]
        self.assertTrue(guards["no_original_minigrid_pycolab_episodes"])
        self.assertTrue(guards["no_protected_original_source_first_use"])
        self.assertTrue(guards["no_controller_queue_dispatch"])
        self.assertTrue(guards["no_held_or_outside_family_generation"])
        text=pathlib.Path(q.__file__).read_text().lower()
        for forbidden in ("import minigrid","import pycolab",
                          "import socket","import urllib","import requests",
                          "import subprocess","import cloudflare"):
            self.assertNotIn(forbidden,text)


if __name__=="__main__":
    unittest.main()

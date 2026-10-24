"""L10-B6 invented-only probe-scarcity, posterior and learning-custody tests."""
from collections import Counter
from dataclasses import replace
import unittest

import l10_dev_source_custody as src
import l10_b4_effect_local_learning as b4
import l10_b5_delayed_probe_dev as b5
import l10_b6_scarce_design_dev as q

def cases():
    a=src.development_collection("WITHHELD_MAPPING")
    return [x for x in a if x.split=="DEV_FIT"],[x for x in a if x.split=="DEV_CHECK"]

class ScarcityTests(unittest.TestCase):
    def test_real_scarcity_not_exhaustive_coverage(self):
        self.assertEqual(len(q.CODES),3)
        self.assertEqual(q.BUDGETS,(1,2))
        self.assertTrue(all(x<len(q.CODES) for x in q.BUDGETS))
        self.assertEqual(len(q.ALL_MAPS),6)
        self.assertEqual(q.BUDGETS[1],2)

    def test_empty_prior_has_six_maps_and_creates_no_meaning(self):
        self.assertEqual(len(q.hypotheses(Counter())),6)
        self.assertEqual(q.determined(Counter()),{})
        fit,check=cases()
        self.assertIsNone(q.infer_with_posterior(src.public_input(check[0]),Counter()))

    def test_one_observation_does_not_overinfer_remaining_codes(self):
        seen=Counter({("P0","E0"):1})
        self.assertEqual(len(q.hypotheses(seen)),2)
        self.assertEqual(q.determined(seen),{"P0":"E0"})
        self.assertNotIn("P1",q.determined(seen))
        self.assertNotIn("P2",q.determined(seen))

    def test_second_distinct_probe_deduces_final_code_with_public_bijection(self):
        seen=Counter({("P0","E0"):1,("P1","E2"):1})
        self.assertEqual(len(q.hypotheses(seen)),1)
        self.assertEqual(q.determined(seen),{"P0":"E0","P1":"E2","P2":"E1"})
        self.assertEqual(q.determined(b4.LocalMemory.restore(
            b4.LocalMemory().update(b4.Observation("P0","E0"))
            .update(b4.Observation("P1","E2")).snapshot()).counts),q.determined(seen))

    def test_inconsistent_sensor_effect_does_not_produce_false_posterior(self):
        for dirty in (
            Counter({("P0","E0"):1,("P0","E1"):1}),
            Counter({("P0","E0"):1,("P1","E0"):1}),
            Counter({("P2","E7"):1})
        ):
            if ("P2","E7") in dirty:
                with self.assertRaises(ValueError):q.hypotheses(dirty)
            else:
                self.assertEqual(q.hypotheses(dirty),())
                self.assertEqual(q.determined(dirty),{})

    def test_bayesian_expected_graph_utility_no_dev_check_access(self):
        fit,_=cases()
        shapes,counts=q._fit_shapes(fit)
        scores=[q.exact_expected_utility(c,Counter(),shapes) for c in q.CODES]
        self.assertEqual(len(scores),3)
        self.assertTrue(all(0<=x<=1 for x in scores))
        first=q.pick("exact-bayesian-design",Counter(),shapes,counts,0)
        self.assertEqual(first, max(q.CODES,key=lambda c:(q.exact_expected_utility(c,Counter(),shapes),
                                                        -q.CODES.index(c))))
        # Candidate has full baseline information too, but deliberately uses
        # a different heuristic for selecting experiments.
        self.assertIn(q.pick("local-uncertainty",Counter(),shapes,counts,0),q.CODES)

    def test_one_budget_prevents_inference_of_all_three_maps(self):
        fit,check=cases()
        for method in q.METHODS[:-1]:
            r=q.execute(fit,check,"DELAYED_CLEAN",method,1)
            self.assertEqual(r["query_count"],1)
            self.assertEqual(r["permutation_posterior_size"],2)
            self.assertEqual(r["fully_determined_relation_count"],1)
            self.assertEqual(r["delivered_ticket_count"],1)
            self.assertTrue(r["delayed_delivery_verified"])
            self.assertIsNotNone(r["recovered_restart_sha256"])
            self.assertTrue(0<=r["micro_exact"]<=1)

    def test_two_budget_strong_bayesian_recovers_bijection(self):
        fit,check=cases()
        r=q.execute(fit,check,"DELAYED_CLEAN","exact-bayesian-design",2)
        self.assertEqual(r["query_count"],2)
        self.assertEqual(r["permutation_posterior_size"],1)
        self.assertEqual(r["fully_determined_relation_count"],3)
        self.assertEqual(r["micro_exact"],1)
        self.assertEqual(r["micro_abstention"],0)
        self.assertEqual(sum(f["exact"] for f in r["outcomes"]),12)
        self.assertEqual(len(set(r["selected_code_sequence"])),2)

    def test_no_query_baseline_abstains_on_complete_case_denominator(self):
        fit,check=cases()
        for budget in q.BUDGETS:
            r=q.execute(fit,check,"DELAYED_CLEAN","no-query",budget)
            self.assertEqual(r["query_count"],0)
            self.assertEqual(r["micro_exact"],0)
            self.assertEqual(r["micro_abstention"],1)
            self.assertEqual(sum(x["abstentions"] for x in r["outcomes"]),12)

    def test_all_regimes_have_explicit_negative_condition(self):
        fit,check=cases()
        for regime in q.CONDITIONS:
            bayes=q.execute(fit,check,regime,"exact-bayesian-design",2)
            self.assertEqual(bayes["prospective_source_consumed"],False)
            self.assertEqual(bayes["scientific_go"],False)
            if regime=="DELAYED_CLEAN":
                self.assertEqual(bayes["micro_exact"],1)
            else:
                self.assertEqual(bayes["micro_exact"],0)
                self.assertEqual(bayes["micro_abstention"],1 if regime=="DELAYED_NO_FEEDBACK" else 0)

    def test_same_budget_every_nonabstaining_policy_and_all_six_controls(self):
        fit,check=cases()
        r=q.benchmark(fit,check)
        self.assertEqual(len(r["outcomes"]),36)
        self.assertEqual(len(r["budgets"]),2)
        self.assertFalse(r["scientific_go"])
        self.assertEqual(r["prospectively_protected_examples_generated"],0)
        for budget in q.BUDGETS:
            for regime in q.CONDITIONS:
                z=[x for x in r["outcomes"] if x["budget"]==budget and x["condition"]==regime]
                self.assertEqual([x["method"] for x in z],list(q.METHODS))
                self.assertEqual([x["query_count"] for x in z],[budget]*5+[0])
                self.assertEqual(len({x["source_fit_world_sha256"] for x in z}),1)

    def test_train_check_or_prospective_role_not_allowed_as_fit(self):
        fit,check=cases()
        with self.assertRaises(ValueError):q.execute(check,fit,"DELAYED_CLEAN","local-uncertainty",1)
        with self.assertRaises(ValueError):
            q.execute([replace(fit[0],role=src.PROSPECTIVE_ROLE)]+fit[1:],check,
                      "DELAYED_CLEAN","local-uncertainty",1)
        with self.assertRaises(ValueError):
            q.execute(fit,[replace(check[0],role=src.PROSPECTIVE_ROLE)]+check[1:],
                      "DELAYED_CLEAN","local-uncertainty",1)
        with self.assertRaises(ValueError):
            q.execute(fit,check,"DELAYED_CLEAN","not-a-method",1)
        with self.assertRaises(ValueError):
            q.execute(fit,check,"DELAYED_CLEAN","local-uncertainty",3)

    def test_repeated_dev_cases_deterministic_scientific_not_timings(self):
        fit,check=cases()
        x=q.execute(fit,check,"DELAYED_CLEAN","exact-bayesian-design",2)
        y=q.execute(fit,check,"DELAYED_CLEAN","exact-bayesian-design",2)
        for field in ("source_fit_world_sha256","selected_code_sequence","learned_state_sha256",
                      "micro_exact","micro_abstention","permutation_posterior_size",
                      "outcomes"):
            self.assertEqual(x[field],y[field])

if __name__=="__main__":unittest.main()

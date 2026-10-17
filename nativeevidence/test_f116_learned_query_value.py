"""F116: source-disjoint noisy sensor, trained policy, baseline and no-authority checks."""
from collections import Counter
import dataclasses
import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f116_learned_query_value as m

class F116Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train,cls.guards=m.cohorts()

    def test_frozen_before_implementation_and_parent_unchanged(self):
        cfg,digest=m.frozen()
        self.assertEqual(m.gitblob(m.canonical(m.FREEZE)),m.FREEZE_BLOB)
        self.assertEqual(cfg["parent"]["exact_F115_head"],m.PARENT_SHA)
        self.assertEqual(len(digest),64)

    def test_all_train_and_guard_source_graph_IDs_disjoint(self):
        allcases=self.train+tuple(w for g in self.guards for w in g)
        self.assertEqual(len(allcases),4096)
        self.assertEqual(len({w.sample_id for w in allcases}),4096)
        self.assertEqual(len({w.graph_fingerprint for w in allcases}),4096)
        self.assertEqual(len({v for w in allcases for v in w.public.candidate_codes}),8192)

    def test_exact_precommitted_splits_and_channel_price_balance(self):
        self.assertEqual([len(g) for g in self.guards],[768]*4)
        for family,group in enumerate((self.train,)+self.guards):
            counter=Counter((w.public.channel,w.public.cost) for w in group)
            self.assertEqual(len(counter),16)
            self.assertEqual(set(counter.values()),{64 if family==0 else 48})
            self.assertTrue(all(w.family==family for w in group))

    def test_hidden_labels_never_in_policy_interface(self):
        self.assertEqual({v.name for v in dataclasses.fields(m.Public)},
                         {"anchor","candidate_codes","channel","cost"})
        self.assertEqual(tuple(inspect.signature(m.learned_policy).parameters),
                         ("model",))
        self.assertEqual(tuple(inspect.signature(m.choose_if_query).parameters),
                         ("p","read","should_query"))
        self.assertNotIn("graph_truth",str(inspect.signature(m.choose_if_query)))

    def test_counterfactual_sign_is_one_observation_only(self):
        for g in (self.train,)+self.guards:
            for w in g:
                changed=[i for i,(a,b) in enumerate(zip(w.positive,w.negative)) if a!=b]
                self.assertEqual(changed,[w.graph_truth])
                self.assertEqual((w.positive[w.graph_truth],w.negative[w.graph_truth]),
                                 (1.,-1.))

    def test_misleading_and_uninformative_evidence_exist_every_guard(self):
        for g in self.guards:
            self.assertGreater(sum(not w.sensor for w in g),0)
            self.assertGreater(sum(w.sensor and w.sensor[0].source_code!=
                              w.public.candidate_codes[w.graph_truth] for w in g),0)
            self.assertGreater(sum(w.sensor and w.sensor[0].source_code==
                              w.public.candidate_codes[w.graph_truth] for w in g),0)

    def test_licensing_of_only_one_paid_sensor_read(self):
        p=m.PaidPort(())
        self.assertEqual(p.read(),())
        self.assertEqual(p.queries,1)
        with self.assertRaisesRegex(m.Invalid,"SECOND_QUERY_REFUSED"):p.read()

    def test_invalid_sensor_anchor_schema_source_or_count_abstains(self):
        meta=self.guards[0][0].public
        good=m.Link(m.EDGE_KIND,meta.anchor,meta.candidate_codes[0])
        self.assertEqual(m.valid_edge(meta,(good,)),0)
        self.assertIsNone(m.valid_edge(meta,()))
        self.assertIsNone(m.valid_edge(meta,(good,good)))
        self.assertIsNone(m.valid_edge(meta,(m.Link("forged",meta.anchor,meta.candidate_codes[0]),)))
        self.assertIsNone(m.valid_edge(meta,(m.Link(m.EDGE_KIND,"forged",meta.candidate_codes[0]),)))
        self.assertIsNone(m.valid_edge(meta,(m.Link(m.EDGE_KIND,meta.anchor,"unlisted"),)))

    def test_learner_uses_train_only_and_exact_eight_parameters(self):
        model=m.LearnedChannelValue().fit(self.train)
        self.assertEqual(model.updates,100)
        self.assertEqual(len(model.availability)+len(model.correctness),8)
        self.assertTrue(all(-8<=x<=8 for x in model.availability+model.correctness))
        with self.assertRaisesRegex(m.Invalid,"TRAIN_ONLY_PROVENANCE"):
            m.LearnedChannelValue().fit(self.guards[0])
        with self.assertRaisesRegex(m.Invalid,"TRAIN_ONLY_PROVENANCE"):
            model.fit(self.train)

    def test_beta_control_has_exact_same_training_data(self):
        model=m.LearnedChannelValue().fit(self.train)
        beta=m.BetaChannelValue(self.train)
        for ch in range(4):
            u,v=model.rates(ch)
            p,q=beta.rates(ch)
            self.assertTrue(0<u<1 and 0<v<1 and 0<p<1 and 0<q<1)
            self.assertLess(abs(u-p),0.06)
            self.assertLess(abs(v-q),0.06)

    def test_query_threshold_preserves_sign_of_cost_intervention(self):
        for reliability in (0.55,0.70,0.86,0.97):
            baseline=m.buy_if_positive((.875,reliability),.05)
            self.assertFalse(m.buy_if_positive((.875,reliability),10))
            if baseline:self.assertTrue(m.buy_if_positive((.875,reliability),0))
        self.assertFalse(m.buy_if_positive((0.0,1.0),.05))

    def test_decision_attribution_and_counterfactual_ablations_are_observable(self):
        model=m.LearnedChannelValue().fit(self.train)
        for ch in range(4):
            for price in m.COSTS:
                t=m.inspect_query_decision(model,ch,price)
                self.assertEqual(t["channel"],ch)
                self.assertEqual(t["quoted_cost"],price)
                self.assertEqual(t["query"],
                    m.buy_if_positive(model.rates(ch),price))
                self.assertEqual(t["ablation_replace_usable_with_half"],
                    m.buy_if_positive((.5,model.rates(ch)[1]),price))
                self.assertEqual(t["ablation_replace_correctness_with_half"],
                    m.buy_if_positive((model.rates(ch)[0],.5),price))
                self.assertEqual(t["intervention_increase_cost_by_0_25"],
                    m.buy_if_positive(model.rates(ch),price+.25))
                self.assertFalse(t["intervention_increase_cost_by_0_25"]
                                 and not t["query"])
                self.assertIn("TRAIN_ONLY",t["source"])

    def test_no_query_never_pays_always_query_always_pays(self):
        for g in self.guards[:1]:
            self.assertEqual(m.assess(g,m.no_query)["queries"],0)
            self.assertEqual(m.assess(g,m.always_query)["queries"],768)

    def test_misleading_graph_edges_are_counted_as_real_negative(self):
        scores=m.assess(self.guards[0],m.always_query)
        self.assertGreater(scores["misleading_paid_queries"],0)
        self.assertGreater(scores["wrong"],0)
        self.assertGreater(scores["empty_paid_queries"],0)
        self.assertEqual(scores["count"],768)
        self.assertEqual(scores["correct"]+scores["wrong"]+scores["abstained"],768)

    def test_full_report_preserves_utility_and_no_authority(self):
        result=m.evaluate("a"*40)
        self.assertEqual(result["train_count"],1024)
        self.assertEqual(result["guard_count"],3072)
        self.assertEqual(result["trained_steps"],100)
        self.assertEqual(result["learned_trainable_params"],8)
        self.assertEqual(len(result["guard_blocks"]),4)
        self.assertEqual(len(result["policy_trace_by_channel_cost"]),16)
        self.assertFalse(result["scientific_first_use_authorized"])
        self.assertFalse(result["independently_accepted_science"])
        self.assertFalse(result["optimizer_promotion_authorized"])
        self.assertEqual(result["accepted_ref_mutations"],0)
        self.assertEqual(result["codex_calls"],0)
        self.assertEqual(result["model_API_calls"],0)
        self.assertTrue(all(len(b["policies"]["learned_train_only_eight_logits"]["rows"])==768
                            for b in result["guard_blocks"]))
        self.assertIn("empirical_beta_train_only",result["totals_by_arm"])
        self.assertIn("unavailable_true_simulator_rate_oracle",result["totals_by_arm"])

if __name__=="__main__":
    unittest.main()

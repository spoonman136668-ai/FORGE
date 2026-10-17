"""F117 guardrail tests: frozen graph-relational context and source-disjoint transfer."""
import collections
import json
import os
from dataclasses import fields,replace
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f117_relational_context as m

class F117Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=m.frozen()
        cls.train,cls.guards=m.cohorts()
    def test_preregistered_first_and_source_provenance(self):
        self.assertEqual(m.blob(m.raw(m.FREEZE)),m.FREEZE_BLOB)
        self.assertEqual(self.cfg["parent"]["exact_F116_head"],m.PARENT_HEAD)
        self.assertTrue(all(self.cfg["authority"].values()))
        self.assertEqual(len(self.digest),64)

    def test_all_train_guard_source_IDs_held_out_and_16_role_pairs(self):
        rows=self.train+tuple(w for g in self.guards for w in g)
        self.assertEqual([len(self.train)]+[len(g) for g in self.guards],
                         [1024,512,512,512,512])
        self.assertEqual(len({w.seed for w in rows}),3072)
        self.assertEqual(len({w.public.root for w in rows}),3072)
        self.assertEqual(len({code for w in rows for code in w.public.source_codes}),6144)

    def test_precommitted_context_balance_and_noise_on_each_guard(self):
        for i,group in enumerate((self.train,)+self.guards):
            reps=4 if i==0 else 2
            count=collections.Counter((w.public.channel,w.public.cost,
                                        m.role_match(w.public)) for w in group)
            for ch in range(4):
                for cost in m.COSTS:
                    self.assertEqual(count[ch,cost,True],reps*4)
                    self.assertEqual(count[ch,cost,False],reps*12)
            if i:
                self.assertGreater(sum(w.sensor_tag is None for w in group),0)
                self.assertGreater(sum(
                    w.sensor_tag is not None and w.sensor_tag!=w.true_tag
                    for w in group),0)

    def test_public_actor_interface_excludes_latent_truth_or_sensor(self):
        names={f.name for f in fields(m.Public)}
        self.assertEqual(names,{"root","target","edges","source_codes",
                                 "channel","cost","schema"})
        p=self.guards[0][0].public
        self.assertFalse(hasattr(p,"true_tag"))
        self.assertFalse(hasattr(p,"sensor_tag"))

    def test_role_equality_survives_guard_graph_transformations(self):
        # Each family has equivalent two-hop role equality even with aliases,
        # reversed edge order, and unrelated graph distractors.
        for group in self.guards:
            for w in group[:32]:
                self.assertEqual(m.role_match(w.public),
                    any(a==b for left,a,mid in w.public.edges
                         if left==w.public.root
                         for src,b,dst in w.public.edges
                         if mid==src and dst==w.public.target))
        self.assertTrue(any(len(w.public.edges)>2 for w in self.guards[3]))

    def test_one_charged_query_no_oracle_response_before(self):
        port=m.PaidSensor(None)
        self.assertIsNone(port.read())
        with self.assertRaisesRegex(m.Quarantined,"SECOND_PAID_QUERY"):
            port.read()
        self.assertEqual(m.evaluate_one(self.guards[0][0],"never_query",
            m.LearnedRelationValue(),m.ContextBeta(self.train),
            m.ContextBeta(self.train,False))["requested"],0)

    def test_train_only_ten_parameters_and_same_data_bayesian(self):
        learner=m.LearnedRelationValue().fit(self.train)
        self.assertEqual(learner.updates,100)
        self.assertEqual(len(learner.theta),10)
        with self.assertRaisesRegex(m.Quarantined,"TRAIN_ONLY"):
            m.LearnedRelationValue().fit(self.guards[0])
        context=m.ContextBeta(self.train,True)
        channel=m.ContextBeta(self.train,False)
        for group in self.guards[:2]:
            for w in group[:16]:
                self.assertTrue(all(0<x<1 for x in learner.rates(w.public)))
                self.assertTrue(all(0<x<1 for x in context.rates(w.public)))
                self.assertTrue(all(0<x<1 for x in channel.rates(w.public)))

    def test_strong_context_Beta_and_oracle_comparators_same_cases(self):
        sample=self.guards[0][0]
        learner=m.LearnedRelationValue().fit(self.train)
        beta=m.ContextBeta(self.train,True)
        control=m.ContextBeta(self.train,False)
        for arm in m.ARMS:
            row=m.evaluate_one(sample,arm,learner,beta,control)
            self.assertEqual(row["correct"]+row["wrong"]+row["abstain"],1)
            self.assertLessEqual(row["requested"],1)
            self.assertEqual(row["requested"],int(row["spent"]>0))

    def test_full_source_only_report_preserves_negative_outcomes(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"a"*40}):
            report=m.evaluate("a"*40)
        self.assertEqual(report["schema"],m.SCHEMA)
        self.assertEqual(report["train_cases"],1024)
        self.assertEqual(report["guard_cases"],2048)
        self.assertEqual(report["learned_trainable_parameters"],10)
        self.assertEqual(len(report["guard_blocks"]),4)
        self.assertTrue(report["engineeered_role_equality_feature_not_unrestricted_learning"])
        for block in report["guard_blocks"]:
            for arm in m.ARMS:
                score=block["arms"][arm]
                self.assertEqual(len(score["records"]),512)
                self.assertEqual(score["correct"]+score["wrong"]+
                                 score["abstain"],512)
        self.assertEqual(report["independent_originals"],0)
        self.assertFalse(report["scientific_first_use_authorized"])
        self.assertEqual(report["codex_calls"],0)
        self.assertEqual(report["accepted_ref_mutations"],0)

    def test_reject_mismatched_host_sha(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(m.Quarantined,"CURRENT_GITHUB_SHA"):
                m.evaluate("a"*40)

if __name__=="__main__":
    unittest.main()

"""F113: verify frozen source identity, full-factorial control and no hidden label input."""
import dataclasses
import inspect
import json
from pathlib import Path
import sys
import unittest
from collections import Counter

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f113_orthogonal_source_binding as m

class F113Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups=m.public_groups()

    def test_frozen_before_code_parent_sha_and_source_contract(self):
        cfg,sha=m.freeze()
        self.assertEqual(m.git_blob(m.canonical(m.FREEZE)),m.FREEZE_BLOB)
        self.assertEqual(len(sha),64)
        self.assertEqual(cfg["intervention"]["pairs_each"],48)

    def test_parent_source_training_diagnostic_and_new_seeds_disjoint(self):
        train,diagnostics=m.parent.wing_cohorts()
        old={p.seed for p in train}
        old.update(p.seed for group in diagnostics for p in group)
        new={p.seed for group in self.groups for p in group}
        self.assertEqual(len(new),144)
        self.assertFalse(old & new)

    def test_each_block_has_every_depth_by_target_cell_three_times(self):
        for block in self.groups:
            c=Counter((p.query_depth,p.true_tag()) for p in block)
            self.assertEqual(len(c),16)
            self.assertEqual(set(c.values()),{3})
            self.assertEqual(sum(p.query_depth==p.true_tag() for p in block),12)

    def test_query_depth_alone_indeed_only_solves_quarter_of_pairs(self):
        for block in self.groups:
            self.assertEqual(sum(m.paired_correct(m.shortcut_only,p) for p in block),12)

    def test_exact_metadata_control_succeeds_without_training(self):
        for block in self.groups:
            self.assertEqual(sum(m.paired_correct(m.parent.exact_lookup,p) for p in block),48)

    def test_only_one_counterfactual_observation_changes(self):
        for block in self.groups:
            for p in block:
                diff=[i for i,(a,b) in enumerate(zip(p.positive_values,p.negative_values)) if a!=b]
                self.assertEqual(diff,[p.observation_depths.index(p.true_tag())])
                self.assertEqual(p.positive_values[diff[0]],1.0)
                self.assertEqual(p.negative_values[diff[0]],-1.0)

    def test_requested_code_not_derivable_from_query_depth_alone(self):
        for block in self.groups:
            by_q={}
            for p in block:
                by_q.setdefault(p.query_depth,set()).add(p.true_tag())
            self.assertEqual(by_q,{q:set(range(4)) for q in range(4)})

    def test_source_code_vocabulary_fresh_within_each_block(self):
        for block in self.groups:
            allcodes=[v for p in block for v in p.source_codes]
            self.assertEqual(len(allcodes),192)
            self.assertEqual(len(set(allcodes)),192)

    def test_frozen_signatures_do_not_admit_outcome_to_predictor(self):
        self.assertEqual(tuple(inspect.signature(m.public_case).parameters),("seed","block"))
        self.assertEqual(tuple(inspect.signature(m.parent.LearnedRelationAttention.predicts).parameters),
                         ("self","p","values"))
        self.assertEqual(dataclasses.fields(m.parent.WCase)[0].name,"seed")
        self.assertNotIn("true_tag",tuple(f.name for f in dataclasses.fields(m.parent.WCase)))

    def test_reject_noncohort_source_even_if_seed_looks_similar(self):
        for seed,block in ((68699,0),(68748,0),(68700,1),(69000,2)):
            with self.subTest(seed=seed,block=block):
                with self.assertRaises(m.Rejected):m.public_case(seed,block)

    def test_test_set_does_not_train_new_parameters(self):
        src=inspect.getsource(m.evaluate)
        self.assertNotIn(".train(",src)
        self.assertNotIn(".fit(",src)
        self.assertIn("models()",src)

    def test_every_public_code_has_single_requested_anchor(self):
        for block in self.groups:
            for p in block:
                self.assertEqual(p.source_codes.count(p.requested_code),1)
                self.assertEqual(len(p.observation_depths),4)
                self.assertEqual(sorted(p.observation_depths),list(range(4)))

    def test_report_preserves_negative_and_denies_accepted_research(self):
        report=m.evaluate("a"*40)
        self.assertEqual(report["new_public_counterfactual_pairs"],144)
        self.assertEqual(report["query_depth_only_total_correct"],36)
        self.assertEqual(report["strong_symbolic_total_correct"],144)
        self.assertEqual(report["diagnostic_training_steps"],0)
        self.assertFalse(report["scientific_first_use_authorized"])
        self.assertFalse(report["independent_scientific_acceptance"])
        self.assertFalse(report["optimizer_promotion_authorized"])
        self.assertEqual(report["accepted_ref_mutations"],0)
        self.assertEqual(report["codex_calls"],0)
        self.assertEqual([len(v["individual_rows"]) for v in report["blocks"]],[48]*3)
        self.assertLessEqual(report["learned_total_correct"],report["strong_symbolic_total_correct"])
        self.assertFalse(report["incremental_learning_superiority_screen_passed"]
                         and report["net_learned_gain_vs_fixed"]<18)
        self.assertEqual(report["lanes_evaluated"],["Wingless"])

if __name__=="__main__":
    unittest.main()

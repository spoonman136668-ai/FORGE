"""F115: precode custody, paid one-read decision bounds and unresolvable twins."""
import dataclasses
import inspect
import sys
import unittest
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f115_bounded_active_clarification as m

class PublicAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks=m.cohorts()

    def test_p0_prereg_frozen_before_code_and_f114_unchanged(self):
        cfg,digest=m.freeze()
        self.assertEqual(m.gitblob(m.readbytes(m.FREEZE)),m.FREEZE_BLOB)
        self.assertEqual(cfg["parent"]["f114_exact_head"],m.PARENT_HEAD)
        self.assertEqual(len(digest),64)

    def test_new_disjoint_world_identity_and_144_source_no_overlap(self):
        ids=[x.case_id for b in self.blocks for x in b]
        self.assertEqual(len(ids),192)
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual([len(b) for b in self.blocks],[48]*4)
        self.assertTrue(all(x>=70000 for x in ids))

    def test_unique_and_role_resolvable_public_cases_need_no_query(self):
        for b in self.blocks[:2]:
            for x in b:
                self.assertEqual(m.parent.certificate(x.public),x.true_tag)
                port=m.Port(x.ledger_links)
                self.assertEqual(m.conditional(x.public,port.read),x.true_tag)
                self.assertEqual(port.calls,0)

    def test_same_prior_public_metadata_twins_are_genuinely_ambiguous(self):
        for b in self.blocks[2:]:
            for i in range(0,48,2):
                a,c=b[i:i+2]
                self.assertEqual(a.public,c.public)
                self.assertNotEqual(a.true_tag,c.true_tag)
                self.assertIsNone(m.parent.certificate(a.public))
                self.assertEqual(m.parent.nearest(a.public)[1],1)
                self.assertEqual(len(m.parent.nearest(a.public)[0]),2)

    def test_signal_query_distinguishes_twins_with_new_external_public_edge(self):
        for i in range(0,48,2):
            a,b=self.blocks[2][i:i+2]
            self.assertEqual(len(a.ledger_links),len(b.ledger_links))
            self.assertNotEqual(a.ledger_links,b.ledger_links)
            for x in (a,b):
                port=m.Port(x.ledger_links)
                self.assertEqual(m.conditional(x.public,port.read),x.true_tag)
                self.assertEqual(port.calls,1)

    def test_empty_query_identical_for_unsolvable_twins(self):
        for i in range(0,48,2):
            a,b=self.blocks[3][i:i+2]
            self.assertEqual(a.public,b.public)
            self.assertEqual(a.ledger_links,b.ledger_links)
            for x in (a,b):
                port=m.Port(x.ledger_links)
                self.assertIsNone(m.conditional(x.public,port.read))
                self.assertEqual(port.calls,1)

    def test_double_paid_query_is_rejected(self):
        port=m.Port(())
        self.assertEqual(port.read(),())
        with self.assertRaisesRegex(m.Invalid,"ADDITIONAL_RELATION_QUERY_DENIED"):
            port.read()

    def test_spoofed_bad_relation_or_wrong_ledger_anchor_fails_closed(self):
        for x in self.blocks[2][:3]:
            wrong=m.RelationLink(x.public.source_codes[x.true_tag],
                "wrong-relation",x.public.requested_code)
            badanchor=m.RelationLink(x.public.source_codes[x.true_tag],
                m.ROLE_LINK,"wrong-anchor")
            self.assertIsNone(m.choose_after_ledger(x.public,(wrong,)))
            self.assertIsNone(m.choose_after_ledger(x.public,(badanchor,)))
            self.assertIsNone(m.choose_after_ledger(x.public,(badanchor,wrong)))

    def test_two_equal_valid_relations_fail_closed(self):
        x=self.blocks[2][0]
        tags=m.parent.nearest(x.public)[0]
        links=tuple(m.RelationLink(x.public.source_codes[t],m.ROLE_LINK,
                                   x.public.requested_code) for t in tags)
        self.assertIsNone(m.choose_after_ledger(x.public,links))

    def test_only_single_sign_is_different_for_positive_negative(self):
        for b in self.blocks:
            for x in b:
                diff=[i for i,(pos,neg) in enumerate(zip(
                  x.positive_values,x.negative_values)) if pos!=neg]
                self.assertEqual(diff,
                    [x.public.observation_order.index(x.true_tag)])

    def test_no_gold_or_source_case_field_in_policy_signature(self):
        self.assertEqual(tuple(inspect.signature(m.conditional).parameters),
                         ("meta","read"))
        self.assertEqual(tuple(inspect.signature(m.always_query).parameters),
                         ("meta","read"))
        self.assertNotIn("true_tag",
            tuple(x.name for x in dataclasses.fields(m.parent.Public)))
        self.assertNotIn("case_id",
            tuple(x.name for x in dataclasses.fields(m.parent.Public)))

    def test_no_query_ablation_never_spends_money(self):
        for b in self.blocks:
            score=m.assess(b,m.no_query)
            self.assertEqual(score["queries"],0)

    def test_always_query_ablation_spends_on_all_even_unique(self):
        for b in self.blocks:
            score=m.assess(b,m.always_query)
            self.assertEqual(score["queries"],48)

    def test_forced_choice_misses_half_identical_twins(self):
        for b in self.blocks[2:]:
            score=m.assess(b,m.forced)
            self.assertEqual((score["correct"],score["wrong"],
                              score["abstained"],score["queries"]),(24,24,0,0))

    def test_full_public_result_preserves_negative_and_costed_controls(self):
        z=m.evaluate("a"*40)
        self.assertEqual(z["new_public_pairs"],192)
        self.assertEqual(z["accepted_ref_mutations"],0)
        self.assertFalse(z["learned_or_general_scientific_superiority"])
        self.assertFalse(z["original_scientific_first_use"])
        self.assertFalse(z["independently_scientifically_accepted"])
        self.assertEqual(z["native_original_dispatches"],0)
        self.assertEqual(z["codex_calls"],0)
        self.assertEqual(z["totals_by_arm"]["conditional_one_query"],
             {"correct":144,"wrong":0,"abstained":48,"queries":96,"utility":115.2})
        self.assertEqual(z["totals_by_arm"]["no_query_certificate"]["utility"],86.4)
        self.assertEqual(z["totals_by_arm"]["always_query"]["utility"],91.2)
        self.assertEqual(z["totals_by_arm"]["forced_public_role_tie"]["utility"],-48)
        for b in z["outcome_by_cohort"]:
            self.assertEqual(b["pairs"],48)
            for name,arm in b["policies"].items():
                self.assertEqual(arm["total"],48)
                self.assertEqual(len(arm["rows"]),48)
                self.assertEqual(arm["correct"]+arm["wrong"]+arm["abstained"],48)
                self.assertLessEqual(arm["queries"],48)

if __name__=="__main__":
    unittest.main()

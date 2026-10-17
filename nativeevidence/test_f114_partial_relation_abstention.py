"""F114: precode identity, one-read selective safety, and impossibility twins."""
import dataclasses
import inspect
import sys
import unittest
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f114_partial_relation_abstention as m

class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cohorts=m.groups()

    def test_exact_precode_git_blob_and_parent_model(self):
        cfg,h=m.freeze()
        self.assertEqual(m.gitblob(m.normalized(m.FREEZE)),m.FREEZE_BLOB)
        self.assertEqual(len(h),64)
        self.assertEqual(cfg["cohorts"][0]["seeds"],[69600,69647])

    def test_three_fresh_disjoint_cohorts(self):
        ids=[p.case_id for g in self.cohorts for p in g]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(ids),144)
        self.assertEqual([len(g) for g in self.cohorts],[48]*3)

    def test_unique_cohort_nearest_singleton_no_exact_match(self):
        for c in self.cohorts[0]:
            tags,dist=m.nearest(c.public)
            self.assertEqual(dist,1)
            self.assertEqual(tags,(c.true_tag,))
            self.assertNotIn(c.public.requested_code,c.public.source_codes)

    def test_witnessed_tie_has_two_nearest_and_one_matching_role(self):
        for c in self.cohorts[1]:
            tags,dist=m.nearest(c.public)
            self.assertEqual((len(tags),dist),(2,1))
            match=[tag for tag in tags
                   if c.public.source_roles[tag]==c.public.query_role]
            self.assertEqual(match,[c.true_tag])

    def test_irresolvable_twin_metadata_identical_without_label(self):
        for i in range(0,48,2):
            a,b=self.cohorts[2][i:i+2]
            self.assertEqual(a.public,b.public)
            self.assertNotEqual(a.true_tag,b.true_tag)
            tags,dist=m.nearest(a.public)
            self.assertEqual((len(tags),dist),(2,1))
            self.assertTrue(all(a.public.source_roles[t]==a.public.query_role
                                for t in tags))
            self.assertEqual(m.certificate(a.public),None)

    def test_query_depth_and_true_tag_balanced_in_resolvable(self):
        for g in self.cohorts[:2]:
            x=Counter((p.public.query_depth,p.true_tag) for p in g)
            self.assertEqual(len(x),16)
            self.assertEqual(set(x.values()),{3})

    def test_all_pairs_differ_in_exactly_one_hidden_sign(self):
        for g in self.cohorts:
            for p in g:
                changed=[i for i,(a,b) in enumerate(zip(
                    p.positive_values,p.negative_values)) if a!=b]
                self.assertEqual(changed,
                    [p.public.observation_order.index(p.true_tag)])
                self.assertEqual((p.positive_values[changed[0]],
                                  p.negative_values[changed[0]]),(1.,-1.))

    def test_public_view_has_no_gold_seed_label_or_evidence_value(self):
        fields={f.name for f in dataclasses.fields(m.Public)}
        self.assertEqual(fields,{"requested_code","source_codes",
                       "source_roles","query_role","observation_order",
                       "query_depth"})
        for name in ("certificate","forced_string","forced_relation"):
            self.assertEqual(tuple(inspect.signature(getattr(m,name)).parameters),
                             ("meta",))

    def test_certificate_unique_or_witness_coverage_and_zero_ambiguous(self):
        for i,g in enumerate(self.cohorts):
            choices=[m.certificate(x.public) for x in g]
            self.assertEqual(sum(x is not None for x in choices),
                             0 if i==2 else 48)
            if i<2:self.assertEqual(choices,[x.true_tag for x in g])

    def test_identical_public_twins_force_at_most_half_correct(self):
        for fn in (m.forced_string,m.forced_relation):
            vals=[m.assess(g,fn) for g in self.cohorts]
            self.assertEqual(vals[2]["correct"],24)
            self.assertEqual(vals[2]["wrong"],24)
            self.assertEqual(vals[2]["coverage"],48)

    def test_disallowed_seeds_fail_without_dataset_reuse(self):
        for seed,cohort in ((69599,0),(69648,0),(69700,0),(69900,2)):
            with self.assertRaises(m.Invalid):
                m.case(seed,cohort)

    def test_parent_model_receives_zero_evidence_and_no_target(self):
        old=m.f112.LearnedRelationAttention().train(m.f112.wing_cohorts()[0])
        for public in (self.cohorts[2][0].public,self.cohorts[2][1].public):
            self.assertEqual(m.parent_learned(public,old),
                             m.parent_learned(public,old))
        self.assertEqual(self.cohorts[2][0].public,self.cohorts[2][1].public)

    def test_full_report_separates_proven_safety_from_science(self):
        result=m.evaluate("a"*40)
        self.assertEqual(result["public_pairs"],144)
        self.assertEqual(result["certificate_resolvable_covered"],96)
        self.assertEqual(result["certificate_unresolvable_abstained"],48)
        self.assertEqual(result["certificate_covered_wrong"],0)
        self.assertEqual(result["irresolvable_forced_correct"],24)
        self.assertTrue(result["public_selective_retrieval_screen_passed"])
        self.assertFalse(result["learned_superiority_claimed"])
        self.assertFalse(result["independent_scientific_acceptance"])
        self.assertFalse(result["protected_first_use_authorized"])
        self.assertEqual(result["accepted_ref_mutations"],0)
        self.assertEqual(result["codex_calls"],0)
        self.assertEqual(len(result["cohorts"]),3)
        for block in result["cohorts"]:
            for name,row in block["policies"].items():
                self.assertEqual(row["coverage"]+row["abstained"],48)
                self.assertEqual(row["correct"]+row["wrong"],row["coverage"])
                self.assertEqual(len(row["cases"]),48)

if __name__=="__main__": unittest.main()

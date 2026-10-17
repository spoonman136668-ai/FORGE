"""Adverse unit tests for F99-O; all fixture rows are synthetic, NOT science."""
import hashlib
import unittest

import f99o_answer_blind_capacity as m

KB = ['Film A|has actor|Actor B', 'Actor B|born in|Place C',
      'Place C|located in|Region D']
QA2 = ['Who belongs to [Film A]?\tActor B', 'From [Actor B], where?\tPlace C']
QA3 = ['Where is [Film A] ultimately?\tRegion D']


class CapacityTests(unittest.TestCase):
    def result(self, kb=KB, qa2=QA2, qa3=QA3):
        return m.assess(kb, qa2, qa3, denominator2=2, denominator3=1)

    def test_complete_cohorts_not_predictions(self):
        r = self.result()
        self.assertEqual(r['two_hop']['complete_population'], 2)
        self.assertEqual(r['three_hop']['complete_population'], 1)
        self.assertEqual(r['three_hop']['fully_bounded_without_role_query'], 1)
        self.assertEqual(r['source_graph']['unique_source_triples'], 3)
        self.assertFalse(r['source_git_objects_authentic'])
        for field in ('f95_accuracy_computed', 'independent_scientific_firstuse',
                      'dream_pareto_promotion', 'thetaevolve_accepted_training',
                      'accepted_ref_mutation', 'science_dispatch_authorized'):
            self.assertFalse(r[field], field)

    def test_changed_answer_fields_cannot_change_report(self):
        original = self.result()
        altered = self.result(qa2=['Who belongs to [Film A]?\tWRONG',
                                      'From [Actor B], where?\tMANY|UNRELATED'],
                              qa3=['Where is [Film A] ultimately?\tNOISE'])
        self.assertEqual(original, altered)

    def test_graph_and_question_order_invariant(self):
        r1 = self.result()
        r2 = self.result(kb=list(reversed(KB)), qa2=list(reversed(QA2)))
        self.assertEqual(r1, r2)

    def test_bidirectional_and_two_vs_three_depth(self):
        g, nodes, _ = m.build_graph(KB)
        self.assertEqual(m.envelope('Film A', 2, g), 'bounded')
        self.assertEqual(m.envelope('Region D', 3, g), 'bounded')
        self.assertIn('Film A', nodes)
        self.assertEqual(len(g['Region D']), 1)

    def test_budget_overflow_refuses_not_truncates(self):
        kb = [f'center|role|leaf{i}' for i in range(129)]
        graph, _, _ = m.build_graph(kb)
        self.assertEqual(m.envelope('center', 2, graph), 'over_budget')
        self.assertEqual(m.envelope('center', 3, graph), 'over_budget')

    def test_missing_root_not_silently_excluded(self):
        result = self.result(qa2=['Why [missing]?\tA', 'Why [Actor B]?\tB'])
        self.assertEqual(result['two_hop']['topic_root_missing'], 1)
        self.assertEqual(result['two_hop']['complete_population'], 2)

    def test_duplicates_counted_and_denominator_preserved(self):
        result = self.result(qa2=[QA2[0], QA2[0]])
        self.assertEqual(result['two_hop']['duplicate_question_text_rows'], 1)
        self.assertEqual(result['two_hop']['complete_population'], 2)
        g, _, d = m.build_graph(KB + [KB[0]])
        self.assertIn('Film A', g)
        self.assertEqual(d['duplicate_source_rows_retained_in_denominator'], 1)

    def test_case_sensitive_distinct_opaque_ids(self):
        used = {}
        k1 = m.canonical('Name With Spaces', 'entity', used)
        k2 = m.canonical('name with spaces', 'entity', used)
        k3 = m.canonical('Name With Spaces', 'forward', used)
        self.assertEqual(len({k1, k2, k3}), 3)
        self.assertTrue(all(m.IDENTIFIER.fullmatch(x) for x in (k1, k2, k3)))
        with self.assertRaises(m.CapacityError):
            used[k1] = 'other'
            m.canonical('Name With Spaces', 'entity', used)

    def test_denominator_and_malformed_inputs_fail_closed(self):
        for kb, qa2, qa3 in [
            ([], QA2, QA3), (['bad|line'], QA2, QA3),
            (KB, ['bad no tab', QA2[1]], QA3),
            (KB, ['two [A] and [B]?\tx', QA2[1]], QA3),
            (KB, [QA2[0], 'missing [bad]?\t'], QA3),
        ]:
            with self.assertRaises(m.CapacityError):
                self.result(kb=kb, qa2=qa2, qa3=qa3)
        with self.assertRaises(m.CapacityError):
            m.assess(KB, QA2, QA3, denominator2=1, denominator3=1)

    def test_raw_git_blob_hash_detects_worktree_drift(self):
        raw = b'a|b|c\n'
        expected = hashlib.sha1(b'blob 6\x00' + raw).hexdigest()
        self.assertEqual(m.git_blob(raw), expected)
        self.assertNotEqual(m.git_blob(raw + b'x'), expected)

    def test_no_arbitrary_depth_or_budget_relaxation(self):
        g, _, _ = m.build_graph(KB)
        with self.assertRaises(m.CapacityError):
            m.envelope('Film A', 4, g)
        with self.assertRaises(m.CapacityError):
            m.envelope('Film A', 3, g, cap=129)


if __name__ == '__main__':
    unittest.main()

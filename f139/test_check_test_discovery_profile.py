"""Profiling must retain the serial unittest inventory, failures and skips."""
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import check_test_discovery_inventory as profile


def example_suite():
    class Cases(unittest.TestCase):
        def test_first(self):
            self.assertEqual(2 + 2, 4)

        @unittest.skip('fixture-only platform skip')
        def test_second(self):
            self.fail('must retain the declared skip')
    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


class ProfileTests(unittest.TestCase):
    def test_all_cases_in_original_order_with_real_skip(self):
        suite=example_suite()
        expected=profile.case_ids(suite)
        result=profile.profile_suite(suite, expected, stream=io.StringIO())
        self.assertTrue(result['successful'])
        self.assertTrue(result['complete_inventory_and_order'])
        self.assertEqual([row['id'] for row in result['cases']], expected)
        self.assertEqual(result['tests_run'], 2)
        self.assertEqual(result['skipped_ids'], [expected[1]])
        self.assertEqual([row['outcome'] for row in result['cases']], ['success', 'skipped'])
        self.assertEqual(sum(row['cases'] for row in result['modules']), 2)

    def test_missing_reordered_or_duplicate_inventory_never_executes(self):
        for kind in ('missing', 'reordered', 'duplicate'):
            suite=example_suite()
            ids=profile.case_ids(suite)
            expected={'missing': ids[:1], 'reordered': list(reversed(ids)),
                      'duplicate': ids+[ids[0]]}[kind]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                profile.profile_suite(suite, expected, stream=io.StringIO())

    def test_subtest_failure_is_not_hidden_by_timing(self):
        class Cases(unittest.TestCase):
            def test_case(self):
                with self.subTest(control='negative'):
                    self.assertEqual(1, 2)
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
        result=profile.profile_suite(suite, profile.case_ids(suite), stream=io.StringIO())
        self.assertFalse(result['successful'])
        self.assertEqual(result['failures'], 1)
        self.assertEqual(result['cases'][0]['outcome'], 'subtest_failure')

    def test_class_fixture_failure_keeps_incomplete_coverage_and_error(self):
        class Cases(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError('fixture negative control')
            def test_case(self):
                self.fail('must not execute')
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
        result=profile.profile_suite(suite, profile.case_ids(suite), stream=io.StringIO())
        self.assertFalse(result['successful'])
        self.assertFalse(result['complete_inventory_and_order'])
        self.assertEqual(result['errors'], 1)
        self.assertEqual(result['tests_run'], 0)

    def test_wrong_exact_source_rejected_before_discovery_or_output(self):
        with patch.dict(profile.os.environ, {'GITHUB_ACTIONS':'true',
                'GITHUB_REPOSITORY':'spoonman136668-ai/FORGE'}), \
             patch.object(profile, 'git', return_value=b'a'*40), \
             patch.object(profile, 'collect') as collect:
            with self.assertRaises(ValueError):
                profile.profile_current('.', SimpleNamespace(expected_source='b'*40))
            collect.assert_not_called()

    def test_historical_inventory_controls_remain_fail_closed(self):
        good={'ids':['a','b'], 'skipped':['b']}
        profile.compare(good, good)
        for changed in ({'ids':['a'], 'skipped':['b']},
                        {'ids':['a','b','b'], 'skipped':['b']},
                        {'ids':['a','b'], 'skipped':[]}):
            with self.assertRaises(ValueError):
                profile.compare(good, changed)


if __name__ == '__main__':
    unittest.main()

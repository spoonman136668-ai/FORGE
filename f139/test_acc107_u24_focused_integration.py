"""ACC-107: run research U24 focused tests in existing cross-platform f139 CI.

This is a regression integration only: no scientific first-use, no research
dispatch, no native learner acceptance, and no TEST-cohort access.
"""
from __future__ import annotations

import io
import pathlib
import sys
import unittest


class ACC107U24FocusedIntegration(unittest.TestCase):
    def test_all_u24_sourcefree_contracts(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        directory = root / "research" / "acc95_u24"
        self.assertTrue(directory.is_dir(), "ACC107_SOURCE_DIRECTORY_MISSING")
        expected = {
            "test_fitdev.py", "test_switching.py", "test_ewma.py",
            "test_local_cells.py", "test_interacting_cells.py",
        }
        actual = {path.name for path in directory.glob("test_*.py")}
        self.assertEqual(actual, expected, "ACC107_TEST_MODULE_COVERAGE_DRIFT")
        sys.path.insert(0, str(directory))
        try:
            suite = unittest.defaultTestLoader.discover(
                str(directory), pattern="test_*.py", top_level_dir=str(directory)
            )
            self.assertGreaterEqual(suite.countTestCases(), 20,
                                    "ACC107_TEST_CASE_COUNT_DRIFT")
            output = io.StringIO()
            result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
            self.assertTrue(result.wasSuccessful(),
                            "ACC107_FOCUSED_U24_FAILED:\n" + output.getvalue())
            self.assertEqual(result.testsRun, suite.countTestCases())
        finally:
            sys.path.remove(str(directory))

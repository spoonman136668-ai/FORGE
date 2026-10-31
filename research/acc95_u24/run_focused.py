"""ACC-106 focused offline entrypoint for existing qualification runners.

Run: python -B research/acc95_u24/run_focused.py
No networking, external data, protected TEST cohort or scientific admission.
Exit nonzero unless every discovered research-specific test succeeds.
"""
from __future__ import annotations
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
EXPECTED = {
    "test_fitdev.py",
    "test_switching.py",
    "test_ewma.py",
    "test_local_cells.py",
    "test_interacting_cells.py",
}
if __name__ == "__main__":
    actual = {p.name for p in HERE.glob("test_*.py")}
    if actual != EXPECTED:
        raise SystemExit(f"FOCUSED_TEST_DISCOVERY_DRIFT: missing={sorted(EXPECTED-actual)} unexpected={sorted(actual-EXPECTED)}")
    sys.path.insert(0, str(HERE))
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py",
                                                 top_level_dir=str(HERE))
    count = suite.countTestCases()
    if count < 20:
        raise SystemExit(f"FOCUSED_TEST_CASE_COVERAGE_DRIFT:{count}")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("FOCUSED_TESTS_FAIL")
    print(f"ACC106_FOCUSED_TESTS_PASS:{result.testsRun}")

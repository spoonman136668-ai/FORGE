"""Regression and leakage negatives for original-owner failure classification."""
from __future__ import annotations

import inspect
import unittest

from f139.local_controller import F139Error, run_once
from f139.nci04_model_free_failure import (
    SAFE_CODES, classify_model_free_failure,
)


class ModelFreeFailureCodeTests(unittest.TestCase):
    def test_frozen_owner_failure_identifies_real_gate(self):
        self.assertEqual(
            classify_model_free_failure(
                F139Error("F139_G3_ORIGINAL_RUNNING_TASK_OR_PROCESS_DRIFT")),
            "F139_G3_ORIGINAL_RUNNING_TASK_OR_PROCESS_DRIFT")
        self.assertEqual(
            classify_model_free_failure(ValueError(
                "F139_OWNER_MODEL_NEGATIVE_HISTORY_TOO_LARGE")),
            "F139_OWNER_MODEL_NEGATIVE_HISTORY_TOO_LARGE")
        self.assertEqual(
            classify_model_free_failure(ValueError(
                "F139_GENENV_RELEASE_NOT_BOUND")),
            "F139_GENENV_RELEASE_NOT_BOUND")

    def test_known_source_and_api_errors_remain_discriminable(self):
        for code in ("F139_MODEL_FREE_SEARCH_FROZEN_SOURCE_DRIFT",
                     "F139_GITHUB_API_FAILED",
                     "F139_GITHUB_API_RESPONSE_TOO_LARGE"):
            with self.subTest(code=code):
                self.assertEqual(classify_model_free_failure(F139Error(code)), code)

    def test_unguarded_text_cannot_escape_even_if_code_shaped(self):
        for message in (
            "password=C:\\Sensitive\\secrets.env",
            "F139_OWNER_MODEL_PASSWORD_TOKEN",
            "F139_GITHUB_API_FAILED token=secret",
            "https://api.github.com/secret?token=abc",
            "F139_GENENV_UNREVIEWED_BOUNDARY",
        ):
            with self.subTest(message=message):
                code = classify_model_free_failure(ValueError(message))
                self.assertEqual(code, "UNCLASSIFIED_VALUE_ERROR")
                self.assertNotIn("secret", code.lower())
                self.assertNotIn("token", code.lower())

    def test_os_error_paths_never_printed(self):
        code = classify_model_free_failure(
            OSError("sensitive C:\\Users\\private\\state.sqlite"))
        self.assertEqual(code, "OS_ERROR_NO_DETAILS")

    def test_codes_are_fixed_data_only(self):
        self.assertTrue(SAFE_CODES)
        self.assertTrue(all(isinstance(x, str) and x.startswith("F139_")
                            and x.upper() == x and " " not in x
                            for x in SAFE_CODES))
        self.assertEqual(classify_model_free_failure(Exception("hidden")),
                         "UNCLASSIFIED_FAILURE")

    def test_natural_owner_keeps_existing_fail_closed_boundary(self):
        source = inspect.getsource(run_once)
        self.assertIn("except (F139Error, ValueError, OSError) as exc:", source)
        self.assertIn('"disposition": "MODEL_FREE_SEARCH_BLOCKED_FAIL_CLOSED"', source)
        self.assertIn('"failure_code": classify_model_free_failure(exc)', source)
        self.assertIn('"worker_dispatched": False', source)
        self.assertIn('"paid_model_calls": 0', source)
        self.assertLess(
            source.index("for active_record in db.actives():"),
            source.index('from f139.nci04_model_free_failure import'))


if __name__ == "__main__":
    unittest.main()

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

    def test_reviewed_denial_reasons_are_exact_source_literals(self):
        from pathlib import Path
        from f139.nci04_model_free_failure import AUDITED_REASON_CODES
        root = Path(__file__).resolve().parent.parent
        groups = {
            "f139/nci04_model_owner_publication.py": ("F139_MODEL_DRAFT_", ["ATTEMPT_DUPLICATE_OR_DRIFT","ATTEMPT_FIELDS_INVALID","BRANCH_SCOPE_INVALID","COMMIT_RESPONSE_AMBIGUOUS_NO_RETRY","COMPILED_PROPOSAL_DRIFT","EXACT_ONE_FILE_COMMIT_REQUIRED","FEEDER_CANDIDATE_DRIFT","HISTORICAL_EVENT_INVALID","ORIGINAL_ATTEMPT_CUSTODY_MOVED","ORIGINAL_OWNER_WITNESS_REQUIRED","ORIGINAL_WINDOWS_OWNER_REQUIRED","OWNER_DRAFT_NOT_AUTHENTICATED","PLAN_MOVED_BEFORE_CUSTODY","PREVIOUSLY_ATTEMPTED_NO_REPLAY","PREWRITE_ORIGINAL_LEDGER_MOVED","PR_ALREADY_PUBLISHED","PR_HISTORY_CHANGED","PR_HISTORY_INVALID","PR_HISTORY_ITEM_INVALID","PR_HISTORY_MOVED","PR_HISTORY_UNBOUNDED","PR_RESPONSE_AMBIGUOUS_NO_RETRY","REF_ALREADY_EXISTS","REF_RESPONSE_AMBIGUOUS_NO_RETRY","SOURCE_CHANGED_BEFORE_PUBLICATION","SUCCESS_FIELDS_INVALID","SUCCESS_ORPHAN_OR_DRIFT","UNRESOLVED_G3_REMOTE_WRITE","UNRESOLVED_REMOTE_WRITE_NO_RETRY"]),
            "f139/nci04_model_proposal.py": ("F139_MODEL_PROPOSAL_", ["DUPLICATE_JSON_KEY","PREVIOUSLY_CONSUMED_NO_REPLAY","REQUEST_HISTORY_INVALID","REQUEST_SOURCE_OR_HISTORY_INVALID","RESEARCH_TEXT_INVALID","RESPONSE_BINDING_DRIFT","RESPONSE_SCHEMA_INVALID","RESPONSE_SIZE_INVALID","SOURCE_INVALID","SOURCE_OR_HISTORY_INVALID","SOURCE_SIZE_OR_CHANGE_INVALID","TARGET_INVALID"]),
            "f139/nci04_prompt_program.py": ("F139_PROMPT_PROGRAM_", ["AMBIGUOUS_HISTORY_MARKER","CONSTANT_CAPACITY","CONSTANT_CHOICE","CONSUMED_IDENTITIES","CONTEXT_PINS","DEGENERATE_RATE","FIXED_CAPACITY_GRAMMAR","HISTORY_BYTES","HISTORY_SOURCE_BUDGET","HISTORY_SOURCE_DRIFT","PARENT_ELIGIBILITY","POPULATION_BUDGET","TEXT_REQUIRED","TYPED_EMBEDDING","TYPED_TOKEN"]),
            "f139/nci04_research_steering.py": ("F139_RESEARCH_STEERING_", ["ADMISSION_HISTORY_INVALID","DOCUMENT_IDENTITY_DRIFT","DOCUMENT_METADATA_INVALID","DOCUMENT_SCOPE_INVALID","PROVIDER_INVALID","RANK_INPUT_INVALID"]),
            "f139/nci04_model_owner_bridge.py": ("F139_OWNER_MODEL_", ["SESSION_INVALID","TARGET_SCOPE_INVALID"]),
        }
        actual = set()
        for path, (prefix, reasons) in groups.items():
            source = (root / path).read_text(encoding="utf-8")
            for reason in reasons:
                with self.subTest(path=path, reason=reason):
                    self.assertIn('"' + reason + '"', source)
                    actual.add(prefix + reason)
        self.assertEqual(actual, set(AUDITED_REASON_CODES))

    def test_exact_new_reasons_classify_without_private_text(self):
        examples = (
            "F139_MODEL_DRAFT_PR_HISTORY_CHANGED",
            "F139_MODEL_DRAFT_UNRESOLVED_REMOTE_WRITE_NO_RETRY",
            "F139_MODEL_PROPOSAL_RESPONSE_BINDING_DRIFT",
            "F139_PROMPT_PROGRAM_HISTORY_SOURCE_DRIFT",
            "F139_RESEARCH_STEERING_DOCUMENT_IDENTITY_DRIFT",
            "F139_OWNER_MODEL_TARGET_SCOPE_INVALID",
        )
        for code in examples:
            with self.subTest(code=code):
                self.assertIn(code, SAFE_CODES)
                self.assertEqual(classify_model_free_failure(ValueError(code)), code)
        self.assertEqual(classify_model_free_failure(ValueError(
            "F139_MODEL_DRAFT_UNREVIEWED_SECRET_TOKEN")), "UNCLASSIFIED_VALUE_ERROR")

    def test_exact_module_and_class_stage_fallbacks(self):
        from f139.nci04_model_free_failure import AUDITED_TYPE_FALLBACK
        from f139.nci04_model_owner_publication import ModelDraftDenied
        from f139.nci04_model_proposal import ProposalDenied
        from f139.nci04_prompt_program import ProgramRejected
        from f139.nci04_research_steering import SteeringDenied
        from f139.nci04_portfolio_source_boundary import PortfolioSourceRejected
        from f139.nci04_genenv_owner_backend import BackendUnavailable
        from f139.nci04_autonomy_feed import NativeFeedDenied
        for cls in (ModelDraftDenied, ProposalDenied, ProgramRejected,
                    SteeringDenied, PortfolioSourceRejected,
                    BackendUnavailable, NativeFeedDenied):
            with self.subTest(cls=cls.__name__):
                key = (cls.__module__, cls.__qualname__)
                self.assertIn(key, AUDITED_TYPE_FALLBACK)
                result = classify_model_free_failure(cls("secret=not-for-logs"))
                self.assertEqual(result, AUDITED_TYPE_FALLBACK[key])
                self.assertIn(result, SAFE_CODES)
                self.assertNotIn("secret", result.lower())
        # A malicious class with the same name, but from a different module,
        # cannot impersonate a reviewed native denial class.
        Mimic = type("ModelDraftDenied", (ValueError,), {})
        self.assertEqual(classify_model_free_failure(Mimic("secret/path")),
                         "UNCLASSIFIED_VALUE_ERROR")
        # Fixed stage labels cannot be forged with an untyped message alone.
        spoof = next(iter(AUDITED_TYPE_FALLBACK.values()))
        self.assertEqual(classify_model_free_failure(ValueError(spoof)),
                         "UNCLASSIFIED_VALUE_ERROR")

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

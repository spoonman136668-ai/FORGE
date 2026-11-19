"""No-provider, no-owner-write negatives for sanitized model-free log telemetry."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from f139.nci04_model_free_log_summary import (
    DISPOSITION, FALLBACK_CODES, MAX_TAIL_LINES, OTHER, SCHEMA,
    main, summarize_model_free_log,
)


def blocked(code):
    return json.dumps({"disposition": DISPOSITION, "failure_code": code}) + "\n"


class ModelFreeLogSummaryTests(unittest.TestCase):
    def test_allowlisted_code_and_fallback_are_counted_only(self):
        lines = [blocked("F139_GENENV_RELEASE_NOT_BOUND"),
                 blocked("OS_ERROR_NO_DETAILS"),
                 blocked("F139_GENENV_RELEASE_NOT_BOUND")]
        result = summarize_model_free_log(lines)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["observed_blocked"], 3)
        self.assertEqual(result["last_code"], "F139_GENENV_RELEASE_NOT_BOUND")
        self.assertEqual(result["code_counts"], {
            "F139_GENENV_RELEASE_NOT_BOUND": 2,
            "OS_ERROR_NO_DETAILS": 1,
        })

    def test_disallowed_error_message_and_secret_are_not_emitted(self):
        raw = "password=C:\\Private\\secret.txt ghp_123456"
        lines = [blocked(raw), blocked("F139_GITHUB_API_FAILED token=secret")]
        payload = json.dumps(summarize_model_free_log(lines))
        self.assertEqual(json.loads(payload)["code_counts"], {OTHER: 2})
        for secret in ("password", "Private", "ghp_", "token=", "secret"):
            self.assertNotIn(secret, payload)

    def test_unknown_code_even_if_f139_prefixed_remains_redacted(self):
        result = summarize_model_free_log([blocked("F139_NEW_UNREVIEWED_CODE")])
        self.assertEqual(result["last_code"], OTHER)

    def test_no_classification_in_unrelated_logs(self):
        lines = [json.dumps({"disposition": "PASS", "failure_code":
                             "F139_GITHUB_API_FAILED"}) + "\n",
                 "other tool output\n"]
        result = summarize_model_free_log(lines)
        self.assertEqual(result["observed_blocked"], 0)
        self.assertIsNone(result["last_code"])
        self.assertEqual(result["code_counts"], {})

    def test_missing_code_is_not_mistaken_for_known_failure(self):
        result = summarize_model_free_log([json.dumps({"disposition": DISPOSITION})])
        self.assertEqual(result["code_counts"], {OTHER: 1})

    def test_malformed_and_duplicate_json_keys_are_ignored(self):
        line = '{"disposition":"' + DISPOSITION + '","failure_code":"F139_GITHUB_API_FAILED","failure_code":"F139_GENENV_RELEASE_NOT_BOUND"}\n'
        result = summarize_model_free_log([line, "{broken", blocked("F139_GITHUB_API_FAILED")])
        self.assertEqual(result["code_counts"], {"F139_GITHUB_API_FAILED": 1})

    def test_oversized_json_is_dropped_without_echo(self):
        huge = json.dumps({"disposition": DISPOSITION,
                           "failure_code": "F139_GITHUB_API_FAILED",
                           "detail": "not-safe" * 18000}) + "\n"
        result = summarize_model_free_log([huge])
        self.assertEqual(result["observed_blocked"], 0)

    def test_last_two_thousand_lines_only(self):
        lines = [blocked("F139_GITHUB_API_FAILED")] + ["noise\n"] * MAX_TAIL_LINES
        self.assertEqual(summarize_model_free_log(lines)["observed_blocked"], 0)

    def test_nonstring_and_nonstring_failure_code_are_not_emitted(self):
        lines = [None, json.dumps({"disposition": DISPOSITION,
                    "failure_code": ["F139_GITHUB_API_FAILED"]}) + "\n"]
        self.assertEqual(summarize_model_free_log(lines)["code_counts"], {OTHER: 1})

    def test_all_classifier_fallback_codes_may_be_summarized(self):
        result = summarize_model_free_log(blocked(x) for x in sorted(FALLBACK_CODES))
        self.assertEqual(set(result["code_counts"]), FALLBACK_CODES)

    def test_cli_readonly_minimum_output_and_no_log_leak(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "controller.log"
            p.write_text(blocked("F139_GITHUB_API_FAILED") +
                         "password=top-secret\n", encoding="utf-8")
            before = p.read_bytes()
            capture = io.StringIO()
            with redirect_stdout(capture):
                self.assertEqual(main([str(p)]), 0)
            self.assertEqual(p.read_bytes(), before)
            output = capture.getvalue()
            self.assertTrue(output.startswith("F139_MODEL_FREE_LOG_SUMMARY="))
            self.assertNotIn("top-secret", output)
            self.assertEqual(json.loads(output.split("=", 1)[1])["last_code"],
                             "F139_GITHUB_API_FAILED")

    def test_cli_fail_closed_on_missing_and_wrong_arguments(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([]), 2)
            self.assertEqual(main(["/definitely/missing/f139.log"]), 2)
        self.assertNotIn("Traceback", out.getvalue())

    def test_cli_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "other.log"
            file.write_text(blocked("F139_GITHUB_API_FAILED"))
            link = Path(d) / "controller.log"
            try:
                link.symlink_to(file)
            except (NotImplementedError, OSError):
                self.skipTest("host does not support symlinks")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main([str(link)]), 2)
            self.assertNotIn("F139_GITHUB_API_FAILED", out.getvalue())


if __name__ == "__main__":
    unittest.main()

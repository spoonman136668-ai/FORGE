"""Q21 native resource instrumentation: source-only, no cohort or science access."""
from __future__ import annotations
import math
import unittest
from unittest import mock

import resource_meter as r


class NativeResourceQualification(unittest.TestCase):
    def test_native_process_peak_rss_is_positive(self):
        self.assertGreater(r.native_peak_rss_bytes(), 0)

    def test_real_process_io_has_required_keys(self):
        data = r.process_io_bytes()
        self.assertIn(data["measurement_source"],
                      ("windows_getprocessiocounters", "linux_proc_self_io"))
        self.assertGreaterEqual(data["read_transfer_bytes"], 0)
        self.assertGreaterEqual(data["write_transfer_bytes"], 0)

    def test_preflight_no_cohorts_or_science(self):
        receipt = r.preflight()
        self.assertFalse(receipt["scientific_first_use"])
        self.assertEqual(receipt["generated_development_cohorts"], 0)
        self.assertEqual(receipt["gate"], "RESOURCE_COUNTER_INSTRUMENTATION_ONLY")
        self.assertEqual(receipt["communication"]["wire_bytes"], 0)
        self.assertEqual(receipt["rss_scope"],
                         "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_STAGE")

    def test_real_native_snapshot_delta_is_finite(self):
        start = r.snapshot()
        stop = r.snapshot()
        delta = r.measured_delta(start, stop, "test_fixture")
        self.assertGreater(delta["process_peak_rss_bytes"], 0)
        self.assertGreaterEqual(delta["process_cpu_seconds"], 0)
        self.assertTrue(math.isfinite(delta["process_cpu_seconds"]))

    def test_mismatched_platform_and_stage_rejected(self):
        start = r.snapshot()
        stop = dict(start, platform="other")
        with self.assertRaisesRegex(r.ResourceUnavailable, "CROSS_PLATFORM"):
            r.measured_delta(start, stop, "test")
        with self.assertRaisesRegex(r.ResourceUnavailable, "STAGE_REQUIRED"):
            r.measured_delta(start, start, "")

    def test_nonmonotonic_cpu_rss_and_io_fail_closed(self):
        a = r.snapshot()
        with self.assertRaisesRegex(r.ResourceUnavailable, "CPU_COUNTER"):
            r.measured_delta(a, dict(a, process_cpu_ns=a["process_cpu_ns"]-1), "test")
        with self.assertRaisesRegex(r.ResourceUnavailable, "RSS_COUNTER"):
            r.measured_delta(a, dict(a, process_peak_rss_bytes=a["process_peak_rss_bytes"]-1), "test")
        old = dict(a["process_io"])
        new = dict(old, read_transfer_bytes=old["read_transfer_bytes"]-1)
        with self.assertRaisesRegex(r.ResourceUnavailable, "IO_COUNTER"):
            r.measured_delta(a, dict(a, process_io=new), "test")

    def test_serialization_bytes_are_exact_and_content_addressed(self):
        p = r.canonical_payload_size({"a": "é", "b": 2})
        self.assertEqual(p["serialized_bytes"], len('{"a":"é","b":2}'.encode("utf-8")))
        self.assertEqual(p, r.canonical_payload_size({"b": 2, "a": "é"}))
        self.assertEqual(len(p["serialized_sha256"]), 64)

    def test_nonfinite_and_unserializable_payloads_fail_closed(self):
        with self.assertRaisesRegex(r.ResourceUnavailable, "SERIALIZATION_FAILED"):
            r.canonical_payload_size({"bad": math.nan})
        with self.assertRaisesRegex(r.ResourceUnavailable, "SERIALIZATION_FAILED"):
            r.canonical_payload_size({"bad": object()})

    def test_zero_transport_requires_explicit_declaration(self):
        zero = r.communication_receipt("none")
        self.assertEqual(zero["wire_bytes"], 0)
        self.assertEqual(zero["adapter_bytes"], 0)
        with self.assertRaisesRegex(r.ResourceUnavailable, "NONE_TRANSPORT"):
            r.communication_receipt("none", wire_bytes=1)

    def test_external_transport_must_supply_nonnegative_integer_counters(self):
        good = r.communication_receipt("measured", wire_bytes=17, adapter_bytes=4)
        self.assertEqual((good["wire_bytes"], good["adapter_bytes"]), (17, 4))
        for kwargs in ({"wire_bytes": None, "adapter_bytes": 0},
                       {"wire_bytes": 1.5, "adapter_bytes": 3},
                       {"wire_bytes": 1, "adapter_bytes": -1}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(r.ResourceUnavailable, "COMMUNICATION_BYTES_MISSING"):
                    r.communication_receipt("measured", **kwargs)

    def test_platform_reader_failures_are_hard_failures(self):
        with mock.patch.object(r.sys, "platform", "unsupported_q21_platform"):
            with self.assertRaisesRegex(r.ResourceUnavailable, "NATIVE_RSS_UNSUPPORTED"):
                r.native_peak_rss_bytes()
            with self.assertRaisesRegex(r.ResourceUnavailable, "NATIVE_IO_UNSUPPORTED"):
                r.process_io_bytes()

    def test_no_execution_or_original_source_imports(self):
        import ast
        from pathlib import Path
        tree = ast.parse(Path(r.__file__).read_text(encoding="utf-8"))
        allowed_import_roots = {"__future__", "ctypes", "json", "os",
                                "platform", "sys", "time", "resource",
                                "hashlib", "argparse"}
        blocked_call_names = {"dispatch", "Popen", "exec", "eval",
                              "compile", "__import__"}
        blocked_module_calls = {("os", "system"), ("os", "popen"),
                                ("subprocess", "run"), ("subprocess", "Popen")}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed_import_roots)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0],
                              allowed_import_roots)
            elif isinstance(node, ast.Call):
                called = node.func
                if isinstance(called, ast.Name):
                    self.assertNotIn(called.id, blocked_call_names)
                elif isinstance(called, ast.Attribute):
                    owner = called.value.id if isinstance(called.value, ast.Name) else ""
                    self.assertNotIn((owner, called.attr), blocked_module_calls)
                    self.assertNotEqual(called.attr, "dispatch")

if __name__ == "__main__":
    unittest.main()

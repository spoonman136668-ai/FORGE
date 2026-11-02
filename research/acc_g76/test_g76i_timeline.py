"""Offline contract tests for G76 diagnostic trace; no GPU qualification."""
import unittest
from g76i_timeline import necessary_removable_fraction, validate_trace, SCHEMA

class Contract(unittest.TestCase):
    def test_schema(self):
        self.assertEqual(SCHEMA, "forge.acc.g76i.cuda-timeline.v1")
    def test_minimum_fraction(self):
        self.assertAlmostEqual(necessary_removable_fraction(), 1 - 1 / 1.15)
    def test_bad_target(self):
        for value in (1.0, 0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                necessary_removable_fraction(value)
    def test_bad_trace(self):
        for value in (None, {}, {"traceEvents": {}}, []):
            with self.assertRaises(ValueError):
                validate_trace(value)
    def test_trace_counts_no_overhead_claim(self):
        result = validate_trace({"traceEvents": [
            {"ph":"X","cat":"cpu_op"},{"ph":"X","cat":"kernel"},
            {"ph":"X","cat":"cuda_runtime"}]})
        self.assertEqual(result["cpu_events"], 1)
        self.assertEqual(result["kernel_events"], 1)
        self.assertEqual(result["cuda_runtime_events"], 1)
        self.assertEqual(result["launch_overhead_fraction"], "UNMEASURED")
        self.assertEqual(result["speedup"], "UNMEASURED")

if __name__ == "__main__":
    unittest.main()

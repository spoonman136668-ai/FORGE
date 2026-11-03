"""G100 original-model harness contracts, without loading model or protected data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import g100_development_original as harness
from g100_stream_manifest import ARMS


class G100HarnessTests(unittest.TestCase):
    def test_arms_and_frozen_thresholds(self):
        self.assertEqual(ARMS, ("no_cache", "lru", "g97_overflow_bypass", "g100_deferred_first_use"))
        self.assertEqual(harness.STRATA, ("round_robin", "bursty", "mixed", "overflow"))
        self.assertEqual(harness.REPETITIONS, 4)
        self.assertEqual(harness.BYTE_LIMIT, 86114304)

    def test_paired_metric_identity_no_inference(self):
        def rep():
            return {"rows": [{"request_wall_ns": 1000} for _ in range(48)],
                    "wall_ns": 48000, "cpu_ns": 40000, "max_rss": 300000,
                    "max_resident_kv_bytes": 0, "hits": 0, "misses": 48,
                    "evictions": 0, "bypasses": 48}
        metric = harness.evaluate([rep() for _ in range(4)], [rep() for _ in range(4)], 8)
        self.assertEqual(metric["throughput_speedup"], 1.0)
        self.assertEqual(metric["minimum_paired_request_speedup"], 1.0)
        self.assertEqual(metric["p95_latency_ratio"], 1.0)
        self.assertEqual(metric["cpu_ratio"], 1.0)
        self.assertEqual(metric["rss_ratio"], 1.0)
        self.assertEqual(metric["max_resident_kv_bytes"], 0)

    def test_partial_or_inconsistent_request_counts_fail_closed(self):
        rep = {"rows": [{"request_wall_ns": 1000} for _ in range(47)]}
        with self.assertRaisesRegex(RuntimeError, "PAIRED_REQUEST_COUNT_DRIFT"):
            harness.evaluate([rep] * 4, [rep] * 4, 8)


if __name__ == "__main__":
    unittest.main()

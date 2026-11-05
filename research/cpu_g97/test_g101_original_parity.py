"""Model-free G101 parity-harness guard tests; no original GPT-2 loads."""
import unittest
from research.cpu_g97.g101_original_parity import (
    PATTERN, check_pattern, verify_forward_calls, kv_comparison)


class Prefix:
    shape = (1, 5)


class Suffix:
    shape = (1, 3)


class TestG101ParityGuard(unittest.TestCase):
    def test_coverage_is_frozen_with_eviction_and_hits(self):
        info = check_pattern()
        self.assertEqual(info["requests"], 10)
        self.assertEqual(info["expected_hits"] + info["expected_misses"], 10)
        self.assertGreaterEqual(info["expected_evictions"], 2)
        with self.assertRaisesRegex(RuntimeError, "PATTERN_DRIFT"):
            check_pattern(PATTERN[:-1] + (0,))

    def test_exact_first_forward_and_no_extra_model_calls(self):
        stream = [{"prefix_id": 0, "suffix": Suffix()}] * 2
        prefixes = [Prefix()]
        calls = [
            {"tokens": 8, "has_past": False},
            {"tokens": 1, "has_past": True},
            {"tokens": 3, "has_past": True},
            {"tokens": 1, "has_past": True},
        ]
        self.assertTrue(verify_forward_calls(calls, stream, prefixes, 2, [False, True]))
        with self.assertRaisesRegex(RuntimeError, "EXTRA_MODEL_FORWARD"):
            verify_forward_calls(calls + [calls[-1]], stream, prefixes, 2, [False, True])
        wrong = [dict(x) for x in calls]
        wrong[2] = {"tokens": 5, "has_past": False}
        with self.assertRaisesRegex(RuntimeError, "WRONG_FIRST_FORWARD"):
            verify_forward_calls(wrong, stream, prefixes, 2, [False, True])

    def test_forward_count_and_invalid_cached_decode_rejected(self):
        stream = [{"prefix_id": 0, "suffix": Suffix()}]
        good = [{"tokens": 8, "has_past": False},
                {"tokens": 1, "has_past": True},
                {"tokens": 1, "has_past": True}]
        self.assertTrue(verify_forward_calls(good, stream, [Prefix()], 3, [False]))
        altered = list(good)
        altered[2] = {"tokens": 2, "has_past": True}
        with self.assertRaisesRegex(RuntimeError, "EXTRA_PREFIX_FORWARD"):
            verify_forward_calls(altered, stream, [Prefix()], 3, [False])


if __name__ == "__main__":
    unittest.main()

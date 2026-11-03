"""G100 isolated model-free development tests; never invoke original GPT-2."""
import unittest
from research.cpu_g97.g100_deferred_admission import DeferredFirstAdmissionCache, replay
from research.cpu_g97.g97_overflow_bypass import OverflowBypassCache
from research.cpu_g96.g96_admission import BYTE_LIMIT

class G100Tests(unittest.TestCase):
    def test_first_use_deferred_then_admitted_then_hit(self):
        cache = DeferredFirstAdmissionCache()
        built = []
        def make():
            built.append(1)
            return {"past": "immutable"}
        self.assertEqual(cache.request("A", 1, make), (None, False, False))
        self.assertEqual(len(built), 0)
        self.assertEqual(cache.seen["A"], 1)
        self.assertEqual(cache.request("A", 1, make)[1:], (False, True))
        self.assertEqual(cache.request("A", 1, make)[1:], (True, False))
        self.assertEqual(len(built), 1)
        self.assertEqual((cache.misses, cache.hits, cache.admissions, cache.bypasses), (2, 1, 1, 1))

    def test_all_unique_never_build_and_overflow_is_preserved(self):
        cache = DeferredFirstAdmissionCache()
        def forbidden():
            raise AssertionError("UNEXPECTED_BUILD")
        for i in range(32):
            self.assertEqual(cache.request("cold-%d" % i, 1, forbidden), (None, False, False))
        self.assertEqual(cache.admissions, 0)
        self.assertEqual(cache.bypasses, 32)
        self.assertTrue(cache.overflow)
        self.assertEqual(cache.decision_count, 32)

    def test_invalid_inputs_fail_before_state_mutation(self):
        cache = DeferredFirstAdmissionCache()
        for key, size in (("", 1), ("x", -1), (None, 1), ("x", 1.5)):
            with self.assertRaises(ValueError):
                cache.request(key, size, lambda: 1)
        self.assertEqual((cache.clock, cache.decision_count, len(cache.history)), (0, 0, 0))

    def test_oversized_key_cannot_evict_and_failure_does_not_evict(self):
        cache = DeferredFirstAdmissionCache()
        cache.request("a", 1, lambda: "a")
        cache.request("a", 1, lambda: "a")
        before = cache.keys()
        cache.request("too-big", BYTE_LIMIT + 1, lambda: 1)
        self.assertEqual(cache.keys(), before)
        cache.request("broken", 1, lambda: 1)
        def fail():
            raise RuntimeError("BUILD_FAILED")
        with self.assertRaisesRegex(RuntimeError, "BUILD_FAILED"):
            cache.request("broken", 1, fail)
        self.assertEqual(cache.keys(), before)

    def test_frozen_order_replay_is_deterministic_and_not_a_performance_verdict(self):
        for name in ("round_robin", "bursty", "mixed", "overflow"):
            first = replay(name, DeferredFirstAdmissionCache)
            self.assertEqual(first, replay(name, DeferredFirstAdmissionCache))
            control = replay(name, OverflowBypassCache)
            self.assertEqual(first["requests"], control["requests"])
            self.assertEqual(first["hits"] + first["misses"], 48)
            self.assertEqual(first["build_calls"], first["admissions"])
            self.assertLessEqual(first["admissions"], control["admissions"])
            self.assertNotIn("throughput_speedup", first)
            self.assertNotIn("qualifies", first)

if __name__ == "__main__":
    unittest.main()

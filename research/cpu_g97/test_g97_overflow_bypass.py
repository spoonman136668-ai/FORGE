"""G97 deterministic adversarial tests; no original-model inference."""
import unittest
from research.cpu_g97.g97_overflow_bypass import OverflowBypassCache, WINDOW
from research.cpu_g96.g96_admission import BYTE_LIMIT

class G97OverflowTests(unittest.TestCase):
    def test_online_overflow_bypass_and_recovery(self):
        c = OverflowBypassCache()
        builds = []
        def request(k):
            return c.request(k, 1, lambda: builds.append(k) or k)
        for i in range(WINDOW):
            request("cold-%d" % i)
        before = len(builds)
        value, hit, admitted = request("new")
        self.assertEqual((value, hit, admitted), (None, False, False))
        self.assertEqual(len(builds), before)
        self.assertTrue(c.overflow)
        for i in range(WINDOW):
            request("stable-%d" % (i % 4))
        request("stable-0")
        self.assertFalse(c.overflow)
        self.assertEqual(c.transitions, 2)
        self.assertLessEqual(len(c.entries), 4)

    def test_oversized_and_failed_build_do_not_evict(self):
        c = OverflowBypassCache()
        c.request("a", 1, lambda: "a")
        keys = c.keys()
        self.assertEqual(c.request("oversized", BYTE_LIMIT+1, lambda: "bad"), (None, False, False))
        self.assertEqual(c.keys(), keys)
        def fail(): raise RuntimeError("BUILD_FAIL")
        with self.assertRaisesRegex(RuntimeError, "BUILD_FAIL"):
            c.request("b", 1, fail)
        self.assertEqual(c.keys(), keys)

    def test_exact_key_and_immutable_budget(self):
        c = OverflowBypassCache()
        for k in ("A", "a", "A "):
            c.request(k, 1, lambda k=k: k)
        self.assertEqual(len(c.entries), 3)
        self.assertTrue(c.request("A", 1, lambda: None)[1])
        self.assertLessEqual(c.resident_bytes(), BYTE_LIMIT)

    def test_reject_invalid_input_without_mutation(self):
        c = OverflowBypassCache()
        with self.assertRaises(ValueError): c.request("", 1, lambda: None)
        with self.assertRaises(ValueError): c.request("x", -1, lambda: None)
        self.assertEqual(c.decision_count, 0)
        self.assertEqual(len(c.history), 0)

    def test_determinism(self):
        def run():
            c = OverflowBypassCache()
            for i in range(80):
                k = "k%d" % (i % 9 if i < 40 else i % 3)
                c.request(k, 1, lambda k=k: k)
            return (c.keys(), c.hits, c.misses, c.bypasses, c.transitions)
        self.assertEqual(run(), run())

if __name__ == "__main__":
    unittest.main()
